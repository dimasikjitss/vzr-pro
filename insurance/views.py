import requests
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db.models import Sum, Count

from openpyxl import Workbook

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

# --- ПРОДАЖИ (АГЕНТ) ---

@login_required
def home(request):
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
            policy.total_premium_som = (total_cur * policy.exchange_rate).quantize(Decimal('0.01'))
            policy.save()
            
            return redirect('policy_success', pk=policy.pk)
        except Exception as e:
            messages.error(request, f"Ошибка сохранения: {e}")

    return render(request, 'insurance/home.html', {
        'usd_rate': rates['USD'], 'eur_rate': rates['EUR'],
        'current_branch_code': user_branch.code if user_branch else '??'
    })

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
    report_type, d_from, d_to = request.GET.get('type'), request.GET.get('date_from'), request.GET.get('date_to')
    policies = InsurancePolicy.objects.filter(issue_date__range=[d_from, d_to])
    wb = Workbook()
    ws = wb.active
    if report_type == 'acc':
        ws.append(['Номер', 'Дата', 'Страхователь', 'Сумма'])
        for p in policies: ws.append([p.policy_number, str(p.issue_date), p.holder_name, p.total_premium_som])
    else:
        ws.append(['Полис', 'Период', 'Застрахованные'])
        for p in policies: ws.append([p.policy_number, f"{p.date_from}-{p.date_to}", "Список..."])
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="report_{report_type}.xlsx"'
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