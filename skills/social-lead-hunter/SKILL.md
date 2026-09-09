---
name: social-lead-hunter
description: Find recent public social posts with buying intent, qualify them, draft contextual replies, and optionally publish only after explicit approval and safety checks.
version: 0.2.0
metadata:
  hermes:
    tags: [social, leads, threads, automation, sales]
    category: productivity
    requires_toolsets: [terminal]
    config:
      - key: social_lead_hunter.config_path
        description: "Path to the local business configuration file. Keep it outside the Git repository."
        default: "~/.config/social-lead-hunter/config.yaml"
        prompt: "Where should Social Lead Hunter read its local config?"
---

# Social Lead Hunter

## Goal

Make setup as automatic as possible while keeping secrets out of GitHub and keeping live replies off until the operator explicitly approves them.

## Plain-language rule

When you need information from the operator, ask in plain language. Do not ask them to understand Python, YAML, APIs, scopes, or database internals.

## Safety rule

**Always start in dry-run mode. Never switch to live publishing without explicit operator approval.**

Dry-run means the engine may search, score, draft, and store leads, but it must not publish a social reply.

Never paste access tokens, app secrets, API keys, database keys, or passwords into this skill, a Git repository, config files committed to Git, chat output, logs, or command history when avoidable.

## Automatic setup procedure

1. Determine the local config path. Default to:

   ```text
   ~/.config/social-lead-hunter/config.yaml
   ```

2. Check whether the `social-lead-hunter` CLI exists.

3. If the CLI is missing, install the engine safely:

   - If you are already inside the repository root and `pyproject.toml` exists:

     ```bash
     python3 -m pip install -e .
     ```

   - Otherwise, if the operator supplied the GitHub repository URL, install directly from that repository URL:

     ```bash
     python3 -m pip install "git+<repository-url>"
     ```

   - If you do not know the repository URL, ask only for the **GitHub repository URL**. This is not a secret. Do not ask for any API key at this stage.

4. Run the one-command local setup:

   ```bash
   social-lead-hunter setup --config "$CONFIG_PATH"
   ```

   This creates a safe local config when missing, prepares SQLite when used, and leaves dry-run enabled. It does not overwrite an existing config unless `--force` is explicitly used.

5. Read the local config. If it still contains `CHANGE_ME` placeholders, configure it using information the operator already provided in the conversation when possible.

6. Only ask for missing non-secret business settings. Ask in plain language, for example:

   - What product or service should I look for customers asking about?
   - Which area or country should I focus on?
   - What words would customers normally use when asking for it?
   - Should replies be formal, casual, or mixed-language?
   - Is there an optional contact/CTA to add, or should replies stay contact-free?

   Do not ask all of these if the answers are already known.

7. Keep business configuration in the local config file, outside the repository. Keep credentials in environment variables or the operator's secret store.

8. Check environment readiness. If a secret is missing, report only the variable name, never a secret value. Required for Threads use:

   ```text
   THREADS_ACCESS_TOKEN
   ```

   Other variables are optional depending on storage/LLM configuration.

9. Run the capability audit:

   ```bash
   social-lead-hunter audit --config "$CONFIG_PATH"
   ```

10. If identity, keyword search, or reply capability is blocked, stop. Explain the problem in plain language and identify the missing permission/error. Do not bypass missing permission by scraping.

11. Run one dry-run cycle:

   ```bash
   social-lead-hunter run --config "$CONFIG_PATH"
   ```

12. Review the result quality. Tune local keywords, services, locations, exclusions, score threshold, and reply style if needed. Do not edit the engine for ordinary business configuration.

13. Only after the operator explicitly approves live replies may `runtime.dry_run` be changed to `false`.

14. Before live scheduling, run `audit` again and confirm the daily reply cap, minimum gap, and same-user cooldown are appropriate.

15. For recurring use, schedule the CLI through the operator's existing Hermes scheduler. Keep the engine's own safety limits enabled.

## Expected Threads permissions

For the current Threads workflow, the engine checks for the scopes needed for identity/search/reply capability, including:

- `threads_basic`
- `threads_keyword_search`
- `threads_content_publish`

Treat the engine's audit output and current official Meta Threads API documentation as the source of truth. If Meta changes an endpoint or scope, do not guess; update the adapter and tests first.

## Retry behavior

Temporary network failures and Threads `5xx` provider failures may be retried a small bounded number of times. Authentication errors, permission errors, normal `4xx` errors, and `429` rate limits must fail immediately rather than being hammered with retries.

## Supabase rule

Supabase is optional. The provided migration enables Row Level Security and is intended for trusted server-side automation access. Never expose a server-side Supabase key in browser/client code or GitHub.

## Good lead behavior

Prefer posts that show concrete intent, for example:

- asking for a supplier/service provider;
- asking for a recommendation or quotation;
- mentioning quantity, size, deadline, price, budget, or location;
- recent posts relevant to the configured services.

Reject or heavily down-rank:

- the operator's own posts;
- other suppliers promoting themselves;
- recruitment/vacancies;
- giveaways/spam;
- stale or unrelated discussions;
- configured negative keywords.

## Reply behavior

Drafts should be short and specific to the original post. Do not claim pricing, stock, location coverage, certifications, turnaround time, or capability unless that information is explicitly available in local configuration/context.

Do not force a CTA into every reply. If no CTA is configured, do not invent one.

## Verification

A safe setup has all of these properties:

- the CLI is installed from the intended repository;
- `social-lead-hunter setup` succeeds;
- capability audit passes before live mode;
- first run is dry-run;
- dry-run produces zero publish calls;
- duplicate post IDs are not handled twice;
- same-user cooldown and daily limits are active;
- credentials are only in environment/secret storage;
- the operator explicitly approved live mode.

If any item is uncertain, stay in dry-run.
