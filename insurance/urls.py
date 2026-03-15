# from django.urls import path
# from django.contrib.auth import views as auth_views
# from . import views

# urlpatterns = [
#     # 1. Страница входа. 
#     # template_name говорит Django искать файл login.html в папке templates
#     path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    
#     # 2. Страница выхода
#     path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
#     # 3. Главная страница с формой (вьюха index)
#     path('', views.index, name='home'),
    
#     # 4. Страница печати PDF (pk - это ID полиса в базе)
#     path('print/<int:pk>/', views.print_policy, name='print_policy'),
# ]

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # --- Авторизация ---
    path('login/', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # --- Основной функционал ---
    path('', views.home, name='home'),
    path('success/<int:pk>/', views.policy_success, name='policy_success'),
    path('print/<int:pk>/', views.print_policy, name='print_policy'),

    # --- API для калькулятора (Новое!) ---
    # Именно по этому адресу JavaScript будет забирать тарифы из базы данных
    path('api/tariffs/', views.get_tariffs_api, name='tariffs_api'),

    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/export/', views.export_excel, name='export_excel'),
    
]