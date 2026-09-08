"""Pure-Python inline SVG chart builders for the FlowSales report. Standard library only.

Every builder returns a Chart with two strings: ``svg`` (an inline SVG fragment) and
``table`` (the matching HTML table, the accessibility twin of the chart). Colours are
never hard-coded here: marks carry class tokens such as ``fill-s1`` or ``stroke-lv2``
and template.html maps them to the validated light and dark palettes through CSS
custom properties. Tooltips ride on ``data-tip`` attributes: lines separated by
newlines; the first line is the title, later lines are ``label|value|token`` triples
that the page turns into keyed rows. Every mark sits inside a focusable hit target
that is larger than the mark itself.

Mark specs follow the dataviz skill: bars at most 24px thick with a 4px rounded data
end and a square baseline end, 2px lines with round joins, markers of radius 4 with a
2px surface ring, hairline solid gridlines, one axis per chart, a legend whenever two
or more series share a plot, direct labels only where asked for.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from html import escape
from typing import Any, Callable, Optional, Sequence

CHAR_W = 6.2          # estimated width of one character at 11px in the system sans
SMALL_CHAR_W = 5.4    # at 10px
BAR_MAX = 24
BAR_RADIUS = 4
GAP = 2
LEGEND_ROW = 18


# ---------------------------------------------------------------- formatting

def fmt_num(v: Any, digits: int = 0) -> str:
    if v is None:
        return "n/a"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if digits == 0 and abs(f - round(f)) < 1e-9:
        return f"{int(round(f)):,}"
    return f"{f:,.{digits or 1}f}"


def fmt_pct(v: Any, digits: int = 0) -> str:
    if v is None:
        return "n/a"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    return f"{f * 100:.{digits}f}%"


def fmt_level(v: Any, digits: int = 1) -> str:
    if v is None:
        return "n/a"
    try:
        return f"{float(v):.{digits}f}"
    except (TypeError, ValueError):
        return str(v)


SYMBOLS = {"GBP": "£", "USD": "$", "EUR": "€"}


def fmt_money_total(total: Any, by_currency: Any, currency: str = "", compact: bool = False) -> str:
    """Show each currency's own sum when more than one is present; never add currencies together."""
    if isinstance(by_currency, dict) and len(by_currency) > 1:
        return " + ".join(fmt_money(v, k, compact) for k, v in sorted(by_currency.items()))
    if isinstance(by_currency, dict) and len(by_currency) == 1:
        (cur, val), = by_currency.items()
        return fmt_money(val, cur, compact)
    return fmt_money(total, currency, compact)


def fmt_money(v: Any, currency: str = "", compact: bool = False) -> str:
    if v is None:
        return "n/a"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    sym = SYMBOLS.get((currency or "").upper())
    a = abs(f)
    if compact:
        if a >= 1e9:
            body = f"{f / 1e9:.1f}B"
        elif a >= 1e6:
            body = f"{f / 1e6:.1f}M"
        elif a >= 1e4:
            body = f"{f / 1e3:.0f}K"
        elif a >= 1e3:
            body = f"{f / 1e3:.1f}K"
        else:
            body = f"{f:,.0f}"
    else:
        body = f"{f:,.0f}"
    if sym:
        return f"{sym}{body}"
    return f"{body} {currency}".strip()


def fmt_date(v: Any) -> str:
    """ISO timestamp or date to '14 Jun 2026'. Anything unparseable is returned as is."""
    if not v:
        return "n/a"
    s = str(v)
    try:
        y, m, d = int(s[0:4]), int(s[5:7]), int(s[8:10])
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        return f"{d} {months[m - 1]} {y}"
    except (ValueError, IndexError):
        return s


# ---------------------------------------------------------------- primitives

def _n(x: float) -> str:
    if abs(x - round(x)) < 0.005:
        return str(int(round(x)))
    return f"{x:.1f}"


def _esc(s: Any) -> str:
    return escape("" if s is None else str(s), quote=True)


def _tipattr(tip: str) -> str:
    return _esc(tip).replace("\n", "&#10;")


def tip(title: Any, rows: Sequence[Sequence[Any]] = ()) -> str:
    """Encode a tooltip: title line, then label|value|token rows."""
    lines = ["" if title is None else str(title)]
    for r in rows:
        lines.append("|".join("" if p is None else str(p) for p in r))
    return "\n".join(lines)


def _fit(text: Any, max_w: float, char_w: float = CHAR_W) -> str:
    text = "" if text is None else str(text)
    n = int(max_w // char_w)
    if len(text) <= n:
        return text
    if n <= 1:
        return ""
    return text[: n - 1].rstrip() + "…"


def _ticks(vmax: Optional[float], is_rate: bool = False, count: int = 4) -> list[float]:
    if is_rate:
        return [0.0, 0.25, 0.5, 0.75, 1.0]
    if vmax is None or vmax <= 0:
        return [0.0, 1.0]
    raw = vmax / count
    mag = 10 ** math.floor(math.log10(raw))
    step = mag
    for m in (1, 2, 2.5, 5, 10):
        step = m * mag
        if step >= raw:
            break
    top = math.ceil(vmax / step - 1e-9) * step
    k = max(1, int(round(top / step)))
    return [i * step for i in range(k + 1)]


def _vbar(x: float, y: float, w: float, h: float, r: float = BAR_RADIUS) -> str:
    """Vertical bar: rounded top (data end), square bottom (baseline)."""
    if h <= 0 or w <= 0:
        return ""
    r = min(r, w / 2, h)
    return (f"M{_n(x)},{_n(y + h)}V{_n(y + r)}A{_n(r)},{_n(r)} 0 0 1 {_n(x + r)},{_n(y)}"
            f"H{_n(x + w - r)}A{_n(r)},{_n(r)} 0 0 1 {_n(x + w)},{_n(y + r)}V{_n(y + h)}Z")


def _hbar(x: float, y: float, w: float, h: float, r: float = BAR_RADIUS) -> str:
    """Horizontal bar: rounded right end (data end), square left end (baseline)."""
    if h <= 0 or w <= 0:
        return ""
    r = min(r, h / 2, w)
    return (f"M{_n(x)},{_n(y)}H{_n(x + w - r)}A{_n(r)},{_n(r)} 0 0 1 {_n(x + w)},{_n(y + r)}"
            f"V{_n(y + h - r)}A{_n(r)},{_n(r)} 0 0 1 {_n(x + w - r)},{_n(y + h)}H{_n(x)}Z")


def _svg(w: float, h: float, body: str, aria: str) -> str:
    return (f'<svg class="viz" viewBox="0 0 {_n(w)} {_n(h)}" width="{_n(w)}" height="{_n(h)}" '
            f'role="img" aria-label="{_esc(aria)}">{body}</svg>')


def _table(headers: Sequence[str], rows: Sequence[Sequence[Any]], caption: str = "",
           numeric: Optional[Sequence[int]] = None) -> str:
    num = set(numeric or [])
    out = ['<table class="viz-table">']
    if caption:
        out.append(f"<caption>{_esc(caption)}</caption>")
    cells = []
    for i, hd in enumerate(headers):
        cls = ' class="num"' if i in num else ""
        cells.append(f'<th scope="col"{cls}>{_esc(hd)}</th>')
    out.append("<thead><tr>" + "".join(cells) + "</tr></thead><tbody>")
    for r in rows:
        cells = []
        for i, c in enumerate(r):
            cls = ' class="num"' if i in num else ""
            cells.append(f"<td{cls}>{_esc(c)}</td>")
        out.append("<tr>" + "".join(cells) + "</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def _legend(items: Sequence[tuple[str, str, bool]], x: float, y: float, max_w: float, kind: str = "rect") -> tuple[str, float]:
    """Flow-layout legend. items: (name, token, dashed). Returns (svg, height used)."""
    parts = []
    cx, cy = x, y
    for name, token, dashed in items:
        w = (18 if kind == "line" else 14) + len(name) * CHAR_W + 16
        if cx > x and cx + w > x + max_w:
            cx = x
            cy += LEGEND_ROW
        if kind == "line":
            dash = ' stroke-dasharray="5 4"' if dashed else ""
            parts.append(f'<line x1="{_n(cx)}" y1="{_n(cy)}" x2="{_n(cx + 14)}" y2="{_n(cy)}" class="lkey stroke-{token}"{dash}/>')
            tx = cx + 19
        else:
            parts.append(f'<rect x="{_n(cx)}" y="{_n(cy - 5)}" width="10" height="10" rx="2" class="mark fill-{token} {token}"/>')
            tx = cx + 15
        parts.append(f'<text x="{_n(tx)}" y="{_n(cy + 4)}" class="lg">{_esc(name)}</text>')
        cx += w
    return "".join(parts), (cy - y) + LEGEND_ROW


# ---------------------------------------------------------------- chart object

@dataclass
class Chart:
    svg: str
    table: str

    def figure(self, chart_id: str, title: str = "", note: str = "", table_open: bool = False) -> str:
        """Wrap the chart and its table in a <figure> with a Chart/Table toggle."""
        hidden_chart = " hidden" if table_open else ""
        hidden_table = "" if table_open else " hidden"
        pressed = "true" if table_open else "false"
        note_html = f'<p class="fig-note">{_esc(note)}</p>' if note else ""
        return (f'<figure class="fig" id="fig-{_esc(chart_id)}"><figcaption class="fig-head">'
                f'<span class="fig-title">{_esc(title)}</span>'
                f'<button type="button" class="btn btn-sm fig-toggle" aria-pressed="{pressed}">Table</button></figcaption>'
                f'<div class="fig-chart"{hidden_chart}>{self.svg}</div>'
                f'<div class="fig-table"{hidden_table}>{self.table}</div>{note_html}</figure>')

    def as_dict(self) -> dict:
        return {"svg": self.svg, "table": self.table}


# ---------------------------------------------------------------- bar (vertical)

def bar_chart(categories: Sequence[str], values: Sequence[Optional[float]], *,
              value_fmt: Callable[[Any], str] = fmt_num, is_rate: bool = False, y_max: Optional[float] = None,
              bar_labels: Optional[Sequence[str]] = None, tips: Optional[Sequence[str]] = None, color: str = "s1",
              width: int = 560, height: int = 240, aria: str = "", table_caption: str = "",
              table_headers: Optional[Sequence[str]] = None, table_rows: Optional[Sequence[Sequence[Any]]] = None) -> Chart:
    n = len(categories)
    vals = [None if v is None else float(v) for v in values]
    vmax = max([v for v in vals if v is not None] + [0.0])
    ticks = _ticks(y_max if y_max is not None else vmax, is_rate)
    top = ticks[-1] if ticks[-1] > 0 else 1.0
    tick_labels = [value_fmt(t) for t in ticks]
    left = max(len(t) for t in tick_labels) * CHAR_W + 12
    pad_top = 24 if bar_labels else 12
    bottom = 28
    plot_w = width - left - 12
    plot_h = height - pad_top - bottom
    y0 = pad_top + plot_h
    body = []
    for t, lab in zip(ticks, tick_labels):
        y = y0 - (t / top) * plot_h
        body.append(f'<line x1="{_n(left)}" x2="{_n(left + plot_w)}" y1="{_n(y)}" y2="{_n(y)}" class="grid"/>')
        body.append(f'<text x="{_n(left - 6)}" y="{_n(y + 4)}" class="ax" text-anchor="end">{_esc(lab)}</text>')
    slot = plot_w / max(n, 1)
    bw = min(BAR_MAX, slot * 0.6)
    for i, (cat, v) in enumerate(zip(categories, vals)):
        cx = left + slot * (i + 0.5)
        x = cx - bw / 2
        h = 0.0 if v is None else (v / top) * plot_h
        y = y0 - h
        t = tips[i] if tips and i < len(tips) and tips[i] else tip(cat, [("value", value_fmt(v), color)])
        body.append(f'<g class="hit" tabindex="0" data-tip="{_tipattr(t)}">')
        body.append(f'<rect x="{_n(left + slot * i)}" y="{_n(pad_top)}" width="{_n(slot)}" height="{_n(plot_h)}" class="hitarea"/>')
        if h > 0:
            body.append(f'<path d="{_vbar(x, y, bw, h)}" class="mark fill-{color} {color}"/>')
        if bar_labels and i < len(bar_labels) and bar_labels[i]:
            body.append(f'<text x="{_n(cx)}" y="{_n(y - 6)}" class="dl" text-anchor="middle">{_esc(bar_labels[i])}</text>')
        body.append("</g>")
        body.append(f'<text x="{_n(cx)}" y="{_n(y0 + 17)}" class="ax" text-anchor="middle">{_esc(_fit(cat, slot - 6))}</text>')
    body.append(f'<line x1="{_n(left)}" x2="{_n(left + plot_w)}" y1="{_n(y0)}" y2="{_n(y0)}" class="axis"/>')
    headers = list(table_headers) if table_headers else ["Category", "Value"]
    rows = table_rows if table_rows is not None else [(c, value_fmt(v)) for c, v in zip(categories, vals)]
    return Chart(_svg(width, height, "".join(body), aria or table_caption),
                 _table(headers, rows, table_caption, numeric=range(1, len(headers))))


# ---------------------------------------------------------------- bar (horizontal)

def hbar_chart(categories: Sequence[str], values: Sequence[Optional[float]], *,
               value_fmt: Callable[[Any], str] = fmt_num, is_rate: bool = False, x_max: Optional[float] = None,
               tips: Optional[Sequence[str]] = None, color: str = "s1", width: int = 520, row_h: int = 24,
               aria: str = "", table_caption: str = "", table_headers: Optional[Sequence[str]] = None,
               table_rows: Optional[Sequence[Sequence[Any]]] = None, label_max: int = 160) -> Chart:
    n = len(categories)
    vals = [None if v is None else float(v) for v in values]
    vmax = max([v for v in vals if v is not None] + [0.0])
    ticks = _ticks(x_max if x_max is not None else vmax, is_rate)
    top = ticks[-1] if ticks[-1] > 0 else 1.0
    tick_labels = [value_fmt(t) for t in ticks]
    label_w = min(label_max, max([len(str(c)) for c in categories] + [4]) * CHAR_W + 6)
    left = label_w + 8
    right = max(len(value_fmt(v)) for v in vals) * CHAR_W + 16 if vals else 40
    pad_top = 6
    bottom = 22
    plot_w = width - left - right
    plot_h = row_h * max(n, 1)
    height = pad_top + plot_h + bottom
    y_end = pad_top + plot_h
    body = []
    for t, lab in zip(ticks, tick_labels):
        x = left + (t / top) * plot_w
        body.append(f'<line x1="{_n(x)}" x2="{_n(x)}" y1="{_n(pad_top)}" y2="{_n(y_end)}" class="grid"/>')
        body.append(f'<text x="{_n(x)}" y="{_n(y_end + 15)}" class="ax" text-anchor="middle">{_esc(lab)}</text>')
    bh = min(18, row_h - 6)
    for i, (cat, v) in enumerate(zip(categories, vals)):
        y = pad_top + row_h * i + (row_h - bh) / 2
        w = 0.0 if v is None else (v / top) * plot_w
        t = tips[i] if tips and i < len(tips) and tips[i] else tip(cat, [("value", value_fmt(v), color)])
        body.append(f'<g class="hit" tabindex="0" data-tip="{_tipattr(t)}">')
        body.append(f'<rect x="0" y="{_n(pad_top + row_h * i)}" width="{_n(width)}" height="{_n(row_h)}" class="hitarea"/>')
        if w > 0:
            body.append(f'<path d="{_hbar(left, y, w, bh)}" class="mark fill-{color} {color}"/>')
        body.append(f'<text x="{_n(left + w + 6)}" y="{_n(y + bh / 2 + 4)}" class="dl">{_esc(value_fmt(v))}</text>')
        body.append("</g>")
        body.append(f'<text x="{_n(left - 8)}" y="{_n(y + bh / 2 + 4)}" class="ax cat" text-anchor="end">{_esc(_fit(cat, label_w))}</text>')
    body.append(f'<line x1="{_n(left)}" x2="{_n(left)}" y1="{_n(pad_top)}" y2="{_n(y_end)}" class="axis"/>')
    headers = list(table_headers) if table_headers else ["Category", "Value"]
    rows = table_rows if table_rows is not None else [(c, value_fmt(v)) for c, v in zip(categories, vals)]
    return Chart(_svg(width, height, "".join(body), aria or table_caption),
                 _table(headers, rows, table_caption, numeric=range(1, len(headers))))


# ---------------------------------------------------------------- grouped bars

def grouped_bars(categories: Sequence[str], series: Sequence[dict], *,
                 value_fmt: Callable[[Any], str] = fmt_num, is_rate: bool = False, y_max: Optional[float] = None,
                 bar_labels: Optional[Sequence[Sequence[Optional[str]]]] = None, tips: Optional[Sequence[str]] = None,
                 width: int = 560, height: int = 260, aria: str = "", table_caption: str = "",
                 category_names: Optional[Sequence[str]] = None, table_rows: Optional[Sequence[Sequence[Any]]] = None,
                 table_headers: Optional[Sequence[str]] = None) -> Chart:
    """series: [{"name": str, "values": [..], "color": token}]. Legend always present for two or more series."""
    n = len(categories)
    ns = len(series)
    allv = [float(v) for s in series for v in s["values"] if v is not None]
    vmax = max(allv + [0.0])
    ticks = _ticks(y_max if y_max is not None else vmax, is_rate)
    top = ticks[-1] if ticks[-1] > 0 else 1.0
    tick_labels = [value_fmt(t) for t in ticks]
    left = max(len(t) for t in tick_labels) * CHAR_W + 12
    plot_w = width - left - 12
    legend_svg, legend_h = ("", 0)
    if ns >= 2:
        legend_svg, legend_h = _legend([(s["name"], s.get("color", "s1"), False) for s in series], left, 10, plot_w, "rect")
    pad_top = legend_h + (22 if bar_labels else 12)
    bottom = 28
    plot_h = height - pad_top - bottom
    y0 = pad_top + plot_h
    body = [legend_svg]
    for t, lab in zip(ticks, tick_labels):
        y = y0 - (t / top) * plot_h
        body.append(f'<line x1="{_n(left)}" x2="{_n(left + plot_w)}" y1="{_n(y)}" y2="{_n(y)}" class="grid"/>')
        body.append(f'<text x="{_n(left - 6)}" y="{_n(y + 4)}" class="ax" text-anchor="end">{_esc(lab)}</text>')
    slot = plot_w / max(n, 1)
    group_w = min(ns * BAR_MAX + (ns - 1) * GAP, slot * 0.72)
    bw = (group_w - (ns - 1) * GAP) / max(ns, 1)
    for i, cat in enumerate(categories):
        cx = left + slot * (i + 0.5)
        name = category_names[i] if category_names and i < len(category_names) else cat
        rows = [(s["name"], value_fmt(s["values"][i] if i < len(s["values"]) else None), s.get("color", "s1")) for s in series]
        t = tips[i] if tips and i < len(tips) and tips[i] else tip(name, rows)
        body.append(f'<g class="hit" tabindex="0" data-tip="{_tipattr(t)}">')
        body.append(f'<rect x="{_n(left + slot * i)}" y="{_n(pad_top)}" width="{_n(slot)}" height="{_n(plot_h)}" class="hitarea"/>')
        bars: list[tuple[float, float, float, Optional[str]]] = []  # (x, y_top, height, label) per series in this group
        for j, s in enumerate(series):
            v = s["values"][i] if i < len(s["values"]) else None
            h = 0.0 if v is None else (float(v) / top) * plot_h
            x = cx - group_w / 2 + j * (bw + GAP)
            y = y0 - h
            token = s.get("color", "s1")
            if h > 0:
                body.append(f'<path d="{_vbar(x, y, bw, h)}" class="mark fill-{token} {token}"/>')
            label = bar_labels[j][i] if bar_labels and j < len(bar_labels) and i < len(bar_labels[j]) else None
            bars.append((x, y, h, label))
        # Labels are wider than the bars, so they are drawn after every bar in the group (on top), lifted
        # clear of any taller neighbour they would run into, then staggered a line apart when two still
        # collide (equal before and after values). Keeps small bars and equal bars readable.
        placed: list[tuple[float, float, float]] = []
        for x, y, h, label in bars:
            if not label:
                continue
            half = len(label) * CHAR_W * 0.9 / 2
            lx, ly = x + bw / 2, y - 5
            for bx, by, bh, _ in bars:
                if bh > 0 and lx - half < bx + bw and lx + half > bx and by < ly + 4:
                    ly = min(ly, by - 5)
            for _ in range(len(placed)):
                if any(lx - half < px1 and lx + half > px0 and abs(ly - py) < 12 for px0, px1, py in placed):
                    ly -= 12
            placed.append((lx - half, lx + half, ly))
            body.append(f'<text x="{_n(lx)}" y="{_n(ly)}" class="dl sm" text-anchor="middle">{_esc(label)}</text>')
        body.append("</g>")
        body.append(f'<text x="{_n(cx)}" y="{_n(y0 + 17)}" class="ax" text-anchor="middle">{_esc(_fit(cat, slot - 6))}</text>')
    body.append(f'<line x1="{_n(left)}" x2="{_n(left + plot_w)}" y1="{_n(y0)}" y2="{_n(y0)}" class="axis"/>')
    headers = list(table_headers) if table_headers else ["Category"] + [s["name"] for s in series]
    if table_rows is None:
        table_rows = []
        for i, cat in enumerate(categories):
            name = category_names[i] if category_names and i < len(category_names) else cat
            table_rows.append([name] + [value_fmt(s["values"][i] if i < len(s["values"]) else None) for s in series])
    return Chart(_svg(width, height, "".join(body), aria or table_caption),
                 _table(headers, table_rows, table_caption, numeric=range(1, len(headers))))


# ---------------------------------------------------------------- line with points

def line_chart(x_labels: Sequence[str], series: Sequence[dict], *, x_tips: Optional[Sequence[str]] = None,
               value_fmt: Callable[[Any], str] = fmt_pct, is_rate: bool = True, y_max: Optional[float] = None,
               vline: Optional[dict] = None, width: int = 680, height: int = 280, aria: str = "",
               table_caption: str = "", end_labels: bool = True, connect_nulls: bool = True,
               table_headers: Optional[Sequence[str]] = None) -> Chart:
    """series: [{"name", "values" (None allowed), "color" token, "dashed" bool}].
    vline: {"pos": fraction 0..1 across the plot, "label": str}. One tooltip per x lists every series."""
    n = len(x_labels)
    allv = [float(v) for s in series for v in s["values"] if v is not None]
    vmax = max(allv + [0.0])
    ticks = _ticks(y_max if y_max is not None else vmax, is_rate)
    top = ticks[-1] if ticks[-1] > 0 else 1.0
    tick_labels = [value_fmt(t) for t in ticks]
    left = max(len(t) for t in tick_labels) * CHAR_W + 12
    label_room = 0
    do_end = end_labels and len(series) <= 4
    if do_end:
        label_room = max(len(s["name"]) for s in series) * CHAR_W + 14
    right = 14 + label_room
    plot_w = width - left - right
    legend_svg, legend_h = ("", 0)
    if len(series) >= 2:
        legend_svg, legend_h = _legend([(s["name"], s.get("color", "s1"), bool(s.get("dashed"))) for s in series], left, 10, plot_w, "line")
    pad_top = legend_h + (26 if vline and vline.get("label") else 14)  # room for the marker label under the legend
    bottom = 28
    plot_h = height - pad_top - bottom
    y0 = pad_top + plot_h
    xs = [left + (plot_w * i / (n - 1) if n > 1 else plot_w / 2) for i in range(n)]
    slot = plot_w / (n - 1) if n > 1 else plot_w
    body = [legend_svg]
    for t, lab in zip(ticks, tick_labels):
        y = y0 - (t / top) * plot_h
        body.append(f'<line x1="{_n(left)}" x2="{_n(left + plot_w)}" y1="{_n(y)}" y2="{_n(y)}" class="grid"/>')
        body.append(f'<text x="{_n(left - 6)}" y="{_n(y + 4)}" class="ax" text-anchor="end">{_esc(lab)}</text>')
    body.append(f'<line x1="{_n(left)}" x2="{_n(left + plot_w)}" y1="{_n(y0)}" y2="{_n(y0)}" class="axis"/>')
    if n:
        max_lab = max(len(str(x)) for x in x_labels)
        every = max(1, math.ceil((max_lab * CHAR_W + 10) / slot)) if n > 1 else 1
        for i, lab in enumerate(x_labels):
            if i % every == 0 or i == n - 1 and (n - 1) % every >= every / 2:
                anchor = "middle"
                body.append(f'<text x="{_n(xs[i])}" y="{_n(y0 + 17)}" class="ax" text-anchor="{anchor}">{_esc(lab)}</text>')
    if vline and vline.get("pos") is not None:
        vx = left + max(0.0, min(1.0, float(vline["pos"]))) * plot_w
        body.append(f'<line x1="{_n(vx)}" x2="{_n(vx)}" y1="{_n(pad_top - 4)}" y2="{_n(y0)}" class="vmark"/>')
        lab = vline.get("label") or ""
        if lab:
            anchor = "start" if vx < left + plot_w * 0.7 else "end"
            tx = vx + 5 if anchor == "start" else vx - 5
            body.append(f'<text x="{_n(tx)}" y="{_n(pad_top - 6)}" class="ax vlab" text-anchor="{anchor}">{_esc(lab)}</text>')
    used_label_y: list[float] = []
    r = 4 if n <= 30 else 3
    for s in series:
        token = s.get("color", "s1")
        pts = [(xs[i], y0 - (float(v) / top) * plot_h) for i, v in enumerate(s["values"]) if v is not None]
        if not pts:
            continue
        dash = ' stroke-dasharray="6 5"' if s.get("dashed") else ""
        if connect_nulls:
            path = "M" + "L".join(f"{_n(px)},{_n(py)}" for px, py in pts)
        else:
            segs, seg = [], []
            for i, v in enumerate(s["values"]):
                if v is None:
                    if seg:
                        segs.append(seg)
                    seg = []
                else:
                    seg.append((xs[i], y0 - (float(v) / top) * plot_h))
            if seg:
                segs.append(seg)
            path = "".join("M" + "L".join(f"{_n(px)},{_n(py)}" for px, py in sg) for sg in segs)
        # solid lines carry pathLength="1" so the page can draw them in once with a dash offset; a dashed
        # line keeps its user-unit dash pattern and fades in instead
        kind = "dashed" if s.get("dashed") else "solid"
        plen = "" if s.get("dashed") else ' pathLength="1"'
        body.append(f'<path d="{path}" class="line {kind} stroke-{token}"{dash}{plen}/>')
        for px, py in pts:
            body.append(f'<circle cx="{_n(px)}" cy="{_n(py)}" r="{r}" class="pt fill-{token}"/>')
        if do_end:
            lx, ly = pts[-1]
            if all(abs(ly - u) >= 12 for u in used_label_y):
                used_label_y.append(ly)
                body.append(f'<text x="{_n(lx + 8)}" y="{_n(ly + 4)}" class="dl">{_esc(s["name"])}</text>')
    for i in range(n):
        title = x_tips[i] if x_tips and i < len(x_tips) else x_labels[i]
        rows = [(s["name"], value_fmt(s["values"][i] if i < len(s["values"]) else None), s.get("color", "s1")) for s in series]
        t = tip(title, rows)
        x0 = xs[i] - slot / 2
        body.append(f'<rect x="{_n(max(left, x0))}" y="{_n(pad_top)}" width="{_n(slot if n > 1 else plot_w)}" height="{_n(plot_h)}" '
                    f'class="hitarea col" tabindex="0" data-x="{_n(xs[i])}" data-tip="{_tipattr(t)}"/>')
    body.append(f'<line x1="{_n(left)}" x2="{_n(left)}" y1="{_n(pad_top)}" y2="{_n(y0)}" class="xhair" style="visibility:hidden"/>')
    headers = list(table_headers) if table_headers else ["Period"] + [s["name"] for s in series]
    rows = []
    for i in range(n):
        rows.append([x_tips[i] if x_tips and i < len(x_tips) else x_labels[i]] + [value_fmt(s["values"][i] if i < len(s["values"]) else None) for s in series])
    return Chart(_svg(width, height, "".join(body), aria or table_caption),
                 _table(headers, rows, table_caption, numeric=range(1, len(headers))))


# ---------------------------------------------------------------- small multiples

def small_multiples(panels: Sequence[dict], categories: Sequence[str], colors: Sequence[str], *,
                    value_fmt: Callable[[Any], str] = fmt_pct, is_rate: bool = True, y_max: Optional[float] = None,
                    cols: int = 4, panel_w: int = 150, panel_h: int = 132, aria: str = "", table_caption: str = "",
                    table_headers: Optional[Sequence[str]] = None, table_rows: Optional[Sequence[Sequence[Any]]] = None) -> Chart:
    """panels: [{"title", "values", "labels" (optional direct labels), "tip" (optional)}]. Shared y scale, one legend."""
    n = len(panels)
    cols = max(1, min(cols, max(n, 1)))
    rows_n = max(1, math.ceil(n / cols))
    allv = [float(v) for p in panels for v in p["values"] if v is not None]
    top = 1.0 if is_rate else (_ticks(y_max if y_max is not None else max(allv + [0.0]))[-1] or 1.0)
    width = cols * panel_w + 16
    legend_svg, legend_h = ("", 0)
    if len(categories) >= 2:
        legend_svg, legend_h = _legend([(c, colors[i % len(colors)], False) for i, c in enumerate(categories)], 8, 12, width - 16, "rect")
    header_h = legend_h + 4
    height = header_h + rows_n * panel_h + 6
    body = [legend_svg]
    nb = max(len(categories), 1)
    for k, p in enumerate(panels):
        px = 8 + (k % cols) * panel_w
        py = header_h + (k // cols) * panel_h
        title = _fit(p.get("title", ""), panel_w - 12)
        body.append(f'<text x="{_n(px + 6)}" y="{_n(py + 14)}" class="pt-title">{_esc(title)}</text>')
        plot_top = py + 34
        base = py + panel_h - 22
        plot_h = base - plot_top
        inner_w = panel_w - 24
        slot = inner_w / nb
        bw = min(BAR_MAX, slot * 0.6)
        body.append(f'<line x1="{_n(px + 12)}" x2="{_n(px + 12 + inner_w)}" y1="{_n(base)}" y2="{_n(base)}" class="axis"/>')
        for i, cat in enumerate(categories):
            v = p["values"][i] if i < len(p["values"]) else None
            cx = px + 12 + slot * (i + 0.5)
            h = 0.0 if v is None else (float(v) / top) * plot_h
            y = base - h
            token = colors[i % len(colors)]
            lab = p.get("labels", [None] * nb)[i] if i < len(p.get("labels", [])) else None
            t = p.get("tips", [None] * nb)[i] if i < len(p.get("tips", [])) else None
            t = t or tip(f"{p.get('title', '')}: {cat}", [(cat, value_fmt(v), token)])
            body.append(f'<g class="hit" tabindex="0" data-tip="{_tipattr(t)}">')
            body.append(f'<rect x="{_n(cx - slot / 2)}" y="{_n(plot_top - 14)}" width="{_n(slot)}" height="{_n(plot_h + 14)}" class="hitarea"/>')
            if h > 0:
                body.append(f'<path d="{_vbar(cx - bw / 2, y, bw, h)}" class="mark fill-{token} {token}"/>')
            if lab:
                body.append(f'<text x="{_n(cx)}" y="{_n(y - 5)}" class="dl sm" text-anchor="middle">{_esc(lab)}</text>')
            body.append("</g>")
            body.append(f'<text x="{_n(cx)}" y="{_n(base + 15)}" class="ax" text-anchor="middle">{_esc(_fit(cat, slot - 4))}</text>')
    headers = list(table_headers) if table_headers else ["Panel"] + list(categories)
    if table_rows is None:
        table_rows = [[p.get("title", "")] + [value_fmt(p["values"][i] if i < len(p["values"]) else None) for i in range(nb)] for p in panels]
    return Chart(_svg(width, height, "".join(body), aria or table_caption),
                 _table(headers, table_rows, table_caption, numeric=range(1, len(headers))))


# ---------------------------------------------------------------- heatmap cells

def heatmap_cells(cells: Sequence[dict], *, max_level: int = 3, size: int = 46, gap: int = 6, aria: str = "",
                  table_caption: str = "") -> Chart:
    """One row of level cells. cells: [{"code", "name", "level" (None = not assessed), "decayed", "firstAt", "lastAt", "tip"}].
    Fill is the sequential level ramp (lv0..lv3); the number is always printed inside so the value never depends on colour."""
    n = len(cells)
    width = n * size + max(n - 1, 0) * gap + 2
    height = size + 18
    body = []
    for i, c in enumerate(cells):
        x = 1 + i * (size + gap)
        level = c.get("level")
        if level is None:
            token, num = "none", "–"
        else:
            lv = max(0, min(int(level), max_level))
            token, num = f"lv{lv}", str(int(level))
        decayed = bool(c.get("decayed"))
        rows = [("level", f"{num} of {max_level}" if level is not None else "not assessed", token)]
        if decayed:
            rows.append(("decayed", "yes: last evidence older than the decay window", ""))
        if c.get("firstAt"):
            rows.append(("first evidence", fmt_date(c.get("firstAt")), ""))
        if c.get("lastAt"):
            rows.append(("last evidence", fmt_date(c.get("lastAt")), ""))
        t = c.get("tip") or tip(f"{c.get('code', '')} {c.get('name', '')}".strip(), rows)
        body.append(f'<g class="hit" tabindex="0" data-tip="{_tipattr(t)}">')
        body.append(f'<rect x="{_n(x)}" y="1" width="{_n(size)}" height="{_n(size)}" rx="4" class="cell fill-{token}"/>')
        body.append(f'<text x="{_n(x + size / 2)}" y="{_n(1 + size / 2 + 6)}" class="cell-num ink-{token}" text-anchor="middle">{_esc(num)}</text>')
        if decayed:
            body.append(f'<path d="M{_n(x + size - 12)},{_n(3)}h9v9z" class="decay"/>')
        body.append("</g>")
        body.append(f'<text x="{_n(x + size / 2)}" y="{_n(size + 14)}" class="ax code" text-anchor="middle">{_esc(c.get("code", ""))}</text>')
    rows = [(c.get("code", ""), c.get("name", ""), "not assessed" if c.get("level") is None else str(c.get("level")),
             "yes" if c.get("decayed") else "no", fmt_date(c.get("firstAt")), fmt_date(c.get("lastAt"))) for c in cells]
    return Chart(_svg(width, height, "".join(body), aria or table_caption),
                 _table(["Code", "Element", "Level", "Decayed", "First evidence", "Last evidence"], rows, table_caption, numeric=[2]))


# ---------------------------------------------------------------- sparkline

def sparkline(values: Sequence[Optional[float]], *, labels: Optional[Sequence[str]] = None, width: int = 140, height: int = 36,
              value_fmt: Callable[[Any], str] = fmt_pct, is_rate: bool = True, aria: str = "", table_caption: str = "") -> Chart:
    """12-point style sparkline: de-emphasis stroke, current period marked in the accent."""
    n = len(values)
    pts_all = [None if v is None else float(v) for v in values]
    defined = [(i, v) for i, v in enumerate(pts_all) if v is not None]
    top = 1.0 if is_rate else max([v for _, v in defined] + [1.0])
    pad = 5
    xs = [pad + ((width - 2 * pad) * i / (n - 1) if n > 1 else (width - 2 * pad) / 2) for i in range(n)]
    ys = {i: height - pad - (v / top) * (height - 2 * pad) for i, v in defined}
    body = []
    if defined:
        path = "M" + "L".join(f"{_n(xs[i])},{_n(ys[i])}" for i, _ in defined)
        body.append(f'<path d="{path}" class="spark"/>')
        li, _ = defined[-1]
        body.append(f'<circle cx="{_n(xs[li])}" cy="{_n(ys[li])}" r="3.5" class="pt fill-s1"/>')
    slot = (width - 2 * pad) / (n - 1) if n > 1 else width
    for i in range(n):
        lab = labels[i] if labels and i < len(labels) else str(i + 1)
        t = tip(lab, [("value", value_fmt(pts_all[i]), "s1")])
        body.append(f'<rect x="{_n(max(0, xs[i] - slot / 2))}" y="0" width="{_n(slot)}" height="{_n(height)}" class="hitarea" tabindex="0" data-tip="{_tipattr(t)}"/>')
    rows = [(labels[i] if labels and i < len(labels) else str(i + 1), value_fmt(pts_all[i])) for i in range(n)]
    return Chart(_svg(width, height, "".join(body), aria or table_caption),
                 _table(["Period", "Value"], rows, table_caption, numeric=[1]))


# ---------------------------------------------------------------- stat tile

def stat_tile(label: str, value: str, *, sub: str = "", delta: Optional[str] = None, delta_good: Optional[bool] = None,
              spark: Optional[Chart] = None, note: str = "", tile_id: str = "") -> str:
    """Stat tile contract: label, value (proportional figures), optional delta, optional sparkline, optional note."""
    parts = [f'<div class="tile"{(" id=" + chr(34) + _esc(tile_id) + chr(34)) if tile_id else ""}>']
    parts.append(f'<div class="tile-label">{_esc(label)}</div>')
    parts.append(f'<div class="tile-value">{_esc(value)}</div>')
    if delta:
        cls = "delta-good" if delta_good else ("delta-bad" if delta_good is False else "delta-neutral")
        parts.append(f'<div class="tile-delta {cls}">{_esc(delta)}</div>')
    if sub:
        parts.append(f'<div class="tile-sub">{_esc(sub)}</div>')
    if spark is not None:
        parts.append(f'<div class="tile-spark">{spark.svg}</div><details class="tile-table"><summary>Table</summary>{spark.table}</details>')
    if note:
        parts.append(f'<div class="tile-note">{_esc(note)}</div>')
    parts.append("</div>")
    return "".join(parts)
