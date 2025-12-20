#!/bin/bash
# MCP Setup Script for Golf Data Analysis
# Configures Claude Desktop for database access

set -e

echo "🏌️  Golf Data MCP Setup"
echo "======================="
echo ""

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    CONFIG_DIR="$HOME/Library/Application Support/Claude"
    OS="macOS"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    CONFIG_DIR="$APPDATA/Claude"
    OS="Windows"
else
    echo "❌ Unsupported OS: $OSTYPE"
    exit 1
fi

echo "Detected OS: $OS"
echo "Config location: $CONFIG_DIR"
echo ""

# Check Node.js
echo "Checking prerequisites..."
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found"
    echo "   Install with: brew install node (macOS)"
    exit 1
fi

NODE_VERSION=$(node --version)
echo "✅ Node.js installed: $NODE_VERSION"

# Check Claude Desktop
if [ ! -d "$CONFIG_DIR" ]; then
    echo "⚠️  Claude Desktop config directory not found"
    echo "   Make sure Claude Desktop is installed"
    echo "   Creating directory: $CONFIG_DIR"
    mkdir -p "$CONFIG_DIR"
fi

# Find database location
DB_PATH=""
if [ -f "data/golf_stats.db" ]; then
    DB_PATH="$(pwd)/data/golf_stats.db"
elif [ -f "golf_stats.db" ]; then
    DB_PATH="$(pwd)/golf_stats.db"
else
    echo "⚠️  SQLite database not found at data/golf_stats.db"
    echo "   Run the Streamlit app first to create it"
    DB_PATH="$(pwd)/data/golf_stats.db"
fi

echo "Database path: $DB_PATH"
echo ""

# Create config
CONFIG_FILE="$CONFIG_DIR/claude_desktop_config.json"

echo "Creating MCP configuration..."

cat > "$CONFIG_FILE" <<EOF
{
  "mcpServers": {
    "golf-data-sqlite": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-sqlite",
        "$DB_PATH"
      ]
    }
  }
}
EOF

echo "✅ Configuration created at: $CONFIG_FILE"
echo ""

# Optional: Add Supabase
read -p "Do you want to add Supabase connection? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Enter your Supabase connection string:"
    echo "Format: postgresql://postgres.[ref]:[password]@[host]:6543/postgres"
    read -p "Connection string: " SUPABASE_URI

    if [ ! -z "$SUPABASE_URI" ]; then
        # Add Supabase to config
        cat > "$CONFIG_FILE" <<EOF
{
  "mcpServers": {
    "golf-data-sqlite": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-sqlite",
        "$DB_PATH"
      ]
    },
    "supabase-golf-data": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-postgres",
        "$SUPABASE_URI"
      ]
    }
  }
}
EOF
        echo "✅ Supabase connection added"
    fi
fi

echo ""
echo "🎉 Setup Complete!"
echo ""
echo "Next Steps:"
echo "1. Restart Claude Desktop (completely quit and reopen)"
echo "2. Look for the 🔌 icon in Claude Desktop"
echo "3. You should see 'golf-data-sqlite' connected"
echo ""
echo "Test it:"
echo "  Ask Claude: 'Show me my recent driver sessions'"
echo "  Ask Claude: 'What should I work on today?'"
echo ""
echo "For more info, see: mcp-setup/SETUP_MCP.md"
