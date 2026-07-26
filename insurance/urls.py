from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # --- Авторизация ---
    path('login/', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # --- Основной функционал ---
    path('', views.home, name='home'),
    path('vzr/', views.vzr_create, name='create_policy_vzr'),
    path('success/<int:pk>/', views.policy_success, name='policy_success'),
    path('print/<int:pk>/', views.print_policy, name='print_policy'),

    # --- API для калькулятора (Новое!) ---
    # Именно по этому адресу JavaScript будет забирать тарифы из базы данных
    path('api/tariffs/', views.get_tariffs_api, name='tariffs_api'),

    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/export/', views.export_excel, name='export_excel'),

    path('policy/preview/', views.policy_preview, name='policy_preview'),
    
    path('analytics/', views.analytics_page, name='analytics_dashboard'),
    path('api/analytics/', views.analytics_api, name='analytics_api'),
    path('analytics/export/', views.export_excel_buh, name='export_excel_buh'),
    path('analytics/export-savitar/', views.export_excel_savitar, name='export_excel_savitar'),
    path('analytics/export-vt/', views.export_excel_buh_vt, name='export_excel_buh_vt'),
    path('analytics/export-student/', views.export_excel_buh_student, name='export_excel_buh_student'),
]