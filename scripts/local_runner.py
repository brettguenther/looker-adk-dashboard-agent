"""Local interactive test runner for Looker Dashboard Architect Agent."""

import asyncio
import os
import sys
from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
from google.genai import types

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from app.agent import root_agent


async def run_prompt_async(prompt: str):
    print("\n" + "=" * 80)
    print(f"🚀 Running Looker Dashboard Architect Agent...")
    print(f"User Prompt: {prompt}")
    print("=" * 80 + "\n")

    runner = InMemoryRunner(agent=root_agent)
    session_id = "test-session-001"
    user_id = "local-developer"

    message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=prompt)],
    )

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=message,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "text", None):
                    print(part.text, end="", flush=True)

    print("\n\n" + "=" * 80)
    print("✅ Completed Agent Run.")
    print("=" * 80 + "\n")


def main():
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = "List available LookML models, inspect explores in the first model, and summarize what dashboards we can create."

    asyncio.run(run_prompt_async(prompt))


if __name__ == "__main__":
    main()
