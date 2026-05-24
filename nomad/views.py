# nomad/views.py
import json
from decimal import Decimal
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import NomadPolicy, NomadInsuredPerson, NomadTariff

# def nomad_create(request):
#     # 1. Проверка филиала
#     try:
#         user_branch = request.user.profile.branch
#     except Exception:
#         return render(request, 'insurance/error.html', {'message': 'Филиал не настроен в профиле.'})

#     # 2. Обработка POST (сохранение)
#     if request.method == "POST":
#         try:
#             start_date = date.fromisoformat(request.POST.get('start_date'))
#             end_date = date.fromisoformat(request.POST.get('end_date'))
#             days = (end_date - start_date).days + 1
            
#             tariff = NomadTariff.objects.filter(
#                 days_min__lte=days, 
#                 days_max__gte=days, 
#                 program='BRONZE'
#             ).first()

#             if not tariff:
#                 messages.error(request, f"Тариф не найден для срока {days} дн. Полис не создан.")
#             else:
#                 policy = NomadPolicy.objects.create(
#                     agent=request.user,
#                     branch=user_branch,
#                     # holder_dob=date.fromisoformat(request.POST.get('holder_dob')), # ДОБАВИТЬ ЭТО
#                     holder_name=request.POST.get('holder_name', '').strip().upper(),
#                     holder_inn=request.POST.get('holder_inn', '').strip(),
#                     holder_phone=request.POST.get('holder_phone', '').strip(),
#                     holder_address=request.POST.get('holder_address', '').strip(),
#                     holder_passport=request.POST.get('holder_passport', '').strip().upper(),
#                     citizenship=request.POST.get('citizenship_type', 'Кыргызстан'), # Проверь имя в HTML
#                     beneficiary=request.POST.get('holder_relative', '').strip() or "Застрахованный",
#                     date_from=start_date,
#                     date_to=end_date,
#                     program="GSO NOMAD BRONZE",
#                     territory="Кыргызская Республика",
#                 )

#                 sum_insured = Decimal(request.POST.get('sum_insured', '0'))
                
#                 dob_raw = request.POST.get('holder_dob')
#                 dob = date.fromisoformat(dob_raw)
#                 today = date.today()
#                 age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

#                 age_coeff = Decimal('1.0')
#                 if 0 <= age <= 5:
#                     age_coeff = Decimal('2.0')
#                 elif 6 <= age <= 13:
#                     age_coeff = Decimal('1.8')
                
#                 rate = Decimal(str(tariff.percent_rate))
#                 netto = (sum_insured * rate / Decimal('100')) * age_coeff

#                 NomadInsuredPerson.objects.create(
#                     policy=policy,
#                     full_name=policy.holder_name,
#                     date_of_birth=dob, 
#                     passport_number=policy.holder_passport,
#                     sum_insured=sum_insured,
#                     premium_netto=netto
#                 )

#                 policy.total_sum_insured = sum_insured
#                 policy.total_premium_netto = netto
#                 policy.total_nsp_amount = (netto * Decimal('0.02')).quantize(Decimal('0.01'))
#                 policy.total_premium_gross = netto + policy.total_nsp_amount
#                 policy.save()

#                 messages.success(request, f"Полис {policy.policy_number} успешно оформлен!")
#                 return redirect('nomad:nomad_success', pk=policy.pk)

#         except Exception as e:
#             messages.error(request, f"Ошибка при сохранении: {e}")
#             print(f"CRITICAL ERROR: {e}")

#     # 3. Блок GET (Отрабатывает всегда, если не случился redirect выше)
#     # Эти строки ДОЛЖНЫ быть на одном уровне с 'if request.method == "POST":'
#     tariffs_qs = NomadTariff.objects.filter(program='BRONZE').values('days_min', 'days_max', 'percent_rate')
    
#     return render(request, 'nomad_create.html', {
#         'tariffs_list': list(tariffs_qs),
#     })

def nomad_create(request):
    # 1. ПРОВЕРКА ФИЛИАЛА АГЕНТА
    try:
        user_branch = request.user.profile.branch
    except Exception:
        return render(request, 'insurance/error.html', {'message': 'Филиал не настроен в профиле.'})

    # 2. ОБРАБОТКА И СОХРАНЕНИЕ ФОРМЫ (POST)
    if request.method == "POST":
        try:
            # Парсим даты поездки и считаем дни
            start_date = date.fromisoformat(request.POST.get('start_date'))
            end_date = date.fromisoformat(request.POST.get('end_date'))
            days = (end_date - start_date).days + 1
            
            # Ищем подходящий тариф в базе данных
            tariff = NomadTariff.objects.filter(
                days_min__lte=days, 
                days_max__gte=days, 
                program='BRONZE'
            ).first()

            if not tariff:
                messages.error(request, f"Тариф не найден для срока {days} дн. Полис не создан.")
            else:
                # Получаем и валидируем дату рождения страхователя
                dob_raw = request.POST.get('holder_dob')
                holder_dob = date.fromisoformat(dob_raw) if dob_raw else None
                
                # Чистим текстовые поля от случайных пробелов
                beneficiary_input = request.POST.get('beneficiary', '').strip()
                relative_input = request.POST.get('holder_relative', '').strip()

                # УМНАЯ ЛОГИКА ГРАЖДАНСТВА:
                # Смотрим, что пришло из селекта `citizenship_type` и инпута `citizenship_manual`
                citizenship_type = request.POST.get('citizenship_type', 'Кыргызстан').strip()
                citizenship_manual = request.POST.get('citizenship_manual', '').strip().upper()

                if citizenship_type == 'Другое' and citizenship_manual:
                    final_citizenship = citizenship_manual
                else:
                    final_citizenship = 'Кыргызстан'

                # СОЗДАЕМ ПОЛИС NOMAD
                policy = NomadPolicy.objects.create(
                    agent=request.user,
                    branch=user_branch,
                    
                    # Теперь дата рождения страхователя успешно пишется в базу:
                    holder_birth_date=holder_dob, 
                    
                    holder_name=request.POST.get('holder_name', '').strip().upper(),
                    holder_inn=request.POST.get('holder_inn', '').strip(),
                    holder_phone=request.POST.get('holder_phone', '').strip(),
                    holder_address=request.POST.get('holder_address', '').strip(),
                    holder_passport=request.POST.get('holder_passport', '').strip().upper(),
                    
                    # Записываем вычисленное гражданство (Кыргызстан или ручной ввод страны):
                    citizenship=final_citizenship, 
                    
                    # Разделяем выгодоприобретателя и телефон родственника:
                    beneficiary=beneficiary_input or "Застрахованный",
                    relative_contact=relative_input,
                    
                    date_from=start_date,
                    date_to=end_date,
                    program="GSO NOMAD BRONZE",
                    territory="Кыргызская Республика",
                )

                # СЧИТАЕМ СТОИМОСТЬ И КОЭФФИЦИЕНТЫ
                sum_insured = Decimal(request.POST.get('sum_insured', '0'))
                
                # Расчет возраста для коэффициентов
                if holder_dob:
                    today = date.today()
                    age = today.year - holder_dob.year - ((today.month, today.day) < (holder_dob.month, holder_dob.day))
                else:
                    age = 30  # дефолт, если дата рождения пустая

                age_coeff = Decimal('1.0')
                if 0 <= age <= 5:
                    age_coeff = Decimal('2.0')
                elif 6 <= age <= 13:
                    age_coeff = Decimal('1.8')
                
                rate = Decimal(str(tariff.percent_rate))
                netto = (sum_insured * rate / Decimal('100')) * age_coeff

                # СОЗДАЕМ ЗАСТРАХОВАННОЕ ЛИЦО (Таблица NomadInsuredPerson)
                NomadInsuredPerson.objects.create(
                    policy=policy,
                    full_name=policy.holder_name,
                    date_of_birth=holder_dob, 
                    passport_number=policy.holder_passport,
                    sum_insured=sum_insured,
                    premium_netto=netto
                )

                # ОБНОВЛЯЕМ ИТОГОВЫЕ ФИНАНСОВЫЕ ДАННЫЕ В ПОЛИСЕ
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

    # 3. ОТПРАВКА ДАННЫХ НА СТРАНИЦУ (GET)
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