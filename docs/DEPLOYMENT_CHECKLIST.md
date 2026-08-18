# Deployment Checklist

## Before Deploying

- [ ] No sensitive data committed (passwords, keys, `.env`)
- [ ] `backend/.env.example` reflects all required env vars
- [ ] `.gitignore` includes `.env`
- [ ] Admin password is not the default
- [ ] `SECRET_KEY` is a random 32+ char string (`openssl rand -hex 32`)
- [ ] `CORS_ORIGINS` is set to the actual frontend URL (EC2 IP or domain)

---

## EC2 Deploy / Update

```bash
git pull

# If nginx config changed
sudo cp ~/think-twice-V0.3/nginx/think-twice.conf /etc/nginx/sites-available/think-twice
sudo nginx -t && sudo systemctl reload nginx

# If backend code or dependencies changed
pip install -r backend/requirements.txt
sudo systemctl restart think-twice-backend
```

See `docs/EC2_DEPLOYMENT.md` for the full setup guide.

---

## Testing Checklist

### Player Registration
- [ ] Can register a new player
- [ ] Can select an existing player
- [ ] Duplicate names are prevented
- [ ] Player limit (40) is enforced

### Admin Authentication
- [ ] Admin login button visible
- [ ] Login succeeds with correct credentials
- [ ] Login fails with wrong credentials
- [ ] Admin panel appears after login
- [ ] Admin action buttons show/hide correctly
- [ ] Can logout
- [ ] Token persists across page refreshes

### Two-Thirds Game
- [ ] Admin can start game
- [ ] Players can submit guesses
- [ ] Cannot submit twice
- [ ] Submission count updates
- [ ] Admin can calculate results
- [ ] Winner is determined correctly
- [ ] Scores update in database
- [ ] Leaderboard reflects new scores

### Horse Race Game
- [ ] Player can start game
- [ ] Can select 5 horses
- [ ] Race button enables/disables correctly
- [ ] Race results show speeds
- [ ] Round counter increments
- [ ] Can submit top 3 guess
- [ ] Scoring works (fewer rounds = more points)
- [ ] Results show correct/incorrect

### Fish Pond Game
- [ ] Admin can start game
- [ ] Current stock displays correctly
- [ ] Each player can submit catch (0–20)
- [ ] Cannot submit twice per round
- [ ] Admin can calculate round
- [ ] Stock regenerates correctly
- [ ] Game ends if stock collapses
- [ ] Game ends after 5 rounds
- [ ] Final results show all player scores

### Leaderboard
- [ ] Shows on home page only
- [ ] Not visible during games
- [ ] Updates after game results
- [ ] Rankings are correct

---

## Common Issues

### 502 Bad Gateway
- Backend service is down — check: `sudo systemctl status think-twice-backend`
- View logs: `sudo journalctl -u think-twice-backend -f`

### 404 on API routes
- Nginx may have a trailing slash on `proxy_pass` — should be `http://127.0.0.1:8000` with no trailing slash
- Confirm FastAPI is running: `curl http://127.0.0.1:8000/api/players`

### CORS error
- `CORS_ORIGINS` in `.env` must include the exact origin the browser is using (no trailing slash)
- Restart backend after `.env` changes

### Database connection failed
- Check `DATABASE_URL` in `backend/.env`
- Check RDS security group allows inbound from EC2 on port 5432
- Check logs: `sudo journalctl -u think-twice-backend -f`

### Admin login fails
- Verify `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `SECRET_KEY` are set in `.env`
- Restart backend after any `.env` change

---

## Event Day

### 30 Minutes Before
- [ ] Services running (`systemctl status think-twice-backend nginx`)
- [ ] Admin login confirmed working
- [ ] Test with 2–3 people
- [ ] Live logs open: `sudo journalctl -u think-twice-backend -f`

### During Event
- [ ] Monitor player registrations
- [ ] Start games when ready
- [ ] Calculate results promptly
- [ ] Watch backend logs for errors

### After Event
- [ ] Save final leaderboard screenshot
- [ ] Back up database if needed
- [ ] Review logs for issues
