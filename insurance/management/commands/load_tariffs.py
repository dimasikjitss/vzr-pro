from django.core.management.base import BaseCommand
from insurance.models import InsuranceTariff
from decimal import Decimal

class Command(BaseCommand):
    help = 'Загружает полную тарифную сетку из официального справочника'

    def handle(self, *args, **kwargs):
        InsuranceTariff.objects.all().delete()

        # Данные: (Программа, Территория, Сумма, Дни_от, Дни_до, Ставка)
        data = [
            # === VZR BRONZE ===
            ('BRONZE', 'ASIA', 15000, 1, 10, 0.65), ('BRONZE', 'ASIA', 30000, 1, 10, 0.75),
            ('BRONZE', 'ASIA', 15000, 11, 20, 0.62), ('BRONZE', 'ASIA', 30000, 11, 20, 0.72),
            ('BRONZE', 'ASIA', 15000, 21, 30, 0.60), ('BRONZE', 'ASIA', 30000, 21, 30, 0.68),
            ('BRONZE', 'ASIA', 15000, 31, 90, 0.52), ('BRONZE', 'ASIA', 30000, 31, 90, 0.60),
            ('BRONZE', 'ASIA', 15000, 91, 180, 0.43), ('BRONZE', 'ASIA', 30000, 91, 180, 0.49),
            ('BRONZE', 'ASIA', 15000, 181, 365, 0.39), ('BRONZE', 'ASIA', 30000, 181, 365, 0.45),

            ('BRONZE', 'SCHENGEN', 30000, 1, 10, 0.75), ('BRONZE', 'SCHENGEN', 50000, 1, 10, 0.90),
            ('BRONZE', 'SCHENGEN', 30000, 11, 20, 0.72), ('BRONZE', 'SCHENGEN', 50000, 11, 20, 0.86),
            ('BRONZE', 'SCHENGEN', 30000, 21, 30, 0.68), ('BRONZE', 'SCHENGEN', 50000, 21, 30, 0.82),
            ('BRONZE', 'SCHENGEN', 30000, 31, 90, 0.60), ('BRONZE', 'SCHENGEN', 50000, 31, 90, 0.71),
            ('BRONZE', 'SCHENGEN', 30000, 91, 180, 0.49), ('BRONZE', 'SCHENGEN', 50000, 91, 180, 0.59),
            ('BRONZE', 'SCHENGEN', 30000, 181, 365, 0.45), ('BRONZE', 'SCHENGEN', 50000, 181, 365, 0.53),

            ('BRONZE', 'WORLD', 30000, 1, 10, 1.45), ('BRONZE', 'WORLD', 30000, 11, 20, 1.38),
            ('BRONZE', 'WORLD', 30000, 21, 30, 1.31), ('BRONZE', 'WORLD', 30000, 31, 90, 1.14),
            ('BRONZE', 'WORLD', 30000, 91, 180, 0.93), ('BRONZE', 'WORLD', 30000, 181, 365, 0.85),

            # === VZR SILVER ===
            ('SILVER', 'ASIA', 30000, 1, 10, 0.93), ('SILVER', 'ASIA', 50000, 1, 10, 1.11),
            ('SILVER', 'ASIA', 30000, 11, 20, 0.89), ('SILVER', 'ASIA', 50000, 11, 20, 1.06),
            ('SILVER', 'ASIA', 30000, 21, 30, 0.84), ('SILVER', 'ASIA', 50000, 21, 30, 1.01),
            ('SILVER', 'ASIA', 30000, 31, 90, 0.74), ('SILVER', 'ASIA', 50000, 31, 90, 0.88),
            ('SILVER', 'ASIA', 30000, 91, 180, 0.60), ('SILVER', 'ASIA', 50000, 91, 180, 0.73),
            ('SILVER', 'ASIA', 30000, 181, 365, 0.55), ('SILVER', 'ASIA', 50000, 181, 365, 0.65),

            ('SILVER', 'SCHENGEN', 30000, 1, 10, 0.93), ('SILVER', 'SCHENGEN', 50000, 1, 10, 1.11),
            ('SILVER', 'SCHENGEN', 30000, 11, 20, 0.89), ('SILVER', 'SCHENGEN', 50000, 11, 20, 1.06),
            ('SILVER', 'SCHENGEN', 30000, 21, 30, 0.84), ('SILVER', 'SCHENGEN', 50000, 21, 30, 1.01),
            ('SILVER', 'SCHENGEN', 30000, 31, 90, 0.74), ('SILVER', 'SCHENGEN', 50000, 31, 90, 0.88),
            ('SILVER', 'SCHENGEN', 30000, 91, 180, 0.60), ('SILVER', 'SCHENGEN', 50000, 91, 180, 0.73),
            ('SILVER', 'SCHENGEN', 30000, 181, 365, 0.55), ('SILVER', 'SCHENGEN', 50000, 181, 365, 0.65),

            ('SILVER', 'WORLD', 30000, 1, 10, 1.80), ('SILVER', 'WORLD', 50000, 1, 10, 2.33),
            ('SILVER', 'WORLD', 30000, 11, 20, 1.71), ('SILVER', 'WORLD', 50000, 11, 20, 2.21),
            ('SILVER', 'WORLD', 30000, 21, 30, 1.63), ('SILVER', 'WORLD', 50000, 21, 30, 2.10),
            ('SILVER', 'WORLD', 30000, 31, 90, 1.41), ('SILVER', 'WORLD', 50000, 31, 90, 1.82),
            ('SILVER', 'WORLD', 30000, 91, 180, 1.15), ('SILVER', 'WORLD', 50000, 91, 180, 1.48),
            ('SILVER', 'WORLD', 30000, 181, 365, 1.05), ('SILVER', 'WORLD', 50000, 181, 365, 1.35),

            # === VZR GOLD ===
            ('GOLD', 'ASIA', 30000, 1, 10, 1.19), ('GOLD', 'ASIA', 50000, 1, 10, 1.51),
            ('GOLD', 'ASIA', 30000, 11, 20, 1.14), ('GOLD', 'ASIA', 50000, 11, 20, 1.44),
            ('GOLD', 'ASIA', 30000, 21, 30, 1.07), ('GOLD', 'ASIA', 50000, 21, 30, 1.36),
            ('GOLD', 'ASIA', 30000, 31, 90, 0.94), ('GOLD', 'ASIA', 50000, 31, 90, 1.19),
            ('GOLD', 'ASIA', 30000, 91, 180, 0.77), ('GOLD', 'ASIA', 50000, 91, 180, 0.97),
            ('GOLD', 'ASIA', 30000, 181, 365, 0.70), ('GOLD', 'ASIA', 50000, 181, 365, 0.88),

            ('GOLD', 'SCHENGEN', 30000, 1, 10, 1.19), ('GOLD', 'SCHENGEN', 50000, 1, 10, 1.51),
            ('GOLD', 'SCHENGEN', 30000, 11, 20, 1.14), ('GOLD', 'SCHENGEN', 50000, 11, 20, 1.44),
            ('GOLD', 'SCHENGEN', 30000, 21, 30, 1.07), ('GOLD', 'SCHENGEN', 50000, 21, 30, 1.36),
            ('GOLD', 'SCHENGEN', 30000, 31, 90, 0.94), ('GOLD', 'SCHENGEN', 50000, 31, 90, 1.19),
            ('GOLD', 'SCHENGEN', 30000, 91, 180, 0.77), ('GOLD', 'SCHENGEN', 50000, 91, 180, 0.97),
            ('GOLD', 'SCHENGEN', 30000, 181, 365, 0.70), ('GOLD', 'SCHENGEN', 50000, 181, 365, 0.88),

            ('GOLD', 'WORLD', 30000, 1, 10, 2.33), ('GOLD', 'WORLD', 50000, 1, 10, 3.01),
            ('GOLD', 'WORLD', 30000, 11, 20, 2.21), ('GOLD', 'WORLD', 50000, 11, 20, 2.86),
            ('GOLD', 'WORLD', 30000, 21, 30, 2.10), ('GOLD', 'WORLD', 50000, 21, 30, 2.71),
            ('GOLD', 'WORLD', 30000, 31, 90, 1.82), ('GOLD', 'WORLD', 50000, 31, 90, 2.35),
            ('GOLD', 'WORLD', 30000, 91, 180, 1.48), ('GOLD', 'WORLD', 50000, 91, 180, 1.91),
            ('GOLD', 'WORLD', 30000, 181, 365, 1.35), ('GOLD', 'WORLD', 50000, 181, 365, 1.74),
        ]

        for p, t, s, dmin, dmax, rate in data:
            InsuranceTariff.objects.create(
                program=p, territory=t, sum_insured=s,
                days_min=dmin, days_max=dmax, rate=Decimal(str(rate))
            )

        self.stdout.write(self.style.SUCCESS(f'Импорт завершен! Загружено {len(data)} строк.'))