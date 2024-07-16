import socket
import os
import sys
import threading

class Server:
    def __init__(self, port) -> None:
        self.host = "127.0.0.1"
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = []
        self.handles = {}

    def start(self):
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen()
            print(f"Server listening on {self.host}:{self.port}")

            while True:
                c_socket, c_address = self.socket.accept()
                print(f"New connection from {c_address}")
                c_thread = threading.Thread(target=self.handle_client, args=(c_socket,))
                c_thread.start()
                self.clients.append(c_socket)
                pass
        except KeyboardInterrupt:
            print("Shutting down server...")
        except socket.error as e:
            print(f"Error: Error starting server {e}")
        finally:
            self.socket.close()

    def handle_client(self, c_socket: socket.socket):
        try:
            while True:
                data = c_socket.recv(1024).decode()
                if not data:
                    break
                
                # Process req
                if data.startswith("REGISTER"):
                    handle = data.split()[1]
                    if handle in self.handles.values():
                        c_socket.sendall("TAKEN".encode())
                        break
                    self.handles[c_socket] = handle
                    c_socket.sendall("".encode())

                elif data.startswith("DIR"):
                    path = "/s_files"
                    file_list = os.listdir(path)
                    file_list_str = "\n".join(file_list)
                    c_socket.sendall(file_list_str.encode())

                elif data.startswith("GET"):
                    fname = data.split()[1]
                    with open(f"/s_files/{fname}", "rb") as f:
                        c_socket.sendall(str(os.path.getsize(f"/s_files/{fname}")).encode('utf8'))
                        c_socket.sendfile(f)

                elif data.startswith("SEND"):
                    fname = data.split()[1]
                    fsize = int(c_socket.recv(1024).decode())
                    rec_file = c_socket.recv(fsize)
                    with open(f"/s_files/{fname}", "wb") as f:
                        f.write(rec_file)

        except:
            pass

def main():
    port = sys.argv[0]
    server = Server(port)
    server.start()

if __name__ == "__main__":
    main()
