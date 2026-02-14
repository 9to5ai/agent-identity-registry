# Deployment Guide

## Option 1: Render.com (Recommended - Free Tier)

1. Go to [Render.com](https://render.com) and sign up/login
2. Click "New +" → "Web Service"
3. Connect your GitHub account and select `agent-identity-registry`
4. Render will auto-detect `render.yaml` and configure everything
5. Click "Create Web Service"
6. Wait ~2 minutes for deployment
7. Your URL will be: `https://agent-identity-registry.onrender.com`

**Note:** Free tier spins down after 15 minutes of inactivity. First request after sleep takes ~30 seconds.

## Option 2: Railway.app

1. Go to [Railway.app](https://railway.app) and sign up/login
2. Click "New Project" → "Deploy from GitHub repo"
3. Select `agent-identity-registry`
4. Railway will auto-detect Dockerfile
5. Click "Deploy"
6. Go to Settings → Generate Domain
7. Your URL will be: `https://agent-identity-registry.up.railway.app`

## Option 3: Local Docker

```bash
# Build image
docker build -t agent-identity-registry .

# Run container
docker run -p 8000:8000 agent-identity-registry

# Access at http://localhost:8000
```

## Option 4: Direct Python

```bash
# Create venv
python -m venv .venv
source .venv/bin/activate

# Install
pip install -e .

# Run
uvicorn src.agent_registry.main:app --host 0.0.0.0 --port 8000
```

## Testing Deployment

After deployment, verify with:

```bash
# Health check
curl https://YOUR-URL/health

# Run demo
python demo.py --base-url https://YOUR-URL
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 8000 | Server port (auto-set by Render/Railway) |

## Updating

All deployment options auto-deploy on push to `main` branch:

```bash
git push origin main
```
