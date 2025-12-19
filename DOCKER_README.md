# Docker Setup - Quick Reference

This is a **containerized version** of the Golf Data Analysis application, optimized for OrbStack on macOS.

## What's Different from the Original?

This Docker version provides:

- **Isolated Environment**: No need to manage Python virtual environments
- **Consistent Setup**: Works the same on any machine with Docker/OrbStack
- **Easy Deployment**: One command to start the entire application
- **Data Persistence**: Your data survives container restarts
- **Portability**: Can be deployed to cloud platforms (AWS ECS, Google Cloud Run, etc.)

## Quick Start

### Prerequisites

- **OrbStack** installed and running on macOS
- Your `.env` file with API credentials

### Three Commands to Get Started

```bash
# 1. Run the automated setup script
./docker-quickstart.sh

# 2. OR do it manually:
# Build the image
docker-compose build

# 3. Start the application
docker-compose up -d

# 4. Access in browser
open http://localhost:8501
```

That's it! Your containerized golf data app is running.

## File Structure

```
GolfDataApp-Docker/
├── Dockerfile                 # Container image definition
├── docker-compose.yml         # Orchestration configuration
├── .dockerignore             # Files excluded from image
├── docker-quickstart.sh      # Automated setup script
├── DOCKER_GUIDE.md           # Comprehensive guide
├── DOCKER_README.md          # This file
├── .env                      # Your secrets (not committed)
├── data/                     # SQLite database (volume)
├── media/                    # Shot images (volume)
└── logs/                     # Application logs (volume)
```

## Essential Commands

### Daily Operations

```bash
# Start the application
docker-compose up -d

# Stop the application
docker-compose down

# Restart after code changes
docker-compose up -d --build

# View logs
docker-compose logs -f

# Check status
docker ps
```

### Development

```bash
# Access container shell
docker exec -it golf-data-app bash

# Run cloud sync script
docker exec golf-data-app python scripts/supabase_to_bigquery.py full

# Run AI analysis
docker exec golf-data-app python scripts/gemini_analysis.py summary

# View Streamlit logs only
docker-compose logs -f | grep streamlit
```

### Troubleshooting

```bash
# Container won't start? Check logs
docker-compose logs

# Port conflict? Check what's using 8501
lsof -i :8501

# Database issues? Check the volume
ls -la data/

# Rebuild from scratch (no cache)
docker-compose build --no-cache

# Remove everything and start fresh
docker-compose down -v
docker-compose up -d --build
```

## How Data Persists

Your data is stored in **volumes** on your Mac, not inside the container:

| Directory | Purpose | Location |
|-----------|---------|----------|
| `data/` | SQLite database | `./data/golf_stats.db` |
| `media/` | Shot images | `./media/{session_id}/` |
| `logs/` | Application logs | `./logs/*.log` |

When you run `docker-compose down`, these directories remain intact. Your data is safe!

## Accessing the Application

Once running:

- **Streamlit UI**: http://localhost:8501
- **Health Check**: http://localhost:8501/_stcore/health

## Common Scenarios

### Scenario 1: First Time Setup

```bash
# Run the interactive setup script
./docker-quickstart.sh
```

The script will:
1. Check prerequisites
2. Create directories
3. Verify .env file
4. Build the image
5. Start the container
6. Open your browser

### Scenario 2: Daily Use

```bash
# Start the app
docker-compose up -d

# Use the app in your browser
# http://localhost:8501

# Stop when done
docker-compose stop
```

### Scenario 3: Development & Testing

```bash
# Make changes to app.py or other files

# Rebuild and restart
docker-compose up -d --build

# Watch logs for errors
docker-compose logs -f

# Test inside container
docker exec -it golf-data-app bash
python -c "import golf_db; golf_db.init_db()"
```

### Scenario 4: Updating Dependencies

```bash
# Edit requirements.txt or requirements_cloud.txt

# Rebuild with no cache (ensures fresh install)
docker-compose build --no-cache

# Restart with new dependencies
docker-compose up -d
```

### Scenario 5: Backing Up Data

```bash
# Create backup directory
mkdir -p backups/$(date +%Y%m%d)

# Copy SQLite database
cp data/golf_stats.db backups/$(date +%Y%m%d)/

# Copy media files
cp -r media/ backups/$(date +%Y%m%d)/

# Or use tar for compressed backup
tar -czf backups/golf-data-$(date +%Y%m%d).tar.gz data/ media/ logs/
```

## Understanding the Container

### What's Inside the Container?

- Python 3.11
- Streamlit framework
- All your Python dependencies
- Your application code
- Non-root user (security best practice)

### What's Outside the Container?

- Your `.env` file (mounted at runtime)
- SQLite database (`data/`)
- Shot images (`media/`)
- Application logs (`logs/`)

This separation means:
- **Container can be deleted/recreated** without losing data
- **Data persists** between restarts
- **Secrets stay secure** (not baked into the image)

## Environment Variables

The container loads environment variables from your `.env` file:

```bash
# Required for cloud features
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your-key-here
GEMINI_API_KEY=your-key-here

# Required for BigQuery sync
GCP_PROJECT_ID=your-project-id
BQ_DATASET_ID=golf_data
BQ_TABLE_ID=shots
```

**Important**: Never commit `.env` to Git! It's already in `.gitignore`.

## OrbStack vs Docker Desktop

If you're familiar with Docker Desktop, here's what's different with OrbStack:

| Feature | OrbStack | Docker Desktop |
|---------|----------|----------------|
| Startup Time | ~1 second | ~30 seconds |
| Resource Usage | Low (~200MB RAM idle) | High (~2GB+ RAM idle) |
| File Sharing | Fast (native) | Slower (virtualized) |
| macOS Integration | Native | VirtualBox-based |
| Command Syntax | **Same** | **Same** |

Good news: All Docker commands work identically! You can use this guide with Docker Desktop too.

## Performance Tips

### Build Performance

```bash
# Parallel builds (faster on multi-core systems)
docker-compose build --parallel

# Use BuildKit for better caching
DOCKER_BUILDKIT=1 docker-compose build
```

### Runtime Performance

- **Volumes are fast** on OrbStack (native macOS access)
- **SQLite performs well** in containers
- **Streamlit auto-reload** works with mounted volumes

### Resource Limits

If you want to limit container resources:

Edit `docker-compose.yml` and uncomment:

```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
```

## Security Notes

### Best Practices Applied

1. **Non-root user**: Container runs as `golfuser` (UID 1000)
2. **Secrets via .env**: No credentials in the image
3. **Minimal base image**: Python 3.11 slim (smaller attack surface)
4. **Read-only mounts**: Can mount files as `:ro` for extra security

### Checking Your Setup

```bash
# Verify non-root user
docker exec golf-data-app whoami
# Should output: golfuser

# Check if .env is in .gitignore
git check-ignore .env
# Should output: .env

# Inspect image for secrets (shouldn't find any)
docker history golf-data-app:latest
```

## Deployment to Cloud

This Docker setup can be deployed to:

- **Google Cloud Run**: `gcloud run deploy`
- **AWS ECS/Fargate**: Via ECS task definition
- **Azure Container Instances**: `az container create`
- **Fly.io**: `fly launch`
- **Railway**: Connect git repo

For cloud deployment, you'll need to:
1. Push image to a container registry (Docker Hub, GCR, ECR)
2. Configure secrets in the cloud platform
3. Set up persistent volumes if needed
4. Configure health checks and monitoring

See `DEPLOYMENT_SUMMARY.md` for cloud-specific guides.

## Getting Help

### Check Logs First

```bash
# Application logs
docker-compose logs

# Just the last 50 lines
docker-compose logs --tail=50

# Follow logs in real-time
docker-compose logs -f

# Logs for last 1 hour
docker-compose logs --since 1h
```

### Common Issues

1. **Port 8501 in use**
   - Change port in docker-compose.yml: `"8502:8501"`

2. **Permission errors**
   - Fix ownership: `sudo chown -R $(whoami) data/ media/ logs/`

3. **OrbStack not running**
   - Start from Applications or: `open -a OrbStack`

4. **Container crashes**
   - Check logs: `docker logs golf-data-app`
   - Verify .env: `ls -la .env`

5. **Slow builds**
   - Enable BuildKit: `export DOCKER_BUILDKIT=1`

### Resources

- **Comprehensive Guide**: `DOCKER_GUIDE.md` (100+ pages, beginner-friendly)
- **Project Documentation**: `README.md`, `SETUP_GUIDE.md`
- **OrbStack Docs**: https://docs.orbstack.dev
- **Docker Docs**: https://docs.docker.com
- **Streamlit Docs**: https://docs.streamlit.io

## Next Steps

1. **Explore the app**: Import some golf data via Uneekor URL
2. **Read DOCKER_GUIDE.md**: Comprehensive guide with explanations
3. **Customize docker-compose.yml**: Add resource limits, networks, etc.
4. **Set up cloud sync**: Configure BigQuery and AI analysis
5. **Deploy to cloud**: Use this container in production

## Summary

You now have a **fully containerized** golf data analysis application:

- ✅ Isolated Python environment
- ✅ Persistent data storage
- ✅ Easy start/stop commands
- ✅ Optimized for OrbStack on macOS
- ✅ Production-ready configuration
- ✅ Comprehensive documentation

**Start using it:**

```bash
docker-compose up -d
open http://localhost:8501
```

Happy containerizing! 🐳⛳
