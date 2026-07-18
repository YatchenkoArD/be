// static/src/js/profile.js

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

    const avatarEditBtn = document.getElementById('profile-avatar-edit');
    const avatarInput = document.getElementById('profile-avatar-input');

    if (avatarEditBtn && avatarInput) {
        avatarEditBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            avatarInput.click();
        });

        avatarInput.addEventListener('change', async function(e) {
            const file = e.target.files[0];
            if (!file) return;
            // Мгновенное превью + индикатор, пока грузится
            const container = document.getElementById('profile-avatar-container');
            {
                const letter = container.querySelector('.profile-avatar-letter');
                if (letter) letter.remove();
                let img = container.querySelector('img');
                if (!img) { img = document.createElement('img'); container.prepend(img); }
                img.src = URL.createObjectURL(file);
                img.style.opacity = '0.5';
            }
            avatarEditBtn.disabled = true;
            const formData = new FormData();
            formData.append('file', file);
            try {
                const res = await fetch('/api/v1/upload/avatar', { method: 'POST', body: formData });
                const data = await res.json();
                const img = container.querySelector('img');
                if (!res.ok) {
                    if (img) img.remove();
                    alert(data.detail || 'Не удалось загрузить фото');
                    return;
                }
                img.src = data.url + '?t=' + Date.now();
                img.style.opacity = '';
            } catch (err) {
                const img = container.querySelector('img');
                if (img) img.remove();
                alert('Сеть недоступна, попробуйте ещё раз');
            } finally {
                avatarEditBtn.disabled = false;
                avatarInput.value = '';
            }
        });
    }
});