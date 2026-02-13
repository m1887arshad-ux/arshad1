# Docker Deployment Guide for Hackathon Judges

## Quick Deploy (One Command)

Create this `docker-compose.yml` in your root directory:

```yaml
version: '3.8'

services:
  backend:
    build: 
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      # Database
      - DATABASE_URL=sqlite:///./bharat.db
      
      # JWT Authentication
      - SECRET_KEY=your-secret-key-change-in-production-min-32-chars
      - ALGORITHM=HS256
      - ACCESS_TOKEN_EXPIRE_MINUTES=10080
      
      # Telegram Bot (Optional)
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      
      # Groq API (Optional - for AI features)
      - GROQ_API_KEY=${GROQ_API_KEY}
    volumes:
      - ./backend/bharat.db:/app/bharat.db
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ./owner-frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - backend

networks:
  default:
    name: bharat-network
```

Then run:
```bash
docker-compose up --build
```

## Backend Dockerfile

Ensure your `backend/Dockerfile` looks like this (no Tesseract):

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (NO Tesseract needed!)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "run_server.py"]
```

## Frontend Dockerfile

Create `owner-frontend/Dockerfile`:

```dockerfile
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy application code
COPY . .

# Build the Next.js application
RUN npm run build

# Expose port
EXPOSE 3000

# Run the application
CMD ["npm", "run", "start"]
```

## Upload to Docker Hub

### 1. Build and Tag Images

```bash
# Backend
cd backend
docker build -t yourusername/bharat-backend:latest .

# Frontend
cd ../owner-frontend
docker build -t yourusername/bharat-frontend:latest .
```

### 2. Login to Docker Hub

```bash
docker login
# Enter your Docker Hub username and password
```

### 3. Push Images

```bash
docker push yourusername/bharat-backend:latest
docker push yourusername/bharat-frontend:latest
```

### 4. Share with Judges

Provide judges with a simple pull command:

```bash
# Pull images
docker pull yourusername/bharat-backend:latest
docker pull yourusername/bharat-frontend:latest

# Run with docker-compose
docker-compose up
```

## Environment Variables for Judges

Create `.env` file for judges:

```env
# Required
SECRET_KEY=bharat-hackathon-secret-key-2026-change-this

# Optional - Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather

# Optional - Groq AI
GROQ_API_KEY=your_groq_api_key

# API URL for frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Test Locally

After `docker-compose up`, test:

```bash
# Health check
curl http://localhost:8000/health

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@bharat.com","password":"Admin@123456"}'

# Get inventory
curl http://localhost:8000/records/inventory \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Free Hosting Options

### Option 1: Render.com (Recommended for Hackathons)

1. **Create render.yaml** in root:

```yaml
services:
  - type: web
    name: bharat-backend
    env: python
    buildCommand: cd backend && pip install -r requirements.txt
    startCommand: cd backend && python run_server.py
    envVars:
      - key: DATABASE_URL
        value: sqlite:///./bharat.db
      - key: SECRET_KEY
        generateValue: true
      - key: TELEGRAM_BOT_TOKEN
        sync: false
      - key: GROQ_API_KEY
        sync: false

  - type: web
    name: bharat-frontend
    env: node
    buildCommand: cd owner-frontend && npm install && npm run build
    startCommand: cd owner-frontend && npm run start
    envVars:
      - key: NEXT_PUBLIC_API_URL
        value: https://bharat-backend.onrender.com
```

2. Push to GitHub
3. Connect to Render.com
4. Deploy automatically

### Option 2: Railway.app

1. Push to GitHub
2. Connect Railway to your repo
3. Add environment variables in Railway dashboard
4. Deploy automatically

### Option 3: Fly.io

1. Install flyctl: `curl -L https://fly.io/install.sh | sh`
2. Login: `fly auth login`
3. Deploy backend:
```bash
cd backend
fly launch
fly deploy
```
4. Deploy frontend:
```bash
cd owner-frontend
fly launch
fly deploy
```

## Troubleshooting

### Issue: "Module not found" errors
**Solution:** Rebuild without cache
```bash
docker-compose build --no-cache
```

### Issue: "Port already in use"
**Solution:** Change ports in docker-compose.yml
```yaml
ports:
  - "8001:8000"  # Changed from 8000:8000
```

### Issue: Database not persisting
**Solution:** Check volume mount
```yaml
volumes:
  - ./backend/bharat.db:/app/bharat.db
```

### Issue: Frontend can't reach backend
**Solution:** Update NEXT_PUBLIC_API_URL
```yaml
environment:
  - NEXT_PUBLIC_API_URL=http://backend:8000  # Use service name
```

## Demo Credentials for Judges

Add this to your README:

```markdown
## Test Account

**Owner Dashboard:**
- URL: http://localhost:3000
- Email: admin@bharat.com
- Password: Admin@123456

**API Documentation:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

**Sample Test Flow:**
1. Login to dashboard
2. Go to chat (or use Telegram bot)
3. Send: "I need 2 Benadryl for Rahul"
4. Check "Pending Approvals" in dashboard
5. Approve the draft order
6. Verify invoice created in "Records"
```

## Production Checklist

- [ ] Change SECRET_KEY
- [ ] Set up proper database (PostgreSQL)
- [ ] Configure CORS properly
- [ ] Add SSL/TLS certificates
- [ ] Set up monitoring (Sentry, DataDog)
- [ ] Configure backup strategy
- [ ] Add rate limiting
- [ ] Set up CI/CD pipeline

## For Judges: One-Line Test

```bash
git clone https://github.com/yourusername/bharat && cd bharat && docker-compose up
```

Then visit: http://localhost:3000

## Resources

- **Docker Hub:** https://hub.docker.com/
- **Render:** https://render.com/
- **Railway:** https://railway.app/
- **Fly.io:** https://fly.io/

Good luck! 🚀
