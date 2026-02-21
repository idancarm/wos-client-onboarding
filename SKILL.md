---
name: wos-client-onboarding
description: >
  Step-by-step guide for onboarding a new client onto the WOS (Warm Outreach System).
  Covers creating n8n data tables, cloning n8n workflows, verifying HubSpot properties,
  creating per-user HubSpot trigger workflows, and end-to-end testing.
  Use this skill whenever someone mentions onboarding a new WOS client, setting up WOS
  for a new company, cloning WOS workflows, creating WOS data tables, or preparing a
  new client for LinkedIn outreach automation. Also trigger if someone asks about the
  WOS system architecture, how the outreach pipeline works, or needs to add a new
  operator/user to an existing WOS client.
---

# WOS Client Onboarding

This skill guides you through onboarding a new client onto the Warm Outreach System (WOS) — an automated LinkedIn outreach pipeline built on n8n, integrated with HubSpot CRM, Unipile (LinkedIn API), and Cargo (email enrichment).

For full system architecture details, read `references/system-architecture.md` in this skill's directory.

## What You Can Help With

When a user invokes this skill, determine which scenario applies:

1. **Full new client onboarding** — Follow the complete workflow below from Step 1.
2. **Adding a new user/operator** to an existing client — Skip to Step 5 (User Counters) and Step 7 (HubSpot Workflows).
3. **Architecture questions** — Read `references/system-architecture.md` and answer from there.
4. **Troubleshooting** — Check the Troubleshooting section at the bottom.

## Prerequisites

Before starting, confirm these are available:

- Access to the n8n instance (browser or API)
- Access to the client's HubSpot portal (via MCP tool or browser)
- The client has provided: company name, desired prefix, list of operators, ICP personas, and API keys for Unipile and Cargo
- An existing WOS client to use as a template (the REFINE client with prefix "REF" is the reference implementation)

## Onboarding Workflow

The steps below must be followed in order — later steps depend on earlier ones.

### Step 1: Gather Client Information

Collect all required information before touching any system. This prevents partial setups.

**Required from the client:**

| Item | Example | Notes |
|------|---------|-------|
| Company name | "Acme Corp" | Used for n8n folder name |
| Short prefix | "ACM" | 3-4 uppercase letters, used in all naming |
| Operators | Erez Frankel, Uri Rivner | People who will run outreach |
| Operator HubSpot owner IDs | 42257128, 42257129 | Look up in HubSpot if not provided |
| ICP personas | See persona table format | Title keywords, location, language |
| HubSpot bearer token | — | From client's HubSpot portal |
| Unipile API key | — | From their Unipile account |
| Unipile account_id | — | From their Unipile account |
| Unipile DNS | — | From their Unipile account |
| Cargo API key | — | From their Cargo account |

**If using Claude to help:** You can look up HubSpot owner IDs using the `search_owners` MCP tool if you have access to the client's HubSpot portal.

### Step 2: Create n8n Data Tables

Create 3 data tables in n8n. These store all client-specific configuration.

#### 2a. Credentials Table: `[PREFIX]-wos-credentials`

Create a table with 6 columns: `service`, `api_key`, `account_id`, `dns`, `extra_1`, `extra_2`

Add 3 rows:

| service | api_key | account_id | dns | extra_1 | extra_2 |
|---------|---------|------------|-----|---------|---------|
| hubspot | [Bearer token] | — | — | — | — |
| unipile | [API key] | [account_id] | [dns subdomain] | — | — |
| cargo | [API key] | — | — | — | — |

#### 2b. Personas Table: `[PREFIX]-wos-personas`

Create a table with 6 columns: `title_keywords`, `language`, `network_distance`, `location`, `extra_1`, `extra_2`

Add one row per persona. Example:

| title_keywords | language | network_distance | location | extra_1 | extra_2 |
|---------------|----------|-----------------|----------|---------|---------|
| ciso OR "chief information security" | en | S | United States | — | — |
| "vp security" OR "head of security" | en | S | United States | — | — |

The `title_keywords` field uses boolean search syntax (OR, AND, quoted phrases). `network_distance` is typically "S" for 2nd-degree connections.

#### 2c. User Counters Table: `[PREFIX]-wos-user_counters`

Create a table with 12 columns: `user_name`, `hubspot_owner_id`, `weekly_count`, `daily_count`, `weekly_remaining`, `daily_remaining`, `weekly_reset_date`, `daily_reset_date`, `invite_safe_date`, `extra_1`, `extra_2`, `extra_3`

Add one row per operator with zeroed counters:

| user_name | hubspot_owner_id | weekly_count | daily_count | weekly_remaining | daily_remaining | weekly_reset_date | daily_reset_date |
|-----------|-----------------|--------------|-------------|-----------------|-----------------|-------------------|------------------|
| [Name] | [Owner ID] | 0 | 0 | 150 | 20 | [Next Monday] | [Tomorrow] |

### Step 3: Create n8n Workflow Folder

In the n8n instance, create a new folder named `WOS - [CLIENT_NAME]` (e.g., "WOS - ACME CORP").

All client workflows will live in this folder.

### Step 4: Clone and Configure n8n Workflows

Clone each workflow from the reference client (REFINE) and update for the new client. There are 13 workflows to clone (workflow 5, the Outreach Orchestrator, is shared and does NOT need cloning).

For each workflow:

1. Open the REFINE version in n8n
2. Select all nodes → Copy
3. Create a new workflow in the client's folder with the correct name
4. Paste all nodes
5. Update references:
   - Change data table references from `REF-wos-*` to `[PREFIX]-wos-*`
   - Change sub-workflow call references to point to the new client's workflow IDs
   - Update the webhook URL in the Entry Point workflow
   - Verify credential table lookups use the new table IDs

**Clone in this order** (dependencies flow downward):

1. `WOS [PREFIX] 16 - Utility - Anti-Ban Delay` (no dependencies)
2. `WOS [PREFIX] 4 - Sub - Safeguard Logic` (reads user_counters table)
3. `WOS [PREFIX] 6 - Sub - LinkedIn Lead Finder` (reads personas table)
4. `WOS [PREFIX] 7 - Sub - Contact Creator`
5. `WOS [PREFIX] 8 - Sub - Connection Status Checker`
6. `WOS [PREFIX] 9 - Sub - HubSpot Updater` (calls Cargo)
7. `WOS [PREFIX] 10 - Interaction - Like Post & Schedule`
8. `WOS [PREFIX] 11 - Invitation - Send Scheduled`
9. `WOS [PREFIX] 12 - Invitation - Monitor Acceptance`
10. `WOS [PREFIX] 2 - Main - Data Validator`
11. `WOS [PREFIX] 3 - Main - Safeguard Check` (calls #4, then calls shared ENVY 5)
12. `WOS [PREFIX] 1 - Main - Entry Point` (calls #2, #3 — this contains the webhook trigger)
13. `WOS - [PREFIX] - SEQUENCE EDITOR`

After cloning all workflows, note down each new workflow's ID — you'll need these for cross-references.

**Critical cross-references to update:**
- Entry Point → must call the new Data Validator and Safeguard Check by their new IDs
- Safeguard Check → must call the new Safeguard Logic by its new ID
- Safeguard Check → still calls the SHARED `WOS ENVY 5 - Outreach Orchestrator` (do not change this)
- All Sub workflows that read data tables → update table IDs to the new client's tables

### Step 5: Verify HubSpot Properties

WOS properties on Contact and Company objects are shared across all clients in a HubSpot portal. They only need to be created once.

**Automated approach (recommended):** Run the verification script:

```bash
# Verify only (dry run) — shows which properties exist / are missing
python scripts/verify_hubspot_properties.py --token "pat-xxx"

# Verify + create any missing properties
python scripts/verify_hubspot_properties.py --token "pat-xxx" --create
```

You can also set `HUBSPOT_TOKEN` as an environment variable instead of passing `--token`.

**Check if these already exist. If not, create them:**

**Contact properties (11):**
- `wos_outreach_stage` (single-line text)
- `wos_sequence_status` (single-line text)
- `wos_sequence_name` (single-line text)
- `wos_sequence_start_date` (date picker)
- `wos_user_id` (single-line text)
- `wos_last_interaction_date` (date picker)
- `wos_linkedin_url` (single-line text)
- `wos_linkedin_id` (single-line text)
- `wos_linkedin_connection_status` (single-line text)
- `wos_connection_accepted_date` (date picker)
- `n8n_initiate_li_message` (single-line text)

**Company properties (3):**
- `wos_process_company` (date picker) — label: "WOS Initiate LI Agent"
- `wos_persona` (single-line text)
- `wos_user_id` (single-line text)

**If using Claude to help:** Use the HubSpot MCP `search_properties` tool to check if these exist, and `manage_crm_objects` if creation is needed. Note that property creation may require direct HubSpot API access or manual creation in the portal UI.

### Step 6: Register Webhook in HubSpot

The n8n Entry Point workflow has a webhook trigger. After creating the Entry Point workflow (Step 4), copy its webhook URL.

This webhook URL needs to be connected to HubSpot so that when `wos_process_company` is set on a company, n8n receives the event. The connection is made through the HubSpot workflows created in the next step.

### Step 7: Create HubSpot Trigger Workflows

Each operator needs two HubSpot workflows. These are created in HubSpot's workflow editor.

#### 7a. Company Trigger Workflow

**Name:** `LI Agent - Trigger Company Processing - [User Name]`

| Setting | Value |
|---------|-------|
| Object | Company |
| Trigger | Manual enrollment |
| Re-enrollment | Off |

**Actions:**
1. Set property `wos_user_id` → operator's HubSpot owner ID
2. Set property `wos_process_company` → `{{current_datetime}}` (this fires the n8n webhook)

#### 7b. Contact Sequence Workflow

**Name:** `LI Agent - TEMPLATE Trigger Contact LI Sequence - From [User Name]`

| Setting | Value |
|---------|-------|
| Object | Contact |
| Trigger | Manual enrollment |
| Re-enrollment | On |

**Actions:**
1. Set property `wos_user_id` → operator's HubSpot owner ID
2. Set property `wos_sequence_name` → "default" (or client-specific sequence name)
3. Set property `wos_sequence_status` → "In Progress"
4. Create task: "SEQ1 - First Message"
5. Delay: 2 minutes
6. Create task: "SEQ2 - Second Message"

Repeat for each operator.

### Step 8: End-to-End Testing

Test the full pipeline with a single company before going live.

#### 8a. Smoke Test — Webhook Connectivity
1. In HubSpot, enroll a test company into the "LI Agent - Trigger Company Processing" workflow
2. Verify n8n Entry Point workflow fires (check execution log in n8n)
3. Verify the company data passes validation

#### 8b. Safeguard Test
1. Check that the user_counters table shows the operator's row
2. Verify daily/weekly remaining counts are correct
3. Trigger the pipeline and verify counters decrement

#### 8c. Lead Discovery Test
1. Choose a company with known LinkedIn employees
2. Trigger the pipeline
3. Verify LinkedIn Lead Finder returns results
4. Verify contacts are created in HubSpot with correct WOS properties

#### 8d. Invitation Test
1. Verify a connection invitation is sent via Unipile
2. Check that `wos_linkedin_connection_status` updates in HubSpot
3. Verify the anti-ban delay is applied between actions

#### 8e. Full Sequence Test
1. Enroll a contact into the sequence workflow
2. Verify tasks are created in HubSpot
3. Verify sequence status properties update correctly

### Step 9: Go Live Checklist

Before declaring the client fully onboarded:

- [ ] All 3 data tables created and populated
- [ ] All 13 workflows cloned, renamed, and cross-references updated
- [ ] All workflows activated in n8n
- [ ] HubSpot properties exist (or were already present)
- [ ] Per-user HubSpot trigger workflows created and turned ON
- [ ] Webhook connectivity confirmed
- [ ] At least one successful end-to-end test completed
- [ ] Client operators briefed on how to enroll companies in HubSpot
- [ ] Rate limits confirmed (20/day, 150/week per user)

---

## Troubleshooting

### Webhook not firing
- Confirm `wos_process_company` property is a date picker type
- Confirm the HubSpot workflow is ON and sets `wos_process_company` to current datetime
- Check n8n Entry Point workflow is active and the webhook URL matches

### Leads not found
- Check personas table has correct boolean syntax in `title_keywords`
- Verify Unipile credentials in credentials table (api_key, account_id, dns)
- Test Unipile API directly with a known company

### Contacts not created in HubSpot
- Verify HubSpot bearer token in credentials table is valid and has write permissions
- Check HubSpot Updater workflow execution logs for errors
- Ensure WOS properties exist on the Contact object

### Rate limit errors
- Check user_counters table — daily_remaining and weekly_remaining should be > 0
- Verify reset dates are correct
- Manually reset counters if needed for testing

### Cargo enrichment failing
- Verify Cargo API key in credentials table
- Test Cargo API directly with a known LinkedIn URL
- Check if Cargo account has remaining credits
