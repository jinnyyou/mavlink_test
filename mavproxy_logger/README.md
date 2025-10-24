# MAVLink Proxy Forwarder with JSON Logging

A Python-based MAVLink proxy that forwards messages between PX4/ArduPilot and QGroundControl while simultaneously logging all MAVLink messages to JSON format for analysis and debugging.

## Features

- **Dual Output**: Forwards MAVLink messages to both QGroundControl and a JSON logger
- **No Connection Conflicts**: Uses separate UDP ports to avoid interference between QGC and logging
- **Comprehensive Logging**: 
  - Traditional TLOG format via MAVProxy
  - JSON Lines (JSONL) format for easy parsing and analysis
- **Message Metadata**: Captures timestamps, system/component IDs, message types, and full payloads
- **Stable QGC Connection**: Maintains reliable connection to QGroundControl
- **Easy Setup**: Simple Python script with minimal configuration

## Prerequisites

### Required Software

- Python 3.6 or higher
- MAVProxy
- pymavlink

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/jinnyyou/mavlink_test.git
   cd mavlink_test
   ```

2. **Install dependencies**:
   ```bash
   pip install MAVProxy pymavlink
   ```

   Or use a virtual environment (recommended):
   ```bash
   python3 -m venv mavproxy_env
   source mavproxy_env/bin/activate  # On Windows: mavproxy_env\Scripts\activate
   pip install MAVProxy pymavlink
   ```

## Usage

### Basic Usage

Run the proxy with default settings:

```bash
python3 mavlink_proxy_with_json.py
```

Default configuration:
- **PX4 Connection**: `udp:127.0.0.1:14550`
- **QGC Port**: `14551`
- **JSON Logger Port**: `14552`
- **Log Directory**: `logs/`

### Custom Configuration

You can modify the script to use different ports or connections:

```python
forwarder = MAVProxyWithJSON(
    px4_connection='udp:127.0.0.1:14550',  # PX4/ArduPilot connection
    qgc_port=14551,                         # Port for QGroundControl
    json_port=14552,                        # Port for JSON logger
    log_dir='logs'                          # Directory for log files
)
```

### Connecting QGroundControl

1. Start the proxy script
2. Open QGroundControl
3. Go to **Application Settings → Comm Links**
4. Add a new UDP connection:
   - **Server Address**: `127.0.0.1`
   - **Port**: `14551` (or your configured QGC port)
5. Click **Connect**

## Log Files

The script generates two types of log files in the `logs/` directory:

### 1. TLOG Files (MAVProxy Format)

- **Filename**: `mavproxy_log_YYYYMMDD_HHMMSS.tlog`
- **Format**: Binary MAVLink telemetry log
- **Usage**: Compatible with MAVProxy, Mission Planner, and other MAVLink tools

### 2. JSON Lines Files

- **Filename**: `mavlink_messages_YYYYMMDD_HHMMSS.jsonl`
- **Format**: JSON Lines (one JSON object per line)
- **Usage**: Easy parsing with Python, jq, or any JSON-compatible tool

#### JSON Log Format

Each line in the JSONL file contains a complete MAVLink message:

```json
{
  "timestamp": "2024-01-15T10:30:45.123456+00:00",
  "system_id": 1,
  "component_id": 1,
  "msg_id": 33,
  "msg_name": "GLOBAL_POSITION_INT",
  "seq": 42,
  "direction": "RX",
  "payload": {
    "time_boot_ms": 123456,
    "lat": 473977420,
    "lon": 85455940,
    "alt": 5000,
    "relative_alt": 100,
    "vx": 5,
    "vy": -2,
    "vz": -1,
    "hdg": 18000
  }
}
```

## Architecture

```
┌─────────────┐
│   PX4/      │
│  ArduPilot  │
│  :14550     │
└──────┬──────┘
       │
       │ MAVLink Messages
       │
       v
┌─────────────────────────────────────┐
│         MAVProxy Forwarder          │
│  (mavlink_proxy_with_json.py)       │
│                                     │
│  ┌─────────────┐  ┌──────────────┐ │
│  │   TLOG      │  │    JSON      │ │
│  │  Logging    │  │   Logging    │ │
│  └─────────────┘  └──────────────┘ │
└───────┬────────────────┬────────────┘
        │                │
        v                v
┌───────────────┐  ┌──────────────┐
│      QGC      │  │     JSON     │
│    :14551     │  │   Logger     │
└───────────────┘  │   :14552     │
                   └──────────────┘
```

## Analyzing JSON Logs

### Using Python

```python
import json

# Read and parse JSON log
with open('logs/mavlink_messages_20240115_103045.jsonl', 'r') as f:
    for line in f:
        msg = json.loads(line)
        if msg['msg_name'] == 'GLOBAL_POSITION_INT':
            print(f"Position: {msg['payload']['lat']}, {msg['payload']['lon']}")
```

### Using jq (Command Line)

```bash
# Count messages by type
cat logs/mavlink_messages_*.jsonl | jq -r '.msg_name' | sort | uniq -c

# Extract all GPS positions
cat logs/mavlink_messages_*.jsonl | jq 'select(.msg_name == "GLOBAL_POSITION_INT") | .payload'

# Filter by timestamp range
cat logs/mavlink_messages_*.jsonl | jq 'select(.timestamp > "2024-01-15T10:00:00")'
```

## Troubleshooting

### MAVProxy Not Found

If you see "MAVProxy not found", install it:
```bash
pip install MAVProxy
```

### Connection Issues

1. **Check PX4/ArduPilot is running** and outputting MAVLink on port 14550
2. **Verify port availability**: Ensure ports 14551 and 14552 are not in use
3. **Check firewall settings**: Allow UDP traffic on the configured ports

### QGroundControl Can't Connect

1. Ensure the proxy is running first
2. Verify the correct port (14551 by default) in QGC settings
3. Try restarting both the proxy and QGC

### No JSON Logs

1. Check the `logs/` directory exists and is writable
2. Verify the JSON logger thread started (check console output)
3. Ensure MAVLink messages are being received from PX4/ArduPilot

## Development

### Project Structure

```
mavlink_test/
├── mavlink_proxy_with_json.py    # Main proxy script
├── logs/                          # Log files directory (auto-created)
│   ├── mavproxy_log_*.tlog       # Binary telemetry logs
│   └── mavlink_messages_*.jsonl  # JSON message logs
└── README.md                      # This file
```

### Extending the Script

You can extend the script to:
- Filter specific message types
- Add real-time analysis
- Forward to additional outputs
- Implement custom data processing

Example - Filter specific messages:

```python
def log_mavlink_message(self, msg, direction='RX'):
    # Only log certain message types
    if msg.get_type() in ['HEARTBEAT', 'GLOBAL_POSITION_INT', 'ATTITUDE']:
        # ... logging code ...
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source. Please check the repository for license information.

## Support

For issues, questions, or contributions:
- **GitHub Issues**: https://github.com/jinnyyou/mavlink_test/issues
- **MAVProxy Documentation**: https://ardupilot.org/mavproxy/
- **MAVLink Documentation**: https://mavlink.io/

## Acknowledgments

- Built with [MAVProxy](https://github.com/ArduPilot/MAVProxy)
- Uses [pymavlink](https://github.com/ArduPilot/pymavlink)
- Compatible with [PX4](https://px4.io/) and [ArduPilot](https://ardupilot.org/)
- Works with [QGroundControl](http://qgroundcontrol.com/)

---

**Note**: This is a development tool. For production use, implement proper error handling, logging rotation, and security measures as needed for your specific application.
