#!/usr/bin/env python3
"""Build the Houston Crash Playbook PDF in English, Spanish and Vietnamese.

Usage:  python3 scripts/build_crash_playbook.py
Output: assets/houston-crash-playbook.pdf      (English)
        assets/houston-crash-playbook-es.pdf   (Español)
        assets/houston-crash-playbook-vi.pdf   (Tiếng Việt)

Fonts are Liberation Serif / Sans (metric-compatible with Times / Helvetica)
so Spanish and Vietnamese diacritics render correctly.
"""
import os
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from playbook_content import CONTENT

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = "/usr/share/fonts/truetype/liberation"
for name, file in [
    ("Serif", "LiberationSerif-Regular.ttf"), ("Serif-Bold", "LiberationSerif-Bold.ttf"),
    ("Serif-Italic", "LiberationSerif-Italic.ttf"), ("Sans", "LiberationSans-Regular.ttf"),
    ("Sans-Bold", "LiberationSans-Bold.ttf"), ("Sans-Italic", "LiberationSans-Italic.ttf"),
]:
    pdfmetrics.registerFont(TTFont(name, os.path.join(FONT_DIR, file)))
pdfmetrics.registerFontFamily("Sans", normal="Sans", bold="Sans-Bold", italic="Sans-Italic")
pdfmetrics.registerFontFamily("Serif", normal="Serif", bold="Serif-Bold", italic="Serif-Italic")

NAVY = HexColor("#0B1533")
GOLD = HexColor("#C9A23F")
GOLD_LIGHT = HexColor("#E9C877")
CREAM = HexColor("#F1E9DA")
INK = HexColor("#1F2430")
MUTED = HexColor("#6B6F78")
LINK = HexColor("#2F4C8A")

W, H = letter
M = 54            # side margin
CW = W - 2 * M    # content width

S = {
    "intro": ParagraphStyle("intro", fontName="Serif-Italic", fontSize=12.5, leading=19, textColor=MUTED),
    "body": ParagraphStyle("body", fontName="Sans", fontSize=9.3, leading=13.6, textColor=INK),
    "h2": ParagraphStyle("h2", fontName="Serif-Bold", fontSize=12.5, leading=16, textColor=NAVY),
    "steptitle": ParagraphStyle("st", fontName="Serif-Bold", fontSize=11.5, leading=14, textColor=NAVY),
    "stepbody": ParagraphStyle("sb", fontName="Sans", fontSize=8.8, leading=12.4, textColor=INK),
    "quote": ParagraphStyle("q", fontName="Serif-Italic", fontSize=11, leading=14, textColor=NAVY, leftIndent=18),
    "callout": ParagraphStyle("c", fontName="Sans-Bold", fontSize=9.2, leading=13.2, textColor=INK),
    "headline": ParagraphStyle("hl", fontName="Serif-Bold", fontSize=23, leading=27, textColor=NAVY),
    "source": ParagraphStyle("src", fontName="Sans", fontSize=7.3, leading=10, textColor=MUTED),
    "disclaimer": ParagraphStyle("d", fontName="Sans", fontSize=6.8, leading=9.4, textColor=MUTED),
}


def logo_mark():
    """Crop just the square 'N' mark from the gold logo (cached)."""
    out = os.path.join(ROOT, "scripts", ".logo-mark.png")
    if not os.path.exists(out):
        im = Image.open(os.path.join(ROOT, "assets", "logo-gold.png")).convert("RGBA")
        a = im.split()[-1]
        bbox = a.getbbox()
        # the mark is the top block; find the first fully transparent row band below it
        rows = [any(a.getpixel((x, y)) > 20 for x in range(bbox[0], bbox[2], 4)) for y in range(bbox[1], bbox[3])]
        end = bbox[1]
        for i, filled in enumerate(rows):
            if not filled and i > 40:
                end = bbox[1] + i
                break
        mark = im.crop((bbox[0], bbox[1], bbox[2], end))
        mark = mark.crop(mark.split()[-1].getbbox())
        mark.save(out)
    return out


class Doc:
    def __init__(self, lang):
        self.t = CONTENT[lang]
        self.lang = lang
        name = "houston-crash-playbook.pdf" if lang == "en" else f"houston-crash-playbook-{lang}.pdf"
        self.path = os.path.join(ROOT, "assets", name)
        self.c = canvas.Canvas(self.path, pagesize=letter)
        self.c.setTitle(self.t["meta_title"])
        self.c.setSubject(self.t["meta_subject"])
        self.c.setAuthor("Nguyen & Associates Injury Law Firm")
        self.page = 0

    # ---------- primitives ----------
    def para(self, text, style, x, y, width=None):
        p = Paragraph(text, style)
        _, h = p.wrap(width or CW, H)
        p.drawOn(self.c, x, y - h)
        return y - h

    def chrome(self):
        c = self.c
        c.setFillColor(GOLD)
        c.circle(M + 3, H - 38, 2.4, stroke=0, fill=1)
        c.setFont("Sans-Bold", 7)
        c.setFillColor(NAVY)
        c.drawString(M + 11, H - 40.5, self.t["running_head"])
        c.setFont("Sans", 7)
        c.setFillColor(MUTED)
        c.drawRightString(W - M, H - 40.5, f'{self.t["page_word"]} {self.page}')
        c.setStrokeColor(HexColor("#DDD6C8"))
        c.setLineWidth(0.5)
        c.line(M, 50, W - M, 50)
        c.setFont("Sans", 6.6)
        c.drawString(M, 38, "(713) 842-9442  ·  nalawtx.com  ·  10050 Northwest Fwy #200, Houston, TX 77092")
        c.drawRightString(W - M, 38, self.t["footer_right"])

    def start(self, eyebrow, headline, intro):
        if self.page:
            self.c.showPage()
        self.page += 1
        self.chrome()
        y = H - 84
        c = self.c
        c.setFont("Sans-Bold", 7.6)
        c.setFillColor(GOLD)
        c.drawString(M, y, eyebrow.upper())
        c.setStrokeColor(GOLD)
        c.setLineWidth(1.6)
        c.line(M, y - 7, M + 20, y - 7)
        y = self.para(headline, S["headline"], M, y - 18)
        y = self.para(intro, S["intro"], M, y - 8)
        return y - 10

    def callout(self, text, y, width=CW - 40):
        x = M + 20
        p = Paragraph(text, S["callout"])
        _, h = p.wrap(width - 36, H)
        box = h + 30
        c = self.c
        c.setFillColor(CREAM)
        c.rect(x, y - box, width, box, stroke=0, fill=1)
        c.setStrokeColor(GOLD)
        c.setLineWidth(1.6)
        c.line(x, y, x + width, y)
        p.drawOn(c, x + 18, y - 15 - h)
        return y - box

    def steps(self, items, y, start):
        for i, (title, body) in enumerate(items):
            c = self.c
            c.setFont("Serif-Bold", 22)
            c.setFillColor(GOLD)
            c.drawString(M + 6, y - 22, f"{start + i:02d}")
            yy = self.para(title, S["steptitle"], M + 52, y, CW - 60)
            yy = self.para(body, S["stepbody"], M + 52, yy - 2, CW - 60)
            y = yy - 18
        return y

    # ---------- pages ----------
    def cover(self):
        self.page = 0
        c = self.c
        c.setFillColor(NAVY)
        c.rect(0, 0, W, H, stroke=0, fill=1)
        mark = logo_mark()
        mw = 92
        iw, ih = Image.open(mark).size
        c.drawImage(mark, (W - mw) / 2, H - 300, width=mw, height=mw * ih / iw, mask="auto")
        t = self.t
        c.setFont("Sans-Bold", 7.6)
        c.setFillColor(GOLD)
        c.drawCentredString(W / 2, H - 352, t["cover_eyebrow"])
        style = ParagraphStyle("ct", fontName="Serif-Bold", fontSize=31, leading=34, textColor=HexColor("#FFFFFF"), alignment=1)
        y = self.para(t["cover_title"], style, M, H - 368)
        sub = ParagraphStyle("cs", fontName="Serif-Italic", fontSize=12.5, leading=18, textColor=GOLD_LIGHT, alignment=1)
        self.para(t["cover_sub"], sub, M + 70, y - 18, CW - 140)
        c.setStrokeColor(GOLD)
        c.setLineWidth(0.8)
        c.line(W / 2 - 45, 118, W / 2 + 45, 118)
        c.setFillColor(HexColor("#FFFFFF"))
        c.setFont("Sans", 7.5)
        c.drawCentredString(W / 2, 100, t["published_by"])
        c.setFont("Serif", 12)
        c.drawCentredString(W / 2, 83, "Nguyen & Associates Injury Law Firm")
        c.setFont("Sans", 7)
        c.setFillColor(GOLD_LIGHT)
        c.drawCentredString(W / 2, 69, t["cover_langs"])
        c.showPage()

    def build(self):
        t = self.t
        self.cover()

        p = t["p1"]
        y = self.start(p["eyebrow"], p["headline"], p["intro"])
        self.c.setStrokeColor(GOLD); self.c.setLineWidth(0.6)
        self.c.line(M, y, M + CW * 0.7, y)
        y = self.para(p["list_title"], S["h2"], M, y - 22)
        for i, item in enumerate(p["items"], 1):
            y = self.para(f"<b>{i}.</b>&nbsp; {item}", S["body"], M, y - 9)
        self.callout(p["callout"], y - 26)

        p = t["p2"]
        y = self.start(p["eyebrow"], p["headline"], p["intro"])
        self.steps(p["steps"], y - 6, 1)

        p = t["p3"]
        y = self.start(p["eyebrow"], p["headline"], p["intro"])
        self.steps(p["steps"], y - 6, 7)

        p = t["p4"]
        y = self.start(p["eyebrow"], p["headline"], p["intro"])
        y -= 6
        for i, (title, body) in enumerate(p["items"], 1):
            self.c.setFont("Serif-Bold", 13); self.c.setFillColor(GOLD)
            self.c.drawString(M + 10, y - 13, f"{i}.")
            yy = self.para(title, S["steptitle"], M + 40, y, CW - 48)
            yy = self.para(body, S["stepbody"], M + 40, yy - 2, CW - 48)
            y = yy - 15

        p = t["p5"]
        y = self.start(p["eyebrow"], p["headline"], p["intro"])
        for quote, translation in p["quotes"]:
            y = self.para(f"“{quote}”", S["quote"], M, y - 8)
            y = self.para(f"<b>{p['translation_word']}</b> {translation}", S["body"], M, y - 8)
            y -= 8
        self.callout(p["callout"], y - 16)

        p = t["p6"]
        y = self.start(p["eyebrow"], p["headline"], p["intro"])
        y = self.para(p["how_title"], S["h2"], M, y - 12)
        y = self.para(p["how_body"], S["body"], M, y - 7)
        y = self.para(f"<b>{p['examples_title']}</b>", S["body"], M, y - 12)
        y = self.para(p["example_a"], S["body"], M, y - 8)
        y = self.para(p["example_b"], S["body"], M, y - 8)
        y = self.para(p["why_title"], S["h2"], M, y - 22)
        y = self.para(p["why_body_1"], S["body"], M, y - 7)
        y = self.para(p["why_body_2"], S["body"], M, y - 8)
        self.para(p["source"], S["source"], M, y - 16)

        p = t["p7"]
        y = self.start(p["eyebrow"], p["headline"], p["intro"])
        y = self.para(p["what_title"], S["h2"], M, y - 12)
        y = self.para(p["what_body"], S["body"], M, y - 7)
        y = self.para(p["myths_title"], S["h2"], M, y - 18)
        for q, a in p["myths"]:
            y = self.para(f"<b>“{q}”</b>", S["body"], M, y - 9)
            y = self.para(a, S["body"], M, y - 2)
        y = self.callout(p["callout"], y - 20)
        self.para(p["source"], S["source"], M, y - 14)

        p = t["p8"]
        y = self.start(p["eyebrow"], p["headline"], p["intro"])
        y = self.para(p["green_title"], S["h2"], M, y - 12)
        for item in p["green"]:
            y = self.para(f"•&nbsp; {item}", S["body"], M, y - 8)
        y = self.para(p["red_title"], S["h2"], M, y - 20)
        for item in p["red"]:
            y = self.para(f"•&nbsp; {item}", S["body"], M, y - 8)

        p = t["p9"]
        y = self.start(p["eyebrow"], p["headline"], p["intro"])
        y = self.para(p["diff_title"], S["h2"], M, y - 12)
        for title, body in p["diffs"]:
            y = self.para(f"<b>{title}</b>&nbsp; {body}", S["body"], M, y - 9)
        # CTA box
        y -= 28
        box_h = 118
        c = self.c
        c.setFillColor(CREAM)
        c.rect(M + 20, y - box_h, CW - 40, box_h, stroke=0, fill=1)
        c.setStrokeColor(GOLD); c.setLineWidth(1.8)
        c.line(M + 20, y, W - M - 20, y)
        c.line(M + 20, y - box_h, W - M - 20, y - box_h)
        center = ParagraphStyle("cc", fontName="Serif-Bold", fontSize=11, leading=14, textColor=NAVY, alignment=1)
        big = ParagraphStyle("cb", fontName="Serif", fontSize=14, leading=18, textColor=NAVY, alignment=1)
        small = ParagraphStyle("cs2", fontName="Serif", fontSize=9.5, leading=13, textColor=NAVY, alignment=1)
        yy = self.para(p["cta_title"], center, M + 40, y - 24, CW - 80)
        yy = self.para(p["cta_call"], big, M + 40, yy - 12, CW - 80)
        self.para(p["cta_visit"], small, M + 40, yy - 12, CW - 80)
        y = y - box_h - 26
        self.para(p["disclaimer"], S["disclaimer"], M, y)
        self.c.save()
        return self.path


if __name__ == "__main__":
    for lang in ("en", "es", "vi"):
        print("built", Doc(lang).build())
