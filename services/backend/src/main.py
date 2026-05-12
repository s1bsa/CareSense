from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from src.utils.data_loader import load_data
from src.api.routes import router as api_router, init_routes
from src.utils.config_loader import settings

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings['cors']['origins'],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load data and initialize routes
probs, _priors, beliefs = load_data()
init_routes(probs, beliefs)

app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run(
        app, 
        host=settings['server']['host'], 
        port=settings['server']['port']
    )
