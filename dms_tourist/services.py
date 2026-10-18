from decimal import Decimal
from datetime import date
from django.db import transaction
from .models import DMSTouristPolicy

# Базовый тариф для страховой суммы 100 000 сомов — 80 сомов в сутки
RATES = {
    100000: Decimal('80.00'),
    500000: Decimal('140.00'),
    1000000: Decimal('200.00'),
}


def get_duration_coeff(days: int) -> Decimal:
    """Шкала понижающих коэффициентов согласно длительности поездки"""
    if days <= 5:
        return Decimal('1.0')
    elif 6 <= days <= 10:
        return Decimal('0.9')
    elif 11 <= days <= 20:
        return Decimal('0.8')
    elif 21 <= days <= 30:
        return Decimal('0.7')
    elif 31 <= days <= 60:
        return Decimal('0.6')
    elif 61 <= days <= 179:
        return Decimal('0.5')
    else:
        return Decimal('0.4')  # От 180 и более дней


def calculate_age(birth_date: date, target_date: date) -> int:
    return target_date.year - birth_date.year - ((target_date.month, target_date.day) < (birth_date.month, birth_date.day))


def get_age_coeff(age: int) -> Decimal:
    """Возрастной коэффициент зафиксирован на 1.0"""
    if age < 1 or age > 75:
        raise ValueError(f"Возраст ({age} лет) должен быть от 1 года до 75 лет включительно")
    return Decimal('1.0')


def get_purpose_coeff(purpose: str) -> Decimal:
    """Коэффициент цели поездки зафиксирован на 1.0 для всех целей"""
    return Decimal('1.0')


def calculate_single_person_premium(sum_insured: int, days: int, birth_date: date, start_date: date, purpose: str):
    if days < 1 or days > 365:
        raise ValueError("Период страхования должен составлять от 1 до 365 дней")

    base_daily_rate = RATES.get(int(sum_insured), Decimal('80.00'))

    age = calculate_age(birth_date, start_date)
    k_dur = get_duration_coeff(days)
    k_age = get_age_coeff(age)
    k_pur = get_purpose_coeff(purpose)

    # Премия Нетто = Дни * Базовая ставка (80 сом) * K_длит * K_возраст (1.0) * K_цель (1.0)
    netto = (Decimal(days) * base_daily_rate * k_dur * k_age * k_pur).quantize(Decimal('0.01'))
    nsp = (netto * Decimal('0.02')).quantize(Decimal('0.01'))
    gross = (netto + nsp).quantize(Decimal('0.01'))

    return {
        'age': age,
        'k_dur': k_dur,
        'k_age': k_age,
        'k_pur': k_pur,
        'netto': netto,
        'nsp': nsp,
        'gross': gross,
    }


def generate_dms_policy_number() -> str:
    """Генерация уникального номера полиса вида DMST-000001"""
    with transaction.atomic():
        last_policy = DMSTouristPolicy.objects.select_for_update().order_by('-id').first()
        next_id = (last_policy.id + 1) if last_policy else 1
        return f"DMST-{next_id:06d}"