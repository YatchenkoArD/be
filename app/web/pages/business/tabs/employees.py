# app/web/pages/business/tabs/employees.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Master, User as UserModel
from app.web.components.icons import (
    ICON_EDIT,
    ICON_USER_PLUS,
    ICON_TRASH,
    ICON_USER,
    ICON_POWER,
)
from app.web.components.hint import hint as _hint


async def render_employees_tab(db: AsyncSession, salon, masters) -> str:
    """Вкладка Сотрудники — управление мастерами."""
    
    active_count = len([m for m in masters if m.is_active])
    
    employees_rows = ""
    for m in masters:
        user_result = await db.execute(select(UserModel).where(UserModel.id == m.user_id))
        master_user = user_result.scalar_one_or_none()
        user_name = master_user.full_name if master_user else "—"
        phone = master_user.phone if master_user else "—"
        
        status_class = "on" if m.is_active else "off"
        status_icon = ICON_POWER
        status_text = "На смене" if m.is_active else "Отключён"
        
        employees_rows += f"""
        <tr>
            <td>
                <div class="employee-cell">
                    <div class="employee-avatar">{user_name[0].upper() if user_name else '?'}</div>
                    <div>
                        <div class="employee-name">{user_name}</div>
                        <div class="employee-phone">{phone}</div>
                    </div>
                </div>
            </td>
            <td>{m.specialization}</td>
            <td>{m.experience_years} лет</td>
            <td>⭐ {m.rating}</td>
            <td>
                <span class="status-badge {status_class}">
                    {status_icon} {status_text}
                </span>
            </td>
            <td>
                <div class="employee-actions">
                    <button onclick="editEmployee({m.id}, '{user_name}', '{m.specialization}', {m.experience_years})" class="edit-btn" title="Редактировать">
                        {ICON_EDIT}
                    </button>
                    <button onclick="toggleEmployee({m.id}, '{user_name}', {str(m.is_active).lower()})" class="toggle-btn {status_class}" title="{'Отключить' if m.is_active else 'Включить'}">
                        {ICON_POWER}
                    </button>
                    <button onclick="deleteEmployee({m.id}, '{user_name}')" class="delete-btn" title="Удалить">
                        {ICON_TRASH}
                    </button>
                </div>
            </td>
        </tr>"""
    
    return f"""
    <div id="tab-employees" class="tab-content">
        <div class="employees-header">
            <div class="employees-stats">
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
                {ICON_USER_PLUS} Добавить мастера
            </button>
        </div>
        
        <div class="card employees-table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Мастер</th>
                        <th>Специализация</th>
                        <th>Опыт</th>
                        <th>Рейтинг</th>
                        <th>Статус</th>
                        <th style="width:120px">Действия {_hint("Отключить — временно скрыть мастера из записи, не теряя историю визитов и зарплат. Удалить — убрать мастера из салона полностью (аккаунт пользователя при этом сохраняется).")}</th>
                    </tr>
                </thead>
                <tbody>
                    {employees_rows or '<tr><td colspan="6" style="text-align:center;padding:2rem;color:var(--color-muted)">Пока нет мастеров</td></tr>'}
                </tbody>
            </table>
        </div>
        
        <!-- Модальное окно -->
        <div class="employee-modal-overlay" id="addEmployeeModal">
            <div class="employee-modal-box">
                <button class="employee-modal-close" onclick="document.getElementById('addEmployeeModal').classList.remove('active')">&times;</button>
                <h2 id="employeeModalTitle">Добавить мастера {_hint("Если телефон уже зарегистрирован на платформе — просто привяжет этого человека мастером к салону. Если телефон новый — заведёт для него аккаунт с временным паролем (покажется один раз, передайте мастеру).")}</h2>
                <form id="employeeForm" action="/api/v1/master/create-web" method="post">
                    <input type="hidden" name="master_id" id="employeeId">
                    <div class="employee-form-group">
                        <label for="employeeName">Имя *</label>
                        <input type="text" name="full_name" id="employeeName" required placeholder="Имя мастера">
                    </div>
                    <div class="employee-form-group">
                        <label for="employeePhone">Телефон *</label>
                        <input type="tel" name="phone" id="employeePhone" required placeholder="+7XXXXXXXXXX">
                    </div>
                    <div class="employee-form-group">
                        <label for="employeeSpec">Специализация *</label>
                        <input type="text" name="specialization" id="employeeSpec" required placeholder="Например: барбер-стилист">
                    </div>
                    <div class="employee-form-group">
                        <label for="employeeExp">Опыт (лет)</label>
                        <input type="number" name="experience_years" id="employeeExp" value="0">
                    </div>
                    <button type="submit" class="btn-primary" style="width:100%">Сохранить</button>
                </form>
            </div>
        </div>
    </div>
    """