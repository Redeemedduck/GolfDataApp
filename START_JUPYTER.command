#!/bin/bash

# Golf Coach AI - Jupyter Notebook Launcher
# Double-click this file to launch the interactive notebook

cd "$(dirname "$0")"

echo "🏌️  Golf Coach AI - Starting Jupyter Notebook..."
echo ""
echo "📓 Opening golf_coach_notebook.ipynb in your browser..."
echo ""
echo "💡 Press Ctrl+C in this window to stop Jupyter when you're done"
echo ""

jupyter notebook golf_coach_notebook.ipynb
