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

# Use NullPool for Railway/serverless environments
engine = create_engine(
    DATABASE_URL, poolclass=NullPool, connect_args={"connect_timeout": 10}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Models
class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
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


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    status = Column(String, default="waiting", index=True)
    round_number = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    participations = relationship(
        "GameParticipation", back_populates="game", cascade="all, delete-orphan"
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
    game_id = Column(Integer, ForeignKey("games.id", ondelete="CASCADE"))
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"))
    score = Column(Integer, default=0)

    # Relationships
    game = relationship("Game", back_populates="participations")
    player = relationship("Player", back_populates="game_participations")


# Two-Thirds Game Models
class TwoThirdsRound(Base):
    __tablename__ = "two_thirds_rounds"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id", ondelete="CASCADE"))
    round_number = Column(Integer)
    status = Column(String, default="open", index=True)
    average = Column(Float, nullable=True)
    two_thirds_average = Column(Float, nullable=True)
    winner_id = Column(
        Integer, ForeignKey("players.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    submissions = relationship(
        "TwoThirdsSubmission", back_populates="round", cascade="all, delete-orphan"
    )


class TwoThirdsSubmission(Base):
    __tablename__ = "two_thirds_submissions"

    id = Column(Integer, primary_key=True, index=True)
    round_id = Column(Integer, ForeignKey("two_thirds_rounds.id", ondelete="CASCADE"))
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"))
    guess = Column(Integer, nullable=False)
    submitted_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    round = relationship("TwoThirdsRound", back_populates="submissions")
    player = relationship("Player", back_populates="two_thirds_submissions")


# Horse Race Game Models
class HorseRaceGame(Base):
    __tablename__ = "horse_race_games"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id", ondelete="CASCADE"), unique=True)
    horses_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class HorseRaceAttempt(Base):
    __tablename__ = "horse_race_attempts"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("horse_race_games.id", ondelete="CASCADE"))
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"))
    round_number = Column(Integer)
    selected_horses = Column(JSON)
    race_results = Column(JSON)
    completed = Column(Boolean, default=False)
    total_rounds_used = Column(Integer, default=0)
    identified_top_three = Column(Boolean, default=False)
    submitted_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    player = relationship("Player", back_populates="horse_race_attempts")


class HorseRaceGameCompletion(Base):
    """Track number of times a player has completed horse race games"""

    __tablename__ = "horse_race_game_completions"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(
        Integer, ForeignKey("players.id", ondelete="CASCADE"), unique=True
    )
    completion_count = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables and default settings"""
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
            ]
            db.add_all(games)
            db.commit()
    finally:
        db.close()
