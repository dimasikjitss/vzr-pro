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
