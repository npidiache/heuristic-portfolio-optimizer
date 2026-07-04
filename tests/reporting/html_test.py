"""Tests for the Obsidian Aqua HTML renderer."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import pandas as pd

from hive_abc.reporting.html import frame_to_html, notice, render_report


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def test_render_report_carries_brand_tokens_and_sections() -> None:
    html = render_report(
        title="PFA sensitivity",
        subtitle="ABC-FAEM trigger sweep",
        sections=[("Setup", "<p>body</p>"), ("Results", "<p>tables</p>")],
        generated_note="run 2026-07-04",
    )
    assert "#1A1A2E" in html and "#00E5FF" in html  # brand palette
    assert "Outfit" in html and "JetBrains Mono" in html
    assert "<span class='section-number'>01</span>" in html
    assert "run 2026-07-04" in html
    assert html.count("<section>") == 2


def test_frame_to_html_formats_floats_and_escapes() -> None:
    frame = pd.DataFrame({"sortino <s>": [1.23456]}, index=["ABC & co"])
    frame.index.name = "model"
    fragment = frame_to_html(frame)
    assert "1.235" in fragment
    assert "ABC &amp; co" in fragment
    assert "sortino &lt;s&gt;" in fragment


def test_notice_uses_coral_callout() -> None:
    fragment = notice("results are frozen", label="FROZEN")
    assert "class='notice'" in fragment
    assert "FROZEN" in fragment
