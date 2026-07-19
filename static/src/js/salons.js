// static/src/js/salons.js

document.addEventListener('DOMContentLoaded', function() {
    // Проверяем, что мы на странице салонов
    if (!document.getElementById('searchInput')) {
        return;
    }

    // === Поиск ===
    const searchInput = document.getElementById('searchInput');
    const cards = document.querySelectorAll('.salon-card');

    searchInput.addEventListener('input', function() {
        const query = this.value.toLowerCase().trim();
        cards.forEach(card => {
            const name = card.querySelector('.salon-name')?.textContent.toLowerCase() || '';
            const desc = card.querySelector('.salon-desc')?.textContent.toLowerCase() || '';
            const match = name.includes(query) || desc.includes(query);
            card.style.display = match ? '' : 'none';
        });
    });

    // === Избранное ===
    const favButtons = document.querySelectorAll('.favorite-btn');

    favButtons.forEach(btn => {
        btn.addEventListener('click', async function(e) {
            e.preventDefault();
            const type = this.dataset.type;
            const id = this.dataset.id;
            const isLiked = this.classList.contains('liked');
            const heartIcon = this.dataset.iconHeart;
            const heartFilledIcon = this.dataset.iconHeartFilled;

            try {
                const response = await fetch(`/api/v1/favorites/toggle-${type}/${id}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                });

                if (response.ok) {
                    if (isLiked) {
                        this.classList.remove('liked');
                        this.querySelector('.heart-icon').innerHTML = heartIcon;
                    } else {
                        this.classList.add('liked');
                        this.querySelector('.heart-icon').innerHTML = heartFilledIcon;
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

    // Инициализация состояния избранного
    async function loadFavorites() {
        try {
            const response = await fetch('/api/v1/favorites/my');
            if (response.ok) {
                const data = await response.json();
                document.querySelectorAll('.favorite-btn[data-type="salon"]').forEach(btn => {
                    const id = parseInt(btn.dataset.id);
                    if (data.salon_ids.includes(id)) {
                        btn.classList.add('liked');
                        btn.querySelector('.heart-icon').innerHTML = btn.dataset.iconHeartFilled;
                    } else {
                        btn.classList.remove('liked');
                        btn.querySelector('.heart-icon').innerHTML = btn.dataset.iconHeart;
                    }
                });
            }
        } catch (e) {
            // пользователь не авторизован – ничего не делаем
        }
    }

    loadFavorites();
});