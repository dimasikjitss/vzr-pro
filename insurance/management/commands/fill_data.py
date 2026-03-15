import random
from datetime import date, timedelta
from decimal import Decimal  # <-- ДОБАВЬ ЭТУ СТРОКУ
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from insurance.models import InsurancePolicy, Branch

class Command(BaseCommand):
    help = 'Заполняет базу 50 тестовыми полисами за последнюю неделю'

    def handle(self, *args, **kwargs):
        # 1. Получаем ресурсы
        users = list(User.objects.all())
        branches = list(Branch.objects.all())
        
        if not users or not branches:
            self.stdout.write(self.style.ERROR('Сначала создайте хотя бы одного юзера и один филиал!'))
            return

        territories = ['ASIA', 'SCHENGEN', 'WORLD']
        programs = ['BRONZE', 'SILVER', 'GOLD']
        
        self.stdout.write(f'Начинаю генерацию 50 полисов...')

        for i in range(50):
            # 2. Генерируем случайную дату за последние 7 дней
            random_days_ago = random.randint(0, 7)
            issue_date = date.today() - timedelta(days=random_days_ago)
            
            # 3. Создаем полис
            policy = InsurancePolicy.objects.create(
                agent=random.choice(users),
                branch=random.choice(branches),
                holder_name=f"ТЕСТОВЫЙ КЛИЕНТ №{i+100}",
                holder_inn="12345678901234",
                holder_phone="+996700112233", # Добавил, если оно NOT NULL
                holder_passport="AN123456",
                date_from=issue_date + timedelta(days=5),
                date_to=issue_date + timedelta(days=15),
                territory=random.choice(territories),
                program=random.choice(programs),
                total_premium_som=Decimal(random.randint(1500, 12000)),
                exchange_rate=Decimal('89.50'), # ТВОЙ ФИКС: добавляем курс валюты
                issue_date=issue_date
            )
            
            # 4. Принудительно обновляем дату, если Django все еще игнорирует её при .create()
            InsurancePolicy.objects.filter(pk=policy.pk).update(issue_date=issue_date)

        self.stdout.write(self.style.SUCCESS(f'Успешно добавлено 50 полисов!'))