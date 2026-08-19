"""Create or update an OAuth Client Application in Looker for Gemini Enterprise integration."""

import argparse
import json
import logging
import os
import sys
import uuid
import requests
from dotenv import load_dotenv

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from app.auth import get_looker_cli_profile, resolve_auth_token, resolve_looker_base_url

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    cli_profile = get_looker_cli_profile(auto_refresh=True)

    default_instance_url = (
        os.getenv("LOOKERSDK_BASE_URL")
        or resolve_looker_base_url()
        or (cli_profile.get("base_url") if cli_profile else None)
    )
    default_token = (
        os.getenv("LOOKER_DEV_TOKEN")
        or os.getenv("LOOKERSDK_ACCESS_TOKEN")
        or resolve_auth_token()
        or (cli_profile.get("access_token") if cli_profile else None)
    )
    default_client_guid = os.getenv("LOOKER_OAUTH_CLIENT_ID") or f"ge-looker-agent-{uuid.uuid4().hex[:8]}"

    parser = argparse.ArgumentParser(description="Create a Looker OAuth Client Application for Gemini Enterprise")
    parser.add_argument("--instance-url", default=default_instance_url, help="Looker instance URL")
    parser.add_argument("--client-id", default=default_client_guid, help="Desired OAuth Client GUID / ID")
    parser.add_argument("--client-name", default=os.getenv("LOOKER_OAUTH_CLIENT_NAME", "Gemini Enterprise Looker Dashboard Agent"))
    parser.add_argument("--redirect-uri", default=os.getenv("LOOKER_OAUTH_REDIRECT_URI", "https://vertexaisearch.cloud.google.com/oauth-redirect"))
    parser.add_argument("--token", default=default_token, help="Admin API access token or dev token")
    args = parser.parse_args()

    if not args.instance_url:
        print("Error: Missing Looker instance URL. Set LOOKERSDK_BASE_URL in .env or pass --instance-url.")
        return

    client_id = os.getenv("LOOKERSDK_CLIENT_ID")
    client_secret = os.getenv("LOOKERSDK_CLIENT_SECRET")
    base_url = args.instance_url.rstrip("/")
    if base_url.endswith("/api/4.0"):
        api_url = base_url
        instance_base = base_url[:-8]
    else:
        api_url = f"{base_url}/api/4.0"
        instance_base = base_url

    # Authenticate via API3 client_id/secret if provided and no Bearer token
    access_token = args.token
    if not access_token and client_id and client_secret:
        logger.info("Authenticating with Looker via API3 credentials at %s/login...", api_url)
        login_resp = requests.post(f"{api_url}/login", data={"client_id": client_id, "client_secret": client_secret}, timeout=30)
        if login_resp.status_code == 200:
            access_token = login_resp.json().get("access_token")

    if not access_token:
        print("Error: Missing Looker access token. Run 'looker-cli session login' or set LOOKER_DEV_TOKEN / API3 credentials in .env.")
        return

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
    }

    payload = {
        "redirect_uri": args.redirect_uri,
        "display_name": args.client_name,
        "description": "OAuth Client for Gemini Enterprise Looker Dashboard Architect Agent",
        "enabled": True,
    }

    client_guid = args.client_id
    register_url = f"{api_url}/oauth_client_apps/{client_guid}"
    logger.info("Registering OAuth client application '%s' with GUID: %s", args.client_name, client_guid)
    logger.info("Target URL: %s", register_url)

    resp = requests.post(register_url, headers=headers, json=payload, timeout=30)
    if resp.status_code == 409:
        # Already exists, update with PUT
        logger.info("Client app '%s' exists. Updating via PUT...", client_guid)
        resp = requests.put(register_url, headers=headers, json=payload, timeout=30)

    if resp.status_code >= 400:
        logger.error("Failed to register OAuth client app (%d): %s", resp.status_code, resp.text)
        resp.raise_for_status()

    data = resp.json()
    registered_guid = data.get("client_guid") or client_guid
    print("\n" + "=" * 80)
    print("LOOKER OAUTH CLIENT CREATED SUCCESSFULLY!")
    print(f"Client GUID (LOOKER_OAUTH_CLIENT_ID): {registered_guid}")
    print(f"Display Name:                         {data.get('display_name')}")
    print(f"Redirect URI:                         {data.get('redirect_uri')}")
    print(f"Looker Instance URL:                  {instance_base}")
    print("-" * 80)
    print("Update your .env file with:")
    print(f"LOOKERSDK_BASE_URL={instance_base}")
    print(f"LOOKER_OAUTH_CLIENT_ID={registered_guid}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
