"""
Light and dark color palettes for the face.

Light is taken directly from the reference SVGs, green family throughout.
Dark switches to a purple family instead of just inverting the green, eyes
and mouth stroke in a lighter purple, the mouth cavity in a dark purple,
and the tongue highlight in a lighter purple than the cavity so the layers
still read clearly against the dark background.
Every value here is a plain RGB tuple, change any of them and the face
picks it up next frame, no other file needs to know palettes changed.
"""

LIGHT = {
    "background": (0xC0, 0xF9, 0xDE),
    "eye": (0x00, 0x00, 0x00),
    "mouth_stroke": (0x00, 0x00, 0x00),
    "mouth_dark_fill": (0x1D, 0x8F, 0x3B),
    "mouth_light_fill": (0x04, 0xD0, 0x5F),
    "mouth_teeth": (0xFF, 0xFF, 0xFF),
}

DARK = {
    "background": (0x11, 0x1B, 0x15),
    "eye": (0x8B, 0x5C, 0xF6),
    "mouth_stroke": (0xC4, 0xB5, 0xFD),
    "mouth_dark_fill": (0x4C, 0x1D, 0x95),
    "mouth_light_fill": (0x7C, 0x3A, 0xED),
    "mouth_teeth": (0xED, 0xE9, 0xFE),
}

THEMES = {"light": LIGHT, "dark": DARK}
DEFAULT_THEME = "light"
