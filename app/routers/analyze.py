from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.services.openai_service import analyze_avito_listing


router = APIRouter(tags=["analyze"])

MIN_FILES = 1
MAX_FILES = 10
MAX_FILE_BYTES = 5 * 1024 * 1024

ALLOWED_CONTENT_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
    }
)


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    s = value.strip()
    return s if s else None


@router.post("/analyze")
async def analyze(
    files: Annotated[list[UploadFile] | None, File()] = None,
    niche: Annotated[str | None, Form()] = None,
    audience: Annotated[str | None, Form()] = None,
    comment: Annotated[str | None, Form()] = None,
):
    """
    Принимает multipart/form-data: files[] (1–10 изображений), niche, audience, comment.
    """
    if not files:
        raise HTTPException(
            status_code=400,
            detail="Загрузите хотя бы один скриншот объявления (до 10 файлов).",
        )
    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Слишком много файлов: максимум {MAX_FILES}.",
        )

    image_parts: list[tuple[bytes, str | None, str | None]] = []

    for upload in files:
        raw = await upload.read()
        if len(raw) > MAX_FILE_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"Файл «{upload.filename or 'без имени'}» больше 5 МБ. "
                "Сожмите скриншот или выберите другой файл.",
            )
        if len(raw) == 0:
            raise HTTPException(
                status_code=400,
                detail=f"Файл «{upload.filename or 'без имени'}» пустой.",
            )

        ctype = (upload.content_type or "").split(";")[0].strip().lower()
        if ctype and ctype not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=400,
                detail="Допустимы только изображения: JPEG, PNG, WebP или GIF.",
            )
        if not ctype:
            name = (upload.filename or "").lower()
            if not any(
                name.endswith(ext)
                for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif")
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Не удалось определить тип изображения. "
                    "Используйте JPEG, PNG, WebP или GIF.",
                )

        image_parts.append((raw, upload.filename, upload.content_type))

    try:
        result = analyze_avito_listing(
            image_parts,
            niche=_normalize_optional(niche),
            audience=_normalize_optional(audience),
            comment=_normalize_optional(comment),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=502,
            detail=str(e),
        ) from e
    except RuntimeError as e:
        raise HTTPException(
            status_code=502,
            detail=str(e),
        ) from e

    return result.model_dump()
