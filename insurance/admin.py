# from django.contrib import admin
# from .models import Branch, Profile, InsuranceTariff, InsurancePolicy, PolicyCounter, InsuredPerson

# # Позволяет редактировать застрахованных лиц прямо внутри карточки полиса
# class InsuredPersonInline(admin.TabularInline):
#     model = InsuredPerson
#     extra = 0
#     # Поля сомов делаем только для чтения, так как они считаются автоматически в модели
#     readonly_fields = ('sum_insured_som', 'premium_som')

# @admin.register(InsurancePolicy)
# class InsurancePolicyAdmin(admin.ModelAdmin):
#     # Поля, которые будут видны в списке всех полисов
#     list_display = ('policy_number', 'holder_name', 'agent', 'branch', 'issue_date', 'total_premium_som')
    
#     # Поля, по которым можно искать
#     search_fields = ('policy_number', 'holder_name', 'holder_passport')
    
#     # Фильтры справа
#     list_filter = ('branch', 'agent', 'issue_date')
    
#     # Поля, которые нельзя редактировать вручную (они считаются автоматически)
#     readonly_fields = ('policy_number', 'days_count', 'total_premium_currency', 'total_premium_som', 'issue_date')
    
#     # Группировка полей в самой карточке для удобства
#     fieldsets = (
#         ('Системная информация', {
#             'fields': ('policy_number', 'agent', 'branch', 'issue_date')
#         }),
#         ('Данные страхователя (кто платит)', {
#             'fields': ('holder_name', 'holder_phone', 'holder_address', 'holder_passport', 'relative_contact')
#         }),
#         ('Параметры страховки', {
#             'fields': ('date_from', 'date_to', 'days_count', 'territory', 'program', 'activity_type')
#         }),
#         ('Экономика', {
#             'fields': ('exchange_rate', 'currency_code', 'total_premium_currency', 'total_premium_som')
#         }),
#     )
    
#     inlines = [InsuredPersonInline]

# @admin.register(Profile)
# class ProfileAdmin(admin.ModelAdmin):
#     list_display = ('user', 'branch')

# @admin.register(InsuranceTariff)
# class InsuranceTariffAdmin(admin.ModelAdmin):
#     list_display = ('program', 'territory', 'sum_insured', 'rate')
#     list_filter = ('program', 'territory')

# admin.site.register(Branch)
# admin.site.register(PolicyCounter)

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Branch, Profile, InsuranceTariff, InsurancePolicy, PolicyCounter, InsuredPerson

# --- 1. ИНТЕГРАЦИЯ ФИЛИАЛА В ПОЛЬЗОВАТЕЛЯ ---

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Настройки филиала'
    fk_name = 'user'

class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_branch', 'is_staff')
    list_select_related = ('profile', 'profile__branch')

    def get_branch(self, instance):
        return instance.profile.branch.name if instance.profile and instance.profile.branch else "-"
    get_branch.short_description = 'Филиал'

# Перерегистрируем стандартный User
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


# --- 2. ОСТАЛЬНЫЕ НАСТРОЙКИ АДМИНКИ ---

class InsuredPersonInline(admin.TabularInline):
    model = InsuredPerson
    extra = 0
    readonly_fields = ('sum_insured_som', 'premium_som')

@admin.register(InsurancePolicy)
class InsurancePolicyAdmin(admin.ModelAdmin):
    list_display = ('policy_number', 'holder_name', 'agent', 'branch', 'issue_date', 'total_premium_som')
    search_fields = ('policy_number', 'holder_name', 'holder_passport')
    list_filter = ('branch', 'agent', 'issue_date')
    readonly_fields = ('policy_number', 'days_count', 'total_premium_currency', 'total_premium_som', 'issue_date')
    
    fieldsets = (
        ('Системная информация', {
            'fields': ('policy_number', 'agent', 'branch', 'issue_date')
        }),
        ('Данные страхователя', {
            'fields': ('holder_name', 'holder_inn', 'holder_phone', 'holder_address', 'holder_passport', 'relative_contact')
        }),
        ('Параметры страховки', {
            'fields': ('date_from', 'date_to', 'days_count', 'territory', 'program', 'activity_type')
        }),
        ('Экономика', {
            'fields': ('exchange_rate', 'currency_code', 'total_premium_currency', 'total_premium_som')
        }),
    )
    inlines = [InsuredPersonInline]

@admin.register(InsuranceTariff)
class InsuranceTariffAdmin(admin.ModelAdmin):
    # Сделали список тарифов более информативным
    list_display = ('program', 'territory', 'sum_insured', 'days_min', 'days_max', 'rate')
    list_filter = ('program', 'territory', 'sum_insured')
    # Позволяет редактировать ставку прямо в списке, не заходя внутрь каждого тарифа
    list_editable = ('rate',)

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')

# Скрываем Profile и PolicyCounter из общего списка, так как они теперь 
# либо внутри User, либо работают автоматически
admin.site.register(PolicyCounter)
# admin.site.register(Profile) # Можно закомментировать, если настроен Inline выше