"""Draws the profile README from live GitHub data: two sky posters made of cards, plus link buttons.

Run locally with the GitHub CLI signed in, or in Actions with GITHUB_TOKEN set.
Standard library only. Output goes to assets/; the header is seeded so it does not
change from run to run.
"""
import json
import math
import os
import random
import re
import subprocess
import urllib.request
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path

LOGIN = "hfatih"
NAME = "Fatih HAN"  # written the way its owner writes it, not as the GitHub profile has it
UTC_OFFSET = 3  # Istanbul; used to place commits on the clock
OUT = Path(__file__).parent / "assets"
SANS = "'Segoe UI', system-ui, -apple-system, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Consolas, 'Liberation Mono', monospace"
SERIF = "Georgia, 'Times New Roman', serif"
PINK, ROSE, TEXT, MUTED, LINE = "#f0abc5", "#e7a0b9", "#f5f5f6", "#a48a97", "#5a2a40"
# Descriptions for repositories whose GitHub description is empty.
# Shown as the first button. Everything else on the page comes from the GitHub API.
DISCORD = ("Talk to me on Discord", "https://discordapp.com/users/268797596280160259")
SKY = "#150a14"  # the one background colour every image shares, so they join without a seam
# What the public repositories are built with, per their own READMEs.
TOOLKIT = ["Rust", "TypeScript", "React", "Tauri 2", "SQLite", "WebGL 2", "GLSL", "Three.js", "C#", "Node.js"]
FALLBACK = {"samanyolu3d": "Interactive 3D galaxy simulation and procedural galactic visualization in your browser."}

QUERY = """query($login: String!) { user(login: $login) {
  name createdAt followers { totalCount }
  contributionsCollection { contributionCalendar { totalContributions
    weeks { contributionDays { contributionCount date } } } }
  repositories(first: 50, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false,
               orderBy: {field: STARGAZERS, direction: DESC}) { nodes {
    name description stargazerCount forkCount url pushedAt createdAt
    defaultBranchRef { target { ... on Commit { history(first: 40) { nodes { messageHeadline committedDate } } } } }
    releases(first: 30, orderBy: {field: CREATED_AT, direction: DESC}) { totalCount nodes { tagName publishedAt } }
    issues(states: OPEN) { totalCount } pullRequests(states: OPEN) { totalCount }
    stargazers(last: 6) { edges { starredAt node { login } } }
    primaryLanguage { name color }
    languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } } } } } }"""


def fetch():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:  # local run: let the GitHub CLI handle sign-in
        out = subprocess.run(["gh", "api", "graphql", "-f", f"query={QUERY}", "-f", f"login={LOGIN}"], capture_output=True, text=True, check=True, encoding="utf-8")
        return json.loads(out.stdout)["data"]["user"]
    body = json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode()
    request = urllib.request.Request("https://api.github.com/graphql", body, {"Authorization": f"Bearer {token}", "User-Agent": LOGIN})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)["data"]["user"]


def sparkle(x, y, size, fill=PINK, opacity=1.0, extra=""):
    """Four-pointed star centred on (x, y)."""
    w = max(0.6, size * 0.18)
    d = f"M{x} {y - size}L{x + w} {y - w} {x + size} {y} {x + w} {y + w} {x} {y + size} {x - w} {y + w} {x - size} {y} {x - w} {y - w}Z"
    return f'<path d="{d}" fill="{fill}" opacity="{opacity:.2f}"{extra}/>'


BASE_CSS = "@keyframes tw{0%,100%{opacity:.25}50%{opacity:1}}.tw{animation:tw 3.2s ease-in-out infinite}@keyframes fall{0%{transform:translate(0,0);opacity:0}8%{opacity:.9}22%{transform:translate(-190px,95px);opacity:0}100%{opacity:0}}.fall{animation:fall 9s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}.spin{animation:spin linear infinite}@media(prefers-reduced-motion:reduce){.tw,.fall,.spin{animation:none}}"
CARDS = {}


def backdrop(width, height, seed=None, stars=0):
    """A card is a pane of glass: the poster's sky shows through it, so the cards read as one piece."""
    return f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="16" fill="#ffffff" fill-opacity=".035" stroke="{PINK}" stroke-opacity=".2"/>'


def svg(name, width, height, body, label, css=""):
    """Registers a finished card; posters place it later."""
    CARDS[name] = (width, height, body, css, label)


def write(name, width, height, body, label, css=""):
    text = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(label)}"><style>{BASE_CSS}{css}</style>{body}</svg>\n'
    (OUT / name).write_text(text, encoding="utf-8", newline="\n")


def night(width, height, seed, nebulae=True):
    """A patch of the shared sky: flat colour, drifts of nebula kept clear of the edges, and stars."""
    rng = random.Random(seed)
    parts = [f'<rect width="{width}" height="{height}" fill="{SKY}"/>']
    if nebulae:
        parts.insert(0, f'<defs><radialGradient id="rose"><stop offset="0" stop-color="#b7466c" stop-opacity=".34"/><stop offset="1" stop-color="#b7466c" stop-opacity="0"/></radialGradient><radialGradient id="violet"><stop offset="0" stop-color="#644d8e" stop-opacity=".3"/><stop offset="1" stop-color="#644d8e" stop-opacity="0"/></radialGradient></defs>')
        # Each drift sits fully inside the image; one cut off at an edge would show as a seam.
        for index, top in enumerate(range(250, height - 240, 430)):
            left = index % 2 == 0
            parts.append(f'<ellipse cx="{rng.uniform(260, 380) if left else rng.uniform(500, 620):.0f}" cy="{top}" rx="{rng.uniform(220, 250):.0f}" ry="{rng.uniform(170, 220):.0f}" fill="url(#{"rose" if index % 3 else "violet"})"/>')
    for index in range(int(width * height / 2100)):
        x, y = round(rng.uniform(4, width - 4), 1), round(rng.uniform(4, height - 4), 1)
        twinkle = f' class="tw" style="animation-delay:-{index % 13 * 0.5:.1f}s"' if index % 9 == 0 else ""
        if rng.random() < 0.26:
            parts.append(sparkle(x, y, round(rng.uniform(2, 5.5), 1), "#ffc3d7", rng.uniform(0.14, 0.4), twinkle))
        else:
            parts.append(f'<circle cx="{x}" cy="{y}" r="{rng.uniform(0.5, 1.4):.1f}" fill="#ffc3d7" opacity="{rng.uniform(0.14, 0.42):.2f}"{twinkle}/>')
    return "".join(parts)


def poster(name, rows, label, round_top=False, round_bottom=False):
    """Lays cards out in rows on the shared sky and writes it as a single image.

    Each card sits in its own nested <svg>, which keeps the pixel transform origins its
    animations use relative to the card instead of the whole poster. Only the outer corners
    of the page are rounded: the posters and the menu between them stack flush.
    """
    pad, gap = 24, 16
    width = 840 + 2 * pad
    y, placed, css = pad, [], []
    for row in rows:
        x, tallest = pad, 0
        for key in row:
            w, h, body, extra, _ = CARDS[key]
            placed.append(f'<svg x="{x}" y="{y}" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{body}</svg>')
            css.append(extra)
            x += w + gap
            tallest = max(tallest, h)
        y += tallest + gap
    height = y - gap + pad
    t, b = (22 if round_top else 0), (22 if round_bottom else 0)
    outline = f"M0 {t}Q0 0 {t} 0H{width - t}Q{width} 0 {width} {t}V{height - b}Q{width} {height} {width - b} {height}H{b}Q0 {height} 0 {height - b}Z"
    body = f'<clipPath id="page"><path d="{outline}"/></clipPath><g clip-path="url(#page)">{night(width, height, name)}</g>' + "".join(placed)
    write(name, width, height, body, label, "".join(css))


def button(text, primary):
    """A link button as (width, markup): filled pink for the main one, glass for the rest."""
    width, height = round(len(text) * 7.6 + 58), 40
    if primary:
        shape = f'<defs><linearGradient id="fill" x1="0" x2="1"><stop offset="0" stop-color="#ffd3e0"/><stop offset="1" stop-color="{ROSE}"/></linearGradient><clipPath id="pill"><rect width="{width}" height="{height}" rx="20"/></clipPath></defs><rect width="{width}" height="{height}" rx="20" fill="url(#fill)"/><g clip-path="url(#pill)"><rect class="shine" x="-40" y="0" width="26" height="{height}" fill="#fff" opacity=".45"/></g>'
        ink, star = "#24121c", "#8e3a5b"
    else:
        shape = f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="19.5" fill="#ffffff" fill-opacity=".05" stroke="{PINK}" stroke-opacity=".55"/>'
        ink, star = "#ffe6ef", PINK
    return width, shape + sparkle(24, 20, 7, star, 1, ' class="tw"') + f'<text x="40" y="25" font-family="{SANS}" font-size="13.5" font-weight="700" fill="{ink}">{escape(text)}</text>'


def menu(links):
    """The link menu, cut into one image per button so each can be its own link.

    The slices carry the same sky and are sized in percentages that add up to a full row, so
    in the README they sit edge to edge between the two posters and read as part of them.
    Returns the README markup.
    """
    total, height, limit = 888, 60, 800
    rows, current, used = [], [], 0
    for text, url, primary in links:
        width, body = button(text, primary)
        if current and used + width + 16 > limit:
            rows.append(current)
            current, used = [], 0
        current.append((text, url, width, body))
        used += width + 16
    rows.append(current)
    # Same number of rows, but shared out evenly so the last one is not a lone button.
    items = [item for row in rows for item in row]
    per_row = math.ceil(len(items) / len(rows))
    rows = [items[index:index + per_row] for index in range(0, len(items), per_row)]
    html = []
    css = "@keyframes shine{0%,70%{transform:translateX(0)}100%{transform:translateX(320px)}}.shine{animation:shine 4.5s ease-in infinite}@media(prefers-reduced-motion:reduce){.shine{animation:none}}"
    for r, row in enumerate(rows):
        # Buttons sit together in the middle of the row; the two end slices take up the slack.
        edge = (total - sum(width + 16 for _, _, width, _ in row)) / 2
        spans = [width + 16 + (edge if i == 0 else 0) + (edge if i == len(row) - 1 else 0) for i, (_, _, width, _) in enumerate(row)]
        # Two-decimal percentages that stop just short of 100, so rounding can never wrap a row.
        shares = [round(span / total * 100, 2) for span in spans]
        shares[-1] = round(99.98 - sum(shares[:-1]), 2)
        for i, ((text, url, width, body), share) in enumerate(zip(row, shares)):
            slice_width = round(total * share / 100, 2)
            file = f"menu-{r}-{i}.svg"
            x = 8 + (edge if i == 0 else 0)
            inner = f'{night(round(slice_width) + 2, height, f"menu{r}{i}", nebulae=False)}<svg x="{x:.1f}" y="10" width="{width}" height="40" viewBox="0 0 {width} 40">{body}</svg>'
            write(file, slice_width, height, inner, text, css)
            html.append(f'<a href="{url}"><img src="assets/{file}" width="{share}%" align="top" alt="{escape(text)}"></a>')
    return "".join(html)


def milestones(calendar, repos):
    """How far along the next round numbers are, each as a comet closing in on its target."""
    width, height = 840, 124

    def next_target(value, steps=(5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000)):
        return next((step for step in steps if step > value), value + 1)

    tracks = [("contributions this year", calendar["totalContributions"]), ("stars", sum(repo["stargazerCount"] for repo in repos))]
    body = [backdrop(width, height)]
    body.append(f'<text x="26" y="34" font-family="{MONO}" font-size="12" letter-spacing="2" fill="{PINK}">NEXT MILESTONES</text>')
    for index, (caption, value) in enumerate(tracks):
        target = next_target(value)
        x, y, span = 26 + index * 406, 78, 370
        reached = span * value / target
        body.append(f'<path d="M{x} {y}H{x + span}" stroke="{PINK}" stroke-opacity=".22" stroke-width="3" stroke-linecap="round"/>')
        body.append(f'<path d="M{x} {y}H{x + reached:.1f}" stroke="url(#trail)" stroke-width="3" stroke-linecap="round"/>')
        body.append(sparkle(round(x + reached, 1), y, 8, "#ffe1ea", 1, ' class="tw"'))
        body.append(sparkle(x + span, y, 5, PINK, 0.55))
        body.append(f'<text x="{x}" y="{y - 16}" font-family="{SANS}" font-size="17" font-weight="700" fill="{TEXT}">{value}<tspan font-size="12" font-weight="400" fill="{MUTED}"> / {target}</tspan><tspan dx="8" font-family="{MONO}" font-size="10.5" font-weight="400" fill="{MUTED}">{caption}</tspan></text>')
        body.append(f'<text x="{x + span}" y="{y + 24}" text-anchor="end" font-family="{MONO}" font-size="10.5" fill="{MUTED}">{target - value} to go</text>')
    body.insert(1, f'<defs><linearGradient id="trail" x1="0" x2="1"><stop offset="0" stop-color="{PINK}" stop-opacity=".1"/><stop offset="1" stop-color="#ffe1ea"/></linearGradient></defs>')
    svg("milestones.svg", width, height, "".join(body), "Next milestones: " + ", ".join(f"{value} of {next_target(value)} {caption}" for caption, value in tracks))


def ticker(repos, now):
    """Recent commit messages scrolling past, newest first."""
    commits = all_commits(repos)
    commits = sorted(commits, reverse=True)[:8]

    def ago(stamp):
        days = (now - datetime.fromisoformat(stamp.replace("Z", "+00:00"))).days
        return "today" if days <= 0 else f"{days}d ago"

    line = "     ✦     ".join(f"{name}: {message[:64]} ({ago(stamp)})" for stamp, name, message in commits) or "no transmissions yet"
    line += "     ✦     "
    width, height, char = 840, 84, 7.52
    span = len(line) * char
    body = [backdrop(width, height)]
    body.append(f'<text x="26" y="34" font-family="{MONO}" font-size="12" letter-spacing="2" fill="{PINK}">TRANSMISSIONS</text>')
    body.append(f'<clipPath id="tape"><rect x="20" y="42" width="{width - 40}" height="30"/></clipPath><g clip-path="url(#tape)"><text class="tape" x="26" y="62" font-family="{MONO}" font-size="12.5" fill="#e9d3dc" xml:space="preserve">{escape(line * 2)}</text></g>')
    css = f"@keyframes tape{{to{{transform:translateX(-{span:.0f}px)}}}}.tape{{animation:tape {max(20, len(line) * 0.16):.0f}s linear infinite}}@media(prefers-reduced-motion:reduce){{.tape{{animation:none}}}}"
    svg("ticker.svg", width, height, "".join(body), "Recent commits: " + "; ".join(f"{name}: {message}" for _, name, message in commits), css)


def toolkit():
    """The tools behind the public repositories, as a row of chips."""
    width, height = 840, 92
    body = [backdrop(width, height)]
    body.append(f'<text x="26" y="34" font-family="{MONO}" font-size="12" letter-spacing="2" fill="{PINK}">TOOLKIT</text>')
    x = 26
    for index, tool in enumerate(TOOLKIT):
        chip = round(len(tool) * 7.3 + 34)
        if x + chip > width - 20:
            break
        body.append(f'<rect x="{x}" y="48" width="{chip}" height="26" rx="13" fill="{PINK}" fill-opacity=".08" stroke="{PINK}" stroke-opacity=".35"/>')
        body.append(sparkle(x + 14, 61, 4, PINK, 1, f' class="tw" style="animation-delay:-{index * 0.45:.2f}s"'))
        body.append(f'<text x="{x + 24}" y="65.5" font-family="{SANS}" font-size="12" font-weight="600" fill="{TEXT}">{escape(tool)}</text>')
        x += chip + 8
    svg("toolkit.svg", width, height, "".join(body), "Toolkit: " + ", ".join(TOOLKIT))


def wrap(text, limit, lines):
    out, current = [], ""
    for word in text.split():
        if len(current) + len(word) + 1 > limit and current:
            out.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    out.append(current)
    if len(out) > lines:
        out = out[:lines]
        out[-1] = out[-1][: limit - 1].rstrip(" ,.;") + "…"
    return out


def header(user, repos):
    width, height = 840, 250
    body = []
    body.append(f'<g class="fall"><path d="M470 24l-46 23" stroke="#ffd3e0" stroke-width="1.4" stroke-linecap="round"/></g>')
    body.append(f'<text x="40" y="62" font-family="{MONO}" font-size="12" letter-spacing="3" fill="{PINK}">HFATIH · GITHUB</text>')
    body.append(f'<text x="38" y="128" font-family="{SANS}" font-size="54" font-weight="700" letter-spacing="-2" fill="{TEXT}">{escape(NAME)}</text>')
    body.append(f'<text x="40" y="172" font-family="{SERIF}" font-size="27" font-style="italic" fill="{PINK}">desktop tools &amp; small universes.</text>')
    body.append(f'<text x="40" y="212" font-family="{SANS}" font-size="13" fill="{MUTED}">Rust and TypeScript for Windows apps · WebGL for galaxies and black holes</text>')
    # Constellation: one star per public repository, joined in order of stars.
    spots = [(560, 150), (640, 74), (722, 118), (786, 196), (608, 208), (500, 92)]
    stars = list(zip(spots, repos))
    path = " ".join(f"{'M' if i == 0 else 'L'}{x} {y}" for i, ((x, y), _) in enumerate(stars))
    body.append(f'<path d="{path}" fill="none" stroke="{ROSE}" stroke-width="1" stroke-dasharray="2 5" opacity=".55"/>')
    for index, ((x, y), repo) in enumerate(stars):
        size = 6 + min(6, repo["stargazerCount"] * 2)
        body.append(f'<circle cx="{x}" cy="{y}" r="{size + 7}" fill="{PINK}" opacity=".07"/>')
        body.append(sparkle(x, y, size, "#ffe1ea", 1, f' class="tw" style="animation-delay:{index * 0.7:.1f}s"'))
        anchor, dx = ("end", -14) if x > 740 else ("start", 14)
        body.append(f'<text x="{x + dx}" y="{y + 20}" text-anchor="{anchor}" font-family="{MONO}" font-size="10.5" fill="#d9bcc8">{escape(repo["name"])}</text>')
    for cx, cy, turn in ((0, 0, 0), (width, 0, 90)):
        garland = [f'<path d="M14 96Q26 30 96 14" fill="none" stroke="{PINK}" stroke-opacity=".35"/>', f'<path d="M14 62Q22 24 62 14" fill="none" stroke="{PINK}" stroke-opacity=".2"/>']
        for index, (x, y, size) in enumerate(((20, 84, 4), (27, 58, 6), (40, 38, 8), (60, 24, 6), (86, 17, 4), (22, 24, 10))):
            garland.append(sparkle(x, y, size, "#ffe1ea" if size > 6 else PINK, 0.9, f' class="tw" style="animation-delay:-{index * 0.6:.1f}s"'))
        body.append(f'<g transform="translate({cx} {cy}) rotate({turn})">{"".join(garland)}</g>')
    svg("header.svg", width, height, "".join(body), f"{NAME}: desktop tools and small universes")


def card(repo):
    width, height = 412, 158
    language = repo["primaryLanguage"] or {"name": "Other", "color": PINK}
    body = [backdrop(width, height, repo["name"], 22)]
    body.append(sparkle(34, 40, 9, language["color"] or PINK))
    body.append(f'<text x="54" y="46" font-family="{SANS}" font-size="18" font-weight="700" fill="{TEXT}">{escape(repo["name"])}</text>')
    description = repo["description"] or FALLBACK.get(repo["name"], "")
    for row, line in enumerate(wrap(description, 54, 3)):
        body.append(f'<text x="26" y="{76 + row * 19}" font-family="{SANS}" font-size="12.5" fill="#cdb9c3">{escape(line)}</text>')
    body.append(f'<circle cx="31" cy="134" r="5" fill="{language["color"] or PINK}"/>')
    body.append(f'<text x="43" y="138" font-family="{MONO}" font-size="11" fill="{MUTED}">{escape(language["name"])}</text>')
    release = (repo["releases"]["nodes"] or [None])[0]
    if release:
        body.append(f'<text x="{52 + len(language["name"]) * 6.8:.0f}" y="138" font-family="{MONO}" font-size="11" fill="{PINK}">{escape(release["tagName"])}</text>')
    if repo["stargazerCount"]:
        body.append(f'<text x="{width - 26}" y="138" text-anchor="end" font-family="{MONO}" font-size="11" fill="{PINK}">✦ {repo["stargazerCount"]}</text>')
    svg(f"repo-{repo['name']}.svg", width, height, "".join(body), f"{repo['name']}: {description}")


def sky(calendar):
    """The contribution year as a night sky: a quiet day is a dim dot, a busy day a bright star."""
    width, height = 840, 232
    weeks = calendar["weeks"]
    days = [day for week in weeks for day in week["contributionDays"]]
    active = [day for day in days if day["contributionCount"]]
    best = max(days, key=lambda day: day["contributionCount"])
    peak = max(1, best["contributionCount"])
    body = [backdrop(width, height, "sky", 0)]
    body.append(f'<text x="28" y="38" font-family="{MONO}" font-size="12.5" fill="{TEXT}"><tspan fill="{PINK}">{LOGIN}@github</tspan> ~ $ ./observe --last-year</text>')
    left, top, step = 30, 64, 14.6
    month = None
    for column, week in enumerate(weeks):
        first = date.fromisoformat(week["contributionDays"][0]["date"])
        if first.month != month and column < len(weeks) - 2:
            month = first.month
            body.append(f'<text x="{left + column * step:.1f}" y="{top + 7 * step + 12:.1f}" font-family="{MONO}" font-size="9.5" fill="{MUTED}">{first.strftime("%b")}</text>')
        for day in week["contributionDays"]:
            row = date.fromisoformat(day["date"]).isoweekday() % 7
            x, y = round(left + column * step, 1), round(top + row * step, 1)
            count = day["contributionCount"]
            if count:
                level = count / peak
                body.append(sparkle(x, y, round(3.4 + 3.4 * level, 1), "#ffe1ea" if level > 0.5 else PINK, 0.55 + 0.45 * level))
            else:
                body.append(f'<circle cx="{x}" cy="{y}" r="1" fill="#ffc3d7" opacity=".18"/>')
    stats = [
        (calendar["totalContributions"], "contributions this year"),
        (len(active), "nights observed"),
        (best["contributionCount"], "brightest night" + (f" · {date.fromisoformat(best['date']).strftime('%b %d')}" if best["contributionCount"] else "")),
    ]
    for index, (value, caption) in enumerate(stats):
        x = 30 + index * 268
        body.append(f'<text x="{x}" y="{height - 20}" font-family="{SANS}" font-size="20" font-weight="700" fill="{TEXT}">{value}<tspan dx="8" font-family="{MONO}" font-size="10.5" font-weight="400" fill="{MUTED}">{escape(caption)}</tspan></text>')
    svg("sky.svg", width, height, "".join(body), f"{calendar['totalContributions']} contributions in the last year")


def languages(repos):
    width, height = 840, 118
    totals = {}
    for repo in repos:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            size, _ = totals.get(name, (0, None))
            totals[name] = (size + edge["size"], edge["node"]["color"] or PINK)
    ranked = sorted(totals.items(), key=lambda item: -item[1][0])[:6]
    total = sum(size for _, (size, _) in ranked) or 1
    body = [backdrop(width, height, "languages", 26)]
    body.append(f'<text x="28" y="36" font-family="{MONO}" font-size="12" letter-spacing="2" fill="{PINK}">WRITTEN IN</text>')
    bar_left, bar_width, x = 28, width - 56, 28.0
    body.append(f'<clipPath id="bar"><rect x="{bar_left}" y="50" width="{bar_width}" height="10" rx="5"/></clipPath><g clip-path="url(#bar)">')
    for _, (size, color) in ranked:
        span = bar_width * size / total
        body.append(f'<rect x="{x:.1f}" y="50" width="{span + 0.5:.1f}" height="10" fill="{color}"/>')
        x += span
    body.append("</g>")
    for index, (name, (size, color)) in enumerate(ranked):
        x = 28 + index * 132
        body.append(f'<circle cx="{x + 5}" cy="88" r="5" fill="{color}"/>')
        body.append(f'<text x="{x + 17}" y="92" font-family="{SANS}" font-size="12" fill="{TEXT}">{escape(name)} <tspan font-family="{MONO}" font-size="10.5" fill="{MUTED}">{100 * size / total:.0f}%</tspan></text>')
    svg("languages.svg", width, height, "".join(body), "Languages: " + ", ".join(name for name, _ in ranked))


def orbits(repos):
    """Each repository as a planet: its size follows the amount of code, its colour the main language."""
    width, height = 412, 260
    cx, cy = 286, 134
    body = [backdrop(width, height, "orbits", 16)]
    body.append(f'<text x="26" y="38" font-family="{MONO}" font-size="12" letter-spacing="2" fill="{PINK}">IN ORBIT</text>')
    body.append(f'<circle cx="{cx}" cy="{cy}" r="16" fill="{PINK}" opacity=".1"/>')
    body.append(sparkle(cx, cy, 10, "#ffe1ea", 1, ' class="tw"'))
    planets = sorted(repos, key=lambda repo: sum(edge["size"] for edge in repo["languages"]["edges"]))[:5]
    for index, repo in enumerate(planets):
        radius = 34 + index * 19
        size = sum(edge["size"] for edge in repo["languages"]["edges"])
        dot = round(3 + min(5, math.log10(max(size, 10)) - 2.5), 1)
        color = (repo["primaryLanguage"] or {}).get("color") or PINK
        start = (index * 97) % 360
        body.append(f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="{ROSE}" stroke-width=".8" stroke-dasharray="1 4" opacity=".5"/>')
        body.append(f'<g class="spin" style="transform-origin:{cx}px {cy}px;animation-duration:{18 + index * 13}s;animation-delay:-{start / 10:.0f}s"><circle cx="{cx + radius}" cy="{cy}" r="{dot}" fill="{color}"/></g>')
        body.append(f'<circle cx="31" cy="{70 + index * 24}" r="{min(dot, 6)}" fill="{color}"/>')
        body.append(f'<text x="45" y="{74 + index * 24}" font-family="{MONO}" font-size="10.5" fill="#d9bcc8">{escape(repo["name"][:19])}</text>')
    body.append(f'<text x="26" y="{height - 22}" font-family="{SANS}" font-size="11" fill="{MUTED}">Planet size follows the amount of code.</text>')
    svg("orbits.svg", width, height, "".join(body), "Repositories drawn as planets in orbit")


def terminal(user, repos, calendar):
    """A terminal that types out who this is, a few live numbers and the latest release."""
    releases = sorted(
        ((repo["releases"]["nodes"][0]["publishedAt"], repo["name"], repo["releases"]["nodes"][0]["tagName"]) for repo in repos if repo["releases"]["nodes"] and repo["releases"]["nodes"][0]["publishedAt"]),
        reverse=True,
    )
    stars = sum(repo["stargazerCount"] for repo in repos)
    prompt = f"{LOGIN}@github ~ $ "
    lines = [
        (prompt, "whoami"),
        ("", f"{NAME} · builds desktop tools and small universes"),
        (prompt, "./stats"),
        ("", f"{len(repos)} public repos · {stars} stars · {calendar['totalContributions']} contributions this year · here since {user['createdAt'][:4]}"),
        (prompt, "./now"),
        ("", f"shipping {releases[0][1]} {releases[0][2]}" if releases else "building the next thing"),
    ]
    width, row, top, left, char = 840, 24, 62, 30, 7.82
    height = top + len(lines) * row + 30
    screen = "#150c13"
    body = [backdrop(width, height, "terminal", 0)]
    body.append(f'<rect x="14" y="14" width="{width - 28}" height="{height - 28}" rx="10" fill="{screen}" stroke="{LINE}"/>')
    body.append(f'<clipPath id="screen"><rect x="16" y="16" width="{width - 32}" height="{height - 32}" rx="9"/></clipPath>')
    for index, color in enumerate(("#e7a0b9", "#e8b86d", "#bca4dd")):
        body.append(f'<circle cx="{34 + index * 16}" cy="33" r="4.5" fill="{color}" opacity=".8"/>')
    body.append(f'<text x="{width / 2}" y="37" text-anchor="middle" font-family="{MONO}" font-size="10.5" fill="{MUTED}">{LOGIN}: ~</text>')
    total, clock, frames = 16.0, 0.6, []
    for index, (lead, text) in enumerate(lines):
        y = top + index * row
        typed = bool(lead)  # commands are typed, their output appears at once
        span = len(text) * 0.07 if typed else 0.05
        start, end = clock / total * 100, (clock + span) / total * 100
        clock += span + (0.35 if typed else 0.8)
        x = left + len(lead) * char
        cover = len(text) * char + 14
        body.append(f'<text x="{left}" y="{y}" font-family="{MONO}" font-size="13" xml:space="preserve"><tspan fill="{PINK}">{escape(lead)}</tspan><tspan fill="{TEXT if typed else "#d9bcc8"}">{escape(text)}</tspan></text>')
        # Clipped to the screen so a cover sliding off its line never paints over the card's edge.
        body.append(f'<g clip-path="url(#screen)"><rect class="cover c{index}" x="{x:.1f}" y="{y - 15}" width="{cover:.1f}" height="21" fill="{screen}"/></g>')
        frames.append(f"@keyframes c{index}{{0%,{start:.2f}%{{transform:translateX(0)}}{end:.2f}%,97%{{transform:translateX({cover:.1f}px)}}100%{{transform:translateX(0)}}}}.c{index}{{animation:c{index} {total}s steps({max(1, len(text)) if typed else 1},end) infinite}}")
    y = top + len(lines) * row
    body.append(f'<text x="{left}" y="{y}" font-family="{MONO}" font-size="13" fill="{PINK}" xml:space="preserve">{escape(prompt)}</text>')
    body.append(f'<rect class="blink" x="{left + len(prompt) * char:.1f}" y="{y - 13}" width="8" height="16" fill="{PINK}"/>')
    css = "".join(frames) + "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}.blink{animation:blink 1.1s steps(1) infinite}@media(prefers-reduced-motion:reduce){.cover{display:none}.blink{animation:none}}"
    svg("terminal.svg", width, height, "".join(body), " ".join(text for _, text in lines), css)


def galaxy(calendar):
    """The year as a slowly turning spiral galaxy: one bright star per contribution, dust for the arms."""
    width, height = 412, 260
    cx, cy = 206, 132
    rng = random.Random("galaxy")
    count = calendar["totalContributions"]

    def arm_point(spread):
        arm, t = rng.choice((0, math.pi)), rng.random() ** 0.8
        angle = arm + t * 3.6 * math.pi / 2 + rng.gauss(0, spread)
        radius = 14 + t * 150
        return round(cx + radius * math.cos(angle), 1), round(cy + radius * math.sin(angle), 1), t

    disc = []
    for _ in range(260):
        x, y, t = arm_point(0.28)
        disc.append(f'<circle cx="{x}" cy="{y}" r="{rng.uniform(0.5, 1.3):.1f}" fill="#ffc3d7" opacity="{0.5 - 0.35 * t:.2f}"/>')
    for index in range(min(count, 140)):
        x, y, _ = arm_point(0.16)
        disc.append(sparkle(x, y, round(rng.uniform(2.6, 5.2), 1), "#ffe1ea", 0.95, f' class="tw" style="animation-delay:-{index % 9 * 0.4:.1f}s"'))
    body = [backdrop(width, height, "galaxy-bg", 14)]
    body.append(f'<defs><radialGradient id="core"><stop offset="0" stop-color="#ffe1ea" stop-opacity=".9"/><stop offset=".35" stop-color="{PINK}" stop-opacity=".28"/><stop offset="1" stop-color="{PINK}" stop-opacity="0"/></radialGradient></defs>')
    # Squash vertically for a tilted view; the inner group does the turning.
    body.append(f'<g transform="translate(0 {cy * 0.42:.1f}) scale(1 .58)"><circle cx="{cx}" cy="{cy}" r="62" fill="url(#core)"/><g class="spin" style="transform-origin:{cx}px {cy}px;animation-duration:140s">{"".join(disc)}</g></g>')
    body.append(f'<text x="26" y="38" font-family="{MONO}" font-size="12" letter-spacing="2" fill="{PINK}">GALAXY</text>')
    body.append(f'<text x="26" y="{height - 22}" font-family="{SANS}" font-size="11" fill="{MUTED}"><tspan font-size="16" font-weight="700" fill="{TEXT}">{count}</tspan>  bright stars, one for each contribution this year.</text>')
    svg("galaxy.svg", width, height, "".join(body), f"A spiral galaxy with {count} bright stars, one per contribution this year")


def signal(calendar):
    """Contributions by weekday as a pulsing signal: which days the work actually happens."""
    width, height = 412, 260
    totals = [0] * 7
    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            totals[date.fromisoformat(day["date"]).weekday()] += day["contributionCount"]
    peak = max(totals) or 1
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    body = [backdrop(width, height, "signal", 16)]
    body.append(f'<text x="26" y="38" font-family="{MONO}" font-size="12" letter-spacing="2" fill="{PINK}">WEEKLY SIGNAL</text>')
    base, tallest, left, step = 196, 118, 44, 50
    body.append(f'<path d="M26 {base + 0.5}H{width - 26}" stroke="{LINE}"/>')
    frames = []
    for index, value in enumerate(totals):
        bar = max(4, tallest * value / peak)
        x = left + index * step
        busiest = value == peak and value > 0
        body.append(f'<rect class="bar b{index}" x="{x - 9}" y="{base - bar:.1f}" width="18" height="{bar:.1f}" rx="5" fill="{"#ffe1ea" if busiest else PINK}" opacity="{1 if busiest else 0.38 + 0.5 * value / peak:.2f}" style="transform-origin:{x}px {base}px;animation-delay:-{index * 0.37:.2f}s"/>')
        if value:
            body.append(f'<text x="{x}" y="{base - bar - 8:.1f}" text-anchor="middle" font-family="{MONO}" font-size="10.5" fill="{TEXT}">{value}</text>')
        body.append(f'<text x="{x}" y="{base + 18}" text-anchor="middle" font-family="{MONO}" font-size="10" fill="{MUTED}">{names[index]}</text>')
    busiest_day = ["Mondays", "Tuesdays", "Wednesdays", "Thursdays", "Fridays", "Saturdays", "Sundays"][totals.index(peak)]
    caption = f"Loudest on {busiest_day}." if sum(totals) else "No signal yet this year."
    body.append(f'<text x="26" y="{height - 22}" font-family="{SANS}" font-size="11" fill="{MUTED}">{caption}</text>')
    css = "@keyframes pulse{0%,100%{transform:scaleY(1)}50%{transform:scaleY(.82)}}.bar{animation:pulse 2.6s ease-in-out infinite}@media(prefers-reduced-motion:reduce){.bar{animation:none}}"
    svg("signal.svg", width, height, "".join(body), "Contributions by weekday: " + ", ".join(f"{name} {value}" for name, value in zip(names, totals)), css)


def code_size(repo):
    return sum(edge["size"] for edge in repo["languages"]["edges"])


def blackhole(repos):
    """All the code that has fallen in so far, circling a black hole."""
    width, height = 412, 260
    cx, cy = 290, 128
    total = sum(code_size(repo) for repo in repos)
    heaviest = max(repos, key=code_size) if repos else None
    body = [backdrop(width, height, "blackhole", 18)]
    body.append(f'<defs><linearGradient id="disk" x1="0" x2="1"><stop offset="0" stop-color="{ROSE}" stop-opacity=".15"/><stop offset=".5" stop-color="#fff3f7"/><stop offset="1" stop-color="{ROSE}" stop-opacity=".15"/></linearGradient><radialGradient id="halo"><stop offset=".55" stop-color="{PINK}" stop-opacity="0"/><stop offset=".8" stop-color="{PINK}" stop-opacity=".22"/><stop offset="1" stop-color="{PINK}" stop-opacity="0"/></radialGradient></defs>')
    rings = [(96, 21, 2.4, 7), (80, 17, 2, 5.5), (64, 13, 1.6, 4)]

    def arcs(front):
        sweep = 0 if front else 1  # the near half of the disk passes in front of the hole
        return "".join(
            f'<path class="flow" d="M{cx - rx} {cy}A{rx} {ry} 0 0 {sweep} {cx + rx} {cy}" fill="none" stroke="url(#disk)" stroke-width="{w}" stroke-linecap="round" stroke-dasharray="14 9" style="animation-duration:{speed}s"/>'
            for rx, ry, w, speed in rings
        )

    body.append(f'<g transform="rotate(-16 {cx} {cy})">{arcs(False)}</g>')
    body.append(f'<circle cx="{cx}" cy="{cy}" r="52" fill="url(#halo)"/>')
    body.append(f'<circle cx="{cx}" cy="{cy}" r="31" fill="#07040a" stroke="#ffe1ea" stroke-width="1.6"/>')
    body.append(f'<g transform="rotate(-16 {cx} {cy})">{arcs(True)}</g>')
    body.append(f'<text x="26" y="38" font-family="{MONO}" font-size="12" letter-spacing="2" fill="{PINK}">CODE MASS</text>')
    body.append(f'<text x="26" y="118" font-family="{SANS}" font-size="38" font-weight="700" letter-spacing="-1" fill="{TEXT}">{total / 1024:,.0f}<tspan dx="6" font-size="15" font-weight="600" fill="{PINK}">KB</tspan></text>')
    body.append(f'<text x="26" y="142" font-family="{MONO}" font-size="10.5" fill="{MUTED}">across {len(repos)} repositories</text>')
    if heaviest:
        body.append(f'<text x="26" y="{height - 22}" font-family="{SANS}" font-size="11" fill="{MUTED}">Heaviest: {escape(heaviest["name"])}, {code_size(heaviest) / 1024:,.0f} KB.</text>')
    css = "@keyframes flow{to{stroke-dashoffset:-46}}.flow{animation:flow linear infinite}@media(prefers-reduced-motion:reduce){.flow{animation:none}}"
    svg("blackhole.svg", width, height, "".join(body), f"{total / 1024:,.0f} KB of code across {len(repos)} repositories, circling a black hole", css)


def radar(user, repos, now):
    """Repositories as radar blips: closer to the centre means pushed more recently, bigger means more stars."""
    width, height = 412, 260
    cx, cy, reach = 124, 136, 92
    rng = random.Random("radar")
    body = [backdrop(width, height, "radar-bg", 10)]
    body.append(f'<defs><linearGradient id="sweep" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{PINK}" stop-opacity=".5"/><stop offset="1" stop-color="{PINK}" stop-opacity="0"/></linearGradient></defs>')
    for radius in (reach, reach * 2 / 3, reach / 3):
        body.append(f'<circle cx="{cx}" cy="{cy}" r="{radius:.0f}" fill="none" stroke="{LINE}"/>')
    body.append(f'<path d="M{cx - reach} {cy}H{cx + reach}M{cx} {cy - reach}V{cy + reach}" stroke="{LINE}"/>')
    body.append(f'<g class="spin" style="transform-origin:{cx}px {cy}px;animation-duration:5s"><path d="M{cx} {cy}L{cx + reach} {cy}A{reach} {reach} 0 0 0 {cx + reach * 0.5:.1f} {cy - reach * 0.866:.1f}Z" fill="url(#sweep)"/><path d="M{cx} {cy}H{cx + reach}" stroke="#ffe1ea" stroke-width="1.2"/></g>')
    for index, repo in enumerate(repos[:8]):
        age = (now - datetime.fromisoformat(repo["pushedAt"].replace("Z", "+00:00"))).days
        distance = 14 + min(1.0, age / 60) * (reach - 24)
        angle = rng.uniform(0, 2 * math.pi)
        x, y = round(cx + distance * math.cos(angle), 1), round(cy + distance * math.sin(angle), 1)
        body.append(f'<circle class="tw" cx="{x}" cy="{y}" r="{3 + min(4, repo["stargazerCount"] * 1.5):.1f}" fill="#ffe1ea" style="animation-delay:-{index * 0.8:.1f}s"/>')
    body.append(f'<text x="26" y="38" font-family="{MONO}" font-size="12" letter-spacing="2" fill="{PINK}">RADAR</text>')
    rows = [(sum(repo["stargazerCount"] for repo in repos), "stars"), (sum(repo["forkCount"] for repo in repos), "forks"), (user["followers"]["totalCount"], "followers")]
    rows = [(value, caption[:-1] if value == 1 else caption) for value, caption in rows]
    for index, (value, caption) in enumerate(rows):
        body.append(f'<text x="252" y="{104 + index * 34}" font-family="{SANS}" font-size="22" font-weight="700" fill="{TEXT}">{value}<tspan dx="8" font-family="{MONO}" font-size="10.5" font-weight="400" fill="{MUTED}">{caption}</tspan></text>')
    body.append(f'<text x="252" y="{height - 34}" font-family="{SANS}" font-size="11" fill="{MUTED}">Near the centre: pushed</text><text x="252" y="{height - 20}" font-family="{SANS}" font-size="11" fill="{MUTED}">recently. Bigger: more stars.</text>')
    svg("radar.svg", width, height, "".join(body), "Radar: " + ", ".join(f"{value} {caption}" for value, caption in rows))


def mission(calendar, today):
    """The last thirty days as a flight path, with streaks."""
    width, height = 840, 168
    days = {day["date"]: day["contributionCount"] for week in calendar["weeks"] for day in week["contributionDays"]}
    ordered = [count for key, count in sorted(days.items()) if key <= today.isoformat()]
    longest = run = 0
    for count in ordered:
        run = run + 1 if count else 0
        longest = max(longest, run)
    current = 0
    for count in reversed(ordered[:-1] if ordered and not ordered[-1] else ordered):  # today may still be empty
        if not count:
            break
        current += 1
    since = next((index for index, count in enumerate(reversed(ordered)) if count), None)
    body = [backdrop(width, height, "mission", 30)]
    body.append(f'<text x="28" y="38" font-family="{MONO}" font-size="12.5" fill="{TEXT}"><tspan fill="{PINK}">{LOGIN}@github</tspan> ~ $ ./mission --last-30-days</text>')
    left, right, y = 44, width - 70, 86
    step = (right - left) / 29
    body.append(f'<path d="M{left} {y}H{right}" stroke="{ROSE}" stroke-width="1" stroke-dasharray="2 6" opacity=".7"/>')
    for index in range(30):
        day = today - timedelta(days=29 - index)
        count = days.get(day.isoformat(), 0)
        x = round(left + index * step, 1)
        if count:
            body.append(sparkle(x, y, min(9, 4 + count), "#ffe1ea", 1, f' class="tw" style="animation-delay:-{index * 0.3:.1f}s"'))
        else:
            body.append(f'<circle cx="{x}" cy="{y}" r="1.6" fill="#ffc3d7" opacity=".35"/>')
        if index % 7 == 1 or index == 29:
            body.append(f'<text x="{x}" y="{y + 24}" text-anchor="middle" font-family="{MONO}" font-size="9.5" fill="{MUTED}">{"today" if index == 29 else day.strftime("%b %d")}</text>')
    rx = right + 22
    body.append(f'<g class="hover"><path class="flame" d="M{rx - 9} {y - 3.5}L{rx - 24} {y}L{rx - 9} {y + 3.5}Z" fill="#e8b86d" style="transform-origin:{rx - 9}px {y}px"/><path d="M{rx - 10} {y - 6}H{rx + 6}Q{rx + 17} {y} {rx + 6} {y + 6}H{rx - 10}Z" fill="#ffe1ea"/><path d="M{rx - 10} {y - 6}L{rx - 16} {y - 11}V{y + 11}L{rx - 10} {y + 6}Z" fill="{ROSE}"/><circle cx="{rx + 3}" cy="{y}" r="2.6" fill="#1f1018"/></g>')
    last = "today" if since == 0 else "yesterday" if since == 1 else f"{since} days ago" if since is not None else "not yet"
    stats = [(f"{current} d", "current streak"), (f"{longest} d", "longest streak this year"), (last, "last contribution")]
    for index, (value, caption) in enumerate(stats):
        body.append(f'<text x="{30 + index * 268}" y="{height - 20}" font-family="{SANS}" font-size="20" font-weight="700" fill="{TEXT}">{value}<tspan dx="8" font-family="{MONO}" font-size="10.5" font-weight="400" fill="{MUTED}">{caption}</tspan></text>')
    css = "@keyframes flame{0%,100%{transform:scaleX(1)}50%{transform:scaleX(.55)}}.flame{animation:flame .28s ease-in-out infinite}@keyframes hover{0%,100%{transform:translateY(-1.5px)}50%{transform:translateY(1.5px)}}.hover{animation:hover 2.4s ease-in-out infinite}@media(prefers-reduced-motion:reduce){.flame,.hover{animation:none}}"
    svg("mission.svg", width, height, "".join(body), f"Last 30 days: current streak {current} days, longest streak {longest} days, last contribution {last}", css)


def aurora():
    """A closing band of slow aurora light. Decorative."""
    width, height, period = 840, 96, 280
    body = []
    body.append(f'<clipPath id="band"><rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="15"/></clipPath><g clip-path="url(#band)">')
    for index, (color, base, swing, speed) in enumerate((("#bca4dd", 62, 13, 19), (PINK, 54, 17, 13), ("#ffe1ea", 68, 9, 27))):
        points = " ".join(f"{x},{base + swing * math.sin(2 * math.pi * x / period + index):.1f}" for x in range(-period, width + period + 1, 14))
        body.append(f'<polyline class="drift" points="{points}" fill="none" stroke="{color}" stroke-width="{10 - index * 3}" stroke-linecap="round" opacity="{0.16 + index * 0.07:.2f}" style="animation-duration:{speed}s"/>')
    body.append("</g>")
    body.append(f'<text x="{width / 2}" y="44" text-anchor="middle" font-family="{SERIF}" font-size="21" font-style="italic" fill="{TEXT}">clear skies.</text>')
    css = f"@keyframes drift{{to{{transform:translateX({period}px)}}}}.drift{{animation:drift linear infinite}}@media(prefers-reduced-motion:reduce){{.drift{{animation:none}}}}"
    svg("aurora.svg", width, height, "".join(body), "Clear skies.", css)


def all_commits(repos):
    return [
        (node["committedDate"], repo["name"], node["messageHeadline"])
        for repo in repos
        for node in ((repo["defaultBranchRef"] or {}).get("target") or {}).get("history", {}).get("nodes", [])
    ]


def hours(repos):
    """Recent commits placed on a 24-hour dial, in local time."""
    width, height = 412, 260
    cx, cy, inner, reach = 292, 134, 30, 52
    counts = [0] * 24
    for stamp, _, _ in all_commits(repos):
        counts[(datetime.fromisoformat(stamp.replace("Z", "+00:00")).hour + UTC_OFFSET) % 24] += 1
    peak = max(counts) or 1
    busiest = counts.index(max(counts))
    body = [backdrop(width, height)]
    body.append(f'<text x="26" y="38" font-family="{MONO}" font-size="12" letter-spacing="2" fill="{PINK}">ACTIVE HOURS</text>')
    body.append(f'<circle cx="{cx}" cy="{cy}" r="{inner}" fill="none" stroke="{PINK}" stroke-opacity=".3"/>')
    for hour, count in enumerate(counts):
        angle = math.radians(hour * 15 - 90)
        length = 3 + reach * count / peak
        x1, y1 = cx + inner * math.cos(angle), cy + inner * math.sin(angle)
        x2, y2 = cx + (inner + length) * math.cos(angle), cy + (inner + length) * math.sin(angle)
        body.append(f'<path d="M{x1:.1f} {y1:.1f}L{x2:.1f} {y2:.1f}" stroke="{"#ffe1ea" if hour == busiest and count else PINK}" stroke-opacity="{1 if count else 0.25}" stroke-width="{4 if count else 2}" stroke-linecap="round"/>')
    for hour in (0, 6, 12, 18):
        angle = math.radians(hour * 15 - 90)
        body.append(f'<text x="{cx + (inner - 12) * math.cos(angle):.1f}" y="{cy + (inner - 12) * math.sin(angle) + 3.5:.1f}" text-anchor="middle" font-family="{MONO}" font-size="9" fill="{MUTED}">{hour:02d}</text>')
    body.append(f'<g class="spin" style="transform-origin:{cx}px {cy}px;animation-duration:24s"><path d="M{cx} {cy}V{cy - inner + 2}" stroke="#ffe1ea" stroke-width="1.4" stroke-linecap="round"/></g>')
    body.append(f'<circle cx="{cx}" cy="{cy}" r="2.4" fill="#ffe1ea"/>')
    total = sum(counts)
    mood = "night shift" if busiest >= 22 or busiest < 5 else "morning" if busiest < 12 else "afternoon" if busiest < 18 else "evening"
    if total:
        body.append(f'<text x="26" y="116" font-family="{SANS}" font-size="34" font-weight="700" letter-spacing="-1" fill="{TEXT}">{busiest:02d}:00</text>')
        body.append(f'<text x="26" y="140" font-family="{SERIF}" font-size="16" font-style="italic" fill="{PINK}">{mood}</text>')
    body.append(f'<text x="26" y="{height - 34}" font-family="{SANS}" font-size="11" fill="{MUTED}">Busiest hour across the last</text><text x="26" y="{height - 20}" font-family="{SANS}" font-size="11" fill="{MUTED}">{total} commits, Istanbul time.</text>')
    svg("hours.svg", width, height, "".join(body), f"Active hours: busiest around {busiest:02d}:00 Istanbul time across the last {total} commits")


def logbook(user, repos, now):
    """How long this has been going, and the first and newest things in it."""
    width, height = 412, 260
    cx, cy = 318, 128
    joined = datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00"))
    by_age = sorted(repos, key=lambda repo: repo["createdAt"])
    body = [backdrop(width, height)]
    body.append(f'<text x="26" y="38" font-family="{MONO}" font-size="12" letter-spacing="2" fill="{PINK}">LOGBOOK</text>')
    body.append(f'<circle cx="{cx}" cy="{cy}" r="22" fill="{PINK}" fill-opacity=".14" stroke="{PINK}" stroke-opacity=".5"/><path d="M{cx - 15} {cy - 6}Q{cx} {cy - 13} {cx + 17} {cy - 9}M{cx - 19} {cy + 6}Q{cx} {cy + 13} {cx + 19} {cy + 5}" fill="none" stroke="{PINK}" stroke-opacity=".4"/>')
    body.append(f'<ellipse cx="{cx}" cy="{cy}" rx="54" ry="54" fill="none" stroke="{ROSE}" stroke-opacity=".4" stroke-dasharray="1 5"/>')
    body.append(f'<g class="spin" style="transform-origin:{cx}px {cy}px;animation-duration:16s"><g transform="translate({cx + 54} {cy})"><rect x="-4" y="-3" width="8" height="6" rx="1.5" fill="#ffe1ea"/><rect x="-13" y="-2" width="7" height="4" fill="{ROSE}"/><rect x="6" y="-2" width="7" height="4" fill="{ROSE}"/></g></g>')
    body.append(f'<text x="26" y="112" font-family="{SANS}" font-size="34" font-weight="700" letter-spacing="-1" fill="{TEXT}">{(now - joined).days:,}</text>')
    body.append(f'<text x="26" y="134" font-family="{MONO}" font-size="10.5" fill="{MUTED}">days on GitHub, since {joined.strftime("%b %Y")}</text>')
    if by_age:
        for index, (caption, repo) in enumerate((("first light", by_age[0]), ("newest", by_age[-1]))):
            when = datetime.fromisoformat(repo["createdAt"].replace("Z", "+00:00")).strftime("%b %Y")
            body.append(f'<text x="26" y="{height - 44 + index * 20}" font-family="{MONO}" font-size="10.5" fill="{MUTED}">{caption}  <tspan fill="{TEXT}">{escape(repo["name"][:22])}</tspan>  {when}</text>')
    svg("logbook.svg", width, height, "".join(body), f"{(now - joined).days} days on GitHub since {joined.strftime('%B %Y')}")


def spectra(repos):
    """Each repository's language mix as one line of a spectrum."""
    shown = repos[:6]
    width, height = 840, 74 + len(shown) * 26
    left, right = 250, width - 28
    body = [backdrop(width, height)]
    body.append(f'<text x="26" y="34" font-family="{MONO}" font-size="12" letter-spacing="2" fill="{PINK}">SPECTRA</text>')
    body.append(f'<text x="{right}" y="34" text-anchor="end" font-family="{SANS}" font-size="11" fill="{MUTED}">One line per repository: its mix of languages.</text>')
    for index, repo in enumerate(shown):
        y = 58 + index * 26
        total = code_size(repo) or 1
        body.append(f'<text x="28" y="{y + 9}" font-family="{MONO}" font-size="11.5" fill="{TEXT}">{escape(repo["name"][:26])}</text>')
        x = float(left)
        for edge in repo["languages"]["edges"]:
            span = (right - left) * edge["size"] / total
            body.append(f'<rect x="{x:.1f}" y="{y}" width="{max(span - 1.5, 0.6):.1f}" height="11" rx="2" fill="{edge["node"]["color"] or PINK}"><title>{escape(edge["node"]["name"])}</title></rect>')
            x += span
    body.append(f'<clipPath id="lines"><rect x="{left}" y="52" width="{right - left}" height="{len(shown) * 26}"/></clipPath><g clip-path="url(#lines)"><rect class="scan" x="{left - 60}" y="52" width="46" height="{len(shown) * 26}" fill="#fff" opacity=".16"/></g>')
    css = f"@keyframes scan{{0%,55%{{transform:translateX(0)}}100%{{transform:translateX({right - left + 80}px)}}}}.scan{{animation:scan 7s ease-in-out infinite}}@media(prefers-reduced-motion:reduce){{.scan{{animation:none}}}}"
    svg("spectra.svg", width, height, "".join(body), "Language mix per repository: " + "; ".join(f"{repo['name']}: " + ", ".join(edge["node"]["name"] for edge in repo["languages"]["edges"][:3]) for repo in shown), css)


# Annual meteor showers: (month, day of the usual peak, name, meteors per hour at best).
SHOWERS = [(1, 3, "Quadrantids", 110), (4, 22, "Lyrids", 18), (5, 6, "Eta Aquariids", 50), (8, 12, "Perseids", 100), (10, 21, "Orionids", 20), (11, 17, "Leonids", 15), (12, 14, "Geminids", 150), (12, 22, "Ursids", 10)]
# The four turning points of the year, to the usual day.
SEASONS = [(3, 20, "March equinox"), (6, 21, "June solstice"), (9, 22, "September equinox"), (12, 21, "December solstice")]


def upcoming(events, today):
    """The next (date, rest...) among yearly events given as (month, day, ...)."""
    dated = [(date(year, month, day), *rest) for year in (today.year, today.year + 1) for month, day, *rest in events]
    return min(event for event in dated if event[0] >= today)


def meteors(today):
    """Countdown to the next annual meteor shower."""
    width, height = 412, 260
    when, name, rate = upcoming(SHOWERS, today)
    days = (when - today).days
    body = [backdrop(width, height)]
    body.append(f'<clipPath id="shower"><rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="15"/></clipPath><g clip-path="url(#shower)">')
    for index, (x, y, length) in enumerate(((360, 30, 60), (300, 70, 44), (396, 96, 52), (250, 26, 36))):
        body.append(f'<g class="streak" style="animation-delay:-{index * 1.3:.1f}s;animation-duration:{4.6 + index * 0.9:.1f}s"><path d="M{x} {y}l-{length} {length * 0.55:.0f}" stroke="url(#tail)" stroke-width="1.6" stroke-linecap="round"/></g>')
    body.append("</g>")
    body.insert(1, f'<defs><linearGradient id="tail" x1="1" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff3f7" stop-opacity="0"/><stop offset="1" stop-color="#fff3f7"/></linearGradient></defs>')
    body.append(f'<text x="26" y="38" font-family="{MONO}" font-size="12" letter-spacing="2" fill="{PINK}">NEXT METEOR SHOWER</text>')
    body.append(f'<text x="26" y="118" font-family="{SERIF}" font-size="30" font-style="italic" fill="{TEXT}">{name}</text>')
    countdown = "tonight" if days == 0 else "tomorrow" if days == 1 else f"in {days} days"
    body.append(f'<text x="26" y="152" font-family="{SANS}" font-size="20" font-weight="700" fill="{TEXT}">{countdown}</text>')
    body.append(f'<text x="26" y="{height - 34}" font-family="{SANS}" font-size="11" fill="{MUTED}">Peaks around {when.strftime("%B")} {when.day}, with up to</text><text x="26" y="{height - 20}" font-family="{SANS}" font-size="11" fill="{MUTED}">about {rate} meteors an hour under a dark sky.</text>')
    css = "@keyframes streak{0%{transform:translate(70px,-38px);opacity:0}10%{opacity:1}34%{transform:translate(-150px,82px);opacity:0}100%{transform:translate(-150px,82px);opacity:0}}.streak{animation:streak linear infinite}@media(prefers-reduced-motion:reduce){.streak{animation:none}}"
    svg("meteors.svg", width, height, "".join(body), f"Next meteor shower: {name}, {countdown}, peaking around {when.strftime('%B')} {when.day}", css)


def earth(today):
    """Where the Earth is on its way round the Sun today."""
    width, height = 412, 260
    cx, cy, radius = 298, 132, 78
    start = date(today.year, 1, 1)
    length = (date(today.year + 1, 1, 1) - start).days
    day = (today - start).days + 1

    def spot(day_of_year, distance=radius):
        angle = math.radians(day_of_year / length * 360 - 90)
        return round(cx + distance * math.cos(angle), 1), round(cy + distance * math.sin(angle), 1)

    body = [backdrop(width, height)]
    body.append(f'<text x="26" y="38" font-family="{MONO}" font-size="12" letter-spacing="2" fill="{PINK}">THIS ORBIT</text>')
    body.append(f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="{PINK}" stroke-opacity=".28"/>')
    ex, ey = spot(day)
    sweep = f"M{cx} {cy - radius}A{radius} {radius} 0 {1 if day / length > 0.5 else 0} 1 {ex} {ey}"
    body.append(f'<path d="{sweep}" fill="none" stroke="#ffe1ea" stroke-width="2" stroke-linecap="round"/>')
    for month, dom, label in SEASONS:
        mx, my = spot((date(today.year, month, dom) - start).days + 1)
        lx, ly = spot((date(today.year, month, dom) - start).days + 1, radius + 15)
        body.append(f'<circle cx="{mx}" cy="{my}" r="2.6" fill="{PINK}"/><text x="{lx}" y="{ly + 3}" text-anchor="middle" font-family="{MONO}" font-size="8.5" fill="{MUTED}">{label[:3].upper()}</text>')
    body.append(f'<circle cx="{cx}" cy="{cy}" r="15" fill="{PINK}" opacity=".1"/>' + sparkle(cx, cy, 10, "#ffe1ea", 1, ' class="tw"'))
    body.append(f'<circle cx="{ex}" cy="{ey}" r="6.5" fill="#8fb7ff"/><path d="M{ex - 4} {ey - 1}q3 -4 6 -1q-2 4 -6 1z" fill="#7fd6a4"/>')
    body.append(f'<g class="spin" style="transform-origin:{ex}px {ey}px;animation-duration:6s"><circle cx="{ex + 13}" cy="{ey}" r="2" fill="#e9d3dc"/></g>')
    when, label = upcoming(SEASONS, today)
    body.append(f'<text x="26" y="112" font-family="{SANS}" font-size="34" font-weight="700" letter-spacing="-1" fill="{TEXT}">{day / length * 100:.0f}%</text>')
    body.append(f'<text x="26" y="134" font-family="{MONO}" font-size="10.5" fill="{MUTED}">of {today.year}, day {day} of {length}</text>')
    body.append(f'<text x="26" y="{height - 34}" font-family="{SANS}" font-size="11" fill="{MUTED}">{(when - today).days} days to the</text><text x="26" y="{height - 20}" font-family="{SANS}" font-size="11" fill="{MUTED}">{label}.</text>')
    svg("earth.svg", width, height, "".join(body), f"Day {day} of {length}: {day / length * 100:.0f}% of {today.year}, {(when - today).days} days to the {label}")


def cargo(repos):
    """What recent commits were for, judged from keywords in each message."""
    # Checked in order, so "Fix ... and add ..." counts as a fix and a README rewrite as docs.
    kinds = [
        ("docs", r"readme|\bdocs?\b|translat|screenshot"),
        ("releases", r"release|initial|ilk commit|^v ?\d|installer"),
        ("fixes", r"\bfix|düzelt|bug"),
        ("features", r"\bfeat|\badd|\bkeep|\bmake|\buse\b|ekle|implement"),
        ("upkeep", r"update|güncel|merge|refresh|refactor|simplify|default|chore|clean"),
    ]
    counts = {name: 0 for name, _ in kinds} | {"other": 0}
    for _, _, message in all_commits(repos):
        head = message.lower()
        counts[next((name for name, pattern in kinds if re.search(pattern, head)), "other")] += 1
    rows = [(name, count) for name, count in counts.items() if count]
    rows.sort(key=lambda row: -row[1])
    peak = max((count for _, count in rows), default=1)
    width, height = 840, 66 + max(1, len(rows)) * 24
    body = [backdrop(width, height)]
    body.append(f'<text x="26" y="34" font-family="{MONO}" font-size="12" letter-spacing="2" fill="{PINK}">CARGO</text>')
    body.append(f'<text x="{width - 28}" y="34" text-anchor="end" font-family="{SANS}" font-size="11" fill="{MUTED}">What the last {sum(counts.values())} commits carried, going by their messages.</text>')
    for index, (name, count) in enumerate(rows):
        y = 54 + index * 24
        span = 560 * count / peak
        body.append(f'<text x="28" y="{y + 10}" font-family="{MONO}" font-size="11.5" fill="{TEXT}">{name}</text>')
        body.append(f'<rect class="load" x="150" y="{y}" width="{span:.1f}" height="12" rx="6" fill="{"#ffe1ea" if index == 0 else PINK}" opacity="{1 if index == 0 else 0.75 - index * 0.09:.2f}" style="transform-origin:150px {y + 6}px;animation-delay:{index * 0.18:.2f}s"/>')
        body.append(f'<text x="{162 + span:.1f}" y="{y + 10}" font-family="{MONO}" font-size="11" fill="{MUTED}">{count}</text>')
    css = "@keyframes load{0%{transform:scaleX(0)}18%,100%{transform:scaleX(1)}}.load{animation:load 9s cubic-bezier(.2,.8,.2,1) infinite}@media(prefers-reduced-motion:reduce){.load{animation:none}}"
    svg("cargo.svg", width, height, "".join(body), "Recent commits by kind: " + ", ".join(f"{count} {name}" for name, count in rows), css)


def when(stamp):
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def control(repos, now):
    """A status board: one row per repository with what is open and how recently it moved."""
    shown = repos[:8]
    width, height = 840, 82 + len(shown) * 26
    columns = [(330, "issues"), (430, "pull requests"), (560, "releases"), (680, "last push")]
    body = [backdrop(width, height)]
    body.append(f'<text x="28" y="38" font-family="{MONO}" font-size="12.5" fill="{TEXT}"><tspan fill="{PINK}">{LOGIN}@github</tspan> ~ $ ./mission-control</text>')
    for x, label in columns:
        body.append(f'<text x="{x}" y="64" text-anchor="end" font-family="{MONO}" font-size="9.5" letter-spacing="1" fill="{MUTED}">{label.upper()}</text>')
    body.append(f'<text x="{width - 28}" y="64" text-anchor="end" font-family="{MONO}" font-size="9.5" letter-spacing="1" fill="{MUTED}">STATUS</text>')
    for index, repo in enumerate(shown):
        y = 88 + index * 26
        age = (now - when(repo["pushedAt"])).days
        status, color, live = ("active", "#ffe1ea", True) if age <= 14 else ("quiet", PINK, False) if age <= 90 else ("dormant", MUTED, False)
        ago = "today" if age <= 0 else f"{age}d ago"
        values = [repo["issues"]["totalCount"], repo["pullRequests"]["totalCount"], repo["releases"]["totalCount"], ago]
        body.append(f'<text x="28" y="{y}" font-family="{MONO}" font-size="12" fill="{TEXT}">{escape(repo["name"][:28])}</text>')
        for (x, _), value in zip(columns, values):
            body.append(f'<text x="{x}" y="{y}" text-anchor="end" font-family="{MONO}" font-size="12" fill="{TEXT if value not in (0, "0") else MUTED}">{value}</text>')
        pulse = f' class="tw" style="animation-delay:-{index * 0.5:.1f}s"' if live else ""
        body.append(f'<circle cx="{width - 34}" cy="{y - 4}" r="4" fill="{color}"{pulse}/>')
        body.append(f'<text x="{width - 46}" y="{y}" text-anchor="end" font-family="{MONO}" font-size="11" fill="{color}">{status}</text>')
    svg("control.svg", width, height, "".join(body), "Status board: " + "; ".join(f"{repo['name']} {repo['issues']['totalCount']} open issues, {repo['releases']['totalCount']} releases" for repo in shown))


def trail(repos, now):
    """Every release of the last twelve months, one lane per repository."""
    shown = repos[:8]
    width, height = 840, 92 + len(shown) * 26
    left, right, span_days = 236, width - 60, 365
    body = [backdrop(width, height)]
    body.append(f'<text x="26" y="34" font-family="{MONO}" font-size="12" letter-spacing="2" fill="{PINK}">RELEASE TRAIL</text>')
    body.append(f'<text x="{width - 28}" y="34" text-anchor="end" font-family="{SANS}" font-size="11" fill="{MUTED}">Each star is a release in the last twelve months.</text>')

    def x_of(moment):
        return right - (right - left) * (now - moment).days / span_days

    for back in range(12):
        tick = (now.replace(day=1) - timedelta(days=30 * back)).replace(day=1)
        if (now - tick).days <= span_days:
            x = x_of(tick)
            body.append(f'<path d="M{x:.1f} 50V{62 + len(shown) * 26}" stroke="{PINK}" stroke-opacity=".1"/>')
            if back % 2 == 0:
                body.append(f'<text x="{x:.1f}" y="{80 + len(shown) * 26}" text-anchor="middle" font-family="{MONO}" font-size="9.5" fill="{MUTED}">{tick.strftime("%b")}</text>')
    for index, repo in enumerate(shown):
        y = 68 + index * 26
        recent = [node for node in repo["releases"]["nodes"] if node["publishedAt"] and (now - when(node["publishedAt"])).days <= span_days]
        body.append(f'<text x="28" y="{y + 4}" font-family="{MONO}" font-size="11.5" fill="{TEXT}">{escape(repo["name"][:24])}</text>')
        body.append(f'<path d="M{left} {y}H{right}" stroke="{ROSE}" stroke-opacity=".35" stroke-dasharray="1 6"/>')
        for position, node in enumerate(recent):
            newest = position == 0
            body.append(sparkle(round(x_of(when(node["publishedAt"])), 1), y, 7 if newest else 4.5, "#ffe1ea" if newest else PINK, 1 if newest else 0.8, ' class="tw"' if newest else ""))
        body.append(f'<text x="{width - 28}" y="{y + 4}" text-anchor="end" font-family="{MONO}" font-size="11" fill="{PINK if recent else MUTED}">{len(recent) or "–"}</text>')
    svg("trail.svg", width, height, "".join(body), "Releases in the last twelve months: " + ", ".join(f"{repo['name']} {repo['releases']['totalCount']}" for repo in shown))


def stargazers(repos):
    """The latest people to star something, by name."""
    fans = sorted(((edge["starredAt"], edge["node"]["login"], repo["name"]) for repo in repos for edge in repo["stargazers"]["edges"] if edge["node"]["login"].lower() != LOGIN), reverse=True)[:6]
    width, height = 840, 104
    body = [backdrop(width, height)]
    body.append(f'<text x="26" y="34" font-family="{MONO}" font-size="12" letter-spacing="2" fill="{PINK}">STARGAZERS</text>')
    body.append(f'<text x="26" y="72" font-family="{SERIF}" font-size="21" font-style="italic" fill="{TEXT}">{"thank you" if fans else "be the first star"}</text>')
    x = 150
    for index, (_, login, repo) in enumerate(fans):
        chip = round((len(login) + len(repo)) * 6.9 + 62)
        if x + chip > width - 20:
            break
        body.append(f'<rect x="{x}" y="52" width="{chip}" height="30" rx="15" fill="{PINK}" fill-opacity=".08" stroke="{PINK}" stroke-opacity=".35"/>')
        body.append(sparkle(x + 16, 67, 5.5, "#ffe1ea", 1, f' class="tw" style="animation-delay:-{index * 0.7:.1f}s"'))
        body.append(f'<text x="{x + 28}" y="71.5" font-family="{SANS}" font-size="12.5" font-weight="700" fill="{TEXT}">@{escape(login)}<tspan dx="7" font-family="{MONO}" font-size="10.5" font-weight="400" fill="{MUTED}">{escape(repo)}</tspan></text>')
        x += chip + 10
    svg("stargazers.svg", width, height, "".join(body), "Latest stargazers: " + ", ".join(f"{login} starred {repo}" for _, login, repo in fans))


SYNODIC = 29.530588853
PHASES = ["New moon", "Waxing crescent", "First quarter", "Waxing gibbous", "Full moon", "Waning gibbous", "Last quarter", "Waning crescent"]


def moon(now):
    """Tonight's moon, from the mean lunar cycle (good to within a few hours)."""
    width, height = 412, 260
    age = ((now - datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)).total_seconds() / 86400) % SYNODIC
    phase = age / SYNODIC
    lit = (1 - math.cos(2 * math.pi * phase)) / 2
    name = PHASES[round(phase * 8) % 8]
    to_full = (SYNODIC / 2 - age) % SYNODIC
    cx, cy, r = 112, 140, 64
    waxing = phase < 0.5
    rx = round(r * abs(math.cos(2 * math.pi * phase)), 1)
    outer = 1 if waxing else 0
    # The terminator bulges toward the lit limb for a crescent and away from it for a gibbous moon.
    crescent = phase < 0.25 or phase > 0.75
    inner = (0 if crescent else 1) if waxing else (1 if crescent else 0)
    body = [backdrop(width, height, "moon", 18)]
    body.append(f'<defs><radialGradient id="lit" cx=".4" cy=".35"><stop offset="0" stop-color="#fff3f7"/><stop offset="1" stop-color="{PINK}"/></radialGradient></defs>')
    body.append(f'<text x="26" y="38" font-family="{MONO}" font-size="12" letter-spacing="2" fill="{PINK}">TONIGHT\'S MOON</text>')
    body.append(f'<circle cx="{cx}" cy="{cy}" r="{r + 12}" fill="{PINK}" opacity="{0.03 + 0.07 * lit:.2f}"/>')
    body.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#2a1722" stroke="{LINE}"/>')
    body.append(f'<path d="M{cx} {cy - r}A{r} {r} 0 0 {outer} {cx} {cy + r}A{rx} {r} 0 0 {inner} {cx} {cy - r}Z" fill="url(#lit)"/>')
    for dx, dy, size in ((-22, -18, 9), (16, 10, 13), (-8, 28, 7), (26, -26, 6)):
        body.append(f'<circle cx="{cx + dx}" cy="{cy + dy}" r="{size}" fill="#3a1d2c" opacity=".16"/>')
    x = 212
    body.append(f'<text x="{x}" y="112" font-family="{SERIF}" font-size="23" font-style="italic" fill="{TEXT}">{name}</text>')
    rows = [(f"{lit * 100:.0f}%", "illuminated"), (f"day {age:.0f}", "of 29.5"), (f"{to_full:.0f} d" if to_full >= 1 else "tonight", "to full moon")]
    for index, (value, caption) in enumerate(rows):
        body.append(f'<text x="{x}" y="{144 + index * 26}" font-family="{SANS}" font-size="16" font-weight="700" fill="{TEXT}">{value}<tspan dx="7" font-family="{MONO}" font-size="10.5" font-weight="400" fill="{MUTED}">{caption}</tspan></text>')
    svg("moon.svg", width, height, "".join(body), f"Tonight's moon: {name}, {lit * 100:.0f}% illuminated")


def launches(repos):
    """Latest release of each repository, newest first, as a terminal listing."""
    rows = []
    for repo in repos:
        release = (repo["releases"]["nodes"] or [None])[0]
        if release and release["publishedAt"]:
            rows.append((release["publishedAt"], repo["name"], release["tagName"], "released"))
        else:
            rows.append((repo["pushedAt"], repo["name"], "main", "last push"))
    rows = sorted(rows, reverse=True)[:5]
    width, height = 840, 68 + len(rows) * 26
    body = [backdrop(width, height, "launches", 30)]
    body.append(f'<text x="28" y="38" font-family="{MONO}" font-size="12.5" fill="{TEXT}"><tspan fill="{PINK}">{LOGIN}@github</tspan> ~ $ ./launches --recent</text>')
    for index, (when, name, tag, verb) in enumerate(rows):
        y = 70 + index * 26
        stamp = datetime.fromisoformat(when.replace("Z", "+00:00")).strftime("%b %d, %Y")
        body.append(sparkle(34, y - 4, 5, "#ffe1ea" if index == 0 else PINK, 1 if index == 0 else 0.6, ' class="tw"' if index == 0 else ""))
        body.append(f'<text x="52" y="{y}" font-family="{MONO}" font-size="12.5" fill="{TEXT}">{escape(name)}</text>')
        body.append(f'<text x="290" y="{y}" font-family="{MONO}" font-size="12.5" fill="{PINK}">{escape(tag)}</text>')
        body.append(f'<text x="{width - 28}" y="{y}" text-anchor="end" font-family="{MONO}" font-size="11.5" fill="{MUTED}">{verb} {stamp}</text>')
    svg("launches.svg", width, height, "".join(body), "Latest releases: " + ", ".join(f"{name} {tag}" for _, name, tag, _ in rows))


def main():
    OUT.mkdir(exist_ok=True)
    for stale in OUT.glob("*.svg"):
        stale.unlink()
    user = fetch()
    repos = [repo for repo in user["repositories"]["nodes"] if repo["name"].lower() != LOGIN]
    calendar = user["contributionsCollection"]["contributionCalendar"]
    now = datetime.now(timezone.utc)

    header(user, repos[:6])
    terminal(user, repos, calendar)
    for repo in repos:
        card(repo)
    orbits(repos)
    moon(now)
    galaxy(calendar)
    signal(calendar)
    blackhole(repos)
    radar(user, repos, now)
    mission(calendar, now.date())
    sky(calendar)
    launches(repos)
    ticker(repos, now)
    languages(repos)
    toolkit()
    aurora()

    milestones(calendar, repos)
    hours(repos)
    logbook(user, repos, now)
    spectra(repos)
    meteors(now.date())
    earth(now.date())
    cargo(repos)
    control(repos, now)
    trail(repos, now)
    stargazers(repos)

    name = NAME
    poster("sky-top.svg", [["header.svg"], ["terminal.svg"]], f"{name}: desktop tools and small universes. " + CARDS["terminal.svg"][4], round_top=True)
    cards = [f"repo-{repo['name']}.svg" for repo in repos]
    rows = [cards[index:index + 2] for index in range(0, len(cards), 2)]
    rows += [["orbits.svg", "moon.svg"], ["galaxy.svg", "signal.svg"], ["blackhole.svg", "radar.svg"], ["hours.svg", "logbook.svg"], ["earth.svg", "meteors.svg"]]
    rows += [[key] for key in ("control.svg", "mission.svg", "milestones.svg", "sky.svg", "launches.svg", "trail.svg", "ticker.svg", "cargo.svg", "languages.svg", "spectra.svg", "toolkit.svg", "stargazers.svg", "aurora.svg")]
    poster("sky-main.svg", rows, ". ".join(CARDS[key][4] for row in rows for key in row), round_bottom=True)

    # The menu carries the links, since a poster is a single image. One button per repository, added automatically.
    links = [(DISCORD[0], DISCORD[1], True)] + [(repo["name"], repo["url"], False) for repo in repos]
    # One paragraph with no whitespace between the tags: any gap would let the page show through.
    readme = (
        f'<p><img src="assets/sky-top.svg" width="100%" align="top" alt="{escape(name)}: desktop tools and small universes">'
        f"{menu(links)}"
        '<img src="assets/sky-main.svg" width="100%" align="top" alt="Projects, orbits, tonight\'s moon, a contribution galaxy, streaks, milestones, recent releases and commits, drawn as one night sky"></p>\n\n'
        '<sub>The sky and every button are SVGs drawn by <a href="build.py"><code>build.py</code></a> from the GitHub API and redrawn every three hours: a new repository gets its own card, planet, radar blip and menu button without any editing.</sub>\n'
    )
    (Path(__file__).parent / "README.md").write_text(readme, encoding="utf-8", newline="\n")
    print("drew", len(CARDS), "cards and", len(links), "menu buttons for", ", ".join(repo["name"] for repo in repos))


if __name__ == "__main__":
    main()
