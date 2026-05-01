from django.apps import AppConfig


class InsuranceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'insurance'
# nomad/apps.py
class NomadConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'nomad'
    verbose_name = '1. Внутренний туризм (NOMAD)' # Это заголовок в админке

    # vzr/apps.py
class VzrConfig(AppConfig):
    name = 'vzr'
    verbose_name = '2. Выезд за рубеж (VZR)'