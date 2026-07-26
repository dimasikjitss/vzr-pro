// document.addEventListener('DOMContentLoaded', function() {
//     lucide.createIcons();

//     // Функция получения данных из json_script
//     const getJson = (id) => {
//         const el = document.getElementById(id);
//         if (!el) return [];
//         return JSON.parse(el.textContent);
//     };

//     const dailyValues = getJson('daily-values');
//     const dailyLabels = getJson('daily-labels');

//     // Если данных нет, не рисуем график
//     if (dailyValues.length > 0) {
//         new ApexCharts(document.querySelector("#dailyChart"), {
//             series: [{ name: 'Сборы', data: dailyValues }],
//             chart: { type: 'area', height: 300, toolbar: {show: false} },
//             xaxis: { categories: dailyLabels },
//             colors: ['#2563eb'],
//             stroke: { curve: 'smooth' }
//         }).render();
//     }
    
//     // Повтори такую же логику для regionChart, programChart и т.д.
// });


//     // Общие настройки стиля для всех графиков
//     const commonOptions = {
//         chart: {
//             fontFamily: 'Inter, sans-serif',
//             toolbar: { show: false },
//             zoom: { enabled: false }
//         },
//         colors: ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'],
//         dataLabels: { enabled: false },
//         stroke: { curve: 'smooth', width: 3 },
//         grid: { borderColor: '#f1f5f9' }
//     };

//     // --- 1. ГРАФИК ДИНАМИКИ (Area) ---
//     const dailyChart = new ApexCharts(document.querySelector("#dailyChart"), {
//         ...commonOptions,
//         series: [{ name: 'Сумма сборов', data: getJson('daily-values') }],
//         chart: { ...commonOptions.chart, type: 'area', height: 300 },
//         xaxis: { 
//             categories: getJson('daily-labels'),
//             labels: { style: { colors: '#94a3b8', fontWeight: 700 } }
//         },
//         yaxis: { labels: { style: { colors: '#94a3b8', fontWeight: 700 } } },
//         fill: { type: 'gradient', gradient: { opacityFrom: 0.4, opacityTo: 0 } }
//     });
//     dailyChart.render();

//     // --- 2. ГРАФИК ТЕРРИТОРИЙ (Donut) ---
//     const regionChart = new ApexCharts(document.querySelector("#regionChart"), {
//         ...commonOptions,
//         series: getJson('region-values'),
//         labels: getJson('region-labels'),
//         chart: { ...commonOptions.chart, type: 'donut', height: 320 },
//         legend: { position: 'bottom', fontWeight: 700 },
//         plotOptions: {
//             pie: {
//                 donut: {
//                     size: '75%',
//                     labels: {
//                         show: true,
//                         total: {
//                             show: true,
//                             label: 'ИТОГО',
//                             formatter: w => {
//                                 const sum = w.globals.seriesTotals.reduce((a, b) => a + b, 0);
//                                 return Math.round(sum).toLocaleString() + ' c.';
//                             }
//                         }
//                     }
//                 }
//             }
//         }
//     });
//     regionChart.render();

//     // --- 3. ГРАФИК ПРОГРАММ (Stacked Bar) ---
//     new ApexCharts(document.querySelector("#programChart"), {
//         ...commonOptions,
//         series: getJson('program-series'), // Это твои данные из вью: [{'name': 'ASIA', 'data': [...]}, ...]
//         chart: { ...commonOptions.chart, type: 'bar', height: 300, stacked: true },
//         xaxis: { 
//             categories: getJson('program-labels'), // ['BRONZE', 'SILVER', 'GOLD']
//             labels: { style: { fontWeight: 700 } }
//         },
//         plotOptions: { bar: { borderRadius: 6, columnWidth: '40%' } },
//         legend: { position: 'top', fontWeight: 700 }
//     }).render();

//     // --- 4. МАТРИЦА АГЕНТОВ (Scatter) ---
//     const agentData = getJson('agent-data').map(a => ({
//         x: a.count,
//         y: a.avg_check,
//         name: a.name
//     }));

//     new ApexCharts(document.querySelector("#agentChart"), {
//         ...commonOptions,
//         series: [{ name: 'Эффективность', data: agentData }],
//         chart: { ...commonOptions.chart, type: 'scatter', height: 300 },
//         xaxis: { 
//             title: { text: 'Кол-во полисов', style: { fontWeight: 900 } },
//             labels: { style: { fontWeight: 700 } }
//         },
//         yaxis: { 
//             title: { text: 'Средний чек (сом)', style: { fontWeight: 900 } },
//             labels: { style: { fontWeight: 700 } }
//         },
//         tooltip: {
//             custom: function({series, seriesIndex, dataPointIndex, w}) {
//                 const d = w.globals.initialSeries[seriesIndex].data[dataPointIndex];
//                 return `<div class="p-3 bg-slate-900 text-white rounded-xl shadow-xl border border-slate-700 text-[10px]">
//                     <b class="text-blue-400 block mb-1 text-xs">${d.name}</b>
//                     <div class="flex flex-col gap-1">
//                         <span>Продаж: <b>${d.x}</b></span>
//                         <span>Ср. чек: <b>${Math.round(d.y).toLocaleString()} c.</b></span>
//                     </div>
//                 </div>`;
//             }
//         }
//     }).render();

//     // Фикс для перерисовки графиков при открытии вкладок
//     window.dailyChart = dailyChart;
//     window.regionChart = regionChart;
// });


// document.addEventListener('DOMContentLoaded', function() {
//     // 1. Инициализация иконок интерфейса
//     if (typeof lucide !== 'undefined') { 
//         lucide.createIcons(); 
//     }

//     // 2. Изолированная функция извлечения структурированного JSON из разметки
//     const getJson = (id) => {
//         const el = document.getElementById(id);
//         if (!el) return [];
//         try {
//             return JSON.parse(el.textContent);
//         } catch (e) {
//             console.error("Ошибка десериализации данных для ключа: " + id, e);
//             return [];
//         }
//     };

//     // 3. Базовая конфигурация стилизации графиков ApexCharts
//     const commonOptions = {
//         chart: {
//             fontFamily: 'Inter, sans-serif',
//             toolbar: { show: false },
//             zoom: { enabled: false }
//         },
//         colors: ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'],
//         dataLabels: { enabled: false },
//         stroke: { curve: 'smooth', width: 3 },
//         grid: { borderColor: '#f1f5f9' }
//     };

//     // --- 1. ОТРИСОВКА ГРАФИКА ДИНАМИКИ СБОРОВ (Area) ---
//     const dailyValues = getJson('daily-values');
//     const dailyLabels = getJson('daily-labels');

//     if (dailyValues.length > 0 && document.querySelector("#dailyChart")) {
//         const dailyChart = new ApexCharts(document.querySelector("#dailyChart"), {
//             ...commonOptions,
//             series: [{ name: 'Сумма сборов', data: dailyValues }],
//             chart: { ...commonOptions.chart, type: 'area', height: 260 },
//             xaxis: { 
//                 categories: dailyLabels,
//                 labels: { style: { colors: '#94a3b8', fontWeight: 700, fontSize: '10px' } }
//             },
//             yaxis: { 
//                 labels: { 
//                     style: { colors: '#94a3b8', fontWeight: 700 },
//                     formatter: (val) => Math.round(val).toLocaleString()
//                 } 
//             },
//             fill: { type: 'gradient', gradient: { opacityFrom: 0.4, opacityTo: 0 } },
//             tooltip: { y: { formatter: (val) => Math.round(val).toLocaleString() + " KGS" } }
//         });
//         dailyChart.render();
//     }

//     // --- 2. ОТРИСОВКА ГРАФИКА ПРОГРАММ ПО ТЕРРИТОРИЯМ (Stacked Bar) ---
//     const programSeries = getJson('program-series');
//     const programLabels = getJson('program-labels');

//     if (programSeries.length > 0 && document.querySelector("#programChart")) {
//         new ApexCharts(document.querySelector("#programChart"), {
//             ...commonOptions,
//             series: programSeries,
//             chart: { ...commonOptions.chart, type: 'bar', height: 260, stacked: true },
//             xaxis: { 
//                 categories: programLabels,
//                 labels: { style: { fontWeight: 700, colors: '#64748b', fontSize: '10px' } }
//             },
//             yaxis: {
//                 labels: { formatter: (val) => Math.round(val).toLocaleString() }
//             },
//             plotOptions: { bar: { borderRadius: 6, columnWidth: '45%' } },
//             legend: { position: 'top', fontWeight: 700 },
//             tooltip: { y: { formatter: (val) => Math.round(val).toLocaleString() + " KGS" } }
//         }).render();
//     }

//     // --- 3. ОТРИСОВКА МАТРИЦЫ ЭФФЕКТИВНОСТИ АГЕНТОВ (Scatter) ---
//     const rawAgentData = getJson('agent-data');
    
//     if (rawAgentData.length > 0 && document.querySelector("#agentChart")) {
//         const agentData = rawAgentData.map(a => ({
//             x: a.count,
//             y: a.avg_check,
//             name: a.name
//         }));

//         new ApexCharts(document.querySelector("#agentChart"), {
//             ...commonOptions,
//             series: [{ name: 'Эффективность', data: agentData }],
//             chart: { ...commonOptions.chart, type: 'scatter', height: 260 },
//             xaxis: { 
//                 title: { text: 'Количество проданных полисов', style: { fontWeight: 800, color: '#64748b', fontSize: '11px' } },
//                 labels: { style: { fontWeight: 700 } }
//             },
//             yaxis: { 
//                 title: { text: 'Средний чек (сом)', style: { fontWeight: 800, color: '#64748b', fontSize: '11px' } },
//                 labels: { style: { fontWeight: 700, formatter: (val) => Math.round(val).toLocaleString() } }
//             },
//             tooltip: {
//                 custom: function({series, seriesIndex, dataPointIndex, w}) {
//                     const d = w.globals.initialSeries[seriesIndex].data[dataPointIndex];
//                     return `
//                         <div class="p-3 bg-slate-900 text-white rounded-xl shadow-xl border border-slate-700 text-[11px] font-sans">
//                             <b class="text-blue-400 block mb-1 text-xs uppercase tracking-wide">${d.name}</b>
//                             <div class="flex flex-col gap-1 mt-1.5">
//                                 <span>Бланков оформлено: <b class="text-slate-200">${d.x} шт.</b></span>
//                                 <span>Средний чек продажи: <b class="text-emerald-400">${Math.round(d.y).toLocaleString()} c.</b></span>
//                             </div>
//                         </div>`;
//                 }
//             }
//         }).render();
//     }
// });

document.addEventListener('DOMContentLoaded', function() {
    if (typeof lucide !== 'undefined') { lucide.createIcons(); }

    const getJson = (id) => {
        const el = document.getElementById(id);
        if (!el || !el.textContent.trim()) return [];
        try { 
            let data = JSON.parse(el.textContent);
            if (typeof data === 'string') {
                data = JSON.parse(data);
            }
            return data; 
        } catch (e) { 
            console.error("Ошибка парсинга для ID: " + id, e);
            return []; 
        }
    };

    const activeTab = window.ACTIVE_TAB || 'ALL';

    // Сбор данных для осей трендов
    const dates = getJson('js-dates');
    const vzrData = getJson('js-vzr');
    const nomadData = getJson('js-nomad');
    const studentData = getJson('js-student');
    const branchLabels = getJson('js-branch-labels');
    const branchValues = getJson('js-branch-values');
    const agentData = getJson('js-agent-data');

    const baseOptions = {
        chart: { fontFamily: 'Inter, sans-serif', toolbar: { show: false } },
        grid: { borderColor: '#f1f5f9' },
        dataLabels: { enabled: false }
    };

    // --- 1. ГРАФИК ДИНАМИКИ СБОРОВ ---
    if (document.querySelector("#newDailyChart") && dates.length > 0) {
        let seriesData = [];
        if (activeTab === 'ALL') {
            seriesData = [
                { name: 'ВЗР', data: vzrData, color: '#2563eb' },
                { name: 'NOMAD', data: nomadData, color: '#6366f1' },
                { name: 'ДЕТИ', data: studentData, color: '#14b8a6' }
            ];
        } else if (activeTab === 'VZR') {
            seriesData = [{ name: 'ВЗР', data: vzrData, color: '#2563eb' }];
        } else if (activeTab === 'NOMAD') {
            seriesData = [{ name: 'NOMAD', data: nomadData, color: '#6366f1' }];
        } else if (activeTab === 'STUDENTS') {
            seriesData = [{ name: 'ДЕТИ', data: studentData, color: '#14b8a6' }];
        }

        new ApexCharts(document.querySelector("#newDailyChart"), {
            ...baseOptions,
            chart: { ...baseOptions.chart, type: 'line', height: 280, zoom: { enabled: false } },
            stroke: { curve: 'smooth', width: 3 },
            series: seriesData,
            xaxis: { categories: dates, labels: { style: { colors: '#94a3b8', fontWeight: 700, fontSize: '10px' } } },
            yaxis: { labels: { formatter: (v) => Math.round(v).toLocaleString() } },
            tooltip: { y: { formatter: (v) => Math.round(v).toLocaleString() + " KGS" } }
        }).render();
    }

    // --- 2. ГРАФИК СБОРОВ ФИЛИАЛОВ ---
    if (document.querySelector("#newBranchChart") && branchLabels.length > 0) {
        new ApexCharts(document.querySelector("#newBranchChart"), {
            ...baseOptions,
            chart: { ...baseOptions.chart, type: 'bar', height: 280 },
            plotOptions: { bar: { borderRadius: 6, columnWidth: '40%', distributed: true } },
            colors: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'],
            series: [{ name: 'Общий сбор', data: branchValues }],
            xaxis: { categories: branchLabels, labels: { style: { fontWeight: 700, fontSize: '10px' } } },
            legend: { show: false },
            tooltip: { y: { formatter: (v) => Math.round(v).toLocaleString() + " KGS" } }
        }).render();
    }

    // --- 3. РЕЙТИНГ СТРАХОВЫХ АГЕНТОВ С КУБКАМИ ---
    if (document.querySelector("#newAgentChart") && agentData.length > 0) {
        const sortedAgents = [...agentData].sort((a, b) => b.total_sum - a.total_sum);
        const namesWithPlaces = sortedAgents.map((item, index) => {
            let place = '';
            if (index === 0) place = '🏆 ';
            else if (index === 1) place = '🥈 ';
            else if (index === 2) place = '🥉 ';
            else place = `${index + 1}. `;
            return place + item.name;
        });

        new ApexCharts(document.querySelector("#newAgentChart"), {
            chart: { fontFamily: 'Inter, sans-serif', type: 'bar', height: 340, toolbar: { show: false } },
            plotOptions: { bar: { horizontal: true, borderRadius: 5, barHeight: '55%' } },
            colors: ['#54f5e2'],
            series: [{ name: 'Сумма продаж', data: sortedAgents.map(a => a.total_sum) }],
            xaxis: { categories: namesWithPlaces, labels: { formatter: (v) => Math.round(v).toLocaleString() } },
            yaxis: { labels: { style: { fontWeight: 800, colors: '#1e293b', fontSize: '11px' } } },
            dataLabels: { enabled: false },
            grid: { borderColor: '#f1f5f9' },
            tooltip: {
                custom: function({ dataPointIndex }) {
                    const item = sortedAgents[dataPointIndex];
                    const branchName = item.branch || 'Не указан'; 
                    const avgCheck = item.avg_check || (item.total_sum / item.count);
                    return `
                        <div class="p-3 bg-slate-900 text-white rounded-xl text-xs font-sans shadow-xl border border-slate-700">
                            <b class="text-blue-400 block mb-1 uppercase tracking-wide">${item.name}</b>
                            <div class="flex flex-col gap-0.5 mt-1.5">
                                <div>Филиал: <b class="text-slate-200">${branchName}</b></div>
                                <div>Оформлено полисов: <b class="text-slate-200">${item.count} шт.</b></div>
                                <div>Сумма премий: <b class="text-emerald-400">${Math.round(item.total_sum).toLocaleString()} с.</b></div>
                                <div>Средний чек: <b class="text-emerald-400">${Math.round(avgCheck).toLocaleString()} с.</b></div>
                            </div>
                        </div>`;
                }
            }
        }).render();
    }

    // --- 4. КРУГОВОЙ ПОНЧИК (DONUT) СТРУКТУРЫ ПОРТФЕЛЯ ---
    if (document.querySelector("#productDonutChart")) {
        const vzrSum = Math.round(parseFloat(document.getElementById('js-vzr-sum')?.textContent) || 0);
        const nomadSum = Math.round(parseFloat(document.getElementById('js-nomad-sum')?.textContent) || 0);
        const studentSum = Math.round(parseFloat(document.getElementById('js-student-sum')?.textContent) || 0);
        const totalSum = vzrSum + nomadSum + studentSum;

        new ApexCharts(document.querySelector("#productDonutChart"), {
            chart: { fontFamily: 'Inter, sans-serif', type: 'donut', height: 240 },
            series: [vzrSum, nomadSum, studentSum],
            labels: ['✈️ ВЗР', '🏔️ NOMAD', '🎓 ДЕТИ'],
            colors: ['#2563eb', '#6366f1', '#14b8a6'],
            stroke: { show: true, colors: ['#ffffff'], width: 2 },
            legend: { position: 'bottom', fontSize: '10px', fontWeight: 700, textColor: '#475569' },
            dataLabels: { enabled: totalSum > 0 },
            plotOptions: {
                pie: {
                    donut: {
                        size: '70%',
                        labels: {
                            show: true,
                            name: { show: true, fontSize: '9px', fontWeight: '800', color: '#94a3b8', offsetY: -4, formatter: () => 'СБОРЫ' },
                            value: { show: true, fontSize: '16px', fontWeight: '900', color: '#1e293b', offsetY: 4, formatter: (v) => Math.round(v).toLocaleString() + ' c.' },
                            total: { show: true, fontSize: '9px', fontWeight: '800', color: '#94a3b8', formatter: () => totalSum.toLocaleString() + ' c.' }
                        }
                    }
                }
            },
            tooltip: { y: { formatter: (val) => val.toLocaleString() + ' сом' } }
        }).render();
    }
});