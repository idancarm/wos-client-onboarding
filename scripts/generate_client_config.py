#!/usr/bin/env python3
"""
Generate a WOS client configuration file.

Interactively collects non-sensitive onboarding info (company name, prefix,
operators, personas) and writes a JSON config plus a blank .env template
for credentials.

Usage:
    # Interactive mode
    python scripts/generate_client_config.py

    # Validate an existing config + env pair
    python scripts/generate_client_config.py --validate --prefix ACM

    # Custom output directory
    python scripts/generate_client_config.py --output-dir /some/path
"""

import argparse
import json
import os
import re
import sys

DEFAULT_CONFIGS_DIR = os.path.join(os.path.dirname(__file__), "..", "configs")

ENV_KEYS = [
    "HUBSPOT_TOKEN",
    "UNIPILE_API_KEY",
    "UNIPILE_ACCOUNT_ID",
    "UNIPILE_DNS",
    "CARGO_API_KEY",
]

# ── Validation helpers ──────────────────────────────────────────────────────


def validate_prefix(prefix: str) -> list[str]:
    errors = []
    if not re.fullmatch(r"[A-Z]{2,4}", prefix):
        errors.append(f"Prefix must be 2-4 uppercase letters, got: '{prefix}'")
    return errors


def validate_config(config: dict) -> list[str]:
    errors = []

    for field in ("company_name", "prefix"):
        if not config.get(field):
            errors.append(f"Missing required field: {field}")

    if config.get("prefix"):
        errors.extend(validate_prefix(config["prefix"]))

    operators = config.get("operators", [])
    if not operators:
        errors.append("At least one operator is required")
    for i, op in enumerate(operators):
        if not op.get("name"):
            errors.append(f"Operator {i + 1}: missing name")
        owner_id = op.get("hubspot_owner_id", "")
        if not owner_id:
            errors.append(f"Operator {i + 1}: missing hubspot_owner_id")
        elif not str(owner_id).isdigit():
            errors.append(f"Operator {i + 1}: hubspot_owner_id must be numeric, got: '{owner_id}'")

    personas = config.get("personas", [])
    if not personas:
        errors.append("At least one persona is required")
    for i, p in enumerate(personas):
        if not p.get("title_keywords"):
            errors.append(f"Persona {i + 1}: missing title_keywords")
        if not p.get("location"):
            errors.append(f"Persona {i + 1}: missing location")

    return errors


def validate_env(env: dict) -> list[str]:
    errors = []
    for key in ENV_KEYS:
        val = env.get(key, "").strip()
        if not val:
            errors.append(f"Missing or empty credential: {key}")
    return errors


def parse_env_file(path: str) -> dict:
    """Parse a simple KEY=VALUE .env file (ignores comments and blank lines)."""
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


# ── Interactive prompts ─────────────────────────────────────────────────────


def prompt_basic_info() -> tuple[str, str]:
    print("\n── Client Information ──\n")

    company_name = input("Company name (e.g. Acme Corp): ").strip()
    while not company_name:
        company_name = input("  Company name cannot be empty: ").strip()

    prefix = input("Short prefix (2-4 uppercase letters, e.g. ACM): ").strip().upper()
    while validate_prefix(prefix):
        prefix = input("  Must be 2-4 uppercase letters: ").strip().upper()

    return company_name, prefix


def prompt_operators() -> list[dict]:
    print("\n── Operators ──")
    print("  Add operators who will run outreach. Enter a blank name to stop.\n")
    operators = []
    idx = 1
    while True:
        name = input(f"  Operator {idx} name (blank to finish): ").strip()
        if not name:
            if not operators:
                print("  At least one operator is required.")
                continue
            break
        owner_id = input(f"  Operator {idx} HubSpot owner ID: ").strip()
        while not owner_id.isdigit():
            owner_id = input("    Must be numeric: ").strip()
        operators.append({"name": name, "hubspot_owner_id": owner_id})
        idx += 1
    return operators


def prompt_personas() -> list[dict]:
    print("\n── ICP Personas ──")
    print("  Add LinkedIn search personas. Enter blank title_keywords to stop.\n")
    personas = []
    idx = 1
    while True:
        title_keywords = input(f"  Persona {idx} title_keywords (blank to finish): ").strip()
        if not title_keywords:
            if not personas:
                print("  At least one persona is required.")
                continue
            break
        language = input(f"  Persona {idx} language [en]: ").strip() or "en"
        network_distance = input(f"  Persona {idx} network_distance [S]: ").strip() or "S"
        location = input(f"  Persona {idx} location (e.g. United States): ").strip()
        while not location:
            location = input("    Location cannot be empty: ").strip()

        personas.append({
            "title_keywords": title_keywords,
            "language": language,
            "network_distance": network_distance,
            "location": location,
        })
        idx += 1
    return personas


# ── File writers ────────────────────────────────────────────────────────────


def write_config(config: dict, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")
    print(f"\n  ✓  Config written to {path}")


def write_env_template(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("# WOS Client Credentials\n")
        f.write("# Fill in the values below — do not commit this file\n")
        for key in ENV_KEYS:
            f.write(f"{key}=\n")
    print(f"  ✓  Env template written to {path}")
    print("     → Fill in credential values before running setup_n8n_tables.py")


# ── Main logic ──────────────────────────────────────────────────────────────


def run_interactive(output_dir: str) -> None:
    company_name, prefix = prompt_basic_info()
    operators = prompt_operators()
    personas = prompt_personas()

    config = {
        "company_name": company_name,
        "prefix": prefix,
        "operators": operators,
        "personas": personas,
    }

    errors = validate_config(config)
    if errors:
        print("\nValidation errors:")
        for e in errors:
            print(f"  ✗  {e}")
        sys.exit(1)

    config_path = os.path.join(output_dir, f"{prefix}-client-config.json")
    env_path = os.path.join(output_dir, f"{prefix}.env")

    write_config(config, config_path)
    if not os.path.exists(env_path):
        write_env_template(env_path)
    else:
        print(f"  ·  Env file already exists at {env_path} — not overwritten")

    print(f"\nDone. Next steps:")
    print(f"  1. Fill in credentials in {env_path}")
    print(f"  2. Run: python scripts/setup_n8n_tables.py --prefix {prefix}")


def run_validate(prefix: str, configs_dir: str) -> None:
    config_path = os.path.join(configs_dir, f"{prefix}-client-config.json")
    env_path = os.path.join(configs_dir, f"{prefix}.env")

    print(f"Validating config for prefix: {prefix}\n")
    all_errors = []

    # Validate config JSON
    if not os.path.exists(config_path):
        all_errors.append(f"Config file not found: {config_path}")
    else:
        print(f"  ✓  Found {config_path}")
        with open(config_path) as f:
            config = json.load(f)
        all_errors.extend(validate_config(config))

    # Validate env file
    if not os.path.exists(env_path):
        all_errors.append(f"Env file not found: {env_path}")
    else:
        print(f"  ✓  Found {env_path}")
        env = parse_env_file(env_path)
        all_errors.extend(validate_env(env))

    if all_errors:
        print(f"\n{'─' * 50}")
        print(f"  {len(all_errors)} error(s) found:")
        for e in all_errors:
            print(f"  ✗  {e}")
        sys.exit(1)
    else:
        print(f"\n{'─' * 50}")
        print("  All checks passed. ✓")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate or validate a WOS client configuration."
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate an existing config + env pair (requires --prefix)",
    )
    parser.add_argument(
        "--prefix",
        help="Client prefix (required for --validate)",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_CONFIGS_DIR,
        help=f"Directory for config files (default: {DEFAULT_CONFIGS_DIR})",
    )
    args = parser.parse_args()

    if args.validate:
        if not args.prefix:
            parser.error("--validate requires --prefix")
        run_validate(args.prefix.upper(), args.output_dir)
    else:
        run_interactive(args.output_dir)


if __name__ == "__main__":
    main()
