// static/js/vzr-calc.js

let serverTariffs = [];

// Элементы
const el = {
    insuredList: document.getElementById('insured-list'),
    addSelfBtn: document.getElementById('add-self'),
    addOtherBtn: document.getElementById('add-other'),
    territory: document.getElementById('territory'),
    program: document.getElementById('program'),
    sum: document.getElementById('sum_insured'),
    activity: document.getElementById('activity'),
    rateInput: document.getElementById('rate-input'),
    submitBtn: document.getElementById('submit-btn'),
    currencyDisplay: document.getElementById('currency-display'),
    startDate: document.getElementById('start_date'),
    endDate: document.getElementById('end_date'),
    previewBtn: document.getElementById('preview-btn'),
    policyForm: document.getElementById('policy-form')
};

// Константы из скрытых полей или window
const usdRateDb = parseFloat(document.getElementById('db-usd-rate').value) || 0;
const eurRateDb = parseFloat(document.getElementById('db-eur-rate').value) || 0;

// ВАЛИДАЦИЯ
function setupValidation(input, type) {
    if (!input) return;
    input.addEventListener('input', function() {
        if (type === 'latin') {
            this.value = this.value.replace(/[^A-Za-z\s\-]/g, '');
        } else if (type === 'passport') {
            this.value = this.value.substring(0, 9).toUpperCase();
        }
    });
}

// ЗАГРУЗКА ТАРИФОВ
fetch('/api/tariffs/')
    .then(res => res.json())
    .then(data => {
        serverTariffs = data;
        updateUI();
    });

// ДОБАВЛЕНИЕ КАРТОЧКИ
function addCard(name = '', dob = '', passport = '') {
    if (el.insuredList.children.length >= 3) return;
    
    // Проверка на дубликат паспорта
    if (passport && Array.from(el.insuredList.querySelectorAll('.i-passport')).some(i => i.value === passport)) return;

    const template = document.getElementById('person-template');
    const clone = template.content.cloneNode(true);
    
    const nameInp = clone.querySelector('.i-name');
    const passInp = clone.querySelector('.i-passport');
    const dobInp = clone.querySelector('.i-dob');
    
    nameInp.value = name;
    dobInp.value = dob;
    passInp.value = passport;

    setupValidation(nameInp, 'latin');
    setupValidation(passInp, 'passport');

    // Скрываем "Для себя", если добавили страхователя
    const holderPassport = document.getElementById('h_passport').value.trim();
    if (passport && passport === holderPassport) el.addSelfBtn.classList.add('hidden-btn');

    el.insuredList.appendChild(clone);
    lucide.createIcons();
    calculate();
}

function updateUI() {
    const territory = el.territory.value;
    const program = el.program.value;
    
    if (!territory) {
        el.currencyDisplay.innerText = "---";
        el.sum.innerHTML = '<option value="" disabled selected hidden>Выберите направление</option>';
        return;
    }

    const isEuro = (territory === 'SCHENGEN');
    const currency = isEuro ? 'EUR' : 'USD';
    el.currencyDisplay.innerText = currency;
    el.rateInput.value = isEuro ? eurRateDb : usdRateDb;
    
    document.getElementById('hidden-currency').value = currency;

    if (!program) {
        el.sum.innerHTML = '<option value="" disabled selected hidden>Выберите программу</option>';
    } else {
        el.sum.innerHTML = '<option value="" disabled selected hidden>Выберите сумму</option>';
        let sums = [];

        if (program === 'BRONZE') {
            if (territory === 'ASIA') sums = [15000, 30000];
            else if (territory === 'SCHENGEN') sums = [30000, 50000];
            else if (territory === 'WORLD') sums = [30000];
        } else {
            sums = [30000, 50000]; // SILVER & GOLD
        }

        sums.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s; 
            opt.innerText = s.toLocaleString() + ' ' + currency;
            el.sum.appendChild(opt);
        });

        if (sums.length === 1) el.sum.value = sums[0];
    }
    calculate();
}

function calculate() {
    const startStr = el.startDate.value;
    const endStr = el.endDate.value;
    const start = new Date(startStr);
    const end = new Date(endStr);
    const rate = parseFloat(el.rateInput.value) || 0;
    const territory = el.territory.value;
    const program = el.program.value;
    const sumLimit = parseInt(el.sum.value);
    const selectedOption = el.activity.options[el.activity.selectedIndex];
    const actCoeff = selectedOption && selectedOption.value ? parseFloat(selectedOption.getAttribute('data-coeff')) : 1.0;
    
    const cards = el.insuredList.querySelectorAll('.insured-card');
    const datesValid = startStr && endStr && !isNaN(start) && !isNaN(end) && end >= start;
    
    // Валидация для кнопки оформления
    const phonesValid = document.getElementById('phone-input').value.length === 13 && 
                         document.getElementById('h_relative').value.length === 13;
    const passValid = document.getElementById('h_passport').value.length === 9;
    const innValid = document.getElementById('h_inn').value.length === 14;

    el.submitBtn.disabled = !(datesValid && cards.length > 0 && sumLimit && phonesValid && passValid && innValid);
    
    const days = datesValid ? Math.ceil(Math.abs(end - start) / (1000 * 60 * 60 * 24)) + 1 : 0;
    document.getElementById('calc-days').innerText = days;
    
    let totalSom = 0;
    const infoBox = document.getElementById('premium-info-main');
    infoBox.innerHTML = '';
    
    cards.forEach((card, idx) => {
        const dobVal = card.querySelector('.i-dob').value;
        let ageCoeff = 1.0;
        if (dobVal) {
            const age = new Date().getFullYear() - new Date(dobVal).getFullYear();
            if (age < 5) ageCoeff = 2.0; else if (age >= 65) ageCoeff = 2.5;
        }
        const match = serverTariffs.find(t => t.program === program && t.territory === territory && t.sum_insured === sumLimit && days >= t.days_min && days <= t.days_max);
        const baseRate = match ? parseFloat(match.rate) : 0;
        const personPremium = baseRate * days * ageCoeff * actCoeff;
        const personSom = personPremium * rate * 1.02;
        
        card.querySelector('.person-sum').value = sumLimit || '';
        card.querySelector('.person-premium').value = personPremium.toFixed(2);
        card.querySelector('.person-calc-info').innerText = personPremium > 0 ? `${personPremium.toFixed(2)} ${el.currencyDisplay.innerText} (~${personSom.toFixed(1)} сом)` : '';
        
        totalSom += personSom;
        if (personPremium > 0) {
            infoBox.innerHTML += `<div class="flex justify-between uppercase tracking-tighter text-white/60"><span>#${idx+1} Участник:</span> <span class="text-white">${personPremium.toFixed(2)}</span></div>`;
        }
    });
    document.getElementById('calc-total').innerText = totalSom.toLocaleString('ru-RU', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

function initPhoneMask(selector) {
    document.querySelectorAll(selector).forEach(input => {
        input.addEventListener('focus', function() { if (!this.value) this.value = '+996'; });
        input.addEventListener('blur', function() { if (this.value === '+996') this.value = ''; });
        input.addEventListener('input', function() {
            let val = this.value;
            if (!val.startsWith('+996')) {
                let digits = val.replace(/\D/g, '');
                if (digits.startsWith('996')) digits = digits.substring(3);
                this.value = '+996' + digits;
            }
            this.value = this.value.substring(0, 13);
        });
    });
}

// Инициализация событий
document.addEventListener('DOMContentLoaded', () => {
    lucide.createIcons();
    initPhoneMask('.phone-field');
    
    const today = new Date().toISOString().split('T')[0];
    el.startDate.setAttribute('min', today);

    setupValidation(document.getElementById('h_name'), 'latin');
    setupValidation(document.getElementById('h_passport'), 'passport');

    el.addSelfBtn.addEventListener('click', () => {
        const n = document.getElementById('h_name').value.trim();
        const d = document.getElementById('h_dob').value;
        const p = document.getElementById('h_passport').value.trim();
        if(!n || !d || p.length < 9) return alert("Заполните данные страхователя");
        addCard(n, d, p);
    });

    el.addOtherBtn.addEventListener('click', () => addCard());

    el.insuredList.addEventListener('click', (e) => {
        if(e.target.closest('.remove-person')) {
            const card = e.target.closest('.insured-card');
            if (card.querySelector('.i-passport').value === document.getElementById('h_passport').value) el.addSelfBtn.classList.remove('hidden-btn');
            card.remove();
            calculate();
        }
    });

    el.startDate.addEventListener('change', function() {
        if (this.value) {
            el.endDate.setAttribute('min', this.value);
            if (el.endDate.value && el.endDate.value < this.value) el.endDate.value = this.value;
        }
        calculate();
    });

    [el.rateInput, el.territory, el.program, el.sum, el.activity, el.endDate].forEach(element => {
        element.addEventListener('change', () => {
            if (element === el.territory || element === el.program) updateUI();
            else calculate();
        });
    });

    el.policyForm.addEventListener('input', calculate);

    // ПЕЧАТЬ ЧЕРНОВИКА
    el.previewBtn.addEventListener('click', function() {
        const previewUrl = this.getAttribute('data-url');
        const originalAction = el.policyForm.action;
        const originalTarget = el.policyForm.target;

        el.policyForm.action = previewUrl;
        el.policyForm.target = "_blank";
        el.policyForm.submit();

        setTimeout(() => {
            el.policyForm.action = originalAction;
            el.policyForm.target = originalTarget;
        }, 100);
    });
});

function downloadPDF(policyNumber, holderName) {
    const elements = document.querySelectorAll('.page');
    const container = document.createElement('div');
    
    elements.forEach(el => {
        const clone = el.cloneNode(true);
        clone.style.margin = "0"; 
        clone.style.boxShadow = "none";
        clone.style.height = "296.5mm"; 
        clone.style.maxHeight = "296.5mm";
        clone.style.overflow = "hidden";
        clone.style.position = "relative";
        container.appendChild(clone);
    });

    let fileName = 'Policy';
    if (policyNumber && !policyNumber.includes('ПРОЕКТ') && !policyNumber.includes('DRAFT')) {
        fileName = `Policy_${policyNumber}`;
    } else if (holderName) {
        const nameSlug = holderName.trim().split(' ')[0] || 'Draft';
        fileName = `Draft_${nameSlug}`;
    }

    const opt = {
        margin: 0,
        filename: `${fileName}.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true, logging: false },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
        // ДОБАВЬТЕ ЭТОТ ПАРАМЕТР:
        pagebreak: { mode: ['avoid-all', 'css', 'legacy'] } 
    };

    html2pdf().set(opt).from(container).save();
}


