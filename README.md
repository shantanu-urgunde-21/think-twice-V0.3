# Think Twice - Game Theory Platform v2.0

A production-ready web platform for conducting game theory experiments with up to 40 participants.

## ✨ What's New in v2.0

### Production Ready
- ✅ **Railway Deployment**: One-click deployment to Railway
- ✅ **Admin Authentication**: JWT-based admin panel with secure login
- ✅ **PostgreSQL**: Production database with proper connection pooling
- ✅ **Better UX**: Leaderboard only on home page, cleaner game views
- ✅ **Error Handling**: Comprehensive error handling and validation
- ✅ **Security**: CORS configuration, environment variables, secure credentials

### Features
- **3 Games**: Two-Thirds Average, Horse Racing, Fish Pond
- **40 Players**: Support for up to 40 concurrent players
- **Admin Panel**: Protected game management and player administration
- **Leaderboard**: Real-time global scoring system
- **Responsive**: Works on desktop and mobile

---

## 🚀 Quick Deploy (5 Minutes)

### 1. Deploy Backend to Railway
```bash
1. Go to railway.app and sign up with GitHub
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Railway auto-detects Python and deploys
5. Add PostgreSQL: Click "New" → "Database" → "PostgreSQL"
```

### 2. Configure Environment Variables
In Railway, set these variables:
```
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password
SECRET_KEY=your_32_char_random_string
FRONTEND_URL=https://your-frontend-url.com
```

### 3. Deploy Frontend to Vercel
```bash
1. Go to vercel.com and sign up with GitHub
2. Import your repository
3. Set root directory to: frontend
4. Deploy
```

### 4. Update Configuration
Update `script.js` with your Railway backend URL:
```javascript
const API_URL = 'https://your-backend.railway.app/api';
```

**📖 Full deployment guide**: See [RAILWAY_DEPLOYMENT.md](docs/RAILWAY_DEPLOYMENT.md)

---

## 🎮 How to Use

### For Participants

1. **Register**
   - Go to the frontend URL
   - Enter your name to register
   - Or select existing player

2. **Play Games**
   - Admin will start games
   - Follow on-screen instructions
   - Submit your moves
   - View results and leaderboard

### For Administrators

1. **Login**
   - Click "Admin Login" button
   - Username: `admin` (or your configured username)
   - Password: Your configured password

2. **Manage Games**
   - Start Two-Thirds game
   - Start Fish Pond game
   - Calculate results when ready

3. **Monitor**
   - View all players
   - See who hasn't submitted
   - Control game flow

---

## 🎯 Games Explained

### 1. Two-Thirds of the Average
**Concept**: Strategic thinking and level-k reasoning

**Rules**:
- Each player guesses a number (0-100)
- Winner is closest to 2/3 of the average
- Tests ability to predict others' reasoning

**Scoring**: Winner gets 10 points

**Admin Actions**:
- Start game
- Calculate results when all submitted

---

### 2. Horse Racing
**Concept**: Information gathering and deduction

**Rules**:
- 25 horses with hidden speeds
- Each round: select 5 horses to race
- Goal: Identify top 3 fastest in minimum rounds
- Individual player challenge

**Scoring**: 
- Base 50 points
- Minus 5 points per round used
- Minimum 10 points

**Strategy**: Efficient testing and elimination

---

### 3. Fish Pond
**Concept**: Tragedy of the commons

**Rules**:
- 100 fish in pond initially
- 5 rounds total
- Each round: catch 0-20 fish
- Pond regenerates 50% per round
- If overfished: pond collapses, game ends

**Scoring**: 1 point per fish caught

**Dilemma**: Individual gain vs. collective sustainability

**Admin Actions**:
- Start game with all registered players
- Calculate each round's results

---

## 📁 Project Structure

```
game-theory-v2/
├── backend/
│   ├── main.py              # FastAPI app with all endpoints
│   ├── auth.py              # JWT authentication
│   ├── database.py          # SQLAlchemy models
│   ├── schemas.py           # Pydantic validation
│   ├── config.py            # Configuration
│   ├── requirements.txt     # Python dependencies
│   ├── Procfile             # Railway config
│   └── .env.example         # Environment template
├── frontend/
│   ├── index.html           # Main HTML
│   ├── script.js            # Frontend logic
│   └── style.css            # Styling
└── docs/
    └── RAILWAY_DEPLOYMENT.md  # Full deployment guide
```

---

## 🔧 Local Development

### Prerequisites
- Python 3.11+
- Docker (for PostgreSQL)

### Setup

1. **Clone and Setup Backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

2. **Start PostgreSQL**
```bash
docker run --name game-db -e POSTGRES_PASSWORD=gamepass123 \
  -e POSTGRES_USER=gameuser -e POSTGRES_DB=game_theory_db \
  -p 5432:5432 -d postgres:15-alpine
```

3. **Run Backend**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

4. **Open Frontend**
```bash
cd frontend
python -m http.server 3000
```

5. **Access**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 🔐 Security

### Default Credentials (CHANGE THESE!)
- Admin Username: `admin`
- Admin Password: `changeme123`

### Production Checklist
- ✅ Change admin password
- ✅ Set strong SECRET_KEY (32+ random chars)
- ✅ Configure CORS_ORIGINS properly
- ✅ Use HTTPS (automatic on Railway/Vercel)
- ✅ Regular database backups

---

## 📊 API Endpoints

### Public Endpoints
- `POST /api/players` - Register player
- `GET /api/players` - List all players
- `GET /api/leaderboard` - Get rankings
- `POST /api/games/{game}/submit` - Submit game move

### Admin Endpoints (Require Authentication)
- `POST /api/auth/login` - Admin login
- `POST /api/games/two-thirds/start` - Start Two-Thirds game
- `POST /api/games/two-thirds/{id}/calculate` - Calculate results
- `POST /api/games/fish-pond/start` - Start Fish Pond game
- `POST /api/games/fish-pond/{id}/calculate-round` - Calculate round
- `DELETE /api/players/{id}` - Delete player

**Full API Documentation**: Visit `/docs` on your backend URL

---

## 🐛 Troubleshooting

### "Database connection failed"
- Check PostgreSQL is running
- Verify DATABASE_URL in environment variables

### "CORS error"
- Update CORS_ORIGINS to include your frontend URL
- No trailing slashes in URLs

### "Admin login failed"
- Check ADMIN_USERNAME and ADMIN_PASSWORD
- Verify SECRET_KEY is set
- Check browser console for errors

### "502 Bad Gateway"
- Backend is starting (wait 30 seconds)
- Check Railway logs
- Verify environment variables

**More help**: See [RAILWAY_DEPLOYMENT.md](docs/RAILWAY_DEPLOYMENT.md)

---

## 📈 Monitoring

### Railway Dashboard
- View deployment logs
- Monitor resource usage
- Check database connections
- Restart services if needed

### Database Backup
1. Go to Railway PostgreSQL service
2. Click "Connect"
3. Use pg_dump to export data

---

## 🎓 Game Theory Concepts

### Two-Thirds Game
- Tests level-k reasoning
- Nash equilibrium: everyone guesses 0
- Real behavior: average often around 20-30

### Horse Racing
- Information search strategies
- Optimal algorithm: 7 races minimum
- Tests systematic elimination

### Fish Pond
- Tragedy of the commons
- Shows tension between individual and collective good
- Real-world applications: fishing, forestry, climate

---

## 📝 License

MIT License - Free for educational and research use

---

## 🙏 Credits

Built for conducting game theory experiments in educational settings.

**Technology Stack**:
- Backend: FastAPI, SQLAlchemy, PostgreSQL
- Frontend: Vanilla JavaScript, HTML, CSS
- Deployment: Railway, Vercel
- Authentication: JWT (python-jose)

---

## 📞 Support

- **Deployment Issues**: Check [RAILWAY_DEPLOYMENT.md](docs/RAILWAY_DEPLOYMENT.md)
- **API Questions**: Visit `/docs` endpoint
- **Game Rules**: See game descriptions above

---

**Ready to deploy? Follow [RAILWAY_DEPLOYMENT.md](docs/RAILWAY_DEPLOYMENT.md)**
