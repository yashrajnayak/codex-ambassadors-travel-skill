---
name: codex-ambassadors-travel-skill
description: Add or update Codex Ambassador travel plans in the private codex-ambassadors-travel GitHub repo by creating correctly formatted travel-plan issues with GitHub CLI. Use when a Codex Ambassador asks Codex to add a trip, submit travel dates, choose up to three destination cities, add a new ambassador, add a new destination city, or update the travel dashboard through the repo automation.
---

# Codex Ambassadors Travel Skill

## Overview

Use this skill to submit Codex Ambassador trips through the private travel repo's issue automation. Create travel-plan issues; do not edit the private repo's `data/*.json` files directly for ambassador submissions.

Default target repo: `yashrajnayak/codex-ambassadors-travel`.

## Workflow

1. Check GitHub access.
   ```bash
   gh auth status
   gh repo view yashrajnayak/codex-ambassadors-travel --json nameWithOwner,visibility
   ```
   If this fails, explain that the ambassador needs collaborator access to the private repo before the skill can submit a trip.

2. Gather the trip fields.
   - Ambassador: existing ambassador name, or a new ambassador name with optional LinkedIn URL.
   - Destinations: one to three city labels in `City, Country` format.
   - Dates: tentative arrival and departure for each city, using `YYYY-MM-DD`.
   - Optional availability and contact details.
   - If a city is not tracked, use `Other / add a new city` and provide `--new-city` plus `--new-country`.

3. Discover current dropdown options when needed.
   ```bash
   python scripts/add_travel_issue.py --repo yashrajnayak/codex-ambassadors-travel --list cities
   python scripts/add_travel_issue.py --repo yashrajnayak/codex-ambassadors-travel --list ambassadors
   ```

4. Dry-run the issue body before creating it when the user gave free-form data or a new city.
   ```bash
   python scripts/add_travel_issue.py \
     --repo yashrajnayak/codex-ambassadors-travel \
     --ambassador "Yashraj Nayak" \
     --destination "Tokyo, Japan|2026-05-20|2026-05-24" \
     --availability "Evenings after 6 PM" \
     --contact "Comment on the issue" \
     --dry-run
   ```

5. Create the issue.
   ```bash
   python scripts/add_travel_issue.py \
     --repo yashrajnayak/codex-ambassadors-travel \
     --ambassador "Yashraj Nayak" \
     --destination "Tokyo, Japan|2026-05-20|2026-05-24" \
     --availability "Evenings after 6 PM" \
     --contact "Comment on the issue"
   ```

6. Return the issue URL and tell the user the repo automation will reformat the title/body, update the dashboard data, label possible duplicates, and refresh the README.

## Script Usage

Use `scripts/add_travel_issue.py` for deterministic submissions.

For a new ambassador:
```bash
python scripts/add_travel_issue.py \
  --new-ambassador-name "Ada Lovelace" \
  --new-ambassador-linkedin "https://www.linkedin.com/in/example/" \
  --destination "London, United Kingdom|2026-06-15|2026-06-18"
```

For multiple destinations:
```bash
python scripts/add_travel_issue.py \
  --ambassador "Yashraj Nayak" \
  --destination "London, United Kingdom|2026-06-15|2026-06-18" \
  --destination "Paris, France|2026-06-19|2026-06-22" \
  --destination "Berlin, Germany|2026-06-23|2026-06-25"
```

For a new destination city:
```bash
python scripts/add_travel_issue.py \
  --ambassador "Yashraj Nayak" \
  --destination "Other / add a new city|2026-06-15|2026-06-18" \
  --new-city "Lisbon" \
  --new-country "Portugal"
```

## Guardrails

- Submit at most three destinations per issue.
- Keep each destination date range valid: departure must be on or after arrival.
- Use `--new-ambassador-name` only when the ambassador is not already in the dashboard data.
- Use `--new-city` and `--new-country` only for one new city per issue; the current issue template has one new-city field.
- Use existing city labels exactly when possible. If unsure, list cities first.
- Do not add local filesystem paths, private tokens, Slack-only identifiers, or travel details the user did not approve for the dashboard.
- If `gh issue create` succeeds, do not manually rewrite the title or body. The private repo automation owns that cleanup.

## References

Read `references/travel-issue-contract.md` when changing the submission body shape or debugging parser failures.
