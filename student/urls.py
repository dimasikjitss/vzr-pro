from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.student_create, name='student_create'),
    path('calculate/', views.student_calculate, name='student_calculate'),
    path('preview/', views.student_preview, name='student_preview'),
    path('success/<int:pk>/', views.student_success, name='student_success'),    # Сюда потом добавим печать PDF и список полисов
    path('print/<int:pk>/', views.print_policy, name='print_policy'), # Использует ту же вьюху, но для чистовика
]


#     path('success/<int:pk>/', views.nomad_success, name='nomad_success'),    # Сюда потом добавим печать PDF и список полисов
#     path('print/<int:pk>/', views.nomad_print, name='nomad_print'),