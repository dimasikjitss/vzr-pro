# external_agents/urls.py
from django.urls import path
from . import views

app_name = 'external_agents'

urlpatterns = [
    # Главный список пользователей
    path('users/', views.users_list_view, name='users_list'),
    
    # Штатные сотрудники
    path('staff/create/', views.staff_create_or_edit_view, name='staff_create'),
    path('staff/<int:pk>/edit/', views.staff_create_or_edit_view, name='staff_edit'),

    # Внешние агенты
    path('register/', views.register_agent_view, name='register_agent'),
    path('agent/<int:pk>/edit/', views.agent_edit_view, name='agent_edit'),
    path('agent/<int:pk>/memo/', views.print_agent_memo, name='print_agent_memo'),

    # Действия
    path('users/<int:user_id>/toggle-active/', views.toggle_user_active_view, name='toggle_user_active'),
    path('users/<int:user_id>/reset-password/', views.reset_user_password_view, name='reset_user_password'),
    
    # Печать и предпросмотры
    path('application/preview/', views.agent_application_preview, name='application_preview'),
    path('contract/preview/', views.agent_contract_preview, name='contract_preview'),
    path('save-printed-memo/', views.save_printed_memo_view, name='save_printed_memo'),
]