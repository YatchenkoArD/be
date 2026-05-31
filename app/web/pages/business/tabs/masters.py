# app/web/pages/business/tabs/masters.py

def render_masters_tab(masters_rows: str) -> str:
    """Вкладка Мастера."""
    return f"""
    <div id="tab-masters" class="tab-content">
        <div class="card" style="overflow-x:auto">
            <table>
                <thead>
                    <tr><th>Имя</th><th>Специализация</th><th>Опыт</th><th>Услуг</th><th>Рейтинг</th></tr>
                </thead>
                <tbody>
                    {masters_rows or '<tr><td colspan="5" style="text-align:center;padding:2rem;color:var(--color-muted)">Пока нет мастеров</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>"""