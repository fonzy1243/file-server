import socket

class Client:
    def __init__(self) -> None:
        self.sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.handle = None

    def get_command(self, cmd):
        pass

    def connect(self, addr, port):
        try:
            self.sck.connect((addr, port))
        except:
            print("Error: Connection to server failed. Please check IP address and port number.")

    def disconnect(self):
        try:
            self.sck.close()
        except:
            print("Error: Failed to disconnect. Please check connection to server.")

    def register(self, handle):
        try:
            msg = "REGISTER " + handle
            self.sck.send(msg.encode())
            resp = self.sck.recv(1024).decode
            if resp != "":
                return
        except:
            print("Error: Failed to register.") 
        finally:
            self.handle = handle

    def get_dir(self):
        pass

    def get_file(self, fname):
        pass

    def send_file(self, fname):
        pass

    def get_help(self):
        pass
