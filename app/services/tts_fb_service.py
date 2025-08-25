import hashlib
import os
import queue
import threading
from datetime import datetime

import scipy
import torch
from transformers import AutoTokenizer, VitsModel


class FBTTSService:
    def __init__(self, device=None):
        print("Loading TTS model...")

        # Device detection and setup
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        print(f"Using device: {self.device}")

        # Load model and tokenizer
        self.model = VitsModel.from_pretrained("facebook/mms-tts-fin")
        self.tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-fin")

        # Move model to the specified device
        self.model = self.model.to(self.device)

        self.request_queue = queue.Queue()
        # New task queue for external services to consume
        self.task_queue = queue.Queue()
        self.is_running = False
        self.worker_thread = None

        # Create output directory if it doesn't exist
        self.output_dir = "output"
        os.makedirs(self.output_dir, exist_ok=True)

        print(f"TTS model loaded successfully on {self.device}!")

    def get_task_queue(self):
        """Returns the task queue for external services to consume task messages"""
        return self.task_queue

    def start_service(self):
        """Start the TTS service worker thread"""
        if not self.is_running:
            self.is_running = True
            self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
            self.worker_thread.start()
            print("TTS service started!")

    def stop_service(self):
        """Stop the TTS service"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join()
            self.worker_thread = None
        print("TTS service stopped!")

    def submit_request(self, text, custom_filename=None):
        """Submit a text-to-speech conversion request"""
        if not text.strip():
            print("Error: Empty text provided")
            return None

        # Generate filename based on timestamp and text hash
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]

        if custom_filename:
            # Remove extension if provided and add .wav
            base_filename = os.path.splitext(custom_filename)[0] + ".wav"
        else:
            base_filename = f"tts_{timestamp}_{text_hash}.wav"

        # Save to output directory
        filename = os.path.join(self.output_dir, base_filename)

        request_id = f"{timestamp}_{text_hash}"
        request = {
            "id": request_id,
            "text": text,
            "filename": filename,
            "status": "queued",
            "submitted_at": datetime.now(),
        }

        self.request_queue.put(request)

        # Publish initial task message to external queue
        self._publish_task_message(request_id, filename, "queued", text=text)

        print(f"Request {request_id} submitted and queued. Output file: {filename}")
        return request_id

    def _publish_task_message(self, request_id, output_file_path, status, **metadata):
        """Publish a task message to the external task queue"""
        task_message = {
            "request_id": request_id,
            "output_file_path": output_file_path,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata,
        }
        self.task_queue.put(task_message)

    def _process_queue(self):
        """Worker thread function to process queued requests"""
        while self.is_running:
            try:
                # Get request from queue with timeout
                request = self.request_queue.get(timeout=1)
                self._process_request(request)
                self.request_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error processing request: {e}")

    def _process_request(self, request):
        """Process a single TTS request"""
        try:
            print(f"Processing request {request['id']} on {self.device}...")
            request["status"] = "processing"

            # Publish processing status
            self._publish_task_message(
                request["id"],
                request["filename"],
                "processing",
                text=request["text"],
                started_at=datetime.now().isoformat(),
                device=str(self.device),
            )

            # Tokenize the text and move to device
            inputs = self.tokenizer(request["text"], return_tensors="pt")
            # Move input tensors to the same device as the model
            inputs = {key: value.to(self.device) for key, value in inputs.items()}

            # Generate audio
            with torch.no_grad():
                output = self.model(**inputs).waveform
                audio_data = output.squeeze().cpu().numpy()

            # Save audio file
            scipy.io.wavfile.write(
                request["filename"], rate=self.model.config.sampling_rate, data=audio_data
            )

            request["status"] = "completed"
            request["completed_at"] = datetime.now()

            # Publish completion status
            self._publish_task_message(
                request["id"],
                request["filename"],
                "completed",
                text=request["text"],
                completed_at=request["completed_at"].isoformat(),
                file_size=(
                    os.path.getsize(request["filename"])
                    if os.path.exists(request["filename"])
                    else None
                ),
                sampling_rate=self.model.config.sampling_rate,
                device=str(self.device),
            )

            # Send 'done' message to indicate task is fully finished
            self._publish_task_message(
                request["id"],
                request["filename"],
                "done",
                text=request["text"],
                completed_at=request["completed_at"].isoformat(),
                file_size=(
                    os.path.getsize(request["filename"])
                    if os.path.exists(request["filename"])
                    else None
                ),
                sampling_rate=self.model.config.sampling_rate,
                device=str(self.device),
            )

            print(f"Request {request['id']} completed! Audio saved as: {request['filename']}")

        except Exception as e:
            request["status"] = "failed"
            request["error"] = str(e)

            # Publish failure status
            self._publish_task_message(
                request["id"],
                request["filename"],
                "failed",
                text=request["text"],
                error=str(e),
                failed_at=datetime.now().isoformat(),
                device=str(self.device),
            )
            print(f"Request {request['id']} failed: {e}")

    def get_queue_size(self):
        """Get the current queue size"""
        return self.request_queue.qsize()

    def get_task_queue_size(self):
        """Get the current task queue size"""
        return self.task_queue.qsize()

    def get_device_info(self):
        """Get information about the current device being used"""
        device_info = {
            "device": str(self.device),
            "device_type": self.device.type,
            "cuda_available": torch.cuda.is_available(),
        }

        if torch.cuda.is_available() and self.device.type == "cuda":
            device_info.update(
                {
                    "cuda_device_count": torch.cuda.device_count(),
                    "cuda_device_name": torch.cuda.get_device_name(self.device),
                    "cuda_memory_allocated": torch.cuda.memory_allocated(self.device),
                    "cuda_memory_reserved": torch.cuda.memory_reserved(self.device),
                }
            )

        return device_info

    def switch_device(self, new_device):
        """Switch the model to a different device (CPU/GPU)"""
        try:
            old_device = self.device
            self.device = torch.device(new_device)
            self.model = self.model.to(self.device)
            print(f"Successfully switched from {old_device} to {self.device}")
            return True
        except Exception as e:
            print(f"Failed to switch to {new_device}: {e}")
            return False


def task_consumer_example(task_queue):
    """Example function demonstrating how to consume task messages from the queue"""
    print("\n=== Task Consumer Example ===")
    print("Monitoring task queue for messages...")

    while True:
        try:
            # Get task message from queue (with timeout to avoid blocking forever)
            task_message = task_queue.get(timeout=2)

            # Process the task message
            print("\nReceived task message:")
            print(f"  Request ID: {task_message['request_id']}")
            print(f"  Output File: {task_message['output_file_path']}")
            print(f"  Status: {task_message['status']}")
            print(f"  Timestamp: {task_message['timestamp']}")

            # Access additional metadata
            if task_message["metadata"]:
                print(f"  Metadata: {task_message['metadata']}")

            # Mark task as done
            task_queue.task_done()

        except queue.Empty:
            # No more messages in queue
            print("No more task messages in queue")
            break
        except Exception as e:
            print(f"Error consuming task message: {e}")


def main():
    # Create and start the TTS service with automatic device detection
    print("=== TTS Service with GPU/CPU Support ===")
    tts_service = FBTTSService()

    # Display device information
    device_info = tts_service.get_device_info()
    print("\nDevice Information:")
    for key, value in device_info.items():
        print(f"  {key}: {value}")

    tts_service.start_service()

    # Get reference to the task queue for external consumption
    task_queue = tts_service.get_task_queue()

    # Example usage
    sample_text = """
    Tallink Silja Serenaden yllättävä kallistuminen aiheutti keskellä tiistain ja keskiviikon välistä yötä vaaralliselta näyttävän tilanteen Ahvenanmaan lähellä. Yle sai tapahtumasta hurjia kuvia, joissa näkyy rikkoutuneita viinipulloja, posliini- ja tarjoilu-astioita. Tallink Siljan viestintäjohtajan Marika Nöjdin mukaan kallistus ei aiheuttanut vaaratilannetta.
    """

    print("\n=== TTS Service Demo ===")

    # Submit multiple requests to demonstrate queue functionality
    request1 = tts_service.submit_request(sample_text, "news_report")
    request2 = tts_service.submit_request("Tervetuloa Suomeen!", "welcome_message")
    request3 = tts_service.submit_request("Kiitos ja näkemiin!", "goodbye_message")

    print(f"\nRequest queue size: {tts_service.get_queue_size()} requests pending")
    print(f"Task queue size: {tts_service.get_task_queue_size()} task messages available")

    # Demonstrate task queue consumption
    import time

    time.sleep(2)  # Give some time for processing
    task_consumer_example(task_queue)

    # Interactive mode
    print("\n=== Interactive Mode ===")
    print("Enter text to convert to speech")
    print(
        "Commands: 'quit' to exit, 'status' for queue status, 'device' for device info, 'switch cpu/cuda' to change device"
    )

    try:
        while True:
            user_input = input("\nText: ").strip()

            if user_input.lower() == "quit":
                break
            elif user_input.lower() == "status":
                print(f"Request queue size: {tts_service.get_queue_size()} requests pending")
                print(
                    f"Task queue size: {tts_service.get_task_queue_size()} task messages available"
                )
            elif user_input.lower() == "device":
                device_info = tts_service.get_device_info()
                print("Current device information:")
                for key, value in device_info.items():
                    print(f"  {key}: {value}")
            elif user_input.lower().startswith("switch "):
                new_device = user_input[7:].strip()
                if new_device in ["cpu", "cuda"]:
                    success = tts_service.switch_device(new_device)
                    if success:
                        print(f"Device switched to {new_device}")
                    else:
                        print(f"Failed to switch to {new_device}")
                else:
                    print("Invalid device. Use 'switch cpu' or 'switch cuda'")
            elif user_input.lower() == "consume":
                task_consumer_example(task_queue)
            elif user_input:
                custom_name = input("Custom filename (optional, press Enter for auto): ").strip()
                filename = custom_name if custom_name else None
                tts_service.submit_request(user_input, filename)
            else:
                print("Please enter some text!")

    except KeyboardInterrupt:
        print("\nShutting down...")

    # Stop the service
    tts_service.stop_service()
    print("Service stopped. Goodbye!")


if __name__ == "__main__":
    main()
