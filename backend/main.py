from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List
import random
from datetime import datetime, timedelta

from database import (
    get_db,
    init_db,
    Player,
    Game,
    GameParticipation,
    TwoThirdsRound,
    TwoThirdsSubmission,
    HorseRaceGame,
    HorseRaceAttempt,
    FishPondGame,
    FishPondRound,
    PlayerFishingDecision,
)
from schemas import (
    PlayerCreate,
    PlayerResponse,
    GameResponse,
    TwoThirdsSubmissionCreate,
    TwoThirdsSubmissionResponse,
    TwoThirdsRoundResponse,
    TwoThirdsResultResponse,
    HorseRaceStart,
    HorseSelectionSubmit,
    HorseRaceRoundResult,
    LeaderboardEntry,
    FishPondSubmitCatch,
    FishPondGameResponse,
    FishPondResultResponse,
)
from config import FISH_POND_CONFIG, TWO_THIRDS_CONFIG, HORSE_RACE_CONFIG, MAX_PLAYERS, CORS_ORIGINS
from auth import AdminLogin, Token, authenticate_admin, create_access_token, require_admin

app = FastAPI(
    title="Game Theory Platform",
    description="Platform for conducting game theory experiments",
    version="2.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    try:
        init_db()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request, exc):
    """Handle database errors gracefully"""
    return JSONResponse(
        status_code=500,
        content={"detail": "Database error occurred. Please try again later."}
    )


# ==================== AUTHENTICATION ENDPOINTS ====================

@app.post("/api/auth/login", response_model=Token)
def login(credentials: AdminLogin):
    """Admin login endpoint"""
    if not authenticate_admin(credentials.username, credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=480)
    access_token = create_access_token(
        data={"sub": credentials.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/auth/verify")
def verify_admin(admin: str = Depends(require_admin)):
    """Verify admin token"""
    return {"authenticated": True, "username": admin}


# ==================== PLAYER ENDPOINTS ====================

@app.post("/api/players", response_model=PlayerResponse, status_code=status.HTTP_201_CREATED)
def create_player(player: PlayerCreate, db: Session = Depends(get_db)):
    """Create a new player"""
    existing = db.query(Player).filter(Player.name == player.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Player name already exists")
    
    player_count = db.query(Player).count()
    if player_count >= MAX_PLAYERS:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_PLAYERS} players reached")
    
    new_player = Player(name=player.name)
    db.add(new_player)
    db.commit()
    db.refresh(new_player)
    return new_player


@app.get("/api/players", response_model=List[PlayerResponse])
def get_players(db: Session = Depends(get_db)):
    """Get all players"""
    return db.query(Player).order_by(Player.created_at).all()


@app.get("/api/players/{player_id}", response_model=PlayerResponse)
def get_player(player_id: int, db: Session = Depends(get_db)):
    """Get a specific player"""
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


@app.delete("/api/players/{player_id}")
def delete_player(player_id: int, db: Session = Depends(get_db), admin: str = Depends(require_admin)):
    """Delete a player (Admin only)"""
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    db.delete(player)
    db.commit()
    return {"message": f"Player {player.name} deleted successfully"}


@app.get("/api/leaderboard", response_model=List[LeaderboardEntry])
def get_leaderboard(db: Session = Depends(get_db)):
    """Get global leaderboard"""
    players = db.query(Player).order_by(Player.total_score.desc()).all()
    return [
        LeaderboardEntry(
            rank=idx + 1,
            player_id=p.id,
            player_name=p.name,
            total_score=p.total_score
        )
        for idx, p in enumerate(players)
    ]


# ==================== TWO-THIRDS GAME ENDPOINTS ====================

@app.post("/api/games/two-thirds/start", response_model=GameResponse)
def start_two_thirds_game(db: Session = Depends(get_db), admin: str = Depends(require_admin)):
    """Start a new Two-Thirds game (Admin only)"""
    # Check if there's already an active game
    existing = db.query(Game).filter(
        Game.name == "two_thirds",
        Game.status == "active"
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="An active Two-Thirds game already exists")
    
    game = Game(name="two_thirds", status="active")
    db.add(game)
    db.commit()
    db.refresh(game)
    
    # Create first round
    round = TwoThirdsRound(game_id=game.id, round_number=1, status="open")
    db.add(round)
    db.commit()
    
    return game


@app.get("/api/games/two-thirds/active", response_model=GameResponse)
def get_active_two_thirds_game(db: Session = Depends(get_db)):
    """Get the current active Two-Thirds game"""
    game = db.query(Game).filter(
        Game.name == "two_thirds",
        Game.status == "active"
    ).first()
    
    if not game:
        raise HTTPException(status_code=404, detail="No active Two-Thirds game")
    
    return game


@app.get("/api/games/two-thirds/{game_id}/current-round", response_model=TwoThirdsRoundResponse)
def get_current_round(game_id: int, db: Session = Depends(get_db)):
    """Get the current round of a Two-Thirds game"""
    round = db.query(TwoThirdsRound).filter(
        TwoThirdsRound.game_id == game_id,
        TwoThirdsRound.status == "open"
    ).first()
    
    if not round:
        raise HTTPException(status_code=404, detail="No open round")
    
    submissions_count = db.query(TwoThirdsSubmission).filter(
        TwoThirdsSubmission.round_id == round.id
    ).count()
    
    return TwoThirdsRoundResponse(
        id=round.id,
        round_number=round.round_number,
        status=round.status,
        average=round.average,
        two_thirds_average=round.two_thirds_average,
        winner_id=round.winner_id,
        submissions_count=submissions_count,
    )


@app.post("/api/games/two-thirds/{game_id}/submit", response_model=TwoThirdsSubmissionResponse)
def submit_two_thirds_guess(
    game_id: int,
    submission: TwoThirdsSubmissionCreate,
    db: Session = Depends(get_db)
):
    """Submit a guess for the current Two-Thirds round"""
    round = db.query(TwoThirdsRound).filter(
        TwoThirdsRound.game_id == game_id,
        TwoThirdsRound.status == "open"
    ).first()
    
    if not round:
        raise HTTPException(status_code=400, detail="No open round available")
    
    # Check if player exists
    player = db.query(Player).filter(Player.id == submission.player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Check if player already submitted
    existing = db.query(TwoThirdsSubmission).filter(
        TwoThirdsSubmission.round_id == round.id,
        TwoThirdsSubmission.player_id == submission.player_id,
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Player already submitted for this round")
    
    new_submission = TwoThirdsSubmission(
        round_id=round.id,
        player_id=submission.player_id,
        guess=submission.guess
    )
    db.add(new_submission)
    db.commit()
    db.refresh(new_submission)
    
    return new_submission


@app.post("/api/games/two-thirds/{game_id}/calculate", response_model=TwoThirdsResultResponse)
def calculate_two_thirds_round(
    game_id: int,
    db: Session = Depends(get_db),
    admin: str = Depends(require_admin)
):
    """Calculate the winner of the current Two-Thirds round (Admin only)"""
    round = db.query(TwoThirdsRound).filter(
        TwoThirdsRound.game_id == game_id,
        TwoThirdsRound.status == "open"
    ).first()
    
    if not round:
        raise HTTPException(status_code=400, detail="No open round to calculate")
    
    submissions = db.query(TwoThirdsSubmission).filter(
        TwoThirdsSubmission.round_id == round.id
    ).all()
    
    if len(submissions) == 0:
        raise HTTPException(status_code=400, detail="No submissions to calculate")
    
    # Calculate average
    guesses = [s.guess for s in submissions]
    average = sum(guesses) / len(guesses)
    two_thirds_avg = (2 / 3) * average
    
    # Find winner
    winner = min(submissions, key=lambda s: abs(s.guess - two_thirds_avg))
    
    # Update round
    round.average = average
    round.two_thirds_average = two_thirds_avg
    round.winner_id = winner.player_id
    round.status = "calculated"
    
    # Award points
    winner_player = db.query(Player).filter(Player.id == winner.player_id).first()
    winner_player.total_score += TWO_THIRDS_CONFIG["winner_points"]
    
    db.commit()
    
    # Prepare response
    all_guesses = [
        {
            "player_id": s.player_id,
            "player_name": db.query(Player).filter(Player.id == s.player_id).first().name,
            "guess": s.guess,
            "distance": abs(s.guess - two_thirds_avg)
        }
        for s in submissions
    ]
    
    return TwoThirdsResultResponse(
        round_id=round.id,
        average=average,
        two_thirds_average=two_thirds_avg,
        winner_id=winner.player_id,
        winner_name=winner_player.name,
        all_guesses=sorted(all_guesses, key=lambda x: x["distance"])
    )


# ==================== HORSE RACE GAME ENDPOINTS ====================

def generate_horses():
    """Generate 25 horses with random speeds"""
    horses = []
    for i in range(HORSE_RACE_CONFIG["num_horses"]):
        horses.append({
            "id": i + 1,
            "name": f"Horse #{i + 1}",
            "speed": random.randint(
                HORSE_RACE_CONFIG["min_speed"],
                HORSE_RACE_CONFIG["max_speed"]
            )
        })
    return horses


@app.post("/api/games/horse-race/start", response_model=dict)
def start_horse_race(player_data: HorseRaceStart, db: Session = Depends(get_db)):
    """Start a new Horse Race game for a player"""
    # Verify player exists
    player = db.query(Player).filter(Player.id == player_data.player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    game = Game(name="horse_race", status="active")
    db.add(game)
    db.commit()
    db.refresh(game)
    
    horses = generate_horses()
    
    horse_game = HorseRaceGame(game_id=game.id, horses_data=horses)
    db.add(horse_game)
    db.commit()
    db.refresh(horse_game)
    
    return {
        "game_id": horse_game.id,
        "message": "Horse race started! Select 5 horses to race.",
        "total_horses": HORSE_RACE_CONFIG["num_horses"]
    }


@app.get("/api/games/horse-race/{game_id}/horses", response_model=List[dict])
def get_available_horses(game_id: int, db: Session = Depends(get_db)):
    """Get list of horses (without showing speeds)"""
    horse_game = db.query(HorseRaceGame).filter(HorseRaceGame.id == game_id).first()
    
    if not horse_game:
        raise HTTPException(status_code=404, detail="Horse race game not found")
    
    horses = horse_game.horses_data
    return [{"id": h["id"], "name": h["name"]} for h in horses]


@app.post("/api/games/horse-race/{game_id}/race", response_model=HorseRaceRoundResult)
def race_horses(
    game_id: int,
    selection: HorseSelectionSubmit,
    db: Session = Depends(get_db)
):
    """Race selected horses and return results"""
    horse_game = db.query(HorseRaceGame).filter(HorseRaceGame.id == game_id).first()
    
    if not horse_game:
        raise HTTPException(status_code=404, detail="Horse race game not found")
    
    # Validate horse IDs
    if any(hid < 1 or hid > HORSE_RACE_CONFIG["num_horses"] for hid in selection.selected_horse_ids):
        raise HTTPException(status_code=400, detail="Invalid horse ID")
    
    if len(selection.selected_horse_ids) != HORSE_RACE_CONFIG["horses_per_race"]:
        raise HTTPException(
            status_code=400,
            detail=f"Must select exactly {HORSE_RACE_CONFIG['horses_per_race']} horses"
        )
    
    # Get selected horses with speeds
    horses = horse_game.horses_data
    selected = [h for h in horses if h["id"] in selection.selected_horse_ids]
    
    # Sort by speed
    race_results = sorted(selected, key=lambda x: x["speed"], reverse=True)
    
    # Get or create player's attempts
    player_attempts = db.query(HorseRaceAttempt).filter(
        HorseRaceAttempt.game_id == game_id,
        HorseRaceAttempt.player_id == selection.player_id
    ).all()
    
    round_number = len(player_attempts) + 1
    
    # Create attempt record
    attempt = HorseRaceAttempt(
        game_id=game_id,
        player_id=selection.player_id,
        round_number=round_number,
        selected_horses=selection.selected_horse_ids,
        race_results=[{"id": h["id"], "name": h["name"], "speed": h["speed"]} for h in race_results],
        total_rounds_used=round_number
    )
    db.add(attempt)
    db.commit()
    
    return HorseRaceRoundResult(
        round_number=round_number,
        selected_horses=selected,
        race_results=race_results,
        message=f"Round {round_number} completed! The fastest horse was {race_results[0]['name']}."
    )


@app.post("/api/games/horse-race/{game_id}/submit-top-three", response_model=dict)
def submit_top_three(
    game_id: int,
    data: dict,
    db: Session = Depends(get_db)
):
    """Submit the player's guess for top 3 fastest horses"""
    player_id = data.get("player_id")
    top_three_ids = data.get("top_three_ids")
    
    if not top_three_ids or len(top_three_ids) != 3:
        raise HTTPException(status_code=400, detail="Must submit exactly 3 horse IDs")
    
    horse_game = db.query(HorseRaceGame).filter(HorseRaceGame.id == game_id).first()
    if not horse_game:
        raise HTTPException(status_code=404, detail="Horse race game not found")
    
    # Find actual top 3
    horses = horse_game.horses_data
    actual_top_three = sorted(horses, key=lambda x: x["speed"], reverse=True)[:3]
    actual_ids = [h["id"] for h in actual_top_three]
    
    # Check if correct
    is_correct = top_three_ids == actual_ids
    
    # Get player's total rounds
    rounds_used = db.query(HorseRaceAttempt).filter(
        HorseRaceAttempt.game_id == game_id,
        HorseRaceAttempt.player_id == player_id
    ).count()
    
    if is_correct:
        score = max(50 - (rounds_used * 5), 10)
        
        player = db.query(Player).filter(Player.id == player_id).first()
        player.total_score += score
        
        latest_attempt = db.query(HorseRaceAttempt).filter(
            HorseRaceAttempt.game_id == game_id,
            HorseRaceAttempt.player_id == player_id
        ).order_by(HorseRaceAttempt.round_number.desc()).first()
        
        if latest_attempt:
            latest_attempt.identified_top_three = True
            latest_attempt.completed = True
        
        db.commit()
        
        return {
            "correct": True,
            "score": score,
            "rounds_used": rounds_used,
            "message": f"Congratulations! You found the top 3 in {rounds_used} rounds and earned {score} points!",
            "actual_top_three": actual_top_three
        }
    else:
        return {
            "correct": False,
            "rounds_used": rounds_used,
            "message": "Incorrect. Keep trying!",
            "your_guess": [next(h for h in horses if h["id"] == hid) for hid in top_three_ids]
        }


# ==================== FISH POND GAME ENDPOINTS ====================

@app.post("/api/games/fish-pond/start", response_model=FishPondGameResponse)
def start_fish_pond_game(db: Session = Depends(get_db), admin: str = Depends(require_admin)):
    """Start a new Fish Pond game with all registered players (Admin only)"""
    # Check if there's already an active game
    existing_game = db.query(Game).filter(
        Game.name == "fish_pond",
        Game.status.in_(["active", "waiting"])
    ).first()
    
    if existing_game:
        raise HTTPException(status_code=400, detail="An active Fish Pond game already exists")
    
    # Get all players
    players = db.query(Player).all()
    if len(players) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 players to start Fish Pond game")
    
    # Create game
    game = Game(name="fish_pond", status="active")
    db.add(game)
    db.commit()
    db.refresh(game)
    
    # Create Fish Pond game instance
    fish_game = FishPondGame(
        game_id=game.id,
        initial_stock=FISH_POND_CONFIG["initial_stock"],
        current_stock=FISH_POND_CONFIG["initial_stock"],
        max_capacity=FISH_POND_CONFIG["max_capacity"],
        current_round=1,
        status="round_open"
    )
    db.add(fish_game)
    db.commit()
    db.refresh(fish_game)
    
    # Create first round
    first_round = FishPondRound(
        game_id=fish_game.id,
        round_number=1,
        status="open",
        stock_at_start=FISH_POND_CONFIG["initial_stock"]
    )
    db.add(first_round)
    
    # Create participations for all players
    for player in players:
        participation = GameParticipation(
            game_id=game.id,
            player_id=player.id,
            score=0
        )
        db.add(participation)
    
    db.commit()
    db.refresh(fish_game)
    
    return FishPondGameResponse(
        id=fish_game.id,
        game_id=fish_game.game_id,
        initial_stock=fish_game.initial_stock,
        current_stock=fish_game.current_stock,
        max_capacity=fish_game.max_capacity,
        current_round=fish_game.current_round,
        status=fish_game.status,
        created_at=fish_game.created_at
    )


@app.get("/api/games/fish-pond/{game_id}", response_model=FishPondGameResponse)
def get_fish_pond_game(game_id: int, db: Session = Depends(get_db)):
    """Get Fish Pond game status"""
    fish_game = db.query(FishPondGame).filter(FishPondGame.id == game_id).first()
    
    if not fish_game:
        raise HTTPException(status_code=404, detail="Fish Pond game not found")
    
    return FishPondGameResponse(
        id=fish_game.id,
        game_id=fish_game.game_id,
        initial_stock=fish_game.initial_stock,
        current_stock=fish_game.current_stock,
        max_capacity=fish_game.max_capacity,
        current_round=fish_game.current_round,
        status=fish_game.status,
        created_at=fish_game.created_at
    )


@app.get("/api/games/fish-pond/{game_id}/round", response_model=dict)
def get_fish_pond_round_status(game_id: int, db: Session = Depends(get_db)):
    """Get current round info and players who haven't submitted"""
    fish_game = db.query(FishPondGame).filter(FishPondGame.id == game_id).first()
    
    if not fish_game:
        raise HTTPException(status_code=404, detail="Fish Pond game not found")
    
    current_round = db.query(FishPondRound).filter(
        FishPondRound.game_id == fish_game.id,
        FishPondRound.round_number == fish_game.current_round
    ).first()
    
    if not current_round:
        raise HTTPException(status_code=404, detail="Current round not found")
    
    # Get all players in game
    all_players = db.query(Player).join(GameParticipation).filter(
        GameParticipation.game_id == fish_game.game_id
    ).all()
    
    # Get players who submitted
    submitted_player_ids = [
        d.player_id for d in db.query(PlayerFishingDecision).filter(
            PlayerFishingDecision.round_id == current_round.id
        ).all()
    ]
    
    pending_players = [
        {"id": p.id, "name": p.name}
        for p in all_players
        if p.id not in submitted_player_ids
    ]
    
    return {
        "round_number": current_round.round_number,
        "status": current_round.status,
        "stock_at_start": current_round.stock_at_start,
        "total_players": len(all_players),
        "submitted_count": len(submitted_player_ids),
        "pending_players": pending_players,
        "all_submitted": len(pending_players) == 0
    }


@app.post("/api/games/fish-pond/{game_id}/submit", response_model=dict)
def submit_fish_catch(
    game_id: int,
    submission: FishPondSubmitCatch,
    db: Session = Depends(get_db)
):
    """Submit a catch amount for the current round"""
    fish_game = db.query(FishPondGame).filter(FishPondGame.id == game_id).first()
    
    if not fish_game:
        raise HTTPException(status_code=404, detail="Fish Pond game not found")
    
    # Get current round
    round = db.query(FishPondRound).filter(
        FishPondRound.game_id == fish_game.id,
        FishPondRound.round_number == fish_game.current_round,
    ).first()
    
    if not round or round.status != "open":
        raise HTTPException(status_code=400, detail="Round is not open")
    
    # Validate catch amount
    if submission.catch_amount > FISH_POND_CONFIG["max_catch_per_player"]:
        raise HTTPException(
            status_code=400,
            detail=f"Catch cannot exceed {FISH_POND_CONFIG['max_catch_per_player']}"
        )
    
    if submission.catch_amount > fish_game.current_stock:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough fish in pond (available: {fish_game.current_stock})"
        )
    
    # Check if already submitted
    existing = db.query(PlayerFishingDecision).filter(
        PlayerFishingDecision.round_id == round.id,
        PlayerFishingDecision.player_id == submission.player_id,
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Player already submitted for this round")
    
    # Create decision record
    decision = PlayerFishingDecision(
        game_id=fish_game.id,
        round_id=round.id,
        player_id=submission.player_id,
        catch_amount=submission.catch_amount,
    )
    db.add(decision)
    db.commit()
    
    player = db.query(Player).filter(Player.id == submission.player_id).first()
    
    return {
        "success": True,
        "player_name": player.name,
        "catch_amount": submission.catch_amount,
        "message": f"Catch of {submission.catch_amount} fish submitted!"
    }


@app.post("/api/games/fish-pond/{game_id}/calculate-round", response_model=dict)
def calculate_fish_pond_round(
    game_id: int,
    db: Session = Depends(get_db),
    admin: str = Depends(require_admin)
):
    """Calculate round results and move to next round (Admin only)"""
    fish_game = db.query(FishPondGame).filter(FishPondGame.id == game_id).first()
    
    if not fish_game:
        raise HTTPException(status_code=404, detail="Fish Pond game not found")
    
    # Get current round
    round = db.query(FishPondRound).filter(
        FishPondRound.game_id == fish_game.id,
        FishPondRound.round_number == fish_game.current_round,
    ).first()
    
    if not round:
        raise HTTPException(status_code=400, detail="No current round")
    
    # Get all decisions
    decisions = db.query(PlayerFishingDecision).filter(
        PlayerFishingDecision.round_id == round.id
    ).all()
    
    if not decisions:
        raise HTTPException(status_code=400, detail="No catches submitted yet")
    
    # Calculate total catch
    total_catch = sum(d.catch_amount for d in decisions)
    round.total_catch = total_catch
    
    # Award points
    for decision in decisions:
        decision.round_score = decision.catch_amount
        player = db.query(Player).filter(Player.id == decision.player_id).first()
        player.total_score += decision.catch_amount
    
    # Update stock
    remaining_stock = fish_game.current_stock - total_catch
    
    if remaining_stock <= 0:
        # Stock collapsed
        round.collapsed = True
        round.stock_at_end = 0
        fish_game.current_stock = 0
        fish_game.status = "completed"
        fish_game.completed_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "round_number": fish_game.current_round,
            "total_catch": total_catch,
            "stock_at_end": 0,
            "collapsed": True,
            "message": "The pond has been overfished and has collapsed! Game ended.",
            "decisions": [
                {
                    "player_id": d.player_id,
                    "player_name": db.query(Player).filter(Player.id == d.player_id).first().name,
                    "catch": d.catch_amount,
                    "score": d.round_score,
                }
                for d in decisions
            ],
            "game_ended": True
        }
    
    # Stock regeneration
    growth = remaining_stock * FISH_POND_CONFIG["regeneration_rate"]
    new_stock = min(remaining_stock + growth, FISH_POND_CONFIG["max_capacity"])
    
    round.stock_at_end = new_stock
    round.status = "calculated"
    fish_game.current_stock = new_stock
    
    # Move to next round or end game
    if fish_game.current_round < FISH_POND_CONFIG["num_rounds"]:
        fish_game.current_round += 1
        next_round = FishPondRound(
            game_id=fish_game.id,
            round_number=fish_game.current_round,
            status="open",
            stock_at_start=new_stock,
        )
        db.add(next_round)
        fish_game.status = "round_open"
    else:
        # Game ended
        fish_game.status = "completed"
        fish_game.completed_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "round_number": fish_game.current_round - 1,
        "total_catch": total_catch,
        "stock_at_end": new_stock,
        "collapsed": False,
        "message": f"Round {fish_game.current_round - 1} completed! Stock regenerated to {int(new_stock)}.",
        "decisions": [
            {
                "player_id": d.player_id,
                "player_name": db.query(Player).filter(Player.id == d.player_id).first().name,
                "catch": d.catch_amount,
                "score": d.round_score,
            }
            for d in decisions
        ],
        "game_ended": fish_game.status == "completed"
    }


@app.get("/api/games/fish-pond/{game_id}/results", response_model=FishPondResultResponse)
def get_fish_pond_results(game_id: int, db: Session = Depends(get_db)):
    """Get final Fish Pond game results"""
    fish_game = db.query(FishPondGame).filter(FishPondGame.id == game_id).first()
    
    if not fish_game:
        raise HTTPException(status_code=404, detail="Fish Pond game not found")
    
    # Get all decisions
    all_decisions = db.query(PlayerFishingDecision).filter(
        PlayerFishingDecision.game_id == fish_game.id
    ).all()
    
    # Calculate final scores
    final_scores = {}
    for decision in all_decisions:
        if decision.player_id not in final_scores:
            player = db.query(Player).filter(Player.id == decision.player_id).first()
            final_scores[decision.player_id] = {
                "player_id": decision.player_id,
                "player_name": player.name,
                "total_catch": 0,
            }
        final_scores[decision.player_id]["total_catch"] += decision.catch_amount
    
    # Get all rounds info
    all_rounds = db.query(FishPondRound).filter(
        FishPondRound.game_id == fish_game.id
    ).all()
    
    rounds_data = [
        {
            "round_number": r.round_number,
            "stock_at_start": r.stock_at_start,
            "total_catch": r.total_catch,
            "stock_at_end": r.stock_at_end,
            "collapsed": r.collapsed,
        }
        for r in all_rounds
    ]
    
    return FishPondResultResponse(
        game_id=fish_game.id,
        completed=fish_game.status == "completed",
        final_scores=sorted(
            final_scores.values(), key=lambda x: x["total_catch"], reverse=True
        ),
        all_rounds=rounds_data,
        game_collapsed=any(r.collapsed for r in all_rounds),
    )


# ==================== GENERAL ENDPOINTS ====================

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Game Theory Platform API",
        "version": "2.0.0",
        "docs": "/docs"
    }


@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get general statistics"""
    total_players = db.query(Player).count()
    active_games = db.query(Game).filter(Game.status == "active").count()
    
    return {
        "total_players": total_players,
        "max_players": MAX_PLAYERS,
        "active_games": active_games,
    }


@app.get("/health")
def health_check():
    """Health check endpoint for Railway"""
    return {"status": "healthy"}
