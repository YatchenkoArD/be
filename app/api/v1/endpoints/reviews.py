# app/api/v1/endpoints/reviews.py
from fastapi import APIRouter, Depends, Request, Form, File, UploadFile, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.models import Review, ReviewPhoto, ReviewTargetType
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
    booking_id: int = Form(None),
    files: list[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db),
):
    """Создание отзыва с привязкой к booking_id."""
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
            booking_id=booking_id,
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
            continue
        db.add(ReviewPhoto(review_id=review.id, url=url))
        saved_any = True
    if saved_any:
        await db.commit()

    await notify_new_review(db, review)
    return RedirectResponse(url=f"/bookings?reviewed=1", status_code=302)


@router.get("/reviews/{review_id}")
async def get_review(
    review_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Получить отзыв по ID (только для владельца)."""
    from app.web.auth import get_current_user_from_cookie
    user = await get_current_user_from_cookie(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    review = (await db.execute(select(Review).where(Review.id == review_id))).scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Отзыв не найден")
    if review.client_id != user.id:
        raise HTTPException(status_code=403, detail="Это не ваш отзыв")

    return {
        "id": review.id,
        "rating": review.rating,
        "comment": review.comment,
        "salon_id": review.salon_id,
        "master_id": review.master_id,
        "target_type": review.target_type.value,
        "booking_id": review.booking_id,
    }


@router.patch("/reviews/{review_id}")
async def update_review(
    review_id: int,
    request: Request,
    rating: int = Form(...),
    comment: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    """Обновить отзыв (только для владельца)."""
    from app.web.auth import get_current_user_from_cookie
    user = await get_current_user_from_cookie(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    review = (await db.execute(select(Review).where(Review.id == review_id))).scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Отзыв не найден")
    if review.client_id != user.id:
        raise HTTPException(status_code=403, detail="Это не ваш отзыв")

    review.rating = rating
    review.comment = comment
    await db.commit()

    return {"status": "updated", "id": review.id}