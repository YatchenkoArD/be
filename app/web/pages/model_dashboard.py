# app/web/pages/model_dashboard.py
from app.web.components.header import render_header
from app.web.components.footer import render_footer
from app.web.components.sidebar import render_sidebar
from app.web.components.styles import get_base_styles


def render_model_dashboard(user=None) -> str:
    """Дашборд модели — личный кабинет после подписки."""
    
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Дашборд модели — руми</title>
    {get_base_styles()}
    <style>
        .dash-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        @media (max-width: 768px) {{
            .dash-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}
        .stat-card {{
            background: var(--color-surface);
            border: 1px solid var(--color-border);
            border-radius: 1rem;
            padding: 1.25rem;
            text-align: center;
        }}
        .stat-value {{
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--color-primary);
        }}
        .stat-label {{
            font-size: 0.75rem;
            color: var(--color-muted);
            margin-top: 0.25rem;
        }}
        .invite-card {{
            background: var(--color-surface);
            border: 1px solid var(--color-border);
            border-radius: 1rem;
            padding: 1.25rem;
            margin-bottom: 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .invite-card:hover {{
            border-color: var(--color-primary);
        }}
        .status-badge {{
            padding: 0.25rem 0.75rem;
            border-radius: 1rem;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        .status-new {{
            background: #fef3c7;
            color: #92400e;
        }}
        .status-accepted {{
            background: #d1fae5;
            color: #065f46;
        }}
        .tier-badge {{
            display: inline-block;
            padding: 0.35rem 1rem;
            border-radius: 2rem;
            font-size: 0.8rem;
            font-weight: 700;
            color: white;
            background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
            margin-bottom: 1rem;
        }}
        .progress-bar {{
            height: 0.5rem;
            background: var(--color-border);
            border-radius: 1rem;
            overflow: hidden;
            margin-top: 0.5rem;
        }}
        .progress-fill {{
            height: 100%;
            border-radius: 1rem;
            background: linear-gradient(90deg, var(--color-primary), var(--color-accent));
        }}
    </style>
</head>
<body>
    {render_header("model")}
    {render_sidebar("model", user)}
    
    <main style="margin-right: 16rem; padding-top: 2rem;">
        <div class="section-container">
            <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:2rem">
                <div>
                    <h1 class="text-display" style="font-size:2rem">Мой дашборд</h1>
                    <p class="text-muted">Добро пожаловать, модель!</p>
                </div>
                <span class="tier-badge">Про · 990 ₽/мес</span>
            </div>
            
            <!-- Статистика -->
            <div class="dash-grid">
                <div class="stat-card">
                    <div class="stat-value">5</div>
                    <div class="stat-label">Записей в этом месяце</div>
                    <div class="progress-bar"><div class="progress-fill" style="width:100%"></div></div>
                    <p style="font-size:0.65rem;color:var(--color-muted);margin-top:0.25rem">Лимит: 5/5</p>
                </div>
                <div class="stat-card">
                    <div class="stat-value">50%</div>
                    <div class="stat-label">Средняя скидка</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">12 500</div>
                    <div class="stat-label">₽ сэкономлено</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">4.8</div>
                    <div class="stat-label">Ваш рейтинг</div>
                </div>
            </div>
            
            <!-- Приглашения от салонов -->
            <h2 class="text-subtitle" style="font-size:1.25rem;margin-bottom:1rem">📩 Приглашения от салонов</h2>
            
            <div class="invite-card">
                <div>
                    <h3 style="font-weight:600">Брутальный</h3>
                    <p style="font-size:0.85rem;color:var(--color-muted)">Ищем модель на стрижку + борода · 15 мая</p>
                </div>
                <div>
                    <span class="status-badge status-new">Новое</span>
                    <button class="btn-primary" style="margin-left:0.75rem;font-size:0.8rem;padding:0.4rem 1rem">Принять</button>
                </div>
            </div>
            
            <div class="invite-card">
                <div>
                    <h3 style="font-weight:600">Имидж</h3>
                    <p style="font-size:0.85rem;color:var(--color-muted)">Окрашивание Bob — ищем модель · 18 мая</p>
                </div>
                <div>
                    <span class="status-badge status-new">Новое</span>
                    <button class="btn-primary" style="margin-left:0.75rem;font-size:0.8rem;padding:0.4rem 1rem">Принять</button>
                </div>
            </div>
            
            <div class="invite-card">
                <div>
                    <h3 style="font-weight:600">Гламур</h3>
                    <p style="font-size:0.85rem;color:var(--color-muted)">Наращивание ногтей · 10 мая</p>
                </div>
                <div>
                    <span class="status-badge status-accepted">Принято</span>
                </div>
            </div>
            
            <!-- История -->
            <h2 class="text-subtitle" style="font-size:1.25rem;margin:2rem 0 1rem">📋 История визитов</h2>
            
            <div class="card" style="margin-bottom:0.75rem">
                <div style="display:flex;justify-content:space-between">
                    <div>
                        <strong>Стрижка + борода</strong>
                        <p style="font-size:0.85rem;color:var(--color-muted)">Брутальный · Александр Петров</p>
                    </div>
                    <div style="text-align:right">
                        <span style="color:green;font-weight:600">Завершено</span>
                        <p style="font-size:0.8rem;color:var(--color-muted)">8 мая 2026</p>
                    </div>
                </div>
            </div>
            
            <div class="card" style="margin-bottom:0.75rem">
                <div style="display:flex;justify-content:space-between">
                    <div>
                        <strong>Окрашивание</strong>
                        <p style="font-size:0.85rem;color:var(--color-muted)">Имидж · Елена Смирнова</p>
                    </div>
                    <div style="text-align:right">
                        <span style="color:green;font-weight:600">Завершено</span>
                        <p style="font-size:0.8rem;color:var(--color-muted)">2 мая 2026</p>
                    </div>
                </div>
            </div>
        </div>
        {render_footer(user)}
    </main>
</body>
</html>"""
    
    return html