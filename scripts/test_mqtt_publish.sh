#!/bin/bash
# Test MQTT publishing script

echo "Publishing test IoT data to MQTT broker..."

# Publish multiple test messages
for i in {1..5}; do
  mosquitto_pub -h localhost -p 1883 -t "iot/sensors/SENSOR_001" -m "{\"device_id\":\"SENSOR_001\",\"temperature\":22.$i,\"humidity\":45.$i,\"pressure\":1013.25,\"battery_level\":85.5,\"signal_strength\":-65,\"status\":\"normal\"}"
  echo "Published message $i"
  sleep 1
done

echo "Test messages published successfully!"
