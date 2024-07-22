import socket
import sys
import os

COMMANDS = [

]

HANDLE_REQUIRED = [
    "/store", "/dir", "/get"
]

class Client:
    def __init__(self) -> None:
        self.sck: socket.socket
        self.handle = None
        self.connected = False

    def get_command(self, cmd: str):
        try:
            cmd_words = cmd.strip().split()
            command = cmd_words[0]

            if command != "/join" and self.connected == False:
                raise Exception("You are not connected to the server.")

            if command in HANDLE_REQUIRED and self.handle is None:
                raise Exception("You must be registered to use this command.")

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
        except Exception as e:
            print(f"Error: {e}")

    def connect(self, addr, port):
        try:
            self.sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sck.connect((addr, port))
            self.connected = True
            print(f"Connected to server at {addr}:{port}.")
        except:
            print("Error: Connection to server failed. Please check IP address and port number.")

    def disconnect(self):
        try:
            self.sck.close()
            self.connected = False
        except Exception as e:
            print(f"Error: {e}")

    def register(self, handle):
        try:
            if self.handle is not None:
                raise Exception("already registered")

            self.sck.send(f"REGISTER {handle}".encode())
            resp = self.sck.recv(1024).decode()
            if resp == "TAKEN":
                raise Exception("handle already taken")
        except Exception as e:
            print(f"Error: Failed to register, {e}.") 
        else:
            self.handle = handle
            if not os.path.exists(self.handle):
                os.mkdir(self.handle)

    def get_dir(self):
        try:
            self.sck.send("DIR".encode())
            resp = self.sck.recv(4096).decode()
            if not resp.startswith("Error"):
                print("Directory:")
                print(resp)
            else:
                raise Exception(resp)
        except Exception as e:
            print(f"Error: Failed to display server dir, {e}")

    def get_file(self, fname):
        try:
            fpath = f"{self.handle}/{fname}"
            self.sck.send(f"GET {fname}".encode())
            resp = self.sck.recv(4096).decode()
            if resp.startswith("Error"):
                raise Exception(f"Server {resp}")
            fsize = int(resp)
            with open(fpath, "wb") as f:
                rec_file = self.sck.recv(fsize)
                f.write(rec_file)
        except Exception as e:
            print(e)

    def send_file(self, fname):
        try:
            fpath = f"{self.handle}/{fname}"
            self.sck.send(f"SEND {fname}".encode())

            with open(fpath, "rb") as f:
                self.sck.sendall(str(os.path.getsize(fpath)).encode('utf8'))
                self.sck.sendfile(f)
        except FileNotFoundError:
            print("Error: File not found.")
        except Exception as e:
            print(f"Error: {e}")

    def get_help(self):
        print("""
        Commands:
        /join <address> <port> - Connect to server
        /leave - Disconnect from server
        /register <handle> - Register with a handle
        /store <filename> - Store a file on the server
        /dir - List files from the server
        /get <filename> - Get a file from the server
        /? - Help message
        """)

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
