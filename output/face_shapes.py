"""
Face geometry, parsed straight from Skyler's reference SVGs rather than
redrawn by hand, so the on screen face actually matches the reference art
instead of an approximation of it.

CANVAS_SIZE is the coordinate space the reference SVGs were drawn in.
Everything below stays in that raw coordinate space, display.py is the
only place that scales it to fit whatever screen it is actually running
on.

Only a small subset of SVG path syntax is supported here, M, H, V, L, C,
Z, all absolute coordinates, because that is all the reference art uses.
Dropping in a new expression later means adding its path string below,
not writing new drawing code.
"""

import re

CANVAS_SIZE = (1280, 720)

# Based on Rosto-01.svg, but rebuilt symmetric. The raw reference curve
# had uneven control points (485.5 on the left, 512.5 on the right), which
# made the smile dip left of center and rise steeper on the right. Same
# width and depth as the original, now mirrored around x 639.5, the exact
# midpoint between the eyes.
SMILE_MOUTH_PATH = "M523 438.5C562 495 717 495 756 438.5"
SMILE_STROKE_WIDTH = 15

# Straight from Rosto-02.svg, the open "gulp" mouth, drawn as four layered
# shapes: a dark green base, a lighter green highlight near the bottom, a
# white band standing in for teeth, and a thick outline drawn last so it
# sits on top of everything else, matching the SVG's paint order.
GULP_DARK_FILL_PATH = "M738.5 409.5H536C533.667 455.5 546 545.5 642 545.5C724.5 545.5 739.667 455.5 738.5 409.5Z"
GULP_LIGHT_HIGHLIGHT_PATH = "M713 500C652.2 479.6 591 503.5 568 518C578.5 527.333 609 545.9 647 545.5C685 545.1 706.833 515 713 500Z"
GULP_TEETH_RECT_PATH = "M737 444H537.5V411H737V444Z"
GULP_TEETH_STROKE_WIDTH = 9
GULP_OUTLINE_PATH = (
    "M733.625 409.5H540.753C538.09 409.5 535.888 411.58 535.818 414.242"
    "C534.582 461.401 549.2 545.5 642 545.5C721.681 545.5 738.551 461.546 "
    "738.56 414.365C738.561 411.653 736.337 409.5 733.625 409.5Z"
)
GULP_OUTLINE_STROKE_WIDTH = 12

# Both eyes are identical ellipses, just mirrored left and right.
EYE_LEFT = {"cx": 333.5, "cy": 271, "rx": 37.5, "ry": 43}
EYE_RIGHT = {"cx": 945.5, "cy": 271, "rx": 37.5, "ry": 43}


def _cubic_bezier(p0, p1, p2, p3, segments=16):
    """Sample a cubic bezier curve into line segments."""
    points = []
    for step in range(1, segments + 1):
        t = step / segments
        mt = 1 - t
        x = (mt ** 3) * p0[0] + 3 * (mt ** 2) * t * p1[0] + 3 * mt * (t ** 2) * p2[0] + (t ** 3) * p3[0]
        y = (mt ** 3) * p0[1] + 3 * (mt ** 2) * t * p1[1] + 3 * mt * (t ** 2) * p2[1] + (t ** 3) * p3[1]
        points.append((x, y))
    return points


def parse_svg_path(d):
    """Turn an SVG path's d attribute into a list of (x, y) points.

    Supports M (moveto), H (horizontal lineto), V (vertical lineto),
    L (lineto), C (cubic bezier), and Z (close path), all absolute.
    That covers every path in the reference art. Curves get flattened
    into straight segments so the result can go straight into
    pygame.draw.polygon or pygame.draw.lines.
    """
    tokens = re.findall(r"[MHVLCZ]|-?\d*\.?\d+", d)
    points = []
    current = (0.0, 0.0)
    command = None
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token in "MHVLCZ":
            command = token
            i += 1
            continue

        if command == "M":
            current = (float(tokens[i]), float(tokens[i + 1]))
            points.append(current)
            i += 2
            command = "L"  # a bare coordinate pair after M is an implicit lineto
        elif command == "L":
            current = (float(tokens[i]), float(tokens[i + 1]))
            points.append(current)
            i += 2
        elif command == "H":
            current = (float(tokens[i]), current[1])
            points.append(current)
            i += 1
        elif command == "V":
            current = (current[0], float(tokens[i]))
            points.append(current)
            i += 1
        elif command == "C":
            p1 = (float(tokens[i]), float(tokens[i + 1]))
            p2 = (float(tokens[i + 2]), float(tokens[i + 3]))
            p3 = (float(tokens[i + 4]), float(tokens[i + 5]))
            points.extend(_cubic_bezier(current, p1, p2, p3))
            current = p3
            i += 6
        elif command == "Z":
            i += 1
        else:
            i += 1  # unsupported command, skip its token rather than crash

    return points


def mirror_vertical(points, baseline_y):
    """Flip a set of points above or below a baseline. Used to turn the
    reference smile curve into a frown for sad and worried moods without
    needing a whole second reference asset for it."""
    return [(x, baseline_y - (y - baseline_y)) for x, y in points]


# Parsed once at import time, every consumer reuses the same point lists.
SMILE_MOUTH_POINTS = parse_svg_path(SMILE_MOUTH_PATH)
FROWN_MOUTH_POINTS = mirror_vertical(SMILE_MOUTH_POINTS, baseline_y=438.5)

GULP_DARK_FILL_POINTS = parse_svg_path(GULP_DARK_FILL_PATH)
GULP_LIGHT_HIGHLIGHT_POINTS = parse_svg_path(GULP_LIGHT_HIGHLIGHT_PATH)
GULP_TEETH_RECT_POINTS = parse_svg_path(GULP_TEETH_RECT_PATH)
GULP_OUTLINE_POINTS = parse_svg_path(GULP_OUTLINE_PATH)
