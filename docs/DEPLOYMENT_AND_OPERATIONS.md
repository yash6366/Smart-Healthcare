# VakCare — Deployment & Operations Manual

## 1. Environment Variables Reference

Create a `.env` file in the `backend/` directory or inject these environment variables into your deployment target (Vercel, Railway, AWS, Docker):

| Variable | Required | Default | Description |
| :--- | :---: | :---: | :--- |
| `DJANGO_SETTINGS_MODULE` | Yes | `config.settings.development` | Set to `config.settings.production` in production environments |
| `DJANGO_SECRET_KEY` | Yes | Insecure Default | Secret cryptographic key (Must be $\ge 40$ chars in production) |
| `DJANGO_DEBUG` | No | `False` | Enable debug mode (`True` only in local development) |
| `DJANGO_ALLOWED_HOSTS` | Yes | `localhost,127.0.0.1` | Comma-separated domain names / IPs permitted to connect |
| `DB_ENGINE` | No | `django.db.backends.mysql` | Database engine (`mysql`, `postgresql`, or `sqlite3`) |
| `DATABASE_URL` | No | Empty | Full connection URL (`mysql://user:pass@host:port/dbname` or `postgres://...`) |
| `DB_NAME` | No | `vakcare_db` | Database schema name |
| `DB_USER` | No | `root` / `postgres` | Database username |
| `DB_PASSWORD` | No | Empty | Database password |
| `DB_HOST` | No | `127.0.0.1` | Database host |
| `DB_PORT` | No | `3306` / `5432` | Database port |
| `DB_CONN_MAX_AGE` | No | `60` | Persistent DB connection lifetime in seconds |
| `DB_SSL_REQUIRE` | No | `False` | Require SSL connection to cloud databases (Aiven, RDS, PlanetScale) |
| `USE_SQLITE_FOR_TESTS` | No | `True` | Uses fast in-memory/file SQLite for `pytest` test runs |
| `REDIS_URL` | No | Empty | Redis connection URL for distributed throttling and cache |
| `CORS_ALLOWED_ORIGINS` | Yes | Localhost ports | Comma-separated list of allowed frontend origins |
| `CSRF_TRUSTED_ORIGINS` | Yes | Localhost ports | Comma-separated list of trusted CSRF origins |
| `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` | No | `30` | JWT Access Token expiration window |
| `JWT_REFRESH_TOKEN_LIFETIME_DAYS` | No | `7` | JWT Refresh Token expiration window |
| `AI_PROVIDER` | No | `mock` | Active AI provider: `openai`, `gemini`, or `mock` |
| `AI_PROVIDER_API_KEY` | If LLM | Empty | API Key for OpenAI or Google Gemini |
| `AI_PROVIDER_MODEL` | No | `gpt-4o-mini` / `gemini-2.5-flash` | Target model identifier |
| `SECURE_SSL_REDIRECT` | No | `True` in prod | Forces HTTPS redirects |
| `SECURE_HSTS_SECONDS` | No | `31536000` | HTTP Strict Transport Security (1 year) |

---

## 2. Serverless Deployment (Vercel)

VakCare is pre-configured for full-stack serverless deployment on **Vercel** via `vercel.json`:
- **Backend**: Managed via `@vercel/python` (Python 3.12 runtime) executing `backend/config/wsgi.py`.
- **Frontend**: Served statically from `frontend/**` via `@vercel/static`.
- **Global Security Headers**: Enforced directly at the Vercel edge.

### `vercel.json` Specification
```json
{
  "version": 2,
  "builds": [
    {
      "src": "backend/config/wsgi.py",
      "use": "@vercel/python",
      "config": {
        "maxLambdaSize": "15mb",
        "runtime": "python3.12"
      }
    },
    {
      "src": "frontend/**",
      "use": "@vercel/static"
    }
  ],
  "routes": [
    { "src": "/api/(.*)", "dest": "backend/config/wsgi.py" },
    { "src": "/admin/(.*)", "dest": "backend/config/wsgi.py" },
    { "src": "/static/(.*)", "dest": "backend/config/wsgi.py" },
    { "src": "/frontend/(.*)", "dest": "frontend/$1" },
    { "src": "/(.*)", "dest": "frontend/$1" }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "X-XSS-Protection", "value": "1; mode=block" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" }
      ]
    }
  ]
}
```

### Deploying to Vercel via CLI
```bash
# 1. Install Vercel CLI
npm install -g vercel

# 2. Deploy from project root
vercel --prod
```

---

## 3. Containerized / Linux VM Production Deployment

For traditional virtual machine (AWS EC2, DigitalOcean, Ubuntu) or Docker container deployments:

### 3.1 Gunicorn WSGI Server
Run the production Gunicorn application server:
```bash
gunicorn --workers 4 \
         --threads 2 \
         --bind 0.0.0.0:8000 \
         --chdir backend \
         --access-logfile - \
         --error-logfile - \
         config.wsgi:application
```

### 3.2 Nginx Reverse Proxy Configuration
```nginx
server {
    listen 80;
    server_name vakcare.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name vakcare.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/vakcare.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/vakcare.yourdomain.com/privkey.pem;

    # Static Frontend
    location / {
        root /var/www/vakcare/frontend;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Django API & Admin
    location ~ ^/(api|admin|static)/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 4. Database Migrations & Administration

### Applying Database Migrations
Always execute migrations prior to launching new application code:
```bash
python backend/manage.py migrate
```

### Creating Initial Administrator Superuser
```bash
python backend/manage.py createsuperuser --email admin@vakcare.com --username admin
```

---

## 5. Background Tasks & Automated Reminders

VakCare includes an automated scanner that identifies confirmed upcoming appointments within a configurable window (default: 48 hours) and dispatches deduplicated in-app reminder notifications to patients.

### Running via Django Management Command
```bash
python backend/manage.py send_appointment_reminders --hours 48
```

### Production Cron Schedule
Add this cron entry to execute reminder scans every hour:
```cron
0 * * * * cd /var/www/vakcare && /var/www/vakcare/.venv/bin/python backend/manage.py send_appointment_reminders --hours 48 >> /var/log/vakcare_reminders.log 2>&1
```

### Automated API Trigger (Admin Only)
Authorized automation bots or monitoring workers can trigger the reminder job over HTTP:
```bash
curl -X POST https://<domain>/api/v1/notifications/trigger-reminders/ \
     -H "Authorization: Bearer <admin_token>" \
     -H "Content-Type: application/json" \
     -d '{"lead_hours": 48}'
```

---

## 6. System Probes & Health Monitoring

Automated load balancers (Kubernetes, AWS ALB, Cloudflare) should monitor these endpoints:

| Endpoint | Method | Expected Status | Description |
| :--- | :---: | :---: | :--- |
| `/api/v1/health/` | `GET` | `200 OK` | **Liveness Probe**: Confirms WSGI worker is alive |
| `/api/v1/health/ready/` | `GET` | `200 OK` (or `503`) | **Readiness Probe**: Verifies database connectivity |
