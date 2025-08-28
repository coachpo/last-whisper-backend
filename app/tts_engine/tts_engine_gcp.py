import hashlib
import io
import os
import queue
import threading
import wave
from datetime import datetime

from google.api_core.exceptions import GoogleAPICallError, RetryError
from google.cloud import texttospeech

from app.core.config import settings
from app.core.logging import get_logger
from app.models.enums import TaskStatus

# Setup logger for this module
logger = get_logger(__name__)


class TTSEngine:
    """
    Drop-in replacement for your current TTSEngine, but powered by
    Google Cloud Text-to-Speech using WaveNet fi-FI-Wavenet-B.
    - Same public methods
    - Same request/task queues and status messages
    - Outputs WAV (LINEAR16, mono) at 24 kHz by default
    """

    def __init__(
            self,
            voice_name: str = "fi-FI-Wavenet-B",
            language_code: str = "fi-FI",
            sample_rate_hz: int = 24000,
            speaking_rate: float = 1.0,
            pitch: float = 0.0,
            volume_gain_db: float = 0.0,
            use_ssml: bool = False,
            max_chars_per_request: int = 4500,  # stay safely under API limits
    ):
        logger.info("TTS engine: Initializing Google Cloud Text-to-Speech client...")

        # Configure Google Cloud credentials from pydantic settings
        self._configure_google_credentials()

        # Google TTS client (auth via configured credentials)
        self.client = texttospeech.TextToSpeechClient()

        # Voice & audio configuration
        self.voice_name = voice_name
        self.language_code = language_code
        self.sample_rate_hz = sample_rate_hz
        self.speaking_rate = speaking_rate
        self.pitch = pitch
        self.volume_gain_db = volume_gain_db
        self.use_ssml = use_ssml
        self.max_chars_per_request = max_chars_per_request

        # Queues & worker lifecycle
        self.request_queue = queue.Queue()
        self.task_message_queue = queue.Queue()
        self.is_running = False
        self.worker_thread = None

        # Output directory
        self.output_dir = settings.audio_dir
        os.makedirs(self.output_dir, exist_ok=True)

        logger.info(
            "TTS engine: Google TTS ready "
            f"(voice={self.voice_name}, lang={self.language_code}, sr={self.sample_rate_hz} Hz)"
        )

    # ----------------------- Public API (unchanged) -----------------------

    def get_task_message_queue(self):
        """Returns the task queue for external services to consume task messages"""
        return self.task_message_queue

    def start_service(self):
        """Start the TTS service worker thread"""
        if not self.is_running:
            self.is_running = True
            self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
            self.worker_thread.start()
            logger.info("TTS engine: Service started successfully!")

    def stop_service(self):
        """Stop the TTS service"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join()
            self.worker_thread = None
        logger.info("TTS engine: Service stopped successfully!")

    def submit_request(self, text, custom_filename=None, language="fi"):
        """Submit a text-to-speech conversion request"""
        if not text or not str(text).strip():
            logger.error("Error: Empty text provided")
            return None

        if language not in settings.tts_supported_languages:
            logger.error(
                f"Error: Language '{language}' is not supported. "
                f"Supported languages: {settings.tts_supported_languages}"
            )
            return None

        # Generate filename based on timestamp + hash
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()[:8]

        if custom_filename:
            base_filename = os.path.splitext(custom_filename)[0] + ".wav"
        else:
            base_filename = f"tts_{timestamp}_{text_hash}.wav"

        filename = os.path.join(self.output_dir, base_filename)

        request_id = f"{timestamp}_{text_hash}"
        request = {
            "id": request_id,
            "text": text,
            "filename": filename,
            "language": language,
            "status": "queued",
            "submitted_at": datetime.now(),
        }

        self.request_queue.put_nowait(request)

        # Publish initial task message
        self._publish_task_message(
            request_id,
            filename,
            "queued",
            text=text,
            language=language,
        )

        logger.info(
            f"TTS engine: Request {request_id} submitted and queued. Output file: {filename}"
        )
        return request_id

    def get_queue_size(self):
        """Get the current queue size"""
        return self.request_queue.qsize()

    def get_task_message_queue_size(self):
        """Get the current task queue size"""
        return self.task_message_queue.qsize()

    def get_device_info(self):
        """API 'device' info (mirrors your original signature)"""
        return {
            "device": "google-tts-api",
            "device_type": "api",
            "cuda_available": False,
        }

    def switch_device(self, new_device):
        """Not applicable; present for interface compatibility."""
        logger.info(f"TTS engine: switch_device requested ({new_device}) — ignored for API backend.")
        return False

    # ----------------------- Internal helpers -----------------------

    def _configure_google_credentials(self):
        """Configure Google Cloud credentials from pydantic settings."""
        if settings.google_application_credentials:
            # Set the environment variable for Google Cloud client
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.google_application_credentials
            logger.info(f"TTS engine: Using Google credentials from {settings.google_application_credentials}")
        else:
            # Check if GOOGLE_APPLICATION_CREDENTIALS is already set in environment
            if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                logger.info("TTS engine: Using existing GOOGLE_APPLICATION_CREDENTIALS from environment")
            else:
                logger.warning(
                    "TTS engine: No Google credentials configured. "
                    "Set GOOGLE_APPLICATION_CREDENTIALS environment variable or "
                    "google_application_credentials in settings."
                )

    def _publish_task_message(self, request_id, output_file_path, status, **metadata):
        task_message = {
            "request_id": request_id,
            "output_file_path": output_file_path,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata,
        }
        self.task_message_queue.put_nowait(task_message)

    def _process_queue(self):
        while self.is_running:
            try:
                request = self.request_queue.get(timeout=1)
                self._process_request(request)
                self.request_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing request: {e}")

    def _process_request(self, request):
        try:
            logger.info(f"TTS engine: Processing request {request['id']} with Google TTS...")
            request["status"] = TaskStatus.PROCESSING

            self._publish_task_message(
                request["id"],
                request["filename"],
                TaskStatus.PROCESSING,
                text=request["text"],
                language=request["language"],
                started_at=datetime.now().isoformat(),
                backend="google-tts",
                voice=self.voice_name,
                sample_rate_hz=self.sample_rate_hz,
                speaking_rate=self.speaking_rate,
                pitch=self.pitch,
                volume_gain_db=self.volume_gain_db,
            )

            # Synthesize audio as WAV (LINEAR16 PCM) and write to file
            total_frames = self._synthesize_to_wav(
                text=request["text"], wav_path=request["filename"]
            )

            request["status"] = TaskStatus.COMPLETED
            request["completed_at"] = datetime.now()

            # Publish completion + done
            meta = {
                "text": request["text"],
                "language": request["language"],
                "completed_at": request["completed_at"].isoformat(),
                "file_size": (
                    os.path.getsize(request["filename"])
                    if os.path.exists(request["filename"])
                    else None
                ),
                "sampling_rate": self.sample_rate_hz,
                "frames": total_frames,
                "backend": "google-tts",
                "voice": self.voice_name,
            }
            self._publish_task_message(request["id"], request["filename"], TaskStatus.COMPLETED, **meta)
            self._publish_task_message(request["id"], request["filename"], TaskStatus.DONE, **meta)

            logger.info(
                f"TTS engine: Request {request['id']} completed! Saved: {request['filename']}"
            )

        except (GoogleAPICallError, RetryError) as e:
            request["status"] = TaskStatus.FAILED
            request["error"] = f"Google API error: {e}"
            self._publish_task_message(
                request["id"],
                request["filename"],
                TaskStatus.FAILED,
                text=request["text"],
                language=request["language"],
                error=str(e),
                failed_at=datetime.now().isoformat(),
                backend="google-tts",
            )
            logger.error(f"Request {request['id']} failed (Google API): {e}")
        except Exception as e:
            request["status"] = TaskStatus.FAILED
            request["error"] = str(e)
            self._publish_task_message(
                request["id"],
                request["filename"],
                TaskStatus.FAILED,
                text=request["text"],
                language=request["language"],
                error=str(e),
                failed_at=datetime.now().isoformat(),
                backend="google-tts",
            )
            logger.error(f"Request {request['id']} failed: {e}")

    def _synthesize_to_wav(self, text: str, wav_path: str) -> int:
        """
        Synthesize `text` (or SSML) to a single WAV file at self.sample_rate_hz.
        Handles chunking for long inputs and concatenates audio seamlessly.
        Returns total frames written.
        """
        # Prepare voice and audio params
        voice = texttospeech.VoiceSelectionParams(
            language_code=self.language_code,
            name=self.voice_name,
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,  # raw PCM
            sample_rate_hertz=self.sample_rate_hz,  # request 24kHz
            speaking_rate=self.speaking_rate,
            pitch=self.pitch,
            volume_gain_db=self.volume_gain_db,
        )

        # Chunk text to stay under API limits
        chunks = self._chunk_text(text, self.max_chars_per_request)

        # Collect raw PCM bytes from all chunks
        pcm_bytes = io.BytesIO()
        for chunk in chunks:
            synthesis_input = (
                texttospeech.SynthesisInput(ssml=chunk)
                if self.use_ssml
                else texttospeech.SynthesisInput(text=chunk)
            )
            response = self.client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )
            pcm_bytes.write(response.audio_content)

        raw = pcm_bytes.getvalue()

        # Write a proper WAV header + frames
        os.makedirs(os.path.dirname(wav_path), exist_ok=True)
        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(1)  # Google TTS returns mono
            wf.setsampwidth(2)  # LINEAR16 -> 16-bit (2 bytes)
            wf.setframerate(self.sample_rate_hz)
            wf.writeframes(raw)

        # Return total frames written (bytes / 2 since 16-bit mono)
        return len(raw) // 2

    @staticmethod
    def _chunk_text(text: str, max_chars: int):
        """Simple chunker that respects word boundaries; good enough for short/medium inputs."""
        if len(text) <= max_chars:
            return [text]

        chunks, current = [], []
        length = 0
        for token in text.split():
            # +1 for space when joined (except first)
            add_len = len(token) + (1 if current else 0)
            if length + add_len > max_chars:
                chunks.append(" ".join(current))
                current = [token]
                length = len(token)
            else:
                current.append(token)
                length += add_len
        if current:
            chunks.append(" ".join(current))
        return chunks
