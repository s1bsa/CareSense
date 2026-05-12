"""Next-step API routes (process answer, return next question)."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from langchain_openai import ChatOpenAI
import httpx

from src.services.next_handler import handle_next
from src.models.requests import NextRequest
from src.services.llm_service import get_llm
from src.services.next_handler import handle_next, SESSIONS
from src.utils.config_loader import settings

router = APIRouter(tags=["Next"])


@router.post("/next-step")
async def next_step_alias(request: NextRequest, llm: ChatOpenAI = Depends(get_llm)):
    """
    Process the user's answer and return the next question.
    """
    data = await handle_next(request, llm)
    return JSONResponse(status_code=200, content=data)

#sends message to reset beliefs in backend
@router.post("/reset")
async def reset_session():
    SESSIONS.clear()
    async with httpx.AsyncClient(timeout=settings['services']['timeout']) as client:
        url = settings['services']['reset_url']
        response = await client.post(url)
        return JSONResponse(status_code=200, content=response.json())