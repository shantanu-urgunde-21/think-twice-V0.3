from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from database import MarketGame, get_db
from schemas import MarketActionSubmit
from game.market import engine

router = APIRouter(prefix="/api/games/market", tags=["Hidden Market Game"])


def _get_market_game(game_id: int, db: Session) -> MarketGame:
    market_game = db.query(MarketGame).filter(MarketGame.game_id == game_id).first()
    if not market_game:
        raise HTTPException(404, "Market game not found")
    return market_game


@router.get("/{game_id}/view/{player_id}")
def get_market_view(game_id: int, player_id: int, db: Session = Depends(get_db)):
    """Per-player projection. Never returns another player's private_signal
    or another player's cash/inventory — see game/market/rules.py:project()."""
    market_game = _get_market_game(game_id, db)
    try:
        view = engine.get_player_view(db, market_game, player_id)
    except KeyError:
        raise HTTPException(404, "Player not part of this market game")
    return view


@router.post("/{game_id}/submit")
def submit_market_action(
    game_id: int,
    submission: MarketActionSubmit,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    market_game = _get_market_game(game_id, db)

    try:
        engine.submit_action(
            db, market_game, submission.player_id, submission.action_type, submission.qty
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    from routers.websockets import manager

    background_tasks.add_task(
        manager.broadcast_game,
        game_id,
        {
            "event": "market_submission",
            "submissions_count": engine.submissions_count(db, market_game),
            "total_players": engine.human_player_count(db, market_game)
            + (1 if market_game.include_ai else 0),
        },
    )

    return {"success": True}


@router.post("/{game_id}/resolve")
def resolve_market_round(game_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Runs the (synchronous, artificially slow) AI turn if needed, then
    resolves the round. In V1 this endpoint is host/deadline-triggered from
    the frontend; Phase 4 moves the AI call off this request path entirely."""
    market_game = _get_market_game(game_id, db)

    engine.run_ai_turn_if_needed(db, market_game)

    try:
        result = engine.resolve_round(db, market_game)
    except ValueError as e:
        raise HTTPException(400, str(e))

    from routers.websockets import manager

    background_tasks.add_task(
        manager.broadcast_game,
        game_id,
        {"event": "market_round_resolved", **result},
    )

    if result["finished"]:
        background_tasks.add_task(
            manager.broadcast_game,
            game_id,
            {"event": "market_game_finished", "scores": engine.final_scores(db, market_game)},
        )

    return result


@router.get("/{game_id}/results")
def get_market_results(game_id: int, db: Session = Depends(get_db)):
    market_game = _get_market_game(game_id, db)
    if not market_game.finished:
        raise HTTPException(400, "Game not finished yet")
    return {
        "scores": engine.final_scores(db, market_game),
        "price_history": market_game.price_history,
    }
