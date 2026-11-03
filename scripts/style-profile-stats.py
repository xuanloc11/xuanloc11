"""Render the hourly GitHub cards in the profile's neon style."""

from html import escape
from pathlib import Path
import re
import xml.etree.ElementTree as ET


ROWS = [
    ("stars", "Total Earned Stars", "★"),
    ("commits", "Commits (last year)", "ϟ"),
    ("prs", "Pull Requests", "⑂"),
    ("issues", "Issues", "◉"),
    ("contribs", "Contributed Repos (year)", "▣"),
]


def text_value(root, test_id):
    node = root.find(f".//*[@data-testid='{test_id}']")
    if node is None or not "".join(node.itertext()).strip():
        raise ValueError(f"Missing card data: {test_id}")
    return "".join(node.itertext()).strip()


def label(x, y, value, css="", extra=""):
    return f'<text x="{x}" y="{y}" class="{css}" {extra}>{escape(value)}</text>'


def panel(title, height=225):
    return (
        f'<rect x="1" y="1" width="493" height="{height - 2}" rx="13" '
        'fill="#161521" stroke="#2d2841" stroke-width="1.5"/>'
        '<circle cx="33" cy="32" r="5.5" fill="#ff408f"/>'
        + label(49, 37, title, "heading")
    )


def render_cards(stats_svg, languages_svg):
    # shortcut: selectors follow the pinned stats core; check them when upgrading it.
    stats = ET.fromstring(stats_svg)
    languages = ET.fromstring(languages_svg)
    title = text_value(stats, "header")
    rank = text_value(stats, "level-rank-icon")
    if rank not in {"S", "A+", "A", "A-", "B+", "B", "B-", "C+", "C"}:
        raise ValueError("Invalid GitHub rank")
    values = []
    description = []
    for key, name, icon in ROWS:
        value = text_value(stats, key)
        if not re.fullmatch(r"[0-9][0-9.,]*[kmbKMB]?", value):
            raise ValueError(f"Invalid numeric statistic: {key}")
        values.append((name, icon, value))
        description.append(f"{name}: {value}")
    description.append(f"GitHub rank: {rank}")

    names = languages.findall(".//*[@data-testid='lang-name']")
    bars = languages.findall(".//*[@data-testid='lang-progress']")
    if not 1 <= len(names) <= 6 or len(names) != len(bars):
        raise ValueError("Expected one to six languages with matching chart segments")
    language_data = []
    for name, bar in zip(names, bars):
        match = re.fullmatch(r"(.+) ([0-9]+(?:\.[0-9]+)?)%", "".join(name.itertext()).strip())
        color = bar.get("fill", "")
        if not match or not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            raise ValueError("Invalid language data")
        language, percentage = match.groups()
        if not 0 <= float(percentage) <= 100:
            raise ValueError("Invalid language percentage")
        language_data.append((language, percentage, color))
    total = sum(float(item[1]) for item in language_data)
    if not 99.9 <= total <= 100.1:
        raise ValueError("Language percentages must total 100")
    for language, percentage, color in language_data:
        description.append(f"{language}: {percentage}%")

    outputs = {}
    for filename, width, height, placement, mobile in [
        ("github-metrics.svg", 1010, 225, "515,0", False),
        ("github-metrics-mobile.svg", 495, 585, "0,265", True),
    ]:
        stats_body = panel(title, 245 if mobile else 225)
        for index, (name, icon, value) in enumerate(values):
            y = 88 + index * 32 if mobile else 77 + index * 27
            stats_body += label(28, y, icon, "icon")
            stats_body += label(49, y, name)
            stats_body += label(445 if mobile else 300, y, value, "value", 'text-anchor="end"')
        if mobile:
            stats_body += '<circle cx="438" cy="33" r="23" fill="none" stroke="url(#rank-gradient)" stroke-width="3"/>'
            stats_body += label(438, 41, rank, "rank", 'text-anchor="middle"')
        else:
            stats_body += (
                '<circle cx="402" cy="128" r="43" fill="none" stroke="#252b43" stroke-width="5"/>'
                '<path d="M359 128a43 43 0 1 1 43 43" fill="none" stroke="url(#rank-gradient)" stroke-width="5"/>'
                + label(402, 135, rank, "rank", 'text-anchor="middle"')
                + label(402, 155, "GITHUB RANK", "rank-label", 'text-anchor="middle"')
            )
        langs_body = panel("Most Used Languages", 320 if mobile else 225)
        x = 28
        rows_per_column = len(language_data) if mobile else (len(language_data) + 1) // 2
        for index, (language, percentage, color) in enumerate(language_data):
            segment_width = (439 - 4 * (len(language_data) - 1)) * float(percentage) / total
            langs_body += f'<rect x="{x:.2f}" y="58" width="{segment_width:.2f}" height="13" rx="4" fill="{color}"/>'
            x += segment_width + 4
            column, row = divmod(index, rows_per_column)
            left, y = 29 + column * 230, 107 + row * 36
            langs_body += f'<circle cx="{left + 5}" cy="{y - 5}" r="5" fill="{color}"/>'
            # Full names remain in the accessible description.
            limit = 25 if mobile else 15
            display_name = language if len(language) <= limit else language[:limit - 1] + "…"
            langs_body += label(left + 20, y, display_name)
            langs_body += label(445 if mobile else left + 205, y, percentage + "%", "value", 'text-anchor="end"')
        outputs[filename] = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">{escape(title)} and Most Used Languages</title>
  <desc id="desc">{escape('; '.join(description))}. Languages are percentages of the displayed top languages.</desc>
  <defs><linearGradient id="rank-gradient" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#12b8a6"/><stop offset="1" stop-color="#008acb"/></linearGradient></defs>
  <style>
    text{{font-family:Segoe UI,Arial,sans-serif;font-size:{22 if mobile else 14}px;font-weight:600;fill:#80f1ff}}
    .heading{{font-size:{22 if mobile else 18}px;font-weight:700;fill:#ff408f}}
    .value{{fill:#ffe64d;font-weight:700}}.icon{{fill:#80f1ff;font-size:16px}}
    .rank{{font-size:28px;font-weight:800}}.rank-label{{font-size:10px;fill:#ff408f}}
  </style>
  <g>{stats_body}</g>
  <g transform="translate({placement})">{langs_body}</g>
</svg>
'''
    return outputs


if __name__ == "__main__":
    directory = Path("dist")
    cards = render_cards(
        (directory / "stats.svg").read_text(encoding="utf-8"),
        (directory / "top-langs.svg").read_text(encoding="utf-8"),
    )
    # Validate both inputs before replacing any published image.
    for filename, svg in cards.items():
        (directory / filename).write_text(svg, encoding="utf-8")
