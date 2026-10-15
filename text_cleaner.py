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


def to_camel_case(words: list[str]) -> str:
    """Converts a list of word tokens to camelCase."""
    tokens = [re.sub(r'[^a-zA-Z0-9]', '', w) for w in words]
    tokens = [t for t in tokens if t]
    if not tokens:
        return ""
    return tokens[0].lower() + "".join(t.capitalize() for t in tokens[1:])


def to_snake_case(words: list[str]) -> str:
    """Converts a list of word tokens to snake_case."""
    tokens = [re.sub(r'[^a-zA-Z0-9]', '', w).lower() for w in words]
    tokens = [t for t in tokens if t]
    return "_".join(tokens)


def to_kebab_case(words: list[str]) -> str:
    """Converts a list of word tokens to kebab-case."""
    tokens = [re.sub(r'[^a-zA-Z0-9]', '', w).lower() for w in words]
    tokens = [t for t in tokens if t]
    return "-".join(tokens)


def to_pascal_case(words: list[str]) -> str:
    """Converts a list of word tokens to PascalCase."""
    tokens = [re.sub(r'[^a-zA-Z0-9]', '', w).capitalize() for w in words]
    tokens = [t for t in tokens if t]
    return "".join(tokens)


def to_constant_case(words: list[str]) -> str:
    """Converts a list of word tokens to CONSTANT_CASE."""
    tokens = [re.sub(r'[^a-zA-Z0-9]', '', w).upper() for w in words]
    tokens = [t for t in tokens if t]
    return "_".join(tokens)


def format_developer_mode(text: str) -> str:
    """
    Transforms spoken programming commands, casing formats, and operators into code tokens:
    - camelCase: "camel case user profile manager" -> "userProfileManager"
    - snake_case: "snake case get current user" -> "get_current_user"
    - kebab-case: "kebab case main container layout" -> "main-container-layout"
    - PascalCase: "pascal case voice profile manager" -> "VoiceProfileManager"
    - CONSTANT_CASE: "constant case max retry attempts" -> "MAX_RETRY_ATTEMPTS"
    - Operators: "arrow function" -> "=>", "double equals" -> "==", "triple equals" -> "===",
                 "not equals" -> "!=", "greater than or equal to" -> ">=", "less than or equal to" -> "<=",
                 "plus equals" -> "+=", "minus equals" -> "-=", "times equals" -> "*=", "divide equals" -> "/=",
                 "double plus" -> "++", "double minus" -> "--", "logical and" -> "&&", "logical or" -> "||",
                 "nullish coalescing" -> "??", "optional chaining" -> "?.", "walrus operator" -> ":="
    - Delimiters: "open paren" -> "(", "close paren" -> ")", "empty parens" -> "()",
                  "open bracket" -> "[", "close bracket" -> "]", "empty brackets" -> "[]",
                  "open brace" -> "{", "close brace" -> "}", "empty braces" -> "{}",
                  "semicolon" -> ";", "backtick" -> "`"
    - Files: "dot env" -> ".env", "dot gitignore" -> ".gitignore", "dot json" -> ".json",
             "dot js" -> ".js", "dot ts" -> ".ts", "dot py" -> ".py", etc.
    - Console: "console dot log" -> "console.log", "console dot error" -> "console.error"
    """
    if not text:
        return ""

    cleaned = text.strip()

    # 1. Base clean: remove hesitation fillers
    cleaned = re.sub(r'\b(um+|uh+|er|ah|eh)\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(\w+)\s+\1\b', r'\1', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # 2. Console & Logging (run before file extensions to protect console dot log)
    cleaned = re.sub(r'\bconsole\s+dot\s+log\b', 'console.log', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bconsole\s+dot\s+error\b', 'console.error', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bconsole\s+dot\s+warn\b', 'console.warn', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bconsole\s+dot\s+info\b', 'console.info', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bconsole\s+dot\s+debug\b', 'console.debug', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bconsole\s+dot\s+table\b', 'console.table', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bprint\s+statement\b', 'print()', cleaned, flags=re.IGNORECASE)

    # 3. Files & Extensions
    cleaned = re.sub(r'\bdot\s+env\b', '.env', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bdot\s+gitignore\b', '.gitignore', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bdot\s+dockerignore\b', '.dockerignore', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bdot\s+eslintrc\b', '.eslintrc', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bdot\s+prettierrc\b', '.prettierrc', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bdot\s+github\b', '.github', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bdot\s+venv\b', '.venv', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bdot\s+config\b', '.config', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bdot\s+json\b', '.json', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bdot\s+ya?ml\b', '.yaml', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bdot\s+jsx?\b', lambda m: m.group(0).lower().replace('dot ', '.'), cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bdot\s+tsx?\b', lambda m: m.group(0).lower().replace('dot ', '.'), cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bdot\s+py\b', '.py', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bdot\s+html\b', '.html', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bdot\s+css\b', '.css', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bdot\s+scss\b', '.scss', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bdot\s+md\b', '.md', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bdot\s+txt\b', '.txt', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bdot\s+log\b', '.log', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bdot\s+sql\b', '.sql', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bdot\s+sh\b', '.sh', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bdot\s+bat\b', '.bat', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bdot\s+ps1\b', '.ps1', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bdot\s+exe\b', '.exe', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bdot\s+toml\b', '.toml', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bdot\s+xml\b', '.xml', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bdot\s+csv\b', '.csv', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bdot\s+cpp\b', '.cpp', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bdot\s+rs\b', '.rs', cleaned, flags=re.IGNORECASE)

    # 4. Spoken casing commands (parse and convert before operator tokenization so casing boundaries are sharp)
    casing_pattern = re.compile(
        r'\b(?:(?:in|as)\s+)?(camel\s*case|snake\s*case|kebab\s*case|pascal\s*case|constant\s*case|screaming\s+snake\s*case|upper\s+snake\s*case)\s+',
        re.IGNORECASE
    )
    stop_pattern = re.compile(
        r'(?:[,\.\?!;:\(\)\[\]\{\}\"\'=\+\-\*/<>&\|\^~`]|'
        r'\b(?:arrow\s+function|fat\s+arrow|thin\s+arrow|skinny\s+arrow|'
        r'strictly\s+equals?|triple\s+equals?|three\s+equals?|strict\s+equals?|'
        r'strict\s+not\s+equals?|exclamation\s+double\s+equals?|'
        r'double\s+equals?|two\s+equals?|equals?\s+equals?|'
        r'not\s+equals?|not\s+equal\s+to|exclamation\s+equals?|'
        r'greater\s+than\s+or\s+equal\s+to|greater\s+than\s+equals?|'
        r'less\s+than\s+or\s+equal\s+to|less\s+than\s+equals?|'
        r'plus\s+equals?|minus\s+equals?|times\s+equals?|multiply\s+equals?|star\s+equals?|divide\s+equals?|slash\s+equals?|'
        r'double\s+plus|plus\s+plus|double\s+minus|minus\s+minus|'
        r'logical\s+and|double\s+ampersand|and\s+and|logical\s+or|double\s+pipe|or\s+or|'
        r'nullish\s+coalescing|double\s+question\s+mark|optional\s+chaining|question\s+dot|'
        r'walrus\s+operator|colon\s+equals?|'
        r'empty\s+parens?|empty\s+parentheses|open\s+close\s+parens?|'
        r'open\s+parens?|open\s+parenthesis|left\s+paren|close\s+parens?|close\s+parenthesis|right\s+paren|'
        r'empty\s+brackets?|empty\s+square\s+brackets?|open\s+close\s+brackets?|'
        r'open\s+brackets?|open\s+square\s+bracket|left\s+bracket|close\s+brackets?|close\s+square\s+bracket|right\s+bracket|'
        r'empty\s+braces?|empty\s+curly\s+braces?|open\s+close\s+braces?|'
        r'open\s+braces?|open\s+curly\s+brace|open\s+curly|left\s+brace|close\s+braces?|close\s+curly\s+brace|close\s+curly|right\s+brace|'
        r'semi\s*colon|back\s*ticks?|double\s+quotes?|single\s+quotes?|'
        r'dot\s+(?:env|gitignore|json|ya?ml|js|ts|py|html|css|md|txt|log)|'
        r'(?:and|or|then)\s+(?:camel|snake|kebab|pascal|constant|screaming|upper)|'
        r'(?:equals?|return|function|class|const|let|var|import|export|from))\b|$)',
        re.IGNORECASE
    )

    pos = 0
    cased_parts = []
    while pos < len(cleaned):
        m = casing_pattern.search(cleaned, pos)
        if not m:
            cased_parts.append(cleaned[pos:])
            break
        cased_parts.append(cleaned[pos:m.start()])
        case_raw = m.group(1).lower().replace(' ', '')
        words_start = m.end()

        stop_m = stop_pattern.search(cleaned, words_start)
        if stop_m and stop_m.start() > words_start:
            words_chunk = cleaned[words_start:stop_m.start()]
            pos = stop_m.start()
        elif stop_m and stop_m.start() == words_start:
            words_chunk = ''
            pos = words_start
        else:
            words_chunk = cleaned[words_start:]
            pos = len(cleaned)

        words = [w.strip() for w in words_chunk.split() if w.strip()]
        if 'camel' in case_raw:
            cased = to_camel_case(words)
        elif 'constant' in case_raw or 'screaming' in case_raw or 'upper' in case_raw:
            cased = to_constant_case(words)
        elif 'snake' in case_raw:
            cased = to_snake_case(words)
        elif 'kebab' in case_raw:
            cased = to_kebab_case(words)
        elif 'pascal' in case_raw:
            cased = to_pascal_case(words)
        else:
            cased = ' '.join(words)

        # Ensure space before cased if previous part did not end with whitespace or opening delimiter
        if cased and cased_parts and cased_parts[-1] and not cased_parts[-1][-1].isspace() and cased_parts[-1][-1] not in '([{`"\'=':
            cased_parts.append(' ')
        cased_parts.append(cased)
        # Ensure space after cased if followed by a word character
        if cased and pos < len(cleaned) and cleaned[pos].isalnum():
            cased_parts.append(' ')

    cleaned = ''.join(cased_parts)

    # 5. Operators
    cleaned = re.sub(r'\b(?:arrow\s+function|fat\s+arrow)\b', '=>', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:thin\s+arrow|skinny\s+arrow)\b', '->', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:strictly\s+equals?|triple\s+equals?|three\s+equals?|strict\s+equals?)\b', '===', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:strict\s+not\s+equals?|exclamation\s+double\s+equals?)\b', '!==', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:double\s+equals?|two\s+equals?|equals?\s+equals?)\b', '==', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:not\s+equals?|not\s+equal\s+to|exclamation\s+equals?)\b', '!=', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:greater\s+than\s+or\s+equal\s+to|greater\s+than\s+equals?)\b', '>=', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:less\s+than\s+or\s+equal\s+to|less\s+than\s+equals?)\b', '<=', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bplus\s+equals?\b', '+=', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bminus\s+equals?\b', '-=', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:times\s+equals?|multiply\s+equals?|star\s+equals?)\b', '*=', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:divide\s+equals?|slash\s+equals?)\b', '/=', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:colon\s+equals?|walrus\s+operator)\b', ':=', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:double\s+plus|plus\s+plus)\b', '++', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:double\s+minus|minus\s+minus)\b', '--', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:logical\s+and|double\s+ampersand|and\s+and)\b', '&&', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:logical\s+or|double\s+pipe|or\s+or)\b', '||', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:nullish\s+coalescing|double\s+question\s+mark)\b', '??', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:optional\s+chaining|question\s+dot)\b', '?.', cleaned, flags=re.IGNORECASE)

    # 6. Delimiters
    cleaned = re.sub(r'\b(?:empty\s+parens?|empty\s+parentheses|open\s+close\s+parens?)\b', '()', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:open\s+parens?|open\s+parenthesis|left\s+paren)\b', '(', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:close\s+parens?|close\s+parenthesis|right\s+paren)\b', ')', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:empty\s+brackets?|empty\s+square\s+brackets?|open\s+close\s+brackets?)\b', '[]', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:open\s+brackets?|open\s+square\s+bracket|left\s+bracket)\b', '[', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:close\s+brackets?|close\s+square\s+bracket|right\s+bracket)\b', ']', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:empty\s+braces?|empty\s+curly\s+braces?|open\s+close\s+braces?)\b', '{}', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:open\s+braces?|open\s+curly\s+brace|open\s+curly|left\s+brace)\b', '{', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:close\s+braces?|close\s+curly\s+brace|close\s+curly|right\s+brace)\b', '}', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:semi\s*colon)\b', ';', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:back\s*ticks?)\b', '`', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:double\s+quotes?)\b', '"', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:single\s+quotes?)\b', "'", cleaned, flags=re.IGNORECASE)

    # 7. Common spoken keywords
    cleaned = re.sub(r'\b(?:try\s+catch)\b', 'try/catch', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:async\s+await)\b', 'async/await', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:type\s+of)\b', 'typeof', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:instance\s+of)\b', 'instanceof', cleaned, flags=re.IGNORECASE)

    # 8. Spacing cleanup around delimiters and operators
    cleaned = re.sub(r'\(\s+', '(', cleaned)
    cleaned = re.sub(r'\s+\)', ')', cleaned)
    cleaned = re.sub(r'\[\s+', '[', cleaned)
    cleaned = re.sub(r'\s+\]', ']', cleaned)
    cleaned = re.sub(r'\{\s+', '{', cleaned)
    cleaned = re.sub(r'\s+\}', '}', cleaned)
    cleaned = re.sub(r'\s+;', ';', cleaned)
    cleaned = re.sub(r'\s+,', ',', cleaned)
    cleaned = re.sub(r'(\b\w+)\s+\(\)', r'\1()', cleaned)
    cleaned = re.sub(r'(\b\w+)\s+\(', r'\1(', cleaned)

    # Clean double spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def format_custom_persona(text: str, rules = None) -> str:
    """
    Rule-based custom persona formatting that applies user-defined tone rules
    instantly on CPU with 0 MB VRAM and 0ms GPU latency.
    """
    if not text:
        return ""

    cleaned = clean_speech_text(text)

    # 1. Resolve rules
    if rules is None:
        try:
            from voice_profile import VoiceProfileManager
            prof = VoiceProfileManager.get_instance().profile
            rules = (
                prof.get("persona_rules")
                or prof.get("custom_persona_rules")
                or prof.get("custom_persona_prompt", "")
            )
        except Exception:
            rules = {}

    rule_dict = {}
    if isinstance(rules, str):
        prompt_lower = rules.lower()
        if "concise" in prompt_lower or "punchy" in prompt_lower or "clear" in prompt_lower:
            rule_dict["concise"] = True
        if "bullet" in prompt_lower or "list" in prompt_lower:
            rule_dict["bullet_points"] = True
        if "numbered" in prompt_lower:
            rule_dict["numbered_list"] = True
        if "lowercase" in prompt_lower:
            rule_dict["case"] = "lower"
        elif "uppercase" in prompt_lower or "shout" in prompt_lower:
            rule_dict["case"] = "upper"
        if "quote" in prompt_lower:
            rule_dict["prefix"] = "> "
        if "strip punctuation" in prompt_lower or "no punctuation" in prompt_lower:
            rule_dict["strip_punctuation"] = True
    elif isinstance(rules, dict):
        rule_dict = rules.copy()

    # 2. Fluff and conversational padding removal for concise/punchy tone
    if rule_dict.get("concise") or rule_dict.get("strip_fillers") or rule_dict.get("tone") == "concise":
        fluff_patterns = [
            r'\b(?:as\s+a\s+matter\s+of\s+fact|at\s+the\s+end\s+of\s+the\s+day|for\s+what\s+it\'?s\s+worth)\b[,]?\s*',
            r'\b(?:to\s+be\s+honest|honestly\s+speaking|in\s+my\s+opinion)\b[,]?\s*',
            r'\b(?:you\s+know|i\s+mean|sort\s+of|kind\s+of|pretty\s+much)\b[,]?\s*',
            r'\b(?:basically|literally|actually|honestly|obviously)\b[,]?\s*'
        ]
        for pat in fluff_patterns:
            cleaned = re.sub(pat, '', cleaned, flags=re.IGNORECASE)
        # Clean double spaces and stray leading punctuation
        cleaned = re.sub(r'^[,\.?!;:]+\s*', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        if cleaned:
            cleaned = cleaned[0].upper() + cleaned[1:]

    # 3. Custom replacements
    reps = rule_dict.get("replacements") or rule_dict.get("custom_replacements")
    if reps and isinstance(reps, dict):
        for k, v in reps.items():
            cleaned = re.sub(r'\b' + re.escape(k) + r'\b', v, cleaned, flags=re.IGNORECASE)

    # 4. Punctuation handling
    if rule_dict.get("strip_punctuation") or rule_dict.get("strip_trailing_punct"):
        cleaned = cleaned.rstrip('.!?,;:')

    # 5. Bullet / Numbered lists
    if rule_dict.get("bullet_points") or rule_dict.get("bullet") or rule_dict.get("tone") == "bullet":
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', cleaned) if s.strip()]
        if len(sentences) > 1:
            cleaned = "\n".join(f"- {s}" for s in sentences)
        elif sentences:
            cleaned = f"- {sentences[0]}"
    elif rule_dict.get("numbered_list") or rule_dict.get("numbered") or rule_dict.get("tone") == "numbered":
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', cleaned) if s.strip()]
        if len(sentences) > 1:
            cleaned = "\n".join(f"{i+1}. {s}" for i, s in enumerate(sentences))
        elif sentences:
            cleaned = f"1. {sentences[0]}"

    # 6. Case adjustments
    case = rule_dict.get("case") or rule_dict.get("casing")
    if case:
        case = case.lower()
        if case in ("lower", "lowercase"):
            cleaned = cleaned.lower()
        elif case in ("upper", "uppercase"):
            cleaned = cleaned.upper()
        elif case in ("title", "titlecase"):
            cleaned = cleaned.title()

    # 7. Prefix and Suffix
    prefix = rule_dict.get("prefix", "")
    suffix = rule_dict.get("suffix", "")
    if prefix:
        cleaned = prefix + cleaned
    if suffix:
        cleaned = cleaned + suffix

    return cleaned

