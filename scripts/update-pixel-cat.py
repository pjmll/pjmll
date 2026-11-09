"""Publish the banner variant that matches the owner's recent public activity."""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


ASSET_BRANCHES = {"refs/heads/snake-output", "refs/heads/pixel-cat-output"}


def counts_as_activity(event, owner, profile_repo, now):
    if event["actor"]["login"].casefold() != owner.casefold():
        return False
    event_time = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))
    if not now - timedelta(hours=24) <= event_time <= now:
        return False

    payload = event["payload"]
    if event["type"] == "PushEvent":
        ref = payload["ref"]
        if event["repo"]["name"].casefold() == profile_repo.casefold() and ref in ASSET_BRANCHES:
            return False
        return ref.startswith("refs/heads/") and payload.get("head") != "0" * 40
    if event["type"] == "PullRequestEvent":
        return payload["action"] in {"opened", "merged"} or (
            payload["action"] == "closed" and payload.get("pull_request", {}).get("merged") is True
        )
    return False


def has_recent_activity(owner, profile_repo, now):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "pjmll-pixel-cat",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token := os.environ.get("GH_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"

    # The events API exposes at most 300 recent events.
    for page in range(1, 4):
        url = f"https://api.github.com/users/{quote(owner)}/events/public?per_page=100&page={page}"
        with urlopen(Request(url, headers=headers), timeout=20) as response:
            events = json.load(response)
        if any(counts_as_activity(event, owner, profile_repo, now) for event in events):
            return True
        if len(events) < 100:
            break
    return False


def main():
    owner = os.environ["GITHUB_REPOSITORY_OWNER"]
    profile_repo = os.environ["GITHUB_REPOSITORY"]
    active = has_recent_activity(owner, profile_repo, datetime.now(timezone.utc))
    state = "working" if active else "napping"
    banner = Path("assets/profile-banner-pixel.svg").read_text(encoding="utf-8")
    output = Path("dist/profile-banner.svg")
    output.parent.mkdir(exist_ok=True)
    output.write_text(
        banner.replace('data-state="working"', f'data-state="{state}"', 1),
        encoding="utf-8",
        newline="\n",
    )
    print(f"Pixel cat state: {state}")


if __name__ == "__main__":
    main()
