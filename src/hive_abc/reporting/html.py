"""Obsidian Aqua HTML report renderer for analysis deliverables."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from html import escape

import pandas as pd

# --------------------------------------------------------------------------------------
# Global Variables
# - Note1: Design tokens follow the obsidian-aqua-brand skill (npidi's brand).
# --------------------------------------------------------------------------------------
OBSIDIAN_AQUA_CSS = """
:root {
  --anchor-dark: #1A1A2E;
  --primary-aqua: #00E5FF;
  --accent-coral: #FF6B6B;
  --neutral-light: #F8FAFC;
  --neutral-border: #E2E8F0;
  --neutral-text: #1E293B;
  --muted-text: #64748B;
  --deep-midnight: #10101E;
  --font-sans: 'Outfit', 'Helvetica Neue', Arial, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: var(--font-sans);
  color: var(--neutral-text);
  background: var(--neutral-light);
  line-height: 1.6;
}
header {
  background: var(--anchor-dark);
  color: #FFFFFF;
  padding: 48px 8% 40px;
  border-bottom: 4px solid var(--primary-aqua);
}
header h1 { font-size: 2rem; font-weight: 600; }
header p.subtitle { color: var(--primary-aqua); margin-top: 8px; }
header p.meta { color: var(--muted-text); font-family: var(--font-mono);
  font-size: 0.85rem; margin-top: 12px; }
main { padding: 40px 8%; max-width: 1100px; }
section { margin-bottom: 40px; }
h2 {
  font-size: 1.3rem; font-weight: 600; margin-bottom: 16px;
  padding-bottom: 8px; border-bottom: 1px solid var(--neutral-border);
}
h2 .section-number { color: var(--primary-aqua); font-family: var(--font-mono);
  margin-right: 10px; }
p { margin-bottom: 12px; }
table {
  border-collapse: collapse; width: 100%; background: #FFFFFF;
  border: 1px solid var(--neutral-border); border-radius: 12px;
  overflow: hidden; font-size: 0.9rem; margin-bottom: 16px;
}
th {
  background: var(--anchor-dark); color: #FFFFFF; text-align: left;
  padding: 10px 14px; font-weight: 600;
}
td { padding: 9px 14px; border-top: 1px solid var(--neutral-border);
  font-family: var(--font-mono); }
td:first-child { font-family: var(--font-sans); font-weight: 600; }
tr:nth-child(even) td { background: var(--neutral-light); }
.notice {
  border-left: 4px solid var(--accent-coral); background: #FFFFFF;
  padding: 14px 18px; border-radius: 0 12px 12px 0; margin-bottom: 16px;
  box-shadow: 0 4px 16px rgba(26, 26, 46, 0.04);
}
.notice strong { color: var(--accent-coral); }
footer { padding: 24px 8%; color: var(--muted-text); font-size: 0.8rem; }
"""


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def render_report(
    title: str,
    subtitle: str,
    sections: list[tuple[str, str]],
    generated_note: str = "",
) -> str:
    """
    Renders a full Obsidian Aqua HTML page from pre-built section bodies.

    Args:
        title: Page title (rendered in sentence case on the dark header).
        subtitle: One-line description shown in primary aqua.
        sections: Ordered `(heading, html_body)` pairs; bodies are trusted
            HTML built with the helpers in this module.
        generated_note: Optional provenance line for the header (e.g., the
            command that produced the report).

    Returns:
        A complete standalone HTML document.
    """
    body_sections = "\n".join(
        f"<section><h2><span class='section-number'>{index:02d}</span>"
        f"{escape(heading)}</h2>{body}</section>"
        for index, (heading, body) in enumerate(sections, start=1)
    )
    meta = f"<p class='meta'>{escape(generated_note)}</p>" if generated_note else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>{OBSIDIAN_AQUA_CSS}</style>
</head>
<body>
<header>
<h1>{escape(title)}</h1>
<p class="subtitle">{escape(subtitle)}</p>
{meta}
</header>
<main>
{body_sections}
</main>
<footer>heuristic-portfolio-optimizer — obsidian aqua report</footer>
</body>
</html>
"""


def frame_to_html(frame: pd.DataFrame, float_format: str = "{:.3f}") -> str:
    """
    Renders a DataFrame as a brand-styled HTML table.

    Args:
        frame: Table to render; the index becomes the first column.
        float_format: Format applied to float cells.

    Returns:
        An HTML `<table>` fragment.
    """
    header_cells = "".join(
        f"<th>{escape(str(c))}</th>" for c in [frame.index.name or "", *frame.columns]
    )
    rows = []
    for index, row in frame.iterrows():
        cells = "".join(
            f"<td>{float_format.format(v) if isinstance(v, float) else escape(str(v))}"
            "</td>"
            for v in row
        )
        rows.append(f"<tr><td>{escape(str(index))}</td>{cells}</tr>")
    body = "".join(rows)
    return f"<table><thead><tr>{header_cells}</tr></thead><tbody>{body}</tbody></table>"


def notice(text: str, label: str = "IMPORTANT") -> str:
    """
    Renders a coral-accented notice block (the brand's critical callout).

    Args:
        text: Notice body text.
        label: Short uppercase label rendered in coral.

    Returns:
        An HTML fragment.
    """
    return (
        f"<div class='notice'><strong>{escape(label)}</strong> — {escape(text)}</div>"
    )
