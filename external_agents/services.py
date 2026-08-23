# external_agents/services.py
import secrets
import string
from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import render_to_string


def generate_random_password(length=10):
    """Генерация надежного случайного пароля"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def send_agent_credentials(user, raw_password, contract_file_path=None):
    """
    Отправка Email агенту с доступом и (опционально) договором
    """
    subject = "Ваши доступы к CRM страхования"
    
    # HTML-шаблон письма
    context = {
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'password': raw_password,
        'login_url': 'http://127.0.0.1:8000/admin/login/', # или твой URL авторизации
    }
    
    # Текст письма (можно отрендерить HTML-шаблон)
    html_content = render_to_string('external_agents/emails/agent_welcome.html', context)
    
    email = EmailMessage(
        subject=subject,
        body=html_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    email.content_subtype = "html"

    # Прикрепляем файл договора, если он сгенерирован
    if contract_file_path:
        email.attach_file(contract_file_path)

    email.send(fail_silently=False)