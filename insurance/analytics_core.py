# analytics_core.py
from django.db.models import Sum, Count, F
from django.db.models.functions import TruncDate
from django.contrib.auth.models import User
from datetime import date, timedelta
from .models import InsurancePolicy, Branch
from nomad.models import NomadPolicy
from student.models import StudentPolicy
from collections import defaultdict

class AnalyticsManager:
    """Универсальный менеджер для сбора аналитики по любому продукту"""

    @staticmethod
    def get_vzr_metrics(d_from, d_to, branch_id=None):  # ДОБАВИЛИ branch_id=None
        filters = {'issue_date__range': [d_from, d_to]}
        
        # Безопасная проверка филиала
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
    def get_vt_metrics(d_from, d_to, branch_id=None):  # ДОБАВИЛИ branch_id=None
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
    def get_student_metrics(d_from, d_to, branch_id=None):  # ДОБАВИЛИ branch_id=None
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
    # def get_global_summary_metrics(d_from, d_to, branch_id=None):
    #     """
    #     АРХИТЕКТУРНОЕ РЕШЕНИЕ ДЛЯ СУПЕРЮЗЕРА: 
    #     Собирает сквозную высокопроизводительную аналитику по ВСЕМ 3 продуктам сразу.
    #     Вся математика выполняется на уровне СУБД (PostgreSQL).
    #     """
    #     filters = {'issue_date__range': [d_from, d_to]}
    #     if branch_id and str(branch_id).strip():
    #         filters['branch_id'] = branch_id

    #     # 1. Запрашиваем только агрегаты (база данных не выгружает сами строки)
    #     vzr_totals = InsurancePolicy.objects.filter(**filters).aggregate(c=Count('id'), s=Sum('total_premium_som'))
    #     nomad_totals = NomadPolicy.objects.filter(**filters).aggregate(c=Count('id'), s=Sum('total_premium_gross'))
    #     student_totals = StudentPolicy.objects.filter(**filters).aggregate(c=Count('id'), s=Sum('total_premium_gross'))

    #     v_count = vzr_totals['c'] or 0
    #     v_sum = float(vzr_totals['s'] or 0)
        
    #     n_count = nomad_totals['c'] or 0
    #     n_sum = float(nomad_totals['s'] or 0)
        
    #     s_count = student_totals['c'] or 0
    #     s_sum = float(student_totals['s'] or 0)

    #     # Считаем глобальные KPI
    #     total_count = v_count + n_count + s_count
    #     total_som = v_sum + n_sum + s_sum

    #     # 2. Динамика продаж по дням (Суммируем по датам на уровне базы)
    #     sales_by_day = defaultdict(float)
        
    #     v_days = InsurancePolicy.objects.filter(**filters).annotate(day=TruncDate('issue_date')).values('day').annotate(s=Sum('total_premium_som'))
    #     n_days = NomadPolicy.objects.filter(**filters).annotate(day=TruncDate('issue_date')).values('day').annotate(s=Sum('total_premium_gross'))
    #     s_days = StudentPolicy.objects.filter(**filters).annotate(day=TruncDate('issue_date')).values('day').annotate(s=Sum('total_premium_gross'))

    #     for d in v_days: sales_by_day[d['day'].strftime('%d.%m')] += float(d['s'] or 0)
    #     for d in n_days: sales_by_day[d['day'].strftime('%d.%m')] += float(d['s'] or 0)
    #     for d in s_days: sales_by_day[d['day'].strftime('%d.%m')] += float(d['s'] or 0)

    #     # 3. Эффективность агентов (Сводный ТОП-10 по всем продуктам)
    #     agents_map = defaultdict(lambda: {'count': 0, 'total': 0.0})
        
    #     v_ags = InsurancePolicy.objects.filter(**filters).values('agent__username', 'agent__first_name', 'agent__last_name').annotate(c=Count('id'), s=Sum('total_premium_som'))
    #     n_ags = NomadPolicy.objects.filter(**filters).values('agent__username', 'agent__first_name', 'agent__last_name').annotate(c=Count('id'), s=Sum('total_premium_gross'))
    #     s_ags = StudentPolicy.objects.filter(**filters).values('agent__username', 'agent__first_name', 'agent__last_name').annotate(c=Count('id'), s=Sum('total_premium_gross'))

    #     for row in v_ags:
    #         name = f"{row['agent__first_name']} {row['agent__last_name']}".strip() or row['agent__username']
    #         agents_map[name]['count'] += row['c']
    #         agents_map[name]['total'] += float(row['s'] or 0)

    #     for row in n_ags:
    #         name = f"{row['agent__first_name']} {row['agent__last_name']}".strip() or row['agent__username']
    #         agents_map[name]['count'] += row['c']
    #         agents_map[name]['total'] += float(row['s'] or 0)

    #     for row in s_ags:
    #         name = f"{row['agent__first_name']} {row['agent__last_name']}".strip() or row['agent__username']
    #         agents_map[name]['count'] += row['c']
    #         agents_map[name]['total'] += float(row['s'] or 0)

    #     agent_performance = [
    #         {
    #             'name': name,
    #             'count': data['count'],
    #             'total': round(data['total'], 2),
    #             'avg_check': round(data['total'] / data['count'], 0) if data['count'] > 0 else 0
    #         } for name, data in agents_map.items()
    #     ]
    #     agent_performance = sorted(agent_performance, key=lambda x: x['total'], reverse=True)[:10]

    #     # 4. Сводка по филиалам (Группировка на бэкенде)
    #     branch_map = defaultdict(lambda: {'count': 0, 'total': 0.0})
        
    #     v_br = InsurancePolicy.objects.filter(**filters).values('branch__name').annotate(c=Count('id'), s=Sum('total_premium_som'))
    #     n_br = NomadPolicy.objects.filter(**filters).values('branch__name').annotate(c=Count('id'), s=Sum('total_premium_gross'))
    #     s_br = StudentPolicy.objects.filter(**filters).values('branch__name').annotate(c=Count('id'), s=Sum('total_premium_gross'))

    #     for b in v_br:
    #         name = b['branch__name'] or "Не указан"
    #         branch_map[name]['count'] += b['c']
    #         branch_map[name]['total'] += float(b['s'] or 0)
    #     for b in n_br:
    #         name = b['branch__name'] or "Не указан"
    #         branch_map[name]['count'] += b['c']
    #         branch_map[name]['total'] += float(b['s'] or 0)
    #     for b in s_br:
    #         name = b['branch__name'] or "Не указан"
    #         branch_map[name]['count'] += b['c']
    #         branch_map[name]['total'] += float(b['s'] or 0)

    #     branch_stats = [
    #         {'branch__name': name, 'count': data['count'], 'total': round(data['total'], 2)}
    #         for name, data in branch_map.items()
    #     ]
    #     branch_stats = sorted(branch_stats, key=lambda x: x['total'], reverse=True)

    #     # 5. Динамическое распределение программ и территорий (ИСПРАВЛЕНО)
    #     program_labels = set()
    #     prog_terr_map = defaultdict(lambda: defaultdict(float))

    #     # Собираем ВЗР направления (берём 'program' напрямую, если это CharField)
    #     v_progs = InsurancePolicy.objects.filter(**filters).values('program', 'territory').annotate(s=Sum('total_premium_som'))
    #     for vp in v_progs:
    #         p_name = str(vp['program'] or "BRONZE")
    #         terr = vp['territory'] or "UNKNOWN"
    #         program_labels.add(p_name)
    #         prog_terr_map[p_name][terr] += float(vp['s'] or 0)

    #     # Добавляем Nomad (берём 'program' напрямую)
    #     n_progs = NomadPolicy.objects.filter(**filters).values('program').annotate(s=Sum('total_premium_gross'))
    #     for np in n_progs:
    #         p_name = str(np['program'] or "NOMAD_PROG")
    #         program_labels.add(p_name)
    #         prog_terr_map[p_name]['KYRGYZSTAN'] += float(np['s'] or 0)

    #     # Добавляем Детей (тут у тебя ForeignKey, поэтому безопасно вытаскиваем имя через релейшн или fallback)
    #     sidebar_progs = StudentPolicy.objects.filter(**filters).values('program__name').annotate(s=Sum('total_premium_gross'))
    #     for sp in sidebar_progs:
    #         p_name = str(sp['program__name'] or "CHILD_PROG")
    #         program_labels.add(p_name)
    #         prog_terr_map[p_name]['KYRGYZSTAN'] += float(sp['s'] or 0)

    #     program_labels = sorted(list(program_labels))
        
    #     all_territories = ['ASIA', 'SCHENGEN', 'WORLD', 'KYRGYZSTAN']
    #     chart_program_series = []
    #     for terr in all_territories:
    #         chart_program_series.append({
    #             'name': terr,
    #             'data': [round(prog_terr_map[prog][terr], 2) for prog in program_labels]
    #         })

    #     return {
    #         'total_count': total_count,
    #         'total_som': round(total_som, 2),
    #         'v_count': v_count, 'v_sum': v_sum,
    #         'n_count': n_count, 'n_sum': n_sum,
    #         's_count': s_count, 's_sum': s_sum,
    #         'chart_daily_labels': list(sales_by_day.keys())[::-1],
    #         'chart_daily_values': list(sales_by_day.values())[::-1],
    #         'chart_program_labels': program_labels,
    #         'chart_program_series': chart_program_series,
    #         'agent_performance': agent_performance,
    #         'branch_stats': branch_stats
    #     }
    #изменил в 17:25 5/07 новая аналитика пробую прод
    def get_global_summary_metrics(date_from, date_to, branch_id=None):
        # 1. Базовая инициализация QuerySet-ов для всех 3-х продуктов
        vzr_qs = InsurancePolicy.objects.all()
        nomad_qs = NomadPolicy.objects.all()
        student_qs = StudentPolicy.objects.all()

        # 2. Фильтрация по филиалу (если выбран в селекторе)
        if branch_id:
            vzr_qs = vzr_qs.filter(branch_id=branch_id)
            nomad_qs = nomad_qs.filter(branch_id=branch_id)
            student_qs = student_qs.filter(branch_id=branch_id)

        # ----------------------------------------------------
        # МЕТРИКИ ЗА ВСЁ ВРЕМЯ (ALL-TIME)
        # ----------------------------------------------------
        all_time_vzr = vzr_qs.aggregate(sum=Sum('total_premium_som'), count=Count('id'))
        all_time_nomad = nomad_qs.aggregate(sum=Sum('total_premium_gross'), count=Count('id'))
        all_time_student = student_qs.aggregate(sum=Sum('total_premium_gross'), count=Count('id'))

        all_time_vzr_sum = all_time_vzr['sum'] or 0
        all_time_nomad_sum = all_time_nomad['sum'] or 0
        all_time_student_sum = all_time_student['sum'] or 0
        
        all_time_total_som = all_time_vzr_sum + all_time_nomad_sum + all_time_student_sum
        all_time_total_count = (all_time_vzr['count'] or 0) + (all_time_nomad['count'] or 0) + (all_time_student['count'] or 0)

        # ----------------------------------------------------
        # МЕТРИКИ ЗА ВЫБРАННЫЙ ОТЧЕТНЫЙ ПЕРИОД
        # ----------------------------------------------------
        vzr_period = vzr_qs.filter(issue_date__range=(date_from, date_to))
        nomad_period = nomad_qs.filter(issue_date__range=(date_from, date_to))
        student_period = student_qs.filter(issue_date__range=(date_from, date_to))

        agg_vzr = vzr_period.aggregate(sum=Sum('total_premium_som'), count=Count('id'))
        agg_nomad = nomad_period.aggregate(sum=Sum('total_premium_gross'), count=Count('id'))
        agg_student = student_period.aggregate(sum=Sum('total_premium_gross'), count=Count('id'))

        v_sum = agg_vzr['sum'] or 0
        n_sum = agg_nomad['sum'] or 0
        s_sum = agg_student['sum'] or 0

        period_total_som = v_sum + n_sum + s_sum
        period_total_count = (agg_vzr['count'] or 0) + (agg_nomad['count'] or 0) + (agg_student['count'] or 0)

        # ----------------------------------------------------
        # ГРАФИК 1: СКВОЗНАЯ ДИНАМИКА СБОРОВ ПО ДНЯМ (Раздельные линии)
        # ----------------------------------------------------
        # Собираем данные за период, схлопывая до даты
        vzr_days = vzr_period.annotate(date=TruncDate('issue_date')).values('date').annotate(total=Sum('total_premium_som')).order_by('date')
        nomad_days = nomad_period.annotate(date=TruncDate('issue_date')).values('date').annotate(total=Sum('total_premium_gross')).order_by('date')
        student_days = student_period.annotate(date=TruncDate('issue_date')).values('date').annotate(total=Sum('total_premium_gross')).order_by('date')

        # Формируем единую временную шкалу (массив дат строк)
        days_dict = {}
        delta = date_to - date_from
        for i in range(delta.days + 1):
            d_str = (date_from + timedelta(days=i)).strftime('%d.%m.%Y')
            days_dict[d_str] = {'VZR': 0, 'NOMAD': 0, 'STUDENT': 0}

        for x in vzr_days:
            d_str = x['date'].strftime('%d.%m.%Y')
            if d_str in days_dict: days_dict[d_str]['VZR'] = float(x['total'] or 0)
        for x in nomad_days:
            d_str = x['date'].strftime('%d.%m.%Y')
            if d_str in days_dict: days_dict[d_str]['NOMAD'] = float(x['total'] or 0)
        for x in student_days:
            d_str = x['date'].strftime('%d.%m.%Y')
            if d_str in days_dict: days_dict[d_str]['STUDENT'] = float(x['total'] or 0)

        chart_dates = list(days_dict.keys())
        chart_vzr_line = [days_dict[d]['VZR'] for d in chart_dates]
        chart_nomad_line = [days_dict[d]['NOMAD'] for d in chart_dates]
        chart_student_line = [days_dict[d]['STUDENT'] for d in chart_dates]

        # ----------------------------------------------------
        # ГРАФИК 2: СБОРЫ ПО ФИЛИАЛАМ И СОТРУДНИКАМ (РЕЙТИНГ)
        # ----------------------------------------------------
        # Собираем сборы филиалов по всем 3-м базам
        branch_data = {}
        for b in Branch.objects.all():
            branch_data[b.name] = 0

        # Агрегируем по филиалам
        v_b = vzr_period.values('branch__name').annotate(s=Sum('total_premium_som'))
        for x in v_b: 
            if x['branch__name']: branch_data[x['branch__name']] += float(x['s'] or 0)
            
        n_b = nomad_period.values('branch__name').annotate(s=Sum('total_premium_gross'))
        for x in n_b: 
            if x['branch__name']: branch_data[x['branch__name']] += float(x['s'] or 0)
            
        s_b = student_period.values('branch__name').annotate(s=Sum('total_premium_gross'))
        for x in s_b: 
            if x['branch__name']: branch_data[x['branch__name']] += float(x['s'] or 0)

        sorted_branches = sorted(branch_data.items(), key=lambda item: item[1], reverse=True)
        branch_labels = [item[0] for item in sorted_branches if item[1] > 0]
        branch_values = [item[1] for item in sorted_branches if item[1] > 0]

        # Рейтинг сотрудников (эффективность агентов)
        # Рейтинг сотрудников (эффективность агентов) с сохранением филиала
        agent_data = {}
        
        # 1. Сбор по ВЗР
        v_a = vzr_period.values('agent__id', 'agent__first_name', 'agent__last_name', 'branch__name').annotate(s=Sum('total_premium_som'), c=Count('id'))
        for x in v_a:
            name = f"{x['agent__last_name']} {x['agent__first_name']}".strip() or f"ID {x['agent__id']}"
            if name not in agent_data: 
                agent_data[name] = {'sum': 0, 'count': 0, 'branch': x['branch__name'] or 'Не указан'}
            agent_data[name]['sum'] += float(x['s'] or 0)
            agent_data[name]['count'] += x['c']

        # 2. Сбор по NOMAD
        n_a = nomad_period.values('agent__id', 'agent__first_name', 'agent__last_name', 'branch__name').annotate(s=Sum('total_premium_gross'), c=Count('id'))
        for x in n_a:
            name = f"{x['agent__last_name']} {x['agent__first_name']}".strip() or f"ID {x['agent__id']}"
            if name not in agent_data: 
                agent_data[name] = {'sum': 0, 'count': 0, 'branch': x['branch__name'] or 'Не указан'}
            agent_data[name]['sum'] += float(x['s'] or 0)
            agent_data[name]['count'] += x['c']

        # 3. Сбор по ДЕТЯМ
        s_a = student_period.values('agent__id', 'agent__first_name', 'agent__last_name', 'branch__name').annotate(s=Sum('total_premium_gross'), c=Count('id'))
        for x in s_a:
            name = f"{x['agent__last_name']} {x['agent__first_name']}".strip() or f"ID {x['agent__id']}"
            if name not in agent_data: 
                agent_data[name] = {'sum': 0, 'count': 0, 'branch': x['branch__name'] or 'Не указан'}
            agent_data[name]['sum'] += float(x['s'] or 0)
            agent_data[name]['count'] += x['c']

        # Формируем плоский список агентов напрямую из локального словаря agent_data
        agent_performance_list = []
        for name, values in agent_data.items():
            if values['sum'] > 0:
                agent_performance_list.append({
                    'name': name,
                    'count': values['count'],
                    'total_sum': values['sum'],
                    'branch': values['branch'],
                    'avg_check': values['sum'] / values['count'] if values['count'] > 0 else 0
                })

        # Жесткая сортировка лидеров по убыванию общей суммы сборов
        agent_performance_list = sorted(agent_performance_list, key=lambda x: x['total_sum'], reverse=True)

        # Возвращаем итоговый словарь метрик (убедись, что ключ называется 'agent_performance')
        return {
            'all_time_total_som': all_time_total_som,
            'all_time_total_count': all_time_total_count,
            'all_time_vzr_sum': all_time_vzr_sum,
            'all_time_nomad_sum': all_time_nomad_sum,
            'all_time_student_sum': all_time_student_sum,

            'period_total_som': period_total_som,
            'period_total_count': period_total_count,
            'v_sum': v_sum, 'v_count': agg_vzr['count'] or 0,
            'n_sum': n_sum, 'n_count': agg_nomad['count'] or 0,
            's_sum': s_sum, 's_count': agg_student['count'] or 0,

            'chart_dates': chart_dates,
            'chart_vzr_line': chart_vzr_line,
            'chart_nomad_line': chart_nomad_line,
            'chart_student_line': chart_student_line,

            'branch_labels': branch_labels,
            'branch_values': branch_values,
            'agent_performance': agent_performance_list, # Передается сюда!
        }
PRODUCT_ANALYTICS_MAP = {
    'vzr': AnalyticsManager.get_vzr_metrics,
    'vt': AnalyticsManager.get_vt_metrics,
    'student': AnalyticsManager.get_student_metrics,
}