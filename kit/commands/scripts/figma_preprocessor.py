#!/usr/bin/env python3
"""
Figma → Flutter Preprocessor v2.1
Transforms raw Figma layout JSON into a normalized Flutter-ready widget tree.

Passes:
  1  Token Resolution       — hex/rgba → Dart AppColors constants
  2  Frame Flattening       — remove pass-through single-child wrapper frames
  3  Decoration & Layout    — fill/gradient/image/border/shadow/clip/opacity
                               + Auto Layout → Row/Column
                               + No-layout FRAME → Stack + Positioned (screen-relative coords)
                               + SPACE_BETWEEN → Spacer hint
                               + Mixed cornerRadius → BorderRadius.only
  3.5 Text Normalization    — TEXT nodes → Text() + TextStyle
  4  Instance & Vector      — INSTANCE → known component / variant params
                               + VECTOR/BOOLEAN_OPERATION → SvgPicture.asset
  5  Sizing & Constraints   — bounds px → flutterWidth/Height
                               + FILL → Expanded / double.infinity
                               + SCALE → FractionallySizedBox
                               + CENTER/alignment → Align hint
  6  Screen Layout Map      — _screen_layout block: z-order, screen-relative positions, roles
  7  Per-widget Export      — widgets/<id>_<name>.json per root child
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from copy import deepcopy
from typing import Optional


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def get_children(node: dict) -> list:
    """Unified: screen level uses 'sections', all others use 'children'."""
    return node.get("children") or node.get("sections") or []


def set_children(node: dict, kids: list):
    if "sections" in node:
        node["sections"] = kids
    else:
        node["children"] = kids


def _rgba_to_hex(r: float, g: float, b: float, a: float = 1.0) -> str:
    ri, gi, bi, ai = int(r * 255), int(g * 255), int(b * 255), int(a * 255)
    if ai == 255:
        return f"#{ri:02X}{gi:02X}{bi:02X}"
    return f"Color(0x{ai:02X}{ri:02X}{gi:02X}{bi:02X})"


def _walk(node: dict, fn):
    """Post-order walk: apply fn to every node bottom-up."""
    kids = get_children(node)
    if kids:
        set_children(node, [_walk(c, fn) for c in kids])
    return fn(node)


# ─────────────────────────────────────────────────────────────
# PASS 1 — TOKEN RESOLUTION
# ─────────────────────────────────────────────────────────────

# Loaded at runtime from .ui-workspace/token_map.json via _load_token_map().
# Format: { "figma.token.name": "DartClass.constantName", ... }
# Run /init-ui-workspace to generate this file for your project.
TOKEN_TO_DART: dict = {}

# Reverse map: hex → dartConst for raw-hex nodes
_HEX_TO_DART: dict = {}


def _load_token_map(ws_root: Path) -> None:
    """Load Figma token → Dart const map from .ui-workspace/token_map.json."""
    global TOKEN_TO_DART
    token_map_path = ws_root / "token_map.json"
    if token_map_path.exists():
        TOKEN_TO_DART = json.loads(token_map_path.read_text())
        print(f"Token map: {len(TOKEN_TO_DART)} entries loaded from {token_map_path.name}")
    else:
        TOKEN_TO_DART = {}
        print(f"⚠ Token map not found at {token_map_path}")
        print(f"  Run /init-ui-workspace to generate token_map.json (token→dartConst disabled)")



def _build_hex_reverse_map(tokens_data: dict):
    """Build hex→dartConst map from design tokens for raw-hex nodes."""
    paint = tokens_data.get("_styles", {}).get("paint", {})

    def _walk_tokens(d: dict, path: str):
        for k, v in d.items():
            p = f"{path}.{k}" if path else k
            if isinstance(v, dict) and "value" in v:
                dart = TOKEN_TO_DART.get(p.lower().replace(" ", "_").replace("/", "."))
                if dart:
                    _HEX_TO_DART[v["value"].upper()] = dart
            elif isinstance(v, dict):
                _walk_tokens(v, p)

    _walk_tokens(paint, "")


def _resolve_color(fill_obj: dict) -> dict:
    """Resolve a single fill dict: tokenRef → dartConst, raw hex → dartConst or keep hex."""
    ref = fill_obj.get("tokenRef")
    if ref and ref in TOKEN_TO_DART:
        fill_obj["dartConst"] = TOKEN_TO_DART[ref]
        return fill_obj
    val = (fill_obj.get("value") or "").upper()
    if val and val in _HEX_TO_DART:
        fill_obj["dartConst"] = _HEX_TO_DART[val]
    # Raw Figma SOLID fill: {"type":"SOLID","color":{"r":..,"g":..,"b":..,"a":..}}
    if fill_obj.get("type") == "SOLID" and "color" in fill_obj:
        c = fill_obj["color"]
        hex_val = _rgba_to_hex(c["r"], c["g"], c["b"], c.get("a", 1.0))
        fill_obj["resolvedHex"] = hex_val
        if hex_val.upper() in _HEX_TO_DART:
            fill_obj["dartConst"] = _HEX_TO_DART[hex_val.upper()]
    return fill_obj


def _normalize_fill(f) -> dict:
    """Accept hex string '#RRGGBB' or fill dict; always return a dict."""
    if isinstance(f, str):
        return {"type": "SOLID", "value": f}
    return _resolve_color(f)


def resolve_tokens(node: dict) -> dict:
    for key in ("fill", "background"):
        if isinstance(node.get(key), dict):
            node[key] = _resolve_color(node[key])
    # Raw Figma fills array (supports both hex strings and fill-dicts)
    if isinstance(node.get("fills"), list):
        node["fills"] = [_normalize_fill(f) for f in node["fills"]]
    # Raw Figma strokes array
    if isinstance(node.get("strokes"), list):
        node["strokes"] = [_normalize_fill(s) for s in node["strokes"]]
    return _walk(node, lambda n: n) if False else node  # walk handled in pipeline


# ─────────────────────────────────────────────────────────────
# PASS 2 — FRAME FLATTENING
# ─────────────────────────────────────────────────────────────

def _is_passthrough(node: dict) -> bool:
    if node.get("type") != "FRAME":
        return False
    if node.get("fill") or node.get("background") or node.get("fills"):
        return False
    if node.get("cornerRadius") not in (None, 0):
        return False
    if node.get("effects") or node.get("opacity") not in (None, 1.0):
        return False
    if node.get("strokes"):
        return False
    if node.get("clipsContent"):
        return False
    padding = node.get("layout", {}).get("padding", {})
    if any(padding.get(k, 0) != 0 for k in ("top", "right", "bottom", "left")):
        return False
    return len(get_children(node)) == 1


def flatten_frames(node: dict) -> dict:
    kids = get_children(node)
    if not kids:
        return node
    flat = [flatten_frames(c) for c in kids]
    result = []
    for child in flat:
        if _is_passthrough(child):
            grandchild = get_children(child)[0]
            grandchild.setdefault("_flattenedFrom", child.get("name"))
            result.append(grandchild)
        else:
            result.append(child)
    set_children(node, result)
    return node


# ─────────────────────────────────────────────────────────────
# PASS 3 — DECORATION, LAYOUT, STACK, OPACITY, CLIP
# ─────────────────────────────────────────────────────────────

ALIGN_MAP = {
    "MIN":           "MainAxisAlignment.start",
    "CENTER":        "MainAxisAlignment.center",
    "MAX":           "MainAxisAlignment.end",
    "SPACE_BETWEEN": "MainAxisAlignment.spaceBetween",
    "SPACE_AROUND":  "MainAxisAlignment.spaceAround",
    "SPACE_EVENLY":  "MainAxisAlignment.spaceEvenly",
}

CROSS_ALIGN_MAP = {
    "MIN":      "CrossAxisAlignment.start",
    "CENTER":   "CrossAxisAlignment.center",
    "MAX":      "CrossAxisAlignment.end",
    "STRETCH":  "CrossAxisAlignment.stretch",
    "BASELINE": "CrossAxisAlignment.baseline",
}


def _build_border_radius(node: dict) -> Optional[str]:
    cr = node.get("cornerRadius")
    if not cr:
        return None
    if cr == "mixed":
        tl = node.get("topLeftRadius", 0)
        tr = node.get("topRightRadius", 0)
        bl = node.get("bottomLeftRadius", 0)
        br = node.get("bottomRightRadius", 0)
        return (
            f"BorderRadius.only("
            f"topLeft: Radius.circular({tl}), "
            f"topRight: Radius.circular({tr}), "
            f"bottomLeft: Radius.circular({bl}), "
            f"bottomRight: Radius.circular({br}))"
        )
    return f"BorderRadius.circular({cr})"


def _gradient_transform_to_alignment(transform: list) -> tuple[str, str]:
    """
    Approximate a Figma 2x3 gradient transform to Flutter begin/end Alignment.
    Transform is [[a,b,tx],[c,d,ty]] — we use the vector (b,d) normalized.
    """
    if not transform or len(transform) < 2:
        return "Alignment.topCenter", "Alignment.bottomCenter"
    a, b = transform[0][0], transform[0][1]
    c, d = transform[1][0], transform[1][1]
    # Direction vector of gradient (perpendicular to gradient lines)
    dx, dy = b, d
    mag = math.sqrt(dx * dx + dy * dy) or 1
    dx, dy = dx / mag, dy / mag
    angle = math.degrees(math.atan2(dy, dx))
    # Map angle to Flutter Alignment pairs
    if -45 <= angle <= 45:
        return "Alignment.centerLeft", "Alignment.centerRight"
    if 45 < angle <= 135:
        return "Alignment.topCenter", "Alignment.bottomCenter"
    if angle > 135 or angle <= -135:
        return "Alignment.centerRight", "Alignment.centerLeft"
    return "Alignment.bottomCenter", "Alignment.topCenter"


def _build_gradient(fill: dict, node_opacity: float = 1.0) -> Optional[dict]:
    """Convert Figma GRADIENT_LINEAR/GRADIENT_RADIAL to Flutter LinearGradient dict.

    node_opacity: the node-level opacity (0.0–1.0). Multiplied into each stop's
    alpha so the gradient color list already contains the correct alpha — no
    Opacity wrapper is needed around the Container.
    """
    ftype = fill.get("type", "")
    if ftype not in ("GRADIENT_LINEAR", "GRADIENT_RADIAL"):
        return None
    stops = fill.get("gradientStops", [])
    transform = fill.get("gradientTransform")
    # per-fill opacity (separate from node opacity)
    fill_opacity = fill.get("opacity", 1.0)
    effective_opacity = node_opacity * fill_opacity

    colors = []
    stop_positions = []
    for s in stops:
        c = s.get("color", {})
        # Bake node + fill opacity into alpha so BoxDecoration.gradient
        # carries the final appearance without an Opacity ancestor widget.
        stop_alpha = c.get("a", 1.0) * effective_opacity
        colors.append(_rgba_to_hex(c.get("r", 0), c.get("g", 0), c.get("b", 0), stop_alpha))
        stop_positions.append(round(s.get("position", 0), 4))

    if ftype == "GRADIENT_RADIAL":
        return {
            "type": "RadialGradient",
            "colors": colors,
            "stops": stop_positions,
        }

    begin, end = _gradient_transform_to_alignment(transform)
    return {
        "type": "LinearGradient",
        "begin": begin,
        "end": end,
        "colors": colors,
        "stops": stop_positions,
    }


def _build_decoration(node: dict) -> Optional[dict]:
    """
    Build a flutterDecoration dict from fills, strokes, cornerRadius, effects.
    Returns None if no decoration needed.
    """
    deco = {}
    # Node-level opacity: needed to bake into gradient stop alphas.
    node_opacity = node.get("opacity", 1.0)

    # ── Fill (solid or gradient or image) ──
    fill_source = node.get("fill") or node.get("background")
    fills_list  = node.get("fills", [])

    # tokenRef-based fill (already resolved in Pass 1)
    if fill_source and isinstance(fill_source, dict):
        ref_type = fill_source.get("tokenRef", "")
        if "gradient" in ref_type:
            deco["gradient"] = {"tokenRef": ref_type, "dartConst": fill_source.get("dartConst")}
        else:
            deco["color"] = fill_source.get("dartConst") or fill_source.get("value")

    # Raw Figma fills array (from get_nodes_info / detail=full)
    for f in fills_list:
        if not f.get("visible", True):
            continue
        ftype = f.get("type", "")
        if ftype == "SOLID":
            deco["color"] = f.get("dartConst") or f.get("resolvedHex") or f.get("value")
        elif ftype in ("GRADIENT_LINEAR", "GRADIENT_RADIAL"):
            g = _build_gradient(f, node_opacity)
            if g:
                deco["gradient"] = g
                # Flag that opacity is already in the color values — coding-ui
                # must NOT add an Opacity() wrapper for this node.
                if node_opacity < 1.0 or f.get("opacity", 1.0) < 1.0:
                    deco["_gradientOpacityBaked"] = True
        elif ftype == "IMAGE":
            scale_mode = f.get("scaleMode", "FILL").lower()
            box_fit = {
                "fill": "BoxFit.fill",
                "fit":  "BoxFit.contain",
                "crop": "BoxFit.cover",
                "tile": "BoxFit.none",
            }.get(scale_mode, "BoxFit.cover")
            deco["image"] = {
                "widget":  "DecorationImage",
                "imageRef": f.get("imageRef", ""),
                "fit":     box_fit,
                "note":    "Replace imageRef with AssetImage or NetworkImage",
            }

    # IMAGE fill + GRADIENT fill combo: Flutter BoxDecoration renders gradient UNDER image.
    # Figma typically places gradient ON TOP of image (overlay). Coding-ui must use Stack.
    if deco.get("image") and deco.get("gradient"):
        deco["_requiresGradientOverlayStack"] = True

    # ── Border radius ──
    br = _build_border_radius(node)
    if br:
        deco["borderRadius"] = br

    # ── Stroke / border ──
    strokes = node.get("strokes", [])
    stroke_weight = node.get("strokeWeight", 1)
    stroke_align  = node.get("strokeAlign", "INSIDE")
    for s in strokes:
        if not s.get("visible", True):
            continue
        stype = s.get("type", "")
        if stype == "SOLID":
            color = s.get("dartConst") or s.get("resolvedHex") or "Colors.transparent"
            deco["border"] = {
                "color":  color,
                "width":  stroke_weight,
                "align":  stroke_align,
                "dart":   f"Border.all(color: {color}, width: {stroke_weight})",
            }
            break
        elif stype in ("GRADIENT_LINEAR", "GRADIENT_RADIAL"):
            g = _build_gradient(s, 1.0)
            if g:
                w = stroke_weight
                deco["gradientBorder"] = {
                    "gradient": g,
                    "width":    w,
                    "dart": (
                        f"// GRADIENT BORDER — Flutter has no native gradient stroke.\n"
                        f"// Nested containers (outer=gradient fill, inner=bg color, padding={w}px):\n"
                        f"Container(\n"
                        f"  decoration: BoxDecoration(gradient: LinearGradient(...), borderRadius: ...),\n"
                        f"  padding: EdgeInsets.all({w}),\n"
                        f"  child: Container(decoration: BoxDecoration(color: bgColor, borderRadius: ...)),\n"
                        f")\n"
                        f"// For glow: add BoxShadow with same gradient start color, large blurRadius."
                    ),
                }
            break

    # ── Box shadows from effects ──
    shadows = []
    for eff in node.get("effects", []):
        if not eff.get("visible", True):
            continue
        etype = eff.get("type", "")
        if etype not in ("DROP_SHADOW", "INNER_SHADOW"):
            continue
        c   = eff.get("color", {})
        color_str = _rgba_to_hex(c.get("r",0), c.get("g",0), c.get("b",0), c.get("a",0.5))
        ox  = eff.get("offset", {}).get("x", 0)
        oy  = eff.get("offset", {}).get("y", 4)
        blur = eff.get("radius", 8)
        spread = eff.get("spread", 0)
        if etype == "INNER_SHADOW":
            dart_hint = (
                f"// INNER_SHADOW — BoxShadow has no inset in Flutter.\n"
                f"// Option A: package 'inner_shadow_widget' on pub.dev\n"
                f"// Option B: CustomPainter\n"
                f"// Soft approximation: BoxShadow(color: {color_str}, "
                f"blurRadius: {blur}, spreadRadius: {-blur/2}, "
                f"offset: Offset({ox}, {oy}))"
            )
        else:
            dart_hint = (
                f"BoxShadow(color: {color_str}, blurRadius: {blur}, "
                f"spreadRadius: {spread}, offset: Offset({ox}, {oy}))"
            )
        shadows.append({
            "type":       etype,
            "isInner":    etype == "INNER_SHADOW",
            "color":      color_str,
            "offsetX":    ox,
            "offsetY":    oy,
            "blurRadius": blur,
            "spread":     spread,
            "dart":       dart_hint,
        })
    if shadows:
        deco["boxShadow"] = shadows

    return deco if deco else None


def _is_stack(node: dict) -> bool:
    """
    Detect absolute-positioned (Stack) layout:
    FRAME with no Auto Layout direction and multiple children
    that have distinct overlapping positions.
    """
    if node.get("type") not in ("FRAME",):
        return False
    layout = node.get("layout", {})
    if layout.get("direction"):
        return False
    kids = get_children(node)
    if len(kids) < 2:
        return False
    return True


def _positioned_hint(child: dict, parent_bounds: dict) -> dict:
    """Generate Positioned(...) hint for a Stack child, using parent-relative coords."""
    cb = child.get("bounds", {})
    pb = parent_bounds
    # Subtract parent origin: Figma bounds are canvas-absolute; parent origin may be non-zero.
    left = round(cb.get("x", 0) - pb.get("x", 0), 2)
    top  = round(cb.get("y", 0) - pb.get("y", 0), 2)
    return {
        "widget": "Positioned",
        "left":   left,
        "top":    top,
        "width":  cb.get("width"),
        "height": cb.get("height"),
        "dart":   f"Positioned(left: {left}, top: {top}, child: ...)",
    }


def _to_edge_insets(p: dict) -> str:
    t, r, b, l = p.get("top",0), p.get("right",0), p.get("bottom",0), p.get("left",0)
    if t == b == l == r:
        return f"EdgeInsets.all({t})"
    if t == b and l == r:
        return f"EdgeInsets.symmetric(vertical: {t}, horizontal: {l})"
    return f"EdgeInsets.fromLTRB({l}, {t}, {r}, {b})"


def normalize_layout(node: dict) -> dict:
    ntype   = node.get("type", "")
    layout  = node.get("layout", {})
    direction   = layout.get("direction")
    padding     = layout.get("padding", {})
    gap         = layout.get("gap", 0)
    main_align  = layout.get("mainAxisAlignment")
    cross_align = layout.get("crossAxisAlignment")

    fw = {}  # flutterWidget dict being built

    # ── 1. Determine base widget ──
    if ntype == "TEXT":
        # handled in Pass 3.5 — skip layout pass
        kids = get_children(node)
        if kids:
            set_children(node, [normalize_layout(c) for c in kids])
        return node

    if ntype == "RECTANGLE":
        fills_list = node.get("fills", [])
        has_image  = any(f.get("type") == "IMAGE" for f in fills_list)
        fw["widget"] = "Image.asset" if has_image else "SizedBox"

    elif direction in ("ROW", "COLUMN"):
        layout_wrap = layout.get("layoutWrap", "NO_WRAP")
        if layout_wrap == "WRAP":
            fw["widget"] = "Wrap"
            fw["spacing"]    = gap
            fw["runSpacing"] = layout.get("counterAxisSpacing", gap)
            fw["wrapHint"]   = (
                "Bento/Grid layout detected (layoutWrap=WRAP). "
                "Use Wrap(spacing: X, runSpacing: X) for variable sizes, "
                "or GridView.count(crossAxisCount: N) for uniform cells."
            )
        else:
            fw["widget"] = "Row" if direction == "ROW" else "Column"
            if gap and main_align not in ("SPACE_BETWEEN", "SPACE_AROUND", "SPACE_EVENLY"):
                fw["gap"]       = gap
                fw["gapWidget"] = f"SizedBox({'width' if direction == 'ROW' else 'height'}: {gap})"
            if main_align in ALIGN_MAP:
                mav = ALIGN_MAP[main_align]
                fw["mainAxisAlignment"] = mav
                # SPACE_BETWEEN: insert Spacer() between children instead of fixed gap
                if main_align == "SPACE_BETWEEN":
                    fw["spacerHint"] = "Insert Spacer() between children"
            if cross_align in CROSS_ALIGN_MAP:
                fw["crossAxisAlignment"] = CROSS_ALIGN_MAP[cross_align]

    elif _is_stack(node):
        fw["widget"] = "Stack"
        fw["fit"]    = "StackFit.loose"
        # Tag children with Positioned hints
        parent_bounds = node.get("bounds", {})
        kids = get_children(node)
        for child in kids:
            child["_positioned"] = _positioned_hint(child, parent_bounds)
        set_children(node, kids)

    else:
        fw["widget"] = "SizedBox"

    # ── 2. Padding ──
    if any(padding.get(k, 0) != 0 for k in ("top", "right", "bottom", "left")):
        fw["padding"] = _to_edge_insets(padding)
        # Padding forces Container or wraps with Padding widget
        if fw["widget"] in ("Row", "Column", "Stack"):
            fw["paddingWrapper"] = f"Padding(padding: {fw['padding']}, child: ...)"

    # ── 3. Decoration (fill / gradient / border / shadow / radius) ──
    deco = _build_decoration(node)
    if deco:
        fw["decoration"] = deco
        # Any decoration requires Container (or DecoratedBox for perf)
        if fw["widget"] in ("SizedBox",):
            fw["widget"] = "Container"
        elif fw["widget"] in ("Row", "Column", "Stack"):
            fw["decorationWrapper"] = "DecoratedBox"  # wrap the layout widget

    # ── 4. Clip ──
    if node.get("clipsContent") and deco and deco.get("borderRadius"):
        fw["clip"] = {
            "widget":        "ClipRRect",
            "borderRadius":  deco["borderRadius"],
            "dart":          f"ClipRRect(borderRadius: {deco['borderRadius']}, child: ...)",
        }

    # ── 5. Opacity ──
    opacity = node.get("opacity")
    if opacity is not None and opacity < 1.0:
        # Skip Opacity wrapper when opacity is already baked into gradient stop
        # colors — adding Opacity on top would double-apply the transparency.
        if deco and deco.get("_gradientOpacityBaked"):
            pass
        else:
            fw["opacity"] = {
                "widget": "Opacity",
                "value":  round(opacity, 3),
                "dart":   f"Opacity(opacity: {round(opacity,3)}, child: ...)",
            }

    # ── 6. Backdrop / layer blur ──
    for eff in node.get("effects", []):
        if not eff.get("visible", True):
            continue
        etype = eff.get("type", "")
        if etype == "BACKGROUND_BLUR":
            sigma = round(eff.get("radius", 10), 1)
            fw["backdropFilter"] = {
                "widget": "BackdropFilter",
                "sigmaX": sigma,
                "sigmaY": sigma,
                "dart":   f"BackdropFilter(filter: ImageFilter.blur(sigmaX: {sigma}, sigmaY: {sigma}), child: ...)",
                "import": "dart:ui",
            }
            break
        elif etype == "LAYER_BLUR":
            sigma = round(eff.get("radius", 5), 1)
            fw["layerBlur"] = {
                "widget": "ImageFiltered",
                "sigmaX": sigma,
                "sigmaY": sigma,
                "dart":   f"ImageFiltered(imageFilter: ImageFilter.blur(sigmaX: {sigma}, sigmaY: {sigma}), child: ...)",
                "import": "dart:ui",
            }
            break

    node["flutterWidget"] = fw
    kids = get_children(node)
    if kids:
        set_children(node, [normalize_layout(c) for c in kids])
    return node


# ─────────────────────────────────────────────────────────────
# PASS 3.5 — TEXT NODE NORMALIZATION
# ─────────────────────────────────────────────────────────────

FONT_WEIGHT_MAP = {
    100: "FontWeight.w100", 200: "FontWeight.w200", 300: "FontWeight.w300",
    400: "FontWeight.w400", 500: "FontWeight.w500", 600: "FontWeight.w600",
    700: "FontWeight.w700", 800: "FontWeight.w800", 900: "FontWeight.w900",
}

TEXT_ALIGN_MAP = {
    "LEFT":    "TextAlign.left",
    "CENTER":  "TextAlign.center",
    "RIGHT":   "TextAlign.right",
    "JUSTIFY": "TextAlign.justify",
}

TEXT_DECORATION_MAP = {
    "UNDERLINE":     "TextDecoration.underline",
    "STRIKETHROUGH": "TextDecoration.lineThrough",
    "NONE":          "TextDecoration.none",
}


def normalize_text(node: dict) -> dict:
    if node.get("type") != "TEXT":
        kids = get_children(node)
        if kids:
            set_children(node, [normalize_text(c) for c in kids])
        return node

    style = node.get("style", {})
    fills = node.get("fills", [])

    # Resolve text color
    color = None
    for f in fills:
        if f.get("type") == "SOLID":
            color = f.get("dartConst") or f.get("resolvedHex")
            break
    if not color and node.get("fill"):
        color = node["fill"].get("dartConst") or node["fill"].get("value")

    font_size   = style.get("fontSize", 14)
    font_weight = FONT_WEIGHT_MAP.get(style.get("fontWeight", 400), "FontWeight.w400")
    font_family = style.get("fontFamily", "")
    line_height = style.get("lineHeightPx") or style.get("lineHeight")
    letter_sp   = style.get("letterSpacing", 0)
    text_align  = TEXT_ALIGN_MAP.get(style.get("textAlignHorizontal", "LEFT"), "TextAlign.left")
    text_deco   = TEXT_DECORATION_MAP.get(style.get("textDecoration", "NONE"), "TextDecoration.none")
    italic      = style.get("italic", False)

    text_style = {
        "fontSize":      font_size,
        "fontWeight":    font_weight,
        "color":         color or "AppColors.greyDark",
        "fontStyle":     "FontStyle.italic" if italic else "FontStyle.normal",
        "textDecoration": text_deco,
    }
    if font_family:
        text_style["fontFamily"] = font_family
    if line_height:
        text_style["height"] = round(line_height / font_size, 4) if font_size else None
    if letter_sp and letter_sp != 0:
        text_style["letterSpacing"] = letter_sp

    node["flutterWidget"] = {
        "widget":    "Text",
        "content":   node.get("characters", ""),
        "textAlign": text_align,
        "style":     text_style,
        "maxLines":  node.get("maxLines"),
        "overflow":  "TextOverflow.ellipsis" if node.get("textTruncation") == "ENDING" else None,
        "dart":      _text_dart_hint(node.get("characters", ""), text_style, text_align),
    }
    return node


def _text_dart_hint(content: str, style: dict, align: str) -> str:
    color = style.get("color", "AppColors.greyDark")
    size  = style.get("fontSize", 14)
    wt    = style.get("fontWeight", "FontWeight.w400")
    return (
        f"Text('{content}', "
        f"textAlign: {align}, "
        f"style: TextStyle(fontSize: {size}, fontWeight: {wt}, color: {color}))"
    )


# ─────────────────────────────────────────────────────────────
# PASS 4 — INSTANCE & VECTOR RESOLUTION
# ─────────────────────────────────────────────────────────────

# Extend this map with your project's component IDs → Flutter widget specs
KNOWN_COMPONENTS: dict[str, dict] = {
    "421:1392": {"widget": "SvgPicture.asset", "asset": "assets/icons/ic_home.svg",         "color": "AppColors.brownNormal"},
    "421:1396": {"widget": "SvgPicture.asset", "asset": "assets/icons/ic_heart.svg",        "color": "AppColors.white"},
    "421:1397": {"widget": "SvgPicture.asset", "asset": "assets/icons/ic_bag.svg",          "color": "AppColors.white"},
    "421:1398": {"widget": "SvgPicture.asset", "asset": "assets/icons/ic_notification.svg", "color": "AppColors.white"},
    # home_page product cards
    "421:1302": {"widget": "ProductCardWidget", "import": "package:travel_app/pages/home_page/widgets/product_card_widget.dart"},
    "421:1318": {"widget": "ProductCardWidget", "import": "package:travel_app/pages/home_page/widgets/product_card_widget.dart"},
    "421:1334": {"widget": "ProductCardWidget", "import": "package:travel_app/pages/home_page/widgets/product_card_widget.dart"},
    "421:1350": {"widget": "ProductCardWidget", "import": "package:travel_app/pages/home_page/widgets/product_card_widget.dart"},
}

# Component variant property → Flutter widget parameter mapping
# e.g. {"State": {"Default": {}, "Hover": {"color": "AppColors.brownNormalHover"}}}
VARIANT_MAP: dict[str, dict] = {}


def resolve_instances(node: dict) -> dict:
    ntype   = node.get("type", "")
    node_id = node.get("id", "")

    # ── VECTOR / BOOLEAN_OPERATION → SvgPicture ──
    if ntype in ("VECTOR", "BOOLEAN_OPERATION"):
        name_slug = node.get("name", "unknown").lower().replace(" ", "_").replace("/", "_")
        node["flutterWidget"] = {
            "widget":  "SvgPicture.asset",
            "asset":   f"assets/icons/ic_{name_slug}.svg",
            "note":    "Export this vector from Figma as SVG and place in assets/icons/",
        }

    # ── INSTANCE → known component or placeholder ──
    elif ntype == "INSTANCE":
        if node_id in KNOWN_COMPONENTS:
            spec = KNOWN_COMPONENTS[node_id]
            fw   = dict(spec)
            # Apply variant overrides
            props = node.get("componentProperties", {})
            for prop_name, prop_val in props.items():
                variant_overrides = VARIANT_MAP.get(prop_name, {}).get(prop_val, {})
                fw.update(variant_overrides)
            node["flutterWidget"] = fw
        else:
            # Unknown instance: create placeholder with variant props for manual resolution
            props = node.get("componentProperties", {})
            node.setdefault("flutterWidget", {
                "widget":     "ComponentPlaceholder",
                "componentId": node_id,
                "variantProps": props,
                "note":        "Map this component ID in KNOWN_COMPONENTS",
            })

    kids = get_children(node)
    if kids:
        set_children(node, [resolve_instances(c) for c in kids])
    return node


# ─────────────────────────────────────────────────────────────
# PASS 5 — SIZING & CONSTRAINTS
# ─────────────────────────────────────────────────────────────

SCREEN_WIDTH = 375.0

CONSTRAINT_H_MAP = {
    "STRETCH": "double.infinity",   # width = parent width → Expanded / double.infinity
    "SCALE":   "fractional",        # proportional → FractionallySizedBox
    "CENTER":  "center",            # centered → Align(alignment: Alignment.center)
    "LEFT":    "fixed",
    "RIGHT":   "fixed",
    "FIXED":   "fixed",
}

CONSTRAINT_V_MAP = {
    "STRETCH": "double.infinity",
    "SCALE":   "fractional",
    "CENTER":  "center",
    "TOP":     "fixed",
    "BOTTOM":  "fixed",
    "FIXED":   "fixed",
}


def normalize_sizing(node: dict, parent_w: float = SCREEN_WIDTH, parent_h: float = 812.0) -> dict:
    bounds      = node.get("bounds", {})
    constraints = node.get("constraints", {})
    w = bounds.get("width")
    h = bounds.get("height")

    h_constraint = CONSTRAINT_H_MAP.get(constraints.get("horizontal", "FIXED"), "fixed")
    v_constraint = CONSTRAINT_V_MAP.get(constraints.get("vertical",   "FIXED"), "fixed")

    # ── Width ──
    if h_constraint == "double.infinity" or (w is not None and abs(w - parent_w) < 1):
        node["flutterWidth"] = "double.infinity"
    elif h_constraint == "fractional" and w and parent_w:
        frac = round(w / parent_w, 4)
        node["flutterWidth"]         = w
        node["flutterWidthFractional"] = frac
        node["flutterWidthWidget"]   = f"FractionallySizedBox(widthFactor: {frac}, child: ...)"
    elif h_constraint == "center":
        node["flutterWidth"]       = w
        node["flutterAlignHint"]   = "Align(alignment: Alignment.center, child: ...)"
    else:
        if w is not None:
            node["flutterWidth"] = w

    # ── Height ──
    if v_constraint == "double.infinity" or (h is not None and abs(h - parent_h) < 1):
        node["flutterHeight"] = "double.infinity"
    elif v_constraint == "fractional" and h and parent_h:
        frac = round(h / parent_h, 4)
        node["flutterHeight"]           = h
        node["flutterHeightFractional"] = frac
    elif v_constraint == "center":
        node["flutterHeight"]    = h
        node["flutterAlignHint"] = node.get("flutterAlignHint") or "Align(alignment: Alignment.center, child: ...)"
    else:
        if h is not None:
            node["flutterHeight"] = h

    # ── Expanded hint (FILL sizing in parent ROW/COLUMN) ──
    if node.get("layoutGrow") == 1:
        node["flutterExpanded"] = "Expanded(child: ...)"

    kids = get_children(node)
    if kids:
        cw = w if w else parent_w
        ch = h if h else parent_h
        set_children(node, [normalize_sizing(c, cw, ch) for c in kids])
    return node


# ─────────────────────────────────────────────────────────────
# PASS 6 — SCREEN LAYOUT MAP + PER-WIDGET EXPORT HELPERS
# ─────────────────────────────────────────────────────────────

def _slugify(name: str) -> str:
    import re
    # Lowercase, keep alphanumerics, collapse everything else to single underscores.
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower())
    return slug.strip("_") or "widget"


# Leaf node types never become their own "root" JSON even if they carry children.
LEAF_TYPES = {
    "TEXT", "VECTOR", "BOOLEAN_OPERATION", "RECTANGLE", "ELLIPSE",
    "LINE", "STAR", "REGULAR_POLYGON", "POLYGON",
}


def _is_complex_container(node: dict) -> bool:
    """A node worth its own root JSON + PNG: a non-leaf container with structure.

    Heuristic proxy for analyze-design's SIMPLE/COMPLEX call so normalize can
    pre-extract every drill-down target up front (analyze has no Figma MCP).
    A container with >= 2 children (and not a leaf shape/text) is 'complex' and
    gets its own root files; analyze later confirms the SIMPLE/COMPLEX label and
    flags NEEDS_EXTRACT for anything still under-extracted.
    """
    if node.get("type", "") in LEAF_TYPES:
        return False
    return len(get_children(node)) >= 2


def _is_body(node: dict) -> bool:
    """A 'body' section node — the scrollable content zone of a mobile screen.

    The body is the meat of the screen, so it must ALWAYS be drilled to the
    full set of root nodes it contains (see _export_roots body rule). Matched
    by name slug so it is found wherever the body sits in the tree (it is often
    nested under a 'Master Layout' frame, not a direct screen child).
    """
    return _slugify(node.get("name", "")) == "body"


def _export_roots(node: dict, widgets_dir: Path, depth: int, max_depth: int,
                  exported: set, manifest: list) -> None:
    """Recursively export each 'root' as its own <id>_<name>.json.

    depth 0 == the screen (its children are the header/body/footer sections).
      - Sections (depth 1) are ALWAYS exported — they are the screen zones.
      - BODY rule: when the current node is named 'body', EVERY non-leaf direct
        child is force-exported as its own root — regardless of the
        >=2-children 'complex' heuristic — so each content card/row/section in
        the body gets its own JSON + PNG. The body is never under-extracted;
        nothing inside it is collapsed into the single body screenshot.
      - Other deeper nodes are exported only when they are complex containers
        (>= 2 children, non-leaf) — i.e. the complex widgets inside the body
        roots, drilling down until leaf level.
      - Recursion descends into any node that still has children (so a single
        wrapper frame does not hide a complex sub-root beneath it).
    """
    node_is_body = _is_body(node)
    for child in get_children(node):
        is_section = (depth == 0)
        cid = child.get("id", "")
        is_leaf = child.get("type", "") in LEAF_TYPES
        # Body rule: a body's direct, non-leaf child is ALWAYS a root.
        force_body_child = node_is_body and not is_leaf
        should_export = is_section or _is_complex_container(child) or force_body_child
        if should_export and cid and cid not in exported:
            slug = cid.replace(":", "_") + "_" + _slugify(child.get("name", "widget"))
            widget_path = widgets_dir / f"{slug}.json"
            widget_path.write_text(json.dumps(child, indent=2, ensure_ascii=False))
            exported.add(cid)
            manifest.append({
                "id":          cid,
                "slug":        slug,
                "name":        child.get("name", ""),
                "type":        child.get("type", ""),
                "depth":       depth + 1,
                "child_count": len(get_children(child)),
                "is_section":  is_section,
                "complex":     _is_complex_container(child),
                "in_body":     node_is_body,
            })
            tag = " (body-root)" if force_body_child else ""
            print(f"  ✓ depth{depth + 1} {widget_path.name}{tag}")
        # Drill deeper to reach complex sub-roots — but NEVER descend into an INSTANCE:
        # a component instance is one reusable widget, and its internal children carry
        # instance-scoped ids (`I<id>;<child>`) that cannot be screenshotted standalone.
        # Recursion always uses the normal heuristic below the body's direct children —
        # only the body's *direct* children are force-exported, not its whole subtree.
        if (depth + 1 < max_depth and get_children(child)
                and child.get("type") != "INSTANCE"):
            _export_roots(child, widgets_dir, depth + 1, max_depth, exported, manifest)


def _find_canvas_offset(screen: dict) -> tuple[float, float]:
    """
    figma_layout.json normalizes the root screen to origin (0,0) but children
    keep canvas-absolute coords. Find the true canvas origin by locating the
    full-screen FRAME child (same w×h as the screen).
    Falls back to the child with the minimum y-value.
    """
    sw = screen.get("bounds", {}).get("width", 375)
    sh = screen.get("bounds", {}).get("height", 812)
    for child in get_children(screen):
        if child.get("type") != "FRAME":
            continue
        cb = child.get("bounds", {})
        if abs(cb.get("width", 0) - sw) < 2 and abs(cb.get("height", 0) - sh) < 2:
            return cb.get("x", 0.0), cb.get("y", 0.0)
    # Fallback: use median x,y from children with valid bounds
    valid = [c.get("bounds", {}) for c in get_children(screen) if "bounds" in c]
    if not valid:
        return 0.0, 0.0
    xs = [b.get("x", 0) for b in valid if b.get("x") is not None]
    ys = [b.get("y", 0) for b in valid if b.get("y") is not None]
    return (sorted(xs)[len(xs) // 2] if xs else 0.0), (min(ys) if ys else 0.0)


def _has_gradient_fill(node: dict) -> bool:
    for f in node.get("fills", []):
        if isinstance(f, dict) and f.get("type", "") in ("GRADIENT_LINEAR", "GRADIENT_RADIAL"):
            return True
    f = node.get("fill") or node.get("background")
    if isinstance(f, dict) and "gradient" in f.get("tokenRef", ""):
        return True
    return False


def _has_image_fill(node: dict) -> bool:
    for f in node.get("fills", []):
        if isinstance(f, dict) and f.get("type") == "IMAGE":
            return True
    return False


def _infer_layout_type(node: dict) -> str:
    direction = node.get("layout", {}).get("direction")
    if direction == "ROW":
        return "ROW"
    if direction == "COLUMN":
        return "COLUMN"
    if _is_stack(node):
        return "STACK"
    return "STACK"


def _infer_visual_role(index: int, total: int, child: dict,
                       canvas_ox: float, canvas_oy: float, screen: dict) -> str:
    """Classify as BACKGROUND / CONTENT / OVERLAY based on z-order and position."""
    cb = child.get("bounds", {})
    sx = round(cb.get("x", 0) - canvas_ox, 2)
    sy = round(cb.get("y", 0) - canvas_oy, 2)
    sw = screen.get("bounds", {}).get("width", 375)
    sh = screen.get("bounds", {}).get("height", 812)

    # Extends beyond screen bounds → decorative background
    cw = cb.get("width", 0)
    ch = cb.get("height", 0)
    if cw > sw * 1.3 or ch > sh * 1.3 or sx < -10 or sy < -10:
        return "BACKGROUND"

    # Full-screen FRAME at z=lowest → content
    if abs(cw - sw) < 2 and abs(ch - sh) < 2 and index <= 1:
        return "CONTENT"

    # Last items or items positioned at the bottom → overlay (e.g. navbar)
    if index == total - 1:
        return "OVERLAY"

    return "CONTENT"


def _build_screen_layout(screen: dict, canvas_ox: float, canvas_oy: float) -> list:
    children = get_children(screen)
    total = len(children)
    result = []
    for i, child in enumerate(children):
        cb = child.get("bounds", {})
        result.append({
            "z_order":    i,
            "id":         child.get("id", ""),
            "name":       child.get("name", ""),
            "screen_x":   round(cb.get("x", 0) - canvas_ox, 2),
            "screen_y":   round(cb.get("y", 0) - canvas_oy, 2),
            "width":      cb.get("width"),
            "height":     cb.get("height"),
            "layout_type": _infer_layout_type(child),
            "role":       _infer_visual_role(i, total, child, canvas_ox, canvas_oy, screen),
            "has_gradient": _has_gradient_fill(child),
            "has_image":  _has_image_fill(child),
        })
    return result


def _merge_nodes_detail(screen: dict, detail_path: str) -> dict:
    """
    Merge full-detail fields (effects, fills with gradientStops/Transform, opacity)
    from figma_nodes_detail.json into matching nodes by id.
    Only merges into root-level children (the widget level).
    """
    if not Path(detail_path).exists():
        return screen
    detail_list = json.loads(Path(detail_path).read_text())
    if not isinstance(detail_list, list):
        detail_list = detail_list.get("nodes", [])
    detail_map = {n["id"]: n for n in detail_list if isinstance(n, dict) and "id" in n}
    for child in get_children(screen):
        node_id = child.get("id", "")
        if node_id in detail_map:
            extra = detail_map[node_id]
            for key in ("effects", "opacity"):
                if key in extra and key not in child:
                    child[key] = extra[key]
            # Overwrite fills only if detail has richer data (gradientStops present)
            detail_fills = extra.get("fills", [])
            if detail_fills and any(
                isinstance(f, dict) and ("gradientStops" in f or f.get("type", "") in ("GRADIENT_LINEAR", "GRADIENT_RADIAL"))
                for f in detail_fills
            ):
                child["fills"] = detail_fills
    return screen


# ─────────────────────────────────────────────────────────────
# PIPELINE
# ─────────────────────────────────────────────────────────────

def run_pipeline(layout_path: str, tokens_path: str, output_path: str,
                 nodes_detail_path: str = "", output_dir: str = ""):
    ws_root = Path.cwd() / ".ui-workspace"
    _load_token_map(ws_root)

    layout = json.loads(Path(layout_path).read_text())
    tokens = json.loads(Path(tokens_path).read_text())

    _build_hex_reverse_map(tokens.get("tokens", tokens))

    screen = deepcopy(layout["screen"])

    # Find canvas offset before any pass.
    # Old format (_adapt_layout.py): screen.bounds normalized to (0,0), children keep canvas-absolute coords.
    # New format (get_node): screen.bounds = page-absolute (e.g. x=-15472), children are ALREADY frame-relative.
    # Fix: normalize screen.bounds to (canvas_ox, canvas_oy) so _positioned_hint subtracts the right origin.
    canvas_ox, canvas_oy = _find_canvas_offset(screen)
    sb = screen.get("bounds", {})
    screen["bounds"] = {"x": canvas_ox, "y": canvas_oy,
                        "width": sb.get("width", 375), "height": sb.get("height", 812)}
    print(f"Canvas  : origin ({canvas_ox}, {canvas_oy})  screen.bounds normalized")

    # Fix B — merge full-detail (effects, gradientStops) from get_nodes_info result
    if nodes_detail_path:
        print("Pre     : Merging figma_nodes_detail.json into root children...")
        screen = _merge_nodes_detail(screen, nodes_detail_path)

    print("Pass 1  : Resolving tokens (hex + tokenRef → dartConst)...")
    screen = _walk(screen, resolve_tokens)

    print("Pass 2  : Flattening pass-through frames...")
    screen = flatten_frames(screen)

    print("Pass 3  : Decoration + Auto Layout + Stack + Opacity + Clip...")
    screen = normalize_layout(screen)

    print("Pass 3.5: Normalizing TEXT nodes → Text() + TextStyle...")
    screen = normalize_text(screen)

    print("Pass 4  : Resolving instances + VECTOR nodes...")
    screen = resolve_instances(screen)

    print("Pass 5  : Sizing + constraints → Flutter width/height hints...")
    screen = normalize_sizing(screen)

    # Fix C — generate _screen_layout block
    print("Pass 6  : Building _screen_layout map...")
    screen_layout = _build_screen_layout(screen, canvas_ox, canvas_oy)

    output = {
        "_meta": {
            **layout.get("_meta", {}),
            "preprocessor": "figma_preprocessor.py v2.1",
            "canvas_offset": {"x": canvas_ox, "y": canvas_oy},
            "passes": ["token-resolution", "frame-flatten", "decoration-layout",
                       "text-normalize", "instance-vector", "sizing-constraints",
                       "screen-layout-map", "per-widget-export"],
        },
        "_screen_layout": screen_layout,
        "screen": screen,
    }

    Path(output_path).write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"\n✓ Written: {output_path}")

    # Fix D — export per-root files (recursive: sections → body sub-roots → complex widgets)
    if output_dir:
        widgets_dir = Path(output_dir) / "widgets"
        widgets_dir.mkdir(parents=True, exist_ok=True)
        print("Pass 7  : Exporting per-root JSON files (recursive drill-down + body rule)...")
        exported: set = set()
        manifest: list = []
        # max_depth=6 so a body nested under wrapper frames (e.g. screen → Master
        # Layout → body) is still reached and every body root is exported.
        _export_roots(screen, widgets_dir, depth=0, max_depth=6,
                      exported=exported, manifest=manifest)
        # Manifest drives the PNG-capture loop in /normalize-figma-file (one PNG per root).
        manifest_path = widgets_dir / "_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
        print(f"  ✓ {len(manifest)} roots → {manifest_path.name}")

    print()
    _print_summary(screen)


# ─────────────────────────────────────────────────────────────
# SUMMARY PRINTER
# ─────────────────────────────────────────────────────────────

def _print_summary(node: dict, depth: int = 0, max_depth: int = 5):
    indent = "  " * depth
    fw = node.get("flutterWidget", {})
    widget = fw.get("widget", node.get("type", "?")) if isinstance(fw, dict) else str(fw)

    tags = []
    if isinstance(fw, dict):
        deco = fw.get("decoration", {})
        if deco.get("color"):     tags.append(f"fill={deco['color']}")
        if deco.get("gradient"):  tags.append(f"gradient={deco['gradient'].get('dartConst') or deco['gradient'].get('type','?')}")
        if deco.get("image"):     tags.append("image=DecorationImage")
        if deco.get("border"):    tags.append(f"border={deco['border']['dart'][:30]}…")
        if deco.get("boxShadow"): tags.append(f"shadow×{len(deco['boxShadow'])}")
        if deco.get("borderRadius"): tags.append(f"r={deco['borderRadius'][:28]}…")
        if fw.get("padding"):     tags.append(f"pad={fw['padding']}")
        if fw.get("gap"):         tags.append(f"gap={fw['gap']}")
        if fw.get("clip"):        tags.append("clip=ClipRRect")
        if fw.get("opacity"):     tags.append(f"opacity={fw['opacity']['value']}")
        if fw.get("content"):     tags.append(f'"{fw["content"][:20]}"')
    w = node.get("flutterWidth", "")
    h = node.get("flutterHeight", "")
    if w: tags.append(f"w={w}")
    if h: tags.append(f"h={h}")
    if node.get("flutterExpanded"):   tags.append("Expanded")
    if node.get("flutterAlignHint"):  tags.append("Align")

    tag_str = f"  ({', '.join(tags)})" if tags else ""
    print(f"{indent}[{node.get('name','?')}] → {widget}{tag_str}")

    if depth < max_depth:
        for child in get_children(node):
            _print_summary(child, depth + 1, max_depth)


if __name__ == "__main__":
    import sys

    # Usage: python3 .claude/commands/scripts/figma_preprocessor.py <feature_name>
    # Run from project root. Features live in .ui-workspace/<feature>/.
    feature = sys.argv[1] if len(sys.argv) > 1 else ""
    ws_root = Path.cwd() / ".ui-workspace"

    if feature:
        input_dir = ws_root / feature / "figma_code"
        out_dir   = ws_root / feature / "normalize_design_code"
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"Feature mode: {feature}")
        print(f"  Input : {input_dir}")
        print(f"  Output: {out_dir}")
    else:
        # Legacy: run from .ui-workspace/ directly
        input_dir = ws_root
        out_dir   = ws_root

    nodes_detail = input_dir / "figma_nodes_detail.json"

    run_pipeline(
        layout_path       = str(input_dir / "figma_layout.json"),
        tokens_path       = str(input_dir / "figma_design_tokens.json"),
        output_path       = str(out_dir   / "figma_normalized.json"),
        nodes_detail_path = str(nodes_detail) if nodes_detail.exists() else "",
        output_dir        = str(out_dir),
    )
