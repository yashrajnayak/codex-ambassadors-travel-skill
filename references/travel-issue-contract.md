# Travel Issue Contract

The private dashboard repo processes travel submissions from GitHub issues. The issue can be created by the GitHub issue form or by this skill's script, as long as the body uses the same markdown headings.

## Target

- Default repo: `yashrajnayak/codex-ambassadors-travel`
- Issue title: `WILL BE UPDATED BY AUTOMATION`
- Labels: `travel-plan`, `dashboard`, `status: needs-review`

## Constants

- Existing or new ambassador selector value: `Other / add a new ambassador`
- Existing or new city selector value: `Other / add a new city`
- Empty optional city selector value: `No additional city`
- Empty new city country selector value: `No new city`
- Consent text: `I am okay with this trip appearing in the private repo README dashboard.`

## Parsed Headings

The private repo parser reads these `###` headings:

- `Ambassador`
- `New ambassador name`
- `New ambassador LinkedIn`
- `Destination City`
- `Destination City tentative arrival date`
- `Destination City tentative departure date`
- `Destination City 2`
- `Destination City 2 tentative arrival date`
- `Destination City 2 tentative departure date`
- `Destination City 3`
- `Destination City 3 tentative arrival date`
- `Destination City 3 tentative departure date`
- `New destination city`
- `New destination country`
- `When are you free to meet?`
- `Best way to coordinate`
- `Dashboard consent`

Blank optional values should be rendered as `_No response_`. Dashboard consent should be rendered as a checked markdown checkbox.

## Automation Behavior

After an issue is created, the private repo action:

1. Parses the issue form markdown.
2. Validates ambassador, city, country, and date fields.
3. Adds new ambassadors or destination cities to the source JSON when requested.
4. Writes one trip record per destination.
5. Detects possible duplicate trips for the same ambassador, city, and overlapping dates.
6. Rewrites the issue title and body into a cleaner summary.
7. Refreshes the README dashboard.

The skill should only create the issue and report the issue URL. The private repo automation owns all data updates.
