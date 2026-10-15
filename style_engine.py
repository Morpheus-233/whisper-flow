import json
import urllib.request
import urllib.error
import re
from text_cleaner import clean_speech_text, format_casual_chat

OLLAMA_API_BASE = "http://127.0.0.1:11434"

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

class StyleEngine:
    _instance = None

    def __init__(self, voice_profile_manager=None):
        from voice_profile import VoiceProfileManager
        self.profile_mgr = voice_profile_manager or VoiceProfileManager.get_instance()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

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
            except Exception as e:
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

    def transform_text(self, raw_text, target_style=None):
        """
        Transforms transcribed text according to the selected style preset or custom persona.
        Falls back to local rule-based cleaning if Ollama is disabled, offline, or times out.
        """
        if not raw_text or not raw_text.strip():
            return ""

        # Step 1: Base clean
        cleaned_base = clean_speech_text(raw_text)

        # Step 2: Determine style
        style = target_style or self.profile_mgr.get_active_style()

        # If style is 'raw' or empty, return immediately
        if not style or style == "raw":
            return cleaned_base

        # Casual style: zero-GPU instant rule without invoking Ollama or adding any latency or punctuation!
        if style == "casual":
            return format_casual_chat(raw_text)

        # Check if Ollama is enabled in profile
        profile = self.profile_mgr.profile
        if not profile.get("ollama_enabled", False):
            return cleaned_base

        model_name = profile.get("ollama_model", "qwen3.5:9b-q4_K_M")

        # Determine prompt
        if style == "custom":
            custom_prompt = profile.get("custom_persona_prompt", "").strip()
            if not custom_prompt:
                return cleaned_base
            system_prompt = (
                f"{custom_prompt}\n"
                "CRITICAL: Output ONLY the final revised text. Do NOT add preamble, quotes, or conversational commentary."
            )
        else:
            system_prompt = PROMPTS.get(style, PROMPTS["professional"])

        # Call Ollama API
        try:
            payload = {
                "model": model_name,
                "prompt": f"{system_prompt}\n\nSpoken input:\n\"\"\"{cleaned_base}\"\"\"\n\nRevised text:",
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
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "WhisperFlow"
                },
                method="POST"
            )

            # 1.5s timeout to guarantee instant responsiveness without freezing dictation
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                output = resp_data.get("response", "").strip()

                # Clean any accidental outer quotes or markdown code blocks
                if output.startswith('"""') and output.endswith('"""'):
                    output = output[3:-3].strip()
                elif output.startswith('"') and output.endswith('"'):
                    output = output[1:-1].strip()

                # Remove common LLM chatter patterns
                output = re.sub(r'^(Here is the revised text:?|Revised text:?|Here\'s your text:?)\s*', '', output, flags=re.IGNORECASE).strip()

                if output:
                    return output
        except Exception:
            pass

        return cleaned_base
