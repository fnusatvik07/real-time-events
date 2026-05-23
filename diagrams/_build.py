"""Build all workshop diagrams from a single style guide.

Run:
    python _build.py

This regenerates the 14 .drawio files in this directory with consistent
typography, colors, spacing, and visual hierarchy.

Design decisions:
  - Title: 20pt bold, centered, single line at top
  - Headers in boxes: 14pt bold
  - Body in boxes:   12pt
  - Wire-format / code: 11pt monospace
  - Footer callout (key takeaway): yellow, 13pt
  - Color palette is semantic:
      client/browser      -> blue
      your server         -> green
      external / 3rd-party -> red
      AI provider / LLM   -> purple
      infrastructure      -> orange
      callout / note      -> yellow
"""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).parent

# ---------------------------------------------------------------------------
# Style palette
# ---------------------------------------------------------------------------
PALETTE = {
    "client":   ("#dae8fc", "#6c8ebf"),  # blue
    "server":   ("#d5e8d4", "#82b366"),  # green
    "third":    ("#f8cecc", "#b85450"),  # red
    "llm":      ("#e1d5e7", "#9673a6"),  # purple
    "infra":    ("#ffe6cc", "#d79b00"),  # orange
    "note":     ("#fff2cc", "#d6b656"),  # yellow
    "neutral":  ("#f5f5f5", "#666666"),  # grey
    "white":    ("#ffffff", "#999999"),
}


# ---------------------------------------------------------------------------
# Cell builders - each returns one <mxCell> XML string with a unique id
# ---------------------------------------------------------------------------
_uid = 0
def _next_id(prefix: str = "n") -> str:
    global _uid
    _uid += 1
    return f"{prefix}{_uid}"


def title(text: str, y: int = 24, page_w: int = 1000) -> str:
    return (
        f'<mxCell id="{_next_id("title")}" value="{esc(text)}" '
        f'style="text;html=1;align=center;verticalAlign=middle;whiteSpace=wrap;fontSize=20;fontStyle=1;" '
        f'vertex="1" parent="1">'
        f'<mxGeometry x="40" y="{y}" width="{page_w - 80}" height="34" as="geometry"/></mxCell>'
    )


def subtitle(text: str, y: int = 60, page_w: int = 1000) -> str:
    return (
        f'<mxCell id="{_next_id("sub")}" value="{esc(text)}" '
        f'style="text;html=1;align=center;whiteSpace=wrap;fontSize=13;fontStyle=2;fontColor=#555;" '
        f'vertex="1" parent="1">'
        f'<mxGeometry x="40" y="{y}" width="{page_w - 80}" height="22" as="geometry"/></mxCell>'
    )


def box(x: int, y: int, w: int, h: int, text: str,
        role: str = "white", *, bold: bool = False, fontsize: int = 13,
        align: str = "center", radius: bool = True, dashed: bool = False) -> tuple[str, str]:
    """Returns (cell_xml, cell_id) so edges can reference it."""
    fill, stroke = PALETTE[role]
    cid = _next_id("box")
    rounded = "1" if radius else "0"
    style = (
        f"rounded={rounded};whiteSpace=wrap;html=1;"
        f"fillColor={fill};strokeColor={stroke};"
        f"fontSize={fontsize};fontStyle={'1' if bold else '0'};"
        f"align={align};verticalAlign=middle;"
        f"strokeWidth=1.5;"
        f"{'dashed=1;' if dashed else ''}"
    )
    cell = (
        f'<mxCell id="{cid}" value="{esc(text)}" style="{style}" '
        f'vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
    )
    return cell, cid


def code(x: int, y: int, w: int, h: int, text: str, *,
         role: str = "white") -> tuple[str, str]:
    """Monospace box for showing wire format / code."""
    fill, stroke = PALETTE[role]
    cid = _next_id("code")
    style = (
        f"rounded=1;whiteSpace=wrap;html=1;"
        f"fillColor={fill};strokeColor={stroke};"
        f"fontSize=11;fontFamily=Courier New;fontStyle=0;"
        f"align=left;verticalAlign=middle;spacingLeft=8;spacingTop=4;spacingBottom=4;"
        f"strokeWidth=1.5;"
    )
    cell = (
        f'<mxCell id="{cid}" value="{esc(text)}" style="{style}" '
        f'vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
    )
    return cell, cid


def lane(x: int, y: int, w: int, h: int, label: str, role: str) -> tuple[str, str]:
    """A vertical swimlane (for sequence diagrams)."""
    fill, stroke = PALETTE[role]
    cid = _next_id("lane")
    style = (
        f"shape=swimlane;horizontal=1;startSize=34;"
        f"fillColor={fill};strokeColor={stroke};"
        f"fontSize=14;fontStyle=1;"
        f"swimlaneFillColor=#ffffff;rounded=0;"
        f"strokeWidth=2;"
    )
    cell = (
        f'<mxCell id="{cid}" value="{esc(label)}" style="{style}" '
        f'vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
    )
    return cell, cid


def msg_box(x: int, y: int, w: int, h: int, text: str, role: str = "white",
            *, mono: bool = False, italic: bool = False) -> str:
    """A small message box used inside swimlane sequence diagrams."""
    fill, stroke = PALETTE[role]
    font_family = ";fontFamily=Courier New" if mono else ""
    style = (
        f"rounded=1;whiteSpace=wrap;html=1;"
        f"fillColor={fill};strokeColor={stroke};"
        f"fontSize=11;fontStyle={'2' if italic else '0'}{font_family};"
        f"align=center;verticalAlign=middle;spacingLeft=6;spacingRight=6;"
    )
    cid = _next_id("msg")
    return (
        f'<mxCell id="{cid}" value="{esc(text)}" style="{style}" '
        f'vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
    )


def callout(x: int, y: int, w: int, h: int, text: str,
            role: str = "note", fontsize: int = 12, align: str = "left") -> str:
    """Yellow takeaway callout."""
    fill, stroke = PALETTE[role]
    cid = _next_id("note")
    style = (
        f"rounded=1;whiteSpace=wrap;html=1;"
        f"fillColor={fill};strokeColor={stroke};"
        f"fontSize={fontsize};align={align};verticalAlign=middle;"
        f"spacingLeft=14;spacingRight=14;spacingTop=8;spacingBottom=8;"
        f"strokeWidth=1.5;"
    )
    return (
        f'<mxCell id="{cid}" value="{esc(text)}" style="{style}" '
        f'vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
    )


def caption(x: int, y: int, w: int, h: int, text: str, *,
            italic: bool = True, fontsize: int = 12, align: str = "center") -> str:
    cid = _next_id("cap")
    style = (
        f"text;html=1;align={align};whiteSpace=wrap;"
        f"fontSize={fontsize};fontStyle={'2' if italic else '0'};fontColor=#555;"
    )
    return (
        f'<mxCell id="{cid}" value="{esc(text)}" style="{style}" '
        f'vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
    )


def arrow(src: str, dst: str, label: str = "", *,
          dashed: bool = False, color: str = "#333", thick: bool = False,
          ortho: bool = False, both: bool = False) -> str:
    """Edge between two existing cells (by id).

    both=True   → arrow heads on both ends (use for bidirectional channels)
    ortho=True  → orthogonal routing (right-angle paths, good for trees)
    """
    cid = _next_id("e")
    edge_style = "orthogonalEdgeStyle" if ortho else "none"
    start_arrow = "classic" if both else "none"
    style = (
        f"endArrow=classic;startArrow={start_arrow};html=1;rounded=0;"
        f"strokeColor={color};"
        f"strokeWidth={'2.5' if thick else '1.6'};"
        f"fontSize=11;"
        f"{'dashed=1;' if dashed else ''}"
        f"edgeStyle={edge_style};"
    )
    return (
        f'<mxCell id="{cid}" value="{esc(label)}" style="{style}" edge="1" '
        f'parent="1" source="{src}" target="{dst}">'
        f'<mxGeometry relative="1" as="geometry"/></mxCell>'
    )


def hline(x: int, y: int, w: int, color: str = "#888") -> str:
    """Horizontal divider line."""
    cid = _next_id("hr")
    style = f"endArrow=none;html=1;strokeColor={color};strokeWidth=1;dashed=1;"
    return (
        f'<mxCell id="{cid}" style="{style}" edge="1" parent="1">'
        f'<mxGeometry relative="1" as="geometry">'
        f'<mxPoint x="{x}" y="{y}" as="sourcePoint"/>'
        f'<mxPoint x="{x + w}" y="{y}" as="targetPoint"/>'
        f'</mxGeometry></mxCell>'
    )


def section_label(x: int, y: int, w: int, text: str) -> str:
    """Small header within a diagram (e.g. 'Phase 1')."""
    cid = _next_id("sl")
    style = (
        "text;html=1;align=center;whiteSpace=wrap;"
        "fontSize=12;fontStyle=1;fontColor=#666;"
    )
    return (
        f'<mxCell id="{cid}" value="{esc(text)}" style="{style}" '
        f'vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="20" as="geometry"/></mxCell>'
    )


def esc(text: str) -> str:
    """Escape for XML attribute, with HTML breaks for newlines."""
    if text is None:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("\n", "&#10;")
    )


# ---------------------------------------------------------------------------
# Page wrapper
# ---------------------------------------------------------------------------
def render(name: str, cells: list[str], width: int = 1000, height: int = 640) -> str:
    return dedent(f"""\
        <mxfile host="app.diagrams.net">
          <diagram name="{esc(name)}" id="{name}">
            <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1"
                          tooltips="1" connect="1" arrows="1" fold="1" page="1"
                          pageScale="1" pageWidth="{width}" pageHeight="{height}"
                          math="0" shadow="0">
              <root>
                <mxCell id="0"/>
                <mxCell id="1" parent="0"/>
                {chr(10).join(cells)}
              </root>
            </mxGraphModel>
          </diagram>
        </mxfile>
    """)


# ---------------------------------------------------------------------------
# Per-diagram builders
# ---------------------------------------------------------------------------
def d01_http_basic() -> tuple[str, str]:
    global _uid
    _uid = 0
    cells = []
    PAGE_W = 1000
    cells.append(title("HTTP - Request / Response, then the conversation ends", page_w=PAGE_W))
    cells.append(subtitle("Stateless. Client always initiates. This is the limitation the next 4 patterns work around.", page_w=PAGE_W))

    c_box, c_id = box(100, 130, 220, 70, "CLIENT\n(browser / app / curl)", role="client", bold=True, fontsize=14)
    s_box, s_id = box(680, 130, 220, 70, "SERVER", role="server", bold=True, fontsize=14)
    cells += [c_box, s_box]

    # Two arrows with their own labels
    req = (
        '<mxCell id="erq" value="① HTTP Request&#10;GET /api/users HTTP/1.1" '
        'style="endArrow=classic;html=1;strokeColor=#333;strokeWidth=2;fontSize=12;" '
        'edge="1" parent="1" source="' + c_id + '" target="' + s_id + '">'
        '<mxGeometry y="-20" relative="1" as="geometry"><mxPoint as="offset"/></mxGeometry></mxCell>'
    )
    resp = (
        '<mxCell id="ersp" value="② HTTP Response&#10;200 OK + body" '
        'style="endArrow=classic;html=1;strokeColor=#333;strokeWidth=2;fontSize=12;dashed=1;" '
        'edge="1" parent="1" source="' + s_id + '" target="' + c_id + '">'
        '<mxGeometry y="20" relative="1" as="geometry"><mxPoint as="offset"/></mxGeometry></mxCell>'
    )
    cells += [req, resp]

    cells.append(caption(100, 240, 800, 22,
        "③ Connection closes (or kept-alive for the NEXT request, but each request is still independent)"))

    cells.append(callout(160, 350, 680, 150,
        "Key idea\n\n"
        "• Server cannot speak unless asked.\n"
        "• Each request is independent - server has no memory between them.\n"
        "• Every other pattern in this workshop exists to escape this limitation."))

    return render("01_http_basic", cells, PAGE_W, 540), "01_http_basic.drawio"


def d02_short_polling() -> tuple[str, str]:
    global _uid
    _uid = 0
    cells = []
    PAGE_W = 1000
    cells.append(title("Short Polling - Client keeps asking on a timer", page_w=PAGE_W))
    cells.append(subtitle("Average latency = poll interval / 2.  Cost = N redundant requests per minute, even when nothing changes.", page_w=PAGE_W))

    lane_top = 110
    msg_top = 170
    row_h = 70  # 28 (req) + gap + 24 (resp) + gap between rows

    msgs = [
        ("t = 0s",  "GET /messages",            "200  []  (nothing yet)",        False),
        ("t = 2s",  "GET /messages   (wasted)", "200  []  (still nothing)",       True),
        ("t = 4s",  "GET /messages   (wasted)", "200  []",                        True),
        ("t = 6s",  "GET /messages",            "200  [msg1]  ← finally!",        False),
        ("t = 8s",  "GET /messages   (wasted)", "200  []  (nothing new)",         True),
    ]
    msg_area_h = row_h * len(msgs) + 10
    lane_h = (msg_top - lane_top) + msg_area_h + 20

    c_lane, _ = lane(120, lane_top, 160, lane_h, "CLIENT", "client")
    s_lane, _ = lane(720, lane_top, 160, lane_h, "SERVER", "server")
    cells += [c_lane, s_lane]

    y = msg_top
    for tlabel, req, resp, wasted in msgs:
        # Time caption: center on the whole row (req + resp = 28 + 24 = 52, plus 2px gap)
        row_center_y = y + 26  # center of the 54-tall row
        cells.append(caption(40, row_center_y - 8, 80, 16, tlabel, italic=False, fontsize=11, align="right"))
        role = "third" if wasted else "white"
        cells.append(msg_box(290, y, 410, 28, req, role=role, mono=True))
        resp_role = "third" if wasted else ("note" if "finally" in resp else "white")
        cells.append(msg_box(290, y + 30, 410, 24, resp, role=resp_role, italic=True))
        y += row_h

    callout_y = lane_top + lane_h + 30
    cells.append(callout(100, callout_y, 800, 80,
        "Waste ratio\n\n"
        "Red rows returned nothing - 60% of these polls were pure overhead.  "
        "Lower the interval → more waste.  Raise it → higher latency.  You can't win both."))
    PAGE_H = callout_y + 100

    return render("02_short_polling", cells, PAGE_W, PAGE_H), "02_short_polling.drawio"


def d03_long_polling() -> tuple[str, str]:
    global _uid
    _uid = 0
    cells = []
    PAGE_W = 1000
    cells.append(title("Long Polling - Server holds the request until data is ready", page_w=PAGE_W))
    cells.append(subtitle("One in-flight request at a time.  No fixed-interval staleness.  Server needs async I/O.", page_w=PAGE_W))

    lane_top = 110

    # Build the sequence as (time_label, msg_text, height, role, mono, italic)
    # time_label is None for continuation rows
    rows = [
        ("t = 0s",  "GET /messages?wait=30",                                      28, "white",  True,  False),
        (None,      "Server holds the request open ...  (no data yet)",           36, "note",   False, True),
        ("t = 8s",  "Message arrives on the server - flush it down",              28, "server", False, True),
        (None,      "200  [msg1]   ← returned immediately",                       28, "white",  True,  False),
        ("t = 8s+", "GET /messages?wait=30   (client reconnects)",                28, "white",  True,  False),
        (None,      "Server holds again ... 30s passes with no data",             36, "note",   False, True),
        ("t = 38s", "204 No Content (timeout)  - client reconnects",              28, "white",  True,  False),
    ]
    gap = 14
    msg_top = 170
    total_msg_h = sum(h for _, _, h, *_ in rows) + gap * (len(rows) - 1)
    lane_h = (msg_top - lane_top) + total_msg_h + 30

    c_lane, _ = lane(120, lane_top, 160, lane_h, "CLIENT", "client")
    s_lane, _ = lane(720, lane_top, 160, lane_h, "SERVER", "server")
    cells += [c_lane, s_lane]

    y = msg_top
    for tlabel, text, h, role, mono, italic in rows:
        if tlabel:
            cells.append(caption(40, y + (h - 16) // 2, 80, 16, tlabel,
                                 italic=False, fontsize=11, align="right"))
        cells.append(msg_box(290, y, 410, h, text, role=role, mono=mono, italic=italic))
        y += h + gap

    callout_y = lane_top + lane_h + 30
    cells.append(callout(100, callout_y, 800, 100,
        "Trade-offs vs short polling\n\n"
        "✓  Sub-second latency for events.   ✓  Far fewer requests per minute.\n"
        "✗  Server holds many open connections - must use async I/O (asyncio, Node, Go).\n"
        "✗  Set server timeout BELOW your load-balancer's timeout."))
    PAGE_H = callout_y + 130

    return render("03_long_polling", cells, PAGE_W, PAGE_H), "03_long_polling.drawio"


def d04_polling_comparison() -> tuple[str, str]:
    global _uid
    _uid = 0
    cells = []
    PAGE_W = 1100
    PAGE_H = 580
    cells.append(title("Short vs Long Polling - Side by Side", page_w=PAGE_W))
    cells.append(subtitle("Same 30-second window. Short polling burns 15 requests. Long polling uses 2.", page_w=PAGE_W))

    # Two cards
    sh_box, _ = box(80,  120, 470, 120,
        "SHORT POLLING\n\n"
        "Many short requests on a fixed timer.\n"
        "Avg latency  ≈  interval / 2\n"
        "Server work  ≈  N requests / minute (even when idle)",
        role="third", bold=False, fontsize=12, align="center")
    lo_box, _ = box(560, 120, 470, 120,
        "LONG POLLING\n\n"
        "Few requests, each held until data arrives.\n"
        "Avg latency  ≈  near-zero on event\n"
        "Server work  ≈  one held connection per client",
        role="server", bold=False, fontsize=12, align="center")
    cells += [sh_box, lo_box]

    # Timeline visualisations
    cells.append(caption(80,  260, 470, 18, "Timeline (30s) - R = full HTTP round-trip", fontsize=11))
    cells.append(caption(560, 260, 470, 18, "Timeline (30s) - = = held connection, R = data flushed", fontsize=11))

    # Use monospace strings to "draw" the timelines
    sh_timeline, _ = code(80, 285, 470, 50,
        "R|R|R|R|R|R|R|R|R|R|R|R|R|R|R|\n"
        "↑ 15 requests, 12 returned nothing")
    lo_timeline, _ = code(560, 285, 470, 50,
        "============R||============R||\n"
        "↑ 2 requests, both delivered data")
    cells += [sh_timeline, lo_timeline]

    cells.append(callout(80, 380, 950, 140,
        "When to use which\n\n"
        "Short polling  →  rare events OK to be a few seconds stale, simple to ship, any backend supports it.\n\n"
        "Long polling   →  lower latency without holding 100K WebSockets, async server, no aggressive proxy timeouts.\n\n"
        "Need <100ms latency or two-way?  Skip both. Use SSE or WebSockets."))

    return render("04_polling_comparison", cells, PAGE_W, PAGE_H), "04_polling_comparison.drawio"


def d05_webhook_basic() -> tuple[str, str]:
    global _uid
    _uid = 0
    cells = []
    PAGE_W = 1100
    PAGE_H = 620
    cells.append(title("Webhooks - Inversion. The third party calls YOU.", page_w=PAGE_W))
    cells.append(subtitle("Zero idle traffic. Server only does work when events fire. You expose a URL; they POST to it.", page_w=PAGE_W))

    # Step list above the diagram
    cells.append(section_label(80, 120, 940, "Lifecycle of a webhook"))
    cells.append(caption(80, 145, 940, 18,
        "① SETUP (once)  -  you register your URL in their dashboard", fontsize=12, align="center", italic=False))
    cells.append(caption(80, 165, 940, 18,
        "② EVENT HAPPENS  -  customer pays $50 on Stripe", fontsize=12, align="center", italic=False))

    # Two big boxes side by side
    third_box, third_id = box(120, 240, 280, 100,
        "THIRD-PARTY SERVICE\n(Stripe / GitHub / Slack)",
        role="third", bold=True, fontsize=14)
    you_box, you_id = box(700, 240, 280, 100,
        "YOUR SERVER\nhttps://you.com/webhooks/stripe",
        role="server", bold=True, fontsize=14)
    cells += [third_box, you_box]

    # ③ POST arrow with edge label above
    cells.append(arrow(third_id, you_id,
        "③ POST + signed body  (x-signature: ...)", thick=True))

    # ④ ACK arrow (dashed return) with edge label below
    ack = (
        '<mxCell id="ack_arrow" value="④ 200 OK (fast)" '
        'style="endArrow=classic;html=1;strokeWidth=1.6;fontSize=11;dashed=1;strokeColor=#888;edgeStyle=none;" '
        'edge="1" parent="1" source="' + you_id + '" target="' + third_id + '">'
        '<mxGeometry x="-1" y="40" relative="1" as="geometry"><mxPoint y="40" as="offset"/></mxGeometry></mxCell>'
    )
    cells.append(ack)

    cells.append(callout(120, 410, 860, 160,
        "Why it's good\n\n"
        "Zero idle cost. No requests until something happens.\n"
        "Push (not pull) - first-byte latency is near zero.\n\n"
        "The cost: you must verify signatures, dedup retries, and return 200 fast (see next two diagrams)."))

    return render("05_webhook_basic", cells, PAGE_W, PAGE_H), "05_webhook_basic.drawio"


def d06_webhook_retries() -> tuple[str, str]:
    global _uid
    _uid = 0
    cells = []
    PAGE_W = 1100
    cells.append(title("Webhooks - Retries and Idempotent Dedup", page_w=PAGE_W))
    cells.append(subtitle("Senders retry on errors and sometimes deliver twice. Your handler MUST be safe to call repeatedly.", page_w=PAGE_W))

    lane_top = 110
    msg_top = 170
    gap = 14
    rows = [
        ("① POST event evt_123  (signed)",                                                    28, "white",  True,  False),
        ("500 Internal Server Error  (your DB was down)",                                     28, "third",  False, True),
        ("Sender retries automatically with exponential backoff",                             24, "note",   False, True),
        ("② POST event evt_123 again",                                                        28, "white",  True,  False),
        ("Check Redis: SEEN evt_123?  No.\n→ mark seen, process event, return 200",          44, "server", False, True),
        ("200 OK",                                                                            28, "white",  True,  False),
        ("③ POST event evt_123 AGAIN (race / network blip)",                                  28, "white",  True,  False),
        ("Check Redis: SEEN evt_123?  YES.\n→ skip, still return 200",                       44, "note",   False, True),
        ("200 OK  (duplicate handled gracefully)",                                            28, "white",  True,  False),
    ]
    total_h = sum(h for _, h, *_ in rows) + gap * (len(rows) - 1)
    lane_h = (msg_top - lane_top) + total_h + 30

    cells.append(lane(100, lane_top, 200, lane_h, "SENDER (Stripe)", "third")[0])
    cells.append(lane(820, lane_top, 200, lane_h, "YOUR SERVER",     "server")[0])

    y = msg_top
    for text, h, role, mono, italic in rows:
        cells.append(msg_box(330, y, 480, h, text, role=role, mono=mono, italic=italic))
        y += h + gap

    callout_y = lane_top + lane_h + 30
    cells.append(callout(100, callout_y, 920, 100,
        "Three rules for webhook receivers\n\n"
        "1.  Return 2xx FAST.  Don't do the actual work in the handler - enqueue it.\n"
        "2.  Dedup by event id (Redis SETEX, DB unique index, etc.).\n"
        "3.  Verify the signature on EVERY request (next diagram)."))
    PAGE_H = callout_y + 130

    return render("06_webhook_retries", cells, PAGE_W, PAGE_H), "06_webhook_retries.drawio"


def d07_webhook_security() -> tuple[str, str]:
    global _uid
    _uid = 0
    cells = []
    PAGE_W = 1100
    PAGE_H = 620
    cells.append(title("Webhook Signature Verification - HMAC-SHA256", page_w=PAGE_W))
    cells.append(subtitle("Without this, anyone with your URL can POST a fake \"payment.succeeded\" event.", page_w=PAGE_W))

    sender_box, sender_id = box(100, 120, 260, 60, "SENDER", role="third", bold=True, fontsize=14)
    server_box, server_id = box(740, 120, 260, 60, "YOUR SERVER", role="server", bold=True, fontsize=14)
    cells += [sender_box, server_box]

    # Sender side computation
    s_calc, _ = code(60, 210, 340, 70,
        "sig = HMAC_SHA256(\n"
        "    secret,\n"
        "    timestamp + body\n"
        ")", role="white")
    cells.append(s_calc)

    # POST payload box
    post_box, _ = code(420, 210, 260, 100,
        "POST /webhooks/stripe\n"
        "Stripe-Signature:\n"
        "  t=1700000000,\n"
        "  v1=abc123def...\n\n"
        "{body}", role="white")
    cells.append(post_box)

    # Server side verification
    v_calc, _ = code(700, 210, 340, 100,
        "expected = HMAC_SHA256(\n"
        "    secret,\n"
        "    timestamp + body\n"
        ")\n"
        "hmac.compare_digest(expected, v1)", role="white")
    cells.append(v_calc)

    # Branches
    cells.append(box(700, 340, 165, 50, "✓  Match → trust body", role="server", fontsize=12)[0])
    cells.append(box(875, 340, 165, 50, "✗  Reject → 401",        role="third",  fontsize=12)[0])

    cells.append(callout(100, 430, 920, 170,
        "Three things that matter\n\n"
        "1.  Use a constant-time compare (`hmac.compare_digest`) - prevents timing attacks.\n"
        "2.  Sign the timestamp + body together, not just the body - prevents replay attacks.\n"
        "3.  Reject requests older than ~5 minutes by checking the timestamp."))

    return render("07_webhook_security", cells, PAGE_W, PAGE_H), "07_webhook_security.drawio"


def d08_sse_basic() -> tuple[str, str]:
    global _uid
    _uid = 0
    cells = []
    PAGE_W = 1100
    cells.append(title("Server-Sent Events - server pushes a stream over one HTTP connection", page_w=PAGE_W))
    cells.append(subtitle("Browser-native via EventSource.  Auto-reconnect.  Just text/event-stream over plain HTTP.", page_w=PAGE_W))

    lane_top = 110
    msg_top = 180
    gap = 14

    rows = [
        ("GET /stream  Accept: text/event-stream",                       28, "white",  True,  False),
        ("200 OK  (connection stays open)",                              28, "white",  False, True),
        ("data: hello",                                                  26, "server", True,  False),
        ("data: world",                                                  26, "server", True,  False),
        ("event: token\ndata: {\"text\":\"Hi\"}",                        42, "server", True,  False),
        (": keep-alive ping  (comment line, ignored by client)",         26, "note",   True,  False),
        ("event: done\ndata: complete",                                  42, "server", True,  False),
    ]
    total_h = sum(h for _, h, *_ in rows) + gap * (len(rows) - 1)
    lane_h = (msg_top - lane_top) + total_h + 30

    cells.append(lane(100, lane_top, 220, lane_h,
        "BROWSER\nnew EventSource('/stream')", "client")[0])
    cells.append(lane(800, lane_top, 220, lane_h,
        "SERVER\nContent-Type: text/event-stream", "server")[0])

    y = msg_top
    for text, h, role, mono, italic in rows:
        cells.append(msg_box(340, y, 440, h, text, role=role, mono=mono, italic=italic))
        y += h + gap

    callout_y = lane_top + lane_h + 30
    cells.append(callout(100, callout_y, 920, 90,
        "What the browser does for free\n"
        "• onmessage / addEventListener('token', e => ...)\n"
        "• auto-reconnect on dropped connection\n"
        "• sends Last-Event-ID header on reconnect → server resumes from there"))
    PAGE_H = callout_y + 120

    return render("08_sse_basic", cells, PAGE_W, PAGE_H), "08_sse_basic.drawio"


def d09_sse_reconnect() -> tuple[str, str]:
    global _uid
    _uid = 0
    cells = []
    PAGE_W = 1100
    cells.append(title("SSE Auto-Reconnect + Resume with Last-Event-ID", page_w=PAGE_W))
    cells.append(subtitle("Connection drops? Browser reconnects automatically and tells the server what it last saw.", page_w=PAGE_W))

    lane_top = 110
    msg_top = 170
    gap = 14
    rows = [
        ("GET /stream",                                                              26, "white",  True,  False),
        ("id: 1\ndata: msg-a",                                                       42, "server", True,  False),
        ("id: 2\ndata: msg-b",                                                       42, "server", True,  False),
        ("✗  CONNECTION DROPS  (network blip)",                                      28, "third",  False, True),
        ("Browser waits ~3 sec, then reconnects automatically",                      26, "note",   False, True),
        ("GET /stream\nLast-Event-ID: 2  ← browser tells server what it last saw",   42, "white",  True,  False),
        ("Server replays from buffer: events with id > 2",                           26, "note",   False, True),
        ("id: 3\ndata: msg-c",                                                       42, "server", True,  False),
        ("id: 4\ndata: msg-d",                                                       42, "server", True,  False),
    ]
    total_h = sum(h for _, h, *_ in rows) + gap * (len(rows) - 1)
    lane_h = (msg_top - lane_top) + total_h + 30

    cells.append(lane(100, lane_top, 180, lane_h, "BROWSER", "client")[0])
    cells.append(lane(820, lane_top, 180, lane_h, "SERVER",  "server")[0])

    y = msg_top
    for text, h, role, mono, italic in rows:
        cells.append(msg_box(300, y, 510, h, text, role=role, mono=mono, italic=italic))
        y += h + gap

    callout_y = lane_top + lane_h + 30
    cells.append(callout(100, callout_y, 920, 80,
        "The Last-Event-ID resume is built into the browser. You only need to:\n"
        "1.  Include `id:` lines in every event you send.\n"
        "2.  On reconnect, check the `Last-Event-ID` request header and replay newer events from a buffer or log."))
    PAGE_H = callout_y + 110

    return render("09_sse_reconnect", cells, PAGE_W, PAGE_H), "09_sse_reconnect.drawio"


def d10_websocket_handshake() -> tuple[str, str]:
    global _uid
    _uid = 0
    cells = []
    PAGE_W = 1100
    cells.append(title("WebSocket - HTTP upgrade, then full-duplex frames", page_w=PAGE_W))
    cells.append(subtitle("Starts life as HTTP so it can punch through proxies. After upgrade, it's a custom protocol on the same TCP.", page_w=PAGE_W))

    lane_top = 110
    y = 150  # Track Y as we build the body so lane height auto-fits

    # Phase 1 header
    cells.append(section_label(300, y, 510, "PHASE 1 - HTTP handshake"))
    y += 26
    cells.append(msg_box(300, y, 510, 90,
        "GET /chat HTTP/1.1\n"
        "Upgrade: websocket\n"
        "Connection: Upgrade\n"
        "Sec-WebSocket-Key: dGhlIHNhbXBsZSB...", role="white", mono=True))
    y += 100
    cells.append(msg_box(300, y, 510, 80,
        "HTTP/1.1 101 Switching Protocols\n"
        "Upgrade: websocket\n"
        "Sec-WebSocket-Accept: s3pPLMBiTxaQ...", role="white", mono=True))
    y += 100

    # Phase 2 header
    cells.append(section_label(300, y, 510, "PHASE 2 - full-duplex WebSocket frames (no more HTTP)"))
    y += 26
    for txt in [
        "→  text frame: \"hello\"",
        "←  text frame: \"hi back\"",
        "→  binary frame: <1024 bytes>",
        "←  text frame: \"ack\"  (server pushes whenever)",
    ]:
        cells.append(msg_box(300, y, 510, 26, txt, role="server", mono=True))
        y += 30

    lane_h = y - lane_top + 10
    cells.append(lane(100, lane_top, 180, lane_h, "CLIENT", "client")[0])
    cells.append(lane(820, lane_top, 180, lane_h, "SERVER", "server")[0])

    callout_y = lane_top + lane_h + 30
    cells.append(callout(100, callout_y, 920, 90,
        "Connection stays open until either side sends a Close frame.\n"
        "Useful for chat, voice, games, collaboration, interruptible LLM streams.\n"
        "Cost:  one open TCP socket per connected client - make sure you need bidirectional."))
    PAGE_H = callout_y + 120

    return render("10_websocket_handshake", cells, PAGE_W, PAGE_H), "10_websocket_handshake.drawio"


def d11_websocket_chat() -> tuple[str, str]:
    global _uid
    _uid = 0
    cells = []
    PAGE_W = 1100
    PAGE_H = 560
    cells.append(title("WebSocket Broadcast - one server, many persistent connections", page_w=PAGE_W))
    cells.append(subtitle("Each client = one open TCP socket. Server fans out every received message to all of them.", page_w=PAGE_W))

    u1, u1_id = box(100, 150, 160, 60, "USER A", role="client", bold=True, fontsize=13)
    u2, u2_id = box(100, 250, 160, 60, "USER B", role="client", bold=True, fontsize=13)
    u3, u3_id = box(100, 350, 160, 60, "USER C", role="client", bold=True, fontsize=13)
    cells += [u1, u2, u3]

    server_box, server_id = box(600, 220, 320, 130,
        "WS SERVER\n\n"
        "clients : set[WebSocket]\n"
        "on receive(msg):\n"
        "    for c in clients: c.send(msg)",
        role="server", bold=False, fontsize=13)
    cells.append(server_box)

    cells.append(arrow(u1_id, server_id, "send \"hi\"", thick=True))
    cells.append(arrow(server_id, u2_id, "broadcast",   dashed=True))
    cells.append(arrow(server_id, u3_id, "broadcast",   dashed=True))
    cells.append(arrow(server_id, u1_id, "(also sender)", dashed=True))

    cells.append(callout(100, 440, 920, 90,
        "Scaling notes\n"
        "1 process → ~10-50K concurrent WS connections is achievable; needs tuning.\n"
        "Multiple processes/servers → broadcast across them with Redis pub-sub (or NATS).\n"
        "Sticky load-balancing → once a client connects to server A, it must stay on A."))

    return render("11_websocket_chat", cells, PAGE_W, PAGE_H), "11_websocket_chat.drawio"


def d12_decision_matrix() -> tuple[str, str]:
    global _uid
    _uid = 0
    cells = []
    PAGE_W = 1200
    PAGE_H = 780
    cells.append(title("Decision Tree - Which pattern when?", page_w=PAGE_W))
    cells.append(subtitle("Walk top-to-bottom. Stop at the first leaf that matches.", page_w=PAGE_W))

    q_style = ("rhombus;whiteSpace=wrap;html=1;"
               "fillColor=#fff2cc;strokeColor=#d6b656;fontSize=13;fontStyle=1;"
               "strokeWidth=1.5;")
    Q_W, Q_H = 220, 90
    LEAF_W, LEAF_H = 240, 60
    CENTER_X = PAGE_W // 2 - Q_W // 2  # center for question diamonds
    LEFT_X   = 80
    RIGHT_X  = PAGE_W - LEAF_W - 80

    # Q1: real-time?
    q1_id = _next_id("q")
    cells.append(
        f'<mxCell id="{q1_id}" value="Need real-time data?" style="{q_style}" vertex="1" parent="1">'
        f'<mxGeometry x="{CENTER_X}" y="110" width="{Q_W}" height="{Q_H}" as="geometry"/></mxCell>'
    )

    rest, rest_id = box(LEFT_X, 125, LEAF_W, LEAF_H,
        "REST\n(plain request/response)", role="neutral", bold=True, fontsize=12)
    cells.append(rest)
    cells.append(arrow(q1_id, rest_id, "no", ortho=True))

    # Q2: who initiates?
    q2_id = _next_id("q")
    cells.append(
        f'<mxCell id="{q2_id}" value="Who initiates the event?" style="{q_style}" vertex="1" parent="1">'
        f'<mxGeometry x="{CENTER_X}" y="250" width="{Q_W}" height="{Q_H}" as="geometry"/></mxCell>'
    )
    cells.append(arrow(q1_id, q2_id, "yes", ortho=True))

    wh, wh_id = box(RIGHT_X, 265, LEAF_W, LEAF_H,
        "WEBHOOK\n(3rd-party POSTs to you)", role="client", bold=True, fontsize=12)
    cells.append(wh)
    cells.append(arrow(q2_id, wh_id, "third-party server", ortho=True))

    # Q3: direction?
    q3_id = _next_id("q")
    cells.append(
        f'<mxCell id="{q3_id}" value="Direction of data?" style="{q_style}" vertex="1" parent="1">'
        f'<mxGeometry x="{CENTER_X}" y="390" width="{Q_W}" height="{Q_H}" as="geometry"/></mxCell>'
    )
    cells.append(arrow(q2_id, q3_id, "your own server", ortho=True))

    poll, poll_id = box(LEFT_X, 405, LEAF_W, LEAF_H,
        "POLLING\n(client keeps asking)", role="third", bold=True, fontsize=12)
    cells.append(poll)
    cells.append(arrow(q3_id, poll_id, "client → server only", ortho=True))

    # Q4: one-way or two-way?
    q4_id = _next_id("q")
    cells.append(
        f'<mxCell id="{q4_id}" value="One-way or two-way?" style="{q_style}" vertex="1" parent="1">'
        f'<mxGeometry x="{CENTER_X}" y="530" width="{Q_W}" height="{Q_H}" as="geometry"/></mxCell>'
    )
    cells.append(arrow(q3_id, q4_id, "server → client", ortho=True))

    sse, sse_id = box(LEFT_X, 545, LEAF_W, LEAF_H,
        "SSE\n(EventSource, server push)", role="server", bold=True, fontsize=12)
    cells.append(sse)
    cells.append(arrow(q4_id, sse_id, "one-way", ortho=True))

    ws, ws_id = box(RIGHT_X, 545, LEAF_W, LEAF_H,
        "WEBSOCKET\n(full-duplex)", role="llm", bold=True, fontsize=12)
    cells.append(ws)
    cells.append(arrow(q4_id, ws_id, "two-way", ortho=True))

    cells.append(callout(80, 660, PAGE_W - 160, 100,
        "Rules of thumb\n\n"
        "• Default to SSE for any \"server pushes updates to user\". Cheap, browser-native, auto-reconnect.\n"
        "• Reach for WebSocket only when you NEED bidirectional or binary (voice, games, collab, interrupt).\n"
        "• Use polling for \"is this slow thing done yet?\".  Use webhooks when something OUTSIDE is the source of truth."))

    return render("12_decision_matrix", cells, PAGE_W, PAGE_H), "12_decision_matrix.drawio"


def d13_ai_app() -> tuple[str, str]:
    global _uid
    _uid = 0
    cells = []
    PAGE_W = 1400
    PAGE_H = 820
    cells.append(title("A Real AI App Uses ALL Four Patterns - Composed, Not Chosen", page_w=PAGE_W))
    cells.append(subtitle("Each edge is labelled with which pattern carries data along it.  Same backend, four delivery mechanisms.", page_w=PAGE_W))

    # Layout: 3 rows. Top = clients & external sources, middle = backend, bottom = infrastructure.
    # Browser is centered-top so REST/SSE edges are nice vertical lines.

    ui,  ui_id   = box(580, 120, 240, 80,  "BROWSER UI",                role="client", bold=True, fontsize=14)
    be,  be_id   = box(580, 380, 240, 100, "APP BACKEND\n(FastAPI / Node)", role="server", bold=True, fontsize=14)

    # External event sources - left side, middle height (row of backend)
    gh,  gh_id   = box(80,  330, 160, 60, "GitHub",  role="third", bold=True, fontsize=13)
    sp,  sp_id   = box(80,  420, 160, 60, "Stripe",  role="third", bold=True, fontsize=13)

    # AI providers - right side, middle height
    llm, llm_id  = box(1140, 330, 200, 60, "LLM API\n(OpenAI/Anthropic)", role="llm", bold=True, fontsize=12)
    rt,  rt_id   = box(1140, 420, 200, 60, "OpenAI Realtime\n(voice)",   role="llm", bold=True, fontsize=12)

    # Infrastructure - bottom row
    q,   q_id    = box(330, 580, 220, 60, "Job Queue (Redis)",         role="infra", bold=True, fontsize=13)
    w,   w_id    = box(580, 580, 240, 60, "WORKER (long-running)",     role="infra", bold=True, fontsize=13)
    db,  db_id   = box(850, 580, 220, 60, "Postgres",                  role="infra", bold=True, fontsize=13)

    cells += [ui, be, gh, sp, llm, rt, q, w, db]

    # --- Edges ---
    # Browser ↔ backend: TWO labelled arrows, slight offset
    cells.append(arrow(ui_id, be_id, "REST   POST /chat", thick=True))
    cells.append(arrow(be_id, ui_id, "SSE   streamed tokens", dashed=True, thick=True))

    # External webhooks → backend (thick, in)
    cells.append(arrow(gh_id, be_id, "WEBHOOK   PR opened",         thick=True))
    cells.append(arrow(sp_id, be_id, "WEBHOOK   payment.succeeded", thick=True))

    # Backend → AI providers
    cells.append(arrow(be_id, llm_id, "HTTP + stream=True (SSE)", thick=True))
    cells.append(arrow(be_id, rt_id,  "WebSocket  audio frames (bidi)", thick=True, both=True))

    # Backend → queue → worker → backend (loop)
    cells.append(arrow(be_id, q_id, "enqueue"))
    cells.append(arrow(q_id, w_id, "dequeue"))
    cells.append(arrow(w_id, be_id, "WEBHOOK callback: done", dashed=True))

    # Backend → DB
    cells.append(arrow(be_id, db_id, "SQL"))

    # Legend in bottom callout
    cells.append(callout(80, 700, PAGE_W - 160, 90,
        "Legend\n"
        "Colour code:  blue = client/UI    green = your backend    red = external services    purple = AI providers    orange = your infrastructure\n"
        "Line style:   solid = primary request    dashed = response / async push    double-headed = bidirectional"))

    return render("13_ai_app_all_patterns", cells, PAGE_W, PAGE_H), "13_ai_app_all_patterns.drawio"


def d14_mcp() -> tuple[str, str]:
    global _uid
    _uid = 0
    cells = []
    PAGE_W = 1100
    PAGE_H = 460
    cells.append(title("MCP (Model Context Protocol) - runs on SSE / Streamable HTTP", page_w=PAGE_W))
    cells.append(subtitle("One tool call → many events (progress, intermediate results, final answer). Exactly the shape SSE is built for.", page_w=PAGE_W))

    host, host_id = box(80, 140, 320, 100,
        "MCP HOST\n(Claude Desktop, Cursor, agent host)",
        role="client", bold=True, fontsize=14)
    server, server_id = box(640, 140, 320, 100,
        "MCP SERVER\n(your tools - files, GitHub, DB, ...)",
        role="server", bold=True, fontsize=14)
    cells += [host, server]

    # Request
    req = (
        '<mxCell id="mcp_req" value="POST /mcp&#10;{ jsonrpc: 2.0, method: \'tools/call\', params: {...} }" '
        'style="endArrow=classic;html=1;strokeColor=#333;strokeWidth=2;fontSize=11;fontFamily=Courier New;" '
        'edge="1" parent="1" source="' + host_id + '" target="' + server_id + '">'
        '<mxGeometry y="-30" relative="1" as="geometry"><mxPoint y="-30" as="offset"/></mxGeometry></mxCell>'
    )
    resp = (
        '<mxCell id="mcp_resp" value="SSE response:&#10;event: progress&#10;event: progress&#10;event: result" '
        'style="endArrow=classic;html=1;strokeColor=#333;strokeWidth=2;fontSize=11;fontFamily=Courier New;dashed=1;" '
        'edge="1" parent="1" source="' + server_id + '" target="' + host_id + '">'
        '<mxGeometry y="30" relative="1" as="geometry"><mxPoint y="30" as="offset"/></mxGeometry></mxCell>'
    )
    cells += [req, resp]

    cells.append(callout(80, 290, 940, 130,
        "Why SSE for MCP?\n\n"
        "• Tool calls take time → progress streaming is a natural fit.\n"
        "• One request can produce many events (search → 10 results, then summary).\n"
        "• Standard HTTP - no WebSocket upgrade, easy to host anywhere.\n"
        "• MCP transports: 1) stdio (local processes)  2) HTTP + SSE  3) Streamable HTTP (current standard)."))

    return render("14_mcp_architecture", cells, PAGE_W, PAGE_H), "14_mcp_architecture.drawio"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    builders = [
        d01_http_basic, d02_short_polling, d03_long_polling, d04_polling_comparison,
        d05_webhook_basic, d06_webhook_retries, d07_webhook_security,
        d08_sse_basic, d09_sse_reconnect,
        d10_websocket_handshake, d11_websocket_chat,
        d12_decision_matrix, d13_ai_app, d14_mcp,
    ]
    for b in builders:
        content, fname = b()
        (ROOT / fname).write_text(content)
        # Basic XML validation
        from xml.etree import ElementTree as ET
        try:
            ET.fromstring(content)
            print(f"  ✓ {fname:45s} ({len(content):,} bytes)")
        except ET.ParseError as e:
            print(f"  ✗ {fname:45s} XML ERROR: {e}")
            raise

    print(f"\nwrote {len(builders)} diagrams to {ROOT}")


if __name__ == "__main__":
    main()
