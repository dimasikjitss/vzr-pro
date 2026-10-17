from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from insurance.models import Branch, PolicyCounter, IndividualHolder, CompanyHolder


class NomadPolicy(models.Model):
    # --- Системные поля ---
    policy_number = models.CharField("Номер полиса", max_length=50, unique=True, blank=True)
    agent = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="Агент")
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, verbose_name="Филиал")
    issue_date = models.DateField("Дата оформления", auto_now_add=True)

    # --- Связь со страхователем через GenericForeignKey (Физ / Юр лицо) ---
    holder_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        limit_choices_to={'model__in': ('individualholder', 'companyholder')},
        null=True, blank=True,
        verbose_name="Тип страхователя"
    )
    holder_id = models.PositiveIntegerField(null=True, blank=True, verbose_name="ID страхователя")
    holder = GenericForeignKey('holder_type', 'holder_id')

    # --- Денормализованные кэш-поля страхователя (Insuree) ---
    holder_name = models.CharField("ФИО / Наименование страхователя", max_length=255, blank=True, null=True)
    holder_birth_date = models.DateField("Дата рождения страхователя", null=True, blank=True)
    holder_phone = models.CharField("Номер телефона", max_length=50, blank=True, null=True)
    holder_address = models.CharField("Адрес проживания / Юр. адрес", max_length=255, blank=True, null=True)
    holder_passport = models.CharField("Паспорт / ID", max_length=50, blank=True, null=True)
    holder_inn = models.CharField("ИНН", max_length=14, blank=True, null=True)
    citizenship = models.CharField("Гражданство", max_length=100, default="Кыргызстан")
    beneficiary = models.CharField(
        "Выгодоприобретатель", max_length=255, blank=True, 
        help_text="Если не указан, считается 'Застрахованный'"
    )
    relative_contact = models.CharField("Контакт родственника / Подписант", max_length=255, blank=True, null=True)

    # --- Условия поездки ---
    date_from = models.DateField("Дата начала")
    date_to = models.DateField("Дата окончания")
    days_count = models.PositiveIntegerField("Кол-во дней", blank=True, null=True)
    
    territory = models.CharField("Территория", max_length=100, default="Кыргызская Республика")
    program = models.CharField("Программа", max_length=100, default="GSO NOMAD BRONZE")

    # --- Финансы (Итоговые значения по всему полису) ---
    total_sum_insured = models.DecimalField("Общая сумма покрытия", max_digits=12, decimal_places=2, default=0)
    total_premium_netto = models.DecimalField("Общая премия (без НСП)", max_digits=12, decimal_places=2, default=0)
    total_nsp_amount = models.DecimalField("Итого НСП (2%)", max_digits=12, decimal_places=2, default=0)
    total_premium_gross = models.DecimalField("ИТОГО К ОПЛАТЕ", max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Полис Nomad"
        verbose_name_plural = "Полисы Nomad"

    def save(self, *args, **kwargs):
        # 1. Автоматическая синхронизация данных страхователя из объекта holder
        if self.holder:
            if isinstance(self.holder, IndividualHolder):
                self.holder_name = self.holder.name
                self.holder_phone = self.holder.phone
                self.holder_inn = self.holder.inn
                self.holder_address = self.holder.address
                self.holder_passport = self.holder.passport
                self.relative_contact = self.holder.relative_contact
            elif isinstance(self.holder, CompanyHolder):
                self.holder_name = self.holder.company_name
                self.holder_phone = self.holder.phone
                self.holder_inn = self.holder.inn
                self.holder_address = self.holder.legal_address
                self.holder_passport = "ЮР. ЛИЦО"
                self.relative_contact = self.holder.signatory_name

        # 2. Генерация уникального номера полиса через счетчик
        if not self.policy_number:
            counter, _ = PolicyCounter.objects.get_or_create(
                branch_code=self.branch.code,
                policy_type='NOMAD'
            )
            counter.current_id += 1
            counter.save()
            self.policy_number = f"VT{self.branch.code}#{counter.current_id:06d}"

        # 3. Расчет количества дней
        if self.date_from and self.date_to:
            d_from = date.fromisoformat(self.date_from) if isinstance(self.date_from, str) else self.date_from
            d_to = date.fromisoformat(self.date_to) if isinstance(self.date_to, str) else self.date_to
            self.days_count = (d_to - d_from).days + 1
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.policy_number} | {self.holder_name or 'Без имени'}"


class NomadInsuredPerson(models.Model):
    policy = models.ForeignKey(NomadPolicy, related_name='insured_persons', on_delete=models.CASCADE)
    full_name = models.CharField("ФИО застрахованного", max_length=255)
    date_of_birth = models.DateField("Дата рождения")
    passport_number = models.CharField("Номер паспорта", max_length=50)
    citizenship = models.CharField("Гражданство", max_length=100, default="Кыргызстан")
    # Расчеты на каждого человека
    sum_insured = models.DecimalField("Сумма покрытия", max_digits=12, decimal_places=2)
    premium_netto = models.DecimalField("Премия (без НСП)", max_digits=10, decimal_places=2)
    nsp_amount = models.DecimalField("НСП (2%)", max_digits=10, decimal_places=2, default=0)
    premium_gross = models.DecimalField("Премия (с НСП)", max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Застрахованное лицо (Nomad)"
        verbose_name_plural = "Застрахованные лица (Nomad)"

    def save(self, *args, **kwargs):
        self.nsp_amount = (self.premium_netto * Decimal('0.02')).quantize(Decimal('0.01'))
        self.premium_gross = self.premium_netto + self.nsp_amount
        super().save(*args, **kwargs)


class NomadTariff(models.Model):
    PROGRAM_CHOICES = [
        ('BRONZE', 'GSO NOMAD BRONZE'),
        ('SILVER', 'GSO NOMAD SILVER'),
        ('GOLD', 'GSO NOMAD GOLD'),
    ]
    program = models.CharField("Программа", max_length=50, choices=PROGRAM_CHOICES)
    days_min = models.IntegerField("Дни от")
    days_max = models.IntegerField("Дни до")
    percent_rate = models.DecimalField("Ставка (%)", max_digits=10, decimal_places=4)

    class Meta:
        verbose_name = "Тариф Nomad"
        verbose_name_plural = "Тарифы Nomad"

    def __str__(self):
        return f"{self.days_min}-{self.days_max} дн. | {self.percent_rate}%"