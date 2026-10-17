from django.apps import AppConfig

# nomad/apps.py
class NomadConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'nomad'
    verbose_name = '1. ВНУТРЕННИЙ ТУРИЗМ (NOMAD)' # Именно это появится в меню