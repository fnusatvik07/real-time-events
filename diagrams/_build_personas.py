"""Build the persona-scenario diagrams used in the workshop slide deck.

These differ from the technical diagrams in _build.py: instead of pure
client/server protocol sequence diagrams, these show our cast of personas
(Maya/Raj/Priya/Sam) interacting with real-named products (Stripe, OpenAI,
etc.) so the audience sees the patterns in a recognisable LiveOrder context.

Run:
    python _build_personas.py
Output: 10 .drawio files in diagrams/personas/ + their PNG renders.
"""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).parent
OUT_DIR = ROOT / "personas"
OUT_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Palette - mirrors the slide deck colours
# ---------------------------------------------------------------------------
class C:
    # Personas (each has a unique colour)
    MAYA   = ("#dae8fc", "#6c8ebf")   # blue   - backend dev
    RAJ    = ("#fff2cc", "#d6b656")   # amber  - customer
    PRIYA  = ("#f8cecc", "#b85450")   # red    - restaurant owner
    SAM    = ("#d5e8d4", "#82b366")   # green  - delivery driver
    # Backend / yours
    BACKEND = ("#e1d5e7", "#9673a6")  # purple - "your backend"
    # External brands
    STRIPE  = ("#ddd6fe", "#7c3aed")  # Stripe purple
    OPENAI  = ("#d1fae5", "#10a37f")  # OpenAI green
    SWIGGY  = ("#ffedd5", "#fc8019")  # Swiggy orange
    UBER    = ("#f3f4f6", "#000000")  # Uber black
    GITHUB  = ("#f3f4f6", "#181717")
    SLACK   = ("#f3e8ff", "#4a154b")
    # Generic
    NOTE    = ("#fff2cc", "#d6b656")
    INFRA   = ("#ffe6cc", "#d79b00")
    GREY    = ("#f5f5f5", "#666666")


# ---------------------------------------------------------------------------
# XML helpers
# ---------------------------------------------------------------------------
_uid = 0


def _next_id(prefix: str = "n") -> str:
    global _uid
    _uid += 1
    return f"{prefix}{_uid}"


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("\n", "&#10;")
    )


def title(text: str, page_w: int = 1100, y: int = 24) -> str:
    """No-op kept for backwards compat - diagram titles are redundant with slide titles.

    Returns an empty cell so callers can still call title(...) without effect.
    """
    return ""


def subtitle(text: str, page_w: int = 1100, y: int = 60) -> str:
    """No-op - subtitles live on the slide, not in the diagram."""
    return ""


def _label_simple(line1: str, line2: str = "", line3: str = "") -> str:
    """Build a multi-line label as plain newline-separated text (no HTML)."""
    lines = [l for l in (line1, line2, line3) if l]
    return "\n".join(lines)


def persona_card(x: int, y: int, w: int, h: int, initial: str, name: str,
                 role: str, color: tuple[str, str]) -> tuple[str, str]:
    """A persona card: bold initial, name, role.  Returns (xml, id)."""
    fill, stroke = color
    cid = _next_id("p")
    label = _label_simple(initial, name, role)
    cell = (
        f'<mxCell id="{cid}" value="{esc(label)}" '
        f'style="rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};'
        f'fontSize=14;fontStyle=1;align=center;verticalAlign=middle;strokeWidth=2;'
        f'spacingTop=4;" '
        f'vertex="1" parent="1">'
        f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
    )
    return cell, cid


def brand_box(x: int, y: int, w: int, h: int, name: str, sub: str,
              color: tuple[str, str]) -> tuple[str, str]:
    """A box that represents a branded product (Stripe, OpenAI, ...)."""
    fill, stroke = color
    cid = _next_id("b")
    label = _label_simple(name, sub)
    cell = (
        f'<mxCell id="{cid}" value="{esc(label)}" '
        f'style="rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};'
        f'fontSize=13;fontStyle=1;align=center;verticalAlign=middle;strokeWidth=2;" '
        f'vertex="1" parent="1">'
        f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
    )
    return cell, cid


def device(x: int, y: int, w: int, h: int, name: str, owner: str,
           color: tuple[str, str]) -> tuple[str, str]:
    """A device card (e.g. 'Raj's phone', 'Priya's tablet')."""
    fill, stroke = color
    cid = _next_id("d")
    label = _label_simple(name, owner)
    cell = (
        f'<mxCell id="{cid}" value="{esc(label)}" '
        f'style="rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};'
        f'fontSize=12;fontStyle=1;align=center;verticalAlign=middle;strokeWidth=1.5;" '
        f'vertex="1" parent="1">'
        f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
    )
    return cell, cid


def arrow(src: str, dst: str, label: str = "",
          dashed: bool = False, thick: bool = False, both: bool = False,
          exit_y: float | None = None, entry_y: float | None = None,
          ortho: bool = False, color: str = "#bbb") -> str:
    """Edge between two cells.

    exit_y / entry_y let parallel arrows between the same boxes be vertically
    offset so their labels don't collide. Pass exit_y=0.3+entry_y=0.3 for the
    top one and 0.7+0.7 for the bottom.
    """
    cid = _next_id("e")
    start_arrow = "classic" if both else "none"
    edge_style = "orthogonalEdgeStyle" if ortho else "none"
    extra = ""
    if exit_y is not None:
        extra += f"exitX=1;exitY={exit_y};exitDx=0;exitDy=0;"
    if entry_y is not None:
        extra += f"entryX=0;entryY={entry_y};entryDx=0;entryDy=0;"
    # Edge labels get a small background pill rendered by drawio. Setting it to
    # the slide background colour (#0B0E14) makes the pill invisible against
    # the slide while keeping the white-text labels readable.
    style = (
        f"endArrow=classic;startArrow={start_arrow};html=1;rounded=0;"
        f"strokeColor={color};strokeWidth={'2.5' if thick else '1.6'};"
        f"fontSize=11;fontColor=#FFFFFF;labelBackgroundColor=#0B0E14;"
        f"{'dashed=1;' if dashed else ''}edgeStyle={edge_style};"
        f"{extra}"
    )
    return (
        f'<mxCell id="{cid}" value="{esc(label)}" style="{style}" '
        f'edge="1" parent="1" source="{src}" target="{dst}">'
        f'<mxGeometry relative="1" as="geometry"/></mxCell>'
    )


def callout(x: int, y: int, w: int, h: int, text: str,
            color: tuple[str, str] = C.NOTE, fontsize: int = 12) -> str:
    """A callout box. Uses dark text on light fill (readable on dark slide BG)."""
    fill, stroke = color
    cid = _next_id("c")
    style = (
        f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
        f"fontSize={fontsize};fontColor=#111;align=center;verticalAlign=middle;"
        f"spacingLeft=12;spacingRight=12;spacingTop=8;spacingBottom=8;strokeWidth=1.5;"
    )
    return (
        f'<mxCell id="{cid}" value="{esc(text)}" style="{style}" '
        f'vertex="1" parent="1">'
        f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
    )


def label_text(x: int, y: int, w: int, h: int, text: str, *,
               fontsize: int = 12, italic: bool = False, color: str = "#a0a8b8") -> str:
    """Free text label. Default color is dim grey - readable on either light or dark BG."""
    cid = _next_id("l")
    style = (
        f"text;html=1;align=center;whiteSpace=wrap;fontSize={fontsize};"
        f"fontStyle={'2' if italic else '0'};fontColor={color};"
    )
    return (
        f'<mxCell id="{cid}" value="{esc(text)}" style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
    )


def render(name: str, cells: list[str], width: int = 1100, height: int = 700) -> str:
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


# ===========================================================================
# Diagram 1: Meet the cast
# ===========================================================================
def p_cast():
    global _uid; _uid = 0
    cells = []
    # 4 persona cards in a row, vertically centered on a 600px-tall canvas
    base_y = 100
    spacing = 240
    start_x = 100
    cells += [persona_card(start_x + i * spacing, base_y, 200, 130, init, name, role, color)[0]
              for i, (init, name, role, color) in enumerate([
                  ("M", "Maya",  "Backend developer",     C.MAYA),
                  ("R", "Raj",   "Hungry customer",       C.RAJ),
                  ("P", "Priya", "Restaurant owner",      C.PRIYA),
                  ("S", "Sam",   "Delivery driver",       C.SAM),
              ])]

    captions = [
        "Builds LiveOrder's backend.\nDecides which pattern\nfor each feature.",
        "Orders biryani on his phone.\nWants live status\nand instant chat.",
        "Watches the kitchen tablet.\nGets notified instantly\nwhen a new order pays.",
        "On a scooter with the food.\nChats with the customer\nabout buzzer codes.",
    ]
    for i, cap in enumerate(captions):
        cells.append(label_text(start_x + i * spacing - 10, base_y + 150, 220, 70, cap,
                                fontsize=11, italic=True, color="#a0a8b8"))

    cells.append(callout(100, 380, 900, 80,
        "Each real-time pattern fits naturally in a moment of their day.\n"
        "Maya's job: pick the right pattern for each feature so Raj's experience feels live."))
    return render("p_cast", cells, 1100, 500)


# ===========================================================================
# Diagram 2: Polling - Raj refreshing Swiggy order
# ===========================================================================
def p_polling_swiggy():
    global _uid; _uid = 0
    cells = []
    raj_dev, raj_id = device(100, 100, 220, 110, "Raj's phone", "Customer", C.RAJ)
    cells.append(raj_dev)

    swiggy, swiggy_id = brand_box(800, 100, 220, 110, "Swiggy backend",
                                   "Order service", C.SWIGGY)
    cells.append(swiggy)

    # Two parallel arrows offset vertically - GET above, response below
    cells.append(arrow(raj_id, swiggy_id, "GET /orders/123  (every 2 seconds)",
                       thick=True, exit_y=0.3, entry_y=0.3))
    cells.append(arrow(swiggy_id, raj_id, '{"status": "cooking"}  (same status again)',
                       dashed=True, exit_y=0.7, entry_y=0.7))

    cells.append(callout(100, 270, 920, 110,
        "Of 25 polls during an order:\n"
        "  about 5 catch a real status change (placed -> confirmed -> cooking -> out for delivery -> delivered)\n"
        "  the other 20 return the same status as last time - that's 80% wasted requests."))

    cells.append(callout(100, 400, 920, 70,
        "When polling is fine\n"
        "Status updates that don't need sub-second latency. Small client counts. Backends that don't push."))
    return render("p_polling_swiggy", cells, 1120, 500)


# ===========================================================================
# Diagram 3: Long polling - Raj requesting Uber
# ===========================================================================
def p_long_polling_uber():
    global _uid; _uid = 0
    cells = []
    raj_dev, raj_id = device(100, 100, 220, 110, "Raj's phone", "Tap 'Request ride'", C.RAJ)
    cells.append(raj_dev)

    uber, uber_id = brand_box(800, 100, 220, 110, "Uber dispatch",
                              "Matching service", C.UBER)
    cells.append(uber)

    cells.append(arrow(raj_id, uber_id,
                       "POST /rides   (then the request just hangs...)",
                       thick=True, exit_y=0.3, entry_y=0.3))
    cells.append(arrow(uber_id, raj_id,
                       '6 seconds later:  {"driver": "Sam", "vehicle": "TN-09-..."}',
                       dashed=True, thick=True, exit_y=0.7, entry_y=0.7))

    cells.append(callout(100, 270, 920, 100,
        "ONE request instead of many\n"
        "Short polling would have fired ~6 requests at 1s interval, 5 of them empty.\n"
        "Long polling sent 1, got the answer the moment a driver accepted, no waste."))

    cells.append(callout(100, 390, 920, 80,
        "Watch out\n"
        "Server must use async I/O (one held connection per rider). Server's timeout MUST be shorter "
        "than the load-balancer's idle timeout, or the LB cuts the connection first."))
    return render("p_long_polling_uber", cells, 1120, 500)


# ===========================================================================
# Diagram 4: Webhook - Stripe pays for Raj's biryani
# ===========================================================================
def p_webhook_stripe():
    global _uid; _uid = 0
    cells = []
    raj_dev, raj_id = device(60, 60, 170, 80, "Raj pays", "Tap 'Pay 450 INR'", C.RAJ)
    cells.append(raj_dev)

    stripe, stripe_id = brand_box(310, 60, 200, 80, "Stripe",
                                   "Payment processor", C.STRIPE)
    cells.append(stripe)

    maya_be, maya_id = brand_box(580, 170, 220, 100, "Maya's backend",
                                  "POST /webhooks/stripe", C.BACKEND)
    cells.append(maya_be)

    priya_dev, priya_id = device(900, 60, 170, 80, "Priya's tablet",
                                  "Restaurant kitchen", C.PRIYA)
    cells.append(priya_dev)

    cells.append(arrow(raj_id, stripe_id, "card details"))
    cells.append(arrow(stripe_id, maya_id,
                       "POST signed event  payment_intent.succeeded", thick=True))
    cells.append(arrow(maya_id, priya_id,
                       "kitchen alert: new paid order #1234",
                       dashed=True, thick=True))

    cells.append(callout(60, 300, 1010, 50,
        "Maya's backend has 5-10 seconds to respond 200. She verifies the HMAC, "
        "writes to a queue, returns 200. The kitchen notification happens asynchronously."))

    cells.append(callout(60, 370, 1010, 130,
        "The 4 webhook rules\n\n"
        "1. Verify the signature (HMAC-SHA256 of the body with a shared secret).\n"
        "2. Dedup by event id - Stripe will sometimes deliver the same event twice.\n"
        "3. Return 200 fast - queue real work; don't do it in the handler.\n"
        "4. Return 200 (not 5xx) for events you don't care about; 5xx triggers retries."))
    return render("p_webhook_stripe", cells, 1140, 530)


# ===========================================================================
# Diagram 5: SSE - Raj watching live order status
# ===========================================================================
def p_sse_order():
    global _uid; _uid = 0
    cells = []
    raj_dev, raj_id = device(100, 100, 220, 110, "Raj's phone",
                              "Order tracking screen", C.RAJ)
    cells.append(raj_dev)

    maya_be, maya_id = brand_box(800, 100, 220, 110, "Maya's backend",
                                  "GET /orders/123/stream", C.BACKEND)
    cells.append(maya_be)

    cells.append(arrow(raj_id, maya_id,
                       "GET /orders/123/stream  Accept: text/event-stream",
                       exit_y=0.3, entry_y=0.3))
    cells.append(arrow(maya_id, raj_id,
                       'event: status   data: {"status": "cooking"}',
                       dashed=True, exit_y=0.7, entry_y=0.7))

    cells.append(callout(100, 270, 920, 100,
        "Same one HTTP connection.  As the order progresses, the server pushes an event for each transition:\n\n"
        "   paid  ->  restaurant_confirmed  ->  cooking  ->  out_for_delivery  ->  delivered\n\n"
        "Raj's phone sees each update within ~50ms. Zero polling.",
        color=("#d5e8d4", "#82b366")))

    cells.append(callout(100, 390, 920, 80,
        "Bonus: if the connection drops (subway tunnel), the browser auto-reconnects and sends "
        "Last-Event-ID. The server picks up exactly where it left off."))
    return render("p_sse_order", cells, 1120, 500)


# ===========================================================================
# Diagram 6: SSE for LLM - food recommender streams to Raj
# ===========================================================================
def p_sse_llm():
    global _uid; _uid = 0
    cells = []
    raj_dev, raj_id = device(60, 110, 200, 110, "Raj's phone",
                              "AI food recommender chat", C.RAJ)
    cells.append(raj_dev)

    maya_be, maya_id = brand_box(420, 110, 220, 110, "Maya's backend",
                                  "Vercel-AI-SDK style proxy", C.BACKEND)
    cells.append(maya_be)

    openai, openai_id = brand_box(800, 110, 220, 110, "OpenAI",
                                   "gpt-4o-mini  stream=True", C.OPENAI)
    cells.append(openai)

    # Raj <-> Maya pair (offset)
    cells.append(arrow(raj_id, maya_id, "POST /chat   {prompt}",
                       exit_y=0.3, entry_y=0.3))
    cells.append(arrow(maya_id, raj_id, "SSE: token, token, ...   (relayed)",
                       dashed=True, thick=True, exit_y=0.7, entry_y=0.7))

    # Maya <-> OpenAI pair (offset)
    cells.append(arrow(maya_id, openai_id, "messages.create  stream=True",
                       exit_y=0.3, entry_y=0.3))
    cells.append(arrow(openai_id, maya_id, "SSE: token, token, ...",
                       dashed=True, exit_y=0.7, entry_y=0.7))

    cells.append(callout(60, 280, 960, 110,
        "Why proxy through Maya's backend instead of letting the browser call OpenAI directly?\n\n"
        "  1.  The API key never reaches the browser.\n"
        "  2.  Maya can log/filter/rate-limit prompts.\n"
        "  3.  Cookies and domain stay simple - the browser only talks to liveorder.app."))
    return render("p_sse_llm", cells, 1080, 420)


# ===========================================================================
# Diagram 7: WebSocket - Raj <-> Sam chat
# ===========================================================================
def p_ws_chat():
    global _uid; _uid = 0
    cells = []
    raj_dev, raj_id = device(60, 110, 200, 110, "Raj's phone",
                              "Customer", C.RAJ)
    cells.append(raj_dev)

    maya_be, maya_id = brand_box(440, 110, 200, 110, "Maya's backend",
                                  "WS /chat/orderXYZ", C.BACKEND)
    cells.append(maya_be)

    sam_dev, sam_id = device(820, 110, 200, 110, "Sam's phone",
                              "Driver", C.SAM)
    cells.append(sam_dev)

    # Raj sends -> Maya broadcasts to Sam (top arrows)
    cells.append(arrow(raj_id, maya_id, '"Apartment 5C, buzzer broken"',
                       thick=True, exit_y=0.25, entry_y=0.25))
    cells.append(arrow(maya_id, sam_id, "broadcast",
                       dashed=True, thick=True, exit_y=0.25, entry_y=0.25))

    # Sam sends -> Maya broadcasts to Raj (bottom arrows)
    cells.append(arrow(maya_id, raj_id, "broadcast",
                       dashed=True, thick=True, exit_y=0.75, entry_y=0.75))
    cells.append(arrow(sam_id, maya_id, '"Got it, calling now"',
                       thick=True, exit_y=0.75, entry_y=0.75))

    cells.append(callout(60, 280, 960, 80,
        "Polling: Raj would refresh every few seconds (laggy + wasteful).\n"
        "SSE: Sam could push to Raj, but Raj couldn't push back - dead-end for chat.\n"
        "WebSocket: both ways, low overhead per message, made for this.",
        color=("#dae8fc", "#6c8ebf")))

    cells.append(callout(60, 380, 960, 70,
        "The cost: one open TCP connection per connected person. 50K users = real RAM. "
        "Use WebSocket only when truly bidirectional. SSE is fine for one-way streaming."))
    return render("p_ws_chat", cells, 1080, 480)


# ===========================================================================
# Diagram 8: Decision tree with Maya
# ===========================================================================
def p_decision_with_persona():
    global _uid; _uid = 0
    cells = []
    # The decision shape — same as our other decision matrix but with Maya's framing
    q_style = ("rhombus;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;"
               "fontSize=13;fontStyle=1;strokeWidth=1.5;")

    PAGE_W = 1200
    CENTER_X = PAGE_W // 2 - 110
    LEFT_X, RIGHT_X = 60, PAGE_W - 60 - 220

    def diamond(x, y, text):
        cid = _next_id("q")
        return (
            f'<mxCell id="{cid}" value="{esc(text)}" style="{q_style}" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="220" height="80" as="geometry"/></mxCell>'
        ), cid

    def leaf(x, y, text, color):
        fill, stroke = color
        cid = _next_id("lf")
        style = (f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
                 f"fontSize=12;fontStyle=1;align=center;verticalAlign=middle;strokeWidth=1.5;")
        return (
            f'<mxCell id="{cid}" value="{esc(text)}" style="{style}" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="220" height="50" as="geometry"/></mxCell>'
        ), cid

    def edge(src, dst, label):
        cid = _next_id("e")
        return (f'<mxCell id="{cid}" value="{esc(label)}" '
                f'style="endArrow=classic;html=1;rounded=0;strokeColor=#333;strokeWidth=1.6;'
                f'fontSize=11;edgeStyle=orthogonalEdgeStyle;" edge="1" parent="1" '
                f'source="{src}" target="{dst}">'
                f'<mxGeometry relative="1" as="geometry"/></mxCell>')

    q1_xml, q1 = diamond(CENTER_X, 110, "Does this feature need real-time updates?")
    cells.append(q1_xml)
    rest_xml, rest = leaf(LEFT_X, 125, "REST\n(plain request/response)", C.GREY)
    cells.append(rest_xml)
    cells.append(edge(q1, rest, "no"))

    q2_xml, q2 = diamond(CENTER_X, 240, "Who fires the event?")
    cells.append(q2_xml)
    cells.append(edge(q1, q2, "yes"))

    wh_xml, wh = leaf(RIGHT_X, 255, "WEBHOOK\nStripe paid, GitHub PR, etc.", C.STRIPE)
    cells.append(wh_xml)
    cells.append(edge(q2, wh, "external service"))

    q3_xml, q3 = diamond(CENTER_X, 370, "Which way does data flow?")
    cells.append(q3_xml)
    cells.append(edge(q2, q3, "your own server"))

    poll_xml, poll = leaf(LEFT_X, 385, "POLLING\nclient asks on a timer", C.SWIGGY)
    cells.append(poll_xml)
    cells.append(edge(q3, poll, "client to server only"))

    q4_xml, q4 = diamond(CENTER_X, 500, "One-way push, or two-way chat?")
    cells.append(q4_xml)
    cells.append(edge(q3, q4, "server to client"))

    sse_xml, sse = leaf(LEFT_X, 515, "SSE\nlive status, LLM streaming", C.OPENAI)
    cells.append(sse_xml)
    cells.append(edge(q4, sse, "one-way"))

    ws_xml, ws = leaf(RIGHT_X, 515, "WEBSOCKET\nchat, voice, collab", C.MAYA)
    cells.append(ws_xml)
    cells.append(edge(q4, ws, "two-way"))

    cells.append(callout(60, 620, 1080, 70,
        "Maya's rule of thumb: default to SSE for server-to-client. Reach for WebSocket only when "
        "you genuinely need bidirectional (chat/voice/games/collab). Polling for batch checks. Webhooks for external triggers."))
    return render("p_decision_with_persona", cells, PAGE_W, 720)


# ===========================================================================
# Diagram 9: LiveOrder - one app, all 4 patterns in Raj's order journey
# ===========================================================================
def p_liveorder_full():
    """LiveOrder full architecture - radial layout with the backend at the centre."""
    global _uid; _uid = 0
    cells = []

    # Layout: backend in the centre. Personas left + bottom. External services right + top.
    # Wider spacing so labels don't collide.
    BW, BH = 220, 80
    raj_dev, raj_id     = device(80,  80,  BW, BH, "Raj's phone",    "Customer app", C.RAJ)
    sam_dev, sam_id     = device(80,  290, BW, BH, "Sam's phone",    "Driver app",   C.SAM)
    priya_dev, priya_id = device(80,  500, BW, BH, "Priya's tablet", "Kitchen",      C.PRIYA)
    cells += [raj_dev, sam_dev, priya_dev]

    maya_be, maya_id = brand_box(580, 290, 260, 100, "Maya's backend",
                                  "FastAPI / Node", C.BACKEND)
    cells.append(maya_be)

    stripe, stripe_id = brand_box(1120, 80,  220, 80, "Stripe", "Payments", C.STRIPE)
    openai, openai_id = brand_box(1120, 290, 220, 80, "OpenAI", "Food recommender", C.OPENAI)
    queue, queue_id   = brand_box(580,  500, 260, 80, "Redis + Postgres",
                                   "Background workers", C.INFRA)
    cells += [stripe, openai, queue]

    # All edges - one labelled arrow per channel.
    # Raj uses REST + SSE for order status; WS for chat.
    cells.append(arrow(raj_id, maya_id, "REST + SSE (orders)",
                       thick=True, exit_y=0.5, entry_y=0.15))
    cells.append(arrow(raj_id, maya_id, "WS (chat)",
                       thick=True, both=True, exit_y=0.85, entry_y=0.35))

    # Sam uses WS for chat
    cells.append(arrow(sam_id, maya_id, "WS (driver chat)",
                       thick=True, both=True, exit_y=0.5, entry_y=0.55))

    # Priya gets SSE alerts from backend
    cells.append(arrow(maya_id, priya_id, "SSE (kitchen alerts)",
                       dashed=True, exit_y=0.85, entry_y=0.5))

    # Stripe pushes webhooks in
    cells.append(arrow(stripe_id, maya_id, "WEBHOOK  payment_intent.succeeded",
                       thick=True, exit_y=0.5, entry_y=0.15))

    # Backend <-> OpenAI (stream=True upstream, tokens downstream)
    cells.append(arrow(maya_id, openai_id, "stream=True",
                       thick=True, exit_y=0.3, entry_y=0.3))
    cells.append(arrow(openai_id, maya_id, "SSE tokens",
                       dashed=True, exit_y=0.7, entry_y=0.7))

    # Backend -> queue
    cells.append(arrow(maya_id, queue_id, "enqueue / SQL",
                       exit_y=0.85, entry_y=0.5))

    cells.append(callout(80, 620, 1260, 50,
        "Read the labels: REST + SSE + WS + WEBHOOK all in one app. Each pattern doing what it's best at.",
        color=C.NOTE, fontsize=12))
    return render("p_liveorder_full", cells, 1360, 700)


# ===========================================================================
# Diagram 10: MCP - Maya's tools for Claude Desktop
# ===========================================================================
def p_mcp_persona():
    global _uid; _uid = 0
    cells = []
    claude, claude_id = brand_box(100, 90, 260, 110,
                                   "Claude Desktop",
                                   "MCP host (calls tools)", C.OPENAI)
    cells.append(claude)

    maya_be, maya_id = brand_box(700, 90, 260, 110,
                                  "Maya's MCP server",
                                  "Exposes liveorder.query_orders", C.BACKEND)
    cells.append(maya_be)

    cells.append(arrow(claude_id, maya_id,
                       "POST /mcp  tools/call  { restaurant_id: 42 }",
                       thick=True, exit_y=0.3, entry_y=0.3))
    cells.append(arrow(maya_id, claude_id,
                       "SSE: progress, progress, result",
                       dashed=True, thick=True, exit_y=0.7, entry_y=0.7))

    cells.append(callout(100, 250, 860, 110,
        "Why SSE for MCP?\n"
        "  Tool calls take real time (DB queries, web fetches, summarising).\n"
        "  One tool call typically produces many progress events.\n"
        "  Standard HTTP - no WebSocket upgrade. Easy to host anywhere.\n"
        "  Resumable via Last-Event-ID on reconnect."))

    cells.append(callout(100, 380, 860, 80,
        "From the user's perspective, Claude asks 'how many veg orders did Priya's restaurant have last week?' "
        "and gets a real answer that came from Maya's database. The MCP transport is SSE the whole way."))
    return render("p_mcp_persona", cells, 1060, 480)


# ===========================================================================
# Main
# ===========================================================================
def main():
    builders = [
        ("p_cast",                       p_cast),
        ("p_polling_swiggy",             p_polling_swiggy),
        ("p_long_polling_uber",          p_long_polling_uber),
        ("p_webhook_stripe",             p_webhook_stripe),
        ("p_sse_order",                  p_sse_order),
        ("p_sse_llm",                    p_sse_llm),
        ("p_ws_chat",                    p_ws_chat),
        ("p_decision_with_persona",      p_decision_with_persona),
        ("p_liveorder_full",             p_liveorder_full),
        ("p_mcp_persona",                p_mcp_persona),
    ]

    from xml.etree import ElementTree as ET
    for name, builder in builders:
        content = builder()
        out = OUT_DIR / f"{name}.drawio"
        out.write_text(content)
        # XML validate
        ET.fromstring(content)
        print(f"  ✓ {out.relative_to(ROOT.parent)}  ({len(content):,} bytes)")

    print(f"\nwrote {len(builders)} persona diagrams to {OUT_DIR}/")


if __name__ == "__main__":
    main()
