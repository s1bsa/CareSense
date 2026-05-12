import json
from typing import List, Optional
from src.utils.config_loader import settings, symptoms as symptom_keywords_list


def normalize_choice(text: str) -> Optional[str]:
    normalized = (text or "").strip().lower()
    
    yes_set = set(settings['normalization']['yes_set'])
    no_set = set(settings['normalization']['no_set'])
    maybe_set = set(settings['normalization']['maybe_set'])

    if normalized in yes_set:
        return "yes"
    if normalized in no_set:
        return "no"
    if normalized in maybe_set:
        return "maybe"
    return None


def fallback_extract_symptoms(text: str) -> List[str]:
    lower = (text or "").lower()
    return list(dict.fromkeys(kw for kw in symptom_keywords_list if kw in lower))


def safe_json_list(raw: str) -> List[str]:
    if not raw:
        return []

    raw = raw.strip()

    try:
        obj = json.loads(raw)
        if isinstance(obj, list):
            return [x for x in obj if isinstance(x, str)]
    except Exception:
        pass

    start = raw.find("[")
    end = raw.rfind("]")
    if start != -1 and end != -1 and end > start:
        snippet = raw[start : end + 1]
        try:
            obj = json.loads(snippet)
            if isinstance(obj, list):
                return [x for x in obj if isinstance(x, str)]
        except Exception:
            return []

    return []
