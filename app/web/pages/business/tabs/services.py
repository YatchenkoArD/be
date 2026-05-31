# app/web/pages/business/tabs/services.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Service, Master, User as UserModel


async def render_services_tab(db: AsyncSession, salon, masters) -> str:
    """Вкладка Услуги — управление услугами мастеров."""
    
    # Получаем все услуги мастеров салона
    master_ids = [m.id for m in masters]
    services_rows = ""
    
    if master_ids:
        services_result = await db.execute(
            select(Service, Master).join(Master, Service.master_id == Master.id)
            .where(Service.master_id.in_(master_ids))
            .order_by(Master.id, Service.price)
        )
        services_data = services_result.all()
        
        total_services = len(services_data)
        
        for service, master in services_data:
            # Имя мастера
            user_result = await db.execute(select(UserModel).where(UserModel.id == master.user_id))
            master_user = user_result.scalar_one_or_none()
            master_name = master_user.full_name if master_user else "—"
            
            services_rows += f"""
            <tr>
                <td><strong>{service.name}</strong></td>
                <td>{master_name}</td>
                <td>{service.duration_minutes} мин</td>
                <td><strong>{service.price:,} ₽</strong></td>
                <td style="font-size:0.85rem;color:var(--color-muted)">{service.description or '—'}</td>
                <td>
                    <button onclick="editService({service.id}, '{service.name}', {service.price}, {service.duration_minutes}, '{service.description or ''}', {service.master_id})" 
                        style="background:none;border:none;color:var(--color-primary);cursor:pointer;font-size:1.1rem" title="Редактировать">✏️</button>
                    <button onclick="deleteService({service.id}, '{service.name}')" 
                        style="background:none;border:none;color:#ef4444;cursor:pointer;font-size:1.1rem;margin-left:0.5rem" title="Удалить">🗑️</button>
                </td>
            </tr>"""
    else:
        total_services = 0
    
    # Список мастеров для выпадающего списка
    master_options = ""
    for m in masters:
        user_result = await db.execute(select(UserModel).where(UserModel.id == m.user_id))
        master_user = user_result.scalar_one_or_none()
        master_name = master_user.full_name if master_user else "—"
        master_options += f'<option value="{m.id}">{master_name} — {m.specialization}</option>'
    
    return f"""
    <div id="tab-services" class="tab-content">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem">
            <div class="stat-card" style="padding:1rem 1.5rem">
                <div class="stat-value" style="font-size:1.5rem">{total_services}</div>
                <div class="stat-label">Всего услуг</div>
            </div>
            <button class="btn-primary" style="font-size:0.85rem;padding:0.5rem 1rem" onclick="document.getElementById('addServiceModal').classList.add('active')">
                + Добавить услугу
            </button>
        </div>
        
        <div class="card" style="overflow-x:auto">
            <table>
                <thead>
                    <tr>
                        <th>Услуга</th>
                        <th>Мастер</th>
                        <th>Длительность</th>
                        <th>Цена</th>
                        <th>Описание</th>
                        <th style="width:100px">Действия</th>
                    </tr>
                </thead>
                <tbody>
                    {services_rows or '<tr><td colspan="6" style="text-align:center;padding:2rem;color:var(--color-muted)">Пока нет услуг</td></tr>'}
                </tbody>
            </table>
        </div>
        
        <!-- Модальное окно: Добавить/Редактировать услугу -->
        <div class="modal-overlay" id="addServiceModal">
            <div class="modal-box">
                <button class="modal-close" onclick="document.getElementById('addServiceModal').classList.remove('active')">&times;</button>
                <h2 style="margin-bottom:1.5rem" id="serviceModalTitle">Добавить услугу</h2>
                <form id="serviceForm" action="/api/v1/services/create" method="post">
                    <input type="hidden" name="service_id" id="serviceId">
                    <div style="margin-bottom:1rem">
                        <label style="display:block;font-weight:500;margin-bottom:0.5rem">Мастер *</label>
                        <select name="master_id" id="serviceMaster" required style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem">
                            <option value="">Выберите мастера</option>
                            {master_options}
                        </select>
                    </div>
                    <div style="margin-bottom:1rem">
                        <label style="display:block;font-weight:500;margin-bottom:0.5rem">Название услуги *</label>
                        <input type="text" name="name" id="serviceName" required placeholder="Например: Стрижка машинкой" 
                            style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem">
                    </div>
                    <div class="grid-2" style="gap:1rem;margin-bottom:1rem">
                        <div>
                            <label style="display:block;font-weight:500;margin-bottom:0.5rem">Цена (₽) *</label>
                            <input type="number" name="price" id="servicePrice" required placeholder="1500" 
                                style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem">
                        </div>
                        <div>
                            <label style="display:block;font-weight:500;margin-bottom:0.5rem">Длительность (мин) *</label>
                            <input type="number" name="duration_minutes" id="serviceDuration" required placeholder="30" 
                                style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem">
                        </div>
                    </div>
                    <div style="margin-bottom:1rem">
                        <label style="display:block;font-weight:500;margin-bottom:0.5rem">Описание</label>
                        <textarea name="description" id="serviceDescription" rows="2" placeholder="Подробнее об услуге..." 
                            style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem;resize:vertical"></textarea>
                    </div>
                    <button type="submit" class="btn-primary" style="width:100%">Сохранить</button>
                </form>
            </div>
        </div>
    </div>
    
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
    
    <script>
        function editService(id, name, price, duration, desc, masterId) {{
            document.getElementById('serviceModalTitle').textContent = 'Редактировать услугу';
            document.getElementById('serviceId').value = id;
            document.getElementById('serviceName').value = name;
            document.getElementById('servicePrice').value = price;
            document.getElementById('serviceDuration').value = duration;
            document.getElementById('serviceDescription').value = desc;
            document.getElementById('serviceMaster').value = masterId;
            document.getElementById('serviceForm').action = '/api/v1/services/' + id + '/update';
            document.getElementById('addServiceModal').classList.add('active');
        }}
        
        function deleteService(id, name) {{
            if (confirm(`Удалить услугу "${{name}}"? Это действие нельзя отменить.`)) {{
                fetch(`/api/v1/services/${{id}}/delete`, {{ method: 'POST' }})
                    .then(r => {{ if (r.ok) location.reload(); else alert('Ошибка при удалении'); }});
            }}
        }}
        
        document.querySelector('[onclick*="addServiceModal"]').addEventListener('click', function() {{
            document.getElementById('serviceModalTitle').textContent = 'Добавить услугу';
            document.getElementById('serviceForm').reset();
            document.getElementById('serviceId').value = '';
            document.getElementById('serviceForm').action = '/api/v1/services/create';
        }});
    </script>"""