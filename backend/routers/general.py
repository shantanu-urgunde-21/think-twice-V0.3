from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db, Player, Game
from config import MAX_PLAYERS

router = APIRouter(tags=["General"])

@router.get("/")
def root():
    return {"message": "Game Theory Platform API", "version": "2.0.0"}


@router.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    return {
        "total_players": db.query(Player).count(),
        "max_players": MAX_PLAYERS,
        "active_games": db.query(Game).filter(Game.status == "active").count(),
    }


@router.get("/health")
def health_check():
    return {"status": "healthy"}
