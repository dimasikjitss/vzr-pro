import json
from decimal import Decimal
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse

from insurance.models import IndividualHolder, CompanyHolder
from .models import NomadPolicy, NomadInsuredPerson, NomadTariff


def calculate_nomad_person(sum_insured: Decimal, rate: Decimal, dob: date, ref_date: date):
    """
    Расчет премии для одного туриста:
    Коэффициент возраста:
      - от 0 до 5 лет: 2.0
      - от 6 до 13 лет: 1.8
      - от 14 до 79 лет: 1.0
    Формула:
      netto = (sum_insured * rate / 100) * age_coeff
      nsp = netto * 0.02
      gross = netto + nsp
    """
    if dob and ref_date:
        age = ref_date.year - dob.year - ((ref_date.month, ref_date.day) < (dob.month, dob.day))
    else:
        age = 30

    age_coeff = Decimal('1.0')
    if 0 <= age <= 5:
        age_coeff = Decimal('2.0')
    elif 6 <= age <= 13:
        age_coeff = Decimal('1.8')

    netto = ((sum_insured * rate / Decimal('100')) * age_coeff).quantize(Decimal('0.01'))
    nsp = (netto * Decimal('0.02')).quantize(Decimal('0.01'))
    gross = netto + nsp

    return {
        'age': age,
        'age_coeff': age_coeff,
        'netto': netto,
        'nsp': nsp,
        'gross': gross,
    }


@login_required
def nomad_create(request):
    # 1. Проверка филиала агента
    try:
        user_branch = request.user.profile.branch
    except Exception:
        return render(request, 'insurance/error.html', {'message': 'Филиал не настроен в профиле пользователя.'})

    # 2. Обработка POST-запроса
    if request.method == "POST":
        try:
            with transaction.atomic():
                start_date = date.fromisoformat(request.POST.get('start_date'))
                end_date = date.fromisoformat(request.POST.get('end_date'))
                days = (end_date - start_date).days + 1
                sum_insured = Decimal(request.POST.get('sum_insured', '100000'))

                # Поиск тарифа
                tariff = NomadTariff.objects.filter(
                    days_min__lte=days, 
                    days_max__gte=days, 
                    program='BRONZE'
                ).first()

                if not tariff:
                    messages.error(request, f"Тариф не найден для срока {days} дн. Полис не создан.")
                    return redirect('nomad:create_policy_nomad')

                rate = Decimal(str(tariff.percent_rate))

                # Определение типа страхователя (Физлицо или Юрлицо)
                holder_kind = request.POST.get('holder_kind', 'individual')
                holder_instance = None
                holder_dob = None

                if holder_kind == 'company':
                    # Юрисдикция / Страна компании
                    c_type = request.POST.get('company_citizenship_type', 'Другое').strip()
                    c_manual = request.POST.get('company_citizenship_manual', '').strip().upper()
                    citizenship = c_manual if (c_type == 'Другое' and c_manual) else 'КЫРГЫЗСТАН'

                    # Выгодоприобретатель
                    beneficiary = (request.POST.get('beneficiary_company') or request.POST.get('beneficiary') or '').strip().upper() or "ЗАСТРАХОВАННЫЙ"
                    signatory = request.POST.get('company_signatory', '').strip().upper()
                    relative_contact = signatory

                    holder_instance = CompanyHolder.objects.create(
                        company_name=request.POST.get('company_name', '').strip().upper(),
                        inn=request.POST.get('company_inn', '').strip(),
                        okpo=request.POST.get('company_okpo', '').strip(),
                        legal_address=request.POST.get('company_address', '').strip().upper(),
                        signatory_name=signatory,
                        phone=request.POST.get('company_phone', '').strip(),
                    )
                else:
                    dob_raw = request.POST.get('holder_dob')
                    holder_dob = date.fromisoformat(dob_raw) if dob_raw else None

                    citizenship_type = request.POST.get('citizenship_type', 'Кыргызстан').strip()
                    citizenship_manual = request.POST.get('citizenship_manual', '').strip().upper()
                    citizenship = citizenship_manual if (citizenship_type == 'Другое' and citizenship_manual) else 'КЫРГЫЗСТАН'

                    relative_contact = request.POST.get('holder_relative', '').strip() or "Не указан"
                    beneficiary = request.POST.get('beneficiary', '').strip().upper() or "ЗАСТРАХОВАННЫЙ"

                    holder_instance = IndividualHolder.objects.create(
                        name=request.POST.get('holder_name', '').strip().upper(),
                        inn=request.POST.get('holder_inn', '').strip(),
                        phone=request.POST.get('holder_phone', '').strip(),
                        address=request.POST.get('holder_address', '').strip().upper(),
                        passport=request.POST.get('holder_passport', '').strip().upper(),
                        relative_contact=relative_contact,
                    )

                # Создание полиса
                policy = NomadPolicy.objects.create(
                    agent=request.user,
                    branch=user_branch,
                    holder=holder_instance,
                    holder_birth_date=holder_dob,
                    citizenship=citizenship,
                    beneficiary=beneficiary,
                    relative_contact=relative_contact,
                    date_from=start_date,
                    date_to=end_date,
                    program="GSO NOMAD BRONZE",
                    territory="Кыргызская Республика",
                )

                # Обработка списка застрахованных туристов
                names = request.POST.getlist('insured_name[]') or request.POST.getlist('insured_name')
                dobs = request.POST.getlist('insured_dob[]') or request.POST.getlist('insured_dob')
                passports = request.POST.getlist('insured_passport[]') or request.POST.getlist('insured_passport')
                citizenships = request.POST.getlist('insured_citizenship[]') or request.POST.getlist('insured_citizenship')

                persons_to_create = []
                total_netto = Decimal('0.00')
                total_sum = Decimal('0.00')

                for i in range(len(names)):
                    n_val = names[i].strip().upper()
                    if not n_val:
                        continue

                    p_val = passports[i].strip().upper() if i < len(passports) else ''
                    c_val = citizenships[i].strip().upper() if i < len(citizenships) else citizenship
                    dob_raw = dobs[i].strip() if i < len(dobs) else ''
                    dob_date = None
                    if dob_raw:
                        try:
                            if '-' in dob_raw:
                                dob_date = date.fromisoformat(dob_raw)
                            elif '.' in dob_raw:
                                parts = dob_raw.split('.')
                                dob_date = date(int(parts[2]), int(parts[1]), int(parts[0]))
                        except Exception:
                            dob_date = None

                    calc_res = calculate_nomad_person(sum_insured, rate, dob_date, start_date)

                    persons_to_create.append(NomadInsuredPerson(
                        policy=policy,
                        full_name=n_val,
                        date_of_birth=dob_date or date(1990, 1, 1),
                        passport_number=p_val,
                        citizenship=c_val or 'ИНОСТРАНЕЦ',
                        sum_insured=sum_insured,
                        premium_netto=calc_res['netto'],
                        nsp_amount=calc_res['nsp'],
                        premium_gross=calc_res['gross']
                    ))
                    total_netto += calc_res['netto']
                    total_sum += sum_insured

                if persons_to_create:
                    NomadInsuredPerson.objects.bulk_create(persons_to_create)

                total_nsp = (total_netto * Decimal('0.02')).quantize(Decimal('0.01'))
                total_gross = total_netto + total_nsp

                policy.total_sum_insured = total_sum
                policy.total_premium_netto = total_netto
                policy.total_nsp_amount = total_nsp
                policy.total_premium_gross = total_gross
                policy.save(update_fields=['total_sum_insured', 'total_premium_netto', 'total_nsp_amount', 'total_premium_gross'])

                messages.success(request, f"Полис {policy.policy_number} успешно оформлен!")
                return redirect('nomad:nomad_success', pk=policy.pk)

        except Exception as e:
            messages.error(request, f"Ошибка при сохранении полиса: {e}")

    # 3. GET-запрос
    tariffs_qs = NomadTariff.objects.filter(program='BRONZE').values('days_min', 'days_max', 'percent_rate')
    
    return render(request, 'nomad_create.html', {
        'tariffs_list': list(tariffs_qs),
    })


@login_required
def nomad_preview(request):
    """Предпросмотр черновика полиса Nomad без сохранения в БД"""
    if request.method != "POST":
        return redirect('nomad:create_policy_nomad')

    try:
        user_branch = getattr(getattr(request.user, 'profile', None), 'branch', None)
        start_date = date.fromisoformat(request.POST.get('start_date'))
        end_date = date.fromisoformat(request.POST.get('end_date'))
        days = (end_date - start_date).days + 1
        sum_insured = Decimal(request.POST.get('sum_insured', '100000'))

        tariff = NomadTariff.objects.filter(
            days_min__lte=days, 
            days_max__gte=days, 
            program='BRONZE'
        ).first()

        rate = Decimal(str(tariff.percent_rate)) if tariff else Decimal('0.46')

        holder_kind = request.POST.get('holder_kind', 'individual')
        is_company = (holder_kind == 'company')
        okpo = request.POST.get('company_okpo', '').strip() if is_company else ''

        if is_company:
            c_type = request.POST.get('company_citizenship_type', 'Другое').strip()
            c_manual = request.POST.get('company_citizenship_manual', '').strip().upper()
            citizenship = c_manual if (c_type == 'Другое' and c_manual) else 'КЫРГЫЗСТАН'

            h_name = request.POST.get('company_name', '').strip().upper()
            h_inn = request.POST.get('company_inn', '').strip()
            h_pass = "ЮР. ЛИЦО"
            h_addr = request.POST.get('company_address', '').strip().upper()
            h_phone = request.POST.get('company_phone', '').strip()
            relative_contact = request.POST.get('company_signatory', '').strip().upper()
            beneficiary = (request.POST.get('beneficiary_company') or request.POST.get('beneficiary') or '').strip().upper() or "ЗАСТРАХОВАННЫЙ"
        else:
            h_name = request.POST.get('holder_name', '').strip().upper()
            h_inn = request.POST.get('holder_inn', '').strip()
            h_pass = request.POST.get('holder_passport', '').strip().upper()
            h_addr = request.POST.get('holder_address', '').strip().upper()
            h_phone = request.POST.get('holder_phone', '').strip()
            relative_contact = request.POST.get('holder_relative', '').strip() or "Не указан"
            beneficiary = request.POST.get('beneficiary', '').strip().upper() or "ЗАСТРАХОВАННЫЙ"

            citizenship_type = request.POST.get('citizenship_type', 'Кыргызстан').strip()
            citizenship_manual = request.POST.get('citizenship_manual', '').strip().upper()
            citizenship = citizenship_manual if (citizenship_type == 'Другое' and citizenship_manual) else 'КЫРГЫЗСТАН'

        names = request.POST.getlist('insured_name[]') or request.POST.getlist('insured_name')
        dobs = request.POST.getlist('insured_dob[]') or request.POST.getlist('insured_dob')
        passports = request.POST.getlist('insured_passport[]') or request.POST.getlist('insured_passport')
        citizenships = request.POST.getlist('insured_citizenship[]') or request.POST.getlist('insured_citizenship')

        insured_persons_preview = []
        total_netto = Decimal('0.00')
        total_sum = Decimal('0.00')

        has_infant = False
        has_child = False
        has_adult = False

        for i in range(len(names)):
            n_val = names[i].strip().upper()
            if not n_val:
                continue

            p_val = passports[i].strip().upper() if i < len(passports) else ''
            c_val = citizenships[i].strip().upper() if i < len(citizenships) else citizenship
            dob_raw = dobs[i].strip() if i < len(dobs) else ''
            dob_date = None
            if dob_raw:
                try:
                    if '-' in dob_raw:
                        dob_date = date.fromisoformat(dob_raw)
                    elif '.' in dob_raw:
                        parts = dob_raw.split('.')
                        dob_date = date(int(parts[2]), int(parts[1]), int(parts[0]))
                except Exception:
                    dob_date = None

            calc_res = calculate_nomad_person(sum_insured, rate, dob_date, start_date)

            age = calc_res['age']
            if 0 <= age <= 5:
                has_infant = True
            elif 6 <= age <= 13:
                has_child = True
            else:
                has_adult = True

            insured_persons_preview.append({
                'full_name': n_val,
                'date_of_birth': dob_date,
                'passport_number': p_val,
                'citizenship': c_val or 'ИНОСТРАНЕЦ',
                'sum_insured': sum_insured,
                'premium_netto': calc_res['netto'],
                'nsp_amount': calc_res['nsp'],
                'premium_gross': calc_res['gross'],
            })
            total_netto += calc_res['netto']
            total_sum += sum_insured

        total_nsp = (total_netto * Decimal('0.02')).quantize(Decimal('0.01'))
        total_gross = total_netto + total_nsp

        preview_policy = {
            'policy_number': 'ПРОЕКТ / DRAFT',
            'issue_date': date.today(),
            'agent': request.user,
            'branch': user_branch,
            'holder_name': h_name,
            'holder_phone': h_phone,
            'holder_passport': h_pass,
            'holder_inn': h_inn,
            'holder_address': h_addr,
            'citizenship': citizenship,
            'relative_contact': relative_contact,
            'beneficiary': beneficiary,
            'date_from': start_date,
            'date_to': end_date,
            'days_count': days,
            'program': 'GSO NOMAD BRONZE',
            'territory': 'Кыргызская Республика',
            'total_sum_insured': total_sum,
            'total_premium_netto': total_netto,
            'total_nsp_amount': total_nsp,
            'total_premium_gross': total_gross,
            'is_company': is_company,
            'holder_kind': holder_kind,
            'okpo': okpo,
        }

        return render(request, 'nomad_policy_pdf.html', {
            'policy': preview_policy,
            'insured_persons_preview': insured_persons_preview,
            'is_company': is_company,
            'okpo': okpo,
            'has_infant': has_infant,
            'has_child': has_child,
            'has_adult': has_adult,
            'is_draft': True,
        })

    except Exception as e:
        return HttpResponse(f"Ошибка при формировании черновика: {e}", status=400)

@login_required
def nomad_success(request, pk):
    policy = get_object_or_404(NomadPolicy, pk=pk)
    return render(request, 'nomad_success.html', {'policy': policy})


@login_required
def nomad_print(request, pk):
    policy = get_object_or_404(NomadPolicy, pk=pk)
    
    start_d = policy.date_from or date.today()
    has_infant = False
    has_child = False
    has_adult = False

    for person in policy.insured_persons.all():
        dob = person.date_of_birth
        if dob:
            age = start_d.year - dob.year - ((start_d.month, start_d.day) < (dob.month, dob.day))
        else:
            age = 30
            
        if 0 <= age <= 5:
            has_infant = True
        elif 6 <= age <= 13:
            has_child = True
        else:
            has_adult = True

    return render(request, 'nomad_policy_pdf.html', {
        'policy': policy,
        'has_infant': has_infant,
        'has_child': has_child,
        'has_adult': has_adult,
        'is_draft': False,
    })