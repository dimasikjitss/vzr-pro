from django.contrib import admin
from .models import InsuranceProgram, StudentTariff, StudentDayCoefficient, StudentPolicy, StudentInsuredPerson

@admin.register(InsuranceProgram)
class InsuranceProgramAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'age_min', 'age_max')
    search_fields = ('name', 'code')


@admin.register(StudentTariff)
class StudentTariffAdmin(admin.ModelAdmin):
    list_display = ('program', 'time_type', 'is_sports', 'percent_rate')
    list_filter = ('program', 'time_type', 'is_sports')
    list_editable = ('percent_rate',)


@admin.register(StudentDayCoefficient)
class StudentDayCoefficientAdmin(admin.ModelAdmin):
    list_display = ('days_min', 'days_max', 'coefficient')
    list_sort = ('days_min',)
    list_editable = ('coefficient',)


class StudentInsuredPersonInline(admin.TabularInline):
    """
    ВЫГОДОПРИОБРЕТАТЕЛИ ТУТ: Отображение детей и их родителей внутри полиса.
    Выводим все новые поля, которые ты добавил на форму.
    """
    model = StudentInsuredPerson
    extra = 0  # Чтобы не плодить пустые строки, если дети уже забиты
    fields = ('full_name', 'date_of_birth', 'document_number', 'educational_institution', 'grade_or_group', 'beneficiary_name', 'beneficiary_relation')


@admin.register(StudentPolicy)
class StudentPolicyAdmin(admin.ModelAdmin):
    # ПАСПОРТ ТУТ: Добавили отображение ИНН и паспорта страхователя прямо в список
    list_display = ('policy_number', 'holder_name', 'get_holder_passport', 'get_holder_inn', 'program', 'time_type', 'total_premium_gross', 'issue_date')
    list_filter = ('branch', 'program', 'time_type', 'is_sports_section', 'issue_date')
    search_fields = ('policy_number', 'holder_name', 'holder_inn')
    
    # Защищаем системные поля от ручного изменения
    readonly_fields = ('issue_date', 'policy_number', 'total_sum_insured', 'total_premium_netto', 'total_nsp_amount', 'total_premium_gross')
    
    # Включаем отображение списка детей с их выгодоприобретателями
    inlines = [StudentInsuredPersonInline]

    # Кастомные методы для вывода паспорта и ИНН из связанных объектов (как в твоем ВЗР)
    def get_holder_passport(self, obj):
        # Если это физлицо, берем паспорт из кэш-поля или объекта
        if hasattr(obj.holder, 'passport'):
            return obj.holder.passport
        return "ЮР. ЛИЦО"
    get_holder_passport.short_description = "Паспорт страхователя"

    def get_holder_inn(self, obj):
        return obj.holder_inn or "---"
    get_holder_inn.short_description = "ИНН"