# app/web/pages/salon_detail.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from app.models.models import Salon, Master, Service, Promotion, User, Booking, BookingStatus, Review
from app.web.components.header import render_header
from app.web.components.footer import render_footer
from app.web.components.sidebar import render_sidebar
from app.web.components.styles import get_base_styles


async def render_salon_detail(db: AsyncSession, salon_id: int, user=None) -> str:
    """Страница салона с мастерами, записью и отзывами."""
    
    result = await db.execute(select(Salon).where(Salon.id == salon_id))
    salon = result.scalar_one_or_none()
    
    if not salon:
        return """<!DOCTYPE html><html><body style="text-align:center;padding:3rem"><h1>Салон не найден</h1><a href="/salons">← К списку салонов</a></body></html>"""
    
    masters_result = await db.execute(
        select(Master).where(Master.salon_id == salon.id, Master.is_active == True)
    )
    masters = masters_result.scalars().all()
    
    promos_result = await db.execute(
        select(Promotion).where(Promotion.salon_id == salon.id, Promotion.is_active == True)
    )
    promotions = promos_result.scalars().all()
    
    reviews_result = await db.execute(
        select(Review).where(Review.salon_id == salon.id).order_by(Review.created_at.desc()).limit(10)
    )
    reviews = reviews_result.scalars().all()
    
    masters_html = ""
    for m in masters:
        user_result = await db.execute(select(User).where(User.id == m.user_id))
        master_user = user_result.scalar_one_or_none()
        user_name = master_user.full_name if master_user else "Мастер"
        avatar = user_name[0].upper() if user_name else "М"
        
        services_result = await db.execute(
            select(Service).where(Service.master_id == m.id).order_by(Service.price)
        )
        services = services_result.scalars().all()
        
        services_cards = ""
        for srv in services:
            services_cards += f"""
            <div class="service-card" id="svc-{m.id}-{srv.id}">
                <div class="service-info">
                    <div class="service-name">{srv.name}</div>
                    <div class="service-meta">⏱ {srv.duration_minutes} мин</div>
                </div>
                <div class="service-price">{srv.price} ₽</div>
                <button class="btn-outline service-select-btn" style="font-size:0.8rem;padding:0.4rem 0.8rem"
                    onclick="showSlots(this, {m.id}, {srv.id}, '{srv.name}', {srv.price}, {srv.duration_minutes})">
                    Выбрать
                </button>
            </div>
            """
        
        masters_html += f"""
        <div class="master-card" id="master-{m.id}">
            <div class="master-header">
                <div class="master-avatar">{avatar}</div>
                <div class="master-info">
                    <h3>{user_name}</h3>
                    <span class="master-spec">{m.specialization} · ⭐{m.rating} · Опыт {m.experience_years} лет</span>
                    <button id="fav-master-{m.id}" onclick="toggleFavorite('master', {m.id})" class="fav-btn" style="font-size:0.9rem;margin-top:0.2rem" title="Добавить в избранное">🤍</button>
                </div>
            </div>
            
            <div class="services-section">
                <div class="services-title">Услуги мастера:</div>
                <div class="services-grid">{services_cards}</div>
            </div>
            
            <div class="slots-container" id="slots-{m.id}" style="display:none">
                <div class="slots-title" id="slots-title-{m.id}"></div>
                <div class="slot-grid" id="slot-grid-{m.id}"></div>
            </div>
        </div>
        """
    
    promos_html = ""
    for p in promotions:
        promos_html += f"""
        <div class="promo-card">
            <span class="promo-tag">{p.tag}</span>
            <strong>{p.title}</strong>
            <p>{p.description or ''}</p>
        </div>
        """
    
    reviews_html = ""
    for r in reviews:
        client_result = await db.execute(select(User).where(User.id == r.client_id))
        client_user = client_result.scalar_one_or_none()
        client_name = client_user.full_name if client_user else "Клиент"
        stars = "⭐" * r.rating + "☆" * (5 - r.rating)
        date_str = r.created_at.strftime("%d.%m.%Y") if r.created_at else ""
        
        reviews_html += f"""
        <div class="review-card">
            <div class="review-header">
                <strong>{client_name}</strong>
                <span class="review-stars">{stars}</span>
                <span class="review-date">{date_str}</span>
            </div>
            <p class="review-comment">{r.comment or 'Без комментария'}</p>
        </div>
        """
    
    review_form = ""
    if user:
        masters_options = ""
        for m in masters:
            master_user = (await db.execute(select(User).where(User.id == m.user_id))).scalar_one_or_none()
            master_name = master_user.full_name if master_user else "Мастер"
            masters_options += f'<option value="{m.id}">{master_name} — {m.specialization}</option>'
        
        review_form = f"""
        <div class="review-form-card">
            <h3>Оставить отзыв</h3>
            <form action="/api/v1/reviews/create" method="post">
                <input type="hidden" name="salon_id" value="{salon.id}">
                <div class="form-group">
                    <label>Мастер:</label>
                    <select name="master_id" required style="width:100%;padding:0.5rem;border:1px solid var(--color-border);border-radius:0.5rem">
                        <option value="">Выберите мастера</option>
                        {masters_options}
                    </select>
                </div>
                <div class="form-group">
                    <label>Оценка:</label>
                    <div class="rating-input">
                        <input type="radio" name="rating" value="5" id="star5"><label for="star5">⭐</label>
                        <input type="radio" name="rating" value="4" id="star4"><label for="star4">⭐</label>
                        <input type="radio" name="rating" value="3" id="star3"><label for="star3">⭐</label>
                        <input type="radio" name="rating" value="2" id="star2"><label for="star2">⭐</label>
                        <input type="radio" name="rating" value="1" id="star1" required><label for="star1">⭐</label>
                    </div>
                </div>
                <div class="form-group">
                    <label>Комментарий:</label>
                    <textarea name="comment" rows="3" placeholder="Расскажите о вашем впечатлении..." style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem;resize:vertical"></textarea>
                </div>
                <button type="submit" class="btn-primary">Отправить отзыв</button>
            </form>
        </div>
        """
    
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{salon.name} — руми</title>
    {get_base_styles()}
    <style>
        .salon-hero {{ background: linear-gradient(135deg, #FFF8F6, #F8C8DC33); padding: 3rem 0; margin-bottom: 2rem; }}
        .salon-hero h1 {{ font-size: 2.5rem; margin-bottom: 0.5rem; }}
        .salon-hero .meta {{ display: flex; gap: 1.5rem; color: var(--color-muted); font-size: 0.9rem; flex-wrap:wrap; align-items:center }}
        .master-card {{ background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 1rem; padding: 1.5rem; margin-bottom: 1.25rem; transition: border-color 0.2s; }}
        .master-card:hover {{ border-color: var(--color-primary); }}
        .master-header {{ display: flex; gap: 1rem; align-items: start; margin-bottom: 1rem; }}
        .master-avatar {{ width: 4rem; height: 4rem; border-radius: 50%; background: linear-gradient(135deg, var(--color-primary), var(--color-accent)); display: flex; align-items: center; justify-content: center; font-size: 1.5rem; color: white; font-weight: 700; flex-shrink: 0; }}
        .master-info h3 {{ font-size: 1.1rem; margin-bottom: 0.25rem; }}
        .master-spec {{ font-size: 0.85rem; color: var(--color-muted); }}
        .services-section {{ border-top: 1px solid var(--color-border); padding-top: 1rem; margin-top: 0.5rem; }}
        .services-title {{ font-size: 0.85rem; font-weight: 600; color: var(--color-muted); margin-bottom: 0.75rem; text-transform: uppercase; letter-spacing: 0.03em; }}
        .services-grid {{ display: flex; flex-direction: column; gap: 0.5rem; }}
        .service-card {{ display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: 0.75rem; background: var(--color-surface-alt); border-radius: 0.75rem; transition: all 0.2s; }}
        .service-card:hover {{ background: var(--color-accent-light); }}
        .service-card.selected {{ background: var(--color-accent-light); border: 1px solid var(--color-primary); }}
        .service-info {{ flex: 1; }}
        .service-name {{ font-weight: 600; font-size: 0.95rem; color: var(--color-heading); }}
        .service-meta {{ font-size: 0.8rem; color: var(--color-muted); margin-top: 0.15rem; }}
        .service-price {{ font-weight: 700; font-size: 1.1rem; color: var(--color-primary); white-space: nowrap; }}
        .slots-container {{ border-top: 1px solid var(--color-primary); margin-top: 1rem; padding-top: 1rem; }}
        .slots-title {{ font-weight: 600; margin-bottom: 0.75rem; color: var(--color-heading); }}
        .slot-grid {{ display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.5rem; }}
        .slot-btn {{ padding: 0.5rem 0.75rem; border: 1px solid var(--color-primary); border-radius: 0.5rem; font-size: 0.85rem; cursor: pointer; background: white; color: var(--color-primary); transition: all 0.2s; font-weight: 500; }}
        .slot-btn:hover {{ background: var(--color-primary); color: white; }}
        .slot-btn.selected {{ background: var(--color-primary); color: white; }}
        .no-slots {{ color: var(--color-muted); font-size: 0.85rem; padding: 0.5rem 0; }}
        .book-panel {{ position: fixed; bottom: 0; left: 0; right: 0; background: white; border-top: 2px solid var(--color-primary); padding: 1rem 2rem; display: none; z-index: 200; box-shadow: 0 -4px 20px rgba(0,0,0,0.1); }}
        .book-panel.active {{ display: block; }}
        .book-panel-inner {{ max-width: 1200px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; }}
        .promo-card {{ background: var(--color-surface-alt); border: 1px solid var(--color-border); border-radius: 0.75rem; padding: 1rem; margin-bottom: 0.5rem; }}
        .promo-tag {{ display: inline-block; background: linear-gradient(135deg, var(--color-primary), var(--color-accent)); color: white; padding: 0.15rem 0.5rem; border-radius: 1rem; font-size: 0.7rem; font-weight: 600; margin-right: 0.5rem; }}
        .section-title {{ font-size: 1.5rem; margin: 2rem 0 1rem; }}
        .review-card {{ background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 0.75rem; padding: 1rem; margin-bottom: 0.75rem; }}
        .review-header {{ display: flex; gap: 0.75rem; align-items: center; margin-bottom: 0.5rem; }}
        .review-stars {{ font-size: 0.9rem; }}
        .review-date {{ font-size: 0.8rem; color: var(--color-muted); margin-left: auto; }}
        .review-comment {{ color: var(--color-body); font-size: 0.9rem; }}
        .review-form-card {{ background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 1rem; padding: 1.5rem; margin-top: 2rem; }}
        .review-form-card h3 {{ margin-bottom: 1rem; }}
        .form-group {{ margin-bottom: 1rem; }}
        .form-group label {{ display: block; font-weight: 500; margin-bottom: 0.5rem; }}
        .rating-input {{ display: flex; gap: 0.5rem; }}
        .rating-input input {{ display: none; }}
        .rating-input label {{ font-size: 1.5rem; cursor: pointer; opacity: 0.5; transition: opacity 0.2s; }}
        .rating-input input:checked ~ label,
        .rating-input label:hover,
        .rating-input label:hover ~ label {{ opacity: 1; }}
        .fav-btn {{
            background: none;
            border: none;
            cursor: pointer;
            font-size: 1.2rem;
            transition: transform 0.2s;
            padding: 0.2rem;
        }}
        .fav-btn:hover {{
            transform: scale(1.2);
        }}
        .fav-btn.liked {{
            color: #ef4444;
        }}
    </style>
</head>
<body>
    {render_header("salons", user)}
    {render_sidebar("salons")}
    
    <main style="margin-right: 16rem;">
        <div class="salon-hero">
            <div class="section-container">
                <a href="/salons" style="color:var(--color-primary);text-decoration:none;margin-bottom:1rem;display:inline-block">← Все салоны</a>
                <h1 class="text-display">{salon.name}</h1>
                <div class="meta">
                    <span>📍 {salon.address or 'Адрес не указан'}</span>
                    <span>📞 {salon.phone or '—'}</span>
                    <span>⭐ {salon.rating} ({salon.reviews_count} отзывов)</span>
                    <button id="fav-salon-{salon.id}" onclick="toggleFavorite('salon', {salon.id})" class="fav-btn" title="Добавить в избранное">🤍</button>
                </div>
                <p style="margin-top:0.75rem;color:var(--color-body)">{salon.description or ''}</p>
            </div>
        </div>
        
        <div class="section-container">
            {f'<div class="section-title">🎉 Акции</div>{promos_html}' if promotions else ''}
            
            <div class="section-title">💇 Мастера и запись</div>
            <p style="color:var(--color-muted);margin-bottom:1.5rem">Выберите услугу и свободное время для записи</p>
            {masters_html or '<p>В этом салоне пока нет мастеров.</p>'}
            
            <div class="section-title">💬 Отзывы</div>
            {reviews_html or '<p style="color:var(--color-muted)">Пока нет отзывов. Будьте первым!</p>'}
            {review_form}
        </div>
    </main>
    
    <div class="book-panel" id="bookPanel">
        <div class="book-panel-inner">
            <div><strong id="panelMaster"></strong> · <span id="panelTime" style="color:var(--color-primary)"></span></div>
            <button class="btn-primary" onclick="confirmBooking()" style="font-size:1rem;padding:0.75rem 2rem">Записаться</button>
        </div>
    </div>
    
    {render_footer()}
    
    <script>
        let selectedSlot = null;
        let selectedMasterId = null;
        let selectedServiceId = null;
        
        // === ИЗБРАННОЕ ===
        async function checkFavorites() {{
            try {{
                const response = await fetch('/api/v1/favorites/my');
                const data = await response.json();
                data.salon_ids.forEach(id => {{
                    const btn = document.getElementById('fav-salon-' + id);
                    if (btn) {{ btn.textContent = '❤️'; btn.classList.add('liked'); }}
                }});
                data.master_ids.forEach(id => {{
                    const btn = document.getElementById('fav-master-' + id);
                    if (btn) {{ btn.textContent = '❤️'; btn.classList.add('liked'); }}
                }});
            }} catch(e) {{}}
        }}
        
        async function toggleFavorite(type, id) {{
            const btn = document.getElementById('fav-' + type + '-' + id);
            const isLiked = btn.classList.contains('liked');
            
            try {{
                const response = await fetch(`/api/v1/favorites/toggle-${{type}}/${{id}}`, {{ method: 'POST' }});
                if (response.ok) {{
                    if (isLiked) {{
                        btn.textContent = '🤍';
                        btn.classList.remove('liked');
                    }} else {{
                        btn.textContent = '❤️';
                        btn.classList.add('liked');
                    }}
                }}
            }} catch(e) {{
                alert('Ошибка. Попробуйте позже.');
            }}
        }}
        
        checkFavorites();
        
        // === СЛОТЫ ===
        async function showSlots(btn, masterId, serviceId, serviceName, price, duration) {{
            document.querySelectorAll('.service-select-btn').forEach(b => b.textContent = 'Выбрать');
            document.querySelectorAll('.service-card').forEach(c => c.classList.remove('selected'));
            
            btn.textContent = '✓ Выбрано';
            btn.parentElement.classList.add('selected');
            
            selectedMasterId = masterId;
            selectedServiceId = serviceId;
            
            document.querySelectorAll('.slots-container').forEach(c => c.style.display = 'none');
            
            const slotsContainer = document.getElementById('slots-' + masterId);
            const slotsTitle = document.getElementById('slots-title-' + masterId);
            const slotGrid = document.getElementById('slot-grid-' + masterId);
            
            slotsTitle.innerHTML = `
                📅 Доступное время для «${{serviceName}}» (${{price}} ₽, ${{duration}} мин):
                <br><input type="date" id="datePicker-${{masterId}}" value="${{new Date().toISOString().split('T')[0]}}" 
                    onchange="loadSlots(${{masterId}}, ${{serviceId}}, '${{serviceName}}', ${{price}}, ${{duration}})"
                    style="margin-top:0.5rem;padding:0.4rem;border:1px solid var(--color-border);border-radius:0.5rem">
            `;
            slotGrid.innerHTML = '<p style="color:var(--color-muted);font-size:0.85rem">Выберите дату для загрузки слотов...</p>';
            slotsContainer.style.display = 'block';
            slotsContainer.scrollIntoView({{ behavior: 'smooth' }});
            
            loadSlots(masterId, serviceId, serviceName, price, duration);
        }}
        
        async function loadSlots(masterId, serviceId, serviceName, price, duration) {{
            const datePicker = document.getElementById('datePicker-' + masterId);
            const dateStr = datePicker ? datePicker.value : new Date().toISOString().split('T')[0];
            const slotGrid = document.getElementById('slot-grid-' + masterId);
            
            slotGrid.innerHTML = '<p style="color:var(--color-muted);font-size:0.85rem">Загружаем слоты...</p>';
            
            try {{
                const response = await fetch(`/api/v1/bookings/available/${{masterId}}?date=${{dateStr}}&service_id=${{serviceId}}`);
                const data = await response.json();
                
                if (data.slots && data.slots.length > 0) {{
                    const now = new Date();
                    const todayStr = new Date().toISOString().split('T')[0];
                    let slotsHtml = '';
                    for (const slot of data.slots) {{
                        const slotDate = new Date(slot);
                        if (dateStr === todayStr && slotDate < now) continue;
                        
                        const timeStr = slotDate.toTimeString().slice(0, 5);
                        const fullSlot = slotDate.getFullYear() + '-' + 
                            String(slotDate.getMonth() + 1).padStart(2, '0') + '-' + 
                            String(slotDate.getDate()).padStart(2, '0') + 'T' + 
                            String(slotDate.getHours()).padStart(2, '0') + ':' + 
                            String(slotDate.getMinutes()).padStart(2, '0');
                        
                        slotsHtml += `<span class="slot-btn" onclick="selectSlot(this, '${{fullSlot}}', ${{masterId}}, ${{serviceId}}, '${{serviceName}}', ${{price}})">${{timeStr}}</span>`;
                    }}
                    
                    if (slotsHtml) {{
                        slotGrid.innerHTML = slotsHtml;
                    }} else {{
                        slotGrid.innerHTML = '<p class="no-slots">Нет свободных окон на выбранную дату.</p>';
                    }}
                }} else {{
                    slotGrid.innerHTML = `<p class="no-slots">${{data.message || 'Нет свободных окон на эту дату.'}}</p>`;
                }}
            }} catch (err) {{
                slotGrid.innerHTML = '<p class="no-slots">Ошибка загрузки. Попробуйте позже.</p>';
            }}
        }}
        
        function selectSlot(el, time, masterId, serviceId, serviceName, price) {{
            document.querySelectorAll('.slot-btn').forEach(b => b.classList.remove('selected'));
            el.classList.add('selected');
            selectedSlot = time;
            selectedMasterId = masterId;
            selectedServiceId = serviceId;
            document.getElementById('bookPanel').classList.add('active');
            document.getElementById('panelMaster').textContent = `${{serviceName}} · ${{price}} ₽`;
            document.getElementById('panelTime').textContent = time.replace('T', ' ');
        }}
        
        function confirmBooking() {{
            if (!selectedSlot || !selectedMasterId || !selectedServiceId) {{
                alert('Выберите услугу и время!');
                return;
            }}
            window.location.href = `/book?master_id=${{selectedMasterId}}&service_id=${{selectedServiceId}}&time=${{encodeURIComponent(selectedSlot)}}`;
        }}
    </script>
</body>
</html>"""
    
    return html