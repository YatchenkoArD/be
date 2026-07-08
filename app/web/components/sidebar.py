# app/web/components/sidebar.py

def render_sidebar(current_page: str = "home", user=None) -> str:
    def is_active(page: str) -> str:
        return "active" if current_page == page else ""

    icons = {
        "home": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-house" aria-hidden="true"><path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"></path><path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path></svg>',
        "salons": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-building2" aria-hidden="true"><path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"></path><path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2"></path><path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"></path><path d="M10 6h4"></path><path d="M10 10h4"></path><path d="M10 14h4"></path><path d="M10 18h4"></path></svg>',
        "business": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-briefcase" aria-hidden="true"><path d="M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path><rect width="20" height="14" x="2" y="6" rx="2"></rect></svg>',
        "offer": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-gift" aria-hidden="true"><path d="M20 12v10H4V12"></path><path d="M2 7h20v5H2z"></path><path d="M12 22V7"></path><path d="M12 7h7.5a2.5 2.5 0 0 0 0-5h-5A2.5 2.5 0 0 0 12 4a2.5 2.5 0 0 0-2.5-2.5h-5a2.5 2.5 0 0 0 0 5H12z"></path></svg>',
        "manifest": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-file-text" aria-hidden="true"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"></path><path d="M14 2v4a2 2 0 0 0 2 2h4"></path><path d="M10 9H8"></path><path d="M16 13H8"></path><path d="M16 17H8"></path></svg>',
        "user": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-user" aria-hidden="true"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>',
    }

    return f"""
    <!-- Оверлей для затемнения -->
    <div class="sidebar-overlay" id="sidebar-overlay"></div>

    <!-- Сайдбар -->
    <aside class="sidebar-container" id="sidebar">
        <div class="sidebar-inner">
            <div class="sidebar-header" style="justify-content: flex-start; border-bottom: none; padding-bottom: 0.5rem;">
                <a class="sidebar-link" href="/login" style="font-weight: 600; color: var(--color-primary);">
                    {icons["user"]} Войти
                </a>
            </div>

            <nav class="sidebar-nav">
                <div class="space-y-1">
                    <a class="sidebar-link {is_active('home')}" href="/">
                        {icons["home"]} Главная
                    </a>
                    <a class="sidebar-link {is_active('salons')}" href="/salons">
                        {icons["salons"]} Салоны
                    </a>
                    <a class="sidebar-link {is_active('business')}" href="/business">
                        {icons["business"]} Для бизнеса
                    </a>
                    <a class="sidebar-link {is_active('offer')}" href="/offer">
                        {icons["offer"]} Предложение
                    </a>
                    <a class="sidebar-link {is_active('manifest')}" href="/about">
                        {icons["manifest"]} Манифест
                    </a>
                </div>
            </nav>
        </div>
    </aside>
    """