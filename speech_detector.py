import threading
import time
import numpy as np

class SpeechDetector:
    def __init__(self, audio_engine, whisper_engine, on_stop_detected_callback):
        self.audio_engine = audio_engine
        self.whisper_engine = whisper_engine
        self.on_stop_detected_callback = on_stop_detected_callback
        self.is_running = False
        self.thread = None

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.is_running = False
        self.thread = None

    def _monitor_loop(self):
        # Allow at least 1.2 seconds of initial speech before checking
        time.sleep(1.2)
        while self.is_running and self.audio_engine.is_recording:
            # Check if total duration >= 1.2s
            if self.audio_engine.get_recording_duration() >= 1.2:
                # Grab recent 1.8 seconds of audio
                recent = self.audio_engine.get_recent_audio(seconds=1.8)
                if len(recent) > 16000 * 0.8:
                    # Check energy / volume to avoid querying on pure silence
                    rms = np.sqrt(np.mean(np.square(recent)))
                    if rms > 0.008:
                        is_stop, text = self.whisper_engine.quick_check_stop(recent)
                        if is_stop and self.is_running:
                            print(f"[SpeechDetector] Detected stop command: '{text}'!")
                            self.is_running = False
                            if self.on_stop_detected_callback:
                                self.on_stop_detected_callback()
                            break

            time.sleep(0.7)
