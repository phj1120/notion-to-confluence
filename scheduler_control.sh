#!/bin/bash
# Notion to Confluence Migration Scheduler Control Script

PLIST_PATH="$HOME/Library/LaunchAgents/com.notion.confluence.migration.plist"
JOB_LABEL="com.notion.confluence.migration"

case "$1" in
    start)
        echo "Starting migration scheduler..."
        launchctl load "$PLIST_PATH"
        echo "Scheduler started."
        ;;
    stop)
        echo "Stopping migration scheduler..."
        launchctl unload "$PLIST_PATH"
        echo "Scheduler stopped."
        ;;
    restart)
        echo "Restarting migration scheduler..."
        launchctl unload "$PLIST_PATH" 2>/dev/null
        launchctl load "$PLIST_PATH"
        echo "Scheduler restarted."
        ;;
    status)
        echo "Checking migration scheduler status..."
        if launchctl list | grep -q "$JOB_LABEL"; then
            echo "✓ Scheduler is running"
            launchctl list | grep "$JOB_LABEL"
        else
            echo "✗ Scheduler is not running"
        fi
        ;;
    logs)
        echo "=== Migration Logs (last 50 lines) ==="
        tail -50 logs/migration.log 2>/dev/null || echo "No logs yet"
        echo ""
        echo "=== Error Logs (last 20 lines) ==="
        tail -20 logs/migration.error.log 2>/dev/null || echo "No errors yet"
        ;;
    run-now)
        echo "Running migration manually..."
        python3 migrate.py
        ;;
    *)
        echo "Notion to Confluence Migration Scheduler Control"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs|run-now}"
        echo ""
        echo "Commands:"
        echo "  start    - Start the scheduler"
        echo "  stop     - Stop the scheduler"
        echo "  restart  - Restart the scheduler"
        echo "  status   - Check if scheduler is running"
        echo "  logs     - View recent migration logs"
        echo "  run-now  - Run migration manually (immediately)"
        exit 1
        ;;
esac

exit 0
