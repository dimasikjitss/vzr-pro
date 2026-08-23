from datetime import date, timedelta
from decimal import Decimal
import json

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.db import transaction

from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, Alignment, PatternFill

from insurance.models import Branch, IndividualHolder, CompanyHolder
from .models import DMSTouristPolicy, DMSTouristInsuredPerson, DMSTouristTariff
from django.core.serializers.json import DjangoJSONEncoder


def is_superadmin(user):
    return user.is_superuser


from django.db import transaction

def create_policy(request):
    """Оформление и сохранение полиса ДМС Турист (индивидуальный или групповой)"""
    if request.method == "POST":
        try:
            with transaction.atomic():
                holder_kind = request.POST.get('holder_kind', 'individual')
                s_date_str = request.POST.get('start_date')
                e_date_str = request.POST.get('end_date')
                sum_insured = int(request.POST.get('sum_insured', 100000))
                purpose = request.POST.get('purpose', 'BUSINESS')

                d_from = date.fromisoformat(s_date_str)
                d_to = date.fromisoformat(e_date_str)
                days_count = (d_to - d_from).days + 1

                # Получение базового тарифа из БД
                tariff = DMSTouristTariff.objects.filter(
                    sum_insured=sum_insured,
                    days_min__lte=days_count,
                    days_max__gte=days_count
                ).first()

                base_rate = Decimal(str(tariff.base_daily_rate)) if tariff else Decimal('100.00')
                k_dur = Decimal(str(tariff.duration_coeff)) if tariff else Decimal('1.00')

                k_pur = Decimal('1.00')
                if purpose == 'TREKKING': k_pur = Decimal('1.50')
                elif purpose == 'SPORT': k_pur = Decimal('2.00')

                # Определение данных страхователя
                if holder_kind == 'company':
                    h_name = request.POST.get('company_name', '').strip().upper()
                    h_pass = request.POST.get('company_inn', '').strip()
                    h_phone = request.POST.get('company_phone', '').strip()
                    h_addr = request.POST.get('company_address', '').strip().upper()
                else:
                    h_name = request.POST.get('holder_name', '').strip().upper()
                    h_pass = request.POST.get('holder_passport', '').strip().upper()
                    h_phone = request.POST.get('holder_phone', '').strip()
                    h_addr = request.POST.get('holder_address', '').strip().upper()

                h_relative = request.POST.get('holder_relative', '').strip() or '—'

                # Создаем полис только с теми полями, которые есть в модели
                policy = DMSTouristPolicy.objects.create(
                    agent=request.user,
                    branch=getattr(getattr(request.user, 'profile', None), 'branch', None),
                    holder_name=h_name,
                    holder_passport=h_pass,
                    holder_phone=h_phone,
                    holder_address=h_addr,
                    relative_contact=h_relative,
                    date_from=d_from,
                    date_to=d_to,
                    days_count=days_count,
                    sum_insured=sum_insured,
                    purpose=purpose,
                )

                # Обработка списка застрахованных туристов
                names = request.POST.getlist('insured_name[]')
                dobs = request.POST.getlist('insured_dob[]')
                passports = request.POST.getlist('insured_passport[]')

                total_netto = Decimal('0.00')
                persons_to_create = []

                for i in range(len(names)):
                    n_val = names[i].strip().upper()
                    p_val = passports[i].strip().upper() if i < len(passports) else ''
                    dob_raw = dobs[i].strip() if i < len(dobs) else ''

                    if not n_val:
                        continue

                    dob_date = None
                    age = 30
                    if dob_raw:
                        try:
                            if '-' in dob_raw:
                                dob_date = date.fromisoformat(dob_raw)
                            elif '.' in dob_raw:
                                parts = dob_raw.split('.')
                                dob_date = date(int(parts[2]), int(parts[1]), int(parts[0]))
                            
                            age = d_from.year - dob_date.year - ((d_from.month, d_from.day) < (dob_date.month, dob_date.day))
                        except Exception:
                            dob_date = date(1990, 1, 1)
                            age = 30

                    k_age = Decimal('1.50') if age >= 61 else Decimal('1.00')
                    p_netto = (Decimal(days_count) * base_rate * k_dur * k_age * k_pur).quantize(Decimal('0.01'))
                    p_nsp = (p_netto * Decimal('0.02')).quantize(Decimal('0.01'))
                    p_gross = p_netto + p_nsp

                    total_netto += p_netto

                    persons_to_create.append(DMSTouristInsuredPerson(
                        policy=policy,
                        full_name=n_val,
                        birth_date=dob_date,
                        passport_number=p_val,
                        age=age,
                        age_coeff=k_age,
                        premium_netto=p_netto,
                        nsp=p_nsp,
                        premium_gross=p_gross
                    ))

                # Массовая вставка всех туристов
                if persons_to_create:
                    DMSTouristInsuredPerson.objects.bulk_create(persons_to_create)

                # Пересчет и сохранение итогов полиса
                total_nsp = (total_netto * Decimal('0.02')).quantize(Decimal('0.01'))
                total_gross = total_netto + total_nsp

                policy.total_premium_netto = total_netto
                policy.total_nsp = total_nsp
                policy.total_premium_gross = total_gross
                policy.save(update_fields=['total_premium_netto', 'total_nsp', 'total_premium_gross'])

                return redirect('dms_tourist:print_policy', pk=policy.pk)

        except Exception as e:
            return HttpResponse(f"Ошибка сохранения полиса: {str(e)}", status=400)

    # GET
    tariffs = DMSTouristTariff.objects.all().order_by('sum_insured', 'days_min')
    return render(request, 'dms_tourist/create.html', {
        'tariffs': tariffs,
        'today': date.today().isoformat()
    })


@login_required
def policy_preview(request):
    """Предпросмотр черновика полиса ДМС Турист (до сохранения в БД)"""
    if request.method != "POST":
        return redirect('dms_tourist:create_policy')

    try:
        holder_kind = request.POST.get('holder_kind', 'individual')
        s_date_str = request.POST.get('start_date')
        e_date_str = request.POST.get('end_date')
        sum_insured = int(request.POST.get('sum_insured', 100000))
        purpose = request.POST.get('purpose', 'BUSINESS')

        d_from = date.fromisoformat(s_date_str)
        d_to = date.fromisoformat(e_date_str)
        days_count = (d_to - d_from).days + 1

        # Поиск базового тарифа в БД
        tariff = DMSTouristTariff.objects.filter(
            sum_insured=sum_insured,
            days_min__lte=days_count,
            days_max__gte=days_count
        ).first()

        base_rate = Decimal(str(tariff.base_daily_rate)) if tariff else Decimal('100.00')
        k_dur = Decimal(str(tariff.duration_coeff)) if tariff else Decimal('1.00')

        k_pur = Decimal('1.00')
        if purpose == 'TREKKING': k_pur = Decimal('1.50')
        elif purpose == 'SPORT': k_pur = Decimal('2.00')

        # Списки застрахованных туристов из формы
        names = request.POST.getlist('insured_name[]')
        dobs = request.POST.getlist('insured_dob[]')
        passports = request.POST.getlist('insured_passport[]')

        insured_persons_list = []
        total_netto = Decimal('0.00')
        has_elderly = False

        for i in range(len(names)):
            n_val = names[i].strip().upper()
            p_val = passports[i].strip().upper() if i < len(passports) else ''
            dob_raw = dobs[i].strip() if i < len(dobs) else ''

            if not n_val:
                continue

            dob_date = None
            age = 30
            if dob_raw:
                try:
                    if '-' in dob_raw:
                        dob_date = date.fromisoformat(dob_raw)
                    elif '.' in dob_raw:
                        parts = dob_raw.split('.')
                        dob_date = date(int(parts[2]), int(parts[1]), int(parts[0]))
                    age = d_from.year - dob_date.year - ((d_from.month, d_from.day) < (dob_date.month, dob_date.day))
                except Exception:
                    dob_date = date(1990, 1, 1)
                    age = 30

            if age >= 61:
                has_elderly = True

            k_age = Decimal('1.50') if age >= 61 else Decimal('1.00')
            p_netto = (Decimal(days_count) * base_rate * k_dur * k_age * k_pur).quantize(Decimal('0.01'))
            p_nsp = (p_netto * Decimal('0.02')).quantize(Decimal('0.01'))
            p_gross = p_netto + p_nsp

            total_netto += p_netto

            insured_persons_list.append({
                'full_name': n_val,
                'birth_date': dob_date,
                'age': age,
                'passport_number': p_val,
                'premium_netto': p_netto,
                'nsp': p_nsp,
                'premium_gross': p_gross,
            })

        total_nsp = (total_netto * Decimal('0.02')).quantize(Decimal('0.01'))
        total_gross = total_netto + total_nsp

        preview_policy = {
            'policy_number': 'ПРОЕКТ / DRAFT',
            'issue_date': date.today(),
            'agent': request.user,
            'holder_kind': holder_kind,
            'holder_name': request.POST.get('company_name', '').strip().upper() if holder_kind == 'company' else request.POST.get('holder_name', '').strip().upper(),
            'holder_passport': request.POST.get('company_inn', '').strip() if holder_kind == 'company' else request.POST.get('holder_passport', '').strip().upper(),
            'holder_inn': request.POST.get('company_inn', '').strip() if holder_kind == 'company' else request.POST.get('holder_inn', '').strip(),
            'company_okpo': request.POST.get('company_okpo', '').strip(),
            'company_signatory': request.POST.get('company_signatory', '').strip().upper(),
            'holder_phone': request.POST.get('company_phone', '').strip() if holder_kind == 'company' else request.POST.get('holder_phone', '').strip(),
            'holder_address': request.POST.get('company_address', '').strip().upper() if holder_kind == 'company' else request.POST.get('holder_address', '').strip().upper(),
            'relative_contact': request.POST.get('holder_relative', '').strip() or '—',
            'date_from': d_from,
            'date_to': d_to,
            'days_count': days_count,
            'sum_insured': sum_insured,
            'purpose': purpose,
            'total_premium_netto': total_netto,
            'total_nsp': total_nsp,
            'total_premium_gross': total_gross,
        }

        return render(request, 'dms_tourist/print_policy.html', {
            'policy': preview_policy,
            'persons': insured_persons_list,
            'has_elderly': has_elderly,
            'is_draft': True
        })

    except Exception as e:
        return HttpResponse(f"Ошибка формирования предпросмотра: {str(e)}", status=400)

@login_required
def policy_success(request, pk):
    return render(request, 'dms_tourist/success.html', {'policy': get_object_or_404(DMSTouristPolicy, pk=pk)})


@login_required
def print_policy(request, pk):
    return render(request, 'dms_tourist/print_policy.html', {'policy': get_object_or_404(DMSTouristPolicy, pk=pk)})


# --- 1. ЭКСПОРТ В БУХГАЛТЕРИЮ ---
@login_required
def export_excel_buh_dms(request):
    d_from_raw = request.GET.get('date_from')
    d_to_raw = request.GET.get('date_to')
    branch_id = request.GET.get('branch')

    try:
        d_from = date.fromisoformat(d_from_raw)
        d_to = date.fromisoformat(d_to_raw)
    except (TypeError, ValueError):
        d_from = d_to = date.today()

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

    policies = DMSTouristPolicy.objects.filter(**filters).select_related('agent', 'branch').prefetch_related('insured_persons').order_by('issue_date', 'id')

    wb = Workbook()
    ws = wb.active
    ws.title = "Отчет ДМС Бухгалтерия"

    font_title = Font(name='Arial', size=14, bold=True, color="1E293B")
    font_bold = Font(name='Arial', size=10, bold=True)
    font_regular = Font(name='Arial', size=10, bold=False)
    align_center = Alignment(horizontal='center', vertical='center', wrap_text=True)
    align_left = Alignment(horizontal='left', vertical='center')
    fill_summary = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

    ws.append([f"Отчет по полисам ДМС Турист за период с {d_from.strftime('%d.%m.%Y')} по {d_to.strftime('%d.%m.%Y')}"])
    ws.row_dimensions[1].height = 35
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=4)
    ws.cell(row=1, column=1).font = font_title
    ws.cell(row=1, column=1).alignment = align_center

    ws.append([])
    headers = [
        'Серия', 'Номер полиса', 'Дата оформления', 'Страхователь',
        'Застрахованный турист', 'Номер паспорта', 'Дата рождения', 'Телефон',
        'Дата въезда', 'Дата выезда', 'Страховая сумма, сом',
        'Премия без НСП, сом', 'НСП 2%', 'Стр. премия с НСП, сом', 'Кто оформил'
    ]
    ws.append(headers)
    ws.row_dimensions[3].height = 28
    for cell in ws[3]:
        cell.font = font_bold
        cell.alignment = align_center

    total_count = 0
    total_gross = Decimal('0.00')
    branch_stats = {}

    for p in policies:
        b_code = p.branch.code
        if b_code not in branch_stats:
            branch_stats[b_code] = {'name': p.branch.name, 'count': 0, 'sum': Decimal('0.00')}
        total_count += 1
        branch_stats[b_code]['count'] += 1

        for person in p.insured_persons.all():
            total_gross += person.premium_gross
            branch_stats[b_code]['sum'] += person.premium_gross
            ws.append([
                'DMST',
                p.policy_number,
                p.issue_date.strftime('%d.%m.%Y'),
                p.holder_name,
                person.full_name,
                person.passport_number,
                person.birth_date.strftime('%d.%m.%Y'),
                p.holder_phone,
                p.date_from.strftime('%d.%m.%Y'),
                p.date_to.strftime('%d.%m.%Y'),
                p.sum_insured,
                person.premium_netto,
                person.nsp,
                person.premium_gross,
                p.agent.get_full_name() or p.agent.username
            ])
            cur_r = ws.max_row
            ws.row_dimensions[cur_r].height = 20
            for c in ws[cur_r]:
                c.font = font_regular
                c.alignment = align_center

    ws.append([])
    ws.append(['ОБЩИЕ ИТОГИ ЗА ПЕРИОД'])
    ws.merge_cells(start_row=ws.max_row, start_column=1, end_row=ws.max_row, end_column=3)
    ws.cell(row=ws.max_row, column=1).font = font_bold
    ws.cell(row=ws.max_row, column=1).fill = fill_summary

    ws.append(['Всего оформлено полисов:', f"{total_count} шт."])
    ws.append(['Общая сумма премий с НСП:', f"{total_gross} сом"])

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = min(max_len + 3, 30)

    filename = f"Report_DMS_Buhgalteriya_{d_from}_{d_to}.xlsx"
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response


# --- 2. ЭКСПОРТ ДЛЯ БИШКЕК АССИСТ ---
@login_required
@user_passes_test(is_superadmin)
def export_excel_bishkek_assist(request):
    d_from_raw = request.GET.get('date_from')
    d_to_raw = request.GET.get('date_to')

    try:
        d_from = date.fromisoformat(d_from_raw)
        d_to = date.fromisoformat(d_to_raw)
    except (TypeError, ValueError):
        d_from = d_to = date.today()

    policies = DMSTouristPolicy.objects.filter(issue_date__range=[d_from, d_to]).select_related('agent', 'branch').prefetch_related('insured_persons').order_by('issue_date', 'id')

    wb = Workbook()
    ws = wb.active
    ws.title = "Отчет Бишкек Ассист"

    font_title = Font(name='Arial', size=14, bold=True, color="1E293B")
    font_bold = Font(name='Arial', size=10, bold=True)
    font_regular = Font(name='Arial', size=10, bold=False)
    align_center = Alignment(horizontal='center', vertical='center', wrap_text=True)

    ws.append([f"Реестр полисов «ДМС Турист» для «Бишкек Ассист» за период с {d_from.strftime('%d.%m.%Y')} по {d_to.strftime('%d.%m.%Y')}"])
    ws.row_dimensions[1].height = 35
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=5)
    ws.cell(row=1, column=1).font = font_title
    ws.cell(row=1, column=1).alignment = align_center

    ws.append([])
    headers = [
        'Номер полиса', 'Дата оформления', 'Начало действия', 'Окончание действия',
        'Цель поездки / Риск', 'Страхователь', 'Застрахованный турист',
        'Номер паспорта', 'Дата рождения', 'Возраст', 'Телефон в КР', 'Адрес в КР / Отель',
        'Страховая сумма, сом', 'Премия без НСП, сом', 'Премия с НСП, сом', 'Кто оформил'
    ]
    ws.append(headers)
    ws.row_dimensions[3].height = 28
    for cell in ws[3]:
        cell.font = font_bold
        cell.alignment = align_center

    for p in policies:
        for person in p.insured_persons.all():
            ws.append([
                p.policy_number,
                p.issue_date.strftime('%d.%m.%Y'),
                p.date_from.strftime('%d.%m.%Y'),
                p.date_to.strftime('%d.%m.%Y'),
                p.get_purpose_display(),
                p.holder_name,
                person.full_name,
                person.passport_number,
                person.birth_date.strftime('%d.%m.%Y'),
                person.age,
                p.holder_phone,
                p.holder_address or "—",
                p.sum_insured,
                person.premium_netto,
                person.premium_gross,
                p.agent.get_full_name() or p.agent.username
            ])
            cur_r = ws.max_row
            ws.row_dimensions[cur_r].height = 20
            for c in ws[cur_r]:
                c.font = font_regular
                c.alignment = align_center

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = min(max_len + 3, 30)

    filename = f"GSO_Bishkek_Assist_Report_{d_from}_{d_to}.xlsx"
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response

def get_dms_tariffs_api(request):
    """API отдачи тарифов для JS (как в ВЗР get_tariffs_api)"""
    tariffs = list(DMSTouristTariff.objects.all().values(
        'sum_insured', 'days_min', 'days_max', 'duration_coeff', 'base_daily_rate'
    ))
    return JsonResponse(tariffs, safe=False)