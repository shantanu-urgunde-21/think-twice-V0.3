import os
from dotenv import load_dotenv

load_dotenv()

# Admin Configuration
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")  # Change in production!

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://gameuser:gamepass123@localhost:5432/game_theory_db")

# If Railway provides DATABASE_URL with postgres:// instead of postgresql://
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# CORS Configuration
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
# Default CORS origins - includes both localhost (dev) and known production URLs
DEFAULT_CORS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "https://think-twice-v03-a171t19c4-think-twice-f383eaa5.vercel.app",  # Production Vercel URL
]
if FRONTEND_URL not in DEFAULT_CORS:
    DEFAULT_CORS.append(FRONTEND_URL)

CORS_ORIGINS_STR = os.getenv("CORS_ORIGINS", None)
if CORS_ORIGINS_STR:
    CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS_STR.split(",")]
else:
    CORS_ORIGINS = DEFAULT_CORS

# Game Configuration
MAX_PLAYERS = int(os.getenv("MAX_PLAYERS", "40"))

# Fish Pond Game Configuration
FISH_POND_CONFIG = {
    "initial_stock": 100,
    "max_capacity": 100,
    "max_catch_per_player": 20,
    "num_rounds": 5,
    "regeneration_rate": 0.5,
    "win_points_per_catch": 1,
    "collapse_penalty": 0,
}

# Two-Thirds Game Configuration
TWO_THIRDS_CONFIG = {
    "min_guess": 0,
    "max_guess": 100,
    "winner_points": 10,
}

# Horse Race Game Configuration
HORSE_RACE_CONFIG = {
    "num_horses": 25,
    "horses_per_race": 5,
    "min_speed": 1,
    "max_speed": 100,
}
