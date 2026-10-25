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
    "active_style": "raw",  # raw, professional, casual, code, custom
    "app_aware_enabled": False,
    "custom_persona_prompt": "You are my personal speech writing assistant. Keep sentences clear, concise, and punchy without altering my core meaning.",
    "ollama_enabled": False,
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

    def get_initial_prompt(self, max_chars=800, include_replacements=True):
        """
        Builds an initial_prompt string for Whisper to prime its token decoder
        with user names, jargon, and formatting conventions.
        Combines custom_words and unique target values from word_replacements.
        Truncates safely within Whisper's context window limit (~224 tokens).
        """
        raw_words = self.get_custom_words()
        clean_custom = [w.strip() for w in raw_words if str(w).strip()]
        if not clean_custom:
            return None

        words = list(clean_custom)
        if include_replacements:
            for target in self.get_replacements().values():
                t_clean = str(target).strip()
                if t_clean and t_clean not in words:
                    words.append(t_clean)

        prefix = "Vocabulary: "
        suffix = "."
        budget = max_chars - len(prefix) - len(suffix)
        if budget <= 0:
            return None

        included = []
        current_len = 0
        for w in words:
            cost = len(w) + (2 if included else 0)
            if current_len + cost <= budget:
                included.append(w)
                current_len += cost
            else:
                break

        if not included:
            return None
        return prefix + ", ".join(included) + suffix

    def get_stage2_context(self, max_replacements=50, max_custom_words=50):
        """
        Returns structured dictionary and XML prompt blocks for Stage 2 LLM prompt injection.
        Capped to prevent prompt bloating and preserve sub-350ms end-to-end latency.
        """
        all_custom = list(self.get_custom_words())
        all_reps = dict(self.get_replacements())

        custom_words = [w.strip() for w in all_custom if w.strip()][:max_custom_words]
        rep_items = list(all_reps.items())[:max_replacements]

        xml_parts = []
        if custom_words:
            words_str = ", ".join(custom_words)
            xml_parts.append(f"<personal_dictionary>\n{words_str}\n</personal_dictionary>")

        if rep_items:
            reps_lines = [f'- "{h}" -> "{t}"' for h, t in rep_items]
            reps_str = "\n".join(reps_lines)
            xml_parts.append(
                f"<phonetic_memory>\n"
                f"Replace any of the following misheard phonetic variations with the exact target:\n"
                f"{reps_str}\n"
                f"</phonetic_memory>"
            )

        prompt_block = "\n\n".join(xml_parts)

        return {
            "phonetic_memory": all_reps,
            "custom_words": all_custom,
            "prompt_block": prompt_block
        }

    def apply_replacements(self, text):
        r"""
        Applies phonetic dictionary replacements using single-pass regex matching with conditional lookarounds.
        Uses (?<!\w) on word-start and (?!\w) on word-end so keys with trailing/internal punctuation
        (e.g., 'cooper nets,') match and replace cleanly while preventing nested substring replacements.
        Guarantees 100% dictionary match for both word_replacements and custom_words casing.
        """
        if not text:
            return text

        reps = dict(self.get_replacements())
        for word in self.get_custom_words():
            w_clean = str(word).strip()
            w_lower = w_clean.lower()
            if w_lower and w_lower not in reps:
                reps[w_lower] = w_clean

        if not reps:
            return text

        sorted_keys = sorted([k for k in reps.keys() if k], key=len, reverse=True)
        if not sorted_keys:
            return text

        dev_word_char = r'[\w\u0900-\u0963\u0966-\u097F]'
        b_both, b_start, b_end, b_none = [], [], [], []
        for k in sorted_keys:
            k_start = (k[0].isalnum() or k[0] == '_' or ('\u0900' <= k[0] <= '\u0963' or '\u0966' <= k[0] <= '\u097F'))
            k_end = (k[-1].isalnum() or k[-1] == '_' or ('\u0900' <= k[-1] <= '\u0963' or '\u0966' <= k[-1] <= '\u097F'))
            esc = re.escape(k)
            if k_start and k_end:
                b_both.append(esc)
            elif k_start:
                b_start.append(esc)
            elif k_end:
                b_end.append(esc)
            else:
                b_none.append(esc)

        parts = []
        if b_both:
            parts.append(rf'(?<!{dev_word_char})(?:' + '|'.join(b_both) + rf')(?!{dev_word_char})')
        if b_start:
            parts.append(rf'(?<!{dev_word_char})(?:' + '|'.join(b_start) + r')')
        if b_end:
            parts.append(r'(?:' + '|'.join(b_end) + rf')(?!{dev_word_char})')
        if b_none:
            parts.append(r'(?:' + '|'.join(b_none) + r')')

        reps_lower = {k.lower(): v for k, v in reps.items()}
        pattern = re.compile(r'(' + '|'.join(parts) + r')', re.IGNORECASE)
        return pattern.sub(lambda m: reps_lower.get(m.group(0).lower(), m.group(0)), text)

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
