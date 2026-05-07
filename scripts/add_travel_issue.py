#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import urlparse


DEFAULT_REPO = "yashrajnayak/codex-ambassadors-travel"
TITLE = "WILL BE UPDATED BY AUTOMATION"
LABELS = ["travel-plan", "dashboard", "status: needs-review"]

ADD_NEW_AMBASSADOR = "Other / add a new ambassador"
ADD_NEW_CITY = "Other / add a new city"
NO_ADDITIONAL_CITY = "No additional city"
NO_NEW_CITY = "No new city"
CONSENT_TEXT = "I am okay with this trip appearing in the private repo README dashboard."


@dataclass(frozen=True)
class Destination:
    city: str
    arrival: str
    departure: str


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def parse_iso_date(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{field} must use YYYY-MM-DD: {value}") from exc


def parse_destination(raw: str) -> Destination:
    parts = [part.strip() for part in raw.split("|")]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError(
            "--destination must be formatted as 'City, Country|YYYY-MM-DD|YYYY-MM-DD'"
        )
    city, arrival, departure = parts
    if not city:
        raise argparse.ArgumentTypeError("Destination city cannot be blank.")
    start = parse_iso_date(arrival, "Arrival date")
    end = parse_iso_date(departure, "Departure date")
    if end < start:
        raise argparse.ArgumentTypeError(
            f"Departure date must be on or after arrival date for {city}."
        )
    return Destination(city=city, arrival=arrival, departure=departure)


def run(command: list[str], *, capture: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        text=True,
        capture_output=capture,
    )


def require_gh() -> None:
    if not shutil.which("gh"):
        raise SystemExit("GitHub CLI is required. Install gh and authenticate before creating issues.")
    auth = run(["gh", "auth", "status"])
    if auth.returncode != 0:
        detail = (auth.stderr or auth.stdout).strip()
        raise SystemExit(f"gh is not authenticated.\n{detail}")


def require_repo_access(repo: str) -> None:
    result = run(["gh", "repo", "view", repo, "--json", "nameWithOwner", "--jq", ".nameWithOwner"])
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise SystemExit(
            f"Cannot access {repo}. Ask the repo owner to add this GitHub account as a collaborator.\n{detail}"
        )


def load_repo_json(repo: str, path: str) -> Any:
    result = run(["gh", "api", f"repos/{repo}/contents/{path}", "--jq", ".content"])
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise SystemExit(f"Could not read {path} from {repo}.\n{detail}")
    try:
        decoded = base64.b64decode(result.stdout).decode("utf-8")
        return json.loads(decoded)
    except (ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Could not decode {path} from {repo}: {exc}") from exc


def city_label(city: dict[str, Any]) -> str:
    return f"{city['city']}, {city['country']}"


def print_options(repo: str, option_type: str) -> None:
    require_gh()
    require_repo_access(repo)
    if option_type in {"ambassadors", "all"}:
        ambassadors = load_repo_json(repo, "data/ambassadors.json")
        print("Ambassadors")
        for ambassador in sorted(ambassadors, key=lambda item: item.get("name", "").casefold()):
            print(f"- {ambassador['name']}")
        if option_type == "all":
            print()
    if option_type in {"cities", "all"}:
        cities = load_repo_json(repo, "data/cities.json")
        print("Cities")
        for city in sorted(cities, key=lambda item: (item.get("city", ""), item.get("country", ""))):
            print(f"- {city_label(city)}")
        if option_type == "all":
            print()
    if option_type in {"countries", "all"}:
        countries = load_repo_json(repo, "data/countries.json")
        print("Countries")
        for country in countries:
            print(f"- {country}")


def issue_value(value: str | None) -> str:
    value = (value or "").strip()
    return value if value else "_No response_"


def issue_field(label: str, value: str | None) -> str:
    return f"### {label}\n\n{issue_value(value)}"


def build_issue_body(args: argparse.Namespace, destinations: list[Destination]) -> str:
    ambassador = ADD_NEW_AMBASSADOR if args.new_ambassador_name else args.ambassador
    fields: list[tuple[str, str | None]] = [
        ("Ambassador", ambassador),
        ("New ambassador name", args.new_ambassador_name),
        ("New ambassador LinkedIn", args.new_ambassador_linkedin),
    ]

    for index in range(3):
        destination = destinations[index] if index < len(destinations) else None
        suffix = "" if index == 0 else f" {index + 1}"
        city_label_text = f"Destination City{suffix}"
        arrival_label = f"Destination City{suffix} tentative arrival date"
        departure_label = f"Destination City{suffix} tentative departure date"
        if destination:
            fields.extend([
                (city_label_text, destination.city),
                (arrival_label, destination.arrival),
                (departure_label, destination.departure),
            ])
        else:
            fields.extend([
                (city_label_text, NO_ADDITIONAL_CITY),
                (arrival_label, None),
                (departure_label, None),
            ])

    fields.extend([
        ("New destination city", args.new_city),
        ("New destination country", args.new_country if args.new_city else NO_NEW_CITY),
        ("When are you free to meet?", args.availability),
        ("Best way to coordinate", args.contact),
    ])

    body = "\n\n".join(issue_field(label, value) for label, value in fields)
    body += f"\n\n### Dashboard consent\n\n- [x] {CONSENT_TEXT}\n"
    return body


def validate_submission(args: argparse.Namespace, destinations: list[Destination]) -> None:
    if len(destinations) > 3:
        raise SystemExit("Add up to three destinations per issue.")

    if args.ambassador and args.new_ambassador_name:
        raise SystemExit("Use either --ambassador or --new-ambassador-name, not both.")
    if not args.ambassador and not args.new_ambassador_name:
        raise SystemExit("Provide --ambassador for an existing ambassador or --new-ambassador-name for a new one.")
    if args.new_ambassador_linkedin and not args.new_ambassador_name:
        raise SystemExit("--new-ambassador-linkedin is only used with --new-ambassador-name.")
    if args.new_ambassador_linkedin:
        parsed = urlparse(args.new_ambassador_linkedin)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise SystemExit("--new-ambassador-linkedin must be a valid http(s) URL.")

    new_city_count = sum(1 for destination in destinations if destination.city == ADD_NEW_CITY)
    if new_city_count > 1:
        raise SystemExit("The current issue template supports one new destination city per issue.")
    if new_city_count and (not args.new_city or not args.new_country):
        raise SystemExit("Provide --new-city and --new-country when using 'Other / add a new city'.")
    if not new_city_count and (args.new_city or args.new_country):
        raise SystemExit("Use 'Other / add a new city' as a destination when providing --new-city or --new-country.")


def validate_against_remote(repo: str, args: argparse.Namespace, destinations: list[Destination]) -> None:
    ambassadors = load_repo_json(repo, "data/ambassadors.json")
    ambassador_names = {item["name"] for item in ambassadors if item.get("name")}

    if args.ambassador and args.ambassador not in ambassador_names:
        raise SystemExit(
            f"Ambassador is not currently tracked: {args.ambassador}\n"
            "Use --list ambassadors to inspect options, or use --new-ambassador-name."
        )
    if args.new_ambassador_name and args.new_ambassador_name in ambassador_names:
        raise SystemExit(
            f"{args.new_ambassador_name} is already tracked. Use --ambassador instead."
        )

    cities = load_repo_json(repo, "data/cities.json")
    city_labels = {city_label(city) for city in cities}
    for destination in destinations:
        if destination.city != ADD_NEW_CITY and destination.city not in city_labels:
            raise SystemExit(
                f"Destination city is not currently tracked: {destination.city}\n"
                "Use --list cities to inspect options, or use 'Other / add a new city' with --new-city and --new-country."
            )

    if any(destination.city == ADD_NEW_CITY for destination in destinations):
        countries = set(load_repo_json(repo, "data/countries.json"))
        if args.new_country not in countries:
            raise SystemExit(
                f"New destination country is not tracked: {args.new_country}\n"
                "Use --list countries to inspect options."
            )


def create_issue(repo: str, body: str) -> str:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as handle:
        handle.write(body)
        body_path = handle.name

    command = ["gh", "issue", "create", "--repo", repo, "--title", TITLE, "--body-file", body_path]
    for label in LABELS:
        command.extend(["--label", label])

    try:
        result = run(command)
    finally:
        os.unlink(body_path)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise SystemExit(f"Could not create issue in {repo}.\n{detail}")
    return result.stdout.strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a Codex Ambassadors travel-plan issue for the dashboard automation."
    )
    parser.add_argument("--repo", default=DEFAULT_REPO, help=f"Target repo. Default: {DEFAULT_REPO}")
    parser.add_argument("--list", choices=["ambassadors", "cities", "countries", "all"], help="List current dropdown options and exit.")
    parser.add_argument("--ambassador", help="Existing ambassador name exactly as tracked.")
    parser.add_argument("--new-ambassador-name", help="New ambassador name if not already tracked.")
    parser.add_argument("--new-ambassador-linkedin", help="Optional LinkedIn URL for a new ambassador.")
    parser.add_argument(
        "--destination",
        action="append",
        type=parse_destination,
        help="Destination in 'City, Country|YYYY-MM-DD|YYYY-MM-DD' format. Repeat up to three times.",
    )
    parser.add_argument("--new-city", help="New city name when destination is 'Other / add a new city'.")
    parser.add_argument("--new-country", help="New country name when destination is 'Other / add a new city'.")
    parser.add_argument("--availability", help="Optional availability notes.")
    parser.add_argument("--contact", help="Optional contact or coordination notes.")
    parser.add_argument("--dry-run", action="store_true", help="Print the issue body without creating an issue.")
    parser.add_argument("--no-remote-validation", action="store_true", help="Skip validation against repo data.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.list:
        print_options(args.repo, args.list)
        return 0

    destinations = args.destination or []
    if not destinations:
        parser.error("At least one --destination is required unless --list is used.")

    validate_submission(args, destinations)
    body = build_issue_body(args, destinations)

    if args.dry_run:
        print(f"Repo: {args.repo}")
        print(f"Title: {TITLE}")
        print(f"Labels: {', '.join(LABELS)}")
        print()
        print(body)
        return 0

    require_gh()
    require_repo_access(args.repo)
    if not args.no_remote_validation:
        validate_against_remote(args.repo, args, destinations)

    issue_url = create_issue(args.repo, body)
    print(issue_url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
