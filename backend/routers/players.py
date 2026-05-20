from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db, Player
from schemas import PlayerCreate, PlayerResponse, LeaderboardEntry
from config import MAX_PLAYERS
from auth import require_admin

router = APIRouter(prefix="/api", tags=["Players"])

@router.post("/players", response_model=PlayerResponse)
def create_player(player: PlayerCreate, db: Session = Depends(get_db)):
    if db.query(Player).filter(Player.name == player.name).first():
        raise HTTPException(400, "Player name already exists")
    if db.query(Player).count() >= MAX_PLAYERS:
        raise HTTPException(400, f"Maximum {MAX_PLAYERS} players reached")

    new_player = Player(name=player.name)
    db.add(new_player)
    db.commit()
    db.refresh(new_player)
    return new_player


@router.get("/players", response_model=List[PlayerResponse])
def get_players(db: Session = Depends(get_db)):
    return db.query(Player).order_by(Player.created_at).all()


@router.get("/players/{player_id}", response_model=PlayerResponse)
def get_player(player_id: int, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(404, "Player not found")
    return player


@router.delete("/players/{player_id}")
def delete_player(
    player_id: int, db: Session = Depends(get_db), admin: str = Depends(require_admin)
):
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(404, "Player not found")
    db.delete(player)
    db.commit()
    return {"message": f"Player {player.name} deleted"}


@router.get("/leaderboard", response_model=List[LeaderboardEntry])
def get_leaderboard(db: Session = Depends(get_db)):
    players = db.query(Player).order_by(Player.total_score.desc()).all()
    return [
        LeaderboardEntry(
            rank=idx + 1, player_id=p.id, player_name=p.name, total_score=p.total_score
        )
        for idx, p in enumerate(players)
    ]
