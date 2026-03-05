"""
PDF report generation for analysis verdicts using fpdf2 with Unicode TTF fonts.
"""

import asyncio
from datetime import datetime, timezone

from fpdf import FPDF, XPos, YPos

_FONT_DIR = r"C:\Windows\Fonts"

_LABEL_COLORS: dict[str, tuple[int, int, int]] = {
    "TRUE":           (22,  163, 74),   # green-600
    "FALSE":          (220, 38,  38),   # red-600
    "MISLEADING":     (217, 119, 6),    # amber-600
    "PARTIALLY_TRUE": (234, 88,  12),   # orange-600
    "UNVERIFIABLE":   (100, 116, 139),  # slate-500
}

_TIER_COLORS: dict[str, tuple[int, int, int]] = {
    "high":    (22,  163, 74),
    "medium":  (59,  130, 246),
    "low":     (220, 38,  38),
    "unknown": (100, 116, 139),
}


def _add_fonts(pdf: FPDF) -> None:
    pdf.add_font("Arial", style="",  fname=f"{_FONT_DIR}\\arial.ttf")
    pdf.add_font("Arial", style="B", fname=f"{_FONT_DIR}\\arialbd.ttf")
    pdf.add_font("Arial", style="I", fname=f"{_FONT_DIR}\\ariali.ttf")
    pdf.add_font("Arial", style="BI", fname=f"{_FONT_DIR}\\arialbi.ttf")


class _ReportPDF(FPDF):
    def __init__(self, claim: str):
        super().__init__()
        self._claim = claim
        _add_fonts(self)
        self.set_auto_page_break(auto=True, margin=20)
        self.add_page()

    def header(self):
        self.set_font("Arial", "B", 10)
        self.set_text_color(100, 116, 139)
        self.cell(0, 8, "FakeNews Tribunal \u2014 Fact-Check Report", align="L",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(200, 200, 200)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10,
                  f"Page {self.page_no()} \u2014 Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
                  align="C")


def _section(pdf: FPDF, title: str) -> None:
    pdf.ln(4)
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 8, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_draw_color(180, 180, 180)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(2)


def _body(pdf: FPDF, text: str) -> None:
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(50, 50, 50)
    pdf.multi_cell(0, 6, text)


def generate_verdict_pdf(
    claim: str,
    verdict: dict,
    rounds: list[dict],
    analysis_id: str,
    created_at: str,
    llm_provider: str,
    llm_model: str,
) -> bytes:
    label = verdict.get("label", "UNVERIFIABLE")
    confidence = verdict.get("confidence", 0.0)
    summary = verdict.get("summary", "")
    reasoning = verdict.get("reasoning", "")

    pdf = _ReportPDF(claim)

    # --- Title block ---
    r, g, b = _LABEL_COLORS.get(label, (100, 116, 139))
    pdf.set_font("Arial", "B", 20)
    pdf.set_text_color(r, g, b)
    pdf.cell(0, 12, f"Verdict: {label}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 7,
             f"Confidence: {confidence:.0%}  |  Rounds: {len(rounds)}  |  Provider: {llm_provider} / {llm_model}",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 7, f"Analysis ID: {analysis_id}  |  Date: {created_at[:10]}",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    # --- Claim ---
    _section(pdf, "Claim")
    pdf.set_font("Arial", "I", 11)
    pdf.set_text_color(30, 30, 30)
    pdf.multi_cell(0, 7, f'\u201c{claim}\u201d')

    # --- Summary ---
    _section(pdf, "Summary")
    _body(pdf, summary)

    # --- Reasoning ---
    _section(pdf, "Reasoning")
    plain_reasoning = "\n".join(
        line.lstrip("# ") if line.startswith("#") else line
        for line in reasoning.splitlines()
    )
    _body(pdf, plain_reasoning)

    # --- Debate rounds ---
    for rnd in rounds:
        n = rnd.get("round_number", "?")
        _section(pdf, f"Round {n} \u2014 Researcher")
        _body(pdf, rnd.get("researcher_report", ""))

        r_sources = rnd.get("researcher_sources", [])
        if r_sources:
            pdf.ln(2)
            pdf.set_font("Arial", "B", 9)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(0, 6, "Sources:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            _render_sources(pdf, r_sources)

        _section(pdf, f"Round {n} \u2014 Devil\u2019s Advocate")
        _body(pdf, rnd.get("advocate_challenge", ""))

        a_sources = rnd.get("advocate_counter_sources", [])
        if a_sources:
            pdf.ln(2)
            pdf.set_font("Arial", "B", 9)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(0, 6, "Sources:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            _render_sources(pdf, a_sources)

        if rnd.get("judge_continuation_reason"):
            pdf.ln(2)
            pdf.set_font("Arial", "I", 9)
            pdf.set_text_color(100, 116, 139)
            pdf.multi_cell(0, 5, f"Judge \u2192 Continue: {rnd['judge_continuation_reason']}")

    return bytes(pdf.output())


def _render_sources(pdf: FPDF, sources: list[dict]) -> None:
    for s in sources[:8]:  # cap at 8 per section to save space
        tier = s.get("credibility_tier", "unknown")
        tr, tg, tb = _TIER_COLORS.get(str(tier), (100, 116, 139))
        domain = s.get("domain", "")
        title = s.get("title", s.get("url", ""))[:80]

        pdf.set_font("Arial", "", 8)
        pdf.set_text_color(tr, tg, tb)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 5, f"[{tier.upper()}] {title} \u2014 {domain}",
                       new_x=XPos.LMARGIN, new_y=YPos.NEXT)


async def generate_verdict_pdf_async(
    claim: str,
    verdict: dict,
    rounds: list[dict],
    analysis_id: str,
    created_at: str,
    llm_provider: str,
    llm_model: str,
) -> bytes:
    return await asyncio.to_thread(
        generate_verdict_pdf,
        claim, verdict, rounds, analysis_id, created_at, llm_provider, llm_model,
    )
