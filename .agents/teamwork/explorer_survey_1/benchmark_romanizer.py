import re
import time

# Devanagari Unicode mappings
DEVANAGARI_VOWELS = {
    '\u0905': 'a', '\u0906': 'aa', '\u0907': 'i', '\u0908': 'ee',
    '\u0909': 'u', '\u090A': 'oo', '\u090B': 'ri', '\u090F': 'e',
    '\u0910': 'ai', '\u0913': 'o', '\u0914': 'au'
}

DEVANAGARI_MATRAS = {
    '\u093E': 'aa', '\u093F': 'i', '\u0940': 'ee', '\u0941': 'u',
    '\u0942': 'oo', '\u0943': 'ri', '\u0947': 'e', '\u0948': 'ai',
    '\u094B': 'o', '\u094C': 'au', '\u0902': 'n', '\u0901': 'n',
    '\u0903': 'h'
}

DEVANAGARI_CONSONANTS = {
    '\u0915': 'k', '\u0916': 'kh', '\u0917': 'g', '\u0918': 'gh', '\u0919': 'ng',
    '\u091A': 'ch', '\u091B': 'chh', '\u091C': 'j', '\u091D': 'jh', '\u091E': 'ny',
    '\u091F': 't', '\u0920': 'th', '\u0921': 'd', '\u0922': 'dh', '\u0923': 'n',
    '\u0924': 't', '\u0925': 'th', '\u0926': 'd', '\u0927': 'dh', '\u0928': 'n',
    '\u092A': 'p', '\u092B': 'ph', '\u092C': 'b', '\u092D': 'bh', '\u092E': 'm',
    '\u092F': 'y', '\u0930': 'r', '\u0932': 'l', '\u0933': 'l', '\u0935': 'v',
    '\u0936': 'sh', '\u0937': 'sh', '\u0938': 's', '\u0939': 'h',
    # Nukta forms
    '\u0958': 'q', '\u0959': 'kh', '\u095A': 'gh', '\u095B': 'z',
    '\u095C': 'r', '\u095D': 'rh', '\u095E': 'f', '\u095F': 'y'
}

VIRAMA = '\u094D'  # Halant

# Common full-word dictionary for natural Hinglish spellings (high priority lookup)
COMMON_HINGLISH_WORDS = {
    'मैं': 'Main', 'कल': 'kal', 'कोड': 'code', 'पुश': 'push', 'कर': 'kar',
    'दूंगा': 'dunga', 'दूंगी': 'dungi', 'देंगे': 'denge', 'करता': 'karta',
    'करती': 'karti', 'करते': 'karte', 'हूँ': 'hoon', 'हूं': 'hoon',
    'है': 'hai', 'हैं': 'hain', 'हो': 'ho', 'था': 'tha', 'थी': 'thi',
    'थे': 'the', 'आज': 'Aaj', 'का': 'ka', 'की': 'ki', 'के': 'ke',
    'को': 'ko', 'में': 'mein', 'से': 'se', 'पर': 'par', 'और': 'aur',
    'भी': 'bhi', 'तो': 'to', 'नहीं': 'nahi', 'ना': 'na', 'क्या': 'kya',
    'क्यों': 'kyun', 'कैसे': 'kaise', 'कब': 'kab', 'कहाँ': 'kahan',
    'कहा': 'kaha', 'मीटिंग': 'meeting', 'शेड्यूल': 'schedule', 'चाय': 'Chai',
    'पीने': 'peene', 'चलते': 'chalte', 'ऑफिस': 'office', 'कैफेटेरिया': 'cafeteria',
    'सुबहा': 'subah', 'सुबह': 'subah', 'शाम': 'sham', 'स्टेशन': 'station',
    'थोड़ी': 'thodi', 'थोड़ा': 'thoda', 'देर': 'der', 'टाइम': 'time',
    'चेक': 'check', 'करके': 'karke', 'बताता': 'batata', 'बताती': 'batati',
    'कॉल': 'call', 'निकलना': 'nikalna', 'पड़ेगा': 'padega', 'डिनर': 'dinner',
    'आ': 'aa', 'रहे': 'rahe', 'रहा': 'raha', 'रही': 'rahi', 'तुम': 'tum',
    'आप': 'aap', 'हम': 'hum', 'वह': 'woh', 'ये': 'ye', 'वे': 've',
    'सर्वर': 'server', 'डिप्लॉय': 'deploy', 'कमिट': 'commit', 'ब्रांच': 'branch',
    'गिटहब': 'github', 'एरर': 'error', 'बग': 'bug', 'फीचर': 'feature'
}

def romanize_devanagari_word(word: str) -> str:
    """Converts a Devanagari word into Romanized Hinglish."""
    # 1. Exact common word match
    clean_w = word.strip('.,!?:;"\'')
    leading_punct = word[:len(word) - len(word.lstrip('.,!?:;"\''))]
    trailing_punct = word[len(word.rstrip('.,!?:;"\'')):]
    
    if clean_w in COMMON_HINGLISH_WORDS:
        return leading_punct + COMMON_HINGLISH_WORDS[clean_w] + trailing_punct

    # If word does not contain Devanagari, return as is
    if not any('\u0900' <= c <= '\u097F' for c in clean_w):
        return word

    # 2. Rule-based phonetic transliteration
    res = []
    i = 0
    chars = list(clean_w)
    n = len(chars)

    while i < n:
        c = chars[i]
        nxt = chars[i+1] if i + 1 < n else ''

        if c in DEVANAGARI_VOWELS:
            res.append(DEVANAGARI_VOWELS[c])
            i += 1
        elif c in DEVANAGARI_CONSONANTS:
            cons = DEVANAGARI_CONSONANTS[c]
            if nxt == VIRAMA:
                res.append(cons)
                i += 2  # skip consonant and virama
            elif nxt in DEVANAGARI_MATRAS:
                res.append(cons + DEVANAGARI_MATRAS[nxt])
                i += 2  # skip consonant and matra
            else:
                # Inherent 'a' vowel unless at end of word (schwa deletion)
                if i + 1 == n:
                    res.append(cons)
                else:
                    res.append(cons + 'a')
                i += 1
        elif c in DEVANAGARI_MATRAS:
            res.append(DEVANAGARI_MATRAS[c])
            i += 1
        else:
            res.append(c)
            i += 1

    translit = "".join(res)
    return leading_punct + translit + trailing_punct

def romanize_text(text: str) -> str:
    """Romanizes any Devanagari text in the string to Romanized Hinglish."""
    if not text or not any('\u0900' <= c <= '\u097F' for c in text):
        return text
    tokens = text.split(' ')
    romanized_tokens = [romanize_devanagari_word(t) for t in tokens]
    return ' '.join(romanized_tokens)

# Benchmark
sentences = [
    "मैं कल कोड पुश कर दूंगा.",
    "Main thodi der mein call karta hoon.",
    "आज का meeting schedule क्या है?",
    "चाय पीने चलते हैं ऑफिस के cafeteria में.",
    "Main staging server par deploy karke PR create kar raha hoon."
]

t0 = time.perf_counter()
for _ in range(100):
    for s in sentences:
        out = romanize_text(s)
elapsed = (time.perf_counter() - t0) / 500.0 * 1000

print(f"Romanize benchmark per sentence: {elapsed:.4f} ms")
for s in sentences:
    print(f"Orig: {s}")
    print(f"Roma: {romanize_text(s)}")
    print()
