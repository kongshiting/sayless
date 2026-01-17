# keyword_phrases.py
# Final version: single-word, story-ordered keyword extraction

import re
from collections import Counter
from typing import List, Tuple
import yake

# ---------------- vocab ----------------

FILLERS = {
    "uh", "um", "eh", "lah", "leh", "lor", "sia", "bro", "bruh",
    "omg", "ya", "yah", "okay", "ok"
}

DISCOURSE = {
    "basically", "recently", "actually", "literally", "anyway", "anyways",
    "like", "just", "mean", "alright", "right", "kinda", "kind", "sorta", "sort",
    "so", "well"
}

STOPWORDS = {
    "i", "me", "my", "mine", "we", "our", "you", "your", "he", "she", "they", "it",
    "a", "an", "the", "and", "or", "but", "because", "then",
    "is", "am", "are", "was", "were", "be", "been", "being",
    "to", "of", "in", "on", "at", "for", "with", "as", "that", "this",
    "really", "very", "today", "now", "later",
    "ll", "im", "ive", "dont", "cant", "wont",
    "not"
}

GENERIC_DROP = {
    "day", "again", "whole", "time", "thing", "stuff",
    "supposed", "weeks", "week", "back",
    "somewhere", "still", "there"
}

EMOTION_WORDS = {
    "tired", "tiring", "stressed", "exhausted", "sad", "angry",
    "upset", "anxious", "worried", "hungry", "confused",
    "happy", "excited", "embarrassed"
}

COMMON_VERBS = {
    "wake", "woke", "miss", "missed", "rush", "rushed",
    "run", "ran", "forget", "forgot", "realized", "realise",
    "reach", "reached", "rain", "raining", "sleep", "overslept"
}

WEAK_VERBS = {
    "get", "got", "make", "made", "do", "did", "have", "had",
    "go", "went", "going", "take", "took", "put", "say", "said",
    "tell", "told", "think", "thought", "know", "knew",
    "ready", "let"
}

# ---------------- utils ----------------

def _expand_contractions(s: str) -> str:
    s = re.sub(r"\bI'm\b", "I am", s, flags=re.IGNORECASE)
    s = re.sub(r"\bI've\b", "I have", s, flags=re.IGNORECASE)
    s = re.sub(r"\bI'll\b", "I will", s, flags=re.IGNORECASE)
    s = re.sub(r"\bit's\b", "it is", s, flags=re.IGNORECASE)
    return s

def _clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def _split_clauses(text: str) -> List[str]:
    s = _expand_contractions(text)
    s = re.sub(r"\b(and then|then|but|so)\b", ", ", s)
    return [p.strip() for p in re.split(r"[.,!?;:]+", s) if p.strip()]

def _tokens(text: str) -> List[str]:
    return [
        t for t in _clean_text(text).split()
        if t not in STOPWORDS
        and t not in FILLERS
        and t not in DISCOURSE
        and t not in GENERIC_DROP
        and len(t) > 2
    ]

# ---------------- core logic ----------------

def _extract_phrases_from_clause(clause: str) -> List[str]:
    toks = _tokens(clause)
    if not toks:
        return []

    if len(toks) <= 3:
        return toks

    extractor = yake.KeywordExtractor(lan="en", n=3, top=6, dedupLim=0.9)
    results = extractor.extract_keywords(clause)

    phrases = []
    for phrase, _ in results:
        ptoks = _tokens(phrase)
        phrases.extend(ptoks)

    return phrases

def extract_key_phrases(transcript: str, max_k: int = 10) -> List[str]:
    """
    FINAL BEHAVIOR:
    - single-word keywords
    - story order preserved
    - last sentence guaranteed to contribute
    - no junk verbs
    """
    if not transcript.strip():
        return ["neutral"]

    full_tokens = _tokens(transcript)
    clauses = _split_clauses(transcript)

    collected: List[str] = []

    # Always extract from every clause (prevents losing ending)
    for c in clauses:
        collected.extend(_extract_phrases_from_clause(c))

    # Force emotion words if present
    for e in EMOTION_WORDS:
        if e in full_tokens and e not in collected:
            collected.append(e)

    # Remove weak verbs & dedup
    seen = set()
    clean = []
    for w in collected:
        if w in WEAK_VERBS:
            continue
        if w not in seen:
            seen.add(w)
            clean.append(w)

    # Order by story appearance
    ordered = sorted(
        clean,
        key=lambda w: full_tokens.index(w) if w in full_tokens else 10**9
    )

    return ordered[:max_k] if ordered else ["neutral"]
