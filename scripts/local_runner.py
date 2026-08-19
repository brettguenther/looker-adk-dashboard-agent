"""Local interactive test runner for Looker Dashboard Architect Agent."""

import asyncio
import json
import os
import sys
import webbrowser
from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
from google.genai import types

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from app.agent import root_agent
from app.auth import get_looker_cli_profile, resolve_looker_base_url


async def run_prompt_async(prompt: str, open_preview: bool = True):
    print("\n" + "=" * 80)
    print("🚀 RUNNING LOOKER DASHBOARD ARCHITECT AGENT LOCALLY")
    print(f"Target Instance: {resolve_looker_base_url()}")
    print(f"User Prompt: {prompt}")
    print("=" * 80 + "\n")

    runner = InMemoryRunner(agent=root_agent)
    session_id = "test-session-001"
    user_id = "local-developer"

    # Initialize local in-memory session
    await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
    )

    message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=prompt)],
    )

    detected_embed_url = None
    detected_dashboard_id = None

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=message,
    ):
        # 1. Check for tool calls or tool responses in parts
        if event.content and event.content.parts:
            for part in event.content.parts:
                fn_call = getattr(part, "function_call", None)
                fn_resp = getattr(part, "function_response", None)
                text = getattr(part, "text", None)

                if fn_call:
                    print(f"\n⚙️ [Tool Call] {fn_call.name}(args={json.dumps(fn_call.args)[:120]}...)")
                elif fn_resp:
                    print(f"📥 [Tool Response] {fn_resp.name} completed.")
                    resp_dict = getattr(fn_resp, "response", {})
                    if isinstance(resp_dict, dict) and "embed_url" in resp_dict:
                        detected_embed_url = resp_dict.get("embed_url")
                        detected_dashboard_id = resp_dict.get("a2ui_payload", {}).get("updateDataModel", {}).get("data", {}).get("dashboard_id")
                elif text:
                    print(text, end="", flush=True)

        # 2. Check for ADK EventActions UI widgets
        if event.actions and event.actions.render_ui_widgets:
            for widget in event.actions.render_ui_widgets:
                print("\n" + "-" * 80)
                print(f"🎨 [A2UI / UiWidget Emitted] Provider: {widget.provider}, ID: {widget.id}")
                if widget.payload:
                    print(f"   Resource URI: {widget.payload.get('resource_uri')}")
                    print(f"   Looker URL: {widget.payload.get('looker_url')}")
                    detected_embed_url = widget.payload.get("resource_uri") or widget.payload.get("url")
                print("-" * 80 + "\n")

    print("\n\n" + "=" * 80)
    print("✅ Completed Agent Run.")
    print("=" * 80)

    if detected_embed_url and open_preview:
        print("\n🖼️ Live Dashboard Embed Detected!")
        print(f"   Embed URL: {detected_embed_url}")
        print("\n💡 You can preview the live rendered iframe locally using:")
        if detected_dashboard_id:
            print(f"   make preview DASHBOARD_ID={detected_dashboard_id}")
        else:
            print(f"   make preview")


def main():
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = "Discover models, inspect thelook_ecomm order_items explore, and generate an executive summary dashboard."

    asyncio.run(run_prompt_async(prompt))


if __name__ == "__main__":
    main()
