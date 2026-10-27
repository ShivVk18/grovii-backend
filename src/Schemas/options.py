"""Allowed values for storyboard inputs.

Each canonical key is the value the frontend sends today, so stored data and
the UI are unchanged. Aliases let other clients (and the eval dataset) send
human labels such as "Instagram Reels"; they are matched case-insensitively and
mapped to the canonical key.
"""
import re

PLATFORMS: dict[str, tuple[str, ...]] = {
    "reels": ("instagram reels", "instagram reel", "instagram", "ig reels"),
    "tiktok": ("tik tok",),
    "shorts": ("youtube shorts", "youtube short", "yt shorts"),
    "linkedin": ("linkedin video",),
}

GOALS: dict[str, tuple[str, ...]] = {
    "inspire": ("inspire & motivate", "motivate"),
    "educate": ("educate & inform", "inform"),
    "entertain": ("entertain & hook",),
    "convert": ("convert & sell", "sell"),
    "promote": (),
    "storytelling": ("tell a story",),
}

TONES: dict[str, tuple[str, ...]] = {
    "energetic": ("energetic & bold", "bold"),
    "calm": ("calm & thoughtful", "thoughtful"),
    "authoritative": ("direct & authoritative", "direct"),
    "relatable": ("casual & relatable",),
    "professional": (),
    "casual": (),
    "fun": ("playful",),
    "authentic": (),
    "conversational": (),
    "motivating": ("motivational",),
    "emotional": (),
}

STYLES: dict[str, tuple[str, ...]] = {
    "talking_head": ("talking head",),
    "educational": ("educational / breakdown", "breakdown"),
    "pov": ("pov / vlog", "vlog"),
    "storytelling": (),
}

# Canonical form here is the display name, because that is what the frontend sends.
LANGUAGES: dict[str, tuple[str, ...]] = {
    "English": (),
    "Hindi": ("hindi / hinglish",),
    "Hinglish": (),
    "Spanish": ("español", "espanol"),
    "French": ("français", "francais"),
    "German": ("deutsch",),
}


def _norm(value: str) -> str:
    return re.sub(r"[\s_\-]+", " ", value.strip().lower())


def _lookup(options: dict[str, tuple[str, ...]]) -> dict[str, str]:
    table: dict[str, str] = {}
    for canonical, aliases in options.items():
        for name in (canonical, *aliases):
            table[_norm(name)] = canonical
    return table


_TABLES = {id(o): _lookup(o) for o in (PLATFORMS, GOALS, TONES, STYLES, LANGUAGES)}


def canonical(options: dict[str, tuple[str, ...]], value: str, label: str) -> str:
    """Map a user value to its canonical key, or raise ValueError with the allowed list."""
    found = _TABLES[id(options)].get(_norm(value)) if isinstance(value, str) else None
    if found is None:
        raise ValueError(f"{label} must be one of: {', '.join(options)}.")
    return found
