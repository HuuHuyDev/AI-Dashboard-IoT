"""
Unit tests for Event Consumer
Tests event consumption and read model updates
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import json

from app.kafka.event_consumer import EventConsumer
from app.services.read_model_service import ReadModelService


@pytest.fixture
def mock_read_model_service():
    """Mock read model service"""
    service = Mock(spec=ReadModelService)
    service.is_event_processed = AsyncMock(return_value=False)
    service.handle_device_created = AsyncMock()
    service.handle_device_updated = AsyncMock()
    service.handle_log_created = AsyncMock()
    service.handle_stats_updated = AsyncMock()
    service.handle_alert_created = AsyncMock()
    return service


@pytest.fixture
def event_consumer():
    """Event consumer instance"""
    with patch('app.kafka.event_consumer.KafkaConsumer'):
        consumer = EventConsumer()
        return consumer


class TestEventConsumer:
    """Test event consumer"""
    
    @pytest.mark.asyncio
    async def test_handle_device_created_event(self, event_consumer, mock_read_model_service):
        """Test handling device.created event"""
        event = {
            'event_id': '123e4567-e89b-12d3-a456-426614174000',
            'event_type': 'device.created',
            'data': {
                'device_id': 'SENSOR_001',
                'device_name': 'Temperature Sensor 1',
                'device_type': 'temperature',
                'location': 'Room A',
                'status': 'active'
            }
        }
        
        await event_consumer._handle_event(event)
        
        mock_read_model_service.is_event_processed.assert_called_once()
        mock_read_model_service.handle_device_created.assert_called_once_with(
            event['event_id'],
            event['data']
        )
    
    @pytest.mark.asyncio
    async def test_handle_log_created_event(self, event_consumer, mock_read_model_service):
        """Test handling log.created event"""
        event = {
            'event_id': '223e4567-e89b-12d3-a456-426614174001',
            'event_type': 'log.created',
            'data': {
                'log_id': 1,
                'device_id': 'SENSOR_001',
                'temperature': 25.5,
                'humidity': 50.0,
                'pressure': 1013.25,
                'battery_level': 85.0,
                'timestamp': '2024-01-15T10:30:00'
            }
        }
        
        await event_consumer._handle_event(event)
        
        mock_read_model_service.handle_log_created.assert_called_once_with(
            event['event_id'],
            event['data']
        )
    
    @pytest.mark.asyncio
    async def test_skip_already_processed_event(self, event_consumer, mock_read_model_service):
        """Test skipping already processed event (idempotency)"""
        mock_read_model_service.is_event_processed.return_value = True
        
        event = {
            'event_id': '323e4567-e89b-12d3-a456-426614174002',
            'event_type': 'device.created',
            'data': {'device_id': 'SENSOR_001'}
        }
        
        await event_consumer._handle_event(event)
        
        mock_read_model_service.is_event_processed.assert_called_once()
        mock_read_model_service.handle_device_created.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_unknown_event_type(self, event_consumer, mock_read_model_service):
        """Test handling unknown event type"""
        event = {
            'event_id': '423e4567-e89b-12d3-a456-426614174003',
            'event_type': 'unknown.event',
            'data': {}
        }
        
        # Should not raise exception
        await event_consumer._handle_event(event)
        
        mock_read_model_service.is_event_processed.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_stats_updated_event(self, event_consumer, mock_read_model_service):
        """Test handling stats.updated event"""
        event = {
            'event_id': '523e4567-e89b-12d3-a456-426614174004',
            'event_type': 'stats.updated',
            'data': {
                'stat_id': 1,
                'device_id': 'SENSOR_001',
                'date': '2024-01-15',
                'avg_temperature': 25.5,
                'min_temperature': 20.0,
                'max_temperature': 30.0,
                'record_count': 100
            }
        }
        
        await event_consumer._handle_event(event)
        
        mock_read_model_service.handle_stats_updated.assert_called_once_with(
            event['event_id'],
            event['data']
        )
    
    @pytest.mark.asyncio
    async def test_handle_device_updated_event(self, event_consumer, mock_read_model_service):
        """Test handling device.updated event"""
        event = {
            'event_id': '623e4567-e89b-12d3-a456-426614174005',
            'event_type': 'device.updated',
            'data': {
                'device_id': 'SENSOR_001',
                'device_name': 'Updated Sensor Name',
                'location': 'Room B',
                'status': 'inactive'
            }
        }
        
        await event_consumer._handle_event(event)
        
        mock_read_model_service.handle_device_updated.assert_called_once_with(
            event['event_id'],
            event['data']
        )
    
    @pytest.mark.asyncio
    async def test_handle_alert_created_event(self, event_consumer, mock_read_model_service):
        """Test handling alert.created event"""
        event = {
            'event_id': '723e4567-e89b-12d3-a456-426614174006',
            'event_type': 'alert.created',
            'data': {
                'alert_id': 1,
                'device_id': 'SENSOR_001',
                'alert_type': 'high_temperature',
                'severity': 'warning',
                'message': 'Temperature exceeds threshold'
            }
        }
        
        await event_consumer._handle_event(event)
        
        mock_read_model_service.handle_alert_created.assert_called_once_with(
            event['event_id'],
            event['data']
        )


@pytest.mark.asyncio
async def test_event_consumer_lifecycle():
    """Test event consumer start and stop"""
    with patch('app.kafka.event_consumer.KafkaConsumer') as mock_kafka:
        consumer = EventConsumer()
        mock_read_model_service = Mock(spec=ReadModelService)
        
        # Start consumer in background
        task = asyncio.create_task(consumer.start(mock_read_model_service))
        
        # Wait a bit
        await asyncio.sleep(0.1)
        
        # Stop consumer
        consumer.stop()
        
        # Wait for task to complete
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.TimeoutError:
            task.cancel()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
