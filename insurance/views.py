import requests
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from decimal import Decimal
import json  # <--- Добавьте это
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db.models import Sum, Count
from nomad.models import NomadTariff
from django.core.serializers.json import DjangoJSONEncoder
from openpyxl import Workbook
from openpyxl.utils import get_column_letter # Добавь этот импорт в начало файла

from .models import InsurancePolicy, InsuranceTariff, InsuredPerson, Branch

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
    """Это теперь Главная"""
    rates = get_nbkr_rates()
    # Получаем все тарифы из базы, чтобы JS мог считать на лету
    tariffs_qs = list(InsuranceTariff.objects.all().values('program', 'territory', 'sum_insured', 'days_min', 'days_max', 'rate'))
    tariffs_json = json.dumps(tariffs_qs, default=str) # Это создаст правильную строку для JS
    nomad_tariffs = NomadTariff.objects.filter(program='BRONZE').values('days_min', 'days_max', 'percent_rate')
    # Получаем последние 5 полисов агента для таблицы
    last_policies = InsurancePolicy.objects.filter(agent=request.user).order_by('-issue_date')[:5]
    
    # Считаем сумму за месяц (не забудь импорт Sum в начале файла)
    start_month = date.today().replace(day=1)
    monthly_total = InsurancePolicy.objects.filter(
        agent=request.user, 
        issue_date__gte=start_month
    ).aggregate(Sum('total_premium_som'))['total_premium_som__sum'] or 0

    return render(request, 'insurance/new_home.html', { # Рендерим новый Dashboard
        'usd_rate': rates['USD'], 
        'eur_rate': rates['EUR'],
        'last_policies': last_policies,
        'monthly_total': monthly_total,
        'tariffs_data': tariffs_json,
        'tariffs_nomad_json': json.dumps(list(nomad_tariffs), cls=DjangoJSONEncoder),
    })

    """ Оформление ВЗР """
@login_required
def vzr_create(request):
    rates = get_nbkr_rates()
    try:
        user_branch = request.user.profile.branch
    except Exception:
        return render(request, 'insurance/error.html', {'message': 'Филиал не настроен в профиле.'})

    if request.method == "POST":
        try:
            policy = InsurancePolicy.objects.create(
                agent=request.user,
                branch=user_branch,
                holder_name=request.POST.get('holder_name', '').strip().upper(),
                holder_inn=request.POST.get('holder_inn', '').strip(),
                holder_phone=request.POST.get('holder_phone', '').strip(),
                holder_address=request.POST.get('holder_address', '').strip(),
                holder_passport=request.POST.get('holder_passport', '').strip().upper(),
                relative_contact=request.POST.get('holder_relative', '').strip() or "Не указан",
                date_from=date.fromisoformat(request.POST.get('start_date')),
                date_to=date.fromisoformat(request.POST.get('end_date')),
                territory=request.POST.get('territory'),
                program=request.POST.get('program'),
                activity_type=request.POST.get('activity'),
                exchange_rate=Decimal(request.POST.get('exchange_rate', '1.0').replace(',', '.'))
            )
            
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
            
            preview_policy = {
                'policy_number': 'ПРОЕКТ / DRAFT',
                'issue_date': date.today(),
                'agent': request.user, 
                'holder_name': request.POST.get('holder_name', '').strip().upper(),
                'holder_phone': request.POST.get('holder_phone', '').strip(),
                'holder_passport': request.POST.get('holder_passport', '').strip().upper(),
                'holder_inn': request.POST.get('holder_inn', '').strip(),
                'holder_address': request.POST.get('holder_address', '').strip(),
                'relative_contact': request.POST.get('holder_relative', '').strip() or "Не указан",
                'date_from': d_from,
                'date_to': d_to,
                'days_count': calculated_days,
                'territory': request.POST.get('territory', 'Кыргызстан'),
                'program': request.POST.get('program_select', 'GSO NOMAD BRONZE'),
                'activity_type': request.POST.get('activity', 'Нет'),
                'exchange_rate': exchange_rate,
            }

            # 2. Получаем списки застрахованных
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
                    # Безопасное получение данных по индексу
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
                            # Считаем возраст
                            age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
                            
                            # Применяем вашу логику коэффициентов
                            if 0 <= age <= 5:
                                age_coeff = Decimal('2.0')
                            elif 6 <= age <= 13:
                                age_coeff = Decimal('1.8')
                            else:
                                age_coeff = Decimal('1.0')
                        except ValueError:
                            pass

                    # --- РАСЧЕТЫ СУММ ---
                    p_total_cur = Decimal(str(p_premium_val or 0).replace(',', '.'))
                    p_sum_cur = Decimal(str(p_sum_val or 0).replace(',', '.'))
                    
                    p_total_som = (p_total_cur * exchange_rate).quantize(Decimal('0.01'))
                    p_sum_som = (p_sum_cur * exchange_rate).quantize(Decimal('1.00'))
                    
                    # Итого с учетом НСП
                    p_netto_som = (p_total_som * nsp_factor).quantize(Decimal('0.01'))
                    p_nsp_som = (p_netto_som - p_total_som).quantize(Decimal('0.01'))
                    
                    # Нетто в валюте (если нужно для шаблона)
                    p_netto_cur = (p_total_cur * nsp_factor).quantize(Decimal('0.01'))

                    insured_persons.append({
                        'full_name': names[i].strip().upper(),
                        'passport_number': passports[i].strip().upper() if i < len(passports) else '',
                        'date_of_birth': formatted_dob,
                        'age': age,  # Передаем возраст для условий в HTML
                        'age_coeff': age_coeff, # Передаем коэффициент
                        'sum_insured_currency': p_sum_cur,
                        'sum_insured_som': p_sum_som,
                        'premium_currency': p_total_cur,
                        'premium_som': p_total_som,
                        'premium_netto_cur': p_netto_cur,
                        'premium_netto_som': p_netto_som,
                        'nsp_amount_som': p_nsp_som,
                    })
                    
                    total_cur += p_total_cur
                    total_netto_som += p_netto_som
                    total_nsp_som += p_nsp_som

            # Итоговые значения для всего полиса
            preview_policy['total_premium_currency'] = total_cur
            preview_policy['total_premium_som'] = total_netto_som 
            preview_policy['total_netto_som'] = total_netto_som
            preview_policy['total_nsp_som'] = total_nsp_som

            return render(request, 'insurance/policy_pdf.html', {
                'policy': preview_policy,
                'insured_persons_preview': insured_persons,
                'is_draft': True
            })
            
        except Exception as e:
            # Выводим конкретную ошибку для отладки
            return HttpResponse(f"Ошибка подготовки предпросмотра: {str(e)}")
            
    return redirect('home')
# --- АНАЛИТИКА (АДМИН) ---

@login_required
@user_passes_test(is_superadmin)
def admin_dashboard(request):
    period = request.GET.get('period', 'today')
    branch_id = request.GET.get('branch')
    date_from_raw = request.GET.get('date_from')
    date_to_raw = request.GET.get('date_to')
    today = date.today()

    try:
        if date_from_raw and date_to_raw:
            d_from, d_to = date.fromisoformat(date_from_raw), date.fromisoformat(date_to_raw)
            period = 'custom'
        else:
            periods = {'today': (today, today), 'week': (today - timedelta(days=7), today), 'month': (today - timedelta(days=30), today)}
            d_from, d_to = periods.get(period, (today, today))
    except:
        d_from, d_to = today, today

    policies_qs = InsurancePolicy.objects.filter(issue_date__range=[d_from, d_to]).select_related('agent', 'branch').order_by('-issue_date')
    if branch_id:
        policies_qs = policies_qs.filter(branch_id=branch_id)

    # Инициализация структур данных
    sales_by_day, regions_map, agents_map, total_som = {}, {}, {}, 0
    
    # Новая структура для группировки Программы + Направления
    all_territories = ['ASIA', 'SCHENGEN', 'WORLD']
    all_programs = ['BRONZE', 'SILVER', 'GOLD']
    prog_territory_map = {prog: {terr: 0 for terr in all_territories} for prog in all_programs}

    for p in policies_qs:
        val = float(p.total_premium_som or 0)
        total_som += val
        
        # Динамика
        day = p.issue_date.strftime('%d.%m') if p.issue_date else "??.??"
        sales_by_day[day] = sales_by_day.get(day, 0) + val
        
        # Регионы (для Donut Chart)
        reg = str(p.territory or "Не указано")
        regions_map[reg] = regions_map.get(reg, 0) + val
        
        # Группировка программ по направлениям (для Grouped Bar Chart)
        prog = str(p.program).upper() if p.program else "BRONZE"
        terr = str(p.territory).upper() if p.territory else "ASIA"
        if prog in prog_territory_map and terr in prog_territory_map[prog]:
            prog_territory_map[prog][terr] += val

        # Агенты
        ag_name = f"{p.agent.first_name} {p.agent.last_name}" if p.agent else "Неизвестный"
        if ag_name not in agents_map: agents_map[ag_name] = {'count': 0, 'total': 0}
        agents_map[ag_name]['count'] += 1
        agents_map[ag_name]['total'] += val

    # Формируем series для ApexCharts: [{name: 'ASIA', data: [100, 200, 300]}, ...]
    chart_program_series = []
    for terr in all_territories:
        chart_program_series.append({
            'name': terr,
            'data': [round(prog_territory_map[prog][terr], 2) for prog in all_programs]
        })

    branch_stats = policies_qs.values('branch__name').annotate(total=Sum('total_premium_som'), count=Count('id')).order_by('-total')

    context = {
        'policies': policies_qs,
        'branches': Branch.objects.all(),
        'branch_stats': branch_stats,
        'total_som': total_som,
        'total_count': policies_qs.count(),
        'date_from': d_from.isoformat(),
        'date_to': d_to.isoformat(),
        'current_period': period,
        'selected_branch': branch_id,
        'chart_daily_labels': list(sales_by_day.keys())[::-1],
        'chart_daily_values': list(sales_by_day.values())[::-1],
        'chart_region_labels': list(regions_map.keys()),
        'chart_region_values': list(regions_map.values()),
        # НОВЫЕ ДАННЫЕ ДЛЯ ГРАФИКА ПРОГРАММ
        'chart_program_labels': all_programs,
        'chart_program_series': chart_program_series,
        'agent_performance': [{'name': n, 'count': d['count'], 'avg_check': round(d['total']/d['count'], 0)} for n, d in agents_map.items()]
    }
    return render(request, 'insurance/admin_dashboard.html', context)

# --- ЭКСПОРТ И ДОП ---

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
    ).select_related('agent').prefetch_related('insured_persons').order_by('-issue_date', '-id')

    # 3. Создаем Excel книгу
    wb = Workbook()
    ws = wb.active
    ws.title = "Отчет ВЗР"

    headers = [
        'Серия полиса', '№ полиса', 'Дата оформления полиса', 'Страхователь', 
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
                p.policy_number,
                p.issue_date.strftime('%d.%m.%Y'),
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