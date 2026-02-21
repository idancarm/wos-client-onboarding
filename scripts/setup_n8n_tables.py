#!/usr/bin/env python3
"""
Print n8n data table specs for WOS client onboarding.

Reads a client config JSON + .env file and prints the exact table names,
columns, and row data needed to create the 3 n8n data tables.

Usage:
    python scripts/setup_n8n_tables.py --prefix ACM
    # Reads configs/ACM-client-config.json + configs/ACM.env
"""

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta

DEFAULT_CONFIGS_DIR = os.path.join(os.path.dirname(__file__), "..", "configs")

# ── Rate-limit defaults ─────────────────────────────────────────────────────

WEEKLY_REMAINING = 150
DAILY_REMAINING = 20

# ── Helpers ─────────────────────────────────────────────────────────────────


def parse_env_file(path: str) -> dict:
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


def next_monday() -> str:
    today = date.today()
    days_ahead = 7 - today.weekday()  # Monday = 0
    if days_ahead == 7:
        days_ahead = 7  # if today is Monday, next Monday
    return (today + timedelta(days=days_ahead)).isoformat()


def tomorrow() -> str:
    return (date.today() + timedelta(days=1)).isoformat()


def print_table(name: str, columns: list[str], rows: list[dict]) -> None:
    """Print a table with name, columns, and rows in a readable format."""
    print(f"\n{'━' * 60}")
    print(f"  TABLE: {name}")
    print(f"{'━' * 60}")
    print(f"  Columns ({len(columns)}): {', '.join(columns)}")
    print(f"  Rows: {len(rows)}")
    print()

    if not rows:
        print("  (no rows)")
        return

    # Calculate column widths
    widths = {col: len(col) for col in columns}
    for row in rows:
        for col in columns:
            val = str(row.get(col, "—"))
            widths[col] = max(widths[col], min(len(val), 40))

    # Header
    header = "  │ ".join(col.ljust(widths[col]) for col in columns)
    sep = "──┼─".join("─" * widths[col] for col in columns)
    print(f"  {header}")
    print(f"  {sep}")

    # Rows
    for row in rows:
        vals = []
        for col in columns:
            val = str(row.get(col, "—"))
            if len(val) > 40:
                val = val[:37] + "..."
            vals.append(val.ljust(widths[col]))
        print(f"  {'  │ '.join(vals)}")


# ── Table generators ────────────────────────────────────────────────────────


def credentials_table(prefix: str, env: dict) -> tuple[str, list[str], list[dict]]:
    name = f"{prefix}-wos-credentials"
    columns = ["service", "api_key", "account_id", "dns", "extra_1", "extra_2"]
    rows = [
        {
            "service": "hubspot",
            "api_key": env.get("HUBSPOT_TOKEN", ""),
            "account_id": "",
            "dns": "",
            "extra_1": "",
            "extra_2": "",
        },
        {
            "service": "unipile",
            "api_key": env.get("UNIPILE_API_KEY", ""),
            "account_id": env.get("UNIPILE_ACCOUNT_ID", ""),
            "dns": env.get("UNIPILE_DNS", ""),
            "extra_1": "",
            "extra_2": "",
        },
        {
            "service": "cargo",
            "api_key": env.get("CARGO_API_KEY", ""),
            "account_id": "",
            "dns": "",
            "extra_1": "",
            "extra_2": "",
        },
    ]
    return name, columns, rows


def personas_table(prefix: str, personas: list[dict]) -> tuple[str, list[str], list[dict]]:
    name = f"{prefix}-wos-personas"
    columns = ["title_keywords", "language", "network_distance", "location", "extra_1", "extra_2"]
    rows = []
    for p in personas:
        rows.append({
            "title_keywords": p["title_keywords"],
            "language": p.get("language", "en"),
            "network_distance": p.get("network_distance", "S"),
            "location": p["location"],
            "extra_1": "",
            "extra_2": "",
        })
    return name, columns, rows


def user_counters_table(prefix: str, operators: list[dict]) -> tuple[str, list[str], list[dict]]:
    name = f"{prefix}-wos-user_counters"
    columns = [
        "user_name", "hubspot_owner_id",
        "weekly_count", "daily_count",
        "weekly_remaining", "daily_remaining",
        "weekly_reset_date", "daily_reset_date",
        "invite_safe_date",
        "extra_1", "extra_2", "extra_3",
    ]
    rows = []
    nm = next_monday()
    tm = tomorrow()
    for op in operators:
        rows.append({
            "user_name": op["name"],
            "hubspot_owner_id": op["hubspot_owner_id"],
            "weekly_count": "0",
            "daily_count": "0",
            "weekly_remaining": str(WEEKLY_REMAINING),
            "daily_remaining": str(DAILY_REMAINING),
            "weekly_reset_date": nm,
            "daily_reset_date": tm,
            "invite_safe_date": "",
            "extra_1": "",
            "extra_2": "",
            "extra_3": "",
        })
    return name, columns, rows


# ── Main ────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print n8n data table specs for a WOS client."
    )
    parser.add_argument(
        "--prefix",
        required=True,
        help="Client prefix (e.g. ACM)",
    )
    parser.add_argument(
        "--configs-dir",
        default=DEFAULT_CONFIGS_DIR,
        help=f"Directory containing config files (default: {DEFAULT_CONFIGS_DIR})",
    )
    args = parser.parse_args()
    prefix = args.prefix.upper()

    config_path = os.path.join(args.configs_dir, f"{prefix}-client-config.json")
    env_path = os.path.join(args.configs_dir, f"{prefix}.env")

    # Load config
    if not os.path.exists(config_path):
        print(f"ERROR: Config file not found: {config_path}")
        print(f"  Run: python scripts/generate_client_config.py")
        sys.exit(1)

    with open(config_path) as f:
        config = json.load(f)

    # Load env
    if not os.path.exists(env_path):
        print(f"ERROR: Env file not found: {env_path}")
        print(f"  Copy configs/.env.example to {env_path} and fill in credentials")
        sys.exit(1)

    env = parse_env_file(env_path)

    # Print header
    print(f"\nn8n Data Table Setup — {config.get('company_name', prefix)}")
    print(f"Prefix: {prefix}")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"\nCreate these 3 tables in the n8n UI, then enter the data below.")

    # Print each table
    for generator in (
        lambda: credentials_table(prefix, env),
        lambda: personas_table(prefix, config.get("personas", [])),
        lambda: user_counters_table(prefix, config.get("operators", [])),
    ):
        name, columns, rows = generator()
        print_table(name, columns, rows)

    print(f"\n{'━' * 60}")
    print(f"  Done. 3 tables, {sum(len(r) for r in [config.get('personas', []), config.get('operators', [])])+3} total rows.")
    print()


if __name__ == "__main__":
    main()
