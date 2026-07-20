# app/web/pages/business/tabs/promo_models.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import SalonModel, User as UserModel
from app.web.components.hint import hint as _hint


async def render_promo_models_tab(db: AsyncSession, salon) -> str:
    """Вкладка «Модели» — promo-модели, привязанные к салону (кастинг/контент)."""

    result = await db.execute(
        select(SalonModel, UserModel)
        .join(UserModel, UserModel.id == SalonModel.user_id)
        .where(SalonModel.salon_id == salon.id, SalonModel.is_active == True)
        .order_by(SalonModel.created_at.desc())
    )
    rows = result.all()

    cards_html = "".join(f"""
        <div class="card" style="display:flex;gap:1rem;align-items:center">
            <img src="{sm.photo_url or 'https://placehold.co/64x64'}" style="width:64px;height:64px;border-radius:50%;object-fit:cover;flex-shrink:0">
            <div style="flex:1">
                <strong>{sm.stage_name or u.full_name or 'Модель'}</strong>
                <p class="text-muted" style="font-size:0.8rem">{u.phone}</p>
                <p style="font-size:0.85rem;margin-top:0.25rem">{sm.bio or ''}</p>
            </div>
            <button class="btn-outline" style="padding:0.4rem 0.8rem;font-size:0.75rem" onclick="detachModel({sm.id})">Отвязать</button>
        </div>""" for sm, u in rows)

    return f"""
    <div id="tab-models" class="tab-content">
        <div class="card" style="margin-bottom:1.5rem">
            <h3 style="margin-bottom:1rem">➕ Привязать модель {_hint("«Модель» здесь — пользователь с ролью «Модель» (кастинг/сотрудничество для портфолио и контента), а не клиент. Привязка фиксирует её сотрудничество с вашим салоном.")}</h3>
            <p class="text-muted" style="margin-bottom:1rem;font-size:0.85rem">Модель должна быть уже зарегистрирована на платформе через «Стать моделью» — здесь вы приглашаете её к сотрудничеству с салоном.</p>
            <form id="attachModelForm" style="display:flex;gap:0.5rem;flex-wrap:wrap">
                <input name="phone" placeholder="Телефон модели" required style="flex:1;min-width:180px;padding:0.6rem;border:1px solid var(--color-border);border-radius:0.5rem">
                <input name="stage_name" placeholder="Творческий псевдоним (необязательно)" style="flex:1;min-width:180px;padding:0.6rem;border:1px solid var(--color-border);border-radius:0.5rem">
                <button type="submit" class="btn-primary">Привязать</button>
            </form>
        </div>

        <div class="grid-2">
            {cards_html or '<p class="text-muted">Пока ни одной модели не привязано</p>'}
        </div>
    </div>

    <script>
    (function() {{
        const form = document.getElementById('attachModelForm');
        if (form) form.addEventListener('submit', async function(e) {{
            e.preventDefault();
            const salonId = {salon.id};
            try {{
                const res = await fetch('/api/v1/business/my-salon/models?salon_id=' + salonId, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ phone: form.phone.value, stage_name: form.stage_name.value || null }})
                }});
                if (res.ok) {{
                    location.reload();
                }} else {{
                    const data = await res.json().catch(() => ({{}}));
                    alert(data.detail || 'Не удалось привязать модель');
                }}
            }} catch (err) {{
                alert('Ошибка соединения с сервером');
            }}
        }});

        window.detachModel = async function(modelId) {{
            if (!confirm('Отвязать модель от салона?')) return;
            try {{
                const res = await fetch('/api/v1/business/my-salon/models/' + modelId, {{ method: 'DELETE' }});
                if (res.ok) {{ location.reload(); }} else {{ alert('Не удалось отвязать модель'); }}
            }} catch (err) {{
                alert('Ошибка соединения с сервером');
            }}
        }};
    }})();
    </script>"""
