"""
Bluetooth Connection Manager
Handles Bluetooth socket connections and data transmission
"""
import socket


class BluetoothManager:
    """Manages Bluetooth RFCOMM socket connection."""
    
    def __init__(self, bt_addr, bt_baud=115200):
        self.bt_addr = bt_addr
        self.bt_baud = bt_baud
        self.socket = None
        self.status = "DISCONNECTED"
        self.recv_buffer = bytearray()
        self.temp_buf = bytearray(1024)
    
    def connect(self):
        """Establish Bluetooth connection."""
        try:
            self.socket = socket.socket(socket.AF_BLUETOOTH,
                                       socket.SOCK_STREAM, 
                                       socket.BTPROTO_RFCOMM)
            self.socket.connect((self.bt_addr, 1))
            self.socket.setblocking(False)
            self.status = "CONNECTED"
            print(f"Connected to Bluetooth device: {self.bt_addr}")
            return True
        except Exception as e:
            print(f"Failed to connect to Bluetooth: {e}")
            self.status = "ERROR"
            self.socket = None
            return False
    
    def send(self, message):
        """Send message over Bluetooth socket."""
        if not self.socket:
            return False
        
        try:
            self.socket.sendall(message.encode("utf-8") if isinstance(message, str) else message)
            return True
        except Exception as e:
            print(f"Send error: {e}")
            self.status = "ERROR"
            return False
    
    def receive_line(self):
        """
        Non-blocking receive that returns complete lines (ending with \\n).
        Returns: line string or None if no complete line available yet.
        """
        if not self.socket:
            return None
        
        try:
            n = self.socket.recv_into(self.temp_buf)
            if n:
                self.recv_buffer.extend(self.temp_buf[:n])
                # Check for newline terminator
                idx = self.recv_buffer.find(b"\n")
                if idx != -1:
                    line = bytes(self.recv_buffer[:idx])
                    del self.recv_buffer[:idx + 1]
                    try:
                        return line.decode('utf-8', errors='replace')
                    except Exception as e:
                        print(f"Decode error: {e}")
                        return None
        except BlockingIOError:
            pass
        except Exception as e:
            print(f"Read error: {e}")
            self.status = "ERROR"
        
        return None
    
    def close(self):
        """Close Bluetooth connection."""
        if self.socket:
            try:
                # Send stop command before closing
                self.socket.sendall(b"+000 +000 +000 +000 000 000 000000000 0 0 0 0 1\n")
            except Exception:
                pass
            
            try:
                self.socket.close()
            except Exception:
                pass
            
            self.socket = None
            self.status = "DISCONNECTED"
    
    def is_connected(self):
        """Check if Bluetooth is connected."""
        return self.socket is not None and self.status == "CONNECTED"
