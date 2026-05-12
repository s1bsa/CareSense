"""Pydantic request body models for API endpoints."""

from typing import Optional
from pydantic import BaseModel


class NextRequest(BaseModel):
    """Request body for the /next-step endpoint."""

    sessionId: Optional[str] = None
    answer: str
    questionId: Optional[str] = None