# external_agents/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class AgentProfile(models.Model):
    AGENT_TYPE_CHOICES = [
        # ('INDIVIDUAL', 'Физическое лицо'),
        ('IP', 'ИП (Индивидуальный предприниматель)'),
        ('LLC', 'ОсОО / Юридическое лицо'),
    ]

    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='agent_profile',
        verbose_name="Пользователь"
    )

    # 1. Основное
    agent_type = models.CharField("Тип агента", max_length=20, choices=AGENT_TYPE_CHOICES, default='IP')
    agent_code = models.CharField("Префикс / Код агента", max_length=30, unique=True, editable=False)
    phone = models.CharField("Телефон", max_length=30)
    middle_name = models.CharField("Отчество", max_length=150, blank=True, null=True)

    # 2. Реквизиты ИП / ОсОО
    company_name = models.CharField("Название ИП / ОсОО", max_length=255, blank=True, null=True)
    inn = models.CharField("ИНН", max_length=14, blank=True, null=True)
    passport_data = models.CharField("Паспортные данные", max_length=255, blank=True, null=True)
    okpo = models.CharField("ОКПО (для ОсОО)", max_length=20, blank=True, null=True)
    power_of_attorney = models.CharField("Доверенность (№ и дата, опционально)", max_length=255, blank=True, null=True)

    # 3. Банковские реквизиты
    bank_name = models.CharField("Название банка", max_length=255, blank=True, null=True)
    bik = models.CharField("БИК банка", max_length=20, blank=True, null=True)
    account_number = models.CharField("Расчетный счет", max_length=50, blank=True, null=True)

    # 4. Файл договора и статус
    contract_file = models.FileField("Агентский договор", upload_to='agent_contracts/%Y/%m/', null=True, blank=True)
    is_active = models.BooleanField("Активен", default=True)
    created_at = models.DateTimeField("Дата регистрации", auto_now_add=True)

    class Meta:
        verbose_name = "Профиль агента"
        verbose_name_plural = "Профили агентов"

    def __str__(self):
        return f"{self.agent_code} | {self.company_name or self.user.get_full_name()}"

    def save(self, *args, **kwargs):
        # Авто-генерация кода агента (AGT-0001, AGT-0002...) если он пустой
        if not self.agent_code:
            last_agent = AgentProfile.objects.order_by('-id').first()
            last_id = last_agent.id if last_agent else 0
            self.agent_code = f"AGT-{(last_id + 1):04d}"
        super().save(*args, **kwargs)


class AgentCommission(models.Model):
    PROGRAM_CHOICES = [
        ('vzr', 'ВЗР (Выезд за рубеж)'),
        ('nomad', 'Nomad (Внутренний туризм)'),
        ('student', 'Student (Учащиеся)'),
    ]

    agent = models.ForeignKey(AgentProfile, on_delete=models.CASCADE, related_name='commissions')
    program = models.CharField("Программа", max_length=20, choices=PROGRAM_CHOICES)
    percent = models.DecimalField("Процент комиссии (%)", max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])

    class Meta:
        unique_together = ('agent', 'program')