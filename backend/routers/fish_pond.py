from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List
from jose import jwt
from database import get_db, Player, Game, FishPondGame, FishPondSubmission
from schemas import GameResponse, FishPondSubmissionCreate, FishPondRoundResultResponse
from config import FISH_POND_CONFIG, SECRET_KEY, ALGORITHM, ADMIN_USERNAME
from auth import require_admin

security = HTTPBearer(auto_error=False)

router = APIRouter(prefix="/api", tags=["Fish Pond Game"])

@router.post("/games/fish-pond/start", response_model=GameResponse)
def start_fish_pond(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db), admin: str = Depends(require_admin)
):
    # Mark any completed fish pond games as finished
    completed_games = (
        db.query(Game)
        .filter(Game.name == "fish_pond", Game.status == "completed")
        .all()
    )
    for g in completed_games:
        g.status = "finished"
    db.commit()

    # Check if there is already an active game
    existing = (
        db.query(Game)
        .filter(Game.name == "fish_pond", Game.status == "active")
        .first()
    )
    if existing:
        raise HTTPException(400, "Active Fish Pond game already exists")

    # Create the new game
    game = Game(name="fish_pond", status="active")
    db.add(game)
    db.commit()
    db.refresh(game)

    # Create the fish pond game instance settings
    fish_pond = FishPondGame(
        game_id=game.id,
        initial_fish=FISH_POND_CONFIG["initial_fish"],
        current_fish=FISH_POND_CONFIG["initial_fish"],
        regeneration_rate=FISH_POND_CONFIG["regeneration_rate"],
        max_rounds=FISH_POND_CONFIG["max_rounds"],
        current_round=1,
        collapsed=False
    )
    db.add(fish_pond)
    db.commit()

    from routers.websockets import manager
    background_tasks.add_task(manager.broadcast_lobby, {
        "event": "game_started",
        "game_name": "fish_pond",
        "game_id": game.id
    })

    return game


@router.get("/games/fish-pond/active")
def get_active_fish_pond(db: Session = Depends(get_db)):
    game = (
        db.query(Game)
        .filter(Game.name == "fish_pond", Game.status == "active")
        .first()
    )
    if not game:
        raise HTTPException(404, "No active game")
    
    fp_game = db.query(FishPondGame).filter(FishPondGame.game_id == game.id).first()
    if not fp_game:
        raise HTTPException(404, "Fish Pond configuration not found")
        
    submissions_count = (
        db.query(FishPondSubmission)
        .filter(
            FishPondSubmission.game_id == game.id,
            FishPondSubmission.round_number == fp_game.current_round
        )
        .count()
    )

    return {
        "id": game.id,
        "name": game.name,
        "status": game.status,
        "current_round": fp_game.current_round,
        "max_rounds": fp_game.max_rounds,
        "initial_fish": fp_game.initial_fish,
        "current_fish": fp_game.current_fish,
        "collapsed": fp_game.collapsed,
        "submissions_count": submissions_count
    }


@router.get("/games/fish-pond/{game_id}/details")
def get_fish_pond_details(game_id: int, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(404, "Game not found")
        
    fp_game = db.query(FishPondGame).filter(FishPondGame.game_id == game_id).first()
    if not fp_game:
        raise HTTPException(404, "Fish Pond configuration not found")
        
    submissions_count = (
        db.query(FishPondSubmission)
        .filter(
            FishPondSubmission.game_id == game_id,
            FishPondSubmission.round_number == fp_game.current_round
        )
        .count()
    )

    return {
        "id": game.id,
        "name": game.name,
        "status": game.status,
        "current_round": fp_game.current_round,
        "max_rounds": fp_game.max_rounds,
        "initial_fish": fp_game.initial_fish,
        "current_fish": fp_game.current_fish,
        "collapsed": fp_game.collapsed,
        "submissions_count": submissions_count
    }


@router.post("/games/fish-pond/{game_id}/submit")
def submit_fish_pond_catch(
    game_id: int, submission: FishPondSubmissionCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    game = db.query(Game).filter(Game.id == game_id, Game.status == "active").first()
    if not game:
        raise HTTPException(404, "Active game not found")

    fp_game = db.query(FishPondGame).filter(FishPondGame.game_id == game_id).first()
    if not fp_game:
        raise HTTPException(404, "Fish Pond configuration not found")

    if fp_game.collapsed:
        raise HTTPException(400, "Pond has collapsed! No catches can be made.")

    # Check if user already submitted for this round
    existing = (
        db.query(FishPondSubmission)
        .filter(
            FishPondSubmission.game_id == game_id,
            FishPondSubmission.player_id == submission.player_id,
            FishPondSubmission.round_number == fp_game.current_round
        )
        .first()
    )
    if existing:
        raise HTTPException(400, "You have already submitted for this round")

    new_submission = FishPondSubmission(
        game_id=game_id,
        player_id=submission.player_id,
        round_number=fp_game.current_round,
        fish_caught=submission.fish_caught
    )
    db.add(new_submission)
    db.commit()

    submissions_count = (
        db.query(FishPondSubmission)
        .filter(
            FishPondSubmission.game_id == game_id,
            FishPondSubmission.round_number == fp_game.current_round
        )
        .count()
    )
    from routers.websockets import manager
    background_tasks.add_task(manager.broadcast_game, game_id, {
        "event": "submission",
        "submissions_count": submissions_count
    })

    return {"success": True, "message": "Catch submitted"}


@router.post("/games/fish-pond/{game_id}/calculate", response_model=FishPondRoundResultResponse)
def calculate_fish_pond_round(
    game_id: int, 
    background_tasks: BackgroundTasks,
    host_id: Optional[int] = None, 
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    game = db.query(Game).filter(Game.id == game_id, Game.status == "active").first()
    if not game:
        raise HTTPException(404, "Active game not found")

    is_authorized = False
    if host_id and game.host_id == host_id:
        is_authorized = True
    elif credentials:
        try:
            token = credentials.credentials
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("sub") == ADMIN_USERNAME:
                is_authorized = True
        except Exception:
            pass

    if not is_authorized:
        raise HTTPException(status_code=403, detail="Not authorized to calculate results")

    fp_game = db.query(FishPondGame).filter(FishPondGame.game_id == game_id).first()
    if not fp_game:
        raise HTTPException(404, "Fish Pond configuration not found")

    submissions = (
        db.query(FishPondSubmission)
        .filter(
            FishPondSubmission.game_id == game_id,
            FishPondSubmission.round_number == fp_game.current_round
        )
        .all()
    )
    if not submissions:
        raise HTTPException(400, "No submissions for this round")

    initial_fish = fp_game.current_fish
    total_caught = sum(s.fish_caught for s in submissions)
    remaining_fish = initial_fish - total_caught

    collapsed = False
    regeneration = 0
    new_fish_count = remaining_fish

    if remaining_fish <= 0:
        collapsed = True
        new_fish_count = 0
        fp_game.collapsed = True
        fp_game.status = "completed"
        game.status = "completed"
        game.completed_at = datetime.utcnow()
    else:
        # Calculate regeneration
        regeneration = int(remaining_fish * fp_game.regeneration_rate)
        new_fish_count = min(fp_game.initial_fish, remaining_fish + regeneration)

    # Update player total scores (1 point per fish caught)
    for sub in submissions:
        player = db.query(Player).filter(Player.id == sub.player_id).first()
        if player:
            player.total_score += sub.fish_caught

    # Update game state
    fp_game.current_fish = new_fish_count
    
    # Compile round submissions before moving round
    all_submissions = []
    for s in submissions:
        player = db.query(Player).filter(Player.id == s.player_id).first()
        all_submissions.append({
            "player_id": s.player_id,
            "player_name": player.name if player else "Unknown",
            "fish_caught": s.fish_caught
        })

    if not collapsed:
        if fp_game.current_round >= fp_game.max_rounds:
            fp_game.status = "completed"
            game.status = "completed"
            game.completed_at = datetime.utcnow()
        else:
            fp_game.current_round += 1

    db.commit()

    from routers.websockets import manager
    background_tasks.add_task(manager.broadcast_game, game_id, {
        "event": "round_calculated"
    })

    return FishPondRoundResultResponse(
        round_number=fp_game.current_round if not collapsed and fp_game.current_round <= fp_game.max_rounds else fp_game.current_round,
        initial_fish=initial_fish,
        total_caught=total_caught,
        remaining_fish=max(0, remaining_fish),
        regeneration=regeneration,
        current_fish=new_fish_count,
        collapsed=collapsed,
        all_submissions=all_submissions
    )


@router.post("/games/fish-pond/{game_id}/close")
def close_fish_pond(
    game_id: int, 
    background_tasks: BackgroundTasks,
    host_id: Optional[int] = None, 
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(404, "Game not found")

    is_authorized = False
    if host_id and game.host_id == host_id:
        is_authorized = True
    elif credentials:
        try:
            token = credentials.credentials
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("sub") == ADMIN_USERNAME:
                is_authorized = True
        except Exception:
            pass

    if not is_authorized:
        raise HTTPException(status_code=403, detail="Not authorized to close game")

    game.status = "completed"
    game.completed_at = datetime.utcnow()

    fp_game = db.query(FishPondGame).filter(FishPondGame.game_id == game_id).first()
    if fp_game:
        fp_game.status = "completed"

    db.commit()

    from routers.websockets import manager
    background_tasks.add_task(manager.broadcast_game, game_id, {
        "event": "game_closed"
    })

    return {"message": "Game closed successfully."}
