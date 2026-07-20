// static/src/js/favorites.js

document.addEventListener('DOMContentLoaded', function() {
    // Проверяем, что мы на странице избранного
    if (!document.querySelector('.favorites-main')) {
        return;
    }

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
                    // Без хрупких прогулок по DOM: убрали карточку; была
                    // последней — сервер сам нарисует «пусто» при reload.
                    // (Раньше: card.remove() отсоединял узел, closest() по
                    // отсоединённому возвращал null → TypeError улетал в catch
                    // и показывал «Ошибка соединения» при успешном удалении.)
                    if (card) card.remove();
                    if (!document.querySelector('.fav-card')) location.reload();
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