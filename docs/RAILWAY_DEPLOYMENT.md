# Railway Deployment Guide

## Step-by-Step Deployment to Railway

### Prerequisites
- GitHub account
- Railway account (sign up at railway.app)
- Your project code pushed to GitHub

---

## Part 1: Deploy Backend to Railway

### 1. Create Railway Account
1. Go to [railway.app](https://railway.app)
2. Click "Sign up" and authenticate with GitHub
3. You'll be redirected to your Railway dashboard

### 2. Create New Project
1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Authorize Railway to access your GitHub repositories
4. Select your repository: `game-theory-platform`
5. Railway will automatically detect it's a Python project

### 3. Add PostgreSQL Database
1. In your project dashboard, click "New"
2. Select "Database" → "Add PostgreSQL"
3. Railway will automatically provision a PostgreSQL database
4. The `DATABASE_URL` environment variable will be automatically set

### 4. Configure Backend Service

#### Set Environment Variables:
1. Click on your backend service
2. Go to "Variables" tab
3. Add the following variables:

```
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password-here
SECRET_KEY=your-super-secret-random-key-change-this
FRONTEND_URL=https://your-frontend-url.com
CORS_ORIGINS=https://your-frontend-url.com,https://your-backend-url.railway.app
MAX_PLAYERS=40
```

**Important**: 
- `DATABASE_URL` is automatically set by Railway
- Change `ADMIN_PASSWORD` and `SECRET_KEY` to secure values
- `FRONTEND_URL` will be set after deploying frontend (Step 5)

#### Set Root Directory:
1. Go to "Settings" tab
2. Find "Root Directory"
3. Set it to: `backend`
4. Click "Save"

#### Configure Start Command:
1. In "Settings" tab
2. Find "Custom Start Command"
3. Set it to: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Click "Save"

### 5. Deploy Backend
1. Railway will automatically deploy after configuration
2. Wait for deployment to complete (usually 2-3 minutes)
3. Click "View Logs" to monitor the deployment
4. Once deployed, click "Generate Domain" to get your backend URL
5. Your backend will be at: `https://your-project-name.up.railway.app`

### 6. Test Backend
1. Visit your backend URL
2. You should see: `{"message": "Game Theory Platform API", "version": "2.0.0"}`
3. Visit `/docs` to see the API documentation
4. Test the health endpoint: `https://your-backend-url.railway.app/health`

---

## Part 2: Deploy Frontend

You have several options for frontend deployment. Here are the best ones:

### Option A: Vercel (Recommended - Easiest)

#### 1. Prepare Frontend for Deployment
1. Update the API URL in your frontend code
2. Create a `vercel.json` in the frontend directory:

```json
{
  "version": 2,
  "routes": [
    {
      "src": "/(.*)",
      "dest": "/$1"
    }
  ]
}
```

#### 2. Deploy to Vercel
1. Go to [vercel.com](https://vercel.com)
2. Sign up with GitHub
3. Click "New Project"
4. Import your repository
5. Configure:
   - Framework Preset: Other
   - Root Directory: `frontend`
   - Build Command: (leave empty)
   - Output Directory: `./`
6. Add Environment Variable:
   ```
   VITE_API_URL=https://your-backend-url.railway.app
   ```
7. Click "Deploy"

#### 3. Update Frontend API URL
1. Get your Vercel URL (e.g., `https://your-project.vercel.app`)
2. Update `script.js` to use your Railway backend URL:

```javascript
const API_URL = 'https://your-backend-url.railway.app/api';
```

#### 4. Update Backend CORS
1. Go back to Railway
2. Update the `FRONTEND_URL` environment variable with your Vercel URL
3. Update `CORS_ORIGINS` to include your Vercel URL
4. Railway will automatically redeploy

---

### Option B: Netlify

#### 1. Prepare Frontend
Create a `netlify.toml` in the frontend directory:

```toml
[build]
  publish = "."
  command = "echo 'No build needed'"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

#### 2. Deploy to Netlify
1. Go to [netlify.com](https://netlify.com)
2. Sign up with GitHub
3. Click "New site from Git"
4. Choose your repository
5. Configure:
   - Base directory: `frontend`
   - Build command: (leave empty)
   - Publish directory: `frontend`
6. Click "Deploy site"

#### 3. Update Configuration
- Same as Vercel (update API URL and backend CORS)

---

### Option C: GitHub Pages

#### 1. Enable GitHub Pages
1. Go to your GitHub repository
2. Click "Settings" → "Pages"
3. Source: Deploy from a branch
4. Branch: `main`, Folder: `/frontend`
5. Click "Save"

#### 2. Update API URL
Update the `API_URL` in your `script.js` to point to Railway backend

#### 3. Access Your Site
Your site will be at: `https://username.github.io/repository-name/`

---

## Part 3: Update Backend with Frontend URL

Once your frontend is deployed:

1. Go to Railway dashboard
2. Click on your backend service
3. Go to "Variables"
4. Update these variables:
   ```
   FRONTEND_URL=https://your-actual-frontend-url.com
   CORS_ORIGINS=https://your-actual-frontend-url.com,https://your-backend-url.railway.app
   ```
5. Railway will automatically redeploy

---

## Part 4: Initialize Database

### Create Tables
1. The database tables are created automatically when the backend starts
2. Check the logs in Railway to confirm: "Database initialized successfully"

### If you need to manually initialize:
1. Go to Railway dashboard
2. Click on your PostgreSQL service
3. Click "Connect" → "psql"
4. Run SQL commands if needed (usually not necessary)

---

## Part 5: Test the Complete Setup

### 1. Test Backend
```bash
curl https://your-backend-url.railway.app/health
# Should return: {"status":"healthy"}

curl https://your-backend-url.railway.app/api/stats
# Should return: {"total_players":0,"max_players":40,"active_games":0}
```

### 2. Test Frontend
1. Visit your frontend URL
2. Register a player
3. Verify leaderboard updates
4. Test admin login (username: admin, password: what you set)

### 3. Test Full Flow
1. Register 2-3 players
2. Admin: Start a Two-Thirds game
3. Players: Submit guesses
4. Admin: Calculate results
5. Verify scores update

---

## Common Issues and Solutions

### Issue 1: "Database connection failed"
**Solution**: 
- Check if PostgreSQL service is running in Railway
- Verify `DATABASE_URL` is set correctly
- Check backend logs for detailed error

### Issue 2: "CORS error" in browser console
**Solution**:
- Update `CORS_ORIGINS` in Railway to include your frontend URL
- Make sure no trailing slashes in URLs
- Clear browser cache

### Issue 3: "502 Bad Gateway"
**Solution**:
- Backend might be starting up (wait 30 seconds)
- Check backend logs in Railway
- Verify `PORT` environment variable is being used

### Issue 4: Admin login not working
**Solution**:
- Check `ADMIN_USERNAME` and `ADMIN_PASSWORD` in Railway variables
- Verify `SECRET_KEY` is set
- Check browser console for errors

### Issue 5: Players can't submit
**Solution**:
- Check if game is started (admin must start game first)
- Verify player is registered
- Check network tab in browser for API errors

---

## Environment Variables Reference

### Backend (Railway)

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection (auto-set) | `postgresql://...` |
| `ADMIN_USERNAME` | Admin login username | `admin` |
| `ADMIN_PASSWORD` | Admin login password | `secure_pass_123` |
| `SECRET_KEY` | JWT secret key | Random 32+ chars |
| `FRONTEND_URL` | Your frontend URL | `https://app.vercel.app` |
| `CORS_ORIGINS` | Allowed origins (comma-separated) | `https://app.vercel.app` |
| `MAX_PLAYERS` | Maximum players allowed | `40` |

---

## Monitoring and Maintenance

### View Logs
1. Go to Railway dashboard
2. Click on your service
3. Click "View Logs"
4. Filter by "Deploy" or "Application"

### Database Management
1. Click on PostgreSQL service
2. Click "Connect"
3. Use provided connection string with any PostgreSQL client

### Restart Service
1. Go to service settings
2. Click "Restart"

### Rollback Deployment
1. Go to "Deployments" tab
2. Find previous successful deployment
3. Click "Redeploy"

---

## Cost Estimation

### Railway Free Tier
- $5 free credit per month
- ~500 hours of runtime
- Sufficient for small events (up to 40 players)

### Expected Usage
- Backend: ~$3-5/month with light usage
- PostgreSQL: Included in free tier initially
- Total: Free tier should cover testing and small events

### Upgrade if needed
- Hobby Plan: $5/month per service
- Recommended for production events

---

## Security Checklist

✅ Changed default admin password
✅ Set a strong SECRET_KEY (32+ random characters)
✅ CORS_ORIGINS is restricted to your frontend URL only
✅ HTTPS is enabled (automatic on Railway/Vercel)
✅ Database credentials are secure (auto-managed by Railway)

---

## Next Steps

1. ✅ Deploy backend to Railway
2. ✅ Deploy frontend to Vercel/Netlify/GitHub Pages
3. ✅ Update CORS settings
4. ✅ Test complete flow
5. ✅ Share URL with participants
6. ✅ Monitor during event
7. ✅ Backup database after event (export from Railway)

---

## Support

If you encounter issues:
1. Check Railway logs
2. Check browser console
3. Test API endpoints directly
4. Verify all environment variables
5. Check this guide's troubleshooting section

**Railway Support**: https://railway.app/help
**Vercel Support**: https://vercel.com/support
