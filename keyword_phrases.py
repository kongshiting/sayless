
# # keyword_phrases.py
import re
from collections import Counter
from typing import List, Tuple
import yake

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
    "supposed", "weeks", "week", "back", "speaking", "found",
    "next", "everywhere", "still", "shall", "there", "before",  # New generic drop words
    "we", "had", "such", "a"  # Added common phrases to drop
}

EMOTION_WORDS = {
    "insecure", "anxious", "stressed", "worried", "scared",
    "sad", "angry", "upset", "happy", "excited",
    "tired", "tiring", "hungry", "confused", "awkward",
    "devastated", "embarrassed"
}

COMMON_VERBS = {
    "wake", "woke", "sleep", "overslept",
    "miss", "missed", "rush", "rushed", "run", "ran", "running",
    "drop", "dropped", "spill", "spilled",
    "cry", "cried", "laugh", "laughed",
    "shower", "showered", "forget", "forgot",
    "call", "called", "reach", "reached", "realise", "realised", "realize", "realized",
    "wear", "wearing", "wore",
    "choose", "choosing", "chose",
    "argue", "argued", "disagree", "disagreement",
    "break", "broke", "broken",
    "cheat", "cheated", "scream", "screaming",
    "rain", "raining", "rained",
    "want", "wanted", "go", "home"
}

# Tunables
MIN_PHRASE_SCORE = 1.0
RARE_TOKEN_FILL_THRESHOLD = 6
DEDUP_OVERLAP = 0.55  # stricter => fewer repeats


def _expand_contractions(s: str) -> str:
    s = re.sub(r"\bI'm\b", "I am", s, flags=re.IGNORECASE)
    s = re.sub(r"\bI've\b", "I have", s, flags=re.IGNORECASE)
    s = re.sub(r"\bI'll\b", "I will", s, flags=re.IGNORECASE)
    s = re.sub(r"\bcan't\b", "cannot", s, flags=re.IGNORECASE)
    s = re.sub(r"\bdon't\b", "do not", s, flags=re.IGNORECASE)
    s = re.sub(r"\bwon't\b", "will not", s, flags=re.IGNORECASE)
    s = re.sub(r"\bit's\b", "it is", s, flags=re.IGNORECASE)
    s = re.sub(r"\bthat's\b", "that is", s, flags=re.IGNORECASE)
    return s


def _clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _normalize_tokens_for_order(text: str) -> List[str]:
    cleaned = _clean_text(_expand_contractions(text))
    return [t for t in cleaned.split() if t not in FILLERS and t not in STOPWORDS and t not in DISCOURSE]


def _split_clauses_keep_punct(raw: str) -> List[str]:
    s = _expand_contractions(raw).lower()
    s = re.sub(r"\b(and then|then|but|so)\b", ", ", s)
    parts = re.split(r"[.,!?;:]+", s)
    return [p.strip() for p in parts if p.strip()]


def _phrase_tokens(text: str) -> List[str]:
    toks = []
    for t in text.split():
        if t in FILLERS or t in STOPWORDS or t in DISCOURSE:
            continue
        if len(t) < 2:
            continue
        if t in GENERIC_DROP:
            continue
        toks.append(t)
    return toks


def _story_quality(tokens: List[str]) -> float:
    if not tokens:
        return -999.0
    score = 0.0
    if len(tokens) == 1:
        score += 0.4
    elif len(tokens) == 2:
        score += 1.2
    elif len(tokens) == 3:
        score += 1.1
    else:
        score -= 0.9

    if any(t in COMMON_VERBS or t.endswith("ed") or t.endswith("ing") for t in tokens):
        score += 0.9

    score += sum(min(len(t), 10) for t in tokens) * 0.03
    return score


def _first_pos_of_any_token(full_tokens: List[str], phrase_tokens: List[str]) -> int:
    s = set(phrase_tokens)
    for i, t in enumerate(full_tokens):
        if t in s:
            return i
    return 10**9


def _story_rule_phrases(raw: str) -> List[str]:
    s = _clean_text(_expand_contractions(raw))
    out = []

    # time-ish
    for tm in ["today", "yesterday", "after lunch", "before lunch", "next day", "tomorrow"]:
        if re.search(rf"\b{re.escape(tm)}\b", s):
            out.append(tm)

    # rain / weather beats
    if re.search(r"\brain(ing|ed)?\b", s):
        out.append("raining")
    if re.search(r"\bweather\b", s):
        out.append("weather")

    # tired / sleep / home
    if re.search(r"\btir(e|ing|ed)\b", s):
        out.append("tiring")
    if re.search(r"\bsleep\b", s):
        out.append("sleep")
    if re.search(r"\bgo home\b", s) or re.search(r"\bwanted to go home\b", s):
        out.append("go home")

    # de-dup keep order
    seen = set()
    res = []
    for x in out:
        if x not in seen and x not in GENERIC_DROP:
            seen.add(x)
            res.append(x)
    return res


def _extract_from_clause(clause_raw: str) -> List[str]:
    clause_clean = _clean_text(_expand_contractions(clause_raw))
    toks = _phrase_tokens(clause_clean)
    if not toks:
        return []

    if len(toks) <= 3:
        return [" ".join(toks)]

    extractor = yake.KeywordExtractor(lan="en", n=3, top=12, dedupLim=0.9)
    yake_ranked = extractor.extract_keywords(clause_clean)

    candidates: List[Tuple[str, float]] = []
    for phrase, yake_score in yake_ranked:
        raw_tokens = phrase.split()
        if "not" in raw_tokens and any(e in raw_tokens for e in EMOTION_WORDS):
            continue

        ptoks = _phrase_tokens(phrase)
        if not ptoks or len(ptoks) > 5:
            continue

        combined = _story_quality(ptoks) - (0.5 * yake_score)
        if combined < MIN_PHRASE_SCORE:
            continue
        candidates.append((" ".join(ptoks), combined))

    candidates.sort(key=lambda x: x[1], reverse=True)
    return [p for p, _ in candidates[:4]]


def _dedup_containment_strings(phrases: List[str]) -> List[str]:
    cleaned = [" ".join(_phrase_tokens(_clean_text(p))) for p in phrases]
    keep = []
    for i, p in enumerate(cleaned):
        if not p:
            continue
        contained = False
        for j, q in enumerate(cleaned):
            if i != j and p != q and len(q) > len(p):
                if re.search(rf"\b{re.escape(p)}\b", q):
                    contained = True
                    break
        if not contained:
            keep.append(phrases[i])
    return keep


def _dedup_keep_best(phrases: List[str]) -> List[str]:
    phrases = _dedup_containment_strings(phrases)

    kept: List[str] = []
    kept_sets: List[set] = []

    def score_phrase(p: str) -> float:
        t = _phrase_tokens(_clean_text(p))
        return _story_quality(t) + (0.15 * len(t))

    for p in phrases:
        s = set(_phrase_tokens(_clean_text(p)))
        if not s:
            continue

        merged = False
        for i, es in enumerate(kept_sets):
            overlap = len(s & es) / max(1, min(len(s), len(es)))
            if overlap < 0.3:
                continue

            if score_phrase(p) > score_phrase(kept[i]):
                kept[i] = p
                kept_sets[i] = s
            merged = True
            break

        if not merged:
            kept.append(p)
            kept_sets.append(s)

    token_sets = [(p, set(_phrase_tokens(_clean_text(p)))) for p in kept]
    final = []
    for i, (p, s) in enumerate(token_sets):
        if len(s) == 1:
            tok = next(iter(s))
            if any((i != j and tok in t and len(t) >= 2) for j, (_, t) in enumerate(token_sets)):
                continue
        final.append(p)

    return final

def _rare_tokens(text: str) -> List[str]:
    toks = _phrase_tokens(_clean_text(_expand_contractions(text)))
    counts = Counter(toks)
    out = []
    for t, c in counts.items():
        if c == 1 and len(t) >= 5 and t not in GENERIC_DROP:
            out.append(t)
    return out

def _phrase_length_filter(phrase: str) -> bool:
    return len(phrase) > 2  # Example length filter

def extract_key_phrases(transcript: str, max_k: int = 10) -> List[str]:
    if not transcript or not transcript.strip():
        return ["neutral"]

    full_tokens = _normalize_tokens_for_order(transcript)

    collected: List[str] = []
    collected.extend(_story_rule_phrases(transcript))

    clauses = _split_clauses_keep_punct(transcript)
    for c in clauses:
        collected.extend(_extract_from_clause(c))

    if not collected:
        return ["neutral"]

    collected = _dedup_keep_best(collected)

    # Force-keep emotion words (clean)
    full_clean = _clean_text(_expand_contractions(transcript))
    present_emotions = [w for w in EMOTION_WORDS if re.search(rf"\b{re.escape(w)}\b", full_clean)]
    for w in present_emotions:
        if w not in collected:
            collected.insert(0, w)

    collected = _dedup_keep_best(collected)

    # Rare tokens only if lacking beats
    if len(collected) < RARE_TOKEN_FILL_THRESHOLD:
        for rt in _rare_tokens(transcript):
            if rt not in collected:
                collected.append(rt)
        collected = _dedup_keep_best(collected)

    # Order by appearance
    collected.sort(key=lambda p: _first_pos_of_any_token(full_tokens, _phrase_tokens(_clean_text(p))))

    # Apply the phrase length filter
    collected = [p for p in collected if _phrase_length_filter(p)]

    return collected[:max_k] if collected else ["neutral"]
    
    
    
    # # Story-beat keyword extraction for speech transcripts (no APIs)
# # YAKE + small story rules + stronger dedup (reduces repetition).
# # Returns up to max_k beats, often fewer.

# import re
# from collections import Counter
# from typing import List, Tuple
# import yake

# FILLERS = {
#     "uh", "um", "eh", "lah", "leh", "lor", "sia", "bro", "bruh",
#     "omg", "ya", "yah", "okay", "ok"
# }

# DISCOURSE = {
#     "basically", "recently", "actually", "literally", "anyway", "anyways",
#     "like", "just", "mean", "alright", "right", "kinda", "kind", "sorta", "sort",
#     "so", "well"
# }

# STOPWORDS = {
#     "i", "me", "my", "mine", "we", "our", "you", "your", "he", "she", "they", "it",
#     "a", "an", "the", "and", "or", "but", "because", "then",
#     "is", "am", "are", "was", "were", "be", "been", "being",
#     "to", "of", "in", "on", "at", "for", "with", "as", "that", "this",
#     "really", "very", "today", "now", "later",
#     "ll", "im", "ive", "dont", "cant", "wont",
#     "not"
# }

# GENERIC_DROP = {
#     "day", "again", "whole", "time", "thing", "stuff",
#     "supposed", "weeks", "week", "back", "speaking", "found",
#     # common low-signal transcript words
#     "somewhere"
# }

# EMOTION_WORDS = {
#     "insecure", "anxious", "stressed", "worried", "scared",
#     "sad", "angry", "upset", "happy", "excited",
#     "tired", "tiring", "hungry", "confused", "awkward",
#     "devastated", "embarrassed"
# }

# COMMON_VERBS = {
#     "wake", "woke", "sleep", "overslept",
#     "miss", "missed", "rush", "rushed", "run", "ran", "running",
#     "drop", "dropped", "spill", "spilled",
#     "cry", "cried", "laugh", "laughed",
#     "shower", "showered", "forget", "forgot",
#     "call", "called", "reach", "reached", "realise", "realised", "realize", "realized",
#     "wear", "wearing", "wore",
#     "choose", "choosing", "chose",
#     "argue", "argued", "disagree", "disagreement",
#     "break", "broke", "broken",
#     "cheat", "cheated", "scream", "screaming",
#     "rain", "raining", "rained",
#     "want", "wanted", "go", "home"
# }

# # Tunables
# MIN_PHRASE_SCORE = 1.0
# RARE_TOKEN_FILL_THRESHOLD = 6
# DEDUP_OVERLAP = 0.55  # stricter => fewer repeats


# def _expand_contractions(s: str) -> str:
#     s = re.sub(r"\bI'm\b", "I am", s, flags=re.IGNORECASE)
#     s = re.sub(r"\bI've\b", "I have", s, flags=re.IGNORECASE)
#     s = re.sub(r"\bI'll\b", "I will", s, flags=re.IGNORECASE)
#     s = re.sub(r"\bcan't\b", "cannot", s, flags=re.IGNORECASE)
#     s = re.sub(r"\bdon't\b", "do not", s, flags=re.IGNORECASE)
#     s = re.sub(r"\bwon't\b", "will not", s, flags=re.IGNORECASE)
#     s = re.sub(r"\bit's\b", "it is", s, flags=re.IGNORECASE)
#     s = re.sub(r"\bthat's\b", "that is", s, flags=re.IGNORECASE)
#     return s


# def _clean_text(text: str) -> str:
#     text = text.lower()
#     text = re.sub(r"[^a-z0-9\s]", " ", text)
#     text = re.sub(r"\s+", " ", text).strip()
#     return text


# def _normalize_tokens_for_order(text: str) -> List[str]:
#     cleaned = _clean_text(_expand_contractions(text))
#     return [t for t in cleaned.split() if t not in FILLERS and t not in STOPWORDS and t not in DISCOURSE]


# def _split_clauses_keep_punct(raw: str) -> List[str]:
#     s = _expand_contractions(raw).lower()
#     s = re.sub(r"\b(and then|then|but|so)\b", ", ", s)
#     parts = re.split(r"[.,!?;:]+", s)
#     return [p.strip() for p in parts if p.strip()]


# def _phrase_tokens(text: str) -> List[str]:
#     toks = []
#     for t in text.split():
#         if t in FILLERS or t in STOPWORDS or t in DISCOURSE:
#             continue
#         if len(t) < 2:
#             continue
#         if t in GENERIC_DROP:
#             continue
#         toks.append(t)
#     return toks


# def _story_quality(tokens: List[str]) -> float:
#     if not tokens:
#         return -999.0
#     score = 0.0
#     if len(tokens) == 1:
#         score += 0.4
#     elif len(tokens) == 2:
#         score += 1.2
#     elif len(tokens) == 3:
#         score += 1.1
#     else:
#         score -= 0.9

#     if any(t in COMMON_VERBS or t.endswith("ed") or t.endswith("ing") for t in tokens):
#         score += 0.9

#     score += sum(min(len(t), 10) for t in tokens) * 0.03
#     return score


# def _first_pos_of_any_token(full_tokens: List[str], phrase_tokens: List[str]) -> int:
#     s = set(phrase_tokens)
#     for i, t in enumerate(full_tokens):
#         if t in s:
#             return i
#     return 10**9


# def _story_rule_phrases(raw: str) -> List[str]:
#     s = _clean_text(_expand_contractions(raw))
#     out = []

#     # time-ish
#     for tm in ["today", "yesterday", "after lunch", "before lunch", "next day", "tomorrow"]:
#         if re.search(rf"\b{re.escape(tm)}\b", s):
#             out.append(tm)

#     # rain / weather beats
#     if re.search(r"\brain(ing|ed)?\b", s):
#         out.append("raining")
#     if re.search(r"\bweather\b", s):
#         out.append("weather")

#     # tired / sleep / home
#     if re.search(r"\btir(e|ing|ed)\b", s):
#         out.append("tiring")
#     if re.search(r"\bsleep\b", s):
#         out.append("sleep")
#     if re.search(r"\bgo home\b", s) or re.search(r"\bwanted to go home\b", s):
#         out.append("go home")

#     # de-dup keep order
#     seen = set()
#     res = []
#     for x in out:
#         if x not in seen and x not in GENERIC_DROP:
#             seen.add(x)
#             res.append(x)
#     return res


# def _extract_from_clause(clause_raw: str) -> List[str]:
#     clause_clean = _clean_text(_expand_contractions(clause_raw))
#     toks = _phrase_tokens(clause_clean)
#     if not toks:
#         return []

#     if len(toks) <= 3:
#         return [" ".join(toks)]

#     extractor = yake.KeywordExtractor(lan="en", n=3, top=12, dedupLim=0.9)
#     yake_ranked = extractor.extract_keywords(clause_clean)

#     candidates: List[Tuple[str, float]] = []
#     for phrase, yake_score in yake_ranked:
#         raw_tokens = phrase.split()
#         if "not" in raw_tokens and any(e in raw_tokens for e in EMOTION_WORDS):
#             continue

#         ptoks = _phrase_tokens(phrase)
#         if not ptoks or len(ptoks) > 5:
#             continue

#         combined = _story_quality(ptoks) - (0.5 * yake_score)
#         if combined < MIN_PHRASE_SCORE:
#             continue
#         candidates.append((" ".join(ptoks), combined))

#     candidates.sort(key=lambda x: x[1], reverse=True)
#     return [p for p, _ in candidates[:4]]


# def _dedup_containment_strings(phrases: List[str]) -> List[str]:
#     """
#     Drop phrase P if its string is contained in another phrase string Q (token boundary aware).
#     e.g. "start raining" is contained in "raining after lunch" (shares core) -> later overlap handles,
#     but string containment also kills obvious ones.
#     """
#     cleaned = [" ".join(_phrase_tokens(_clean_text(p))) for p in phrases]
#     keep = []
#     for i, p in enumerate(cleaned):
#         if not p:
#             continue
#         contained = False
#         for j, q in enumerate(cleaned):
#             if i != j and p != q and len(q) > len(p):
#                 if re.search(rf"\b{re.escape(p)}\b", q):
#                     contained = True
#                     break
#         if not contained:
#             keep.append(phrases[i])
#     return keep

# def _dedup_keep_best(phrases: List[str]) -> List[str]:
#     # 1) string containment first
#     phrases = _dedup_containment_strings(phrases)

#     kept: List[str] = []
#     kept_sets: List[set] = []

#     def score_phrase(p: str) -> float:
#         t = _phrase_tokens(_clean_text(p))
#         return _story_quality(t) + (0.15 * len(t))

#     for p in phrases:
#         s = set(_phrase_tokens(_clean_text(p)))
#         if not s:
#             continue

#         merged = False
#         for i, es in enumerate(kept_sets):
#             overlap = len(s & es) / max(1, min(len(s), len(es)))
#             # A stricter condition for overlap to promote more unique phrases
#             if overlap < 0.3:
#                 continue

#             # keep the better one based on score
#             if score_phrase(p) > score_phrase(kept[i]):
#                 kept[i] = p
#                 kept_sets[i] = s
#             merged = True
#             break

#         if not merged:
#             kept.append(p)
#             kept_sets.append(s)

#     # Final pass to eliminate single-word beats if a longer beat contains them
#     token_sets = [(p, set(_phrase_tokens(_clean_text(p)))) for p in kept]
#     final = []
#     for i, (p, s) in enumerate(token_sets):
#         if len(s) == 1:
#             tok = next(iter(s))
#             if any((i != j and tok in t and len(t) >= 2) for j, (_, t) in enumerate(token_sets)):
#                 continue
#         final.append(p)

#     return final

# def _rare_tokens(text: str) -> List[str]:
#     toks = _phrase_tokens(_clean_text(_expand_contractions(text)))
#     counts = Counter(toks)
#     out = []
#     for t, c in counts.items():
#         if c == 1 and len(t) >= 5 and t not in GENERIC_DROP:
#             out.append(t)
#     return out


# def extract_key_phrases(transcript: str, max_k: int = 10) -> List[str]:
#     if not transcript or not transcript.strip():
#         return ["neutral"]

#     full_tokens = _normalize_tokens_for_order(transcript)

#     collected: List[str] = []
#     collected.extend(_story_rule_phrases(transcript))

#     clauses = _split_clauses_keep_punct(transcript)
#     for c in clauses:
#         collected.extend(_extract_from_clause(c))

#     if not collected:
#         return ["neutral"]

#     collected = _dedup_keep_best(collected)

#     # Force-keep emotion words (clean)
#     full_clean = _clean_text(_expand_contractions(transcript))
#     present_emotions = [w for w in EMOTION_WORDS if re.search(rf"\b{re.escape(w)}\b", full_clean)]
#     for w in present_emotions:
#         if w not in collected:
#             collected.insert(0, w)

#     collected = _dedup_keep_best(collected)

#     # Rare tokens only if lacking beats
#     if len(collected) < RARE_TOKEN_FILL_THRESHOLD:
#         for rt in _rare_tokens(transcript):
#             if rt not in collected:
#                 collected.append(rt)
#         collected = _dedup_keep_best(collected)

#     # Order by appearance
#     collected.sort(key=lambda p: _first_pos_of_any_token(full_tokens, _phrase_tokens(_clean_text(p))))

#     return collected[:max_k] if collected else ["neutral"]



