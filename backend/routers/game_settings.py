from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from database import get_db, GameSettings
from schemas import GameSettingsUpdate, GameSettingsResponse
from auth import require_admin

router = APIRouter(prefix="/api/games", tags=["Game Settings"])

@router.get("/enabled")
def get_enabled_games(db: Session = Depends(get_db)):
    return db.query(GameSettings).filter(GameSettings.enabled == True).all()


@router.get("/settings", response_model=List[GameSettingsResponse])
def get_all_settings(
    db: Session = Depends(get_db), admin: str = Depends(require_admin)
):
    return db.query(GameSettings).all()


@router.put("/settings/{game_name}", response_model=GameSettingsResponse)
def update_settings(
    game_name: str,
    update: GameSettingsUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: str = Depends(require_admin),
):
    setting = db.query(GameSettings).filter(GameSettings.game_name == game_name).first()
    if not setting:
        raise HTTPException(404, "Game not found")
    setting.enabled = update.enabled
    db.commit()
    db.refresh(setting)

    from routers.websockets import manager
    background_tasks.add_task(manager.broadcast_lobby, {"event": "settings_updated"})

    return setting
