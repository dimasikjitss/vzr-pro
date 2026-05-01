# nomad/views.py
from django.shortcuts import render
from .models import NomadTariff
import json

# nomad/views.py
# def nomad_create(request):
#     # Было 'rate', стало 'percent_rate'
#     tariffs = NomadTariff.objects.filter(program='BRONZE').values('days_min', 'days_max', 'percent_rate')
    
#     context = {
#         'tariffs_json': json.dumps(list(tariffs), default=str),
#     }
#     return render(request, 'nomad_create.html', context)

import json
from decimal import Decimal
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import NomadPolicy, NomadInsuredPerson, NomadTariff

def nomad_create(request):
    # 1. Проверка филиала
    try:
        user_branch = request.user.profile.branch
    except Exception:
        return render(request, 'insurance/error.html', {'message': 'Филиал не настроен в профиле.'})

    # 2. Обработка POST (сохранение)
    if request.method == "POST":
        try:
            start_date = date.fromisoformat(request.POST.get('start_date'))
            end_date = date.fromisoformat(request.POST.get('end_date'))
            days = (end_date - start_date).days + 1
            
            tariff = NomadTariff.objects.filter(
                days_min__lte=days, 
                days_max__gte=days, 
                program='BRONZE'
            ).first()

            if not tariff:
                messages.error(request, f"Тариф не найден для срока {days} дн. Полис не создан.")
            else:
                policy = NomadPolicy.objects.create(
                    agent=request.user,
                    branch=user_branch,
                    # holder_dob=date.fromisoformat(request.POST.get('holder_dob')), # ДОБАВИТЬ ЭТО
                    holder_name=request.POST.get('holder_name', '').strip().upper(),
                    holder_inn=request.POST.get('holder_inn', '').strip(),
                    holder_phone=request.POST.get('holder_phone', '').strip(),
                    holder_address=request.POST.get('holder_address', '').strip(),
                    holder_passport=request.POST.get('holder_passport', '').strip().upper(),
                    citizenship=request.POST.get('citizenship_type', 'Кыргызстан'), # Проверь имя в HTML
                    beneficiary=request.POST.get('holder_relative', '').strip() or "Застрахованный",
                    date_from=start_date,
                    date_to=end_date,
                    program="GSO NOMAD BRONZE",
                    territory="Кыргызская Республика",
                )

                sum_insured = Decimal(request.POST.get('sum_insured', '0'))
                
                dob_raw = request.POST.get('holder_dob')
                dob = date.fromisoformat(dob_raw)
                today = date.today()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

                age_coeff = Decimal('1.0')
                if 0 <= age <= 5:
                    age_coeff = Decimal('2.0')
                elif 6 <= age <= 13:
                    age_coeff = Decimal('1.8')
                
                rate = Decimal(str(tariff.percent_rate))
                netto = (sum_insured * rate / Decimal('100')) * age_coeff

                NomadInsuredPerson.objects.create(
                    policy=policy,
                    full_name=policy.holder_name,
                    date_of_birth=dob, 
                    passport_number=policy.holder_passport,
                    sum_insured=sum_insured,
                    premium_netto=netto
                )

                policy.total_sum_insured = sum_insured
                policy.total_premium_netto = netto
                policy.total_nsp_amount = (netto * Decimal('0.02')).quantize(Decimal('0.01'))
                policy.total_premium_gross = netto + policy.total_nsp_amount
                policy.save()

                messages.success(request, f"Полис {policy.policy_number} успешно оформлен!")
                return redirect('nomad:nomad_success', pk=policy.pk)

        except Exception as e:
            messages.error(request, f"Ошибка при сохранении: {e}")
            print(f"CRITICAL ERROR: {e}")

    # 3. Блок GET (Отрабатывает всегда, если не случился redirect выше)
    # Эти строки ДОЛЖНЫ быть на одном уровне с 'if request.method == "POST":'
    tariffs_qs = NomadTariff.objects.filter(program='BRONZE').values('days_min', 'days_max', 'percent_rate')
    
    return render(request, 'nomad_create.html', {
        'tariffs_list': list(tariffs_qs),
    })

def nomad_success(request, pk):
    # Достаем полис по ID, который пришел из URL
    policy = get_object_or_404(NomadPolicy, pk=pk)
    return render(request, 'nomad_success.html', {'policy': policy})


def nomad_print(request, pk):
    policy = get_object_or_404(NomadPolicy, pk=pk)
    insured = policy.insured_persons.first() # Берем застрахованного
    
    # Рассчитываем возраст для печати
    today = policy.issue_date
    dob = insured.date_of_birth
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    
    age_ratio = "1.0"
    if 0 <= age <= 5:
        age_ratio = "2.0"
    elif 6 <= age <= 13:
        age_ratio = "1.8"
        
    return render(request, 'nomad_policy_pdf.html', {
        'policy': policy,
        'insured': insured,
        'age_ratio': age_ratio, # Передаем в шаблон
    })