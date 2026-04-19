import json
import re
from typing import Any, Self

from pydantic import BaseModel, Field, field_validator, model_validator


class ScoresByCriteria(BaseModel):
    headline: int = Field(ge=1, le=10)
    price: int = Field(ge=1, le=10)
    description: int = Field(ge=1, le=10)
    structure: int = Field(ge=1, le=10)
    offer_clarity: int = Field(ge=1, le=10)
    benefit: int = Field(ge=1, le=10)
    trust: int = Field(ge=1, le=10)
    photos: int = Field(ge=1, le=10)
    audience_fit: int = Field(ge=1, le=10)


def score_to_label(score: int) -> str:
    """Фиксированная словесная интерпретация общей оценки."""
    if 1 <= score <= 3:
        return "слабое объявление"
    if 4 <= score <= 6:
        return "среднее объявление"
    if 7 <= score <= 8:
        return "хорошее объявление"
    return "сильное объявление"


FINAL_OFFER_FIXED = (
    "Если вы хотите улучшить своё объявление, получить более сильную продающую версию "
    "или подробную консультацию, рекомендуем обратиться к специалистам."
)


class AnalysisResult(BaseModel):
    score_overall: int = Field(ge=1, le=10)
    score_label: str = ""
    scores_by_criteria: ScoresByCriteria
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]
    improved_text_short: str
    final_summary: str
    final_offer: str

    @model_validator(mode="after")
    def canonical_score_label_and_offer(self) -> Self:
        """score_label и final_offer приводятся к эталону (модель могла ошибиться в формулировке)."""
        object.__setattr__(self, "score_label", score_to_label(self.score_overall))
        object.__setattr__(self, "final_offer", FINAL_OFFER_FIXED)
        return self

    @field_validator(
        "strengths",
        "weaknesses",
        "recommendations",
        mode="before",
    )
    @classmethod
    def ensure_list_of_str(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        return [str(v).strip()] if str(v).strip() else []


def _strip_code_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        lines = t.split("\n")
        if len(lines) >= 2 and lines[0].startswith("```"):
            inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
            t = "\n".join(inner)
    return t.strip()


def parse_model_json(raw_text: str) -> AnalysisResult:
    """
    Извлекает JSON из ответа модели и валидирует через Pydantic.
    Бросает ValueError с понятным текстом при невалидных данных.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("Модель вернула пустой ответ.")

    cleaned = _strip_code_fence(raw_text)

    json_match = re.search(r"\{[\s\S]*\}", cleaned)
    if json_match:
        cleaned = json_match.group(0)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(
            "Не удалось разобрать ответ модели как JSON. "
            "Попробуйте отправить запрос ещё раз."
        ) from e

    if not isinstance(data, dict):
        raise ValueError("Ответ модели должен быть JSON-объектом.")

    try:
        return AnalysisResult.model_validate(data)
    except Exception as e:
        raise ValueError(
            "Ответ модели не соответствует ожидаемой структуре (оценки, списки, поля). "
            "Попробуйте ещё раз или смените скриншоты."
        ) from e
