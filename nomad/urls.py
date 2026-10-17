from django.urls import path
from . import views

app_name = 'nomad'

urlpatterns = [
    path('create/', views.nomad_create, name='create_policy_nomad'),
    path('preview/', views.nomad_preview, name='nomad_preview'),
    path('success/<int:pk>/', views.nomad_success, name='nomad_success'),
    path('print/<int:pk>/', views.nomad_print, name='nomad_print'),
]