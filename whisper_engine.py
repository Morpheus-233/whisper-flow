import os
import sys
import threading
import numpy as np

import ctypes

# Ensure NVIDIA CUDA DLLs are found and loaded by CTranslate2 on Windows
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

setup_cuda_dlls()

from faster_whisper import WhisperModel
import ctranslate2

class WhisperEngine:
    _instance = None
    _lock = threading.Lock()

    def __init__(self, model_name="base.en", device="cuda", compute_type="float16"):
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.model = None
        self.is_loading = False
        self._load_lock = threading.Lock()

    @classmethod
    def get_instance(cls, model_name="base.en"):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(model_name=model_name)
            elif cls._instance.model_name != model_name:
                cls._instance.model_name = model_name
                cls._instance.model = None
            return cls._instance

    def load_model(self):
        with self._load_lock:
            if self.model is not None:
                return self.model

            self.is_loading = True
            target_device = self.device
            target_compute = self.compute_type

            # Check CUDA compatibility
            try:
                supported_cuda = ctranslate2.get_supported_compute_types("cuda")
                if not supported_cuda:
                    print("CUDA not available in ctranslate2, falling back to CPU.")
                    target_device = "cpu"
                    target_compute = "int8"
                elif target_compute not in supported_cuda:
                    target_compute = "float16" if "float16" in supported_cuda else "int8_float16"
            except Exception as e:
                print(f"Error checking CUDA types: {e}, falling back to CPU.")
                target_device = "cpu"
                target_compute = "int8"

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
                    download_root=os.path.join(os.path.expanduser("~"), ".cache", "whisper_flow_models")
                )
                self.device = "cpu"
                self.compute_type = "int8"

            self.is_loading = False
            return self.model

    def transcribe(self, audio_data, sample_rate=16000, initial_prompt=None, remove_trailing_stop=False):
        """
        Transcribes audio_data (1D numpy float32 array).
        Returns the formatted transcribed text.
        """
        if self.model is None:
            self.load_model()

        if len(audio_data) == 0:
            return ""

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

