"""Tests for FBTTSService."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os
import tempfile
import shutil

from app.services.tts_fb_service import FBTTSService


class TestFBTTSService:
    """Test cases for FBTTSService."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def tts_service(self, temp_output_dir):
        """Create a TTS service instance for testing."""
        with patch('app.services.tts_fb_service.VitsModel') as mock_model, \
             patch('app.services.tts_fb_service.AutoTokenizer') as mock_tokenizer:
            
            # Mock the model and tokenizer
            mock_model.from_pretrained.return_value = Mock()
            mock_tokenizer.from_pretrained.return_value = Mock()
            
            service = FBTTSService(device="cpu")
            service.output_dir = temp_output_dir
            return service

    def test_init_default_device(self):
        """Test service initialization with default device detection."""
        with patch('app.services.tts_fb_service.VitsModel') as mock_model, \
             patch('app.services.tts_fb_service.AutoTokenizer') as mock_tokenizer, \
             patch('app.services.tts_fb_service.torch') as mock_torch:
            
            # Mock CUDA availability
            mock_torch.cuda.is_available.return_value = False
            mock_torch.device.return_value = "cpu"
            
            mock_model.from_pretrained.return_value = Mock()
            mock_tokenizer.from_pretrained.return_value = Mock()
            
            service = FBTTSService()
            
            assert service.device == "cpu"
            assert service.model is not None
            assert service.tokenizer is not None
            assert service.request_queue is not None
            assert service.task_queue is not None
            assert service.is_running is False
            assert service.worker_thread is None

    def test_init_custom_device(self):
        """Test service initialization with custom device."""
        with patch('app.services.tts_fb_service.VitsModel') as mock_model, \
             patch('app.services.tts_fb_service.AutoTokenizer') as mock_tokenizer, \
             patch('app.services.tts_fb_service.torch') as mock_torch:
            
            mock_torch.device.return_value = "cuda:0"
            mock_model.from_pretrained.return_value = Mock()
            mock_tokenizer.from_pretrained.return_value = Mock()
            
            service = FBTTSService(device="cuda:0")
            
            assert service.device == "cuda:0"
            mock_torch.device.assert_called_with("cuda:0")

    def test_init_cuda_available(self):
        """Test service initialization when CUDA is available."""
        with patch('app.services.tts_fb_service.VitsModel') as mock_model, \
             patch('app.services.tts_fb_service.AutoTokenizer') as mock_tokenizer, \
             patch('app.services.tts_fb_service.torch') as mock_torch:
            
            mock_torch.cuda.is_available.return_value = True
            mock_torch.device.return_value = "cuda:0"
            
            mock_model.from_pretrained.return_value = Mock()
            mock_tokenizer.from_pretrained.return_value = Mock()
            
            service = FBTTSService()
            
            assert service.device == "cuda:0"
            mock_torch.cuda.is_available.assert_called_once()

    def test_get_task_queue(self, tts_service):
        """Test getting the task queue."""
        queue = tts_service.get_task_queue()
        assert queue == tts_service.task_queue

    def test_start_service(self, tts_service):
        """Test starting the TTS service."""
        tts_service.start_service()
        
        assert tts_service.is_running is True
        assert tts_service.worker_thread is not None
        assert tts_service.worker_thread.is_alive()

    def test_start_service_already_running(self, tts_service):
        """Test starting service when already running."""
        tts_service.is_running = True
        
        tts_service.start_service()
        
        # Should not start again
        assert tts_service.is_running is True

    def test_stop_service(self, tts_service):
        """Test stopping the TTS service."""
        # Start service first
        tts_service.start_service()
        assert tts_service.is_running is True
        
        # Stop service
        tts_service.stop_service()
        
        assert tts_service.is_running is False
        assert tts_service.worker_thread is None

    def test_stop_service_not_running(self, tts_service):
        """Test stopping service when not running."""
        tts_service.is_running = False
        tts_service.worker_thread = None
        
        # Should not raise exception
        tts_service.stop_service()
        
        assert tts_service.is_running is False

    def test_submit_request_success(self, tts_service):
        """Test successful request submission."""
        text = "Test text for TTS"
        custom_filename = "test_audio"
        
        request_id = tts_service.submit_request(text, custom_filename)
        
        assert request_id is not None
        assert isinstance(request_id, str)
        assert len(request_id) > 0
        
        # Check that request was added to queue
        assert tts_service.request_queue.qsize() == 1
        
        # Check that task message was published
        assert tts_service.task_queue.qsize() == 1

    def test_submit_request_empty_text(self, tts_service):
        """Test request submission with empty text."""
        result = tts_service.submit_request("", "test")
        assert result is None
        
        result = tts_service.submit_request("   ", "test")
        assert result is None

    def test_submit_request_without_custom_filename(self, tts_service):
        """Test request submission without custom filename."""
        text = "Test text"
        
        request_id = tts_service.submit_request(text)
        
        assert request_id is not None
        
        # Check that request was added to queue
        assert tts_service.request_queue.qsize() == 1

    def test_submit_request_filename_generation(self, tts_service):
        """Test automatic filename generation."""
        text = "Test text"
        
        request_id = tts_service.submit_request(text)
        
        # Get the request from queue to check filename
        request = tts_service.request_queue.get()
        
        assert request["filename"].endswith(".wav")
        assert "tts_" in request["filename"]
        assert request_id in request["filename"]

    def test_submit_request_custom_filename_extension(self, tts_service):
        """Test custom filename with extension handling."""
        text = "Test text"
        custom_filename = "test_audio.wav"
        
        request_id = tts_service.submit_request(text, custom_filename)
        
        # Get the request from queue to check filename
        request = tts_service.request_queue.get()
        
        # Should remove extension and add .wav
        assert request["filename"].endswith("test_audio.wav")

    def test_publish_task_message(self, tts_service):
        """Test publishing task messages."""
        request_id = "test_123"
        output_file_path = "/tmp/test.wav"
        status = "queued"
        metadata = {"text": "Test text"}
        
        tts_service._publish_task_message(request_id, output_file_path, status, **metadata)
        
        # Check that message was added to task queue
        assert tts_service.task_queue.qsize() == 1
        
        # Get message and verify content
        message = tts_service.task_queue.get()
        assert message["request_id"] == request_id
        assert message["output_file_path"] == output_file_path
        assert message["status"] == status
        assert message["metadata"]["text"] == "Test text"
        assert "timestamp" in message

    def test_get_queue_size(self, tts_service):
        """Test getting request queue size."""
        # Add some requests
        tts_service.submit_request("Text 1")
        tts_service.submit_request("Text 2")
        
        size = tts_service.get_queue_size()
        assert size == 2

    def test_get_task_queue_size(self, tts_service):
        """Test getting task queue size."""
        # Add some task messages
        tts_service._publish_task_message("test1", "/tmp/test1.wav", "queued")
        tts_service._publish_task_message("test2", "/tmp/test2.wav", "queued")
        
        size = tts_service.get_task_queue_size()
        assert size == 2

    def test_get_device_info_cpu(self, tts_service):
        """Test getting device information for CPU."""
        with patch('app.services.tts_fb_service.torch') as mock_torch:
            mock_torch.cuda.is_available.return_value = False
            
            device_info = tts_service.get_device_info()
            
            assert device_info["device"] == "cpu"
            assert device_info["device_type"] == "cpu"
            assert device_info["cuda_available"] is False
            assert "cuda_device_count" not in device_info

    def test_get_device_info_cuda(self, tts_service):
        """Test getting device information for CUDA."""
        tts_service.device = Mock()
        tts_service.device.type = "cuda"
        
        with patch('app.services.tts_fb_service.torch') as mock_torch:
            mock_torch.cuda.is_available.return_value = True
            mock_torch.cuda.device_count.return_value = 2
            mock_torch.cuda.get_device_name.return_value = "GeForce RTX 3080"
            mock_torch.cuda.memory_allocated.return_value = 1024
            mock_torch.cuda.memory_reserved.return_value = 2048
            
            device_info = tts_service.get_device_info()
            
            assert device_info["device_type"] == "cuda"
            assert device_info["cuda_available"] is True
            assert device_info["cuda_device_count"] == 2
            assert device_info["cuda_device_name"] == "GeForce RTX 3080"
            assert device_info["cuda_memory_allocated"] == 1024
            assert device_info["cuda_memory_reserved"] == 2048

    def test_switch_device_success(self, tts_service):
        """Test successful device switching."""
        old_device = tts_service.device
        
        with patch('app.services.tts_fb_service.torch') as mock_torch:
            mock_torch.device.return_value = "cuda:0"
            
            success = tts_service.switch_device("cuda:0")
            
            assert success is True
            assert tts_service.device != old_device
            assert tts_service.device == "cuda:0"

    def test_switch_device_failure(self, tts_service):
        """Test device switching failure."""
        old_device = tts_service.device
        
        # Mock model.to to raise exception
        tts_service.model.to.side_effect = Exception("Device switch failed")
        
        success = tts_service.switch_device("invalid_device")
        
        assert success is False
        assert tts_service.device == old_device  # Should remain unchanged

    @patch('app.services.tts_fb_service.scipy.io.wavfile.write')
    def test_process_request_success(self, mock_wavfile_write, tts_service):
        """Test successful request processing."""
        # Mock the model output
        mock_waveform = Mock()
        mock_waveform.squeeze.return_value.cpu.return_value.numpy.return_value = [0.1, 0.2, 0.3]
        tts_service.model.return_value.waveform = mock_waveform
        tts_service.model.config.sampling_rate = 22050
        
        # Create a test request
        request = {
            "id": "test_123",
            "text": "Test text",
            "filename": os.path.join(tts_service.output_dir, "test.wav"),
            "status": "queued"
        }
        
        # Process the request
        tts_service._process_request(request)
        
        # Check that status was updated
        assert request["status"] == "completed"
        assert "completed_at" in request
        
        # Check that audio file was saved
        mock_wavfile_write.assert_called_once()
        
        # Check that task messages were published
        assert tts_service.task_queue.qsize() >= 2  # processing + completed + done

    def test_process_request_failure(self, tts_service):
        """Test request processing failure."""
        # Mock the model to raise exception
        tts_service.model.side_effect = Exception("Model error")
        
        # Create a test request
        request = {
            "id": "test_123",
            "text": "Test text",
            "filename": os.path.join(tts_service.output_dir, "test.wav"),
            "status": "queued"
        }
        
        # Process the request
        tts_service._process_request(request)
        
        # Check that status was updated to failed
        assert request["status"] == "failed"
        assert "error" in request
        
        # Check that failure task message was published
        assert tts_service.task_queue.qsize() >= 1

    def test_process_request_processing_status(self, tts_service):
        """Test that processing status is published during request processing."""
        # Mock the model to take some time
        tts_service.model.return_value.waveform = Mock()
        tts_service.model.return_value.waveform.squeeze.return_value.cpu.return_value.numpy.return_value = [0.1, 0.2]
        tts_service.model.config.sampling_rate = 22050
        
        # Create a test request
        request = {
            "id": "test_123",
            "text": "Test text",
            "filename": os.path.join(tts_service.output_dir, "test.wav"),
            "status": "queued"
        }
        
        # Process the request
        tts_service._process_request(request)
        
        # Check that processing status was published
        # Get all messages from task queue
        messages = []
        while not tts_service.task_queue.empty():
            messages.append(tts_service.task_queue.get())
        
        # Should have processing, completed, and done messages
        statuses = [msg["status"] for msg in messages]
        assert "processing" in statuses
        assert "completed" in statuses
        assert "done" in statuses

    def test_worker_thread_processing(self, tts_service):
        """Test worker thread processing."""
        # Start the service
        tts_service.start_service()
        
        # Submit a request
        tts_service.submit_request("Test text")
        
        # Wait a bit for processing
        import time
        time.sleep(0.1)
        
        # Stop the service
        tts_service.stop_service()
        
        # Check that request was processed
        assert tts_service.request_queue.qsize() == 0

    def test_worker_thread_empty_queue(self, tts_service):
        """Test worker thread behavior with empty queue."""
        # Start the service
        tts_service.start_service()
        
        # Wait a bit
        import time
        time.sleep(0.1)
        
        # Stop the service
        tts_service.stop_service()
        
        # Should not crash with empty queue

    def test_worker_thread_exception_handling(self, tts_service):
        """Test worker thread exception handling."""
        # Mock _process_request to raise exception
        tts_service._process_request = Mock(side_effect=Exception("Processing error"))
        
        # Start the service
        tts_service.start_service()
        
        # Submit a request
        tts_service.submit_request("Test text")
        
        # Wait a bit for processing
        import time
        time.sleep(0.1)
        
        # Stop the service
        tts_service.stop_service()
        
        # Should not crash due to exception

    def test_output_directory_creation(self, tts_service):
        """Test that output directory is created if it doesn't exist."""
        # Remove output directory if it exists
        if os.path.exists(tts_service.output_dir):
            shutil.rmtree(tts_service.output_dir)
        
        # Create new service (should create output directory)
        with patch('app.services.tts_fb_service.VitsModel') as mock_model, \
             patch('app.services.tts_fb_service.AutoTokenizer') as mock_tokenizer:
            
            mock_model.from_pretrained.return_value = Mock()
            mock_tokenizer.from_pretrained.return_value = Mock()
            
            service = FBTTSService(device="cpu")
            service.output_dir = tts_service.output_dir
            
            # Check that directory was created
            assert os.path.exists(service.output_dir)

    def test_request_id_uniqueness(self, tts_service):
        """Test that request IDs are unique."""
        # Submit multiple requests
        request_ids = set()
        for i in range(10):
            request_id = tts_service.submit_request(f"Text {i}")
            request_ids.add(request_id)
        
        # All IDs should be unique
        assert len(request_ids) == 10

    def test_filename_uniqueness(self, tts_service):
        """Test that filenames are unique."""
        # Submit multiple requests
        filenames = set()
        for i in range(5):
            request_id = tts_service.submit_request(f"Text {i}")
            
            # Get filename from request
            request = tts_service.request_queue.get()
            filenames.add(request["filename"])
        
        # All filenames should be unique
        assert len(filenames) == 5

    def test_metadata_in_task_messages(self, tts_service):
        """Test that metadata is properly included in task messages."""
        text = "Test text with metadata"
        
        request_id = tts_service.submit_request(text)
        
        # Get all task messages
        messages = []
        while not tts_service.task_queue.empty():
            messages.append(tts_service.task_queue.get())
        
        # Check that metadata is included
        for message in messages:
            assert "metadata" in message
            if "text" in message["metadata"]:
                assert message["metadata"]["text"] == text
