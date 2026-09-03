import json
import os
import urllib.request
from datetime import date, timedelta
from pathlib import Path


USERNAME = "Abdulqasem-Bakhshi"
OUTPUT = Path("assets/github-contributions.svg")

TOKEN = os.environ["GH_TOKEN"]

today = date.today()
start = today - timedelta(days=364)

query = """
query($username: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $username) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
            weekday
          }
        }
      }
    }
  }
}
"""

variables = {
    "username": USERNAME,
    "from": f"{start.isoformat()}T00:00:00Z",
    "to": f"{today.isoformat()}T23:59:59Z",
}

payload = json.dumps({
    "query": query,
    "variables": variables,
}).encode("utf-8")

request = urllib.request.Request(
    "https://api.github.com/graphql",
    data=payload,
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "github-contribution-calendar",
    },
)

with urllib.request.urlopen(request) as response:
    result = json.load(response)

if "errors" in result:
    raise RuntimeError(json.dumps(result["errors"], indent=2))

calendar = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]

days = {}

for week in calendar["weeks"]:
    for day in week["contributionDays"]:
        days[day["date"]] = day["contributionCount"]


# ------------------------------------------------------------
# SVG settings
# ------------------------------------------------------------

CELL = 12
GAP = 3
STEP = CELL + GAP

LEFT = 42
TOP = 30
BOTTOM = 30

# GitHub-style contribution colors
COLORS = [
    "#161b22",  # 0
    "#0e4429",  # 1-3
    "#006d32",  # 4-7
    "#26a641",  # 8-15
    "#39d353",  # 16+
]

MAX_COLUMNS = 53

width = LEFT + (MAX_COLUMNS * STEP) + 10
height = TOP + (7 * STEP) + BOTTOM


def color_for_count(count):
    if count == 0:
        return COLORS[0]
    if count <= 3:
        return COLORS[1]
    if count <= 7:
        return COLORS[2]
    if count <= 15:
        return COLORS[3]
    return COLORS[4]


# ------------------------------------------------------------
# Build SVG
# ------------------------------------------------------------

svg = []

svg.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" '
    f'width="{width}" height="{height}" '
    f'viewBox="0 0 {width} {height}">'
)

svg.append(
    '<style>'
    'text { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", '
    'Helvetica, Arial, sans-serif; }'
    '</style>'
)

# Background
svg.append(
    f'<rect width="{width}" height="{height}" '
    f'rx="6" fill="#0d1117"/>'
)

# Month labels
months_seen = set()

# Find Sunday before/at first day
first_day = start - timedelta(days=(start.weekday() + 1) % 7)

current = first_day
column = 0

while current <= today and column < MAX_COLUMNS:
    month_key = (current.year, current.month)

    if month_key not in months_seen:
        # Don't put a label too close to the left edge
        if column >= 1:
            month_name = current.strftime("%b")

            x = LEFT + (column * STEP)

            svg.append(
                f'<text x="{x}" y="16" '
                f'font-size="10" fill="#8b949e">'
                f'{month_name}</text>'
            )

        months_seen.add(month_key)

    current += timedelta(days=7)
    column += 1


# Day labels
day_labels = {
    1: "Mon",
    3: "Wed",
    5: "Fri",
}

for weekday, label in day_labels.items():
    y = TOP + (weekday * STEP) + 10

    svg.append(
        f'<text x="0" y="{y}" '
        f'font-size="10" fill="#8b949e">'
        f'{label}</text>'
    )


# Contribution squares
current = first_day

while current <= today:
    column = (current - first_day).days // 7
    weekday = (current.weekday() + 1) % 7  # Sunday = 0

    if column < MAX_COLUMNS:
        count = days.get(current.isoformat(), 0)

        x = LEFT + (column * STEP)
        y = TOP + (weekday * STEP)

        svg.append(
            f'<rect x="{x}" y="{y}" '
            f'width="{CELL}" height="{CELL}" rx="2" '
            f'fill="{color_for_count(count)}">'
            f'<title>{current.isoformat()}: '
            f'{count} contributions</title>'
            f'</rect>'
        )

    current += timedelta(days=1)


# Legend
legend_y = height - 12

svg.append(
    f'<text x="{LEFT}" y="{legend_y}" '
    f'font-size="10" fill="#8b949e">Less</text>'
)

legend_x = LEFT + 28

for index, color in enumerate(COLORS):
    svg.append(
        f'<rect x="{legend_x + index * STEP}" '
        f'y="{legend_y - 10}" '
        f'width="{CELL}" height="{CELL}" rx="2" '
        f'fill="{color}"/>'
    )

svg.append(
    f'<text x="{legend_x + len(COLORS) * STEP + 4}" '
    f'y="{legend_y}" '
    f'font-size="10" fill="#8b949e">More</text>'
)

svg.append("</svg>")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("\n".join(svg), encoding="utf-8")

print(f"Generated {OUTPUT}")