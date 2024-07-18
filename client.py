import socket
import sys
import os

class Client:
    def __init__(self) -> None:
        self.sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.handle = None

    def get_command(self, cmd: str):
        try:
            cmd_words = cmd.strip().split()
            command = cmd_words[0]

            if command == "/join" and len(cmd_words) == 3:
                addr = cmd_words[1]
                port = int(cmd_words[2])
                self.connect(addr, port)
            elif command == "/leave" and len(cmd_words) == 1:
                self.disconnect()
            elif command == "/register" and len(cmd_words) == 2:
                handle = cmd_words[1]
                self.register(handle)
            elif command == "/store" and len(cmd_words) == 2:
                fname = cmd_words[1]
                self.send_file(fname)
            elif command == "/dir" and len(cmd_words) == 1:
                self.get_dir()
            elif command == "/get" and len(cmd_words) == 2:
                fname = cmd_words[1]
                self.get_file(fname)
            elif command == "/?" and len(cmd_words) == 1:
                self.get_help()
            else:
                print("Error: Invalid command.")
        except Exception as e:
            print(f"Error: {e}")

    def connect(self, addr, port):
        try:
            self.sck.connect((addr, port))
            print(f"Connected to server at {addr}:{port}.")
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
                raise Exception("Error: Handle already taken.")
        except:
            print("Error: Failed to register.") 
        finally:
            self.handle = handle
            if not os.path.exists(self.handle):
                os.mkdir(self.handle)

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

            with open(f"/{self.handle}/{fname}", "rb") as f:
                self.sck.sendall(str(os.path.getsize(fname)).encode('utf8'))
                self.sck.sendfile(f)
        except FileNotFoundError:
            pass
        except socket.error as e:
            pass

    def get_help(self):
        pass

def main():
    client = Client()

    print("Client launched.")
    while True:
        cmd = input()
        client.get_command(cmd)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Closing client...")
        try:
            sys.exit()
        except SystemExit:
            print("Client closed.")
            os._exit(0)
