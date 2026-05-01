from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date

class NomadPolicy(models.Model):
    # --- Системные поля ---
    policy_number = models.CharField("Номер полиса", max_length=50, unique=True, blank=True)
    agent = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="Агент")
    # Ссылаемся на филиалы из основной апки insurance
    branch = models.ForeignKey('insurance.Branch', on_delete=models.PROTECT, verbose_name="Филиал")
    issue_date = models.DateField("Дата оформления", auto_now_add=True)

    # --- Данные страхователя (Insuree) ---
    holder_name = models.CharField("ФИО страхователя", max_length=255)
    holder_birth_date = models.DateField("Дата рождения страхователя", null=True, blank=True) # Добавь это!
    holder_phone = models.CharField("Номер телефона", max_length=50)
    holder_address = models.CharField("Адрес проживания", max_length=255)
    holder_passport = models.CharField("Паспорт / ID", max_length=50)
    holder_inn = models.CharField("ИНН", max_length=14, blank=True, null=True)
    citizenship = models.CharField("Гражданство", max_length=100, default="Кыргызстан")
    beneficiary = models.CharField("Выгодоприобретатель", max_length=255, blank=True, 
                                   help_text="Если не указан, считается 'Застрахованный'")

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
        if not self.policy_number:
            from insurance.models import PolicyCounter 
            
            # Ищем счетчик именно для этого филиала И для типа NOMAD
            counter, _ = PolicyCounter.objects.get_or_create(
                branch_code=self.branch.code,
                policy_type='NOMAD' # <--- Вот здесь магия разделения
            )
            counter.current_id += 1
            counter.save()
            
            self.policy_number = f"VT{self.branch.code}#{counter.current_id:06d}"
        # 2. Расчет дней
        if self.date_from and self.date_to:
            self.days_count = (self.date_to - self.date_from).days + 1
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.policy_number} | {self.holder_name}"


class NomadInsuredPerson(models.Model):
    # СВЯЗЬ С ПОЛИСОМ (Та самая группа людей)
    policy = models.ForeignKey(NomadPolicy, related_name='insured_persons', on_delete=models.CASCADE)
    
    full_name = models.CharField("ФИО застрахованного", max_length=255)
    date_of_birth = models.DateField("Дата рождения")
    passport_number = models.CharField("Номер паспорта", max_length=50)
    
    # Расчеты на каждого человека
    sum_insured = models.DecimalField("Сумма покрытия", max_digits=12, decimal_places=2)
    premium_netto = models.DecimalField("Премия (без НСП)", max_digits=10, decimal_places=2)
    nsp_amount = models.DecimalField("НСП (2%)", max_digits=10, decimal_places=2, default=0)
    premium_gross = models.DecimalField("Премия (с НСП)", max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Застрахованное лицо (Nomad)"
        verbose_name_plural = "Застрахованные лица (Nomad)"

    def save(self, *args, **kwargs):
        # Автоматический расчет НСП для каждого человека
        self.nsp_amount = (self.premium_netto * Decimal('0.02')).quantize(Decimal('0.01'))
        self.premium_gross = self.premium_netto + self.nsp_amount
        super().save(*args, **kwargs)


class NomadTariff(models.Model):
    # Программа (пока только Bronze)
    PROGRAM_CHOICES = [
        ('BRONZE', 'GSO NOMAD BRONZE'),
        ('SILVER', 'GSO NOMAD SILVER'),
        ('GOLD', 'GSO NOMAD GOLD'),
    ]
    program = models.CharField("Программа", max_length=50, choices=PROGRAM_CHOICES)
        
    # Диапазон дней
    days_min = models.IntegerField("Дни от")
    days_max = models.IntegerField("Дни до")
    
    # Процентная ставка (например, 0.46)
    percent_rate = models.DecimalField("Ставка (%)", max_digits=10, decimal_places=4)

    class Meta:
        verbose_name = "Тариф Nomad"
        verbose_name_plural = "Тарифы Nomad"

    def __str__(self):
        return f"{self.days_min}-{self.days_max} дн. | {self.percent_rate}%"