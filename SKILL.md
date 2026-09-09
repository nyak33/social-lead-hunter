---
name: social-lead-hunter
description: Generic Hermes workflow for finding, qualifying, and safely replying to public social buying-intent posts.
version: 0.2.0
---

# Social Lead Hunter

The canonical Hermes skill is:

`skills/social-lead-hunter/SKILL.md`

For a fresh install, the intended flow is:

```text
install engine from repository URL
        ↓
social-lead-hunter setup
        ↓
fill local non-secret business settings
        ↓
audit Threads permissions
        ↓
dry-run
        ↓
explicit approval before live replies
```

Business-specific settings and secrets stay local. Do not commit them to this repository.
