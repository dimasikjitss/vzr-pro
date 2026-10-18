import requests
import io
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from decimal import Decimal
import json  # <--- Добавьте это
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden 
from django.contrib import messages
from django.db.models import Sum, Count
from nomad.models import NomadTariff, NomadPolicy
from django.core.serializers.json import DjangoJSONEncoder
from openpyxl import Workbook
from openpyxl.utils import get_column_letter # Добавь этот импорт в начало файла
from openpyxl.styles import Font, Alignment, PatternFill
from django.contrib.contenttypes.models import ContentType
from .models import InsurancePolicy, InsuranceTariff, InsuredPerson, Branch, IndividualHolder, CompanyHolder
from student.models import StudentPolicy, StudentTariff
from nomad.models import NomadPolicy
from .analytics_core import PRODUCT_ANALYTICS_MAP, AnalyticsManager
from dms_tourist.models import DMSTouristTariff, DMSTouristPolicy

# --- УТИЛИТЫ ---

def is_superadmin(user):
    return user.is_superuser

def get_nbkr_rates():
    """Курсы валют НБКР"""
    rates = {'USD': Decimal('88.45'), 'EUR': Decimal('96.20')}
    try:
        response = requests.get("https://www.nbkr.kg/XML/daily.xml", timeout=5)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            for currency in root.findall('Currency'):
                code = currency.get('ISOCode')
                if code in rates:
                    raw_value = currency.find('Value').text.replace(',', '.')
                    rates[code] = Decimal(raw_value).quantize(Decimal('0.01'))
    except Exception as e:
        print(f"Ошибка НБКР: {e}")
    return rates

@login_required
def home(request):
    """Главная страница с быстрым калькулятором и журналами по 4 продуктам"""
    rates = get_nbkr_rates()
    
    # 1. Тарифы всех 4-х продуктов для калькулятора в JS
    tariffs_qs = list(InsuranceTariff.objects.all().values('program', 'territory', 'sum_insured', 'days_min', 'days_max', 'rate'))
    tariffs_json = json.dumps(tariffs_qs, default=str) 
    
    nomad_tariffs = NomadTariff.objects.filter(program='BRONZE').values('days_min', 'days_max', 'percent_rate')
    student_tariffs = StudentTariff.objects.all().values('time_type', 'is_sports', 'percent_rate')
    
    # Тарифы ДМС Турист
    dms_tariffs = DMSTouristTariff.objects.all().values('sum_insured', 'days_min', 'days_max', 'duration_coeff', 'base_daily_rate')

    # 2. Списки последних полисов (для суперадмина — все, для агента — свои)
    if request.user.is_superuser:
        last_policies = InsurancePolicy.objects.all().order_by('-id')[:10]
        last_policies_nomad = NomadPolicy.objects.all().order_by('-id')[:10]
        last_policies_student = StudentPolicy.objects.all().order_by('-id')[:10]
        last_policies_dms = DMSTouristPolicy.objects.all().order_by('-id')[:10]
    else:
        last_policies = InsurancePolicy.objects.filter(agent=request.user).order_by('-issue_date', '-id')[:10]
        last_policies_nomad = NomadPolicy.objects.filter(agent=request.user).order_by('-issue_date', '-id')[:10]
        last_policies_student = StudentPolicy.objects.filter(agent=request.user).order_by('-issue_date', '-id')[:10]
        last_policies_dms = DMSTouristPolicy.objects.filter(agent=request.user).order_by('-issue_date', '-id')[:10]

    # 3. Финансовые сборы за текущий месяц
    start_month = date.today().replace(day=1)
    end_month = date.today()

    if request.user.is_superuser:
        vzr_total = InsurancePolicy.objects.filter(issue_date__gte=start_month).aggregate(Sum('total_premium_som'))['total_premium_som__sum'] or 0
        nomad_total = NomadPolicy.objects.filter(issue_date__gte=start_month).aggregate(Sum('total_premium_gross'))['total_premium_gross__sum'] or 0
        student_total = StudentPolicy.objects.filter(issue_date__gte=start_month).aggregate(Sum('total_premium_gross'))['total_premium_gross__sum'] or 0
        dms_total = DMSTouristPolicy.objects.filter(issue_date__gte=start_month).aggregate(Sum('total_premium_gross'))['total_premium_gross__sum'] or 0
    else:
        vzr_total = InsurancePolicy.objects.filter(agent=request.user, issue_date__gte=start_month).aggregate(Sum('total_premium_som'))['total_premium_som__sum'] or 0
        nomad_total = NomadPolicy.objects.filter(agent=request.user, issue_date__gte=start_month).aggregate(Sum('total_premium_gross'))['total_premium_gross__sum'] or 0
        student_total = StudentPolicy.objects.filter(agent=request.user, issue_date__gte=start_month).aggregate(Sum('total_premium_gross'))['total_premium_gross__sum'] or 0
        dms_total = DMSTouristPolicy.objects.filter(agent=request.user, issue_date__gte=start_month).aggregate(Sum('total_premium_gross'))['total_premium_gross__sum'] or 0

    monthly_total = vzr_total + nomad_total + student_total + dms_total

    return render(request, 'insurance/new_home.html', {
        'usd_rate': rates['USD'], 
        'eur_rate': rates['EUR'],
        
        # Журналы
        'last_policies': last_policies,
        'last_policies_nomad': last_policies_nomad,
        'last_policies_student': last_policies_student,
        'last_policies_dms': last_policies_dms,
        
        # Финансы
        'monthly_total': monthly_total,
        'vzr_total': vzr_total,
        'nomad_total': nomad_total,
        'student_total': student_total,
        'dms_total': dms_total,
        
        # Тарифы для JS
        'tariffs_data': tariffs_json,
        'tariffs_nomad_json': json.dumps(list(nomad_tariffs), cls=DjangoJSONEncoder),
        'tariffs_student_json': json.dumps(list(student_tariffs), cls=DjangoJSONEncoder),
        'tariffs_dms_json': json.dumps(list(dms_tariffs), cls=DjangoJSONEncoder),
        
        'start_month': start_month,
        'end_month': end_month,
    })

@login_required
def vzr_create(request):
    rates = get_nbkr_rates()
    try:
        user_branch = request.user.profile.branch
    except Exception:
        return render(request, 'insurance/error.html', {'message': 'Филиал не настроен в профиле.'})

    if request.method == "POST":
        try:
            # 1. Определяем, кто страхователь: 'individual' (физ) или 'company' (юр)
            holder_kind = request.POST.get('holder_kind', 'individual')
            holder_instance = None

            if holder_kind == 'company':
                # Создаем или находим Юридическое лицо (ищем по ИНН)
                holder_instance = CompanyHolder.objects.create(
                    company_name=request.POST.get('company_name', '').strip().upper(),
                    inn=request.POST.get('company_inn', '').strip(),
                    okpo=request.POST.get('company_okpo', '').strip(),
                    legal_address=request.POST.get('company_address', '').strip().upper(),
                    signatory_name=request.POST.get('company_signatory', '').strip().upper(),
                    phone=request.POST.get('company_phone', '').strip(),
                )
            else:
                # По дефолту создаем или находим Физическое лицо (ищем по Паспорту)
                holder_instance = IndividualHolder.objects.create(
                    passport=request.POST.get('holder_passport', '').strip().upper(),
                    name=request.POST.get('holder_name', '').strip().upper(),
                    inn=request.POST.get('holder_inn', '').strip(),
                    phone=request.POST.get('holder_phone', '').strip(),
                    address=request.POST.get('holder_address', '').strip().upper(),
                    relative_contact=request.POST.get('holder_relative', '').strip() or "Не указан",
                )

            # 2. Создаем полис и передаем туда наш holder_instance
            # Наш кастомный метод save() сам заполнит старые текстовые поля (holder_name, holder_phone и т.д.)
            policy = InsurancePolicy.objects.create(
                agent=request.user,
                branch=user_branch,
                holder=holder_instance,  # <- Передаем объект напрямую в GenericForeignKey
                date_from=date.fromisoformat(request.POST.get('start_date')),
                date_to=date.fromisoformat(request.POST.get('end_date')),
                territory=request.POST.get('territory'),
                to_country=request.POST.get('to_country', '').strip().upper(),
                program=request.POST.get('program'),
                activity_type=request.POST.get('activity'),
                exchange_rate=Decimal(request.POST.get('exchange_rate', '1.0').replace(',', '.'))
            )
            
            # 3. Логика добавления застрахованных (осталась без изменений)
            names = request.POST.getlist('insured_name[]')
            dobs = request.POST.getlist('insured_dob[]')
            passports = request.POST.getlist('insured_passport[]')
            sums = request.POST.getlist('insured_sum[]')
            premiums = request.POST.getlist('insured_premium[]')
            
            total_cur = Decimal('0.00')
            for i in range(len(names)):
                if names[i].strip():
                    person = InsuredPerson.objects.create(
                        policy=policy,
                        full_name=names[i].strip().upper(),
                        date_of_birth=date.fromisoformat(dobs[i]),
                        passport_number=passports[i].strip().upper(),
                        sum_insured_currency=Decimal(sums[i] or 0),
                        premium_currency=Decimal(premiums[i] or 0)
                    )
                    total_cur += person.premium_currency
            
            policy.total_premium_currency = total_cur
            policy.total_premium_som = (total_cur * policy.exchange_rate * Decimal(1.02)).quantize(Decimal('0.01'))
            policy.save()
            
            return redirect('policy_success', pk=policy.pk)
        except Exception as e:
            messages.error(request, f"Ошибка сохранения: {e}")

    return render(request, 'insurance/vzr_create.html', {
        'usd_rate': rates['USD'], 'eur_rate': rates['EUR'],
        'current_branch_code': user_branch.code if user_branch else '??'
    })


@login_required
def policy_preview(request):
    if request.method == "POST":
        try:
            # 1. Получаем базовые данные полиса
            exchange_rate_str = request.POST.get('exchange_rate', '1.0').replace(',', '.')
            exchange_rate = Decimal(exchange_rate_str or '1.0')
            
            d_from_raw = request.POST.get('start_date')
            d_to_raw = request.POST.get('end_date')
            
            if not d_from_raw or not d_to_raw:
                return HttpResponse("Ошибка: Не указаны даты действия полиса")
                
            d_from = date.fromisoformat(d_from_raw)
            d_to = date.fromisoformat(d_to_raw)
            calculated_days = (d_to - d_from).days + 1
            
            # --- УМНОЕ ОПРЕДЕЛЕНИЕ ТИПА СТРАХОВАТЕЛЯ ---
            company_name_raw = request.POST.get('company_name', '').strip()
            holder_name_raw = request.POST.get('holder_name', '').strip()
            
            holder_fake_obj = {}

            # Если на форме заполнено имя компании — это 100% Юридическое Лицо
            if company_name_raw:
                holder_fake_obj = {
                    'company_name': company_name_raw.upper(),
                    'inn': request.POST.get('company_inn', '').strip(),
                    'okpo': request.POST.get('company_okpo', '').strip(),
                    'legal_address': request.POST.get('company_address', '').strip().upper(),
                    'signatory_name': request.POST.get('company_signatory', '').strip().upper(),
                    'phone': request.POST.get('company_phone', '').strip(),
                }
            # Во всех остальных случаях собираем данные как для Физического Лица
            else:
                holder_fake_obj = {
                    'name': holder_name_raw.upper() if holder_name_raw else "НЕ УКАЗАНО",
                    'passport': request.POST.get('holder_passport', '').strip().upper(),
                    'inn': request.POST.get('holder_inn', '').strip(),
                    'address': request.POST.get('holder_address', '').strip().upper(),
                    'phone': request.POST.get('holder_phone', '').strip(),
                    'relative_contact': request.POST.get('holder_relative', '').strip() or "Не указан",
                }

            preview_policy = {
                'policy_number': 'ПРОЕКТ / DRAFT',
                'issue_date': date.today(),
                'agent': request.user, 
                
                # Передаем сымитированный объект держателя (шаблон увидит его через policy.holder)
                'holder': holder_fake_obj,
                
                'date_from': d_from,
                'date_to': d_to,
                'days_count': calculated_days,
                'territory': request.POST.get('territory', 'Кыргызстан'),
                'program': request.POST.get('program', 'GSO NOMAD BRONZE'),
                'activity_type': request.POST.get('activity', 'NONE'),
                'exchange_rate': exchange_rate,
                
                # Инициализируем флаги для чекбоксов/галочек в HTML
                'has_child': False,
                'has_adult': False,
                'has_senior': False,
            }

            # 2. Получаем списки застрахованных лиц из динамической таблицы
            names = request.POST.getlist('insured_name[]')
            passports = request.POST.getlist('insured_passport[]')
            dobs = request.POST.getlist('insured_dob[]')
            premiums = request.POST.getlist('insured_premium[]')
            sums = request.POST.getlist('insured_sum[]')

            insured_persons = []
            total_cur = Decimal('0.00')
            total_netto_som = Decimal('0.00')
            total_nsp_som = Decimal('0.00')
            nsp_factor = Decimal('1.02') # Налог с продаж 2%
            
            today = date.today()

            for i in range(len(names)):
                if names[i].strip():
                    # Безопасное получение данных по текущему индексу строки
                    raw_dob_str = dobs[i] if i < len(dobs) else None
                    p_premium_val = premiums[i] if i < len(premiums) else 0
                    p_sum_val = sums[i] if i < len(sums) else 0

                    # --- РАСЧЕТ ВОЗРАСТА И КОЭФФИЦИЕНТА ---
                    age = 0
                    age_coeff = Decimal('1.0')
                    formatted_dob = raw_dob_str
                    
                    if raw_dob_str:
                        try:
                            dob_date = date.fromisoformat(raw_dob_str)
                            formatted_dob = dob_date.strftime('%d.%m.%Y')
                            
                            # Вычисляем точный возраст на сегодняшний день
                            age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
                            
                            # Проверяем возрастные группы и взводим соответствующие флаги в полисе
                            if age <= 4:
                                age_coeff = Decimal('2.0')
                                preview_policy['has_child'] = True
                            elif age >= 65:
                                age_coeff = Decimal('2.5')
                                preview_policy['has_senior'] = True
                            else:
                                age_coeff = Decimal('1.0')
                                preview_policy['has_adult'] = True
                                
                        except ValueError:
                            # Если дата рождения не распарсилась, ставим дефолт "взрослый"
                            preview_policy['has_adult'] = True

                    # --- МАТЕМАТИЧЕСКИЕ РАСЧЕТЫ СУММ И ПРЕМИЙ ---
                    p_total_cur = Decimal(str(p_premium_val or 0).replace(',', '.'))
                    p_sum_cur = Decimal(str(p_sum_val or 0).replace(',', '.'))
                    
                    p_total_som = (p_total_cur * exchange_rate).quantize(Decimal('0.01'))
                    p_sum_som = (p_sum_cur * exchange_rate).quantize(Decimal('1.00'))
                    
                    # Расчет НСП (Налог С Продаж) 2%
                    p_netto_som = (p_total_som * nsp_factor).quantize(Decimal('0.01'))
                    p_nsp_som = (p_netto_som - p_total_som).quantize(Decimal('0.01'))
                    
                    # Сумма нетто в валюте для отображения
                    p_netto_cur = (p_total_cur * nsp_factor).quantize(Decimal('0.01'))

                    # Наполняем структуру застрахованного лица для передачи в контекст шаблона
                    insured_persons.append({
                        'full_name': names[i].strip().upper(),
                        'passport_number': passports[i].strip().upper() if i < len(passports) else '',
                        'date_of_birth': formatted_dob,
                        'age': age,  
                        'age_coeff': age_coeff, 
                        'sum_insured_currency': p_sum_cur,
                        'sum_insured_som': p_sum_som,
                        'premium_currency': p_total_cur,
                        'premium_som': p_total_som,
                        'premium_netto_cur': p_netto_cur,
                        'premium_netto_som': p_netto_som,
                        'nsp_amount_som': p_nsp_som,
                    })
                    
                    # Аккумулируем общие итоги по всему документу
                    total_cur += p_total_cur
                    total_netto_som += p_netto_som
                    total_nsp_som += p_nsp_som

            # Страховка от пустой таблицы: если застрахованных нет, ставим дефолтную галочку "взрослый"
            if not insured_persons:
                preview_policy['has_adult'] = True

            # Записываем агрегированные финансовые итоги в словарь проекта полиса
            preview_policy['total_premium_currency'] = total_cur
            preview_policy['total_premium_som'] = total_netto_som 
            preview_policy['total_netto_som'] = total_netto_som
            preview_policy['total_nsp_som'] = total_nsp_som

            # Возвращаем сгенерированную страницу предпросмотра
            return render(request, 'insurance/policy_pdf.html', {
                'policy': preview_policy,
                'insured_persons_preview': insured_persons,
                'is_draft': True
            })
            
        except Exception as e:
            # Предотвращаем падение страницы белым экраном, выводим ошибку для быстрой отладки
            return HttpResponse(f"Ошибка подготовки предпросмотра: {str(e)}")
            
    return redirect('home')


# @login_required
# def admin_dashboard(request):
#     """Панель аналитики и отчетов (Доступна админам и агентам с разграничением по филиалам)"""
#     branch_id = request.GET.get('branch')
#     date_from_raw = request.GET.get('date_from')
#     date_to_raw = request.GET.get('date_to')
#     today = date.today()

#     # 1. ЛОГИКА ДАТ: По умолчанию берем с 1-го числа ТЕКУЩЕГО месяца по ТЕКУЩИЙ день
#     if date_from_raw and date_to_raw:
#         try:
#             d_from = date.fromisoformat(date_from_raw)
#             d_to = date.fromisoformat(date_to_raw)
#             current_period = 'custom'
#         except ValueError:
#             d_from = today.replace(day=1)
#             d_to = today
#             current_period = 'month'
#     else:
#         d_from = today.replace(day=1)
#         d_to = today
#         current_period = 'month'

#     # 2. ОГРАНИЧЕНИЕ ПРАВ: Если не суперюзер, то принудительно берем только филиал сотрудника
#     is_admin = request.user.is_superuser
#     user_branch = getattr(request.user, 'branch', None)

#     if not is_admin:
#         if user_branch:
#             branch_id = str(user_branch.id)
#         else:
#             # Если у пользователя нет филиала и он не админ — возвращаем пустой дашборд во избежание утечки
#             return render(request, 'insurance/admin_dashboard.html', {'error': 'Вы не привязаны к филиалу'})

#     # 3. ФОРМИРОВАНИЕ QUERYSETS
#     # Базовые фильтры по датам
#     vzr_filter = {'issue_date__range': [d_from, d_to]}
#     student_filter = {'issue_date__range': [d_from, d_to]} # Предполагается поле issue_date в StudentPolicy

#     if branch_id:
#         vzr_filter['branch_id'] = branch_id
#         student_filter['branch_id'] = branch_id

#     policies_vzr = InsurancePolicy.objects.filter(**vzr_filter).select_related('agent', 'branch').order_by('-issue_date')
#     policies_student = StudentPolicy.objects.filter(**student_filter).select_related('agent', 'branch').order_by('-issue_date')

#     # Инициализация структур для графиков и KPI
#     sales_by_day = {}
#     regions_map = {}
#     agents_map = {}
#     total_som = 0
#     total_count = 0

#     all_territories = ['ASIA', 'SCHENGEN', 'WORLD', 'KYRGYZSTAN'] # Добавили КР для детских полисов
#     all_programs = ['BRONZE', 'SILVER', 'GOLD', 'CHILD_PROG']
#     prog_territory_map = {prog: {terr: 0 for terr in all_territories} for prog in all_programs}

#     # ОБРАБОТКА ВЗР ПОЛИСОВ
#     for p in policies_vzr:
#         val = float(p.total_premium_som or 0)
#         total_som += val
#         total_count += 1
        
#         day = p.issue_date.strftime('%d.%m') if p.issue_date else "??.??"
#         sales_by_day[day] = sales_by_day.get(day, 0) + val
        
#         reg = str(p.territory or "Не указано").upper()
#         regions_map[reg] = regions_map.get(reg, 0) + val
        
#         prog = str(p.program).upper() if p.program else "BRONZE"
#         if prog in prog_territory_map and reg in prog_territory_map[prog]:
#             prog_territory_map[prog][reg] += val

#         ag_name = f"{p.agent.first_name} {p.agent.last_name}" if p.agent else "Неизвестный"
#         if ag_name not in agents_map: agents_map[ag_name] = {'count': 0, 'total': 0}
#         agents_map[ag_name]['count'] += 1
#         agents_map[ag_name]['total'] += val

#     # ОБРАБОТКА ДЕТСКИХ ПОЛИСОВ (Интеграция в общую аналитику)
#     for p in policies_student:
#         val = float(p.total_premium_gross or 0) # Суммируем брутто сбор по детям
#         total_som += val
#         total_count += 1
        
#         day = p.issue_date.strftime('%d.%m') if p.issue_date else "??.??"
#         sales_by_day[day] = sales_by_day.get(day, 0) + val
        
#         # Детские полисы по умолчанию относятся к территории КР
#         regions_map['KYRGYZSTAN'] = regions_map.get('KYRGYZSTAN', 0) + val
        
#         prog_name = str(p.program.name).upper() if p.program else "CHILD_PROG"
#         if prog_name not in prog_territory_map:
#             prog_territory_map[prog_name] = {terr: 0 for terr in all_territories}
#         if 'KYRGYZSTAN' in prog_territory_map[prog_name]:
#             prog_territory_map[prog_name]['KYRGYZSTAN'] += val

#         ag_name = f"{p.agent.first_name} {p.agent.last_name}" if p.agent else "Неизвестный"
#         if ag_name not in agents_map: agents_map[ag_name] = {'count': 0, 'total': 0}
#         agents_map[ag_name]['count'] += 1
#         agents_map[ag_name]['total'] += val

#     # Формирование данных для графиков ApexCharts
#     chart_program_series = []
#     for terr in all_territories:
#         chart_program_series.append({
#             'name': terr,
#             'data': [round(prog_territory_map.get(prog, {}).get(terr, 0), 2) for prog in prog_territory_map.keys()]
#         })

#     # Сбор статистики по филиалам
#     branch_stats = policies_vzr.values('branch__name').annotate(total=Sum('total_premium_som'), count=Count('id')).order_by('-total')

#     context = {
#         'policies': policies_vzr,
#         'student_policies': policies_student,
#         'branches': Branch.objects.all() if is_admin else [user_branch], # Обычный агент видит только свой филиал в селекторе
#         'branch_stats': branch_stats,
#         'total_som': total_som,
#         'total_count': total_count,
#         'date_from': d_from.isoformat(),
#         'date_to': d_to.isoformat(),
#         'current_period': current_period,
#         'selected_branch': branch_id,
#         'is_admin': is_admin,
#         'chart_daily_labels': list(sales_by_day.keys())[::-1],
#         'chart_daily_values': list(sales_by_day.values())[::-1],
#         'chart_region_labels': list(regions_map.keys()),
#         'chart_region_values': list(regions_map.values()),
#         'chart_program_labels': list(prog_territory_map.keys()),
#         'chart_program_series': chart_program_series,
#         'agent_performance': [{'name': n, 'count': d['count'], 'avg_check': round(d['total']/d['count'], 0)} for n, d in agents_map.items()]
#     }
#     return render(request, 'insurance/admin_dashboard.html', context)


@login_required
# def admin_dashboard(request):
    # """Глобальная панель аналитики по 3 продуктам (Строго для Суперпользователей)"""
    # # Доступ только суперюзеру по требованию заказчика
    # if not request.user.is_superuser:
    #     return HttpResponseForbidden("Доступ к сводной аналитике разрешен только суперпользователям.")

    # branch_id = request.GET.get('branch')
    # date_from_raw = request.GET.get('date_from')
    # date_to_raw = request.GET.get('date_to')
    # today = date.today()

    # if date_from_raw and date_to_raw:
    #     try:
    #         d_from = date.fromisoformat(date_from_raw)
    #         d_to = date.fromisoformat(date_to_raw)
    #         current_period = 'custom'
    #     except ValueError:
    #         d_from = today.replace(day=1)
    #         d_to = today
    #         current_period = 'month'
    # else:
    #     d_from = today.replace(day=1)
    #     d_to = today
    #     current_period = 'month'

    # # Вызываем наше новое архитектурное решение
    # metrics = AnalyticsManager.get_global_summary_metrics(d_from, d_to, branch_id=branch_id)

    # context = {
    #     'branches': Branch.objects.all().order_by('code'),
    #     'date_from': d_from.isoformat(),
    #     'date_to': d_to.isoformat(),
    #     'current_period': current_period,
    #     'selected_branch': branch_id,
    #     'is_admin': True,
        
    #     # Общие KPI
    #     'total_som': metrics['total_som'],
    #     'total_count': metrics['total_count'],
        
    #     # Доли продуктов для отображения круговых графиков (если нужно)
    #     'v_count': metrics['v_count'], 'v_sum': metrics['v_sum'],
    #     'n_count': metrics['n_count'], 'n_sum': metrics['n_sum'],
    #     's_count': metrics['s_count'], 's_sum': metrics['s_sum'],
        
    #     # Данные графиков ApexCharts/Chart.js
    #     'chart_daily_labels': metrics['chart_daily_labels'],
    #     'chart_daily_values': metrics['chart_daily_values'],
    #     'chart_program_labels': metrics['chart_program_labels'],
    #     'chart_program_series': metrics['chart_program_series'],
        
    #     # Таблицы лидеров
    #     'agent_performance': metrics['agent_performance'],
    #     'branch_stats': metrics['branch_stats'],
    # }
    # return render(request, 'insurance/admin_dashboard.html', context)
# --- изменил длЯ новой аналитики тест ---
def admin_dashboard(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Доступ к сводной аналитике разрешен только суперпользователям.")

    branch_id = request.GET.get('branch')
    date_from_raw = request.GET.get('date_from')
    date_to_raw = request.GET.get('date_to')
    active_tab = request.GET.get('tab', 'ALL') # По умолчанию вкладка ВСЕ
    
    today = date.today()

    # По требованию заказчика: по умолчанию с 1-го числа текущего месяца
    if date_from_raw and date_to_raw:
        try:
            d_from = date.fromisoformat(date_from_raw)
            d_to = date.fromisoformat(date_to_raw)
        except ValueError:
            d_from = today.replace(day=1)
            d_to = today
    else:
        d_from = today.replace(day=1)
        d_to = today

    # Сбор обогащенных структурированных данных
    data = AnalyticsManager.get_global_summary_metrics(d_from, d_to, branch_id=branch_id)

    context = {
        'branches': Branch.objects.all().order_by('code'),
        'date_from': d_from.isoformat(),
        'date_to': d_to.isoformat(),
        'selected_branch': branch_id,
        'active_tab': active_tab,

        # Сборы за отчетный период
        'period_total_som': data['period_total_som'],
        'period_total_count': data['period_total_count'],
        'v_sum': data['v_sum'], 'v_count': data['v_count'],
        'n_sum': data['n_sum'], 'n_count': data['n_count'],
        's_sum': data['s_sum'], 's_count': data['s_count'],

        # Сборы за ВСЁ время (All-time)
        'all_time_total_som': data['all_time_total_som'],
        'all_time_total_count': data['all_time_total_count'],
        'all_time_vzr_sum': data['all_time_vzr_sum'],
        'all_time_nomad_sum': data['all_time_nomad_sum'],
        'all_time_student_sum': data['all_time_student_sum'],

        # Сериализация списков для безопасной передачи в ApexCharts
        'chart_dates_json': json.dumps(data['chart_dates']),
        'chart_vzr_json': json.dumps(data['chart_vzr_line']),
        'chart_nomad_json': json.dumps(data['chart_nomad_line']),
        'chart_student_json': json.dumps(data['chart_student_line']),
        
        'branch_labels_json': json.dumps(data['branch_labels']),
        'branch_values_json': json.dumps(data['branch_values']),
        
        'agent_performance_json': json.dumps(data['agent_performance'], cls=DjangoJSONEncoder),
    }

    return render(request, 'insurance/admin_dashboard.html', context)


@login_required
@user_passes_test(is_superadmin)
def export_excel(request):
    # 1. Получаем параметры периода
    d_from_raw = request.GET.get('date_from')
    d_to_raw = request.GET.get('date_to')
    
    try:
        d_from = date.fromisoformat(d_from_raw)
        d_to = date.fromisoformat(d_to_raw)
    except (TypeError, ValueError):
        d_from = d_to = date.today()

    # 2. Выгружаем полисы с СОРТИРОВКОЙ от новых к старым (-issue_date)
    policies = InsurancePolicy.objects.filter(
        issue_date__range=[d_from, d_to]
    ).select_related('agent').prefetch_related('insured_persons').order_by('issue_date', 'id')

    # 3. Создаем Excel книгу
    wb = Workbook()
    ws = wb.active
    ws.title = "Отчет ВЗР"

    headers = [
        'Серия полиса', 'Дата оформления полиса', '№ полиса', 'Страхователь', 
        'Выгодоприобретатель', 'ИНН', 'Номер паспорта', 'Дата рождения', 
        'Телефон', 'Начало действия', 'Окончание действия', 'Курс Доллар/ Евро НБ КР', 
        'Страховая сумма, USD/Euro', 'Страховая сумма, сом', 'Страховая премия без НСП, сомы', 
        'НСП 2%', 'Стр. премия сомы с НСП', 'Кто оформил'
    ]
    ws.append(headers)

    # Жирный шрифт для шапки (опционально, для красоты)
    for cell in ws[1]:
        cell.font = cell.font.copy(bold=True)

    # 4. Наполняем данными
    for p in policies:
        for person in p.insured_persons.all():
            currency_label = "EURO" if p.territory == 'SCHENGEN' else "USD"
            
            ws.append([
                'VZR',
                p.issue_date.strftime('%d.%m.%Y'),
                p.policy_number,
                p.holder_name,
                person.full_name,
                p.holder_inn,
                person.passport_number,
                person.date_of_birth.strftime('%d.%m.%Y'),
                p.holder_phone,
                p.date_from.strftime('%d.%m.%Y'),
                p.date_to.strftime('%d.%m.%Y'),
                p.exchange_rate,
                f"{person.sum_insured_currency} {currency_label}",
                person.sum_insured_som,
                person.premium_som,
                person.nsp_amount_som,
                person.premium_nsp_som,
                # f"P{p.id}",
                p.agent.get_full_name() or p.agent.username
            ])

    # 5. АВТОПОДБОР ШИРИНЫ КОЛОНОК (AutoFit)
    for col in ws.columns:
        max_length = 0
        column_letter = get_column_letter(col[0].column)
        for cell in col:
            try:
                if cell.value:
                    # Считаем длину содержимого и берем максимум
                    val_len = len(str(cell.value))
                    if val_len > max_length:
                        max_length = val_len
            except:
                pass
        # Устанавливаем ширину с небольшим запасом (+2)
        ws.column_dimensions[column_letter].width = max_length + 2

    # 6. Форматируем ответ
    filename = f"VZR_Report_{d_from}_{d_to}.xlsx"
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response

@login_required
def policy_success(request, pk):
    return render(request, 'insurance/success.html', {'policy': get_object_or_404(InsurancePolicy, pk=pk)})

@login_required
def print_policy(request, pk):
    return render(request, 'insurance/policy_pdf.html', {'policy': get_object_or_404(InsurancePolicy, pk=pk)})

def get_tariffs_api(request):
    return JsonResponse(list(InsuranceTariff.objects.all().values('program', 'territory', 'sum_insured', 'days_min', 'days_max', 'rate')), safe=False)

@login_required
def analytics_page(request):
    """Рендерит страницу аналитики с отфильтрованным журналом полисов"""
    is_admin = request.user.is_superuser
    
    # 1. Читаем параметры фильтра из URL (если они есть)
    d_from_raw = request.GET.get('date_from')
    d_to_raw = request.GET.get('date_to')
    branch_id_raw = request.GET.get('branch')

    # Устанавливаем даты по умолчанию (последние 30 дней), если ничего не передано
    try:
        d_from = date.fromisoformat(d_from_raw)
        d_to = date.fromisoformat(d_to_raw)
    except (TypeError, ValueError):
        d_to = date.today()
        d_from = d_to - timedelta(days=30)

    # 2. Формируем базовый фильтр по датам
    filters = {'issue_date__range': [d_from, d_to]}
    user_branch_id = None

    # 3. АРХИТЕКТУРНАЯ ПРОВЕРКА ПРАВ (как в отчетах)
    if not is_admin:
        profile = getattr(request.user, 'profile', None)
        if profile and profile.branch:
            user_branch_id = profile.branch.id
            filters['branch_id'] = user_branch_id
        else:
            # Подстраховка: если у сотрудника нет филиала, ставим нереальный ID, 
            # чтобы не выводить чужие данные
            filters['branch_id'] = -1 
    else:
        # Для админа: если он выбрал конкретный филиал в фильтре
        if branch_id_raw and str(branch_id_raw).strip():
            filters['branch_id'] = branch_id_raw
            # Сохраняем ID для селекта на фронтенде, чтобы он не сбрасывался
            try:
                user_branch_id = int(branch_id_raw)
            except ValueError:
                pass

    # 4. Выгружаем отфильтрованные полисы 
    # (Ограничиваем до 100 штук, чтобы страница не висла, если выберут период за 5 лет)
    last_policies = InsurancePolicy.objects.filter(**filters).select_related('agent', 'branch').prefetch_related('insured_persons').order_by('-issue_date')[:100]
    last_policies_nomad = NomadPolicy.objects.filter(**filters).select_related('agent', 'branch').order_by('-issue_date')[:100]
    last_policies_student = StudentPolicy.objects.filter(**filters).select_related('agent', 'branch').order_by('-issue_date')[:100]

    context = {
        'is_admin': is_admin,
        'user_branch_id': user_branch_id,
        'branches': Branch.objects.all().order_by('code'),
        # Передаем списки в шаблон для таблицы
        'last_policies': last_policies,
        'last_policies_nomad': last_policies_nomad,
        'last_policies_student': last_policies_student,
        # Передаем текущие даты обратно в шаблон, чтобы подставить в инпуты
        'default_date_from': d_from.strftime('%Y-%m-%d'),
        'default_date_to': d_to.strftime('%Y-%m-%d'),
    }
    return render(request, 'insurance/analytics_dashboard.html', context)

@login_required
def analytics_api(request):
    """Возвращает JSON для графиков, карточек и журнала с фильтрацией по дате и филиалу"""
    product_type = request.GET.get('product', 'vzr').lower()
    d_from_raw = request.GET.get('date_from')
    d_to_raw = request.GET.get('date_to')
    branch_id = request.GET.get('branch')

    try:
        d_from = date.fromisoformat(d_from_raw)
        d_to = date.fromisoformat(d_to_raw)
    except (TypeError, ValueError):
        d_to = date.today()
        d_from = d_to - timedelta(days=30)

    # Жесткая архитектурная проверка прав
    if not request.user.is_superuser:
        profile = getattr(request.user, 'profile', None)
        if profile and profile.branch:
            branch_id = profile.branch.id
        else:
            return JsonResponse({'error': 'Доступ запрещен'}, status=403)

    if product_type not in PRODUCT_ANALYTICS_MAP:
        return JsonResponse({'error': 'Неизвестный продукт'}, status=400)

    metrics_func = PRODUCT_ANALYTICS_MAP[product_type]
    data = metrics_func(d_from, d_to, branch_id=branch_id)

    # --- ДОБАВЛЯЕМ ВЫГРУЗКУ ЖУРНАЛА СТРОГО ЗА ВЫБРАННЫЙ ПЕРИОД ---
    filters = {'issue_date__range': [d_from, d_to]}
    if branch_id and str(branch_id).strip():
        filters['branch_id'] = branch_id

    policies_list = []

    if product_type == 'vzr':
        policies = InsurancePolicy.objects.filter(**filters).select_related('agent').prefetch_related('insured_persons').order_by('-issue_date','-id')[:50]
        for p in policies:
            first_person = p.insured_persons.first()
            limit_val = f"{int(first_person.sum_insured_currency)} EUR" if p.territory == "SCHENGEN" else f"{int(first_person.sum_insured_currency)} USD" if first_person else "-"
            policies_list.append({
                'date': p.issue_date.strftime('%d.%m.%Y'),
                'holder_name': p.holder_name,
                'policy_number': p.policy_number,
                'details': f"{p.territory} / {p.to_country or ''}",
                'program': p.program.name if hasattr(p.program, 'name') else str(p.program),
                'limit': limit_val,
                'spec': p.activity_type,
                'premium': float(p.total_premium_som),
                'print_url': f"/print/{p.pk}/" # Проверь свой урл для печати ВЗР
            })
            
    elif product_type == 'vt':
        policies = NomadPolicy.objects.filter(**filters).select_related('agent').order_by('-issue_date','-id')[:50]
        for p in policies:
            policies_list.append({
                'date': p.issue_date.strftime('%d.%m.%Y'),
                'holder_name': p.holder_name,
                'policy_number': p.policy_number,
                'details': "Кыргызстан",
                'program': str(p.program),
                'limit': f"{int(p.total_sum_insured)} СОМ",
                'spec': "—",
                'premium': float(p.total_premium_gross),
                'print_url': f"/nomad/print/{p.pk}/" # Проверь урл для печати Nomad
            })
            
    elif product_type == 'student':
        policies = StudentPolicy.objects.filter(**filters).select_related('agent').order_by('-issue_date','-id')[:50]
        for p in policies:
            spec_val = "Спорт. секции" if p.is_sports_section else "Без спорта"
            policies_list.append({
                'date': p.issue_date.strftime('%d.%m.%Y'),
                'holder_name': p.holder_name,
                'policy_number': p.policy_number,
                'details': "Покрытие 24ч" if p.time_type == "24H" else "Во время учебы",
                'program': p.program.name if hasattr(p.program, 'name') else str(p.program),
                'limit': f"{int(p.total_sum_insured)} СОМ",
                'spec': spec_val,
                'premium': float(p.total_premium_gross),
                'print_url': f"/student/print/{p.pk}/" # Проверь урл для печати Детей
            })

    elif product_type == 'dms':
        policies = DMSTouristPolicy.objects.filter(**filters).select_related('agent').prefetch_related('insured_persons').order_by('-issue_date', '-id')[:50]
        for p in policies:
            first_person = p.insured_persons.first()
            policies_list.append({
                'date': p.issue_date.strftime('%d.%m.%Y'),
                'holder_name': p.holder_name,
                'policy_number': p.policy_number,
                'details': p.get_purpose_display(),
                'program': "ДМС Турист",
                'limit': f"{p.sum_insured} СОМ",
                'spec': f"{p.days_count} дн.",
                'premium': float(p.total_premium_gross),
                'print_url': f"/dms-tourist/print/{p.pk}/"
            })

    data['recent_policies'] = policies_list
    return JsonResponse(data)

@login_required
def export_excel_buh(request):

    # 1. Получаем параметры периода из запроса
    d_from_raw = request.GET.get('date_from')
    d_to_raw = request.GET.get('date_to')
    branch_id = request.GET.get('branch') # ЛОВИМ ФИЛИАЛ ИЗ ШАБЛОНА
    
    try:
        d_from = date.fromisoformat(d_from_raw)
        d_to = date.fromisoformat(d_to_raw)
    except (TypeError, ValueError):
        d_from = d_to = date.today()

    date_from_str = d_from.strftime('%d.%m.%Y')
    date_to_str = d_to.strftime('%d.%m.%Y')

   # 2. АРХИТЕКТУРНАЯ ПРОВЕРКА ПРАВ И ФИЛЬТРАЦИЯ ПО ФИЛИАЛУ
    filters = {'issue_date__range': [d_from, d_to]}
    
    if not request.user.is_superuser:
        # ИСПРАВЛЕНО: Залезаем в профиль обычного сотрудника для проверки филиала
        profile = getattr(request.user, 'profile', None)
        if profile and profile.branch:
            filters['branch_id'] = profile.branch.id
        else:
            return HttpResponse("Вы не привязаны к филиалу", status=403)
    else:
        # Если админ И выбрал конкретный филиал в фильтре шаблона
        if branch_id and str(branch_id).strip():
            filters['branch_id'] = branch_id

    # Выгружаем полисы с учетом динамических фильтров
    policies = InsurancePolicy.objects.filter(**filters)\
        .select_related('agent', 'branch')\
        .prefetch_related('insured_persons')\
        .order_by('issue_date', 'id')

    # 3. Создаем Excel книгу
    wb = Workbook()
    ws = wb.active
    ws.title = "Отчет ВЗР Бухгалтерия"

    # Настройки шрифтов и стилей
    font_title = Font(name='Arial', size=14, bold=True, color="1E293B")
    font_bold = Font(name='Arial', size=10, bold=True)
    font_regular = Font(name='Arial', size=10, bold=False)
    align_center = Alignment(horizontal='center', vertical='center', wrap_text=True)
    align_left = Alignment(horizontal='left', vertical='center')
    fill_summary = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

    # --- ГЛАВНЫЙ ЗАГОЛОВОК ---
    ws.append([f"Отчет по полисам VZR за период с {date_from_str} по {date_to_str}"])
    ws.row_dimensions[1].height = 35
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=4)
    ws.cell(row=1, column=1).font = font_title
    ws.cell(row=1, column=1).alignment = align_center

    # --- СТРОКА 2: Отступ ---
    ws.append([])
    ws.row_dimensions[2].height = 15

    # --- СТРОКА 3: Шапка таблицы ---
    headers = [
        'Серия полиса', 'Дата оформления полиса', '№ полиса', 'Страхователь', 
        'Выгодоприобретатель', 'ИНН', 'Номер паспорта', 'Дата рождения', 
        'Телефон', 'Начало действия', 'Окончание действия', 'Курс Доллар/Евро НБКР', 
        'Страховая сумма, USD/Euro', 'Страховая сумма, сом', 'Страховая премия без НСП, сомы', 
        'НСП 2%', 'Стр. премия сомы с НСП', 'Кто оформил'
    ]
    ws.append(headers)
    
    ws.row_dimensions[3].height = 28
    for cell in ws[3]:
        cell.font = font_bold
        cell.alignment = align_center

    # Переменные для общих итогов
    total_policies_count = 0
    total_premium_gross = Decimal('0.00')
    branch_stats = {}

    # 4. Наполняем таблицу данными
    for p in policies:
        branch_code = p.branch.code
        branch_name = p.branch.name
        
        if branch_code not in branch_stats:
            branch_stats[branch_code] = {
                'name': branch_name,
                'count': 0,
                'sum': Decimal('0.00')
            }

        total_policies_count += 1
        branch_stats[branch_code]['count'] += 1

        for person in p.insured_persons.all():
            currency_label = "EURO" if p.territory == 'SCHENGEN' else "USD"
            
            p_som = Decimal(str(person.premium_som or '0.00'))
            p_nsp_som = Decimal(str(person.premium_nsp_som or '0.00'))
            nsp_val = Decimal(str(person.nsp_amount_som or '0.00'))
            
            if p_nsp_som == Decimal('0.00') and p_som > Decimal('0.00'):
                final_premium_gross = p_som
            else:
                final_premium_gross = p_nsp_som
            
            total_premium_gross += final_premium_gross
            branch_stats[branch_code]['sum'] += final_premium_gross
            
            row_data = [
                'VZR',
                p.issue_date.strftime('%d.%m.%Y'),
                p.policy_number,
                p.holder_name,
                person.full_name,
                p.holder_inn,
                person.passport_number,
                person.date_of_birth.strftime('%d.%m.%Y'),
                p.holder_phone,
                p.date_from.strftime('%d.%m.%Y'),
                p.date_to.strftime('%d.%m.%Y'),
                p.exchange_rate,
                f"{person.sum_insured_currency} {currency_label}",
                person.sum_insured_som,
                p_som,
                nsp_val,
                final_premium_gross,
                p.agent.get_full_name() or p.agent.username
            ]
            ws.append(row_data)
            
            current_row = ws.max_row
            ws.row_dimensions[current_row].height = 20
            for cell in ws[current_row]:
                cell.font = font_regular
                cell.alignment = align_center

    # 5. ФОРМИРУЕМ БЛОК ИТОГОВ ВНИЗУ ТАБЛИЦЫ
    ws.append([]) 
    ws.append([]) 

    # --- ОБЩИЙ ИТОГ ПО ВСЕЙ КОМПАНИИ ---
    start_summary_row = ws.max_row + 1
    
    ws.append(['ОБЩИЕ ИТОГИ ЗА ПЕРИОД'])
    ws.merge_cells(start_row=ws.max_row, start_column=1, end_row=ws.max_row, end_column=3)
    ws.cell(row=ws.max_row, column=1).font = font_bold
    ws.cell(row=ws.max_row, column=1).alignment = align_center
    ws.cell(row=ws.max_row, column=1).fill = fill_summary

    ws.append(['Всего оформлено полисов (бланков):', f"{total_policies_count} шт."])
    ws.append(['Общая сумма страховых премий с НСП:', f"{total_premium_gross} сом"])
    
    for r in range(start_summary_row + 1, ws.max_row + 1):
        ws.cell(row=r, column=1).font = font_bold
        ws.cell(row=r, column=2).font = font_bold
        ws.cell(row=r, column=2).alignment = align_center

    ws.append([]) 

    # --- ИТОГИ В РАЗРЕЗЕ ФИЛИАЛОВ (С КРАСИВОЙ СОРТИРОВКОЙ И СТРУКТУРОЙ) ---
    ws.append(['ИТОГИ В РАЗРЕЗЕ ФИЛИАЛОВ'])
    ws.merge_cells(start_row=ws.max_row, start_column=1, end_row=ws.max_row, end_column=3)
    ws.cell(row=ws.max_row, column=1).font = font_bold
    ws.cell(row=ws.max_row, column=1).alignment = align_center
    ws.cell(row=ws.max_row, column=1).fill = fill_summary

    # Добавляем мини-шапку для колонок филиалов, как на твоем макете №2
    ws.append(['Филиал:', 'Кол-во полисов', 'Премия с НСП, сом'])
    current_row = ws.max_row
    ws.cell(row=current_row, column=1).font = font_regular
    ws.cell(row=current_row, column=1).alignment = align_left
    ws.cell(row=current_row, column=2).font = font_regular
    ws.cell(row=current_row, column=2).alignment = align_center
    ws.cell(row=current_row, column=3).font = font_regular
    ws.cell(row=current_row, column=3).alignment = align_center

    # ИСПРАВЛЕНО: Сортируем филиалы по возрастанию кодов ('00', '01', '07'...) перед выводом
    sorted_branches = sorted(branch_stats.items(), key=lambda item: item[0])

    for b_code, b_info in sorted_branches:
        # Теперь выводим строго в три раздельные ячейки без лишнего текста
        ws.append([
            f"{b_code} - {b_info['name']}", 
            f"{b_info['count']} шт.", 
            f"{b_info['sum']} сом"
        ])
        
        current_row = ws.max_row
        ws.row_dimensions[current_row].height = 20
        
        # Применяем жирный шрифт и правильное выравнивание
        cell_name = ws.cell(row=current_row, column=1)
        cell_name.font = font_bold
        cell_name.alignment = align_left # название филиала прижмем к левому краю
        
        cell_count = ws.cell(row=current_row, column=2)
        cell_count.font = font_bold
        cell_count.alignment = align_center # количество строго по центру
        
        cell_sum = ws.cell(row=current_row, column=3)
        cell_sum.font = font_bold
        cell_sum.alignment = align_center # сумму строго по центру

    # 6. АВТОПОДБОР ШИРИНЫ КОЛОНОК
    for col in ws.columns:
        max_length = 0
        column_letter = get_column_letter(col[0].column)
        
        for cell in col:
            # Игнорируем длинные строки заголовков и серых плашек, чтобы они не ломали ширину колонок
            if cell.row in [1, start_summary_row, start_summary_row + 4]:
                continue
            try:
                if cell.value:
                    val_len = len(str(cell.value))
                    if val_len > max_length:
                        max_length = val_len
            except:
                pass
        ws.column_dimensions[column_letter].width = min(max_length + 3, 30)

    # 7. Формируем HTTP-ответ
    filename = f"Report_VZR_Buhgalteriya_{d_from}_{d_to}.xlsx"
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    
    return response

@login_required
@user_passes_test(is_superadmin)
def export_excel_savitar(request):
    # 1. Получаем параметры периода из запроса
    d_from_raw = request.GET.get('date_from')
    d_to_raw = request.GET.get('date_to')
    
    try:
        d_from = date.fromisoformat(d_from_raw)
        d_to = date.fromisoformat(d_to_raw)
    except (TypeError, ValueError):
        d_from = d_to = date.today()

    date_from_str = d_from.strftime('%d.%m.%Y')
    date_to_str = d_to.strftime('%d.%m.%Y')

    # 2. Выгружаем полисы с СОРТИРОВКОЙ от старых к новым
    policies = InsurancePolicy.objects.filter(
        issue_date__range=[d_from, d_to]
    ).select_related('agent').prefetch_related('insured_persons').order_by('issue_date', 'id')

    # 3. Создаем Excel книгу
    wb = Workbook()
    ws = wb.active
    ws.title = "Отчет Савитар"

    # Настройки шрифтов и стилей
    font_title = Font(name='Arial', size=14, bold=True, color="1E293B")
    font_bold = Font(name='Arial', size=10, bold=True)
    font_regular = Font(name='Arial', size=10, bold=False)
    align_center = Alignment(horizontal='center', vertical='center', wrap_text=True)

    # --- ГЛАВНЫЙ ЗАГОЛОВОК ---
    ws.append([f"Отчет ВЗР ГСО за период с {date_from_str} по {date_to_str}"])
    ws.row_dimensions[1].height = 35
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=5) # 17 колонок
    ws.cell(row=1, column=1).font = font_title
    ws.cell(row=1, column=1).alignment = align_center

    # --- СТРОКА 2: Отступ ---
    ws.append([])
    ws.row_dimensions[2].height = 15

    # --- СТРОКА 3: Шапка таблицы для Савитар ---
    headers = [
        'Номер полиса', 'Дата оформления', 'Начало действия', 'Окончание действия',
        'Программа страхования', 'Территория страхования', 'Страхователь', 'Застрахованный',
        'Номер паспорта', 'Дата рождения', 'Телефон', 'Страховая сумма, USD/EUR',
        'Страховая сумма, сом', 'Страховая премия, USD/EUR', 'Страховая премия, сом без НСП',
        'Кто оформил',
    ]
    ws.append(headers)
    
    ws.row_dimensions[3].height = 28
    for cell in ws[3]:
        cell.font = font_bold
        cell.alignment = align_center

    # 4. Наполняем данными в разрезе застрахованных лиц
    for p in policies:
        for person in p.insured_persons.all():
            currency_label = "EURO" if p.territory == 'SCHENGEN' else "USD"
            
            # Конвертируем премию в валюте (base_premium_currency) безопасности ради
            # Если в твоей модели поле называется иначе, подправь имя аттрибута
            premium_currency = getattr(person, 'premium_currency', 0) or 0
            
            row_data = [
                p.policy_number,
                p.issue_date.strftime('%d.%m.%Y'),
                p.date_from.strftime('%d.%m.%Y'),
                p.date_to.strftime('%d.%m.%Y'),
                p.program,
                p.to_country or "", # Территория страхования (пока пусто, дорабатываешь модельку)
                p.holder_name,
                person.full_name, # Застрахованный
                person.passport_number,
                person.date_of_birth.strftime('%d.%m.%Y') if person.date_of_birth else "",
                p.holder_phone,
                f"{person.sum_insured_currency} {currency_label}",
                person.sum_insured_som,
                f"{premium_currency} {currency_label}",
                person.premium_som, # Чистая премия сом без НСП
                p.agent.get_full_name() or p.agent.username,
                
            ]
            ws.append(row_data)
            
            # Выравниваем всё строго по центру
            current_row = ws.max_row
            ws.row_dimensions[current_row].height = 20
            for cell in ws[current_row]:
                cell.font = font_regular
                cell.alignment = align_center

    # 5. Автоподбор ширины колонок
    for col in ws.columns:
        max_length = 0
        column_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.row == 1:
                continue
            try:
                if cell.value:
                    val_len = len(str(cell.value))
                    if val_len > max_length:
                        max_length = val_len
            except:
                pass
        ws.column_dimensions[column_letter].width = min(max_length + 3, 30)

    # 6. HTTP-ответ
    filename = f"GSO_VZR_Savitar_Report_{d_from}_{d_to}.xlsx"
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    
    return response

@login_required
def export_excel_buh_vt(request):
    # 1. Получаем параметры периода и филиала из запроса
    d_from_raw = request.GET.get('date_from')
    d_to_raw = request.GET.get('date_to')
    branch_id = request.GET.get('branch')
    
    try:
        d_from = date.fromisoformat(d_from_raw)
        d_to = date.fromisoformat(d_to_raw)
    except (TypeError, ValueError):
        d_from = d_to = date.today()

    date_from_str = d_from.strftime('%d.%m.%Y')
    date_to_str = d_to.strftime('%d.%m.%Y')

    # 2. Проверка прав и фильтрация по филиалу
    filters = {'issue_date__range': [d_from, d_to]}
    
    if not request.user.is_superuser:
        profile = getattr(request.user, 'profile', None)
        if profile and profile.branch:
            filters['branch_id'] = profile.branch.id
        else:
            return HttpResponse("Вы не привязаны к филиалу", status=403)
    else:
        if branch_id and str(branch_id).strip():
            filters['branch_id'] = branch_id

    # Выгружаем полисы NOMAD (ВТ)
    policies = NomadPolicy.objects.filter(**filters)\
        .select_related('agent', 'branch')\
        .prefetch_related('insured_persons')\
        .order_by('issue_date', 'id')

    # 3. Создаем книгу Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Отчет ВТ Бухгалтерия"

    font_title = Font(name='Arial', size=14, bold=True, color="1E293B")
    font_bold = Font(name='Arial', size=10, bold=True)
    font_regular = Font(name='Arial', size=10, bold=False)
    align_center = Alignment(horizontal='center', vertical='center', wrap_text=True)
    fill_summary = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    fill_group = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")

    # --- ЗАГОЛОВОК ---
    ws.append([f"Отчет по полисам ВТ за период с {date_from_str} по {date_to_str}"])
    ws.row_dimensions[1].height = 35
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=15)
    ws.cell(row=1, column=1).font = font_title
    ws.cell(row=1, column=1).alignment = align_center

    ws.append([])
    ws.row_dimensions[2].height = 15

    # --- ШАПКА ТАБЛИЦЫ ---
    headers = [
        'Серия', 'Номер полиса', 'Дата оформления', 'Страхователь', 
        'Номер паспорта', 'Гражданство', 'Дата рождения', 'Телефон', 
        'Дата начала', 'Окончание действия', 'Страховая сумма', 
        'Премия без НСП', 'НСП', 'Стр. премия с НСП', 'Кто оформил'
    ]
    ws.append(headers)
    
    ws.row_dimensions[3].height = 28
    for cell in ws[3]:
        cell.font = font_bold
        cell.alignment = align_center

    # 4. Наполнение данными с группировкой
    total_count = 0
    total_gross = Decimal('0.00')

    for p in policies:
        persons = list(p.insured_persons.all())
        count_persons = len(persons)
        total_count += 1

        p_som = Decimal(str(p.total_premium_netto or '0.00'))      
        p_nsp_som = Decimal(str(p.total_premium_gross or '0.00'))  
        nsp_val = Decimal(str(p.total_nsp_amount or '0.00'))       

        if p_nsp_som == Decimal('0.00') and p_som > Decimal('0.00'):
            final_premium_gross = p_som
        else:
            final_premium_gross = p_nsp_som

        total_gross += final_premium_gross

        if count_persons <= 1:
            person = persons[0] if count_persons == 1 else None
            row_data = [
                'VT',                                              
                p.policy_number,                                   
                p.issue_date.strftime('%d.%m.%Y') if p.issue_date else "", 
                p.holder_name,                                     
                person.passport_number if person else "—",                            
                p.citizenship,                                     
                person.date_of_birth.strftime('%d.%m.%Y') if person and person.date_of_birth else "", 
                p.holder_phone,                                    
                p.date_from.strftime('%d.%m.%Y') if p.date_from else "", 
                p.date_to.strftime('%d.%m.%Y') if p.date_to else "",     
                person.sum_insured if person else "—",                                
                p_som,                                             
                nsp_val,                                           
                final_premium_gross,                               
                p.agent.get_full_name() or p.agent.username        
            ]
            ws.append(row_data)
            current_row = ws.max_row
            ws.row_dimensions[current_row].height = 20
            for cell in ws[current_row]:
                cell.font = font_regular
                cell.alignment = align_center
        else:
            ws.append([
                'VT', p.policy_number, 
                p.issue_date.strftime('%d.%m.%Y') if p.issue_date else "", 
                p.holder_name, 
                f"📎 Группа (всего застраховано: {count_persons} чел.)", 
                p.citizenship, "—", p.holder_phone, 
                p.date_from.strftime('%d.%m.%Y') if p.date_from else "", 
                p.date_to.strftime('%d.%m.%Y') if p.date_to else "",     
                persons[0].sum_insured if persons else "—", 
                p_som, nsp_val, final_premium_gross, 
                p.agent.get_full_name() or p.agent.username
            ])
            summary_r = ws.max_row
            ws.row_dimensions[summary_r].height = 22
            for c in ws[summary_r]:
                c.font = font_bold
                c.fill = fill_group
                c.alignment = align_center

            for person in persons:
                ws.append([
                    '', '', '', '',
                    f"   ↳ {person.full_name}", p.citizenship,
                    person.date_of_birth.strftime('%d.%m.%Y') if person.date_of_birth else "",
                    '', '', '', person.sum_insured, '', '', '', ''
                ])
                sub_r = ws.max_row
                ws.row_dimensions[sub_r].outline_level = 1
                ws.row_dimensions[sub_r].hidden = True
                ws.row_dimensions[sub_r].height = 18
                for c in ws[sub_r]:
                    c.font = font_regular
                    c.alignment = align_center

    # --- ИТОГИ ВНИЗУ ---
    ws.append([])
    ws.append(['ОБЩИЕ ИТОГИ ЗА ПЕРИОД'])
    ws.merge_cells(start_row=ws.max_row, start_column=1, end_row=ws.max_row, end_column=3)
    ws.cell(row=ws.max_row, column=1).font = font_bold
    ws.cell(row=ws.max_row, column=1).fill = fill_summary

    ws.append(['Всего оформлено полисов:', f"{total_count} шт."])
    ws.append(['Общая сумма премий с НСП:', f"{total_gross} сом"])

    # 5. Ширина колонок
    for col in ws.columns:
        max_length = 0
        column_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.row == 1:
                continue
            try:
                if cell.value:
                    val_len = len(str(cell.value))
                    if val_len > max_length:
                        max_length = val_len
            except:
                pass
        ws.column_dimensions[column_letter].width = min(max_length + 3, 30)

    # 6. Сохранение через буфер и возврат ответа
    filename = f"VT_Nomad_Accounting_Report_{d_from}_{d_to}.xlsx"
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@login_required
def export_excel_buh_student(request):
    # 1. Получаем параметры периода и филиала из запроса
    d_from_raw = request.GET.get('date_from')
    d_to_raw = request.GET.get('date_to')
    branch_id = request.GET.get('branch')
    
    try:
        d_from = date.fromisoformat(d_from_raw)
        d_to = date.fromisoformat(d_to_raw)
    except (TypeError, ValueError):
        d_from = d_to = date.today()

    date_from_str = d_from.strftime('%d.%m.%Y')
    date_to_str = d_to.strftime('%d.%m.%Y')

    # 2. АРХИТЕКТУРНАЯ ПРОВЕРКА ПРАВ И ФИЛЬТРАЦИЯ ПО ФИЛИАЛУ
    filters = {'issue_date__range': [d_from, d_to]}
    
    if not request.user.is_superuser:
        profile = getattr(request.user, 'profile', None)
        if profile and profile.branch:
            filters['branch_id'] = profile.branch.id
        else:
            return HttpResponse("Вы не привязаны к филиалу", status=403)
    else:
        if branch_id and str(branch_id).strip():
            filters['branch_id'] = branch_id

    # Находим имя связи с застрахованными через метаданные Django, чтобы prefetch не падал
    prefetch_name = None
    for rel in StudentPolicy._meta.related_objects:
        if rel.one_to_many and 'insured' in rel.name.lower():
            prefetch_name = rel.get_accessor_name()
            break
            
    # Если связь определена динамически — подгружаем её, иначе просто забираем полисы
    policies = StudentPolicy.objects.filter(**filters).select_related('agent', 'branch')
    if prefetch_name:
        policies = policies.prefetch_related(prefetch_name)

    # 3. Создаем книгу Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Отчет Дети Бухгалтерия"

    font_title = Font(name='Arial', size=14, bold=True, color="1E293B")
    font_bold = Font(name='Arial', size=10, bold=True)
    font_regular = Font(name='Arial', size=10, bold=False)
    align_center = Alignment(horizontal='center', vertical='center', wrap_text=True)

    # --- ГЛАВНЫЙ ЗАГОЛОВОК ---
    ws.append([f"Отчет по полисам ДЕТИ (Студент) за период с {date_from_str} по {date_to_str}"])
    ws.row_dimensions[1].height = 35
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=15)
    ws.cell(row=1, column=1).font = font_title
    ws.cell(row=1, column=1).alignment = align_center

    ws.append([])
    ws.row_dimensions[2].height = 15

    # --- ШАПКА ТАБЛИЦЫ ---
    headers = [
        'Серия', 'Номер полиса', 'Дата оформления', 'Страхователь', 
        'Застрахованный (Ребенок)', 'Номер паспорта/Свидетельства', 'Дата рождения', 'Телефон', 
        'Дата начала', 'Окончание действия', 'Страховая сумма', 
        'Премия без НСП', 'НСП', 'Стр. премия с НСП', 'Кто оформил'
    ]
    ws.append(headers)
    
    ws.row_dimensions[3].height = 28
    for cell in ws[3]:
        cell.font = font_bold
        cell.alignment = align_center

    # 4. Наполнение данными
    for p in policies:
        # Извлекаем финансовые показатели строго по твоей модели:
        p_som = Decimal(str(p.total_premium_netto or '0.00'))      
        p_nsp_som = Decimal(str(p.total_premium_gross or '0.00'))  
        nsp_val = Decimal(str(p.total_nsp_amount or '0.00'))       

        if p_nsp_som == Decimal('0.00') and p_som > Decimal('0.00'):
            final_premium_gross = p_som
        else:
            final_premium_gross = p_nsp_som

        # Получаем застрахованных детей, если связь найдена
        kids = getattr(p, prefetch_name).all() if prefetch_name else []

        if kids:
            # Если дети есть в связанной таблице — бежим по ним циклом
            for kid in kids:
                kid_name = getattr(kid, 'full_name', getattr(kid, 'name', p.holder_name))
                kid_passport = getattr(kid, 'passport_number', getattr(kid, 'document_number', ""))
                kid_dob_raw = getattr(kid, 'date_of_birth', None)
                kid_dob = kid_dob_raw.strftime('%d.%m.%Y') if kid_dob_raw else ""
                kid_sum = getattr(kid, 'sum_insured', p.total_sum_insured)

                row_data = [
                    'STUDENT',                                         
                    p.policy_number,                                   
                    p.issue_date.strftime('%d.%m.%Y') if p.issue_date else "", 
                    p.holder_name,                                     
                    kid_name,
                    kid_passport,                            
                    kid_dob, 
                    p.holder_phone,                                    
                    p.date_from.strftime('%d.%m.%Y') if p.date_from else "", 
                    p.date_to.strftime('%d.%m.%Y') if p.date_to else "",     
                    kid_sum,                                
                    p_som,                                             
                    nsp_val,                                           
                    final_premium_gross,                               
                    p.agent.get_full_name() or p.agent.username        
                ]
                ws.append(row_data)
        else:
            # Фолбэк: если застрахованных лиц в базе не привязано, выводим одну строку с данными страхователя
            row_data = [
                'STUDENT',                                         
                p.policy_number,                                   
                p.issue_date.strftime('%d.%m.%Y') if p.issue_date else "", 
                p.holder_name,                                     
                p.holder_name, # Ребенок = страхователь
                p.holder_passport or "",                            
                "", 
                p.holder_phone,                                    
                p.date_from.strftime('%d.%m.%Y') if p.date_from else "", 
                p.date_to.strftime('%d.%m.%Y') if p.date_to else "",     
                p.total_sum_insured,                                
                p_som,                                             
                nsp_val,                                           
                final_premium_gross,                               
                p.agent.get_full_name() or p.agent.username        
            ]
            ws.append(row_data)
        
        # Стилизуем добавленные строки
        current_row = ws.max_row
        ws.row_dimensions[current_row].height = 20
        for cell in ws[current_row]:
            cell.font = font_regular
            cell.alignment = align_center

    # 5. Автоподбор ширины колонок под контент
    for col in ws.columns:
        max_length = 0
        column_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.row == 1:
                continue
            try:
                if cell.value:
                    val_len = len(str(cell.value))
                    if val_len > max_length:
                        max_length = val_len
            except:
                pass
        ws.column_dimensions[column_letter].width = min(max_length + 3, 30)

    # 6. Генерируем HTTP-ответ для скачивания файла
    filename = f"Student_Children_Accounting_Report_{d_from}_{d_to}.xlsx"
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    
    return response