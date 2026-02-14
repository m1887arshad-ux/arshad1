# 🐳 Bharat Biz-Agent Docker Deployment Guide

## ✅ What's Ready for Docker

### Backend ✓
- ✅ Dockerfile configured (Python 3.12-slim)
- ✅ Uvicorn server configured for Docker (0.0.0.0:8000)
- ✅ Database persistence via volume mount
- ✅ Health check endpoint (/health)
- ✅ CORS configured for Docker containers
- ✅ TrustedHostMiddleware updated for Docker hostnames
- ✅ Environment-based configuration

### Frontend ✓
- ✅ Dockerfile created (Multi-stage Next.js build)
- ✅ Production build optimized
- ✅ Environment variable for API_URL
- ✅ Uses 'backend' service name in Docker

### Orchestration ✓
- ✅ docker-compose.yml configured
- ✅ Networking between services
- ✅ Environment variables management
- ✅ Health checks
- ✅ Volume persistence

---

## 🚀 Quick Start Guide

### Step 1: Prepare Environment Variables

Create `.env` file in project root:

```bash
cp .env.docker .env
```

Edit `.env` and add your secrets:

```bash
# CHANGE THESE IN PRODUCTION!
SECRET_KEY=generate-a-random-string-with-python
TELEGRAM_BOT_TOKEN=your-bot-token-here
GROQ_API_KEY=your-groq-key-here
ENVIRONMENT=production
```

Generate SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Step 2: Build Images

```bash
# Build both images
docker-compose build

# Or build individual images
docker-compose build backend
docker-compose build frontend
```

### Step 3: Start Services

```bash
# Start all services in background
docker-compose up -d

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Step 4: Verify Deployment

```bash
# Check all services are running
docker-compose ps

# Test backend health
curl http://localhost:8000/health

# Test frontend
curl http://localhost:3000

# Check container logs for errors
docker-compose logs backend | tail -20
docker-compose logs frontend | tail -20
```

---

## 📋 Service URLs (Local Docker)

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API Docs (ReDoc) | http://localhost:8000/redoc |
| Health Check | http://localhost:8000/health |

---

## 🔄 Common Commands

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v

# Restart a service
docker-compose restart backend
docker-compose restart frontend

# View container output
docker-compose logs backend --tail=100

# Execute command in running container
docker-compose exec backend python -c "import app; print('OK')"

# Remove old images before rebuild
docker-compose down
docker image prune -a
docker-compose build --no-cache
```

---

## 📦 Production Deployment Checklist

### Security
- [ ] Generate strong SECRET_KEY (not the default)
- [ ] Store secrets in .env file (NOT in docker-compose.yml)
- [ ] Use environment variables for sensitive data
- [ ] Set ENVIRONMENT=production
- [ ] Update CORS_ALLOW_ORIGIN for your domain
- [ ] Use HTTPS (via reverse proxy like nginx)

### Database
- [ ] Mount bharat.db volume to persistent storage
- [ ] Set up automated backups of the database volume
- [ ] Consider upgrading to PostgreSQL for multi-container deployments

### Networking
- [ ] Use docker network (already configured)
- [ ] Consider network policies if using Kubernetes
- [ ] Set up reverse proxy (nginx) for production

### Monitoring
- [ ] Set up container health checks (already configured)
- [ ] Configure logging drivers for centralized logging
- [ ] Set up monitoring/alerting for health endpoint

### Telegram Bot
- [ ] Verify bot token is correct in .env
- [ ] Test bot receives messages in logs: `docker-compose logs backend | grep Telegram`

### Testing After Deployment
- [ ] Test login/signup flows
- [ ] Send test messages via Telegram bot
- [ ] Verify orders are created as drafts
- [ ] Check database persistence after container restart

---

## 🏗️ Advanced: Production Deployment with Nginx (Optional)

### 1. Create nginx.conf for reverse proxy:

```nginx
upstream backend {
    server backend:8000;
}

upstream frontend {
    server frontend:3000;
}

server {
    listen 80;
    server_name your-domain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/ssl/certs/your-cert.crt;
    ssl_certificate_key /etc/ssl/private/your-key.key;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Backend API
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Frontend
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 2. Update docker-compose.yml with nginx service:

```yaml
nginx:
  image: nginx:alpine
  ports:
    - "80:80"
    - "443:443"  # Add SSL cert volumes
  volumes:
    - ./nginx.conf:/etc/nginx/conf.d/default.conf
  networks:
    - bharat-network
  depends_on:
    - backend
    - frontend
```

---

## 🐛 Troubleshooting

### Backend not starting
```bash
docker-compose logs backend
# Check for missing env vars, import errors, or port conflicts
```

### Frontend can't reach backend
```bash
# Check if CORS is allowing the request
# Check if backend service name 'backend' resolves (docker network DNS)
docker-compose exec frontend ping backend
```

### Database not persisting
```bash
# Verify volume mount is correct
docker volume ls
docker volume inspect bharat_db-volume
```

### Port conflicts
```bash
# If ports 3000/8000 are already in use:
# Edit docker-compose.yml ports section:
# "8080:8000"  (external:internal)
```

---

## 📝 Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| ENVIRONMENT | development | Set to 'production' for deployments |
| SECRET_KEY | (required) | JWT signing key - CHANGE IN PRODUCTION |
| DATABASE_URL | sqlite:///./bharat.db | Database connection string |
| TELEGRAM_BOT_TOKEN | (required) | Bot token from @BotFather |
| GROQ_API_KEY | (required) | AI model access key |
| CORS_ALLOW_ORIGIN | localhost | Comma-separated allowed origins |

---

## 🎯 Next Steps

1. **Test locally** with docker-compose
2. **Deploy to cloud** (AWS ECS, Google Cloud Run, Azure Container Instances)
3. **Set up CI/CD** for automated deployments
4. **Configure monitoring** (Prometheus, Grafana)
5. **Add load balancing** if scaling horizontally
