import os
import sys
import json
import re
import difflib
import io
import email
from email import policy
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler
import mimetypes
import numpy as np

# Apply PyAV metadata_errors compatibility patch for faster_whisper
try:
    import av
    _orig_av_open = av.open
    def _safe_av_open(*args, **kwargs):
        kwargs.pop("metadata_errors", None)
        return _orig_av_open(*args, **kwargs)
    av.open = _safe_av_open
except Exception as e:
    print(f"[StudioServer] Warning applying PyAV patch: {e}")

from whisper_engine import WhisperEngine
from voice_profile import VoiceProfileManager
from calibration_engine import compute_diff, auto_register_misheard_pairs

# Directory paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STUDIO_DIR = os.path.join(BASE_DIR, "studio")
DATA_DIR = os.path.join(BASE_DIR, "data")
CALIBRATION_FILE = os.path.join(DATA_DIR, "calibration_sentences.json")

# Initialize WhisperEngine with CPU int8 and multilingual base model
print("[StudioServer] Initializing WhisperEngine (CPU int8)...")
whisper_engine = WhisperEngine(model_name="base", device="cpu", compute_type="int8")
whisper_engine.load_model()
print("[StudioServer] WhisperEngine ready.")

voice_profile_mgr = VoiceProfileManager.get_instance()


def audio_bytes_to_float32(audio_bytes: bytes) -> np.ndarray:
    """
    Decodes audio bytes (WAV or WebM/Opus) into a 16kHz float32 mono numpy array.
    """
    if not audio_bytes:
        return np.array([], dtype=np.float32)

    # Fast path for standard 16kHz WAV
    if audio_bytes.startswith(b"RIFF"):
        try:
            import scipy.io.wavfile as wavfile
            sr, data = wavfile.read(io.BytesIO(audio_bytes))
            if data.ndim > 1:
                data = data.mean(axis=1)
            if data.dtype == np.int16:
                data = data.astype(np.float32) / 32768.0
            elif data.dtype == np.int32:
                data = data.astype(np.float32) / 2147483648.0
            elif data.dtype == np.uint8:
                data = (data.astype(np.float32) - 128.0) / 128.0
            elif data.dtype != np.float32:
                data = data.astype(np.float32)

            if sr == 16000:
                return data
        except Exception:
            pass

    # Universal path: PyAV via faster_whisper decode_audio
    from faster_whisper.audio import decode_audio
    return decode_audio(io.BytesIO(audio_bytes), sampling_rate=16000)



class StudioRequestHandler(BaseHTTPRequestHandler):
    server_version = "WhisperStudioServer/1.0"

    def log_message(self, format, *args):
        # Clean logging without noise
        sys.stdout.write(f"[StudioServer] {self.address_string()} - {format % args}\n")
        sys.stdout.flush()

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With, X-Target-Sentence")

    def send_json(self, status_code: int, data: dict or list):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        url_path = self.path.split("?")[0]

        if url_path == "/api/sentences":
            self.handle_get_sentences()
        elif url_path == "/api/profile":
            self.handle_get_profile()
        elif url_path in ("/", "/studio", "/studio/", "/index.html", "/studio/index.html"):
            self.serve_studio_html()
        else:
            self.serve_static_file(url_path)

    def do_POST(self):
        url_path = self.path.split("?")[0]

        if url_path == "/api/transcribe":
            self.handle_post_transcribe()
        elif url_path == "/api/add_word":
            self.handle_post_add_word()
        else:
            self.send_json(404, {"error": "Endpoint not found"})

    def handle_get_sentences(self):
        if not os.path.exists(CALIBRATION_FILE):
            self.send_json(404, {"error": "calibration_sentences.json not found"})
            return

        try:
            with open(CALIBRATION_FILE, "r", encoding="utf-8") as f:
                sentences = json.load(f)
            self.send_json(200, sentences)
        except Exception as e:
            self.send_json(500, {"error": f"Failed reading sentences: {str(e)}"})

    def handle_get_profile(self):
        try:
            custom_words = voice_profile_mgr.get_custom_words()
            replacements = voice_profile_mgr.get_replacements()
            self.send_json(200, {
                "custom_words_count": len(custom_words),
                "replacements_count": len(replacements),
                "custom_words": custom_words,
                "word_replacements": replacements
            })
        except Exception as e:
            self.send_json(500, {"error": f"Failed reading profile: {str(e)}"})

    def handle_post_add_word(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self.send_json(400, {"error": "Empty request body"})
                return

            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))

            action_type = data.get("type", "")
            word = data.get("word", "").strip()
            heard = data.get("heard", "").strip()
            target = (data.get("target") or data.get("replacement", "")).strip()

            if action_type == "custom_word" or (word and not heard):
                if not word:
                    self.send_json(400, {"error": "Word is required"})
                    return
                voice_profile_mgr.add_custom_word(word)
                msg = f"Added '{word}' to custom words"
            elif action_type == "replacement" or (heard and target):
                if not heard or not target:
                    self.send_json(400, {"error": "Both heard and target/replacement are required"})
                    return
                voice_profile_mgr.add_replacement(heard, target)
                msg = f"Added replacement rule: '{heard}' -> '{target}'"
            else:
                self.send_json(400, {"error": "Invalid payload format. Provide 'word' or 'heard' and 'target'"})
                return

            custom_words = voice_profile_mgr.get_custom_words()
            replacements = voice_profile_mgr.get_replacements()

            self.send_json(200, {
                "status": "success",
                "message": msg,
                "custom_words_count": len(custom_words),
                "replacements_count": len(replacements)
            })
        except Exception as e:
            self.send_json(500, {"error": f"Failed updating voice profile: {str(e)}"})

    def handle_post_transcribe(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self.send_json(400, {"error": "Empty audio payload"})
                return

            content_type = self.headers.get("Content-Type", "")
            body = self.rfile.read(content_length)

            audio_bytes = b""
            target_text = ""
            phonetic_keywords = []

            # 1. Check if multipart/form-data
            if "multipart/form-data" in content_type:
                msg = email.message_from_bytes(
                    b"Content-Type: " + content_type.encode("utf-8") + b"\r\n\r\n" + body,
                    policy=policy.default
                )
                for part in msg.iter_parts():
                    name = part.get_param("name", header="content-disposition")
                    filename = part.get_filename()
                    if filename or name == "audio":
                        audio_bytes = part.get_payload(decode=True)
                    elif name == "target":
                        target_text = part.get_payload(decode=True).decode("utf-8", errors="replace")
                    elif name == "keywords":
                        try:
                            phonetic_keywords = json.loads(part.get_payload(decode=True).decode("utf-8", errors="replace"))
                        except Exception:
                            phonetic_keywords = []

            # 2. Check if application/json
            elif "application/json" in content_type:
                data = json.loads(body.decode("utf-8"))
                import base64
                audio_b64 = data.get("audio_base64") or data.get("audio", "")
                if audio_b64:
                    if "," in audio_b64:
                        audio_b64 = audio_b64.split(",", 1)[1]
                    audio_bytes = base64.b64decode(audio_b64)
                target_text = data.get("target", "")
                phonetic_keywords = data.get("keywords", [])

            # 3. Raw audio stream
            else:
                audio_bytes = body
                target_text = self.headers.get("X-Target-Sentence", "")

            if not audio_bytes:
                self.send_json(400, {"error": "No audio data extracted from request"})
                return

            # Convert audio bytes to 16kHz float32
            audio_data = audio_bytes_to_float32(audio_bytes)
            if len(audio_data) == 0:
                self.send_json(400, {"error": "Decoded audio is empty"})
                return

            # Prime Whisper token decoder with custom vocabulary
            initial_prompt = voice_profile_mgr.get_initial_prompt()

            # Transcribe using WhisperEngine (CPU int8)
            raw_transcript = whisper_engine.transcribe(
                audio_data,
                initial_prompt=initial_prompt,
                remove_trailing_stop=False
            )

            # Apply phonetic dictionary replacements
            final_transcript = voice_profile_mgr.apply_replacements(raw_transcript)

            # Compute difference and accuracy
            result = compute_diff(target_text, final_transcript, phonetic_keywords)
            self.send_json(200, result)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.send_json(500, {"error": f"Transcription error: {str(e)}"})

    def serve_studio_html(self):
        index_file = os.path.join(STUDIO_DIR, "index.html")
        if not os.path.exists(index_file):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"studio/index.html not found.")
            return

        with open(index_file, "rb") as f:
            content = f.read()

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(content)

    def serve_static_file(self, rel_path: str):
        rel_path = rel_path.lstrip("/")
        if rel_path.startswith("studio/"):
            rel_path = rel_path[len("studio/"):]

        file_path = os.path.join(STUDIO_DIR, rel_path)
        if not os.path.exists(file_path) or os.path.isdir(file_path):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
            return

        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "application/octet-stream"

        with open(file_path, "rb") as f:
            content = f.read()

        self.send_response(200)
        self.send_header("Content-Type", f"{mime_type}; charset=utf-8" if "text" in mime_type else mime_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(content)


def run_server(host="127.0.0.1", port=8000):
    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, StudioRequestHandler)
    print(f"[StudioServer] Local Web Voice Studio running on http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[StudioServer] Shutting down...")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    run_server(port=port)
