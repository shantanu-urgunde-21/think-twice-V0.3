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
    GameSettings,
    GameParticipation,
    TwoThirdsRound,
    TwoThirdsSubmission,
    HorseRaceGame,
    HorseRaceAttempt,
    HorseRaceGameCompletion,
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
    GameSettingsUpdate,
    GameSettingsResponse,
)
from config import (
    TWO_THIRDS_CONFIG,
    HORSE_RACE_CONFIG,
    MAX_PLAYERS,
    CORS_ORIGINS,
)
from auth import (
    AdminLogin,
    Token,
    authenticate_admin,
    create_access_token,
    require_admin,
)

app = FastAPI(
    title="Game Theory Platform",
    description="Platform for conducting game theory experiments",
    version="2.0.0",
)

# CORS Configuration - Build origins list
origins = [
    "http://localhost:3000",
    "http://localhost:8000",
]

# Add origins from environment variables (includes production Vercel URL)
if CORS_ORIGINS:
    origins.extend([origin.strip() for origin in CORS_ORIGINS if origin.strip()])

# Remove duplicates while preserving order
origins = list(dict.fromkeys(origins))

# Add CORS middleware - must be first middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
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
        content={"detail": "Database error occurred. Please try again later."},
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


# ==================== GAME SETTINGS ENDPOINTS ====================


@app.get("/api/games/enabled", response_model=List[dict])
def get_enabled_games(db: Session = Depends(get_db)):
    """Get list of enabled games to display on homepage"""
    settings = db.query(GameSettings).filter(GameSettings.enabled == True).all()
    return [{"game_name": s.game_name} for s in settings]


@app.get("/api/games/settings", response_model=List[GameSettingsResponse])
def get_game_settings(
    db: Session = Depends(get_db), admin: str = Depends(require_admin)
):
    """Get all game settings (Admin only)"""
    return db.query(GameSettings).all()


@app.put("/api/games/settings/{game_name}", response_model=GameSettingsResponse)
def update_game_settings(
    game_name: str,
    settings: GameSettingsUpdate,
    db: Session = Depends(get_db),
    admin: str = Depends(require_admin),
):
    """Update game visibility settings (Admin only)"""
    game_setting = (
        db.query(GameSettings).filter(GameSettings.game_name == game_name).first()
    )

    if not game_setting:
        # Create new settings if doesn't exist
        game_setting = GameSettings(game_name=game_name, enabled=settings.enabled)
        db.add(game_setting)
    else:
        game_setting.enabled = settings.enabled

    db.commit()
    db.refresh(game_setting)
    return game_setting


# ==================== PLAYER ENDPOINTS ====================


@app.post(
    "/api/players", response_model=PlayerResponse, status_code=status.HTTP_201_CREATED
)
def create_player(player: PlayerCreate, db: Session = Depends(get_db)):
    """Create a new player"""
    existing = db.query(Player).filter(Player.name == player.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Player name already exists")

    player_count = db.query(Player).count()
    if player_count >= MAX_PLAYERS:
        raise HTTPException(
            status_code=400, detail=f"Maximum {MAX_PLAYERS} players reached"
        )

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
def delete_player(
    player_id: int, db: Session = Depends(get_db), admin: str = Depends(require_admin)
):
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
            rank=idx + 1, player_id=p.id, player_name=p.name, total_score=p.total_score
        )
        for idx, p in enumerate(players)
    ]


# ==================== TWO-THIRDS GAME ENDPOINTS ====================


@app.post("/api/games/two-thirds/start", response_model=GameResponse)
def start_two_thirds_game(
    db: Session = Depends(get_db), admin: str = Depends(require_admin)
):
    """Start a new Two-Thirds game (Admin only)"""
    # Check if there's already an active game
    existing = (
        db.query(Game)
        .filter(Game.name == "two_thirds", Game.status == "active")
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400, detail="An active Two-Thirds game already exists"
        )

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
    game = (
        db.query(Game)
        .filter(Game.name == "two_thirds", Game.status == "active")
        .first()
    )

    if not game:
        raise HTTPException(status_code=404, detail="No active Two-Thirds game")

    return game


@app.get(
    "/api/games/two-thirds/{game_id}/current-round",
    response_model=TwoThirdsRoundResponse,
)
def get_current_round(game_id: int, db: Session = Depends(get_db)):
    """Get the current round of a Two-Thirds game"""
    round = (
        db.query(TwoThirdsRound)
        .filter(TwoThirdsRound.game_id == game_id, TwoThirdsRound.status == "open")
        .first()
    )

    if not round:
        raise HTTPException(status_code=404, detail="No open round")

    submissions_count = (
        db.query(TwoThirdsSubmission)
        .filter(TwoThirdsSubmission.round_id == round.id)
        .count()
    )

    return TwoThirdsRoundResponse(
        id=round.id,
        round_number=round.round_number,
        status=round.status,
        average=round.average,
        two_thirds_average=round.two_thirds_average,
        winner_id=round.winner_id,
        submissions_count=submissions_count,
    )


@app.post(
    "/api/games/two-thirds/{game_id}/submit", response_model=TwoThirdsSubmissionResponse
)
def submit_two_thirds_guess(
    game_id: int, submission: TwoThirdsSubmissionCreate, db: Session = Depends(get_db)
):
    """Submit a guess for the current Two-Thirds round"""
    round = (
        db.query(TwoThirdsRound)
        .filter(TwoThirdsRound.game_id == game_id, TwoThirdsRound.status == "open")
        .first()
    )

    if not round:
        raise HTTPException(status_code=400, detail="No open round available")

    # Check if player exists
    player = db.query(Player).filter(Player.id == submission.player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    # Check if player already submitted
    existing = (
        db.query(TwoThirdsSubmission)
        .filter(
            TwoThirdsSubmission.round_id == round.id,
            TwoThirdsSubmission.player_id == submission.player_id,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400, detail="Player already submitted for this round"
        )

    new_submission = TwoThirdsSubmission(
        round_id=round.id, player_id=submission.player_id, guess=submission.guess
    )
    db.add(new_submission)
    db.commit()
    db.refresh(new_submission)

    return new_submission


@app.post(
    "/api/games/two-thirds/{game_id}/calculate", response_model=TwoThirdsResultResponse
)
def calculate_two_thirds_round(
    game_id: int, db: Session = Depends(get_db), admin: str = Depends(require_admin)
):
    """Calculate results of the current Two-Thirds round (Admin only)"""
    round = (
        db.query(TwoThirdsRound)
        .filter(TwoThirdsRound.game_id == game_id, TwoThirdsRound.status == "open")
        .first()
    )

    if not round:
        raise HTTPException(status_code=400, detail="No open round to calculate")

    submissions = (
        db.query(TwoThirdsSubmission)
        .filter(TwoThirdsSubmission.round_id == round.id)
        .all()
    )

    if len(submissions) == 0:
        raise HTTPException(status_code=400, detail="No submissions to calculate")

    # Calculate average
    guesses = [s.guess for s in submissions]
    average = sum(guesses) / len(guesses)
    two_thirds_avg = (2 / 3) * average

    # Find winner (closest to 2/3 average)
    winner = min(submissions, key=lambda s: abs(s.guess - two_thirds_avg))

    # Update round
    round.average = average
    round.two_thirds_average = two_thirds_avg
    round.winner_id = winner.player_id
    round.status = "calculated"

    # Award points based on distance (closer = more points)
    # Max distance is 100 (if guessed 0 and target is 100, or vice versa)
    # Points = 100 - distance (minimum 0)
    max_distance = 100
    for submission in submissions:
        distance = abs(submission.guess - two_thirds_avg)
        points = max(0, int(max_distance - distance))

        player = db.query(Player).filter(Player.id == submission.player_id).first()
        player.total_score += points

    db.commit()

    # Prepare response
    all_guesses = [
        {
            "player_id": s.player_id,
            "player_name": db.query(Player)
            .filter(Player.id == s.player_id)
            .first()
            .name,
            "guess": s.guess,
            "distance": abs(s.guess - two_thirds_avg),
            "points": max(0, int(max_distance - abs(s.guess - two_thirds_avg))),
        }
        for s in submissions
    ]

    return TwoThirdsResultResponse(
        round_id=round.id,
        average=average,
        two_thirds_average=two_thirds_avg,
        winner_id=winner.player_id,
        winner_name=winner_player.name,
        all_guesses=sorted(all_guesses, key=lambda x: x["distance"]),
    )


# ==================== HORSE RACE GAME ENDPOINTS ====================


def generate_horses():
    """Generate 25 horses with random speeds"""
    horses = []
    for i in range(HORSE_RACE_CONFIG["num_horses"]):
        horses.append(
            {
                "id": i + 1,
                "name": f"Horse #{i + 1}",
                "speed": random.randint(
                    HORSE_RACE_CONFIG["min_speed"], HORSE_RACE_CONFIG["max_speed"]
                ),
            }
        )
    return horses


@app.post("/api/games/horse-race/start", response_model=dict)
def start_horse_race(player_data: HorseRaceStart, db: Session = Depends(get_db)):
    """Start a new Horse Race game for a player"""
    # Verify player exists
    player = db.query(Player).filter(Player.id == player_data.player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    # Check if player has already played 2 times
    completion = (
        db.query(HorseRaceGameCompletion)
        .filter(HorseRaceGameCompletion.player_id == player_data.player_id)
        .first()
    )

    if completion and completion.completion_count >= 2:
        raise HTTPException(
            status_code=400,
            detail="You have already played the Horse Race game 2 times. Maximum plays reached.",
        )

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
        "total_horses": HORSE_RACE_CONFIG["num_horses"],
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
    game_id: int, selection: HorseSelectionSubmit, db: Session = Depends(get_db)
):
    """Race selected horses and return results"""
    horse_game = db.query(HorseRaceGame).filter(HorseRaceGame.id == game_id).first()

    if not horse_game:
        raise HTTPException(status_code=404, detail="Horse race game not found")

    # Validate horse IDs
    if any(
        hid < 1 or hid > HORSE_RACE_CONFIG["num_horses"]
        for hid in selection.selected_horse_ids
    ):
        raise HTTPException(status_code=400, detail="Invalid horse ID")

    if len(selection.selected_horse_ids) != HORSE_RACE_CONFIG["horses_per_race"]:
        raise HTTPException(
            status_code=400,
            detail=f"Must select exactly {HORSE_RACE_CONFIG['horses_per_race']} horses",
        )

    # Get selected horses with speeds
    horses = horse_game.horses_data
    selected = [h for h in horses if h["id"] in selection.selected_horse_ids]

    # Sort by speed
    race_results = sorted(selected, key=lambda x: x["speed"], reverse=True)

    # Get or create player's attempts
    player_attempts = (
        db.query(HorseRaceAttempt)
        .filter(
            HorseRaceAttempt.game_id == game_id,
            HorseRaceAttempt.player_id == selection.player_id,
        )
        .all()
    )

    round_number = len(player_attempts) + 1

    # Create attempt record
    attempt = HorseRaceAttempt(
        game_id=game_id,
        player_id=selection.player_id,
        round_number=round_number,
        selected_horses=selection.selected_horse_ids,
        race_results=[
            {"id": h["id"], "name": h["name"], "speed": h["speed"]}
            for h in race_results
        ],
        total_rounds_used=round_number,
    )
    db.add(attempt)
    db.commit()

    return HorseRaceRoundResult(
        round_number=round_number,
        selected_horses=selected,
        race_results=race_results,
        message=f"Round {round_number} completed! The fastest horse was {race_results[0]['name']}.",
    )


@app.post("/api/games/horse-race/{game_id}/submit-top-three", response_model=dict)
def submit_top_three(game_id: int, data: dict, db: Session = Depends(get_db)):
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
    rounds_used = (
        db.query(HorseRaceAttempt)
        .filter(
            HorseRaceAttempt.game_id == game_id, HorseRaceAttempt.player_id == player_id
        )
        .count()
    )

    player = db.query(Player).filter(Player.id == player_id).first()

    if is_correct:
        # Changed formula: max(100 - rounds*5, 10) instead of max(50 - rounds*5, 10)
        score = max(100 - (rounds_used * 5), 10)

        player.total_score += score

        latest_attempt = (
            db.query(HorseRaceAttempt)
            .filter(
                HorseRaceAttempt.game_id == game_id,
                HorseRaceAttempt.player_id == player_id,
            )
            .order_by(HorseRaceAttempt.round_number.desc())
            .first()
        )

        if latest_attempt:
            latest_attempt.identified_top_three = True
            latest_attempt.completed = True

        # Increment game completion count
        completion = (
            db.query(HorseRaceGameCompletion)
            .filter(HorseRaceGameCompletion.player_id == player_id)
            .first()
        )

        if not completion:
            completion = HorseRaceGameCompletion(
                player_id=player_id, completion_count=1
            )
            db.add(completion)
        else:
            completion.completion_count += 1

        db.commit()

        return {
            "correct": True,
            "score": score,
            "rounds_used": rounds_used,
            "message": f"Congratulations! You found the top 3 in {rounds_used} rounds and earned {score} points!",
            "actual_top_three": actual_top_three,
        }
    else:
        # Wrong submission penalty: -10 points
        penalty = -10
        player.total_score += penalty

        # Increment game completion count even on failure
        completion = (
            db.query(HorseRaceGameCompletion)
            .filter(HorseRaceGameCompletion.player_id == player_id)
            .first()
        )

        if not completion:
            completion = HorseRaceGameCompletion(
                player_id=player_id, completion_count=1
            )
            db.add(completion)
        else:
            completion.completion_count += 1

        db.commit()

        return {
            "correct": False,
            "penalty": penalty,
            "rounds_used": rounds_used,
            "message": "Incorrect! You lost 10 points. Keep trying!",
            "your_guess": [
                next(h for h in horses if h["id"] == hid) for hid in top_three_ids
            ],
        }


# ==================== GENERAL ENDPOINTS ====================


@app.get("/")
def root():
    """Root endpoint"""
    return {"message": "Game Theory Platform API", "version": "2.0.0", "docs": "/docs"}


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
