#!/usr/bin/env python3
"""
Week-indexed hyperlinked notebook generator for reMarkable tablets.

Creates one PDF per year: an index page with every ISO 8601 (Swedish-style)
week, followed by week pages with Previous / Index / Next buttons.

Requirements:  pip install reportlab

Examples:
  python make_week_notebook.py                          # defaults from SETTINGS below
  python make_week_notebook.py --years 2026-2032
  python make_week_notebook.py --format multi --n 5
  python make_week_notebook.py --lang sv --paper lined --spacing-mm 7
  python make_week_notebook.py --undated
  python make_week_notebook.py --device paperpro --toolbar right
"""

import argparse
import math
import os
from datetime import date, timedelta

from reportlab.lib.colors import Color, black, white
from reportlab.pdfgen import canvas

# ---------------------------------------------------------------------------
# SETTINGS: edit these defaults, or override any of them on the command line
# ---------------------------------------------------------------------------
SETTINGS = {
    "years": "2027",            # "2027" or a range such as "2026-2032"
    "device": "rm2",            # rm2, rm1, paperpro, or custom (see --width-px etc.)
    "format": "long",           # "long" = one tall page per week, "multi" = N pages per week
    "n": 5,                     # screens tall (long) or pages per week (multi)
    "paper": "dots",            # dots, lined, grid, blank
    "spacing_mm": 5.0,          # distance between dots/lines
    "lang": "en",               # en or sv (sets labels and month names)
    "undated": False,           # True = week numbers only, no dates or year
    "toolbar": "left",          # side that gets the wider margin
    "out_dir": ".",
    "name": "Week_Notebook_{YEAR}_{FORMAT}.pdf",  # {YEAR} and {FORMAT} are filled in
}

DEVICES = {                     # (width px, height px, DPI)
    "rm2": (1404, 1872, 226),
    "rm1": (1404, 1872, 226),
    "paperpro": (1620, 2160, 229),
}

LABELS = {
    "en": dict(week="Week", abbr="w.", index="Index",
               index_title="Week index", index_hint="tap a week to open it",
               page="page {p} of {n}", end="end",
               months="Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()),
    "sv": dict(week="Vecka", abbr="v.", index="Innehåll",
               index_title="Veckoregister", index_hint="tryck på en vecka för att öppna den",
               page="sida {p} av {n}", end="slut",
               months="jan feb mar apr maj jun jul aug sep okt nov dec".split()),
}

# E-ink friendly colours
TEXT_DARK = Color(0.30, 0.30, 0.30)   # dates and secondary text
LINE_LIGHT = Color(0.72, 0.72, 0.72)  # cell borders, dots and lines


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------
def weeks_in_year(year):
    """ISO 8601: 28 December is always in the last week of its year."""
    return date(year, 12, 28).isocalendar()[1]


def short_range(year, week, months):
    """Short date range for index cells, e.g. '15–21 Mar' or '29 Mar – 4 Apr'."""
    mon = date.fromisocalendar(year, week, 1)
    sun = mon + timedelta(days=6)
    if mon.month == sun.month:
        return f"{mon.day}–{sun.day} {months[mon.month - 1]}"
    return f"{mon.day} {months[mon.month - 1]} – {sun.day} {months[sun.month - 1]}"


def full_range(year, week, months):
    """Date range with year(s); both years are shown when a week crosses New Year."""
    mon = date.fromisocalendar(year, week, 1)
    sun = mon + timedelta(days=6)
    if mon.year != sun.year:
        return (f"{mon.day} {months[mon.month - 1]} {mon.year} – "
                f"{sun.day} {months[sun.month - 1]} {sun.year}")
    return f"{short_range(year, week, months)} {mon.year}"


# ---------------------------------------------------------------------------
# Notebook builder
# ---------------------------------------------------------------------------
class Notebook:
    def __init__(self, cfg, year):
        self.cfg = cfg
        self.year = year                      # None when undated
        self.L = LABELS[cfg["lang"]]
        wpx, hpx, dpi = cfg["screen"]
        self.W = wpx * 72 / dpi
        self.H = hpx * 72 / dpi
        wide, narrow = 58, 22
        if cfg["toolbar"] == "left":
            self.LM, self.RM = wide, narrow
        else:
            self.LM, self.RM = narrow, wide
        self.TM, self.BM = 26, 22
        self.nweeks = 53 if year is None else weeks_in_year(year)
        self.long = cfg["format"] == "long"
        self.n = cfg["n"]

    # -- small drawing helpers ------------------------------------------------
    def dest(self, week, page=1):
        return f"w{week}" if page == 1 else f"w{week}p{page}"

    def button(self, c, x, y, w, h, label, dest, filled):
        if filled:
            c.setFillColor(black)
            c.roundRect(x, y, w, h, 6, stroke=0, fill=1)
            c.setFillColor(white)
        else:
            c.setStrokeColor(black)
            c.setLineWidth(1.2)
            c.roundRect(x, y, w, h, 6, stroke=1, fill=0)
            c.setFillColor(black)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(x + w / 2, y + 12, label)
        # Generous invisible tap area around the visible button
        c.linkRect("", dest, (x - 3, y - 6, x + w + 3, y + h + 6), relative=0, thickness=0)

    def nav(self, c, week, y):
        bh, nw, iw, gap = 34, 58, 62, 8
        nx = self.W - self.RM - nw
        ix = nx - gap - iw
        px = ix - gap - nw
        a = self.L["abbr"]
        if week > 1:
            self.button(c, px, y, nw, bh, f"‹ {a} {week - 1}", self.dest(week - 1), False)
        self.button(c, ix, y, iw, bh, self.L["index"], "index", True)
        if week < self.nweeks:
            self.button(c, nx, y, nw, bh, f"{a} {week + 1} ›", self.dest(week + 1), False)

    def paper_form(self, c, top, bottom):
        """Draw the paper pattern once as a reusable form XObject."""
        s = self.cfg["spacing_mm"] * 72 / 25.4
        left, right = self.LM, self.W - self.RM
        c.beginForm("paper")
        style = self.cfg["paper"]
        if style == "dots":
            c.setFillColor(LINE_LIGHT)
            y = top - s
            while y > bottom:
                x = left
                while x < right + 0.1:
                    c.circle(x, y, 0.55, stroke=0, fill=1)
                    x += s
                y -= s
        elif style in ("lined", "grid"):
            c.setStrokeColor(LINE_LIGHT)
            c.setLineWidth(0.5)
            y = top - s
            while y > bottom:
                c.line(left, y, right, y)
                y -= s
            if style == "grid":
                x = left
                while x < right + 0.1:
                    c.line(x, top, x, bottom)
                    x += s
        c.endForm()

    # -- pages ----------------------------------------------------------------
    def index_page(self, c):
        W, H, LM, RM, TM, BM = self.W, self.H, self.LM, self.RM, self.TM, self.BM
        c.setPageSize((W, H))
        c.bookmarkPage("index")
        c.addOutlineEntry(self.L["index"], "index", 0)

        c.setFillColor(black)
        if self.year is not None:
            c.setFont("Helvetica-Bold", 22)
            c.drawString(LM, H - TM - 22, str(self.year))
            hint_x = LM + 62
            hint = f"{self.L['index_title']}  ·  {self.L['index_hint']}"
        else:
            c.setFont("Helvetica-Bold", 22)
            c.drawString(LM, H - TM - 22, self.L["index_title"])
            hint_x = LM + c.stringWidth(self.L["index_title"], "Helvetica-Bold", 22) + 12
            hint = self.L["index_hint"]
        c.setFont("Helvetica", 11)
        c.setFillColor(TEXT_DARK)
        c.drawString(hint_x, H - TM - 20, hint)

        cols = 4
        rows = math.ceil(self.nweeks / cols)
        top = H - TM - 44
        gap = 5
        cw = (W - LM - RM - gap * (cols - 1)) / cols
        ch = (top - BM - gap * (rows - 1)) / rows
        for i in range(self.nweeks):
            week = i + 1
            col, row = i // rows, i % rows          # fill down each column
            x = LM + col * (cw + gap)
            y = top - (row + 1) * ch - row * gap
            c.setStrokeColor(LINE_LIGHT)
            c.setLineWidth(0.8)
            c.roundRect(x, y, cw, ch, 4, stroke=1, fill=0)
            c.setFillColor(black)
            if self.year is None:
                c.setFont("Helvetica-Bold", 15)
                c.drawString(x + 7, y + ch / 2 - 5, f"{self.L['abbr']} {week}")
            else:
                c.setFont("Helvetica-Bold", 13)
                c.drawString(x + 7, y + ch - 17, f"{self.L['abbr']} {week}")
                c.setFillColor(TEXT_DARK)
                c.setFont("Helvetica", 7.5)
                c.drawString(x + 7, y + 7, short_range(self.year, week, self.L["months"]))
            c.linkRect("", self.dest(week), (x, y, x + cw, y + ch), relative=0, thickness=0)
        c.showPage()

    def header(self, c, week, page_h, page_no=None):
        LM, TM = self.LM, self.TM
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 24)
        c.drawString(LM, page_h - TM - 24, f"{self.L['week']} {week}")
        parts = []
        if self.year is not None:
            parts.append(full_range(self.year, week, self.L["months"]))
        if page_no is not None:
            parts.append(self.L["page"].format(p=page_no, n=self.n))
        if parts:
            c.setFont("Helvetica", 10.5)
            c.setFillColor(TEXT_DARK)
            c.drawString(LM, page_h - TM - 40, "   ·   ".join(parts))
        self.nav(c, week, page_h - TM - 38)
        c.setStrokeColor(black)
        c.setLineWidth(1)
        c.line(LM, page_h - TM - 52, self.W - self.RM, page_h - TM - 52)

    def week_pages(self, c):
        if self.long:
            ph = self.H * self.n
            footer_y = self.BM + 52
            c.setPageSize((self.W, ph))
            self.paper_form(c, ph - self.TM - 52, footer_y + 4)
            for week in range(1, self.nweeks + 1):
                c.bookmarkPage(self.dest(week), fit="FitH", top=ph)
                c.addOutlineEntry(f"{self.L['week']} {week}", self.dest(week), 1)
                self.header(c, week, ph)
                c.doForm("paper")
                c.setStrokeColor(black)
                c.setLineWidth(1)
                c.line(self.LM, footer_y, self.W - self.RM, footer_y)
                c.setFillColor(TEXT_DARK)
                c.setFont("Helvetica", 10.5)
                c.drawString(self.LM, self.BM + 14, f"{self.L['week']} {week}  ·  {self.L['end']}")
                self.nav(c, week, self.BM + 4)
                c.showPage()
        else:
            c.setPageSize((self.W, self.H))
            self.paper_form(c, self.H - self.TM - 52, self.BM)
            for week in range(1, self.nweeks + 1):
                for p in range(1, self.n + 1):
                    c.bookmarkPage(self.dest(week, p))
                    if p == 1:
                        c.addOutlineEntry(f"{self.L['week']} {week}", self.dest(week), 1)
                    self.header(c, week, self.H, page_no=p if self.n > 1 else None)
                    c.doForm("paper")
                    c.showPage()

    def build(self, path):
        c = canvas.Canvas(path, pagesize=(self.W, self.H))
        title = "Undated" if self.year is None else str(self.year)
        c.setTitle(f"Week Notebook {title}")
        self.index_page(c)
        self.week_pages(c)
        c.showOutline()
        c.save()
        pages = 1 + self.nweeks * (1 if self.long else self.n)
        return pages


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------
def parse_years(text):
    if "-" in text:
        a, b = text.split("-", 1)
        return list(range(int(a), int(b) + 1))
    return [int(text)]


def main():
    d = SETTINGS
    ap = argparse.ArgumentParser(description="Generate week-indexed reMarkable notebooks.")
    ap.add_argument("--years", default=d["years"], help='e.g. "2027" or "2026-2032"')
    ap.add_argument("--device", default=d["device"], choices=[*DEVICES, "custom"])
    ap.add_argument("--width-px", type=int, help="screen width in pixels (custom device)")
    ap.add_argument("--height-px", type=int, help="screen height in pixels (custom device)")
    ap.add_argument("--dpi", type=int, help="screen DPI (custom device)")
    ap.add_argument("--format", default=d["format"], choices=["long", "multi"])
    ap.add_argument("--n", type=int, default=d["n"], help="screens tall or pages per week")
    ap.add_argument("--paper", default=d["paper"], choices=["dots", "lined", "grid", "blank"])
    ap.add_argument("--spacing-mm", type=float, default=d["spacing_mm"])
    ap.add_argument("--lang", default=d["lang"], choices=list(LABELS))
    ap.add_argument("--undated", action="store_true", default=d["undated"])
    ap.add_argument("--toolbar", default=d["toolbar"], choices=["left", "right"])
    ap.add_argument("--out-dir", default=d["out_dir"])
    ap.add_argument("--name", default=d["name"], help="file name template with {YEAR} and {FORMAT}")
    args = ap.parse_args()

    if args.device == "custom":
        if not (args.width_px and args.height_px and args.dpi):
            ap.error("--device custom needs --width-px, --height-px and --dpi")
        screen = (args.width_px, args.height_px, args.dpi)
    else:
        screen = DEVICES[args.device]
    if args.n < 1:
        ap.error("--n must be at least 1")
    if args.format == "long" and screen[1] * 72 / screen[2] * args.n > 14400:
        ap.error("page too tall for PDF (14400 pt limit); lower --n")

    cfg = dict(format=args.format, n=args.n, paper=args.paper, spacing_mm=args.spacing_mm,
               lang=args.lang, toolbar=args.toolbar, screen=screen)
    fmt_label = "Long_Pages" if args.format == "long" else f"{args.n}_Pages_per_Week"
    os.makedirs(args.out_dir, exist_ok=True)

    years = [None] if args.undated else parse_years(args.years)
    for year in years:
        name = args.name.format(YEAR="Undated" if year is None else year, FORMAT=fmt_label)
        path = os.path.join(args.out_dir, name)
        nb = Notebook(cfg, year)
        pages = nb.build(path)
        print(f"{path}: {nb.nweeks} weeks, {pages} pages")


if __name__ == "__main__":
    main()
