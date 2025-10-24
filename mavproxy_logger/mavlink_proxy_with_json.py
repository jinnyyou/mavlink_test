#!/usr/bin/env python3
"""
MAVLink Proxy Forwarder with JSON Logging (Fixed Version)
Uses MAVProxy's built-in capabilities to avoid connection conflicts

This version:
- Uses MAVProxy for forwarding (no connection conflicts)
- Uses MAVProxy's built-in logging for TLOG files
- Adds JSON logging through MAVProxy's output stream
- Maintains QGC connection stability
"""

import subprocess
import time
import os
import signal
import sys
import json
import threading
from datetime import datetime, timezone
from pymavlink import mavutil

class MAVProxyWithJSON:
    def __init__(self,
                 px4_connection='udp:127.0.0.1:14550',
                 qgc_port=14551,
                 json_port=14552,  # Separate port for JSON logging
                 log_dir='logs'):
        """
        Initialize MAVProxy with JSON logging

        Args:
            px4_connection: Connection to PX4
            qgc_port: Port for QGC to connect to
            json_port: Port for JSON logger to connect to
            log_dir: Directory for log files
        """
        self.px4_connection = px4_connection
        self.qgc_port = qgc_port
        self.json_port = json_port
        self.log_dir = log_dir

        # Create log directory
        os.makedirs(log_dir, exist_ok=True)

        # MAVProxy process
        self.mavproxy_process = None

        # JSON logging
        self.json_logger = None
        self.json_log_file = None
        self.json_logging_enabled = True

    def setup_logging(self):
        """Setup MAVProxy logging"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"{self.log_dir}/mavproxy_log_{timestamp}.tlog"

        print(f"✓ MAVProxy logging to: {log_filename}")
        return log_filename

    def setup_json_logging(self):
        """Setup JSON logging for MAVLink messages"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_log_filename = f"{self.log_dir}/mavlink_messages_{timestamp}.jsonl"

        try:
            self.json_log_file = open(json_log_filename, 'w', encoding='utf-8')
            print(f"✓ JSON logging to: {json_log_filename}")
            return True
        except Exception as e:
            print(f"✗ Failed to setup JSON logging: {e}")
            return False

    def make_json_serializable(self, obj):
        """Convert objects to JSON-serializable format"""
        if isinstance(obj, bytearray):
            return obj.decode('utf-8', errors='replace')
        elif isinstance(obj, bytes):
            return obj.decode('utf-8', errors='replace')
        elif isinstance(obj, dict):
            return {key: self.make_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self.make_json_serializable(item) for item in obj]
        elif isinstance(obj, tuple):
            return [self.make_json_serializable(item) for item in obj]
        else:
            return obj

    def log_mavlink_message(self, msg, direction='RX'):
        """Log a MAVLink message to JSON"""
        if not self.json_log_file or not self.json_logging_enabled:
            return

        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            msg_type = msg.get_type()
            msg_id = msg.get_msgId()

            # Prepare message data
            msg_dict = msg.to_dict()

            # Create JSON entry
            json_entry = {
                "timestamp": timestamp,
                "system_id": msg.get_srcSystem(),
                "component_id": msg.get_srcComponent(),
                "msg_id": msg_id,
                "msg_name": msg_type,
                "seq": msg.get_seq(),
                "direction": direction,
                "payload": self.make_json_serializable(msg_dict)
            }

            # Write to JSON file
            self.json_log_file.write(json.dumps(json_entry) + '\n')
            self.json_log_file.flush()

        except Exception as e:
            print(f"✗ JSON logging error: {e}")

    def start_json_logger(self):
        """Start JSON logger thread"""
        if not self.setup_json_logging():
            return False

        def json_logger_thread():
            """JSON logger thread function"""
            try:
                # Connect to MAVProxy's JSON output port
                json_connection = f"udp:127.0.0.1:{self.json_port}"
                master = mavutil.mavlink_connection(json_connection)

                print("✓ JSON logger connected to MAVProxy JSON output")

                while self.json_logging_enabled:
                    try:
                        # Get next message from MAVProxy
                        msg = master.recv_match(blocking=True, timeout=1.0)

                        if msg is None:
                            continue

                        # Log the message
                        self.log_mavlink_message(msg, 'RX')

                    except Exception as e:
                        if self.json_logging_enabled:
                            print(f"✗ JSON logger error: {e}")
                        break

            except Exception as e:
                print(f"✗ JSON logger connection failed: {e}")

        # Start JSON logger thread
        self.json_logger = threading.Thread(target=json_logger_thread, daemon=True)
        self.json_logger.start()

        return True

    def start_mavproxy(self):
        """Start MAVProxy with multiple outputs"""
        log_filename = self.setup_logging()

        # Check for virtual environment
        venv_path = os.path.join(os.path.dirname(__file__), 'mavproxy_env')
        if os.path.exists(venv_path):
            mavproxy_cmd = os.path.join(venv_path, 'bin', 'mavproxy.py')
        else:
            mavproxy_cmd = 'mavproxy.py'

        # MAVProxy command with multiple outputs
        cmd = [
            mavproxy_cmd,
            '--master', self.px4_connection,
            '--out', f'udp:127.0.0.1:{self.qgc_port}',      # QGC connection
            '--out', f'udp:127.0.0.1:{self.json_port}',    # JSON logger connection
            '--logfile', log_filename,
            '--daemon'  # Run in background
        ]

        print("Starting MAVProxy with multiple outputs...")
        print(f"Command: {' '.join(cmd)}")

        try:
            # Start MAVProxy
            self.mavproxy_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Give it time to start
            time.sleep(3)

            if self.mavproxy_process.poll() is None:
                print("✓ MAVProxy started successfully")
                print(f"✓ PX4 connection: {self.px4_connection}")
                print(f"✓ QGC connection: udp:127.0.0.1:{self.qgc_port}")
                print(f"✓ JSON logger connection: udp:127.0.0.1:{self.json_port}")
                print(f"✓ MAVProxy logging to: {log_filename}")

                # Start JSON logger after MAVProxy is ready
                if self.json_logging_enabled:
                    time.sleep(2)  # Wait for MAVProxy to be fully ready
                    self.start_json_logger()

                print("\n📡 QGroundControl Setup:")
                print(f"   1. Open QGC")
                print(f"   2. Go to: Application Settings → Comm Links")
                print(f"   3. Add UDP connection:")
                print(f"      - Server Address: 127.0.0.1")
                print(f"      - Port: {self.qgc_port}")
                print(f"   4. Connect")
                print("\nPress Ctrl+C to stop")
                return True
            else:
                print("✗ Failed to start MAVProxy")
                return False

        except FileNotFoundError:
            print("✗ MAVProxy not found. Please install MAVProxy:")
            print("   pip install MAVProxy")
            return False
        except Exception as e:
            print(f"✗ Error starting MAVProxy: {e}")
            return False

    def run(self):
        """Run the forwarder"""
        if not self.start_mavproxy():
            return

        try:
            # Keep running
            while True:
                time.sleep(1)

                # Check if MAVProxy is still running
                if self.mavproxy_process.poll() is not None:
                    print("✗ MAVProxy stopped unexpectedly")
                    break

        except KeyboardInterrupt:
            print("\n\n✓ Stopping MAVProxy...")
            self.stop()

    def stop(self):
        """Stop MAVProxy and JSON logger"""
        # Stop JSON logging
        if self.json_logging_enabled:
            self.json_logging_enabled = False
            if self.json_log_file:
                self.json_log_file.close()
                print("✓ JSON logging stopped")

        if self.mavproxy_process:
            try:
                # Send SIGTERM to MAVProxy
                self.mavproxy_process.terminate()

                # Wait for it to stop
                try:
                    self.mavproxy_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't stop
                    self.mavproxy_process.kill()
                    self.mavproxy_process.wait()

                print("✓ MAVProxy stopped")

            except Exception as e:
                print(f"Error stopping MAVProxy: {e}")

def main():
    """Main function"""
    print("=" * 70)
    print("MAVLink Proxy Forwarder with JSON Logging (Fixed Version)")
    print("=" * 70)
    print("This version avoids connection conflicts by using separate ports")
    print("for QGC and JSON logging through MAVProxy.")
    print()

    # Create forwarder
    forwarder = MAVProxyWithJSON()

    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n\n✓ Stopping forwarder...")
        forwarder.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Run forwarder
    forwarder.run()

if __name__ == "__main__":
    main()
