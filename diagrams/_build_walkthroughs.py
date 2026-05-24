#!/usr/bin/env python3
"""Build the multi-page draw.io file of concept walkthroughs.

Diagrams the concept md files describe but no .drawio existed for:

  1. HTTP connection lifecycle              (01_http_fundamentals.md §1.7)
  2. HTTP/1.0 vs HTTP/1.1 keep-alive        (01_http_fundamentals.md §1.5)
  3. Production webhook pipeline            (03_webhooks.md §3.7)
  4. Long-running task with SSE progress    (07_ai_agents_mcp.md §7.3 option B)
  5. External event triggers AI agent       (07_ai_agents_mcp.md §7.4)
  6. MCP three transports compared          (07_ai_agents_mcp.md §7.6)
  7. Webhook callback for external long job (07_ai_agents_mcp.md §7.3 option C)

Output:
    diagrams/walkthroughs/concept_walkthroughs.drawio   (one file, 7 pages)
    diagrams/walkthroughs/png/p?_*.png                  (one PNG per page)
"""
from pathlib import Path

HERE = Path(__file__).parent
OUT_DIR = HERE / "walkthroughs"
OUT_DIR.mkdir(exist_ok=True)
OUT_FILE = OUT_DIR / "concept_walkthroughs.drawio"

# ---------------------------------------------------------------- palette ---
C_CLIENT = ("#dae8fc", "#6c8ebf")   # blue       browser/app
C_OS     = ("#f5f5f5", "#666666")   # gray       OS / network
C_NET    = ("#fff2cc", "#d6b656")   # yellow     DNS
C_LB     = ("#ffe6cc", "#d79b00")   # orange     LB / proxy
C_SRV    = ("#d5e8d4", "#82b366")   # green      your backend
C_DB     = ("#e1d5e7", "#9673a6")   # purple     storage
C_EXT    = ("#f8cecc", "#b85450")   # red        external services
C_AI     = ("#e1d5e7", "#9673a6")   # purple     AI providers
C_Q      = ("#ffe6cc", "#d79b00")   # orange     queues
C_NOTE   = ("#fff9e6", "#d4b600")   # soft yellow note
C_INSIGHT = ("#e8f5e9", "#43a047")  # soft green insight
C_DARK   = ("#263238", "#263238")   # dark divider

BLUE   = "#1e88e5"
ORANGE = "#fb8c00"
RED    = "#e53935"
GREEN  = "#43a047"
PURPLE = "#8e24aa"
GRAY   = "#666666"


# ---------------------------------------------------------------- helpers --
def esc(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))


class Ids:
    def __init__(self):
        self.n = 1
    def next(self):
        self.n += 1
        return str(self.n)


def box(ids, x, y, w, h, label, color=C_SRV, font_size=12, bold=False, italic=False, align="center"):
    fill, stroke = color
    style_bits = []
    if bold and italic: style_bits.append("fontStyle=3;")
    elif bold:          style_bits.append("fontStyle=1;")
    elif italic:        style_bits.append("fontStyle=2;")
    bold_attr = "".join(style_bits)
    style = (f"rounded=1;arcSize=10;whiteSpace=wrap;html=1;"
             f"fillColor={fill};strokeColor={stroke};fontColor=#000000;"
             f"fontSize={font_size};align={align};verticalAlign=middle;"
             f"{bold_attr}")
    return (f'<mxCell id="{ids.next()}" value="{esc(label)}" style="{style}" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>'
            f'</mxCell>')


def text(ids, x, y, w, h, label, font_size=12, color="#000000",
         bold=False, italic=False, align="center"):
    bold_attr = "fontStyle=1;" if bold else ("fontStyle=2;" if italic else "")
    style = (f"text;html=1;strokeColor=none;fillColor=none;"
             f"align={align};verticalAlign=middle;whiteSpace=wrap;"
             f"fontColor={color};fontSize={font_size};{bold_attr}")
    return (f'<mxCell id="{ids.next()}" value="{esc(label)}" style="{style}" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>'
            f'</mxCell>')


def lifeline(ids, x, y_top, y_bottom, color="#999999"):
    style = (f"endArrow=none;dashed=1;html=1;strokeColor={color};"
             f"strokeWidth=1;dashPattern=4 4;")
    return (f'<mxCell id="{ids.next()}" style="{style}" edge="1" parent="1">'
            f'<mxGeometry relative="1" as="geometry">'
            f'<mxPoint x="{x}" y="{y_top}" as="sourcePoint"/>'
            f'<mxPoint x="{x}" y="{y_bottom}" as="targetPoint"/>'
            f'</mxGeometry></mxCell>')


def msg(ids, x1, x2, y, label, color="#000000", dashed=False,
        font_size=11, bold=False, double_arrow=False):
    """Horizontal message arrow between two lifeline x-coords at y."""
    bold_attr = "fontStyle=1;" if bold else ""
    dash = "dashed=1;dashPattern=6 6;" if dashed else ""
    start = "startArrow=classic;" if double_arrow else ""
    style = (f"endArrow=classic;{start}html=1;rounded=0;"
             f"strokeColor={color};strokeWidth=1.6;"
             f"fontSize={font_size};fontColor=#000000;"
             f"labelBackgroundColor=#FFFFFF;verticalAlign=bottom;{bold_attr}{dash}")
    return (f'<mxCell id="{ids.next()}" value="{esc(label)}" style="{style}" '
            f'edge="1" parent="1">'
            f'<mxGeometry relative="1" as="geometry">'
            f'<mxPoint x="{x1}" y="{y}" as="sourcePoint"/>'
            f'<mxPoint x="{x2}" y="{y}" as="targetPoint"/>'
            f'</mxGeometry></mxCell>')


def arrow(ids, x1, y1, x2, y2, label="", color="#000000", dashed=False,
          font_size=11, bold=False, edge_style=""):
    bold_attr = "fontStyle=1;" if bold else ""
    dash = "dashed=1;dashPattern=4 4;" if dashed else ""
    es = f"edgeStyle={edge_style};" if edge_style else ""
    style = (f"endArrow=classic;html=1;rounded=0;strokeColor={color};"
             f"strokeWidth=1.6;fontSize={font_size};fontColor=#000000;"
             f"labelBackgroundColor=#FFFFFF;{es}{bold_attr}{dash}")
    return (f'<mxCell id="{ids.next()}" value="{esc(label)}" style="{style}" '
            f'edge="1" parent="1">'
            f'<mxGeometry relative="1" as="geometry">'
            f'<mxPoint x="{x1}" y="{y1}" as="sourcePoint"/>'
            f'<mxPoint x="{x2}" y="{y2}" as="targetPoint"/>'
            f'</mxGeometry></mxCell>')


def arrow_wp(ids, x1, y1, x2, y2, waypoints, label="", color="#000000",
             dashed=False, font_size=11, bold=False):
    """Orthogonal arrow with explicit waypoints  =  forces channel routing."""
    bold_attr = "fontStyle=1;" if bold else ""
    dash = "dashed=1;dashPattern=4 4;" if dashed else ""
    style = (f"endArrow=classic;html=1;rounded=0;strokeColor={color};"
             f"strokeWidth=1.6;fontSize={font_size};fontColor=#000000;"
             f"labelBackgroundColor=#FFFFFF;edgeStyle=orthogonalEdgeStyle;"
             f"exitX=0.5;exitY=1;exitDx=0;exitDy=0;"
             f"entryX=0.5;entryY=0;entryDx=0;entryDy=0;"
             f"{bold_attr}{dash}")
    wp_xml = ""
    if waypoints:
        pts = "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in waypoints)
        wp_xml = f'<Array as="points">{pts}</Array>'
    return (f'<mxCell id="{ids.next()}" value="{esc(label)}" style="{style}" '
            f'edge="1" parent="1">'
            f'<mxGeometry relative="1" as="geometry">'
            f'{wp_xml}'
            f'<mxPoint x="{x1}" y="{y1}" as="sourcePoint"/>'
            f'<mxPoint x="{x2}" y="{y2}" as="targetPoint"/>'
            f'</mxGeometry></mxCell>')


def step_num(ids, n, x, y, color="#1565c0"):
    """Small numbered black circle to mark a step in a sequence."""
    style = (f"ellipse;whiteSpace=wrap;html=1;fillColor={color};"
             f"strokeColor={color};fontColor=#FFFFFF;fontSize=11;fontStyle=1;")
    return (f'<mxCell id="{ids.next()}" value="{n}" style="{style}" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{x-12}" y="{y-12}" width="24" height="24" as="geometry"/>'
            f'</mxCell>')


def hbar(ids, x1, x2, y, color=GRAY, h=4):
    """Thin colored horizontal bar (used to visualize TCP open/close)."""
    style = (f"endArrow=none;html=1;strokeColor={color};strokeWidth={h};")
    return (f'<mxCell id="{ids.next()}" style="{style}" edge="1" parent="1">'
            f'<mxGeometry relative="1" as="geometry">'
            f'<mxPoint x="{x1}" y="{y}" as="sourcePoint"/>'
            f'<mxPoint x="{x2}" y="{y}" as="targetPoint"/>'
            f'</mxGeometry></mxCell>')


def page(name, cells, w=1300, h=750):
    pid = name.replace(" ", "_").replace("/", "_").replace(".", "_")
    return (f'  <diagram id="{pid}" name="{esc(name)}">\n'
            f'    <mxGraphModel dx="1422" dy="794" grid="1" gridSize="10" '
            f'guides="1" tooltips="1" connect="1" arrows="1" fold="1" '
            f'page="1" pageScale="1" pageWidth="{w}" pageHeight="{h}" '
            f'math="0" shadow="0">\n'
            f'      <root>\n'
            f'        <mxCell id="0"/>\n'
            f'        <mxCell id="1" parent="0"/>\n'
            f'        {"".join(cells)}\n'
            f'      </root>\n'
            f'    </mxGraphModel>\n'
            f'  </diagram>\n')


def mxfile(pages):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<mxfile host="app.diagrams.net" type="device">\n'
            f'{"".join(pages)}'
            '</mxfile>\n')


# =========================================================== DIAGRAM 1 ====
def d1_http_lifecycle():
    """6-lane sequence diagram of Maya's first API call (10 numbered steps)."""
    ids = Ids()
    cells = []
    W, H = 1320, 800

    cells.append(text(ids, 20, 18, W-40, 28,
                      "How an HTTP Request Actually Works  —  Raj loads the restaurant list",
                      font_size=17, bold=True))
    cells.append(text(ids, 20, 48, W-40, 20,
                      "Step-by-step from fetch() to rendered JSON, with each network hop in its own lane",
                      font_size=11, color=GRAY, italic=True))

    # Lanes
    lane_y, lane_h = 88, 60
    lanes = [
        (130,  C_CLIENT, "Raj's app",       "fetch()"),
        (330,  C_OS,     "OS / TCP stack",  "iOS / Android"),
        (530,  C_NET,    "DNS resolver",    "8.8.8.8"),
        (730,  C_LB,     "Maya's LB",       "api.liveorder.app"),
        (930,  C_SRV,    "Backend",         "one of 50"),
        (1130, C_DB,     "Postgres",        "restaurants"),
    ]
    for x, color, name, sub in lanes:
        cells.append(box(ids, x-85, lane_y, 170, lane_h,
                         f"{name}\n{sub}", color=color, font_size=12, bold=True))

    ll_top    = lane_y + lane_h
    ll_bottom = H - 170
    for x, *_ in lanes:
        cells.append(lifeline(ids, x, ll_top, ll_bottom))

    def lx(i): return lanes[i][0]

    y = ll_top + 30
    DY = 42

    # 1
    cells.append(step_num(ids, "1", 60, y))
    cells.append(msg(ids, lx(0), lx(1), y,
                     "fetch('https://api.liveorder.app/restaurants?lat=12.97&lng=77.59')",
                     color=BLUE))
    y += DY

    # 2
    cells.append(step_num(ids, "2", 60, y))
    cells.append(msg(ids, lx(1), lx(2), y, "resolve api.liveorder.app", color=ORANGE))
    y += 28
    cells.append(msg(ids, lx(2), lx(1), y, "52.6.184.12", color=ORANGE, dashed=True))
    y += DY

    # 3
    cells.append(step_num(ids, "3", 60, y))
    cells.append(msg(ids, lx(1), lx(3), y,
                     "TCP connect :443    (SYN / SYN-ACK / ACK)",
                     color=RED))
    y += DY

    # 4
    cells.append(step_num(ids, "4", 60, y))
    cells.append(msg(ids, lx(1), lx(3), y,
                     "TLS handshake  —  encrypted tunnel established",
                     color=RED, double_arrow=True))
    y += DY

    # 5
    cells.append(step_num(ids, "5", 60, y))
    cells.append(msg(ids, lx(0), lx(3), y,
                     "GET /restaurants?lat=12.97&lng=77.59 HTTP/1.1     "
                     "Authorization: Bearer eyJhbGc...",
                     color=BLUE, bold=True))
    y += DY

    # 6
    cells.append(step_num(ids, "6", 60, y))
    cells.append(msg(ids, lx(3), lx(4), y,
                     "forward to backend-37  (round-robin among 50)",
                     color=GREEN))
    y += DY

    # 7
    cells.append(step_num(ids, "7", 60, y))
    cells.append(msg(ids, lx(4), lx(5), y,
                     "SELECT * FROM restaurants WHERE earth_dist(...) < 5km",
                     color=PURPLE))
    y += 28
    cells.append(msg(ids, lx(5), lx(4), y, "rows", color=PURPLE, dashed=True))
    y += DY

    # 8
    cells.append(step_num(ids, "8", 60, y))
    cells.append(msg(ids, lx(4), lx(3), y,
                     "HTTP/1.1 200 OK    Content-Type: application/json    [{...}]",
                     color=GREEN, bold=True, dashed=True))
    y += DY

    # 9
    cells.append(step_num(ids, "9", 60, y))
    cells.append(msg(ids, lx(3), lx(0), y,
                     "bytes flow back through LB + OS  —  JSON parsed, list rendered",
                     color=BLUE, dashed=True))
    y += DY

    # 10 — note
    cells.append(step_num(ids, "10", 60, y))
    cells.append(box(ids, 120, y-15, W-260, 40,
                     "TCP connection stays OPEN (keep-alive)  —  the next request, e.g. GET /restaurants/1/menu, skips steps 2-4 entirely.",
                     color=C_NOTE, font_size=12, bold=True))

    # Bottom insight
    cells.append(box(ids, 60, H-90, W-120, 60,
                     "STATELESS:   everything from step 6 onward had no idea it was Raj specifically.   The token is validated each time.   "
                     "That's how Maya runs 50 backends in parallel with zero coordination between them.",
                     color=C_INSIGHT, font_size=12))

    return page("1 HTTP Lifecycle", cells, W, H)


# =========================================================== DIAGRAM 2 ====
def d2_http_versions():
    """Side-by-side HTTP/1.0 vs HTTP/1.1 keep-alive."""
    ids = Ids()
    cells = []
    W, H = 1300, 720

    cells.append(text(ids, 20, 18, W-40, 28,
                      "HTTP/1.0 vs HTTP/1.1 keep-alive  —  why long-lived patterns are even possible",
                      font_size=17, bold=True))
    cells.append(text(ids, 20, 48, W-40, 20,
                      "Same three requests, two protocol generations.  Count the TCP handshakes.",
                      font_size=11, color=GRAY, italic=True))

    # ---- LEFT  HTTP/1.0  ----------------------------------------------------
    LX_C, LX_S = 160, 540
    cells.append(box(ids, 80, 88, 540, 38,
                     "HTTP/1.0  —  one TCP connection per request",
                     color=C_LB, font_size=14, bold=True))
    cells.append(box(ids, LX_C-70, 140, 140, 40, "Client",
                     color=C_CLIENT, font_size=12, bold=True))
    cells.append(box(ids, LX_S-70, 140, 140, 40, "Server",
                     color=C_SRV, font_size=12, bold=True))
    cells.append(lifeline(ids, LX_C, 180, 610))
    cells.append(lifeline(ids, LX_S, 180, 610))

    # 3 full cycles each ~140px tall
    cycle_y = 210
    for i, path in enumerate(("/a", "/b", "/c"), start=1):
        # TCP open bar across both lifelines
        cells.append(hbar(ids, LX_C, LX_S, cycle_y, color=RED, h=3))
        cells.append(text(ids, LX_C+10, cycle_y-22, 180, 16,
                          f"TCP open  (handshake #{i})", font_size=10,
                          color=RED, italic=True, align="left"))
        # request
        cells.append(msg(ids, LX_C, LX_S, cycle_y+25,
                         f"GET {path}", color=BLUE, font_size=11))
        # response
        cells.append(msg(ids, LX_S, LX_C, cycle_y+50,
                         "200 OK", color=GREEN, font_size=11, dashed=True))
        # TCP close bar
        cells.append(hbar(ids, LX_C, LX_S, cycle_y+80, color=RED, h=3))
        cells.append(text(ids, LX_C+10, cycle_y+85, 180, 16,
                          "TCP close", font_size=10, color=RED,
                          italic=True, align="left"))
        cycle_y += 125

    cells.append(box(ids, 80, H-90, 540, 55,
                     "3 requests  =  3 expensive TCP+TLS handshakes.\n"
                     "Each handshake is 1-3 round trips of network latency.",
                     color=C_NOTE, font_size=11, bold=True))

    # ---- RIGHT  HTTP/1.1 keep-alive ----------------------------------------
    RX_C, RX_S = 800, 1180
    cells.append(box(ids, 720, 88, 540, 38,
                     "HTTP/1.1 keep-alive  —  reuse the same TCP connection",
                     color=C_INSIGHT, font_size=14, bold=True))
    cells.append(box(ids, RX_C-70, 140, 140, 40, "Client",
                     color=C_CLIENT, font_size=12, bold=True))
    cells.append(box(ids, RX_S-70, 140, 140, 40, "Server",
                     color=C_SRV, font_size=12, bold=True))
    cells.append(lifeline(ids, RX_C, 180, 610))
    cells.append(lifeline(ids, RX_S, 180, 610))

    # One TCP open at top
    cells.append(hbar(ids, RX_C, RX_S, 210, color=RED, h=3))
    cells.append(text(ids, RX_C+10, 188, 200, 16,
                      "TCP open  (one handshake)", font_size=10,
                      color=RED, italic=True, align="left"))
    # Three req/resp pairs much closer together
    y = 250
    for path in ("/a", "/b", "/c"):
        cells.append(msg(ids, RX_C, RX_S, y, f"GET {path}", color=BLUE,
                         font_size=11))
        cells.append(msg(ids, RX_S, RX_C, y+24, "200 OK", color=GREEN,
                         font_size=11, dashed=True))
        y += 70

    # TCP close at end (optional)
    cells.append(hbar(ids, RX_C, RX_S, y+10, color=RED, h=3))
    cells.append(text(ids, RX_C+10, y+15, 200, 16,
                      "TCP close  (eventually, after idle)",
                      font_size=10, color=RED, italic=True, align="left"))

    cells.append(box(ids, 720, H-90, 540, 55,
                     "3 requests  =  1 handshake + 3 cheap exchanges.\n"
                     "Long polling, SSE, and WebSocket all rely on this primitive.",
                     color=C_INSIGHT, font_size=11, bold=True))

    return page("2 HTTP versions", cells, W, H)


# =========================================================== DIAGRAM 3 ====
def d3_webhook_pipeline():
    """The full LiveOrder webhook pipeline:
       Raj -> Stripe -> API receiver -> Queue -> Worker -> fan-out to DB/Priya/Raj/Email
    """
    ids = Ids()
    cells = []
    W, H = 1500, 980

    cells.append(text(ids, 20, 18, W-40, 28,
                      "Production webhook pipeline  —  Stripe pays for Raj's biryani",
                      font_size=17, bold=True))
    cells.append(text(ids, 20, 48, W-40, 20,
                      "The 100ms handler   vs   the worker doing real work.   Notice the fan-out at the end.",
                      font_size=11, color=GRAY, italic=True))

    # ROW 1 - trigger and ingest -----------------------------------------
    # x positions
    XR = (40,   200)   # Raj
    XS = (260,  420)   # Stripe
    XA = (480,  900)   # API receiver (wide)
    XQ = (960,  1110)  # Queue
    XW = (1170, 1330)  # Worker

    row1_y, row1_h = 110, 80

    cells.append(box(ids, XR[0], row1_y, XR[1]-XR[0], row1_h,
                     "Raj's phone\nconfirm payment 450 INR",
                     color=C_CLIENT, font_size=11, bold=True))
    cells.append(box(ids, XS[0], row1_y, XS[1]-XS[0], row1_h,
                     "Stripe\ncharges card",
                     color=C_EXT, font_size=11, bold=True))
    # API receiver - large box with 3 internal substeps
    cells.append(box(ids, XA[0], 90, XA[1]-XA[0], 220,
                     "LiveOrder API receiver  —  POST /webhooks/stripe",
                     color=C_SRV, font_size=13, bold=True, align="center"))
    sub_y = 140
    for i, label in enumerate([
        "a.  verify HMAC signature   (constant-time compare)",
        "b.  dedup by event id       (Redis SETNX, TTL = 24h)",
        "c.  enqueue   then   return 200 OK   (<100 ms end-to-end)",
    ]):
        cells.append(box(ids, XA[0]+20, sub_y + i*48, XA[1]-XA[0]-40, 38,
                         label, color=("#ffffff", "#82b366"),
                         font_size=11, align="left"))

    cells.append(box(ids, XQ[0], row1_y, XQ[1]-XQ[0], row1_h,
                     "Redis queue\norders.paid",
                     color=C_Q, font_size=12, bold=True))
    cells.append(box(ids, XW[0], row1_y, XW[1]-XW[0], row1_h,
                     "Worker\n(retry-safe)",
                     color=C_SRV, font_size=12, bold=True))

    # Arrows along row 1
    mid_y = row1_y + row1_h // 2
    cells.append(arrow(ids, XR[1], mid_y, XS[0], mid_y,
                       "1.  confirm",
                       color=BLUE, bold=True, font_size=11))
    cells.append(arrow(ids, XS[1], mid_y, XA[0], mid_y,
                       "2.  POST /webhooks/stripe",
                       color=RED, bold=True, font_size=11))
    # 3. API -> Stripe (200 OK)   - put this below to avoid overlap
    cells.append(arrow(ids, XA[0], 290, XS[1], 290,
                       "3.  200 OK   (under 100 ms)",
                       color=GREEN, bold=True, dashed=True, font_size=11))
    cells.append(arrow(ids, XA[1], mid_y, XQ[0], mid_y,
                       "4.  enqueue",
                       color=ORANGE, bold=True, font_size=11))
    cells.append(arrow(ids, XQ[1], mid_y, XW[0], mid_y,
                       "5.  pop",
                       color=ORANGE, bold=True, font_size=11))

    # ROW 2 - fan-out ---------------------------------------------------
    row2_y, row2_h = 580, 80
    fanout_boxes = [
        ( 100, "Postgres\nUPDATE orders\nSET paid = true",      C_DB,     "6.  mark order paid",        PURPLE),
        ( 440, "Priya's tablet\nrestaurant new-order page",     C_CLIENT, "7.  SSE: new paid order",    "#43a047"),
        ( 780, "Raj's phone\ntrack-order page",                 C_CLIENT, "8.  SSE: payment confirmed", "#43a047"),
        (1120, "Email service\nreceipt to Raj",                 C_EXT,    "9.  send receipt",           RED),
    ]
    # Each fan-out arrow drops from worker bottom into its own horizontal
    # channel (so labels don't stack), then to the target box top.
    worker_bottom_y = row1_y + row1_h   # = 190
    channel_ys = [380, 420, 460, 500]   # below the API box bottom (= 310)
    for i, (x, label, color, arrow_label, acolor) in enumerate(fanout_boxes):
        # box
        cells.append(box(ids, x, row2_y, 280, row2_h, label,
                         color=color, font_size=12, bold=True))
        # routed arrow with waypoint at the channel y
        target_x = x + 140
        wp_y = channel_ys[i]
        worker_drop_x = XW[0] + 30 + i * 35  # spread drop points across worker bottom
        cells.append(arrow_wp(ids,
                              worker_drop_x, worker_bottom_y,
                              target_x, row2_y,
                              waypoints=[(worker_drop_x, wp_y), (target_x, wp_y)],
                              label=arrow_label,
                              color=acolor, bold=True, font_size=11))

    # Bottom insights
    cells.append(box(ids, 40, H-260, W-80, 70,
                     "WHY THE SPLIT:   the API handler must return 200 within Stripe's 5-10s timeout.\n"
                     "Worker does the slow / retryable work.   If the DB is briefly down, the worker retries — without involving Stripe.",
                     color=C_INSIGHT, font_size=13, bold=True))
    cells.append(box(ids, 40, H-180, W-80, 65,
                     "WHY DEDUP:   Stripe may deliver the same event id twice (lost ACK, internal retry).\n"
                     "SETNX in Redis is atomic — even two workers racing the same event process it exactly once.",
                     color=C_NOTE, font_size=13, bold=True))
    cells.append(box(ids, 40, H-105, W-80, 55,
                     "WHY THE FAN-OUT IS ASYNC:   one paid event triggers DB + 2 SSE pushes + 1 email.\n"
                     "Worker fires them in parallel — none block any other.",
                     color=C_INSIGHT, font_size=13, bold=True))

    return page("3 Webhook pipeline", cells, W, H)


# =========================================================== DIAGRAM 4 ====
def d4_sse_progress_long_task():
    """Priya's weekly report — 3-lifeline SSE-progress sequence."""
    ids = Ids()
    cells = []
    W, H = 1200, 880

    cells.append(text(ids, 20, 18, W-40, 28,
                      "Long-running task with SSE progress  —  Priya's weekly restaurant report",
                      font_size=17, bold=True))
    cells.append(text(ids, 20, 48, W-40, 20,
                      "POST to kick off the job, separate SSE stream for live progress events.",
                      font_size=11, color=GRAY, italic=True))

    # Lanes
    lane_y, lane_h = 88, 60
    lanes = [
        (180,  C_CLIENT, "Priya's browser",  "report dashboard"),
        (550,  C_SRV,    "LiveOrder backend", "FastAPI"),
        (940,  C_AI,     "Worker (agent)",   "LLM + tools"),
    ]
    for x, color, name, sub in lanes:
        cells.append(box(ids, x-110, lane_y, 220, lane_h,
                         f"{name}\n{sub}", color=color, font_size=12, bold=True))
    ll_top, ll_bottom = lane_y + lane_h, H - 200
    for x, *_ in lanes:
        cells.append(lifeline(ids, x, ll_top, ll_bottom))

    def lx(i): return lanes[i][0]

    y = ll_top + 30
    DY = 40

    # 1. POST /reports
    cells.append(step_num(ids, "1", 80, y))
    cells.append(msg(ids, lx(0), lx(1), y, "POST /reports", color=BLUE, bold=True))
    y += DY

    # 2. backend enqueues, returns id
    cells.append(step_num(ids, "2", 80, y))
    cells.append(msg(ids, lx(1), lx(2), y, "enqueue job  (report_id = abc)",
                     color=ORANGE))
    y += 28
    cells.append(msg(ids, lx(1), lx(0), y, "202 Accepted   { id: 'abc' }",
                     color=GREEN, dashed=True))
    y += DY

    # 3. browser opens SSE
    cells.append(step_num(ids, "3", 80, y))
    cells.append(msg(ids, lx(0), lx(1), y,
                     "GET /reports/abc/stream    Accept: text/event-stream",
                     color=BLUE, bold=True))
    y += 28
    cells.append(msg(ids, lx(1), lx(0), y,
                     "200 OK   Content-Type: text/event-stream   (stream stays open)",
                     color=GREEN, dashed=True))
    y += DY

    # 4..7. progress events flowing back as worker progresses
    progress_steps = [
        ("4", "loaded last week's orders",
              "event: progress\ndata: { step: 'load_data', pct: 20 }"),
        ("5", "searched benchmark data",
              "event: progress\ndata: { step: 'benchmark', pct: 50 }"),
        ("6", "wrote summary with LLM",
              "event: progress\ndata: { step: 'summarise', pct: 80 }"),
        ("7", "done — uploaded PDF",
              "event: done\ndata: { url: 'https://.../report.pdf' }"),
    ]
    for num, worker_label, sse_label in progress_steps:
        cells.append(step_num(ids, num, 80, y))
        cells.append(msg(ids, lx(2), lx(1), y, worker_label,
                         color=PURPLE, font_size=10))
        y += 28
        cells.append(msg(ids, lx(1), lx(0), y, sse_label,
                         color=GREEN, dashed=True, font_size=10))
        y += DY

    # Bottom insight
    cells.append(box(ids, 60, H-180, W-120, 60,
                     "PERCEIVED LATENCY:   total work is still 3-5 min.   But Priya sees a checkmark next to each step as it lands —\n"
                     "her brain registers progress instead of a frozen spinner.   The same job feels twice as fast.",
                     color=C_INSIGHT, font_size=12, bold=True))
    cells.append(box(ids, 60, H-110, W-120, 50,
                     "Two endpoints in tandem:   POST kicks off the job (returns immediately),   GET /stream is the live SSE feed.   "
                     "Browser auto-reconnects with Last-Event-ID; server resumes from the last sent progress event.",
                     color=C_NOTE, font_size=11))

    return page("4 SSE progress long task", cells, W, H)


# =========================================================== DIAGRAM 5 ====
def d5_external_event_agent():
    """Order delivered -> LLM generates personalised SMS -> Twilio sends."""
    ids = Ids()
    cells = []
    W, H = 1700, 900

    cells.append(text(ids, 20, 18, W-40, 28,
                      "External event triggers AI agent  —  delivered order  →  personalised thank-you SMS",
                      font_size=17, bold=True))
    cells.append(text(ids, 20, 48, W-40, 20,
                      "Webhook in, webhook out.   Notice that every external boundary uses a webhook.",
                      font_size=11, color=GRAY, italic=True))

    box_w, box_h = 200, 90
    row_y = 150
    # 5 boxes - leave 140 px gap between each so labels have room
    xs = [40, 380, 720, 1060, 1400]
    box_defs = [
        ("Order service\n(LiveOrder)",            C_SRV),
        ("Post-delivery service\n/post-delivery", C_SRV),
        ("Redis queue\nthank-you jobs",           C_Q),
        ("Agent worker\nLLM call (3-5s)",         C_AI),
        ("Twilio API\nSMS send",                  C_EXT),
    ]
    for x, (label, color) in zip(xs, box_defs):
        cells.append(box(ids, x, row_y, box_w, box_h, label,
                         color=color, font_size=12, bold=True))

    arrow_y = row_y + box_h // 2
    arrow_labels = [
        ("1.  POST\n/post-delivery",   RED),
        ("2.  enqueue\n(200 OK)",      ORANGE),
        ("3.  pop",                    ORANGE),
        ("4.  generate\nSMS text",     PURPLE),
    ]
    for i, (lbl, color) in enumerate(arrow_labels):
        x1 = xs[i] + box_w
        x2 = xs[i+1]
        cells.append(arrow(ids, x1, arrow_y, x2, arrow_y, lbl,
                           color=color, bold=True, font_size=11))

    # Customer phone (below Twilio)
    phone_y = 420
    cells.append(box(ids, xs[4], phone_y, box_w, box_h,
                     "Customer's phone\nSMS arrives",
                     color=C_CLIENT, font_size=12, bold=True))
    cells.append(arrow(ids, xs[4] + box_w//2, row_y + box_h,
                       xs[4] + box_w//2, phone_y,
                       "5.  SMS over carrier",
                       color=RED, bold=True, font_size=11))

    # Twilio webhook back to post-delivery service
    feedback_y = 600
    cells.append(arrow(ids, xs[4] + box_w//2, phone_y + box_h,
                       xs[4] + box_w//2, feedback_y,
                       "",
                       color=RED, dashed=True,
                       edge_style="orthogonalEdgeStyle"))
    cells.append(arrow(ids, xs[4] + box_w//2, feedback_y,
                       xs[1] + box_w//2, feedback_y,
                       "6.  Twilio webhook   →   POST /webhooks/twilio   { delivered / failed }",
                       color=RED, bold=True, dashed=True, font_size=11,
                       edge_style="orthogonalEdgeStyle"))
    cells.append(arrow(ids, xs[1] + box_w//2, feedback_y,
                       xs[1] + box_w//2, row_y + box_h,
                       "",
                       color=RED, dashed=True,
                       edge_style="orthogonalEdgeStyle"))

    # Failure-modes panel
    fail_y = 670
    cells.append(text(ids, 40, fail_y, W-80, 24,
                      "Three places this goes wrong (and how teams avoid them)",
                      font_size=14, bold=True, color="#b71c1c", align="left"))
    failures = [
        ("LLM call inside webhook handler",
         "LLM takes 1-5s, sender times out at 5-10s.\nResult: retries, duplicate SMSes go out."),
        ("No dedup on internal webhook",
         "Same delivered event processed twice.\nCustomer gets 2 SMSes; Twilio bills twice."),
        ("No idempotency in worker",
         "Two workers race the same job.\nWrap LLM+send in a DB transaction\nthat checks 'already sent?'."),
    ]
    card_w = (W - 160) // 3
    for i, (head, body) in enumerate(failures):
        x = 40 + i * (card_w + 40)
        cells.append(box(ids, x, fail_y + 35, card_w, 60,
                         head, color=("#ffebee", "#b71c1c"),
                         font_size=13, bold=True))
        cells.append(box(ids, x, fail_y + 100, card_w, 95,
                         body, color=("#ffffff", "#b71c1c"),
                         font_size=12))

    return page("5 External event triggers agent", cells, W, H)


# =========================================================== DIAGRAM 6 ====
def d6_mcp_transports():
    """3 columns: stdio, HTTP+SSE (older), Streamable HTTP (current)."""
    ids = Ids()
    cells = []
    W, H = 1400, 780

    cells.append(text(ids, 20, 18, W-40, 28,
                      "MCP transports compared  —  stdio  vs  HTTP+SSE  vs  Streamable HTTP",
                      font_size=17, bold=True))
    cells.append(text(ids, 20, 48, W-40, 20,
                      "Same protocol shape (one request, many events).   Three ways to ship the bytes.",
                      font_size=11, color=GRAY, italic=True))

    col_w = 430
    col_x = [40, 490, 940]
    col_titles = [
        ("stdio",                      "local subprocess",   C_OS),
        ("HTTP + SSE  (older)",        "two endpoints",      C_LB),
        ("Streamable HTTP  (current)", "single endpoint",    C_INSIGHT),
    ]
    for i, (title, sub, color) in enumerate(col_titles):
        cells.append(box(ids, col_x[i], 88, col_w, 60,
                         f"{title}\n{sub}", color=color, font_size=14, bold=True))

    # --- Column 1: stdio --------------------------------------------------
    cx = col_x[0]
    cells.append(box(ids, cx+50, 180, 160, 60,
                     "Claude Desktop\n(MCP host)",
                     color=C_CLIENT, font_size=12, bold=True))
    cells.append(box(ids, cx+50, 380, 160, 60,
                     "MCP server\n(local Python / Node)",
                     color=C_SRV, font_size=12, bold=True))
    # stdin pipe
    cells.append(arrow(ids, cx+130, 240, cx+130, 380,
                       "stdin\nJSON-RPC requests",
                       color=BLUE, bold=True, font_size=10))
    # stdout pipe
    cells.append(arrow(ids, cx+170, 380, cx+170, 240,
                       "stdout\nresponses",
                       color=GREEN, bold=True, font_size=10, dashed=True))
    cells.append(box(ids, cx+20, 470, col_w-40, 90,
                     "Used for filesystem, git, sqlite — tools that live on the host.\n\n"
                     "No network.   No auth.   Process lifecycle = transport lifecycle.\n"
                     "Doesn't count as one of our four patterns.",
                     color=C_NOTE, font_size=11))
    cells.append(box(ids, cx+20, 580, col_w-40, 60,
                     "Examples:\nclaude_desktop_config.json — type: 'stdio'\nmcp dev / mcp run (Python SDK)",
                     color=("#ffffff", "#cccccc"), font_size=10, align="left"))

    # --- Column 2: HTTP + SSE (old) ---------------------------------------
    cx = col_x[1]
    cells.append(box(ids, cx+50, 180, 160, 60,
                     "Claude Desktop\n(MCP host)",
                     color=C_CLIENT, font_size=12, bold=True))
    cells.append(box(ids, cx+50, 380, 160, 60,
                     "MCP server\n(your tools)",
                     color=C_SRV, font_size=12, bold=True))
    # GET /sse stream
    cells.append(arrow(ids, cx+100, 240, cx+100, 380,
                       "GET /sse\nopens SSE stream\n(server → client)",
                       color=GREEN, bold=True, font_size=10))
    # POST /messages
    cells.append(arrow(ids, cx+180, 380, cx+180, 240,
                       "POST /messages\n(client → server)",
                       color=BLUE, bold=True, font_size=10, dashed=True))
    cells.append(box(ids, cx+20, 470, col_w-40, 90,
                     "Two endpoints, glued together.\n"
                     "SSE for server-to-client; separate POSTs for client-to-server.\n"
                     "Works but awkward to host (sticky sessions, two routes to manage).",
                     color=C_NOTE, font_size=11))
    cells.append(box(ids, cx+20, 580, col_w-40, 60,
                     "Examples:\nServer-Sent Events transport, MCP spec v0.1\nUsed by early MCP servers (2024)",
                     color=("#ffffff", "#cccccc"), font_size=10, align="left"))

    # --- Column 3: Streamable HTTP (new) ----------------------------------
    cx = col_x[2]
    cells.append(box(ids, cx+50, 180, 160, 60,
                     "Claude Desktop\n(MCP host)",
                     color=C_CLIENT, font_size=12, bold=True))
    cells.append(box(ids, cx+50, 380, 160, 60,
                     "MCP server\n(your tools)",
                     color=C_SRV, font_size=12, bold=True))
    # one endpoint - paired POST and SSE response
    cells.append(arrow(ids, cx+130, 240, cx+130, 380,
                       "POST /mcp\nrequest body",
                       color=BLUE, bold=True, font_size=10))
    cells.append(arrow(ids, cx+130, 380, cx+130, 240,
                       "response body\nIS the SSE stream\n(many progress events\n + final result)",
                       color=GREEN, bold=True, font_size=10, dashed=True))
    cells.append(box(ids, cx+20, 470, col_w-40, 90,
                     "Single endpoint.   The response body itself is an SSE stream.\n"
                     "One request can stream many progress events plus a final result.\n"
                     "Easy to host on Cloud Run, Vercel, anywhere that supports streaming.",
                     color=C_INSIGHT, font_size=11))
    cells.append(box(ids, cx+20, 580, col_w-40, 60,
                     "Examples:\nMCP spec 2025-03-26 onwards (current standard)\nClaude Desktop, mcp.run, Cursor",
                     color=("#ffffff", "#43a047"), font_size=10, align="left"))

    cells.append(box(ids, 40, H-90, W-80, 55,
                     "ALL THREE ARE SSE-SHAPED AT THE PROTOCOL LEVEL:   one request   →   many response events (progress + result).\n"
                     "The transport differs.   The protocol shape does not.",
                     color=C_INSIGHT, font_size=12, bold=True))

    return page("6 MCP transports", cells, W, H)


# =========================================================== DIAGRAM 7 ====
def d7_webhook_callback_long_job():
    """OpenAI Batch style: pass callback_url, walk away, get notified."""
    ids = Ids()
    cells = []
    W, H = 1200, 760

    cells.append(text(ids, 20, 18, W-40, 28,
                      "Webhook callback for a slow external job  —  OpenAI Batch API pattern",
                      font_size=17, bold=True))
    cells.append(text(ids, 20, 48, W-40, 20,
                      "Job runs for hours.   The user doesn't stay on the page.   The external service POSTs you when it's done.",
                      font_size=11, color=GRAY, italic=True))

    lane_y, lane_h = 88, 60
    lanes = [
        (180,  C_CLIENT, "User's browser",  "weekly report page"),
        (570,  C_SRV,    "Your backend",    "/generate-report"),
        (960,  C_EXT,    "OpenAI Batch",    "external"),
    ]
    for x, color, name, sub in lanes:
        cells.append(box(ids, x-110, lane_y, 220, lane_h,
                         f"{name}\n{sub}", color=color, font_size=12, bold=True))
    ll_top, ll_bottom = lane_y + lane_h, H - 200
    for x, *_ in lanes:
        cells.append(lifeline(ids, x, ll_top, ll_bottom))

    def lx(i): return lanes[i][0]

    y = ll_top + 30
    DY = 40

    # 1. user POST
    cells.append(step_num(ids, "1", 80, y))
    cells.append(msg(ids, lx(0), lx(1), y, "POST /generate-report",
                     color=BLUE, bold=True))
    y += DY

    # 2. backend submits to OpenAI Batch with callback_url
    cells.append(step_num(ids, "2", 80, y))
    cells.append(msg(ids, lx(1), lx(2), y,
                     "POST /v1/batches\n{ callback_url: 'https://you.com/callback/openai',\n  input_file, model, ... }",
                     color=RED, font_size=10, bold=True))
    y += 36
    cells.append(msg(ids, lx(2), lx(1), y,
                     "{ id: 'batch_abc', status: 'validating' }",
                     color=RED, dashed=True, font_size=10))
    y += DY

    # 3. backend responds to user
    cells.append(step_num(ids, "3", 80, y))
    cells.append(msg(ids, lx(1), lx(0), y,
                     "202 Accepted   { 'we'll email when ready' }",
                     color=GREEN, dashed=True))
    y += DY

    # Time passes
    cells.append(box(ids, 130, y, W-220, 36,
                     "·   ·   ·    minutes to hours pass     ·    user closes the tab,  goes for coffee    ·   ·   ·",
                     color=("#fafafa", "#bdbdbd"), font_size=11, italic=True, bold=True))
    y += 60

    # 4. OpenAI processes
    cells.append(step_num(ids, "4", 80, y))
    cells.append(text(ids, lx(2)-110, y-10, 220, 24,
                      "running ... validating ... in_progress ... completed",
                      font_size=10, italic=True, color=PURPLE, align="center"))
    y += DY

    # 5. OpenAI POSTs the callback
    cells.append(step_num(ids, "5", 80, y))
    cells.append(msg(ids, lx(2), lx(1), y,
                     "POST /callback/openai\n{ id: 'batch_abc', status: 'completed',\n  output_file_id: 'file-xyz' }",
                     color=RED, font_size=10, bold=True))
    y += 36
    cells.append(msg(ids, lx(1), lx(2), y,
                     "200 OK  (verify, dedup, enqueue, return 200)",
                     color=GREEN, dashed=True, font_size=10))
    y += DY

    # 6. backend stores and notifies user (email or push notification)
    cells.append(step_num(ids, "6", 80, y))
    cells.append(text(ids, lx(1)-110, y-10, 220, 24,
                      "store result   ·   send push or email",
                      font_size=10, italic=True, color=GREEN))
    y += 30

    # 7. user opens email - or app shows notification
    cells.append(step_num(ids, "7", 80, y))
    cells.append(msg(ids, lx(1), lx(0), y,
                     "push notification / email\n→ report ready, tap to view",
                     color=BLUE, bold=True, font_size=10))
    y += DY

    # Bottom insight
    cells.append(box(ids, 60, H-180, W-120, 60,
                     "WHY WEBHOOK:   the wait is hours.   Holding an SSE/WS connection for that long is wasteful and fragile.\n"
                     "Submit, walk away, get called back.   That's the same shape as Stripe / GitHub / Twilio.",
                     color=C_INSIGHT, font_size=12, bold=True))
    cells.append(box(ids, 60, H-110, W-120, 50,
                     "callback_url is the entire mechanism.   The external service is essentially Stripe for a different domain (compute).\n"
                     "All four webhook rules still apply on /callback/openai:  verify signature, dedup by id, return 2xx fast, no 5xx for noise.",
                     color=C_NOTE, font_size=11))

    return page("7 Webhook callback long job", cells, W, H)


# ====================================================================== run
def main():
    pages = [
        d1_http_lifecycle(),
        d2_http_versions(),
        d3_webhook_pipeline(),
        d4_sse_progress_long_task(),
        d5_external_event_agent(),
        d6_mcp_transports(),
        d7_webhook_callback_long_job(),
    ]
    OUT_FILE.write_text(mxfile(pages), encoding="utf-8")
    n = len(pages)
    size = OUT_FILE.stat().st_size
    print(f"wrote {OUT_FILE.relative_to(HERE.parent)}")
    print(f"  {n} pages")
    print(f"  {size:,} bytes")


if __name__ == "__main__":
    main()
