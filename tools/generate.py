#!/usr/bin/env python3
"""
Builds the Flip Fella watch face (Watch Face Format v1) and a matching preview.

Outputs:
  app/src/main/res/raw/watchface.xml        the face itself
  app/src/main/res/drawable-nodpi/*.png     Pebble, pointer and dial icons
  app/src/main/res/drawable-nodpi/preview.png
  tools/out/preview.svg                     what the face should look like

Every element is described once and written to both the XML and the SVG, so the
preview stays in step with what the watch draws. Run: python3 tools/generate.py
"""
import math
import os
import subprocess
from xml.sax.saxutils import escape, quoteattr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "app", "src", "main", "res")
OUT = os.path.join(ROOT, "tools", "out")
DRAW = os.path.join(RES, "drawable-nodpi")

C = 240
BG = "#070708"
DISC = "#0F0F11"
CARD = "#1B1B1B"
INK = "#F3F0E8"
MUTED = "#A0A0A6"
ACCENT = "#FF6A1A"

F_CARD = "rc_extrabold"
F_LABEL = "rc_bold"
F_COMPASS = "saira_medium"

# Sample values for the preview only.
SAMPLE = dict(hour=10, minute=52, second=38, dow_mon0=0, day=2, month="NOV",
              battery=84, steps=6412, step_pct=64, hr=72)


def pt(deg, r):
    a = math.radians(deg - 90)
    return C + math.cos(a) * r, C + math.sin(a) * r


def f(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def attrs(**kw):
    return " ".join(f'{k}={quoteattr(str(v))}' for k, v in kw.items() if v is not None)


class Face:
    def __init__(self):
        self.xml = []
        self.svg = []
        self.n = 0
        self.ox = 0
        self.oy = 0

    def name(self, base):
        self.n += 1
        return f"{base}_{self.n}"

    # ---------------------------------------------------------------- shapes
    def draw(self, shapes, variant_alpha=None, base_alpha=None, svg_hidden=False):
        """shapes: list of (kind, dict) drawn in one full-screen PartDraw."""
        inner = []
        for kind, s in shapes:
            stroke = s.get("stroke")
            fill = s.get("fill")
            style = ""
            if stroke:
                style += f'<Stroke {attrs(color=stroke[0], thickness=f(stroke[1]), cap=s.get("cap", "BUTT"), dashIntervals=s.get("dash"))}/>'
            if fill:
                style += f'<Fill {attrs(color=fill)}/>'
            tf = "".join(f'<Transform {attrs(target=t, value=v)}/>' for t, v in s.get("transforms", []))
            if kind == "ellipse":
                inner.append(f'<Ellipse {attrs(x=f(s["x"]), y=f(s["y"]), width=f(s["w"]), height=f(s["h"]))}>{style}{tf}</Ellipse>')
            elif kind == "rrect":
                inner.append(f'<RoundRectangle {attrs(x=f(s["x"]), y=f(s["y"]), width=f(s["w"]), height=f(s["h"]), cornerRadiusX=f(s["r"]), cornerRadiusY=f(s["r"]))}>{style}{tf}</RoundRectangle>')
            elif kind == "rect":
                inner.append(f'<Rectangle {attrs(x=f(s["x"]), y=f(s["y"]), width=f(s["w"]), height=f(s["h"]))}>{style}{tf}</Rectangle>')
            elif kind == "line":
                inner.append(f'<Line {attrs(startX=f(s["x1"]), startY=f(s["y1"]), endX=f(s["x2"]), endY=f(s["y2"]))}>{style}{tf}</Line>')
            elif kind == "arc":
                inner.append(f'<Arc {attrs(centerX=f(s["cx"]), centerY=f(s["cy"]), width=f(s["w"]), height=f(s["h"]), startAngle=f(s["a1"]), endAngle=f(s["a2"]))}>{style}{tf}</Arc>')

            if svg_hidden:
                continue
            sv = ""
            if stroke:
                sv += f' stroke="{stroke[0]}" stroke-width="{f(stroke[1])}"'
                if s.get("cap") == "ROUND":
                    sv += ' stroke-linecap="round"'
                if s.get("dash"):
                    sv += f' stroke-dasharray="{s["dash"]}"'
            sv += f' fill="{fill}"' if fill else ' fill="none"'
            if kind == "ellipse":
                self.svg.append(f'<ellipse cx="{f(s["x"] + s["w"] / 2)}" cy="{f(s["y"] + s["h"] / 2)}" rx="{f(s["w"] / 2)}" ry="{f(s["h"] / 2)}"{sv}/>')
            elif kind == "rrect":
                self.svg.append(f'<rect x="{f(s["x"])}" y="{f(s["y"])}" width="{f(s["w"])}" height="{f(s["h"])}" rx="{f(s["r"])}"{sv}/>')
            elif kind == "rect":
                self.svg.append(f'<rect x="{f(s["x"])}" y="{f(s["y"])}" width="{f(s["w"])}" height="{f(s["h"])}"{sv}/>')
            elif kind == "line":
                self.svg.append(f'<line x1="{f(s["x1"])}" y1="{f(s["y1"])}" x2="{f(s["x2"])}" y2="{f(s["y2"])}"{sv}/>')
            elif kind == "arc":
                a2 = s.get("svg_a2", s["a2"])
                if a2 - s["a1"] > 0.01:
                    r = s["w"] / 2
                    x1, y1 = pt(s["a1"], r)
                    x2, y2 = pt(a2, r)
                    large = 1 if a2 - s["a1"] > 180 else 0
                    self.svg.append(f'<path d="M{f(x1)} {f(y1)} A{f(r)} {f(r)} 0 {large} 1 {f(x2)} {f(y2)}"{sv}/>')

        extra = ""
        if variant_alpha is not None:
            extra = f'<Variant mode="AMBIENT" target="alpha" value="{variant_alpha}"/>'
        self.xml.append(
            f'<PartDraw {attrs(name=self.name("draw"), x=0, y=0, width=480, height=480, alpha=base_alpha)}>'
            f'{extra}{"".join(inner)}</PartDraw>'
        )

    # ---------------------------------------------------------------- text
    def text(self, cx, cy, content, size, family, color, w=None, h=None, angle=0,
             template=None, upper=False, svg_text=None, ambient_alpha=None, base_alpha=None,
             svg_hidden=False):
        w = w or max(40, size * 4)
        h = h or size * 1.4
        w, h = int(round(w)), int(round(h))
        x, y = int(round(cx - w / 2)), int(round(cy - h / 2))
        if template:
            fmt, params = template
            body = escape(fmt) + "".join(f'<Parameter {attrs(expression=p)}/>' for p in params)
            body = f"<Template>{body}</Template>"
        else:
            body = escape(content)
        if upper:
            body = f"<Upper>{body}</Upper>"
        variant = f'<Variant mode="AMBIENT" target="alpha" value="{ambient_alpha}"/>' if ambient_alpha is not None else ""
        self.xml.append(
            f'<PartText {attrs(name=self.name("text"), x=f(x - self.ox), y=f(y - self.oy), width=f(w), height=f(h), angle=f(angle) if angle else None, alpha=base_alpha)}>'
            f'{variant}<Text align="CENTER"><Font {attrs(family=family, size=f(size), color=color)}>{body}</Font></Text></PartText>'
        )
        if svg_hidden:
            return
        shown = svg_text if svg_text is not None else content
        fam = {"rc_extrabold": "Roboto Condensed", "rc_bold": "Roboto Condensed", "saira_medium": "Saira Condensed"}[family]
        weight = {"rc_extrabold": 800, "rc_bold": 700, "saira_medium": 500}[family]
        rot = f' transform="rotate({f(angle)} {f(cx)} {f(cy)})"' if angle else ""
        self.svg.append(
            f'<text x="{f(cx)}" y="{f(cy + 0.355 * size)}" text-anchor="middle" '
            f'font-family="{fam}" font-weight="{weight}" font-size="{f(size)}" fill="{color}"{rot}>{escape(shown)}</text>'
        )

    def image(self, x, y, w, h, resource, svg_png=None, ambient_alpha=None, base_alpha=None,
              tint=None, gyro=""):
        x, y, w, h = (int(round(v)) for v in (x, y, w, h))
        variant = f'<Variant mode="AMBIENT" target="alpha" value="{ambient_alpha}"/>' if ambient_alpha is not None else ""
        self.xml.append(
            f'<PartImage {attrs(name=self.name("image"), x=f(x - self.ox), y=f(y - self.oy), width=f(w), height=f(h), alpha=base_alpha, tintColor=tint)}>'
            f'{variant}{gyro}<Image resource="{resource}"/></PartImage>'
        )
        if svg_png:
            import base64
            with open(os.path.join(DRAW, svg_png + ".png"), "rb") as fh:
                data = base64.b64encode(fh.read()).decode()
            self.svg.append(f'<image x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" href="data:image/png;base64,{data}"/>')

    def raw(self, xml, svg=None):
        self.xml.append(xml)
        if svg:
            self.svg.append(svg)

    def capture(self):
        """Collect the XML of the following calls separately (for Conditions/Groups)."""
        start = len(self.xml)
        return start

    def take(self, start):
        chunk = "".join(self.xml[start:])
        del self.xml[start:]
        return chunk


# ==================================================================== assets

PEBBLE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 88 88">
<defs><clipPath id="w"><circle cx="44" cy="44" r="42"/></clipPath></defs>
<circle cx="44" cy="44" r="43" fill="#151518" stroke="#2A2A2E" stroke-width="2"/>
<g clip-path="url(#w)"><g transform="translate(-6 30) scale(0.5)">
<path transform="translate(7 9)" fill="#2329A8" d="M100 22 C146 20 176 54 174 100 C172 146 140 176 98 174 C54 172 24 142 26 98 C28 56 58 24 100 22Z"/>
<path fill="#4B57FF" d="M100 22 C146 20 176 54 174 100 C172 146 140 176 98 174 C54 172 24 142 26 98 C28 56 58 24 100 22Z"/>
<circle cx="78" cy="80" r="18" fill="#FFFFFF"/><circle cx="122" cy="80" r="18" fill="#FFFFFF"/>
<circle cx="81" cy="72" r="9" fill="#0B0B12"/><circle cx="125" cy="72" r="9" fill="#0B0B12"/>
<path d="M88 116 Q100 126 112 116" stroke="#0B0B12" stroke-width="6" stroke-linecap="round" fill="none"/>
</g></g></svg>"""

PEBBLE_SLEEP_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 88 88">
<defs><clipPath id="w"><circle cx="44" cy="44" r="42"/></clipPath></defs>
<circle cx="44" cy="44" r="43" fill="#000000" stroke="#24242A" stroke-width="2"/>
<g clip-path="url(#w)"><g transform="translate(-6 30) scale(0.5)">
<path fill="none" stroke="#3A3F8A" stroke-width="5" d="M100 22 C146 20 176 54 174 100 C172 146 140 176 98 174 C54 172 24 142 26 98 C28 56 58 24 100 22Z"/>
<path d="M62 84 Q78 92 94 84 M106 84 Q122 92 138 84 M94 118 H106" stroke="#5A5A62" stroke-width="6" stroke-linecap="round" fill="none"/>
</g></g></svg>"""

POINTER_SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" width="32" height="28" viewBox="0 0 16 14">
<path d="M8 14 L16 0 L0 0 Z" fill="{ACCENT}"/></svg>"""

HEART_SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24">
<path fill="{ACCENT}" d="M12 21 C4 14 1 9.5 3.5 6 C6 2.5 10.5 3.5 12 7 C13.5 3.5 18 2.5 20.5 6 C23 9.5 20 14 12 21Z"/></svg>"""

FEET_SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24">
<ellipse cx="8.5" cy="9" rx="3.4" ry="6" fill="{ACCENT}"/>
<ellipse cx="15.5" cy="13" rx="3.4" ry="6" fill="{ACCENT}"/></svg>"""


def render_png(svg, name):
    os.makedirs(DRAW, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    src = os.path.join(OUT, name + ".svg")
    with open(src, "w") as fh:
        fh.write(svg)
    dst = os.path.join(DRAW, name + ".png")
    subprocess.run(["rsvg-convert", "-o", dst, src], check=True)
    return dst



# ---------------------------------------------------------------- Pebble layers
BODY = "M100 22 C146 20 176 54 174 100 C172 146 140 176 98 174 C54 172 24 142 26 98 C28 56 58 24 100 22Z"
EYES = ((78, 80), (122, 80))


def pebble_svg(inner, window=True, dy=0):
    """Pebble's window at 2x. `inner` is drawn in body coordinates, moved by dy."""
    bg = ('<circle cx="44" cy="44" r="43" fill="#151518" stroke="#2A2A2E" stroke-width="2"/>'
          if window else "")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="176" height="176" viewBox="0 0 88 88">'
            f'<defs><clipPath id="w"><circle cx="44" cy="44" r="42"/></clipPath></defs>{bg}'
            f'<g clip-path="url(#w)"><g transform="translate(-6 {30 + dy * 0.5}) scale(0.5)">{inner}</g></g></svg>')


def body_parts(eyes="open", mouth="smile"):
    out = (f'<path transform="translate(7 9)" fill="#2329A8" d="{BODY}"/>'
           f'<path fill="#4B57FF" d="{BODY}"/>')
    if eyes == "open":
        out += "".join(f'<circle cx="{x}" cy="{y}" r="18" fill="#FFFFFF"/>' for x, y in EYES)
    elif eyes == "happy":
        out += ('<path d="M62 86 Q78 70 94 86 M106 86 Q122 70 138 86" stroke="#0B0B12" '
                'stroke-width="6" stroke-linecap="round" fill="none"/>')
    if mouth == "smile":
        out += '<path d="M88 116 Q100 126 112 116" stroke="#0B0B12" stroke-width="6" stroke-linecap="round" fill="none"/>'
    elif mouth == "open":
        out += ('<path d="M84 104 H116 Q114 132 100 132 Q86 132 84 104 Z" fill="#0B0B12"/>'
                '<path d="M92 125 Q100 120 108 125 Q105 131 100 131 Q95 131 92 125 Z" fill="#FF6B8A"/>')
    return out


PUPILS = "".join(f'<circle cx="{x + 1}" cy="{y - 4}" r="9" fill="#0B0B12"/>' for x, y in EYES)


def lids(p):
    """Eyelids closing from the top. p = 0 open, 1 shut."""
    out = '<defs>' + "".join(
        f'<clipPath id="e{i}"><circle cx="{x}" cy="{y}" r="18.6"/></clipPath>' for i, (x, y) in enumerate(EYES)) + '</defs>'
    for i, (x, y) in enumerate(EYES):
        h = 38 * p
        out += f'<rect x="{x - 20}" y="{y - 20}" width="40" height="{h}" fill="#4B57FF" clip-path="url(#e{i})"/>'
        if p >= 1:
            out += f'<path d="M{x - 16} {y} Q{x} {y + 8} {x + 16} {y}" stroke="#0B0B12" stroke-width="6" stroke-linecap="round" fill="none"/>'
    return out


SPARKS = ('<g stroke="#FFD24A" stroke-width="5" stroke-linecap="round">'
          '<path d="M30 40 L42 50"/><path d="M170 40 L158 50"/><path d="M100 2 L100 14"/></g>')

BLINK_LEVELS = [0.55, 1, 1, 0.55]
BLINK_FRAMES = [f"pebble_blink_{i}" for i in range(len(BLINK_LEVELS))]
HAPPY_DY = [0, -8, -16, -22, -24, -20, -12, -2, 4, 2, -6, -8, -4, 0]
HAPPY_FRAMES = [f"pebble_happy_{i}" for i in range(len(HAPPY_DY))]


def pebble_assets():
    render_png(pebble_svg(body_parts()), "pebble_base")
    render_png(pebble_svg(PUPILS, window=False), "pebble_pupils")
    for name, p in zip(BLINK_FRAMES, BLINK_LEVELS):
        render_png(pebble_svg(lids(p), window=False), name)
    for i, (name, dy) in enumerate(zip(HAPPY_FRAMES, HAPPY_DY)):
        sparks = SPARKS if 3 <= i <= 6 else ""
        render_png(pebble_svg(sparks + body_parts(eyes="happy", mouth="open"), dy=dy), name)


# ==================================================================== face

def build():
    pebble_assets()
    for svg, name in [(PEBBLE_SLEEP_SVG, "pebble_sleep"),
                      (POINTER_SVG, "pointer"), (HEART_SVG, "heart"), (FEET_SVG, "feet")]:
        render_png(svg, name)

    face = Face()
    s = SAMPLE

    # ---------------- interactive layer (hidden in always on)
    face.draw([("ellipse", dict(x=0, y=0, w=480, h=480, fill=BG))])

    # Compass bezel: dark band, tick ring, points and degrees. Fixed with north up.
    shapes = [("ellipse", dict(x=21, y=21, w=438, h=438, stroke=("#141417", 38))),
              ("ellipse", dict(x=40, y=40, w=400, h=400, stroke=("#2A2A2E", 1.5)))]
    for d in range(0, 360, 5):
        major, mid = d % 45 == 0, d % 15 == 0
        inner = 228 if major else (231 if mid else 233)
        x1, y1 = pt(d, 237)
        x2, y2 = pt(d, inner)
        shapes.append(("line", dict(x1=x1, y1=y1, x2=x2, y2=y2, cap="ROUND",
                                    stroke=("#8A8A90" if (major or mid) else "#3E3E44", 2 if major else 1.4))))
    face.draw(shapes, variant_alpha=0)

    points = {0: "N", 45: "NE", 90: "E", 135: "SE", 180: "S", 225: "SW", 270: "W", 315: "NW"}
    for d, label in points.items():
        cardinal = len(label) == 1
        x, y = pt(d, 214)
        face.text(x, y, label, 25 if cardinal else 15, F_COMPASS,
                  ACCENT if label == "N" else (INK if cardinal else MUTED),
                  w=44, h=34, angle=d, ambient_alpha=0)
    for d in range(30, 360, 30):
        if d % 90 == 0:
            continue
        x, y = pt(d, 216)
        face.text(x, y, str(d), 13, F_COMPASS, "#6E6E76", w=36, h=22, angle=d, ambient_alpha=0)

    # Minute track
    shapes = []
    for i in range(60):
        five = i % 5 == 0
        x1, y1 = pt(i * 6, 197)
        x2, y2 = pt(i * 6, 189 if five else 193)
        shapes.append(("line", dict(x1=x1, y1=y1, x2=x2, y2=y2, cap="ROUND",
                                    stroke=(INK if five else "#4A4A50", 2.4 if five else 1.2))))
    face.draw(shapes, variant_alpha=0)

    # Inner disc
    face.draw([("ellipse", dict(x=66, y=66, w=348, h=348, fill=DISC, stroke=("#1F1F23", 2)))], variant_alpha=0)

    # Arcs: two customisable slots. Left defaults to battery, right to built-in steps.
    def arc_value(a1, frac_expr):
        return f"{a1} + 52 * clamp({frac_expr}, 0, 1)"

    ranged_frac = ("([COMPLICATION.RANGED_VALUE_VALUE] - [COMPLICATION.RANGED_VALUE_MIN]) / "
                   "(([COMPLICATION.RANGED_VALUE_MAX] - [COMPLICATION.RANGED_VALUE_MIN]) > 0 ? "
                   "([COMPLICATION.RANGED_VALUE_MAX] - [COMPLICATION.RANGED_VALUE_MIN]) : 1)")
    goal_frac = ("[COMPLICATION.GOAL_PROGRESS_VALUE] / "
                 "([COMPLICATION.GOAL_PROGRESS_TARGET_VALUE] > 0 ? [COMPLICATION.GOAL_PROGRESS_TARGET_VALUE] : 1)")

    def arc_slot(slot_id, label, a1, dashed, label_x, label_angle, default_provider, default_type,
                 fallback_frac, fallback_label, sample_frac, sample_label):
        def arc_parts(frac_expr, text_template, show_svg):
            dash = "3 3" if dashed else None
            start = face.capture()
            face.draw([
                ("arc", dict(cx=C, cy=C, w=360, h=360, a1=a1, a2=a1 + 52, stroke=("#2A2A2E", 8), cap="ROUND")),
                ("arc", dict(cx=C, cy=C, w=360, h=360, a1=a1, a2=a1 + 52, stroke=(INK, 8),
                             cap=None if dashed else "ROUND", dash=dash,
                             transforms=[("endAngle", arc_value(a1, frac_expr))],
                             svg_a2=a1 + 52 * sample_frac)),
            ], svg_hidden=not show_svg)
            face.text(label_x, C, "", 15, F_LABEL, MUTED, w=60, h=22, angle=label_angle,
                      template=text_template, svg_text=sample_label, svg_hidden=not show_svg)
            return face.take(start)

        comps = [
            ("RANGED_VALUE", arc_parts(ranged_frac, ("%s", ["[COMPLICATION.TEXT]"]), False)),
            ("GOAL_PROGRESS", arc_parts(goal_frac, ("%s", ["[COMPLICATION.TEXT]"]), False)),
            ("EMPTY", arc_parts(fallback_frac, fallback_label, True)),
        ]
        body = "".join(f'<Complication type="{t}">{x}</Complication>' for t, x in comps)
        face.raw(
            f'<ComplicationSlot slotId="{slot_id}" name="{label.lower().replace(" ", "_")}" displayName="{label}" '
            f'x="0" y="0" width="480" height="480" isCustomizable="TRUE" '
            f'supportedTypes="RANGED_VALUE GOAL_PROGRESS EMPTY">'
            f'<DefaultProviderPolicy defaultSystemProvider="{default_provider}" defaultSystemProviderType="{default_type}"/>'
            f'<BoundingArc centerX="240" centerY="240" width="360" height="360" thickness="40" '
            f'startAngle="{a1}" endAngle="{a1 + 52}" isRoundEdge="TRUE"/>'
            f'{body}<Variant mode="AMBIENT" target="alpha" value="0"/></ComplicationSlot>'
        )

    arc_slot(1, "Left arc", 244, False, 76, -90, "WATCH_BATTERY", "RANGED_VALUE",
             "[BATTERY_PERCENT] / 100", ("%d%%", ["[BATTERY_PERCENT]"]),
             s["battery"] / 100, f'{s["battery"]}%')
    arc_slot(2, "Right arc", 64, True, 404, 90, "EMPTY", "EMPTY",
             "[STEP_PERCENT] / 100", ("%d%%", ["[STEP_PERCENT]"]),
             s["step_pct"] / 100, f'{s["step_pct"]}%')

    # Seconds dot running round the minute track
    sx, sy = pt(0, 193)
    start = face.capture()
    face.draw([("ellipse", dict(x=sx - 4.5, y=sy - 4.5, w=9, h=9, fill=ACCENT))], svg_hidden=True)
    inner = face.take(start)
    face.raw(
        f'<Group name="seconds" x="0" y="0" width="480" height="480" pivotX="0.5" pivotY="0.5">'
        f'<Transform target="angle" value="[SECOND] * 6"/>'
        f'<Variant mode="AMBIENT" target="alpha" value="0"/>{inner}</Group>'
    )
    px, py = pt(s["second"] * 6, 193)
    face.svg.append(f'<circle cx="{f(px)}" cy="{f(py)}" r="4.5" fill="{ACCENT}"/>')

    # Pointer at 12
    face.image(234, 3, 12, 11, "pointer", svg_png="pointer", ambient_alpha=0)

    # Weekday row: Monday first, today circled in orange, dots for days gone
    letters = ["M", "T", "W", "T", "F", "S", "S"]
    for i, letter in enumerate(letters):
        cx = 150 + 30 * i
        dow = (i + 1) % 7 + 1  # Calendar.DAY_OF_WEEK: Sunday 1 .. Saturday 7
        today_x = f"[DAY_OF_WEEK] == {dow}"
        past_x = f"(([DAY_OF_WEEK] + 5) % 7) >= {i}"

        start = face.capture()
        face.draw([("ellipse", dict(x=cx - 11, y=98, w=22, h=22, fill=ACCENT))], svg_hidden=True)
        face.text(cx, 109, letter, 16, F_LABEL, BG, w=22, h=22, svg_hidden=True)
        today_xml = face.take(start)
        start = face.capture()
        face.text(cx, 109, letter, 16, F_LABEL, "#C8C8CC", w=22, h=22, svg_hidden=True)
        other_xml = face.take(start)
        start = face.capture()
        face.draw([("ellipse", dict(x=cx - 3.5, y=124, w=7, h=7, fill="#5A5A62"))], svg_hidden=True)
        past_xml = face.take(start)
        start = face.capture()
        face.draw([("ellipse", dict(x=cx - 3.5, y=124, w=7, h=7, fill="#2A2A2E"))], svg_hidden=True)
        future_xml = face.take(start)

        g = lambda name, body: f'<Group name="{name}" x="0" y="0" width="480" height="480">{body}</Group>'
        face.raw(
            f'<Group name="day{i}" x="0" y="0" width="480" height="480">'
            f'<Variant mode="AMBIENT" target="alpha" value="0"/>'
            f'<Condition><Expressions>'
            f'<Expression name="today{i}"><![CDATA[{today_x}]]></Expression>'
            f'</Expressions>'
            f'<Compare expression="today{i}">{g(f"day{i}_on", today_xml)}</Compare>'
            f'<Default>{g(f"day{i}_off", other_xml)}</Default>'
            f'</Condition>'
            f'<Condition><Expressions>'
            f'<Expression name="past{i}"><![CDATA[{past_x}]]></Expression>'
            f'</Expressions>'
            f'<Compare expression="past{i}">{g(f"dot{i}_on", past_xml)}</Compare>'
            f'<Default>{g(f"dot{i}_off", future_xml)}</Default>'
            f'</Condition></Group>'
        )
        is_today = i == s["dow_mon0"]
        if is_today:
            face.svg.append(f'<circle cx="{cx}" cy="109" r="11" fill="{ACCENT}"/>')
        face.svg.append(
            f'<text x="{cx}" y="114.7" text-anchor="middle" font-family="Roboto Condensed" '
            f'font-weight="700" font-size="16" fill="{BG if is_today else "#C8C8CC"}">{letter}</text>')
        face.svg.append(f'<circle cx="{cx}" cy="127.5" r="3.5" fill="{"#5A5A62" if i <= s["dow_mon0"] else "#2A2A2E"}"/>')

    # Date cards
    face.draw([
        ("rrect", dict(x=179, y=146, w=48, h=34, r=6, fill=CARD)),
        ("rrect", dict(x=233, y=146, w=68, h=34, r=6, fill=CARD)),
    ], variant_alpha=0)
    face.text(203, 163, "", 22, F_LABEL, INK, w=48, h=34, template=("%s", ["[DAY_Z]"]),
              svg_text=f'{s["day"]:02d}', ambient_alpha=0)
    face.text(267, 163, "", 22, F_LABEL, INK, w=68, h=34, template=("%s", ["[MONTH_S]"]), upper=True,
              svg_text=s["month"], ambient_alpha=0)
    face.draw([
        ("rect", dict(x=179, y=162, w=48, h=2, fill="#000000")),
        ("rect", dict(x=233, y=162, w=68, h=2, fill="#000000")),
    ], variant_alpha=0)

    # Time: four flip cards, 24 hour
    lefts = [92, 162, 254, 324]
    exprs = ["floor([HOUR_0_23] / 10)", "[HOUR_0_23] % 10", "floor([MINUTE] / 10)", "[MINUTE] % 10"]
    sample_digits = f'{s["hour"]:02d}{s["minute"]:02d}'
    face.draw([("rrect", dict(x=x, y=192, w=64, h=96, r=9, fill=CARD)) for x in lefts], variant_alpha=0)
    for x, e, d in zip(lefts, exprs, sample_digits):
        face.text(x + 32, 240, "", 88, F_CARD, INK, w=64, h=96, template=("%d", [e]), svg_text=d,
                  ambient_alpha=0)
    face.draw([("rect", dict(x=x, y=239, w=64, h=2, fill="#000000")) for x in lefts] + [
        ("ellipse", dict(x=235.5, y=221, w=9, h=9, fill=ACCENT)),
        ("ellipse", dict(x=235.5, y=250, w=9, h=9, fill=ACCENT)),
    ], variant_alpha=0)

    # Dials: two customisable slots. Left falls back to heart rate, right defaults to steps.
    def dial_slot(slot_id, label, sx, default_provider, default_type, fallback_xml_fn, show_fallback_svg):
        sy, sw, sh = 296, 88, 76
        face.ox, face.oy = sx, sy
        cx = sx + sw / 2

        def icon_and_text(size):
            start = face.capture()
            face.image(cx - 11, sy + 8, 22, 22, "[COMPLICATION.MONOCHROMATIC_IMAGE]", tint=ACCENT)
            face.text(cx, sy + 50, "", size, F_LABEL, INK, w=sw, h=40,
                      template=("%s", ["[COMPLICATION.TEXT]"]), svg_hidden=True)
            return face.take(start)

        comps = []
        for t in ("SHORT_TEXT", "RANGED_VALUE", "GOAL_PROGRESS"):
            comps.append((t, icon_and_text(28)))
        start = face.capture()
        face.text(cx, sy + 38, "", 17, F_LABEL, INK, w=sw, h=60,
                  template=("%s", ["[COMPLICATION.TEXT]"]), svg_hidden=True)
        comps.append(("LONG_TEXT", face.take(start)))
        start = face.capture()
        face.image(cx - 18, sy + 20, 36, 36, "[COMPLICATION.MONOCHROMATIC_IMAGE]", tint=ACCENT)
        comps.append(("MONOCHROMATIC_IMAGE", face.take(start)))
        start = face.capture()
        face.image(cx - 22, sy + 16, 44, 44, "[COMPLICATION.SMALL_IMAGE]")
        comps.append(("SMALL_IMAGE", face.take(start)))
        start = face.capture()
        fallback_xml_fn(cx, sy, show_fallback_svg)
        comps.append(("EMPTY", face.take(start)))
        face.ox, face.oy = 0, 0

        body = "".join(f'<Complication type="{t}">{x}</Complication>' for t, x in comps)
        face.raw(
            f'<ComplicationSlot slotId="{slot_id}" name="{label.lower().replace(" ", "_")}" displayName="{label}" '
            f'x="{sx}" y="{sy}" width="{sw}" height="{sh}" isCustomizable="TRUE" '
            f'supportedTypes="SHORT_TEXT RANGED_VALUE GOAL_PROGRESS LONG_TEXT MONOCHROMATIC_IMAGE SMALL_IMAGE EMPTY">'
            f'<DefaultProviderPolicy defaultSystemProvider="{default_provider}" defaultSystemProviderType="{default_type}"/>'
            f'<BoundingRoundBox x="0" y="0" width="{sw}" height="{sh}" cornerRadius="20" outlinePadding="2"/>'
            f'{body}<Variant mode="AMBIENT" target="alpha" value="0"/></ComplicationSlot>'
        )

    def heart_fallback(cx, sy, show_svg):
        face.image(cx - 10, sy + 10, 20, 20, "heart", svg_png="heart" if show_svg else None)
        start = face.capture()
        face.text(cx, sy + 50, "", 30, F_LABEL, INK, w=88, h=40, template=("%d", ["[HEART_RATE]"]),
                  svg_text=str(s["hr"]), svg_hidden=not show_svg)
        on = face.take(start)
        start = face.capture()
        face.text(cx, sy + 50, "--", 30, F_LABEL, "#6E6E76", w=88, h=40, svg_hidden=True)
        off = face.take(start)
        face.raw(
            '<Condition><Expressions><Expression name="hasHr"><![CDATA[[HEART_RATE] > 0]]></Expression></Expressions>'
            f'<Compare expression="hasHr"><Group name="hr_on" x="0" y="0" width="88" height="76">{on}</Group></Compare>'
            f'<Default><Group name="hr_off" x="0" y="0" width="88" height="76">{off}</Group></Default></Condition>'
        )

    def steps_fallback(cx, sy, show_svg):
        face.image(cx - 10, sy + 10, 20, 20, "feet", svg_png="feet" if show_svg else None)
        start = face.capture()
        face.text(cx, sy + 50, "", 30, F_LABEL, INK, w=96, h=40, template=(
            "%d,%d%d%d", ["floor([STEP_COUNT] / 1000)", "floor(([STEP_COUNT] % 1000) / 100)",
                          "floor(([STEP_COUNT] % 100) / 10)", "[STEP_COUNT] % 10"]),
            svg_text=f'{s["steps"] // 1000},{s["steps"] % 1000:03d}', svg_hidden=not show_svg)
        big = face.take(start)
        start = face.capture()
        face.text(cx, sy + 50, "", 30, F_LABEL, INK, w=96, h=40, template=("%d", ["[STEP_COUNT]"]), svg_hidden=True)
        small = face.take(start)
        face.raw(
            '<Condition><Expressions><Expression name="thousands"><![CDATA[[STEP_COUNT] >= 1000]]></Expression></Expressions>'
            f'<Compare expression="thousands"><Group name="steps_big" x="0" y="0" width="88" height="76">{big}</Group></Compare>'
            f'<Default><Group name="steps_small" x="0" y="0" width="88" height="76">{small}</Group></Default></Condition>'
        )

    dial_slot(3, "Left dial", 100, "EMPTY", "EMPTY", heart_fallback, True)
    # Right dial: default is the system step counter, falling back to built-in steps if left empty.
    dial_slot(4, "Right dial", 292, "STEP_COUNT", "SHORT_TEXT", steps_fallback, True)

    # Pebble: base body, eyes that follow your wrist tilt, a blink on wake and each minute,
    # and a happy bounce when you tap him or the hour changes.
    face.image(190, 302, 100, 100, "pebble_base", svg_png="pebble_base", ambient_alpha=0)
    gyro = ('<Gyro x="2.5 * clamp([ACCELEROMETER_ANGLE_X], -45, 45) / 45" '
            'y="2.5 * clamp([ACCELEROMETER_ANGLE_Y], -45, 45) / 45"/>')
    face.image(190, 302, 100, 100, "pebble_pupils", svg_png="pebble_pupils", ambient_alpha=0, gyro=gyro)

    def sequence(name, frames, play, fps):
        imgs = "".join(f'<Image resource="{fr}"/>' for fr in frames)
        face.raw(
            f'<PartAnimatedImage name="{name}" x="190" y="302" width="100" height="100">'
            f'<Variant mode="AMBIENT" target="alpha" value="0"/>'
            f'<AnimationController play="{play}" beforePlaying="HIDE" afterPlaying="HIDE"/>'
            f'<SequenceImages frameRate="{fps}" loopCount="1">{imgs}</SequenceImages>'
            f'</PartAnimatedImage>'
        )

    sequence("blink", BLINK_FRAMES, "ON_VISIBLE ON_NEXT_MINUTE", 12)
    sequence("bounce", HAPPY_FRAMES, "TAP ON_NEXT_HOUR", 15)

    # Shortcut slot under the N: accepts every type so the most apps show up in the picker.
    face.ox, face.oy = 205, 52
    comps = []
    start = face.capture()
    face.image(225, 57, 30, 30, "[COMPLICATION.SMALL_IMAGE]")
    comps.append(("SMALL_IMAGE", face.take(start)))
    start = face.capture()
    face.image(227, 59, 26, 26, "[COMPLICATION.MONOCHROMATIC_IMAGE]", tint=ACCENT)
    comps.append(("MONOCHROMATIC_IMAGE", face.take(start)))
    for t in ("SHORT_TEXT", "RANGED_VALUE", "GOAL_PROGRESS", "LONG_TEXT"):
        start = face.capture()
        face.text(240, 72, "", 17, F_LABEL, ACCENT, w=70, h=40,
                  template=("%s", ["[COMPLICATION.TEXT]"]), svg_hidden=True)
        comps.append((t, face.take(start)))
    face.ox, face.oy = 0, 0
    body = "".join(f'<Complication type="{t}">{x}</Complication>' for t, x in comps) + '<Complication type="EMPTY"/>'
    face.raw(
        '<ComplicationSlot slotId="0" name="top_shortcut" displayName="Top shortcut" '
        'x="205" y="52" width="70" height="40" isCustomizable="TRUE" '
        'supportedTypes="SMALL_IMAGE MONOCHROMATIC_IMAGE SHORT_TEXT RANGED_VALUE GOAL_PROGRESS LONG_TEXT EMPTY">'
        '<DefaultProviderPolicy defaultSystemProvider="EMPTY" defaultSystemProviderType="EMPTY"/>'
        '<BoundingRoundBox x="0" y="0" width="70" height="40" cornerRadius="20" outlinePadding="2"/>'
        f'{body}<Variant mode="AMBIENT" target="alpha" value="0"/></ComplicationSlot>'
    )

    # ---------------- always on layer (shown only in ambient)
    amb = []
    for i in range(0, 60, 5):
        x1, y1 = pt(i * 6, 197)
        x2, y2 = pt(i * 6, 189)
        amb.append(("line", dict(x1=x1, y1=y1, x2=x2, y2=y2, cap="ROUND", stroke=("#3A3A3E", 2))))
    for x in lefts:
        amb.append(("rrect", dict(x=x + 1, y=193, w=62, h=94, r=9, stroke=("#2A2A2E", 2))))
        amb.append(("line", dict(x1=x + 1, y1=240, x2=x + 63, y2=240, stroke=("#2A2A2E", 2))))
    amb.append(("ellipse", dict(x=235.5, y=221, w=9, h=9, fill="#5A3A12")))
    amb.append(("ellipse", dict(x=235.5, y=250, w=9, h=9, fill="#5A3A12")))
    face.draw(amb, base_alpha=0, variant_alpha=255, svg_hidden=True)
    face.text(C, 160, "", 22, F_LABEL, "#7A7A80", w=240, h=32,
              template=("%s %s %s", ["[DAY_OF_WEEK_S]", "[DAY_Z]", "[MONTH_S]"]), upper=True,
              base_alpha=0, ambient_alpha=255, svg_hidden=True)
    for x, e in zip(lefts, exprs):
        face.text(x + 32, 240, "", 88, F_CARD, "#9A9A9E", w=64, h=96, template=("%d", [e]),
                  base_alpha=0, ambient_alpha=255, svg_hidden=True)
    face.image(205, 317, 70, 70, "pebble_sleep", base_alpha=0, ambient_alpha=255)

    xml = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<WatchFace width="480" height="480" clipShape="CIRCLE">\n'
        '<Metadata key="CLOCK_TYPE" value="DIGITAL"/>\n'
        '<Metadata key="PREVIEW_TIME" value="10:52:38"/>\n'
        f'<Scene backgroundColor="#FF000000">\n' + "\n".join(face.xml) + '\n</Scene>\n</WatchFace>\n'
    )
    raw_dir = os.path.join(RES, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    # Clear out images no longer used.
    used = set(__import__("re").findall(r'resource="([a-z_0-9]+)"', xml)) | {"preview"}
    for fn in os.listdir(DRAW):
        if fn.endswith(".png") and fn[:-4] not in used:
            os.remove(os.path.join(DRAW, fn))
    with open(os.path.join(raw_dir, "watchface.xml"), "w") as fh:
        fh.write(xml)

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="480" viewBox="0 0 480 480">'
        '<defs><clipPath id="face"><circle cx="240" cy="240" r="240"/></clipPath></defs>'
        '<rect width="480" height="480" fill="#000"/><g clip-path="url(#face)">'
        + "".join(face.svg) + "</g></svg>"
    )
    with open(os.path.join(OUT, "preview.svg"), "w") as fh:
        fh.write(svg)
    subprocess.run(["rsvg-convert", "-w", "450", "-h", "450", "-o",
                    os.path.join(DRAW, "preview.png"), os.path.join(OUT, "preview.svg")], check=True)
    print("watchface.xml:", len(xml), "bytes")


if __name__ == "__main__":
    build()
