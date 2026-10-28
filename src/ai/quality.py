"""Output-quality rules enforced in code (Phase D): hook choice, hashtags,
music labelling, language check."""
import re

# ------------------------------------------------------------------ hooks ----
HOOK_MIN_WORDS, HOOK_MAX_WORDS = 3, 12


def pick_best_hook(candidates: list[dict]) -> str:
    """Highest-scoring candidate that is short enough to say in ~3 seconds.
    Replaces the old second LLM call that "regenerated" the hook."""
    def words(c):
        return len(str(c.get("hook", "")).split())

    usable = [c for c in candidates if isinstance(c, dict) and HOOK_MIN_WORDS <= words(c) <= HOOK_MAX_WORDS]
    pool = usable or [c for c in candidates if isinstance(c, dict) and str(c.get("hook", "")).strip()]
    if not pool:
        return ""
    best = max(pool, key=lambda c: float(c.get("score") or 0))
    return str(best["hook"]).strip().strip('"')


# --------------------------------------------------------------- hashtags ----
# Same filler list the Phase 5 validator uses: tags that say nothing about the video.
FILLER_HASHTAGS = {
    "viral", "fyp", "foryou", "trending", "explore", "reels", "shorts", "tiktok", "instagram",
    "video", "like", "share", "follow", "foryoupage", "reel", "short", "love", "instagood", "trend",
}
MAX_HASHTAGS = 10


def clean_hashtags(tags: list, max_count: int = MAX_HASHTAGS) -> list[str]:
    """Normalise to #lowercase without spaces, drop filler and duplicates, cap the count."""
    out: list[str] = []
    for tag in tags:
        text = tag.get("hashtag") or tag.get("tag") or "" if isinstance(tag, dict) else str(tag)
        body = re.sub(r"[^\w]", "", text.lower(), flags=re.UNICODE)
        if not body or body in FILLER_HASHTAGS:
            continue
        clean = f"#{body}"
        if clean not in out:
            out.append(clean)
        if len(out) == max_count:
            break
    return out


# ------------------------------------------------------------------ music ----
MUSIC_LABEL = "Style reference, not verified: check the track exists and is licensed before using it."
LICENSING_NOTE = ("Commercial or brand accounts usually can't use popular songs. Use the royalty-free "
                  "alternative or your platform's commercial music library.")


def label_music(songs: list[dict]) -> list[dict]:
    """Song suggestions come from the model's memory and are not checked against
    any catalogue, so they are labelled as unverified style references."""
    return [{**s, "verified": False, "label": MUSIC_LABEL, "licensing_note": LICENSING_NOTE}
            for s in songs if isinstance(s, dict)]


# --------------------------------------------------------------- language ----
_DEVANAGARI = re.compile(r"[ऀ-ॿ]")
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
HINGLISH_WORDS = {"hai", "hain", "ka", "ki", "ke", "ko", "mein", "main", "nahi", "karo", "karna", "karte",
                  "kar", "yeh", "ye", "woh", "aur", "bhi", "kya", "hum", "tum", "aap", "apna", "phir",
                  "pehle", "raha", "rahe", "wala", "se", "tha", "thi", "ho", "bhai", "yaar", "bas", "sab"}
STOPWORDS = {
    "English": {"the", "and", "you", "your", "for", "with", "this", "that", "are", "is", "to", "of", "in", "a", "it"},
    "Spanish": {"el", "la", "los", "las", "de", "que", "y", "en", "un", "una", "para", "con", "por", "es", "tu"},
    "French": {"le", "la", "les", "de", "des", "et", "un", "une", "pour", "avec", "est", "que", "dans", "vous", "ton"},
    "German": {"der", "die", "das", "und", "ein", "eine", "mit", "fur", "für", "ist", "zu", "den", "nicht", "du", "dein"},
}
MIN_WORDS_TO_CHECK = 6


def language_problems(language: str, texts: dict[str, str]) -> list[str]:
    """Names of fields that do not look like `language` ([] if all fine).
    A cheap heuristic, not a language model: it catches wholesale English
    leakage and wrong scripts, not subtle mistakes."""
    problems = []
    for field, text in texts.items():
        text = text or ""
        words = [w.lower() for w in _WORD.findall(text)]
        if len(words) < MIN_WORDS_TO_CHECK and language != "Hindi":
            continue
        if language == "Hinglish":
            if _DEVANAGARI.search(text) or not (set(words) & HINGLISH_WORDS):
                problems.append(field)
        elif language == "Hindi":
            if text.strip() and not _DEVANAGARI.search(text):
                problems.append(field)
        elif language in STOPWORDS and language != "English":
            target = sum(w in STOPWORDS[language] for w in words)
            english = sum(w in STOPWORDS["English"] for w in words)
            if english > target:
                problems.append(field)
    return problems
