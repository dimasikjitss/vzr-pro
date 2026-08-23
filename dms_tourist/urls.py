from django.urls import path
from . import views

app_name = 'dms_tourist'

urlpatterns = [
    path('create/', views.create_policy, name='create_policy'),
    path('preview/', views.policy_preview, name='policy_preview'),
    path('success/<int:pk>/', views.policy_success, name='policy_success'),
    path('api/tariffs/', views.get_dms_tariffs_api, name='api_tariffs'),  # <-- API
    path('print/<int:pk>/', views.print_policy, name='print_policy'),
    path('export/buh/', views.export_excel_buh_dms, name='export_excel_buh_dms'),
    path('export/assist/', views.export_excel_bishkek_assist, name='export_excel_bishkek_assist'),
]