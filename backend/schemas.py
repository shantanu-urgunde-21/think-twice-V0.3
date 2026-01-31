from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# Player Schemas
class PlayerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class PlayerResponse(BaseModel):
    id: int
    name: str
    total_score: int
    created_at: datetime

    class Config:
        from_attributes = True


# Game Schemas
class GameCreate(BaseModel):
    name: str  # "two_thirds", "horse_race", "fish_pond"


class GameResponse(BaseModel):
    id: int
    name: str
    status: str
    round_number: int
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


# Two-Thirds Game Schemas
class TwoThirdsSubmissionCreate(BaseModel):
    player_id: int
    guess: int = Field(..., ge=0, le=100)


class TwoThirdsSubmissionResponse(BaseModel):
    id: int
    player_id: int
    guess: int
    submitted_at: datetime

    class Config:
        from_attributes = True


class TwoThirdsRoundResponse(BaseModel):
    id: int
    round_number: int
    status: str
    average: Optional[float]
    two_thirds_average: Optional[float]
    winner_id: Optional[int]
    submissions_count: int

    class Config:
        from_attributes = True


class TwoThirdsResultResponse(BaseModel):
    round_id: int
    average: float
    two_thirds_average: float
    winner_id: Optional[int]
    winner_name: Optional[str]
    all_guesses: List[dict]


# Horse Race Game Schemas
class HorseRaceStart(BaseModel):
    player_id: int


class HorseSelectionSubmit(BaseModel):
    player_id: int
    selected_horse_ids: List[int] = Field(..., min_length=5, max_length=5)


class HorseRaceRoundResult(BaseModel):
    round_number: int
    selected_horses: List[dict]
    race_results: List[dict]
    message: str


class HorseRaceAttemptResponse(BaseModel):
    id: int
    player_id: int
    round_number: int
    total_rounds_used: int
    completed: bool
    identified_top_three: bool

    class Config:
        from_attributes = True


# Leaderboard Schema
class LeaderboardEntry(BaseModel):
    rank: int
    player_id: int
    player_name: str
    total_score: int

    class Config:
        from_attributes = True


# Game Settings Schemas
class GameSettingsUpdate(BaseModel):
    game_name: str
    enabled: bool


class GameSettingsResponse(BaseModel):
    game_name: str
    enabled: bool
    updated_at: datetime

    class Config:
        from_attributes = True
