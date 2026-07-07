"""Tests for output/face_shapes.py: SVG parsing and face geometry."""

from output import face_shapes as fs


def test_parse_moveto_and_lineto():
    points = fs.parse_svg_path("M10 20 L30 40")
    assert points == [(10.0, 20.0), (30.0, 40.0)]


def test_parse_horizontal_and_vertical():
    points = fs.parse_svg_path("M0 0 H50 V60")
    assert points == [(0.0, 0.0), (50.0, 0.0), (50.0, 60.0)]


def test_parse_cubic_bezier_lands_on_endpoint():
    points = fs.parse_svg_path("M0 0 C0 10 10 10 10 0")
    assert points[0] == (0.0, 0.0)
    assert points[-1] == (10.0, 0.0)
    assert len(points) > 2  # the curve got sampled into segments


def test_mirror_vertical_flips_around_baseline():
    mirrored = fs.mirror_vertical([(0, 10), (5, 30)], baseline_y=20)
    assert mirrored == [(0, 30), (5, 10)]


def test_smile_is_centered_between_eyes():
    eye_mid = (fs.EYE_LEFT["cx"] + fs.EYE_RIGHT["cx"]) / 2
    xs = [x for x, _ in fs.SMILE_MOUTH_POINTS]
    span_center = (min(xs) + max(xs)) / 2
    assert abs(span_center - eye_mid) < 1


def test_smile_lowest_point_is_at_center():
    eye_mid = (fs.EYE_LEFT["cx"] + fs.EYE_RIGHT["cx"]) / 2
    lowest = max(fs.SMILE_MOUTH_POINTS, key=lambda p: p[1])
    assert abs(lowest[0] - eye_mid) < 8


def test_frown_mirrors_smile():
    smile_bottom = max(y for _, y in fs.SMILE_MOUTH_POINTS)
    frown_top = min(y for _, y in fs.FROWN_MOUTH_POINTS)
    # Mirrored around 438.5: smile's deepest dip equals frown's highest rise.
    assert abs((smile_bottom - 438.5) - (438.5 - frown_top)) < 0.001
