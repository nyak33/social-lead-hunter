# Generic Social Lead Hunter — Design

Date: 2026-09-09
Status: Proposed for implementation

## Objective

Turn the fork into a generic, reusable social lead-hunting engine that Hermes can install or reference from GitHub and configure locally for any business. The repository must contain no business-specific names, contact details, credentials, tokens, API keys, customer data, or server-specific secrets.

## Success criteria

- Hermes can use the repository without editing core source code.
- Business profile, services, keywords, locations, reply style, CTA/contact details, thresholds, credentials, and runtime limits are supplied only through local config/environment variables.
- Threads support uses the official API for keyword discovery and reply publishing.
- The engine is safe by default: `DRY_RUN=true`, no automatic publishing after install, bounded retries, duplicate protection, user cooldowns, and daily reply caps.
- Existing useful lead-scoring ideas are preserved while the monolithic worker and platform-detection bug are removed.
- No secret values are committed or logged.
- Automated tests cover qualification, dedupe, configuration, dry-run behavior, and platform adapters.

## Current repository findings

The fork currently has a monolithic `worker.py` that combines platform retrieval, database access, AI qualification, and scheduling. It is focused on Reddit/X, contains platform inference that can disagree between lookup and insert paths, and uses an InsForge/OpenRouter-specific environment example. The repository also includes an unrelated SaaS frontend and agent configuration from the upstream project.

## Approaches considered

### 1. Minimal patch

Keep `worker.py` and add Threads functions directly.

Pros: fastest initial implementation.
Cons: preserves tight coupling, makes Hermes reuse harder, keeps vendor-specific assumptions, and makes testing/rate limiting/dedupe harder to reason about.

### 2. Modular refactor while keeping the legacy SaaS app

Refactor the backend into adapters and keep the existing frontend alongside it.

Pros: retains all upstream UI work.
Cons: the UI is not needed for Hermes, carries legacy branding/backend assumptions, and increases maintenance surface.

### 3. Generic engine + Hermes skill — selected

Keep the useful lead-hunting concepts, refactor them into a small platform-agnostic Python package, add a Hermes skill, and remove runtime dependency on the legacy SaaS frontend/InsForge setup.

Pros: smallest maintainable surface for the actual goal, reusable across businesses, easy to test, safest for secrets, and easy for Hermes to configure.
Cons: larger refactor than a one-file patch.

## Architecture

```text
Hermes / CLI
    |
    v
Local business config + environment secrets
    |
    v
Lead Hunter Orchestrator
    |-- Platform adapter(s)
    |     `-- Threads official API
    |-- Qualification pipeline
    |     |-- intent
    |     |-- service/product relevance
    |     |-- location
    |     |-- freshness
    |     `-- exclusions: self / competitor / spam / duplicate
    |-- Reply generator
    |-- Safety / rate-limit policy
    `-- Storage adapter
          |-- SQLite (safe local default)
          `-- Supabase (optional)
```

## Proposed repository layout

```text
README.md
SKILL.md
.env.example
config.example.yaml
pyproject.toml
src/social_lead_hunter/
  __init__.py
  cli.py
  config.py
  models.py
  orchestrator.py
  platforms/
    base.py
    threads.py
  qualification/
    rules.py
    scorer.py
  replies/
    generator.py
  storage/
    base.py
    sqlite.py
    supabase.py
  safety/
    policy.py
  llm/
    base.py
    openai_compatible.py
migrations/
  supabase.sql
skills/
  social-lead-hunter/
    SKILL.md
tests/
```

A root `SKILL.md` will provide a convenient entry point; `skills/social-lead-hunter/SKILL.md` will contain the canonical Hermes skill definition.

## Configuration model

All business-specific behavior lives in an ignored local configuration file. The repository includes only `config.example.yaml` with neutral placeholders.

Configurable fields include:

- business description
- services/products
- positive and negative keywords
- target locations
- search freshness window
- minimum qualification score
- reply language/style instructions
- optional CTA/contact text
- maximum replies per day
- minimum gap between replies
- same-user cooldown
- enabled platforms
- storage backend
- LLM provider/model
- dry-run/live mode

Secrets are environment variables only.

## Security design

`.env.example` contains variable names and placeholder values only. `.gitignore` blocks `.env`, local config, credentials, tokens, PEM/key files, generated databases, and secret directories.

The application will:

- never print full tokens, API keys, passwords, or authorization headers;
- mask sensitive values in diagnostics;
- use HTTP timeouts;
- avoid retrying authentication/permission failures indefinitely;
- default to dry-run;
- require explicit live mode plus valid reply capability before publishing;
- never store secrets inside lead records;
- use parameterized SQL / SDK calls;
- avoid logging full response bodies when they may contain credentials.

No real account identifiers, business names, phone numbers, customer data, Supabase URLs, Threads tokens, or LLM keys will be committed.

## Threads adapter

The Threads adapter will expose a small interface:

- `search_recent(query, limit, since)`
- `validate_identity()`
- `validate_search_capability()`
- `validate_reply_capability()`
- `publish_reply(post_id, text)`

The implementation will use the current official Meta Threads API and configurable API version/base URL. Permission names and endpoint behavior will be verified against current official documentation during implementation instead of being guessed.

Live reply publishing is disabled unless both local configuration and capability checks allow it.

## Qualification pipeline

Each candidate is normalized to a platform-independent `SocialPost` model and scored 0–100.

Signals include:

- direct buying/service intent;
- service/product relevance;
- location relevance;
- freshness;
- specificity such as quantity, deadline, budget, dimensions, or requirement details.

Negative/exclusion signals include:

- own account;
- competitors/suppliers advertising themselves;
- vacancies/recruitment;
- spam/giveaways;
- unrelated discussions/news/memes;
- stale posts;
- unsupported location when location is required.

The result stores score plus human-readable reasons. Rules provide deterministic baseline scoring; an optional LLM can refine classification and draft replies.

## Deduplication and safety

Primary dedupe key: `(platform, external_post_id)`.

Additional controls:

- never reply twice to the same post;
- configurable cooldown per username;
- daily reply cap;
- minimum interval between live replies;
- exclude own account;
- verify candidate still exists before publishing when practical;
- record failed/skipped/qualified/replied states.

## Reply generation

Replies are short, contextual, and based on the original post plus local business/service configuration. No fixed business name, phone number, or CTA is embedded in code.

The generator supports:

- deterministic template fallback when no LLM is configured;
- OpenAI-compatible LLM endpoint for Hermes-compatible/provider-flexible use;
- configurable language and tone instructions;
- optional CTA only when configured.

## Storage

SQLite is the safe zero-setup default for generic/local use.

An optional Supabase adapter supports the user's existing infrastructure without making Supabase mandatory. The repository will include a generic SQL migration with no project-specific URL or key.

Lead records store normalized post data, qualification result, draft reply, state, timestamps, and publish result identifiers only.

## Hermes integration

The Hermes skill instructs Hermes to:

1. install/reference this repository;
2. create local config from the example outside source control;
3. resolve credentials from its environment/secret store;
4. run capability audit before first use;
5. start in dry-run;
6. review sample qualified leads;
7. enable live mode only after explicit operator approval.

Hermes can replace or override the built-in LLM adapter with its own model/fallback routing while keeping the lead-hunter engine deterministic around retrieval, dedupe, safety, and storage.

## Legacy files

The implementation branch will remove or retire files that exist only for the upstream SaaS/InsForge application when they are not required by the generic lead-hunter engine. Git history preserves the original fork content.

No unrelated redesign work will be performed.

## Error handling

Explicit handling will cover:

- invalid/expired credentials;
- missing API permissions;
- rate limits;
- network timeouts;
- 5xx provider failures;
- invalid/deleted posts;
- malformed LLM output;
- storage failure;
- duplicate candidate processing.

4xx authentication/permission errors fail fast and surface an actionable diagnostic instead of entering retry loops.

## Testing strategy

Tests will be written before production behavior where practical and will use mocked HTTP/storage boundaries.

Required coverage:

- config validation and secret masking;
- post normalization;
- deterministic score rules;
- self/competitor/spam exclusion;
- dedupe correctness;
- username cooldown;
- daily/gap rate limits;
- Threads request construction and error mapping;
- dry-run guarantees zero publish calls;
- live mode refuses to publish without capability validation;
- Supabase and SQLite storage contracts;
- end-to-end dry-run using fixtures.

No test will publish a real Threads reply.

## Non-goals for first release

- full SaaS dashboard;
- multi-tenant billing/authentication;
- browser scraping where an official API exists;
- autonomous live replying immediately after installation;
- hardcoded business-specific scoring;
- complex analytics/CRM features.

These can be added later without changing the core platform/storage interfaces.
