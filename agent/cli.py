"""Golf Agent CLI — terminal chat interface.

Provides both interactive chat and one-shot query modes.

Usage:
    # Interactive chat (default)
    python3 -m agent.cli

    # One-shot question
    python3 -m agent.cli --single "How is my driver trending?"
    python3 -m agent.cli -s "Summarize my last session"
"""
from __future__ import annotations

import argparse
import asyncio

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
)

from agent.core import create_golf_agent_options, single_query


# ---------------------------------------------------------------------------
# Interactive chat
# ---------------------------------------------------------------------------


async def interactive_chat() -> None:
    """Run an interactive chat loop with the golf agent.

    Reads user input from stdin, sends it to the Claude SDK client,
    and prints assistant text responses.  Exits on quit/exit/q,
    EOFError (Ctrl-D), or KeyboardInterrupt (Ctrl-C).
    """
    options = create_golf_agent_options()

    print("Golf Agent (type 'quit', 'exit', or 'q' to stop)")
    print("-" * 50)

    async with ClaudeSDKClient(options=options) as client:
        while True:
            # Read user input
            try:
                user_input = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break

            if not user_input:
                continue

            if user_input.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            # Send to agent and collect response
            await client.query(user_input)

            parts: list[str] = []
            async for message in client.receive_response():
                if isinstance(message, (AssistantMessage, ResultMessage)):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            parts.append(block.text)

            if parts:
                print(f"\nCoach: {''.join(parts)}")
            else:
                print("\nCoach: (no response)")


# ---------------------------------------------------------------------------
# One-shot mode
# ---------------------------------------------------------------------------


async def one_shot(question: str) -> None:
    """Send a single question and print the response."""
    response = await single_query(question)
    print(response)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse arguments and dispatch to the appropriate mode."""
    parser = argparse.ArgumentParser(
        prog="golf-agent",
        description="Golf performance coach powered by Claude and your Uneekor data.",
    )
    parser.add_argument(
        "--single",
        "-s",
        type=str,
        default=None,
        help="Ask a single question (non-interactive mode).",
    )

    args = parser.parse_args()

    if args.single:
        asyncio.run(one_shot(args.single))
    else:
        asyncio.run(interactive_chat())


if __name__ == "__main__":
    main()
