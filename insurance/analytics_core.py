# analytics_core.py
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from datetime import date
from insurance.models import InsurancePolicy
from nomad.models import NomadPolicy

class AnalyticsManager:
    """Универсальный менеджер для сбора аналитики по любому продукту"""

    @staticmethod
    def get_vzr_metrics(d_from, d_to):
        # Фильтруем полисы за период
        qs = InsurancePolicy.objects.filter(issue_date__range=[d_from, d_to])
        
        # Общие сборы и количество
        # Премию берем общую по полису total_premium_som
        totals = qs.aggregate(
            total_count=Count('id'),
            total_amount=Sum('total_premium_som')
        )

        # Продажи по дням для графика
        chart_data = qs.annotate(date=TruncDate('issue_date')) \
                       .values('date') \
                       .annotate(sum=Sum('total_premium_som'), count=Count('id')) \
                       .order_by('date')

        # Топ-5 агентов
        top_agents = qs.values('agent__username', 'agent__first_name', 'agent__last_name') \
                       .annotate(total_sales=Sum('total_premium_som'), count=Count('id')) \
                       .order_by('-total_sales')[:5]

        return {
            'total_count': totals['total_count'] or 0,
            'total_amount': float(totals['total_amount'] or 0),
            'chart': [{'date': item['date'].strftime('%d.%m.%Y'), 'sum': float(item['sum']), 'count': item['count']} for item in chart_data],
            'top_agents': [
                {
                    'name': f"{a['agent__first_name']} {a['agent__last_name']}".strip() or a['agent__username'],
                    'sales': float(a['total_sales']),
                    'count': a['count']
                } for a in top_agents
            ]
        }

    @staticmethod
    def get_vt_metrics(d_from, d_to):
        # Фильтруем полисы Nomad за период
        qs = NomadPolicy.objects.filter(issue_date__range=[d_from, d_to])
        
        # Общие сборы и количество (у Nomad поле называется total_premium_gross)
        totals = qs.aggregate(
            total_count=Count('id'),
            total_amount=Sum('total_premium_gross')
        )

        # Продажи по дням для графика
        chart_data = qs.annotate(date=TruncDate('issue_date')) \
                       .values('date') \
                       .annotate(sum=Sum('total_premium_gross'), count=Count('id')) \
                       .order_by('date')

        # Топ-5 агентов
        top_agents = qs.values('agent__username', 'agent__first_name', 'agent__last_name') \
                       .annotate(total_sales=Sum('total_premium_gross'), count=Count('id')) \
                       .order_by('-total_sales')[:5]

        return {
            'total_count': totals['total_count'] or 0,
            'total_amount': float(totals['total_amount'] or 0),
            'chart': [{'date': item['date'].strftime('%d.%m.%Y'), 'sum': float(item['sum']), 'count': item['count']} for item in chart_data],
            'top_agents': [
                {
                    'name': f"{a['agent__first_name']} {a['agent__last_name']}".strip() or a['agent__username'],
                    'sales': float(a['total_sales']),
                    'count': a['count']
                } for a in top_agents
            ]
        }

# КАРТА ПРОДУКТОВ: Когда появится 3-й тип полиса, ты просто добавишь метод выше 
# и зарегистрируешь его в этом словаре за 1 минуту.
PRODUCT_ANALYTICS_MAP = {
    'vzr': AnalyticsManager.get_vzr_metrics,
    'vt': AnalyticsManager.get_vt_metrics,
}