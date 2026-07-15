# app/web/views.py
import html
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.models import Salon, User, Master, Service as ServiceModel
from app.web.pages.home import render_home_page
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


@router.get("/business/dashboard", response_class=HTMLResponse)
async def business_dashboard_page(
    request: Request,
    salon_id: int = None,
    db: AsyncSession = Depends(get_db)
):
    """Бизнес-панель с аналитикой. Доступна любому активному участнику
    салона (owner/admin), не только его создателю."""
    from app.web.pages.business import render_business_dashboard
    from app.api.deps import get_user_primary_salon_id, get_salon_membership

    user = await get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login?redirect=/business/dashboard", status_code=302)

    resolved_id = await get_user_primary_salon_id(db, user.id, salon_id)
    if resolved_id is None:
        return RedirectResponse(url="/business/register-salon", status_code=302)

    salon = (await db.execute(select(Salon).where(Salon.id == resolved_id))).scalar_one_or_none()
    membership = await get_salon_membership(db, user.id, resolved_id)
    if not salon or not membership:
        return RedirectResponse(url="/business/register-salon", status_code=302)

    return HTMLResponse(content=await render_business_dashboard(db, user, salon, membership))


@router.get("/business/my-salon", response_class=HTMLResponse)
async def my_salon_page(
    request: Request,
    salon_id: int = None,
    db: AsyncSession = Depends(get_db)
):
    """Страница редактирования своего салона (доступна с правом manage_salon)."""
    from app.web.pages.my_salon import render_my_salon_page
    from app.api.deps import get_user_primary_salon_id, check_salon_permission
    from fastapi import HTTPException

    user = await get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login?redirect=/business/my-salon", status_code=302)

    resolved_id = await get_user_primary_salon_id(db, user.id, salon_id)
    if resolved_id is None:
        return RedirectResponse(url="/business/register-salon", status_code=302)

    try:
        await check_salon_permission(db, user, resolved_id, "manage_salon")
    except HTTPException:
        return RedirectResponse(url="/business/dashboard", status_code=302)

    salon = (await db.execute(select(Salon).where(Salon.id == resolved_id))).scalar_one_or_none()
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


@router.get("/business/register-salon", response_class=HTMLResponse)
async def register_salon_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Страница регистрации салона."""
    user = await get_current_user_from_cookie(request, db)
    from app.web.pages.register_salon import render_register_salon_page
    html = render_register_salon_page(user)
    return HTMLResponse(content=html)


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
    {render_header("salons", user)}
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


# Маска ввода телефона: 8…→+7, разбивка на блоки +7 (XXX) XXX-XX-XX.
# Без интерполяции Python → raw-строка. Сервер всё равно канонизирует значение.
_PHONE_FORMAT_SCRIPT = r"""<script>
(function () {
  function format(value) {
    var d = (value || '').replace(/\D/g, '');
    if (!d) return '';                                 // пусто → поле можно очистить полностью
    if (d[0] === '8') d = '7' + d.slice(1);            // 8… → 7…
    else if (d[0] !== '7') d = '7' + d;                // ввели без кода → подставляем 7
    d = d.slice(0, 11);                                // 7 + 10 цифр
    var r = d.slice(1), out = '+7';
    if (r.length)      out += ' (' + r.slice(0, 3);
    if (r.length >= 3) out += ') ' + r.slice(3, 6);
    if (r.length >= 6) out += '-' + r.slice(6, 8);
    if (r.length >= 8) out += '-' + r.slice(8, 10);
    // без хвостовых разделителей — иначе backspace «застревает» на ) или -
    return out.replace(/[\s()\-]+$/, '');
  }
  document.querySelectorAll('.phone-input').forEach(function (inp) {
    inp.addEventListener('input', function () { inp.value = format(inp.value); });
    if (inp.value) inp.value = format(inp.value);       // отформатировать префилл
  });
})();
</script>"""


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница входа."""
    q = request.query_params
    redirect = html.escape(q.get("redirect", "/"), quote=True)
    phone = html.escape(q.get("phone", ""), quote=True)
    errors = {
        "1": "Неверный телефон или пароль",
        "locked": "Слишком много попыток входа. Попробуйте через 15 минут.",
    }
    banner = _alert(errors.get(q.get("error", ""), ""))

    return HTMLResponse(content=f"""<!DOCTYPE html>
<html lang="ru">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Вход — руми</title>
{get_base_styles()}
</head>
<body style="display:flex;align-items:center;justify-content:center;min-height:100vh;background:var(--color-surface-alt)">
<div class="card" style="width:100%;max-width:400px;padding:2.5rem">
    <div style="text-align:center;margin-bottom:1.5rem;font-size:1.5rem;font-weight:800"><span style="color:var(--color-primary)">руми.</span></div>
    <h1 style="font-size:1.5rem;color:var(--color-heading);text-align:center;margin-bottom:1.5rem">Вход</h1>
    {banner}
    <form action="/api/v1/auth/login-web" method="post">
        <input type="hidden" name="redirect" value="{redirect}">
        <label style="display:block;font-size:0.875rem;font-weight:500;margin-bottom:0.5rem;color:var(--color-heading)">Телефон</label>
        <input type="tel" name="phone" value="{phone}" placeholder="+7 (___) ___-__-__" inputmode="tel" class="phone-input" required style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem;font-size:0.875rem;margin-bottom:1rem">
        <label style="display:block;font-size:0.875rem;font-weight:500;margin-bottom:0.5rem;color:var(--color-heading)">Пароль</label>
        <input type="password" name="password" required style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem;font-size:0.875rem;margin-bottom:1rem">
        <button type="submit" class="btn-primary" style="width:100%">Войти</button>
    </form>
    <div style="text-align:center;margin-top:1rem;font-size:0.875rem"><a href="/register">Регистрация</a> · <a href="/">На главную</a></div>
</div>
""" + _PHONE_FORMAT_SCRIPT + """
</body>
</html>""")


# Живой индикатор требований к паролю (без интерполяции Python → raw-строка)
_PASSWORD_HINT_SCRIPT = r"""<script>
(function () {
  var pw = document.getElementById('pw');
  var btn = document.getElementById('submitBtn');
  if (!pw || !btn) return;
  var rules = {
    len:   function (v) { return v.length >= 8; },
    lower: function (v) { return /[a-zа-яё]/.test(v); },
    upper: function (v) { return /[A-ZА-ЯЁ]/.test(v); },
    digit: function (v) { return /[0-9]/.test(v); }
  };
  function update() {
    var v = pw.value, all = true;
    Object.keys(rules).forEach(function (k) {
      var ok = rules[k](v);
      all = all && ok;
      var li = document.querySelector('[data-rule="' + k + '"]');
      if (li) {
        li.querySelector('.m').textContent = ok ? '✓' : '✗';
        li.style.color = ok ? '#16A34A' : 'var(--color-muted)';
      }
    });
    btn.disabled = !all;
    btn.style.opacity = all ? '1' : '0.6';
    btn.style.cursor = all ? 'pointer' : 'not-allowed';
  }
  pw.addEventListener('input', update);
  update();
})();
</script>"""


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Страница регистрации."""
    q = request.query_params
    phone = html.escape(q.get("phone", ""), quote=True)
    full_name = html.escape(q.get("full_name", ""), quote=True)
    errors = {
        "phone_exists": "Пользователь с таким телефоном уже зарегистрирован",
        "weak_password": "Пароль не отвечает требованиям сложности",
        "bad_phone": "Неверный формат телефона. Пример: +7 (999) 123-45-67",
        "no_code": "Получите код подтверждения на телефон перед регистрацией",
        "bad_code": "Неверный или истёкший код подтверждения",
        "otp_unavailable": "Сервис отправки кода временно недоступен, попробуйте позже",
    }
    banner = _alert(errors.get(q.get("error", ""), ""))

    body = f"""<!DOCTYPE html>
<html lang="ru">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Регистрация — руми</title>
{get_base_styles()}
</head>
<body style="display:flex;align-items:center;justify-content:center;min-height:100vh;background:var(--color-surface-alt)">
<div class="card" style="width:100%;max-width:400px;padding:2.5rem">
    <div style="text-align:center;margin-bottom:1.5rem;font-size:1.5rem;font-weight:800"><span style="color:var(--color-primary)">руми.</span></div>
    <h1 style="font-size:1.5rem;color:var(--color-heading);text-align:center;margin-bottom:1.5rem">Регистрация</h1>
    {banner}
    <form action="/api/v1/auth/register-web" method="post" id="registerForm">
        <label style="display:block;font-size:0.875rem;font-weight:500;margin-bottom:0.5rem;color:var(--color-heading)">Имя</label>
        <input type="text" name="full_name" value="{full_name}" placeholder="Ваше имя" style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem;font-size:0.875rem;margin-bottom:1rem">
        <label style="display:block;font-size:0.875rem;font-weight:500;margin-bottom:0.5rem;color:var(--color-heading)">Телефон</label>
        <div style="display:flex;gap:0.5rem;margin-bottom:1rem">
            <input type="tel" id="phone" name="phone" value="{phone}" placeholder="+7 (___) ___-__-__" inputmode="tel" class="phone-input" required style="flex:1;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem;font-size:0.875rem">
            <button type="button" id="sendCodeBtn" style="white-space:nowrap;padding:0 1rem;border:1px solid var(--color-primary);border-radius:0.5rem;background:white;color:var(--color-primary);font-size:0.8rem;font-weight:500;cursor:pointer">Получить код</button>
        </div>
        <div id="codeGroup" style="display:none;margin-bottom:1rem">
            <label style="display:block;font-size:0.875rem;font-weight:500;margin-bottom:0.5rem;color:var(--color-heading)">Код из SMS / звонка</label>
            <input type="text" id="code" name="code" placeholder="1234" inputmode="numeric" autocomplete="one-time-code" style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem;font-size:0.875rem">
            <p id="codeHint" style="font-size:0.75rem;color:var(--color-muted);margin-top:0.375rem"></p>
        </div>
        <input type="hidden" id="request_id" name="request_id" value="">
        <label style="display:block;font-size:0.875rem;font-weight:500;margin-bottom:0.5rem;color:var(--color-heading)">Пароль</label>
        <input type="password" id="pw" name="password" required minlength="8" style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem;font-size:0.875rem;margin-bottom:0.5rem">
        <ul style="list-style:none;padding:0;margin:0 0 1rem;font-size:0.75rem;color:var(--color-muted)">
            <li data-rule="len"><span class="m">✗</span> Минимум 8 символов</li>
            <li data-rule="lower"><span class="m">✗</span> Строчная буква</li>
            <li data-rule="upper"><span class="m">✗</span> Заглавная буква</li>
            <li data-rule="digit"><span class="m">✗</span> Цифра</li>
        </ul>
        <button type="submit" id="submitBtn" class="btn-primary" style="width:100%">Зарегистрироваться</button>
    </form>
    <div style="text-align:center;margin-top:1rem;font-size:0.875rem"><a href="/login">Вход</a> · <a href="/">На главную</a></div>
</div>
<script>
(function() {{
  var btn = document.getElementById('sendCodeBtn');
  btn.addEventListener('click', async function() {{
    var phone = document.getElementById('phone').value;
    if (!phone) {{ alert('Сначала введите номер телефона'); return; }}
    btn.disabled = true;
    btn.textContent = 'Отправляем...';
    try {{
      var res = await fetch('/api/v1/auth/register/send-code', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ phone: phone }})
      }});
      var data = await res.json();
      if (res.ok) {{
        document.getElementById('request_id').value = data.request_id;
        document.getElementById('codeGroup').style.display = 'block';
        document.getElementById('codeHint').textContent = 'Код отправлен на ' + data.masked_phone;
        btn.textContent = 'Отправить ещё раз';
      }} else {{
        alert(data.detail || 'Не удалось отправить код');
        btn.textContent = 'Получить код';
      }}
    }} catch (e) {{
      alert('Ошибка соединения с сервером');
      btn.textContent = 'Получить код';
    }} finally {{
      btn.disabled = false;
    }}
  }});

  document.getElementById('registerForm').addEventListener('submit', function(e) {{
    if (!document.getElementById('request_id').value) {{
      e.preventDefault();
      alert('Сначала получите и введите код из SMS/звонка');
    }}
  }});
}})();
</script>
"""
    tail = _PHONE_FORMAT_SCRIPT + _PASSWORD_HINT_SCRIPT + "\n</body>\n</html>"
    return HTMLResponse(content=body + tail)


@router.get("/logout", response_class=HTMLResponse)
async def logout_page():
    """Выход из системы."""
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("access_token")
    return response


@router.get("/model", response_class=HTMLResponse)
async def model_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Страница 'Стань моделью'."""
    user = await get_current_user_from_cookie(request, db)
    from app.web.pages.model import render_model_page
    return HTMLResponse(content=render_model_page(user))


@router.get("/model/checkout/{plan}", response_class=HTMLResponse)
async def model_checkout_page(plan: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Страница оформления подписки."""
    user = await get_current_user_from_cookie(request, db)
    from app.web.pages.model_checkout import render_model_checkout
    return HTMLResponse(content=render_model_checkout(plan, user))


@router.get("/model/dashboard", response_class=HTMLResponse)
async def model_dashboard_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Дашборд модели."""
    user = await get_current_user_from_cookie(request, db)
    from app.web.pages.model_dashboard import render_model_dashboard
    return HTMLResponse(content=render_model_dashboard(user))


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