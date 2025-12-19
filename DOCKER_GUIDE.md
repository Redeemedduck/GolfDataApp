# Docker Deployment Guide - Golf Data Analysis App

This guide will help you build and run the containerized golf data application using OrbStack on macOS.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Understanding the Docker Setup](#understanding-the-docker-setup)
3. [First Time Setup](#first-time-setup)
4. [Building the Docker Image](#building-the-docker-image)
5. [Running the Application](#running-the-application)
6. [Common Operations](#common-operations)
7. [Troubleshooting](#troubleshooting)
8. [OrbStack-Specific Tips](#orbstack-specific-tips)

---

## Prerequisites

### Required Software

- **OrbStack**: Installed and running on macOS
- **Git**: For cloning the repository (already installed)

### Verify OrbStack Installation

```bash
# Check if Docker CLI is available (OrbStack provides this)
docker --version

# Check if Docker Compose is available
docker-compose --version

# Verify OrbStack is running
docker info
```

If these commands work, you're ready to go!

---

## Understanding the Docker Setup

### What is a Container?

Think of a container as a **lightweight, isolated environment** that packages your application with all its dependencies. It's like a virtual machine but much faster and more efficient.

**Key Concepts:**

- **Image**: A blueprint/template for your container (like a class in programming)
- **Container**: A running instance of an image (like an object)
- **Volume**: A way to persist data outside the container (survives restarts)
- **Port Mapping**: Connects container ports to your Mac's ports

### Project Structure

```
GolfDataApp-Docker/
├── Dockerfile              # Instructions to build the container image
├── docker-compose.yml      # Orchestration file (easy container management)
├── .dockerignore          # Files to exclude from the image
├── .env                   # Your secrets (NEVER commit this!)
├── .env.example           # Template for environment variables
├── app.py                 # Main Streamlit application
├── golf_scraper.py        # Uneekor API client
├── golf_db.py            # Database operations
├── requirements.txt       # Python dependencies
└── requirements_cloud.txt # Cloud pipeline dependencies
```

### How Our Container Works

```
┌─────────────────────────────────────────────────────────┐
│  Your Mac (OrbStack)                                    │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Docker Container (golf-data-app)                 │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  Python 3.11 + Streamlit                    │  │  │
│  │  │  ├── app.py                                 │  │  │
│  │  │  ├── golf_scraper.py                        │  │  │
│  │  │  └── golf_db.py                             │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │                                                     │  │
│  │  Mounted Volumes (persist data):                   │  │
│  │  /app/data   → ./data/     (SQLite database)      │  │
│  │  /app/media  → ./media/    (shot images)          │  │
│  │  /app/logs   → ./logs/     (application logs)     │  │
│  │                                                     │  │
│  │  Port 8501 → localhost:8501 (Streamlit UI)         │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## First Time Setup

### Step 1: Prepare Your Environment File

Your `.env` file contains secrets and should already exist. Let's verify it:

```bash
cd /Users/duck/public/GolfDataApp-Docker

# Check if .env exists
ls -la .env

# Verify it has content (don't print it, just check size)
wc -l .env
```

If `.env` doesn't exist, copy from the example:

```bash
cp .env.example .env
```

Then edit `.env` with your actual credentials:

```bash
# Use your preferred editor
nano .env
# or
code .env
```

### Step 2: Create Directories for Persistent Data

These directories will store data outside the container so it persists between restarts:

```bash
# Create directories if they don't exist
mkdir -p data media logs

# Verify they were created
ls -la
```

**What each directory stores:**
- `data/`: SQLite database (`golf_stats.db`)
- `media/`: Shot images and videos
- `logs/`: Application and sync logs

---

## Building the Docker Image

### What is Building?

**Building** takes the instructions in `Dockerfile` and creates a reusable image. This is like compiling code - you do it once, then run it many times.

### Build Command

```bash
# Simple build (uses docker-compose.yml configuration)
docker-compose build

# Or build directly with Docker (more control)
docker build -t golf-data-app:latest .
```

**Understanding the command:**
- `docker-compose build`: Reads `docker-compose.yml` and builds the image
- `-t golf-data-app:latest`: Tags the image with a name and version
- `.`: Build context (current directory)

### What Happens During Build

```
1. Downloads Python 3.11 slim base image
2. Installs system dependencies (build tools, PostgreSQL client)
3. Copies and installs Python packages from requirements.txt
4. Copies application code into the image
5. Sets up non-root user for security
6. Configures Streamlit to run
```

**First build takes 3-5 minutes**. Subsequent builds are much faster thanks to layer caching.

### Verify the Build

```bash
# List Docker images
docker images

# You should see something like:
# REPOSITORY        TAG       IMAGE ID       CREATED         SIZE
# golf-data-app     latest    abc123def456   2 minutes ago   450MB
```

---

## Running the Application

### Option 1: Using Docker Compose (Recommended)

Docker Compose makes it easy to start/stop the application with all the right settings:

```bash
# Start the application (detached mode - runs in background)
docker-compose up -d

# Start with logs visible (helpful for debugging)
docker-compose up

# Stop with Ctrl+C if running in foreground, or:
docker-compose down
```

**What happens when you run this:**
1. Creates a container from your image
2. Mounts volumes (data, media, logs)
3. Loads environment variables from .env
4. Exposes port 8501
5. Starts Streamlit

### Option 2: Using Docker Directly

```bash
# Run container with all necessary configurations
docker run -d \
  --name golf-data-app \
  -p 8501:8501 \
  --env-file .env \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/media:/app/media" \
  -v "$(pwd)/logs:/app/logs" \
  --restart unless-stopped \
  golf-data-app:latest
```

**Breaking down the command:**
- `-d`: Detached mode (runs in background)
- `--name`: Give the container a friendly name
- `-p 8501:8501`: Map port 8501 (host:container)
- `--env-file`: Load environment variables from .env
- `-v`: Mount volumes for persistent data
- `--restart unless-stopped`: Auto-restart if container crashes
- `golf-data-app:latest`: The image to run

### Access the Application

Once running, open your browser:

```
http://localhost:8501
```

You should see the "My Golf Lab" Streamlit interface!

---

## Common Operations

### Check Container Status

```bash
# List running containers
docker ps

# List all containers (including stopped)
docker ps -a

# Check container health
docker inspect golf-data-app | grep -A 5 Health
```

### View Logs

```bash
# Follow logs in real-time (Ctrl+C to exit)
docker-compose logs -f

# View last 50 lines
docker-compose logs --tail=50

# View logs for specific service
docker logs golf-data-app

# Follow logs with timestamps
docker logs -f --timestamps golf-data-app
```

### Stop and Start

```bash
# Stop the application
docker-compose stop

# Start it again
docker-compose start

# Restart (stop + start)
docker-compose restart

# Stop and remove container (data in volumes is preserved!)
docker-compose down
```

### Execute Commands Inside Container

Sometimes you need to run commands inside the container:

```bash
# Open a shell inside the container
docker exec -it golf-data-app bash

# Run a specific Python script
docker exec golf-data-app python scripts/supabase_to_bigquery.py full

# Check Python version
docker exec golf-data-app python --version

# List files in the container
docker exec golf-data-app ls -la /app
```

### Update Application Code

If you change your Python code and want to update the container:

```bash
# Rebuild the image
docker-compose build

# Stop old container and start new one
docker-compose down
docker-compose up -d

# Or do both in one command
docker-compose up -d --build
```

### View Resource Usage

```bash
# See CPU/memory usage
docker stats golf-data-app

# See disk usage
docker system df
```

### Clean Up

```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune

# Remove all unused data (careful!)
docker system prune

# Nuclear option - remove everything (CAREFUL!)
docker system prune -a --volumes
```

---

## Troubleshooting

### Container Won't Start

**Check logs:**
```bash
docker-compose logs
```

**Common issues:**

1. **Port already in use**
   ```
   Error: bind: address already in use
   ```
   Solution:
   ```bash
   # Find what's using port 8501
   lsof -i :8501

   # Kill the process or change port in docker-compose.yml
   # Change "8501:8501" to "8502:8501"
   ```

2. **Permission denied errors**
   ```
   PermissionError: [Errno 13] Permission denied
   ```
   Solution:
   ```bash
   # Fix directory permissions
   chmod -R 755 data media logs
   ```

3. **Missing .env file**
   ```
   Error: No such file or directory: '.env'
   ```
   Solution:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

### Application Not Loading

1. **Check if container is running:**
   ```bash
   docker ps
   ```

2. **Check health status:**
   ```bash
   docker inspect golf-data-app --format='{{.State.Health.Status}}'
   ```

3. **Check Streamlit logs:**
   ```bash
   docker logs golf-data-app | grep streamlit
   ```

### Database Issues

**SQLite file locked:**
```bash
# Stop container
docker-compose down

# Check if file exists
ls -la data/golf_stats.db

# Restart
docker-compose up -d
```

**Database not persisting:**
```bash
# Verify volume mounts
docker inspect golf-data-app | grep -A 10 Mounts

# Check if data directory exists
ls -la data/
```

### OrbStack-Specific Issues

**OrbStack not running:**
```bash
# Start OrbStack from Applications folder
open -a OrbStack

# Or check if it's running
ps aux | grep OrbStack
```

**File permissions on macOS:**

OrbStack handles macOS file permissions better than Docker Desktop, but you may still encounter issues:

```bash
# Verify ownership
ls -la data/ media/ logs/

# Fix if needed
sudo chown -R $(whoami) data/ media/ logs/
```

### Container Crashes Immediately

```bash
# Check exit code
docker ps -a | grep golf-data-app

# View full logs
docker logs golf-data-app

# Common causes:
# 1. Python import errors (missing dependencies)
# 2. Invalid .env variables
# 3. Port conflicts
```

---

## OrbStack-Specific Tips

### Why OrbStack is Great for This Project

1. **Native Performance**: OrbStack uses macOS virtualization framework for near-native speed
2. **Fast Startup**: Containers start in milliseconds
3. **Better File Sharing**: Volumes mounted from macOS are much faster than Docker Desktop
4. **Lower Resource Usage**: Uses less CPU and memory than Docker Desktop
5. **Better Integration**: Feels more native on macOS

### OrbStack Volume Performance

OrbStack optimizes volume mounts for macOS. Your SQLite database operations will be significantly faster than with Docker Desktop:

```bash
# Test read performance
docker exec golf-data-app time ls -R /app/data

# Test write performance
docker exec golf-data-app time dd if=/dev/zero of=/app/data/test.dat bs=1M count=100
```

### Accessing Containers via OrbStack UI

OrbStack provides a nice GUI:

1. Click OrbStack icon in menu bar
2. Select "Containers"
3. Click on `golf-data-app`
4. You can:
   - View logs
   - Open a shell
   - See resource usage
   - Stop/start/restart

### OrbStack CLI Shortcuts

```bash
# OrbStack provides the orb CLI for container management
orb list

# SSH into container (OrbStack specific)
orb exec golf-data-app bash

# View OrbStack status
orb status
```

### Apple Silicon (M1/M2/M3) Considerations

If you're on Apple Silicon, the container runs natively in ARM64 architecture:

```bash
# Verify architecture
docker exec golf-data-app uname -m
# Should show: aarch64

# Check Python was built for ARM
docker exec golf-data-app python -c "import platform; print(platform.machine())"
```

All Python dependencies in our requirements are compatible with ARM64, so you shouldn't have issues.

---

## Development Workflow

### Typical Development Cycle

1. **Make changes to Python files** (app.py, golf_scraper.py, etc.)

2. **Rebuild and restart:**
   ```bash
   docker-compose up -d --build
   ```

3. **Test changes** at http://localhost:8501

4. **View logs if issues occur:**
   ```bash
   docker-compose logs -f
   ```

### Development with Live Reloading

For faster iteration during development, you can mount your code files directly:

Edit `docker-compose.yml` and uncomment these lines:

```yaml
volumes:
  - ./app.py:/app/app.py:ro
  - ./golf_scraper.py:/app/golf_scraper.py:ro
  - ./golf_db.py:/app/golf_db.py:ro
```

Then restart:

```bash
docker-compose restart
```

Now Streamlit will detect changes and auto-reload!

**Note**: Remove these volume mounts before deploying to production.

### Testing Cloud Pipeline Scripts

Run cloud pipeline scripts inside the container:

```bash
# Test Supabase connection
docker exec golf-data-app python legacy/test_connection.py

# Sync to BigQuery
docker exec golf-data-app python scripts/supabase_to_bigquery.py full

# Run AI analysis
docker exec golf-data-app python scripts/gemini_analysis.py summary
```

---

## Production Deployment

### Security Best Practices

1. **Never commit .env to version control**
   ```bash
   # Verify .env is in .gitignore
   git check-ignore .env
   ```

2. **Use secrets management** (for production)
   - Docker Swarm secrets
   - Kubernetes secrets
   - Cloud provider secret managers

3. **Update base image regularly**
   ```bash
   docker pull python:3.11-slim
   docker-compose build --no-cache
   ```

### Resource Limits

For production, uncomment the resource limits in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
    reservations:
      cpus: '0.5'
      memory: 512M
```

### Monitoring

Set up monitoring for production:

```bash
# Health check endpoint
curl http://localhost:8501/_stcore/health

# Container stats
docker stats golf-data-app --no-stream

# Disk usage
du -sh data/ media/ logs/
```

---

## Quick Reference

### Essential Commands

```bash
# Build and start
docker-compose up -d --build

# Stop
docker-compose down

# View logs
docker-compose logs -f

# Restart
docker-compose restart

# Shell access
docker exec -it golf-data-app bash

# Rebuild after code changes
docker-compose up -d --build

# Check status
docker ps

# Clean up
docker system prune
```

### File Locations

| What | Where |
|------|-------|
| SQLite DB | `./data/golf_stats.db` |
| Shot images | `./media/{session_id}/` |
| Application logs | `./logs/` |
| Environment vars | `./.env` |
| Container app code | `/app/` (inside container) |

### Ports

| Service | Port | URL |
|---------|------|-----|
| Streamlit UI | 8501 | http://localhost:8501 |
| Health check | 8501 | http://localhost:8501/_stcore/health |

---

## Next Steps

1. **Build your image**: `docker-compose build`
2. **Start the app**: `docker-compose up -d`
3. **Access in browser**: http://localhost:8501
4. **Import some golf data** using a Uneekor URL
5. **Explore the containerized app!**

For more advanced usage, see:
- `SETUP_GUIDE.md` - Original setup guide
- `AUTOMATION_GUIDE.md` - Automating cloud syncs
- `QUICKSTART.md` - Quick command reference

---

## Getting Help

**Container won't start?**
1. Check logs: `docker-compose logs`
2. Verify .env exists: `ls -la .env`
3. Check port 8501 is free: `lsof -i :8501`

**Data not persisting?**
1. Check volumes: `docker inspect golf-data-app | grep Mounts`
2. Verify directories exist: `ls -la data/ media/ logs/`

**Performance issues?**
1. Check resources: `docker stats golf-data-app`
2. Check OrbStack CPU/memory allocation in settings

**Still stuck?**
- Check OrbStack docs: https://docs.orbstack.dev
- Docker docs: https://docs.docker.com
- Streamlit docs: https://docs.streamlit.io

Happy containerizing! 🐳⛳
