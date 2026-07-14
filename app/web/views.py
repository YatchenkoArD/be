# app/web/views.py
import html
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.models import Salon, User, Master, Service as ServiceModel
from app.web.pages.home import render_home_page
from app.web.pages.login import render_login_page         
from app.web.pages.register import render_register_page
from app.web.pages.model_landing import render_model_landing_page
from app.web.pages.model_checkout import render_model_checkout_page   
from app.web.pages.about import render_about_page
from app.web.pages.business_landing import render_business_landing_page
from app.web.components.header import render_header
from app.web.components.footer import render_footer
from app.web.components.styles import get_base_styles
from app.web.components.sidebar import render_sidebar
from app.web.auth import get_current_user_from_cookie


router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Главная страница."""
    user = await get_current_user_from_cookie(request, db)
    html = await render_home_page(db, user)
    return HTMLResponse(content=html)


@router.get("/salons", response_class=HTMLResponse)
async def salons_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Страница со списком салонов."""
    user = await get_current_user_from_cookie(request, db)
    from app.web.pages.salons import render_salons_page
    html = await render_salons_page(db, user)
    return HTMLResponse(content=html)


@router.get("/salons/{salon_id}", response_class=HTMLResponse)
async def salon_detail_page(salon_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """Страница конкретного салона."""
    user = await get_current_user_from_cookie(request, db)
    from app.web.pages.salon_detail import render_salon_detail
    html = await render_salon_detail(db, salon_id, user)
    return HTMLResponse(content=html)


@router.get("/masters/{master_id}", response_class=HTMLResponse)
async def master_detail_page(master_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """Страница конкретного мастера."""
    user = await get_current_user_from_cookie(request, db)
    from app.web.pages.master_detail import render_master_detail
    html = await render_master_detail(db, master_id, user)
    return HTMLResponse(content=html)


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Страница профиля."""
    from app.web.pages.profile import render_profile_page
    
    user = await get_current_user_from_cookie(request, db)
    return HTMLResponse(content=render_profile_page(user))


@router.get("/bookings", response_class=HTMLResponse)
async def bookings_page(
    request: Request, 
    db: AsyncSession = Depends(get_db)
):
    """Страница 'Мои записи'."""
    from app.web.pages.bookings import render_bookings_page
    
    user = await get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login?redirect=/bookings", status_code=302)
    
    return HTMLResponse(content=await render_bookings_page(db, user))


@router.get("/favorites", response_class=HTMLResponse)
async def favorites_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Страница 'Избранное'."""
    user = await get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login?redirect=/favorites", status_code=302)
    from app.web.pages.favorites import render_favorites_page
    return HTMLResponse(content=await render_favorites_page(db, user))

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Страница настроек."""
    from app.web.pages.settings import render_settings_page
    user = await get_current_user_from_cookie(request, db)
    return HTMLResponse(content=render_settings_page(user))


@router.get("/business", response_class=HTMLResponse)
async def business_landing_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Страница «Для бизнеса» (лендинг)."""
    user = await get_current_user_from_cookie(request, db)
    return HTMLResponse(content=render_business_landing_page(user))


@router.get("/business/dashboard", response_class=HTMLResponse)
async def business_dashboard_page(
    request: Request, 
    db: AsyncSession = Depends(get_db)
):
    """Бизнес-панель с аналитикой."""
    from app.web.pages.business import render_business_dashboard
    
    user = await get_current_user_from_cookie(request, db)
    if not user or user.role.value != "business":
        return RedirectResponse(url="/login?redirect=/business/dashboard", status_code=302)
    
    result = await db.execute(select(Salon).where(Salon.owner_id == user.id))
    salon = result.scalar_one_or_none()
    
    if not salon:
        return RedirectResponse(url="/business/register-salon", status_code=302)
    
    return HTMLResponse(content=await render_business_dashboard(db, user, salon))


@router.get("/business/register-salon", response_class=HTMLResponse)
async def register_salon_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Анкета регистрации салона. Маршрут потерялся при редизайне, хотя
    страница и редиректы на неё остались — возвращаем."""
    from app.web.pages.register_salon import render_register_salon_page

    user = await get_current_user_from_cookie(request, db)
    if not user or user.role.value != "business":
        return RedirectResponse(url="/login?redirect=/business/register-salon", status_code=302)
    return HTMLResponse(content=render_register_salon_page(user))


@router.get("/business/my-salon", response_class=HTMLResponse)
async def my_salon_page(
    request: Request, 
    db: AsyncSession = Depends(get_db)
):
    """Страница редактирования своего салона."""
    from app.web.pages.my_salon import render_my_salon_page
    
    user = await get_current_user_from_cookie(request, db)
    if not user or user.role.value != "business":
        return RedirectResponse(url="/login?redirect=/business/my-salon", status_code=302)
    
    # Получаем салон владельца
    result = await db.execute(select(Salon).where(Salon.owner_id == user.id))
    salon = result.scalar_one_or_none()
    
    if not salon:
        return RedirectResponse(url="/business/register-salon", status_code=302)
    
    return HTMLResponse(content=await render_my_salon_page(db, salon, user))


@router.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Админ-панель (только роль ADMIN)."""
    from app.web.pages.admin_panel import render_admin_panel

    user = await get_current_user_from_cookie(request, db)
    if not user or user.role.value != "admin" or not user.is_active:
        return RedirectResponse(url="/login?redirect=/admin", status_code=302)

    return HTMLResponse(content=await render_admin_panel(db, user, request.query_params))


@router.get("/business/checkout", response_class=HTMLResponse)
async def business_checkout_page(request: Request, db: AsyncSession = Depends(get_db)):
    plan = request.query_params.get("plan", "business")
    user = await get_current_user_from_cookie(request, db)
    from app.web.pages.business_checkout import render_business_checkout_page
    return HTMLResponse(content=render_business_checkout_page(plan, user))


@router.get("/salons/{salon_id}/book", response_class=HTMLResponse)
async def book_service_page(salon_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """Страница записи в салон."""
    user = await get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url=f"/login?redirect=/salons/{salon_id}/book", status_code=302)
    
    # Получаем салон
    result = await db.execute(select(Salon).where(Salon.id == salon_id))
    salon = result.scalar_one_or_none()
    if not salon:
        return HTMLResponse(content="<h1>Салон не найден</h1>", status_code=404)
    
    # Получаем мастеров с услугами
    masters_result = await db.execute(select(Master).where(Master.salon_id == salon_id, Master.is_active == True))
    masters = masters_result.scalars().all()
    
    masters_options = ""
    for m in masters:
        user_res = await db.execute(select(User).where(User.id == m.user_id))
        master_user = user_res.scalar_one_or_none()
        name = master_user.full_name if master_user else "Мастер"
        masters_options += f'<option value="{m.id}">{name} — {m.specialization}</option>'
    
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Запись — {salon.name} — руми</title>
    {get_base_styles()}
</head>
<body>
    {render_header("salons")}
    <div class="section-container" style="padding-top:2rem;max-width:500px;margin:0 auto">
        <h1 class="text-display" style="font-size:1.75rem;margin-bottom:0.5rem">Запись в {salon.name}</h1>
        <p class="text-muted" style="margin-bottom:2rem">Выберите мастера и услугу</p>
        <form action="/api/v1/bookings" method="post">
            <input type="hidden" name="salon_id" value="{salon_id}">
            <div style="margin-bottom:1rem">
                <label style="display:block;font-weight:500;margin-bottom:0.5rem">Мастер</label>
                <select name="master_id" style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem" required>
                    <option value="">Выберите мастера</option>
                    {masters_options}
                </select>
            </div>
            <div style="margin-bottom:1rem">
                <label style="display:block;font-weight:500;margin-bottom:0.5rem">Услуга</label>
                <select name="service_id" style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem" required onchange="updatePriceAndTime(this)">
                    <option value="">Сначала выберите мастера</option>
                </select>
            </div>
            <div style="margin-bottom:1rem">
                <label style="display:block;font-weight:500;margin-bottom:0.5rem">Дата и время</label>
                <input type="datetime-local" name="start_time" style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem" required>
            </div>
            <button type="submit" class="btn-primary" style="width:100%">Записаться</button>
        </form>
    </div>
    
    <script>
        // Функция для загрузки услуг мастера
        document.querySelector('select[name="master_id"]').addEventListener('change', async function() {{
            const masterId = this.value;
            const serviceSelect = document.querySelector('select[name="service_id"]');
            
            if (!masterId) {{
                serviceSelect.innerHTML = '<option value="">Сначала выберите мастера</option>';
                return;
            }}
            
            try {{
                const response = await fetch(`/api/v1/masters/${{masterId}}/services`);
                const services = await response.json();
                
                serviceSelect.innerHTML = '<option value="">Выберите услугу</option>';
                services.forEach(service => {{
                    serviceSelect.innerHTML += `<option value="${{service.id}}" data-price="${{service.price}}" data-duration="${{service.duration_minutes}}">${{service.name}} — ${{service.price}} ₽ (${{service.duration_minutes}} мин)</option>`;
                }});
            }} catch (error) {{
                console.error('Ошибка загрузки услуг:', error);
            }}
        }});
        
        function updatePriceAndTime(select) {{
            const selectedOption = select.options[select.selectedIndex];
            if (selectedOption && selectedOption.dataset.price) {{
                console.log('Цена:', selectedOption.dataset.price);
            }}
        }}
    </script>
</body>
</html>"""
    return HTMLResponse(content=html)


def _alert(msg: str) -> str:
    """Баннер-уведомление об ошибке вверху карточки (msg — фиксированный текст)."""
    if not msg:
        return ""
    return (
        '<div style="background:#FEE2E2;color:#991B1B;border:1px solid #FCA5A5;'
        'border-radius:0.5rem;padding:0.75rem 1rem;margin-bottom:1rem;font-size:0.875rem">'
        f'{msg}</div>'
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница входа."""
    return HTMLResponse(content=render_login_page(request))


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Страница регистрации."""
    return HTMLResponse(content=render_register_page(request))


@router.get("/logout", response_class=HTMLResponse)
async def logout_page():
    """Выход из системы."""
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("access_token")
    return response


@router.get("/about", response_class=HTMLResponse)
async def about_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Страница «Манифест»."""
    user = await get_current_user_from_cookie(request, db)
    return HTMLResponse(content=render_about_page(user))


@router.get("/model", response_class=HTMLResponse)
async def model_landing_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Страница «Стань моделью»."""
    user = await get_current_user_from_cookie(request, db)
    return HTMLResponse(content=render_model_landing_page(user))


@router.get("/model/checkout", response_class=HTMLResponse)
async def model_checkout_page(
    request: Request,
    plan: str = "start",
    db: AsyncSession = Depends(get_db)
):
    """Страница оформления подписки модели."""
    user = await get_current_user_from_cookie(request, db)
    return HTMLResponse(content=render_model_checkout_page(plan, user))


@router.get("/model/dashboard", response_class=HTMLResponse)
async def model_dashboard_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Дашборд модели."""
    user = await get_current_user_from_cookie(request, db)
    from app.web.pages.model_dashboard import render_model_dashboard
    return HTMLResponse(content=render_model_dashboard(user))


@router.get("/offer", response_class=HTMLResponse)
async def offer_landing_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Страница «Коммерческое предложение»."""
    user = await get_current_user_from_cookie(request, db)
    return HTMLResponse(content=render_offer_landing_page(user))


@router.get("/book", response_class=HTMLResponse)
async def book_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Страница подтверждения записи."""
    params = dict(request.query_params)
    master_id = int(params.get("master_id", 0))
    service_id = int(params.get("service_id", 0))
    time_str = params.get("time", "")
    
    user = await get_current_user_from_cookie(request, db)
    
    # Получаем данные мастера и услуги
    master = (await db.execute(select(Master).where(Master.id == master_id))).scalar_one_or_none()
    service = (await db.execute(select(ServiceModel).where(ServiceModel.id == service_id))).scalar_one_or_none()
    
    if not master or not service:
        return HTMLResponse(content="<h1>Ошибка: мастер или услуга не найдены</h1>", status_code=404)
    
    master_user = (await db.execute(select(User).where(User.id == master.user_id))).scalar_one_or_none()
    master_name = master_user.full_name if master_user else "Мастер"
    salon = (await db.execute(select(Salon).where(Salon.id == master.salon_id))).scalar_one_or_none()
    salon_name = salon.name if salon else "Салон"
    
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Подтверждение записи — руми</title>
    {get_base_styles()}
</head>
<body style="background:var(--color-surface-alt);min-height:100vh;display:flex;align-items:center;justify-content:center">
<div class="card" style="max-width:500px;width:100%;padding:2rem">
    <h2 style="margin-bottom:1.5rem">Подтверждение записи</h2>
    
    <div style="margin-bottom:1rem;padding:1rem;background:var(--color-surface-alt);border-radius:0.75rem">
        <p><strong>🏢 Салон:</strong> {salon_name}</p>
        <p><strong>💇 Мастер:</strong> {master_name}</p>
        <p><strong>✂️ Услуга:</strong> {service.name}</p>
        <p><strong>⏱ Длительность:</strong> {service.duration_minutes} мин</p>
        <p><strong>📅 Время:</strong> {time_str.replace('T', ' ')}</p>
        <p><strong>💰 Цена:</strong> <span style="font-size:1.25rem;font-weight:700;color:var(--color-primary)">{service.price} ₽</span></p>
    </div>
    
    <form action="/api/v1/bookings/confirm" method="post">
        <input type="hidden" name="master_id" value="{master_id}">
        <input type="hidden" name="service_id" value="{service_id}">
        <input type="hidden" name="start_time" value="{time_str}">
        <button type="submit" class="btn-primary" style="width:100%;padding:1rem;font-size:1rem">Подтвердить запись</button>
    </form>
    
    <a href="/salons/{master.salon_id}" style="display:block;text-align:center;margin-top:1rem;color:var(--color-muted);font-size:0.9rem">← Назад к салону</a>
</div>
</body>
</html>"""
    
    return HTMLResponse(content=html)


@router.get("/{path:path}", response_class=HTMLResponse)
async def not_found_page(request: Request, path: str):
    """Страница 404 — для всех несуществующих маршрутов."""
    return HTMLResponse(content=f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Страница не найдена — руми</title>
    {get_base_styles()}
    <style>
        .notfound {{
            text-align: center;
            padding: 6rem 2rem;
            min-height: 80vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #FFF8F6, #F8C8DC33);
        }}
        .notfound-code {{
            font-size: 8rem;
            font-weight: 900;
            background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            line-height: 1;
            margin-bottom: 1rem;
        }}
        .notfound h1 {{
            font-size: 2rem;
            color: var(--color-heading);
            margin-bottom: 0.75rem;
        }}
        .notfound p {{
            color: var(--color-muted);
            max-width: 28rem;
            margin: 0 auto 2rem;
            font-size: 1rem;
            line-height: 1.6;
        }}
        .notfound .path {{
            background: white;
            padding: 0.5rem 1rem;
            border-radius: 0.5rem;
            font-family: monospace;
            font-size: 0.9rem;
            color: var(--color-primary);
            border: 1px solid var(--color-border);
            margin-bottom: 1.5rem;
        }}
        .quick-links {{
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
            justify-content: center;
        }}
    </style>
</head>
<body>
    <div class="notfound">
        <div class="notfound-code">404</div>
        <h1>Страница не найдена</h1>
        <p>Такой страницы не существует. Возможно, она была удалена или вы набрали неправильный адрес.</p>
        <div class="path">/{path}</div>
        <div class="quick-links">
            <a href="/" class="btn-primary">🏠 На главную</a>
            <a href="/salons" class="btn-outline">💇 Найти салон</a>
            <a href="/model" class="btn-outline">📸 Стать моделью</a>
        </div>
    </div>
</body>
</html>""", status_code=404)