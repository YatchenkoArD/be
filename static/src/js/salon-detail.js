// staticsrc/js/salon-detail.js

document.addEventListener('DOMContentLoaded', function() {
    let selectedMasterId = null;
    let selectedServiceId = null;
    let selectedSlot = null;

    // ===== ИЗБРАННОЕ (салон и мастера) =====
    async function loadFavorites() {
        try {
            const response = await fetch('/api/v1/favorites/my');
            if (response.ok) {
                const data = await response.json();
                
                // Салоны
                document.querySelectorAll('.salon-top-fav[data-type="salon"]').forEach(btn => {
                    const id = parseInt(btn.dataset.id);
                    if (data.salon_ids.includes(id)) {
                        btn.classList.add('liked');
                    } else {
                        btn.classList.remove('liked');
                    }
                });
                
                // Мастера
                document.querySelectorAll('.master-fav[data-type="master"]').forEach(btn => {
                    const id = parseInt(btn.dataset.id);
                    if (data.master_ids.includes(id)) {
                        btn.classList.add('liked');
                    } else {
                        btn.classList.remove('liked');
                    }
                });
            }
        } catch (e) {
            // пользователь не авторизован
        }
    }

    document.querySelectorAll('.salon-top-fav, .master-fav').forEach(btn => {
        btn.addEventListener('click', async function(e) {
            e.preventDefault();
            e.stopPropagation();
            const type = this.dataset.type;
            const id = this.dataset.id;
            const isLiked = this.classList.contains('liked');

            try {
                const response = await fetch(`/api/v1/favorites/toggle-${type}/${id}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                });
                if (response.ok) {
                    if (isLiked) {
                        this.classList.remove('liked');
                    } else {
                        this.classList.add('liked');
                    }
                } else if (response.status === 302) {
                    window.location.href = '/login?redirect=' + encodeURIComponent(window.location.pathname);
                } else {
                    alert('Не удалось изменить избранное. Попробуйте позже.');
                }
            } catch (err) {
                console.error(err);
                alert('Ошибка соединения.');
            }
        });
    });

    loadFavorites();

    // ===== ПЕРЕКЛЮЧЕНИЕ МЕЖДУ СПИСКОМ И ДЕТАЛЬНЫМ ВИДОМ =====
    const mastersList = document.getElementById('masters-list-container');
    const masterDetails = document.querySelectorAll('.master-detail');

    document.querySelectorAll('.master-card').forEach(card => {
        card.addEventListener('click', () => {
            const masterId = card.dataset.masterId;
            showMasterDetail(masterId);
        });
    });

    document.querySelectorAll('.master-book-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            showMasterDetail(btn.dataset.masterId);
        });
    });

    function showMasterDetail(masterId) {
        mastersList.style.display = 'none';
        masterDetails.forEach(d => d.classList.add('hidden'));
        const detail = document.querySelector(`.master-detail[data-master-id="${masterId}"]`);
        if (detail) detail.classList.remove('hidden');
        selectedMasterId = masterId;
    }

    // Назад к мастерам
    document.querySelectorAll('.back-to-masters').forEach(btn => {
        btn.addEventListener('click', () => {
            mastersList.style.display = 'block';
            masterDetails.forEach(d => d.classList.add('hidden'));
        });
    });

    // ===== ВЫБОР УСЛУГИ =====
    document.querySelectorAll('.service-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.service-btn').forEach(b => b.classList.remove('selected'));
            this.classList.add('selected');

            selectedServiceId = this.dataset.serviceId;
            const masterId = this.dataset.masterId;
            const serviceName = this.dataset.serviceName;
            const price = this.dataset.price;

            const slotsContainer = document.getElementById(`detail-slots-${masterId}`);
            const titleEl = document.getElementById(`detail-slots-title-${masterId}`);
            const gridEl = document.getElementById(`detail-slot-grid-${masterId}`);

            if (slotsContainer && titleEl && gridEl) {
                titleEl.innerHTML = `
                    📅 Время для «${serviceName}» (${price} ₽)
                    <input type="date" id="date-${masterId}" value="${new Date().toISOString().split('T')[0]}" style="margin-top:8px;">
                `;
                slotsContainer.classList.remove('hidden');
                loadSlots(masterId, selectedServiceId, serviceName, price);
            }
        });
    });

    async function loadSlots(masterId, serviceId, serviceName, price) {
        const dateInput = document.getElementById(`date-${masterId}`);
        const grid = document.getElementById(`detail-slot-grid-${masterId}`);
        
        if (!dateInput || !grid) return;

        grid.innerHTML = '<p style="color:#888; grid-column:1/-1;">Загрузка слотов...</p>';

        try {
            const res = await fetch(`/api/v1/bookings/available/${masterId}?date=${dateInput.value}&service_id=${serviceId}`);
            const data = await res.json();

            grid.innerHTML = '';
            if (data.slots && data.slots.length) {
                data.slots.forEach(slot => {
                    const btn = document.createElement('button');
                    btn.className = 'slot-btn';
                    btn.textContent = new Date(slot).toLocaleTimeString('ru-RU', {hour:'2-digit', minute:'2-digit'});
                    btn.dataset.fullslot = slot;
                    btn.dataset.master = masterId;
                    btn.dataset.service = serviceId;
                    btn.dataset.name = serviceName;
                    btn.dataset.price = price;
                    grid.appendChild(btn);
                });
            } else {
                grid.innerHTML = '<p style="color:#888; grid-column:1/-1;">Нет свободных окон</p>';
            }
        } catch (e) {
            grid.innerHTML = '<p style="color:red; grid-column:1/-1;">Ошибка загрузки</p>';
        }
    }

    // ===== ВЫБОР СЛОТА =====
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('slot-btn')) {
            document.querySelectorAll('.slot-btn').forEach(b => b.classList.remove('selected'));
            e.target.classList.add('selected');

            selectedSlot = e.target.dataset.fullslot;

            const panel = document.getElementById('bookPanel');
            document.getElementById('panelMaster').textContent = `${e.target.dataset.name} · ${e.target.dataset.price} ₽`;
            document.getElementById('panelTime').textContent = selectedSlot.replace('T', ' ');
            panel.classList.remove('hidden');
        }
    });

    // ===== ПОДТВЕРЖДЕНИЕ ЗАПИСИ =====
    window.confirmBooking = function() {
        if (!selectedSlot || !selectedMasterId || !selectedServiceId) {
            alert('Выберите время!');
            return;
        }
        window.location.href = `/book?master_id=${selectedMasterId}&service_id=${selectedServiceId}&time=${encodeURIComponent(selectedSlot)}`;
    };

    // Закрытие панели при клике на фон (опционально)
    document.getElementById('bookPanel').addEventListener('click', function(e) {
        if (e.target.id === 'bookPanel') this.classList.add('hidden');
    });
});