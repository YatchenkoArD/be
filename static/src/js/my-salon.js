// static/src/js/pages/my-salon.js

(function() {
    // === Мастера ===
    window.editMaster = function(id, name, spec, exp) {
        document.getElementById('editMasterId').value = id;
        document.getElementById('editMasterName').value = name;
        document.getElementById('editMasterSpec').value = spec;
        document.getElementById('editMasterExp').value = exp;
        document.getElementById('editMasterForm').action = '/api/v1/master/' + id + '/update';
        document.getElementById('editMasterModal').classList.add('active');
    };

    window.deleteMaster = function(id, name) {
        if (confirm('Удалить мастера "' + name + '"? Это действие нельзя отменить.')) {
            fetch('/api/v1/master/' + id + '/delete', { method: 'POST' })
                .then(r => { if (r.ok) location.reload(); else alert('Ошибка при удалении'); });
        }
    };

    // === Акции ===
    window.deletePromo = function(id, title) {
        if (confirm('Удалить акцию "' + title + '"? Это действие нельзя отменить.')) {
            fetch('/api/v1/business/my-salon/promotions/' + id + '/delete', { method: 'POST' })
                .then(r => { if (r.ok) location.reload(); else alert('Ошибка при удалении'); });
        }
    };

    // === Часы работы ===
    const WH_DAY_KEYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'];

    window.toggleDayClosed = function(day, isClosed) {
        document.getElementById('wh-start-' + day).disabled = isClosed;
        document.getElementById('wh-end-' + day).disabled = isClosed;
    };

    window.copyMondayToWeekdays = function() {
        const start = document.getElementById('wh-start-mon').value;
        const end = document.getElementById('wh-end-mon').value;
        const mondayClosed = document.querySelector('.wh-closed[data-day="mon"]').checked;
        ['tue', 'wed', 'thu', 'fri'].forEach(day => {
            document.querySelector(`.wh-closed[data-day="${day}"]`).checked = mondayClosed;
            document.getElementById('wh-start-' + day).value = start;
            document.getElementById('wh-end-' + day).value = end;
            toggleDayClosed(day, mondayClosed);
        });
    };

    window.saveWorkingHours = async function(salonId) {
        const hours = {};
        for (const day of WH_DAY_KEYS) {
            const closed = document.querySelector(`.wh-closed[data-day="${day}"]`).checked;
            if (closed) {
                hours[day] = 'closed';
            } else {
                const start = document.getElementById('wh-start-' + day).value;
                const end = document.getElementById('wh-end-' + day).value;
                if (!start || !end) { alert('Укажите время начала и конца для рабочего дня'); return; }
                hours[day] = start + '-' + end;
            }
        }
        try {
            const res = await fetch(`/api/v1/business/my-salon?salon_id=${salonId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ working_hours: JSON.stringify(hours) })
            });
            if (res.ok) { alert('Часы работы сохранены'); location.reload(); }
            else { const d = await res.json(); alert(d.detail || 'Ошибка'); }
        } catch (e) { alert('Ошибка сети'); }
    };

    // === Лояльность ===
    window.saveLoyaltySettings = async function(salonId) {
        const body = {
            regular_client_discount_percent: parseInt(document.getElementById('loyaltyRegularPercent').value) || 0,
            regular_client_visits_threshold: document.getElementById('loyaltyVisitsThreshold').value
                ? parseInt(document.getElementById('loyaltyVisitsThreshold').value) : null,
            bonus_accrual_percent: parseFloat(document.getElementById('loyaltyBonusAccrual').value) || 0,
        };
        try {
            const res = await fetch(`/api/v1/loyalty/salon/${salonId}/settings`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            if (res.ok) { alert('Настройки лояльности сохранены'); }
            else { const d = await res.json(); alert(d.detail || 'Ошибка'); }
        } catch (e) { alert('Ошибка сети'); }
    };

    window.addLoyaltyOffer = async function(salonId) {
        const title = document.getElementById('loyaltyOfferTitle').value.trim();
        const discount_percent = parseInt(document.getElementById('loyaltyOfferPercent').value);
        const promo_code = document.getElementById('loyaltyOfferCode').value.trim() || null;
        if (!title || !discount_percent) { alert('Заполните название и размер скидки'); return; }
        try {
            const res = await fetch(`/api/v1/loyalty/salon/${salonId}/offers`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, discount_percent, promo_code })
            });
            if (res.ok) { location.reload(); }
            else { const d = await res.json(); alert(d.detail || 'Ошибка'); }
        } catch (e) { alert('Ошибка сети'); }
    };

    window.deleteLoyaltyOffer = function(id, title) {
        if (!confirm(`Удалить скидку «${title}»?`)) return;
        const salonId = window.salonId;
        fetch(`/api/v1/loyalty/salon/${salonId}/offers/${id}`, { method: 'DELETE' })
            .then(r => { if (r.ok) location.reload(); else r.json().then(d => alert(d.detail || 'Ошибка')); });
    };

    // === Фото: drag & drop ===
    const dropZone = document.getElementById('photoDropZone');
    const fileInput = document.getElementById('photoFileInput');
    const statusDiv = document.getElementById('photoUploadStatus');

    if (dropZone && fileInput) {
        dropZone.addEventListener('click', () => fileInput.click());

        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.style.borderColor = 'var(--color-primary)';
            dropZone.style.background = 'var(--color-surface-alt)';
        });

        dropZone.addEventListener('dragleave', () => {
            dropZone.style.borderColor = '';
            dropZone.style.background = '';
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.style.borderColor = '';
            dropZone.style.background = '';
            if (e.dataTransfer.files.length) {
                uploadPhotos(e.dataTransfer.files);
            }
        });

        fileInput.addEventListener('change', () => {
            if (fileInput.files.length) {
                uploadPhotos(fileInput.files);
                fileInput.value = '';
            }
        });
    }

    async function uploadPhotos(files) {
        const url = dropZone.dataset.uploadUrl;
        statusDiv.innerHTML = '<p style="color:var(--color-muted)">Загрузка...</p>';
        const formData = new FormData();
        for (const file of files) {
            formData.append('files', file);
        }
        try {
            const res = await fetch(url, { method: 'POST', body: formData });
            if (res.ok) {
                statusDiv.innerHTML = '<p style="color:#22c55e">Фото загружены</p>';
                location.reload();
            } else {
                const d = await res.json();
                statusDiv.innerHTML = `<p style="color:#ef4444">Ошибка: ${d.detail || 'Неизвестная ошибка'}</p>`;
            }
        } catch (e) {
            statusDiv.innerHTML = '<p style="color:#ef4444">Ошибка сети</p>';
        }
    }

    // === Модалки ===
    document.querySelectorAll('.my-salon-modal-close').forEach(btn => {
        btn.addEventListener('click', function() {
            this.closest('.my-salon-modal-overlay').classList.remove('active');
        });
    });

    document.querySelectorAll('.my-salon-modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', function(e) {
            if (e.target === this) {
                this.classList.remove('active');
            }
        });
    });

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            document.querySelectorAll('.my-salon-modal-overlay.active').forEach(el => el.classList.remove('active'));
        }
    });
})();