# Social Lead Hunter

A small, generic engine for finding public social posts from people who appear to be looking for a product or service.

In plain language, it does this:

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

It is designed to be configured locally for different businesses. **Business names, services, contact details, credentials, tokens, and customer data do not belong in this repository.**

## Safety first

The default is:

```yaml
runtime:
  dry_run: true
```

With dry-run enabled, the engine can search, score, draft, and save leads, but it does not publish replies.

Do not switch to live mode until:

1. the Threads permission audit passes;
2. dry-run results look relevant;
3. duplicate/user cooldown limits are working;
4. the operator explicitly approves live replies.

## What is configurable

You can change these without editing the engine:

- what the business does;
- services/products;
- search keywords;
- negative keywords;
- target locations;
- freshness window;
- minimum lead score;
- reply style;
- optional CTA;
- daily reply limit;
- minimum time between replies;
- same-user cooldown;
- SQLite or Supabase storage;
- whether an OpenAI-compatible LLM is used.

See `config.example.yaml`.

## Requirements

- Python 3.11+
- a Threads app/token with the required permissions for Threads mode
- Hermes only if you want to use the included Hermes skill/scheduler workflow

## Quick start

### 1. Get the code

```bash
git clone <repository-url> social-lead-hunter
cd social-lead-hunter
```

### 2. Create a Python environment

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

### 3. Create your local config

Keep the real config outside the Git repository when possible:

```bash
mkdir -p ~/.config/social-lead-hunter
cp config.example.yaml ~/.config/social-lead-hunter/config.yaml
```

Edit that copied file with your own **non-secret** business settings.

### 4. Set secrets locally

The engine reads credentials from environment variables. `.env.example` contains names only.

Relevant variables:

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

**Do not put real secret values in `config.yaml`, README files, SKILL files, or Git commits.**

### 5. Check permissions before searching

```bash
social-lead-hunter audit --config ~/.config/social-lead-hunter/config.yaml
```

The audit checks the Threads token with the official token debugger and performs a harmless read-only keyword-search test. It does **not** publish a test reply.

For the current workflow, expect these Threads scopes to matter:

- `threads_basic`
- `threads_keyword_search`
- `threads_content_publish`

If the audit says a scope is missing, fix the Threads app/token permission first. Do not bypass it with scraping.

### 6. Run dry-run

```bash
social-lead-hunter run --config ~/.config/social-lead-hunter/config.yaml
```

Expected output includes:

- posts scanned;
- new posts;
- qualified leads;
- rejected posts;
- duplicates;
- drafts;
- replies;
- failures.

In dry-run, `replied` should remain `0`.

## Hermes setup

This repository includes a Hermes skill at:

```text
skills/social-lead-hunter/SKILL.md
```

Hermes supports direct GitHub skill installation. With the real repository owner/path, the pattern is:

```bash
hermes skills install <owner>/social-lead-hunter/skills/social-lead-hunter
```

Or add the repository as a custom skill tap:

```bash
hermes skills tap add <owner>/social-lead-hunter
hermes skills search social-lead-hunter
```

The skill is an operating guide; the Python engine still needs to be installed on the machine where Hermes will run it.

A sensible layout is:

```text
~/.hermes/projects/social-lead-hunter/     # cloned engine
~/.config/social-lead-hunter/config.yaml   # local business settings
Hermes environment/secret store            # tokens and keys
```

Then Hermes runs:

```bash
social-lead-hunter audit --config ~/.config/social-lead-hunter/config.yaml
social-lead-hunter run --config ~/.config/social-lead-hunter/config.yaml
```

Only add a recurring Hermes schedule after dry-run quality is acceptable.

## Config explained simply

### `business`

Tells the scorer what you actually offer.

```yaml
business:
  description: "A local service provider helping customers with custom project needs"
  services:
    - "custom service"
  reply_style: "helpful, concise, contextual"
  cta: ""
```

Leave `cta` blank if you do not want contact details added automatically.

### `search`

Tells the engine what to look for.

```yaml
search:
  keywords:
    - "looking for service provider"
  negative_keywords:
    - "job vacancy"
  target_locations:
    - "Malaysia"
  freshness_hours: 24
  min_score: 80
```

A higher `min_score` means fewer but stricter leads.

### `runtime`

Controls live-reply risk.

```yaml
runtime:
  dry_run: true
  max_replies_per_day: 5
  min_reply_gap_minutes: 30
  same_user_cooldown_days: 7
```

Keep these conservative when live mode is first enabled.

### `storage`

SQLite is the simplest option:

```yaml
storage:
  backend: "sqlite"
  path: "social_leads.sqlite3"
```

Supabase is optional. Use `migrations/supabase.sql` to create the generic tables, then provide `SUPABASE_URL` and `SUPABASE_KEY` through environment variables.

### `llm`

The deterministic reply fallback works without an LLM.

```yaml
llm:
  enabled: false
```

When enabled, configure an OpenAI-compatible endpoint through environment variables. The LLM is used for drafting, not for bypassing deterministic safety checks.

## Threads behavior

The Threads adapter uses the official Threads API.

Current core operations are:

- recent discovery: `GET /keyword_search` with `search_type=RECENT`;
- permission inspection: `GET /debug_token`;
- text reply creation: `POST /me/threads` with `reply_to_id` and text auto-publish enabled.

API behavior can change. If Meta changes an endpoint or permission, update the adapter and mocked tests before relying on live mode.

Official source of truth: Meta's Threads API workspace/documentation.

## Live mode checklist

Before changing:

```yaml
dry_run: true
```

to:

```yaml
dry_run: false
```

confirm all of these:

- [ ] `audit` passes identity, keyword search, and reply capability
- [ ] recent dry-run leads are actually relevant
- [ ] drafts do not sound like repetitive sales spam
- [ ] own account is excluded
- [ ] suppliers/competitors promoting themselves are rejected
- [ ] daily reply limit is sensible
- [ ] minimum reply gap is sensible
- [ ] same-user cooldown is sensible
- [ ] operator explicitly approves live mode

## CLI reference

Show effective non-secret config:

```bash
social-lead-hunter show-config --config /path/to/config.yaml
```

Audit Threads access:

```bash
social-lead-hunter audit --config /path/to/config.yaml
```

Run one cycle:

```bash
social-lead-hunter run --config /path/to/config.yaml
```

Scheduling is intentionally left to Hermes, cron, systemd, or another scheduler. The engine itself performs one cycle and exits.

## SQLite vs Supabase

| Option | Best for | Trade-off |
|---|---|---|
| SQLite | One machine, easiest setup | Local file only |
| Supabase | Shared/remote storage | Requires a Supabase project and credentials |

**Default recommendation:** start with SQLite. Move to Supabase only when you actually need shared access or integration with an existing database.

## How lead scoring works

The first release uses transparent rules rather than letting an LLM decide everything.

Positive signals include:

- direct request language;
- configured service match;
- quantity/size/budget/deadline details;
- target-location match;
- recent post age.

Negative/exclusion signals include:

- own account;
- supplier self-promotion;
- vacancies/recruitment;
- spam/giveaways;
- configured negative keywords.

Every result stores human-readable reasons so you can see why it received its score.

## Adding another platform

Implement the same small adapter boundary used by Threads:

```text
search_recent(...)
validate_identity()
validate_search_capability()
validate_reply_capability()
publish_reply(...)
```

Keep platform-specific API details inside that adapter. Do not put platform detection inside the database or lead scorer.

## Troubleshooting

### `THREADS_ACCESS_TOKEN is required`

The token is not available in the process environment. Add it through your local secret/environment setup. Do not commit it.

### Audit says `missing scopes`

The current token was not authorized with everything the workflow needs. Update the Threads app/OAuth permission and obtain/refresh the correct token.

### Too many bad leads

Raise `min_score`, improve service phrases, add negative keywords, tighten target locations, or use more buyer-intent search phrases.

### Replies sound generic

Improve `business.description`, `services`, and `reply_style`. Only enable the optional LLM after the deterministic pipeline is already selecting good leads.

### Rate limited

Stop/reduce the schedule frequency. Do not create aggressive retries around `429` responses.

## Security rules

- Never commit `.env`, local config containing secrets, keys, certificates, database files, or credential folders.
- Never print full tokens/API keys in diagnostics.
- Keep live mode off after a fresh install.
- Treat permission errors as blockers, not something to bypass.
- Use conservative reply limits.
- Review dependency and API changes before updating production automation.

## Project structure

```text
src/social_lead_hunter/
  config.py              local non-secret configuration
  models.py              shared data models
  orchestrator.py        one lead-hunting cycle
  platforms/threads.py   official Threads API adapter
  qualification/         deterministic lead scoring
  replies/               reply drafting
  safety/                publish limits/cooldowns
  storage/               SQLite + optional Supabase
  llm/                   optional OpenAI-compatible drafting
skills/social-lead-hunter/
  SKILL.md                Hermes operating procedure
migrations/
  supabase.sql            optional generic Supabase schema
tests/                    mocked tests; no live publishing
```

## Development

Install test dependencies:

```bash
pip install -e .[dev]
```

Run tests:

```bash
pytest -q
```

No automated test should make a real Threads publish call.

## Project scope

The first release is deliberately small. It is not a CRM, billing system, SaaS dashboard, or browser scraper. The goal is a reliable lead-discovery engine that Hermes can configure and operate safely.

The repository preserves its upstream Git history while the current runtime is kept generic and vendor-neutral.
