"""
Build the v2 BPMN 2.0 files, SVG renders and lint report from model.py.

    python tools/v2/build.py

Outputs
  model/v2/*.bpmn        BPMN 2.0 XML with diagram interchange (opens in
                         Camunda Modeler / demo.bpmn.io)
  diagrams/v2/*.svg      rendered diagrams
  tools/v2/lint-report.md
"""
import html
import math
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import model as M  # noqa: E402

COLW = 170
POOL_LBL = 30
LANE_LBL = 44
X0 = POOL_LBL + LANE_LBL + 40
SIZES = {
    "user": (130, 80), "send": (130, 80), "call": (130, 80),
    "manual": (130, 80), "service": (130, 80),
    "gw_x": (50, 50), "gw_p": (50, 50),
}
EVENT = 36
FONT = "'Source Sans 3', 'Segoe UI', Arial, sans-serif"
INK = "#22201c"
TASK_FILL = "#fbf6dc"     # pale yellow, a nod to the source diagram
LANE_FILL = "#fafaf7"
LANE_BAND = "#efede4"
NOTE = "#6b6658"
ADDED = "#c8371e"      # elements not in the source diagram
ADDED_FILL = "#fbe9e4"


def cx_of(col):
    return X0 + 65 + col * COLW


def is_gw(t):
    return t.startswith("gw_")


def is_event(t):
    return t in ("start", "start_msg", "end", "end_error", "end_escalation",
                 "timer", "boundary_error", "boundary_escalation")


def is_task(t):
    return t in ("user", "send", "call", "manual", "service")


class Node:
    def __init__(self, d):
        self.__dict__.update(d)
        self.w, self.h = SIZES.get(self.type, (EVENT, EVENT))
        self.cx = self.cy = 0

    @property
    def x(self):
        return self.cx - self.w / 2

    @property
    def y(self):
        return self.cy - self.h / 2

    def side(self, s):
        return {"T": (self.cx, self.cy - self.h / 2),
                "B": (self.cx, self.cy + self.h / 2),
                "L": (self.cx - self.w / 2, self.cy),
                "R": (self.cx + self.w / 2, self.cy)}[s]

    def box(self, pad=0):
        return (self.x - pad, self.y - pad, self.x + self.w + pad, self.y + self.h + pad)


class Layout:
    def __init__(self, p):
        self.p = p
        self.rowh = p.get("rowh", 130)
        self.top = 20
        self.app_h = 0
        if p.get("applicant_pool"):
            self.app_h = 70
            self.top = 20 + self.app_h + 70
        self.lanes = []  # (key, name, top, rows)
        y = self.top
        if p["lanes"]:
            for key, rows in p["lanes"]:
                self.lanes.append((key, M.LANES[key], y, rows))
                y += rows * self.rowh
        else:
            self.lanes.append((None, None, y, p["rows"]))
            y += p["rows"] * self.rowh
        self.bottom = y
        self.nodes = {d["id"]: Node(d) for d in p["nodes"]}
        maxcol = max(d.get("col", 0) for d in p["nodes"] if "attach" not in d)
        self.width = cx_of(maxcol) + 65 + 60
        for n in self.nodes.values():
            if getattr(n, "attach", None):
                continue
            n.cx = cx_of(n.col)
            n.cy = self.rowy_of(n.lane, n.row)
        for n in self.nodes.values():
            if getattr(n, "attach", None):
                h = self.nodes[n.attach]
                n.cx = h.cx + getattr(n, "bx", 0)
                n.cy = h.cy + h.h / 2

    def lane(self, key):
        for l in self.lanes:
            if l[0] == key:
                return l
        raise KeyError(key)

    def lane_top(self, key):
        return self.lane(key)[2]

    def rowy_of(self, key, row):
        return self.lane(key)[2] + self.rowh / 2 + row * self.rowh

    def lane_y(self, key):
        return self.rowy_of(key, 0)

    def rowy(self, r):
        return self.lanes[0][2] + self.rowh / 2 + r * self.rowh


def route(L, f):
    s, t = L.nodes[f["src"]], L.nodes[f["tgt"]]
    if "wp" in f:
        return [tuple(map(float, p)) for p in f["wp"](L, s, t)]
    mode = f.get("mode")
    vside = lambda a, b: "B" if b.cy > a.cy else "T"
    if s.type.startswith("boundary"):
        if abs(t.cx - s.cx) < 1:
            return [s.side("B"), t.side("T")]
        return [s.side("B"), (s.cx, t.cy), t.side("L" if t.cx > s.cx else "R")]
    if mode is None:
        if abs(s.cy - t.cy) < 1:
            return [s.side("R"), t.side("L")]
        if abs(s.cx - t.cx) < 1:
            return [s.side(vside(s, t)), t.side(vside(t, s))]
        if is_gw(s.type):
            mode = "vh"
        elif is_gw(t.type):
            mode = "hv"
        else:
            mode = "z"
    if mode == "vh":
        return [s.side(vside(s, t)), (s.cx, t.cy), t.side("L")]
    if mode == "hv":
        return [s.side("R"), (t.cx, s.cy), t.side(vside(t, s))]
    if mode == "z":
        a, b = s.side("R"), t.side("L")
        mx = (a[0] + b[0]) / 2
        return [a, (mx, a[1]), (mx, b[1]), b]
    raise ValueError(mode)


def text_width(s, size=12):
    return len(s) * size * 0.5


def wrap(s, maxch):
    words, lines, cur = s.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > maxch:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines


def label_pos(n):
    """Return (x, y, anchor, lines) for event/gateway labels."""
    lp = getattr(n, "lp", None)
    lines = wrap(n.name, 30 if is_gw(n.type) else 20)
    lh = 14
    if is_gw(n.type):
        lines = wrap(n.name, 20)
        if not lp:
            used = getattr(n, "used", set())
            lp = ("aboveright" if "T" not in used else
                  "belowright" if "B" not in used else "aboveleft")
        if lp == "belowright":
            return n.cx + 20, n.cy + 38, "start", lines
        if lp == "aboveleft":
            return n.cx - 20, n.cy - 30 - (len(lines) - 1) * lh, "end", lines
        if lp == "aboveright":
            return n.cx + 20, n.cy - 30 - (len(lines) - 1) * lh, "start", lines
        if lp == "belowleft":
            return n.cx - 20, n.cy + 40, "end", lines
        if lp == "below":
            return n.cx + 8, n.cy + 42, "start", lines
    lp = lp or "below"
    if lp == "below":
        return n.cx, n.cy + n.h / 2 + 16, "middle", lines
    if lp == "left":
        return n.cx - n.w / 2 - 8, n.cy - (len(lines) - 1) * lh / 2 + 4, "end", lines
    if lp == "right":
        return n.cx + n.w / 2 + 8, n.cy - (len(lines) - 1) * lh / 2 + 4, "start", lines
    raise ValueError(lp)


def flow_label_pos(pts, name, side="right"):
    (x1, y1), (x2, y2) = pts[0], pts[1]
    if abs(x1 - x2) < 1:  # vertical first segment
        dy = 1 if y2 > y1 else -1
        if side == "left":
            return x1 - 6, y1 + dy * 20 + (8 if dy > 0 else 0), "end"
        return x1 + 6, y1 + dy * 20 + (8 if dy > 0 else 0), "start"
    return x1 + 6, y1 - 7, "start"


# ---------------------------------------------------------------------------
# XML
# ---------------------------------------------------------------------------
XML_TYPE = {
    "start": "startEvent", "start_msg": "startEvent", "end": "endEvent",
    "end_error": "endEvent", "end_escalation": "endEvent",
    "timer": "intermediateCatchEvent", "user": "userTask", "send": "sendTask",
    "call": "callActivity", "manual": "manualTask", "service": "serviceTask", "gw_x": "exclusiveGateway", "gw_p": "parallelGateway",
    "boundary_error": "boundaryEvent", "boundary_escalation": "boundaryEvent",
}


def esc(s):
    return html.escape(s or "", quote=True)


def build_xml(p, L, routes):
    pid = "Process_" + p["file"].replace("-", "_")
    nid = lambda i: f"{p['id']}_{i}"
    fid = lambda k: f"{p['id']}_Flow_{k}"
    inc, out = defaultdict(list), defaultdict(list)
    for k, f in enumerate(p["flows"]):
        out[f["src"]].append(fid(k))
        inc[f["tgt"]].append(fid(k))
    x = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" '
         'xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" '
         'xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" '
         'xmlns:di="http://www.omg.org/spec/DD/20100524/DI" '
         'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
         'xmlns:bioc="http://bpmn.io/schema/bpmn/biocolor/1.0" '
         f'id="Defs_{p["id"]}" targetNamespace="https://github.com/alphanAkbulut/public-service-license-process-bpmn2.0-case" '
         'exporter="tools/v2/build.py" exporterVersion="2.0">']
    used_err = {n.error for n in L.nodes.values() if getattr(n, "error", None)}
    used_esc = {n.escalation for n in L.nodes.values() if getattr(n, "escalation", None)}
    for e in sorted(used_err):
        name, code = M.ERRORS[e]
        x.append(f'  <bpmn:error id="{e}" name="{esc(name)}" errorCode="{code}" />')
    for e in sorted(used_esc):
        name, code = M.ESCALATIONS[e]
        x.append(f'  <bpmn:escalation id="{e}" name="{esc(name)}" escalationCode="{code}" />')
    if any(n.type == "start_msg" for n in L.nodes.values()):
        x.append('  <bpmn:message id="Msg_Application" name="License application" />')
    for g in p.get("groups", []):
        x.append(f'  <bpmn:category id="{p["id"]}_{g["id"]}_cat"><bpmn:categoryValue id="{p["id"]}_{g["id"]}_cv" value="{esc(g["label"])}" /></bpmn:category>')
    x.append(f'  <bpmn:collaboration id="Collab_{p["id"]}">')
    x.append(f'    <bpmn:participant id="Part_{p["id"]}" name="{esc(p["pool"])}" processRef="{pid}" />')
    if p.get("applicant_pool"):
        x.append(f'    <bpmn:participant id="Part_APP" name="{esc(p["applicant_pool"])}" />')
        for k, (a, b, nm, _) in enumerate(p["messages"]):
            ra = "Part_APP" if a == "APP" else nid(a)
            rb = "Part_APP" if b == "APP" else nid(b)
            x.append(f'    <bpmn:messageFlow id="{p["id"]}_MF_{k}" name="{esc(nm)}" sourceRef="{ra}" targetRef="{rb}" />')
    for a in p["annotations"]:
        pass
    x.append('  </bpmn:collaboration>')
    x.append(f'  <bpmn:process id="{pid}" name="{esc(p["name"])}" isExecutable="false">')
    if p["lanes"]:
        x.append(f'    <bpmn:laneSet id="LaneSet_{p["id"]}">')
        for key, name, _, _ in L.lanes:
            x.append(f'      <bpmn:lane id="{p["id"]}_Lane_{key}" name="{esc(name)}">')
            for n in L.nodes.values():
                lane = n.lane if not getattr(n, "attach", None) else L.nodes[n.attach].lane
                if lane == key:
                    x.append(f'        <bpmn:flowNodeRef>{nid(n.id)}</bpmn:flowNodeRef>')
            x.append('      </bpmn:lane>')
        x.append('    </bpmn:laneSet>')
    for n in L.nodes.values():
        tag = XML_TYPE[n.type]
        attrs = f'id="{nid(n.id)}"'
        if n.name:
            attrs += f' name="{esc(n.name)}"'
        if n.type == "call":
            attrs += f' calledElement="Process_{n.calls.replace("-", "_")}"'
        if n.type.startswith("boundary"):
            attrs += f' attachedToRef="{nid(n.attach)}"'
            if getattr(n, "interrupting", True) is False:
                attrs += ' cancelActivity="false"'
        body = []
        if getattr(n, "orig", None):
            body.append(f'<bpmn:documentation>Source step {n.orig}: {esc(M.ORIGINAL[n.orig][0])}</bpmn:documentation>')
        body += [f'<bpmn:incoming>{i}</bpmn:incoming>' for i in inc[n.id]]
        body += [f'<bpmn:outgoing>{o}</bpmn:outgoing>' for o in out[n.id]]
        if n.type in ("end_error", "boundary_error"):
            body.append(f'<bpmn:errorEventDefinition id="{nid(n.id)}_ed" errorRef="{n.error}" />')
        if n.type in ("end_escalation", "boundary_escalation"):
            body.append(f'<bpmn:escalationEventDefinition id="{nid(n.id)}_esd" escalationRef="{n.escalation}" />')
        if n.type == "start_msg":
            body.append(f'<bpmn:messageEventDefinition id="{nid(n.id)}_md" messageRef="Msg_Application" />')
        if n.type == "timer":
            body.append(f'<bpmn:timerEventDefinition id="{nid(n.id)}_td"><bpmn:timeDuration xsi:type="bpmn:tFormalExpression">P15D</bpmn:timeDuration></bpmn:timerEventDefinition>')
        x.append(f'    <bpmn:{tag} {attrs}>')
        x += ['      ' + b for b in body]
        x.append(f'    </bpmn:{tag}>')
    for k, f in enumerate(p["flows"]):
        nm = f' name="{esc(f["name"])}"' if f.get("name") else ""
        x.append(f'    <bpmn:sequenceFlow id="{fid(k)}"{nm} sourceRef="{nid(f["src"])}" targetRef="{nid(f["tgt"])}" />')
    for a in p["annotations"]:
        x.append(f'    <bpmn:textAnnotation id="{p["id"]}_{a["id"]}"><bpmn:text>{esc(a["text"])}</bpmn:text></bpmn:textAnnotation>')
        x.append(f'    <bpmn:association id="{p["id"]}_{a["id"]}_assoc" sourceRef="{p["id"]}_{a["id"]}" targetRef="{nid(a["target"])}" />')
    for g in p.get("groups", []):
        x.append(f'    <bpmn:group id="{p["id"]}_{g["id"]}" categoryValueRef="{p["id"]}_{g["id"]}_cv" />')
    x.append('  </bpmn:process>')
    # DI
    x.append(f'  <bpmndi:BPMNDiagram id="Diagram_{p["id"]}" name="{esc(p["name"])}">')
    x.append(f'    <bpmndi:BPMNPlane id="Plane_{p["id"]}" bpmnElement="Collab_{p["id"]}">')
    b = lambda X, Y, W, H: f'<dc:Bounds x="{X:.0f}" y="{Y:.0f}" width="{W:.0f}" height="{H:.0f}" />'
    x.append(f'      <bpmndi:BPMNShape id="Part_{p["id"]}_di" bpmnElement="Part_{p["id"]}" isHorizontal="true">{b(POOL_LBL - 30 + 10, L.top, L.width - 10, L.bottom - L.top)}</bpmndi:BPMNShape>')
    if p.get("applicant_pool"):
        x.append(f'      <bpmndi:BPMNShape id="Part_APP_di" bpmnElement="Part_APP" isHorizontal="true">{b(10, 20, L.width - 10, L.app_h)}</bpmndi:BPMNShape>')
    if p["lanes"]:
        for key, name, top, rows in L.lanes:
            x.append(f'      <bpmndi:BPMNShape id="{p["id"]}_Lane_{key}_di" bpmnElement="{p["id"]}_Lane_{key}" isHorizontal="true">{b(10 + POOL_LBL, top, L.width - 10 - POOL_LBL, rows * L.rowh)}</bpmndi:BPMNShape>')
    for n in L.nodes.values():
        extra = ' isMarkerVisible="true"' if n.type == "gw_x" else ""
        lab = ""
        if n.name and (is_event(n.type) or is_gw(n.type)) and not n.type.startswith("boundary"):
            lx, ly, anchor, lines = label_pos(n)
            w = max(text_width(l) for l in lines) + 4
            h = len(lines) * 14
            bx = lx - (w if anchor == "end" else w / 2 if anchor == "middle" else 0)
            lab = f'<bpmndi:BPMNLabel>{b(bx, ly - 11, w, h)}</bpmndi:BPMNLabel>'
        if getattr(n, "added_step", False):
            extra += f' bioc:stroke="{ADDED}" bioc:fill="{ADDED_FILL}"'
        x.append(f'      <bpmndi:BPMNShape id="{nid(n.id)}_di" bpmnElement="{nid(n.id)}"{extra}>{b(n.x, n.y, n.w, n.h)}{lab}</bpmndi:BPMNShape>')
    for a in p["annotations"]:
        t = L.nodes[a["target"]]
        ax, ay = t.cx + a["dx"], t.cy + a["dy"]
        ah = 14 * len(wrap(a["text"], int(a["w"] / 6.2))) + 10
        x.append(f'      <bpmndi:BPMNShape id="{p["id"]}_{a["id"]}_di" bpmnElement="{p["id"]}_{a["id"]}">{b(ax, ay, a["w"], ah)}</bpmndi:BPMNShape>')
    for k, f in enumerate(p["flows"]):
        pts = routes[k]
        wps = "".join(f'<di:waypoint x="{px:.0f}" y="{py:.0f}" />' for px, py in pts)
        lab = ""
        if f.get("name"):
            lx, ly, anc = flow_label_pos(pts, f["name"], f.get("lab", "right"))
            tw = text_width(f["name"], 11)
            lab = f'<bpmndi:BPMNLabel>{b(lx - (tw if anc == "end" else 0), ly - 11, tw, 14)}</bpmndi:BPMNLabel>'
        col = f' bioc:stroke="{ADDED}"' if f.get("added") else ""
        x.append(f'      <bpmndi:BPMNEdge id="{fid(k)}_di" bpmnElement="{fid(k)}"{col}>{wps}{lab}</bpmndi:BPMNEdge>')
    for g in p.get("groups", []):
        gx, gy, gw, gh = group_box(L, g)
        x.append(f'      <bpmndi:BPMNShape id="{p["id"]}_{g["id"]}_di" bpmnElement="{p["id"]}_{g["id"]}">{b(gx, gy, gw, gh)}<bpmndi:BPMNLabel>{b(gx + 8, gy + gh - 22, text_width(g["label"], 11.5), 16)}</bpmndi:BPMNLabel></bpmndi:BPMNShape>')
    for a in p["annotations"]:
        t = L.nodes[a["target"]]
        p1, p2 = assoc_points(L, a)
        x.append(f'      <bpmndi:BPMNEdge id="{p["id"]}_{a["id"]}_assoc_di" bpmnElement="{p["id"]}_{a["id"]}_assoc"><di:waypoint x="{p1[0]:.0f}" y="{p1[1]:.0f}" /><di:waypoint x="{p2[0]:.0f}" y="{p2[1]:.0f}" /></bpmndi:BPMNEdge>')
    if p.get("applicant_pool"):
        for k, (a, bb, nm, off) in enumerate(p["messages"]):
            p1, p2 = msg_points(L, a, bb, off)
            x.append(f'      <bpmndi:BPMNEdge id="{p["id"]}_MF_{k}_di" bpmnElement="{p["id"]}_MF_{k}"><di:waypoint x="{p1[0]:.0f}" y="{p1[1]:.0f}" /><di:waypoint x="{p2[0]:.0f}" y="{p2[1]:.0f}" /></bpmndi:BPMNEdge>')
    x.append('    </bpmndi:BPMNPlane>')
    x.append('  </bpmndi:BPMNDiagram>')
    x.append('</bpmn:definitions>')
    return "\n".join(x) + "\n"


def group_box(L, g):
    ns = [L.nodes[i] for i in g["nodes"]]
    pad = g.get("pad", 16)
    x1 = min(n.x for n in ns) - pad
    y1 = min(n.y for n in ns) - pad
    x2 = max(n.x + n.w for n in ns) + pad
    y2 = max(n.y + n.h for n in ns) + pad + g.get("extra_bottom", 0)
    return x1, y1, x2 - x1, y2 - y1


def assoc_points(L, a):
    t = L.nodes[a["target"]]
    ax, ay = t.cx + a["dx"], t.cy + a["dy"]
    ah = 14 * len(wrap(a["text"], int(a["w"] / 6.2))) + 10
    # anchor on annotation: nearest of left-mid / bottom-mid / top-mid
    cands = [(ax, ay + ah / 2), (ax + a["w"] / 2, ay + ah), (ax + a["w"] / 2, ay)]
    p1 = min(cands, key=lambda c: math.hypot(c[0] - t.cx, c[1] - t.cy))
    # anchor on target box edge toward p1
    dx, dy = p1[0] - t.cx, p1[1] - t.cy
    sx = (t.w / 2) / abs(dx) if dx else 1e9
    sy = (t.h / 2) / abs(dy) if dy else 1e9
    s = min(sx, sy)
    return p1, (t.cx + dx * s, t.cy + dy * s)


def msg_points(L, a, b, off):
    app_bottom = 20 + L.app_h
    if a == "APP":
        n = L.nodes[b]
        return (n.cx + off, app_bottom), (n.cx + off, n.cy - n.h / 2)
    n = L.nodes[a]
    return (n.cx + off, n.cy - n.h / 2), (n.cx + off, app_bottom)


# ---------------------------------------------------------------------------
# SVG
# ---------------------------------------------------------------------------
def svg_text(x, y, lines, anchor="middle", size=12, weight=400, fill=INK, lh=14, italic=False):
    st = ' font-style="italic"' if italic else ""
    out = [f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-size="{size}" font-weight="{weight}" fill="{fill}"{st}>']
    for i, l in enumerate(lines):
        out.append(f'<tspan x="{x:.1f}" dy="{0 if i == 0 else lh}">{esc(l)}</tspan>')
    out.append('</text>')
    return "".join(out)


def icon_user(x, y):
    return (f'<g transform="translate({x},{y})" fill="none" stroke="{INK}" stroke-width="1.1">'
            f'<circle cx="7" cy="5" r="3.4" fill="#fff"/><path d="M1 15 Q1 9 7 9 Q13 9 13 15 Z" fill="#fff"/></g>')


def icon_env(x, y, filled):
    f = INK if filled else "#fff"
    s = "#fff" if filled else INK
    return (f'<g transform="translate({x},{y})"><rect x="0" y="0" width="15" height="10" fill="{f}" stroke="{INK}" stroke-width="1.1"/>'
            f'<path d="M0 0 L7.5 5.5 L15 0" fill="none" stroke="{s}" stroke-width="1.1"/></g>')


def icon_hand(x, y):
    # BPMN manual-task hand, simplified
    return (f'<g transform="translate({x},{y})" fill="#fff" stroke="{INK}" stroke-width="1.1" stroke-linejoin="round">'
            f'<path d="M2 9 V5.5 Q2 4.3 3.2 4.3 Q4.4 4.3 4.4 5.5 V8 V3 Q4.4 1.8 5.6 1.8 Q6.8 1.8 6.8 3 V8 V2.2 Q6.8 1 8 1 Q9.2 1 9.2 2.2 V8 V3.2 Q9.2 2 10.4 2 Q11.6 2 11.6 3.2 V10 Q11.6 15 7 15 Q3.6 15 2.4 12 Z"/></g>')


def icon_gear(x, y):
    import math as _m
    pts = []
    for i in range(16):
        r = 7 if i % 2 == 0 else 5.2
        a = i * _m.pi / 8
        pts.append(f"{7 + r * _m.cos(a):.2f},{7 + r * _m.sin(a):.2f}")
    return (f'<g transform="translate({x},{y})"><polygon points="{" ".join(pts)}" fill="#fff" stroke="{INK}" stroke-width="1.1"/>'
            f'<circle cx="7" cy="7" r="2.2" fill="#fff" stroke="{INK}" stroke-width="1.1"/></g>')


def bolt(cx, cy, filled):
    f = INK if filled else "none"
    return (f'<path d="M{cx-6},{cy+7} L{cx-2},{cy-6} L{cx+2},{cy+1} L{cx+6},{cy-7} L{cx+3},{cy+7} L{cx-1},{cy-1} Z" '
            f'fill="{f}" stroke="{INK}" stroke-width="1.1" stroke-linejoin="round"/>')


def escal(cx, cy, filled):
    f = INK if filled else "none"
    return (f'<path d="M{cx},{cy-8} L{cx+6},{cy+7} L{cx},{cy+2} L{cx-6},{cy+7} Z" fill="{f}" stroke="{INK}" '
            f'stroke-width="1.1" stroke-linejoin="round"/>')


def render_node(n):
    o = []
    if is_task(n.type):
        sw = 3 if n.type == "call" else 1.4
        dc = f' data-calls="{n.calls}"' if n.type == "call" else ""
        added = getattr(n, "added_step", False)
        fill, stroke = (ADDED_FILL, ADDED) if added else (TASK_FILL, INK)
        dash = ' stroke-dasharray="7 4"' if added else ""
        o.append(f'<rect x="{n.x:.1f}" y="{n.y:.1f}" width="{n.w}" height="{n.h}" rx="9" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{dash}{dc}/>')
        if n.type == "user":
            o.append(icon_user(n.x + 7, n.y + 6))
        elif n.type == "send":
            o.append(icon_env(n.x + 8, n.y + 8, True))
        elif n.type == "manual":
            o.append(icon_hand(n.x + 7, n.y + 6))
        elif n.type == "service":
            o.append(icon_gear(n.x + 7, n.y + 6))
        lines = wrap(n.name, 19)
        ty = n.cy - (len(lines) - 1) * 7 + 5 + (2 if n.type != "call" else 0)
        o.append(svg_text(n.cx, ty, lines, weight=600 if n.type == "call" else 400))
        if n.type == "call":
            bx, by = n.cx - 7, n.y + n.h - 17
            o.append(f'<rect x="{bx}" y="{by}" width="14" height="14" fill="#fff" stroke="{INK}" stroke-width="1.2"/>'
                     f'<path d="M{bx+3} {by+7} H{bx+11} M{bx+7} {by+3} V{by+11}" stroke="{INK}" stroke-width="1.4"/>')
    elif is_gw(n.type):
        c, r = (n.cx, n.cy), 25
        o.append(f'<path d="M{c[0]} {c[1]-r} L{c[0]+r} {c[1]} L{c[0]} {c[1]+r} L{c[0]-r} {c[1]} Z" fill="#fff" stroke="{INK}" stroke-width="1.4"/>')
        if n.type == "gw_x":
            d = 7.5
            o.append(f'<path d="M{c[0]-d} {c[1]-d} L{c[0]+d} {c[1]+d} M{c[0]+d} {c[1]-d} L{c[0]-d} {c[1]+d}" stroke="{INK}" stroke-width="3.4" stroke-linecap="round"/>')
        else:
            d = 10
            o.append(f'<path d="M{c[0]} {c[1]-d} V{c[1]+d} M{c[0]-d} {c[1]} H{c[0]+d}" stroke="{INK}" stroke-width="3.4" stroke-linecap="round"/>')
    else:
        cx, cy, r = n.cx, n.cy, EVENT / 2
        t = n.type
        if t in ("start", "start_msg"):
            o.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#fff" stroke="{INK}" stroke-width="1.4"/>')
            if t == "start_msg":
                o.append(icon_env(cx - 7.5, cy - 5, False))
        elif t.startswith("end"):
            o.append(f'<circle cx="{cx}" cy="{cy}" r="{r-1.5}" fill="#fff" stroke="{INK}" stroke-width="3.6"/>')
            if t == "end_error":
                o.append(bolt(cx, cy, True))
            if t == "end_escalation":
                o.append(escal(cx, cy, True))
        elif t == "timer" or t.startswith("boundary"):
            dash = ' stroke-dasharray="4 2.5"' if getattr(n, "interrupting", True) is False else ""
            o.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#fff" stroke="{INK}" stroke-width="1.3"{dash}/>'
                     f'<circle cx="{cx}" cy="{cy}" r="{r-3.5}" fill="none" stroke="{INK}" stroke-width="1.3"{dash}/>')
            if t == "timer":
                o.append(f'<circle cx="{cx}" cy="{cy}" r="9.5" fill="#fff" stroke="{INK}" stroke-width="1.2"/>'
                         f'<path d="M{cx} {cy-7} V{cy} L{cx+5} {cy+3}" fill="none" stroke="{INK}" stroke-width="1.2"/>')
            elif t == "boundary_error":
                o.append(bolt(cx, cy, False))
            else:
                o.append(escal(cx, cy, False))
    if getattr(n, "added_step", False) and not is_task(n.type):
        o = [x.replace(f'stroke="{INK}"', f'stroke="{ADDED}"').replace(f'fill="{INK}"', f'fill="{ADDED}"') for x in o]
    if n.name and (is_event(n.type) or is_gw(n.type)) and not n.type.startswith("boundary"):
        lx, ly, anchor, lines = label_pos(n)
        o.append(svg_text(lx, ly, lines, anchor=anchor, size=11.5, lh=13.5,
                          fill=ADDED if getattr(n, "added_step", False) else INK))
    return "".join(o)


def path_d(pts):
    return "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)


def render_svg(p, L, routes):
    W, H = L.width + 10, L.bottom + 40
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}" font-family="{FONT}">',
         f'<title>{esc(p["name"])}</title>',
         '<defs>'
         f'<marker id="seq" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="9" markerHeight="9" orient="auto"><path d="M0 1 L10 5 L0 9 Z" fill="{INK}"/></marker>'
         f'<marker id="seqa" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="9" markerHeight="9" orient="auto"><path d="M0 1 L10 5 L0 9 Z" fill="{ADDED}"/></marker>'
         f'<marker id="msg" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="10" markerHeight="10" orient="auto"><path d="M1 1.5 L11 6 L1 10.5 Z" fill="#fff" stroke="{INK}" stroke-width="1"/></marker>'
         f'<marker id="msgstart" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="8" markerHeight="8"><circle cx="5" cy="5" r="3.5" fill="#fff" stroke="{INK}" stroke-width="1"/></marker>'
         '</defs>',
         f'<rect width="{W:.0f}" height="{H:.0f}" fill="#ffffff"/>']
    # applicant pool
    if p.get("applicant_pool"):
        o.append(f'<rect x="10" y="20" width="{L.width-10:.0f}" height="{L.app_h}" fill="{LANE_FILL}" stroke="{INK}" stroke-width="1.4"/>')
        o.append(svg_text((L.width) / 2, 20 + L.app_h / 2 + 5, [p["applicant_pool"]], size=13, weight=600))
    # main pool
    o.append(f'<rect x="10" y="{L.top}" width="{L.width-10:.0f}" height="{L.bottom-L.top:.0f}" fill="#fff" stroke="{INK}" stroke-width="1.4"/>')
    o.append(f'<line x1="{10+POOL_LBL}" y1="{L.top}" x2="{10+POOL_LBL}" y2="{L.bottom}" stroke="{INK}" stroke-width="1.4"/>')
    my = (L.top + L.bottom) / 2
    o.append(f'<text transform="translate({10+POOL_LBL/2+5},{my}) rotate(-90)" text-anchor="middle" font-size="13" font-weight="600" fill="{INK}">{esc(p["pool"])}</text>')
    if p["lanes"]:
        for key, name, top, rows in L.lanes:
            h = rows * L.rowh
            o.append(f'<rect x="{10+POOL_LBL}" y="{top}" width="{L.width-10-POOL_LBL:.0f}" height="{h}" fill="{LANE_FILL}" stroke="{INK}" stroke-width="0.9"/>')
            o.append(f'<rect x="{10+POOL_LBL}" y="{top}" width="{LANE_LBL}" height="{h}" fill="{LANE_BAND}" stroke="{INK}" stroke-width="0.9"/>')
            lines = wrap(name, max(12, int(h / 6.0)))
            cy = top + h / 2
            o.append(f'<text transform="translate({10+POOL_LBL+LANE_LBL/2+4 - (len(lines)-1)*6.5},{cy}) rotate(-90)" text-anchor="middle" font-size="11.5" fill="{INK}">'
                     + "".join(f'<tspan x="0" dy="{0 if i == 0 else 13}">{esc(l)}</tspan>' for i, l in enumerate(lines)) + '</text>')
    else:
        o.append(f'<rect x="{10+POOL_LBL}" y="{L.top}" width="{L.width-10-POOL_LBL:.0f}" height="{L.bottom-L.top:.0f}" fill="{LANE_FILL}" stroke="none"/>')
    # groups
    for g in p.get("groups", []):
        gx, gy, gw, gh = group_box(L, g)
        o.append(f'<rect x="{gx:.1f}" y="{gy:.1f}" width="{gw:.1f}" height="{gh:.1f}" rx="12" fill="none" stroke="{NOTE}" stroke-width="1.4" stroke-dasharray="9 4 2 4"/>')
        o.append(svg_text(gx + 10, gy + gh - 9, [g["label"]], anchor="start", size=11.5, fill=NOTE, weight=600))
    # flows
    for k, f in enumerate(p["flows"]):
        pts = routes[k]
        if f.get("added"):
            o.append(f'<path d="{path_d(pts)}" fill="none" stroke="{ADDED}" stroke-width="1.5" stroke-linejoin="round" marker-end="url(#seqa)"/>')
        else:
            o.append(f'<path d="{path_d(pts)}" fill="none" stroke="{INK}" stroke-width="1.3" stroke-linejoin="round" marker-end="url(#seq)"/>')
    # annotations
    for a in p["annotations"]:
        t = L.nodes[a["target"]]
        ax, ay = t.cx + a["dx"], t.cy + a["dy"]
        lines = wrap(a["text"], int(a["w"] / 6.2))
        ah = 14 * len(lines) + 10
        p1, p2 = assoc_points(L, a)
        o.append(f'<path d="M{p1[0]:.1f} {p1[1]:.1f} L{p2[0]:.1f} {p2[1]:.1f}" stroke="{NOTE}" stroke-width="1.1" stroke-dasharray="2 3" fill="none"/>')
        o.append(f'<rect x="{ax:.1f}" y="{ay:.1f}" width="{a["w"]}" height="{ah}" fill="#fff" fill-opacity="0.85" stroke="none"/>')
        o.append(f'<path d="M{ax+12:.1f} {ay:.1f} H{ax:.1f} V{ay+ah:.1f} H{ax+12:.1f}" stroke="{NOTE}" stroke-width="1.2" fill="none"/>')
        o.append(svg_text(ax + 8, ay + 17, lines, anchor="start", size=11, fill=NOTE, lh=14))
    # nodes
    for n in L.nodes.values():
        if not n.type.startswith("boundary"):
            o.append(render_node(n))
    for n in L.nodes.values():
        if n.type.startswith("boundary"):
            o.append(render_node(n))
    # flow labels (on top)
    for k, f in enumerate(p["flows"]):
        if f.get("name"):
            lx, ly, anchor = flow_label_pos(routes[k], f["name"], f.get("lab", "right"))
            w = text_width(f["name"], 11) + 4
            rx = lx - 2 - (w - 4 if anchor == "end" else 0)
            o.append(f'<rect x="{rx:.1f}" y="{ly-11:.1f}" width="{w:.1f}" height="14" fill="#fff" fill-opacity="0.9"/>')
            o.append(svg_text(lx, ly, [f["name"]], anchor=anchor, size=11, fill=ADDED if f.get("added") else INK, italic="label added" in f["name"]))
    # message flows
    if p.get("applicant_pool"):
        for k, (a, b, nm, off) in enumerate(p["messages"]):
            p1, p2 = msg_points(L, a, b, off)
            o.append(f'<path d="M{p1[0]:.1f} {p1[1]:.1f} L{p2[0]:.1f} {p2[1]:.1f}" stroke="{INK}" stroke-width="1.2" stroke-dasharray="7 4" fill="none" marker-start="url(#msgstart)" marker-end="url(#msg)"/>')
            ly = (p1[1] + p2[1]) / 2 - 8
            o.append(svg_text(p1[0] + (6 if off >= 0 else -6), ly, wrap(nm, 16), anchor="start" if off >= 0 else "end", size=11, lh=13))
    o.append('</svg>')
    return "\n".join(o) + "\n"


# ---------------------------------------------------------------------------
# Lint (subset of bpmnlint 'recommended' + layout checks)
# ---------------------------------------------------------------------------
def seg_hits_box(a, b, box):
    (x1, y1), (x2, y2) = a, b
    bx1, by1, bx2, by2 = box
    if abs(x1 - x2) < 0.5:
        return bx1 < x1 < bx2 and max(min(y1, y2), by1) < min(max(y1, y2), by2)
    if abs(y1 - y2) < 0.5:
        return by1 < y1 < by2 and max(min(x1, x2), bx1) < min(max(x1, x2), bx2)
    return False


def lint(p, L, routes):
    issues = []
    nodes = L.nodes
    inc, out = defaultdict(list), defaultdict(list)
    seen = set()
    for f in p["flows"]:
        for e in (f["src"], f["tgt"]):
            if e not in nodes:
                issues.append(("error", f"flow references unknown node {e}"))
        key = (f["src"], f["tgt"])
        if key in seen:
            issues.append(("error", f"duplicate sequence flow {key}"))
        seen.add(key)
        out[f["src"]].append(f)
        inc[f["tgt"]].append(f)
    starts = [n for n in nodes.values() if n.type.startswith("start")]
    ends = [n for n in nodes.values() if n.type.startswith("end")]
    if len(starts) != 1:
        issues.append(("error", "process needs exactly one start event"))
    if not ends:
        issues.append(("error", "process has no end event"))
    for n in nodes.values():
        t = n.type
        if not t.startswith("start") and not t.startswith("boundary") and not inc[n.id]:
            issues.append(("error", f"{n.id} has no incoming flow"))
        if not t.startswith("end") and not out[n.id]:
            issues.append(("error", f"{n.id} has no outgoing flow"))
        if (is_task(t) or is_event(t)) and len(inc[n.id]) > 1:
            issues.append(("error", f"{n.id} fake join (multiple incoming)"))
        if (is_task(t) or is_event(t)) and len(out[n.id]) > 1:
            issues.append(("error", f"{n.id} implicit split (multiple outgoing)"))
        if is_gw(t):
            if len(inc[n.id]) > 1 and len(out[n.id]) > 1:
                issues.append(("error", f"{n.id} gateway both joins and forks"))
            if len(inc[n.id]) == 1 and len(out[n.id]) == 1:
                issues.append(("error", f"{n.id} superfluous gateway"))
            if t == "gw_x" and len(out[n.id]) > 1:
                if not n.name:
                    issues.append(("error", f"{n.id} diverging gateway without label"))
                for f in out[n.id]:
                    if not f.get("name"):
                        issues.append(("error", f"{n.id} outgoing flow to {f['tgt']} without label"))
        if (is_task(t) or is_event(t)) and not n.name:
            issues.append(("error", f"{n.id} missing label"))
        if t.startswith("boundary") and len(out[n.id]) != 1:
            issues.append(("error", f"{n.id} boundary needs exactly one outgoing flow"))
    # reachability
    reach, stack = set(), [s.id for s in starts]
    while stack:
        i = stack.pop()
        if i in reach:
            continue
        reach.add(i)
        stack += [f["tgt"] for f in out[i]]
        stack += [b.id for b in nodes.values() if getattr(b, "attach", None) == i]
    for n in nodes.values():
        if n.id not in reach:
            issues.append(("error", f"{n.id} unreachable from start"))
    # layout: flow segments crossing unrelated nodes
    for k, f in enumerate(p["flows"]):
        pts = routes[k]
        for n in nodes.values():
            if n.id in (f["src"], f["tgt"]) or getattr(n, "attach", None) in (f["src"],) or n.id == getattr(nodes[f["src"]], "attach", None):
                continue
            for a, b in zip(pts, pts[1:]):
                if seg_hits_box(a, b, n.box(2)):
                    issues.append(("layout", f"flow {f['src']}->{f['tgt']} passes through {n.id}"))
                    break
        for a, b in zip(pts, pts[1:]):
            if abs(a[0] - b[0]) > 0.5 and abs(a[1] - b[1]) > 0.5:
                issues.append(("layout", f"flow {f['src']}->{f['tgt']} has a diagonal segment"))
    # layout: nodes outside their lane
    if p["lanes"]:
        for n in nodes.values():
            if getattr(n, "attach", None):
                continue
            key, name, top, rows = L.lane(n.lane)
            if not (top < n.cy - n.h / 2 and n.cy + n.h / 2 < top + rows * L.rowh):
                issues.append(("layout", f"{n.id} outside lane {key}"))
    return issues


def write_docs(used):
    """Generate traceability, responsibility and milestone tables from the model."""
    by_file = {p["file"]: p for p in M.PROCESSES}
    def lane_of(p, n):
        if not p["lanes"]:
            return "— (role in task name)"
        nd = {d["id"]: d for d in p["nodes"]}
        d = nd[n]
        if d.get("attach"):
            d = nd[d["attach"]]
        return M.LANES[d["lane"]]
    rows = []
    for k, (label, role) in M.ORIGINAL.items():
        f, nid = used[k][0].split(":")
        p = by_file[f]
        node = next(d for d in p["nodes"] if d["id"] == nid)
        flag = " *(wording interpreted)*" if node.get("interpreted") else ""
        rows.append(f"| {k} | {label} | {role} | {p['name'].split(' — ')[0]} | {lane_of(p, nid)} | {node['name']}{flag} | `{f}.bpmn` |")
    t = ["# Traceability: source diagram → v2", "",
         "Generated by `tools/v2/build.py`. Every step of the original diagram",
         "(`diagrams/license-process-bpmn.jpg`) appears exactly once in v2; the build fails otherwise.",
         "Internal system names are masked in square brackets.", "",
         "| # | Original step (as drawn) | Original role / note | v2 stage | v2 lane | v2 name | File |",
         "|---|---|---|---|---|---|---|"] + rows
    added = []
    for p in M.PROCESSES:
        for d in p["nodes"]:
            if d.get("added_step"):
                stg = "Overview" if p["level"] == 0 else p['name'].split(' — ')[0]
                ln = "—" if p["level"] == 0 else lane_of(p, d['id'])
                added.append(f"| {stg} | {d['name']} | {ln} | {d.get('basis', '')} |")
    if added:
        t += ["", "## Elements added (not in the source diagram)", "",
              "Shown in red with a dashed border on the diagrams.", "",
              "| v2 stage | Element | Lane | Basis |", "|---|---|---|---|"] + added
    with open(os.path.join(ROOT, "docs", "v2-traceability.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(t) + "\n")
    # responsibilities: who performs which step, per stage
    resp = defaultdict(lambda: defaultdict(list))
    stages = []
    for p in M.PROCESSES:
        if p["level"] == 0:
            continue
        st = p["name"].split(" — ")[0]
        stages.append(st)
        for d in p["nodes"]:
            if d["type"] in ("user", "send", "manual", "service"):
                if p["lanes"]:
                    role = M.LANES[d["lane"]]
                    name = d["name"]
                else:
                    role, name = d["name"].split(" — ", 1)
                    role = {"Building Inspection Chief": "Building Inspection Chief",
                            "Mapping Chief": "Mapping Chief", "Rapporteur": "Rapporteur (zoning)",
                            "Zoning Director": M.LANES["ZDIR"], "Deputy Mayor": M.LANES["DEP"]}[role]
                resp[role][st].append(name)
    r = ["# Who does what, per stage", "",
         "Generated from the v2 model: each cell lists the steps a role performs in that stage.",
         "This is a performer matrix only; approval and consultation rights are not part of the source.", "",
         "| Role | " + " | ".join(stages) + " |", "|---|" + "---|" * len(stages)]
    for role in resp:
        r.append(f"| {role} | " + " | ".join("<br>".join(resp[role][s]) for s in stages) + " |")
    with open(os.path.join(ROOT, "docs", "v2-responsibilities.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(r) + "\n")
    # milestones and outcomes = stage end events
    m = ["# Application milestones and outcomes", "",
         "Generated from the end events of each stage. These are the points the software",
         "can expose as application statuses.", "",
         "| Stage | Outcome | Kind |", "|---|---|---|"]
    for p in M.PROCESSES:
        if p["level"] == 0:
            continue
        for d in p["nodes"]:
            if d["type"].startswith("end"):
                kind = {"end": "milestone" if p["level"] == 1 else "sub-process result",
                        "end_error": "**cancellation → Stage C (closure)**",
                        "end_escalation": "escalation (meaning to confirm)"}[d["type"]]
                if d["type"] == "end" and d.get("added_label"):
                    kind = "side branch end"
                if p["file"].startswith("07-"):
                    kind = "**terminal: premises closed**"
                m.append(f"| {p['name'].split(' — ')[0]} | {d['name']} | {kind} |")
    with open(os.path.join(ROOT, "docs", "v2-milestones.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(m) + "\n")


def main():
    out_bpmn = os.path.join(ROOT, "model", "v2")
    out_svg = os.path.join(ROOT, "diagrams", "v2")
    os.makedirs(out_bpmn, exist_ok=True)
    os.makedirs(out_svg, exist_ok=True)
    report = ["# Lint report (generated)", ""]
    used = defaultdict(list)
    total_err = 0
    stats = []
    for p in M.PROCESSES:
        L = Layout(p)
        routes = [route(L, f) for f in p["flows"]]
        for f, pts in zip(p["flows"], routes):
            for nid_, pt in ((f["src"], pts[0]), (f["tgt"], pts[-1])):
                n = L.nodes[nid_]
                for sd in "TBLR":
                    if math.dist(n.side(sd), pt) < 1:
                        n.__dict__.setdefault("used", set()).add(sd)
        for n in L.nodes.values():
            if getattr(n, "orig", None):
                used[n.orig].append(f'{p["file"]}:{n.id}')
        xml = build_xml(p, L, routes)
        with open(os.path.join(out_bpmn, p["file"] + ".bpmn"), "w", encoding="utf-8") as fh:
            fh.write(xml)
        with open(os.path.join(out_svg, p["file"] + ".svg"), "w", encoding="utf-8") as fh:
            fh.write(render_svg(p, L, routes))
        issues = lint(p, L, routes)
        total_err += sum(1 for s, _ in issues if s == "error")
        report.append(f"## {p['name']}  (`{p['file']}.bpmn`)")
        report += [f"- **{s}**: {m}" for s, m in issues] or ["- no issues"]
        report.append("")
        c = defaultdict(int)
        for n in L.nodes.values():
            c["task" if is_task(n.type) and n.type != "call" else "gateway" if is_gw(n.type) else "call" if n.type == "call" else "event"] += 1
        stats.append((p["file"], c["task"], c["gateway"], c["event"], c["call"], len(p["flows"])))
    write_docs(used)
    missing = [k for k in M.ORIGINAL if k not in used]
    dup = {k: v for k, v in used.items() if len(v) > 1}
    report.append("## Coverage of the source diagram")
    report.append(f"- source steps: {len(M.ORIGINAL)}; mapped: {len(used)}; missing: {missing or 'none'}; mapped twice: {dup or 'none'}")
    with open(os.path.join(HERE, "lint-report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(report) + "\n")
    print("\n".join(report))
    print("stats (file, tasks, gateways, events, calls, flows):")
    for s in stats:
        print("  ", s)
    if missing or dup or total_err:
        sys.exit(1)


if __name__ == "__main__":
    main()
