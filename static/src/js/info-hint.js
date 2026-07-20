// static/src/js/info-hint.js
// Всплывающие подсказки (значок ⓘ, .info-hint) — рендерятся в <body> через
// position:fixed, чтобы не обрезались контейнерами с overflow-x:auto
// (таблицы, карточки заявок и т.п.). Один общий элемент на всю страницу,
// координаты пересчитываются при каждом наведении/фокусе.
(function () {
    let tooltipEl = null;

    function ensureTooltip() {
        if (!tooltipEl) {
            tooltipEl = document.createElement('div');
            tooltipEl.className = 'info-hint-tooltip';
            document.body.appendChild(tooltipEl);
        }
        return tooltipEl;
    }

    function showTooltip(icon) {
        const text = icon.getAttribute('data-tooltip');
        if (!text) return;

        const tip = ensureTooltip();
        tip.textContent = text;
        tip.classList.remove('is-visible');
        tip.style.left = '0px';
        tip.style.top = '0px';

        const iconRect = icon.getBoundingClientRect();
        const tipRect = tip.getBoundingClientRect();

        let left = iconRect.left + iconRect.width / 2 - tipRect.width / 2;
        left = Math.max(8, Math.min(left, window.innerWidth - tipRect.width - 8));

        let top = iconRect.top - tipRect.height - 8;
        if (top < 8) {
            top = iconRect.bottom + 8; // не влезает сверху — показываем снизу
        }

        tip.style.left = left + 'px';
        tip.style.top = top + 'px';
        tip.classList.add('is-visible');
    }

    function hideTooltip() {
        if (tooltipEl) tooltipEl.classList.remove('is-visible');
    }

    document.addEventListener('mouseover', function (e) {
        const icon = e.target.closest('.info-hint');
        if (icon) showTooltip(icon);
    });
    document.addEventListener('mouseout', function (e) {
        const icon = e.target.closest('.info-hint');
        if (icon) hideTooltip();
    });
    document.addEventListener('focusin', function (e) {
        const icon = e.target.closest('.info-hint');
        if (icon) showTooltip(icon);
    });
    document.addEventListener('focusout', function (e) {
        const icon = e.target.closest('.info-hint');
        if (icon) hideTooltip();
    });
    // Подсказка привязана к координатам конкретного показа — при скролле/ресайзе
    // просто прячем, а не пересчитываем на лету.
    window.addEventListener('scroll', hideTooltip, true);
    window.addEventListener('resize', hideTooltip);
})();
