# app/web/pages/business/tabs/promos.py

def render_promos_tab(promotions) -> str:
    """Вкладка Акции."""
    promos_rows = ""
    for p in promotions:
        promos_rows += f"""
        <tr>
            <td>{p.title}</td>
            <td><span class="promo-badge">{p.tag}</span></td>
            <td>{p.description or '—'}</td>
        </tr>"""
    
    return f"""
    <div id="tab-promos" class="tab-content">
        <div class="card" style="overflow-x:auto">
            <table>
                <thead>
                    <tr><th>Название</th><th>Тег</th><th>Описание</th></tr>
                </thead>
                <tbody>
                    {promos_rows or '<tr><td colspan="3" style="text-align:center;padding:2rem;color:var(--color-muted)">Пока нет акций</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>"""