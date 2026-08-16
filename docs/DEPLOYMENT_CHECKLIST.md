# Pre-Deployment Checklist

## ✅ Before You Deploy

### 1. Code Review

- [ ] All files are in the correct directories
- [ ] No sensitive data in code (passwords, keys, etc.)
- [ ] API_URL configuration is correct in script.js
- [ ] All admin functions are implemented

### 2. Configuration Files

- [ ] `backend/.env.example` is present and reflects the required env vars (don't commit actual `.env`)
- [ ] `Procfile` is in backend directory
- [ ] `railway.json` is in backend directory
- [ ] `.gitignore` includes `.env` at the repo root

### 3. Security

- [ ] Admin password will be changed from default
- [ ] SECRET_KEY will be generated (use: `openssl rand -hex 32`)
- [ ] CORS_ORIGINS will be set to actual frontend URL
- [ ] No hardcoded credentials in code

---

## 📋 Deployment Steps

### Phase 1: Prepare Repository

1. [ ] Create GitHub repository
2. [ ] Add all files to repository:
   ```bash
   git init
   git add .
   git commit -m "Initial commit - v2.0 production ready"
   git remote add origin https://github.com/yourusername/game-theory-platform.git
   git push -u origin main
   ```

### Phase 2: Deploy Backend to Railway

1. [ ] Sign up at railway.app
2. [ ] Create new project from GitHub repo
3. [ ] Add PostgreSQL database service
4. [ ] Set backend root directory to `backend`
5. [ ] Configure environment variables:
   ```
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD=[SECURE_PASSWORD_HERE]
   SECRET_KEY=[32_CHAR_RANDOM_STRING]
   FRONTEND_URL=[WILL_SET_AFTER_FRONTEND_DEPLOY]
   CORS_ORIGINS=[WILL_SET_AFTER_FRONTEND_DEPLOY]
   MAX_PLAYERS=40
   ```
6. [ ] Wait for deployment (2-3 minutes)
7. [ ] Generate domain for backend
8. [ ] Test backend: Visit `https://your-backend.railway.app`
9. [ ] Check health: `https://your-backend.railway.app/health`
10. [ ] View API docs: `https://your-backend.railway.app/docs`

### Phase 3: Deploy Frontend to Vercel

1. [ ] Sign up at vercel.com
2. [ ] Import GitHub repository
3. [ ] Set framework: Other
4. [ ] Set root directory to `frontend`
5. [ ] Deploy
6. [ ] Note your Vercel URL: `https://your-project.vercel.app`

### Phase 4: Update Configuration

1. [ ] Update `script.js` line ~5:
   ```javascript
   const API_URL = "https://your-backend.railway.app/api";
   ```
2. [ ] Commit and push changes
3. [ ] Vercel will auto-redeploy
4. [ ] Update Railway environment variables:
   ```
   FRONTEND_URL=https://your-project.vercel.app
   CORS_ORIGINS=https://your-project.vercel.app,https://your-backend.railway.app
   ```
5. [ ] Railway will auto-redeploy

### Phase 5: Test Everything

1. [ ] Visit frontend URL
2. [ ] Register a test player
3. [ ] Check leaderboard appears
4. [ ] Test admin login (top-right corner)
5. [ ] Start Two-Thirds game as admin
6. [ ] Submit a guess as player
7. [ ] Calculate results as admin
8. [ ] Verify scores update
9. [ ] Test Horse Race game
10. [ ] Test Fish Pond game

---

## 🔍 Testing Checklist

### Player Registration

- [ ] Can register new player
- [ ] Can select existing player
- [ ] Player limit (40) is enforced
- [ ] Duplicate names are prevented

### Admin Authentication

- [ ] Admin login button visible
- [ ] Can login with correct credentials
- [ ] Login fails with wrong credentials
- [ ] Admin panel appears after login
- [ ] Admin action buttons show/hide correctly
- [ ] Can logout
- [ ] Token persists across page refreshes

### Two-Thirds Game

- [ ] Admin can start game
- [ ] Players can submit guesses
- [ ] Can't submit twice
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

- [ ] Admin can start game with all players
- [ ] Current stock displays correctly
- [ ] Each player can submit catch (0-20)
- [ ] Can't submit twice per round
- [ ] Pending players list updates
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
- [ ] Shows player names and scores

---

## 🐛 Common Issues to Check

### Issue: "CORS Error"

**Check:**

- [ ] CORS_ORIGINS includes your frontend URL
- [ ] No trailing slashes in URLs
- [ ] Both HTTP and HTTPS match

### Issue: "Database Connection Failed"

**Check:**

- [ ] PostgreSQL service is running in Railway
- [ ] DATABASE_URL is automatically set
- [ ] Backend logs show connection attempts

### Issue: "Admin Login Fails"

**Check:**

- [ ] ADMIN_USERNAME is set correctly
- [ ] ADMIN_PASSWORD is set correctly
- [ ] SECRET_KEY is set
- [ ] Browser console for errors

### Issue: "502 Bad Gateway"

**Check:**

- [ ] Wait 30 seconds (backend starting)
- [ ] Check Railway logs
- [ ] PORT environment variable is used

---

## 📊 Performance Checks

### Backend Performance

- [ ] API responds in < 500ms
- [ ] Database queries are fast
- [ ] No memory leaks in Railway metrics
- [ ] Logs show no errors

### Frontend Performance

- [ ] Page loads in < 3 seconds
- [ ] No console errors
- [ ] API calls complete successfully
- [ ] UI is responsive

---

## 🔒 Security Checklist

- [ ] Admin password is NOT the default
- [ ] SECRET_KEY is random and secure (32+ chars)
- [ ] CORS is restricted to specific origins
- [ ] No API keys or secrets in frontend code
- [ ] HTTPS is enabled (automatic on Railway/Vercel)
- [ ] Database credentials are managed by Railway
- [ ] JWT tokens expire (8 hours default)

---

## 📝 Documentation Checklist

- [ ] README.md is updated
- [ ] RAILWAY_DEPLOYMENT.md exists
- [ ] DEPLOYMENT_SUMMARY.md exists
- [ ] Environment variables are documented
- [ ] API endpoints are documented
- [ ] Game rules are explained

---

## 🎯 Launch Day Checklist

### Before Event (1 Day Prior)

- [ ] All tests passing
- [ ] Admin credentials shared with organizers only
- [ ] Frontend URL shared with participants
- [ ] Database is empty (fresh start)
- [ ] Backup plan in place

### Event Start (30 Minutes Prior)

- [ ] Services are running
- [ ] Admin is logged in
- [ ] Test with 2-3 people
- [ ] Monitor Railway logs
- [ ] Have this checklist handy

### During Event

- [ ] Monitor player registrations
- [ ] Start games when ready
- [ ] Calculate results promptly
- [ ] Watch for errors in Railway logs
- [ ] Keep admin panel open

### After Event

- [ ] Export database (Railway → PostgreSQL → Connect)
- [ ] Save final leaderboard screenshot
- [ ] Thank participants
- [ ] Review logs for issues
- [ ] Document any problems

---

## 🆘 Emergency Contacts

**Railway Status**: https://railway.app/status
**Vercel Status**: https://www.vercel-status.com

**Quick Fixes**:

- Restart Railway service: Go to service → Settings → Restart
- Rollback deployment: Go to Deployments → Click previous → Redeploy
- Check logs: Click on service → View Logs
- Clear cache: Hard refresh browser (Ctrl+Shift+R)

---

## ✅ Final Checklist

Before saying "We're ready":

- [ ] Backend deployed and accessible
- [ ] Frontend deployed and accessible
- [ ] Admin login works
- [ ] All three games tested end-to-end
- [ ] Leaderboard updates correctly
- [ ] Environment variables are set
- [ ] No errors in logs
- [ ] Performance is acceptable
- [ ] Security checklist completed
- [ ] Backup plan ready

---

## 🎉 You're Ready!

When all boxes are checked, you're ready to run your game theory event!

**Pro Tips**:

- Have 2-3 admins logged in (different browsers/devices)
- Keep Railway logs open in a tab
- Test with friends before the actual event
- Have this checklist printed/open during event
- Don't panic - you can always restart services if needed

**Good luck with your event!** 🎮
