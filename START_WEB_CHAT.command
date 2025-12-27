#!/bin/bash

# Golf Coach AI - Web Chat Launcher
# Double-click this file to launch the web chat interface

cd "$(dirname "$0")"

echo "🏌️  Golf Coach AI - Starting Web Chat..."
echo ""
echo "🌐 Opening http://localhost:5000 in your browser..."
echo ""
echo "💡 Press Ctrl+C in this window to stop the server when you're done"
echo ""

# Wait a moment then open browser
sleep 3 && open http://localhost:5000 &

python golf_coach_web.py
