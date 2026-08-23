// ==========================================
// КАЛЬКУЛЯТОР СТРАХОВАНИЯ (ИЗОЛИРОВАННЫЙ)
// ==========================================

// 1. Инициализация глобальных данных
let vzrTariffs = window.tariffsData || [];
let nomadTariffs = window.nomadTariffsData || []; 
let kidsTariffs = window.kidsTariffsData || []; 
const usdRate = window.usdRate || 0;
const eurRate = window.eurRate || 0;
let currentCalcTab = 'VZR'; // Локальное состояние для калькулятора

// Селекторы элементов калькулятора
const calcEl = {
    h_dob: () => document.getElementById('h_dob'),
    start: () => document.getElementById('start_date'),
    end: () => document.getElementById('end_date'),
    calcBtn: document.getElementById('calc-btn'),
    resetBtn: document.getElementById('reset-btn'),
    resPrice: document.getElementById('preview-price'),
    resNsp: document.getElementById('preview-nsp'),
    resNetto: document.getElementById('res-netto'),
    resDays: document.getElementById('res-days'),
    resAge: document.getElementById('res-age'),
    resAgeCoeff: document.getElementById('res-age-coeff'),
    resProg: document.getElementById('preview-prog-label'),
    resRate: document.getElementById('res-rate')
};

// 2. Функция переключения вкладок КАЛЬКУЛЯТОРА
function switchCalcTab(type) {
    currentCalcTab = type;
    const dynamicBox = document.getElementById('dynamic-fields');
    if (!dynamicBox) return;

    // Уникальные ID кнопок калькулятора
    const vBtn = document.getElementById('calc-tab-vzr');
    const nBtn = document.getElementById('calc-tab-nomad');
    const kBtn = document.getElementById('calc-tab-students');

    const activeClass = "flex-1 flex items-center justify-center gap-2 py-2.5 bg-white rounded-xl shadow-sm border border-slate-200 text-blue-600 font-bold cursor-pointer transition-all";
    const inactiveClass = "flex-1 flex items-center justify-center gap-2 py-2.5 text-slate-400 hover:text-slate-600 font-medium cursor-pointer transition-all";

    if (vBtn) vBtn.className = (type === 'VZR') ? activeClass : inactiveClass;
    if (nBtn) nBtn.className = (type === 'NOMAD') ? activeClass : inactiveClass;
    if (kBtn) kBtn.className = (type === 'STUDENTS') ? activeClass : inactiveClass;

    if (type === 'VZR') {
        dynamicBox.innerHTML = `
            <div>
                <label class="input-label">Территория</label>
                <select id="territory" onchange="updateSumOptions()" class="custom-input">
                    <option value="ASIA">Азия, СНГ, Африка</option>
                    <option value="SCHENGEN">Шенген и Европа</option>
                    <option value="WORLD">Северная и Южная Америка, Юго-Восточная Азия, Мальдивы</option>
                </select>
            </div>
            <div>
                <label class="input-label">Программа</label>
                <select id="program" onchange="updateSumOptions()" class="custom-input">
                    <option value="BRONZE">BRONZE</option>
                    <option value="SILVER">SILVER</option>
                    <option value="GOLD">GOLD</option>
                </select>
            </div>
            <div class="col-span-2">
                <label class="input-label">Сумма покрытия (Лимит)</label>
                <select id="sum_insured" class="custom-input"></select>
            </div>
            <div class="col-span-2">
                <label class="input-label">Тип покрытия (Активность)</label>
                <select id="activity" class="custom-input">
                    <option value="NONE">Стандарт (1.0)</option>
                    <option value="A+">Активный отдых (1.25)</option>
                    <option value="E+">Экстремальный туризм (1.75)</option>
                    <option value="S+">Спорт и соревнования (2.0)</option>
                </select>
            </div>
        `;
    } else if (type === 'NOMAD') {
        dynamicBox.innerHTML = `
            <div class="col-span-2">
                <label class="input-label">Программа</label>
                <select id="program" class="custom-input">
                    <option value="BRONZE">GSO NOMAD BRONZE</option>
                </select>
            </div>
            <div class="col-span-2">
                <label class="input-label font-black text-blue-600">Сумма покрытия (СОМ)</label>
                <select id="sum_insured" class="custom-input border-blue-100 bg-blue-50/30 font-black text-blue-700"></select>
            </div>
        `;
    } else if (type === 'STUDENTS') {
        dynamicBox.innerHTML = `
            <div class="col-span-2">
                <label class="input-label">Период покрытия</label>
                <select id="time_type" class="custom-input">
                    <option value="24H">24 часа в сутки</option>
                    <option value="12H">12 часов (07:00 - 19:00)</option>
                </select>
            </div>
            <div class="col-span-2">
                <label class="input-label">Занятия в спорт. секциях</label>
                <div class="flex items-center h-12 px-4 bg-slate-50 rounded-xl border border-slate-200">
                    <input type="checkbox" id="is_sports_section" class="w-4 h-4 text-teal-600 rounded border-slate-300 focus:ring-teal-500">
                    <label for="is_sports_section" class="ml-2 text-sm text-slate-600 font-medium select-none cursor-pointer">Включая тренировки и соревнования</label>
                </div>
            </div>
            <div class="col-span-4">
                <label class="input-label font-black text-teal-600">Сумма покрытия (СОМ)</label>
                <select id="sum_insured" class="custom-input border-teal-100 bg-teal-50/30 font-black text-teal-700"></select>
            </div>
        `;
    }
    
    updateSumOptions();
    if (window.lucide) lucide.createIcons();
    resetOutputs();
}

// 3. Динамическое обновление списка сумм
function updateSumOptions() {
    const sumEl = document.getElementById('sum_insured');
    if (!sumEl) return;
    sumEl.innerHTML = '';

    if (currentCalcTab === 'VZR') {
        const territory = document.getElementById('territory').value;
        const program = document.getElementById('program').value;
        const currency = (territory === 'SCHENGEN') ? 'EUR' : 'USD';
        
        let sums = [...new Set(vzrTariffs
            .filter(t => t.program === program && t.territory === territory)
            .map(t => parseInt(t.sum_insured))
        )].sort((a, b) => a - b);

        sums.forEach(s => {
            let opt = new Option(s.toLocaleString('ru-RU') + ' ' + currency, s);
            sumEl.add(opt);
        });
    } else if (currentCalcTab === 'NOMAD') {
        for (let i = 50000; i <= 2000000; i += 50000) {
            let opt = new Option(i.toLocaleString('ru-RU') + ' СОМ', i);
            if (i === 100000) opt.selected = true;
            sumEl.add(opt);
        }
    } else if (currentCalcTab === 'STUDENTS') {
        for (let i = 50000; i <= 1000000; i += 50000) {
            let opt = new Option(i.toLocaleString('ru-RU') + ' СОМ', i);
            if (i === 100000) opt.selected = true;
            sumEl.add(opt);
        }
    }
}

// 4. Основная функция расчета
function runCalculation() {
    const startVal = calcEl.start() ? calcEl.start().value : '';
    const endVal = calcEl.end() ? calcEl.end().value : '';
    const dobVal = calcEl.h_dob() ? calcEl.h_dob().value : '';

    if (!startVal || !endVal) return alert("Укажите даты поездки/страхования");
    
    const startDate = new Date(startVal);
    const endDate = new Date(endVal);
    if (endDate < startDate) return alert("Дата окончания не может быть раньше начала");

    const days = Math.ceil(Math.abs(endDate - startDate) / (1000 * 60 * 60 * 24)) + 1;
    const sumVal = parseInt(document.getElementById('sum_insured').value);

    let age = 0, ageCoeff = 1.0;
    if (dobVal) {
        const birthDate = new Date(dobVal);
        const today = new Date();
        age = today.getFullYear() - birthDate.getFullYear();
        const m = today.getMonth() - birthDate.getMonth();
        if (m < 0 || (m === 0 && today.getDate() < birthDate.getDate())) age--;
    }

    let premiumNettoSom = 0;

    if (currentCalcTab === 'VZR') {
        const territoryVal = document.getElementById('territory').value;
        const programVal = document.getElementById('program').value;
        const activityVal = document.getElementById('activity').value;
        const rate = (territoryVal === 'SCHENGEN') ? eurRate : usdRate;
        const actCoeff = activityVal === 'A+' ? 1.25 : activityVal === 'E+' ? 1.75 : activityVal === 'S+' ? 2.0 : 1.0;

        if (age < 5) ageCoeff = 2.0;
        else if (age >= 65) ageCoeff = 2.5;

        const match = vzrTariffs.find(t => 
            t.program === programVal && 
            t.territory === territoryVal && 
            parseInt(t.sum_insured) === sumVal && 
            days >= parseInt(t.days_min) && 
            days <= parseInt(t.days_max)
        );

        if (match) {
            premiumNettoSom = parseFloat(match.rate) * days * ageCoeff * actCoeff * rate;
            if(calcEl.resRate) calcEl.resRate.innerText = rate.toFixed(2) + (territoryVal === 'SCHENGEN' ? ' EUR' : ' USD');
        }
    } else if (currentCalcTab === 'NOMAD') {
        if (age <= 5) ageCoeff = 2.0;
        else if (age <= 13) ageCoeff = 1.8;

        const match = nomadTariffs.find(t => 
            days >= parseInt(t.days_min) && 
            days <= parseInt(t.days_max)
        );

        if (match) {
            const percentRate = parseFloat(match.percent_rate);
            premiumNettoSom = (sumVal * percentRate / 100) * ageCoeff;
            if(calcEl.resRate) calcEl.resRate.innerText = "1.00 (KGS)";
        }
    } else if (currentCalcTab === 'STUDENTS') {
        const timeType = document.getElementById('time_type').value;
        const isSports = document.getElementById('is_sports_section').checked;

        const formData = new FormData();
        formData.append('time_type', timeType);
        formData.append('sum_insured', sumVal);
        formData.append('is_sports_section', isSports ? 'true' : 'false');
        formData.append('start_date', startVal);
        formData.append('end_date', endVal);
        formData.append('birth_dates[]', dobVal); 

        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

        fetch('/student/calculate/', {
            method: 'POST',
            headers: { 'X-CSRFToken': csrfToken },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const fmt = { minimumFractionDigits: 2, maximumFractionDigits: 2 };
                calcEl.resPrice.innerText = parseFloat(data.gross).toLocaleString('ru-RU', fmt);
                calcEl.resNsp.innerText = parseFloat(data.nsp).toLocaleString('ru-RU', fmt);
                calcEl.resNetto.innerText = parseFloat(data.netto).toLocaleString('ru-RU', fmt);
                calcEl.resDays.innerText = data.days_count;
                calcEl.resAge.innerText = data.student_age + " лет";
                calcEl.resAgeCoeff.innerText = "1.0";
                calcEl.resProg.innerText = data.program_name + ' ' + sumVal.toLocaleString('ru-RU');
                if(calcEl.resRate) calcEl.resRate.innerText = "1.00";
            } else {
                alert(data.error || "Ошибка при расчете тарифа");
            }
        })
        .catch(err => {
            console.error(err);
            alert("Ошибка соединения с сервером при расчете");
        });
        
        return;
    }

    // Отрисовка результатов
    if (premiumNettoSom > 0) {
        const total = premiumNettoSom * 1.02;
        const nsp = total - premiumNettoSom;
        const fmt = { minimumFractionDigits: 2, maximumFractionDigits: 2 };

        if(calcEl.resPrice) calcEl.resPrice.innerText = total.toLocaleString('ru-RU', fmt);
        if(calcEl.resNsp) calcEl.resNsp.innerText = nsp.toLocaleString('ru-RU', fmt);
        if(calcEl.resNetto) calcEl.resNetto.innerText = premiumNettoSom.toLocaleString('ru-RU', fmt);
        if(calcEl.resDays) calcEl.resDays.innerText = days;
        if(calcEl.resAge) calcEl.resAge.innerText = dobVal ? age + " лет" : "---";
        if(calcEl.resAgeCoeff) calcEl.resAgeCoeff.innerText = ageCoeff.toFixed(1);
        if(calcEl.resProg) calcEl.resProg.innerText = (currentCalcTab === 'STUDENTS' ? 'ДЕТИ ' : currentCalcTab + ' ') + sumVal.toLocaleString('ru-RU');
    } else {
        alert("Тариф не найден для выбранных параметров.");
    }
}

// 5. Очистка результатов
function resetOutputs() {
    if(calcEl.resPrice) calcEl.resPrice.innerText = "0.00";
    if(calcEl.resNsp) calcEl.resNsp.innerText = "0.00";
    if(calcEl.resNetto) calcEl.resNetto.innerText = "0.00";
    if(calcEl.resDays) calcEl.resDays.innerText = "0";
    if(calcEl.resAge) calcEl.resAge.innerText = "---";
    if(calcEl.resAgeCoeff) calcEl.resAgeCoeff.innerText = "1.0";
    if(calcEl.resProg) calcEl.resProg.innerText = "---";
    if(calcEl.resRate) calcEl.resRate.innerText = "0.00";
}

// 6. Слушатели и инициализация
document.addEventListener('DOMContentLoaded', () => {
    switchCalcTab('VZR'); 
    
    if(calcEl.calcBtn) calcEl.calcBtn.onclick = runCalculation;
    
    if(calcEl.resetBtn) {
        calcEl.resetBtn.onclick = () => {
            if(calcEl.h_dob()) calcEl.h_dob().value = '';
            if(calcEl.start()) calcEl.start().value = '';
            if(calcEl.end()) calcEl.end().value = '';
            switchCalcTab(currentCalcTab);
        };
    }
});

let currentJournalProduct = 'vzr';
let loadedJournalData = [];

// Функция переключения продукта в журнале
window.switchProduct = function(product) {
    currentJournalProduct = product;

    // 1. Подсветка табов
    const jTabs = {
        'vzr': document.getElementById('jtab-vzr'),
        'vt': document.getElementById('jtab-vt'),
        'student': document.getElementById('jtab-student')
    };

    const jActiveClass = "journal-btn flex-1 flex items-center justify-center gap-1.5 py-1.5 bg-white rounded-lg shadow-sm border border-slate-200/60 text-blue-600 font-bold cursor-pointer";
    const jInactiveClass = "journal-btn flex-1 flex items-center justify-center gap-1.5 py-1.5 text-slate-400 hover:text-slate-600 transition-all cursor-pointer";

    Object.keys(jTabs).forEach(key => {
        if (jTabs[key]) jTabs[key].className = (key === product) ? jActiveClass : jInactiveClass;
    });

    // 2. Запрос за полисами
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    
    // За текущий месяц
    const dateFrom = `${year}-${month}-01`;
    const dateTo = `${year}-${month}-${day}`;

    fetch(`/api/analytics/?product=${product}&date_from=${dateFrom}&date_to=${dateTo}`)
        .then(res => {
            if (!res.ok) throw new Error(`HTTP error ${res.status}`);
            return res.json();
        })
        .then(data => {
            loadedJournalData = data.recent_policies || [];
            renderJournalTable(loadedJournalData);
        })
        .catch(err => console.error("Ошибка загрузки журнала:", err));
};

