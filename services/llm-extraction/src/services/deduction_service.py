"""HTTP client for the deduction service (rank/top-10 questions)."""

import httpx
from typing import Any, Dict, List, Optional

from src.utils.config_loader import settings


async def call_deduction_service(
    deduction_session_id: Optional[str],
    answer_text: str,
    extracted_symptoms: List[str],
    choice: Optional[str],
) -> Dict[str, Any]:
    """Call the deduction service to rank questions and get top-10 suggestions."""
    payload = {
        "sessionId": deduction_session_id,
        "answer": answer_text,
        "extractedSymptoms": extracted_symptoms,
        "choice": choice,
    }

    async with httpx.AsyncClient(timeout=settings['services']['timeout']) as client:
        url = settings['services']['deduction_url']
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()
