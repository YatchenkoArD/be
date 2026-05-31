# app/web/pages/business/tabs/employees.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Master, User as UserModel


async def render_employees_tab(db: AsyncSession, salon, masters) -> str:
    """Вкладка Сотрудники — управление мастерами."""
    
    active_count = len([m for m in masters if m.is_active])
    
    employees_rows = ""
    for m in masters:
        user_result = await db.execute(select(UserModel).where(UserModel.id == m.user_id))
        master_user = user_result.scalar_one_or_none()
        user_name = master_user.full_name if master_user else "—"
        phone = master_user.phone if master_user else "—"
        
        status_badge = "🟢 На смене" if m.is_active else "🔴 Отключён"
        status_color = "#22c55e" if m.is_active else "#ef4444"
        
        employees_rows += f"""
        <tr>
            <td>
                <div style="display:flex;align-items:center;gap:0.75rem">
                    <div class="employee-avatar">{user_name[0].upper() if user_name else '?'}</div>
                    <div>
                        <strong>{user_name}</strong>
                        <div style="font-size:0.8rem;color:var(--color-muted)">{phone}</div>
                    </div>
                </div>
            </td>
            <td>{m.specialization}</td>
            <td>{m.experience_years} лет</td>
            <td>⭐ {m.rating}</td>
            <td><span style="color:{status_color};font-size:0.85rem">{status_badge}</span></td>
            <td>
                <button onclick="editEmployee({m.id}, '{user_name}', '{m.specialization}', {m.experience_years})" 
                    style="background:none;border:none;color:var(--color-primary);cursor:pointer;font-size:1.1rem" title="Редактировать">✏️</button>
                <button onclick="toggleEmployee({m.id}, '{user_name}', {str(m.is_active).lower()})" 
                    style="background:none;border:none;color:{'#ef4444' if m.is_active else '#22c55e'};cursor:pointer;font-size:1.1rem;margin-left:0.5rem" 
                    title="{'Отключить' if m.is_active else 'Включить'}">{'🔴' if m.is_active else '🟢'}</button>
                <button onclick="deleteEmployee({m.id}, '{user_name}')" 
                    style="background:none;border:none;color:#ef4444;cursor:pointer;font-size:1.1rem;margin-left:0.5rem" title="Удалить">🗑️</button>
            </td>
        </tr>"""
    
    return f"""
    <div id="tab-employees" class="tab-content">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem">
            <div style="display:flex;gap:1rem">
                <div class="stat-card" style="padding:1rem 1.5rem">
                    <div class="stat-value" style="font-size:1.5rem">{len(masters)}</div>
                    <div class="stat-label">Всего</div>
                </div>
                <div class="stat-card" style="padding:1rem 1.5rem">
                    <div class="stat-value" style="font-size:1.5rem;color:#22c55e">{active_count}</div>
                    <div class="stat-label">Активных</div>
                </div>
            </div>
            <button class="btn-primary" style="font-size:0.85rem;padding:0.5rem 1rem" onclick="document.getElementById('addEmployeeModal').classList.add('active')">
                + Добавить мастера
            </button>
        </div>
        
        <div class="card" style="overflow-x:auto">
            <table>
                <thead>
                    <tr>
                        <th>Мастер</th>
                        <th>Специализация</th>
                        <th>Опыт</th>
                        <th>Рейтинг</th>
                        <th>Статус</th>
                        <th style="width:100px">Действия</th>
                    </tr>
                </thead>
                <tbody>
                    {employees_rows or '<tr><td colspan="6" style="text-align:center;padding:2rem;color:var(--color-muted)">Пока нет мастеров</td></tr>'}
                </tbody>
            </table>
        </div>
        
        <!-- Модальное окно -->
        <div class="modal-overlay" id="addEmployeeModal">
            <div class="modal-box">
                <button class="modal-close" onclick="document.getElementById('addEmployeeModal').classList.remove('active')">&times;</button>
                <h2 style="margin-bottom:1.5rem" id="employeeModalTitle">Добавить мастера</h2>
                <form id="employeeForm" action="/api/v1/master/create-web" method="post">
                    <input type="hidden" name="master_id" id="employeeId">
                    <div style="margin-bottom:1rem">
                        <label style="display:block;font-weight:500;margin-bottom:0.5rem">Имя *</label>
                        <input type="text" name="full_name" id="employeeName" required placeholder="Имя мастера" 
                            style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem">
                    </div>
                    <div style="margin-bottom:1rem">
                        <label style="display:block;font-weight:500;margin-bottom:0.5rem">Телефон *</label>
                        <input type="tel" name="phone" id="employeePhone" required placeholder="+7XXXXXXXXXX" 
                            style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem">
                    </div>
                    <div style="margin-bottom:1rem">
                        <label style="display:block;font-weight:500;margin-bottom:0.5rem">Специализация *</label>
                        <input type="text" name="specialization" id="employeeSpec" required placeholder="Например: барбер-стилист" 
                            style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem">
                    </div>
                    <div style="margin-bottom:1rem">
                        <label style="display:block;font-weight:500;margin-bottom:0.5rem">Опыт (лет)</label>
                        <input type="number" name="experience_years" id="employeeExp" value="0" 
                            style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem">
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
        .employee-avatar {{
            width: 2.5rem;
            height: 2.5rem;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1rem;
            color: white;
            font-weight: 700;
            flex-shrink: 0;
        }}
    </style>
    
    <script>
        function editEmployee(id, name, spec, exp) {{
            document.getElementById('employeeModalTitle').textContent = 'Редактировать мастера';
            document.getElementById('employeeId').value = id;
            document.getElementById('employeeName').value = name;
            document.getElementById('employeeSpec').value = spec;
            document.getElementById('employeeExp').value = exp;
            document.getElementById('employeeForm').action = '/api/v1/master/' + id + '/update';
            document.getElementById('addEmployeeModal').classList.add('active');
        }}
        
        function toggleEmployee(id, name, isActive) {{
            const action = isActive ? 'отключить' : 'включить';
            if (confirm(`${{action.charAt(0).toUpperCase() + action.slice(1)}} мастера "${{name}}"?`)) {{
                fetch(`/api/v1/master/${{id}}/toggle`, {{ method: 'POST' }})
                    .then(r => {{ if (r.ok) location.reload(); else alert('Ошибка'); }});
            }}
        }}
        
        function deleteEmployee(id, name) {{
            if (confirm(`Удалить мастера "${{name}}"? Это действие нельзя отменить.`)) {{
                fetch(`/api/v1/master/${{id}}/delete`, {{ method: 'POST' }})
                    .then(r => {{ if (r.ok) location.reload(); else alert('Ошибка при удалении'); }});
            }}
        }}
        
        document.querySelector('[onclick*="addEmployeeModal"]').addEventListener('click', function() {{
            document.getElementById('employeeModalTitle').textContent = 'Добавить мастера';
            document.getElementById('employeeForm').reset();
            document.getElementById('employeeId').value = '';
            document.getElementById('employeeForm').action = '/api/v1/master/create-web';
        }});
    </script>"""