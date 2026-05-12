import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from langchain_openai import ChatOpenAI
from src.utils.config_loader import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    api_key = settings['openai']['api_key']
    model = settings['openai']['model']
    
    if api_key and api_key != "${OPENAI_API_KEY}":
        logger.info("Initialized LLM client with model %s", model)
        app.state.llm = ChatOpenAI(
            model=model,
            api_key=api_key
        )
    else:
        logger.info("No OpenAI API key configured; running without an LLM client")
        app.state.llm = None
        
    yield
