from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Boolean,
    ForeignKey,
    DateTime,
    JSON,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import NullPool
from datetime import datetime
from config import DATABASE_URL

# SQLite requires check_same_thread=False, PostgreSQL requires connect_timeout=10
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    connect_args["connect_timeout"] = 10

# NullPool avoids idle-connection buildup; see internaldocs/horizontalscaling.md
# for the tradeoff if this ever needs to move to a pooled connection.
engine = create_engine(
    DATABASE_URL, poolclass=NullPool, connect_args=connect_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Models
class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    passcode = Column(String(6), nullable=True)
    total_score = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    game_participations = relationship(
        "GameParticipation", back_populates="player", cascade="all, delete-orphan"
    )
    two_thirds_submissions = relationship(
        "TwoThirdsSubmission", back_populates="player", cascade="all, delete-orphan"
    )
    horse_race_attempts = relationship(
        "HorseRaceAttempt", back_populates="player", cascade="all, delete-orphan"
    )
    fish_pond_submissions = relationship(
        "FishPondSubmission", back_populates="player", cascade="all, delete-orphan"
    )
    room_memberships = relationship(
        "RoomMembership", back_populates="player", cascade="all, delete-orphan"
    )


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    status = Column(String, default="waiting", index=True)
    round_number = Column(Integer, default=1)
    
    # Room specific columns
    room_code = Column(String(6), unique=True, index=True, nullable=True)
    host_id = Column(Integer, ForeignKey("players.id", ondelete="SET NULL"), nullable=True)
    max_players = Column(Integer, default=10)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    participations = relationship(
        "GameParticipation", back_populates="game", cascade="all, delete-orphan"
    )
    room_members = relationship(
        "RoomMembership", back_populates="game", cascade="all, delete-orphan"
    )


class GameSettings(Base):
    """Global settings for which games are displayed"""

    __tablename__ = "game_settings"

    id = Column(Integer, primary_key=True, index=True)
    game_name = Column(
        String, unique=True, nullable=False
    )  # "two_thirds", "horse_race"
    enabled = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GameParticipation(Base):
    __tablename__ = "game_participations"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id", ondelete="CASCADE"), index=True)
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"), index=True)
    score = Column(Integer, default=0)

    # Relationships
    game = relationship("Game", back_populates="participations")
    player = relationship("Player", back_populates="game_participations")


class RoomMembership(Base):
    __tablename__ = "room_memberships"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id", ondelete="CASCADE"), index=True)
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"), index=True)
    is_ready = Column(Boolean, default=False)
    joined_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    game = relationship("Game", back_populates="room_members")
    player = relationship("Player", back_populates="room_memberships")


# Two-Thirds Game Models
class TwoThirdsRound(Base):
    __tablename__ = "two_thirds_rounds"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id", ondelete="CASCADE"), index=True)
    round_number = Column(Integer)
    status = Column(String, default="open", index=True)
    average = Column(Float, nullable=True)
    two_thirds_average = Column(Float, nullable=True)
    winner_id = Column(
        Integer, ForeignKey("players.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    submissions = relationship(
        "TwoThirdsSubmission", back_populates="round", cascade="all, delete-orphan"
    )


class TwoThirdsSubmission(Base):
    __tablename__ = "two_thirds_submissions"

    id = Column(Integer, primary_key=True, index=True)
    round_id = Column(Integer, ForeignKey("two_thirds_rounds.id", ondelete="CASCADE"), index=True)
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"), index=True)
    guess = Column(Integer, nullable=False)
    submitted_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    round = relationship("TwoThirdsRound", back_populates="submissions")
    player = relationship("Player", back_populates="two_thirds_submissions")


# Horse Race Game Models
class HorseRaceGame(Base):
    __tablename__ = "horse_race_games"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id", ondelete="CASCADE"), unique=True, index=True)
    horses_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class HorseRaceAttempt(Base):
    __tablename__ = "horse_race_attempts"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("horse_race_games.id", ondelete="CASCADE"), index=True)
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"), index=True)
    round_number = Column(Integer)
    selected_horses = Column(JSON)
    race_results = Column(JSON)
    completed = Column(Boolean, default=False)
    total_rounds_used = Column(Integer, default=0)
    identified_top_three = Column(Boolean, default=False)
    submitted_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    player = relationship("Player", back_populates="horse_race_attempts")


class FishPondGame(Base):
    __tablename__ = "fish_pond_games"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id", ondelete="CASCADE"), unique=True, index=True)
    status = Column(String, default="active", index=True)
    initial_fish = Column(Integer, default=100)
    current_fish = Column(Integer, default=100)
    regeneration_rate = Column(Float, default=0.5)
    max_rounds = Column(Integer, default=5)
    current_round = Column(Integer, default=1)
    collapsed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class FishPondSubmission(Base):
    __tablename__ = "fish_pond_submissions"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id", ondelete="CASCADE"), index=True)
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"), index=True)
    round_number = Column(Integer, index=True)
    fish_caught = Column(Integer, nullable=False)
    submitted_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    player = relationship("Player", back_populates="fish_pond_submissions")


class GameSession(Base):
    """Track game sessions for analytics"""

    __tablename__ = "game_sessions"

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"))
    player_id = Column(Integer, ForeignKey("players.id"))
    game_type = Column(String)  # "two_thirds", "horse_race"
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    points_earned = Column(Integer, default=0)
    completed = Column(Boolean, default=False)


class GameRoundAnalytics(Base):
    """Track per-round analytics"""

    __tablename__ = "game_round_analytics"

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"))
    round_number = Column(Integer)
    game_type = Column(String)
    total_participants = Column(Integer, default=0)
    average_score = Column(Float, nullable=True)
    highest_score = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PlayerGameStatistics(Base):
    """Aggregate player statistics per game type"""

    __tablename__ = "player_game_statistics"

    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey("players.id"))
    game_type = Column(String)  # "two_thirds", "horse_race"
    total_plays = Column(Integer, default=0)
    total_wins = Column(Integer, default=0)
    total_points = Column(Integer, default=0)
    average_points_per_game = Column(Float, default=0)
    last_played = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables and default settings"""
    # Migration logic for existing SQLite/Postgres DB
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    
    db = SessionLocal()
    try:
        # Check games table
        if inspector.has_table("games"):
            columns = [c["name"] for c in inspector.get_columns("games")]
            if "room_code" not in columns:
                db.execute(text("ALTER TABLE games ADD COLUMN room_code VARCHAR(6)"))
                # Create a unique index for room_code
                try:
                    db.execute(text("CREATE UNIQUE INDEX ix_games_room_code ON games (room_code)"))
                except Exception as e:
                    print(f"Skipping index creation or index exists: {e}")
            if "host_id" not in columns:
                db.execute(text("ALTER TABLE games ADD COLUMN host_id INTEGER"))
            if "max_players" not in columns:
                db.execute(text("ALTER TABLE games ADD COLUMN max_players INTEGER DEFAULT 10"))
                
        # Check players table
        if inspector.has_table("players"):
            columns = [c["name"] for c in inspector.get_columns("players")]
            if "passcode" not in columns:
                db.execute(text("ALTER TABLE players ADD COLUMN passcode VARCHAR(6)"))
                
        db.commit()
    except Exception as e:
        print(f"Migration error: {e}")
        db.rollback()
    finally:
        db.close()

    Base.metadata.create_all(bind=engine)

    # Initialize default game settings
    db = SessionLocal()
    try:
        # Check if settings already exist
        existing = db.query(GameSettings).count()
        if existing == 0:
            # Create default settings for both games (enabled)
            games = [
                GameSettings(game_name="two_thirds", enabled=True),
                GameSettings(game_name="horse_race", enabled=True),
                GameSettings(game_name="fish_pond", enabled=True),
            ]
            db.add_all(games)
            db.commit()
            
        # Seed initial admin user if none exists
        from auth import get_password_hash
        from config import ADMIN_USERNAME, ADMIN_PASSWORD
        
        admin_count = db.query(AdminUser).count()
        if admin_count == 0:
            admin = AdminUser(
                username=ADMIN_USERNAME,
                hashed_password=get_password_hash(ADMIN_PASSWORD)
            )
            db.add(admin)
            db.commit()
            
    finally:
        db.close()
