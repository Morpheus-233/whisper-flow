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
    cleaned = re.sub(r'^[,\.?!;:]+\s*', '', cleaned)
    cleaned = cleaned.strip()

    # 4. Capitalize first letter
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]

    return cleaned


def format_casual_chat(text: str) -> str:
    """
    Format speech transcription for casual chat messaging:
    - Strips trailing periods, exclamation marks, and formal commas.
    - Converts formal title/sentence casing to relaxed natural lowercase chat text.
    - Retains numbers and technical tokens, but removes robotic punctuation marks.
    """
    if not text:
        return ""

    cleaned = text.strip()

    # 1. Protect URLs from punctuation removal
    urls = []
    def save_url(m):
        urls.append(m.group(0).rstrip('.!?,;:'))
        return f"___URLTOKEN_{len(urls)-1}___"
    cleaned = re.sub(r'https?://[^\s]+', save_url, cleaned)

    # 2. Remove vocal hesitation sounds
    cleaned = re.sub(r'\b(um+|uh+|er|ah|eh)\b', '', cleaned, flags=re.IGNORECASE)

    # 3. Remove immediate single-word stutters
    cleaned = re.sub(r'\b(\w+)\s+\1\b', r'\1', cleaned, flags=re.IGNORECASE)

    # 4. Replace semicolons and colons (excluding timestamps e.g. 10:30) with spaces
    cleaned = re.sub(r';', ' ', cleaned)
    cleaned = re.sub(r'(?<!\d):(?!\d)', ' ', cleaned)

    # 5. Remove formal commas (commas not surrounded by digits)
    cleaned = re.sub(r'(?<!\d),(?!\d)|(?<=\D),(?=\d)|(?<=\d),(?=\D)', ' ', cleaned)

    # 6. Remove exclamation and question marks
    cleaned = re.sub(r'[!?]+', ' ', cleaned)

    # 7. Remove quotes except contraction apostrophes (e.g. don\'t, it\'s)
    cleaned = re.sub(r'["“”«»„]', '', cleaned)
    cleaned = re.sub(r"(?<![a-zA-Z])'|'(?![a-zA-Z])", '', cleaned)

    # 8. Remove standalone/parenthetical dashes and ellipses
    cleaned = re.sub(r'\s+[-—–]+\s+', ' ', cleaned)
    cleaned = re.sub(r'\.{2,}', ' ', cleaned)

    # 9. Remove formal periods (at end of line, followed by whitespace, or preceded by whitespace)
    # Preserves decimals (3.14) and technical filenames/domains (app.py)
    cleaned = re.sub(r'\.+(?=\s|$)', '', cleaned)
    cleaned = re.sub(r'(?<=\s)\.+', '', cleaned)

    # 10. Clean up extra spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # 11. Strip any trailing punctuation
    cleaned = cleaned.rstrip('.!?,;:~`')

    # 12. Convert formal title/sentence casing to relaxed natural lowercase chat text
    # Retaining numbers and technical tokens
    tokens = cleaned.split(' ')
    new_tokens = []

    # Check if the whole string was typed in ALL CAPS
    is_all_caps = cleaned.isupper() and len([t for t in tokens if len(t) > 1]) > 1

    for token in tokens:
        if not token:
            continue
        # Check for protected URL token
        if token.startswith('___URLTOKEN_'):
            new_tokens.append(token)
        # Preserve code tokens with underscores or backticks
        elif '_' in token or '`' in token:
            new_tokens.append(token)
        # Preserve tokens with digits (e.g. v1.2, int8, 3.14, $50, 100%)
        elif any(c.isdigit() for c in token):
            new_tokens.append(token)
        # Acronyms (e.g. API, GPU, CPU, JSON) if not part of an all-caps sentence
        elif not is_all_caps and token.isupper() and len(token) > 1:
            new_tokens.append(token)
        # camelCase (e.g. PySide6, iPhone, myFunction)
        elif any(c.isupper() for c in token[1:]) and any(c.islower() for c in token):
            new_tokens.append(token)
        else:
            new_tokens.append(token.lower())

    result = ' '.join(new_tokens).strip()

    # Restore URLs
    for idx, u in enumerate(urls):
        result = result.replace(f"___URLTOKEN_{idx}___", u)

    return result

