# app/services/uploads.py
"""Загрузка изображений (аватары, фото салона) — задача 1 от команды.

Безопасность (загрузка файлов — классическая дыра, поэтому строго):
- тип проверяется по СОДЕРЖИМОМУ (Pillow открывает и валидирует), не по
  расширению и не по Content-Type из запроса — их контролирует атакующий;
- файл ПЕРЕСОХРАНЯЕТСЯ: decode → resize → encode в JPEG. Это уничтожает
  всё, что можно спрятать в метаданных/EXIF/полиглот-файле — на диск
  попадают только наши собственные пиксели;
- имя файла — uuid4, от пользователя не берётся ни байта пути;
- лимит размера читается до обработки, чтобы не декодировать гигабайты.

Хранилище: локальный каталог settings.UPLOADS_DIR (volume в compose).
ВРЕМЕННО до S3 Timeweb — интерфейс сводится к _store(), при переезде
меняется только он.
"""
import io
import uuid
from pathlib import Path

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.config import settings

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 МБ до обработки
JPEG_QUALITY = 85

# Максимальная сторона после ресайза по назначению
MAX_SIDE = {"avatars": 512, "salons": 1600, "masters": 1600, "reviews": 1600}


class UploadError(ValueError):
    """Файл не подходит: не изображение, повреждён или слишком большой."""


def process_image(data: bytes, kind: str) -> bytes:
    """Валидирует и пересохраняет картинку в чистый JPEG. Кидает UploadError."""
    if len(data) > MAX_UPLOAD_BYTES:
        raise UploadError("Файл больше 5 МБ")
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()  # структурная проверка формата
        img = Image.open(io.BytesIO(data))  # verify() портит объект — открываем заново
        img = img.convert("RGB")  # убирает альфу/палитры/EXIF-ориентацию не трогаем
    except (UnidentifiedImageError, OSError, ValueError) as e:
        raise UploadError("Файл не является изображением") from e

    max_side = MAX_SIDE.get(kind, 1600)
    img.thumbnail((max_side, max_side))  # пропорционально, только уменьшение

    out = io.BytesIO()
    img.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return out.getvalue()


def _store(content: bytes, kind: str) -> str:
    """Кладёт готовый JPEG в хранилище, возвращает публичный URL-путь."""
    name = f"{uuid.uuid4()}.jpg"
    directory = Path(settings.UPLOADS_DIR) / kind
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_bytes(content)
    return f"/uploads/{kind}/{name}"


async def save_image(file: UploadFile, kind: str) -> str:
    """Полный цикл: прочитать (с лимитом), обеззаразить, сохранить. → URL."""
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    return _store(process_image(data, kind), kind)


def delete_stored(url: str) -> None:
    """Удаляет файл по нашему URL (best-effort: файла может уже не быть).

    Путь собирается только из валидированного хвоста /uploads/<kind>/<uuid>.jpg —
    произвольные пути сюда не пролезают.
    """
    try:
        parts = Path(url).parts  # ('/', 'uploads', kind, name)
        if len(parts) == 4 and parts[1] == "uploads":
            target = Path(settings.UPLOADS_DIR) / parts[2] / parts[3]
            target.unlink(missing_ok=True)
    except OSError:
        pass
