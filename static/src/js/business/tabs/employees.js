// static/src/js/business/employees.js

(function() {
    // Переменные для модального окна
    let currentEmployeeId = null;

    // Открытие модалки редактирования
    window.editEmployee = function(id, name, spec, exp) {
        const modal = document.getElementById('addEmployeeModal');
        const title = document.getElementById('employeeModalTitle');
        const form = document.getElementById('employeeForm');
        
        currentEmployeeId = id;
        title.textContent = 'Редактировать мастера';
        document.getElementById('employeeId').value = id;
        document.getElementById('employeeName').value = name;
        document.getElementById('employeeSpec').value = spec;
        document.getElementById('employeeExp').value = exp;
        form.action = '/api/v1/master/' + id + '/update';
        modal.classList.add('active');
    };

    // Сброс формы при открытии модалки "Добавить"
    document.querySelector('[onclick*="addEmployeeModal"]')?.addEventListener('click', function() {
        const form = document.getElementById('employeeForm');
        const modal = document.getElementById('addEmployeeModal');
        const title = document.getElementById('employeeModalTitle');
        title.textContent = 'Добавить мастера';
        form.reset();
        document.getElementById('employeeId').value = '';
        form.action = '/api/v1/master/create-web';
        modal.classList.add('active');
    });

    // Включение/отключение мастера
    window.toggleEmployee = function(id, name, isActive) {
        const action = isActive ? 'отключить' : 'включить';
        if (confirm(`${action.charAt(0).toUpperCase() + action.slice(1)} мастера "${name}"?`)) {
            fetch(`/api/v1/master/${id}/toggle`, { method: 'POST' })
                .then(r => {
                    if (r.ok) location.reload();
                    else alert('Ошибка');
                });
        }
    };

    // Удаление мастера
    window.deleteEmployee = function(id, name) {
        if (confirm(`Удалить мастера "${name}"? Это действие нельзя отменить.`)) {
            fetch(`/api/v1/master/${id}/delete`, { method: 'POST' })
                .then(r => {
                    if (r.ok) location.reload();
                    else alert('Ошибка при удалении');
                });
        }
    };

    // Закрытие модалки по крестику и оверлею
    document.querySelectorAll('.employee-modal-close').forEach(btn => {
        btn.addEventListener('click', function() {
            this.closest('.employee-modal-overlay').classList.remove('active');
        });
    });

    document.querySelectorAll('.employee-modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', function(e) {
            if (e.target === this) {
                this.classList.remove('active');
            }
        });
    });

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            document.querySelectorAll('.employee-modal-overlay.active').forEach(el => el.classList.remove('active'));
        }
    });
})();