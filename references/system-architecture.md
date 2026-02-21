# WOS System Architecture Reference

## Table of Contents
1. [System Overview](#system-overview)
2. [n8n Workflow Map](#n8n-workflow-map)
3. [n8n Data Tables Schema](#n8n-data-tables-schema)
4. [HubSpot Properties](#hubspot-properties)
5. [HubSpot Workflows](#hubspot-workflows)
6. [Third-Party Services](#third-party-services)
7. [Naming Conventions](#naming-conventions)

---

## System Overview

WOS (Warm Outreach System) is an automated LinkedIn outreach pipeline built on n8n. It finds leads at target companies, sends connection invitations, engages with prospects' posts, and syncs all activity to HubSpot CRM.

**Core flow:**
1. HubSpot "LI Agent" workflow triggers n8n via `wos_process_company` datetime property
2. n8n Entry Point receives company data, validates it, checks safeguards
3. LinkedIn Lead Finder searches for relevant people at the company using personas
4. HubSpot Updater creates/updates contact records (enriched via Cargo for email)
5. Connection invitations are sent via Unipile (LinkedIn API)
6. Post interactions (likes) warm up the prospect
7. Message sequences are triggered from HubSpot for connected leads

**Architecture layers:**
- **Trigger layer**: HubSpot workflows → n8n webhooks
- **Orchestration layer**: n8n Main workflows (Entry Point, Data Validator, Safeguard Check)
- **Execution layer**: n8n Sub workflows (Lead Finder, Contact Creator, HubSpot Updater, Connection Checker)
- **Engagement layer**: n8n Invitation & Interaction workflows
- **Safety layer**: Safeguard Logic + Anti-Ban Delay + User Counters table

---

## n8n Workflow Map

Each client gets a set of workflows with a unique prefix. The REFINE client has prefix `REF`/`REFINE`.

### Naming Convention
`WOS [CLIENT_PREFIX] [NUMBER] - [Category] - [Name]`

Categories: Main, Sub, Invitation, Interaction, Utility

### Workflows (13 total for REFINE client)

| # | Category | Name | Purpose |
|---|----------|------|---------|
| 1 | Main | Entry Point | Two triggers (webhook batch + single company). Validates data, splits by user, loops into safeguard. |
| 2 | Main | Data Validator | Validates incoming company data structure and required fields. |
| 3 | Main | Safeguard Check | Calls Safeguard Logic sub-workflow, checks "No Ban Risks" flag, if safe → calls shared ENVY Outreach Orchestrator (WOS ENVY 5). |
| 4 | Sub | Safeguard Logic | Reads user_counters table, checks daily (20/day) and weekly (150/week) limits, updates counters. |
| 5 | — | Outreach Orchestrator | **SHARED across clients** (WOS ENVY 5). Not per-client. Orchestrates the full outreach sequence. |
| 6 | Sub | LinkedIn Lead Finder | Reads personas from data table, searches LinkedIn via Unipile API for matching people at target company. |
| 7 | Sub | Contact Creator | Creates HubSpot contact records from discovered LinkedIn leads. |
| 8 | Sub | Connection Status Checker | Checks current LinkedIn connection status for leads via Unipile. |
| 9 | Sub | HubSpot Updater | Three paths: (a) contact exists → update, (b) doesn't exist → enrich via Cargo → create, (c) fallback → search company by domain. |
| 10 | Interaction | Like Post & Schedule | Finds and likes prospects' recent LinkedIn posts to build engagement. |
| 11 | Invitation | Send Scheduled | Sends scheduled LinkedIn connection invitations with personalized notes. |
| 12 | Invitation | Monitor Acceptance | Monitors whether connection invitations have been accepted. |
| 16 | Utility | Anti-Ban Delay | Rate limiting utility — adds delays between LinkedIn actions to avoid detection. |
| — | — | Sequence Editor | Tool for editing message sequences (not part of the automated flow). |

### Workflow Dependencies
```
HubSpot "LI Agent" workflow
  → sets wos_process_company datetime
    → triggers n8n webhook
      → WOS [PREFIX] 1 - Entry Point
        → WOS [PREFIX] 2 - Data Validator
        → WOS [PREFIX] 3 - Safeguard Check
          → WOS [PREFIX] 4 - Safeguard Logic (reads user_counters table)
          → WOS ENVY 5 - Outreach Orchestrator (SHARED)
            → WOS [PREFIX] 6 - LinkedIn Lead Finder (reads personas table)
            → WOS [PREFIX] 7 - Contact Creator
            → WOS [PREFIX] 8 - Connection Status Checker
            → WOS [PREFIX] 9 - HubSpot Updater (uses Cargo for enrichment)
            → WOS [PREFIX] 10 - Like Post & Schedule
            → WOS [PREFIX] 11 - Invitation - Send Scheduled
            → WOS [PREFIX] 12 - Invitation - Monitor Acceptance
            → WOS [PREFIX] 16 - Anti-Ban Delay
```

---

## n8n Data Tables Schema

Each client gets 3 data tables with their prefix.

### 1. [PREFIX]-wos-credentials
Stores API keys for all third-party services.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| service | string | Service name | "hubspot", "unipile", "cargo" |
| api_key | string | API key or bearer token | Bearer token for HubSpot |
| account_id | string | Account identifier (Unipile) | Unipile account ID |
| dns | string | DNS endpoint (Unipile) | Unipile DNS subdomain |
| extra_1 | string | Additional config | — |
| extra_2 | string | Additional config | — |

**Required rows:** hubspot, unipile, cargo

### 2. [PREFIX]-wos-personas
Defines LinkedIn search personas — each persona targets a specific job function.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| title_keywords | string | Boolean search query for job titles | "risk OR fraud OR bsa OR aml" |
| language | string | Profile language filter | "en" |
| network_distance | string | LinkedIn network distance | "S" (2nd degree) |
| location | string | Geographic filter | "United States" |
| extra_1 | string | Reserved | — |
| extra_2 | string | Reserved | — |

**Typical setup:** 3-7 personas per client based on their ICP.

### 3. [PREFIX]-wos-user_counters
Tracks daily and weekly LinkedIn action counts per operator to enforce rate limits.

| Column | Type | Description | Default |
|--------|------|-------------|---------|
| user_name | string | Operator's full name | — |
| hubspot_owner_id | string | HubSpot owner ID for this user | — |
| weekly_count | number | Actions taken this week | 0 |
| daily_count | number | Actions taken today | 0 |
| weekly_remaining | number | Actions left this week | 150 |
| daily_remaining | number | Actions left today | 20 |
| weekly_reset_date | date | Next weekly counter reset | Next Monday |
| daily_reset_date | date | Next daily counter reset | Tomorrow |
| invite_safe_date | date | Earliest date for next invite batch | — |
| extra_1 | string | Reserved | — |
| extra_2 | string | Reserved | — |
| extra_3 | string | Reserved | — |

**Rate limits:** 20 actions/day, 150 actions/week per user.

---

## HubSpot Properties

### Contact Properties (11 WOS fields)

| Property Name | Type | Label | Purpose |
|--------------|------|-------|---------|
| wos_outreach_stage | string | WOS Outreach Stage | Master lead status in outreach flow |
| wos_sequence_status | string | WOS Sequence Status | "In Progress" / "Finished" / "Stopped" |
| wos_sequence_name | string | WOS Sequence Name | Name of active LinkedIn message sequence |
| wos_sequence_start_date | datetime | WOS Sequence Start Date | When sequence was triggered |
| wos_user_id | string | WOS User ID | Which operator is running outreach for this contact |
| wos_last_interaction_date | datetime | WOS Last Interaction Date | Last post-like or engagement timestamp |
| wos_linkedin_url | string | WOS LinkedIn URL | Lead's LinkedIn profile URL |
| wos_linkedin_id | string | WOS LinkedIn ID | Lead's LinkedIn member ID |
| wos_linkedin_connection_status | string | WOS LinkedIn Connection Status | Current connection status |
| wos_connection_accepted_date | datetime | WOS Connection Accepted Date | When invite was accepted |
| n8n_initiate_li_message | string | n8n Initiate LI Message | Triggers LI message flow |

### Company Properties (3 WOS fields)

| Property Name | Type | Label | Purpose |
|--------------|------|-------|---------|
| wos_process_company | datetime | WOS Initiate LI Agent | Setting this fires n8n webhook — primary trigger |
| wos_persona | string | WOS Persona | Which search persona to use for this company |
| wos_user_id | string | WOS User ID | Which operator will handle this company |

---

## HubSpot Workflows

Each operator (user) needs their own pair of HubSpot workflows.

### 1. "LI Agent - Trigger Company Processing - [User Name]"
- **Object:** Company
- **Trigger:** Manual enrollment
- **Actions:**
  1. Set `wos_user_id` → operator's HubSpot owner ID
  2. Set `wos_process_company` → current datetime (this fires the n8n webhook)

### 2. "LI Agent - TEMPLATE Trigger Contact LI Sequence - From [User Name]"
- **Object:** Contact
- **Trigger:** Manual enrollment (re-enrollment ON)
- **Actions:**
  1. Set `wos_user_id` → operator's HubSpot owner ID
  2. Set `wos_sequence_name` → sequence name (e.g., "default")
  3. Set `wos_sequence_status` → "In Progress"
  4. Create task "SEQ1 - First Message"
  5. Delay 2 minutes
  6. Create task "SEQ2 - Second Message"

---

## Third-Party Services

### Unipile (LinkedIn API Proxy)
- **Purpose:** All LinkedIn interactions — search, profile retrieval, invitations, post likes, messaging
- **Authentication:** API key + account_id + DNS endpoint
- **Stored in:** credentials data table (service: "unipile")
- **Key endpoints used:**
  - Search people at company
  - Get profile details
  - Send connection invitation
  - Get/like posts
  - Send messages

### Cargo (Email Enrichment)
- **Purpose:** Find email addresses from LinkedIn profile URLs
- **Authentication:** API key
- **Base URL:** api.getcargo.io
- **Stored in:** credentials data table (service: "cargo")
- **Used by:** HubSpot Updater workflow (when creating new contacts)

### HubSpot CRM
- **Purpose:** Central contact/company management, workflow triggers, activity tracking
- **Authentication:** Bearer token
- **Stored in:** credentials data table (service: "hubspot")
- **Portal:** Each client has their own HubSpot portal (or operates within the ENVY portal)

---

## Naming Conventions

### Client Prefix
Each client gets a short prefix (e.g., "REF" for REFINE). This prefix appears in:
- All n8n workflow names: `WOS [PREFIX] ...`
- All n8n data table names: `[PREFIX]-wos-...`
- n8n workflow folder name: `WOS - [CLIENT_NAME]`

### Standard Prefixes
- Workflow numbers are consistent across clients (1 = Entry Point, 2 = Data Validator, etc.)
- Data table suffixes are consistent: `-wos-credentials`, `-wos-personas`, `-wos-user_counters`
- HubSpot properties are shared (not per-client) — the `wos_` prefix is global
- HubSpot workflows are per-user, not per-client
