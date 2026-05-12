import logging
import json
import pandas as pd
from typing import List, Optional

from fastapi import Request
from langchain_openai import ChatOpenAI

from src.prompts.templates import (
    disease_explanation_prompt,
    extraction_prompt,
    question_prompt,
)
from src.utils.helpers import fallback_extract_symptoms, safe_json_list
from src.utils.config_loader import symptoms as symptom_keywords_list


logger = logging.getLogger(__name__)


async def get_llm(request: Request) -> ChatOpenAI:
    return request.app.state.llm


async def get_symptom_to_question(symptom: str, llm: ChatOpenAI) -> str:
    if llm is None:
        return f"Do you have {symptom}?"

    chain = question_prompt | llm
    response = await chain.ainvoke({"symptom": symptom})
    return response.content



async def llm_extract_symptoms(answer_text: str, llm: Optional[ChatOpenAI] = None) -> List[str]:
    if llm is None:
        return fallback_extract_symptoms(answer_text)

    logger.debug("Invoking LLM extraction for answer text")
    try:

        chain = extraction_prompt | llm
        response = await chain.ainvoke({
            "answer_text": answer_text,
            "symptoms": "\n".join(symptom_keywords_list),
        })
        extracted = safe_json_list(response.content or "")

        if extracted:
            logger.debug("LLM extracted %d symptom candidates", len(extracted))
            return extracted

        logger.debug("LLM returned no symptoms; falling back to keyword extraction")
        return fallback_extract_symptoms(answer_text)
    except Exception as exc:
        logger.warning(
            "LLM extraction failed; falling back to keyword extraction: %r",
            exc,
        )
        return fallback_extract_symptoms(answer_text)


async def generate_disease_explanation(
    disease: str,
    probability: float,
    present_symptoms: List[str],
    absent_symptoms: List[str],
    llm: Optional[ChatOpenAI] = None,
) -> str:
    """Generate a patient-friendly explanation of the current leading disease."""
    if llm is None:
        return ""

    df = pd.read_csv("data/disease_master.csv")
    disease_info = df[df["disease_name"] == disease]
    
    if not disease_info.empty:
        context = disease_info.iloc[0].to_dict()
    else:
        context = {}

    input_data = {
        "disease_name": disease,
        "probability": float(probability),
        "context_summary": context.get("context_summary", ""),
        "typical_symptoms": context.get("symptoms", ""),
        "present_symptoms": present_symptoms,
        "absent_symptoms": absent_symptoms,
        "urgency": context.get("urgency_classification", ""),
        "recommended_tests": context.get("recommended_tests", ""),
    }

    chain = disease_explanation_prompt | llm
    response = await chain.ainvoke({
        "input_json": json.dumps(input_data, ensure_ascii=False, indent=2)
    })
    return response.content
