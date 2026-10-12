"""Draws the profile README's SVG cards from live GitHub data.

Run locally with the GitHub CLI signed in, or in Actions with GITHUB_TOKEN set.
Standard library only. Output goes to assets/; the header is seeded so it does not
change from run to run.
"""
import json
import math
import os
import random
import subprocess
import urllib.request
from datetime import date, datetime, timezone
from html import escape
from pathlib import Path

LOGIN = "hfatih"
OUT = Path(__file__).parent / "assets"
SANS = "'Segoe UI', system-ui, -apple-system, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Consolas, 'Liberation Mono', monospace"
SERIF = "Georgia, 'Times New Roman', serif"
PINK, ROSE, TEXT, MUTED, LINE = "#f0abc5", "#e7a0b9", "#f5f5f6", "#a48a97", "#5a2a40"
# Descriptions for repositories whose GitHub description is empty.
FALLBACK = {"samanyolu3d": "Interactive 3D galaxy simulation and procedural galactic visualization in your browser."}

QUERY = """query($login: String!) { user(login: $login) {
  name createdAt
  contributionsCollection { contributionCalendar { totalContributions
    weeks { contributionDays { contributionCount date } } } }
  repositories(first: 50, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false,
               orderBy: {field: STARGAZERS, direction: DESC}) { nodes {
    name description stargazerCount url pushedAt
    releases(first: 1, orderBy: {field: CREATED_AT, direction: DESC}) { nodes { tagName publishedAt } }
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


def backdrop(width, height, seed, stars):
    """Card background: burgundy night with a seeded scatter of faint stars."""
    rng = random.Random(seed)
    parts = [
        f'<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1f1018"/><stop offset="1" stop-color="#130d14"/></linearGradient></defs>',
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="16" fill="url(#bg)" stroke="{LINE}"/>',
    ]
    for _ in range(stars):
        x, y = round(rng.uniform(10, width - 10), 1), round(rng.uniform(10, height - 10), 1)
        if rng.random() < 0.3:
            parts.append(sparkle(x, y, round(rng.uniform(2, 5), 1), "#ffc3d7", rng.uniform(0.1, 0.28)))
        else:
            parts.append(f'<circle cx="{x}" cy="{y}" r="{rng.uniform(0.6, 1.4):.1f}" fill="#ffc3d7" opacity="{rng.uniform(0.1, 0.3):.2f}"/>')
    return "".join(parts)


def svg(name, width, height, body, label, css=""):
    style = "<style>@keyframes tw{0%,100%{opacity:.25}50%{opacity:1}}.tw{animation:tw 3.2s ease-in-out infinite}@keyframes fall{0%{transform:translate(0,0);opacity:0}8%{opacity:.9}22%{transform:translate(-190px,95px);opacity:0}100%{opacity:0}}.fall{animation:fall 9s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}.spin{animation:spin linear infinite}@media(prefers-reduced-motion:reduce){.tw,.fall,.spin{animation:none}}</style>"
    extra = f"<style>{css}</style>" if css else ""
    text = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(label)}">{style}{extra}{body}</svg>\n'
    (OUT / name).write_text(text, encoding="utf-8", newline="\n")


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
    body = [backdrop(width, height, "header", 70)]
    body.append(f'<g class="fall"><path d="M800 28l-46 23" stroke="#ffd3e0" stroke-width="1.4" stroke-linecap="round"/></g>')
    body.append(f'<text x="40" y="62" font-family="{MONO}" font-size="12" letter-spacing="3" fill="{PINK}">HFATIH · GITHUB</text>')
    body.append(f'<text x="38" y="128" font-family="{SANS}" font-size="54" font-weight="700" letter-spacing="-2" fill="{TEXT}">{escape(user["name"] or LOGIN)}</text>')
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
    svg("header.svg", width, height, "".join(body), f"{user['name']}: desktop tools and small universes")


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
        ("", f"{user['name'] or LOGIN} · builds desktop tools and small universes"),
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
    user = fetch()
    repos = [repo for repo in user["repositories"]["nodes"] if repo["name"].lower() != LOGIN]
    header(user, repos[:6])
    for repo in repos:
        card(repo)
    sky(user["contributionsCollection"]["contributionCalendar"])
    languages(repos)
    calendar = user["contributionsCollection"]["contributionCalendar"]
    terminal(user, repos, calendar)
    galaxy(calendar)
    signal(calendar)
    orbits(repos)
    moon(datetime.now(timezone.utc))
    launches(repos)
    # Keep the README's project grid in step with the repositories that exist.
    readme = Path(__file__).parent / "README.md"
    before, _, rest = readme.read_text(encoding="utf-8").partition("<!-- projects:start -->")
    grid = "\n".join(f'<a href="{repo["url"]}"><img src="assets/repo-{repo["name"]}.svg" width="49.5%" alt="{escape(repo["name"])}"></a>' for repo in repos)
    tail = rest.partition("<!-- projects:end -->")[2]
    readme.write_text(f"{before}<!-- projects:start -->\n{grid}\n<!-- projects:end -->{tail}", encoding="utf-8", newline="\n")
    print("drew", 9 + len(repos), "cards for", ", ".join(repo["name"] for repo in repos))


if __name__ == "__main__":
    main()
