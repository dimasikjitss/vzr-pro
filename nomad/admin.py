from django.contrib import admin
from .models import NomadPolicy, NomadInsuredPerson, NomadTariff

class InsuredPersonInline(admin.TabularInline):
    model = NomadInsuredPerson
    extra = 1 # Сколько пустых строк выводить для добавления новых людей
    fields = ('full_name', 'date_of_birth', 'passport_number', 'sum_insured', 'premium_netto', 'premium_gross')
    readonly_fields = ('premium_gross',)

@admin.register(NomadPolicy)
class NomadPolicyAdmin(admin.ModelAdmin):
    list_display = ('policy_number', 'holder_name', 'issue_date', 'total_premium_gross')
    search_fields = ('policy_number', 'holder_name', 'holder_passport')
    list_filter = ('branch', 'issue_date')
    inlines = [InsuredPersonInline] # ТЕ САМЫЕ КАРТОЧКИ ЛЮДЕЙ ВНУТРИ ПОЛИСА


@admin.register(NomadTariff)
class NomadTariffAdmin(admin.ModelAdmin):
    list_display = ('program', 'days_min', 'days_max', 'percent_rate') 
    list_filter = ('program',)