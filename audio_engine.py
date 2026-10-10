import sounddevice as sd
import numpy as np
import threading
import time

class AudioEngine:
    def __init__(self, sample_rate=16000, device_index=None):
        self.sample_rate = sample_rate
        self.device_index = device_index
        self.stream = None
        self.is_recording = False
        self.frames = []
        self._lock = threading.Lock()
        self.current_rms = 0.0
        self.start_time = 0

    def get_input_devices(self):
        """Returns list of available audio input devices."""
        devices = sd.query_devices()
        input_devices = []
        for i, dev in enumerate(devices):
            if dev.get('max_input_channels', 0) > 0:
                input_devices.append((i, dev['name']))
        return input_devices

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            pass  # Overflow or underflow handling if necessary
        if self.is_recording:
            # indata shape is (frames, 1)
            audio_chunk = indata[:, 0].copy()
            with self._lock:
                self.frames.append(audio_chunk)
                # Compute RMS volume level for UI visualization
                rms = np.sqrt(np.mean(np.square(audio_chunk)))
                # Exponential moving average for smooth display
                self.current_rms = 0.6 * self.current_rms + 0.4 * float(rms)

    def start_recording(self):
        with self._lock:
            self.frames = []
            self.is_recording = True
            self.current_rms = 0.0
            self.start_time = time.time()

        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass

        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype='float32',
            device=self.device_index,
            callback=self._audio_callback,
            blocksize=1024
        )
        self.stream.start()

    def stop_recording(self):
        if not self.is_recording:
            return np.array([], dtype=np.float32)

        self.is_recording = False
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                print(f"Error closing stream: {e}")
            self.stream = None

        with self._lock:
            if not self.frames:
                return np.array([], dtype=np.float32)
            audio_array = np.concatenate(self.frames, axis=0)
            self.frames = []
            self.current_rms = 0.0
            return audio_array

    def get_current_volume(self):
        """Returns smoothed volume level scaled from 0.0 to 1.0"""
        # RMS of typical voice is around 0.01 - 0.2
        # Scale with non-linear boost for nice visuals
        vol = min(1.0, self.current_rms * 8.0)
        return vol

    def get_recent_audio(self, seconds=2.0):
        """Returns the most recent N seconds of audio recorded so far."""
        with self._lock:
            if not self.frames:
                return np.array([], dtype=np.float32)
            total_samples = int(seconds * self.sample_rate)
            # Collect from end
            accum = []
            count = 0
            for chunk in reversed(self.frames):
                accum.append(chunk)
                count += len(chunk)
                if count >= total_samples:
                    break
            if not accum:
                return np.array([], dtype=np.float32)
            recent = np.concatenate(list(reversed(accum)), axis=0)
            if len(recent) > total_samples:
                recent = recent[-total_samples:]
            return recent

    def get_recording_duration(self):
        if self.is_recording:
            return time.time() - self.start_time
        return 0.0
