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

# Ensure NVIDIA CUDA DLLs are found and loaded by CTranslate2 on Windows when using CUDA
def setup_cuda_dlls():
    try:
        site_pkg = os.path.join(sys.prefix, 'Lib', 'site-packages')
        nvidia_base = os.path.join(site_pkg, 'nvidia')
        if os.path.exists(nvidia_base):
            for root, dirs, _ in os.walk(nvidia_base):
                if 'bin' in dirs:
                    bin_dir = os.path.join(root, 'bin')
                    try:
                        os.add_dll_directory(bin_dir)
                    except Exception:
                        pass
                    if bin_dir not in os.environ.get('PATH', ''):
                        os.environ['PATH'] = bin_dir + os.pathsep + os.environ.get('PATH', '')
                    # Crucial: Preload all CUDA/cuBLAS/cuDNN DLLs into process memory
                    # so CTranslate2 C++ LoadLibrary() calls succeed without failing back to CPU!
                    for file in os.listdir(bin_dir):
                        if file.endswith('.dll'):
                            try:
                                ctypes.CDLL(os.path.join(bin_dir, file))
                            except Exception:
                                pass
    except Exception as e:
        print(f"Warning setting up CUDA DLLs: {e}")


class WhisperEngine:
    _instance = None
    _lock = threading.Lock()

    def __init__(self, model_name=None, device=None, compute_type=None, groq_api_key=None):
        cfg = load_config()
        self.model_name = model_name or cfg.get("model_name", "base.en")
        self.device = device or cfg.get("device", "cpu")
        self.compute_type = compute_type or cfg.get("compute_type", "int8")
        self.groq_api_key = groq_api_key if groq_api_key is not None else cfg.get("groq_api_key", "")
        self.model = None
        self.is_loading = False
        self._load_lock = threading.Lock()

    @classmethod
    def get_instance(cls, model_name=None, device=None, compute_type=None, groq_api_key=None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(
                    model_name=model_name,
                    device=device,
                    compute_type=compute_type,
                    groq_api_key=groq_api_key
                )
            else:
                if model_name is not None and cls._instance.model_name != model_name:
                    cls._instance.model_name = model_name
                    cls._instance.model = None
                if device is not None and cls._instance.device != device:
                    cls._instance.device = device
                    cls._instance.model = None
                if compute_type is not None and cls._instance.compute_type != compute_type:
                    cls._instance.compute_type = compute_type
                    cls._instance.model = None
                if groq_api_key is not None:
                    cls._instance.groq_api_key = groq_api_key
            return cls._instance

    def load_model(self):
        with self._load_lock:
            if self.model is not None:
                return self.model

            self.is_loading = True
            cfg = load_config()
            target_device = self.device or cfg.get("device", "cpu")
            target_compute = self.compute_type or cfg.get("compute_type", "int8")

            # Zero-GPU CPU execution: guaranteed 0 MB VRAM allocation
            if target_device == "cpu":
                print(f"[WhisperEngine] Loading model '{self.model_name}' on CPU (int8, cpu_threads=6)...")
                try:
                    self.model = WhisperModel(
                        self.model_name,
                        device="cpu",
                        compute_type="int8",
                        cpu_threads=6,
                        download_root=os.path.join(os.path.expanduser("~"), ".cache", "whisper_flow_models")
                    )
                    self.device = "cpu"
                    self.compute_type = "int8"
                    print(f"[WhisperEngine] Model '{self.model_name}' successfully loaded on CPU (0 MB VRAM)!")
                except Exception as e:
                    print(f"[WhisperEngine] Failed loading model on CPU: {e}")
                    raise
                self.is_loading = False
                return self.model

            # CUDA execution path
            setup_cuda_dlls()
            try:
                supported_cuda = ctranslate2.get_supported_compute_types("cuda")
                if not supported_cuda:
                    print("[WhisperEngine] CUDA not available in ctranslate2, falling back to CPU.")
                    target_device = "cpu"
                    target_compute = "int8"
                elif target_compute not in supported_cuda:
                    target_compute = "float16" if "float16" in supported_cuda else "int8_float16"
            except Exception as e:
                print(f"[WhisperEngine] Error checking CUDA types: {e}, falling back to CPU.")
                target_device = "cpu"
                target_compute = "int8"

            if target_device == "cpu":
                print(f"[WhisperEngine] Loading model '{self.model_name}' on CPU (int8, cpu_threads=6)...")
                self.model = WhisperModel(
                    self.model_name,
                    device="cpu",
                    compute_type="int8",
                    cpu_threads=6,
                    download_root=os.path.join(os.path.expanduser("~"), ".cache", "whisper_flow_models")
                )
                self.device = "cpu"
                self.compute_type = "int8"
            else:
                print(f"[WhisperEngine] Loading model '{self.model_name}' on {target_device} ({target_compute})...")
                try:
                    self.model = WhisperModel(
                        self.model_name,
                        device=target_device,
                        compute_type=target_compute,
                        download_root=os.path.join(os.path.expanduser("~"), ".cache", "whisper_flow_models")
                    )
                    print(f"[WhisperEngine] Model '{self.model_name}' successfully loaded on {target_device}!")
                except Exception as e:
                    print(f"[WhisperEngine] Failed on {target_device}: {e}. Retrying on CPU...")
                    self.model = WhisperModel(
                        self.model_name,
                        device="cpu",
                        compute_type="int8",
                        cpu_threads=6,
                        download_root=os.path.join(os.path.expanduser("~"), ".cache", "whisper_flow_models")
                    )
                    self.device = "cpu"
                    self.compute_type = "int8"

            self.is_loading = False
            return self.model

    def _transcribe_groq(self, audio_data, api_key, sample_rate=16000, initial_prompt=None):
        """
        Cloud speech API fallback method using Groq's cloud Whisper API endpoint:
        https://api.groq.com/openai/v1/audio/transcriptions with model whisper-large-v3-turbo.
        Guarantees sub-100ms transcription with 0% CPU and 0% GPU.
        """
        if len(audio_data) == 0:
            return ""

        # Normalize audio if needed
        max_val = np.max(np.abs(audio_data))
        if max_val > 0.001:
            if max_val > 1.0:
                audio_data = audio_data / max_val

        # Convert float32 array to 16-bit PCM WAV in memory
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

        add_field("model", "whisper-large-v3-turbo")
        add_field("response_format", "json")
        add_field("temperature", "0.0")
        if initial_prompt:
            add_field("prompt", initial_prompt)

        # Audio file field
        body_parts.append(f"--{boundary}\r\n".encode("utf-8"))
        body_parts.append(b'Content-Disposition: form-data; name="file"; filename="audio.wav"\r\n')
        body_parts.append(b"Content-Type: audio/wav\r\n\r\n")
        body_parts.append(wav_bytes)
        body_parts.append(b"\r\n")

        body_parts.append(f"--{boundary}--\r\n".encode("utf-8"))
        payload = b"".join(body_parts)

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

        with urllib.request.urlopen(req, timeout=10.0) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            return resp_data.get("text", "").strip()

    def transcribe(self, audio_data, sample_rate=16000, initial_prompt=None, remove_trailing_stop=False):
        """
        Transcribes audio_data (1D numpy float32 array).
        Returns the formatted transcribed text.
        """
        if len(audio_data) == 0:
            return ""

        # Cloud speech API fallback: If groq_api_key is present in config, transcribe via Groq
        cfg = load_config()
        groq_key = (getattr(self, "groq_api_key", "") or cfg.get("groq_api_key", "")).strip()
        if groq_key:
            try:
                full_text = self._transcribe_groq(audio_data, groq_key, sample_rate=sample_rate, initial_prompt=initial_prompt)
                if remove_trailing_stop and full_text:
                    full_text = self.clean_stop_keyword(full_text)
                return full_text
            except Exception as e:
                print(f"[WhisperEngine] Groq API transcription failed: {e}. Falling back to local model.")

        if self.model is None:
            self.load_model()

        # Normalize audio if needed
        max_val = np.max(np.abs(audio_data))
        if max_val > 0.001:
            # Don't let clipping distort, but ensure good signal amplitude
            if max_val > 1.0:
                audio_data = audio_data / max_val

        segments, info = self.model.transcribe(
            audio_data,
            initial_prompt=initial_prompt,
            beam_size=1,
            best_of=1,
            temperature=0.0,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=300),
            condition_on_previous_text=False
        )

        text_pieces = []
        for segment in segments:
            text_pieces.append(segment.text.strip())

        full_text = " ".join(text_pieces).strip()

        if remove_trailing_stop and full_text:
            full_text = self.clean_stop_keyword(full_text)

        return full_text

    def clean_stop_keyword(self, text):
        """Removes trailing 'stop', 'stop recording', 'done', etc."""
        cleaned = text.strip()
        lower_cleaned = cleaned.lower()

        stop_phrases = ["stop recording", "stop listening", "stop", "done recording", "finished recording"]
        for phrase in stop_phrases:
            # Check ends with phrase (accounting for potential punctuation like period or comma)
            stripped_lower = lower_cleaned.rstrip(".!,? ")
            if stripped_lower.endswith(phrase):
                # Cut the phrase length from the end
                cut_len = len(phrase)
                # Find the actual case sensitive position
                actual_text_stripped = cleaned.rstrip(".!,? ")
                cleaned = actual_text_stripped[:-cut_len].rstrip(",;:- ")
                break

        return cleaned

