"""
Bilingual Calibration & Phonetic Diff Engine for Whisper Flow.

Pure-computation, zero-side-effect module for sentence accuracy diffing,
phonetic keyword validation, dataset loading, and automated profile registration.
Zero heavy dependencies (no PySide6 or faster-whisper imports).
"""

import os
import re
import json
import difflib
from typing import List, Dict, Any, Optional


def clean_token(token: str) -> str:
    """
    Normalizes a token for matching: strips surrounding non-alphanumeric punctuation
    and converts to lowercase while preserving Devanagari characters and combining marks.
    """
    return re.sub(r"[^\w\s\u0900-\u097F]", "", token).strip().lower()


def strip_punctuation(text: str) -> str:
    """
    Strips leading and trailing punctuation from a phrase/token, preserving internal
    alphanumerics, internal hyphens, apostrophes, spaces, and Devanagari combining marks (matras).
    Example: "hoon." -> "hoon", "cooper nets," -> "cooper nets", "“PySide6!”" -> "PySide6",
    "नमस्ते!" -> "नमस्ते".
    """
    if not text:
        return ""
    words = text.split()
    cleaned_words = []
    for w in words:
        cw = re.sub(r"^[^\w\u0900-\u097F]+|[^\w\u0900-\u097F]+$", "", w)
        if cw:
            cleaned_words.append(cw)
    return " ".join(cleaned_words)


def compute_diff(
    target_text: str,
    transcribed_text: str,
    phonetic_keywords: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Computes word-level diff, accuracy score, and extracts clean phonetic misheard pairs.

    Returns:
        {
            "accuracy": float (0.0 to 100.0),
            "target": str,
            "heard": str,
            "transcribed": str,
            "diff": list[dict],
            "misheard_pairs": list[dict],
            "missing_keywords": list[str]
        }
    """
    if phonetic_keywords is None:
        phonetic_keywords = []

    target_clean = target_text.strip()
    heard_clean = transcribed_text.strip()

    # Empty text handling
    if not target_clean and not heard_clean:
        return {
            "accuracy": 100.0,
            "target": target_text,
            "heard": transcribed_text,
            "transcribed": transcribed_text,
            "diff": [],
            "misheard_pairs": [],
            "missing_keywords": []
        }
    if not target_clean or not heard_clean:
        diff_list = []
        if target_clean:
            diff_list.append({"type": "delete", "target": target_clean, "heard": ""})
        if heard_clean:
            diff_list.append({"type": "insert", "target": "", "heard": heard_clean})
        return {
            "accuracy": 0.0,
            "target": target_text,
            "heard": transcribed_text,
            "transcribed": transcribed_text,
            "diff": diff_list,
            "misheard_pairs": [],
            "missing_keywords": list(phonetic_keywords) if phonetic_keywords else []
        }

    target_tokens = target_clean.split()
    heard_tokens = heard_clean.split()

    target_norm = [clean_token(t) for t in target_tokens]
    heard_norm = [clean_token(t) for t in heard_tokens]

    # When both target and heard contain no alphanumeric or Devanagari tokens (e.g. '...' vs '???')
    has_target_content = any(t for t in target_norm)
    has_heard_content = any(h for h in heard_norm)

    if not has_target_content and not has_heard_content:
        if target_clean == heard_clean:
            return {
                "accuracy": 100.0,
                "target": target_text,
                "heard": transcribed_text,
                "transcribed": transcribed_text,
                "diff": [{"type": "equal", "target": target_clean, "heard": heard_clean}],
                "misheard_pairs": [],
                "missing_keywords": []
            }
        else:
            return {
                "accuracy": 0.0,
                "target": target_text,
                "heard": transcribed_text,
                "transcribed": transcribed_text,
                "diff": [{"type": "replace", "target": target_clean, "heard": heard_clean}],
                "misheard_pairs": [],
                "missing_keywords": list(phonetic_keywords) if phonetic_keywords else []
            }

    matcher = difflib.SequenceMatcher(lambda x: x == "", target_norm, heard_norm)
    diff = []
    misheard_pairs = []
    matches = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for ti, hj in zip(range(i1, i2), range(j1, j2)):
                if target_norm[ti] == "" and heard_norm[hj] == "" and target_tokens[ti] != heard_tokens[hj]:
                    diff.append({"type": "replace", "target": target_tokens[ti], "heard": heard_tokens[hj]})
                else:
                    diff.append({"type": "equal", "target": target_tokens[ti], "heard": heard_tokens[hj]})
                    matches += 1
        elif tag == "replace":
            t_chunk = " ".join(target_tokens[i1:i2])
            h_chunk = " ".join(heard_tokens[j1:j2])
            diff.append({"type": "replace", "target": t_chunk, "heard": h_chunk})

            # Check if 1:1 token replacement or phrase replacement
            if (i2 - i1) == (j2 - j1) and (i2 - i1) > 1:
                for ti, hj in zip(range(i1, i2), range(j1, j2)):
                    ct = strip_punctuation(target_tokens[ti])
                    ch = strip_punctuation(heard_tokens[hj]).lower()
                    if ct and ch and (ct.lower() != ch or ct != ch):
                        pair = {"heard": ch, "target": ct}
                        if pair not in misheard_pairs:
                            misheard_pairs.append(pair)
            else:
                clean_t = strip_punctuation(t_chunk)
                clean_h = strip_punctuation(h_chunk).lower()
                if clean_t and clean_h and (clean_t.lower() != clean_h or clean_t != clean_h):
                    pair = {"heard": clean_h, "target": clean_t}
                    if pair not in misheard_pairs:
                        misheard_pairs.append(pair)
        elif tag == "delete":
            t_chunk = " ".join(target_tokens[i1:i2])
            diff.append({"type": "delete", "target": t_chunk, "heard": ""})
        elif tag == "insert":
            h_chunk = " ".join(heard_tokens[j1:j2])
            diff.append({"type": "insert", "target": "", "heard": h_chunk})

    denominator = max(len(target_tokens), len(heard_tokens), 1)
    raw_acc = (matches / denominator) * 100.0
    accuracy = max(0.0, min(100.0, round(raw_acc, 1)))

    # Missing keywords check with word boundaries
    clean_transcript = " ".join(re.sub(r"[^\w\s\u0900-\u097F]", "", transcribed_text).lower().split())
    missing_keywords = []
    for kw in phonetic_keywords:
        kw_norm = " ".join(re.sub(r"[^\w\s\u0900-\u097F]", "", kw).lower().split())
        if kw_norm:
            kw_pattern = r'(?<![\w\u0900-\u097F])' + re.escape(kw_norm) + r'(?![\w\u0900-\u097F])'
            if not re.search(kw_pattern, clean_transcript):
                missing_keywords.append(kw)

    return {
        "accuracy": float(accuracy),
        "target": target_text,
        "heard": transcribed_text,
        "transcribed": transcribed_text,
        "diff": diff,
        "misheard_pairs": misheard_pairs,
        "missing_keywords": missing_keywords
    }


def load_calibration_dataset(
    json_path: str = "data/calibration_sentences.json"
) -> List[Dict[str, Any]]:
    """
    Loads all calibration sentences from JSON dataset file.
    Resolves relative paths safely and validates schema structure.
    """
    from config import get_resource_path
    target_path = json_path
    if not os.path.isabs(target_path):
        candidate = get_resource_path(json_path)
        if os.path.exists(candidate):
            target_path = candidate
        elif not os.path.exists(target_path):
            module_dir = os.path.dirname(os.path.abspath(__file__))
            candidate2 = os.path.join(module_dir, json_path)
            if os.path.exists(candidate2):
                target_path = candidate2

    with open(target_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    validated = []
    for item in data:
        if all(k in item for k in ("id", "category", "text", "phonetic_keywords")):
            validated.append({
                "id": int(item["id"]),
                "category": str(item["category"]),
                "text": str(item["text"]),
                "phonetic_keywords": list(item["phonetic_keywords"])
            })
    return validated


def auto_register_misheard_pairs(
    misheard_pairs: List[Dict[str, str]],
    profile_mgr: Any
) -> int:
    """
    Registers clean phonetic replacement pairs into VoiceProfileManager.
    Skips pairs already present with identical targets.
    Returns the count of newly added replacements.
    """
    if not misheard_pairs:
        return 0

    if profile_mgr is None:
        try:
            from voice_profile import VoiceProfileManager
            profile_mgr = VoiceProfileManager.get_instance()
        except ImportError:
            return 0

    added_count = 0
    existing = profile_mgr.get_replacements()
    existing_lower = {k.lower(): v for k, v in existing.items()}

    for pair in misheard_pairs:
        heard = strip_punctuation(pair.get("heard", "")).lower()
        target = strip_punctuation(pair.get("target", ""))
        if not heard or not target:
            continue
        if existing_lower.get(heard) != target:
            profile_mgr.add_replacement(heard, target)
            existing_lower[heard] = target
            added_count += 1

    return added_count
