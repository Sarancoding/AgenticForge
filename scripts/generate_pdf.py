#!/usr/bin/env python3
"""
NexusCore PDF Guide Generator — Converts GUIDE.md to a professional PDF.

Usage:
    python scripts/generate_pdf.py

Requires: pip install fpdf2 markdown
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from fpdf import FPDF
except ImportError:
    print("Installing fpdf2...")
    os.system("pip install fpdf2 markdown")
    from fpdf import FPDF


class NexusCorePDF(FPDF):
    """Professional PDF generator for the NexusCore Enterprise Guide."""

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "NexusCore Enterprise — Setup & Operations Guide", align="L")
        self.cell(0, 8, "v0.2.0", align="R", new_x="LMARGIN", new_y="NEXT")
        self.line(10, 16, 200, 16)
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def chapter_title(self, title: str, level: int = 1):
        if level == 1:
            self.set_font("Helvetica", "B", 18)
            self.set_text_color(30, 60, 120)
            self.ln(6)
            self.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(30, 60, 120)
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(6)
        elif level == 2:
            self.set_font("Helvetica", "B", 14)
            self.set_text_color(60, 90, 150)
            self.ln(4)
            self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
            self.ln(3)
        else:
            self.set_font("Helvetica", "B", 11)
            self.set_text_color(80, 80, 80)
            self.ln(2)
            self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
            self.ln(2)

    def body_text(self, text: str):
        self.set_font("Courier", "", 9)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 5, text)
        self.ln(2)

    def code_block(self, code: str):
        self.set_fill_color(240, 240, 245)
        self.set_font("Courier", "", 8)
        self.set_text_color(40, 40, 40)
        lines = code.strip().split("\n")
        for line in lines[:30]:  # Limit to 30 lines
            self.cell(0, 4.5, "  " + line[:100], new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def table_row(self, cells: list[str], bold: bool = False, header: bool = False):
        style = "B" if bold or header else ""
        self.set_font("Helvetica", style, 9)
        if header:
            self.set_fill_color(30, 60, 120)
            self.set_text_color(255, 255, 255)
        else:
            self.set_text_color(50, 50, 50)

        # Calculate column width
        col_width = 180 / max(len(cells), 1)
        for cell in cells:
            self.cell(col_width, 7, str(cell)[:30], border=1, fill=header)
        self.ln()

    def add_cover_page(self):
        """Generate a professional cover page."""
        self.add_page()
        self.ln(40)

        # Title
        self.set_font("Helvetica", "B", 28)
        self.set_text_color(30, 60, 120)
        self.cell(0, 15, "NexusCore Enterprise", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

        # Subtitle
        self.set_font("Helvetica", "", 16)
        self.set_text_color(100, 100, 100)
        self.cell(0, 12, "Complete Setup & Operations Guide", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(10)

        # Divider
        self.set_draw_color(30, 60, 120)
        self.set_line_width(0.5)
        self.line(60, self.get_y(), 150, self.get_y())
        self.ln(10)

        # Tagline
        self.set_font("Helvetica", "I", 12)
        self.set_text_color(80, 80, 80)
        self.cell(0, 10, "Unified Agentic Orchestration for Global Business", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(20)

        # Version & Date
        self.set_font("Helvetica", "", 11)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, "Version 0.2.0  |  July 2026", align="C", new_x="LMARGIN", new_y="NEXT")

        # Features summary
        self.ln(20)
        self.set_font("Helvetica", "", 10)
        features = [
            "10 Agent Archetypes — ReAct, Debate, Crew, Workflow & more",
            "Enterprise Observability — LangSmith & Arize Phoenix Tracing",
            "Cost-Aware Routing — Up to 87% savings on LLM costs",
            "Canary Testing — Safe rollouts with auto-rollback",
            "HITL Approval — Human oversight for sensitive operations",
            "Rollback Management — One-click config restore",
        ]
        for f in features:
            self.cell(0, 7, f"  \u2713  {f}", new_x="LMARGIN", new_y="NEXT")

        self.ln(20)
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, "MIT License  |  \u00a9 2026 Sarancoding", align="C", new_x="LMARGIN", new_y="NEXT")

    def add_toc(self):
        """Add table of contents."""
        self.add_page()
        self.chapter_title("Table of Contents", 1)
        toc = [
            "1. Executive Summary",
            "2. System Overview",
            "3. Prerequisites & Requirements",
            "4. Installation Guide",
            "5. Configuration",
            "6. Agent Archetypes Reference",
            "7. Observability & Monitoring",
            "8. Production Deployment",
            "9. Security & Compliance",
            "10. Operations Runbook",
            "11. Troubleshooting",
            "12. API Reference",
            "13. Benchmarks",
            "14. Quick Start in 5 Minutes",
        ]
        for i, item in enumerate(toc, 1):
            self.set_font("Helvetica", "", 11)
            self.set_text_color(50, 50, 50)
            self.cell(0, 8, f"  {item}", new_x="LMARGIN", new_y="NEXT")

    def add_section(self, title: str, content: str):
        """Add a formatted section from markdown-like content."""
        lines = content.strip().split("\n")
        for line in lines:
            line = line.strip()

            # Headers
            if line.startswith("### "):
                self.chapter_title(line[4:], 3)
            elif line.startswith("## "):
                self.chapter_title(line[3:], 2)
            elif line.startswith("# "):
                self.chapter_title(line[2:], 1)

            # Code blocks
            elif line.startswith("```"):
                continue

            # Table rows
            elif "|" in line and line.startswith("|"):
                cells = [c.strip() for c in line.split("|") if c.strip()]
                if cells:
                    is_header = "---" in line
                    if not is_header:
                        self.table_row(cells)

            # List items
            elif line.startswith("- ") or line.startswith("* "):
                self.set_font("Helvetica", "", 10)
                self.set_text_color(50, 50, 50)
                self.cell(5, 6, "")
                self.cell(0, 6, line[2:], new_x="LMARGIN", new_y="NEXT")

            # Numbered items
            elif re.match(r"^\d+\.", line):
                self.set_font("Helvetica", "", 10)
                self.set_text_color(50, 50, 50)
                self.cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")

            # Regular text (non-empty)
            elif line:
                self.body_text(line)


def generate_pdf():
    """Generate the complete NexusCore PDF guide."""
    pdf = NexusCorePDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)

    # Cover page
    pdf.add_cover_page()

    # Table of Contents
    pdf.add_toc()

    # Read GUIDE.md content
    guide_path = os.path.join(os.path.dirname(__file__), "..", "GUIDE.md")
    with open(guide_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by sections (## headers)
    sections = re.split(r"(?=^## )", content, flags=re.MULTILINE)

    for section in sections:
        section = section.strip()
        if not section or section.startswith("---"):
            continue

        # Extract level 1 title
        title_match = re.match(r"^# (.+)", section)
        if title_match:
            title = title_match.group(1)
            # Skip the main title (already covered)
            if "NexusCore" in title and "Setup" in title:
                continue

        # Find if this section has a subtitle
        lines = section.split("\n")
        pdf.add_page()
        for line in lines:
            line = line.strip()
            if line.startswith("## "):
                pdf.chapter_title(line[3:], 2)
            elif line.startswith("### "):
                pdf.chapter_title(line[4:], 3)
            elif line.startswith("# "):
                pdf.chapter_title(line[2:], 1)
            elif line.startswith("|") and "|" in line:
                cells = [c.strip() for c in line.split("|") if c.strip()]
                if cells and "---" not in line:
                    pdf.table_row(cells)
            elif line.startswith("- ") or line.startswith("* "):
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(50, 50, 50)
                pdf.cell(5, 6, "")
                pdf.cell(0, 6, line[2:], new_x="LMARGIN", new_y="NEXT")
                pdf.ln(1)
            elif line.startswith("```"):
                pass  # Skip code block markers
            elif line:
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(50, 50, 50)
                pdf.multi_cell(0, 5.5, line)
                pdf.ln(1)

    # Output
    output_dir = os.path.join(os.path.dirname(__file__), "..", "dist")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "NexusCore_Enterprise_Guide.pdf")

    pdf.output(output_path)
    print(f"\n✅ PDF generated: {output_path}")
    print(f"   Pages: {pdf.page_no()}")
    print(f"   File size: {os.path.getsize(output_path) / 1024:.0f} KB")

    return output_path


if __name__ == "__main__":
    print("╔══════════════════════════════════════════════╗")
    print("║   NexusCore Enterprise PDF Guide Generator   ║")
    print("╚══════════════════════════════════════════════╝")
    generate_pdf()
