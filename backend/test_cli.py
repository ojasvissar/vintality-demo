"""Interactive CLI for testing the Vintality agent.

Run: python -m test_cli

This lets you chat with the agent in your terminal and see
exactly what tools are being called — perfect for debugging
and for demo screen recordings.
"""

import sys
import os
import json

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from app.agent.orchestrator import run_agent


EXAMPLE_QUERIES = [
    "Is it safe to irrigate Block 5 today?",
    "Why is PM risk spiking on my Cab Franc blocks?",
    "Which blocks need attention most urgently?",
    "What's the soil moisture trend for B5 over the last week?",
    "Compare disease risk across all my blocks",
    "Is there a spray window in the next 24 hours?",
    "Check the canopy environment in Block B9 — something seems off",
    "How do I calibrate a soil moisture sensor in clay soil?",
]


def print_colored(text: str, color: str):
    colors = {
        "green": "\033[92m",
        "blue": "\033[94m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "cyan": "\033[96m",
        "bold": "\033[1m",
        "end": "\033[0m",
    }
    print(f"{colors.get(color, '')}{text}{colors['end']}")


def main():
    print_colored("\n╔══════════════════════════════════════════╗", "cyan")
    print_colored("║   Vintality AI — Agronomic Advisor CLI   ║", "cyan")
    print_colored("╚══════════════════════════════════════════╝\n", "cyan")

    print_colored("Example queries to try:", "yellow")
    for i, q in enumerate(EXAMPLE_QUERIES, 1):
        print(f"  {i}. {q}")

    print_colored("\nType a question, a number (1-8) for an example, or 'quit' to exit.\n", "yellow")

    conversation_history = []

    while True:
        try:
            user_input = input("\033[92m🍇 You: \033[0m").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print_colored("Goodbye!", "cyan")
            break

        # Allow selecting example queries by number
        if user_input.isdigit() and 1 <= int(user_input) <= len(EXAMPLE_QUERIES):
            user_input = EXAMPLE_QUERIES[int(user_input) - 1]
            print_colored(f"  → {user_input}", "green")

        print_colored("\n⏳ Thinking...", "yellow")

        try:
            result = run_agent(
                user_message=user_input,
                conversation_history=conversation_history,
            )

            # Show tool calls
            if result["tool_calls"]:
                print_colored("\n🔧 Tools called:", "blue")
                for tc in result["tool_calls"]:
                    status = "✓" if tc["success"] else "✗"
                    print_colored(
                        f"   {status} {tc['tool']}({json.dumps(tc['input'])})",
                        "blue" if tc["success"] else "red"
                    )

            # Show response
            print_colored(f"\n🤖 Agent:\n", "cyan")
            print(result["response"])

            # Show validation results
            if "validation" in result:
                v = result["validation"]
                conf_pct = f"{v['confidence']:.0%}"
                if v["is_valid"]:
                    print_colored(f"\n✅ Validation: {conf_pct} grounded", "green")
                else:
                    print_colored(f"\n⚠️  Validation: {conf_pct} grounded", "yellow")
                    for fc in v["flagged_claims"]:
                        print_colored(f"   Flagged: {fc['claim']} — {fc['reason']}", "yellow")

            print()

            # Update conversation history for multi-turn
            conversation_history = result["messages"]

        except Exception as e:
            print_colored(f"\n❌ Error: {e}", "red")
            import traceback
            traceback.print_exc()
            print()


if __name__ == "__main__":
    main()
