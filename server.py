from typing import List

import socket
import os
import sys
import threading

class Server:
    def __init__(self, port) -> None:
        self.host = "127.0.0.1"
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients: List[socket.socket] = []
        self.handles = {}
        self.threads = []
        self.running = False
        self.shutdown_even = threading.Event()

    def start(self):
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen()
            print(f"Server listening on {self.host}:{self.port}")
            self.running = True

            while self.running:
                try:
                    self.socket.settimeout(1.0)
                    c_socket, c_address = self.socket.accept()
                    print(f"New connection from {c_address[0]}:{c_address[1]}")
                    c_thread = threading.Thread(target=self.handle_client, args=(c_socket,))
                    c_thread.start()
                    self.clients.append(c_socket)
                    self.threads.append(c_thread)
                except socket.timeout:
                    if self.shutdown_even.is_set():
                        self.running = False
                except Exception as e:
                    print(f"Error: {e}")
        except KeyboardInterrupt:
            print("Shutting down server...")
        except ConnectionResetError:
            print("Error: Connection forcefully terminated by client.")
        except socket.error as e:
            print(f"Error: Error starting server {e}")
        finally:
            self.shutdown()

    def shutdown(self):
        self.shutdown_even.set()
        self.running = False
        for c in self.clients:
            c.close()
        for t in self.threads:
            t.join()
        self.socket.close()
        print("Server closed.")

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
                    else:
                        self.handles[c_socket] = handle
                        c_socket.sendall(f"{handle}".encode())

                elif data.startswith("DIR"):
                    try:
                        path = "s_files"
                        file_list = os.listdir(path)
                        if not file_list:
                            c_socket.sendall("EMPTY".encode())
                        else:
                            file_list_str = "\n".join(file_list)
                            c_socket.sendall(file_list_str.encode())
                    except Exception as e:
                        c_socket.sendall("{e}".encode())

                elif data.startswith("GET"):
                    try:
                        fname = data.split()[1]
                        fpath = f"s_files/{fname}"
                        with open(fpath, "rb") as f:
                            fsize = os.path.getsize(fpath)
                            c_socket.sendall(str(fsize).encode('utf8'))
                            c_socket.sendfile(f)
                    except Exception as e:
                        c_socket.sendall(f"Error: {e}".encode())

                elif data.startswith("SEND"):
                    try: 
                        fname = data.split()[1]
                        fpath = f"s_files/{fname}"
                        fsize = int(c_socket.recv(1024).decode())
                        rec_file = c_socket.recv(fsize)
                        with open(fpath, "wb") as f:
                            f.write(rec_file)
                    except Exception as e:
                        print(f"Error: {e}")

        except KeyboardInterrupt:
            print("Test") 
        except ConnectionResetError:
            print("Error: Connection forcefully terminated by client.")
        except ConnectionAbortedError:
            pass 
        except Exception as e:
            print(f"Error: {e}")

def main():
    port = int(sys.argv[1])
    server = Server(port)
    server.start()

if __name__ == "__main__":
    main()
