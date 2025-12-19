#!/bin/bash
# Setup script for automated golf data syncing

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "======================================================================"
echo "            Golf Data Pipeline - Automation Setup"
echo "======================================================================"
echo ""
echo "This script will help you set up automated data syncing."
echo ""
echo "Current directory: $SCRIPT_DIR"
echo ""

# Create logs directory
mkdir -p "$SCRIPT_DIR/logs"
echo "✅ Created logs directory"

# Make scripts executable
chmod +x "$SCRIPT_DIR/auto_sync.py"
chmod +x "$SCRIPT_DIR/post_session.py"
chmod +x "$SCRIPT_DIR/gemini_analysis.py"
chmod +x "$SCRIPT_DIR/supabase_to_bigquery.py"
echo "✅ Made scripts executable"

# Show cron job options
echo ""
echo "======================================================================"
echo "                    Automation Options"
echo "======================================================================"
echo ""
echo "Option 1: HOURLY SYNC (Recommended)"
echo "  Syncs new data from Supabase to BigQuery every hour"
echo "  Cron schedule: 0 * * * *"
echo ""
echo "Option 2: DAILY SYNC WITH ANALYSIS"
echo "  Syncs and analyzes data once per day (evening)"
echo "  Cron schedule: 0 20 * * *  (8 PM daily)"
echo ""
echo "Option 3: MANUAL ONLY"
echo "  No automatic syncing, run manually after sessions"
echo ""

read -p "Select option (1/2/3): " option

case $option in
  1)
    CRON_SCHEDULE="0 * * * *"
    COMMAND="cd $SCRIPT_DIR && python auto_sync.py >> logs/sync.log 2>&1"
    ;;
  2)
    CRON_SCHEDULE="0 20 * * *"
    COMMAND="cd $SCRIPT_DIR && python auto_sync.py --analyze >> logs/sync.log 2>&1"
    ;;
  3)
    echo ""
    echo "✅ Manual mode selected. No cron job will be created."
    echo ""
    echo "To sync manually, run:"
    echo "  python post_session.py"
    echo ""
    exit 0
    ;;
  *)
    echo "Invalid option. Exiting."
    exit 1
    ;;
esac

echo ""
echo "======================================================================"
echo "                    Cron Job Configuration"
echo "======================================================================"
echo ""
echo "The following cron job will be added:"
echo ""
echo "  Schedule: $CRON_SCHEDULE"
echo "  Command: $COMMAND"
echo ""
echo "This will be added to your crontab."
echo ""

read -p "Continue? (y/n): " confirm

if [[ $confirm != "y" && $confirm != "Y" ]]; then
    echo "Setup cancelled."
    exit 0
fi

# Add to crontab
(crontab -l 2>/dev/null; echo "$CRON_SCHEDULE $COMMAND") | crontab -

echo ""
echo "✅ Cron job installed successfully!"
echo ""
echo "======================================================================"
echo "                    Setup Complete!"
echo "======================================================================"
echo ""
echo "Your automated sync is now configured."
echo ""
echo "Useful commands:"
echo "  • View cron jobs:        crontab -l"
echo "  • Edit cron jobs:        crontab -e"
echo "  • Remove cron job:       crontab -e  (then delete the line)"
echo "  • View sync logs:        tail -f $SCRIPT_DIR/logs/sync.log"
echo "  • Manual sync:           python post_session.py"
echo ""
echo "First sync will run according to the schedule."
echo "You can also run manually: python auto_sync.py"
echo ""
