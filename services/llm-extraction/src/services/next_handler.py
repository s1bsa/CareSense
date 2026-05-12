import logging
import os
import pandas as pd
from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI

from src.models.requests import NextRequest
from src.services.deduction_service import call_deduction_service
from src.services.dialogue_service import pick_next_question_from_top10
from src.services.llm_service import (
    generate_disease_explanation,
    llm_extract_symptoms,
)
from src.utils.config_loader import settings
from src.utils.helpers import fallback_extract_symptoms, normalize_choice


SESSIONS: Dict[str, Dict[str, Any]] = {}
logger = logging.getLogger(__name__)

# Cached disease master dataframe
_disease_df: Optional[pd.DataFrame] = None


def _get_disease_df() -> pd.DataFrame:
    global _disease_df
    if _disease_df is None:
        _disease_df = pd.read_csv("data/disease_master.csv")
    return _disease_df


def _lookup_disease_field(disease_name: str, field: str) -> str:
    """Look up a field for a disease from disease_master.csv."""
    try:
        df = _get_disease_df()
        row = df[df["disease_name"] == disease_name]
        if not row.empty:
            value = row.iloc[0].get(field, "")
            if pd.notna(value) and str(value).strip():
                return str(value).strip()
    except Exception as exc:
        logger.warning("Could not load disease field '%s': %r", field, exc)
    return ""


def _get_recommended_tests(disease_name: str) -> str:
    return _lookup_disease_field(disease_name, "recommended_tests")


def _get_context_summary(disease_name: str) -> str:
    return _lookup_disease_field(disease_name, "context_summary")


def _build_static_explanation(
    disease_name: str,
    present_symptoms: List[str],
    absent_symptoms: List[str],
    context_summary: str,
) -> str:
    """Build a plain-text explanation without an LLM, using CSV data and symptom lists."""
    parts = []

    if context_summary:
        parts.append(context_summary)
    else:
        parts.append(f"{disease_name.capitalize()} was identified as the top candidate based on your reported symptoms.")

    if present_symptoms:
        symptom_list = ", ".join(present_symptoms)
        parts.append(f"Symptoms you reported that match this condition: {symptom_list}.")

    if absent_symptoms:
        absent_list = ", ".join(absent_symptoms)
        parts.append(f"Symptoms associated with this condition that you did not report: {absent_list}.")

    parts.append("This is a probabilistic result — please consult a doctor for a proper assessment.")
    return " ".join(parts)


def _get_top_candidate(deduction_response: Dict[str, Any]) -> Dict[str, Any]:
    top10 = deduction_response.get("top10", [])
    if isinstance(top10, list) and top10:
        return top10[0]
    return {}


async def handle_next(request: NextRequest, llm: ChatOpenAI) -> Dict[str, Any]:
    sid = request.sessionId or os.urandom(settings['session']['id_length']).hex()

    if sid not in SESSIONS:
        SESSIONS[sid] = {"asked_dialogue": [], "deduction_session": None}

    state = SESSIONS[sid]
    answer_text = (request.answer or "").strip()
    choice = normalize_choice(answer_text)

    if choice is not None:
        extracted = []
    else:
        extracted = fallback_extract_symptoms(answer_text)
        if not extracted:
            extracted = await llm_extract_symptoms(answer_text, llm)

    top10: List[Dict[str, Any]] = []
    ded: Dict[str, Any] = {}
    try:
        ded = await call_deduction_service(
            deduction_session_id=state.get("deduction_session"),
            answer_text=answer_text,
            extracted_symptoms=extracted,
            choice=choice,
        )
        if ded.get("sessionId"):
            state["deduction_session"] = ded["sessionId"]

        top10 = ded.get("top10", []) or []
    except Exception as exc:
        logger.warning("Deduction service error: %r", exc)

    explanation = ""
    recommended_tests = ""
    is_end = ded.get("end", False)

    if is_end:
        top_candidate = _get_top_candidate(ded)
        top_disease = top_candidate.get("disease", "")

        if top_disease:
            present_symptoms = ded.get("presentSymptoms", [])
            absent_symptoms = ded.get("absentSymptoms", [])

            # Always fetch from CSV first (no API key needed)
            recommended_tests = _get_recommended_tests(top_disease)
            context_summary = _get_context_summary(top_disease)

            # Try LLM explanation
            explanation = await generate_disease_explanation(
                top_disease,
                top_candidate.get("score", 0),
                present_symptoms,
                absent_symptoms,
                llm,
            )

            # Fall back to static explanation built from CSV + symptom lists
            if not explanation:
                explanation = _build_static_explanation(
                    top_disease, present_symptoms, absent_symptoms, context_summary
                )

            logger.debug("Explanation ready for: %s (llm=%s)", top_disease, llm is not None)

    next_q = ded.get("nextQuestionText") if isinstance(ded, dict) else None
    if not next_q:
        next_q = pick_next_question_from_top10(top10, state["asked_dialogue"])

    if choice is not None:
        assistant_note = None
    elif extracted:
        assistant_note = settings['dialogue']['assistant_notes']['extracted'].format(symptoms=extracted)
    else:
        assistant_note = settings['dialogue']['assistant_notes']['none']

    return {
        "sessionId": sid,
        "nextQuestionId": "done" if is_end else "q_dynamic",
        "nextQuestionText": next_q,
        "quickOptions": settings['dialogue']['default_quick_options'],
        "assistantNote": assistant_note,
        "top10": top10,
        "explanation": explanation,
        "recommendedTests": recommended_tests,
    }
