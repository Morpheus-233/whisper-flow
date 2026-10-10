import re

def clean_speech_text(text: str) -> str:
    """
    Safe and gentle speech cleaner:
    - Removes vocal fillers (um, uh, er, ah)
    - Removes obvious immediate single-word stutters (e.g. 'the the' -> 'the', 'I I' -> 'I')
    - Preserves ALL legitimate phrases and never deletes sentences or multi-word thoughts.
    """
    if not text:
        return ""

    cleaned = text.strip()

    # 1. Remove vocal hesitation sounds only
    cleaned = re.sub(r'\b(um+|uh+|er|ah|eh)\b', '', cleaned, flags=re.IGNORECASE)

    # 2. Remove only immediate single-word stutters (e.g. 'the the' -> 'the', 'to to' -> 'to')
    # Does NOT delete multi-word phrases to ensure zero accidental speech deletion!
    cleaned = re.sub(r'\b(\w+)\s+\1\b', r'\1', cleaned, flags=re.IGNORECASE)

    # 3. Clean up spaces and punctuation formatting
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = re.sub(r'\s*([,\.?!;])', r'\1', cleaned)
    cleaned = re.sub(r'([,\.?!;])\1+', r'\1', cleaned)
    cleaned = cleaned.strip()

    # 4. Capitalize first letter
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]

    return cleaned
