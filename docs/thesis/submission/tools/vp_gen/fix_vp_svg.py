"""Clean up Visual Paradigm SVG exports before they are rasterised for the thesis.

VP CE's SVG export (Batik) has three defects that show in print:
  * every connector carries a clip-path that cuts holes where VP *thinks* labels sit
    and clips its own bounding box, so dashed lines have gaps and one stroke of many
    arrow heads is missing;
  * labels are positioned with Java font metrics, so in the browser they overlap
    lines, ellipses and each other;
  * all text is 11 px on a canvas 800-1600 px wide, about 5 pt once printed.

This tool keeps VP's drawing (shapes, colours, strokes, arrow heads) and:
  1. removes every clip-path;
  2. enlarges text, re-centres it in its shape and widens shapes when needed;
  3. re-lays out use case diagrams (LAYOUTS below) so no association or
     include/extend line crosses another use case, recomputing every connector
     against the ellipse/actor border;
  4. places each connector label at a free spot beside its line;
  5. replaces the glyph outlines inside notes with real wrapped text.

    python fix_vp_svg.py <in_dir> <out_dir>
"""
from __future__ import annotations

import html
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import ImageFont

SVG = "http://www.w3.org/2000/svg"
XL = "http://www.w3.org/1999/xlink"
ET.register_namespace("", SVG)
ET.register_namespace("xlink", XL)
_ARIAL = ImageFont.truetype("arial.ttf", 200)
_ARIAL_B = ImageFont.truetype("arialbd.ttf", 200)


def N(tag):
    return f"{{{SVG}}}{tag}"


def local(tag):
    return tag.split("}")[-1]


def text_w(s, size, bold=False):
    return (_ARIAL_B if bold else _ARIAL).getlength(s) * size / 200


def fnum(v):
    return float(str(v).replace("px", ""))


def fmt(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


TR = re.compile(r"^\s*translate\(([-\d.]+)[ ,]+([-\d.]+)\)\s*$")


def get_tr(el):
    t = el.get("transform")
    if not t:
        return (0.0, 0.0)
    m = TR.match(t)
    return (float(m[1]), float(m[2])) if m else None


def set_tr(el, x, y):
    el.set("transform", f"translate({fmt(x)},{fmt(y)})")


# ---------------------------------------------------------------------------
# geometry
# ---------------------------------------------------------------------------
class Box:
    def __init__(self, x0, y0, x1, y1):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1

    @property
    def w(self):
        return self.x1 - self.x0

    @property
    def h(self):
        return self.y1 - self.y0

    @property
    def cx(self):
        return (self.x0 + self.x1) / 2

    @property
    def cy(self):
        return (self.y0 + self.y1) / 2

    def union(self, o):
        if o is None:
            return self
        return Box(min(self.x0, o.x0), min(self.y0, o.y0), max(self.x1, o.x1), max(self.y1, o.y1))

    def grow(self, d):
        return Box(self.x0 - d, self.y0 - d, self.x1 + d, self.y1 + d)

    def overlaps(self, o):
        return self.x0 < o.x1 and o.x0 < self.x1 and self.y0 < o.y1 and o.y0 < self.y1

    def inside(self, o):
        return self.x0 >= o.x0 and self.y0 >= o.y0 and self.x1 <= o.x1 and self.y1 <= o.y1

    def __repr__(self):
        return f"Box({self.x0:.0f},{self.y0:.0f},{self.x1:.0f},{self.y1:.0f})"


def seg_hits_box(p, q, b: Box):
    """Liang-Barsky: does segment p-q pass through box b?"""
    x0, y0 = p
    dx, dy = q[0] - p[0], q[1] - p[1]
    t0, t1 = 0.0, 1.0
    for pp, qq in ((-dx, x0 - b.x0), (dx, b.x1 - x0), (-dy, y0 - b.y0), (dy, b.y1 - y0)):
        if pp == 0:
            if qq < 0:
                return False
        else:
            r = qq / pp
            if pp < 0:
                t0 = max(t0, r)
            else:
                t1 = min(t1, r)
            if t0 > t1:
                return False
    return True


def segs_cross(a, b, c, d):
    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    o1, o2, o3, o4 = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
    return o1 * o2 < 0 and o3 * o4 < 0


def ellipse_hits_box(cx, cy, rx, ry, b: Box):
    for i in range(7):
        for j in range(5):
            x = b.x0 + b.w * i / 6
            y = b.y0 + b.h * j / 4
            if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1:
                return True
    return b.x0 <= cx <= b.x1 and b.y0 <= cy <= b.y1


def seg_hits_ellipse(p, q, cx, cy, rx, ry, steps=80, margin=0.0):
    rx, ry = rx + margin, ry + margin
    for k in range(1, steps):
        t = k / steps
        x = p[0] + (q[0] - p[0]) * t
        y = p[1] + (q[1] - p[1]) * t
        if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 < 0.97:
            return True
    return False


# ---------------------------------------------------------------------------
# SVG model
# ---------------------------------------------------------------------------
def walk(el, ox=0.0, oy=0.0, size=11.0, weight="normal"):
    t = get_tr(el)
    if t is None:
        return
    ox, oy = ox + t[0], oy + t[1]
    if el.get("font-size"):
        size = fnum(el.get("font-size"))
    if el.get("font-weight"):
        weight = el.get("font-weight")
    yield el, ox, oy, size, weight
    for c in el:
        yield from walk(c, ox, oy, size, weight)


def prim_box(el, ox, oy, size=11.0, weight="normal"):
    tag = local(el.tag)
    g = lambda k, d=0: fnum(el.get(k, d))  # noqa: E731
    if tag == "rect":
        return Box(ox + g("x"), oy + g("y"), ox + g("x") + g("width"), oy + g("y") + g("height"))
    if tag == "ellipse":
        return Box(ox + g("cx") - g("rx"), oy + g("cy") - g("ry"), ox + g("cx") + g("rx"), oy + g("cy") + g("ry"))
    if tag == "circle":
        return Box(ox + g("cx") - g("r"), oy + g("cy") - g("r"), ox + g("cx") + g("r"), oy + g("cy") + g("r"))
    if tag == "line":
        return Box(ox + min(g("x1"), g("x2")), oy + min(g("y1"), g("y2")), ox + max(g("x1"), g("x2")), oy + max(g("y1"), g("y2")))
    if tag in ("polygon", "polyline", "path"):
        nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", el.get("points") or el.get("d") or "")]
        if len(nums) < 2:
            return None
        xs, ys = nums[0::2], nums[1::2]
        return Box(ox + min(xs), oy + min(ys), ox + max(xs), oy + max(ys))
    if tag == "image":
        return Box(ox + g("x"), oy + g("y"), ox + g("x") + g("width"), oy + g("y") + g("height"))
    if tag == "text":
        w = text_w(el.text or "", size, weight == "bold")
        x = ox + g("x")
        if el.get("text-anchor") == "middle":
            x -= w / 2
        y = oy + g("y")
        return Box(x, y - 0.8 * size, x + w, y + 0.25 * size)
    return None


class Shape:
    def __init__(self, g, kind, name):
        self.g, self.kind, self.name = g, kind, name
        self.extras = []        # sibling groups VP emits for the shape's text
        self.caption = None     # actor caption group

    def prims(self):
        for el, ox, oy, s, w in walk(self.g):
            if local(el.tag) not in ("g", "text"):
                yield el, ox, oy

    @property
    def box(self):
        b = None
        for el, ox, oy in self.prims():
            pb = prim_box(el, ox, oy)
            if pb:
                b = pb.union(b)
        return b

    def texts(self):
        for grp in [self.g] + self.extras:
            for el, ox, oy, s, w in walk(grp):
                if local(el.tag) == "text":
                    yield el, ox, oy, s, w

    def shift(self, dx, dy):
        for grp in [self.g] + self.extras + ([self.caption] if self.caption is not None else []):
            tops = [grp] if grp is not self.g else list(grp)
            for el in tops:
                t = get_tr(el) or (0, 0)
                set_tr(el, t[0] + dx, t[1] + dy)


class Conn:
    def __init__(self, g, kind, name):
        self.g, self.kind, self.name = g, kind, name
        self.label = None  # text group

    def lines(self):
        """absolute (p, q, is_head) for every line of the connector."""
        raw = []
        dashed = False
        for el, ox, oy, s, w in walk(self.g):
            da = el.get("stroke-dasharray")
            if local(el.tag) == "g" and da and da != "none":
                dashed = True
            if local(el.tag) == "line":
                p = (ox + fnum(el.get("x1")), oy + fnum(el.get("y1")))
                q = (ox + fnum(el.get("x2")), oy + fnum(el.get("y2")))
                raw.append((p, q, el.get("stroke-dasharray") == "none"))
        if dashed:
            return raw
        # solid connector: the head is the last two short lines leaving one point
        out = [(p, q, False) for p, q, _ in raw]
        if len(raw) >= 3:
            (p1, q1, _), (p2, q2, _) = raw[-2], raw[-1]
            if math.dist(p1, p2) < 0.5 and math.dist(p1, q1) < 16 and math.dist(p2, q2) < 16:
                out[-2] = (p1, q1, True)
                out[-1] = (p2, q2, True)
        return out

    def segments(self):
        segs = [(p, q) for p, q, head in self.lines() if not head]
        return segs or [(p, q) for p, q, _ in self.lines()]

    def heads(self):
        return [(p, q) for p, q, head in self.lines() if head]


class Diagram:
    def __init__(self, path: Path):
        self.path = path
        self.tree = ET.parse(path)
        self.root = self.tree.getroot()
        self.main = [c for c in self.root if local(c.tag) == "g"][0]
        self.shapes: list[Shape] = []
        self.conns: list[Conn] = []
        self.labels = []        # loose text groups that belong to connectors
        self.watermark = None
        self.background = None
        seen_conn = False
        loose = []
        for c in list(self.main):
            if local(c.tag) == "defs":
                continue
            mid = c.get("model-id") or ""
            if mid:
                data = json.loads(html.unescape(c.get("data")))
                kind, name = data.get("modelType"), data.get("name", "")
                if mid.startswith("shape-"):
                    self.shapes.append(Shape(c, kind, name))
                else:
                    self.conns.append(Conn(c, kind, name))
                    seen_conn = True
                continue
            if c.find(f".//{N('image')}") is not None:
                self.watermark = c
            elif c.find(N("rect")) is not None and self.background is None and not self.shapes:
                self.background = c
            elif seen_conn:
                self.labels.append(c)
            else:
                loose.append(c)
        # loose groups right after a shape with the same origin are that shape's text
        shape_origins = {}
        for s in self.shapes:
            firsts = [k for k in s.g if get_tr(k)]
            if firsts:
                shape_origins.setdefault(get_tr(firsts[0]), []).append(s)
        for grp in loose:
            t = get_tr(grp)
            if t in shape_origins:
                shape_origins[t][0].extras.append(grp)
                continue
            tb = self.group_box(grp)
            txt = "".join(t.text or "" for t in grp.iter(N("text"))).strip()
            # a caption that names a participant belongs to it
            named = [s for s in self.shapes if txt and s.name == txt and s.kind not in ("NOTE",)]
            if named:
                if named[0].kind == "Actor" and named[0].caption is None:
                    named[0].caption = grp
                else:
                    named[0].extras.append(grp)
                continue
            # otherwise the smallest shape that contains it (guards -> their operand)
            holders = [s for s in self.shapes if s.kind not in ("Activation",) and s.box is not None
                       and tb is not None and s.box.grow(1).x0 <= tb.cx <= s.box.grow(1).x1
                       and s.box.grow(1).y0 <= tb.cy <= s.box.grow(1).y1]
            if holders and txt:
                min(holders, key=lambda s: s.box.w * s.box.h).extras.append(grp)
                continue
            # actor captions: the nearest actor above
            best, dist = None, 1e9
            for s in self.shapes:
                b = s.box
                if b is None:
                    continue
                d = math.dist((b.cx, b.y1), (tb.cx, tb.y0))
                if d < dist:
                    best, dist = s, d
            if best is not None and best.kind == "Actor" and best.caption is None:
                best.caption = grp
            elif best is not None:
                best.extras.append(grp)
        # a text after the connectors that names a shape (state, partition) belongs to it
        conn_names = {c.name for c in self.conns}
        for grp in list(self.labels):
            txt = "".join(t.text or "" for t in grp.iter(N("text"))).strip()
            owner = [s for s in self.shapes if txt and s.name == txt and txt not in conn_names]
            if owner:
                owner[0].extras.append(grp)
                self.labels.remove(grp)
        # labels -> connector with the same name, nearest first
        for grp in self.labels:
            txt = "".join(t.text or "" for t in grp.iter(N("text")))
            tb = self.group_box(grp)
            cands = [c for c in self.conns if c.label is None and c.name.replace("�", "") and
                     (c.name == txt or c.name.strip("«»�") in txt)]
            cands = cands or [c for c in self.conns if c.label is None]
            if not cands:
                continue

            def dist(c):
                return min(_pt_seg((tb.cx, tb.cy), p, q) for p, q in c.segments())
            min(cands, key=dist).label = grp

    def group_box(self, grp):
        b = None
        for el, ox, oy, s, w in walk(grp):
            pb = prim_box(el, ox, oy, s, w)
            if pb and local(el.tag) != "g":
                b = pb.union(b)
        return b

    def by_name(self, name, kind=None):
        for s in self.shapes:
            if s.name == name and (kind is None or s.kind == kind):
                return s
        raise KeyError(name)

    def strip_clips(self):
        for el in self.root.iter():
            el.attrib.pop("clip-path", None)
        for d in self.main.findall(N("defs")):
            self.main.remove(d)

    def write(self, out: Path):
        self.tree.write(out, encoding="utf-8", xml_declaration=True)


def _pt_seg(pt, p, q):
    dx, dy = q[0] - p[0], q[1] - p[1]
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((pt[0] - p[0]) * dx + (pt[1] - p[1]) * dy) / L))
    return math.dist(pt, (p[0] + t * dx, p[1] + t * dy))


# ---------------------------------------------------------------------------
# text
# ---------------------------------------------------------------------------
CENTERED = {"UseCase", "ActivityAction", "DecisionNode", "InteractionLifeLine", "InteractionActor", "Component", "Class", "State2"}
CAPTIONED = {"InteractionLifeLine", "InteractionActor"}   # name under a robustness icon / stick figure


def _text_frame(s: Shape, el, ox, oy, size, strict=False):
    """The primitive box that holds a text (a lifeline's header, not the whole lifeline)."""
    tb = prim_box(el, ox, oy, size)
    best = None
    for p, px, py in s.prims():
        if local(p.tag) not in ("rect", "ellipse", "path", "polygon"):
            continue
        pb = prim_box(p, px, py)
        if pb and pb.w > 30 and pb.x0 - 2 <= tb.cx <= pb.x1 + 2 and pb.y0 - 2 <= tb.cy <= pb.y1 + 2:
            if best is None or pb.w * pb.h > best.w * best.h:
                best = pb
    return best if (best or strict) else s.box


def enlarge_shape_texts(d: Diagram, size: float, kinds=CENTERED, pad0=12, widen=True, max_widen=0):
    """Bigger text, centred horizontally in its frame. Shapes of one kind share one
    size (shrunk at most to 85 % so a single long name does not shrink all); a frame
    is widened symmetrically up to max_widen px before a text has to shrink."""
    work = []
    for s in d.shapes:
        if s.kind not in kinds or s.box is None:
            continue
        texts = list(s.texts())
        if not texts:
            continue
        frame = _text_frame(s, *texts[0][:4], strict=s.kind in CAPTIONED)
        if frame is None:
            # caption below the icon: same centre, bigger, pushed down a little
            for el, ox, oy, old, weight in texts:
                tb = prim_box(el, ox, oy, old, weight)
                el.set("font-size", f"{size:.1f}px")
                el.set("text-anchor", "middle")
                el.set("x", fmt(tb.cx - ox))
                el.set("y", fmt(fnum(el.get("y")) + (size - old) * 0.8))
            # the lifeline (dashed line, or the actor's bar) starts below the caption
            cap_bottom = max(prim_box(el, ox, oy, size, weight).y1 for el, ox, oy, old, weight in texts) + 4
            for el, ox, oy in s.prims():
                tag = local(el.tag)
                if tag == "line" and abs(fnum(el.get("x1")) - fnum(el.get("x2"))) < 0.5:
                    y1, y2 = sorted((fnum(el.get("y1")), fnum(el.get("y2"))))
                    if y2 - y1 > 60 and oy + y1 < cap_bottom:
                        el.set("y1", fmt(cap_bottom - oy))
                        el.set("y2", fmt(y2))
                elif tag == "rect" and fnum(el.get("height", 0)) > 60 and fnum(el.get("width", 0)) < 14:
                    top = oy + fnum(el.get("y", 0))
                    if top < cap_bottom:
                        h = fnum(el.get("height")) - (cap_bottom - top)
                        el.set("y", fmt(cap_bottom - oy))
                        el.set("height", fmt(h))
            continue
        pad = 26 if s.kind == "Component" else pad0
        need = max(text_w(t.text or "", size, w == "bold") for t, *_r, w in texts) + 2 * pad
        if widen and max_widen and need > frame.w:
            old = s.box
            grow = min(need - frame.w, max_widen)
            widen_shape(s, grow)
            shift_conn_ends(d, old, grow / 2)
            frame = _text_frame(s, *texts[0][:4])
        work.append((s, texts, frame))
    fits = {}
    for s, texts, frame in work:
        pad = 26 if s.kind == "Component" else pad0
        f = min(min(size, (frame.w - 2 * pad) / max(1e-6, text_w(t.text or "", 1, w == "bold"))) for t, *_r, w in texts)
        fits[s.kind] = min(fits.get(s.kind, size), f)
    for s, texts, frame in work:
        pad = 26 if s.kind == "Component" else pad0
        base = max(fits[s.kind], size * 0.85)
        sizes = [min(base, (frame.w - 2 * pad) / max(1e-6, text_w(el.text or "", 1, weight == "bold")))
                 for el, ox, oy, old, weight in texts]
        # lines keep their order and are stacked as one block centred in the frame
        order = sorted(range(len(texts)), key=lambda i: texts[i][2] + fnum(texts[i][0].get("y")))
        heights = [sizes[i] * 1.3 for i in order]
        y = frame.cy - sum(heights) / 2
        for i, hgt in zip(order, heights):
            el, ox, oy, old, weight = texts[i]
            fit = sizes[i]
            el.set("font-size", f"{fit:.1f}px")
            el.set("text-anchor", "middle")
            el.set("x", fmt(frame.cx - ox))
            el.set("y", fmt(y + hgt / 2 + 0.35 * fit - oy))
            y += hgt


OPERATORS = {"alt", "opt", "loop", "par", "break", "critical", "neg", "assert", "strict", "seq", "ignore", "consider"}


def enlarge_fragment_texts(d: Diagram, size: float):
    """Operator tab (alt/loop) and guards of combined fragments: bigger, left edge kept."""
    for s in d.shapes:
        if s.kind not in ("CombinedFragment", "InteractionOperand"):
            continue
        for el, ox, oy, old, weight in s.texts():
            if (el.text or "").strip() in OPERATORS:   # the alt/loop tab keeps VP's size
                continue
            el.set("font-size", f"{size:.1f}px")
            el.set("y", fmt(fnum(el.get("y")) + (size - old) * 0.8))


def shift_conn_ends(d: Diagram, old: Box, half: float, reach=16):
    """After a shape is widened, move connector ends (and arrow heads) that sat on
    its old left/right edge out to the new edge."""
    for c in d.conns:
        for el, ox, oy, s_, w_ in walk(c.g):
            if local(el.tag) not in ("line", "polygon", "path"):
                continue
            if local(el.tag) == "line":
                pts = [("x1", "y1"), ("x2", "y2")]
                xs = [(ox + fnum(el.get(a)), oy + fnum(el.get(b))) for a, b in pts]
                for (ka, kb), (x, y) in zip(pts, xs):
                    if old.y0 - 2 <= y <= old.y1 + 2:
                        if abs(x - old.x0) < reach:
                            el.set(ka, fmt(fnum(el.get(ka)) - half))
                        elif abs(x - old.x1) < reach:
                            el.set(ka, fmt(fnum(el.get(ka)) + half))
            else:
                attr = "points" if local(el.tag) == "polygon" else "d"

                def mv(m):
                    x, y = float(m[1]), float(m[2])
                    X, Y = ox + x, oy + y
                    if old.y0 - 2 <= Y <= old.y1 + 2:
                        if abs(X - old.x0) < reach:
                            x -= half
                        elif abs(X - old.x1) < reach:
                            x += half
                    return f"{fmt(x)} {m[2]}"
                el.set(attr, re.sub(r"(-?\d+(?:\.\d+)?)[ ,](-?\d+(?:\.\d+)?)", mv, el.get(attr)))


def widen_shape(s: Shape, grow: float):
    """Widen a box-like shape by `grow` px, keeping its centre. Small decorations at the
    right edge (component icon) move with the edge."""
    b = s.box
    half = grow / 2
    for el, ox, oy in list(s.prims()):
        tag = local(el.tag)
        if tag == "rect":
            w = fnum(el.get("width"))
            if w > b.w * 0.6:
                el.set("x", fmt(fnum(el.get("x", 0)) - half))
                el.set("width", fmt(w + grow))
            else:
                el.set("x", fmt(fnum(el.get("x", 0)) + half))
        elif tag == "ellipse":
            el.set("cx", fmt(fnum(el.get("cx"))))
            el.set("rx", fmt(fnum(el.get("rx")) + half))
        elif tag == "path":
            el.set("d", _widen_path(el.get("d"), b.cx - ox, half))
        elif tag in ("polygon", "polyline"):
            el.set("points", _widen_points(el.get("points"), b.cx - ox, half))
        elif tag == "line":
            for k in ("x1", "x2"):
                x = fnum(el.get(k))
                el.set(k, fmt(x + (half if x > b.cx - ox else -half)))


def _widen_path(d, cx, half):
    def rep(m):
        x, y = float(m[1]), float(m[2])
        return f"{fmt(x + (half if x > cx else -half))} {m[2]}"
    return re.sub(r"(-?\d+(?:\.\d+)?)[ ,](-?\d+(?:\.\d+)?)", rep, d)


def _widen_points(pts, cx, half):
    return _widen_path(pts, cx, half)


def rewrite_notes(d: Diagram, size: float, line_h=None, pad=8):
    """Replace Batik glyph outlines in notes with wrapped <text>; grow the note
    downwards to fit. Returns the height added below the lowest note."""
    line_h = line_h or size * 1.3
    grown = 0
    for s in d.shapes:
        if s.kind != "NOTE":
            continue
        b = s.box
        for grp in list(s.extras):
            if grp.find(f".//{N('path')}") is not None or grp.find(f".//{N('text')}") is not None:
                d.main.remove(grp)
                s.extras.remove(grp)
        words, lines, cur = s.name.split(), [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if text_w(t, size) > b.w - 2 * pad - 16 and cur:
                lines.append(cur)
                cur = w
            else:
                cur = t
        lines.append(cur)
        new_h = max(b.h, pad * 2 + line_h * len(lines))
        grown = max(grown, new_h - b.h)
        for el, ox, oy in s.prims():
            if local(el.tag) == "polygon":
                w = b.w
                el.set("points", f" 0 0 {fmt(w-15)} 0 {fmt(w)} 15 {fmt(w-15)} 15 {fmt(w-15)} 0 {fmt(w)} 15 {fmt(w)} {fmt(new_h)} 0 {fmt(new_h)}")
        g = ET.Element(N("g"), {"fill": "black", "fill-opacity": "1", "stroke": "none", "font-family": "sans-serif",
                                "font-size": f"{size}px", "transform": f"translate({fmt(b.x0)},{fmt(b.y0)})"})
        for i, ln in enumerate(lines):
            t = ET.SubElement(g, N("text"), {"x": str(pad), "y": fmt(pad + size * 0.95 + i * line_h),
                                             "xml:space": "preserve"})
            t.text = ln
        idx = list(d.main).index(s.g)
        d.main.insert(idx + 1, g)
        s.extras.append(g)
    return grown


# ---------------------------------------------------------------------------
# connectors
# ---------------------------------------------------------------------------
def rebuild_conn(c: Conn, p, q, head=None, head_len=13, head_ang=30):
    """Redraw a straight connector p->q with VP's own stroke attributes."""
    inner = [k for k in c.g if local(k.tag) == "g"][0]
    first = inner.find(N("line"))
    attrs = {k: v for k, v in first.attrib.items() if k not in ("x1", "x2", "y1", "y2")}
    for k in list(inner):
        inner.remove(k)
    set_tr(inner, 0, 0)
    ET.SubElement(inner, N("line"), dict(attrs, x1=fmt(p[0]), y1=fmt(p[1]), x2=fmt(q[0]), y2=fmt(q[1])))
    if head:
        tip, frm = (q, p) if head == "q" else (p, q)
        ang = math.atan2(frm[1] - tip[1], frm[0] - tip[0])
        for s in (-1, 1):
            a = ang + s * math.radians(head_ang)
            e = (tip[0] + head_len * math.cos(a), tip[1] + head_len * math.sin(a))
            ET.SubElement(inner, N("line"), dict(attrs, **{"stroke-dasharray": "none"},
                                                 x1=fmt(tip[0]), y1=fmt(tip[1]), x2=fmt(e[0]), y2=fmt(e[1])))


def clip_to(shape_geom, frm, to):
    """Point where the ray centre->`to` leaves the shape."""
    kind, (cx, cy, a, b) = shape_geom
    dx, dy = to[0] - cx, to[1] - cy
    if dx == 0 and dy == 0:
        return (cx, cy)
    if kind == "ellipse":
        t = 1 / math.sqrt((dx / a) ** 2 + (dy / b) ** 2)
    elif kind == "diamond":
        t = 1 / (abs(dx) / a + abs(dy) / b)
    else:
        t = min(a / abs(dx) if dx else 1e9, b / abs(dy) if dy else 1e9)
    return (cx + dx * t, cy + dy * t)


# ---------------------------------------------------------------------------
# label placement
# ---------------------------------------------------------------------------
def place_labels(d: Diagram, size: float, area: Box | None = None, skip_kinds=("System", "CombinedFragment", "InteractionOperand"), gap=4, lifeline_ok=True):
    obst_boxes, obst_ell, soft_segs = [], [], []
    for s in d.shapes:
        if s.kind in skip_kinds:
            # the title of a container is still an obstacle
            for el, ox, oy, sz, w in s.texts():
                obst_boxes.append(prim_box(el, ox, oy, sz, w).grow(2))
            continue
        for el, ox, oy in s.prims():
            tag = local(el.tag)
            if tag == "ellipse":
                obst_ell.append((ox + fnum(el.get("cx")), oy + fnum(el.get("cy")), fnum(el.get("rx")) + 2, fnum(el.get("ry")) + 2))
            elif tag == "line" and s.kind == "InteractionLifeLine":
                p1 = (ox + fnum(el.get("x1")), oy + fnum(el.get("y1")))
                p2 = (ox + fnum(el.get("x2")), oy + fnum(el.get("y2")))
                soft_segs.append((p1, p2))
                continue
            else:
                pb = prim_box(el, ox, oy)
                if pb:
                    obst_boxes.append(pb.grow(2))
        for el, ox, oy, sz, w in s.texts():
            obst_boxes.append(prim_box(el, ox, oy, sz, w).grow(2))
        if s.caption is not None:
            obst_boxes.append(d.group_box(s.caption).grow(2))
    all_segs = [(c, p, q) for c in d.conns for p, q in c.segments()]
    head_boxes = [Box(min(p[0], q[0]), min(p[1], q[1]), max(p[0], q[0]), max(p[1], q[1])).grow(2)
                  for c in d.conns for p, q in c.heads()]
    placed = []
    conns = [c for c in d.conns if c.label is not None]
    # long labels first: they have fewer good spots
    for c in sorted(conns, key=lambda c: -len("".join(t.text or "" for t in c.label.iter(N("text"))))):
        texts = list(c.label.iter(N("text")))
        txt = "".join(t.text or "" for t in texts)
        w = text_w(txt, size) + 2
        h = size * 1.15
        best = None
        segs = c.segments()
        total = sum(math.dist(p, q) for p, q in segs)
        for t in (0.5, 0.42, 0.58, 0.34, 0.66, 0.26, 0.74, 0.18, 0.82):
            # point at fraction t of the polyline
            acc, P, seg = 0, None, None
            for p, q in segs:
                L = math.dist(p, q)
                if acc + L >= t * total and L > 0:
                    u = (t * total - acc) / L
                    P = (p[0] + (q[0] - p[0]) * u, p[1] + (q[1] - p[1]) * u)
                    seg = (p, q)
                    break
                acc += L
            if P is None:
                continue
            (p, q) = seg
            L = math.dist(p, q) or 1
            nx, ny = -(q[1] - p[1]) / L, (q[0] - p[0]) / L
            for side in (-1, 1):
                off = abs(nx) * w / 2 + abs(ny) * h / 2 + gap
                cx, cy = P[0] + side * nx * off, P[1] + side * ny * off
                bx = Box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
                cost = abs(t - 0.5) * 30
                # prefer the upper side of near-horizontal lines (VP/UML habit)
                if abs(ny) > 0.7 and side * ny > 0:
                    cost += 6
                cost += 1000 * sum(bx.overlaps(o) for o in placed)
                cost += 400 * sum(bx.overlaps(o) for o in obst_boxes)
                cost += 400 * sum(ellipse_hits_box(*e, bx) for e in obst_ell)
                cost += 120 * sum(seg_hits_box(a, b2, bx) for cc, a, b2 in all_segs)
                cost += 400 * sum(bx.overlaps(o) for o in head_boxes)
                cost += 40 * sum(seg_hits_box(a, b2, bx) for a, b2 in soft_segs)
                if area is not None and not bx.inside(area):
                    cost += 500
                if best is None or cost < best[0]:
                    best = (cost, bx)
        bx = best[1]
        placed.append(bx)
        # one <text> per label group: rewrite in absolute coordinates
        set_tr(c.label, 0, 0)
        for extra in texts[1:]:
            for par in c.label.iter():
                if extra in list(par):
                    par.remove(extra)
        t0 = texts[0]
        t0.text = txt
        t0.set("x", fmt(bx.cx))
        t0.set("y", fmt(bx.cy + 0.35 * size))
        t0.set("text-anchor", "middle")
        t0.set("font-size", f"{size}px")
        for k in list(c.label):
            if local(k.tag) == "g":
                set_tr(k, 0, 0)
        # VP gives some labels a white backing rect: keep it (fitted to the text) only
        # where the label has to sit on a line, so the text stays readable.
        on_line = any(seg_hits_box(a, b2, bx) for cc, a, b2 in all_segs if cc is not c) or any(seg_hits_box(a, b2, bx) for a, b2 in soft_segs)
        for par in [c.label] + list(c.label.iter()):
            for r in [k for k in list(par) if local(k.tag) == "rect"]:
                if on_line:
                    r.set("x", fmt(bx.x0 - 1))
                    r.set("y", fmt(bx.y0))
                    r.set("width", fmt(bx.w + 2))
                    r.set("height", fmt(bx.h))
                else:
                    par.remove(r)
    return placed


# ---------------------------------------------------------------------------
# canvas
# ---------------------------------------------------------------------------
def finalize(d: Diagram, pad=12, wm_h=22):
    """Fit the canvas to the content and park VP's watermark under it, bottom right."""
    content = None
    for c in list(d.main):
        if c is d.watermark or c is d.background or local(c.tag) == "defs":
            continue
        b = d.group_box(c)
        if b:
            content = b.union(content)
    W = content.w + 2 * pad
    H = content.h + 2 * pad + wm_h
    wrap = ET.Element(N("g"), {"transform": f"translate({fmt(pad - content.x0)},{fmt(pad - content.y0)})"})
    for c in list(d.main):
        if c is d.watermark or c is d.background or local(c.tag) == "defs":
            continue
        d.main.remove(c)
        wrap.append(c)
    d.main.insert(1 if d.background is not None else 0, wrap)
    if d.background is not None:
        r = d.background.find(N("rect"))
        r.set("width", fmt(W))
        r.set("height", fmt(H))
    if d.watermark is not None:
        d.main.remove(d.watermark)
        d.main.append(d.watermark)
        t = d.watermark.find(N("text"))
        im = d.watermark.find(N("image"))
        tw = text_w(t.text or "", 10)
        im.set("x", fmt(W - 22))
        im.set("y", fmt(H - 19))
        t.set("x", fmt(W - 28 - tw))
        t.set("y", fmt(H - 7))
    d.root.set("width", fmt(W))
    d.root.set("height", fmt(H))
    d.root.set("viewbox", f"0 0 {fmt(W)} {fmt(H)}")
    d.root.set("viewBox", f"0 0 {fmt(W)} {fmt(H)}")


# ---------------------------------------------------------------------------
# use case layout
# ---------------------------------------------------------------------------
# cols: list of columns, each [(use case, row)]; actors: {name: row or None (= mean of
# linked use cases)}. Rows are in units of ROW px.
LAYOUTS = {
    "H2_3_use_case_tong_quan": dict(
        cols=[[("Đăng nhập", 0), ("Tra cứu tài liệu, xem PDF", 1), ("Hỏi đáp có trích dẫn", 2),
               ("Tìm kiếm ngữ nghĩa", 3), ("Nạp và xử lý tài liệu", 4.4),
               ("Quản trị cơ sở tri thức đồ thị", 5.6), ("Quản lý tài liệu và phiên bản", 6.8),
               ("Quản lý người dùng", 8), ("Giám sát truy vấn AI", 9.2)]],
        left={"Người dùng": None, "Quản trị viên": None},
        right={"Mô hình ngôn ngữ (LLM)": 0.3, "Dịch vụ AI": None}, actor_gap=230, font=18, label_font=16),
    "H2_4_uc_xac_thuc_nguoi_dung": dict(
        cols=[[("Đăng nhập", 0), ("Đăng ký tài khoản", 1), ("Xem danh sách người dùng", 2.5),
               ("Tạo tài khoản", 3.5), ("Đổi vai trò", 4.5), ("Khóa / mở khóa tài khoản", 5.5)],
              [("Kiểm tra mật khẩu BCrypt", 0), ("Cấp JWT (1 giờ)", 1.5), ("Kiểm tra quyền ADMIN", 4.5)]],
        left={"Người dùng": None, "Quản trị viên": None}, right={}, font=16, label_font=15),
    "H2_5_uc_quan_ly_tai_lieu": dict(
        cols=[[("Xem danh sách tài liệu", 0), ("Xem chi tiết và phiên bản", 1), ("Xem đoạn trích", 2),
               ("Xem PDF gốc", 3), ("Tải lên tài liệu mới", 4.5), ("Tải lên phiên bản mới", 6),
               ("Đặt phiên bản hiện hành", 7), ("Xóa tài liệu", 8)],
              [("Lọc theo danh mục, trạng thái", 0), ("Kiểm tra tệp PDF (≤ 25 MB)", 4.5),
               ("Khởi chạy pipeline nạp", 6), ("Xóa vector ở ai-service", 8)]],
        left={"Người dùng": None, "Quản trị viên": None}, right={"Dịch vụ AI": 7},
        font=18, label_font=16, col_gap=140),
    "H2_6_uc_nap_tai_lieu": dict(
        cols=[[("Theo dõi tiến trình nạp", 0), ("Thử lại phiên bản lỗi", 1.25), ("Nạp lại phiên bản hiện hành", 2.25)],
              [("Nạp tài liệu (5 bước)", 1.75)],
              [("Trích xuất văn bản, OCR", 0.5), ("Phân đoạn theo Chương/Điều", 1.5),
               ("Tạo embedding, ghi Qdrant", 2.5), ("Ghi nút vào đồ thị Neo4j", 3.75)]],
        left={"Quản trị viên": None}, right={"Dịch vụ AI": None}, font=18, label_font=16, col_gap=130),
    "H2_7_uc_hoi_dap_tim_kiem": dict(
        cols=[[("Xem trích dẫn trên PDF", 0), ("Hỏi đáp có trích dẫn", 1.5), ("Xem vết xử lý tác tử", 3),
               ("Tìm kiếm ngữ nghĩa", 5)],
              [("Sinh câu trả lời bằng LLM", 0), ("Giới hạn 30 yêu cầu/phút", 2.25),
               ("Lọc theo quyền tài liệu", 3.5), ("Ghi nhật ký truy vấn AI", 4.75)]],
        left={"Người dùng": None}, right={"Mô hình ngôn ngữ (LLM)": 0, "Dịch vụ AI": 3.5},
        col_gap=230, font=16, label_font=15),
    "H4_1_use_case_kb": dict(
        cols=[[("Gộp KB1, KB2 thành KB", 0), ("Cập nhật KB theo hash nội dung", 1), ("Nạp PDF vào KB1", 2.2),
               ("Nạp link công khai vào KB2", 3.2), ("Hỏi đáp có trích dẫn", 4.4), ("Xem đoạn nguồn trên PDF", 5.6)]],
        left={"Quản trị KB": None, "Nhân viên hỏi đáp": None}, right={"Dịch vụ AI": None},
        actor_gap=200, font=17, label_font=15),
    "H2_8_uc_giam_sat_tri_thuc": dict(
        cols=[[("Kiểm tra trạng thái dịch vụ AI", 0), ("Xem nhật ký truy vấn AI", 1.25),
               ("Quản trị KB đồ thị", 2.75), ("Đánh giá cấu hình truy xuất", 4.25)],
              [("Nạp PDF vào KB1", 1.25), ("Nạp link vào KB2", 2.25), ("Gộp KB1 + KB2", 3.25),
               ("Bảo trì: trùng lặp, mâu thuẫn", 4.25)]],
        left={"Người dùng": 0, "Quản trị viên": None}, right={"Dịch vụ AI": None}, font=16, label_font=15),
}

UC_FONT = 15
LABEL_FONT = 14
UC_H = 56
ROW = 80
TOP = 50          # room for the system title
ACTOR_GAP = 120   # actor centre to system border


def layout_usecases(d: Diagram, spec):
    col_gap = spec.get("col_gap", 170)
    F = spec.get("font", UC_FONT)
    UH = round(max(UC_H, F * 3.5))     # ellipse height grows with the text
    RW = UH + 24                         # row pitch
    # endpoints of every connector, in terms of the original shapes
    def nearest(pt, kinds=("UseCase", "Actor")):
        best, bd = None, 1e9
        for s in d.shapes:
            if s.kind not in kinds:
                continue
            b = s.box.grow(6)
            dx = max(b.x0 - pt[0], 0, pt[0] - b.x1)
            dy = max(b.y0 - pt[1], 0, pt[1] - b.y1)
            dd = math.hypot(dx, dy) + 0.001 * math.dist(pt, (b.cx, b.cy))
            if dd < bd:
                best, bd = s, dd
        return best

    ends = []
    for c in d.conns:
        segs = c.segments()
        p, q = segs[0][0], segs[-1][1]
        heads = c.heads()
        tip = None
        if heads:
            tip = "q" if math.dist(heads[0][0], q) < math.dist(heads[0][0], p) else "p"
        ends.append((c, nearest(p), nearest(q), tip))

    system = [s for s in d.shapes if s.kind == "System"][0]
    sb = system.box
    title = list(system.texts())
    # column widths
    widths = []
    for col in spec["cols"]:
        widths.append(max(230, max(text_w(n, F) for n, _ in col) + 70))
    left_names, right_names = list(spec["left"]), list(spec["right"])
    cap_w = max([text_w(n, F) for n in left_names + right_names] + [60])
    sys_x = sb.x0
    sys_y = sb.y0
    sys_w = 50 + sum(widths) + col_gap * (len(widths) - 1) + 50
    max_row = max(r for col in spec["cols"] for _, r in col)
    sys_h = TOP + max_row * RW + UH + 34
    sys_w = max(sys_w, text_w(title[0][0].text or "", F) + 40)

    # place use cases
    centers = {}
    x = sys_x + 50
    for col, w in zip(spec["cols"], widths):
        for name, row in col:
            s = d.by_name(name, "UseCase")
            b = s.box
            cy = sys_y + TOP + row * RW + UH / 2
            # resize ellipse
            for el, ox, oy in s.prims():
                if local(el.tag) == "ellipse":
                    el.set("cx", fmt(w / 2))
                    el.set("cy", fmt(UH / 2))
                    el.set("rx", fmt(w / 2))
                    el.set("ry", fmt(UH / 2))
            s.shift(x - b.x0, cy - UH / 2 - b.y0)
            for el, ox, oy, sz, wt in s.texts():
                el.set("font-size", f"{F}px")
                el.set("text-anchor", "middle")
                el.set("x", fmt(w / 2))
                el.set("y", fmt(UH / 2 + 0.36 * F))
            centers[name] = ("ellipse", (x + w / 2, cy, w / 2, UH / 2))
        x += w + col_gap

    # system box + title
    for el, ox, oy in system.prims():
        if local(el.tag) == "rect":
            el.set("width", fmt(sys_w))
            el.set("height", fmt(sys_h))
    for el, ox, oy, sz, wt in system.texts():
        el.set("font-size", f"{F}px")
        el.set("font-weight", "bold")
        el.set("text-anchor", "middle")
        el.set("x", fmt(sys_w / 2))
        el.set("y", fmt(26))

    # actors
    links = {}
    for c, a, b, tip in ends:
        for s1, s2 in ((a, b), (b, a)):
            if s1.kind == "Actor" and s2.kind == "UseCase":
                links.setdefault(s1.name, []).append(s2.name)
    rows = {n: r for col in spec["cols"] for n, r in col}
    for side, names in (("L", left_names), ("R", right_names)):
        gap = spec.get("actor_gap", ACTOR_GAP)
        cx = sys_x - gap if side == "L" else sys_x + sys_w + gap
        for name in names:
            s = d.by_name(name, "Actor")
            r = spec["left" if side == "L" else "right"][name]
            if r is None:
                rs = [rows[u] for u in links.get(name, [])]
                r = sum(rs) / len(rs)
            cy = sys_y + TOP + r * RW + UH / 2
            fig = s.box
            s.shift(cx - fig.cx, cy - fig.cy)
            centers[name] = ("rect", (cx, cy, fig.w / 2 + 4, fig.h / 2 + 2))
            if s.caption is not None:
                set_tr(s.caption, cx, cy + fig.h / 2 + 6)
                for t in s.caption.iter(N("text")):
                    t.set("x", "0")
                    t.set("y", fmt(F))
                    t.set("text-anchor", "middle")
                    t.set("font-size", f"{F}px")

    # connectors
    for c, a, b, tip in ends:
        ga, gb = centers[a.name], centers[b.name]
        pa = clip_to(ga, None, gb[1][:2])
        pb = clip_to(gb, None, ga[1][:2])
        rebuild_conn(c, pa, pb, head=tip)

    # note under the system box
    for s in d.shapes:
        if s.kind == "NOTE":
            nb = s.box
            _resize_note(s, sys_w)
            s.shift(sys_x - nb.x0, sys_y + sys_h + 16 - nb.y0)
    return Box(sys_x, sys_y, sys_x + sys_w, sys_y + sys_h)


def _resize_note(s: Shape, w):
    for el, ox, oy in s.prims():
        if local(el.tag) == "polygon":
            h = max(float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", el.get("points"))[1::2])
            el.set("points", f" 0 0 {fmt(w-15)} 0 {fmt(w)} 15 {fmt(w-15)} 15 {fmt(w-15)} 0 {fmt(w)} 15 {fmt(w)} {fmt(h)} 0 {fmt(h)}")


def check_usecase(d: Diagram):
    """Report any connector that passes through a use case it does not touch."""
    probs = []
    ells = {}
    for s in d.shapes:
        if s.kind == "UseCase":
            for el, ox, oy in s.prims():
                if local(el.tag) == "ellipse":
                    ells[s.name] = (ox + fnum(el.get("cx")), oy + fnum(el.get("cy")), fnum(el.get("rx")), fnum(el.get("ry")))
    for c in d.conns:
        for p, q in c.segments():
            for n, e in ells.items():
                if seg_hits_ellipse(p, q, *e, margin=14) and not any(
                        abs(((pt[0] - e[0]) / e[2]) ** 2 + ((pt[1] - e[1]) / e[3]) ** 2 - 1) < 0.05 for pt in (p, q)):
                    probs.append(f"{c.kind} {p[0]:.0f},{p[1]:.0f}->{q[0]:.0f},{q[1]:.0f} too close to '{n}'")
    return probs


# ---------------------------------------------------------------------------
# box diagrams (component / class): explicit centres, straight connectors
# ---------------------------------------------------------------------------
def conn_ends(d: Diagram):
    """(connector, from shape, to shape, arrow end) for every connector."""
    def nearest(pt):
        best, bd = None, 1e9
        for s in d.shapes:
            if s.kind in ("System", "NOTE", "ActivitySwimlane2", "ActivityPartition") or s.box is None:
                continue
            b = s.box
            dx = max(b.x0 - pt[0], 0, pt[0] - b.x1)
            dy = max(b.y0 - pt[1], 0, pt[1] - b.y1)
            dd = math.hypot(dx, dy) + 0.001 * math.dist(pt, (b.cx, b.cy))
            if dd < bd:
                best, bd = s, dd
        return best
    out = []
    for c in d.conns:
        segs = c.segments()
        p, q = segs[0][0], segs[-1][1]
        heads = c.heads()
        tip = None
        if heads:
            tip = "q" if math.dist(heads[0][0], q) < math.dist(heads[0][0], p) else "p"
        out.append((c, nearest(p), nearest(q), tip))
    return out


def relayout_boxes(d: Diagram, centers: dict, note_gap=30):
    ends = conn_ends(d)
    for name, (cx, cy) in centers.items():
        s = d.by_name(name)
        b = s.box
        s.shift(cx - b.cx, cy - b.cy)
    for c, a, b, tip in ends:
        A, B = a.box, b.box
        ga = ("rect", (A.cx, A.cy, A.w / 2, A.h / 2))
        gb = ("rect", (B.cx, B.cy, B.w / 2, B.h / 2))
        rebuild_conn(c, clip_to(ga, None, (B.cx, B.cy)), clip_to(gb, None, (A.cx, A.cy)), head=tip)
    others = [s.box for s in d.shapes if s.kind != "NOTE" and s.box is not None]
    x0 = min(b.x0 for b in others)
    y1 = max(b.y1 for b in others)
    for s in d.shapes:
        if s.kind == "NOTE":
            nb = s.box
            s.shift(x0 - nb.x0, y1 + note_gap - nb.y0)


CONTAINERS = ("System", "NOTE", "ActivitySwimlane2", "ActivityPartition", "CombinedFragment",
              "InteractionOperand", "Node", "Package", "InteractionLifeLine")


def push_detours(d: Diagram, margin=26):
    """A vertical leg of a routed connector that runs through a shape it does not
    connect is moved just outside that shape, taking the joints with it."""
    ends = {c: (a, b) for c, a, b, t in conn_ends(d)}
    for c in d.conns:
        lines = [(el, ox, oy) for el, ox, oy, s_, w_ in walk(c.g) if local(el.tag) == "line"]
        for el, ox, oy in lines:
            x1, x2 = ox + fnum(el.get("x1")), ox + fnum(el.get("x2"))
            y1, y2 = oy + fnum(el.get("y1")), oy + fnum(el.get("y2"))
            if abs(x1 - x2) > 0.5 or abs(y1 - y2) < 30:
                continue
            hits = [s.box for s in d.shapes if s not in ends[c] and s.kind not in CONTAINERS
                    and s.box is not None and seg_hits_box((x1, y1), (x2, y2), s.box.grow(-1))]
            if not hits:
                continue
            left = sum(b.cx for b in hits) / len(hits) > x1
            nx = (min(b.x0 for b in hits) - margin) if left else (max(b.x1 for b in hits) + margin)
            for e2, ox2, oy2 in lines:
                for kx, ky in (("x1", "y1"), ("x2", "y2")):
                    px, py = ox2 + fnum(e2.get(kx)), oy2 + fnum(e2.get(ky))
                    if abs(px - x1) < 0.6 and (abs(py - y1) < 0.6 or abs(py - y2) < 0.6):
                        e2.set(kx, fmt(nx - ox2))


def check_boxes(d: Diagram):
    probs = []
    for c, a, b, tip in conn_ends(d):
        for p, q in c.segments():
            for s in d.shapes:
                if s is a or s is b or s.kind in ("System",) or s.box is None:
                    continue
                if seg_hits_box(p, q, s.box.grow(-1)):
                    probs.append(f"{a.name} -> {b.name} crosses {s.name}")
    return probs


ROW_TS = 56
BOX_LAYOUTS = {
    # Controller -> Service -> client/repository, as three columns.
    "H2_13_lop_thiet_ke_backend": {
        **{n: (140, 30 + r * ROW_TS) for n, r in [
            ("DocumentController", 1), ("IngestionController", 2.6), ("AiGatewayController", 8),
            ("UserController", 9.9), ("AuthController", 11.1)]},
        **{n: (490, 30 + r * ROW_TS) for n, r in [
            ("DocumentService", 1), ("IngestionService", 4.5), ("AiGatewayService", 8),
            ("UserService", 9.9), ("AuthService", 11.1)]},
        **{n: (870, 30 + r * ROW_TS) for n, r in [
            ("PdfProcessor", 0), ("DocumentRepository", 1), ("DocumentVersionRepository", 2),
            ("AiParseClient", 3), ("AiIngestClient", 4), ("DocumentChunkRepository", 5),
            ("IngestionTaskRepository", 6), ("AiRateLimiter", 7), ("AiGatewayClient", 8),
            ("AiAuditLogRepository", 9), ("UserRepository", 10.2), ("JwtService", 11.4)]},
    },
    "H5_1_kien_truc_tac_tu": {
        "POST /api/v1/chat/ask (chat.py)": (230, 60), "Vòng lặp: agent.py (tối đa 4 bước)": (230, 300),
        **{n: (790, 40 + r * 95) for n, r in [
            ("Nhận thức: perception.py", 0), ("Chính sách: rules.py (9 luật)", 1), ("Công cụ kb_attribute", 2),
            ("Công cụ retrieve:hybrid_rag", 3), ("Công cụ retrieve:flat_rag", 4), ("Công cụ refuse", 5)]},
        **{n: (1290, 40 + r * 95) for n, r in [
            ("Neo4j: nút Claim, đồ thị", 2), ("Qdrant + cross-encoder", 3.6), ("LLM (tùy chọn)", 4.9)]},
    },
    "H3_2_truy_xuat_hai_tang": {
        "Bi-encoder E5-small": (130, 50), "Qdrant (HNSW, cosine)": (520, 50),
        "Cross-encoder mMiniLMv2": (910, 50), "Bộ chọn bằng chứng": (1300, 50),
    },
    "H4_2_kien_truc_kb": {
        "35 tệp PDF nội bộ": (110, 40), "10 link công khai": (110, 210), "7 tài liệu upload": (110, 380),
        "KB1 (35 tài liệu, 1.313 chunk)": (540, 40), "KB2 (10 tài liệu, 31 chunk)": (540, 210),
        "Qdrant (321 vector upload)": (540, 380),
        "KB hợp nhất trên Neo4j (52 tài liệu, 1.665 chunk)": (1010, 210), "RAG Service": (1010, 380),
    },
    "H4_6_kb_output_mot_trang": {
        "KB : KnowledgeBase": (100, 190), "Điều lệ công ty - 2021 : Document (v6, 38 trang)": (470, 190),
        "c33 : Chunk (trang 11, Điều 13)": (860, 190),
        "Hội đồng Quản trị : Entity": (1290, 30), "Điều 11 : Entity": (1290, 130),
        "Điều 13 : Entity": (1290, 230), "Đại hội đồng cổ đông : Entity": (1290, 330),
        "c27 : Chunk (Điều 11)": (740, 380), "c30 : Chunk (Điều 11)": (990, 380),
    },
    # 3 x 4 grid: user -> frontend -> backend on the left/middle, stores around their owner
    "H2_1_kien_truc_microservice": {
        "Trình duyệt (người dùng)": (210, 40), "PostgreSQL 15 (6 bảng)": (680, 40), "Redis 7 (rate limit)": (1150, 40),
        "frontend: React SPA + Nginx (:3000)": (210, 210), "backend: Spring Boot API Gateway (:8080)": (680, 210),
        "Kho tệp PDF (volume uploads)": (1150, 210),
        "Qdrant (vector 384 chiều)": (210, 380), "ai-service: FastAPI (:8001)": (680, 380),
        "Neo4j 5 (đồ thị tri thức)": (1150, 380),
        "LLM: Ollama / Gemini": (210, 550), "Mô hình nhúng + reranker": (680, 550),
    },
}

# label text corrections (keep in step with ch2_diagrams.py)
TEXT_FIX = {
    "H2_11_tuan_tu_hoi_dap": {"3: INCR rate:{email}": "3: INCR ai:rate:{email}:{phút}"},
}


# ---------------------------------------------------------------------------
# per diagram
# ---------------------------------------------------------------------------
GENERIC = {
    # name prefix: (shape text px, label px, note px, max widen px)
    "H2_1_": (15, 14, 14, 70),
    "H2_2_": (14, 13, 13, 0),
    "H2_9_": (15, 14, 14, 0),
    "H2_10_": (15, 14, 14, 0),
    "H2_11_": (15, 14, 14, 0),
    "H4_7_": (15, 14, 14, 0),
    "H3_": (15, 14, 14, 40),
    "H4_": (15, 14, 14, 40),
    "HD_": (14, 13, 13, 0),
    "TT_": (15, 14, 14, 0),
    "TK_": (14, 13, 13, 40),
    "CSDL_": (None, 13, 13, 0),
    "H2_12_": (16, 15, 15, 40),
    "H2_13_": (16, 14, 15, 60),
    "H2_14_": (None, 13, 13, 0),
    "H5_1_": (15, 14, 14, 40),
    "H5_2_": (16, 15, 15, 0),
}


def drop_notes(d: Diagram):
    """The thesis explains each figure in the text, so VP note shapes are removed."""
    for s in [x for x in d.shapes if x.kind == "NOTE"]:
        for grp in [s.g] + s.extras:
            if grp in list(d.main):
                d.main.remove(grp)
        d.shapes.remove(s)


SWIMLANE_KINDS = {"ActivitySwimlane2", "ActivityPartition"}


def lanes_to_back(d: Diagram):
    """VP exports swimlanes after the actions they hold; draw them first instead."""
    lane_groups = [s.g for s in d.shapes if s.kind in SWIMLANE_KINDS]
    for s in d.shapes:
        if s.kind in SWIMLANE_KINDS:
            lane_groups += s.extras
    if not lane_groups:
        return
    children = list(d.main)
    first = next(i for i, c in enumerate(children) if c is not d.background and local(c.tag) != "defs")
    for g in lane_groups:
        if g in children:
            d.main.remove(g)
    for k, g in enumerate(lane_groups):
        d.main.insert(first + k, g)


def straighten_flows(d: Diagram):
    """Redraw every connector as one straight segment between the shape borders
    (VP reroutes flows that cross swimlane partitions through odd points)."""
    def geom(s):
        b = s.box
        if s.kind == "DecisionNode":
            return ("diamond", (b.cx, b.cy, b.w / 2, b.h / 2))
        if s.kind in ("InitialNode", "ActivityFinalNode", "InitialPseudoState", "FinalState", "FinalState2"):
            return ("ellipse", (b.cx, b.cy, b.w / 2, b.h / 2))
        return ("rect", (b.cx, b.cy, b.w / 2, b.h / 2))
    for c, a, b, tip in conn_ends(d):
        if a is None or b is None or a is b or len(c.segments()) > 1:
            continue   # a routed polyline from the generator is kept as drawn
        ga, gb = geom(a), geom(b)
        pa = clip_to(ga, None, gb[1][:2])
        pb = clip_to(gb, None, ga[1][:2])
        rebuild_conn(c, pa, pb, head=tip or "q")


def check_all(d: Diagram):
    """Connectors that run through a shape they do not join (lanes and fragments excluded)."""
    skip = {"System", "NOTE", "CombinedFragment", "InteractionOperand", "InteractionLifeLine", "InteractionActor",
            "Activation", "Node", "Package"} | SWIMLANE_KINDS
    probs = []
    for c, a, b, tip in conn_ends(d):
        for p_, q_ in c.segments():
            for s in d.shapes:
                if s is a or s is b or s.kind in skip or s.box is None:
                    continue
                if s.box.w < 30 and s.box.h < 30:
                    continue
                if seg_hits_box(p_, q_, s.box.grow(-2)):
                    probs.append(f"{a.name or a.kind} -> {b.name or b.kind} crosses {s.name or s.kind}")
    return probs


def process(src: Path, dst: Path):
    d = Diagram(src)
    d.strip_clips()
    drop_notes(d)
    lanes_to_back(d)
    name = src.stem
    if name in LAYOUTS:
        area = layout_usecases(d, LAYOUTS[name])
        spec = LAYOUTS[name]
        rewrite_notes(d, spec.get("font", UC_FONT) - 1)
        place_labels(d, spec.get("label_font", LABEL_FONT), area=area.grow(-4))
        probs = check_usecase(d)
        print(name, "use case relayout;", "OK" if not probs else probs)
    else:
        cfg = next((v for k, v in GENERIC.items() if name.startswith(k)), (14, 13, 13, 0))
        shape_px, label_px, note_px, widen = cfg
        for c in d.conns:
            if c.label is None:
                continue
            for t in c.label.iter(N("text")):
                for old, new in TEXT_FIX.get(name, {}).items():
                    if t.text and t.text.strip() == old:
                        t.text = new
        if shape_px:
            enlarge_shape_texts(d, shape_px, max_widen=widen)
            enlarge_fragment_texts(d, label_px)
        if any(x.kind == "ActivitySwimlane2" for x in d.shapes):
            straighten_flows(d)
        push_detours(d)
        probs = None
        if name in BOX_LAYOUTS:
            relayout_boxes(d, BOX_LAYOUTS[name])
            probs = check_boxes(d)
        rewrite_notes(d, note_px)
        place_labels(d, label_px)
        print(name, "generic" + ("" if probs is None else "; box relayout " + ("OK" if not probs else str(probs))))
        crossing = check_all(d)
        if crossing:
            print("   CROSSING:", crossing)
    finalize(d)
    d.write(dst / src.name)


if __name__ == "__main__":
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    dst.mkdir(parents=True, exist_ok=True)
    files = [src] if src.is_file() else sorted(src.glob("*.svg"))
    if src.is_file():
        src = src.parent
    for f in files:
        if len(sys.argv) > 3 and not any(f.stem.startswith(a) for a in sys.argv[3:]):
            continue
        process(f, dst)
