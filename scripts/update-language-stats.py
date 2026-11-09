"""Build a language card from the public project repositories owned by the profile."""

import json
import os
from collections import Counter
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape


COLORS = ("#82e5bd", "#88adff", "#c6b5ff", "#ffc982", "#f4a4b1", "#7f96af")


def github_json(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "pjmll-language-stats",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token := os.environ.get("GH_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(url, headers=headers), timeout=20) as response:
        return json.load(response)


def collect_languages(owner, profile_repo):
    totals = Counter()
    repo_count = 0
    page = 1
    while True:
        url = f"https://api.github.com/users/{quote(owner)}/repos?type=owner&per_page=100&page={page}"
        repos = github_json(url)
        for repo in repos:
            if repo["private"] or repo["fork"] or repo["full_name"].casefold() == profile_repo.casefold():
                continue
            full_name = quote(repo["full_name"], safe="/")
            languages = github_json(f"https://api.github.com/repos/{full_name}/languages")
            if languages:
                totals.update(languages)
                repo_count += 1
        if len(repos) < 100:
            return totals, repo_count
        page += 1


def language_card(totals, repo_count):
    ranked = sorted(
        ((name, size) for name, size in totals.items() if size > 0),
        key=lambda item: (-item[1], item[0].casefold()),
    )
    total = sum(size for _, size in ranked)
    rows = ranked[:5]
    if len(ranked) > 5:
        rows.append(("Other", sum(size for _, size in ranked[5:])))

    segments = []
    labels = []
    details = []
    used = 0
    for index, ((name, size), color) in enumerate(zip(rows, COLORS)):
        start = 24 + 732 * used / total
        used += size
        end = 24 + 732 * used / total
        segments.append(f'<rect x="{start:.4f}" y="57" width="{end-start:.4f}" height="16" fill="{color}"/>')
        x = 25 + (index % 3) * 246
        y = 108 + (index // 3) * 35
        percent = "<0.1%" if 0 < size / total < 0.001 else f"{size / total:.1%}"
        short_name = name if len(name) <= 17 else name[:16] + "…"
        labels.append(
            f'<circle cx="{x + 5}" cy="{y - 6}" r="5" fill="{color}"/>'
            f'<text x="{x + 19}" y="{y}" fill="#e5eef9" font-size="16">{escape(short_name)}</text>'
            f'<text x="{x + 224}" y="{y}" text-anchor="end" fill="#b2c8e2" font-size="16">{escape(percent)}</text>'
        )
        details.append(f"{name} {percent}")

    if not rows:
        labels.append('<text x="25" y="108" fill="#b2c8e2" font-size="16">No public language data yet.</text>')
    summary = ", ".join(details) or "No public language data yet."
    height = 127 if len(rows) <= 3 else 163
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="780" height="{height}" viewBox="0 0 780 {height}" role="img" aria-labelledby="title desc">
  <title id="title">Programming languages</title>
  <desc id="desc">{escape(summary)}. Based on code bytes across {repo_count} public project repositories.</desc>
  <defs>
    <linearGradient id="background" x2="100%" y2="65%">
      <stop stop-color="#101728"/>
      <stop offset="1" stop-color="#17273b"/>
    </linearGradient>
    <clipPath id="bar"><rect x="24" y="57" width="732" height="16" rx="5"/></clipPath>
  </defs>
  <rect x=".5" y=".5" width="779" height="{height - 1}" rx="15" fill="url(#background)" stroke="#4e6380"/>
  <g font-family="Consolas, Menlo, monospace">
    <text x="24" y="35" fill="#b4cde5" font-size="16" font-weight="700" letter-spacing="1.5">LANGUAGE BREAKDOWN</text>
    <text x="756" y="35" text-anchor="end" fill="#9bb0cd" font-size="14">{repo_count} PUBLIC REPOS</text>
    <rect x="24" y="57" width="732" height="16" rx="5" fill="#293a52"/>
    <g clip-path="url(#bar)">{''.join(segments)}</g>
    {''.join(labels)}
  </g>
</svg>
'''


def main():
    totals, repo_count = collect_languages(
        os.environ["GITHUB_REPOSITORY_OWNER"], os.environ["GITHUB_REPOSITORY"]
    )
    output = Path("dist/languages.svg")
    output.parent.mkdir(exist_ok=True)
    output.write_text(language_card(totals, repo_count), encoding="utf-8")
    print(f"Generated language card from {repo_count} public project repositories.")


if __name__ == "__main__":
    main()
