"""Color output themes for agentix CLI output."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ColorTheme:
    """Color theme definition for CLI output.

    Parameters
    ----------
    name : str
        Theme name.
    success : str
        Color for success messages.
    error : str
        Color for error messages.
    warning : str
        Color for warning messages.
    info : str
        Color for info messages.
    accent : str
        Color for accents/highlights.
    muted : str
        Color for muted/secondary text.
    """

    name: str
    success: str = "green"
    error: str = "red"
    warning: str = "yellow"
    info: str = "cyan"
    accent: str = "magenta"
    muted: str = "dim white"

    def to_rich_style(self, key: str) -> str:
        """Get Rich-style format string for a theme key.

        Parameters
        ----------
        key : str
            Theme key (success, error, warning, info, accent, muted).

        Returns
        -------
        str
            Rich-compatible style string.
        """
        return getattr(self, key, self.info)


# ---------------------------------------------------------------------------
# Built-in themes
# ---------------------------------------------------------------------------

THEMES: Dict[str, ColorTheme] = {
    "default": ColorTheme(
        name="default",
        success="green",
        error="red",
        warning="yellow",
        info="cyan",
        accent="magenta",
        muted="dim white",
    ),
    "dark": ColorTheme(
        name="dark",
        success="spring_green1",
        error="orange_red",
        warning="gold1",
        info="deep_sky_blue2",
        accent="medium_purple1",
        muted="grey50",
    ),
    "light": ColorTheme(
        name="light",
        success="dark_green",
        error="dark_red",
        warning="dark_orange",
        info="dark_blue",
        accent="purple4",
        muted="grey62",
    ),
    "monochrome": ColorTheme(
        name="monochrome",
        success="white",
        error="bright_white",
        warning="white",
        info="bright_white",
        accent="white",
        muted="grey50",
    ),
    "ocean": ColorTheme(
        name="ocean",
        success="sea_green2",
        error="light_coral",
        warning="light_goldenrod2",
        info="dodger_blue2",
        accent="medium_turquoise",
        muted="steel_blue",
    ),
    "sunset": ColorTheme(
        name="sunset",
        success="pale_green3",
        error="indian_red",
        warning="orange1",
        info="light_sky_blue1",
        accent="plum2",
        muted="light_pink4",
    ),
}


def get_theme(name: str = "default") -> ColorTheme:
    """Get a color theme by name.

    Parameters
    ----------
    name : str
        Theme name (default: "default").

    Returns
    -------
    ColorTheme
        The matching theme, or the default theme if not found.
    """
    return THEMES.get(name, THEMES["default"])


def list_themes() -> str:
    """Return a formatted list of available themes.

    Returns
    -------
    str
        Human-readable list of theme names.
    """
    return "\n".join(f"  • {name}" for name in sorted(THEMES.keys()))
