"""
Unit tests for event publishing functionality
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from app.kafka.event_publisher import EventPublisher
from app.repositories.log_repository import LogRepository
from app.services.outbox_processor import OutboxProcessor


class TestEventPublisher:
    """Test EventPublisher class"""
    
    def test_build_event_envelope(self):
        """Test event envelope building"""
        publisher = EventPublisher()
        
        event = publisher._build_event_envelope(
            event_type="log.created",
            aggregate_type="log",
            aggregate_id="123",
            data={"temperature": 25.5},
            correlation_id="test-correlation-id"
        )
        
        assert event["event_type"] == "log.created"
        assert event["aggregate_type"] == "log"
        assert event["aggregate_id"] == "123"
        assert event["data"]["temperature"] == 25.5
        assert event["metadata"]["correlation_id"] == "test-correlation-id"
        assert event["metadata"]["version"] == "1.0"
        assert "event_id" in event
        assert "timestamp" in event
    
    def test_get_topic_name(self):
        """Test topic name generation"""
        publisher = EventPublisher()
        
        topic = publisher._get_topic_name("device.created")
        assert topic == "processing.device.created"
        
        topic = publisher._get_topic_name("log.created")
        assert topic == "processing.log.created"
    
    @patch('app.kafka.event_publisher.KafkaProducer')
    def test_publish_event_success(self, mock_producer):
        """Test successful event publishing"""
        # Setup mock
        mock_future = Mock()
        mock_producer_instance = Mock()
        mock_producer_instance.send.return_value = mock_future
        mock_producer.return_value = mock_producer_instance
        
        publisher = EventPublisher()
        publisher.producer = mock_producer_instance
        
        # Publish event
        result = publisher.publish_event(
            event_type="log.created",
            aggregate_type="log",
            aggregate_id="123",
            data={"temperature": 25.5}
        )
        
        assert result is True
        mock_producer_instance.send.assert_called_once()
        mock_producer_instance.flush.assert_called_once()
    
    @patch('app.kafka.event_publisher.KafkaProducer')
    def test_publish_log_created(self, mock_producer):
        """Test publish_log_created helper method"""
        mock_producer_instance = Mock()
        mock_producer.return_value = mock_producer_instance
        
        publisher = EventPublisher()
        publisher.producer = mock_producer_instance
        
        log_data = {
            "log_id": 123,
            "device_id": "SENSOR_001",
            "temperature": 25.5
        }
        
        result = publisher.publish_log_created(log_data)
        
        assert result is True
        mock_producer_instance.send.assert_called_once()


class TestLogRepository:
    """Test LogRepository with event publishing"""
    
    @patch('app.repositories.log_repository.Session')
    def test_insert_log_with_outbox(self, mock_session):
        """Test log insertion with outbox event"""
        # Setup mock
        mock_db = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = (
            123, "SENSOR_001", datetime.utcnow(), 25.5, 50.0,
            1013.25, 85.0, -65, "normal", datetime.utcnow()
        )
        mock_db.execute.return_value = mock_result
        
        repository = LogRepository(mock_db)
        
        # Insert log
        log_data = {
            "device_id": "SENSOR_001",
            "temperature": 25.5,
            "humidity": 50.0,
            "pressure": 1013.25,
            "battery_level": 85.0,
            "signal_strength": -65,
            "status": "normal"
        }
        
        log_id, returned_data = repository.insert_log(log_data)
        
        assert log_id == 123
        assert returned_data["device_id"] == "SENSOR_001"
        assert returned_data["temperature"] == 25.5
        
        # Verify outbox event was inserted
        assert mock_db.execute.call_count == 2  # log insert + outbox insert
        mock_db.commit.assert_called_once()
    
    @patch('app.repositories.log_repository.Session')
    def test_get_unpublished_events(self, mock_session):
        """Test getting unpublished events from outbox"""
        # Setup mock
        mock_db = Mock()
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([
            (
                "event-id-1", "log.created", "log", "123",
                '{"temperature": 25.5}', '{"version": "1.0"}',
                datetime.utcnow(), 0
            )
        ]))
        mock_db.execute.return_value = mock_result
        
        repository = LogRepository(mock_db)
        
        # Get unpublished events
        events = repository.get_unpublished_events(limit=10)
        
        assert len(events) == 1
        assert events[0]["event_type"] == "log.created"
        assert events[0]["aggregate_type"] == "log"
        assert events[0]["payload"]["temperature"] == 25.5
    
    @patch('app.repositories.log_repository.Session')
    def test_mark_event_published(self, mock_session):
        """Test marking event as published"""
        mock_db = Mock()
        repository = LogRepository(mock_db)
        
        repository.mark_event_published("event-id-1")
        
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()


class TestOutboxProcessor:
    """Test OutboxProcessor"""
    
    @pytest.mark.asyncio
    @patch('app.services.outbox_processor.SessionLocal')
    @patch('app.services.outbox_processor.event_publisher')
    async def test_process_outbox_events(self, mock_publisher, mock_session):
        """Test processing outbox events"""
        # Setup mocks
        mock_db = Mock()
        mock_session.return_value = mock_db
        
        mock_repository = Mock()
        mock_repository.get_unpublished_events.return_value = [
            {
                "event_id": "event-1",
                "event_type": "log.created",
                "aggregate_type": "log",
                "aggregate_id": "123",
                "payload": {"temperature": 25.5},
                "metadata": {"correlation_id": "test-id"}
            }
        ]
        
        mock_publisher.publish_event.return_value = True
        
        processor = OutboxProcessor()
        
        with patch('app.services.outbox_processor.LogRepository', return_value=mock_repository):
            await processor.process_outbox_events()
        
        # Verify event was published
        mock_publisher.publish_event.assert_called_once()
        mock_repository.mark_event_published.assert_called_once_with("event-1")


class TestEventSchema:
    """Test event schema validation"""
    
    def test_event_schema_structure(self):
        """Test event schema has required fields"""
        publisher = EventPublisher()
        
        event = publisher._build_event_envelope(
            event_type="log.created",
            aggregate_type="log",
            aggregate_id="123",
            data={"temperature": 25.5}
        )
        
        # Required fields
        required_fields = [
            "event_id", "event_type", "aggregate_type", "aggregate_id",
            "timestamp", "service", "data", "metadata"
        ]
        
        for field in required_fields:
            assert field in event, f"Missing required field: {field}"
        
        # Metadata fields
        assert "version" in event["metadata"]
        assert "correlation_id" in event["metadata"]
    
    def test_event_types(self):
        """Test all event types are properly formatted"""
        event_types = [
            "device.created",
            "device.updated",
            "log.created",
            "stats.updated",
            "alert.created"
        ]
        
        for event_type in event_types:
            assert "." in event_type, f"Event type should contain dot: {event_type}"
            parts = event_type.split(".")
            assert len(parts) == 2, f"Event type should have 2 parts: {event_type}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
