# app/web/components/sidebar.py

def render_sidebar(current_page: str = "home") -> str:
    """Боковая панель навигации."""
    nav_items = [
        ("/", "Главная", "home", "🏠"),
        ("/salons", "Салоны", "salons", "🏢"),
    ]
    
    profile_items = [
        ("/profile", "Мой профиль", "👤"),
        ("/bookings", "Мои записи", "📅"),
        ("/favorites", "Избранное", "❤️"),
        ("/settings", "Настройки", "⚙️"),
    ]
    
    business_items = [
        ("/model/dashboard", "Стать моделью", "📸"),
        ("/business/dashboard", "Бизнес", "💼"),
    ]
    
    def render_items(items, current):
        html = ""
        for url, title, page_id, *icon in items:
            icon_str = icon[0] if icon else ""
            active_class = "background: var(--color-accent-light); color: var(--color-heading);" if current == page_id else "color: var(--color-muted);"
            html += f"""
            <a href="{url}" style="display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1rem; border-radius: 0.75rem; font-size: 1rem; font-weight: 500; text-decoration: none; transition: all 0.2s; {active_class}">
                <span>{icon_str}</span>
                <span>{title}</span>
            </a>
            """
        return html
    
    return f"""
    <aside style="position: fixed; right: 0; top: 0; width: 16rem; height: 100vh; background: var(--color-surface); border-left: 1px solid var(--color-border); display: flex; flex-direction: column; z-index: 50;">
        <!-- Логотип -->
        <div style="padding: 1rem 1.25rem; border-bottom: 1px solid var(--color-border);">
            <a href="/" style="font-family: var(--font-heading); font-size: 1.25rem; font-weight: 800; color: var(--color-primary); text-decoration: none;">руми.</a>
        </div>
        
        <!-- Навигация -->
        <nav style="flex: 1; overflow-y: auto; padding: 1rem 0.75rem;">
            <div style="margin-bottom: 0.5rem;">
                {render_items(nav_items, current_page)}
            </div>
            
            <div style="border-top: 1px solid var(--color-border); margin: 1rem 0; padding-top: 1rem;">
                <p style="font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--color-muted); padding: 0 0.75rem; margin-bottom: 0.5rem;">Клиенту</p>
                {render_items(profile_items, current_page)}
            </div>
            
            <div style="border-top: 1px solid var(--color-border); margin: 1rem 0; padding-top: 1rem;">
                {render_items(business_items, current_page)}
            </div>
        </nav>
        
        <!-- Выход -->
        <div style="padding: 1rem 0.75rem; border-top: 1px solid var(--color-border);">
            <button onclick="location.href='/logout'" style="display: flex; align-items: center; gap: 0.75rem; width: 100%; padding: 0.75rem 1rem; border: none; background: transparent; border-radius: 0.75rem; font-size: 1rem; color: var(--color-primary); cursor: pointer; transition: background 0.2s;">
                🚪 Выход
            </button>
        </div>
    </aside>
    """