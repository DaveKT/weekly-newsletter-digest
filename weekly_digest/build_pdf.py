"""
build_pdf.py — weekly newsletter digest renderer.

Matches the Weekly Digest design (typography and palette extracted
from the source PDF).

Palette:
  INK       #1a1a1a   body text, headlines
  SLATE     #6b6b6b   bylines, chrome text
  RULE      #d8d8d8   header/footer separator rules
  TEAL      #2da1ba   kicker, hyperlinks, issue number
  NAVY_TEAL #0e2a36   cover title (deep)
  GOLD      #e8b34b   cover accent
  CREAM     #f4ede2   cover background panel

Typography: Helvetica family throughout.
"""
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer,
    PageBreak, NextPageTemplate, HRFlowable
)

# ---------- Palette ----------
INK = HexColor("#1a1a1a")
SLATE = HexColor("#6b6b6b")
RULE = HexColor("#d8d8d8")
TEAL = HexColor("#2da1ba")
NAVY_TEAL = HexColor("#0e2a36")
GOLD = HexColor("#e8b34b")
CREAM = HexColor("#f4ede2")

# ---------- Page geometry ----------
PAGE_W, PAGE_H = LETTER
MARGIN_L = 0.75 * inch
MARGIN_R = 0.75 * inch
MARGIN_T = 0.95 * inch
MARGIN_B = 0.85 * inch


LIGHT_GRAY_CCC = HexColor("#cccccc")


def make_styles():
    return {
        # ----- Cover (text sits on NAVY_TEAL background) -----
        "cover_title": ParagraphStyle(
            "cover_title", fontName="Helvetica-Bold", fontSize=44,
            textColor=CREAM, leading=48, alignment=TA_LEFT, spaceAfter=4),
        "cover_title_bot": ParagraphStyle(
            "cover_title_bot", fontName="Helvetica-Bold", fontSize=44,
            textColor=CREAM, leading=48, alignment=TA_LEFT, spaceAfter=12),
        "cover_tag": ParagraphStyle(
            "cover_tag", fontName="Helvetica-Oblique", fontSize=14,
            textColor=CREAM, leading=20, alignment=TA_LEFT, spaceAfter=28),
        "cover_issue_label": ParagraphStyle(
            "cover_issue_label", fontName="Helvetica-Bold", fontSize=10,
            textColor=CREAM, leading=12, alignment=TA_LEFT, spaceAfter=2),
        "cover_issue_num": ParagraphStyle(
            "cover_issue_num", fontName="Helvetica-Bold", fontSize=72,
            textColor=GOLD, leading=76, alignment=TA_LEFT, spaceAfter=18),
        "cover_meta": ParagraphStyle(
            "cover_meta", fontName="Helvetica", fontSize=10,
            textColor=CREAM, leading=15, alignment=TA_LEFT, spaceAfter=2),
        "cover_toc_h": ParagraphStyle(
            "cover_toc_h", fontName="Helvetica-Bold", fontSize=12,
            textColor=GOLD, leading=14, alignment=TA_LEFT,
            spaceBefore=0, spaceAfter=14),
        # TOC items: title cream-bold inline, blurb in light gray (style color)
        "cover_toc_item": ParagraphStyle(
            "cover_toc_item", fontName="Helvetica", fontSize=10.5,
            textColor=LIGHT_GRAY_CCC, leading=14.5, alignment=TA_LEFT,
            spaceAfter=8),
        # ----- Inner sections -----
        "kicker": ParagraphStyle(
            "kicker", fontName="Helvetica-Bold", fontSize=9,
            textColor=TEAL, leading=11, alignment=TA_LEFT, spaceAfter=4),
        "headline": ParagraphStyle(
            "headline", fontName="Helvetica-Bold", fontSize=22,
            textColor=INK, leading=26, alignment=TA_LEFT, spaceAfter=6),
        "byline": ParagraphStyle(
            "byline", fontName="Helvetica-Oblique", fontSize=10,
            textColor=SLATE, leading=13, alignment=TA_LEFT, spaceAfter=14),
        "deck": ParagraphStyle(
            "deck", fontName="Helvetica", fontSize=10.5,
            textColor=INK, leading=15, alignment=TA_JUSTIFY, spaceAfter=12),
        "subhead": ParagraphStyle(
            "subhead", fontName="Helvetica-Bold", fontSize=14,
            textColor=INK, leading=17, alignment=TA_LEFT,
            spaceBefore=10, spaceAfter=6),
        "body": ParagraphStyle(
            "body", fontName="Helvetica", fontSize=10.5,
            textColor=INK, leading=15, alignment=TA_JUSTIFY, spaceAfter=8),
        "quote": ParagraphStyle(
            "quote", fontName="Helvetica-Oblique", fontSize=10,
            textColor=SLATE, leading=13.5, leftIndent=18,
            rightIndent=18, spaceAfter=10),
        # ----- Additional items / briefer -----
        "additional_h": ParagraphStyle(
            "additional_h", fontName="Helvetica-Bold", fontSize=9,
            textColor=TEAL, leading=11, alignment=TA_LEFT, spaceAfter=4),
        "additional_title": ParagraphStyle(
            "additional_title", fontName="Helvetica-Bold", fontSize=22,
            textColor=INK, leading=26, alignment=TA_LEFT, spaceAfter=12),
        "briefer_subh": ParagraphStyle(
            "briefer_subh", fontName="Helvetica-Bold", fontSize=12,
            textColor=INK, leading=15, alignment=TA_LEFT,
            spaceBefore=8, spaceAfter=3),
        "briefer_body": ParagraphStyle(
            "briefer_body", fontName="Helvetica", fontSize=10.5,
            textColor=INK, leading=15, alignment=TA_JUSTIFY, spaceAfter=6),
        # ----- Bibliography -----
        "biblio_title": ParagraphStyle(
            "biblio_title", fontName="Helvetica-Bold", fontSize=22,
            textColor=INK, leading=26, alignment=TA_LEFT, spaceAfter=8),
        "biblio_intro": ParagraphStyle(
            "biblio_intro", fontName="Helvetica-Oblique", fontSize=10,
            textColor=SLATE, leading=14, alignment=TA_LEFT, spaceAfter=12),
        "biblio_source_h": ParagraphStyle(
            "biblio_source_h", fontName="Helvetica-Bold", fontSize=11,
            textColor=NAVY_TEAL, leading=14, alignment=TA_LEFT,
            spaceBefore=12, spaceAfter=6),
        "biblio_item": ParagraphStyle(
            "biblio_item", fontName="Helvetica", fontSize=10,
            textColor=INK, leading=13.5, alignment=TA_LEFT, spaceAfter=3),
        "biblio_url": ParagraphStyle(
            "biblio_url", fontName="Helvetica", fontSize=9,
            textColor=TEAL, leading=12, alignment=TA_LEFT,
            leftIndent=12, spaceAfter=8),
        "closing": ParagraphStyle(
            "closing", fontName="Helvetica-Oblique", fontSize=9.5,
            textColor=SLATE, leading=13, alignment=TA_LEFT,
            spaceBefore=16, spaceAfter=2),
    }


def _draw_inner_chrome(canv, content, coverage):
    canv.saveState()
    issue_num = content["cover"]["issue_number"]
    canv.setFont("Helvetica-Bold", 8)
    canv.setFillColor(SLATE)
    canv.drawString(MARGIN_L, PAGE_H - 0.55 * inch,
                    f"THE WEEKLY DIGEST  \u00b7  ISSUE {issue_num}")
    canv.setFont("Helvetica", 8)
    canv.drawRightString(PAGE_W - MARGIN_R, PAGE_H - 0.55 * inch, coverage)
    canv.setStrokeColor(RULE)
    canv.setLineWidth(0.5)
    canv.line(MARGIN_L, PAGE_H - 0.65 * inch,
              PAGE_W - MARGIN_R, PAGE_H - 0.65 * inch)
    canv.line(MARGIN_L, 0.65 * inch, PAGE_W - MARGIN_R, 0.65 * inch)
    canv.setFont("Helvetica", 8)
    canv.setFillColor(SLATE)
    canv.drawString(MARGIN_L, 0.5 * inch,
                    "Personal compilation \u2014 not for redistribution")
    canv.drawRightString(PAGE_W - MARGIN_R, 0.5 * inch,
                         f"Page {canv.getPageNumber()}")
    canv.restoreState()


def _draw_cover_chrome(canv, content):
    """Paint the navy backdrop, teal bands, gold side rule, gold dot,
    cream header text, and the upper cover block (title, tagline, issue
    number, metadata). The TOC is rendered separately by the Frame so it
    can anchor in the lower portion of the page for magazine balance."""
    cover = content["cover"]
    canv.saveState()
    # 1. Full-bleed navy background
    canv.setFillColor(NAVY_TEAL)
    canv.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    # 2. Top teal band (y=774, h=18) and bottom teal band (y=0, h=14)
    canv.setFillColor(TEAL)
    canv.rect(0, 774, PAGE_W, 18, stroke=0, fill=1)
    canv.rect(0, 0, PAGE_W, 14, stroke=0, fill=1)
    # 3. Gold vertical side rule
    canv.setStrokeColor(GOLD)
    canv.setLineWidth(2)
    canv.line(43.2, 36, 43.2, 748.8)
    # 4. Gold dot on the top band
    canv.setFillColor(GOLD)
    canv.circle(558, 783, 3, stroke=0, fill=1)
    # 5. Header text on the top band (cream)
    canv.setFillColor(CREAM)
    canv.setFont("Helvetica-Bold", 9)
    canv.drawString(54, 781,
                    "THE WEEKLY DIGEST")

    # --- Upper cover block: anchored to top, drawn directly ---
    x = 60  # left edge of text column (sits right of the gold rule)

    # "The Weekly" — baseline near the top
    canv.setFillColor(CREAM)
    canv.setFont("Helvetica-Bold", 44)
    canv.drawString(x, 700, "The Weekly")
    canv.drawString(x, 654, "Digest")

    # Tagline
    canv.setFont("Helvetica-Oblique", 14)
    canv.drawString(x, 620, cover["subtitle"])

    # ISSUE label
    canv.setFont("Helvetica-Bold", 10)
    canv.drawString(x, 580, "ISSUE")

    # Issue number (gold, very large)
    canv.setFillColor(GOLD)
    canv.setFont("Helvetica-Bold", 72)
    canv.drawString(x, 510, cover["issue_number"])

    # Metadata block (cream)
    canv.setFillColor(CREAM)
    canv.setFont("Helvetica", 10)
    canv.drawString(x, 478, "Coverage period:")
    canv.setFont("Helvetica-Bold", 10)
    canv.drawString(x + 85, 478,
                    f"{cover['coverage_start']} \u2013 "
                    f"{cover['coverage_end']}")
    canv.setFont("Helvetica", 10)
    canv.drawString(x, 463, f"Compiled: {cover['compiled_date']}")
    canv.drawString(x, 448, f"Compiled for: {cover['compiled_for']}")

    canv.restoreState()


def _inner_chrome_factory(content):
    coverage = (f"{content['cover']['coverage_start']} \u2013 "
                f"{content['cover']['coverage_end']}")
    return lambda c, d: _draw_inner_chrome(c, content, coverage)


def _cover_chrome_factory(content):
    return lambda c, d: _draw_cover_chrome(c, content)


def link(url, label):
    return f'<link href="{url}" color="#2da1ba"><u>{label}</u></link>'


# ---------- Cover flowables (TOC only — upper block is drawn on canvas) ----------
def build_cover_flowables(content, styles):
    flow = [Paragraph("IN THIS ISSUE", styles["cover_toc_h"])]
    for item in content["toc"]:
        title = item["title"].rstrip(".")
        blurb = item["blurb"].rstrip(".")
        # Title in cream-bold (overriding the gray style color); blurb takes
        # the paragraph's default light-gray color.
        flow.append(Paragraph(
            f'<font color="#f4ede2"><b>{title}.</b></font> {blurb}.',
            styles["cover_toc_item"]))
    return flow


def build_section_flowables(section, styles):
    flow = [Paragraph(section["kicker"].upper(), styles["kicker"]),
            Paragraph(section["headline"], styles["headline"]),
            Paragraph(section["byline"], styles["byline"]),
            Paragraph(section["deck"], styles["deck"])]
    for sub in section["subsections"]:
        flow.append(Paragraph(sub["subhead"], styles["subhead"]))
        for para in sub["paragraphs"]:
            flow.append(Paragraph(para, styles["body"]))
        if sub.get("quote"):
            q = sub["quote"]
            flow.append(Paragraph(
                f'&ldquo;{q["text"]}&rdquo; &mdash; <i>{q["attribution"]}</i>',
                styles["quote"]))
    return flow


def build_additional_flowables(content, styles):
    notes = content.get("briefer_notes") or []
    if not notes:
        return []
    flow = [Paragraph("ADDITIONAL ITEMS THIS WEEK", styles["additional_h"]),
            Paragraph("Briefer notes", styles["additional_title"])]
    for note in notes:
        flow.append(Paragraph(note["headline"], styles["briefer_subh"]))
        flow.append(Paragraph(note["body"], styles["briefer_body"]))
    return flow


def build_biblio_flowables(content, styles):
    flow = [Paragraph("Bibliography &amp; sources", styles["biblio_title"]),
            Paragraph(
                "All clickable links below resolve to the original web "
                "versions of the cited stories. Where a newsletter was "
                "video-led with minimal text, only the source URL is given.",
                styles["biblio_intro"]),
            HRFlowable(width="100%", thickness=0.5,
                       color=RULE, spaceAfter=10)]
    for group in content["bibliography"]:
        flow.append(Paragraph(group["heading"], styles["biblio_source_h"]))
        for entry in group["entries"]:
            flow.append(Paragraph(entry["citation"], styles["biblio_item"]))
            flow.append(Paragraph(link(entry["url"], entry["url"]),
                                  styles["biblio_url"]))
    flow.append(Paragraph(content["closing_line"], styles["closing"]))
    return flow


def build_pdf(content, out_path):
    styles = make_styles()
    doc = BaseDocTemplate(
        out_path, pagesize=LETTER,
        leftMargin=MARGIN_L, rightMargin=MARGIN_R,
        topMargin=MARGIN_T, bottomMargin=MARGIN_B,
        title=f"The Weekly Digest \u2014 Issue {content['cover']['issue_number']}",
        author="The Weekly Digest",
    )
    # Cover frame: anchored to the LOWER portion of the page so the TOC
    # sits below the metadata block (which is drawn on the canvas at the
    # top). Top of frame near y=350; bottom just above the teal band.
    cover_frame = Frame(60, 30, PAGE_W - 60 - 36, 320,
                        leftPadding=0, rightPadding=0,
                        topPadding=0, bottomPadding=0,
                        id="cover_frame")
    inner_frame = Frame(MARGIN_L, MARGIN_B,
                        PAGE_W - MARGIN_L - MARGIN_R,
                        PAGE_H - MARGIN_T - MARGIN_B,
                        id="main_frame")
    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[cover_frame],
                     onPage=_cover_chrome_factory(content)),
        PageTemplate(id="inner", frames=[inner_frame],
                     onPage=_inner_chrome_factory(content)),
    ])
    story = build_cover_flowables(content, styles)
    story.append(NextPageTemplate("inner"))
    story.append(PageBreak())
    for i, section in enumerate(content["sections"]):
        if i > 0:
            story.append(PageBreak())
        story.extend(build_section_flowables(section, styles))
    additional = build_additional_flowables(content, styles)
    if additional:
        story.append(PageBreak())
        story.extend(additional)
    story.append(PageBreak())
    story.extend(build_biblio_flowables(content, styles))
    doc.build(story)
    return out_path
