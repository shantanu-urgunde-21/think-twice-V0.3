from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from config import CORS_ORIGINS
from routers import auth, game_settings, players, two_thirds, horse_race, general, fish_pond, market, websockets, rooms

app = FastAPI(title="Game Theory Platform", version="2.0.0")

# CORS - simplified
origins = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
]
if CORS_ORIGINS:
    origins.extend([o.strip() for o in CORS_ORIGINS if o.strip()])
origins = list(dict.fromkeys(origins))  # Remove duplicates

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    init_db()

# Include routers
app.include_router(auth.router)
app.include_router(game_settings.router)
app.include_router(players.router)
app.include_router(rooms.router)
app.include_router(two_thirds.router)
app.include_router(horse_race.router)
app.include_router(fish_pond.router)
app.include_router(market.router)
app.include_router(websockets.router)
app.include_router(general.router)
