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


def build_codex_toml(repo_root: Path):
    return "\n".join([
        "[mcp_servers.supabase-golf-data]",
        "command = \"bash\"",
        "args = [\"scripts/start_mcp_supabase.sh\"]",
        f"cwd = \"{repo_root}\"",
        "# Requires SUPABASE_DB_URI in environment",
        "",
    ])


def main():
    repo_root = Path(__file__).resolve().parents[1]
    output_path = repo_root / "mcp" / "claude_desktop_config.supabase.generated.json"
    codex_output_path = repo_root / "mcp" / "codex_config.supabase.generated.toml"

    db_uri = os.getenv("SUPABASE_DB_URI")
    if not db_uri:
        placeholder = "postgresql://postgres.[YOUR_REF]:[YOUR_PASSWORD]@[POOLER_HOST]:6543/postgres"
        config = build_config(placeholder)
        output_path.write_text(json.dumps(config, indent=2))
        codex_output_path.write_text(build_codex_toml(repo_root))
        print("SUPABASE_DB_URI not set; wrote template config.")
        print(f"Update {output_path} with your connection string.")
        print(f"Codex snippet written to {codex_output_path}.")
        return

    config = build_config(db_uri)
    output_path.write_text(json.dumps(config, indent=2))
    codex_output_path.write_text(build_codex_toml(repo_root))
    print(f"Wrote MCP config to {output_path}")
    print(f"Wrote Codex MCP snippet to {codex_output_path}")


if __name__ == "__main__":
    main()
