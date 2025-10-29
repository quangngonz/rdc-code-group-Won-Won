import serial.tools.list_ports

# Get all available ports
ports = serial.tools.list_ports.comports()

# Print them out
for port in ports:
    print(f"Device: {port.device}\tDescription: {port.description}")
