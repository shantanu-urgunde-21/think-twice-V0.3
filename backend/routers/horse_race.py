from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import random
from database import get_db, Player, Game, HorseRaceGame, HorseRaceAttempt
from schemas import HorseRaceStart, HorseSelectionSubmit
from config import HORSE_RACE_CONFIG
from auth import require_admin

router = APIRouter(prefix="/api", tags=["Horse Race Game"])

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


@router.post("/games/horse-race/start")
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


@router.get("/games/horse-race/player-status/{player_id}")
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


@router.get("/games/horse-race/{game_id}/horses")
def get_horses(game_id: int, db: Session = Depends(get_db)):
    """Get horses WITHOUT speeds - only ID and name"""
    horse_game = db.query(HorseRaceGame).filter(HorseRaceGame.id == game_id).first()
    if not horse_game:
        raise HTTPException(404, "Game not found")
    return [{"id": h["id"], "name": h["name"]} for h in horse_game.horses_data]


@router.post("/games/horse-race/{game_id}/race")
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


@router.post("/games/horse-race/{game_id}/submit-top-three")
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


@router.get("/admin/horse-race-scores/{game_id}")
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
