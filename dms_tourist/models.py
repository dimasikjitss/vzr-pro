from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from insurance.models import Branch, PolicyCounter, IndividualHolder, CompanyHolder


# 1. ТАРИФЫ ДМС ТУРИСТ В БАЗЕ ДАННЫХ
class DMSTouristTariff(models.Model):
    PURPOSE_CHOICES = [
        ('BUSINESS', 'Туризм / Деловая (1.0)'),
        ('TREKKING', 'Трекинг (1.5)'),
        ('SPORT', 'Спорт (2.0)'),
    ]

    sum_insured = models.IntegerField("Страховая сумма (сом)")
    days_min = models.IntegerField("Дни от")
    days_max = models.IntegerField("Дни до")
    duration_coeff = models.DecimalField("Коэфф. длительности", max_digits=4, decimal_places=2, default=1.0)
    base_daily_rate = models.DecimalField("Базовая ставка за день (сом)", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Тариф ДМС Турист'
        verbose_name_plural = 'Тарифы ДМС Турист'
        ordering = ['sum_insured', 'days_min']

    def __str__(self):
        return f"{self.sum_insured} сом ({self.days_min}-{self.days_max} дн.) — {self.base_daily_rate} сом/день"


# 2. ПОЛИС ДМС ТУРИСТ
class DMSTouristPolicy(models.Model):
    PURPOSE_CHOICES = [
        ('BUSINESS', 'Гостевая / Деловая'),
        ('TREKKING', 'Trekking, Hiking / Треккинг'),
        ('SPORT', 'Sport / Спорт'),
        ('STUDENT', 'Студент'),
        ('RESIDENCE', 'ВНЖ'),
        ('REGISTRATION', 'Регистрация'),
    ]

    policy_number = models.CharField("Номер полиса", max_length=50, unique=True, blank=True)
    agent = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="Агент")
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, verbose_name="Филиал")
    issue_date = models.DateField("Дата оформления", auto_now_add=True)

    # Связь со страхователем через GenericForeignKey
    holder_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        limit_choices_to={'model__in': ('individualholder', 'companyholder')},
        null=True, blank=True,
        verbose_name="Тип страхователя"
    )
    holder_id = models.PositiveIntegerField(null=True, blank=True, verbose_name="ID страхователя")
    holder = GenericForeignKey('holder_type', 'holder_id')

    # Денормализованные поля для быстрого поиска и печати
    holder_name = models.CharField("ФИО / Наименование", max_length=255, blank=True, null=True)
    holder_citizenship = models.CharField("Гражданство страхователя", max_length=100, blank=True, null=True) # <-- Новое поле
    holder_inn = models.CharField("ИНН", max_length=14, blank=True, null=True)
    holder_phone = models.CharField("Телефон", max_length=50, blank=True, null=True)
    holder_address = models.CharField("Адрес в КР / Отель", max_length=255, blank=True, null=True)
    holder_passport = models.CharField("Паспорт", max_length=50, blank=True, null=True)
    relative_contact = models.CharField("Родственник / Сопровождающий", max_length=255, blank=True, null=True)

    # Параметры страхования
    date_from = models.DateField("Дата начала")
    date_to = models.DateField("Дата окончания")
    days_count = models.PositiveIntegerField("Дней", blank=True, null=True)
    territory = models.CharField("Территория", max_length=100, default="Кыргызская Республика")
    sum_insured = models.IntegerField("Страховая сумма (сом)", default=100000)
    purpose = models.CharField("Цель поездки", max_length=50, choices=PURPOSE_CHOICES, default='BUSINESS')

    # Финансовые итоги
    total_premium_netto = models.DecimalField("Премия без НСП (сом)", max_digits=12, decimal_places=2, default=0)
    total_nsp = models.DecimalField("НСП 2% (сом)", max_digits=12, decimal_places=2, default=0)
    total_premium_gross = models.DecimalField("Итого премия с НСП (сом)", max_digits=12, decimal_places=2, default=0)

    def _calculate_age(self, birth_date):
        ref_date = self.date_from or date.today()
        return ref_date.year - birth_date.year - ((ref_date.month, ref_date.day) < (birth_date.month, birth_date.day))

    def has_adult(self):
        return any(self._calculate_age(p.birth_date) <= 60 for p in self.insured_persons.all())

    def has_senior(self):
        return any(self._calculate_age(p.birth_date) >= 61 for p in self.insured_persons.all())

    def save(self, *args, **kwargs):
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
                self.holder_passport = ""
                self.relative_contact = self.holder.signatory_name

        if not self.policy_number:
            counter, _ = PolicyCounter.objects.get_or_create(branch_code=self.branch.code, policy_type='DMST')
            counter.current_id += 1
            counter.save()
            self.policy_number = f"DMST{self.branch.code}#{counter.current_id:06d}"

        if self.date_from and self.date_to:
            self.days_count = (self.date_to - self.date_from).days + 1

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Полис ДМС Турист"
        verbose_name_plural = "Полисы ДМС Турист"
        ordering = ['-issue_date', '-id']

    def __str__(self):
        return f"{self.policy_number} — {self.holder_name}"


# 3. ЗАСТРАХОВАННЫЕ ЛИЦА
class DMSTouristInsuredPerson(models.Model):
    policy = models.ForeignKey(DMSTouristPolicy, on_delete=models.CASCADE, related_name='insured_persons')
    full_name = models.CharField("ФИО туриста (латиница)", max_length=255)
    birth_date = models.DateField("Дата рождения")
    citizenship = models.CharField("Гражданство", max_length=100, blank=True, null=True) # <-- Новое поле
    passport_number = models.CharField("Паспорт", max_length=50)

    age = models.PositiveIntegerField("Возраст", default=0)
    age_coeff = models.DecimalField("Коэфф. возраста", max_digits=4, decimal_places=2, default=1.0)
    duration_coeff = models.DecimalField("Коэфф. длительности", max_digits=4, decimal_places=2, default=1.0)
    purpose_coeff = models.DecimalField("Коэфф. цели", max_digits=4, decimal_places=2, default=1.0)

    premium_netto = models.DecimalField("Премия без НСП (сом)", max_digits=10, decimal_places=2, default=0)
    nsp = models.DecimalField("НСП 2% (сом)", max_digits=10, decimal_places=2, default=0)
    premium_gross = models.DecimalField("Премия с НСП (сом)", max_digits=10, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        if self.policy and self.birth_date:
            self.age = self.policy._calculate_age(self.birth_date)
            self.age_coeff = Decimal('1.5') if self.age >= 61 else Decimal('1.0')
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Застрахованный турист"
        verbose_name_plural = "Застрахованные туристы"

    def __str__(self):
        return f"{self.full_name} ({self.passport_number})"