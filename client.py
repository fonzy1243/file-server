import socket
import struct
import os

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
            self.sck.send(f"REGISTER {handle}".encode())
            resp = self.sck.recv(1024).decode()
            if resp != "":
                return
        except:
            print("Error: Failed to register.") 
        finally:
            self.handle = handle

    def get_dir(self):
        try:
            self.sck.send("DIR".encode())
            resp = self.sck.recv(1024).decode()
            print("Directory:\n")
            print(resp)
        except:
            pass

    def get_file(self, fname):
        try:
            self.sck.send(f"GET {fname}".encode())
        except:
            pass

    def send_file(self, fname):
        try:
            self.sck.send(f"SEND {fname}".encode())

            with open(f"/s_files/{fname}", "rb") as f:
                self.sck.sendall(str(os.path.getsize(fname)).encode('utf8'))
                self.sck.sendfile(f)
        except FileNotFoundError:
            pass
        except socket.error as e:
            pass

    def get_help(self):
        pass
