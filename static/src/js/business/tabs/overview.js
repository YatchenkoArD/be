// static/src/js/business/overview.js

(function() {
    // Получаем данные, переданные из Python
    const weekOperations = window.weekOperations || [];
    const days = window.days || [];

    // Глобальные функции для вызова из HTML
    window.showDayDetails = function(index, dayName, revenue, prevRevenue) {
        const ops = weekOperations[index] || [];
        const overlay = document.getElementById('dayDetailsOverlay');
        const sheet = document.getElementById('dayDetailsModal');
        const title = document.getElementById('modalDayTitle');
        const summary = document.getElementById('modalDaySummary');
        const container = document.getElementById('modalDayOperations');

        if (!overlay || !sheet) return;

        title.textContent = `Операции за ${dayName}`;
        const totalOps = ops.length;
        const paidCount = ops.filter(o => o.status === 'completed').length;
        summary.textContent = `${totalOps} операций • ${revenue.toLocaleString()} ₽ • Оплачено: ${paidCount}/${totalOps}`;

        container.innerHTML = '';
        if (totalOps === 0) {
            container.innerHTML = '<p class="text-muted">Нет операций за этот день</p>';
        } else {
            ops.forEach(op => {
                const time = new Date(op.start_time).toLocaleTimeString('ru-RU', {hour:'2-digit', minute:'2-digit'});
                const price = (op.final_price || op.service.price).toLocaleString();
                const statusLabel = op.status === 'completed' ? '✓' : '○';
                const statusClass = op.status === 'completed' ? 'status-paid' : 'status-waiting';
                const initials = op.client.full_name ? op.client.full_name.split(' ').map(n => n[0]).join('') : 'К';
                const method = op.payment_method || 'Карта';

                const item = document.createElement('div');
                item.className = 'booking-item';
                item.innerHTML = `
                    <div class="avatar">${initials}</div>
                    <div class="info">
                        <div class="name">${op.client.full_name || op.client.phone}</div>
                        <div class="desc">
                            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:middle"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                            ${time} • ${op.service.name}
                        </div>
                    </div>
                    <div class="price">${price} ₽</div>
                    <div style="display:flex;align-items:center;gap:0.5rem;flex-shrink:0">
                        <span style="font-size:0.7rem;color:var(--color-muted)">${method}</span>
                        <span class="status ${statusClass}">${statusLabel}</span>
                    </div>
                `;
                container.appendChild(item);
            });
        }

        overlay.classList.add('active');
        sheet.classList.add('active');
        document.body.style.overflow = 'hidden';
    };

    window.closeDayDetails = function() {
        const overlay = document.getElementById('dayDetailsOverlay');
        const sheet = document.getElementById('dayDetailsModal');
        if (overlay) overlay.classList.remove('active');
        if (sheet) sheet.classList.remove('active');
        document.body.style.overflow = '';
    };

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            window.closeDayDetails();
        }
    });
})();