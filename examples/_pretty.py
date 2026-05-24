"""Shared pretty-print helpers for the workshop client scripts.

Each example imports the small set of functions here so output looks
consistent across all 7 examples.

Design:
  - Banner / demo headers for visual hierarchy
  - REQUEST / RESPONSE / LESSON labelled lines for the common shapes
  - Colour-coded status codes (green 2xx, cyan 3xx, red 4xx/5xx)
  - Colours auto-disable when stdout is not a TTY (so qa.sh greps work
    cleanly and so output piped to files doesn't have escape codes)

Usage:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from _pretty import (
        banner, demo, divider, hr,
        request_line, request_header, request_body,
        response_line, response_body, show_response,
        lesson, note, info, ok, fail, warn,
    )
"""
from __future__ import annotations

import json
import os
import sys
import textwrap

WIDTH = 78

# ----- colour detection ---------------------------------------------------
USE_COLOR = (
    sys.stdout.isatty()
    and os.environ.get("NO_COLOR") is None
    and os.environ.get("TERM") not in (None, "dumb")
)


def _c(code: str) -> str:
    return code if USE_COLOR else ""


RESET   = _c("\033[0m")
BOLD    = _c("\033[1m")
DIM     = _c("\033[2m")

# Standard colours (saturated, slightly darker)
CYAN    = _c("\033[36m")
GREEN   = _c("\033[32m")
YELLOW  = _c("\033[33m")
RED     = _c("\033[31m")
MAGENTA = _c("\033[35m")
BLUE    = _c("\033[34m")
WHITE   = _c("\033[37m")
GREY    = _c("\033[90m")

# Bright variants (more vibrant; better for callouts that need to pop)
BRIGHT_CYAN   = _c("\033[96m")
BRIGHT_GREEN  = _c("\033[92m")
BRIGHT_YELLOW = _c("\033[93m")
BRIGHT_RED    = _c("\033[91m")
BRIGHT_BLUE   = _c("\033[94m")

# Semantic aliases used through the rest of the file.
# Inspired by modern dev tools (gh CLI, Vercel, Stripe CLI):
#   - cyan for structure
#   - amber/yellow for "your action" + warnings
#   - green for success / agent output
#   - red only for real errors
#   - no magenta in chrome (some downstream files still import it for accents)
PRIMARY_BAR     = BRIGHT_CYAN   # banner top and bottom
SECTION_BAR     = CYAN          # per-demo headers
HIGHLIGHT_LABEL = BRIGHT_YELLOW  # LESSON callouts - highlighter style
REQUEST_COLOR   = YELLOW
INFO_COLOR      = BRIGHT_CYAN
OK_COLOR        = BRIGHT_GREEN
FAIL_COLOR      = BRIGHT_RED
WARN_COLOR      = BRIGHT_YELLOW


# ----- headings & dividers -----------------------------------------------
def banner(title: str, subtitle: str | None = None) -> None:
    """Top-level banner for the whole script. Bright-cyan double-bar."""
    bar = "═" * WIDTH
    print()
    print(f"{PRIMARY_BAR}{bar}{RESET}")
    print(f"  {BOLD}{title}{RESET}")
    if subtitle:
        print(f"  {DIM}{subtitle}{RESET}")
    print(f"{PRIMARY_BAR}{bar}{RESET}")


def demo(num: int, title: str) -> None:
    """Per-demo header. Cyan single-bar with bold step label inline."""
    label_text = f"  Step {num}  -  {title}  "
    bar_len = max(2, WIDTH - len(label_text) - 4)
    print()
    print(f"{SECTION_BAR}━━{BOLD}{label_text}{RESET}{SECTION_BAR}{'━' * bar_len}{RESET}")
    print()


def divider() -> None:
    """Subtle dim grey horizontal rule between sections."""
    print(f"{DIM}{'─' * WIDTH}{RESET}")


def hr() -> None:
    """Alias of divider for consistency."""
    divider()


# ----- request / response blocks -----------------------------------------
def request_line(method: str, url: str) -> None:
    print(f"  {REQUEST_COLOR}{BOLD}REQUEST {RESET}  {REQUEST_COLOR}{method:<6}{RESET} {url}")


def request_header(name: str, value: str) -> None:
    print(f"            {DIM}>{RESET} {name}: {value}")


def request_body(obj) -> None:
    print(f"            {DIM}> Body:{RESET}")
    if isinstance(obj, (dict, list)):
        text = json.dumps(obj, indent=2)
    else:
        text = str(obj)
    for line in text.splitlines():
        print(f"              {line}")


def response_line(status: int, reason: str = "", content_type: str = "") -> None:
    if 200 <= status < 300:
        col = BRIGHT_GREEN
    elif 300 <= status < 400:
        col = BRIGHT_CYAN
    elif 400 <= status < 500:
        col = BRIGHT_YELLOW
    else:
        col = BRIGHT_RED
    ct = f"   {DIM}({content_type}){RESET}" if content_type else ""
    print(f"  {col}{BOLD}RESPONSE{RESET}  {col}{status} {reason}{RESET}{ct}")


def response_body(obj_or_text) -> None:
    if isinstance(obj_or_text, (dict, list)):
        text = json.dumps(obj_or_text, indent=2)
    else:
        text = str(obj_or_text)
    for line in text.splitlines():
        print(f"            {line}")


def show_response(r) -> None:
    """Combined helper: status line + body, from an httpx Response."""
    ct = r.headers.get("content-type", "?").split(";")[0]
    response_line(r.status_code, r.reason_phrase, ct)
    try:
        response_body(r.json())
    except Exception:
        response_body(r.text[:400])


# ----- labelled lines ----------------------------------------------------
def lesson(text: str) -> None:
    """The takeaway sentence for a demo.

    Rendered with a bright-yellow 'highlighter' label so the takeaway
    stands out from the request/response lines above it.
    """
    print()
    wrapped = textwrap.wrap(text, width=WIDTH - 14)
    for i, line in enumerate(wrapped):
        prefix = f"  {HIGHLIGHT_LABEL}{BOLD}LESSON  {RESET}  " if i == 0 else "            "
        print(f"{prefix}{line}")


def note(text: str) -> None:
    """A dim grey informational line, indented under the request/response block."""
    print(f"            {DIM}{text}{RESET}")


def info(text: str) -> None:
    print(f"  {INFO_COLOR}{BOLD}INFO    {RESET}  {text}")


def ok(text: str) -> None:
    print(f"  {OK_COLOR}{BOLD}OK      {RESET}  {text}")


def fail(text: str) -> None:
    print(f"  {FAIL_COLOR}{BOLD}FAIL    {RESET}  {text}")


def warn(text: str) -> None:
    print(f"  {WARN_COLOR}{BOLD}WARN    {RESET}  {text}")


def event(label_text: str, content: str = "", color: str = CYAN) -> None:
    """Used by SSE / WS clients to print received events."""
    print(f"  {color}{BOLD}{label_text:9s}{RESET} {content}")


def summary_table(rows: list[tuple[str, str]]) -> None:
    """Print a 2-column summary table."""
    if not rows:
        return
    key_width = max(len(k) for k, _ in rows)
    print()
    for k, v in rows:
        print(f"  {DIM}{k:<{key_width}}{RESET}   {v}")
    print()


def pause(message: str = "Press ENTER for next step") -> None:
    """Pause for the user between demos so a presenter can talk in between.

    Skipped automatically when:
      - stdin is not a TTY (e.g. qa.sh captures output via $(...))
      - the env var NO_PAUSE is set
    """
    if not sys.stdin.isatty() or os.environ.get("NO_PAUSE"):
        return
    print()
    print(f"  {DIM}{message}...{RESET}", end="", flush=True)
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)


def preflight_check(base_url: str, expected_keyword: str = "") -> None:
    """Verify the server at base_url is reachable and is the right one.

    Hits GET / and checks the response. Prints a clear, actionable error
    and exits if anything is off. This catches the very common case of an
    OLD uvicorn from a previous example still being bound to the port, so
    the client sees mysterious 404s on endpoints the new server has but
    the old one didn't.
    """
    import httpx
    port = base_url.rsplit(":", 1)[-1].split("/")[0]

    try:
        r = httpx.get(f"{base_url}/", timeout=3)
    except httpx.HTTPError as e:
        print()
        print(f"  {RED}{BOLD}ERROR{RESET}     could not reach the server at {base_url}")
        print(f"            ({e})")
        print()
        print(f"  {YELLOW}{BOLD}FIX{RESET}       start the server in another terminal:")
        print()
        print(f"            {CYAN}uvicorn server:app --port {port}{RESET}")
        print()
        sys.exit(1)

    if r.status_code != 200:
        print()
        print(f"  {RED}{BOLD}ERROR{RESET}     server at {base_url} returned {r.status_code} for GET /")
        print(f"            (expected 200 with an info page)")
        print()
        sys.exit(1)

    if expected_keyword and expected_keyword.lower() not in r.text.lower():
        print()
        print(f"  {RED}{BOLD}ERROR{RESET}     port {port} is serving the WRONG server.")
        print(f"            expected the response to mention {expected_keyword!r}")
        print(f"            but got: {r.text[:120]}{'...' if len(r.text) > 120 else ''}")
        print()
        print(f"  {YELLOW}{BOLD}LIKELY CAUSE{RESET}  an OLD uvicorn from a previous example is still")
        print(f"            running on port {port}. Two-step fix:")
        print()
        print(f"            {CYAN}1.  pkill -f uvicorn{RESET}                    {DIM}# kill all stale servers{RESET}")
        print(f"            {CYAN}2.  uvicorn server:app --port {port}{RESET}     {DIM}# start the right one (from THIS folder){RESET}")
        print(f"            {CYAN}3.  python client.py{RESET}                     {DIM}# rerun this script{RESET}")
        print()
        sys.exit(1)
