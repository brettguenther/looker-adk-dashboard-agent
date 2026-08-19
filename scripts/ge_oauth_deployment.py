"""Register Gemini Enterprise OAuth authorization configuration for Looker."""

import argparse
import json
import logging
import os
import sys
import urllib.parse
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


def main():
    parser = argparse.ArgumentParser(description="Configure Gemini Enterprise OAuth Authorization for Looker")
    parser.add_argument("--project-id", default=os.getenv("GOOGLE_CLOUD_PROJECT"), help="GCP Project ID")
    parser.add_argument("--auth-id", default=os.getenv("AUTH_ID", "looker-oauth"), help="Authorization ID")
    parser.add_argument("--client-id", default=os.getenv("LOOKER_OAUTH_CLIENT_ID"), help="Looker OAuth Client ID")
    parser.add_argument("--client-secret", default=os.getenv("LOOKER_OAUTH_CLIENT_SECRET", "LOOKER_DOES_NOT_USE_SECRET_IN_THIS_FLOW"), help="Looker OAuth Client Secret")
    parser.add_argument("--instance-url", default=os.getenv("LOOKERSDK_BASE_URL"), help="Looker instance URL")
    parser.add_argument("--scopes", default=os.getenv("SCOPES", "cors_api"), help="OAuth scopes")
    args = parser.parse_args()

    if not args.project_id:
        print("Error: Missing GCP Project ID. Set GOOGLE_CLOUD_PROJECT or pass --project-id.")
        return
    if not args.client_id:
        print("Error: Missing Looker Client ID. Set LOOKER_OAUTH_CLIENT_ID or pass --client-id.")
        return
    if not args.instance_url:
        print("Error: Missing Looker instance URL. Set LOOKERSDK_BASE_URL or pass --instance-url.")
        return

    instance_url = args.instance_url.rstrip("/")
    scopes_encoded = urllib.parse.quote(args.scopes)
    authorization_uri = f"{instance_url}/auth?client_id={args.client_id}&scope={scopes_encoded}&response_type=code&code_challenge_method=S256"
    token_uri = f"{instance_url}/api/token"

    logger.info("Fetching GCP Application Default Credentials...")
    credentials, _ = google.auth.default()
    credentials.refresh(Request())
    access_token = credentials.token

    url = f"{DISCOVERY_ENGINE_BASE_URL}/{args.project_id}/locations/global/authorizations?authorizationId={args.auth_id}"
    patch_url = f"{DISCOVERY_ENGINE_BASE_URL}/{args.project_id}/locations/global/authorizations/{args.auth_id}?updateMask=serverSideOauth2"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": args.project_id,
    }

    payload = {
        "name": f"projects/{args.project_id}/locations/global/authorizations/{args.auth_id}",
        "serverSideOauth2": {
            "clientId": args.client_id,
            "clientSecret": args.client_secret,
            "authorizationUri": authorization_uri,
            "tokenUri": token_uri,
            "pkce_verification_enabled": True,
        },
    }

    logger.info("Registering/Updating OAuth config '%s' in Discovery Engine project '%s'...", args.auth_id, args.project_id)
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    if response.status_code == 409:
        logger.info("Authorization '%s' already exists in Discovery Engine. Updating via PATCH...", args.auth_id)
        patch_response = requests.patch(patch_url, headers=headers, json=payload, timeout=30)
        if patch_response.status_code >= 400:
            logger.error("Failed to patch Discovery Engine authorization (%d): %s", patch_response.status_code, patch_response.text)
            patch_response.raise_for_status()
        print("\n" + "=" * 80)
        print(f"OAUTH AUTHORIZATION '{args.auth_id}' SUCCESSFULLY UPDATED IN DISCOVERY ENGINE!")
        print(json.dumps(patch_response.json(), indent=2))
        print("=" * 80 + "\n")
        return

    print("\n" + "=" * 80)
    print("GEMINI ENTERPRISE OAUTH AUTHORIZATION REGISTERED!")
    print(json.dumps(response.json(), indent=2))
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
