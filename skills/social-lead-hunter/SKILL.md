---
name: social-lead-hunter
description: Find recent public social posts with buying intent, qualify them, draft contextual replies, and optionally publish only after explicit approval and safety checks.
version: 0.1.0
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

## When to use

Use this skill when the operator wants Hermes to find recent public posts from people who appear to need a product or service, score the opportunity, draft a relevant reply, or run the lead-hunting workflow on a schedule.

The engine is intentionally generic. Business details, services, keywords, target locations, reply style, CTA, and limits come from the operator's local config file. Credentials come from environment variables or the operator's secret store.

## Safety rule

**Always start in dry-run mode. Never switch to live publishing without explicit operator approval.**

Dry-run means the engine may search, score, draft, and store leads, but it must not publish a social reply.

Never paste access tokens, app secrets, API keys, database keys, or passwords into this skill, a Git repository, `config.yaml`, chat output, logs, or command history when avoidable.

## Procedure

1. Resolve the configured local config path. Expand `~` before use.
2. Confirm the `social-lead-hunter` CLI is installed. If it is missing, stop and tell the operator the engine must first be installed from the repository into a local Python environment.
3. Confirm the local config exists. If not, copy `config.example.yaml` from the engine repository to the configured local path and ask the operator to fill in non-secret business settings.
4. Confirm `runtime.dry_run` is `true` before the first run.
5. Run the capability audit:

   ```bash
   social-lead-hunter audit --config "$CONFIG_PATH"
   ```

6. If identity, keyword search, or reply capability is blocked, stop. Report which capability failed and the missing scope/error. Do not try to work around a missing permission by scraping.
7. Run one dry-run cycle:

   ```bash
   social-lead-hunter run --config "$CONFIG_PATH"
   ```

8. Review the generated leads and drafts. Pay attention to false positives, competitors advertising themselves, irrelevant locations, duplicate users, and generic/spammy drafts.
9. Tune local keywords, services, locations, exclusions, score threshold, and reply style as needed. Do not edit the engine for normal business configuration.
10. Only after the operator explicitly says to enable live replies may `runtime.dry_run` be changed to `false`.
11. Before live scheduling, run `audit` again and confirm the daily reply cap, minimum gap, and same-user cooldown are appropriate.
12. For recurring use, schedule the CLI through the operator's existing Hermes scheduler. Keep the engine's own safety limits enabled.

## Expected Threads permissions

For the current Threads workflow, the engine checks for the scopes needed for identity/search/reply capability, including:

- `threads_basic`
- `threads_keyword_search`
- `threads_content_publish`

Treat the engine's audit output and current official Meta Threads API documentation as the source of truth. If Meta changes an endpoint or scope, do not guess; update the adapter and tests first.

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

- capability audit passes before live mode;
- first run is dry-run;
- dry-run produces zero publish calls;
- duplicate post IDs are not handled twice;
- same-user cooldown and daily limits are active;
- credentials are only in environment/secret storage;
- the operator explicitly approved live mode.

If any item is uncertain, stay in dry-run.
