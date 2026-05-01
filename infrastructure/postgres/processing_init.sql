-- Processing Service Database Schema
-- Database per Service Pattern - Processing Service owns IoT core data

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Devices Table
CREATE TABLE IF NOT EXISTS devices (
    device_id VARCHAR(100) PRIMARY KEY,
    device_name VARCHAR(255) NOT NULL,
    device_type VARCHAR(100) NOT NULL,
    location VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active',
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes on devices table
CREATE INDEX idx_devices_type ON devices(device_type);
CREATE INDEX idx_devices_status ON devices(status);
CREATE INDEX idx_devices_location ON devices(location);
CREATE INDEX idx_devices_created_at ON devices(created_at DESC);

-- Logs Table (Main IoT Data)
CREATE TABLE IF NOT EXISTS logs (
    log_id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    temperature DECIMAL(5,2),
    humidity DECIMAL(5,2),
    pressure DECIMAL(7,2),
    battery_level DECIMAL(5,2),
    signal_strength INTEGER,
    status VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
);

-- Create indexes for performance optimization
CREATE INDEX idx_logs_device_id ON logs(device_id);
CREATE INDEX idx_logs_timestamp ON logs(timestamp DESC);
CREATE INDEX idx_logs_device_timestamp ON logs(device_id, timestamp DESC);
CREATE INDEX idx_logs_status ON logs(status);
CREATE INDEX idx_logs_created_at ON logs(created_at DESC);

-- Composite index for common queries
CREATE INDEX idx_logs_device_time_temp ON logs(device_id, timestamp, temperature);

-- Daily Statistics Table (Aggregated Data)
CREATE TABLE IF NOT EXISTS daily_stats (
    stat_id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(100) NOT NULL,
    date DATE NOT NULL,
    avg_temperature DECIMAL(5,2),
    min_temperature DECIMAL(5,2),
    max_temperature DECIMAL(5,2),
    avg_humidity DECIMAL(5,2),
    min_humidity DECIMAL(5,2),
    max_humidity DECIMAL(5,2),
    avg_pressure DECIMAL(7,2),
    min_pressure DECIMAL(7,2),
    max_pressure DECIMAL(7,2),
    avg_battery_level DECIMAL(5,2),
    min_battery_level DECIMAL(5,2),
    max_battery_level DECIMAL(5,2),
    record_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE,
    UNIQUE(device_id, date)
);

-- Create indexes for daily_stats
CREATE INDEX idx_daily_stats_device_id ON daily_stats(device_id);
CREATE INDEX idx_daily_stats_date ON daily_stats(date DESC);
CREATE INDEX idx_daily_stats_device_date ON daily_stats(device_id, date DESC);

-- Alerts Table
CREATE TABLE IF NOT EXISTS alerts (
    alert_id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(100) NOT NULL,
    alert_type VARCHAR(100) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    message TEXT,
    threshold_value DECIMAL(10,2),
    actual_value DECIMAL(10,2),
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP,
    acknowledged_by VARCHAR(255),
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
);

-- Create indexes for alerts
CREATE INDEX idx_alerts_device_id ON alerts(device_id);
CREATE INDEX idx_alerts_timestamp ON alerts(timestamp DESC);
CREATE INDEX idx_alerts_severity ON alerts(severity);
CREATE INDEX idx_alerts_acknowledged ON alerts(acknowledged);
CREATE INDEX idx_alerts_resolved ON alerts(resolved);

-- Outbox Table for Transactional Outbox Pattern
CREATE TABLE IF NOT EXISTS outbox_events (
    event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(100) NOT NULL,
    aggregate_type VARCHAR(100) NOT NULL,
    aggregate_id VARCHAR(255) NOT NULL,
    payload JSONB NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP,
    published BOOLEAN DEFAULT FALSE,
    retry_count INTEGER DEFAULT 0,
    last_error TEXT
);

-- Create indexes for outbox
CREATE INDEX idx_outbox_published ON outbox_events(published, created_at);
CREATE INDEX idx_outbox_event_type ON outbox_events(event_type);
CREATE INDEX idx_outbox_aggregate ON outbox_events(aggregate_type, aggregate_id);
CREATE INDEX idx_outbox_created_at ON outbox_events(created_at DESC);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for devices table
CREATE TRIGGER update_devices_updated_at BEFORE UPDATE ON devices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger for daily_stats table
CREATE TRIGGER update_daily_stats_updated_at BEFORE UPDATE ON daily_stats
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to aggregate daily statistics
CREATE OR REPLACE FUNCTION aggregate_daily_stats(target_date DATE)
RETURNS void AS $$
BEGIN
    INSERT INTO daily_stats (
        device_id,
        date,
        avg_temperature,
        min_temperature,
        max_temperature,
        avg_humidity,
        min_humidity,
        max_humidity,
        avg_pressure,
        min_pressure,
        max_pressure,
        avg_battery_level,
        min_battery_level,
        max_battery_level,
        record_count
    )
    SELECT
        device_id,
        target_date,
        AVG(temperature),
        MIN(temperature),
        MAX(temperature),
        AVG(humidity),
        MIN(humidity),
        MAX(humidity),
        AVG(pressure),
        MIN(pressure),
        MAX(pressure),
        AVG(battery_level),
        MIN(battery_level),
        MAX(battery_level),
        COUNT(*)
    FROM logs
    WHERE DATE(timestamp) = target_date
    GROUP BY device_id
    ON CONFLICT (device_id, date) DO UPDATE SET
        avg_temperature = EXCLUDED.avg_temperature,
        min_temperature = EXCLUDED.min_temperature,
        max_temperature = EXCLUDED.max_temperature,
        avg_humidity = EXCLUDED.avg_humidity,
        min_humidity = EXCLUDED.min_humidity,
        max_humidity = EXCLUDED.max_humidity,
        avg_pressure = EXCLUDED.avg_pressure,
        min_pressure = EXCLUDED.min_pressure,
        max_pressure = EXCLUDED.max_pressure,
        avg_battery_level = EXCLUDED.avg_battery_level,
        min_battery_level = EXCLUDED.min_battery_level,
        max_battery_level = EXCLUDED.max_battery_level,
        record_count = EXCLUDED.record_count,
        updated_at = CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- Insert sample devices
INSERT INTO devices (device_id, device_name, device_type, location, status, metadata) VALUES
('SENSOR_001', 'Temperature Sensor 1', 'temperature', 'Building A - Floor 1', 'active', '{"manufacturer": "SensorCorp", "model": "TC-100"}'),
('SENSOR_002', 'Temperature Sensor 2', 'temperature', 'Building A - Floor 2', 'active', '{"manufacturer": "SensorCorp", "model": "TC-100"}'),
('SENSOR_003', 'Humidity Sensor 1', 'humidity', 'Building B - Floor 1', 'active', '{"manufacturer": "HumidTech", "model": "HM-200"}'),
('SENSOR_004', 'Pressure Sensor 1', 'pressure', 'Building C - Basement', 'active', '{"manufacturer": "PressurePro", "model": "PP-300"}'),
('SENSOR_005', 'Multi Sensor 1', 'multi', 'Building A - Roof', 'active', '{"manufacturer": "MultiSense", "model": "MS-500"}')
ON CONFLICT (device_id) DO NOTHING;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO processing_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO processing_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO processing_user;
