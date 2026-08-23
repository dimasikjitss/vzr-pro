# analytics_core.py
from django.db.models import Sum, Count, F
from django.db.models.functions import TruncDate
from django.contrib.auth.models import User
from datetime import date, timedelta
from decimal import Decimal
from collections import defaultdict

from .models import InsurancePolicy, Branch
from nomad.models import NomadPolicy
from student.models import StudentPolicy
from dms_tourist.models import DMSTouristPolicy


class AnalyticsManager:
    """Универсальный менеджер для сбора аналитики по любому продукту"""

    @staticmethod
    def get_vzr_metrics(d_from, d_to, branch_id=None):
        filters = {'issue_date__range': [d_from, d_to]}
        if branch_id and str(branch_id).strip():
            filters['branch_id'] = branch_id

        qs = InsurancePolicy.objects.filter(**filters)
        
        totals = qs.aggregate(
            total_count=Count('id'),
            total_amount=Sum('total_premium_som')
        )

        chart_data = qs.annotate(date=TruncDate('issue_date')) \
                       .values('date') \
                       .annotate(sum=Sum('total_premium_som'), count=Count('id')) \
                       .order_by('date')

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
    def get_vt_metrics(d_from, d_to, branch_id=None):
        filters = {'issue_date__range': [d_from, d_to]}
        if branch_id and str(branch_id).strip():
            filters['branch_id'] = branch_id

        qs = NomadPolicy.objects.filter(**filters)
        
        totals = qs.aggregate(
            total_count=Count('id'),
            total_amount=Sum('total_premium_gross')
        )

        chart_data = qs.annotate(date=TruncDate('issue_date')) \
                       .values('date') \
                       .annotate(sum=Sum('total_premium_gross'), count=Count('id')) \
                       .order_by('date')

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

    @staticmethod
    def get_student_metrics(d_from, d_to, branch_id=None):
        filters = {'issue_date__range': [d_from, d_to]}
        if branch_id and str(branch_id).strip():
            filters['branch_id'] = branch_id

        qs = StudentPolicy.objects.filter(**filters)
        
        totals = qs.aggregate(
            total_count=Count('id'),
            total_amount=Sum('total_premium_gross')
        )

        chart_data = qs.annotate(date=TruncDate('issue_date')) \
                       .values('date') \
                       .annotate(sum=Sum('total_premium_gross'), count=Count('id')) \
                       .order_by('date')

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

    @staticmethod
    def get_dms_metrics(d_from, d_to, branch_id=None):
        """Аналитика по продукту ДМС Турист"""
        filters = {'issue_date__range': [d_from, d_to]}
        if branch_id and str(branch_id).strip():
            filters['branch_id'] = branch_id

        qs = DMSTouristPolicy.objects.filter(**filters)

        totals = qs.aggregate(
            total_count=Count('id'),
            total_amount=Sum('total_premium_gross')
        )

        chart_data = qs.annotate(date=TruncDate('issue_date')) \
                       .values('date') \
                       .annotate(sum=Sum('total_premium_gross'), count=Count('id')) \
                       .order_by('date')

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

    @staticmethod
    def get_global_summary_metrics(date_from, date_to, branch_id=None):
        """Сводная аналитика по всем 4 продуктам (ВЗР, Nomad, Дети, ДМС Турист)"""
        # 1. QuerySets
        vzr_qs = InsurancePolicy.objects.all()
        nomad_qs = NomadPolicy.objects.all()
        student_qs = StudentPolicy.objects.all()
        dms_qs = DMSTouristPolicy.objects.all()

        # 2. Фильтрация по филиалу
        if branch_id:
            vzr_qs = vzr_qs.filter(branch_id=branch_id)
            nomad_qs = nomad_qs.filter(branch_id=branch_id)
            student_qs = student_qs.filter(branch_id=branch_id)
            dms_qs = dms_qs.filter(branch_id=branch_id)

        # 3. МЕТРИКИ ЗА ВСЁ ВРЕМЯ (ALL-TIME)
        all_time_vzr = vzr_qs.aggregate(sum=Sum('total_premium_som'), count=Count('id'))
        all_time_nomad = nomad_qs.aggregate(sum=Sum('total_premium_gross'), count=Count('id'))
        all_time_student = student_qs.aggregate(sum=Sum('total_premium_gross'), count=Count('id'))
        all_time_dms = dms_qs.aggregate(sum=Sum('total_premium_gross'), count=Count('id'))

        all_time_vzr_sum = all_time_vzr['sum'] or 0
        all_time_nomad_sum = all_time_nomad['sum'] or 0
        all_time_student_sum = all_time_student['sum'] or 0
        all_time_dms_sum = all_time_dms['sum'] or 0
        
        all_time_total_som = all_time_vzr_sum + all_time_nomad_sum + all_time_student_sum + all_time_dms_sum
        all_time_total_count = (all_time_vzr['count'] or 0) + (all_time_nomad['count'] or 0) + (all_time_student['count'] or 0) + (all_time_dms['count'] or 0)

        # 4. МЕТРИКИ ЗА ВЫБРАННЫЙ ПЕРИОД
        vzr_period = vzr_qs.filter(issue_date__range=(date_from, date_to))
        nomad_period = nomad_qs.filter(issue_date__range=(date_from, date_to))
        student_period = student_qs.filter(issue_date__range=(date_from, date_to))
        dms_period = dms_qs.filter(issue_date__range=(date_from, date_to))

        agg_vzr = vzr_period.aggregate(sum=Sum('total_premium_som'), count=Count('id'))
        agg_nomad = nomad_period.aggregate(sum=Sum('total_premium_gross'), count=Count('id'))
        agg_student = student_period.aggregate(sum=Sum('total_premium_gross'), count=Count('id'))
        agg_dms = dms_period.aggregate(sum=Sum('total_premium_gross'), count=Count('id'))

        v_sum = agg_vzr['sum'] or 0
        n_sum = agg_nomad['sum'] or 0
        s_sum = agg_student['sum'] or 0
        d_sum = agg_dms['sum'] or 0

        period_total_som = v_sum + n_sum + s_sum + d_sum
        period_total_count = (agg_vzr['count'] or 0) + (agg_nomad['count'] or 0) + (agg_student['count'] or 0) + (agg_dms['count'] or 0)

        # 5. ДИНАМИКА СБОРОВ ПО ДНЯМ
        vzr_days = vzr_period.annotate(date=TruncDate('issue_date')).values('date').annotate(total=Sum('total_premium_som')).order_by('date')
        nomad_days = nomad_period.annotate(date=TruncDate('issue_date')).values('date').annotate(total=Sum('total_premium_gross')).order_by('date')
        student_days = student_period.annotate(date=TruncDate('issue_date')).values('date').annotate(total=Sum('total_premium_gross')).order_by('date')
        dms_days = dms_period.annotate(date=TruncDate('issue_date')).values('date').annotate(total=Sum('total_premium_gross')).order_by('date')

        days_dict = {}
        delta = date_to - date_from
        for i in range(delta.days + 1):
            d_str = (date_from + timedelta(days=i)).strftime('%d.%m.%Y')
            days_dict[d_str] = {'VZR': 0, 'NOMAD': 0, 'STUDENT': 0, 'DMS': 0}

        for x in vzr_days:
            d_str = x['date'].strftime('%d.%m.%Y')
            if d_str in days_dict: days_dict[d_str]['VZR'] = float(x['total'] or 0)
        for x in nomad_days:
            d_str = x['date'].strftime('%d.%m.%Y')
            if d_str in days_dict: days_dict[d_str]['NOMAD'] = float(x['total'] or 0)
        for x in student_days:
            d_str = x['date'].strftime('%d.%m.%Y')
            if d_str in days_dict: days_dict[d_str]['STUDENT'] = float(x['total'] or 0)
        for x in dms_days:
            d_str = x['date'].strftime('%d.%m.%Y')
            if d_str in days_dict: days_dict[d_str]['DMS'] = float(x['total'] or 0)

        chart_dates = list(days_dict.keys())
        chart_vzr_line = [days_dict[d]['VZR'] for d in chart_dates]
        chart_nomad_line = [days_dict[d]['NOMAD'] for d in chart_dates]
        chart_student_line = [days_dict[d]['STUDENT'] for d in chart_dates]
        chart_dms_line = [days_dict[d]['DMS'] for d in chart_dates]

        # 6. СБОРЫ ПО ФИЛИАЛАМ
        branch_data = {b.name: 0.0 for b in Branch.objects.all()}

        for x in vzr_period.values('branch__name').annotate(s=Sum('total_premium_som')):
            if x['branch__name']: branch_data[x['branch__name']] += float(x['s'] or 0)
            
        for x in nomad_period.values('branch__name').annotate(s=Sum('total_premium_gross')):
            if x['branch__name']: branch_data[x['branch__name']] += float(x['s'] or 0)
            
        for x in student_period.values('branch__name').annotate(s=Sum('total_premium_gross')):
            if x['branch__name']: branch_data[x['branch__name']] += float(x['s'] or 0)

        for x in dms_period.values('branch__name').annotate(s=Sum('total_premium_gross')):
            if x['branch__name']: branch_data[x['branch__name']] += float(x['s'] or 0)

        sorted_branches = sorted(branch_data.items(), key=lambda item: item[1], reverse=True)
        branch_labels = [item[0] for item in sorted_branches if item[1] > 0]
        branch_values = [item[1] for item in sorted_branches if item[1] > 0]

        # 7. РЕЙТИНГ СОТРУДНИКОВ
        agent_data = {}
        
        # ВЗР
        for x in vzr_period.values('agent__id', 'agent__first_name', 'agent__last_name', 'branch__name').annotate(s=Sum('total_premium_som'), c=Count('id')):
            name = f"{x['agent__last_name']} {x['agent__first_name']}".strip() or f"ID {x['agent__id']}"
            if name not in agent_data: 
                agent_data[name] = {'sum': 0.0, 'count': 0, 'branch': x['branch__name'] or 'Не указан'}
            agent_data[name]['sum'] += float(x['s'] or 0)
            agent_data[name]['count'] += x['c']

        # NOMAD
        for x in nomad_period.values('agent__id', 'agent__first_name', 'agent__last_name', 'branch__name').annotate(s=Sum('total_premium_gross'), c=Count('id')):
            name = f"{x['agent__last_name']} {x['agent__first_name']}".strip() or f"ID {x['agent__id']}"
            if name not in agent_data: 
                agent_data[name] = {'sum': 0.0, 'count': 0, 'branch': x['branch__name'] or 'Не указан'}
            agent_data[name]['sum'] += float(x['s'] or 0)
            agent_data[name]['count'] += x['c']

        # ДЕТИ
        for x in student_period.values('agent__id', 'agent__first_name', 'agent__last_name', 'branch__name').annotate(s=Sum('total_premium_gross'), c=Count('id')):
            name = f"{x['agent__last_name']} {x['agent__first_name']}".strip() or f"ID {x['agent__id']}"
            if name not in agent_data: 
                agent_data[name] = {'sum': 0.0, 'count': 0, 'branch': x['branch__name'] or 'Не указан'}
            agent_data[name]['sum'] += float(x['s'] or 0)
            agent_data[name]['count'] += x['c']

        # ДМС ТУРИСТ
        for x in dms_period.values('agent__id', 'agent__first_name', 'agent__last_name', 'branch__name').annotate(s=Sum('total_premium_gross'), c=Count('id')):
            name = f"{x['agent__last_name']} {x['agent__first_name']}".strip() or f"ID {x['agent__id']}"
            if name not in agent_data: 
                agent_data[name] = {'sum': 0.0, 'count': 0, 'branch': x['branch__name'] or 'Не указан'}
            agent_data[name]['sum'] += float(x['s'] or 0)
            agent_data[name]['count'] += x['c']

        agent_performance_list = [
            {
                'name': name,
                'count': values['count'],
                'total_sum': values['sum'],
                'branch': values['branch'],
                'avg_check': values['sum'] / values['count'] if values['count'] > 0 else 0
            }
            for name, values in agent_data.items() if values['sum'] > 0
        ]
        agent_performance_list = sorted(agent_performance_list, key=lambda x: x['total_sum'], reverse=True)

        return {
            'all_time_total_som': all_time_total_som,
            'all_time_total_count': all_time_total_count,
            'all_time_vzr_sum': all_time_vzr_sum,
            'all_time_nomad_sum': all_time_nomad_sum,
            'all_time_student_sum': all_time_student_sum,
            'all_time_dms_sum': all_time_dms_sum,

            'period_total_som': period_total_som,
            'period_total_count': period_total_count,
            'v_sum': v_sum, 'v_count': agg_vzr['count'] or 0,
            'n_sum': n_sum, 'n_count': agg_nomad['count'] or 0,
            's_sum': s_sum, 's_count': agg_student['count'] or 0,
            'd_sum': d_sum, 'd_count': agg_dms['count'] or 0,

            'chart_dates': chart_dates,
            'chart_vzr_line': chart_vzr_line,
            'chart_nomad_line': chart_nomad_line,
            'chart_student_line': chart_student_line,
            'chart_dms_line': chart_dms_line,

            'branch_labels': branch_labels,
            'branch_values': branch_values,
            'agent_performance': agent_performance_list,
        }


PRODUCT_ANALYTICS_MAP = {
    'vzr': AnalyticsManager.get_vzr_metrics,
    'vt': AnalyticsManager.get_vt_metrics,
    'student': AnalyticsManager.get_student_metrics,
    'dms': AnalyticsManager.get_dms_metrics,
}