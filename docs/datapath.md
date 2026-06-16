# Think Twice - End-to-End Data Path

This document outlines the end-to-end data flow and lifecycle of game sessions, participant actions, database persistence, and administrative controls within the **Think Twice** platform.

---

## 1. End-to-End Sequence Diagram

The following sequence diagram illustrates the lifecycle of a player registration, admin login, starting a game, submitting moves, calculating results, and refreshing the leaderboard.

```mermaid
sequenceDiagram
    autonumber
    actor Player as Player (UI)
    actor Admin as Admin (UI)
    participant FastAPI as FastAPI Backend
    participant Auth as JWT Auth (auth.py)
    participant DB as PostgreSQL Database
    participant Engine as Game Engines

    Note over Player, DB: 1. Player Registration
    Player->>FastAPI: POST /api/players {name}
    FastAPI->>DB: Check if name exists & insert player record
    DB-->>FastAPI: Return Player ID & Name
    FastAPI-->>Player: 200 OK (Player ID)

    Note over Admin, Auth: 2. Admin Authentication
    Admin->>FastAPI: POST /api/auth/login {username, password}
    FastAPI->>Auth: Verify credentials (env match)
    Auth-->>FastAPI: Generate & return JWT Access Token
    FastAPI-->>Admin: 200 OK (JWT Token)

    Note over Admin, DB: 3. Admin Initializes Game
    Admin->>FastAPI: POST /api/games/{game}/start (Header: JWT)
    FastAPI->>Auth: Verify JWT Token
    Auth-->>FastAPI: Token Valid
    FastAPI->>DB: Update game_sessions table (status=ACTIVE, round=1)
    DB-->>FastAPI: Update confirmed
    FastAPI-->>Admin: 200 OK (Game started)

    Note over Player, DB: 4. Move Submission
    Player->>FastAPI: POST /api/games/{game}/submit {player_id, move_data}
    FastAPI->>DB: Check if player exists & game session is active
    FastAPI->>DB: Insert record into submissions table
    DB-->>FastAPI: Insert confirmed
    FastAPI-->>Player: 200 OK (Submission saved)

    Note over Admin, Engine: 5. Results Calculation
    Admin->>FastAPI: POST /api/games/{game}/calculate (Header: JWT)
    FastAPI->>Auth: Verify JWT Token
    Auth-->>FastAPI: Token Valid
    FastAPI->>DB: Query all submissions for the active session
    DB-->>FastAPI: Return submissions list
    FastAPI->>Engine: Run game rules (e.g., Two-Thirds, Fish Pond)
    Engine-->>FastAPI: Return calculated scores & state updates
    FastAPI->>DB: Update players table (add points) & submissions table (round scores)
    FastAPI->>DB: Update game_sessions table (status=COMPLETED or advance round)
    DB-->>FastAPI: Persistence complete
    FastAPI-->>Admin: 200 OK (Results computed)

    Note over Player, DB: 6. Real-Time Leaderboard Refresh
    Player->>FastAPI: GET /api/leaderboard
    FastAPI->>DB: Query players order by total_score DESC
    DB-->>FastAPI: Return sorted rankings
    FastAPI-->>Player: 200 OK (Leaderboard Data)
```

---

## 2. Key Data Path Breakdown

### A. Participant Registration
*   **Path**: `POST /api/players`
*   **Payload**: `{"name": "Alice"}`
*   **Action**: Inserts a new row in the `players` table with `total_score = 0`. Returns the unique player ID to store in local storage on the client.

### B. Game Action Submission
*   **Path**: `POST /api/games/{game}/submit`
*   **Payload**: Contains the `player_id`, the active `session_id`, the `round_number`, and the game-specific action (e.g., a guess number from `0-100` for Two-Thirds, or fish count to catch `0-20` for Fish Pond).
*   **Action**: Validates the submission using Pydantic schemas and saves it in the database to prevent duplicate play.

### C. Admin Control & Calculations
*   **Path**: `POST /api/games/{game}/calculate`
*   **Authorization**: Bearer JWT Token
*   **Action**: The server fetches all submitted moves for the active round. It calls the corresponding game logic:
    *   **Two-Thirds Average Engine**: Calculates the average of all guesses, multiplies by `2/3`, finds the closest guess, and awards 10 points to the winner(s).
    *   **Fish Pond Engine**: Aggregates the total fish caught. Evaluates if the pond collapsed (>100 fish caught). If sustained, calculates remaining fish and regenerates the pond by 50% for the next round.
*   **Persistence**: Atomically updates the players' scores and marks submissions as calculated.
