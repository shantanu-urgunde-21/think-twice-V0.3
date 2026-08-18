# EC2 + RDS Deployment Guide

This document covers the production deployment of Think Twice on AWS EC2 with an RDS PostgreSQL database.

---

## Architecture

```
Public Internet
      |
      v
EC2 / Nginx  (port 80)
      |
      |--- /api/*  --->  FastAPI (127.0.0.1:8000, systemd-managed)
      |                        |
      |                        v
      |                  RDS PostgreSQL (port 5432, private)
      |
      \--- /       --->  frontend/ (static files served directly)
```

---

## 1. Repository Layout (EC2-relevant files)

```
think-twice-V0.3/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   └── .env                  ← not in git, placed manually on server
├── frontend/
│   ├── index.html
│   ├── shared.js
│   ├── script.js
│   ├── style.css
│   └── *.html
└── nginx/
    └── think-twice.conf      ← source of truth for nginx config
```

---

## 2. RDS PostgreSQL

- Engine: **PostgreSQL** (standard RDS, not Aurora)
- The EC2 security group must allow outbound to the RDS security group on port `5432`
- The RDS security group must allow inbound from the EC2 security group on port `5432`
- Port `5432` should **not** be exposed to `0.0.0.0/0`

### Connection string format

```
postgresql://postgres:<password>@<rds-endpoint>:5432/postgres
```

Set this as `DATABASE_URL` in `backend/.env`.

---

## 3. Backend — FastAPI / systemd

The FastAPI backend runs as a systemd service so it starts automatically on boot and restarts on failure.

### Useful commands

```bash
# Status
sudo systemctl status think-twice-backend

# Restart
sudo systemctl restart think-twice-backend

# Live logs
sudo journalctl -u think-twice-backend -f
```

> The `--reload` flag must **not** be used in the production service definition.

### Setting up the .env

The `.env` file is not committed to git. Copy it from your local machine to the server:

```bash
scp -i your-key.pem backend/.env ubuntu@<EC2_IP>:~/think-twice-V0.3/backend/.env
```

Or create it directly on the server:

```bash
nano ~/think-twice-V0.3/backend/.env
```

Minimum required variables:

```env
DATABASE_URL=postgresql://postgres:<password>@<rds-endpoint>:5432/postgres
SECRET_KEY=<random-32-char-string>
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<your-password>
FRONTEND_URL=http://<EC2_IP>
```

### Installing dependencies

```bash
cd ~/think-twice-V0.3/backend
pip install -r requirements.txt
```

---

## 4. Frontend — Static Files via Nginx

This is a vanilla HTML/JS/CSS application. No build step is required for production. Nginx serves the `frontend/` source directory directly.

> Do **not** run the Vite development server in production. `npm run dev` / port 3000 is for local development only.

---

## 5. Nginx Configuration

The config lives in the repo at `nginx/think-twice.conf`. After any changes, copy it to the system location and reload:

```bash
sudo cp ~/think-twice-V0.3/nginx/think-twice.conf /etc/nginx/sites-available/think-twice
sudo nginx -t && sudo systemctl reload nginx
```

### Current configuration

```nginx
server {
    listen 80;
    server_name _;

    # Backend API + WebSocket
    location /api/ {
        proxy_pass http://127.0.0.1:8000;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }

    # Frontend — vanilla static files
    location / {
        root /home/ubuntu/think-twice-V0.3/frontend;
        index index.html;
        try_files $uri $uri/ /index.html;

        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    gzip on;
    gzip_types text/plain text/css application/javascript application/json image/svg+xml;
    gzip_min_length 1024;
}
```

**Important:** `proxy_pass` for `/api/` has no trailing slash. FastAPI defines routes as `/api/players`, `/api/auth/login`, etc., so Nginx must forward the `/api` prefix unchanged.

---

## 6. WebSocket Configuration

WebSocket URLs are constructed from the browser's current location, so they work correctly regardless of the host:

```js
const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${wsProtocol}//${window.location.host}/api/ws/game/${gameId}`;
```

Nginx proxies WebSocket upgrade requests through the same `/api/` location block using the `Upgrade` and `Connection` headers.

---

## 7. Operational Commands

```bash
# Nginx
sudo nginx -t
sudo systemctl reload nginx
sudo systemctl status nginx

# FastAPI backend
sudo systemctl status think-twice-backend
sudo systemctl restart think-twice-backend
sudo journalctl -u think-twice-backend -f

# Check listening services
sudo ss -lntp

# Test FastAPI directly (bypass Nginx)
curl http://127.0.0.1:8000/api/players

# Test through Nginx
curl http://127.0.0.1/api/players
```

---

## 8. Deployment Update Workflow

```bash
# On EC2 — pull latest changes
git pull

# If nginx config changed
sudo cp ~/think-twice-V0.3/nginx/think-twice.conf /etc/nginx/sites-available/think-twice
sudo nginx -t && sudo systemctl reload nginx

# If backend code changed
sudo systemctl restart think-twice-backend

# If backend dependencies changed
pip install -r backend/requirements.txt
sudo systemctl restart think-twice-backend
```

No frontend build or restart is needed — Nginx serves the files directly from the working tree.

---

## 9. Security Notes

- Do **not** expose RDS port `5432` to `0.0.0.0/0`
- Do **not** expose FastAPI port `8000` publicly — Nginx is the only public proxy
- Do **not** expose Vite port `3000` in production
- Do **not** commit `DATABASE_URL` passwords or any secrets to git
- Keep SSH (port 22) restricted to known IPs where practical
- Review and remove unused security group rules after deployment is stable

---

## 10. Current Deployment Status

| Component | Status |
|---|---|
| EC2 application server | Complete |
| Nginx reverse proxy | Complete |
| Frontend static serving | Complete |
| FastAPI systemd service | Complete |
| Auto-start on reboot | Complete |
| RDS PostgreSQL | Complete |
| EC2 to RDS connectivity | Complete |
| WebSocket proxy | Configured |
| Elastic IP | Allocated |
