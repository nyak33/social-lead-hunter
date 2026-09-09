# Generic Social Lead Hunter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a generic, reusable social lead-hunting engine with official Threads search/reply support, configurable lead scoring, safe dry-run behavior, optional Supabase storage, and a Hermes skill that can be configured locally without committing secrets.

**Architecture:** Refactor the current monolithic worker into a small Python package with clear interfaces for platform retrieval, qualification, reply generation, safety controls, and storage. Threads is the first production platform adapter; SQLite is the safe local default and Supabase is optional. Hermes supplies business-specific config and secrets locally, while GitHub contains only generic code and examples.

**Tech Stack:** Python 3.11+, `requests`, `PyYAML`, standard-library `sqlite3`, `pytest`, optional Supabase REST calls through `requests`.

**Spec:** `docs/superpowers/specs/2026-09-09-generic-social-lead-hunter-design.md`

## Global Constraints

- Repository code and docs must remain generic: no business names, personal contacts, customer data, real account identifiers, project-specific URLs, tokens, keys, or passwords.
- Secrets must come from environment variables only.
- `DRY_RUN=true` is the default and live publishing must require both explicit configuration and a successful capability check.
- Threads integration must use the official API; as of 2026-09-09 Meta's official Threads Postman workspace documents `GET /keyword_search` with `search_type=RECENT|TOP`, and replies through `POST /me/threads` with `reply_to_id`.
- Minimum expected scopes for the documented flow are `threads_basic`, `threads_keyword_search`, and `threads_content_publish`; implementation must surface missing-scope errors instead of assuming access.
- No test may publish a real Threads reply.
- Existing upstream history stays intact; implementation occurs on `upgrade/generic-lead-hunter` and `main` remains untouched until review.
- Keep dependencies minimal and avoid introducing a new hosted backend requirement.

---

## File Map

- `pyproject.toml` — packaging, runtime dependencies, CLI entry point, test config.
- `.env.example` — environment variable names only; no realistic secret values.
- `.gitignore` — blocks local config, environment files, private keys, local databases, credentials, caches, and generated artifacts.
- `config.example.yaml` — neutral sample business/search/scoring/reply/safety configuration.
- `src/social_lead_hunter/models.py` — shared post, qualification, reply, capability, and lead-record dataclasses.
- `src/social_lead_hunter/config.py` — YAML loading, defaults, validation, and environment-secret lookup.
- `src/social_lead_hunter/platforms/base.py` — platform adapter protocol and common exceptions.
- `src/social_lead_hunter/platforms/threads.py` — official Threads API adapter.
- `src/social_lead_hunter/qualification/scorer.py` — deterministic scoring and exclusion logic.
- `src/social_lead_hunter/safety/policy.py` — dry-run, daily cap, minimum-gap, and same-user cooldown policy.
- `src/social_lead_hunter/storage/base.py` — storage protocol.
- `src/social_lead_hunter/storage/sqlite.py` — zero-setup local storage and dedupe.
- `src/social_lead_hunter/storage/supabase.py` — optional Supabase REST adapter.
- `src/social_lead_hunter/replies/generator.py` — safe deterministic fallback and optional LLM-generated reply.
- `src/social_lead_hunter/llm/openai_compatible.py` — generic OpenAI-compatible HTTP client.
- `src/social_lead_hunter/orchestrator.py` — search → dedupe → qualify → draft → safety → publish/log pipeline.
- `src/social_lead_hunter/cli.py` — `audit`, `run`, and `show-config` commands.
- `migrations/supabase.sql` — generic schema for optional Supabase storage.
- `skills/social-lead-hunter/SKILL.md` — canonical Hermes skill instructions.
- `SKILL.md` — short pointer/entry file for agents that look at repository root.
- `README.md` — layman-friendly setup, Hermes usage, safety model, troubleshooting, and security notes.
- `tests/` — mocked unit/integration tests; no live social API writes.

---

### Task 1: Secure package/config baseline

**Files:**
- Create: `pyproject.toml`
- Create: `config.example.yaml`
- Modify: `.env.example`
- Modify: `.gitignore`
- Create: `src/social_lead_hunter/__init__.py`
- Create: `src/social_lead_hunter/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `load_config(path: str) -> AppConfig`, `mask_secret(value: str | None) -> str`, `AppConfig` dataclass.
- Later tasks consume `AppConfig` for all runtime settings.

- [ ] **Step 1: Write failing config/security tests**

```python
from pathlib import Path
import os
import pytest

from social_lead_hunter.config import load_config, mask_secret


def test_default_dry_run_is_true(tmp_path: Path):
    p = tmp_path / "config.yaml"
    p.write_text("business:\n  description: generic service provider\nsearch:\n  keywords: [service]\n", encoding="utf-8")
    cfg = load_config(str(p))
    assert cfg.runtime.dry_run is True


def test_missing_keywords_is_rejected(tmp_path: Path):
    p = tmp_path / "config.yaml"
    p.write_text("business:\n  description: test\n", encoding="utf-8")
    with pytest.raises(ValueError, match="keywords"):
        load_config(str(p))


def test_mask_secret_never_returns_full_value():
    secret = "abcd1234SUPERSECRET"
    masked = mask_secret(secret)
    assert secret not in masked
    assert masked.endswith("CRET")
```

- [ ] **Step 2: Run tests and verify they fail**

Run: `pytest tests/test_config.py -v`

Expected: import/module failures because package/config code does not exist yet.

- [ ] **Step 3: Add minimal package/config implementation**

Implement dataclasses for:

```python
@dataclass
class RuntimeConfig:
    dry_run: bool = True
    max_replies_per_day: int = 5
    min_reply_gap_minutes: int = 30
    same_user_cooldown_days: int = 7

@dataclass
class SearchConfig:
    keywords: list[str]
    freshness_hours: int = 24
    min_score: int = 80
    target_locations: list[str] = field(default_factory=list)
    negative_keywords: list[str] = field(default_factory=list)

@dataclass
class BusinessConfig:
    description: str
    services: list[str] = field(default_factory=list)
    reply_style: str = "helpful, concise, contextual"
    cta: str = ""

@dataclass
class AppConfig:
    business: BusinessConfig
    search: SearchConfig
    runtime: RuntimeConfig
    storage_backend: str = "sqlite"
    llm_enabled: bool = False
```

`load_config()` must parse YAML, validate at least one keyword, validate score 0–100, reject non-positive reply limits, and default `dry_run` to `True` when omitted.

`mask_secret()` behavior:
- `None`/empty -> `"<unset>"`
- length <= 4 -> `"****"`
- otherwise -> `"****" + last 4 characters`

- [ ] **Step 4: Harden ignored-secret patterns**

Ensure `.gitignore` includes:

```gitignore
.env
.env.*
!.env.example
config.yaml
config.local.yaml
credentials/
secrets/
*.pem
*.key
*.p12
*.pfx
*.sqlite
*.sqlite3
*.db
```

Replace `.env.example` with names/placeholders only:

```env
THREADS_ACCESS_TOKEN=
THREADS_USER_ID=
THREADS_API_BASE=https://graph.threads.net
THREADS_API_VERSION=
SUPABASE_URL=
SUPABASE_KEY=
LLM_API_BASE=
LLM_API_KEY=
LLM_MODEL=
```

- [ ] **Step 5: Add neutral example config**

`config.example.yaml` must include a generic sample with `dry_run: true`, neutral services/keywords/locations, score threshold 80, daily cap 5, 30-minute gap, and 7-day same-user cooldown.

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_config.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .env.example .gitignore config.example.yaml src/social_lead_hunter tests/test_config.py
git commit -m "feat: add secure generic configuration baseline"
```

---

### Task 2: Shared models and deterministic qualification

**Files:**
- Create: `src/social_lead_hunter/models.py`
- Create: `src/social_lead_hunter/qualification/__init__.py`
- Create: `src/social_lead_hunter/qualification/scorer.py`
- Test: `tests/test_qualification.py`

**Interfaces:**
- Produces: `SocialPost`, `QualificationResult`, `qualify_post(post, config, own_username=None)`.
- `QualificationResult` fields: `score: int`, `qualified: bool`, `excluded: bool`, `reasons: list[str]`, `intent: str`, `location_detected: str | None`, `service_detected: str | None`.

- [ ] **Step 1: Write failing qualification tests**

```python
from datetime import datetime, timezone

from social_lead_hunter.models import SocialPost
from social_lead_hunter.qualification.scorer import qualify_post


def test_direct_request_scores_high(app_config):
    post = SocialPost(
        platform="threads",
        external_id="p1",
        username="buyer",
        text="Looking for a supplier for custom labels, need quotation urgently",
        permalink="https://example.invalid/p1",
        timestamp=datetime.now(timezone.utc),
    )
    result = qualify_post(post, app_config)
    assert result.score >= 80
    assert result.qualified is True


def test_self_post_is_excluded(app_config):
    post = SocialPost(platform="threads", external_id="p2", username="myaccount", text="looking for service", permalink="x", timestamp=datetime.now(timezone.utc))
    result = qualify_post(post, app_config, own_username="myaccount")
    assert result.excluded is True
    assert result.score == 0


def test_supplier_advertisement_is_not_a_buying_lead(app_config):
    post = SocialPost(platform="threads", external_id="p3", username="vendor", text="We provide professional label printing. DM us now.", permalink="x", timestamp=datetime.now(timezone.utc))
    result = qualify_post(post, app_config)
    assert result.excluded is True or result.score < app_config.search.min_score
```

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/test_qualification.py -v`

Expected: missing model/scorer failures.

- [ ] **Step 3: Implement `SocialPost` and `QualificationResult` dataclasses**

`SocialPost` fields:

```python
platform: str
external_id: str
username: str
text: str
permalink: str
timestamp: datetime
raw: dict[str, Any] = field(default_factory=dict)
```

- [ ] **Step 4: Implement deterministic scoring**

Use transparent rules with capped final score 0–100:

```text
+35 direct request words: looking for, need, cari, recommend, recommendation, supplier, quotation, quote, siapa boleh, anyone can, urgent
+25 configured service/product phrase match
+15 requirement specificity: quantity/qty/MOQ/size/budget/deadline/urgent/price
+10 configured target-location match when target locations exist
+10 post age <= 6 hours
+5 post age <= 24 hours
-40 clear seller/self-promotion wording: we provide, kami menyediakan, our service, dm us, contact us for
EXCLUDE own username, configured negative keyword, obvious vacancy/recruitment, spam/giveaway
```

A post is `qualified=True` only when it is not excluded and score >= configured `min_score`.

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_qualification.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/social_lead_hunter/models.py src/social_lead_hunter/qualification tests/test_qualification.py
git commit -m "feat: add transparent lead qualification"
```

---

### Task 3: Storage contracts, dedupe, and cooldown history

**Files:**
- Create: `src/social_lead_hunter/storage/__init__.py`
- Create: `src/social_lead_hunter/storage/base.py`
- Create: `src/social_lead_hunter/storage/sqlite.py`
- Create: `src/social_lead_hunter/storage/supabase.py`
- Create: `migrations/supabase.sql`
- Test: `tests/test_storage.py`

**Interfaces:**
- Produces storage methods:
  - `has_post(platform: str, external_id: str) -> bool`
  - `save_candidate(post: SocialPost, result: QualificationResult, draft_reply: str | None, status: str) -> None`
  - `mark_replied(platform: str, external_id: str, reply_id: str) -> None`
  - `last_reply_to_user(username: str) -> datetime | None`
  - `replies_since(since: datetime) -> list[datetime]`

- [ ] **Step 1: Write failing SQLite contract tests**

```python
from datetime import datetime, timezone

from social_lead_hunter.storage.sqlite import SQLiteStorage


def test_post_dedupe(tmp_path):
    db = SQLiteStorage(str(tmp_path / "lead.db"))
    db.save_raw_post("threads", "abc", "user", "text", "url", datetime.now(timezone.utc))
    assert db.has_post("threads", "abc") is True
    assert db.has_post("threads", "different") is False


def test_same_platform_id_is_unique(tmp_path):
    db = SQLiteStorage(str(tmp_path / "lead.db"))
    now = datetime.now(timezone.utc)
    db.save_raw_post("threads", "abc", "u", "x", "url", now)
    db.save_raw_post("threads", "abc", "u", "x", "url", now)
    assert db.count_posts() == 1
```

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/test_storage.py -v`

Expected: missing storage implementation.

- [ ] **Step 3: Implement SQLite schema and adapter**

Use parameterized SQL and unique key `(platform, external_id)`. Tables:

```sql
CREATE TABLE posts (..., UNIQUE(platform, external_id));
CREATE TABLE leads (..., UNIQUE(platform, external_id));
CREATE TABLE replies (...);
```

Persist timestamps in ISO-8601 UTC.

- [ ] **Step 4: Add generic Supabase migration**

`migrations/supabase.sql` must create `social_lead_posts`, `social_leads`, and `social_lead_replies` with the same uniqueness/cooldown information and no project-specific URLs or credentials.

- [ ] **Step 5: Implement Supabase REST adapter**

Use `${SUPABASE_URL}/rest/v1/...` with headers built from `SUPABASE_KEY`, HTTP timeouts, and no secret logging. If URL/key are absent, raise a clear `ValueError` before making a request.

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_storage.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/social_lead_hunter/storage migrations/supabase.sql tests/test_storage.py
git commit -m "feat: add generic lead storage and dedupe"
```

---

### Task 4: Safety policy for dry-run, caps, gap, and user cooldown

**Files:**
- Create: `src/social_lead_hunter/safety/__init__.py`
- Create: `src/social_lead_hunter/safety/policy.py`
- Test: `tests/test_safety.py`

**Interfaces:**
- Produces: `SafetyDecision(allowed: bool, reason: str)`, `can_publish(config, storage, username, now) -> SafetyDecision`.

- [ ] **Step 1: Write failing safety tests**

```python
def test_dry_run_blocks_publish(app_config, fake_storage, now):
    app_config.runtime.dry_run = True
    decision = can_publish(app_config, fake_storage, "buyer", now)
    assert decision.allowed is False
    assert "dry" in decision.reason.lower()


def test_daily_limit_blocks_publish(app_config, fake_storage, now):
    app_config.runtime.dry_run = False
    fake_storage.reply_times = [now] * app_config.runtime.max_replies_per_day
    assert can_publish(app_config, fake_storage, "buyer", now).allowed is False


def test_same_user_cooldown_blocks_publish(app_config, fake_storage, now):
    app_config.runtime.dry_run = False
    fake_storage.last_user_reply = now
    assert can_publish(app_config, fake_storage, "buyer", now).allowed is False
```

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/test_safety.py -v`

Expected: missing safety policy.

- [ ] **Step 3: Implement ordered safety checks**

Order:
1. dry-run -> block live publish;
2. daily reply count >= cap -> block;
3. newest reply is within minimum gap -> block;
4. same username was replied to inside cooldown days -> block;
5. otherwise allow.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_safety.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/social_lead_hunter/safety tests/test_safety.py
git commit -m "feat: add conservative publishing safety policy"
```

---

### Task 5: Official Threads platform adapter and capability audit

**Files:**
- Create: `src/social_lead_hunter/platforms/__init__.py`
- Create: `src/social_lead_hunter/platforms/base.py`
- Create: `src/social_lead_hunter/platforms/threads.py`
- Test: `tests/test_threads_adapter.py`

**Interfaces:**
- Produces `ThreadsAdapter` methods:
  - `validate_identity() -> CapabilityResult`
  - `validate_search_capability() -> CapabilityResult`
  - `validate_reply_capability() -> CapabilityResult`
  - `search_recent(query: str, limit: int = 50, since: datetime | None = None) -> list[SocialPost]`
  - `publish_reply(post_id: str, text: str) -> str`

- [ ] **Step 1: Pin current official API behavior in tests using mocked HTTP**

Test expected request construction:

```python
def test_search_uses_recent_keyword_search(session, adapter):
    adapter.search_recent("custom service", limit=5)
    request = session.last_request
    assert request.method == "GET"
    assert request.path.endswith("/keyword_search")
    assert request.params["q"] == "custom service"
    assert request.params["search_type"] == "RECENT"
    assert request.params["limit"] == 5


def test_reply_uses_reply_to_id(session, adapter):
    session.queue_json({"id": "reply-container-id"})
    adapter.publish_reply("source-post-id", "Helpful reply")
    request = session.last_request
    assert request.method == "POST"
    assert request.path.endswith("/me/threads")
    assert request.params["media_type"] == "TEXT"
    assert request.params["reply_to_id"] == "source-post-id"
```

Also test 401/403 mapping to `AuthenticationError` / `PermissionError`, 429 to `RateLimitError`, and 5xx to `ProviderError`.

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/test_threads_adapter.py -v`

Expected: missing adapter implementation.

- [ ] **Step 3: Implement generic platform exceptions/protocol**

Define:

```python
class PlatformError(RuntimeError): ...
class AuthenticationError(PlatformError): ...
class PermissionError(PlatformError): ...
class RateLimitError(PlatformError): ...
class ProviderError(PlatformError): ...
```

- [ ] **Step 4: Implement Threads search**

Base URL defaults to `https://graph.threads.net` unless `THREADS_API_BASE` is set. Send Bearer authorization header. Request fields must include at least `id,username,text,timestamp,permalink`. Normalize API results to `SocialPost`.

- [ ] **Step 5: Implement reply publishing**

Use the official documented create-text endpoint with `media_type=TEXT`, `text`, and `reply_to_id`. Return the API `id`. Do not log authorization headers or access tokens.

- [ ] **Step 6: Implement capability audit**

Audit must report:

```python
CapabilityResult(name="identity", ok=True|False, detail="...")
CapabilityResult(name="keyword_search", ok=True|False, detail="...")
CapabilityResult(name="reply", ok=True|False, detail="...")
```

Search capability is validated with a read-only harmless keyword query. Reply capability must be inferred from configured scopes/token inspection when available and from documented permission errors; it must not publish a test reply.

- [ ] **Step 7: Run tests**

Run: `pytest tests/test_threads_adapter.py -v`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/social_lead_hunter/platforms tests/test_threads_adapter.py
git commit -m "feat: add official Threads search and reply adapter"
```

---

### Task 6: Reply generator and optional OpenAI-compatible LLM

**Files:**
- Create: `src/social_lead_hunter/replies/__init__.py`
- Create: `src/social_lead_hunter/replies/generator.py`
- Create: `src/social_lead_hunter/llm/__init__.py`
- Create: `src/social_lead_hunter/llm/openai_compatible.py`
- Test: `tests/test_reply_generator.py`

**Interfaces:**
- Produces: `generate_reply(post, qualification, config, llm=None) -> str`.
- LLM client: `complete_json(system: str, user: str) -> dict`.

- [ ] **Step 1: Write failing reply tests**

```python
def test_fallback_reply_is_short_and_contextual(post, result, app_config):
    reply = generate_reply(post, result, app_config, llm=None)
    assert 1 <= len(reply.splitlines()) <= 3
    assert len(reply) <= 500
    assert "Hi kami menyediakan" not in reply


def test_cta_is_not_added_when_blank(post, result, app_config):
    app_config.business.cta = ""
    reply = generate_reply(post, result, app_config, llm=None)
    assert "contact" not in reply.lower()
```

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/test_reply_generator.py -v`

Expected: missing generator/client.

- [ ] **Step 3: Implement deterministic fallback**

Fallback must reference a detected service/requirement when possible, ask for the smallest useful missing detail, and append CTA only when configured. It must not invent price, availability, location coverage, certifications, or technical capability.

- [ ] **Step 4: Implement generic OpenAI-compatible client**

Environment variables: `LLM_API_BASE`, `LLM_API_KEY`, `LLM_MODEL`. Use `/chat/completions`, timeout 30 seconds, JSON response mode when supported by configured provider, and redact secrets from exceptions.

- [ ] **Step 5: Implement LLM prompt contract**

Require JSON:

```json
{"reply":"...","safe":true,"reason":"..."}
```

Reject malformed output, `safe=false`, empty replies, or replies >500 characters and fall back to deterministic generation.

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_reply_generator.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/social_lead_hunter/replies src/social_lead_hunter/llm tests/test_reply_generator.py
git commit -m "feat: add safe configurable reply generation"
```

---

### Task 7: Orchestrator and CLI with guaranteed dry-run behavior

**Files:**
- Create: `src/social_lead_hunter/orchestrator.py`
- Create: `src/social_lead_hunter/cli.py`
- Test: `tests/test_orchestrator.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `run_cycle(config, adapter, storage, llm=None) -> RunSummary`.
- CLI commands:
  - `social-lead-hunter audit --config config.yaml`
  - `social-lead-hunter run --config config.yaml`
  - `social-lead-hunter show-config --config config.yaml`

- [ ] **Step 1: Write failing end-to-end dry-run test**

```python
def test_dry_run_never_calls_publish(app_config, fake_adapter, fake_storage):
    app_config.runtime.dry_run = True
    fake_adapter.posts = [high_intent_post()]
    summary = run_cycle(app_config, fake_adapter, fake_storage)
    assert summary.qualified >= 1
    assert fake_adapter.publish_calls == []
```

Also test duplicate skipping, low-score rejection, and live mode refusing to publish when `validate_reply_capability().ok` is false.

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/test_orchestrator.py tests/test_cli.py -v`

Expected: missing orchestrator/CLI.

- [ ] **Step 3: Implement cycle pipeline**

For each configured keyword:
1. `search_recent()`;
2. skip duplicate `(platform, external_id)`;
3. save raw post;
4. qualify;
5. save rejected/qualified result;
6. generate draft for qualified leads;
7. apply safety policy;
8. if dry-run, store draft only;
9. if live, require successful reply capability before first publish;
10. publish only when safety decision allows;
11. mark reply or failure without losing the lead record.

- [ ] **Step 4: Implement concise `RunSummary`**

Fields:

```python
scanned: int
new_posts: int
qualified: int
rejected: int
duplicates: int
drafted: int
replied: int
failed: int
```

- [ ] **Step 5: Implement CLI**

`audit` prints masked environment status and capability results. `show-config` prints effective non-secret configuration. `run` prints summary and current mode (`DRY RUN` or `LIVE`). Never print secret values.

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_orchestrator.py tests/test_cli.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/social_lead_hunter/orchestrator.py src/social_lead_hunter/cli.py tests/test_orchestrator.py tests/test_cli.py
git commit -m "feat: add safe lead hunting runtime and CLI"
```

---

### Task 8: Hermes skill and layman-friendly README

**Files:**
- Create: `skills/social-lead-hunter/SKILL.md`
- Create: `SKILL.md`
- Create/Replace: `README.md`
- Test: `tests/test_docs_security.py`

**Interfaces:**
- Hermes skill is documentation/instruction-driven and invokes the CLI/config rather than embedding account secrets.

- [ ] **Step 1: Write docs security test**

```python
from pathlib import Path


def test_public_docs_do_not_contain_real_secret_patterns():
    text = "\n".join(
        p.read_text(encoding="utf-8")
        for p in [Path("README.md"), Path("SKILL.md"), Path("config.example.yaml"), Path(".env.example")]
    )
    forbidden = ["Bearer ey", "service_role", "sk-proj-", "ghp_", "xoxb-"]
    assert not any(token in text for token in forbidden)
```

- [ ] **Step 2: Write canonical Hermes skill**

The skill must instruct Hermes, in order:
1. clone/reference repo;
2. create local `config.yaml` from example;
3. resolve secrets from environment/secret store;
4. run `audit` first;
5. stop and report if search/reply permissions are missing;
6. run in dry-run;
7. review qualified examples;
8. require explicit operator approval before changing `dry_run` to false;
9. use scheduler only after successful dry-run verification.

- [ ] **Step 3: Write root `SKILL.md`**

Keep it short and point to `skills/social-lead-hunter/SKILL.md` as canonical.

- [ ] **Step 4: Replace upstream README with a generic README**

README sections, in this order:
- What this does, in plain language;
- Safety first: dry-run default;
- How the flow works;
- Requirements;
- Quick start;
- Hermes setup;
- Config explained field-by-field in plain language;
- Threads permissions/capability audit;
- Dry-run example;
- Live mode checklist;
- SQLite vs Supabase;
- CLI reference;
- How to add another platform adapter;
- Troubleshooting;
- Security rules;
- Project structure;
- Development/tests;
- Upstream attribution/license note if required by the fork's license/history.

README must explicitly say secrets belong in environment variables and must never be pasted into `config.yaml` or committed.

- [ ] **Step 5: Run docs/security tests**

Run: `pytest tests/test_docs_security.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add README.md SKILL.md skills/social-lead-hunter/SKILL.md tests/test_docs_security.py
git commit -m "docs: add Hermes skill and secure setup guide"
```

---

### Task 9: Remove legacy runtime coupling and run full verification

**Files:**
- Delete: `worker.py`
- Delete or retire: `frontend/` if it is unrelated to the generic engine
- Delete or replace: legacy InsForge-only agent/project files that are not needed for the engine
- Keep: design/plan docs and generic migrations
- Test: entire suite

**Interfaces:**
- Produces a repo whose documented runtime path is only the new package/CLI/Hermes skill.

- [ ] **Step 1: Confirm no new code imports legacy `worker.py`, InsForge SDK, frontend code, or old database schema**

Run:

```bash
grep -R "worker.py\|insforge\|leadscout.ai\|opencli\|twitter-cli" -n src tests README.md SKILL.md skills config.example.yaml pyproject.toml || true
```

Expected: no runtime dependency; historical/spec references may be reviewed manually if present.

- [ ] **Step 2: Remove obsolete runtime files**

Delete `worker.py`. Remove the upstream frontend and InsForge-only project instructions if they are not referenced by the new package. Preserve git history rather than copying old vendor-specific code into new modules.

- [ ] **Step 3: Run full test suite**

Run: `pytest -q`

Expected: all tests pass, zero live network publishing.

- [ ] **Step 4: Run syntax/import checks**

Run:

```bash
python -m compileall -q src
python -c "from social_lead_hunter.cli import main; print('import-ok')"
```

Expected: `import-ok` and exit code 0.

- [ ] **Step 5: Run secret scan over tracked text**

Run:

```bash
grep -R -n -E "(ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|xox[baprs]-|Bearer[[:space:]]+[A-Za-z0-9._-]{20,}|service_role[[:space:]]*=[[:space:]]*[^[:space:]]+)" . --exclude-dir=.git --exclude='*.lock' || true
```

Expected: no real credential-like values.

- [ ] **Step 6: Verify public example files contain no personal/business-specific strings**

Manually inspect:

```text
README.md
SKILL.md
skills/social-lead-hunter/SKILL.md
config.example.yaml
.env.example
migrations/supabase.sql
```

Expected: generic placeholders only.

- [ ] **Step 7: Commit cleanup**

```bash
git add -A
git commit -m "refactor: remove legacy app coupling"
```

---

### Task 10: Final review and pull request

**Files:**
- No production file changes unless verification finds a defect.

**Interfaces:**
- Produces a reviewable PR from `upgrade/generic-lead-hunter` to `main`.

- [ ] **Step 1: Compare branch against main**

Run:

```bash
git diff --stat main...upgrade/generic-lead-hunter
git diff --check main...upgrade/generic-lead-hunter
```

Expected: no whitespace errors; changes limited to the generic engine/docs/tests and removal of obsolete upstream runtime/UI files.

- [ ] **Step 2: Re-run full verification**

Run:

```bash
pytest -q
python -m compileall -q src
```

Expected: PASS.

- [ ] **Step 3: Review against spec**

Confirm each success criterion in `docs/superpowers/specs/2026-09-09-generic-social-lead-hunter-design.md` is either implemented or explicitly called out in PR notes. No undocumented live-posting behavior is allowed.

- [ ] **Step 4: Open PR**

PR title:

```text
feat: build generic Hermes social lead hunter
```

PR body must summarize:
- generic modular architecture;
- official Threads keyword search/reply adapter;
- dry-run/safety controls;
- SQLite + optional Supabase;
- Hermes skill + README;
- legacy cleanup;
- exact verification commands/results;
- confirmation that no live reply was published during tests.
