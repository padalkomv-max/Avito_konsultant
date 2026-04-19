import base64
from pathlib import Path

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from app.config import settings
from app.schemas.analysis import AnalysisResult, parse_model_json


KNOWLEDGE_PATH = Path(__file__).resolve().parent.parent / "knowledge" / "knowledge.txt"


def load_knowledge_text() -> str:
    if not KNOWLEDGE_PATH.exists():
        return ""
    return KNOWLEDGE_PATH.read_text(encoding="utf-8")


def _mime_for_image(filename: str | None, content_type: str | None) -> str:
    if content_type and content_type.startswith("image/"):
        ct = content_type.split(";")[0].strip().lower()
        if ct in (
            "image/jpeg",
            "image/png",
            "image/webp",
            "image/gif",
        ):
            return ct
    name = (filename or "").lower()
    if name.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if name.endswith(".png"):
        return "image/png"
    if name.endswith(".webp"):
        return "image/webp"
    if name.endswith(".gif"):
        return "image/gif"
    return "image/jpeg"


def _build_instruction_block(
    niche: str | None,
    audience: str | None,
    comment: str | None,
    knowledge: str,
) -> str:
    parts = [
        "Ты эксперт по объявлениям на Avito. Пользователь прислал скриншоты объявления.",
        "Проанализируй только то, что видно на скриншотах и что явно следует из контекста. "
        "Не выдумывай факты. Если информации мало — так и укажи в слабых сторонах и рекомендациях.",
        "",
        "### Шкала общей оценки score_overall (1–10)",
        "1–3: слабое объявление; неясно предложение; нет структуры и доверия.",
        "4–6: средний уровень; слабый заголовок; мало конкретики; нет акцента на результате.",
        "7–8: хорошо; есть структура и понятное предложение; можно усилить формулировки.",
        "9–10: сильное; ясно что, кому, какой результат; доверие; текст читается.",
        "",
        "### Поле score_label (строго по score_overall)",
        'Если score_overall 1–3 — ровно: "слабое объявление".',
        'Если 4–6 — ровно: "среднее объявление".',
        'Если 7–8 — ровно: "хорошее объявление".',
        'Если 9–10 — ровно: "сильное объявление".',
        "",
        "### Критерии scores_by_criteria (каждый 1–10)",
        "- headline — заголовок привлекает и отражает суть.",
        "- price — понятно ли как подана цена.",
        "- description — полнота и ясность описания услуги.",
        "- structure — логика, абзацы, удобство чтения.",
        "- offer_clarity — понятно ЧТО продаётся (услуга без лишних «выгод»).",
        "- benefit — понятно ЗАЧЕМ клиенту (результат, выгода).",
        "- trust — доверие (опыт, гарантии, примеры, конкретика).",
        "- photos — помогают ли фото понять услугу (польза, не просто наличие).",
        "- audience_fit — соответствие объявления ЦА (заявленной или предполагаемой).",
        "",
        "### База знаний Avito (ориентиры для рекомендаций)",
        knowledge.strip() if knowledge else "(файл базы знаний пуст)",
        "",
    ]
    if niche and niche.strip():
        parts.append(f"Ниша (от пользователя): {niche.strip()}")
    if audience and audience.strip():
        parts.append(f"Целевая аудитория (от пользователя): {audience.strip()}")
    if comment and comment.strip():
        parts.append(f"Комментарий пользователя: {comment.strip()}")
    parts.extend(
        [
            "",
            "Верни ТОЛЬКО один JSON-объект без текста до или после, без markdown. Поля:",
            '{"score_overall": number, "score_label": "...", "scores_by_criteria": {'
            '"headline": number, "price": number, "description": number, '
            '"structure": number, "offer_clarity": number, "benefit": number, '
            '"trust": number, "photos": number, "audience_fit": number}, '
            '"strengths": ["..."], "weaknesses": ["..."], "recommendations": ["..."], '
            '"improved_text_short": "...", "final_summary": "...", "final_offer": "..."}',
            "",
            "Разделяй смыслы: final_summary — только краткий вывод по ТЕКУЩЕМУ объявлению на основе анализа "
            "(без призыва обращаться к специалистам и без продажи услуг консультации). "
            'final_offer — отдельно: короткий стандартный текст-предложение помощи специалистов; '
            'используй ДОСЛОВНО эту формулировку: '
            '"Если вы хотите улучшить своё объявление, получить более сильную продающую версию или подробную консультацию, рекомендуем обратиться к специалистам."',
            "",
            "Правила: рекомендации короткие и конкретные; не переписывай объявление целиком; "
            "improved_text_short — не более 5–7 строк.",
        ]
    )
    return "\n".join(parts)


def analyze_avito_listing(
    image_parts: list[tuple[bytes, str | None, str | None]],
    niche: str | None = None,
    audience: str | None = None,
    comment: str | None = None,
) -> AnalysisResult:
    """
    image_parts: список (сырой байты файла, имя файла, content_type).

    Изображения передаются в OpenAI Responses API как input_image с data URL base64.
    """
    knowledge = load_knowledge_text()
    instruction = _build_instruction_block(niche, audience, comment, knowledge)

    content: list[dict] = [{"type": "input_text", "text": instruction}]
    for raw, filename, ctype in image_parts:
        mime = _mime_for_image(filename, ctype)
        b64 = base64.b64encode(raw).decode("ascii")
        content.append(
            {
                "type": "input_image",
                "image_url": f"data:{mime};base64,{b64}",
            }
        )

    key = (settings.openai_api_key or "").strip()
    if not key:
        raise RuntimeError(
            "Не задан ключ OPENAI_API_KEY. Создайте файл .env в корне проекта "
            "по образцу .env.example и укажите ключ API."
        )

    client = OpenAI(api_key=key)

    try:
        response = client.responses.create(
            model=settings.openai_model,
            input=[
                {
                    "role": "user",
                    "content": content,
                }
            ],
        )
    except APITimeoutError as e:
        raise RuntimeError(
            "Сервис анализа не ответил вовремя. Попробуйте ещё раз через минуту."
        ) from e
    except APIConnectionError as e:
        raise RuntimeError(
            "Нет соединения с сервисом OpenAI. Проверьте интернет и попробуйте снова."
        ) from e
    except APIStatusError as e:
        msg = "Сервис OpenAI временно недоступен."
        if e.response is not None:
            try:
                err = e.response.json().get("error", {})
                if isinstance(err, dict) and err.get("message"):
                    msg = f"Ошибка OpenAI: {err['message']}"
            except Exception:
                pass
        raise RuntimeError(msg) from e
    except Exception as e:
        raise RuntimeError(
            "Не удалось получить ответ от OpenAI. Попробуйте позже."
        ) from e

    raw_text = (response.output_text or "").strip()
    try:
        return parse_model_json(raw_text)
    except ValueError as e:
        raise ValueError(str(e)) from e
