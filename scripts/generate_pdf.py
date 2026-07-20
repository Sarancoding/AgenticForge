#!/usr/bin/env python3
"""
NexusCore PDF Guide Generator — Converts GUIDE.md to a professional PDF.

Usage:
    python3 scripts/generate_pdf.py
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from fpdf import FPDF
except ImportError:
    os.system("pip install fpdf2 markdown > /dev/null 2>&1")
    from fpdf import FPDF


def latin1(text: str) -> str:
    """Replace/remove characters that can't be encoded in latin-1."""
    table = str.maketrans({
        "\u2014": "-", "\u2013": "-",
        "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"',
        "\u2026": "...", "\u2713": "v",
        "\u2192": "->", "\u2190": "<-",
        "\u25cf": "*",
        "\u20ac": "EUR", "\u2122": "TM",
        "\u2022": "*", "\u2027": "*",
    })
    result = text.translate(table)
    return result.encode("latin-1", "replace").decode("latin-1")


class NexusCorePDF(FPDF):
    """Professional PDF for the NexusCore Enterprise Guide."""

    def _w(self, text: str) -> str:
        return latin1(text)

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, self._w("NexusCore Enterprise -- Setup & Operations Guide"), align="L")
        self.cell(0, 8, "v0.2.0", align="R", new_x="LMARGIN", new_y="NEXT")
        self.line(10, 16, 200, 16)
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def title1(self, text: str):
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(30, 60, 120)
        self.ln(6)
        self.cell(0, 12, self._w(text), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(30, 60, 120)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)

    def title2(self, text: str):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(60, 90, 150)
        self.ln(4)
        self.cell(0, 10, self._w(text), new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def title3(self, text: str):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(80, 80, 80)
        self.ln(2)
        self.cell(0, 8, self._w(text), new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def para(self, text: str):
        if not text.strip():
            return
        self.set_font("Helvetica", "", 10)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 5.5, self._w(text))
        self.ln(2)

    def bullet(self, text: str):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(50, 50, 50)
        self.cell(5, 6, "")
        self.cell(0, 6, self._w(text), new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def table_row(self, cells: list[str], header: bool = False):
        style = "B" if header else ""
        self.set_font("Helvetica", style, 9)
        if header:
            self.set_fill_color(30, 60, 120)
            self.set_text_color(255, 255, 255)
        else:
            self.set_text_color(50, 50, 50)
        col_w = 180 / max(len(cells), 1)
        for cell in cells:
            self.cell(col_w, 7, self._w(str(cell)[:30]), border=1, fill=header)
        self.ln()

    def code(self, code: str):
        self.set_fill_color(240, 240, 245)
        self.set_font("Courier", "", 8)
        self.set_text_color(40, 40, 40)
        for line in code.strip().split("\n")[:20]:
            self.cell(0, 4.5, self._w("  " + line[:100]), new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def cover_page(self):
        self.add_page()
        self.ln(40)
        self.set_font("Helvetica", "B", 28)
        self.set_text_color(30, 60, 120)
        self.cell(0, 15, "NexusCore Enterprise", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)
        self.set_font("Helvetica", "", 16)
        self.set_text_color(100, 100, 100)
        self.cell(0, 12, "Complete Setup & Operations Guide", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(10)
        self.set_draw_color(30, 60, 120)
        self.set_line_width(0.5)
        self.line(60, self.get_y(), 150, self.get_y())
        self.ln(10)
        self.set_font("Helvetica", "I", 12)
        self.set_text_color(80, 80, 80)
        self.cell(0, 10, "Unified Agentic Orchestration for Global Business", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(20)
        self.set_font("Helvetica", "", 11)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, "Version 0.2.0  |  July 2026", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(20)
        self.set_font("Helvetica", "", 10)
        for f in [
            "10 Agent Archetypes -- ReAct, Debate, Crew, Workflow & more",
            "Enterprise Observability -- LangSmith & Arize Phoenix Tracing",
            "Cost-Aware Routing -- Up to 87% savings on LLM costs",
            "Canary Testing -- Safe rollouts with auto-rollback",
            "HITL Approval -- Human oversight for sensitive operations",
            "Rollback Management -- One-click config restore",
        ]:
            self.cell(0, 7, f"  v  {f}", new_x="LMARGIN", new_y="NEXT")
        self.ln(20)
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, "MIT License  |  (c) 2026 Sarancoding", align="C", new_x="LMARGIN", new_y="NEXT")

    def toc_page(self):
        self.add_page()
        self.title1("Table of Contents")
        for item in [
            "1. Executive Summary", "2. System Overview",
            "3. Prerequisites & Requirements", "4. Installation Guide",
            "5. Configuration", "6. Agent Archetypes Reference",
            "7. Observability & Monitoring", "8. Production Deployment",
            "9. Security & Compliance", "10. Operations Runbook",
            "11. Troubleshooting", "12. API Reference",
            "13. Benchmarks", "14. Quick Start in 5 Minutes",
        ]:
            self.set_font("Helvetica", "", 11)
            self.set_text_color(50, 50, 50)
            self.cell(0, 8, f"  {item}", new_x="LMARGIN", new_y="NEXT")

    def render_markdown(self, content: str):
        """Render markdown-like content from GUIDE.md."""
        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("---"):
                continue
            if line.startswith("## "):
                self.title2(line[3:])
            elif line.startswith("### "):
                self.title3(line[4:])
            elif line.startswith("# "):
                # Skip main title (already covered by cover page)
                pass
            elif line.startswith("|") and "---" not in line:
                cells = [c.strip() for c in line.split("|") if c.strip()]
                if cells:
                    self.table_row(cells)
            elif line.startswith("- ") or line.startswith("* "):
                self.bullet(line[2:])
            elif re.match(r"^\d+\.", line):
                self.bullet(line)
            elif line.startswith("```"):
                continue  # skip markers
            else:
                self.para(line)


def generate_pdf():
    """Generate the complete NexusCore Enterprise PDF guide."""
    pdf = NexusCorePDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)

    pdf.cover_page()
    pdf.toc_page()

    guide = os.path.join(os.path.dirname(__file__), "..", "GUIDE.md")
    with open(guide, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by ## sections
    sections = re.split(r"(?m)^## ", content)
    for section in sections:
        section = section.strip()
        if not section:
            continue
        pdf.add_page()
        lines = section.split("\n")
        # First line is the title
        title = lines[0].strip().lstrip("#").strip()
        if title and "NexusCore" not in title:
            pdf.title2(title)
        # Rest of content
        pdf.render_markdown("\n".join(lines[1:]))

    output_dir = os.path.join(os.path.dirname(__file__), "..", "dist")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "NexusCore_Enterprise_Guide.pdf")
    pdf.output(output_path)

    print(f"\nDone! PDF generated: {output_path}")
    print(f"  Pages: {pdf.page_no()}")
    print(f"  Size:  {os.path.getsize(output_path) / 1024:.0f} KB")
    return output_path


if __name__ == "__main__":
    generate_pdf()
