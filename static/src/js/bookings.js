// static/src/js/bookings.js

document.addEventListener('DOMContentLoaded', function() {
    // === Переключение вкладок ===
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const target = this.dataset.tab;
            tabButtons.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            this.classList.add('active');
            document.getElementById('tab-' + target).classList.add('active');
        });
    });

    // === Отмена записи ===
    window.cancelBooking = function(bookingId) {
        if (confirm('Вы уверены, что хотите отменить запись?')) {
            fetch('/api/v1/bookings/' + bookingId + '/cancel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
            .then(response => response.json())
            .then(data => {
                alert('Запись отменена');
                location.reload();
            })
            .catch(err => {
                alert('Ошибка при отмене: ' + err.message);
            });
        }
    };
});