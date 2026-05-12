from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.api.llm_routes import router as llm_router
from src.api.next_routes import router as next_router
from src.api.health_routes import router as health_router
from src.services.lifespan import lifespan
from src.utils.config_loader import settings

app = FastAPI(
    lifespan=lifespan,
    title="LLM Extraction + Dialogue API",
    description="API for LLM Extraction and Dialogue",
    version="1.0.0",
)
app.include_router(llm_router, prefix="/api/v1")
app.include_router(next_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings['cors']['origins'],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Return a welcome message for the LLM Extraction + Dialogue API."""
    return JSONResponse(
        status_code=200,
        content={"message": "Welcome to the LLM Extraction + Dialogue API"}
    )

if __name__ == "__main__":
    uvicorn.run(
        app, 
        host=settings['server']['host'], 
        port=settings['server']['port']
    )
