"""
Unit and integration tests for Zero-GPU Whisper Engine.
Covers:
- F7: CPU int8 Execution (0 GPU VRAM, cpu_threads=6, greedy decoding)
- F8: Multilingual Model Default ("base" instead of English-only "base.en")
- F9: Groq Cloud Fallback & Failover to local CPU on exception
- F5 (engine-side): Vocabulary Biasing (initial_prompt) injection
- Tier 2 Boundary Cases: Empty audio arrays, volume normalization
"""

import unittest
from unittest.mock import MagicMock, patch
import numpy as np

import config
from whisper_engine import WhisperEngine


class TestWhisperEngineConfig(unittest.TestCase):
    """Tier 1 tests for zero-GPU multilingual configuration defaults."""

    def test_default_config_is_multilingual_base(self):
        # Multilingual "base" is required for bilingual English + Hindi/Hinglish decoding
        self.assertEqual(
            config.DEFAULT_CONFIG.get("model_name"),
            "base",
            "DEFAULT_CONFIG model_name must be multilingual 'base', not English-only 'base.en'"
        )

    def test_default_device_and_compute_type(self):
        self.assertEqual(config.DEFAULT_CONFIG.get("device"), "cpu")
        self.assertEqual(config.DEFAULT_CONFIG.get("compute_type"), "int8")

    def test_whisper_engine_initializes_with_cpu_int8(self):
        engine = WhisperEngine(model_name="base", device="cpu", compute_type="int8")
        self.assertEqual(engine.device, "cpu")
        self.assertEqual(engine.compute_type, "int8")
        self.assertEqual(engine.model_name, "base")


class TestWhisperEngineExecution(unittest.TestCase):
    """Tier 1 & Tier 2 tests for WhisperEngine model loading and transcription."""

    @patch("whisper_engine.WhisperModel")
    def test_cpu_int8_model_loading_parameters(self, mock_whisper_model):
        """Verifies WhisperModel is initialized with device='cpu', compute_type='int8', and cpu_threads=6."""
        mock_instance = MagicMock()
        mock_whisper_model.return_value = mock_instance

        engine = WhisperEngine(model_name="base", device="cpu", compute_type="int8")
        engine.load_model()

        mock_whisper_model.assert_called_once()
        _, kwargs = mock_whisper_model.call_args
        self.assertEqual(kwargs.get("device"), "cpu")
        self.assertEqual(kwargs.get("compute_type"), "int8")
        self.assertEqual(kwargs.get("cpu_threads"), 6)
        self.assertEqual(engine.device, "cpu")

    def test_empty_audio_array_returns_empty_string(self):
        """Tier 2 boundary: 0-length audio input returns empty string without invoking model."""
        engine = WhisperEngine(model_name="base", device="cpu", compute_type="int8")
        engine.model = MagicMock()

        result = engine.transcribe(np.array([], dtype=np.float32))
        self.assertEqual(result, "")
        engine.model.transcribe.assert_not_called()

    @patch("whisper_engine.load_config")
    def test_initial_prompt_biasing_passed_to_transcribe(self, mock_load_config):
        """Tier 1: initial_prompt biasing is forwarded to faster-whisper decoding loop."""
        mock_load_config.return_value = {"groq_api_key": ""}

        engine = WhisperEngine(model_name="base", device="cpu", compute_type="int8")
        mock_model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.text = "Main thodi der mein call karta hoon."
        mock_model.transcribe.return_value = ([mock_segment], MagicMock())
        engine.model = mock_model

        dummy_audio = np.ones(16000, dtype=np.float32) * 0.1
        test_prompt = "Vocabulary: thodi der, call karta hoon, PySide6."

        text = engine.transcribe(dummy_audio, initial_prompt=test_prompt)
        self.assertEqual(text, "Main thodi der mein call karta hoon.")

        mock_model.transcribe.assert_called_once()
        _, kwargs = mock_model.transcribe.call_args
        self.assertEqual(kwargs.get("initial_prompt"), test_prompt)
        # Greedy decoding verification
        self.assertEqual(kwargs.get("beam_size"), 1)
        self.assertEqual(kwargs.get("best_of"), 1)
        self.assertEqual(kwargs.get("temperature"), 0.0)

    @patch("whisper_engine.load_config")
    def test_groq_cloud_fallback_and_failover_to_local_cpu(self, mock_load_config):
        """
        Tier 1 & Tier 2: When groq_api_key is set, engine attempts Groq cloud transcription.
        If Groq raises an exception (network down, rate limit, invalid key), it transparently
        falls back to the local CPU int8 model without crashing or re-raising.
        """
        mock_load_config.return_value = {"groq_api_key": "gsk_test_mock_key"}

        engine = WhisperEngine(model_name="base", device="cpu", compute_type="int8", groq_api_key="gsk_test_mock_key")

        # Mock local model
        mock_local_model = MagicMock()
        mock_local_seg = MagicMock()
        mock_local_seg.text = "Local CPU transcription successful"
        mock_local_model.transcribe.return_value = ([mock_local_seg], MagicMock())
        engine.model = mock_local_model

        dummy_audio = np.ones(16000, dtype=np.float32) * 0.1

        # Case A: Groq succeeds
        with patch.object(engine, "_transcribe_groq", return_value="Groq Cloud transcription"):
            text_groq = engine.transcribe(dummy_audio)
            self.assertEqual(text_groq, "Groq Cloud transcription")
            mock_local_model.transcribe.assert_not_called()

        # Case B: Groq fails with an exception -> transparent fallback to local CPU model
        with patch.object(engine, "_transcribe_groq", side_effect=RuntimeError("Groq API 503 Service Unavailable")):
            text_fallback = engine.transcribe(dummy_audio)
            self.assertEqual(text_fallback, "Local CPU transcription successful")
            mock_local_model.transcribe.assert_called_once()

    def test_audio_normalization_safeguard(self):
        """Tier 2: High amplitude / clipped audio is safely normalized without NaN or Inf."""
        engine = WhisperEngine(model_name="base", device="cpu", compute_type="int8")
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([], MagicMock())
        engine.model = mock_model

        # Audio array with clipping amplitude > 1.0
        clipped_audio = np.array([2.5, -3.0, 1.8, -2.2], dtype=np.float32)
        engine.transcribe(clipped_audio)

        call_args, _ = mock_model.transcribe.call_args
        normalized_audio = call_args[0]
        self.assertTrue(np.max(np.abs(normalized_audio)) <= 1.0)
        self.assertFalse(np.any(np.isnan(normalized_audio)))
        self.assertFalse(np.any(np.isinf(normalized_audio)))


if __name__ == "__main__":
    unittest.main()
