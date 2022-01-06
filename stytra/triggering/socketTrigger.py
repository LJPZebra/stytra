import socket
import json
import time

from stytra.triggering import Trigger

class SocketTrigger(Trigger):
    """This trigger uses vanilla python sockets.

        It receives a json file from the Matlab LightSheet programm upon run start.
    """

    def __init__(self,port=5555):
        """Parameters.

        :port: <int> port on which communication will happen.
        """
        self.port = port
        self.protocol_duration = None
        self.scope_config = {}
        super().__init__()

    def check_trigger(self):
        try:
            datab = self.sock.recv(1000)
        except socket.error as error:
            return False

        stringdata = datab.decode('utf-8')
        jsondata = json.loads(stringdata)
        jsondata['TimeReceived'] = time.time()
        self.device_params_queue.put(jsondata)
        return True

    def run(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('127.0.0.1',self.port))
        
        s.listen(5)
        print('[SocketTrigger] Waiting for connection...')
        self.sock, addr = s.accept()
        self.sock.setblocking(False)
        print(f'[SocketTrigger] Connection received from {addr} .')

        super().run()

    def complete(self):
        print("[SocketTrigger] Compete function called.")
        self.sock.close()





