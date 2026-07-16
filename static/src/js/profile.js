// static/js/pages/profile.js

document.addEventListener('DOMContentLoaded', function() {
    // === Переключение режима редактирования ===
    const editToggle = document.getElementById('profile-edit-toggle');
    const viewMode = document.getElementById('profile-view');
    const editMode = document.getElementById('profile-edit');
    const cancelBtn = document.getElementById('profile-edit-cancel');
    const saveBtn = document.getElementById('profile-edit-save');
    const editForm = document.getElementById('profile-edit-form');
    const container = document.querySelector('.profile-container');

    if (editToggle && viewMode && editMode) {
        editToggle.addEventListener('click', function() {
            viewMode.style.display = 'none';
            editMode.style.display = 'block';
            // Добавляем класс для показа кнопки камеры
            if (container) container.classList.add('profile-edit-active');
        });

        if (cancelBtn) {
            cancelBtn.addEventListener('click', function() {
                editMode.style.display = 'none';
                viewMode.style.display = 'block';
                if (container) container.classList.remove('profile-edit-active');
            });
        }

        if (saveBtn) {
            saveBtn.addEventListener('click', function() {
                editForm.submit();
            });
        }
    }

    // === Загрузка аватара (только через кнопку) ===
    const avatarEditBtn = document.getElementById('profile-avatar-edit');
    const avatarInput = document.getElementById('profile-avatar-input');

    if (avatarEditBtn && avatarInput) {
        avatarEditBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            avatarInput.click();
        });

        avatarInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (!file) return;
            alert('Загрузка аватара: ' + file.name + '\n(Функция будет добавлена позже)');
            avatarInput.value = '';
        });
    }
});