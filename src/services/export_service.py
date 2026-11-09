"""Multi-format research report export service supporting Markdown, JSON, CSV, and PDF."""
import csv
import io
import json
from typing import Any, Dict, List, Optional
from fpdf import FPDF
from fpdf.enums import XPos, YPos


def export_to_markdown(job_detail: Dict[str, Any]) -> str:
    """Format and export research report as publication-grade Markdown."""
    if job_detail.get("markdown"):
        return job_detail["markdown"]

    # Fallback compilation if raw markdown was empty
    rep = job_detail.get("report_json", {})
    tickers = ", ".join(job_detail.get("tickers", []))
    tab = job_detail.get("tab", "news").upper()
    lines = [
        f"# Stock Market Research Report — {tab} TAB",
        f"**Generated:** {job_detail.get('created_at', '')[:19]} UTC | **Tickers:** {tickers}",
        f"**Date Range:** {job_detail.get('start_at')} to {job_detail.get('end_at')}",
    ]
    if job_detail.get("horizon_days"):
        lines.append(f"**Forward Horizon:** {job_detail['horizon_days']} Days")

    lines.extend([
        "\n## Executive Summary",
        rep.get("executive_summary", "No executive summary available."),
        "\n---",
    ])

    citations = rep.get("all_citations", [])
    if citations:
        lines.append("\n## Verified Source Citations")
        lines.append("| Article ID | Publisher | Date | Verified Claim | Source Link |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for c in citations:
            art_id = c.get("article_id", "N/A")
            pub = c.get("publisher", "Unknown")
            dt = (c.get("publication_date") or "")[:10]
            claim = c.get("claim", "")[:60]
            url = c.get("source_url", "#")
            lines.append(f"| `{art_id}` | {pub} | {dt} | {claim}... | [Source]({url}) |")

    lines.extend([
        "\n## Methodology & Regulatory Disclaimer",
        "This research report is generated for informational and research purposes only using bounded agentic AI. "
        "It does not constitute investment advice, financial endorsement, price targets, or trade recommendations.",
    ])
    return "\n".join(lines)


def export_to_json(job_detail: Dict[str, Any]) -> str:
    """Export research report and metadata as structured JSON string."""
    export_payload = {
        "job_id": job_detail.get("id"),
        "user_id": job_detail.get("user_id"),
        "tab": job_detail.get("tab"),
        "tickers": job_detail.get("tickers"),
        "date_range": {
            "start": job_detail.get("start_at"),
            "end": job_detail.get("end_at"),
        },
        "forward_horizon_days": job_detail.get("horizon_days"),
        "status": job_detail.get("status"),
        "created_at": job_detail.get("created_at"),
        "completed_at": job_detail.get("completed_at"),
        "model_version": job_detail.get("model_version"),
        "report": job_detail.get("report_json", {}),
        "source_records": job_detail.get("sources", []),
        "disclaimer": "Informational research only. Not investment advice or price forecasts.",
    }
    return json.dumps(export_payload, indent=2)


def export_to_csv(job_detail: Dict[str, Any]) -> str:
    """Export findings, citations, and factor weights as a structured tabular CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)

    # 1. Header Information
    writer.writerow(["# STOCK MARKET NEWS RESEARCH AGENT - RESEARCH REPORT"])
    writer.writerow(["Job ID", job_detail.get("id")])
    writer.writerow(["Tab Type", job_detail.get("tab")])
    writer.writerow(["Tickers", ", ".join(job_detail.get("tickers", []))])
    writer.writerow(["Date Window", f"{job_detail.get('start_at')} to {job_detail.get('end_at')}"])
    if job_detail.get("horizon_days"):
        writer.writerow(["Forward Horizon Days", job_detail.get("horizon_days")])
    writer.writerow(["Status", job_detail.get("status")])
    writer.writerow(["Generated At", job_detail.get("created_at")])
    writer.writerow([])

    # 2. Main Tabular Records
    writer.writerow([
        "Record Type",
        "Ticker",
        "Category",
        "Date",
        "Publisher",
        "Claim / Headline / Summary",
        "Source URL",
        "Notes / Weights",
    ])

    rep = job_detail.get("report_json", {})

    # Executive summary
    if rep.get("executive_summary"):
        writer.writerow([
            "EXECUTIVE_SUMMARY",
            "ALL",
            "Synthesis",
            job_detail.get("created_at", "")[:10],
            "AI Agent",
            rep["executive_summary"],
            "",
            "",
        ])

    # Stock News Summaries
    for s in rep.get("stock_news_summaries", []):
        sym = s.get("ticker", "")
        for dev in s.get("key_developments", []):
            writer.writerow([
                "KEY_DEVELOPMENT",
                sym,
                "News Development",
                "",
                "Verified Publisher",
                dev,
                "",
                "",
            ])

    # Sentiment Outlooks, Catalysts, Risks
    for o in rep.get("stock_sentiment_outlooks", []):
        sym = o.get("ticker", "")
        writer.writerow([
            "SENTIMENT_OUTLOOK",
            sym,
            "News: " + o.get("current_news_sentiment", "").upper(),
            "",
            "Scenario Lens",
            f"Forward ({o.get('horizon_days')}D): {o.get('forward_scenario_outlook', '').upper()}",
            "",
            f"Evidence Strength: {o.get('evidence_strength', '').upper()}",
        ])
        for c in o.get("catalysts", []):
            writer.writerow(["CATALYST", sym, "Positive Catalyst", "", "Agent Extracted", c, "", ""])
        for r in o.get("risks", []):
            writer.writerow(["DOWNSIDE_RISK", sym, "Downside Headwind", "", "Agent Extracted", r, "", ""])
        for opp in o.get("opposing_evidence", []):
            writer.writerow(["OPPOSING_EVIDENCE", sym, "Counter-Narrative", "", "Agent Extracted", opp, "", ""])

    # Verified Citations
    for cit in rep.get("all_citations", []):
        writer.writerow([
            "CITATION",
            cit.get("ticker", "N/A"),
            "Verified Fact",
            (cit.get("publication_date") or "")[:10],
            cit.get("publisher", ""),
            cit.get("claim", ""),
            cit.get("source_url", ""),
            f"Article ID: {cit.get('article_id', '')}",
        ])

    # Source Records if citations were empty
    if not rep.get("all_citations") and job_detail.get("sources"):
        for src in job_detail["sources"]:
            writer.writerow([
                "SOURCE_RECORD",
                src.get("ticker", ""),
                "News Article",
                (src.get("published_at") or "")[:10],
                src.get("publisher", ""),
                src.get("headline", "[No headline provided]"),
                src.get("source_url", ""),
                f"Duplicate: {src.get('is_duplicate', False)}",
            ])

    writer.writerow([])
    writer.writerow([
        "DISCLAIMER",
        "ALL",
        "Compliance",
        "",
        "Stock Market Agent",
        "Informational report only. Does not constitute investment advice or guaranteed return.",
        "",
        "",
    ])

    return output.getvalue()


class ResearchPDF(FPDF):
    """Custom styled PDF for research reports with branded navy header and footer."""

    def header(self):
        self.set_fill_color(11, 25, 44)  # Deep Navy #0B192C
        self.rect(0, 0, 210, 20, "F")
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, "Stock Market News Research Agent", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(203, 213, 225)
        self.cell(0, 4, "Agentic AI Multi-Stock Intelligence & Sentiment Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}} · Confidential Research Report · Not Investment Advice", align="C")


def export_to_pdf(job_detail: Dict[str, Any]) -> bytes:
    """Generate a high-quality PDF report."""
    pdf = ResearchPDF(orientation="P", unit="mm", format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    rep = job_detail.get("report_json", {})
    tickers_str = ", ".join(job_detail.get("tickers", []))
    tab_str = job_detail.get("tab", "news").upper()

    # Meta Section
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 9, f"Financial Research Report: {tickers_str}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 116, 139)
    date_str = f"Date Window: {job_detail.get('start_at')} to {job_detail.get('end_at')} | Mode: {tab_str}"
    if job_detail.get("horizon_days"):
        date_str += f" | Forward Horizon: {job_detail['horizon_days']} Days"
    pdf.cell(0, 5, date_str, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 5, f"Generated At: {job_detail.get('created_at', '')[:19]} UTC | Job ID: {job_detail.get('id', '')[:8]}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    # Executive Summary Card
    pdf.set_fill_color(241, 245, 249)
    pdf.set_draw_color(203, 213, 225)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 62, 98)
    pdf.cell(0, 7, "Executive Summary", border="LTR", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(15, 23, 42)
    exec_text = rep.get("executive_summary", "Synthesis generated across retrieved financial news feeds.")
    # Clean non-latin-1 characters for standard Helvetica
    clean_exec = exec_text.encode("latin-1", "replace").decode("latin-1")
    pdf.multi_cell(0, 5, clean_exec, border="LBR", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(6)

    # Key Findings / Developments
    summaries = rep.get("stock_news_summaries", [])
    if summaries:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(11, 25, 44)
        pdf.cell(0, 7, "Key Corporate Developments", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(30, 41, 59)
        for s in summaries:
            sym = s.get("ticker", "")
            comp = s.get("company_name", "")
            pdf.set_font("Helvetica", "B", 9.5)
            pdf.cell(0, 5, f"{sym} ({comp})", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", "", 9)
            for dev in s.get("key_developments", []):
                clean_dev = dev.encode("latin-1", "replace").decode("latin-1")
                pdf.multi_cell(0, 4.5, f"   - {clean_dev}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(2)

    # Sentiment Scenarios
    outlooks = rep.get("stock_sentiment_outlooks", [])
    if outlooks:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(11, 25, 44)
        pdf.cell(0, 7, "Forward Scenario Outlook & Catalyst Analysis", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        for o in outlooks:
            sym = o.get("ticker", "")
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(15, 23, 42)
            hist_sent = o.get("current_news_sentiment", "").upper()
            fwd_out = o.get("forward_scenario_outlook", "").upper()
            strength = o.get("evidence_strength", "").upper()
            pdf.cell(0, 5, f"{sym} | News Sentiment: {hist_sent} | Forward Outlook: {fwd_out} | Evidence: {strength}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", "", 9)
            if o.get("catalysts"):
                pdf.set_text_color(22, 101, 52)
                for c in o["catalysts"][:3]:
                    clean_c = c.encode("latin-1", "replace").decode("latin-1")
                    pdf.multi_cell(0, 4.5, f"   + Catalyst: {clean_c}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            if o.get("risks"):
                pdf.set_text_color(153, 27, 27)
                for r in o["risks"][:3]:
                    clean_r = r.encode("latin-1", "replace").decode("latin-1")
                    pdf.multi_cell(0, 4.5, f"   - Risk: {clean_r}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(3)

    # Citations Table
    citations = rep.get("all_citations", [])
    if citations:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(11, 25, 44)
        pdf.cell(0, 7, "Verified Source Citations", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(226, 232, 240)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(28, 6, "Article ID", border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.cell(32, 6, "Publisher", border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.cell(22, 6, "Date", border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.cell(108, 6, "Verified Fact Claim", border=1, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_font("Helvetica", "", 7.5)
        for cit in citations[:10]:  # Up to 10 prominent citations
            art_id = str(cit.get("article_id", "N/A"))[:15]
            pub = str(cit.get("publisher", "Unknown"))[:18]
            dt = str(cit.get("publication_date", ""))[:10]
            claim = str(cit.get("claim", ""))[:75].encode("latin-1", "replace").decode("latin-1")
            pdf.cell(28, 5, art_id, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.cell(32, 5, pub, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.cell(22, 5, dt, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.cell(108, 5, claim, border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(5)

    # Disclaimer Block
    pdf.set_fill_color(254, 242, 242)
    pdf.set_draw_color(252, 165, 165)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(153, 27, 27)
    pdf.cell(0, 5, "REGULATORY & METHODOLOGY NOTICE", border="LTR", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.multi_cell(
        0,
        4,
        "This research report is generated for informational purposes only using bounded agentic AI. "
        "It does not constitute investment advice, trade recommendations, or price target guarantees. "
        "All citations were grounded against public news feeds with point-in-time constraints.",
        border="LBR",
        fill=True,
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )

    pdf_bytes = pdf.output()
    return bytes(pdf_bytes)
