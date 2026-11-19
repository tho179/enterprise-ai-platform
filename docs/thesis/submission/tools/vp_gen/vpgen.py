"""Minimal Visual Paradigm XML generator (ImportXML format) for the thesis diagrams.

Every shape is filled with the report blue Cr:122,207,245,255 (same as Chapters 3-4).
"""
from __future__ import annotations

import itertools
import random
import string
from xml.sax.saxutils import escape, quoteattr

BLUE = "Cr:122,207,245,255"
WHITE = "Cr:255,255,255,255"
ORANGE = "Cr:255,192,128,255"  # database diagrams
_rng = random.Random(20261116)
_ALPHA = string.ascii_letters + string.digits + "._"


def new_id() -> str:
    return "".join(_rng.choice(_ALPHA) for _ in range(6)) + "WGAqAEpQ" + "".join(
        _rng.choice(_ALPHA) for _ in range(2)
    )


def q(v) -> str:
    return quoteattr(str(v))


class Element:
    def __init__(self, kind, name="", parent=None, extra="", **props):
        self.id = new_id()
        self.kind = kind
        self.name = name
        self.children: list[Element] = []
        self.props = props
        self.extra = extra
        if parent is not None:
            parent.children.append(self)

    def xml(self, depth=2) -> str:
        pad = "\t" * depth
        extra = ""
        for key, value in self.props.items():
            if isinstance(value, bool):
                tag, val = "BooleanProperty", str(value).lower()
            elif isinstance(value, int):
                tag, val = "IntegerProperty", str(value)
            else:
                tag, val = "StringProperty", str(value)
            extra += f'\n{pad}\t\t<{tag} displayName={q(key)} name={q(key)} value={q(val)}/>'
        if self.kind == "NOTE":
            extra += (
                f'\n{pad}\t\t<HTMLProperty displayName="Description" name="documentation" '
                f'plainTextValue={q(self.name)} value={q(self.name)}/>'
            )
        kids = ""
        if self.children:
            kids = f"\n{pad}\t<ChildModels>" + "".join(
                "\n" + c.xml(depth + 2) for c in self.children
            ) + f"\n{pad}\t</ChildModels>"
        return (
            f'{pad}<Model composite="false" considerDefaultProperties="true" displayModelType={q(self.kind)} '
            f'id={q(self.id)} modelType={q(self.kind)} name={q(self.name)}>\n'
            f'{pad}\t<ModelProperties>\n'
            f'{pad}\t\t<StringProperty displayName="Name" name="name" value={q(self.name)}/>{extra}{self.extra}\n'
            f'{pad}\t</ModelProperties>{kids}\n'
            f'{pad}</Model>'
        )


class Relation:
    def __init__(self, kind, src: Element, dst: Element, name="", extra=""):
        self.extra = extra
        self.id = new_id()
        self.kind = kind
        self.src = src
        self.dst = dst
        self.name = name

    def xml(self, depth=4) -> str:
        pad = "\t" * depth
        name = f' name={q(self.name)}' if self.name else ""
        if self.kind == "Association":
            ends = ""
            for tag, el in (("FromEnd", self.src), ("ToEnd", self.dst)):
                ends += (
                    f'\n{pad}\t<{tag}>\n{pad}\t\t<Model composite="true" considerDefaultProperties="true" '
                    f'displayModelType="Association End" id={q(new_id())} modelType="AssociationEnd">\n'
                    f'{pad}\t\t\t<ModelProperties>\n'
                    f'{pad}\t\t\t\t<ModelRefProperty displayName="End Model Element" name="EndModelElement">'
                    f'<ModelRef id={q(el.id)}/></ModelRefProperty>\n'
                    f'{pad}\t\t\t\t<TextModelProperty displayName="Type" name="type"><ModelRef id={q(el.id)}/></TextModelProperty>\n'
                    f'{pad}\t\t\t</ModelProperties>\n{pad}\t\t</Model>\n{pad}\t</{tag}>'
                )
            return (
                f'{pad}<Model composite="false" considerDefaultProperties="true" displayModelType="Association" '
                f'id={q(self.id)} modelType="Association"{name}>\n'
                f'{pad}\t<ModelProperties>\n'
                f'{pad}\t\t<StringProperty displayName="Name" name="name" value={q(self.name)}/>\n'
                f'{pad}\t\t<ModelRefProperty displayName="End Relationship From Meta Model Element" '
                f'name="endRelationshipFromMetaModelElement"><ModelRef id={q(self.src.id)}/></ModelRefProperty>\n'
                f'{pad}\t\t<ModelRefProperty displayName="End Relationship To Meta Model Element" '
                f'name="endRelationshipToMetaModelElement"><ModelRef id={q(self.dst.id)}/></ModelRefProperty>\n'
                f'{pad}\t</ModelProperties>{ends}\n{pad}</Model>'
            )
        return (
            f'{pad}<Model composite="false" considerDefaultProperties="true" displayModelType={q(self.kind)} '
            f'id={q(self.id)} modelType={q(self.kind)}{name}>\n'
            f'{pad}\t<ModelProperties>\n'
            f'{pad}\t\t<StringProperty displayName="Name" name="name" value={q(self.name)}/>\n'
            f'{pad}\t\t<ModelRefProperty displayName="From" name="from"><ModelRef id={q(self.src.id)}/></ModelRefProperty>\n'
            f'{pad}\t\t<ModelRefProperty displayName="To" name="to"><ModelRef id={q(self.dst.id)}/></ModelRefProperty>{self.extra}\n'
            f'{pad}\t</ModelProperties>\n{pad}</Model>'
        )


class Shape:
    def __init__(self, el: Element, x, y, w, h, shape_type=None, fill=BLUE, caption=None, font=11, bold=False, fit=False, extra=""):
        self.extra = extra
        self.id = new_id()
        self.el = el
        self.type = shape_type or el.kind
        self.x, self.y, self.w, self.h = int(x), int(y), int(w), int(h)
        self.fill = fill
        self.children: list[Shape] = []
        self.caption = caption
        self.font = font
        self.bold = bold
        self.fit = fit

    def cx(self):
        return self.x + self.w // 2

    def cy(self):
        return self.y + self.h // 2

    def xml(self, z, depth=3) -> str:
        pad = "\t" * depth
        if self.caption is not None:
            cx, cy, cw, ch = self.caption
            cap = f'<Caption height="{ch}" side="None" visible="true" width="{cw}" x="{cx}" y="{cy}"/>'
        else:
            cap = f'<Caption height="{self.h}" side="Center" visible="true" width="{self.w}" x="-14" y="-8"/>'
        zz = next(z) if not isinstance(z, int) else z
        counter = z if not isinstance(z, int) else itertools.count(z + 1)
        kids = ""
        if self.children:
            kids = f"\n{pad}\t<ChildShapes>" + "".join(
                "\n" + c.xml(counter, depth + 2) for c in self.children
            ) + f"\n{pad}\t</ChildShapes>"
        return (
            f'{pad}<Shape height="{self.h}" id={q(self.id)} model={q(self.el.id)} name={q(self.el.name)} '
            f'shapeType={q(self.type)} width="{self.w}" x="{self.x}" y="{self.y}" zorder="{zz}">\n'
            f'{pad}\t<DiagramElementProperties>\n'
            f'{pad}\t\t<IntegerProperty displayName="ZOrder" name="zOrder" value="{zz}"/>\n'
            f'{pad}\t\t<ModelRefProperty displayName="Meta Model Element" name="metaModelElement"><ModelRef id={q(self.el.id)}/></ModelRefProperty>\n'
            + (f'{pad}\t\t<BooleanProperty displayName="Request Fit Size" name="requestFitSize" value="true"/>\n' if self.fit else '')
            + (f'{pad}\t\t{self.extra}\n' if self.extra else '')
            + f'{pad}\t</DiagramElementProperties>\n'
            f'{pad}\t<ElementFont color="Cr:0,0,0,255" name="Dialog" size="{self.font}" style="{1 if self.bold else 0}"/>\n'
            f'{pad}\t<Line cap="0" color="Cr:0,0,0,255" transparency="0" weight="1.0"><Stroke/></Line>\n'
            f'{pad}\t{cap}{kids}\n'
            f'{pad}\t<FillColor color="{self.fill}" style="1" transparency="0" type="1"/>\n'
            f'{pad}</Shape>'
        )


class Conn:
    def __init__(self, rel: Relation, a: Shape, b: Shape, points=None, label_xy=None):
        self.id = new_id()
        self.rel = rel
        self.a, self.b = a, b
        self.points = points
        self.label_xy = label_xy

    def xml(self, z, depth=3) -> str:
        pad = "\t" * depth
        pts = self.points or [(self.a.cx(), self.a.cy()), (self.b.cx(), self.b.cy())]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x, y = min(xs), min(ys)
        w, h = max(1, max(xs) - x), max(1, max(ys) - y)
        label_w = max(20, int(7.4 * len(self.rel.name)) + 16)
        t = 0.38 if self.rel.kind in ("Include", "Extend") else 0.5
        mx = pts[0][0] + (pts[-1][0] - pts[0][0]) * t
        my = pts[0][1] + (pts[-1][1] - pts[0][1]) * t
        lx, ly = self.label_xy or (int(mx - label_w / 2), int(my - 18))
        points = "".join(f'<Point x="{px}" y="{py}"/>' for px, py in pts)
        return (
            f'{pad}<Connector connectorStyle="Follow Diagram" from={q(self.a.id)} height="{h}" id={q(self.id)} '
            f'model={q(self.rel.id)} shapeType={q(self.rel.kind)} to={q(self.b.id)} width="{w}" x="{x}" y="{y}" zorder="{z}">\n'
            f'{pad}\t<DiagramElementProperties>\n'
            f'{pad}\t\t<IntegerProperty displayName="ZOrder" name="zOrder" value="{z}"/>\n'
            f'{pad}\t\t<ModelRefProperty displayName="Meta Model Element" name="metaModelElement"><ModelRef id={q(self.rel.id)}/></ModelRefProperty>\n'
            f'{pad}\t</DiagramElementProperties>\n'
            f'{pad}\t<ElementFont color="Cr:0,0,0,255" name="Dialog" size="11" style="0"/>\n'
            f'{pad}\t<Line cap="0" color="Cr:0,0,0,255" transparency="0" weight="1.0"><Stroke/></Line>\n'
            f'{pad}\t<Caption height="16" side="None" visible="true" width="{label_w}" x="{lx}" y="{ly}"/>\n'
            f'{pad}\t<Points>{points}</Points>\n'
            f'{pad}</Connector>'
        )


def border(s: Shape, tx, ty):
    """Point where the segment from the centre of `s` towards (tx, ty) leaves the shape."""
    import math

    cx, cy = s.x + s.w / 2, s.y + s.h / 2
    dx, dy = tx - cx, ty - cy
    if dx == 0 and dy == 0:
        return int(cx), int(cy)
    rx, ry = s.w / 2, s.h / 2
    if s.type == "UseCase":
        t = 1 / math.sqrt((dx / rx) ** 2 + (dy / ry) ** 2)
    else:
        t = min(rx / abs(dx) if dx else math.inf, ry / abs(dy) if dy else math.inf)
    return int(round(cx + dx * t)), int(round(cy + dy * t))


DIAGRAM_TYPES = {
    "UseCaseDiagram": "Use Case Diagram",
    "ClassDiagram": "Class Diagram",
    "ComponentDiagram": "Component Diagram",
    "ActivityDiagram": "Activity Diagram",
    "InteractionDiagram": "Sequence Diagram",
    "DeploymentDiagram": "Deployment Diagram",
    "ERDiagram": "Entity Relationship Diagram",
    "PackageDiagram": "Package Diagram",
    "StateDiagram": "State Machine Diagram",
}


class Diagram:
    def __init__(self, name, dtype):
        self.id = new_id()
        self.name = name
        self.dtype = dtype
        self.shapes: list[Shape] = []
        self.conns: list[Conn] = []

    def add(self, shape: Shape, parent: Shape | None = None) -> Shape:
        (parent.children if parent else self.shapes).append(shape)
        return shape

    def connect(self, rel, a, b, **kw) -> Conn:
        if not kw.get("points"):
            kw["points"] = [border(a, b.cx(), b.cy()), border(b, a.cx(), a.cy())]
        c = Conn(rel, a, b, **kw)
        self.conns.append(c)
        return c

    def xml(self) -> str:
        z = itertools.count(0)
        shapes = "\n".join(s.xml(z, 3) for s in self.shapes)
        conns = "\n".join(c.xml(next(z), 3) for c in self.conns)
        return (
            f'\t\t<Diagram connectorStyle="Follow Diagram" diagramType={q(self.dtype)} '
            f'displayDiagramType={q(DIAGRAM_TYPES.get(self.dtype, self.dtype))} documentation="" id={q(self.id)} '
            f'name={q(self.name)} rtfDocumentation="">\n'
            f'\t\t\t<Shapes>\n{shapes}\n\t\t\t</Shapes>\n'
            f'\t\t\t<Connectors>\n{conns}\n\t\t\t</Connectors>\n'
            f'\t\t</Diagram>'
        )


class Project:
    def __init__(self):
        self.elements: list[Element] = []
        self.relations: list[Relation] = []
        self.diagrams: list[Diagram] = []

    def el(self, kind, name="", parent=None, extra="", **props) -> Element:
        # One model element per (kind, name): VP renames duplicates ("Người dùng2").
        if parent is None and kind in ("Actor", "UseCase", "Class", "Component", "InteractionLifeLine"):
            registry = self.__dict__.setdefault("_named", {})
            if (kind, name) in registry:
                return registry[(kind, name)]
            e = Element(kind, name, None, extra, **props)
            registry[(kind, name)] = e
            self.elements.append(e)
            return e
        e = Element(kind, name, parent, extra, **props)
        if parent is None:
            self.elements.append(e)
        return e

    def rel(self, kind, a, b, name="", extra="") -> Relation:
        r = Relation(kind, a, b, name, extra)
        self.relations.append(r)
        return r

    def diagram(self, name, dtype) -> Diagram:
        d = Diagram(name, dtype)
        self.diagrams.append(d)
        return d

    def xml(self) -> str:
        groups: dict[str, list[Relation]] = {}
        for r in self.relations:
            groups.setdefault(r.kind, []).append(r)
        containers = "".join(
            f'\n\t\t<Model composite="false" considerDefaultProperties="true" displayModelType="ModelRelationshipContainer" '
            f'id={q(new_id())} modelType="ModelRelationshipContainer" name={q(kind)}>\n'
            f'\t\t\t<ModelProperties><StringProperty displayName="Name" name="name" value={q(kind)}/></ModelProperties>\n'
            f'\t\t\t<ChildModels>\n' + "\n".join(r.xml(4) for r in rels) + '\n\t\t\t</ChildModels>\n\t\t</Model>'
            for kind, rels in groups.items()
        )
        models = "\n".join(e.xml(2) for e in self.elements)
        diagrams = "\n".join(d.xml() for d in self.diagrams)
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Project author="lsc" documentationType="html" exportedFromDifferentName="false" exporterVersion="16.1" '
            'name="DoAn" umlVersion="2.x" xmlns="http://www.visual-paradigm.com/product/vpuml/modelexporter">\n'
            f'\t<Models>\n{models}{containers}\n\t</Models>\n'
            f'\t<Diagrams>\n{diagrams}\n\t</Diagrams>\n'
            '</Project>\n'
        )
