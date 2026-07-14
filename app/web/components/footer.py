# app/web/components/footer.py

def render_footer() -> str:
    return """
    <footer class="comp-footer">
        <div class="section-container footer-bottom-section">
            <div class="footer-links-grid">
                <div>
                    <h3 class="footer-logo">руми<span>.</span></h3>
                    <p class="footer-desc">Запись в салон за 4 клика. Управление салоном — в одном окне.</p>
                </div>
                <div>
                    <h4 class="footer-col-title">Клиентам</h4>
                    <ul class="footer-nav-list">
                        <li><a class="footer-link" href="/salons">Салоны</a></li>
                        <li><a class="footer-link" href="/model">Стать моделью</a></li>
                        <li><a class="footer-link" href="/bookings">Мои записи</a></li>
                        <li><a class="footer-link" href="/favorites">Избранное</a></li>
                    </ul>
                </div>
                <div>
                    <h4 class="footer-col-title">Бизнесу</h4>
                    <ul class="footer-nav-list">
                        <li><a class="footer-link" href="/business">Подключить салон</a></li>
                        <li><a class="footer-link" href="/business/dashboard">Панель салона</a></li>
                    </ul>
                </div>
                <div>
                    <h4 class="footer-col-title">О сервисе</h4>
                    <ul class="footer-nav-list">
                        <li><a class="footer-link" href="/about">Манифест</a></li>
                        <li><a class="footer-link" href="/settings">Настройки</a></li>
                    </ul>
                </div>
            </div>
            <div class="footer-meta footer-meta-flex">
                <span>© 2026 руми. Все права защищены.</span>
                <span>4 клика · 30 секунд · 0 звонков</span>
            </div>
        </div>
    </footer>
    """