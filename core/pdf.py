"""
PDF report generation for analysis verdicts using fpdf2.
"""

import asyncio
from datetime import datetime

from fpdf import FPDF, XPos, YPos

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


class _ReportPDF(FPDF):
    def __init__(self, claim: str):
        super().__init__()
        self._claim = claim
        self.set_auto_page_break(auto=True, margin=20)
        self.add_page()

    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(100, 116, 139)
        self.cell(0, 8, "FakeNews Tribunal — Fact-Check Report", align="L",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(200, 200, 200)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()} — Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
                  align="C")


def _section(pdf: FPDF, title: str) -> None:
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 8, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_draw_color(180, 180, 180)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(2)


def _body(pdf: FPDF, text: str) -> None:
    pdf.set_font("Helvetica", "", 10)
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
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(r, g, b)
    pdf.cell(0, 12, f"Verdict: {label}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 7, f"Confidence: {confidence:.0%}  |  Rounds: {len(rounds)}  |  Provider: {llm_provider} / {llm_model}",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 7, f"Analysis ID: {analysis_id}  |  Date: {created_at[:10]}",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    # --- Claim ---
    _section(pdf, "Claim")
    pdf.set_font("Helvetica", "I", 11)
    pdf.set_text_color(30, 30, 30)
    pdf.multi_cell(0, 7, f'"{claim}"')

    # --- Summary ---
    _section(pdf, "Summary")
    _body(pdf, summary)

    # --- Reasoning ---
    _section(pdf, "Reasoning")
    # Strip markdown headers for plain text rendering
    plain_reasoning = "\n".join(
        line.lstrip("# ") if line.startswith("#") else line
        for line in reasoning.splitlines()
    )
    _body(pdf, plain_reasoning)

    # --- Debate rounds ---
    for rnd in rounds:
        n = rnd.get("round_number", "?")
        _section(pdf, f"Round {n} — Researcher")
        _body(pdf, rnd.get("researcher_report", ""))

        r_sources = rnd.get("researcher_sources", [])
        if r_sources:
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(0, 6, "Sources:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            _render_sources(pdf, r_sources)

        _section(pdf, f"Round {n} — Devil's Advocate")
        _body(pdf, rnd.get("advocate_challenge", ""))

        a_sources = rnd.get("advocate_counter_sources", [])
        if a_sources:
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(0, 6, "Sources:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            _render_sources(pdf, a_sources)

        if rnd.get("judge_continuation_reason"):
            pdf.ln(2)
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(100, 116, 139)
            pdf.multi_cell(0, 5, f"Judge → Continue: {rnd['judge_continuation_reason']}")

    return bytes(pdf.output())


def _render_sources(pdf: FPDF, sources: list[dict]) -> None:
    for s in sources[:8]:  # cap at 8 per section to save space
        tier = s.get("credibility_tier", "unknown")
        tr, tg, tb = _TIER_COLORS.get(str(tier), (100, 116, 139))
        domain = s.get("domain", "")
        title = s.get("title", s.get("url", ""))[:80]

        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(tr, tg, tb)
        pdf.cell(22, 5, f"[{tier}]")
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(0, 5, f"{title} — {domain}")


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
