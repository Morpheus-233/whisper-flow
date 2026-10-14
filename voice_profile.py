import json
import os
import re

PROFILE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voice_profile.json")

DEFAULT_PROFILE = {
    "custom_words": [
        "Soham",
        "OpenCode",
        "PySide6",
        "CTranslate2",
        "PostgreSQL",
        "Whisper Flow",
        "BetterWispr"
    ],
    "word_replacements": {
        "pie side": "PySide6",
        "pyside": "PySide6",
        "see translate": "CTranslate2",
        "ctranslate": "CTranslate2",
        "open code": "OpenCode",
        "whisper flow": "Whisper Flow",
        "better whisper": "BetterWispr"
    },
    "active_style": "professional",  # raw, professional, casual, code, custom
    "app_aware_enabled": True,
    "custom_persona_prompt": "You are my personal speech writing assistant. Keep sentences clear, concise, and punchy without altering my core meaning.",
    "ollama_enabled": True,
    "ollama_model": "qwen3.5:9b-q4_K_M",
    "acoustic_settings": {
        "mic_gain_multiplier": 1.0,
        "calibrated_noise_floor": 0.005,
        "speaking_wpm": 130
    },
    "app_rules": {
        "code": [
            "code", "visual studio", "terminal", "powershell", "cmd",
            "wezterm", "alacritty", "mintty", "nvim", "vim", "sublime", "pycharm", "intellij"
        ],
        "casual": [
            "discord", "slack", "telegram", "whatsapp", "signal", "messages", "messenger", "twitter", "x.com"
        ],
        "professional": [
            "winword", "word", "outlook", "excel", "powerpnt", "powerpoint", "notion", "docs.google", "gmail"
        ]
    }
}

class VoiceProfileManager:
    _instance = None

    def __init__(self):
        self.profile = self.load_profile()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load_profile(self):
        if os.path.exists(PROFILE_FILE):
            try:
                with open(PROFILE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    profile = DEFAULT_PROFILE.copy()
                    profile.update(data)
                    return profile
            except Exception as e:
                print(f"[VoiceProfile] Error loading voice profile: {e}")
        return DEFAULT_PROFILE.copy()

    def save_profile(self):
        try:
            with open(PROFILE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.profile, f, indent=4)
        except Exception as e:
            print(f"[VoiceProfile] Error saving voice profile: {e}")

    def get_custom_words(self):
        return self.profile.get("custom_words", [])

    def add_custom_word(self, word):
        word = word.strip()
        if not word:
            return
        words = self.profile.get("custom_words", [])
        if word not in words:
            words.append(word)
            self.profile["custom_words"] = words
            self.save_profile()

    def remove_custom_word(self, word):
        words = self.profile.get("custom_words", [])
        if word in words:
            words.remove(word)
            self.profile["custom_words"] = words
            self.save_profile()

    def get_replacements(self):
        return self.profile.get("word_replacements", {})

    def add_replacement(self, heard, replacement):
        heard = heard.strip().lower()
        replacement = replacement.strip()
        if not heard or not replacement:
            return
        reps = self.profile.get("word_replacements", {})
        reps[heard] = replacement
        self.profile["word_replacements"] = reps
        self.save_profile()

    def remove_replacement(self, heard):
        heard = heard.strip().lower()
        reps = self.profile.get("word_replacements", {})
        if heard in reps:
            del reps[heard]
            self.profile["word_replacements"] = reps
            self.save_profile()

    def get_initial_prompt(self):
        """
        Builds an initial_prompt string for Whisper to prime its token decoder
        with user names, jargon, and formatting conventions.
        """
        words = self.get_custom_words()
        if not words:
            return None
        # Format as natural vocabulary context
        return "Vocabulary: " + ", ".join(words) + "."

    def apply_replacements(self, text):
        """
        Applies phonetic dictionary replacements using single-pass regex matching with word boundaries.
        Matches longer multi-word phrases first and avoids nested substring double replacements.
        """
        if not text:
            return text

        reps = self.get_replacements()
        if not reps:
            return text

        sorted_keys = sorted(reps.keys(), key=len, reverse=True)
        escaped_keys = [re.escape(k) for k in sorted_keys]
        pattern = re.compile(r'\b(' + '|'.join(escaped_keys) + r')\b', re.IGNORECASE)
        return pattern.sub(lambda m: reps.get(m.group(0).lower(), m.group(0)), text)

    def get_active_style(self):
        return self.profile.get("active_style", "professional")

    def set_active_style(self, style_name):
        self.profile["active_style"] = style_name
        self.save_profile()

    def get_effective_style(self, window_title="", window_class=""):
        """
        Determines the effective style. If app_aware_enabled is True,
        checks window_title and window_class against app_rules.
        """
        if not self.profile.get("app_aware_enabled", True):
            return self.get_active_style()

        target_str = f"{window_title} {window_class}".lower()
        app_rules = self.profile.get("app_rules", {})

        for style, keywords in app_rules.items():
            for kw in keywords:
                if kw in target_str:
                    return style

        return self.get_active_style()

    def get_acoustic_settings(self):
        return self.profile.get("acoustic_settings", DEFAULT_PROFILE["acoustic_settings"])

    def set_acoustic_settings(self, settings):
        self.profile["acoustic_settings"] = settings
        self.save_profile()
