# external_agents/admin.py
from django.contrib import admin
from .models import AgentProfile, AgentCommission


class AgentCommissionInline(admin.TabularInline):
    """Позволяет редактировать комиссии прямо внутри карточки агента"""
    model = AgentCommission
    extra = 0
    min_num = 1


@admin.register(AgentProfile)
class AgentProfileAdmin(admin.ModelAdmin):
    list_display = ('agent_code', 'get_full_name', 'phone', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('agent_code', 'user__first_name', 'user__last_name', 'user__email', 'phone', 'inn_passport')
    inlines = [AgentCommissionInline]

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    get_full_name.short_description = "ФИО / Логин"


@admin.register(AgentCommission)
class AgentCommissionAdmin(admin.ModelAdmin):
    list_display = ('agent', 'program', 'percent')
    list_filter = ('program',)
    search_fields = ('agent__agent_code', 'agent__user__email')