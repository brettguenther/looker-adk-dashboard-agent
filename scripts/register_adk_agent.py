"""Register or patch the Looker Dashboard ADK Reasoning Engine in Gemini Enterprise (Agentspace)."""

import argparse
import json
import logging
import os
import subprocess
import sys
import google.auth
from google.auth.transport.requests import Request
import requests
from dotenv import load_dotenv

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from scripts.constants import DISCOVERY_ENGINE_BASE_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_project_number(project_id: str) -> str:
    """Retrieves the numerical Google Cloud project number."""
    try:
        res = subprocess.run(
            ["gcloud", "projects", "describe", project_id, "--format=value(projectNumber)"],
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception as e:
        logger.warning("Could not fetch project number for %s: %s. Using project_id.", project_id, e)
        return project_id


def main():
    parser = argparse.ArgumentParser(description="Register/Patch Looker Dashboard ADK Agent in Gemini Enterprise")
    parser.add_argument("--action", choices=["create", "patch"], default="create", help="Register new (create) or update existing (patch)")
    parser.add_argument("--auth-id", default=os.getenv("AUTH_ID", "looker-oauth"), help="Authorization ID")
    parser.add_argument("--engine-id", default=os.getenv("GE_ENGINE_ID", "default_engine"), help="Agentspace Engine ID")
    parser.add_argument("--agent-id", default=os.getenv("AGENT_ID", "looker-dashboard-agent"), help="Agent resource ID")
    parser.add_argument("--display-name", default=os.getenv("AGENT_DISPLAY_NAME", "Looker Dashboard Architect"), help="User-facing display name")
    parser.add_argument("--icon-uri", default=os.getenv("AGENT_ICON_URI"), help="Icon image URI")
    parser.add_argument("--reasoning-engine-id", default=os.getenv("REASONING_ENGINE_ID"), help="Reasoning Engine resource name (projects/.../locations/.../reasoningEngines/...)")
    parser.add_argument("--project-id", default=os.getenv("GOOGLE_CLOUD_PROJECT"), help="GCP project ID")
    args = parser.parse_args()

    if not args.reasoning_engine_id:
        print("Error: Missing Reasoning Engine ID. Set REASONING_ENGINE_ID in .env or pass --reasoning-engine-id.")
        return
    if not args.project_id:
        print("Error: Missing GCP Project ID. Set GOOGLE_CLOUD_PROJECT in .env or pass --project-id.")
        return

    logger.info("Fetching GCP Application Default Credentials...")
    credentials, project_id = google.auth.default()
    credentials.refresh(Request())
    access_token = credentials.token
    target_project = args.project_id or project_id

    # Extract or resolve project number
    project_number = None
    if args.reasoning_engine_id.startswith("projects/"):
        parts = args.reasoning_engine_id.split("/")
        if len(parts) > 1 and parts[1].isdigit():
            project_number = parts[1]

    if not project_number:
        project_number = get_project_number(target_project)

    payload = {
        "displayName": args.display_name,
        "description": "Autonomous Looker LookML Dashboard Architect Agent for designing, verifying, and deploying interactive dashboards.",
        "authorizationConfig": {
            "agentAuthorization": f"projects/{project_number}/locations/global/authorizations/{args.auth_id}",
            "toolAuthorizations": [
                f"projects/{project_number}/locations/global/authorizations/{args.auth_id}"
            ],
        },
        "adkAgentDefinition": {
            "provisionedReasoningEngine": {
                "reasoningEngine": args.reasoning_engine_id
            }
        },
    }

    if args.icon_uri:
        payload["icon"] = {"uri": args.icon_uri}

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": target_project,
    }

    base_url = f"{DISCOVERY_ENGINE_BASE_URL}/{project_number}/locations/global/collections/default_collection/engines/{args.engine_id}/assistants/default_assistant/agents"

    if args.action == "create":
        url = f"{base_url}?agentId={args.agent_id}"
        logger.info("Creating agent in Gemini Enterprise: %s", url)
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
    else:
        payload["name"] = f"projects/{project_number}/locations/global/collections/default_collection/engines/{args.engine_id}/assistants/default_assistant/agents/{args.agent_id}"
        mask_fields = ["adkAgentDefinition", "authorizationConfig", "displayName"]
        if args.icon_uri:
            mask_fields.append("icon")
        update_mask = ",".join(mask_fields)
        url = f"{base_url}/{args.agent_id}?updateMask={update_mask}"
        logger.info("Patching agent in Gemini Enterprise: %s", url)
        resp = requests.patch(url, headers=headers, json=payload, timeout=30)

    if resp.status_code >= 400:
        logger.error("Gemini Enterprise registration failed (%d): %s", resp.status_code, resp.text)
        resp.raise_for_status()

    print("\n" + "=" * 80)
    print(f"AGENT '{args.agent_id}' {args.action.upper()}D IN GEMINI ENTERPRISE SUCCESSFULLY!")
    print(json.dumps(resp.json(), indent=2))
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
