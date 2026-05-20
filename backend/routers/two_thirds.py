from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db, Player, Game, TwoThirdsRound, TwoThirdsSubmission
from schemas import GameResponse, TwoThirdsSubmissionCreate, TwoThirdsResultResponse
from config import TWO_THIRDS_CONFIG
from auth import require_admin

router = APIRouter(prefix="/api", tags=["Two-Thirds Game"])

@router.post("/games/two-thirds/start", response_model=GameResponse)
def start_two_thirds(
    db: Session = Depends(get_db), admin: str = Depends(require_admin)
):
    # First, mark any completed games as finished
    completed_games = (
        db.query(Game)
        .filter(Game.name == "two_thirds", Game.status == "completed")
        .all()
    )
    for g in completed_games:
        g.status = "finished"
    db.commit()

    # Check if there's already an active game with open rounds
    existing = (
        db.query(Game)
        .filter(Game.name == "two_thirds", Game.status == "active")
        .first()
    )
    if existing:
        # Check if it has open rounds
        open_round = (
            db.query(TwoThirdsRound)
            .filter(
                TwoThirdsRound.game_id == existing.id, TwoThirdsRound.status == "open"
            )
            .first()
        )
        if open_round:
            raise HTTPException(400, "Active game already exists")
        else:
            # No open round, so this game is orphaned - mark it as finished
            existing.status = "finished"
            db.commit()

    # Now create the new game
    game = Game(name="two_thirds", status="active")
    db.add(game)
    db.commit()
    db.refresh(game)

    round = TwoThirdsRound(game_id=game.id, round_number=1, status="open")
    db.add(round)
    db.commit()

    return game


@router.get("/games/two-thirds/active", response_model=GameResponse)
def get_active_two_thirds(db: Session = Depends(get_db)):
    game = (
        db.query(Game)
        .filter(Game.name == "two_thirds", Game.status == "active")
        .first()
    )
    if not game:
        raise HTTPException(404, "No active game")
    return game


@router.get("/games/two-thirds/{game_id}/current-round")
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


@router.post("/games/two-thirds/{game_id}/submit")
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


@router.post(
    "/games/two-thirds/{game_id}/calculate", response_model=TwoThirdsResultResponse
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


@router.post("/games/two-thirds/{game_id}/close")
def close_two_thirds(
    game_id: int, db: Session = Depends(get_db), admin: str = Depends(require_admin)
):
    """Close the game and all its rounds"""
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

    db.commit()
    return {"message": "Game closed successfully. You can start a new game now."}


@router.get("/admin/game-stats/{game_id}")
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
