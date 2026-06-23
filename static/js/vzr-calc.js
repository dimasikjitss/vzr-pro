// 1. Инициализация глобальных данных
let vzrTariffs = window.tariffsData || [];
let nomadTariffs = window.nomadTariffsData || []; 
const usdRate = window.usdRate || 0;
const eurRate = window.eurRate || 0;
let currentTab = 'VZR'; // По умолчанию начинаем с ВЗР

// Глобальный объект элементов (используем функции, так как элементы пересоздаются)
const el = {
    h_dob: () => document.getElementById('h_dob'),
    start: () => document.getElementById('start_date'),
    end: () => document.getElementById('end_date'),
    calcBtn: document.getElementById('calc-btn'),
    resetBtn: document.getElementById('reset-btn'),
    // Элементы правой панели (результаты)
    resPrice: document.getElementById('preview-price'),
    resNsp: document.getElementById('preview-nsp'),
    resNetto: document.getElementById('res-netto'),
    resDays: document.getElementById('res-days'),
    resAge: document.getElementById('res-age'),
    resAgeCoeff: document.getElementById('res-age-coeff'),
    resProg: document.getElementById('preview-prog-label'),
    resRate: document.getElementById('res-rate')
};

// 2. Функция переключения вкладок
function switchTab(type) {
    currentTab = type;
    const dynamicBox = document.getElementById('dynamic-fields');
    const vBtn = document.getElementById('tab-vzr');
    const nBtn = document.getElementById('tab-students');

    // Визуальное переключение кнопок
    if (type === 'VZR') {
        vBtn.className = "flex-1 flex items-center justify-center gap-2 py-2.5 bg-white rounded-xl shadow-sm border border-slate-200 text-blue-600";
        nBtn.className = "flex-1 flex items-center justify-center gap-2 py-2.5 text-slate-400";
        
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
        vBtn.className = "flex-1 flex items-center justify-center gap-2 py-2.5 text-slate-400";
        nBtn.className = "flex-1 flex items-center justify-center gap-2 py-2.5 bg-white rounded-xl shadow-sm border border-slate-200 text-blue-600";
        
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
        vBtn.className = "flex-1 flex items-center justify-center gap-2 py-2.5 text-slate-400";
        nBtn.className = "flex-1 flex items-center justify-center gap-2 py-2.5 bg-white rounded-xl shadow-sm border border-slate-200 text-blue-600";
        
        dynamicBox.innerHTML = `
            <div class="col-span-2">
                <label class="input-label">Период покрытия</label>
                <select id="time_type" class="custom-input">
                    <option value="24H">24 часа в сутки</option>
                    <option value="SCHOOL">Только во время учебы</option>
                </select>
            </div>
            <div class="col-span-2">
                <label class="input-label">Занятия в спорт. секциях</label>
                <div class="flex items-center h-12 px-4 bg-slate-50 rounded-xl border border-slate-200">
                    <input type="checkbox" id="is_sports_section" class="w-4 h-4 text-teal-600 rounded border-slate-300 focus:ring-teal-500">
                    <label for="is_sports_section" class="ml-2 text-sm text-slate-600 font-medium select-none">Включая тренировки и соревнования</label>
                </div>
            </div>
            <div class="col-span-4">
                <label class="input-label font-black text-teal-600">Сумма покрытия (СОМ)</label>
                <select id="sum_insured" class="custom-input border-teal-100 bg-teal-50/30 font-black text-teal-700">
                    <option value="" disabled selected hidden>Выберите сумму</option>
                    <option value="50000">50 000 сом</option>
                    <option value="100000">100 000 сом</option>
                    <option value="200000">200 000 сом</option>
                    <option value="300000">300 000 сом</option>
                    <option value="500000">50 0000 сом</option>
                    <option value="1000000">1 000 000 сом</option>
                </select>
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

    if (currentTab === 'VZR') {
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
    } else {
        // Лимиты Номада: от 50к до 2млн
        for (let i = 50000; i <= 2000000; i += 50000) {
            let opt = new Option(i.toLocaleString('ru-RU') + ' СОМ', i);
            if (i === 100000) opt.selected = true;
            sumEl.add(opt);
        }
    }
}

// 4. Основная функция расчета
function runCalculation() {
    const startVal = el.start().value;
    const endVal = el.end().value;
    const dobVal = el.h_dob().value;

    if (!startVal || !endVal) return alert("Укажите даты поездки");
    
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

    if (currentTab === 'VZR') {
        const territoryVal = document.getElementById('territory').value;
        const programVal = document.getElementById('program').value;
        const activityVal = document.getElementById('activity').value;
        const rate = (territoryVal === 'SCHENGEN') ? eurRate : usdRate;
        const actCoeff = activityVal === 'A+' ? 1.25 : activityVal === 'E+' ? 1.75 : activityVal === 'S+' ? 2.0 : 1.0;

        // Возрастные коэффициенты ВЗР
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
            if(el.resRate) el.resRate.innerText = rate.toFixed(2) + (territoryVal === 'SCHENGEN' ? ' EUR' : ' USD');
        }
    } else {
        // Логика НОМАД
        if (age <= 5) ageCoeff = 2.0;
        else if (age <= 13) ageCoeff = 1.8;

        const match = nomadTariffs.find(t => 
            days >= parseInt(t.days_min) && 
            days <= parseInt(t.days_max)
        );

        if (match) {
            const percentRate = parseFloat(match.percent_rate);
            premiumNettoSom = (sumVal * percentRate / 100) * ageCoeff;
            if(el.resRate) el.resRate.innerText = "1.00 (KGS)";
        }
    }

    // Отрисовка результатов
    if (premiumNettoSom > 0) {
        const total = premiumNettoSom * 1.02; // НСП 2%
        const nsp = total - premiumNettoSom;
        const fmt = { minimumFractionDigits: 2, maximumFractionDigits: 2 };

        el.resPrice.innerText = total.toLocaleString('ru-RU', fmt);
        el.resNsp.innerText = nsp.toLocaleString('ru-RU', fmt);
        el.resNetto.innerText = premiumNettoSom.toLocaleString('ru-RU', fmt);
        el.resDays.innerText = days;
        el.resAge.innerText = dobVal ? age + " лет" : "---";
        el.resAgeCoeff.innerText = ageCoeff.toFixed(1);
        el.resProg.innerText = (currentTab === 'VZR' ? 'VZR ' : 'NOMAD ') + sumVal.toLocaleString('ru-RU');
    } else {
        alert("Тариф не найден для периода " + days + " дн.");
    }
}

// 5. Очистка результатов
function resetOutputs() {
    el.resPrice.innerText = "0.00";
    el.resNsp.innerText = "0.00";
    el.resNetto.innerText = "0.00";
    el.resDays.innerText = "0";
    el.resAge.innerText = "---";
    el.resAgeCoeff.innerText = "1.0";
    el.resProg.innerText = "---";
    if(el.resRate) el.resRate.innerText = "0.00";
}

// 6. Слушатели и инициализация
document.addEventListener('DOMContentLoaded', () => {
    switchTab('VZR'); // Стартуем с ВЗР
    
    el.calcBtn.onclick = runCalculation;
    
    el.resetBtn.onclick = () => {
        el.h_dob().value = '';
        el.start().value = '';
        el.end().value = '';
        switchTab(currentTab);
    };
});