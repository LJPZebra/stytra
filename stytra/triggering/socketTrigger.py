import json
import socket
import tempfile
import time

from stytra.triggering import Trigger


class SocketTrigger(Trigger):
    """This trigger uses vanilla python sockets.

    It receives a json file from the Matlab LightSheet programm upon run start.
    """

    def __init__(self, port=5555):
        """Parameters.

        :port: <int or 'auto'> port on which communication will happen.
                        if int : use this in as port number
                        if 'auto' : finds available port and saves to temp file
        """
        self.port = port
        self.protocol_duration = None
        self.scope_config = {}
        super().__init__()

    def check_trigger(self):
        """Check if trigger signal was received."""
        try:
            datab = self.sock.recv(1000)
        except socket.error as error:
            return False

        stringdata = datab.decode("utf-8")
        jsondata = json.loads(stringdata)
        jsondata["TimeReceived"] = time.time()
        self.device_params_queue.put(jsondata)
        return True

    def run(self):
        """Open socket.

        Opens a socket, saves the port used to a temporary file, and waits for
        client connection.
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if type(self.port) is int:
            s.bind(("127.0.0.1", self.port))
        elif self.port == "auto":
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
            
        temp_path = tempfile.gettempdir() + '\\stytra_socket_trigger_port.txt'
        with open(temp_path, "w") as f:
            f.write(f"{self.port}\n")

        s.listen(5)
        print(f"[SocketTrigger] Waiting for connection on port {self.port} ..")
        self.sock, addr = s.accept()
        self.sock.setblocking(False)
        print(f"[SocketTrigger] Connection received from {addr} .")

        super().run()

    def complete(self):
        """Clean up socket upon exit."""
        print("[SocketTrigger] Compete function called.")
        self.sock.close()
        self.temp.close()
