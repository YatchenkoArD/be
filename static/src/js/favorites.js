// static/src/js/favorites.js

document.addEventListener('DOMContentLoaded', function() {
    const removeButtons = document.querySelectorAll('.fav-remove-btn');

    removeButtons.forEach(btn => {
        btn.addEventListener('click', async function(e) {
            e.preventDefault();
            const type = this.dataset.type;
            const id = this.dataset.id;
            const card = this.closest('.fav-card');

            if (!confirm(`Убрать ${type === 'salon' ? 'салон' : 'мастера'} из избранного?`)) {
                return;
            }

            try {
                const response = await fetch(`/api/v1/favorites/toggle-${type}/${id}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                });

                if (response.ok) {
                    if (card) {
                        card.remove();
                        // Проверяем, остались ли карточки в секции
                        const section = card.closest('.fav-section');
                        const remaining = section.querySelectorAll('.fav-card');
                        if (remaining.length === 0) {
                            const emptyState = section.querySelector('.empty-state');
                            if (emptyState) emptyState.style.display = 'block';
                        }
                    } else {
                        location.reload();
                    }
                } else if (response.status === 302) {
                    window.location.href = '/login?redirect=' + encodeURIComponent(window.location.pathname);
                } else {
                    alert('Не удалось удалить из избранного. Попробуйте позже.');
                }
            } catch (err) {
                console.error(err);
                alert('Ошибка соединения.');
            }
        });
    });
});