import json
import os
from pathlib import Path
from dotenv import load_dotenv


load_dotenv()


def build_config(db_uri: str):
    return {
        "mcpServers": {
            "supabase-golf-data": {
                "command": "npx",
                "args": [
                    "-y",
                    "@modelcontextprotocol/server-postgres",
                    db_uri,
                ],
            }
        }
    }


def main():
    repo_root = Path(__file__).resolve().parents[1]
    output_path = repo_root / "mcp" / "claude_desktop_config.supabase.generated.json"

    db_uri = os.getenv("SUPABASE_DB_URI")
    if not db_uri:
        placeholder = "postgresql://postgres.[YOUR_REF]:[YOUR_PASSWORD]@[POOLER_HOST]:6543/postgres"
        config = build_config(placeholder)
        output_path.write_text(json.dumps(config, indent=2))
        print("SUPABASE_DB_URI not set; wrote template config.")
        print(f"Update {output_path} with your connection string.")
        return

    config = build_config(db_uri)
    output_path.write_text(json.dumps(config, indent=2))
    print(f"Wrote MCP config to {output_path}")


if __name__ == "__main__":
    main()
