#!/usr/bin/env python3
"""Test imports"""
try:
    import pandas as pd
    print('✓ pandas OK')
except ImportError as e:
    print(f'❌ pandas error: {e}')

try:
    import paho.mqtt.client as mqtt
    print('✓ paho-mqtt OK')
except ImportError as e:
    print(f'❌ paho-mqtt error: {e}')

try:
    from tqdm import tqdm
    print('✓ tqdm OK')
except ImportError as e:
    print(f'❌ tqdm error: {e}')

print("Test hoàn thành!")