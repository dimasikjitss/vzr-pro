from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import date
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

# 1. СПРАВОЧНИК ФИЛИАЛОВ
class Branch(models.Model):
    name = models.CharField("Название филиала", max_length=255)
    code = models.CharField("Код филиала", max_length=10, unique=True) 
    qr_code = models.ImageField(upload_to='branch_qrs/', null=True, blank=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

    class Meta:
        verbose_name = "Филиал"
        verbose_name_plural = "Филиалы"

# 2. СИСТЕМНЫЙ СЧЕТЧИК
class PolicyCounter(models.Model):
    branch_code = models.CharField(max_length=10)
    current_id = models.PositiveIntegerField(default=0)
    policy_type = models.CharField(max_length=20)
    
    class Meta:
        verbose_name='Счетчик'
        verbose_name_plural='Счетчик'
        # Теперь уникальность строится по паре "Код филиала + Тип полиса"
        unique_together = ('branch_code', 'policy_type')

# 3. ТАРИФЫ
class InsuranceTariff(models.Model):
    program = models.CharField("Программа", max_length=100)
    territory = models.CharField("Территория", max_length=100)
    sum_insured = models.IntegerField("Страховая сумма")
    days_min = models.IntegerField("Дни от")
    days_max = models.IntegerField("Дни до")
    rate = models.DecimalField("Ставка", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name='Тарифы VZR'
        verbose_name_plural = "Тарифы VZR"


# 1. СТРАХОВАТЕЛЬ - ФИЗИЧЕСКОЕ ЛИЦО
class IndividualHolder(models.Model):
    name = models.CharField("ФИО", max_length=255)
    inn = models.CharField("ИНН", max_length=14, blank=True, null=True)
    phone = models.CharField("Телефон", max_length=50)
    address = models.CharField("Адрес проживания", max_length=255)
    passport = models.CharField("Паспорт", max_length=50)
    relative_contact = models.CharField("Родственник (связь)", max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Физ. лицо: {self.name} (ИНН: {self.inn or 'нет'})"

    class Meta:
        verbose_name = "Страхователь (Физ. лицо)"
        verbose_name_plural = "Страхователи (Физ. лица)"


# 2. СТРАХОВАТЕЛЬ - ЮРИДИЧЕСКОЕ ЛИЦО
class CompanyHolder(models.Model):
    company_name = models.CharField("Наименование компании", max_length=255)
    inn = models.CharField("ИНН", max_length=14)
    okpo = models.CharField("ОКПО", max_length=20)
    legal_address = models.CharField("Юридический адрес", max_length=255)
    signatory_name = models.CharField("ФИО подписанта (директора)", max_length=255)
    phone = models.CharField("Контакт для связи", max_length=50)

    def __str__(self):
        return f"Юр. лицо: {self.company_name} (ИНН: {self.inn})"

    class Meta:
        verbose_name = "Страхователь (Юр. лицо)"
        verbose_name_plural = "Страхователи (Юр. лица)"

# 4. ПОЛИС
class InsurancePolicy(models.Model):
    TERRITORY_CHOICES = [
        ('ASIA', 'Азия, СНГ, Африка, Океания и Австралия'), 
        ('SCHENGEN', 'Шенген и страны Европы'), 
        ('WORLD', 'Северная и Южная Америка, Юго-Восточная Азия, Мальдивы')
    ]

    policy_number = models.CharField("Номер", max_length=50, unique=True, blank=True)
    agent = models.ForeignKey(User, on_delete=models.PROTECT)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT)
    issue_date = models.DateField(auto_now_add=True)
    to_country = models.CharField(max_length=255, blank=True, null=True, verbose_name="Страна назначения (вручную)")

    # 1. ДОБАВИЛИ: Новые универсальные поля связи (Generic Foreign Key)
    holder_type = models.ForeignKey(
        ContentType, 
        on_delete=models.PROTECT,
        limit_choices_to={'model__in': ('individualholder', 'companyholder')},
        null=True, blank=True,
        verbose_name="Тип страхователя"
    )
    holder_id = models.PositiveIntegerField(null=True, blank=True, verbose_name="ID страхователя")
    holder = GenericForeignKey('holder_type', 'holder_id')

    # 2. ИЗМЕНИЛИ: Старым полям страхователя дописываем blank=True, null=True
    # Теперь они не обязательны для заполнения вручную в базе
    holder_name = models.CharField("ФИО", max_length=255, blank=True, null=True)
    holder_inn = models.CharField("ИНН", max_length=14, blank=True, null=True)
    holder_phone = models.CharField("Телефон", max_length=50, blank=True, null=True)
    holder_address = models.CharField("Адрес", max_length=255, blank=True, null=True)
    holder_passport = models.CharField("Паспорт", max_length=50, blank=True, null=True)
    relative_contact = models.CharField("Родственник", max_length=255, blank=True, null=True)

    # Эти поля остаются без изменений
    date_from = models.DateField()
    date_to = models.DateField()
    days_count = models.PositiveIntegerField(blank=True, null=True)
    territory = models.CharField(max_length=20, choices=TERRITORY_CHOICES)
    program = models.CharField(max_length=100)
    activity_type = models.CharField(max_length=100)
    
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4)
    currency_code = models.CharField(max_length=3, default="USD")
    
    total_premium_currency = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_premium_som = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Вспомогательный расчет точного возраста (без изменений)
    def _calculate_age(self, birth_date):
        today = date.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

    def has_child(self):
        return any(self._calculate_age(p.date_of_birth) < 5 for p in self.insured_persons.all())

    def has_adult(self):
        return any(5 <= self._calculate_age(p.date_of_birth) < 65 for p in self.insured_persons.all())

    def has_senior(self):
        return any(self._calculate_age(p.date_of_birth) >= 65 for p in self.insured_persons.all())

    # 3. ИЗМЕНИЛИ: В начало метода save() добавляем автоматическое копирование данных
    def save(self, *args, **kwargs):
        # Если выбран новый объект страхователя, автоматом пишем его данные в текстовые поля
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
                # Для компаний паспорта и родственников нет, зануляем кэш
                self.holder_passport = ""
                self.relative_contact = ""

        # Весь твой старый код логики сохранения ниже остается нетронутым:
        if not self.policy_number:
            counter, _ = PolicyCounter.objects.get_or_create(branch_code=self.branch.code, policy_type='VZR')
            counter.current_id += 1
            counter.save()
            self.policy_number = f"VZR{self.branch.code}#{counter.current_id:06d}"
        
        if self.date_from and self.date_to:
            self.days_count = (self.date_to - self.date_from).days + 1
        
        self.currency_code = 'EUR' if self.territory == 'SCHENGEN' else 'USD'
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Полис VZR"
        verbose_name_plural = "Полисы VZR"

# 5. ЗАСТРАХОВАННЫЕ
class InsuredPerson(models.Model):
    policy = models.ForeignKey(InsurancePolicy, related_name='insured_persons', on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255)
    date_of_birth = models.DateField()
    passport_number = models.CharField(max_length=50)
    
    sum_insured_currency = models.DecimalField(max_digits=10, decimal_places=2)
    sum_insured_som = models.DecimalField(max_digits=10, decimal_places=2, blank=True)
    
    premium_currency = models.DecimalField(max_digits=10, decimal_places=2)
    premium_som = models.DecimalField(max_digits=10, decimal_places=2, blank=True)

    premium_nsp_som = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    nsp_amount_som = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        rate = Decimal(str(self.policy.exchange_rate))
        self.sum_insured_som = (self.sum_insured_currency * rate).quantize(Decimal('1.00'))
        self.premium_som = (self.premium_currency * rate).quantize(Decimal('0.01'))
        
        self.premium_nsp_som = (self.premium_som * Decimal('1.02'))
        self.nsp_amount_som = (self.premium_nsp_som - self.premium_som)
        
        super().save(*args, **kwargs)

# 6. ПРОФИЛЬ
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)