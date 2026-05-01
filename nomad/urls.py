# nomad/urls.py
from django.urls import path
from . import views
app_name = 'nomad'

urlpatterns = [
    # Страница создания полиса Nomad
    path('create/', views.nomad_create, name='create_policy_nomad'),
    path('success/<int:pk>/', views.nomad_success, name='nomad_success'),    # Сюда потом добавим печать PDF и список полисов
    path('print/<int:pk>/', views.nomad_print, name='nomad_print'),
    # path('list/', views.nomad_list, name='nomad_list'),
]