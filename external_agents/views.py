# external_agents/views.py
from datetime import date
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.db import transaction
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse,JsonResponse
from django.views.decorators.csrf import csrf_exempt

from insurance.models import Branch, Profile
from .forms import AgentRegistrationForm
from .models import AgentProfile, AgentCommission
from .services import generate_random_password, send_agent_credentials


def is_staff_or_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def get_next_agent_code():
    last_agent = AgentProfile.objects.order_by('-id').first()
    last_id = last_agent.id if last_agent else 0
    return f"AG{(last_id + 1)}"




@login_required
@user_passes_test(is_staff_or_admin)
def agent_application_preview(request):
    """Генерация черновика Заявления на лету (по аналогии с policy_preview)"""
    if request.method == "POST":
        try:
            draft_data = {
                'agent_code': request.POST.get('agent_code', 'AG1'),
                'agent_type': request.POST.get('agent_type', 'IP'),
                'last_name': request.POST.get('last_name', '').strip().upper(),
                'first_name': request.POST.get('first_name', '').strip().upper(),
                'middle_name': request.POST.get('middle_name', '').strip().upper(),
                'company_name': request.POST.get('company_name', '').strip().upper(),
                'inn': request.POST.get('inn', '').strip(),
                'passport_data': request.POST.get('passport_data', '').strip(),
                'phone': request.POST.get('phone', '').strip(),
                'email': request.POST.get('email', '').strip(),
            }
            return render(request, 'external_agents/pdf_application.html', {
                'draft': draft_data,
                'today': date.today()
            })
        except Exception as e:
            return HttpResponse(f"Ошибка подготовки предпросмотра заявления: {str(e)}")

    return redirect('external_agents:register_agent')


@login_required
@user_passes_test(is_staff_or_admin)
def agent_contract_preview(request):
    """Генерация черновика Договора и Приложения №1 на лету (по аналогии с policy_preview)"""
    if request.method == "POST":
        try:
            draft_data = {
                'agent_code': request.POST.get('agent_code', 'AG1'),
                'agent_type': request.POST.get('agent_type', 'IP'),
                'last_name': request.POST.get('last_name', '').strip().upper(),
                'first_name': request.POST.get('first_name', '').strip().upper(),
                'middle_name': request.POST.get('middle_name', '').strip().upper(),
                'company_name': request.POST.get('company_name', '').strip().upper(),
                'inn': request.POST.get('inn', '').strip(),
                'passport_data': request.POST.get('passport_data', '').strip(),
                'power_of_attorney': request.POST.get('power_of_attorney', '').strip(),
                'bank_name': request.POST.get('bank_name', '').strip(),
                'bik': request.POST.get('bik', '').strip(),
                'account_number': request.POST.get('account_number', '').strip(),
                'commission_vzr': request.POST.get('commission_vzr', '20.00'),
                'commission_nomad': request.POST.get('commission_nomad', '20.00'),
                'commission_student': request.POST.get('commission_student', '20.00'),
            }
            return render(request, 'external_agents/pdf_contract.html', {
                'draft': draft_data,
                'today': date.today()
            })
        except Exception as e:
            return HttpResponse(f"Ошибка подготовки предпросмотра договора: {str(e)}")

    return redirect('external_agents:register_agent')

# external_agents/views.py

@login_required
@user_passes_test(is_staff_or_admin)
def register_agent_view(request):
    """Отображает форму и обрабатывает финальное сохранение (Активацию) агента в БД"""
    next_code = get_next_agent_code()

    if request.method == 'POST':
        form = AgentRegistrationForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                with transaction.atomic():
                    raw_password = generate_random_password()
                    email = data['email']
                    agent_code = data.get('agent_code') or next_code

                    # 1. Пользователь Django
                    user = User.objects.create_user(
                        username=email,
                        email=email,
                        password=raw_password,
                        first_name=data['first_name'],
                        last_name=data['last_name'],
                        is_staff=False
                    )

                    # 2. Назначаем группу AGENT
                    agent_group, _ = Group.objects.get_or_create(name='AGENT')
                    user.groups.add(agent_group)

                    company_or_name = data.get('company_name') or f"{user.last_name} {user.first_name}".strip()

                    # 3. Создаем Филиал по коду агента
                    branch, _ = Branch.objects.get_or_create(
                        code=agent_code,
                        defaults={'name': company_or_name}
                    )

                    # 4. Базовый профиль страховой
                    Profile.objects.update_or_create(
                        user=user,
                        defaults={'branch': branch}
                    )

                    # 5. Профиль внешнего агента
                    profile = AgentProfile.objects.create(
                        user=user,
                        agent_code=agent_code,
                        agent_type=data['agent_type'],
                        middle_name=data.get('middle_name'),
                        phone=data['phone'],
                        company_name=data.get('company_name'),
                        inn=data.get('inn'),
                        passport_data=data.get('passport_data'),
                        okpo=data.get('okpo'),
                        power_of_attorney=data.get('power_of_attorney'),
                        bank_name=data.get('bank_name'),
                        bik=data.get('bik'),
                        account_number=data.get('account_number'),
                    )

                    # 6. Фиксация комиссий по 3 продуктам
                    AgentCommission.objects.create(agent=profile, program='vzr', percent=data.get('commission_vzr', 20.00))
                    AgentCommission.objects.create(agent=profile, program='nomad', percent=data.get('commission_nomad', 20.00))
                    AgentCommission.objects.create(agent=profile, program='student', percent=data.get('commission_student', 20.00))

                    # 7. ВМЕСТО EMAIL — ОТДАЕМ КАРТОЧКУ С ДОСТУПАМИ И МИНИ-ГАЙДОМ!
                    return render(request, 'external_agents/activation_success.html', {
                        'agent_user': user,
                        'agent_profile': profile,
                        'raw_password': raw_password,
                        'today': date.today()
                    })

            except Exception as e:
                messages.error(request, f"Ошибка сохранения: {e}")
        else:
            messages.error(request, "Проверьте правильность заполнения полей формы.")

    else:
        form = AgentRegistrationForm(initial={'agent_code': next_code})

    return render(request, 'external_agents/register_agent.html', {
        'form': form,
        'next_code': next_code
    })


@login_required
@user_passes_test(is_staff_or_admin)
def save_printed_memo_view(request):
    
    """Принимает PDF-файл памятки/договора из JavaScript и сохраняет в contract_file"""
    if request.method == 'POST' and request.FILES.get('printed_pdf'):
        agent_code = request.POST.get('agent_code')
        pdf_file = request.FILES['printed_pdf']

        profile = AgentProfile.objects.filter(agent_code=agent_code).first()
        if profile:
            filename = f"Contract_{agent_code}_{profile.company_name or profile.user.last_name}.pdf"
            # Сохраняем полученный PDF прямо в FileField
            profile.contract_file.save(filename, pdf_file, save=True)
            return JsonResponse({'status': 'ok', 'message': 'Файл успешно сохранен в БД'})

    return JsonResponse({'status': 'error', 'message': 'Ошибка сохранения файла'}, status=400)

# external_agents/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.db import transaction

from insurance.models import Branch, Profile
from .models import AgentProfile, AgentCommission
from .forms import StaffUserForm, AgentEditForm
from .services import generate_random_password

def is_staff_or_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)

# 1. ОБЩИЙ РЕЕСТР ПОЛЬЗОВАТЕЛЕЙ (ШТАТ + АГЕНТЫ)
@login_required
@user_passes_test(is_staff_or_admin)
def users_list_view(request):
    tab = request.GET.get('tab', 'staff')
    search_query = request.GET.get('q', '').strip()

    # ИССПРАВЛЕНИЕ: Штатные сотрудники — это все пользователи, у которых НЕТ AgentProfile
    staff_users = User.objects.filter(agent_profile__isnull=True).select_related('profile__branch').prefetch_related('groups')
    
    # Внешние агенты — пользователи, у которых ЕСТЬ AgentProfile
    agents = AgentProfile.objects.select_related('user').prefetch_related('commissions')

    if search_query:
        staff_users = staff_users.filter(
            first_name__icontains=search_query
        ) | staff_users.filter(
            last_name__icontains=search_query
        ) | staff_users.filter(
            email__icontains=search_query
        )

        agents = agents.filter(
            user__first_name__icontains=search_query
        ) | agents.filter(
            user__last_name__icontains=search_query
        ) | agents.filter(
            inn__icontains=search_query
        ) | agents.filter(
            agent_code__icontains=search_query
        )

    return render(request, 'external_agents/users_list.html', {
        'tab': tab,
        'staff_users': staff_users,
        'agents': agents,
        'search_query': search_query
    })
# 2. СОЗДАНИЕ / РЕДАКТИРОВАНИЕ ШТАТНОГО СОТРУДНИКА
# external_agents/views.py

@login_required
@user_passes_test(is_staff_or_admin)
def staff_create_or_edit_view(request, pk=None):
    user_obj = get_object_or_404(User, pk=pk) if pk else None
    user_policies_count = 0
    recent_policies = []

    # Если сотрудник существует, подтягиваем его статистику по полисам
    if user_obj:
        from insurance.models import InsurancePolicy
        user_policies = InsurancePolicy.objects.filter(agent=user_obj)
        user_policies_count = user_policies.count()
        recent_policies = user_policies.order_by('-issue_date')[:5]

    if request.method == 'POST':
        form = StaffUserForm(request.POST, instance=user_obj)
        if form.is_valid():
            with transaction.atomic():
                user = form.save(commit=False)
                raw_password = None
                
                if not pk:
                    raw_password = generate_random_password()
                    user.set_password(raw_password)
                    user.is_staff = True
                    user.username = form.cleaned_data['email']

                user.save()

                # Назначаем группу (Роль)
                role_group = form.cleaned_data['role']
                user.groups.clear()
                user.groups.add(role_group)

                # Назначаем филиал в профиле
                branch = form.cleaned_data.get('branch')
                Profile.objects.update_or_create(user=user, defaults={'branch': branch})

                if raw_password:
                    messages.success(request, f"Сотрудник {user.get_full_name()} успешно создан! Временный пароль: {raw_password}")
                else:
                    messages.success(request, f"Данные сотрудника {user.get_full_name()} успешно обновлены.")
                
                return redirect('external_agents:users_list')
    else:
        initial = {}
        if user_obj:
            initial['role'] = user_obj.groups.first()
            if hasattr(user_obj, 'profile'):
                initial['branch'] = user_obj.profile.branch
        form = StaffUserForm(instance=user_obj, initial=initial)

    return render(request, 'external_agents/staff_form.html', {
        'form': form, 
        'edit_user': user_obj,
        'user_policies_count': user_policies_count,
        'recent_policies': recent_policies,
    })
# 3. РЕДАКТИРОВАНИЕ ВНЕШНЕГО АГЕНТА
@login_required
@user_passes_test(is_staff_or_admin)
def agent_edit_view(request, pk):
    agent_profile = get_object_or_404(AgentProfile, pk=pk)
    user_obj = agent_profile.user

    # Комиссии
    comm_vzr = agent_profile.commissions.filter(program='vzr').first()
    comm_nomad = agent_profile.commissions.filter(program='nomad').first()
    comm_student = agent_profile.commissions.filter(program='student').first()

    # Статистика агента
    from insurance.models import InsurancePolicy
    agent_policies = InsurancePolicy.objects.filter(agent=user_obj)
    policies_count = agent_policies.count()
    recent_policies = agent_policies.order_by('-issue_date')[:5]

    if request.method == 'POST':
        form = AgentEditForm(request.POST, instance=agent_profile)
        if form.is_valid():
            with transaction.atomic():
                profile = form.save()
                
                # Обновляем аккаунт User
                user_obj.first_name = form.cleaned_data['first_name']
                user_obj.last_name = form.cleaned_data['last_name']
                user_obj.email = form.cleaned_data['email']
                user_obj.username = form.cleaned_data['email']
                user_obj.is_active = form.cleaned_data['is_active']
                user_obj.save()

                # Обновляем комиссии
                AgentCommission.objects.update_or_create(
                    agent=profile, program='vzr', 
                    defaults={'percent': form.cleaned_data['commission_vzr']}
                )
                AgentCommission.objects.update_or_create(
                    agent=profile, program='nomad', 
                    defaults={'percent': form.cleaned_data['commission_nomad']}
                )
                AgentCommission.objects.update_or_create(
                    agent=profile, program='student', 
                    defaults={'percent': form.cleaned_data['commission_student']}
                )

                messages.success(request, f"Профиль агента {profile.agent_code} успешно обновлен.")
                return redirect('/agents/users/?tab=agents')
    else:
        initial = {
            'first_name': user_obj.first_name,
            'last_name': user_obj.last_name,
            'email': user_obj.email,
            'commission_vzr': comm_vzr.percent if comm_vzr else 20.0,
            'commission_nomad': comm_nomad.percent if comm_nomad else 20.0,
            'commission_student': comm_student.percent if comm_student else 20.0,
        }
        form = AgentEditForm(instance=agent_profile, initial=initial)

    return render(request, 'external_agents/agent_edit_form.html', {
        'form': form, 
        'agent_profile': agent_profile,
        'policies_count': policies_count,
        'recent_policies': recent_policies,
    })
# 4. БЫСТРАЯ БЛОКИРОВКА / РАЗБЛОКИРОВКА (AJAX или POST)
@login_required
@user_passes_test(is_staff_or_admin)
def toggle_user_active_view(request, user_id):
    target_user = get_object_or_404(User, pk=user_id)
    target_user.is_active = not target_user.is_active
    target_user.save()

    # Синхронизируем статус с AgentProfile, если это агент
    if hasattr(target_user, 'agent_profile'):
        target_user.agent_profile.is_active = target_user.is_active
        target_user.agent_profile.save()

    status_text = "разблокирован" if target_user.is_active else "заблокирован"
    messages.info(request, f"Пользователь {target_user.email} был {status_text}.")
    return redirect(request.META.get('HTTP_REFERER', 'external_agents:users_list'))

# 5. СБРОС ПАРОЛЯ
@login_required
@user_passes_test(is_staff_or_admin)
def reset_user_password_view(request, user_id):
    target_user = get_object_or_404(User, pk=user_id)
    new_password = generate_random_password()
    target_user.set_password(new_password)
    target_user.save()

    messages.warning(request, f"Новый пароль для {target_user.email}: {new_password}")
    return redirect(request.META.get('HTTP_REFERER', 'external_agents:users_list'))

# external_agents/views.py

@login_required
def print_agent_memo(request, pk):
    """Вывод сохраненной в БД Памятки (Приложение №2)"""
    profile = get_object_or_404(AgentProfile, pk=pk)

    # Проверка прав: Админ/штат может смотреть всех, агент — только свою
    if not (request.user.is_staff or request.user.is_superuser):
        if not hasattr(request.user, 'agent_profile') or request.user.agent_profile.id != profile.id:
            return HttpResponse("У вас нет прав для просмотра этого документа.", status=403)

    if profile.activation_memo_html:
        return HttpResponse(profile.activation_memo_html)
    
    return HttpResponse("Для этого агента памятка ещё не сгенерирована.", status=404)