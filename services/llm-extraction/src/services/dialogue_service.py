from typing import Any, Dict, List
from src.utils.config_loader import settings

def pick_next_question_from_top10(
    top10: List[Dict[str, Any]],
    asked: List[str],
) -> str:
    first_q = settings['dialogue']['first_question']
    fallback_q = settings['dialogue']['fallback_question']
    mapping = settings['dialogue']['disease_mapping']

    if not top10:
        return first_q

    top_disease = (top10[0].get("disease", "") or "").lower()
    candidates: List[str] = []

    for disease, symptoms in mapping.items():
        if disease in top_disease:
            candidates = symptoms
            break

    for symptom in candidates:
        if symptom not in asked:
            asked.append(symptom)
            return settings['dialogue']['question_template'].format(symptom=symptom)

    return fallback_q
