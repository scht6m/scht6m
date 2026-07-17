#!/usr/bin/env python3
"""Add GitHub-style month/day labels and a Less..More legend to the snk snake SVG.

Usage: python3 decorate_snake.py <svg-file>   (edits the file in place)

Geometry is derived from the contribution-grid cells in the SVG itself, so it
follows snk's layout. Month labels are computed from the run date: the last
grid column is the current week (Sunday-start, UTC), matching GitHub's graph.
"""
import re
import sys
from datetime import datetime, timedelta, timezone

FONT_SIZE = 10
TEXT_COLOR = "#7a8490"
CHAR_W = 0.6 * FONT_SIZE  # rough average glyph width, only used for spacing
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
CELL = 12  # snk dot size (kept in CSS, not on the rect attributes)


def text_w(s):
    return len(s) * CHAR_W


def fmt(v):
    return f"{v:g}"


def main(path):
    with open(path, encoding="utf-8") as f:
        svg = f.read()

    vb = re.search(r'viewBox="([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)"', svg)
    x0, y0, w, h = (float(v) for v in vb.groups())

    cells = re.findall(r'<rect class="c[^"]*" x="([-\d.]+)" y="([-\d.]+)"', svg)
    if not cells:
        sys.exit("no contribution cells found in the SVG")
    xs = sorted({float(x) for x, _ in cells})
    ys = sorted({float(y) for _, y in cells})
    pitch = xs[1] - xs[0]
    n_cols = len(xs)
    grid_left = xs[0] - (pitch - CELL) / 2
    grid_right = xs[-1] + CELL
    grid_bottom = ys[-1] + CELL

    parts = []

    def label(x, y, s, anchor="start"):
        a = f' text-anchor="{anchor}"' if anchor != "start" else ""
        parts.append(f'<text class="lbl" x="{fmt(x)}" y="{fmt(y)}"{a}>{s}</text>')

    # month labels: column i is the week starting (n_cols-1-i) weeks before
    # the Sunday of the current week
    today = datetime.now(timezone.utc).date()
    this_sunday = today - timedelta(days=(today.weekday() + 1) % 7)

    def week_start(i):
        return this_sunday - timedelta(weeks=n_cols - 1 - i)

    marks = [(0, week_start(0).month)]
    for i in range(1, n_cols):
        if week_start(i).month != week_start(i - 1).month:
            marks.append((i, week_start(i).month))
    if len(marks) > 1 and marks[1][0] - marks[0][0] < 3:
        marks = marks[1:]  # partial first month is too narrow for a label

    month_y = ys[0] - 23
    for col, month in marks:
        label(xs[col], month_y, MONTHS[month - 1])

    # day labels next to the Mon / Wed / Fri rows (rows are Sun..Sat top-down)
    day_x = grid_left - 8
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        label(day_x, ys[row] + CELL / 2 + 3.5, name, anchor="end")

    # legend: Less [c0..c4] More, right-aligned to the grid's right edge
    legend_y = grid_bottom + 10
    baseline = legend_y + CELL / 2 + 3.5
    sw_right = grid_right - text_w("More") - 8
    sw_x = [sw_right - CELL - (4 - j) * pitch for j in range(5)]
    label(sw_x[0] - 8, baseline, "Less", anchor="end")
    for j, x in enumerate(sw_x):
        parts.append(
            f'<rect x="{fmt(x)}" y="{fmt(legend_y)}" width="{CELL}" height="{CELL}"'
            f' rx="2" ry="2" fill="var(--c{j})" stroke="var(--cb)" stroke-width="1"/>'
        )
    label(grid_right, baseline, "More", anchor="end")

    # grow the viewBox where the labels need room
    new_x0 = min(x0, day_x - text_w("Wed") - 8)
    new_y0 = min(y0, month_y - FONT_SIZE)
    new_right = max(x0 + w, xs[marks[-1][0]] + text_w(MONTHS[marks[-1][1] - 1]) + 4)
    new_bottom = max(y0 + h, legend_y + CELL + 6)
    new_w, new_h = new_right - new_x0, new_bottom - new_y0

    style = (
        f"<style>.lbl{{fill:{TEXT_COLOR};font-size:{FONT_SIZE}px;"
        f"font-family:'Segoe UI',Ubuntu,Helvetica,Arial,sans-serif}}</style>"
    )
    svg = svg.replace(vb.group(0), f'viewBox="{fmt(new_x0)} {fmt(new_y0)} {fmt(new_w)} {fmt(new_h)}"', 1)
    svg = re.sub(r'width="[-\d.]+" height="[-\d.]+"',
                 f'width="{fmt(new_w)}" height="{fmt(new_h)}"', svg, count=1)
    svg = svg.replace("</svg>", style + "<g>" + "".join(parts) + "</g></svg>", 1)

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(svg)

    months_log = ", ".join(f"{MONTHS[m - 1]}@col{c}" for c, m in marks)
    print(f"decorated {path}: {n_cols} cols, months [{months_log}], "
          f"viewBox {fmt(new_x0)} {fmt(new_y0)} {fmt(new_w)} {fmt(new_h)}")


if __name__ == "__main__":
    main(sys.argv[1])
