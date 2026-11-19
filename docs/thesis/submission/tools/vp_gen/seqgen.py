"""UML sequence diagrams for Visual Paradigm in Boundary-Control-Entity style.

Participants are an Actor (stick figure) or lifelines stereotyped «boundary»,
«control» or «entity» (VP draws the robustness icons), or plain lifelines for
external systems. Messages are real VP Message models between activations, so
VP numbers them, draws synchronous calls with a filled head, asynchronous calls
with an open head and returns dashed. Combined fragments (alt / opt / loop) carry
their guards.

    spec = Seq("H2_9_tuan_tu_dang_nhap", [("Người dùng", "actor"), ("LoginPage", "boundary"), ...])
    spec.call(0, 1, "nhập email, mật khẩu"); spec.ret(2, 1, "AuthResponse")
    with spec.fragment("alt") as f:
        f.operand("sai mật khẩu"); spec.ret(...)
        f.operand("hợp lệ"); spec.call(...)
    open("x.xml", "w").write(spec.xml())
"""
from __future__ import annotations

from contextlib import contextmanager

from PIL import ImageFont

from vpgen import Conn, Element, Project, Shape, new_id, q

_FONT = ImageFont.truetype("arial.ttf", 100)
TRANSPARENT = "Cr:255,255,255,0"


def _w(text, px=14):
    return _FONT.getlength(text) * px / 100


def _ref(name, el):
    return f'\n\t\t\t\t<ModelRefProperty displayName="{name}" name="{name}"><ModelRef id={q(el.id)}/></ModelRefProperty>'


def _refs(name, els):
    inner = "".join(f"<ModelRef id={q(e.id)}/>" for e in els)
    return f'\n\t\t\t\t<ModelRefsProperty displayName="{name}" name="{name}">{inner}</ModelRefsProperty>'


def _sprop(name, value):
    return f'\n\t\t\t\t<StringProperty displayName="{name}" name="{name}" value={q(value)}/>'


def _bprop(name, value):
    return f'\n\t\t\t\t<BooleanProperty displayName="{name}" name="{name}" value="{str(value).lower()}"/>'


RETURN_TYPE = (
    '\n\t\t\t\t<ModelProperty displayName="Action Type" name="actionType"><Model composite="true" '
    'considerDefaultProperties="true" displayModelType="Return" id={id} modelType="ActionTypeReturn">'
    "<ModelProperties/></Model></ModelProperty>"
)


class _Fragment:
    def __init__(self, seq, operator):
        self.seq, self.operator = seq, operator
        self.operands = []          # [guard, first message index, last index, top y, bottom y]

    def operand(self, guard):
        seq = self.seq
        if self.operands:
            self._close()
            seq.y += 4
        top = seq.y if self.operands else seq.y + 20
        self.operands.append([guard, len(seq.msgs), None, top, None])
        seq.y = top + 40


    def _close(self):
        op = self.operands[-1]
        op[2] = len(self.seq.msgs) - 1
        op[4] = self.seq.y - 10


class Seq:
    STEP_MIN = 150
    GAP = 40

    def __init__(self, name, participants):
        self.name = name
        self.parts = participants        # [(name, kind)]
        self.msgs = []                   # dicts
        self.frags = []                  # (_Fragment, top, bottom)
        self.y = 130

    # ---- messages --------------------------------------------------------
    def _add(self, a, b, text, kind):
        self.msgs.append(dict(a=a, b=b, text=text, kind=kind, y=self.y))
        self.y += self.GAP + (22 if a == b else 0)

    def call(self, a, b, text):
        self._add(a, b, text, "call")

    def async_call(self, a, b, text):
        self._add(a, b, text, "async")

    def ret(self, a, b, text):
        self._add(a, b, text, "return")

    def self_call(self, a, text):
        self._add(a, a, text, "self")

    @contextmanager
    def fragment(self, operator):
        f = _Fragment(self, operator)
        top = self.y
        yield f
        f._close()
        bottom = self.y
        self.frags.append((f, top, bottom))
        self.y = bottom + 24

    # ---- layout ----------------------------------------------------------
    def _layout(self):
        n = len(self.parts)
        widths = [max(80 if k == "actor" else 110, _w(nm, 14) + 24) for nm, k in self.parts]
        gaps = [max(self.STEP_MIN, (widths[i] + widths[i + 1]) / 2 + 30) for i in range(n - 1)]
        # every message label fits between its two lifelines
        for m in sorted(self.msgs, key=lambda m: abs(m["a"] - m["b"])):
            lo, hi = sorted((m["a"], m["b"]))
            if lo == hi:
                need = _w(m["text"], 14) + 60
                if hi < n - 1:
                    gaps[hi] = max(gaps[hi], need)
                continue
            need = _w(m["text"], 14) + 50
            have = sum(gaps[lo:hi])
            if have < need:
                extra = (need - have) / (hi - lo)
                for i in range(lo, hi):
                    gaps[i] += extra
        # a fragment starts between its first covered lifeline and the one before,
        # with room for its guards there
        left = 30 + widths[0] / 2
        for f, _, _ in self.frags:
            c0 = min(self._covered(f))
            guard = self._guard_w(f)
            if c0 == 0:
                left = max(left, guard + 20)
            else:
                gaps[c0 - 1] = max(gaps[c0 - 1], guard + widths[c0 - 1] / 2 + 20)
        xs = [round(left)]
        for g in gaps:
            xs.append(round(xs[-1] + g))
        return xs, widths

    @staticmethod
    def _guard_w(f):
        return max(_w(f"[{op[0]}]", 14) for op in f.operands) + 64

    def _covered(self, f):
        idx = set()
        for op in f.operands:
            for m in self.msgs[op[1]:op[2] + 1]:
                idx.update((m["a"], m["b"]))
        return idx

    # ---- XML -------------------------------------------------------------
    def xml(self):
        p = Project()
        xs, widths = self._layout()
        st = {k: p.el("Stereotype", k, extra=_sprop("baseType", "InteractionLifeLine"))
              for k in ("boundary", "control", "entity")}
        d = p.diagram(self.name, "InteractionDiagram")
        bottom = self.y + 20
        els, shapes = [], []
        for (nm, kind), x, w in zip(self.parts, xs, widths):
            if kind == "actor":
                el = p.el("InteractionActor", nm)
                sh = d.add(Shape(el, x - 40, 10, 80, bottom, shape_type="InteractionActor"))
            else:
                extra = _refs("stereotypes", [st[kind]]) if kind in st else ""
                el = p.el("InteractionLifeLine", nm, extra=extra)
                sh = d.add(Shape(el, x - w / 2, 10, w, bottom))
            els.append(el)
            shapes.append(sh)
        # activations. Boundary/control lifelines keep one bar from their first call
        # to their last message; entities and external systems get one bar per call,
        # closed by the matching return (or just after the call).
        spans = {}
        for i, (nm, kind) in enumerate(self.parts):
            if kind == "actor":
                continue
            mine = [m for m in self.msgs if i in (m["a"], m["b"])]
            if not mine:
                continue
            if kind in ("boundary", "control"):
                calls = [m["y"] for m in mine if m["b"] == i and m["kind"] in ("call", "async")]
                start = (min(calls) if calls else min(m["y"] for m in mine)) - 6
                end = max(m["y"] + (22 if m["a"] == m["b"] else 0) for m in mine) + 10
                spans[i] = [(start, end)]
                continue
            out = []
            for k, m in enumerate(mine):
                if m["b"] == i and m["kind"] in ("call", "async"):
                    nxt = mine[k + 1] if k + 1 < len(mine) else None
                    end = nxt["y"] + 8 if nxt is not None and nxt["a"] == i and nxt["kind"] == "return" else m["y"] + 16
                    out.append((m["y"] - 6, end))
            spans[i] = out
        act = {}
        for i, lst in spans.items():
            for start, end in lst:
                a_el = Element("Activation", "", els[i])
                act.setdefault(i, []).append((start, end, d.add(Shape(a_el, xs[i] - 6, start, 12, end - start), shapes[i])))

        def bar(i, y):
            for start, end, sh in act.get(i, []):
                if start - 1 <= y <= end + 1:
                    return sh
            return None

        for m in self.msgs:
            a, b, y = m["a"], m["b"], m["y"]
            ba, bb = bar(a, y), bar(b, y)
            extra = ""
            if ba is not None:
                extra += _ref("fromActivation", ba.el)
            if bb is not None:
                extra += _ref("toActivation", bb.el)
            if m["kind"] == "return":
                extra += RETURN_TYPE.format(id=q(new_id()))
            if m["kind"] == "async":
                extra += _bprop("asynchronous", True)
            if m["kind"] == "self":
                extra += _sprop("type", "Self Message")
            rel = p.rel("Message", els[a], els[b], m["text"], extra=extra)
            sa = ba or shapes[a]
            sb = bb or shapes[b]
            if a == b:
                x0 = int(round(xs[a] + 6))
                pts = [(x0, y), (x0 + 34, y), (x0 + 34, y + 18), (x0, y + 18)]
                d.conns.append(Conn(rel, sa, sb, points=pts, label_xy=(x0 + 40, y - 4)))
                continue
            right = xs[b] > xs[a]
            ha, hb = (6 if ba is not None else 0), (6 if bb is not None else 0)
            xa = xs[a] + (ha if right else -ha)
            xb = xs[b] + (-hb if right else hb)
            d.conns.append(Conn(rel, sa, sb, points=[(int(xa), y), (int(xb), y)]))
        # combined fragments
        for f, top, bot in self.frags:
            covered = sorted(self._covered(f))
            x0 = xs[covered[0]] - self._guard_w(f)
            x1 = xs[covered[-1]] + 70
            cf = Element("CombinedFragment", "", None,
                         extra=_sprop("interactionOperator", f.operator) + _refs("coveredLifeLines", [els[i] for i in covered]))
            p.elements.append(cf)
            CF = d.add(Shape(cf, x0, top, x1 - x0, bot - top, fill=TRANSPARENT))
            for guard, _, _, otop, obot in f.operands:
                g = (f'\n\t\t\t\t<ModelProperty displayName="Guard" name="guard"><Model composite="true" '
                     f'considerDefaultProperties="true" displayModelType="Interaction Constraint" id={q(new_id())} '
                     f'modelType="InteractionConstraint"><ModelProperties><StringProperty displayName="Constraint" '
                     f'name="constraint" value={q(guard)}/></ModelProperties></Model></ModelProperty>')
                op = Element("InteractionOperand", "", cf, extra=g)
                d.add(Shape(op, x0, otop, x1 - x0, obot - otop, fill=TRANSPARENT), CF)
        return p.xml()
