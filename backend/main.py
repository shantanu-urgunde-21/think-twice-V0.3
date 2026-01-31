from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import random
from datetime import datetime, timedelta

from database import (
    get_db,
    init_db,
    Player,
    Game,
    GameSettings,
    TwoThirdsRound,
    TwoThirdsSubmission,
    HorseRaceGame,
    HorseRaceAttempt,
)
from schemas import (
    PlayerCreate,
    PlayerResponse,
    GameResponse,
    TwoThirdsSubmissionCreate,
    TwoThirdsResultResponse,
    HorseRaceStart,
    HorseSelectionSubmit,
    LeaderboardEntry,
    GameSettingsUpdate,
    GameSettingsResponse,
)
from config import TWO_THIRDS_CONFIG, HORSE_RACE_CONFIG, MAX_PLAYERS, CORS_ORIGINS
from auth import (
    AdminLogin,
    Token,
    authenticate_admin,
    create_access_token,
    require_admin,
)

app = FastAPI(title="Game Theory Platform", version="2.0.0")

# CORS - simplified
origins = ["http://localhost:3000", "http://localhost:8000"]
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


# ==================== AUTH ====================


@app.post("/api/auth/login", response_model=Token)
def login(credentials: AdminLogin):
    if not authenticate_admin(credentials.username, credentials.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(
        data={"sub": credentials.username}, expires_delta=timedelta(minutes=480)
    )
    return {"access_token": token, "token_type": "bearer"}


@app.get("/api/auth/verify")
def verify_admin(admin: str = Depends(require_admin)):
    return {"authenticated": True}


# ==================== GAME SETTINGS ====================


@app.get("/api/games/enabled")
def get_enabled_games(db: Session = Depends(get_db)):
    return db.query(GameSettings).filter(GameSettings.enabled == True).all()


@app.get("/api/games/settings", response_model=List[GameSettingsResponse])
def get_all_settings(
    db: Session = Depends(get_db), admin: str = Depends(require_admin)
):
    return db.query(GameSettings).all()


@app.put("/api/games/settings/{game_name}", response_model=GameSettingsResponse)
def update_settings(
    game_name: str,
    update: GameSettingsUpdate,
    db: Session = Depends(get_db),
    admin: str = Depends(require_admin),
):
    setting = db.query(GameSettings).filter(GameSettings.game_name == game_name).first()
    if not setting:
        raise HTTPException(404, "Game not found")
    setting.enabled = update.enabled
    db.commit()
    db.refresh(setting)
    return setting


# ==================== PLAYERS ====================


@app.post("/api/players", response_model=PlayerResponse)
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


@app.get("/api/players", response_model=List[PlayerResponse])
def get_players(db: Session = Depends(get_db)):
    return db.query(Player).order_by(Player.created_at).all()


@app.get("/api/players/{player_id}", response_model=PlayerResponse)
def get_player(player_id: int, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(404, "Player not found")
    return player


@app.delete("/api/players/{player_id}")
def delete_player(
    player_id: int, db: Session = Depends(get_db), admin: str = Depends(require_admin)
):
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(404, "Player not found")
    db.delete(player)
    db.commit()
    return {"message": f"Player {player.name} deleted"}


@app.get("/api/leaderboard", response_model=List[LeaderboardEntry])
def get_leaderboard(db: Session = Depends(get_db)):
    players = db.query(Player).order_by(Player.total_score.desc()).all()
    return [
        LeaderboardEntry(
            rank=idx + 1, player_id=p.id, player_name=p.name, total_score=p.total_score
        )
        for idx, p in enumerate(players)
    ]


# ==================== TWO-THIRDS GAME ====================


@app.post("/api/games/two-thirds/start", response_model=GameResponse)
def start_two_thirds(
    db: Session = Depends(get_db), admin: str = Depends(require_admin)
):
    existing = (
        db.query(Game)
        .filter(Game.name == "two_thirds", Game.status == "active")
        .first()
    )
    if existing:
        raise HTTPException(400, "Active game already exists")

    game = Game(name="two_thirds", status="active")
    db.add(game)
    db.commit()
    db.refresh(game)

    round = TwoThirdsRound(game_id=game.id, round_number=1, status="open")
    db.add(round)
    db.commit()

    return game


@app.get("/api/games/two-thirds/active", response_model=GameResponse)
def get_active_two_thirds(db: Session = Depends(get_db)):
    game = (
        db.query(Game)
        .filter(Game.name == "two_thirds", Game.status == "active")
        .first()
    )
    if not game:
        raise HTTPException(404, "No active game")
    return game


@app.get("/api/games/two-thirds/{game_id}/current-round")
def get_current_round(game_id: int, db: Session = Depends(get_db)):
    round = (
        db.query(TwoThirdsRound)
        .filter(TwoThirdsRound.game_id == game_id, TwoThirdsRound.status == "open")
        .first()
    )
    if not round:
        raise HTTPException(404, "No open round")

    submissions_count = (
        db.query(TwoThirdsSubmission)
        .filter(TwoThirdsSubmission.round_id == round.id)
        .count()
    )
    return {
        "id": round.id,
        "round_number": round.round_number,
        "status": round.status,
        "submissions_count": submissions_count,
    }


@app.post("/api/games/two-thirds/{game_id}/submit")
def submit_two_thirds_guess(
    game_id: int, submission: TwoThirdsSubmissionCreate, db: Session = Depends(get_db)
):
    round = (
        db.query(TwoThirdsRound)
        .filter(TwoThirdsRound.game_id == game_id, TwoThirdsRound.status == "open")
        .first()
    )
    if not round:
        raise HTTPException(400, "No open round")

    existing = (
        db.query(TwoThirdsSubmission)
        .filter(
            TwoThirdsSubmission.round_id == round.id,
            TwoThirdsSubmission.player_id == submission.player_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(400, "Already submitted")

    new_submission = TwoThirdsSubmission(
        round_id=round.id, player_id=submission.player_id, guess=submission.guess
    )
    db.add(new_submission)
    db.commit()
    return {"success": True, "message": "Guess submitted"}


@app.post(
    "/api/games/two-thirds/{game_id}/calculate", response_model=TwoThirdsResultResponse
)
def calculate_two_thirds(
    game_id: int, db: Session = Depends(get_db), admin: str = Depends(require_admin)
):
    round = (
        db.query(TwoThirdsRound)
        .filter(TwoThirdsRound.game_id == game_id, TwoThirdsRound.status == "open")
        .first()
    )
    if not round:
        raise HTTPException(400, "No open round")

    submissions = (
        db.query(TwoThirdsSubmission)
        .filter(TwoThirdsSubmission.round_id == round.id)
        .all()
    )
    if not submissions:
        raise HTTPException(400, "No submissions")

    guesses = [s.guess for s in submissions]
    average = sum(guesses) / len(guesses)
    two_thirds_avg = (2 / 3) * average

    winner = min(submissions, key=lambda s: abs(s.guess - two_thirds_avg))

    round.average = average
    round.two_thirds_average = two_thirds_avg
    round.winner_id = winner.player_id
    round.status = "calculated"

    winner_player = db.query(Player).filter(Player.id == winner.player_id).first()
    winner_player.total_score += TWO_THIRDS_CONFIG["winner_points"]

    # Award 1 point to everyone else for participation
    for submission in submissions:
        if submission.player_id != winner.player_id:
            player = db.query(Player).filter(Player.id == submission.player_id).first()
            player.total_score += 1

    db.commit()

    all_guesses = []
    for s in submissions:
        player = db.query(Player).filter(Player.id == s.player_id).first()
        points = (
            TWO_THIRDS_CONFIG["winner_points"] if s.player_id == winner.player_id else 1
        )
        all_guesses.append(
            {
                "player_id": s.player_id,
                "player_name": player.name,
                "guess": s.guess,
                "distance": abs(s.guess - two_thirds_avg),
                "points": points,
            }
        )

    return TwoThirdsResultResponse(
        round_id=round.id,
        average=average,
        two_thirds_average=two_thirds_avg,
        winner_id=winner.player_id,
        winner_name=winner_player.name,
        all_guesses=sorted(all_guesses, key=lambda x: x["distance"]),
    )


@app.post("/api/games/two-thirds/{game_id}/close")
def close_two_thirds(
    game_id: int, db: Session = Depends(get_db), admin: str = Depends(require_admin)
):
    """Close the game and create a new round for next game"""
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(404, "Game not found")

    game.status = "completed"
    game.completed_at = datetime.utcnow()

    # Close any open rounds
    open_rounds = (
        db.query(TwoThirdsRound)
        .filter(TwoThirdsRound.game_id == game_id, TwoThirdsRound.status == "open")
        .all()
    )
    for r in open_rounds:
        r.status = "closed"

    # Create a new game and round for next round
    new_game = Game(name="two_thirds", status="active")
    db.add(new_game)
    db.commit()
    db.refresh(new_game)

    new_round = TwoThirdsRound(game_id=new_game.id, round_number=1, status="open")
    db.add(new_round)
    db.commit()

    return {
        "message": "Game closed successfully and new game started",
        "new_game_id": new_game.id,
    }


@app.get("/api/admin/game-stats/{game_id}")
def get_game_stats(
    game_id: int, db: Session = Depends(get_db), admin: str = Depends(require_admin)
):
    """Get detailed game statistics for admin"""
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(404, "Game not found")

    if game.name == "two_thirds":
        rounds = (
            db.query(TwoThirdsRound).filter(TwoThirdsRound.game_id == game_id).all()
        )
        stats = []
        for round in rounds:
            submissions = (
                db.query(TwoThirdsSubmission)
                .filter(TwoThirdsSubmission.round_id == round.id)
                .all()
            )
            player_data = [
                {
                    "player_name": db.query(Player)
                    .filter(Player.id == sub.player_id)
                    .first()
                    .name,
                    "guess": sub.guess,
                    "score": db.query(Player)
                    .filter(Player.id == sub.player_id)
                    .first()
                    .total_score,
                }
                for sub in submissions
            ]
            stats.append(
                {
                    "round_number": round.round_number,
                    "status": round.status,
                    "average": round.average,
                    "two_thirds_average": round.two_thirds_average,
                    "submissions": player_data,
                }
            )
        return {"game_type": "two_thirds", "rounds": stats}

    return {"message": "Stats not available"}


# ==================== HORSE RACE GAME ====================


def generate_horses():
    """Generate horses WITHOUT exposing speeds"""
    return [
        {
            "id": i + 1,
            "name": f"Horse #{i + 1}",
            "speed": random.randint(
                HORSE_RACE_CONFIG["min_speed"], HORSE_RACE_CONFIG["max_speed"]
            ),
        }
        for i in range(HORSE_RACE_CONFIG["num_horses"])
    ]


@app.post("/api/games/horse-race/start")
def start_horse_race(player_data: HorseRaceStart, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.id == player_data.player_id).first()
    if not player:
        raise HTTPException(404, "Player not found")

    # CHECK: Count how many horse race games this player has completed
    completed_games = (
        db.query(HorseRaceAttempt)
        .filter(
            HorseRaceAttempt.player_id == player_data.player_id,
            HorseRaceAttempt.completed == True,
        )
        .distinct(HorseRaceAttempt.game_id)
        .count()
    )

    # LIMIT: Prevent starting if already completed 2 games
    if completed_games >= 2:
        raise HTTPException(
            status_code=403,
            detail=f"You have completed the maximum 2 Horse Race games. You cannot play anymore.",
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
        "message": "Horse race started!",
        "total_horses": HORSE_RACE_CONFIG["num_horses"],
        "games_completed": completed_games,
    }


@app.get("/api/games/horse-race/player-status/{player_id}")
def get_player_horse_status(player_id: int, db: Session = Depends(get_db)):
    """Check how many horse race games player has completed"""
    completed_games = (
        db.query(HorseRaceAttempt)
        .filter(
            HorseRaceAttempt.player_id == player_id, HorseRaceAttempt.completed == True
        )
        .distinct(HorseRaceAttempt.game_id)
        .count()
    )

    return {
        "player_id": player_id,
        "games_completed": completed_games,
        "games_remaining": max(0, 2 - completed_games),
        "can_play": completed_games < 2,
    }


@app.get("/api/games/horse-race/{game_id}/horses")
def get_horses(game_id: int, db: Session = Depends(get_db)):
    """Get horses WITHOUT speeds - only ID and name"""
    horse_game = db.query(HorseRaceGame).filter(HorseRaceGame.id == game_id).first()
    if not horse_game:
        raise HTTPException(404, "Game not found")
    return [{"id": h["id"], "name": h["name"]} for h in horse_game.horses_data]


@app.post("/api/games/horse-race/{game_id}/race")
def race_horses(
    game_id: int, selection: HorseSelectionSubmit, db: Session = Depends(get_db)
):
    horse_game = db.query(HorseRaceGame).filter(HorseRaceGame.id == game_id).first()
    if not horse_game:
        raise HTTPException(404, "Game not found")

    if any(
        hid < 1 or hid > HORSE_RACE_CONFIG["num_horses"]
        for hid in selection.selected_horse_ids
    ):
        raise HTTPException(400, "Invalid horse ID")
    if len(selection.selected_horse_ids) != HORSE_RACE_CONFIG["horses_per_race"]:
        raise HTTPException(
            400, f"Must select exactly {HORSE_RACE_CONFIG['horses_per_race']} horses"
        )

    horses = horse_game.horses_data
    selected = [h for h in horses if h["id"] in selection.selected_horse_ids]
    race_results = sorted(selected, key=lambda x: x["speed"], reverse=True)

    player_attempts = (
        db.query(HorseRaceAttempt)
        .filter(
            HorseRaceAttempt.game_id == game_id,
            HorseRaceAttempt.player_id == selection.player_id,
        )
        .all()
    )
    round_number = len(player_attempts) + 1

    attempt = HorseRaceAttempt(
        game_id=game_id,
        player_id=selection.player_id,
        round_number=round_number,
        selected_horses=selection.selected_horse_ids,
        race_results=[
            {"id": h["id"], "name": h["name"], "position": idx + 1}
            for idx, h in enumerate(race_results)
        ],
        total_rounds_used=round_number,
    )
    db.add(attempt)
    db.commit()

    # Return ONLY positions, NO speeds
    return {
        "round_number": round_number,
        "race_results": [
            {"id": h["id"], "name": h["name"], "position": idx + 1}
            for idx, h in enumerate(race_results)
        ],
        "message": f"Round {round_number}: {race_results[0]['name']} was fastest!",
    }


@app.post("/api/games/horse-race/{game_id}/submit-top-three")
def submit_top_three(game_id: int, data: dict, db: Session = Depends(get_db)):
    player_id = data.get("player_id")
    top_three_ids = data.get("top_three_ids")

    if not top_three_ids or len(top_three_ids) != 3:
        raise HTTPException(400, "Must submit exactly 3 horse IDs")

    horse_game = db.query(HorseRaceGame).filter(HorseRaceGame.id == game_id).first()
    if not horse_game:
        raise HTTPException(404, "Game not found")

    horses = horse_game.horses_data
    actual_top_three = sorted(horses, key=lambda x: x["speed"], reverse=True)[:3]
    actual_ids = [h["id"] for h in actual_top_three]

    is_correct = top_three_ids == actual_ids
    rounds_used = (
        db.query(HorseRaceAttempt)
        .filter(
            HorseRaceAttempt.game_id == game_id, HorseRaceAttempt.player_id == player_id
        )
        .count()
    )

    if is_correct:
        score = max(50 - (rounds_used * 5), 10)
        player = db.query(Player).filter(Player.id == player_id).first()
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

        db.commit()

        return {
            "correct": True,
            "score": score,
            "rounds_used": rounds_used,
            "message": f"Congratulations! You earned {score} points in {rounds_used} rounds!",
            "actual_top_three": [
                {"id": h["id"], "name": h["name"]} for h in actual_top_three
            ],
        }
    else:
        return {
            "correct": False,
            "rounds_used": rounds_used,
            "message": "Incorrect. Keep trying!",
        }


@app.get("/api/admin/horse-race-scores/{game_id}")
def get_horse_race_scores(
    game_id: int, db: Session = Depends(get_db), admin: str = Depends(require_admin)
):
    """Get participant scores for horse race (admin only)"""
    attempts = (
        db.query(HorseRaceAttempt).filter(HorseRaceAttempt.game_id == game_id).all()
    )

    player_stats = {}
    for attempt in attempts:
        if attempt.player_id not in player_stats:
            player = db.query(Player).filter(Player.id == attempt.player_id).first()
            player_stats[attempt.player_id] = {
                "player_name": player.name,
                "total_score": player.total_score,
                "rounds_used": attempt.total_rounds_used,
                "completed": attempt.completed,
            }

    return {"participants": list(player_stats.values())}


# ==================== GENERAL ====================


@app.get("/")
def root():
    return {"message": "Game Theory Platform API", "version": "2.0.0"}


@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    return {
        "total_players": db.query(Player).count(),
        "max_players": MAX_PLAYERS,
        "active_games": db.query(Game).filter(Game.status == "active").count(),
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
