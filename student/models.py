from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

# Импортируем общие справочники из твоего ядра (из приложения ВЗР/insurance)
from insurance.models import Branch, PolicyCounter, IndividualHolder, CompanyHolder


# ================= 1. СПРАВОЧНИКИ ДЛЯ НОВЫХ ТАРИФОВ =================

class InsuranceProgram(models.Model):
    """Справочник программ: ЭРКЕ (3-6), УЧУР (7-17), САПАР (17-25)"""
    code = models.CharField("Код программы", max_length=20, unique=True)
    name = models.CharField("Название программы", max_length=100)
    age_min = models.PositiveSmallIntegerField("Минимальный возраст")
    age_max = models.PositiveSmallIntegerField("Максимальный возраст")

    class Meta:
        verbose_name = "Справочник: Программа учащихся"
        verbose_name_plural = "Справочники: Программы учащихся"

    def __str__(self):
        return self.name


class StudentTariff(models.Model):
    """Тарифная сетка процентных ставок (Таблицы 2, 3, 4, 5)"""
    TIME_CHOICES = [
        ('12H', '12 часов (07:00 - 19:00)'),
        ('24H', '24 часа в сутки'),
    ]
    program = models.ForeignKey(InsuranceProgram, on_delete=models.CASCADE, verbose_name="Программа")
    time_type = models.CharField("Период действия", max_length=10, choices=TIME_CHOICES)
    is_sports = models.BooleanField("Включая спорт", default=False)
    
    # Сюда вбиваем ставки из таблиц (например: 3.50, 2.00, 1.80)
    percent_rate = models.DecimalField("Ставка (%)", max_digits=4, decimal_places=2)

    class Meta:
        verbose_name = "Процентная ставка учащихся"
        verbose_name_plural = "Процентные ставки учащихся"


class StudentDayCoefficient(models.Model):
    """Справочник понижающих коэффициентов на срок менее года (Таблица 6)"""
    days_min = models.PositiveIntegerField("Дней от")
    days_max = models.PositiveIntegerField("Дней до")
    coefficient = models.DecimalField("Коэффициент", max_digits=3, decimal_places=2)

    class Meta:
        verbose_name = "Коэффициент короткого срока"
        verbose_name_plural = "Коэффициенты короткого срока"

    def __str__(self):
        return f"От {self.days_min} до {self.days_max} дней -> {self.coefficient}"


# ================= 2. ПОЛИС СТРАХОВАНИЯ УЧАЩИЕСЯ =================

class StudentPolicy(models.Model):
    TIME_CHOICES = [
        ('12H', '12 часов (07:00 - 19:00)'),
        ('24H', '24 часа в сутки'),
    ]

    policy_number = models.CharField("Номер", max_length=50, unique=True, blank=True)
    agent = models.ForeignKey(User, on_delete=models.PROTECT)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT)
    issue_date = models.DateField(auto_now_add=True)

    # ПОЛНОЕ ПОВТОРЕНИЕ ТВОЕЙ ЛОГИКИ GENERIC foreign key ДЛЯ СТРАХОВАТЕЛЯ
    holder_type = models.ForeignKey(
        ContentType, 
        on_delete=models.PROTECT,
        limit_choices_to={'model__in': ('individualholder', 'companyholder')},
        null=True, blank=True,
        verbose_name="Тип страхователя"
    )
    holder_id = models.PositiveIntegerField(null=True, blank=True, verbose_name="ID страхователя")
    holder = GenericForeignKey('holder_type', 'holder_id')

    # Текстовые кэш-поля страхователя (заполняются автоматически)
    holder_name = models.CharField("ФИО / Название", max_length=255, blank=True, null=True)
    holder_inn = models.CharField("ИНН", max_length=14, blank=True, null=True)
    holder_phone = models.CharField("Телефон", max_length=50, blank=True, null=True)
    holder_address = models.CharField("Адрес", max_length=255, blank=True, null=True)
    holder_passport = models.CharField("Паспорт", max_length=50, blank=True, null=True)

    # Параметры страхования
    program = models.ForeignKey(InsuranceProgram, on_delete=models.PROTECT, verbose_name="Программа")
    time_type = models.CharField("Период действия", max_length=10, choices=TIME_CHOICES, default='24H')
    is_sports_section = models.BooleanField("Включая спорт", default=False)
    
    date_from = models.DateField("Дата начала")
    date_to = models.DateField("Дата окончания")
    days_count = models.PositiveIntegerField("Количество дней", blank=True, null=True)

    # Финансовые агрегаторы по документу
    total_sum_insured = models.DecimalField("Общая страховая сумма", max_digits=12, decimal_places=2, default=0)
    total_premium_netto = models.DecimalField("Премия Нетто (без НСП)", max_digits=10, decimal_places=2, default=0)
    total_nsp_amount = models.DecimalField("НСП (2%)", max_digits=10, decimal_places=2, default=0)
    total_premium_gross = models.DecimalField("Премия Брутто (Итого)", max_digits=10, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        # 1. Автоматическое кэширование данных страхователя (как в твоем ВЗР)
        if self.holder:
            if isinstance(self.holder, IndividualHolder):
                self.holder_name = self.holder.name
                self.holder_phone = self.holder.phone
                self.holder_inn = self.holder.inn
                self.holder_address = self.holder.address
            elif isinstance(self.holder, CompanyHolder):
                self.holder_name = self.holder.company_name
                self.holder_phone = self.holder.phone
                self.holder_inn = self.holder.inn
                self.holder_address = self.holder.legal_address
                self.holder_passport = "ЮР. ЛИЦО"

        # 2. Генерация номера через системный счетчик PolicyCounter
        if not self.policy_number:
            counter, _ = PolicyCounter.objects.get_or_create(branch_code=self.branch.code, policy_type='STUDENT')
            counter.current_id += 1
            counter.save()
            self.policy_number = f"STU{self.branch.code}#{counter.current_id:06d}"
        
        # 3. Подсчет дней
        if self.date_from and self.date_to:
            self.days_count = (self.date_to - self.date_from).days + 1
            
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Полис Учащегося"
        verbose_name_plural = "Полисы Учащихся"


# ================= 3. СПИСОК ЗАСТРАХОВАННЫХ ДЕТЕЙ =================

class StudentInsuredPerson(models.Model):
    """Застрахованное лицо (Ученик) с расчетом сумм на каждого, как в ВЗР"""
    policy = models.ForeignKey(StudentPolicy, related_name='insured_students', on_delete=models.CASCADE)
    full_name = models.CharField("ФИО Ребенка", max_length=255)
    date_of_birth = models.DateField("Дата рождения")
    document_number = models.CharField("Свидетельство / Паспорт", max_length=50)
    
    educational_institution = models.CharField("Учебное заведение", max_length=255)
    grade_or_group = models.CharField("Класс / Группа", max_length=50)

    # Индивидуальный выгодоприобретатель на каждого ребенка
    beneficiary_name = models.CharField("ФИО Выгодоприобретателя (Родителя)", max_length=255)
    beneficiary_relation = models.CharField("Статус представителя (Мать/Отец/Опекун)", max_length=100)

    def __str__(self):
        return self.full_name