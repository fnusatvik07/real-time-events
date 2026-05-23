"""Automated QA for the diagrams.

Checks each .drawio file for:
  1. XML well-formedness
  2. All vertex elements within page bounds
  3. No overlapping vertex (box / lane / callout) elements
     (edges are allowed to cross things; vertices should not)
  4. Page height is not wildly oversized (>= max_content_y + 20, <= max_content_y + 120)
  5. Every edge source/target references an existing element
"""
from __future__ import annotations

import sys
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).parent

# Tolerance for "this is basically the same element": same id reported once
# Elements that are intentionally containers (lanes) are allowed to contain other elements.
LANE_STYLE_SUBSTR = "shape=swimlane"
TEXT_STYLE_SUBSTR = "text;html=1"  # bare text labels - overlap OK


def is_lane(style: str) -> bool:
    return LANE_STYLE_SUBSTR in style


def is_text_only(style: str) -> bool:
    return style.startswith("text;") or ";text;" in style


def rect_overlap(a, b) -> bool:
    """a,b are (x, y, w, h). Returns True if rectangles overlap (not just touch)."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay)


def is_contained(inner, outer) -> bool:
    """inner is contained inside outer (>=80% of inner's area within outer)."""
    ix, iy, iw, ih = inner
    ox, oy, ow, oh = outer
    sx = max(ix, ox); sy = max(iy, oy)
    ex = min(ix + iw, ox + ow); ey = min(iy + ih, oy + oh)
    if sx >= ex or sy >= ey:
        return False
    inter = (ex - sx) * (ey - sy)
    inner_area = iw * ih
    return inter / inner_area >= 0.8


def check_file(path: Path) -> list[str]:
    issues: list[str] = []
    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        return [f"XML parse error: {e}"]

    root = tree.getroot()
    diag = root.find("diagram")
    if diag is None:
        return ["No <diagram> element"]
    model = diag.find("mxGraphModel")
    if model is None:
        return ["No <mxGraphModel>"]
    page_w = int(model.attrib.get("pageWidth", 0))
    page_h = int(model.attrib.get("pageHeight", 0))

    vertices = []  # (id, x, y, w, h, style)
    ids = {"0", "1"}
    edges = []

    for cell in model.iter("mxCell"):
        cid = cell.attrib.get("id")
        if cid:
            ids.add(cid)
        style = cell.attrib.get("style", "")
        is_vertex = cell.attrib.get("vertex") == "1"
        is_edge = cell.attrib.get("edge") == "1"
        geom = cell.find("mxGeometry")
        if is_vertex and geom is not None:
            try:
                x = float(geom.attrib.get("x", 0))
                y = float(geom.attrib.get("y", 0))
                w = float(geom.attrib.get("width", 0))
                h = float(geom.attrib.get("height", 0))
            except ValueError:
                continue
            vertices.append((cid, x, y, w, h, style))
        elif is_edge:
            edges.append((
                cid,
                cell.attrib.get("source"),
                cell.attrib.get("target"),
            ))

    # 1. Bounds check
    max_y = 0
    for cid, x, y, w, h, style in vertices:
        if x < 0 or y < 0:
            issues.append(f"{cid}: negative coords ({x},{y})")
        if x + w > page_w + 1:
            issues.append(f"{cid}: extends past right edge (x+w={x+w} > pageWidth={page_w})")
        if y + h > page_h + 1:
            issues.append(f"{cid}: extends past bottom (y+h={y+h} > pageHeight={page_h})")
        max_y = max(max_y, y + h)

    # 2. Page-height appropriateness
    margin = page_h - max_y
    if margin > 120:
        issues.append(
            f"page is taller than needed: content ends at y={max_y}, page is {page_h} (margin {margin}px) - trim PAGE_H")
    if margin < 10:
        issues.append(
            f"page too short: content ends at y={max_y}, page is {page_h} (margin {margin}px)")

    # 3. Overlap check (vertex on vertex, excluding lanes-as-containers and text labels)
    body = [(cid, x, y, w, h, style) for (cid, x, y, w, h, style) in vertices]
    for i, a in enumerate(body):
        for b in body[i + 1:]:
            cid_a, ax, ay, aw, ah, sa = a
            cid_b, bx, by, bw, bh, sb = b
            # Allow text-only labels to overlap with other things
            if is_text_only(sa) or is_text_only(sb):
                continue
            # Allow lane to contain non-lane elements
            if is_lane(sa) and not is_lane(sb):
                if is_contained((bx, by, bw, bh), (ax, ay, aw, ah)):
                    continue
            if is_lane(sb) and not is_lane(sa):
                if is_contained((ax, ay, aw, ah), (bx, by, bw, bh)):
                    continue
            if rect_overlap((ax, ay, aw, ah), (bx, by, bw, bh)):
                issues.append(
                    f"overlap: {cid_a} ({ax},{ay},{aw}x{ah}) vs {cid_b} ({bx},{by},{bw}x{bh})")

    # 4. Edge reference check
    for cid, src, tgt in edges:
        if src and src not in ids:
            issues.append(f"edge {cid}: source '{src}' does not exist")
        if tgt and tgt not in ids:
            issues.append(f"edge {cid}: target '{tgt}' does not exist")

    return issues


def main():
    files = sorted(ROOT.glob("*.drawio"))
    total_issues = 0
    for f in files:
        issues = check_file(f)
        if issues:
            print(f"\n=== {f.name} ({len(issues)} issue{'s' if len(issues) != 1 else ''}) ===")
            for it in issues:
                print(f"  - {it}")
            total_issues += len(issues)
        else:
            print(f"OK  {f.name}")

    print()
    if total_issues == 0:
        print("ALL DIAGRAMS PASSED QA")
        sys.exit(0)
    else:
        print(f"TOTAL: {total_issues} issue(s) across diagrams")
        sys.exit(1)


if __name__ == "__main__":
    main()
