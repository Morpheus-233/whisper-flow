import urllib.request
import json
import time

system_prompt = """You are the Stage 2 Fast Romanizer and Speech Stylist for Whisper Flow.
Your job is to format speech transcriptions into natural Romanized Hinglish (Latin alphabet) or English.

STRICT RULES:
1. NEVER TRANSLATE Hindi to English. Translating 'Main theek hoon' to 'I am fine' is STRICTLY FORBIDDEN.
2. If input is in Devanagari script (Hindi), transliterate it into natural Romanized Hinglish using the Latin alphabet (e.g., 'मैं कल कोड पुश कर दूंगा' -> 'Main kal code push kar dunga').
3. If input is in English, KEEP it in English.
4. Preserve ALL technical terms, programming jargon, and code tokens exactly (e.g., deploy, server, github, commit, PR, PySide6).
5. Output ONLY the processed text. No greetings, no preamble, no quotes, no explanations.

Active Style: CASUAL CHAT (lowercase, relaxed, remove trailing periods and commas).
"""

test_inputs = [
    "मैं कल कोड पुश कर दूंगा",
    "Main thodi der mein call karta hoon.",
    "Aaj ka meeting schedule kya hai?",
    "Main staging server par deploy karke PR create kar raha hoon."
]

for inp in test_inputs:
    payload = {
        "model": "qwen3.5:9b-q4_K_M",
        "prompt": f"{system_prompt}\n\nSpoken input: \"{inp}\"\nRevised text:",
        "stream": False,
        "options": {"temperature": 0.1}
    }
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=15) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        elapsed = (time.perf_counter() - t0) * 1000
    print(f"Input:   {inp}")
    print(f"Output:  {res.get('response', '').strip()}")
    print(f"Latency: {elapsed:.1f}ms")
    print("-" * 50)
