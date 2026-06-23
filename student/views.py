from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from datetime import date, datetime
from decimal import Decimal

from insurance.models import IndividualHolder, CompanyHolder
from .models import InsuranceProgram, StudentTariff, StudentDayCoefficient, StudentPolicy, StudentInsuredPerson


def _calculate_age(birth_date):
    """Вычисление точного возраста ребенка на текущую дату"""
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def _find_program_by_age(age):
    """Автоматический подбор программы по возрасту из БД"""
    try:
        return InsuranceProgram.objects.get(age_min__lte=age, age_max__gte=age)
    except InsuranceProgram.DoesNotExist:
        return None

@login_required
def student_create(request):
    try:
        user_branch = request.user.profile.branch
    except Exception:
        return render(request, 'insurance/error.html', {'message': 'Филиал не настроен в профиле.'})

    programs = InsuranceProgram.objects.all()

    if request.method == "POST":
        try:
            # 1. ОПРЕДЕЛЯЕМ СТРАХОВАТЕЛЯ (ФИЗ / ЮР)
            holder_kind = request.POST.get('holder_kind', 'individual')
            holder_instance = None

            if holder_kind == 'company':
                holder_instance = CompanyHolder.objects.create(
                    company_name=request.POST.get('company_name', '').strip().upper(),
                    inn=request.POST.get('company_inn', '').strip(),
                    okpo=request.POST.get('company_okpo', '').strip(),
                    legal_address=request.POST.get('holder_address', '').strip().upper(),
                    signatory_name=request.POST.get('company_signatory', '').strip().upper(),
                    phone=request.POST.get('holder_phone', '').strip(),
                )
            else:
                holder_instance = IndividualHolder.objects.create(
                    passport=request.POST.get('holder_passport', '').strip().upper(),
                    name=request.POST.get('holder_name', '').strip().upper(),
                    inn=request.POST.get('holder_inn', '').strip(),
                    phone=request.POST.get('holder_phone', '').strip(),
                    address=request.POST.get('holder_address', '').strip().upper(),
                    relative_contact=request.POST.get('holder_relative', '').strip() or "Не указан",
                )

            # 2. ПОЛУЧАЕМ ДАННЫЕ РЕБЕНКА (ОН ВСЕГДА ОДИН)
            names = request.POST.getlist('student_name[]')
            dobs = request.POST.getlist('student_dob[]')
            documents = request.POST.getlist('student_doc[]')
            schools = request.POST.getlist('student_school[]')
            grades = request.POST.getlist('student_grade[]')
            b_names = request.POST.getlist('beneficiary_name[]')
            b_relations = request.POST.getlist('beneficiary_relation[]')

            student_name_raw = names[0] if names else None
            student_dob_raw = dobs[0] if dobs else None

            if not student_dob_raw or not student_name_raw:
                raise ValueError("Необходимо указать ФИО и дату рождения ребенка.")

            # Вычисляем возраст и АВТОМАТИЧЕСКИ подбираем программу, игнорируя то, что пришло с фронта
            dob_date = date.fromisoformat(student_dob_raw)
            age = _calculate_age(dob_date)

            program_obj = _find_program_by_age(age)
            if not program_obj:
                raise ValueError(f"Возраст ребенка ({age} лет) не подходит ни под одну программу ГСО.")

            time_type = request.POST.get('time_type', '24H')
            is_sports = request.POST.get('is_sports') == 'true'
            sum_insured_val = Decimal(request.POST.get('sum_insured', 0))

            # 3. СОЗДАЕМ ПОЛИС УЧАЩЕГОСЯ
            policy = StudentPolicy.objects.create(
                agent=request.user,
                branch=user_branch,
                holder=holder_instance,
                program=program_obj,
                time_type=time_type,
                is_sports_section=is_sports,
                date_from=date.fromisoformat(request.POST.get('start_date')),
                date_to=date.fromisoformat(request.POST.get('end_date')),
            )

            # Определяем дефолтное имя родителя/организации для выгодоприобретателя
            # Избегаем прямой вызов кэш-методов полиса, берем напрямую из созданного holder_instance
            default_beneficiary_name = getattr(holder_instance, 'company_name', None) or getattr(holder_instance, 'name', 'НЕ УКАЗАНО')

            # 4. СОХРАНЯЕМ ЗАСТРАХОВАННОГО В БД
            with transaction.atomic():
                StudentInsuredPerson.objects.create(
                    policy=policy,
                    full_name=student_name_raw.strip().upper(),
                    date_of_birth=dob_date,
                    document_number=documents[0].strip().upper() if documents else '',
                    educational_institution=schools[0].strip().upper() if schools else '',
                    grade_or_group=grades[0].strip().upper() if grades else '',
                    beneficiary_name=b_names[0].strip().upper() if (b_names and b_names[0].strip()) else default_beneficiary_name,
                    beneficiary_relation=b_relations[0].strip().upper() if (b_relations and b_relations[0].strip()) else "СТРАХОВАТЕЛЬ"
                )

            # --- МАТЕМАТИЧЕСКИЙ РАСЧЕТ И ИТОГИ ---
            tariff = StudentTariff.objects.get(program=program_obj, time_type=time_type, is_sports=is_sports)
            rate = tariff.percent_rate / Decimal('100')

            try:
                day_coeff_obj = StudentDayCoefficient.objects.get(days_min__lte=policy.days_count, days_max__gte=policy.days_count)
                day_coefficient = day_coeff_obj.coefficient
            except StudentDayCoefficient.DoesNotExist:
                day_coefficient = Decimal('1.00')

            total_netto = sum_insured_val * rate * day_coefficient
            
            policy.total_sum_insured = sum_insured_val
            policy.total_premium_netto = total_netto.quantize(Decimal('0.01'))
            policy.total_premium_gross = (total_netto * Decimal('1.02')).quantize(Decimal('0.01'))
            policy.total_nsp_amount = (policy.total_premium_gross - policy.total_premium_netto).quantize(Decimal('0.01'))
            policy.save()

            return redirect('student_success', pk=policy.pk)

        except Exception as e:
            messages.error(request, f"Ошибка сохранения: {e}")

    return render(request, 'student_create.html', {
        'programs': programs,
        'current_branch_code': user_branch.code if user_branch else '??'
    })

@login_required
def student_preview(request):
    """Генерация фейкового объекта полиса для PDF-черновика на основе процентных ставок"""
    if request.method == "POST":
        try:
            d_from = date.fromisoformat(request.POST.get('start_date'))
            d_to = date.fromisoformat(request.POST.get('end_date'))
            calculated_days = (d_to - d_from).days + 1
            
            # --- ИМИТАЦИЯ ТИПА СТРАХОВАТЕЛЯ ДЛЯ ШАБЛОНА БЕЗ ИСКЛЮЧЕНИЙ АТРИБУТОВ ---
            company_name_raw = request.POST.get('company_name', '').strip()
            holder_name_raw = request.POST.get('holder_name', '').strip()
            holder_fake_obj = {}

            if company_name_raw:
                holder_fake_obj = {
                    'company_name': company_name_raw.upper(),
                    'inn': request.POST.get('company_inn', '').strip(),
                    'okpo': request.POST.get('company_okpo', '').strip(),
                    'legal_address': request.POST.get('holder_address', '').strip().upper(),
                    'signatory_name': request.POST.get('company_signatory', '').strip().upper(),
                    'phone': request.POST.get('holder_phone', '').strip(),
                }
            else:
                holder_fake_obj = {
                    'name': holder_name_raw.upper() if holder_name_raw else "НЕ УКАЗАНО",
                    'passport': request.POST.get('holder_passport', '').strip().upper(),
                    'inn': request.POST.get('holder_inn', '').strip(),
                    'address': request.POST.get('holder_address', '').strip().upper(),
                    'phone': request.POST.get('holder_phone', '').strip(),
                }

            program_obj = get_object_or_404(InsuranceProgram, id=request.POST.get('program'))
            is_sports = request.POST.get('is_sports') == 'true'
            time_type = request.POST.get('time_type', '24H')
            sum_insured_val = Decimal(request.POST.get('sum_insured', 0))

            preview_policy = {
                'policy_number': 'ПРОЕКТ / DRAFT',
                'issue_date': date.today(),
                'agent': request.user,
                'holder': holder_fake_obj,
                'holder_name': holder_fake_obj.get('company_name') or holder_fake_obj.get('name'),
                'holder_phone': holder_fake_obj.get('phone'),
                'holder_inn': holder_fake_obj.get('inn'),
                'holder_address': holder_fake_obj.get('legal_address') or holder_fake_obj.get('address'),
                'program': program_obj,
                'time_type': time_type,
                'is_sports_section': is_sports,
                'date_from': d_from,
                'date_to': d_to,
                'days_count': calculated_days,
            }

            # Сбор списков детей с формы
            names = request.POST.getlist('student_name[]')
            dobs = request.POST.getlist('student_dob[]')
            documents = request.POST.getlist('student_doc[]')
            schools = request.POST.getlist('student_school[]')
            grades = request.POST.getlist('student_grade[]')
            b_names = request.POST.getlist('beneficiary_name[]')
            b_relations = request.POST.getlist('beneficiary_relation[]')

            # --- ИСПРАВЛЕННЫЙ РАСЧЕТ ДЛЯ ПРЕДПРОСМОТРА С УЧЕТОМ СТАВКИ ---
            tariff = get_object_or_404(StudentTariff, program=program_obj, time_type=time_type, is_sports=is_sports)
            rate = tariff.percent_rate / Decimal('100')

            try:
                day_coeff_obj = StudentDayCoefficient.objects.get(days_min__lte=calculated_days, days_max__gte=calculated_days)
                day_coefficient = day_coeff_obj.coefficient
            except StudentDayCoefficient.DoesNotExist:
                day_coefficient = Decimal('1.00')

            insured_students = []
            total_netto = Decimal('0.00')

            for i in range(len(names)):
                if names[i].strip():
                    dob_date = date.fromisoformat(dobs[i])
                    age = _calculate_age(dob_date)
                    
                    p_netto = (sum_insured_val * rate * day_coefficient).quantize(Decimal('0.01'))
                    p_gross = (p_netto * Decimal('1.02')).quantize(Decimal('0.01'))
                    p_nsp = (p_gross - p_netto).quantize(Decimal('0.01'))

                    # Безопасный вытаскивание дефолтного родителя через .get()
                    default_beneficiary = preview_policy['holder_name']

                    insured_students.append({
                        'full_name': names[i].strip().upper(),
                        'date_of_birth': dob_date.strftime('%d.%m.%Y'),
                        'age': age,
                        'document_number': documents[i].strip().upper() if i < len(documents) else '',
                        'educational_institution': schools[i].strip().upper() if i < len(schools) else '',
                        'grade_or_group': grades[i].strip().upper() if i < len(grades) else '',
                        'beneficiary_name': b_names[i].strip().upper() if (i < len(b_names) and b_names[i].strip()) else default_beneficiary,
                        'beneficiary_relation': b_relations[i].strip().upper() if (i < len(b_relations) and b_relations[i].strip()) else "СТРАХОВАТЕЛЬ",
                        'premium_netto': p_netto,
                        'premium_gross': p_gross,
                        'nsp_amount': p_nsp
                    })
                    total_netto += p_netto

            preview_policy['total_sum_insured'] = sum_insured_val * len(insured_students)
            preview_policy['total_premium_netto'] = total_netto
            preview_policy['total_premium_gross'] = (total_netto * Decimal('1.02')).quantize(Decimal('0.01'))
            preview_policy['total_nsp_amount'] = (preview_policy['total_premium_gross'] - total_netto).quantize(Decimal('0.01'))

            return render(request, 'student_policy_pdf.html', {
                'policy': preview_policy,
                'insured_students_preview': insured_students,
                'is_draft': True
            })

        except Exception as e:
            return HttpResponse(f"Ошибка подготовки предпросмотра учащихся: {str(e)}")

    return redirect('home')

@login_required
def student_calculate(request):
    """AJAX-view для мгновенного расчета стоимости на фронтенде"""
    if request.method != "POST":
        return JsonResponse({"error": "Неверный метод запроса"}, status=400)

    # УБРАЛИ program_id из запроса, так как рассчитываем её на лету по дате рождения!
    time_type = request.POST.get("time_type")
    sum_insured = request.POST.get("sum_insured")
    is_sports = request.POST.get("is_sports_section") == "true"
    
    start_date_raw = request.POST.get("start_date")
    end_date_raw = request.POST.get("end_date")
    birth_dates_raw = request.POST.getlist("birth_dates[]")
    birth_date_str = birth_dates_raw[0] if birth_dates_raw else None

    # Проверяем только то, что реально приходит с фронтенда
    if not (time_type and sum_insured and start_date_raw and end_date_raw and birth_date_str):
        return JsonResponse({"error": "Заполните все параметры расчета, сроки и дату рождения ребенка"}, status=400)

    # 1. Расчет дней и коэффициента короткого периода
    try:
        start_date = datetime.strptime(start_date_raw, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_raw, "%Y-%m-%d").date()
        days_count = (end_date - start_date).days + 1
        if days_count <= 0:
            return JsonResponse({"error": "Дата окончания не может быть меньше даты начала"}, status=400)
    except ValueError:
        return JsonResponse({"error": "Неверный формат дат действия полиса"}, status=400)

    try:
        day_coeff_obj = StudentDayCoefficient.objects.get(days_min__lte=days_count, days_max__gte=days_count)
        day_coefficient = day_coeff_obj.coefficient
    except StudentDayCoefficient.DoesNotExist:
        day_coefficient = Decimal('1.00')

    # 2. Вычисляем возраст ребенка
    try:
        b_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
        age = _calculate_age(b_date)
    except ValueError:
        return JsonResponse({"error": "Неверный формат даты рождения ребенка"}, status=400)

    # 3. АВТОПОДБОР ПРОГРАММЫ ПО ВОЗРАСТУ (Вместо get_object_or_404)
    try:
        program = InsuranceProgram.objects.get(age_min__lte=age, age_max__gte=age)
    except InsuranceProgram.DoesNotExist:
        return JsonResponse({"error": f"Возраст ребенка ({age} лет) не подходит ни под одну программу ГСО"}, status=400)

    # 4. Ищем ставку в справочниках
    try:
        tariff = StudentTariff.objects.get(program=program, time_type=time_type, is_sports=is_sports)
        rate = tariff.percent_rate / Decimal("100")
    except StudentTariff.DoesNotExist:
        return JsonResponse({"error": f"Ставка для программы '{program.name}' не настроена в админке"}, status=400)

    # 5. МАТЕМАТИКА
    count_children = max(1, len(birth_dates_raw))
    sum_insured_dec = Decimal(sum_insured)
    
    premium_netto_per_child = sum_insured_dec * rate * day_coefficient
    premium_netto = (premium_netto_per_child * count_children).quantize(Decimal("0.01"))
    premium_gross = (premium_netto * Decimal("1.02")).quantize(Decimal("0.01"))
    nsp_amount = (premium_gross - premium_netto).quantize(Decimal("0.01"))

    # ОБЯЗАТЕЛЬНО возвращаем program_id на фронтенд, чтобы форма закинула её в hidden input!
    return JsonResponse({
        "success": True,
        "program_id": program.id,
        "program_name": program.name,
        "student_age": age,
        "netto": str(premium_netto),
        "nsp": str(nsp_amount),
        "gross": str(premium_gross),
        "days_count": days_count
    })


def student_success(request, pk):
    policy = get_object_or_404(StudentPolicy, pk=pk)
    return render(request, 'student_success.html', {'policy': policy})


@login_required
def print_policy(request, pk):
    """Вывод реального, сохраненного в БД полиса на печать"""
    policy = get_object_or_404(StudentPolicy, pk=pk)
    return render(request, 'student_policy_pdf.html', {
        'policy': policy,
        'is_draft': False
    })