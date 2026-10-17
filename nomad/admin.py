from django.contrib import admin
from .models import NomadPolicy, NomadInsuredPerson, NomadTariff


class InsuredPersonInline(admin.TabularInline):
    model = NomadInsuredPerson
    extra = 1
    fields = ('full_name', 'citizenship', 'date_of_birth', 'passport_number', 'sum_insured', 'premium_netto', 'nsp_amount', 'premium_gross')
    readonly_fields = ('nsp_amount', 'premium_gross')


@admin.register(NomadPolicy)
class NomadPolicyAdmin(admin.ModelAdmin):
    list_display = ('policy_number', 'holder_name', 'issue_date', 'total_sum_insured', 'total_premium_gross', 'branch', 'agent')
    search_fields = ('policy_number', 'holder_name', 'holder_passport', 'holder_inn')
    list_filter = ('branch', 'issue_date', 'program')
    inlines = [InsuredPersonInline]


@admin.register(NomadTariff)
class NomadTariffAdmin(admin.ModelAdmin):
    list_display = ('program', 'days_min', 'days_max', 'percent_rate')
    list_filter = ('program',)