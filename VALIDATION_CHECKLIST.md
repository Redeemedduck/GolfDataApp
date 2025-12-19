# Docker Setup Validation Checklist

Use this checklist to verify your containerization setup is complete and working correctly.

## Pre-Flight Checks

### Environment Verification

- [ ] OrbStack is installed and running
  ```bash
  docker --version
  # Should show: Docker version 28.x.x or higher
  ```

- [ ] Docker Compose is available
  ```bash
  docker-compose --version
  # Should show: Docker Compose version v2.x.x or higher
  ```

- [ ] OrbStack daemon is running
  ```bash
  docker info
  # Should display system information without errors
  ```

### File Structure Verification

- [ ] All Docker configuration files exist
  ```bash
  ls -la Dockerfile docker-compose.yml .dockerignore
  # All three files should be listed
  ```

- [ ] Documentation files created
  ```bash
  ls -la DOCKER_*.md
  # Should show: DOCKER_GUIDE.md, DOCKER_README.md, DOCKER_SETUP_COMPLETE.md
  ```

- [ ] Automation script exists and is executable
  ```bash
  ls -la docker-quickstart.sh
  # Should show: -rwxr-xr-x (executable permissions)
  ```

- [ ] Persistent data directories exist
  ```bash
  ls -la data/ media/ logs/
  # All three directories should exist with .gitkeep files
  ```

### Configuration Validation

- [ ] docker-compose.yml is valid
  ```bash
  docker-compose config --quiet
  # Should complete without errors (version warning is OK)
  ```

- [ ] .env file exists with credentials
  ```bash
  ls -la .env
  # File should exist (don't display contents - contains secrets!)
  ```

- [ ] .env contains actual values (not placeholders)
  ```bash
  grep -q "your-anon-key-here" .env && echo "⚠️  Update .env with real credentials" || echo "✓ .env appears configured"
  ```

## Build Phase Checks

### Image Building

- [ ] Docker image builds successfully
  ```bash
  docker-compose build
  # Should complete without errors
  # First build: 3-5 minutes
  # Subsequent builds: 30 seconds (if only code changed)
  ```

- [ ] Image exists in local registry
  ```bash
  docker images | grep golf-data-app
  # Should show: golf-data-app:latest with size ~450MB
  ```

- [ ] Image layers are optimized
  ```bash
  docker history golf-data-app:latest | head -10
  # Should show multi-stage build layers
  ```

### Build Optimization

- [ ] Build uses layer caching
  ```bash
  # Make a small change to app.py, then rebuild:
  docker-compose build
  # Should complete in ~30 seconds (not 3-5 minutes)
  ```

- [ ] .dockerignore is working
  ```bash
  docker build -t test-ignore . 2>&1 | grep -E "(\.env|\.git|__pycache__|\.db)" || echo "✓ Files properly ignored"
  ```

## Runtime Phase Checks

### Container Startup

- [ ] Container starts successfully
  ```bash
  docker-compose up -d
  # Should show: Creating/Starting golf-data-app ... done
  ```

- [ ] Container is running
  ```bash
  docker ps | grep golf-data-app
  # Should show golf-data-app with status "Up"
  ```

- [ ] Container health check passes
  ```bash
  docker inspect golf-data-app --format='{{.State.Health.Status}}'
  # Should show: healthy (after 5-10 seconds)
  ```

### Application Access

- [ ] Streamlit port is accessible
  ```bash
  curl -f http://localhost:8501/_stcore/health
  # Should return: ok
  ```

- [ ] Web UI loads in browser
  ```
  Open: http://localhost:8501
  # Should see "My Golf Data Lab" Streamlit interface
  ```

- [ ] No error messages in browser console
  ```
  Open browser dev tools (F12) → Console tab
  # Should see no red error messages
  ```

### Data Persistence

- [ ] Volumes are mounted correctly
  ```bash
  docker inspect golf-data-app | grep -A 10 Mounts
  # Should show three mounts: data, media, logs
  ```

- [ ] SQLite database is created
  ```bash
  # Import some data via UI first, then:
  ls -la data/golf_stats.db
  # File should exist with size > 0 bytes
  ```

- [ ] Data survives container restart
  ```bash
  # Import data → Stop container → Start container → Check data still visible
  docker-compose restart
  # Open http://localhost:8501 - data should still be there
  ```

- [ ] Media files are accessible
  ```bash
  # After importing data with images:
  ls -la media/
  # Should show session directories with images
  ```

### Environment Variables

- [ ] .env variables loaded
  ```bash
  docker exec golf-data-app printenv | grep SUPABASE_URL
  # Should show your Supabase URL (not empty)
  ```

- [ ] Streamlit configuration applied
  ```bash
  docker exec golf-data-app printenv | grep STREAMLIT_
  # Should show Streamlit environment variables
  ```

### Application Functionality

- [ ] Import feature works
  ```
  1. Paste a Uneekor URL in sidebar
  2. Click "Run Import"
  3. Should see "Import complete" success message
  ```

- [ ] Data displays correctly
  ```
  1. Select a session from dropdown
  2. Should see shot data in tables and charts
  ```

- [ ] Interactive features work
  ```
  1. Click a row in Shot Viewer tab
  2. Should see shot details and images
  ```

- [ ] Data management works
  ```
  1. Go to "Manage Data" tab
  2. Try renaming a club
  3. Change should persist
  ```

## Security Checks

### Container Security

- [ ] Container runs as non-root user
  ```bash
  docker exec golf-data-app whoami
  # Should show: golfuser (not root)
  ```

- [ ] User ID is correct
  ```bash
  docker exec golf-data-app id
  # Should show: uid=1000(golfuser)
  ```

### Secrets Management

- [ ] .env is in .gitignore
  ```bash
  git check-ignore .env
  # Should output: .env
  ```

- [ ] .env not in Docker image
  ```bash
  docker run --rm golf-data-app:latest cat .env 2>&1 | grep "No such file"
  # Should show "No such file or directory"
  ```

- [ ] No secrets in image history
  ```bash
  docker history golf-data-app:latest | grep -E "(SUPABASE|GEMINI|API)" && echo "⚠️  Found potential secrets in image!" || echo "✓ No secrets found"
  ```

### File Permissions

- [ ] Data directories are writable
  ```bash
  docker exec golf-data-app touch /app/data/test.txt
  docker exec golf-data-app rm /app/data/test.txt
  # Should complete without "Permission denied" errors
  ```

## Performance Checks

### Resource Usage

- [ ] CPU usage is reasonable
  ```bash
  docker stats golf-data-app --no-stream
  # CPU: Should be <5% when idle, <20% when active
  # Memory: Should be ~100-300MB
  ```

- [ ] Container starts quickly
  ```bash
  time docker-compose restart
  # Should complete in <10 seconds
  ```

### Build Performance

- [ ] Cached build is fast
  ```bash
  time docker-compose build
  # Should complete in <1 minute (if no dependency changes)
  ```

- [ ] Image size is optimized
  ```bash
  docker images golf-data-app:latest --format "{{.Size}}"
  # Should be ~400-500MB (not >1GB)
  ```

## Logging Checks

### Log Access

- [ ] Container logs are accessible
  ```bash
  docker-compose logs | head -20
  # Should show Streamlit startup logs
  ```

- [ ] Logs can be streamed
  ```bash
  timeout 5 docker-compose logs -f
  # Should show live logs for 5 seconds
  ```

- [ ] Application logs persist to volume
  ```bash
  # After running the app for a while:
  ls -la logs/
  # Should show log files
  ```

### Log Rotation

- [ ] Log rotation is configured
  ```bash
  docker inspect golf-data-app | grep -A 5 LogConfig
  # Should show max-size: 10m, max-file: 3
  ```

## Cloud Integration Checks (Optional)

### Database Sync

- [ ] Supabase connection works
  ```bash
  docker exec golf-data-app python -c "from golf_db import get_supabase_client; client = get_supabase_client(); print('✓ Supabase connected')"
  ```

- [ ] BigQuery sync script works
  ```bash
  docker exec golf-data-app python scripts/supabase_to_bigquery.py full
  # Should complete without errors (if GCP credentials configured)
  ```

### AI Analysis

- [ ] Gemini API connection works
  ```bash
  docker exec golf-data-app python scripts/gemini_analysis.py summary
  # Should show AI-generated analysis (if API key configured)
  ```

## Operational Checks

### Container Management

- [ ] Container stops cleanly
  ```bash
  docker-compose stop
  # Should complete in <10 seconds
  ```

- [ ] Container starts cleanly
  ```bash
  docker-compose start
  # Should complete in <5 seconds
  ```

- [ ] Container can be removed and recreated
  ```bash
  docker-compose down
  docker-compose up -d
  # Data should still be present after recreation
  ```

### Cleanup

- [ ] Old images can be cleaned up
  ```bash
  docker image prune -f
  # Should remove dangling images
  ```

- [ ] Disk space is reasonable
  ```bash
  docker system df
  # Check if usage is reasonable for your needs
  ```

## Documentation Checks

### File Completeness

- [ ] DOCKER_GUIDE.md exists and is readable
  ```bash
  wc -l DOCKER_GUIDE.md
  # Should show ~500+ lines
  ```

- [ ] DOCKER_README.md exists and is readable
  ```bash
  wc -l DOCKER_README.md
  # Should show ~300+ lines
  ```

- [ ] All code examples are valid
  ```
  Manual check: Open DOCKER_GUIDE.md and verify code blocks make sense
  ```

### Setup Script

- [ ] docker-quickstart.sh is executable
  ```bash
  test -x docker-quickstart.sh && echo "✓ Executable" || echo "⚠️  Not executable"
  ```

- [ ] Script runs without errors (dry run)
  ```bash
  # Review the script:
  head -50 docker-quickstart.sh
  # Should show clear bash script with helpful comments
  ```

## Final Validation

### End-to-End Test

- [ ] Complete workflow test
  ```
  1. Stop everything: docker-compose down
  2. Start fresh: docker-compose up -d
  3. Wait for health check: sleep 10
  4. Access UI: open http://localhost:8501
  5. Import data: Paste Uneekor URL
  6. View data: Select session, view shots
  7. Restart: docker-compose restart
  8. Verify data persists: Reload browser
  ```

### Production Readiness

- [ ] All checks above are passing
- [ ] Documentation is complete
- [ ] .env is configured (not using example values)
- [ ] Secrets are not committed to git
- [ ] Application functions as expected
- [ ] Data persists across restarts
- [ ] Performance is acceptable

## Troubleshooting Reference

If any checks fail, refer to:

1. **DOCKER_GUIDE.md** - Comprehensive troubleshooting section
2. **DOCKER_README.md** - Quick fixes for common issues
3. Container logs: `docker-compose logs`
4. OrbStack status: `docker info`

## Success Criteria

All items should be checked before considering the containerization complete:

- ✅ All files created
- ✅ Configuration validated
- ✅ Image builds successfully
- ✅ Container runs healthy
- ✅ Application accessible
- ✅ Data persists
- ✅ Security checks pass
- ✅ Performance acceptable
- ✅ Documentation complete

Once all checks pass, you're ready to use your containerized application!

---

**Last Updated**: 2025-12-19
**Docker Version**: 28.5.2 (OrbStack)
**Base Image**: python:3.11-slim
