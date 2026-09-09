# Social Lead Hunter

A generic engine for finding recent public social posts from people who appear to be looking for a product or service, qualifying those posts, drafting contextual replies, and optionally publishing replies after safety checks.

The repository is intentionally **business-neutral**. Business names, services, contact details, customer data, tokens, API keys, and server-specific secrets belong in local configuration or environment variables, not in GitHub.

## In plain language

```text
Search recent posts
        ↓
Remove duplicates / obvious bad matches
        ↓
Score buying intent
        ↓
Draft a contextual reply
        ↓
DRY RUN: save only
LIVE: safety checks → reply
```

The safe default is **dry-run**. A fresh setup does not publish replies.

---

# Fastest Hermes setup

The intended experience is that you can give Hermes this repository URL and ask it to install and configure the tool.

A suitable instruction is:

> Install and set up this Social Lead Hunter repository. Keep all secrets local, start in dry-run, check Threads permissions first, configure the business locally, and do not enable live replies until I explicitly approve them.

The included Hermes skill is designed to handle that flow.

Hermes should:

1. install the Python engine from the repository URL;
2. run `social-lead-hunter setup`;
3. use information already provided to fill the local business config;
4. ask only for missing **non-secret** business details in plain language;
5. keep credentials in environment variables / secret storage;
6. run the Threads capability audit;
7. run a dry-run;
8. keep live replies disabled until explicit approval.

Canonical Hermes skill:

```text
skills/social-lead-hunter/SKILL.md
```

## Copy-paste Hermes prompt for any business

Use this when you want Hermes to handle most of the setup for you.

```text
Set up Social Lead Hunter from this GitHub repository:
<REPOSITORY_URL>

I want to use it to find potential customers on Threads for my business.

What my business offers:
<BUSINESS_DESCRIPTION>

Products or services I want to find leads for:
- <PRODUCT_OR_SERVICE_1>
- <PRODUCT_OR_SERVICE_2>
- <PRODUCT_OR_SERVICE_3>

Target location or market:
<TARGET_LOCATION_OR_MARKET>

Examples of how potential customers may ask for these products/services:
- <BUYER_INTENT_PHRASE_1>
- <BUYER_INTENT_PHRASE_2>
- <BUYER_INTENT_PHRASE_3>

Preferred reply style:
<REPLY_STYLE>

Optional CTA/contact instruction:
<CTA_OR_LEAVE_BLANK>

GOAL

Install and configure the engine so it can search recent public Threads posts, identify genuine buying intent, score the leads, draft contextual replies, and save the results.

SETUP REQUIREMENTS

1. Install the engine from the GitHub repository.
2. Run `social-lead-hunter setup`.
3. Keep the business configuration locally, outside the Git repository.
4. Keep API tokens, database keys, LLM keys, and all other secrets in environment variables or local secret storage. Never commit or print secret values.
5. Use the information in this prompt and any existing conversation context first. Ask me only for missing non-secret information.
6. If you need to ask me something, explain it in plain language rather than assuming I understand Python, YAML, APIs, scopes, or database internals.
7. Configure the products/services, buyer-intent keywords, exclusions, target location, reply style, CTA, score threshold, and safety limits based on the information above.
8. Run the Threads capability audit before the first search.
9. If a Threads permission or token capability is missing, stop and explain exactly what is missing. Do not bypass it with scraping.
10. Start in DRY RUN.
11. During dry-run, search for recent public posts that show genuine buying intent for the configured products/services.
12. Exclude obvious bad matches such as my own account, seller self-promotion, recruitment/job posts, spam, giveaways, irrelevant posts, irrelevant locations, and duplicates.
13. Generate short contextual draft replies that match the poster's language/style where practical.
14. Do not invent prices, stock, lead time, certifications, service coverage, capabilities, or other business facts that were not provided.
15. Report the dry-run results clearly: posts scanned, qualified leads, rejected posts, duplicates, drafted replies, failures, and any configuration issues.
16. Keep live auto-replies disabled after setup.
17. Do not change dry-run to live mode until I explicitly review the dry-run results and approve live replies.
```

### Very generic example

This example deliberately avoids any specific industry. Replace the example values with whatever you actually sell or provide.

```text
Set up Social Lead Hunter from this GitHub repository:
<REPOSITORY_URL>

What my business offers:
A business that provides products and services to customers.

Products or services I want to find leads for:
- Product A
- Service B

Target location or market:
My target market

Examples of how potential customers may ask:
- looking for Product A
- need someone who can provide Service B
- any recommendation for this type of service

Preferred reply style:
Helpful, short, natural, and not pushy.

Optional CTA/contact instruction:
Leave blank for now.

Please install and configure the tool, keep all secrets local, run the Threads permission audit, start in dry-run, show me the leads and draft replies, and keep live replies disabled until I explicitly approve them.
```

The placeholders are intentionally generic. A user can replace `Product A`, `Service B`, location, customer phrases, reply style, and CTA without changing the engine code.

## Manual install, if needed

Install directly from a Git repository:

```bash
python3 -m pip install "git+<repository-url>"
```

Or from a local clone:

```bash
python3 -m pip install -e .
```

Then run:

```bash
social-lead-hunter setup
```

That one command:

- creates the default local config folder/file if missing;
- keeps `dry_run: true`;
- prepares the default SQLite database;
- reports missing required environment variable names;
- never prints secret values;
- does not overwrite an existing config unless `--force` is explicitly used.

Default local config path:

```text
~/.config/social-lead-hunter/config.yaml
```

Custom path:

```bash
social-lead-hunter setup --config /path/to/config.yaml
```

Only use this if you intentionally want to replace an existing config:

```bash
social-lead-hunter setup --config /path/to/config.yaml --force
```

---

# First-time configuration

The generated config contains obvious `CHANGE_ME` placeholders for non-secret business settings.

Example:

```yaml
business:
  description: "CHANGE_ME: describe what the business offers"
  services:
    - "CHANGE_ME: service or product"
  reply_style: "helpful, concise, contextual"
  cta: ""

search:
  keywords:
    - "CHANGE_ME: buyer-intent search phrase"
  negative_keywords: []
  target_locations: []
  freshness_hours: 24
  min_score: 80

runtime:
  dry_run: true
  max_replies_per_day: 5
  min_reply_gap_minutes: 30
  same_user_cooldown_days: 7

storage:
  backend: "sqlite"
  path: "~/.local/share/social-lead-hunter/social_leads.sqlite3"

llm:
  enabled: false
```

Normal business changes should be made in the local config, not by editing engine code.

## What the settings mean

- `business.description` — what the business does.
- `business.services` — products/services that count as relevant.
- `reply_style` — how replies should sound.
- `cta` — optional contact/call-to-action. Leave blank if not wanted.
- `search.keywords` — buyer-intent phrases to search.
- `negative_keywords` — phrases that should reject a post.
- `target_locations` — optional locations to prioritize.
- `freshness_hours` — how recent a post should be.
- `min_score` — minimum lead score before drafting.
- `dry_run` — when `true`, never publish.
- `max_replies_per_day` — hard daily limit in live mode.
- `min_reply_gap_minutes` — minimum time between live replies.
- `same_user_cooldown_days` — avoid repeatedly contacting the same user.

---

# Secrets and environment variables

Credentials are read from environment variables.

```text
THREADS_ACCESS_TOKEN
THREADS_USER_ID
THREADS_API_BASE
THREADS_API_VERSION
SUPABASE_URL
SUPABASE_KEY
LLM_API_BASE
LLM_API_KEY
LLM_MODEL
```

`THREADS_ACCESS_TOKEN` is required for Threads use. The others depend on the selected configuration.

Do **not** put real credentials into:

- Git commits;
- README/SKILL files;
- `config.yaml`;
- screenshots/logs;
- public issue/PR comments.

The included `.env.example` contains variable names only.

---

# Permission audit

Before relying on Threads search/reply capability, run:

```bash
social-lead-hunter audit --config ~/.config/social-lead-hunter/config.yaml
```

The current flow expects Threads permissions including:

```text
threads_basic
threads_keyword_search
threads_content_publish
```

The audit checks identity, search capability, and reply capability without publishing a test reply.

If permissions are missing, fix the app/token configuration first. Do not bypass it with scraping.

---

# Dry-run

Run one cycle:

```bash
social-lead-hunter run --config ~/.config/social-lead-hunter/config.yaml
```

The output reports counts such as:

- posts scanned;
- new posts;
- qualified leads;
- rejected posts;
- duplicates;
- drafted replies;
- published replies;
- failures.

With `dry_run: true`, published replies remain zero.

---

# Live mode

Do not change:

```yaml
dry_run: true
```

to:

```yaml
dry_run: false
```

until all of these are true:

- Threads audit passes;
- dry-run leads are genuinely relevant;
- drafts are not repetitive spam;
- own-account exclusion works;
- duplicate protection works;
- daily limit is acceptable;
- minimum reply gap is acceptable;
- same-user cooldown is acceptable;
- the operator explicitly approves live replies.

---

# Threads behavior

The first production adapter is Threads and uses the official API.

Core operations:

```text
GET  /keyword_search   recent public discovery
GET  /me               identity check
GET  /debug_token      token/scope inspection
POST /me/threads       reply creation with reply_to_id
```

The adapter uses `search_type=RECENT` for discovery.

## Retry policy

Temporary failures are treated conservatively:

- network/connection failure → bounded retry;
- Threads `5xx` → bounded retry;
- `401` authentication failure → no retry;
- `403` permission failure → no retry;
- normal `4xx` → no retry;
- `429` rate limit → no automatic hammering/retry loop.

The default is at most two retries after the first attempt.

---

# Storage

## SQLite — default

Best for one Hermes/VPS instance and easiest to start with.

```yaml
storage:
  backend: "sqlite"
```

`social-lead-hunter setup` prepares the database automatically.

## Supabase — optional

Use Supabase when leads need to be shared with other systems or machines.

Run:

```text
migrations/supabase.sql
```

against the target Supabase database, then configure:

```yaml
storage:
  backend: "supabase"
```

and provide `SUPABASE_URL` and `SUPABASE_KEY` locally.

### Supabase security

The supplied migration:

- enables Row Level Security on all lead tables;
- removes direct access for normal public client roles;
- grants the trusted server role the required database operations.

Use a **trusted server-side key** for this automation. Never expose that key in a browser, frontend bundle, public GitHub repository, or client application.

---

# Optional LLM drafting

The engine works without an LLM.

```yaml
llm:
  enabled: false
```

When enabled, it can use an OpenAI-compatible endpoint configured with:

```text
LLM_API_BASE
LLM_API_KEY
LLM_MODEL
```

The LLM is used for drafting. Deterministic safety, dedupe, limits, and publishing rules remain outside the LLM.

---

# Lead scoring

The first release uses transparent deterministic rules.

Positive signals include:

- direct request language;
- service/product match;
- quantity/size/budget/deadline details;
- location match;
- recency.

Exclusions/negative signals include:

- own account;
- seller self-promotion;
- recruitment/vacancies;
- spam/giveaways;
- configured negative keywords.

Each result keeps human-readable reasons for the score.

---

# Scheduling with Hermes

The engine runs one cycle and exits. Hermes can schedule recurring cycles after dry-run quality is acceptable.

Recommended operating pattern:

```text
Hermes scheduler
      ↓
social-lead-hunter run
      ↓
engine safety limits
      ↓
Threads
```

Do not rely on the scheduler alone for safety. Keep the engine's daily cap, reply gap, same-user cooldown, and dry-run/live controls enabled.

---

# CLI reference

Create/prepare local setup:

```bash
social-lead-hunter setup
```

Show effective non-secret config:

```bash
social-lead-hunter show-config --config /path/to/config.yaml
```

Audit Threads access:

```bash
social-lead-hunter audit --config /path/to/config.yaml
```

Run one lead-hunting cycle:

```bash
social-lead-hunter run --config /path/to/config.yaml
```

---

# Development and automatic tests

Install test dependencies:

```bash
python -m pip install -e '.[dev]'
```

Run locally:

```bash
pytest -q
python -m compileall -q src
```

GitHub Actions also runs the test suite automatically for pull requests and relevant pushes on supported Python versions.

No automated test should publish a real Threads reply.

---

# Project structure

```text
src/social_lead_hunter/
  cli.py                  CLI: setup/audit/run/show-config
  setup.py                safe first-run setup
  config.py               local non-secret configuration
  models.py               shared data models
  orchestrator.py         search → qualify → draft → publish pipeline
  platforms/threads.py    official Threads API adapter + bounded retry
  qualification/          deterministic lead scoring
  replies/                reply drafting
  safety/                 daily caps / cooldowns / gaps
  storage/                SQLite + optional Supabase
  llm/                    optional OpenAI-compatible drafting
skills/social-lead-hunter/
  SKILL.md                Hermes operating procedure
migrations/
  supabase.sql            optional secure Supabase schema
tests/                    mocked tests; no live publishing
.github/workflows/
  tests.yml               automatic CI tests
```

## Scope

This project is deliberately focused. It is not a CRM, billing platform, full SaaS dashboard, or browser scraper. Its job is to provide a small, reusable lead-discovery engine that Hermes can configure and operate safely.