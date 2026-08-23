from django.contrib import admin
from .models import DMSTouristTariff, DMSTouristPolicy, DMSTouristInsuredPerson


class DMSTouristInsuredPersonInline(admin.TabularInline):
    model = DMSTouristInsuredPerson
    extra = 0
    readonly_fields = ('age', 'age_coeff', 'duration_coeff', 'purpose_coeff', 'premium_netto', 'nsp', 'premium_gross')


@admin.register(DMSTouristTariff)
class DMSTouristTariffAdmin(admin.ModelAdmin):
    list_display = ('sum_insured', 'days_min', 'days_max', 'duration_coeff', 'base_daily_rate')
    list_filter = ('sum_insured',)
    list_editable = ('duration_coeff', 'base_daily_rate')


@admin.register(DMSTouristPolicy)
class DMSTouristPolicyAdmin(admin.ModelAdmin):
    list_display = ('policy_number', 'holder_name', 'agent', 'branch', 'issue_date', 'total_premium_gross')
    search_fields = ('policy_number', 'holder_name', 'holder_passport', 'holder_inn')
    list_filter = ('branch', 'agent', 'purpose', 'sum_insured', 'issue_date')
    readonly_fields = ('policy_number', 'days_count', 'total_premium_netto', 'total_nsp', 'total_premium_gross', 'issue_date')

    fieldsets = (
        ('Системная информация', {
            'fields': ('policy_number', 'agent', 'branch', 'issue_date')
        }),
        ('Данные страхователя', {
            'fields': ('holder_type', 'holder_id', 'holder_name', 'holder_inn', 'holder_phone', 'holder_address', 'holder_passport', 'relative_contact')
        }),
        ('Параметры страхования', {
            'fields': ('date_from', 'date_to', 'days_count', 'territory', 'sum_insured', 'purpose')
        }),
        ('Экономика', {
            'fields': ('total_premium_netto', 'total_nsp', 'total_premium_gross')
        }),
    )
    inlines = [DMSTouristInsuredPersonInline]