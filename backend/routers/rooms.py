from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import random
import string
from database import get_db, Game, Player, RoomMembership, GameParticipation
from schemas import RoomCreate, RoomJoin, RoomDetailsResponse, RoomMemberInfo
from routers.websockets import manager

router = APIRouter(prefix="/api/rooms", tags=["Rooms & Lobbies"])

def generate_room_code(db: Session) -> str:
    while True:
        code = "".join(random.choices(string.ascii_uppercase + "0123456789", k=4))
        # Ensure code uniqueness
        existing = db.query(Game).filter(Game.room_code == code, Game.status != "finished").first()
        if not existing:
            return code

@router.post("/create", response_model=RoomDetailsResponse)
def create_room(room: RoomCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.id == room.player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Generate unique room code
    room_code = generate_room_code(db)
    
    # Create the game session as waiting room
    game = Game(
        name=room.game_name,
        status="waiting",
        room_code=room_code,
        host_id=room.player_id,
        max_players=room.max_players or 10
    )
    db.add(game)
    db.commit()
    db.refresh(game)
    
    # Add creator to membership
    membership = RoomMembership(game_id=game.id, player_id=room.player_id, is_ready=True)
    db.add(membership)
    db.commit()
    
    # Broadcast to lobby websocket
    background_tasks.add_task(manager.broadcast_lobby, {"event": "lobby_updated", "room_code": room_code})
    
    return get_room_details_internal(room_code, db)

@router.post("/join", response_model=RoomDetailsResponse)
def join_room(join_info: RoomJoin, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.id == join_info.player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
        
    game = db.query(Game).filter(Game.room_code == join_info.room_code, Game.status == "waiting").first()
    if not game:
        raise HTTPException(status_code=404, detail="Active room not found or game already started")
        
    # Check if already joined
    existing_membership = db.query(RoomMembership).filter(
        RoomMembership.game_id == game.id,
        RoomMembership.player_id == join_info.player_id
    ).first()
    
    if not existing_membership:
        # Check capacity
        current_members = db.query(RoomMembership).filter(RoomMembership.game_id == game.id).count()
        if current_members >= game.max_players:
            raise HTTPException(status_code=400, detail="Room is full")
            
        membership = RoomMembership(game_id=game.id, player_id=join_info.player_id, is_ready=False)
        db.add(membership)
        db.commit()
        
    # Broadcast to lobby websocket
    background_tasks.add_task(manager.broadcast_lobby, {"event": "lobby_updated", "room_code": join_info.room_code})
    # Broadcast to game websocket room
    background_tasks.add_task(manager.broadcast_game, game.id, {"event": "player_joined", "player_name": player.name})
    
    return get_room_details_internal(join_info.room_code, db)

@router.get("/{room_code}", response_model=RoomDetailsResponse)
def get_room_details(room_code: str, db: Session = Depends(get_db)):
    return get_room_details_internal_sync(room_code, db)

@router.post("/{room_code}/ready")
def toggle_ready(room_code: str, player_id: int, is_ready: bool, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.room_code == room_code, Game.status == "waiting").first()
    if not game:
        raise HTTPException(status_code=404, detail="Room not found")
        
    membership = db.query(RoomMembership).filter(
        RoomMembership.game_id == game.id,
        RoomMembership.player_id == player_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=404, detail="Player not in room")
        
    membership.is_ready = is_ready
    db.commit()
    
    background_tasks.add_task(manager.broadcast_game, game.id, {"event": "player_ready", "player_id": player_id, "is_ready": is_ready})
    background_tasks.add_task(manager.broadcast_lobby, {"event": "lobby_updated", "room_code": room_code})
    
    return {"success": True}

@router.post("/{room_code}/start")
def start_room_game(room_code: str, host_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.room_code == room_code, Game.status == "waiting").first()
    if not game:
        raise HTTPException(status_code=404, detail="Room not found or game already active")
        
    if game.host_id != host_id:
        raise HTTPException(status_code=403, detail="Only the host can start the game")
        
    memberships = db.query(RoomMembership).filter(RoomMembership.game_id == game.id).all()
    if len(memberships) < 2:
        # For testing, we can allow 1 player, but usually we want multiplayer. Let's allow starting anyway but log it.
        pass
        
    # Change status to active
    game.status = "active"
    db.commit()
    
    # Initialize GameParticipation records for all members
    for m in memberships:
        existing_p = db.query(GameParticipation).filter(
            GameParticipation.game_id == game.id,
            GameParticipation.player_id == m.player_id
        ).first()
        if not existing_p:
            gp = GameParticipation(game_id=game.id, player_id=m.player_id, score=0)
            db.add(gp)
    
    # Specifically initialize specific game rounds:
    if game.name == "two_thirds":
        from database import TwoThirdsRound
        # Create round 1
        existing_round = db.query(TwoThirdsRound).filter(
            TwoThirdsRound.game_id == game.id,
            TwoThirdsRound.round_number == 1
        ).first()
        if not existing_round:
            r = TwoThirdsRound(game_id=game.id, round_number=1, status="open")
            db.add(r)
    elif game.name == "fish_pond":
        from database import FishPondGame
        existing_fp = db.query(FishPondGame).filter(FishPondGame.game_id == game.id).first()
        if not existing_fp:
            # Seed defaults
            fp = FishPondGame(
                game_id=game.id,
                status="active",
                initial_fish=100,
                current_fish=100,
                regeneration_rate=0.5,
                max_rounds=5,
                current_round=1,
                collapsed=False
            )
            db.add(fp)
            
    db.commit()
    
    # Broadcast game start
    background_tasks.add_task(manager.broadcast_game, game.id, {"event": "game_started", "game_name": game.name, "game_id": game.id, "room_code": room_code})
    background_tasks.add_task(manager.broadcast_lobby, {"event": "game_started", "game_name": game.name, "game_id": game.id, "room_code": room_code})
    
    return {"success": True, "game_id": game.id}

@router.post("/{room_code}/leave")
def leave_room(room_code: str, player_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.room_code == room_code).first()
    if not game:
        raise HTTPException(status_code=404, detail="Room not found")
        
    membership = db.query(RoomMembership).filter(
        RoomMembership.game_id == game.id,
        RoomMembership.player_id == player_id
    ).first()
    
    if membership:
        db.delete(membership)
        db.commit()
        
    # Check remaining members
    remaining = db.query(RoomMembership).filter(RoomMembership.game_id == game.id).all()
    if len(remaining) == 0:
        # Archive room
        game.status = "finished"
        db.commit()
    else:
        # If host left, assign new host
        if game.host_id == player_id:
            game.host_id = remaining[0].player_id
            db.commit()
            
    background_tasks.add_task(manager.broadcast_game, game.id, {"event": "player_left", "player_id": player_id})
    background_tasks.add_task(manager.broadcast_lobby, {"event": "lobby_updated", "room_code": room_code})
    
    return {"success": True}


@router.get("/active-player-game/{player_id}")
def get_active_player_game(player_id: int, db: Session = Depends(get_db)):
    membership = db.query(RoomMembership).join(Game).filter(
        RoomMembership.player_id == player_id,
        Game.status == "active"
    ).first()
    if not membership:
        game = db.query(Game).filter(Game.host_id == player_id, Game.status == "active").first()
        if game:
            return {"game_id": game.id, "game_name": game.name, "room_code": game.room_code}
        raise HTTPException(404, "No active game found for player")
    return {"game_id": membership.game.id, "game_name": membership.game.name, "room_code": membership.game.room_code}


# Helpers
def get_room_details_internal(room_code: str, db: Session) -> dict:
    return get_room_details_internal_sync(room_code, db)

def get_room_details_internal_sync(room_code: str, db: Session) -> dict:
    game = db.query(Game).filter(Game.room_code == room_code, Game.status != "finished").first()
    if not game:
        raise HTTPException(status_code=404, detail="Room not found")
        
    memberships = db.query(RoomMembership).filter(RoomMembership.game_id == game.id).all()
    members_info = []
    
    for m in memberships:
        p = db.query(Player).filter(Player.id == m.player_id).first()
        if p:
            members_info.append(RoomMemberInfo(
                player_id=m.player_id,
                player_name=p.name,
                is_ready=m.is_ready
            ))
            
    host_name = None
    if game.host_id:
        host = db.query(Player).filter(Player.id == game.host_id).first()
        if host:
            host_name = host.name
            
    return RoomDetailsResponse(
        game_id=game.id,
        room_code=game.room_code,
        game_name=game.name,
        status=game.status,
        host_id=game.host_id,
        host_name=host_name,
        members=members_info,
        max_players=game.max_players
    )
