document.addEventListener('DOMContentLoaded', function() {
    lucide.createIcons();

    // Функция получения данных из json_script
    const getJson = (id) => {
        const el = document.getElementById(id);
        if (!el) return [];
        return JSON.parse(el.textContent);
    };

    const dailyValues = getJson('daily-values');
    const dailyLabels = getJson('daily-labels');

    // Если данных нет, не рисуем график
    if (dailyValues.length > 0) {
        new ApexCharts(document.querySelector("#dailyChart"), {
            series: [{ name: 'Сборы', data: dailyValues }],
            chart: { type: 'area', height: 300, toolbar: {show: false} },
            xaxis: { categories: dailyLabels },
            colors: ['#2563eb'],
            stroke: { curve: 'smooth' }
        }).render();
    }
    
    // Повтори такую же логику для regionChart, programChart и т.д.
});


    // Общие настройки стиля для всех графиков
    const commonOptions = {
        chart: {
            fontFamily: 'Inter, sans-serif',
            toolbar: { show: false },
            zoom: { enabled: false }
        },
        colors: ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'],
        dataLabels: { enabled: false },
        stroke: { curve: 'smooth', width: 3 },
        grid: { borderColor: '#f1f5f9' }
    };

    // --- 1. ГРАФИК ДИНАМИКИ (Area) ---
    const dailyChart = new ApexCharts(document.querySelector("#dailyChart"), {
        ...commonOptions,
        series: [{ name: 'Сумма сборов', data: getJson('daily-values') }],
        chart: { ...commonOptions.chart, type: 'area', height: 300 },
        xaxis: { 
            categories: getJson('daily-labels'),
            labels: { style: { colors: '#94a3b8', fontWeight: 700 } }
        },
        yaxis: { labels: { style: { colors: '#94a3b8', fontWeight: 700 } } },
        fill: { type: 'gradient', gradient: { opacityFrom: 0.4, opacityTo: 0 } }
    });
    dailyChart.render();

    // --- 2. ГРАФИК ТЕРРИТОРИЙ (Donut) ---
    const regionChart = new ApexCharts(document.querySelector("#regionChart"), {
        ...commonOptions,
        series: getJson('region-values'),
        labels: getJson('region-labels'),
        chart: { ...commonOptions.chart, type: 'donut', height: 320 },
        legend: { position: 'bottom', fontWeight: 700 },
        plotOptions: {
            pie: {
                donut: {
                    size: '75%',
                    labels: {
                        show: true,
                        total: {
                            show: true,
                            label: 'ИТОГО',
                            formatter: w => {
                                const sum = w.globals.seriesTotals.reduce((a, b) => a + b, 0);
                                return Math.round(sum).toLocaleString() + ' c.';
                            }
                        }
                    }
                }
            }
        }
    });
    regionChart.render();

    // --- 3. ГРАФИК ПРОГРАММ (Stacked Bar) ---
    new ApexCharts(document.querySelector("#programChart"), {
        ...commonOptions,
        series: getJson('program-series'), // Это твои данные из вью: [{'name': 'ASIA', 'data': [...]}, ...]
        chart: { ...commonOptions.chart, type: 'bar', height: 300, stacked: true },
        xaxis: { 
            categories: getJson('program-labels'), // ['BRONZE', 'SILVER', 'GOLD']
            labels: { style: { fontWeight: 700 } }
        },
        plotOptions: { bar: { borderRadius: 6, columnWidth: '40%' } },
        legend: { position: 'top', fontWeight: 700 }
    }).render();

    // --- 4. МАТРИЦА АГЕНТОВ (Scatter) ---
    const agentData = getJson('agent-data').map(a => ({
        x: a.count,
        y: a.avg_check,
        name: a.name
    }));

    new ApexCharts(document.querySelector("#agentChart"), {
        ...commonOptions,
        series: [{ name: 'Эффективность', data: agentData }],
        chart: { ...commonOptions.chart, type: 'scatter', height: 300 },
        xaxis: { 
            title: { text: 'Кол-во полисов', style: { fontWeight: 900 } },
            labels: { style: { fontWeight: 700 } }
        },
        yaxis: { 
            title: { text: 'Средний чек (сом)', style: { fontWeight: 900 } },
            labels: { style: { fontWeight: 700 } }
        },
        tooltip: {
            custom: function({series, seriesIndex, dataPointIndex, w}) {
                const d = w.globals.initialSeries[seriesIndex].data[dataPointIndex];
                return `<div class="p-3 bg-slate-900 text-white rounded-xl shadow-xl border border-slate-700 text-[10px]">
                    <b class="text-blue-400 block mb-1 text-xs">${d.name}</b>
                    <div class="flex flex-col gap-1">
                        <span>Продаж: <b>${d.x}</b></span>
                        <span>Ср. чек: <b>${Math.round(d.y).toLocaleString()} c.</b></span>
                    </div>
                </div>`;
            }
        }
    }).render();

    // Фикс для перерисовки графиков при открытии вкладок
    window.dailyChart = dailyChart;
    window.regionChart = regionChart;
});