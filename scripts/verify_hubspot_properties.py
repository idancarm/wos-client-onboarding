#!/usr/bin/env python3
"""
Verify and create WOS HubSpot properties.

Checks that all 15 required WOS properties exist on Contact (12) and Company (3)
objects, grouped under the "envy_agent" property group. Optionally creates any
missing properties (and the group itself) via the HubSpot API.

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

# ── Property group ──────────────────────────────────────────────────────────

GROUP_NAME = "envy_agent"
GROUP_LABEL = "Envy Agent"

# ── Property definitions ────────────────────────────────────────────────────

OUTREACH_STAGE_OPTIONS = [
    {"value": "Invitation Scheduled", "label": "Invitation Scheduled"},
    {"value": "Invitation Sent", "label": "Invitation Sent"},
    {"value": "Connected", "label": "Connected"},
    {"value": "Sequence In Progress", "label": "Sequence In Progress"},
    {"value": "Sequence Finished", "label": "Sequence Finished"},
    {"value": "Replied", "label": "Replied"},
    {"value": "Do Not Contact", "label": "Do Not Contact"},
]

SEQUENCE_STATUS_OPTIONS = [
    {"value": "In Progress", "label": "In Progress"},
    {"value": "Finished", "label": "Finished"},
    {"value": "Stopped (Replied)", "label": "Stopped (Replied)"},
]

CONTACT_PROPERTIES = [
    {
        "name": "wos_outreach_stage",
        "type": "enumeration",
        "fieldType": "select",
        "label": "WOS Outreach Stage",
        "description": "Master status of the lead in the outreach flow",
        "groupName": GROUP_NAME,
        "options": OUTREACH_STAGE_OPTIONS,
    },
    {
        "name": "wos_sequence_status",
        "type": "enumeration",
        "fieldType": "select",
        "label": "WOS Sequence Status",
        "description": "Status of the message sequence sent by WOS agent",
        "groupName": GROUP_NAME,
        "options": SEQUENCE_STATUS_OPTIONS,
    },
    {
        "name": "wos_sequence_name",
        "type": "string",
        "fieldType": "text",
        "label": "WOS Sequence Name",
        "description": "The name of the LinkedIn sequence that the agent manages",
        "groupName": GROUP_NAME,
    },
    {
        "name": "wos_sequence_start_date",
        "type": "datetime",
        "fieldType": "date",
        "label": "WOS Sequence Start Date",
        "description": "When the sequence was triggered",
        "groupName": GROUP_NAME,
    },
    {
        "name": "wos_user_id",
        "type": "string",
        "fieldType": "text",
        "label": "WOS User ID",
        "description": "HubSpot user ID of the operator running outreach for this contact",
        "groupName": GROUP_NAME,
    },
    {
        "name": "wos_last_interaction_date",
        "type": "datetime",
        "fieldType": "date",
        "label": "WOS Last Interaction Date",
        "description": "Timestamp when the WOS agent last interacted with the lead",
        "groupName": GROUP_NAME,
    },
    {
        "name": "wos_linkedin_url",
        "type": "string",
        "fieldType": "text",
        "label": "WOS LinkedIn URL",
        "description": "Full URL of the lead's LinkedIn profile",
        "groupName": GROUP_NAME,
    },
    {
        "name": "wos_linkedin_id",
        "type": "string",
        "fieldType": "text",
        "label": "WOS LinkedIn ID",
        "description": "LinkedIn member ID of the lead",
        "groupName": GROUP_NAME,
    },
    {
        "name": "wos_linkedin_connection_status",
        "type": "string",
        "fieldType": "text",
        "label": "WOS LinkedIn Connection Status",
        "description": "Current LinkedIn connection status with the lead",
        "groupName": GROUP_NAME,
    },
    {
        "name": "wos_connection_accepted_date",
        "type": "datetime",
        "fieldType": "date",
        "label": "WOS Connection Accepted Date",
        "description": "Date when the LinkedIn connection invitation was accepted",
        "groupName": GROUP_NAME,
    },
    {
        "name": "wos_scheduled_invitation_date",
        "type": "datetime",
        "fieldType": "date",
        "label": "WOS Scheduled Invitation Date",
        "description": "Date when the LinkedIn invitation is scheduled to be sent",
        "groupName": GROUP_NAME,
    },
    {
        "name": "wos_last_date_work_email_enriched",
        "type": "datetime",
        "fieldType": "date",
        "label": "WOS Last Date Work Email Enriched",
        "description": "Date when the contact's work email was last enriched",
        "groupName": GROUP_NAME,
    },
]

COMPANY_PROPERTIES = [
    {
        "name": "wos_process_company",
        "type": "datetime",
        "fieldType": "date",
        "label": "WOS Initiate LI Agent",
        "description": "Setting this fires the n8n webhook to process the company",
        "groupName": GROUP_NAME,
    },
    {
        "name": "wos_persona",
        "type": "string",
        "fieldType": "text",
        "label": "WOS Persona",
        "description": "Identifier for the search persona the LI agent will use",
        "groupName": GROUP_NAME,
    },
    {
        "name": "wos_user_id",
        "type": "string",
        "fieldType": "text",
        "label": "WOS User ID",
        "description": "HubSpot user ID of the operator handling this company",
        "groupName": GROUP_NAME,
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


def ensure_property_group(token: str, object_type: str) -> bool:
    """Create the envy_agent property group on *object_type*. 409 means it exists."""
    url = f"{BASE_URL}/{object_type}/groups"
    payload = {"name": GROUP_NAME, "label": GROUP_LABEL}
    resp = requests.post(url, headers=get_headers(token), json=payload, timeout=30)
    if resp.status_code in (200, 201):
        print(f"  Group '{GROUP_NAME}' created on {object_type}")
        return True
    if resp.status_code == 409:
        return True
    print(f"  ERROR creating group on {object_type}: {resp.status_code} {resp.text}")
    return False


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

        missing = [p for p in specs if p["name"] not in existing]
        if do_create and missing:
            ensure_property_group(token, object_type)

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

    total = sum(len(specs) for specs in PROPERTY_SPECS.values())
    print(f"\n{'─' * 50}")
    if ok:
        print(f"  All {total} WOS properties are present. ✓")
    elif not args.create:
        print("  Some properties are missing. Re-run with --create to fix.")
    else:
        print("  Some properties could not be created. Check errors above.")
    print()

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
