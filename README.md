# Think Twice - Game Theory Platform

A multiplayer game theory platform built for live classroom events — deployed on **AWS EC2 + RDS PostgreSQL**, with real-time state sync over **WebSockets** proxied through Nginx.

![Think Twice main page](mainpagewelcomescreen.png)

---

## What's technically interesting

### Real-time WebSocket communication
The platform uses persistent WebSocket connections for lobby presence and live game events. In production, WebSocket connections share port 80 with the API — Nginx handles the HTTP→WS upgrade and forwards to FastAPI, so the same reverse proxy and the same port serve everything. The client derives the WS URL from `window.location`, making it work transparently across `localhost`, IP, or domain, and it upgrades to `wss://` automatically when HTTPS is in place:

```js
const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${wsProtocol}//${window.location.host}/api/ws/game/${gameId}`;
```

### AWS infrastructure
- **EC2** runs the full stack: Nginx (reverse proxy + static file server) and FastAPI (managed by systemd — auto-starts on boot, restarts on crash)
- **RDS PostgreSQL** sits in a private subnet — port 5432 is open only to the EC2 security group, never to the public internet
- **Elastic IP** assigned to EC2 for a stable public address
- **Nginx** handles everything on port 80: `/api/*` proxied to FastAPI on `127.0.0.1:8000`, `/` served directly from the `frontend/` source tree as static files — Vite is a local dev tool only

### Games
- **Two-Thirds Average** — tests level-k strategic reasoning (Nash equilibrium: 0, real average: ~20–30)
- **Horse Racing** — information search under constraint (optimal: 7 races for 25 horses)
- **Fish Pond** — tragedy of the commons, real-time per-round state managed server-side

---

## Quick Start (Local Development)

### Prerequisites

- Python 3.11–3.12
- Node.js (for Vite dev server)
- Docker (optional, for local PostgreSQL)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # edit as needed
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Without any `.env` changes the backend runs with SQLite automatically.

### Local PostgreSQL (optional)

```bash
docker-compose up -d
# Then set in backend/.env:
# DATABASE_URL=postgresql://gameuser:gamepass123@localhost:5433/game_theory_db
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

- Frontend: http://localhost:3000
- Backend API: http://127.0.0.1:8000
- API Docs: http://127.0.0.1:8000/docs

---

## Production Deployment (EC2 + RDS)

See **[docs/EC2_DEPLOYMENT.md](docs/EC2_DEPLOYMENT.md)** for the full setup guide.

Architecture:

```
Browser → EC2 / Nginx (port 80)
              ├── /api/*  → FastAPI systemd service (port 8000)
              │                  └── RDS PostgreSQL (port 5432, private)
              └── /       → frontend/ static files
```

---

## How to Use

### For Participants

1. Go to the app URL and enter your name to register
2. Wait for admin to start a game
3. Follow on-screen instructions and submit your move
4. View results and leaderboard

### For Administrators

1. Click **Admin Login** (top-right)
2. Enter your configured username and password
3. Start games, calculate results, and manage players from the admin panel

---

## Games

### 1. Two-Thirds of the Average

**Concept**: Strategic thinking and level-k reasoning

- Each player guesses a number (0–100)
- Winner is closest to 2/3 of the average of all guesses
- Nash equilibrium: everyone guesses 0; real average typically lands around 20–30

**Scoring**: Winner gets 10 points

### 2. Horse Racing

**Concept**: Information gathering and deduction

- 25 horses with hidden speeds
- Each round: select 5 to race
- Goal: identify the top 3 fastest in the minimum number of rounds
- Optimal algorithm: 7 races

**Scoring**: 50 points base, minus 5 per round used (min 10)

### 3. Fish Pond

**Concept**: Tragedy of the commons

- 100 fish in pond initially, 5 rounds
- Each round: catch 0–20 fish; pond regenerates 50%
- If total catch exceeds stock: pond collapses, game ends early

**Scoring**: 1 point per fish caught

---

## Architecture & Data Flow

```mermaid
flowchart TD
  classDef frontend fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0369a1
  classDef backend fill:#d1fae5,stroke:#059669,stroke-width:2px,color:#065f46
  classDef database fill:#f3e8ff,stroke:#7c3aed,stroke-width:2px,color:#5b21b6

  subgraph Frontend ["Frontend (Nginx → frontend/)"]
    UI_Player["Participant Interface"]:::frontend
    UI_Admin["Admin Panel (JWT-protected)"]:::frontend
  end

  subgraph Public_Endpoints ["Public Endpoints"]
    Endpoint_Reg["POST /api/players"]:::frontend
    Endpoint_Submit["POST /api/games/{game}/submit"]:::frontend
    Endpoint_Leaderboard["GET /api/leaderboard"]:::frontend
  end

  subgraph Admin_Endpoints ["Admin Endpoints (JWT)"]
    Endpoint_Login["POST /api/auth/login"]:::frontend
    Endpoint_Start["POST /api/games/{game}/start"]:::frontend
    Endpoint_Calc["POST /api/games/{game}/calculate"]:::frontend
  end

  UI_Player --> Endpoint_Reg & Endpoint_Submit & Endpoint_Leaderboard
  UI_Admin --> Endpoint_Login & Endpoint_Start & Endpoint_Calc

  subgraph Backend ["Backend (FastAPI / systemd)"]
    FastAPI["FastAPI (main.py)"]:::backend
    JWTAuth["JWT Auth (auth.py)"]:::backend
    GameLogic["Game Engines"]:::backend
    ORM["SQLAlchemy ORM"]:::backend
  end

  Endpoint_Reg & Endpoint_Submit & Endpoint_Leaderboard & Endpoint_Start & Endpoint_Calc --> FastAPI
  Endpoint_Login --> JWTAuth
  JWTAuth -.-> FastAPI
  FastAPI <--> GameLogic
  FastAPI --> ORM

  subgraph DB ["RDS PostgreSQL"]
    T1["players"]:::database
    T2["game_sessions"]:::database
    T3["submissions"]:::database
  end

  ORM <--> DB
```

For a detailed request-by-request data path, see **[docs/datapath.md](docs/datapath.md)**.

---

## Project Structure

```
think-twice-V0.3/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── auth.py              # JWT authentication
│   ├── database.py          # SQLAlchemy models
│   ├── schemas.py           # Pydantic validation
│   ├── config.py            # Centralised config
│   ├── routers/             # Route handlers per game
│   ├── .env.example         # Local env template
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── shared.js            # Shared API client & state
│   ├── script.js            # Home page logic
│   ├── two-thirds-game.html
│   ├── horse-race-game.html
│   ├── fish-pond-game.html
│   └── style.css
├── nginx/
│   └── think-twice.conf     # Nginx config (versioned)
└── docs/
    ├── EC2_DEPLOYMENT.md    # Full EC2 + RDS setup guide
    ├── DEPLOYMENT_CHECKLIST.md
    └── datapath.md          # End-to-end data flow
```

---

## API Endpoints

### Public

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/players` | Register player |
| `GET` | `/api/players` | List all players |
| `GET` | `/api/leaderboard` | Get rankings |
| `POST` | `/api/games/{game}/submit` | Submit game move |

### Admin (JWT required)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/login` | Admin login |
| `POST` | `/api/games/two-thirds/start` | Start Two-Thirds game |
| `POST` | `/api/games/two-thirds/{id}/calculate` | Calculate results |
| `POST` | `/api/games/fish-pond/start` | Start Fish Pond game |
| `POST` | `/api/games/fish-pond/{id}/calculate-round` | Calculate round |
| `DELETE` | `/api/players/{id}` | Delete player |

Full interactive docs: `http://<host>/api/docs`

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| 502 Bad Gateway | `sudo systemctl status think-twice-backend` |
| Backend errors | `sudo journalctl -u think-twice-backend -f` |
| DB connection failed | `DATABASE_URL` in `.env`, RDS security group |
| CORS error | `CORS_ORIGINS` in `.env` matches origin exactly |
| Admin login fails | `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `SECRET_KEY` in `.env` |

---

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, PostgreSQL (psycopg2)
- **Frontend**: Vanilla JavaScript, HTML, CSS (Vite for local dev)
- **Infrastructure**: AWS EC2, AWS RDS PostgreSQL, Nginx, systemd
- **Auth**: JWT (python-jose, passlib/bcrypt)

---

## License

MIT — free for educational and research use.

---

**Contact**: urgundeshantanu@gmail.com
