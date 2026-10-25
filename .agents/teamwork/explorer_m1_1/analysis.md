# Analysis Report: Stage 1 Acoustic Capture in `whisper_engine.py`

**Milestone**: M1 (Two-Stage Hinglish Pipeline)  
**Author**: M1 Explorer 1 (`explorer_m1_1`)  
**Target File**: `whisper_engine.py`  
**Dependencies/Callers**: `config.py`, `style_engine.py`, `voice_profile.py`, `app.py`, `tests/test_whisper_engine.py`

---

## 1. Executive Summary

In Milestone M1, Whisper Flow transitions to a two-stage speech processing architecture. **Stage 1 (Acoustic Capture)** is solely responsible for capturing spoken acoustic phonemes and transcribing them into raw text in their natural spoken form (Devanagari for Hindi, Latin alphabet for English and technical terms, or code-mixed) without forced translation into English.

This investigation analyzes how Groq Cloud (`whisper-large-v3-turbo`) and local CPU (`faster-whisper` `base` int8) must be configured, explicitly passing `task="transcribe"`, enabling language auto-detection for code-mixed Hinglish, providing seamless zero-crash CPU fallback, and presenting a clean decoupled interface (`transcribe_stage1`) that feeds Stage 2 (`StyleEngine.format_two_stage`).

---

## 2. Examination of Current `whisper_engine.py`

### 2.1 Current State Findings

1. **Groq Cloud Implementation (`_transcribe_groq`)**:
   - Uses `urllib.request` to `POST` multipart/form-data to `https://api.groq.com/openai/v1/audio/transcriptions`.
   - Sends: `model="whisper-large-v3-turbo"`, `response_format="json"`, `temperature="0.0"`, optional `prompt=initial_prompt`, and audio `file="audio.wav"`.
   - **Gaps Identified**:
     - Does not accept or forward `language` parameter.
     - Does not inspect `engine_mode` from config (will attempt Groq even if user selected "local" if a key exists in config).
     - Network timeout is set to `10.0` seconds; if Groq hangs, user experiences unacceptable desktop lag before fallback. Recommended timeout: `5.0` seconds.
     - Does not document or assert that the endpoint is strictly `/audio/transcriptions` (preventing any possibility of hitting `/audio/translations`).

2. **Local CPU Implementation (`WhisperModel.transcribe`)**:
   - Loads `WhisperModel(self.model_name, device="cpu", compute_type="int8", cpu_threads=6)`.
   - Executes greedy decoding (`beam_size=1, best_of=1, temperature=0.0`) with `vad_filter=True`.
   - **Gaps Identified**:
     - `task="transcribe"` is NOT explicitly passed to `self.model.transcribe()`. Although "transcribe" is faster-whisper's default, omitting it leaves open potential regressions if translation flags or presets are altered.
     - `language` is NOT explicitly forwarded. Passing `language=None` (or omitting for auto-detect) allows Whisper's language detection head to identify Hindi or English dynamically.
     - Model name risk: `config.json` had `"model_name": "base.en"`. The English-only `.en` models completely lack Hindi Devanagari tokens and crash or produce phonetic gibberish on Hindi audio. Any `.en` suffix must be sanitized to multilingual `"base"`.

---

## 3. Anti-Translation Guarantee: Preventing Whisper Translation

### 3.1 The Whisper Translation Trap
OpenAI Whisper architectures contain two distinct sequence-to-sequence decoder modes:
- `<|transcribe|>`: Emits tokens in the language identified from the speech audio.
- `<|translate|>`: Forces the decoder to translate all foreign speech directly into English prose.

If Whisper performs translation, a sentence like *"Main kal code push kar dunga"* becomes *"I will push the code tomorrow."* This violates User Requirement R1:
> *"Strictly prevents literal translation into English... Transcribes Hindi into natural Romanized Hinglish using the English alphabet."*

### 3.2 Guarantee Mechanisms
1. **Groq Cloud API**:
   - Groq enforces task separation at the routing level:
     - `/openai/v1/audio/transcriptions` -> Maps directly to Whisper transcription.
     - `/openai/v1/audio/translations` -> Maps to Whisper English translation.
   - Whisper Flow strictly targets `https://api.groq.com/openai/v1/audio/transcriptions`.
   - The translation endpoint is never referenced or called anywhere in the codebase.
2. **Local CPU (`faster-whisper`)**:
   - `self.model.transcribe(..., task="transcribe", ...)` must be explicitly provided in the keyword arguments.
3. **Language Mode Configuration**:
   - For code-mixed Hinglish speech, passing `language=None` (or `"auto"`) instructs Whisper to auto-detect language across segments. Spoken English words ("deploy", "server", "github") remain in English Latin script; spoken Hindi words are captured in Devanagari.
   - If user explicitly selects Hindi, `language="hi"` can be passed.
   - If user selects English, `language="en"` can be passed.
   - When `language` is `"auto"`, `None`, or empty:
     - Groq: Omit the `"language"` multipart field (triggers Groq server-side auto-detect).
     - Local CPU: Pass `language=None` to `self.model.transcribe()`.

---

## 4. Interface Architecture: Stage 1 to Stage 2

### 4.1 Interface Decoupling: `transcribe_stage1`
To cleanly separate acoustic transcription from downstream styling and Romanization, `WhisperEngine` should expose:

```python
def transcribe_stage1(
    self,
    audio_data: np.ndarray,
    sample_rate: int = 16000,
    initial_prompt: str | None = None,
    language: str | None = None,
    engine_mode: str | None = None
) -> str
```

**Responsibilities of `transcribe_stage1`**:
- Validates input audio: if empty, returns `""` immediately.
- Normalizes audio amplitude to `[-1.0, 1.0]` without distortion.
- Determines active engine mode (`"groq"` vs `"local"`).
- Attempts Groq Cloud if `engine_mode != "local"` and `groq_api_key` is available.
- On any Groq failure (or if in `"local"` mode), falls back to `_transcribe_local`.
- Returns raw string (Devanagari, English, or mixed).
- Does NOT apply Romanization or styling.

### 4.2 Two-Stage Coordination: `WhisperEngine.transcribe`
`WhisperEngine.transcribe` serves as the primary coordinator conforming to `PROJECT.md` line 73:

```python
def transcribe(
    self,
    audio_data: np.ndarray,
    sample_rate: int = 16000,
    initial_prompt: str | None = None,
    style: str | None = None,
    language: str | None = None,
    engine_mode: str | None = None,
    remove_trailing_stop: bool = False
) -> str
```

**Execution Flow**:
1. **Stage 1 (Acoustic Capture)**:
   `raw_text = self.transcribe_stage1(audio_data, sample_rate, initial_prompt, language, engine_mode)`
   If `remove_trailing_stop`: `raw_text = self.clean_stop_keyword(raw_text)`
   If `not raw_text`: return `""`
2. **Stage 2 (Fast Romanizer & Stylist)**:
   If `StyleEngine.format_two_stage` is available:
   `formatted_text = StyleEngine.get_instance().format_two_stage(raw_text, style=style, voice_profile=profile)`
   Else fallback to `StyleEngine.get_instance().transform_text(raw_text, target_style=style)`.
3. **Stage 3 (Deterministic Exact Match Guarantee)**:
   `final_text = profile.apply_replacements(formatted_text)`
   Return `final_text`.

---

## 5. Automatic Local CPU Fallback Mechanism

### 5.1 Failure Modes Handled
| Trigger | Cause | Fallback Action |
|---|---|---|
| User selection | `engine_mode == "local"` in config | Directly calls `_transcribe_local`, bypasses network |
| Missing Credentials | `groq_api_key` is empty or None | Directly calls `_transcribe_local` |
| Auth Failure | HTTP 401 Unauthorized (expired/invalid key) | Logs warning, catches HTTPError, invokes `_transcribe_local` |
| Rate Limiting | HTTP 429 Too Many Requests | Logs warning, catches HTTPError, invokes `_transcribe_local` |
| Cloud Outage | HTTP 500, 502, 503 Service Unavailable | Logs warning, catches HTTPError, invokes `_transcribe_local` |
| Network Loss | URLError, DNS failure, ConnectionRefused | Logs warning, catches URLError, invokes `_transcribe_local` |
| Network Timeout | Request exceeds 5.0 seconds | Logs warning, catches TimeoutError/socket.timeout, invokes `_transcribe_local` |

### 5.2 Zero-Crash Contract
- Any exception inside `_transcribe_groq` is caught by `except Exception as e:` inside `transcribe_stage1`.
- A descriptive log entry is output: `[WhisperEngine] Groq API transcription failed: {e}. Falling back to local model.`
- Execution immediately proceeds to `_transcribe_local`.
- If the local model is not yet in memory, `self.load_model()` is invoked on the fly, loading `base` on CPU int8 with 0 MB GPU VRAM.

---

## 6. Blueprint & Method Signatures for `whisper_engine.py`

```python
import os
import sys
import threading
import uuid
import io
import json
import urllib.request
import urllib.error
import numpy as np
import scipy.io.wavfile as wav
import ctypes

from config import load_config
from faster_whisper import WhisperModel
import ctranslate2

class WhisperEngine:
    _instance = None
    _lock = threading.Lock()

    def __init__(self, model_name=None, device=None, compute_type=None, groq_api_key=None, engine_mode=None):
        cfg = load_config()
        # Enforce multilingual 'base' model - strip any '.en' suffix
        raw_model = model_name or cfg.get("model_name", "base")
        self.model_name = "base" if raw_model.endswith(".en") else raw_model
        
        self.device = device or cfg.get("device", "cpu")
        self.compute_type = compute_type or cfg.get("compute_type", "int8")
        self.groq_api_key = groq_api_key if groq_api_key is not None else cfg.get("groq_api_key", "")
        self.engine_mode = engine_mode or cfg.get("engine_mode", "groq")
        self.model = None
        self.is_loading = False
        self._load_lock = threading.Lock()

    @classmethod
    def get_instance(cls, model_name=None, device=None, compute_type=None, groq_api_key=None, engine_mode=None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(
                    model_name=model_name,
                    device=device,
                    compute_type=compute_type,
                    groq_api_key=groq_api_key,
                    engine_mode=engine_mode
                )
            else:
                if model_name is not None and cls._instance.model_name != model_name:
                    cls._instance.model_name = "base" if model_name.endswith(".en") else model_name
                    cls._instance.model = None
                if device is not None and cls._instance.device != device:
                    cls._instance.device = device
                    cls._instance.model = None
                if compute_type is not None and cls._instance.compute_type != compute_type:
                    cls._instance.compute_type = compute_type
                    cls._instance.model = None
                if groq_api_key is not None:
                    cls._instance.groq_api_key = groq_api_key
                if engine_mode is not None:
                    cls._instance.engine_mode = engine_mode
            return cls._instance

    def _transcribe_groq(self, audio_data, api_key, sample_rate=16000, initial_prompt=None, language=None):
        if len(audio_data) == 0:
            return ""

        max_val = np.max(np.abs(audio_data))
        if max_val > 0.001 and max_val > 1.0:
            audio_data = audio_data / max_val

        int16_data = np.clip(audio_data * 32767.0, -32768, 32767).astype(np.int16)
        buf = io.BytesIO()
        wav.write(buf, sample_rate, int16_data)
        wav_bytes = buf.getvalue()

        boundary = f"----WhisperFlowBoundary{uuid.uuid4().hex}"
        body_parts = []

        def add_field(name, value):
            body_parts.append(f"--{boundary}\r\n".encode("utf-8"))
            body_parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
            body_parts.append(str(value).encode("utf-8"))
            body_parts.append(b"\r\n")

        # Required & optional parameters for Groq Whisper
        add_field("model", "whisper-large-v3-turbo")
        add_field("response_format", "json")
        add_field("temperature", "0.0")
        
        if initial_prompt:
            add_field("prompt", initial_prompt)

        # Language: omit if auto/None, send ISO-639-1 code if specified
        if language and language.lower() not in ("auto", "none"):
            add_field("language", language.lower())

        # Audio file payload
        body_parts.append(f"--{boundary}\r\n".encode("utf-8"))
        body_parts.append(b'Content-Disposition: form-data; name="file"; filename="audio.wav"\r\n')
        body_parts.append(b"Content-Type: audio/wav\r\n\r\n")
        body_parts.append(wav_bytes)
        body_parts.append(b"\r\n")
        body_parts.append(f"--{boundary}--\r\n".encode("utf-8"))
        
        payload = b"".join(body_parts)

        # Strictly hitting /audio/transcriptions (never /audio/translations)
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key.strip()}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "User-Agent": "WhisperFlow"
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=5.0) as resp:
            status_code = getattr(resp, "status", 200)
            if status_code != 200:
                raise RuntimeError(f"Groq API returned HTTP status {status_code}")
            resp_body = resp.read().decode("utf-8")
            resp_data = json.loads(resp_body)
            if isinstance(resp_data, dict) and "error" in resp_data:
                raise RuntimeError(f"Groq API returned error: {resp_data['error']}")
            return resp_data.get("text", "").strip()

    def _transcribe_local(self, audio_data, initial_prompt=None, language=None):
        if len(audio_data) == 0:
            return ""

        if self.model is None:
            self.load_model()

        if initial_prompt is None:
            try:
                from voice_profile import VoiceProfileManager
                initial_prompt = VoiceProfileManager.get_instance().get_initial_prompt()
            except Exception:
                initial_prompt = None

        max_val = np.max(np.abs(audio_data))
        if max_val > 0.001 and max_val > 1.0:
            audio_data = audio_data / max_val

        model_lang = None if (not language or language.lower() in ("auto", "none")) else language.lower()

        # Explicitly pass task="transcribe" to forbid translation
        segments, info = self.model.transcribe(
            audio_data,
            task="transcribe",
            language=model_lang,
            initial_prompt=initial_prompt,
            beam_size=1,
            best_of=1,
            temperature=0.0,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=300),
            condition_on_previous_text=False
        )

        text_pieces = [segment.text.strip() for segment in segments]
        return " ".join(text_pieces).strip()

    def transcribe_stage1(self, audio_data, sample_rate=16000, initial_prompt=None, language=None, engine_mode=None):
        if len(audio_data) == 0:
            return ""

        cfg = load_config()
        active_mode = (engine_mode or getattr(self, "engine_mode", None) or cfg.get("engine_mode", "groq")).lower()
        groq_key = (getattr(self, "groq_api_key", "") or cfg.get("groq_api_key", "")).strip()

        if active_mode != "local" and groq_key:
            try:
                return self._transcribe_groq(
                    audio_data,
                    api_key=groq_key,
                    sample_rate=sample_rate,
                    initial_prompt=initial_prompt,
                    language=language
                )
            except Exception as e:
                print(f"[WhisperEngine] Groq API transcription failed: {e}. Falling back to local model.")

        return self._transcribe_local(
            audio_data,
            initial_prompt=initial_prompt,
            language=language
        )

    def transcribe(self, audio_data, sample_rate=16000, initial_prompt=None, style=None, language=None, engine_mode=None, remove_trailing_stop=False):
        if len(audio_data) == 0:
            return ""

        raw_text = self.transcribe_stage1(
            audio_data=audio_data,
            sample_rate=sample_rate,
            initial_prompt=initial_prompt,
            language=language,
            engine_mode=engine_mode
        )

        if remove_trailing_stop and raw_text:
            raw_text = self.clean_stop_keyword(raw_text)

        if not raw_text:
            return ""

        # Coordinate with Stage 2 Romanizer and Stage 3 Replacements
        try:
            from voice_profile import VoiceProfileManager
            from style_engine import StyleEngine

            profile_mgr = VoiceProfileManager.get_instance()
            style_eng = StyleEngine.get_instance()

            if hasattr(style_eng, "format_two_stage"):
                formatted_text = style_eng.format_two_stage(raw_text, style=style, voice_profile=profile_mgr)
                return profile_mgr.apply_replacements(formatted_text)
            elif style is not None:
                styled = style_eng.transform_text(raw_text, target_style=style)
                return profile_mgr.apply_replacements(styled)
        except Exception as e:
            print(f"[WhisperEngine] Style formatting failed: {e}. Returning raw text.")

        return raw_text
```

---

## 7. Test Strategy & Unit Test Cases

The following test suite should be integrated into `tests/test_whisper_engine.py`:

```python
class TestWhisperEngineStage1(unittest.TestCase):
    """Unit tests for Stage 1 Acoustic Capture and failover behaviors."""

    def test_model_name_sanitizes_base_en_to_multilingual_base(self):
        engine = WhisperEngine(model_name="base.en")
        self.assertEqual(engine.model_name, "base")

    @patch("whisper_engine.WhisperModel")
    def test_stage1_local_explicitly_passes_task_transcribe(self, mock_whisper_model):
        mock_instance = MagicMock()
        mock_seg = MagicMock()
        mock_seg.text = "नमस्ते दुनिया"
        mock_instance.transcribe.return_value = ([mock_seg], MagicMock())
        mock_whisper_model.return_value = mock_instance

        engine = WhisperEngine(model_name="base", device="cpu", compute_type="int8")
        engine.model = mock_instance

        dummy_audio = np.ones(16000, dtype=np.float32) * 0.1
        res = engine.transcribe_stage1(dummy_audio, engine_mode="local")

        self.assertEqual(res, "नमस्ते दुनिया")
        mock_instance.transcribe.assert_called_once()
        _, kwargs = mock_instance.transcribe.call_args
        self.assertEqual(kwargs.get("task"), "transcribe", "Must explicitly enforce task='transcribe'")

    @patch("whisper_engine.WhisperModel")
    def test_stage1_auto_language_passes_none(self, mock_whisper_model):
        mock_instance = MagicMock()
        mock_instance.transcribe.return_value = ([], MagicMock())
        mock_whisper_model.return_value = mock_instance

        engine = WhisperEngine(model_name="base", device="cpu")
        engine.model = mock_instance
        dummy_audio = np.ones(16000, dtype=np.float32) * 0.1

        engine.transcribe_stage1(dummy_audio, language="auto", engine_mode="local")
        _, kwargs = mock_instance.transcribe.call_args
        self.assertIsNone(kwargs.get("language"), "Auto language must pass language=None for detection")

    @patch("whisper_engine.WhisperModel")
    def test_stage1_explicit_hindi_language_passed(self, mock_whisper_model):
        mock_instance = MagicMock()
        mock_instance.transcribe.return_value = ([], MagicMock())
        mock_whisper_model.return_value = mock_instance

        engine = WhisperEngine(model_name="base", device="cpu")
        engine.model = mock_instance
        dummy_audio = np.ones(16000, dtype=np.float32) * 0.1

        engine.transcribe_stage1(dummy_audio, language="hi", engine_mode="local")
        _, kwargs = mock_instance.transcribe.call_args
        self.assertEqual(kwargs.get("language"), "hi")

    @patch("whisper_engine.urllib.request.urlopen")
    def test_groq_strictly_targets_transcriptions_endpoint(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"text": "Acoustic raw capture"}'
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        engine = WhisperEngine(groq_api_key="gsk_valid_test_key")
        dummy_audio = np.ones(16000, dtype=np.float32) * 0.1
        res = engine._transcribe_groq(dummy_audio, api_key="gsk_valid_test_key")

        self.assertEqual(res, "Acoustic raw capture")
        req_arg = mock_urlopen.call_args[0][0]
        self.assertEqual(req_arg.full_url, "https://api.groq.com/openai/v1/audio/transcriptions")

    @patch("whisper_engine.load_config")
    def test_engine_mode_local_skips_groq_even_with_api_key(self, mock_load_config):
        mock_load_config.return_value = {"groq_api_key": "gsk_key", "engine_mode": "local"}
        engine = WhisperEngine(groq_api_key="gsk_key", engine_mode="local")

        with patch.object(engine, "_transcribe_groq") as mock_groq, \
             patch.object(engine, "_transcribe_local", return_value="Local CPU text") as mock_local:
            res = engine.transcribe_stage1(np.ones(16000, dtype=np.float32) * 0.1)
            self.assertEqual(res, "Local CPU text")
            mock_groq.assert_not_called()
            mock_local.assert_called_once()
```
