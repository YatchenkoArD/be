# app/web/pages/my_salon.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Salon, Master, Promotion, User as UserModel
from app.web.components.header import render_header
from app.web.components.footer import render_footer
from app.web.components.sidebar import render_sidebar
from app.web.components.styles import get_base_styles


async def render_my_salon_page(db: AsyncSession, salon: Salon, user=None) -> str:
    """Страница редактирования своего салона."""
    
    # Получаем мастеров салона
    masters_result = await db.execute(
        select(Master).where(Master.salon_id == salon.id)
    )
    masters = masters_result.scalars().all()
    
    # Получаем акции
    promos_result = await db.execute(
        select(Promotion).where(Promotion.salon_id == salon.id)
    )
    promotions = promos_result.scalars().all()
    
    # Таблица мастеров
    masters_rows = ""
    for m in masters:
        # Явно загружаем пользователя для мастера (вместо ленивой загрузки m.user)
        user_result = await db.execute(
            select(UserModel).where(UserModel.id == m.user_id)
        )
        master_user = user_result.scalar_one_or_none()
        user_name = master_user.full_name if master_user else "—"
        
        masters_rows += f"""
        <tr>
            <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-border);">
                <strong>{user_name}</strong>
            </td>
            <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-border);">{m.specialization}</td>
            <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-border);">
                <button onclick="editMaster({m.id}, '{user_name}', '{m.specialization}', {m.experience_years})" style="background: none; border: none; color: var(--color-primary); cursor: pointer; font-size:1.1rem" title="Редактировать">✏️</button>
                <button onclick="deleteMaster({m.id}, '{user_name}')" style="background: none; border: none; color: #ef4444; cursor: pointer; font-size:1.1rem; margin-left:0.5rem" title="Удалить">🗑️</button>
            </td>
        </tr>
        """
    
    # Таблица акций (с рабочей кнопкой удаления)
    promos_rows = ""
    for p in promotions:
        promos_rows += f"""
        <tr>
            <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-border);"><strong>{p.title}</strong></td>
            <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-border);">{p.tag}</td>
            <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-border);">
                <button onclick="deletePromo({p.id}, '{p.title}')" style="background: none; border: none; color: red; cursor: pointer;">🗑️</button>
            </td>
        </tr>
        """
    
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Мой салон — {salon.name} — руми</title>
    {get_base_styles()}
    <style>
        .modal-overlay {{
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }}
        .modal-overlay.active {{
            display: flex;
        }}
        .modal-box {{
            background: white;
            border-radius: 1rem;
            padding: 2rem;
            max-width: 500px;
            width: 90%;
            position: relative;
            max-height: 90vh;
            overflow-y: auto;
        }}
        .modal-close {{
            position: absolute;
            top: 1rem;
            right: 1rem;
            background: none;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            color: var(--color-muted);
        }}
        .modal-close:hover {{
            color: var(--color-heading);
        }}
    </style>
</head>
<body>
    {render_header("business", user)}
    {render_sidebar("business")}
    
    <main style="margin-right: 16rem; padding-top: 2rem;">
        <div class="section-container">
            
            <!-- Заголовок -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
                <div>
                    <h1 class="text-display" style="font-size: 2rem;">{salon.name}</h1>
                    <p class="text-muted">Редактирование карточки салона</p>
                </div>
                <a href="/business/dashboard" class="btn-outline">← К панели управления</a>
            </div>
            
            <!-- Форма редактирования -->
            <div class="card" style="margin-bottom: 2rem;">
                <h2 class="text-subtitle" style="font-size: 1.25rem; margin-bottom: 1.5rem;">Основная информация</h2>
                <form action="/api/v1/business/my-salon" method="post">
                    <input type="hidden" name="method_override" value="put">
                    <input type="hidden" name="salon_id" value="{salon.id}">
                    <div class="grid-2" style="gap: 1.5rem; margin-bottom: 1.5rem;">
                        <div>
                            <label style="display: block; font-weight: 500; margin-bottom: 0.5rem;">Название салона</label>
                            <input type="text" name="name" value="{salon.name}" style="width: 100%; padding: 0.75rem; border: 1px solid var(--color-border); border-radius: 0.5rem;">
                        </div>
                        <div>
                            <label style="display: block; font-weight: 500; margin-bottom: 0.5rem;">Телефон</label>
                            <input type="tel" name="phone" value="{salon.phone or ''}" style="width: 100%; padding: 0.75rem; border: 1px solid var(--color-border); border-radius: 0.5rem;">
                        </div>
                    </div>
                    
                    <div style="margin-bottom: 1.5rem;">
                        <label style="display: block; font-weight: 500; margin-bottom: 0.5rem;">Адрес</label>
                        <input type="text" name="address" value="{salon.address or ''}" style="width: 100%; padding: 0.75rem; border: 1px solid var(--color-border); border-radius: 0.5rem;">
                    </div>
                    
                    <div style="margin-bottom: 1.5rem;">
                        <label style="display: block; font-weight: 500; margin-bottom: 0.5rem;">Описание</label>
                        <textarea name="description" rows="3" style="width: 100%; padding: 0.75rem; border: 1px solid var(--color-border); border-radius: 0.5rem; resize: vertical;">{salon.description or ''}</textarea>
                    </div>
                    
                    <button type="submit" class="btn-primary">💾 Сохранить изменения</button>
                </form>
            </div>
            
            <!-- Мастера -->
            <div class="card" style="margin-bottom: 2rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                    <h2 class="text-subtitle" style="font-size: 1.25rem;">Мастера</h2>
                    <button class="btn-primary" style="font-size:0.85rem;padding:0.5rem 1rem" onclick="document.getElementById('addMasterModal').classList.add('active')">+ Добавить мастера</button>
                </div>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr>
                            <th style="text-align: left; padding: 0.75rem; border-bottom: 2px solid var(--color-border);">Имя</th>
                            <th style="text-align: left; padding: 0.75rem; border-bottom: 2px solid var(--color-border);">Специализация</th>
                            <th style="text-align: left; padding: 0.75rem; border-bottom: 2px solid var(--color-border); width:80px"></th>
                        </tr>
                    </thead>
                    <tbody>
                        {masters_rows or '<tr><td colspan="3" style="padding:2rem;text-align:center;color:var(--color-muted)">Пока нет мастеров</td></tr>'}
                    </tbody>
                </table>
            </div>
            
            <!-- Акции -->
            <div class="card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                    <h2 class="text-subtitle" style="font-size: 1.25rem;">Акции</h2>
                    <button class="btn-primary" style="font-size:0.85rem;padding:0.5rem 1rem" onclick="document.getElementById('addPromoModal').classList.add('active')">+ Добавить акцию</button>
                </div>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr>
                            <th style="text-align: left; padding: 0.75rem; border-bottom: 2px solid var(--color-border);">Название</th>
                            <th style="text-align: left; padding: 0.75rem; border-bottom: 2px solid var(--color-border);">Тег</th>
                            <th style="text-align: left; padding: 0.75rem; border-bottom: 2px solid var(--color-border);">Действия</th>
                        </tr>
                    </thead>
                    <tbody>
                        {promos_rows or '<tr><td colspan="3" style="padding:2rem;text-align:center;color:var(--color-muted)">Пока нет акций</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>
    </main>
    
    <!-- Модальное окно: Добавить мастера -->
    <div class="modal-overlay" id="addMasterModal">
        <div class="modal-box">
            <button class="modal-close" onclick="document.getElementById('addMasterModal').classList.remove('active')">&times;</button>
            <h2 style="margin-bottom:1.5rem">Добавить мастера</h2>
            <form action="/api/v1/master/create-web" method="post">
                <input type="hidden" name="salon_id" value="{salon.id}">
                <div style="margin-bottom:1rem">
                    <label style="display:block;font-weight:500;margin-bottom:0.5rem">Имя *</label>
                    <input type="text" name="full_name" required placeholder="Имя мастера" style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem">
                </div>
                <div style="margin-bottom:1rem">
                    <label style="display:block;font-weight:500;margin-bottom:0.5rem">Телефон *</label>
                    <input type="tel" name="phone" required placeholder="+7XXXXXXXXXX" style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem">
                </div>
                <div style="margin-bottom:1rem">
                    <label style="display:block;font-weight:500;margin-bottom:0.5rem">Специализация *</label>
                    <input type="text" name="specialization" required placeholder="Например: барбер-стилист" style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem">
                </div>
                <div style="margin-bottom:1rem">
                    <label style="display:block;font-weight:500;margin-bottom:0.5rem">Опыт (лет)</label>
                    <input type="number" name="experience_years" value="0" style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem">
                </div>
                <button type="submit" class="btn-primary" style="width:100%">Добавить мастера</button>
            </form>
        </div>
    </div>
    
    <!-- Модальное окно: Редактировать мастера -->
    <div class="modal-overlay" id="editMasterModal">
        <div class="modal-box">
            <button class="modal-close" onclick="document.getElementById('editMasterModal').classList.remove('active')">&times;</button>
            <h2 style="margin-bottom:1.5rem">Редактировать мастера</h2>
            <form id="editMasterForm" method="post">
                <input type="hidden" name="master_id" id="editMasterId">
                <div style="margin-bottom:1rem">
                    <label style="display:block;font-weight:500;margin-bottom:0.5rem">Имя *</label>
                    <input type="text" name="full_name" id="editMasterName" required style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem">
                </div>
                <div style="margin-bottom:1rem">
                    <label style="display:block;font-weight:500;margin-bottom:0.5rem">Специализация *</label>
                    <input type="text" name="specialization" id="editMasterSpec" required style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem">
                </div>
                <div style="margin-bottom:1rem">
                    <label style="display:block;font-weight:500;margin-bottom:0.5rem">Опыт (лет)</label>
                    <input type="number" name="experience_years" id="editMasterExp" value="0" style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem">
                </div>
                <button type="submit" class="btn-primary" style="width:100%">Сохранить изменения</button>
            </form>
        </div>
    </div>
    
    <!-- Модальное окно: Добавить акцию -->
    <div class="modal-overlay" id="addPromoModal">
        <div class="modal-box">
            <button class="modal-close" onclick="document.getElementById('addPromoModal').classList.remove('active')">&times;</button>
            <h2 style="margin-bottom:1.5rem">Добавить акцию</h2>
            <form action="/api/v1/business/my-salon/promotions/web" method="post">
                <input type="hidden" name="salon_id" value="{salon.id}">
                <div style="margin-bottom:1rem">
                    <label style="display:block;font-weight:500;margin-bottom:0.5rem">Название *</label>
                    <input type="text" name="title" required placeholder="Например: Скидка 20%" style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem">
                </div>
                <div style="margin-bottom:1rem">
                    <label style="display:block;font-weight:500;margin-bottom:0.5rem">Описание</label>
                    <textarea name="description" rows="2" placeholder="Условия акции..." style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem"></textarea>
                </div>
                <div style="margin-bottom:1rem">
                    <label style="display:block;font-weight:500;margin-bottom:0.5rem">Тег *</label>
                    <input type="text" name="tag" required placeholder="Новичкам, Выгода, Подарок..." style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem">
                </div>
                <button type="submit" class="btn-primary" style="width:100%">Добавить акцию</button>
            </form>
        </div>
    </div>
    
    {render_footer()}
    
    <script>
    function editMaster(id, name, spec, exp) {{
        document.getElementById('editMasterId').value = id;
        document.getElementById('editMasterName').value = name;
        document.getElementById('editMasterSpec').value = spec;
        document.getElementById('editMasterExp').value = exp;
        document.getElementById('editMasterForm').action = '/api/v1/master/' + id + '/update';
        document.getElementById('editMasterModal').classList.add('active');
    }}
    
    function deleteMaster(id, name) {{
        if (confirm('Удалить мастера "' + name + '"? Это действие нельзя отменить.')) {{
            fetch('/api/v1/master/' + id + '/delete', {{ method: 'POST' }})
                .then(r => {{ if (r.ok) location.reload(); else alert('Ошибка при удалении'); }});
        }}
    }}
    
    function deletePromo(id, title) {{
        if (confirm('Удалить акцию "' + title + '"? Это действие нельзя отменить.')) {{
            fetch('/api/v1/business/my-salon/promotions/' + id + '/delete', {{ method: 'POST' }})
                .then(r => {{ if (r.ok) location.reload(); else alert('Ошибка при удалении'); }});
        }}
    }}
    </script>
</body>
</html>"""
    
    return html