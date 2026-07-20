# app/api/v1/endpoints/reviews.py
from fastapi import APIRouter, Depends, Request, Form, File, UploadFile
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.models import ReviewPhoto, ReviewTargetType
from app.services.review_service import ReviewService, ReviewError
from app.services.notifications import notify_new_review
from app.services.uploads import UploadError, save_image

router = APIRouter()

MAX_REVIEW_PHOTOS = 5
_TARGET_TYPES = {t.value: t for t in ReviewTargetType}


@router.post("/reviews/create")
@limiter.limit("5/hour")  # лимит по IP — против спама отзывами
async def create_review_web(
    request: Request,
    salon_id: int = Form(...),
    target_type: str = Form("master"),
    rating: int = Form(...),
    comment: str = Form(""),
    master_id: int = Form(None),
    staff_user_id: int = Form(None),
    files: list[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db),
):
    """Создание отзыва (любым зарегистрированным пользователем) + до
    MAX_REVIEW_PHOTOS фото. Вся проверка прав/состояния — в ReviewService;
    подтверждение реальным визитом сервис проставляет сам."""
    from app.web.auth import get_current_user_from_cookie

    user = await get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    parsed_type = _TARGET_TYPES.get(target_type)
    if parsed_type is None:
        return HTMLResponse(content="<h1>Некорректный тип отзыва</h1>", status_code=400)

    if len(files) > MAX_REVIEW_PHOTOS:
        return HTMLResponse(content=f"<h1>Не больше {MAX_REVIEW_PHOTOS} фото на отзыв</h1>", status_code=400)

    try:
        review = await ReviewService.create_review(
            db,
            client_id=user.id,
            salon_id=salon_id,
            target_type=parsed_type,
            master_id=master_id,
            staff_user_id=staff_user_id,
            rating=rating,
            comment=comment,
        )
    except ReviewError as e:
        return HTMLResponse(content=f"<h1>{e.message}</h1>", status_code=e.status)

    saved_any = False
    for file in files:
        if not file.filename:
            continue
        try:
            url = await save_image(file, "reviews")
        except UploadError:
            continue  # битый файл молча пропускаем — сам отзыв уже создан
        db.add(ReviewPhoto(review_id=review.id, url=url))
        saved_any = True
    if saved_any:
        await db.commit()

    await notify_new_review(db, review)
    return RedirectResponse(url=f"/salons/{salon_id}?reviewed=1", status_code=302)
