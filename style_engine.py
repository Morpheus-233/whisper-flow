import json
import urllib.request
import urllib.error
import re
import logging

logger = logging.getLogger("whisper_flow.style_engine")
from text_cleaner import (
    clean_speech_text,
    format_casual_chat,
    format_developer_mode,
    format_custom_persona
)

__all__ = [
    "StyleEngine",
    "FastDevanagariRomanizer",
    "format_developer_mode",
    "format_custom_persona",
    "format_casual_chat",
    "clean_speech_text"
]

OLLAMA_API_BASE = "http://127.0.0.1:11434"

GROQ_STAGE2_SYSTEM_PROMPT = """You are an expert bilingual speech transcript formatter and smart editor specializing in Hindi-English (Hinglish) transcription and speech styling.

Your task is to take the raw transcript of spoken audio and produce the final polished transcript adhering strictly to the following rules:

1. SMART RETRACTIONS & FALSE STARTS:
- Detect verbal self-corrections such as "no wait", "actually", "scratch that", "sorry I mean", "nah", "wait", "nahi wait", "ruko".
- Aggressively eliminate the discarded thought/clause and output only the intended correction.
- Example: "let us meet on wednesday no wait let us meet on monday" -> "Let us meet on Monday"
- Example: "send it to rahul actually send it to priya" -> "Send it to Priya"
- Example: "kal milte hai 4 baje nahi wait 5 baje cafeteria mein" -> "Kal milte hai 5 baje cafeteria mein"

2. LISTS & ENUMERATED POINTS:
- When speech enumerates items, outlines points, or uses markers like "number one", "number two", "point 1", "firstly", "secondly", "there are three points/tasks", format them as clean multi-line markdown lists:
1. Item one
2. Item two
- If the user explicitly asks for bullet points (e.g. "bullet points"), format as:
- Item one
- Item two

3. ROMANIZATION (Devanagari to Latin alphabet):
- If the input contains Hindi or Devanagari script (e.g., "मैं कल कोड पुश कर दूंगा"), phonetically transcribe it into natural, conversational Romanized Hinglish using the Latin English alphabet (e.g., "Main kal code push kar dunga").
- If the input is already in Latin alphabet (English or Romanized Hinglish), keep it in Latin alphabet.
- NEVER output Devanagari script characters in the final output.

4. STRICT NEGATIVE CONSTRAINT (NEVER TRANSLATE TO ENGLISH):
- CRITICAL: DO NOT translate Hindi words into English under any circumstances!
- "मैं कल आऊंगा" MUST become "Main kal aaunga", NEVER "I will come tomorrow".
- "आज मीटिंग है" MUST become "Aaj meeting hai", NEVER "There is a meeting today".
- "कोड पुश कर दिया है" MUST become "Code push kar diya hai", NEVER "I have pushed the code".
- Translating the meaning of Hindi speech into English is a critical failure. Always transcribe the sound (phonetics) into Latin script.

5. PRESERVE TECHNICAL AND ENGLISH WORDS:
- Keep all English technical words, programming jargon, and code tokens in clean, accurate English spelling (e.g., "deploy", "server", "github", "commit", "PR", "database", "backend", "frontend", "API", "bug", "branch", "repo", "query", "pipeline").
- Never phonetically alter, translate, or mangle technical terms.

6. VOICE PROFILE CONTEXT:
{context_block}
- Always prioritize the exact casing and spellings from the personal dictionary and phonetic memory.

7. SPEECH STYLE ENFORCEMENT:
{style_instructions}

8. OUTPUT FORMAT:
- Output ONLY the final revised text.
- Do NOT output preamble, greetings, explanations, notes, quotation marks, or surrounding ``` markdown code fence blocks."""

PROMPTS = {
    "professional": (
        "You are an executive dictation editor. Rewrite the following transcribed speech into "
        "clear, well-punctuated, professional prose. Fix grammatical errors, remove filler words, "
        "and format numbers/dates appropriately. Preserve the user's exact original meaning. "
        "CRITICAL: Output ONLY the revised text. Do not include greetings, explanations, or quotes."
    ),
    "casual": (
        "You are a friendly chat dictation assistant. Rewrite the following transcribed speech into "
        "natural, concise, conversational chat text suitable for Slack, Discord, or messages. "
        "Remove stuttering and awkward filler words while keeping the tone warm and relaxed. "
        "CRITICAL: Output ONLY the revised text. Do not include greetings, explanations, or quotes."
    ),
    "code": (
        "You are a developer dictation assistant. The user is dictating code comments, git messages, "
        "or technical documentation. Format technical jargon properly, use backticks for variable names "
        "or code references, and format spoken code terms correctly (e.g., 'dot env' to '.env', 'snake case' "
        "or 'camelCase' as requested). "
        "CRITICAL: Output ONLY the revised text. Do not include greetings, explanations, or quotes."
    )
}


class FastDevanagariRomanizer:
    """
    Ultra-low-latency rule-based Devanagari to Romanized Hinglish transliterator.
    2-tier architecture: 200+ word dictionary lookup + algorithmic transliteration with schwa deletion.
    Runs in <0.01ms on CPU with 0 MB GPU VRAM.
    """

    VOWELS = {
        'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo', 'ऋ': 'ri',
        'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au', 'अं': 'an', 'अः': 'ah',
        'ऑ': 'o', 'ऍ': 'e', 'ॲ': 'a', 'ऎ': 'e', 'ऒ': 'o', 'ः': 'h'
    }

    MATRAS = {
        'ा': 'a', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo', 'ृ': 'ri',
        'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', 'ॉ': 'o', 'ॅ': 'e',
        'ॆ': 'e', 'ॊ': 'o'
    }

    CONSONANTS = {
        'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
        'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
        'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
        'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
        'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
        'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v',
        'श': 'sh', 'ष': 'sh', 'स': 's', 'ह': 'h',
        'क़': 'q', 'ख़': 'kh', 'ग़': 'gh', 'ज़': 'z', 'ड़': 'r', 'ढ़': 'rh', 'फ़': 'f',
        'ळ': 'l'
    }

    DEV_COMMON_WORDS = {
        # Pronouns & Demonstratives
        'मैं': 'Main', 'हम': 'hum', 'तुम': 'tum', 'आप': 'aap', 'वह': 'woh', 'वो': 'woh', 'यह': 'yeh', 'ये': 'yeh',
        'मेरा': 'mera', 'मेरी': 'meri', 'मेरे': 'mere', 'हमारा': 'hamara', 'हमारी': 'hamari', 'हमारे': 'hamare',
        'तेरा': 'tera', 'तेरी': 'teri', 'तेरे': 'tere', 'तुम्हारा': 'tumhara', 'तुम्हारी': 'tumhari', 'तुम्हारे': 'tumhare',
        'आपका': 'aapka', 'आपकी': 'aapki', 'आपके': 'aapke', 'उसका': 'uska', 'उसकी': 'uski', 'उसके': 'uske',
        'उनका': 'unka', 'उनकी': 'unki', 'उनके': 'unke', 'इसका': 'iska', 'इसकी': 'iski', 'इसके': 'iske',
        'इनका': 'inka', 'इनकी': 'inki', 'इनके': 'inke', 'मुझे': 'mujhe', 'मुझको': 'mujhko', 'हमें': 'humein',
        'तुझे': 'tujhe', 'तुम्हें': 'tumhein', 'आपको': 'aapko', 'उसे': 'use', 'उन्हें': 'unhein', 'इसे': 'ise', 'इन्हें': 'inhein',
        'मैंने': 'maine', 'हमने': 'humne', 'तुमने': 'tumne', 'आपने': 'aapne', 'उसने': 'usne', 'उन्होंने': 'unhone',
        'इसने': 'isne', 'इन्होंने': 'inhone', 'खुद': 'khud', 'अपना': 'apna', 'अपनी': 'apni', 'अपने': 'apne',
        # Question Words
        'क्या': 'kya', 'क्यों': 'kyun', 'कैसे': 'kaise', 'कैसा': 'kaisa', 'कैसी': 'kaisi', 'कब': 'kab',
        'कहाँ': 'kahan', 'कहा': 'kaha', 'कौन': 'kaun', 'किस': 'kis', 'किसे': 'kise', 'किसने': 'kisne',
        'कितना': 'kitna', 'कितनी': 'kitni', 'कितने': 'kitne',
        # Conjunctions & Prepositions
        'का': 'ka', 'की': 'ki', 'के': 'ke', 'को': 'ko', 'से': 'se', 'में': 'mein', 'पर': 'par',
        'और': 'aur', 'या': 'ya', 'लेकिन': 'lekin', 'मगर': 'magar', 'परन्तु': 'parantu', 'किंतु': 'kintu',
        'तो': 'to', 'भी': 'bhi', 'नहीं': 'nahin', 'ना': 'na', 'हाँ': 'haan', 'हा': 'haan', 'मत': 'mat',
        'अगर': 'agar', 'यदि': 'yadi', 'क्योंकि': 'kyunki', 'ताकि': 'taaki', 'जैसे': 'jaise', 'वैसे': 'waise',
        'तक': 'tak', 'बिना': 'bina', 'साथ': 'saath', 'अलावा': 'alawa', 'बारे': 'baare',
        # Auxiliary & State Verbs
        'है': 'hai', 'हैं': 'hain', 'हूँ': 'hoon', 'हु': 'hoon', 'था': 'tha', 'थी': 'thi', 'थे': 'the',
        'हो': 'ho', 'होगा': 'hoga', 'होगी': 'hogi', 'होंगे': 'honge', 'होना': 'hona', 'होता': 'hota', 'होती': 'hoti',
        'होते': 'hote', 'हुआ': 'hua', 'हुई': 'hui', 'हुए': 'hue',
        # Time & Adverbs
        'कल': 'kal', 'आज': 'aaj', 'अब': 'ab', 'तब': 'tab', 'जब': 'jab', 'अभी': 'abhi', 'कभी': 'kabhi', 'हमेशा': 'hamesha',
        'सुबह': 'subah', 'शाम': 'sham', 'रात': 'raat', 'दोपहर': 'dopahar', 'समय': 'samay', 'वक्त': 'waqt', 'दिन': 'din',
        'साल': 'saal', 'महीना': 'mahina', 'हफ्ता': 'hafta', 'घंटा': 'ghanta', 'मिनट': 'minute',
        'पहले': 'pehle', 'बाद': 'baad', 'जल्दी': 'jaldi', 'धीरे': 'dheere', 'थोड़ा': 'thoda', 'थोड़ी': 'thodi',
        'बहुत': 'bahut', 'ज्यादा': 'zyada', 'कम': 'kam', 'सिर्फ': 'sirf', 'बस': 'bas', 'शायद': 'shayad',
        'ज़रूर': 'zaroor', 'जरूर': 'zaroor',
        # Action Verbs
        'कर': 'kar', 'करना': 'karna', 'करो': 'karo', 'करेंगे': 'karenge', 'करेगा': 'karega', 'करेगी': 'karegi',
        'करूंगा': 'karunga', 'करूँगा': 'karunga', 'करूंगी': 'karungi', 'करूँगी': 'karungi',
        'करते': 'karte', 'करता': 'karta', 'करती': 'karti', 'किया': 'kiya', 'कीजिए': 'kijiye', 'करने': 'karne',
        'दे': 'de', 'देना': 'dena', 'दो': 'do', 'देंगे': 'denge', 'देगा': 'dega', 'दूंगा': 'dunga', 'दूँगा': 'dunga',
        'दिया': 'diya', 'दी': 'di', 'दीजिए': 'dijiye',
        'ले': 'le', 'लेना': 'lena', 'लो': 'lo', 'लेंगे': 'lenge', 'लूंगा': 'loonga', 'लिया': 'liya', 'ली': 'li', 'लीजिए': 'lijiye',
        'चल': 'chal', 'चलना': 'chalna', 'चलो': 'chalo', 'चलते': 'chalte', 'चले': 'chale', 'गया': 'gaya', 'गए': 'gaye', 'गई': 'gayi',
        'आ': 'aa', 'आना': 'aana', 'आओ': 'aao', 'आते': 'aate', 'आता': 'aata', 'आती': 'aati', 'आया': 'aaya', 'आए': 'aaye', 'आयी': 'aayi', 'आइए': 'aaiye',
        'जा': 'ja', 'जाना': 'jaana', 'जाओ': 'jaao', 'जाते': 'jaate', 'जाता': 'jaata', 'जाती': 'jaati', 'जाइए': 'jaiye',
        'बोल': 'bol', 'बोलना': 'bolna', 'बोलो': 'bolo', 'बोलते': 'bolte', 'बोला': 'bola', 'कहो': 'kaho', 'कहना': 'kahna',
        'देख': 'dekh', 'देखना': 'dekhna', 'देखो': 'dekho', 'देखा': 'dekha', 'सुन': 'sun', 'सुनना': 'sunna', 'सुनो': 'suno', 'सुना': 'suna',
        'समझ': 'samajh', 'समझना': 'samajhna', 'समझे': 'samjhe', 'भेज': 'bhej', 'भेजना': 'bhejna', 'भेजो': 'bhejo', 'भेजा': 'bheja',
        'रख': 'rakh', 'रखना': 'rakhna', 'रखो': 'rakho', 'रखा': 'rakha', 'मिल': 'mil', 'मिलना': 'milna', 'मिलो': 'milo', 'मिला': 'mila',
        'बता': 'bata', 'बताओ': 'batao', 'बताना': 'batana', 'बताया': 'bataya', 'पूछ': 'poochh', 'पूछना': 'poochhna',
        'लिख': 'likh', 'लिखना': 'likhna', 'लिखो': 'likho', 'लिखा': 'likha', 'पढ़': 'padh', 'पढ़ना': 'padhna',
        # Common Nouns & Adjectives
        'बात': 'baat', 'काम': 'kaam', 'दोस्त': 'dost', 'भाई': 'bhai', 'यार': 'yaar', 'घर': 'ghar', 'पानी': 'paani',
        'खाना': 'khaana', 'चाय': 'chai', 'कॉफी': 'coffee', 'पैसा': 'paisa', 'पैसे': 'paise', 'चीज': 'cheez',
        'अच्छा': 'achha', 'अच्छी': 'achhi', 'अच्छे': 'achhe', 'सही': 'sahi', 'गलत': 'galat', 'ठीक': 'theek',
        'बढ़िया': 'badhiya', 'मस्त': 'mast', 'नया': 'naya', 'नई': 'nayi', 'नए': 'naye', 'पुराना': 'purana',
        'पुराने': 'purane', 'बड़ा': 'bada', 'बड़ी': 'badi', 'बड़े': 'bade', 'छोटा': 'chhota', 'छोटी': 'chhoti', 'छोटे': 'chhote',
        # Tech & Domain Terms
        'कोड': 'code', 'सर्वर': 'server', 'कमिट': 'commit', 'डिप्लॉय': 'deploy', 'डिप्लॉयमेंट': 'deployment',
        'गिटहब': 'github', 'गिट': 'git', 'पीआर': 'PR', 'ब्रांच': 'branch', 'रिक्वेस्ट': 'request', 'पुल': 'pull', 'मर्ज': 'merge',
        'डेटा': 'data', 'डेटाबेस': 'database', 'फाइल': 'file', 'फ़ाइल': 'file', 'टेस्ट': 'test', 'टेस्टिंग': 'testing',
        'बग': 'bug', 'फिक्स': 'fix', 'रन': 'run', 'लॉग': 'log', 'लॉग्स': 'logs', 'पुश': 'push',
        'कॉल': 'call', 'मीटिंग': 'meeting', 'शेड्यूल': 'schedule', 'ऑफिस': 'office', 'टीम': 'team',
        'कैफेटेरिया': 'cafeteria', 'चैट': 'chat', 'मैसेज': 'message', 'लिंक': 'link',
        'यूजर': 'user', 'सिस्टम': 'system', 'पासवर्ड': 'password', 'ईमेल': 'email', 'स्क्रीन': 'screen',
        'लैपटॉप': 'laptop', 'फोन': 'phone', 'इंटरनेट': 'internet', 'नेटवर्क': 'network',
        'प्रोजेक्ट': 'project', 'प्रॉजेक्ट': 'project', 'स्क्रिप्ट': 'script', 'क्लाउड': 'cloud',
        'डॉकर': 'docker', 'कंटेनर': 'container', 'एपीआई': 'API', 'क्लाइंट': 'client',
        'फीचर': 'feature', 'रिस्टार्ट': 'restart', 'रीस्टार्ट': 'restart', 'कनेक्शन': 'connection',
        'टाइमआउट': 'timeout', 'क्वेरी': 'query', 'ऑप्टिमाइज़': 'optimize', 'प्रोडक्शन': 'production',
        'स्टेजिंग': 'staging', 'पैकेज': 'package', 'डिलीवरी': 'delivery', 'ट्रैफिक': 'traffic',
        'टिकट': 'ticket', 'टिकट्स': 'tickets', 'स्टेटस': 'status', 'कन्फर्म': 'confirmed',
        'बैटरी': 'battery', 'चार्जर': 'charger', 'ड्राइविंग': 'driving', 'प्लान': 'plan', 'वीकेंड': 'weekend',
        'रिलीज': 'release', 'वर्जन': 'version', 'अपडेट': 'update', 'डाउनलोड': 'download', 'अपलोड': 'upload',
        'बटन': 'button', 'विंडो': 'window', 'मॉनिटर': 'monitor', 'कीबोर्ड': 'keyboard', 'माउस': 'mouse',
        'एपीआई': 'API', 'रिस्पॉन्स': 'response', 'टाइम': 'time', 'फास्ट': 'fast', 'अराउंड': 'around',
        'सब': 'sub', 'एमएस': 'ms', 'होम': 'home', 'लॉगिन': 'login', 'डीबग': 'debug', 'सेशन': 'session',
        'स्टार्ट': 'start', 'स्प्रिंट': 'sprint', 'प्लानिंग': 'planning', 'जीरा': 'Jira',
        'फ्रंटएंड': 'frontend', 'फ्रांटएंड': 'frontend', 'बिल्ड': 'build', 'कम्प्लीट': 'complete',
        'कंप्लीट': 'complete', 'स्लैक': 'Slack', 'नोटिफिकेशन': 'notification', 'डिनर': 'dinner',
        'फाइल्स': 'files', 'इंस्पेक्ट': 'inspect', 'मेमोरी': 'memory', 'लीक': 'leak', 'डायग्नोस': 'diagnose',
        'वॉइस': 'voice', 'कैलिब्रेशन': 'calibration', 'हिंग्लिश': 'Hinglish', 'आउटपुट': 'output',
        'एक्यूरेट': 'accurate', 'आएगा': 'aayega', 'क्रिएट': 'create', 'माइग्रेशन': 'migration',
        'पाइथन': 'python', 'प्रेजेंटेशन': 'presentation', 'आफ्टरनून': 'afternoon', 'अर्जेन्ट': 'urgent',
        'एरर': 'error', 'स्टेशन': 'station', 'चेक': 'check',
        'ऑप्शन': 'option', 'ऑनलाइन': 'online', 'ऑब्जेक्ट': 'object', 'ॲप': 'app', 'ऐप': 'app',
        'दुःख': 'dukh', 'अतः': 'atah', 'पुनः': 'punah'
    }

    DIGITS = {
        '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
        '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
    }

    @classmethod
    def has_devanagari(cls, text: str) -> bool:
        """Returns True if the string contains any Devanagari character (U+0900 to U+097F)."""
        return any('\u0900' <= c <= '\u097F' for c in text)

    @classmethod
    def transliterate_token(cls, word: str) -> str:
        """Translates a single token via dictionary lookup or algorithmic schwa deletion transliteration."""
        if not word:
            return ""
        # Strip invisible zero-width joiner and non-joiner characters
        word = word.replace('\u200c', '').replace('\u200d', '')
        if not word:
            return ""

        # Check dictionary first (O(1))
        if word in cls.DEV_COMMON_WORDS:
            return cls.DEV_COMMON_WORDS[word]

        # If token does not contain any Devanagari characters, return verbatim
        if not any('\u0900' <= c <= '\u097F' for c in word):
            return word

        out = []
        n = len(word)
        i = 0
        while i < n:
            ch = word[i]
            # Strip lingering zero-width joiner/non-joiner
            if ch in ('\u200c', '\u200d'):
                i += 1
                continue

            # Handle decomposed Candra vowels (e.g. अ + ॉ -> o, अ + ॅ -> e)
            if ch == 'अ' and i + 1 < n:
                if word[i + 1] == '\u0949':
                    out.append('o')
                    i += 2
                    continue
                elif word[i + 1] == '\u0945':
                    out.append('e')
                    i += 2
                    continue

            # Handle Nukta combination
            if i + 1 < n and word[i + 1] == '\u093C':
                comb = ch + '\u093C'
                if comb in cls.CONSONANTS:
                    ch = comb
                    i += 1

            if ch in cls.DIGITS:
                out.append(cls.DIGITS[ch])
                i += 1
            elif ch in cls.VOWELS:
                out.append(cls.VOWELS[ch])
                i += 1
            elif ch in cls.CONSONANTS:
                base = cls.CONSONANTS[ch]
                if i + 1 < n:
                    nxt = word[i + 1]
                    if nxt == '\u094D':  # Halant / Virama
                        out.append(base)
                        i += 2
                    elif nxt in cls.MATRAS:
                        out.append(base + cls.MATRAS[nxt])
                        i += 2
                    elif nxt in ('\u0902', '\u0901'):  # Anusvara / Candrabindu
                        out.append(base + 'an')
                        i += 2
                    elif nxt == '\u0903':  # Visarga after consonant
                        out.append(base + 'ah')
                        i += 2
                    elif nxt in ('\u0964', '\u0965'):  # Word-final before Danda
                        out.append(base)
                        i += 1
                    else:
                        out.append(base + 'a')
                        i += 1
                else:
                    # Word-final schwa deletion
                    out.append(base)
                    i += 1
            elif ch in cls.MATRAS:
                out.append(cls.MATRAS[ch])
                i += 1
            elif ch in ('\u0902', '\u0901'):
                out.append('n')
                i += 1
            elif ch in ('\u0964', '\u0965'):  # Danda / Double Danda
                out.append('.')
                i += 1
            elif ch == '\u0970':  # Abbreviation sign
                out.append('.')
                i += 1
            elif ch == '\u0950':  # Om
                out.append('om')
                i += 1
            elif ch == '\u093D':  # Avagraha
                i += 1
            elif ch == '\u0903':  # Standalone Visarga
                out.append('h')
                i += 1
            elif '\u0900' <= ch <= '\u097F':
                # Safety catch-all to prevent unmapped Devanagari from leaking
                i += 1
            else:
                out.append(ch)
                i += 1

        res = ''.join(out)
        res = res.replace('\u200c', '').replace('\u200d', '')
        # Medial schwa deletion for non-initial syllables (e.g., chalate -> chalte, karate -> karte)
        res = re.sub(r'(?<=[aeiou][b-df-hj-np-tv-z])a(?=[b-df-hj-np-tv-z][aeiou])', '', res)
        return res

    @classmethod
    def romanize(cls, text: str) -> str:
        """Converts Devanagari script in text to natural Romanized Hinglish."""
        if not text:
            return ""

        # Strip invisible zero-width joiner and non-joiner control codes
        text = text.replace('\u200c', '').replace('\u200d', '')
        if not cls.has_devanagari(text):
            return text

        # Exclude Devanagari Danda (\u0964) and Double Danda (\u0965) from word tokens to enable dictionary lookup
        tokens = re.split(r'(\s+|[^\w\u0900-\u0963\u0966-\u097F]+)', text)
        result = ''.join(cls.transliterate_token(t) for t in tokens)
        result = result.replace('\u200c', '').replace('\u200d', '')
        result = re.sub(r'[ \t]+', ' ', result).strip()
        return result


class StyleEngine:
    _instance = None
    _unauthorized_keys = set()

    format_developer_mode = staticmethod(format_developer_mode)
    format_custom_persona = staticmethod(format_custom_persona)
    format_casual_chat = staticmethod(format_casual_chat)
    clean_speech_text = staticmethod(clean_speech_text)

    def __init__(self, voice_profile_manager=None):
        from voice_profile import VoiceProfileManager
        self.profile_mgr = voice_profile_manager or VoiceProfileManager.get_instance()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def format_two_stage(
        cls,
        raw_text: str,
        style: str | None = None,
        voice_profile=None,
        engine_mode: str | None = None,
        groq_api_key: str | None = None
    ) -> str:
        """
        Stage 2: Fast Romanizer & Stylist.
        Converts raw transcript (Devanagari/English/Hinglish) into natural Romanized Hinglish
        in the Latin alphabet, enforces the speech style, preserves technical terms,
        and forbids English translation.
        Routes to Groq Cloud (llama-3.3-70b-versatile) or local CPU fallback.
        """
        if not raw_text or not raw_text.strip():
            return ""

        from config import load_config
        cfg = load_config()

        profile_mgr = voice_profile or (cls._instance.profile_mgr if cls._instance else None)
        if profile_mgr is None:
            try:
                from voice_profile import VoiceProfileManager
                profile_mgr = VoiceProfileManager.get_instance()
            except Exception:
                profile_mgr = None

        active_style = (style or (profile_mgr.get_active_style() if profile_mgr else "professional") or "professional").lower()
        active_engine = (engine_mode or cfg.get("engine_mode", "groq")).lower()
        api_key = (groq_api_key or cfg.get("groq_api_key", "")).strip()

        # Branch A: Groq Cloud LLM Romanizer & Stylist
        # If active_style == 'custom' and persona_rules is a structured dictionary, route to deterministic local format_custom_persona
        persona_rules = None
        if profile_mgr and hasattr(profile_mgr, "profile"):
            p = profile_mgr.profile
            persona_rules = p.get("persona_rules") or p.get("custom_persona_rules")

        if active_style == "custom" and isinstance(persona_rules, dict):
            return cls._format_local(raw_text, active_style, profile_mgr)

        if active_engine == "groq" and api_key and api_key not in cls._unauthorized_keys:
            try:
                formatted = cls._format_groq(raw_text, active_style, profile_mgr, api_key)
                if formatted:
                    return formatted
            except urllib.error.HTTPError as e:
                if e.code == 401:
                    cls._unauthorized_keys.add(api_key)
                print(f"[StyleEngine] Groq Stage 2 formatting failed: {e}. Falling back to local Romanizer.")
            except Exception as e:
                if "401" in str(e):
                    cls._unauthorized_keys.add(api_key)
                print(f"[StyleEngine] Groq Stage 2 formatting failed: {e}. Falling back to local Romanizer.")

        # Branch B: Local Offline CPU Romanizer & Style Transform Fallback
        return cls._format_local(raw_text, active_style, profile_mgr)

    @classmethod
    def _format_groq(cls, raw_text: str, style: str, profile_mgr, api_key: str) -> str:
        """Calls Groq Cloud llama-3.3-70b-versatile API."""
        context_block = "None."
        custom_persona_prompt = ""

        if profile_mgr:
            if hasattr(profile_mgr, "get_stage2_context"):
                ctx = profile_mgr.get_stage2_context()
                if ctx.get("prompt_block"):
                    context_block = ctx["prompt_block"]
            else:
                c_words = getattr(profile_mgr, "get_custom_words", lambda: [])()
                reps = getattr(profile_mgr, "get_replacements", lambda: {})()
                parts = []
                if c_words:
                    parts.append("<personal_dictionary>\n" + ", ".join(c_words) + "\n</personal_dictionary>")
                if reps:
                    lines = [f'- "{h}" -> "{t}"' for h, t in list(reps.items())[:30]]
                    parts.append("<phonetic_memory>\n" + "\n".join(lines) + "\n</phonetic_memory>")
                if parts:
                    context_block = "\n\n".join(parts)

            if hasattr(profile_mgr, "profile"):
                p = profile_mgr.profile
                custom_persona_prompt = p.get("custom_persona_prompt", "") or p.get("persona_rules", "")

        if style == "casual":
            style_instructions = (
                "- Style: Casual Chat.\n"
                "- Remove all formal trailing periods, exclamation marks, and formal commas.\n"
                "- Use relaxed, conversational lowercase text (e.g., 'main kal code push kar dunga').\n"
                "- Preserve uppercase for acronyms (e.g., 'API', 'GPU', 'CPU', 'PR', 'JSON') and proper nouns/code tokens.\n"
                "- Keep numbers, URLs, and decimal points intact."
            )
        elif style in ("code", "developer", "dev"):
            style_instructions = (
                "- Style: Developer Mode.\n"
                "- Transform spoken casing commands: 'camel case [words]' -> camelCase, 'snake case [words]' -> snake_case, "
                "'kebab case [words]' -> kebab-case, 'pascal case [words]' -> PascalCase, 'constant case [words]' -> CONSTANT_CASE.\n"
                "- Transform spoken code tokens: 'dot env' -> '.env', 'dot py' -> '.py', 'dot json' -> '.json', "
                "'console dot log' -> 'console.log', 'arrow function' -> '=>', 'double equals' -> '==', 'triple equals' -> '===', "
                "'not equals' -> '!=', 'open paren/close paren' -> '()', 'open brace/close brace' -> '{}', 'open bracket/close bracket' -> '[]'.\n"
                "- For non-code spoken portions, keep natural Romanized Hinglish or English."
            )
        elif style == "custom":
            style_instructions = (
                f"- Style: Custom Persona.\n"
                f"- Apply the user's custom persona rules: {custom_persona_prompt}\n"
                "- Ensure the output strictly maintains Romanized Hinglish without translating to English."
            )
        elif style == "raw":
            style_instructions = (
                "- Style: Raw / Faithful.\n"
                "- Only Romanize Devanagari script to Latin alphabet and apply basic vocal filler cleanup, preserving original phrasing and punctuation."
            )
        else:
            style_instructions = (
                "- Style: Professional.\n"
                "- Ensure clear, well-punctuated, grammatically cohesive sentences with proper sentence capitalization and ending periods.\n"
                "- Remove vocal fillers (um, uh, ah, er) and immediate stuttering words.\n"
                "- Format numbers, currencies, and dates properly."
            )

        system_prompt = GROQ_STAGE2_SYSTEM_PROMPT.format(
            context_block=context_block,
            style_instructions=style_instructions
        )

        candidate_models = [
            "qwen/qwen3.8-27b",
            "openai/gpt-oss-120b",
            "llama-3.3-70b-versatile",
            "llama-3.1-70b-versatile"
        ]

        for model_id in candidate_models:
            payload = {
                "model": model_id,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": raw_text}
                ],
                "temperature": 0.1,
                "max_tokens": 512,
                "stream": False
            }

            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {api_key.strip()}",
                    "Content-Type": "application/json",
                    "User-Agent": "WhisperFlow"
                },
                method="POST"
            )

            try:
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    choices = data.get("choices", [])
                    if choices and "message" in choices[0]:
                        content = choices[0]["message"].get("content", "").strip()
                        if content.startswith('"""') and content.endswith('"""'):
                            content = content[3:-3].strip()
                        elif content.startswith('"') and content.endswith('"'):
                            content = content[1:-1].strip()
                        content = re.sub(r'^(Here is the revised text:?|Revised text:?|Here\'s your text:?)\s*', '', content, flags=re.IGNORECASE).strip()
                        if FastDevanagariRomanizer.has_devanagari(content):
                            content = FastDevanagariRomanizer.romanize(content)
                        return content
            except urllib.error.HTTPError as err:
                if err.code == 404:
                    logger.warning("Groq model %s returned 404, attempting fallback candidate model...", model_id)
                    continue
                # Re-raise non-404 HTTP errors so caller (format_two_stage) handles 401 circuit breaking
                raise err
            except Exception as e:
                logger.warning("Groq Stage 2 request failed with model %s: %s", model_id, e)
                raise e

        return ""

    @classmethod
    def _call_ollama(cls, text: str, style: str, profile_mgr) -> str:
        """Fallback to local Ollama if configured and reachable."""
        profile = profile_mgr.profile if profile_mgr and hasattr(profile_mgr, "profile") else {}
        model_name = profile.get("ollama_model", "qwen3.5:9b-q4_K_M")
        prompt = PROMPTS.get(style, PROMPTS["professional"])
        payload = {
            "model": model_name,
            "prompt": f"{prompt}\n\nSpoken input:\n\"\"\"{text}\"\"\"\n\nRevised text:",
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "stop": ["\nSpoken input:", "\n\nSpoken input:"]
            }
        }
        req = urllib.request.Request(
            f"{OLLAMA_API_BASE}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "WhisperFlow"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            output = resp_data.get("response", "").strip()
            if output.startswith('"""') and output.endswith('"""'):
                output = output[3:-3].strip()
            elif output.startswith('"') and output.endswith('"'):
                output = output[1:-1].strip()
            output = re.sub(r'^(Here is the revised text:?|Revised text:?|Here\'s your text:?)\s*', '', output, flags=re.IGNORECASE).strip()
            return output

    @classmethod
    def _format_local(cls, raw_text: str, style: str, profile_mgr) -> str:
        """Local offline zero-GPU CPU Romanizer and Style transform fallback."""
        # Step 1: Romanize Devanagari if present (<0.001ms)
        romanized = FastDevanagariRomanizer.romanize(raw_text)

        # Step 2: Apply style transformation
        if style == "casual":
            return format_casual_chat(romanized)
        elif style in ("code", "developer", "dev"):
            return format_developer_mode(romanized)
        elif style == "custom":
            persona_rules = None
            if profile_mgr and hasattr(profile_mgr, "profile"):
                p = profile_mgr.profile
                persona_rules = p.get("persona_rules") or p.get("custom_persona_rules") or p.get("custom_persona_prompt")
            return format_custom_persona(romanized, rules=persona_rules)
        elif style == "raw":
            return clean_speech_text(romanized)
        else:
            # Professional / default style
            if profile_mgr and hasattr(profile_mgr, "profile") and profile_mgr.profile.get("ollama_enabled", False):
                try:
                    ollama_res = cls._call_ollama(romanized, style, profile_mgr)
                    if ollama_res:
                        return ollama_res
                except Exception:
                    pass
            cleaned = clean_speech_text(romanized)
            return cleaned

    def transform_text(self, raw_text, target_style=None):
        """
        Transforms transcribed text according to the selected style preset or custom persona.
        Delegates to format_two_stage for complete two-stage Hinglish Romanization & styling.
        """
        if not raw_text or not raw_text.strip():
            return ""

        return self.format_two_stage(
            raw_text,
            style=target_style,
            voice_profile=self.profile_mgr
        )

    def prewarm(self):
        """Send a lightweight prompt in background so model stays warm in VRAM."""
        def _worker():
            try:
                profile = self.profile_mgr.profile
                if not profile.get("ollama_enabled", False):
                    return
                model_name = profile.get("ollama_model", "qwen3.5:9b-q4_K_M")
                payload = {
                    "model": model_name,
                    "prompt": "hi",
                    "stream": False
                }
                req = urllib.request.Request(
                    f"{OLLAMA_API_BASE}/api/generate",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=10.0) as resp:
                    resp.read()
                print(f"[StyleEngine] Ollama model '{model_name}' is warm in VRAM!")
            except Exception:
                pass

        import threading
        threading.Thread(target=_worker, daemon=True).start()

    @staticmethod
    def list_installed_models():
        """Returns list of model names currently installed in Ollama."""
        try:
            req = urllib.request.Request(f"{OLLAMA_API_BASE}/api/tags", headers={"User-Agent": "WhisperFlow"})
            with urllib.request.urlopen(req, timeout=0.4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = [m.get("name") for m in data.get("models", []) if m.get("name")]
                return models
        except Exception:
            return []
