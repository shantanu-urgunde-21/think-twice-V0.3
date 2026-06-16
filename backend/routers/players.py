from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import random
from pydantic import BaseModel, Field
from database import get_db, Player
from schemas import PlayerCreate, PlayerResponse, LeaderboardEntry
from config import MAX_PLAYERS
from auth import require_admin

router = APIRouter(prefix="/api", tags=["Players"])

class PlayerVerify(BaseModel):
    name: str
    passcode: str

@router.post("/players", response_model=PlayerResponse)
def create_player(player: PlayerCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    existing_player = db.query(Player).filter(Player.name == player.name).first()
    if existing_player:
        # If the player already exists, check if they provided the correct passcode to log in.
        if player.passcode and existing_player.passcode == player.passcode:
            return existing_player
        raise HTTPException(400, "Player name already exists")
        
    if db.query(Player).count() >= MAX_PLAYERS:
        raise HTTPException(400, f"Maximum {MAX_PLAYERS} players reached")

    passcode = player.passcode
    if not passcode:
        # Generate a random 4-digit passcode
        passcode = "".join(random.choices("0123456789", k=4))
    else:
        if not passcode.isdigit():
            raise HTTPException(400, "Passcode must contain only digits")

    new_player = Player(name=player.name, passcode=passcode)
    db.add(new_player)
    db.commit()
    db.refresh(new_player)

    from routers.websockets import manager
    background_tasks.add_task(manager.broadcast_lobby, {"event": "player_registered"})

    return new_player

@router.post("/players/verify", response_model=PlayerResponse)
def verify_player(data: PlayerVerify, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.name == data.name).first()
    if not player:
        raise HTTPException(404, "Player not found")
    if player.passcode != data.passcode:
        raise HTTPException(401, "Invalid passcode")
    return player


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


@router.post("/players/reset-scores")
def reset_scores(db: Session = Depends(get_db), admin: str = Depends(require_admin)):
    players = db.query(Player).all()
    for p in players:
        p.total_score = 0
    db.commit()
    return {"message": "All player scores reset to 0"}


@router.post("/players/clear-all")
def clear_all_players(db: Session = Depends(get_db), admin: str = Depends(require_admin)):
    db.query(Player).delete()
    db.commit()
    return {"message": "All players deleted"}


@router.get("/leaderboard", response_model=List[LeaderboardEntry])
def get_leaderboard(db: Session = Depends(get_db)):
    players = db.query(Player).order_by(Player.total_score.desc()).all()
    return [
        LeaderboardEntry(
            rank=idx + 1, player_id=p.id, player_name=p.name, total_score=p.total_score
        )
        for idx, p in enumerate(players)
    ]
