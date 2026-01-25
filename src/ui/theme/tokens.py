"""Design tokens for UI theme: colors, spacing, typography, radius.

Used by apply_theme for programmatic styling (e.g. font). QSS (app_style.qss)
uses matching values; kept here as single source for any Python-driven styling.
"""

# -----------------------------------------------------------------------------
# Colors (hex for QSS compatibility when substituted; names for code)
# -----------------------------------------------------------------------------
colors = {
    "primary": "#2563eb",
    "primary_hover": "#1d4ed8",
    "secondary": "#64748b",
    "background": "#f8fafc",
    "surface": "#ffffff",
    "text": "#0f172a",
    "text_muted": "#64748b",
    "border": "#e2e8f0",
    "success": "#16a34a",
    "warning": "#ca8a04",
    "error": "#dc2626",
}

# -----------------------------------------------------------------------------
# Spacing (pixels)
# -----------------------------------------------------------------------------
spacing = {
    "xs": 2,
    "sm": 4,
    "md": 8,
    "lg": 16,
    "xl": 24,
}

# -----------------------------------------------------------------------------
# Typography
# -----------------------------------------------------------------------------
typography = {
    "font_family": "Segoe UI",  # Windows; macOS/SF use system default fallback
    "font_family_fallback": "Helvetica Neue",  # fallback
    "font_size_base": 10,
    "font_size_small": 9,
    "font_size_large": 11,
}

# -----------------------------------------------------------------------------
# Radius (px) for rounded corners
# -----------------------------------------------------------------------------
radius = {
    "radius_sm": 3,
    "radius_md": 6,
    "radius_lg": 8,
}

__all__ = ["colors", "spacing", "typography", "radius"]
