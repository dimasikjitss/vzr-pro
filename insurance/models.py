from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import date

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

# 4. ПОЛИС
class InsurancePolicy(models.Model):
    TERRITORY_CHOICES = [('ASIA', 'Азия, СНГ, Африка, Океания и Австралия'), ('SCHENGEN', 'Шенген и страны Европы'), ('WORLD', 'Северная и Южная Америка, Юго-Восточная Азия, Мальдивы')]

    policy_number = models.CharField("Номер", max_length=50, unique=True, blank=True)
    agent = models.ForeignKey(User, on_delete=models.PROTECT)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT)
    issue_date = models.DateField(auto_now_add=True)
    to_country = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name="Страна назначения (вручную)"
    )

    holder_name = models.CharField("ФИО", max_length=255)
    holder_inn = models.CharField("ИНН", max_length=14, blank=True, null=True)
    holder_phone = models.CharField("Телефон", max_length=50)
    holder_address = models.CharField("Адрес", max_length=255)
    holder_passport = models.CharField("Паспорт", max_length=50)
    relative_contact = models.CharField("Родственник", max_length=255)

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

    # Вспомогательный расчет точного возраста
    def _calculate_age(self, birth_date):
        today = date.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

    def has_child(self):
        return any(self._calculate_age(p.date_of_birth) < 5 for p in self.insured_persons.all())

    def has_adult(self):
        return any(5 <= self._calculate_age(p.date_of_birth) < 65 for p in self.insured_persons.all())

    def has_senior(self):
        return any(self._calculate_age(p.date_of_birth) >= 65 for p in self.insured_persons.all())

    def save(self, *args, **kwargs):
        if not self.policy_number:
            counter, _ = PolicyCounter.objects.get_or_create(branch_code=self.branch.code, policy_type='VZR')
            counter.current_id += 1
            counter.save()
            self.policy_number = f"VZR{self.branch.code}#{counter.current_id:06d}"
        
        if self.date_from and self.date_to:
            self.days_count = (self.date_to - self.date_from).days + 1
        
        self.currency_code = 'EUR' if self.territory == 'SCHENGEN' else 'USD'
        super().save(*args, **kwargs)

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