#!/bin/bash
#
# GolfDataApp Daily Automation Script
# Runs discover, date scraping, and backfill operations
#
# Usage: ./daily_automation.sh
# Scheduled via launchd: com.golfdataapp.automation.plist
#

set -o pipefail

# Configuration
APP_DIR="/Users/duck/Documents/GitHub/GolfDataApp"
VENV_DIR="${APP_DIR}/venv"
LOG_FILE="${APP_DIR}/logs/automation.log"
MAX_SCRAPE_SESSIONS=20

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Logging function with timestamps
log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$LOG_FILE"
}

# Error handler
handle_error() {
    local exit_code=$?
    local line_no=$1
    log "ERROR" "Script failed at line $line_no with exit code $exit_code"
    log "ERROR" "Automation run completed with errors"
    exit $exit_code
}

trap 'handle_error $LINENO' ERR

# Start logging
log "INFO" "=========================================="
log "INFO" "Starting GolfDataApp daily automation"
log "INFO" "=========================================="

# Change to app directory
cd "$APP_DIR" || {
    log "ERROR" "Failed to change to app directory: $APP_DIR"
    exit 1
}

# Activate virtual environment
if [[ -f "${VENV_DIR}/bin/activate" ]]; then
    log "INFO" "Activating virtual environment"
    source "${VENV_DIR}/bin/activate"
else
    log "ERROR" "Virtual environment not found at ${VENV_DIR}"
    exit 1
fi

# Verify Python is available
if ! command -v python3 &> /dev/null; then
    log "ERROR" "python3 not found in PATH after venv activation"
    exit 1
fi

log "INFO" "Python: $(python3 --version)"
log "INFO" "Working directory: $(pwd)"

# Step 1: Discover new sessions
log "INFO" "------------------------------------------"
log "INFO" "Step 1: Discovering new sessions from Uneekor portal"
log "INFO" "------------------------------------------"

if python3 automation_runner.py discover --headless 2>&1 | tee -a "$LOG_FILE"; then
    log "INFO" "Session discovery completed successfully"
else
    log "WARN" "Session discovery encountered issues (continuing anyway)"
fi

# Step 2: Scrape dates for sessions missing them
log "INFO" "------------------------------------------"
log "INFO" "Step 2: Scraping dates for sessions (max $MAX_SCRAPE_SESSIONS)"
log "INFO" "------------------------------------------"

if python3 automation_runner.py reclassify-dates --scrape --max $MAX_SCRAPE_SESSIONS 2>&1 | tee -a "$LOG_FILE"; then
    log "INFO" "Date scraping completed successfully"
else
    log "WARN" "Date scraping encountered issues (continuing anyway)"
fi

# Step 3: Backfill dates to shots table
log "INFO" "------------------------------------------"
log "INFO" "Step 3: Backfilling dates to shots table"
log "INFO" "------------------------------------------"

if python3 automation_runner.py reclassify-dates --backfill 2>&1 | tee -a "$LOG_FILE"; then
    log "INFO" "Date backfill completed successfully"
else
    log "WARN" "Date backfill encountered issues"
fi

# Deactivate virtual environment
deactivate 2>/dev/null || true

log "INFO" "=========================================="
log "INFO" "GolfDataApp daily automation completed"
log "INFO" "=========================================="

exit 0
