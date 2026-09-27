# Prompt: Week-Indexed Hyperlinked Notebook for reMarkable

Copy everything below the line into Claude (or another AI assistant with code execution). Edit the **Settings** section first; everything else can stay as is.

---

Please generate a hyperlinked PDF notebook for a reMarkable e-ink tablet using Python and ReportLab. Build the PDF, render a few pages to PNG to check the layout visually, verify the links, and then give me the file(s).

## Settings (edit these)

| Setting | Value | Options / notes |
|---|---|---|
| Year(s) | `2027` | One year, or a range like `2026–2032` (one PDF per year) |
| Device | reMarkable 2 | reMarkable 2: 1404 × 1872 px at 226 DPI. For other devices, give the screen resolution and DPI |
| Week page format | Long pages | **Long pages**: one page per week, N screens tall. **Multi-page**: N normal-sized pages per week |
| N (length or page count) | `5` | How many screens tall (long pages) or how many pages per week (multi-page) |
| Paper style | Dot grid, 5 mm spacing | Dot grid, lined, square grid, or blank; set the spacing |
| Week label | `Week` | e.g. `Vecka` for Swedish |
| Week abbreviation | `w.` | e.g. `v.` for Swedish |
| Month names | English 3-letter (`Jan`, `Feb` …) | e.g. Swedish: `jan feb mar apr maj jun jul aug sep okt nov dec` |
| Show dates | Yes | Set to No for an undated notebook (week numbers only) |
| Toolbar side | Left | Left or right; the wider margin goes on this side |
| Output file name | `Week_Notebook_{YEAR}_Long_Pages.pdf` | Must be unique per variation so files don't overwrite each other |

## Week numbering

- Use the **ISO 8601 week system** (the Swedish/European standard): weeks start on Monday, and week 1 is the week containing the year's first Thursday.
- Compute weeks with Python's `date.fromisocalendar(year, week, 1)`. Get the number of weeks in a year with `date(year, 12, 28).isocalendar()[1]`. Some years have 53 weeks (for example 2026 and 2032), so never hard-code 52.
- Week 1 can start in the previous December, and the last week can end in the next January. When a week crosses a year boundary, show both years in full on the week page, for example `29 Dec 2025 – 4 Jan 2026`. Never write a single trailing year that makes the range ambiguous.

## Page size and margins

- Size every page to the device's screen aspect ratio: width = `px_width × 72 / DPI` points, height = `px_height × 72 / DPI` points. For the reMarkable 2 that is about 447 × 596 pt.
- Margins: about 58 pt on the toolbar side, about 22 pt on the other sides, about 26 pt at the top.
- Long-page format: the index page stays at normal height, and each week page is N × the normal height. Switch sizes with `canvas.setPageSize()`.

## Page 1: Index

- Heading: the year in large bold type, followed by a small line: `Week index · tap a week to open it`.
- A grid of every week in 4 columns, filling **down each column** (weeks 1–13 in column 1, and so on) so it reads like a calendar year. Compute the row count as `ceil(weeks / 4)` so 53-week years fit.
- Each cell is a light grey rounded rectangle with the abbreviation and number in bold (for example `w. 12`) and the date range underneath in smaller dark grey text (for example `15–21 Mar` or `29 Mar – 4 Apr`).
- **The whole cell is a tappable internal link** to the first page of that week.

## Week pages

**Header (top of the page)**

- Left: the week label and number in large bold type (for example `Week 12`). Underneath, the full date range with year in dark grey. For the multi-page format, also add `· page X of N`.
- Right: three navigation buttons in a row, each about 34 pt tall:
  - `‹ w. 11`: outlined, links to the previous week. Omit it on week 1.
  - `Index`: solid black with white text, links to page 1.
  - `w. 13 ›`: outlined, links to the next week. Omit it on the last week.
- Previous/next buttons go to the **first page** of that week.
- A thin black rule under the header, across the full content width.

**Body**

- The chosen paper style (dot grid by default) filling the space between the header rule and the bottom margin (or footer).
- Draw the grid **once as a ReportLab form XObject** (`beginForm` / `endForm` / `doForm`) and reuse it on every page, so the file stays small (under about 500 KB per year).

**Footer (long-page format only)**

- A thin rule near the bottom, a small `Week 12 · end` label on the left, and the same three navigation buttons on the right. This way, users don't have to scroll back up to move on.

## Styling for e-ink

- Colors: black for headings and buttons, dark grey (about RGB 0.3) for dates and secondary text, light grey (about RGB 0.72) for cell borders and dots. Mid greys look washed out on e-ink, so avoid them for anything that should be read.
- Font: Helvetica / Helvetica-Bold (built into ReportLab). Don't use Unicode superscripts or special glyphs that the built-in fonts can't render. The `‹` and `›` arrows are fine.
- Make link areas generous: pad each clickable rectangle about 3–6 pt beyond the visible button, since links are tapped with a finger.

## Links (important)

- Use ReportLab's `canvas.bookmarkPage(name)` to create named destinations and `canvas.linkRect("", name, rect, relative=0, thickness=0)` to create invisible clickable areas.
- For long pages, create the destination with `fit="FitH", top=page_height` so it opens at the top.
- Add a PDF outline (sidebar bookmarks): `Index`, then `Week 1` … `Week N`.
- Use **internal links only**. The reMarkable has no browser, so web links do nothing.

## Verification before delivering

1. Render the index and at least one week page to PNG (`pdftoppm`) and look at them. Check for overlapping text, clipped buttons, and grid alignment.
2. Check the page count: 1 + weeks (long format) or 1 + weeks × N (multi-page format).
3. Count link annotations with `pypdf`: the index should have one per week. The first and last week pages should have one fewer navigation link than the middle weeks.
4. Print the date labels for week 1 and the last week of every year generated, and confirm that year-crossing ranges show both years.

## Usage notes to include in your reply

- Transfer the PDF with the reMarkable desktop/mobile app or my.remarkable.com.
- Links are activated by tapping with a **finger**; the Marker pen won't trigger them.
- Long pages open shrunk to fit the screen. Zoom in to fit the width, then scroll down.

## Optional variations you can ask for

- Undated notebook (week numbers only, no year)
- Swedish labels throughout (`Vecka`, `v.`, Swedish month names, `Innehåll` instead of `Index`)
- Lined or square grid instead of dots, or a different spacing
- A notes section or monthly overview pages linked from the index
- Right-handed vs left-handed layouts (swap the wide margin and move the buttons)
- Different devices: provide the resolution and DPI
