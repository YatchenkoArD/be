# app/web/pages/business/tabs/reviews.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import (
    Master, User as UserModel, Review, ReviewPhoto, ReviewTargetType, MasterPhoto, PhotoReport, PhotoReportStatus,
)

TARGET_LABELS = {
    ReviewTargetType.MASTER: "Мастер",
    ReviewTargetType.SALON: "Салон",
    ReviewTargetType.STAFF: "Сотрудник",
}


async def render_reviews_tab(db: AsyncSession, reviews, salon, can_moderate: bool = False) -> str:
    """Вкладка Отзывы: список с тегами (тип цели/подтверждение), фото,
    фильтры, и — для тех, у кого есть manage_reviews — очередь жалоб."""
    reviews_rows = ""
    for r in reviews:
        client_result = await db.execute(select(UserModel).where(UserModel.id == r.client_id))
        client_user = client_result.scalar_one_or_none()
        client_name = client_user.full_name if client_user else "Клиент"

        target_name = "—"
        if r.target_type == ReviewTargetType.MASTER and r.master_id:
            master_result = await db.execute(select(Master).where(Master.id == r.master_id))
            master = master_result.scalar_one_or_none()
            if master:
                mu = (await db.execute(select(UserModel).where(UserModel.id == master.user_id))).scalar_one_or_none()
                target_name = mu.full_name if mu else "Мастер"
        elif r.target_type == ReviewTargetType.STAFF and r.staff_user_id:
            su = (await db.execute(select(UserModel).where(UserModel.id == r.staff_user_id))).scalar_one_or_none()
            target_name = su.full_name if su else "Сотрудник"
        else:
            target_name = "Салон в целом"

        stars = "⭐" * r.rating + "☆" * (5 - r.rating)
        date_str = r.created_at.strftime("%d.%m.%Y") if r.created_at else ""
        verified_html = (
            '<span class="badge-tag" style="background:#dcfce7;color:#166534">✅ Подтверждено</span>'
            if r.is_verified else
            '<span class="badge-tag" style="background:#f3f4f6;color:var(--color-muted)">Без подтверждения</span>'
        )

        photos = (await db.execute(select(ReviewPhoto).where(ReviewPhoto.review_id == r.id))).scalars().all()
        photos_html = "".join(
            f'<img src="{p.url}" alt="" loading="lazy" style="width:48px;height:48px;object-fit:cover;'
            f'border-radius:0.4rem;margin-right:0.25rem">'
            for p in photos
        )

        reviews_rows += f"""
        <tr data-target-type="{r.target_type.value}" data-verified="{'1' if r.is_verified else '0'}">
            <td><strong>{client_name}</strong></td>
            <td>{TARGET_LABELS[r.target_type]}: {target_name}</td>
            <td>{verified_html}</td>
            <td>{stars}</td>
            <td style="max-width:260px">{r.comment or 'Без комментария'}</td>
            <td>{photos_html or '—'}</td>
            <td style="font-size:0.85rem;color:var(--color-muted)">{date_str}</td>
        </tr>"""

    moderation_html = ""
    if can_moderate:
        # Жалобы на фото из портфолио мастеров ЭТОГО салона
        master_reports_result = await db.execute(
            select(PhotoReport, MasterPhoto)
            .join(MasterPhoto, MasterPhoto.id == PhotoReport.master_photo_id)
            .join(Master, Master.id == MasterPhoto.master_id)
            .where(PhotoReport.status == PhotoReportStatus.PENDING, Master.salon_id == salon.id)
        )
        # Жалобы на фото из отзывов ЭТОГО салона
        review_reports_result = await db.execute(
            select(PhotoReport, ReviewPhoto)
            .join(ReviewPhoto, ReviewPhoto.id == PhotoReport.review_photo_id)
            .join(Review, Review.id == ReviewPhoto.review_id)
            .where(PhotoReport.status == PhotoReportStatus.PENDING, Review.salon_id == salon.id)
        )
        report_pairs = list(master_reports_result.all()) + list(review_reports_result.all())

        report_rows = ""
        for rep, photo in report_pairs:
            report_rows += f"""
            <div class="card" style="display:flex;gap:1rem;align-items:center;padding:1rem;margin-bottom:0.75rem">
                <img src="{photo.url}" alt="" style="width:80px;height:80px;object-fit:cover;border-radius:0.5rem">
                <div style="flex:1">
                    <p style="font-size:0.85rem;color:var(--color-muted)">{rep.reason or 'Без указания причины'}</p>
                </div>
                <button class="btn-primary" style="font-size:0.8rem;padding:0.4rem 0.9rem" onclick="resolvePhotoReport({rep.id})">Удалить фото</button>
                <button class="btn-outline" style="font-size:0.8rem;padding:0.4rem 0.9rem" onclick="dismissPhotoReport({rep.id})">Оставить</button>
            </div>"""

        moderation_html = f"""
        <div class="card" style="margin-bottom:1.5rem;border:2px solid #f59e0b">
            <h3 style="margin-bottom:1rem">⚠️ Жалобы на фото ({len(report_pairs)})</h3>
            {report_rows or '<p class="text-muted">Жалоб нет</p>'}
        </div>
        <script>
            async function resolvePhotoReport(id) {{
                if (!confirm('Удалить это фото?')) return;
                const res = await fetch(`/api/v1/reports/${{id}}/resolve`, {{ method: 'POST' }});
                if (res.ok) location.reload(); else alert('Не удалось обработать жалобу');
            }}
            async function dismissPhotoReport(id) {{
                const res = await fetch(`/api/v1/reports/${{id}}/dismiss`, {{ method: 'POST' }});
                if (res.ok) location.reload(); else alert('Не удалось обработать жалобу');
            }}
        </script>
        """

    return f"""
    <div id="tab-reviews" class="tab-content">
        <div class="card" style="margin-bottom:1.5rem">
            <div class="rating-summary">
                <div>
                    <div class="rating-big">{salon.rating}</div>
                    <div class="rating-stars">{"⭐" * int(salon.rating)}{"☆" * (5 - int(salon.rating))}</div>
                    <div style="font-size:0.85rem;color:var(--color-muted)">{salon.reviews_count} отзывов</div>
                </div>
            </div>
        </div>
        {moderation_html}
        <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:1rem">
            <button class="btn-outline reviews-filter-btn active" data-filter="all" onclick="reviewsTabFilter('all', this)">Все</button>
            <button class="btn-outline reviews-filter-btn" data-filter="master" onclick="reviewsTabFilter('master', this)">О мастерах</button>
            <button class="btn-outline reviews-filter-btn" data-filter="salon" onclick="reviewsTabFilter('salon', this)">О салоне</button>
            <button class="btn-outline reviews-filter-btn" data-filter="staff" onclick="reviewsTabFilter('staff', this)">О сотрудниках</button>
            <button class="btn-outline reviews-filter-btn" data-filter="verified" onclick="reviewsTabFilter('verified', this)">Только подтверждённые</button>
        </div>
        <div class="card" style="overflow-x:auto">
            <table>
                <thead>
                    <tr><th>Клиент</th><th>О чём</th><th>Статус</th><th>Оценка</th><th>Комментарий</th><th>Фото</th><th>Дата</th></tr>
                </thead>
                <tbody id="reviewsTabBody">
                    {reviews_rows or '<tr><td colspan="7" style="text-align:center;padding:2rem;color:var(--color-muted)">Пока нет отзывов</td></tr>'}
                </tbody>
            </table>
        </div>
        <script>
            function reviewsTabFilter(kind, btn) {{
                document.querySelectorAll('.reviews-filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                document.querySelectorAll('#reviewsTabBody tr[data-target-type]').forEach(el => {{
                    let show = true;
                    if (kind === 'verified') show = el.dataset.verified === '1';
                    else if (kind !== 'all') show = el.dataset.targetType === kind;
                    el.style.display = show ? '' : 'none';
                }});
            }}
        </script>
    </div>"""
