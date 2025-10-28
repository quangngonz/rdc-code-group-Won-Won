# @Simple test for send/receive

import socket

s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)

s.connect(('98:d3:02:96:be:1b', 1))

_input = input("Input sth: ")
_recv = bytearray(5)

while (_input != 'end'):
    s.send("Hello")
    # s.send(_input[:5].encode("ascii"))
    s.recv_into(_recv, 5)
    print(_recv)

    _input = input("Input sth: ")

s.close()

# =============================================================================================================

# import bluetooth, subprocess
# import socket

# class BCI(object):
#     """
#     Bluetooth Connection to BCI
#     """
#     socket_ = None
#     bluetooth_address = None
#     connected = False
#     port = 0x001
#     dev_name = None

#     cmds = {}
        

#     status = {
#         0:  'ok',
#         1:  'communication timeout',
#         3:  'checksum error',
#         4:  'unknown command',
#         5:  'invalid access level',
#         8:  'hardware error',
#         10: 'device not ready',
#     }

#     def __init__(self, *args, **kwargs):
#         self.bluetooth_address = kwargs.get("bluetooth_address", None)
#         if self.bluetooth_address is None:
#             self.find()

#     def connect(self):
#         try:         
#             self.socket_ = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
#             #self.socket_ = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP)
#             self.socket_.connect((self.bluetooth_address, self.port))
#             self.connected = True
#         except:
#             self.socket_.close()
#             self.connected = False
#             raise ConnectionError

#     def find(self):
#         dev = self.__class__.__name__
#         print('Searching for ' + dev)
#         nearby_devices = bluetooth.discover_devices(duration=8, lookup_names=True, flush_cache=True)
#         for index, val in enumerate(nearby_devices):
#             addr, name = val
#             if dev in name.upper():
#                 self.dev_name = name
#                 self.bluetooth_address = addr
#                 print('Found BCI: ' + name + ' @', self.bluetooth_address)
#                 return
        
#     def find_bluetooth_services(self):
#         services = bluetooth.find_service(address=self.bluetooth_address)
#         if len(services) > 0:
#             print("found %d services on %s" % (len(services), self.bluetooth_address))
#             print(services)
#         else:
#             print("no services found")
            
#     def close(self):
#         self.socket_.close()
        
# if __name__ == "__main__":
#     try:
#         device = BCI()
#     except:
#         print('No devices BCI found')
    
#     # try:
#     #     print("Trying to connect with "+ device.__class__.__name__)
#     #     device.connect()
#     # except ConnectionError:
#     #     print ('Can\'t connect with ' + device.__class__.__name__)
#     # '''    
#     try:
#         device.find_bluetooth_services()
#     except:
#         print("Some problem occured")
#     # '''
    
#     if device.connected:
#         print('Connected {}'.format(device.dev_name)+ device.__class__.__name__ +'  @', device.bluetooth_address)
