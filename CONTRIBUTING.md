# Contributing to factura_electronica_gt

Thank you for helping improve electronic invoicing (FEL) for Guatemala on Frappe/ERPNext.

## Branches

| Branch | Intent |
| --- | --- |
| `production-v13` | ERPNext / Frappe **v13** line |
| `production-v14` / `production-v15` | Newer ERPNext lines (do not mix PRs without intent) |

Open pull requests against the branch that matches the ERPNext major version you tested.

## Security & privacy (public repository)

This repository is **public**. Never publish:

- Production hostnames, site URLs, or server paths  
- Customer NIT, tokens, PFX material, `llave_pfx` / `llave_ws`, or API keys  
- Staff personal data beyond what is needed  

Use generic placeholders: `<site>`, `/path/to/frappe-bench`, “customer production site”, redacted error payloads (codes only when possible).

## Issue hygiene — 4-year policy

1. **Stale threshold:** Issues **older than 4 years**, or with **no meaningful activity for 4 years**, may be closed as **stale** without implementing the request.
2. **Backlog epics:** Long-lived ideas may be summarized under open issues labeled `backlog-epic`. Those epics are **triage archives**, not delivery commitments.
3. **Before closing as stale:** Maintainers may point the issue at a backlog epic. Detail remains in the closed issue history.
4. **Reopen policy:** Prefer a **new issue** with current product context over reopening a multi-year-old ticket.
5. **Cadence:** Maintainers should review open issues at least **yearly** (or after major releases).

Labels commonly used:

- `stale` — closed or marked under this policy  
- `backlog-epic` — umbrella tracker only  
- `bug` / `enhancement` / `wontfix` / `duplicate` — standard triage  

## Pull requests

- Keep secrets out of commits and PR descriptions.  
- Reference issues with `Fixes #NNN` / `Closes #NNN` when appropriate.  
- Note the ERPNext version and app branch you used for testing.

## Support

Product questions for a specific deployment belong with that site’s operator or implementer—not as a dump of production config in a public issue.
