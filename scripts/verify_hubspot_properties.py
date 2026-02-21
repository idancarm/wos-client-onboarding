#!/usr/bin/env python3
"""
Verify and create WOS HubSpot properties.

Checks that all 14 required WOS properties exist on Contact (11) and Company (3)
objects. Optionally creates any missing properties via the HubSpot API.

Usage:
    # Verify only (dry run)
    python scripts/verify_hubspot_properties.py --token "pat-xxx"

    # Verify + create missing
    python scripts/verify_hubspot_properties.py --token "pat-xxx" --create

    # Using env var instead of --token
    HUBSPOT_TOKEN="pat-xxx" python scripts/verify_hubspot_properties.py
"""

import argparse
import os
import sys

import requests

BASE_URL = "https://api.hubapi.com/crm/v3/properties"

# ── Property definitions ────────────────────────────────────────────────────

CONTACT_PROPERTIES = [
    {
        "name": "wos_outreach_stage",
        "type": "string",
        "fieldType": "text",
        "label": "WOS Outreach Stage",
        "groupName": "contactinformation",
    },
    {
        "name": "wos_sequence_status",
        "type": "string",
        "fieldType": "text",
        "label": "WOS Sequence Status",
        "groupName": "contactinformation",
    },
    {
        "name": "wos_sequence_name",
        "type": "string",
        "fieldType": "text",
        "label": "WOS Sequence Name",
        "groupName": "contactinformation",
    },
    {
        "name": "wos_sequence_start_date",
        "type": "datetime",
        "fieldType": "date",
        "label": "WOS Sequence Start Date",
        "groupName": "contactinformation",
    },
    {
        "name": "wos_user_id",
        "type": "string",
        "fieldType": "text",
        "label": "WOS User ID",
        "groupName": "contactinformation",
    },
    {
        "name": "wos_last_interaction_date",
        "type": "datetime",
        "fieldType": "date",
        "label": "WOS Last Interaction Date",
        "groupName": "contactinformation",
    },
    {
        "name": "wos_linkedin_url",
        "type": "string",
        "fieldType": "text",
        "label": "WOS LinkedIn URL",
        "groupName": "contactinformation",
    },
    {
        "name": "wos_linkedin_id",
        "type": "string",
        "fieldType": "text",
        "label": "WOS LinkedIn ID",
        "groupName": "contactinformation",
    },
    {
        "name": "wos_linkedin_connection_status",
        "type": "string",
        "fieldType": "text",
        "label": "WOS LinkedIn Connection Status",
        "groupName": "contactinformation",
    },
    {
        "name": "wos_connection_accepted_date",
        "type": "datetime",
        "fieldType": "date",
        "label": "WOS Connection Accepted Date",
        "groupName": "contactinformation",
    },
    {
        "name": "n8n_initiate_li_message",
        "type": "string",
        "fieldType": "text",
        "label": "n8n Initiate LI Message",
        "groupName": "contactinformation",
    },
]

COMPANY_PROPERTIES = [
    {
        "name": "wos_process_company",
        "type": "datetime",
        "fieldType": "date",
        "label": "WOS Initiate LI Agent",
        "groupName": "companyinformation",
    },
    {
        "name": "wos_persona",
        "type": "string",
        "fieldType": "text",
        "label": "WOS Persona",
        "groupName": "companyinformation",
    },
    {
        "name": "wos_user_id",
        "type": "string",
        "fieldType": "text",
        "label": "WOS User ID",
        "groupName": "companyinformation",
    },
]

PROPERTY_SPECS = {
    "contacts": CONTACT_PROPERTIES,
    "companies": COMPANY_PROPERTIES,
}

# ── API helpers ─────────────────────────────────────────────────────────────


def get_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def fetch_existing_properties(token: str, object_type: str) -> set[str]:
    """Return the set of property names that already exist on *object_type*."""
    url = f"{BASE_URL}/{object_type}"
    resp = requests.get(url, headers=get_headers(token), timeout=30)
    resp.raise_for_status()
    return {p["name"] for p in resp.json().get("results", [])}


def create_property(token: str, object_type: str, prop: dict) -> bool:
    """Create a single property. Returns True on success."""
    url = f"{BASE_URL}/{object_type}"
    resp = requests.post(url, headers=get_headers(token), json=prop, timeout=30)
    if resp.status_code in (200, 201):
        return True
    print(f"  ERROR creating {prop['name']}: {resp.status_code} {resp.text}")
    return False


# ── Main logic ──────────────────────────────────────────────────────────────


def verify_and_create(token: str, do_create: bool) -> bool:
    """Verify all WOS properties; optionally create missing ones.

    Returns True if all properties exist (or were successfully created).
    """
    all_ok = True

    for object_type, specs in PROPERTY_SPECS.items():
        label = object_type.capitalize()
        print(f"\n{'─' * 50}")
        print(f"  {label} properties ({len(specs)} required)")
        print(f"{'─' * 50}")

        try:
            existing = fetch_existing_properties(token, object_type)
        except requests.HTTPError as exc:
            print(f"  ERROR fetching {object_type} properties: {exc}")
            all_ok = False
            continue

        for prop in specs:
            name = prop["name"]
            if name in existing:
                print(f"  ✓  {name}")
            else:
                print(f"  ✗  {name}  — MISSING")
                if do_create:
                    print(f"     → Creating {name} …", end=" ")
                    ok = create_property(token, object_type, prop)
                    if ok:
                        print("done")
                    else:
                        all_ok = False
                else:
                    all_ok = False

    return all_ok


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify (and optionally create) WOS HubSpot properties."
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("HUBSPOT_TOKEN"),
        help="HubSpot bearer token (or set HUBSPOT_TOKEN env var)",
    )
    parser.add_argument(
        "--create",
        action="store_true",
        help="Create any missing properties (default: dry-run only)",
    )
    args = parser.parse_args()

    if not args.token:
        parser.error("Provide a token via --token or HUBSPOT_TOKEN env var")

    print("WOS HubSpot Property Verification")
    print(f"Mode: {'CREATE missing' if args.create else 'verify only (dry run)'}")

    ok = verify_and_create(args.token, args.create)

    print(f"\n{'─' * 50}")
    if ok:
        print("  All 14 WOS properties are present. ✓")
    elif not args.create:
        print("  Some properties are missing. Re-run with --create to fix.")
    else:
        print("  Some properties could not be created. Check errors above.")
    print()

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
