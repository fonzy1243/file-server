from typing import List, Dict
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
        self.handles: Dict[socket.socket, str] = {}
        self.threads = []
        self.running = False
        self.shutdown_event = threading.Event()
        self.server_directory = 's_files'
        os.makedirs(self.server_directory, exist_ok=True)

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
                    if self.shutdown_event.is_set():
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
        self.shutdown_event.set()
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
                msg = c_socket.recv(1024).decode()
                if not msg:
                    break
                
                print(f"Received message: {msg}")
                self.process_command(c_socket, msg)
        except Exception as e:
            print(f"Error: {e}")
        finally:
            c_socket.close()

    def process_command(self, c_socket: socket.socket, msg: str):
        msg_parts = msg.split()
        command = msg_parts[0]

        if command == "/register" and len(msg_parts) == 2:
            handle = msg_parts[1]
            if handle in self.handles.values():
                c_socket.sendall(f"Error: Handle {handle} already exists.".encode())
            else:
                self.handles[c_socket] = handle
                user_directory = os.path.join(self.server_directory, handle)
                os.makedirs(user_directory, exist_ok=True)
                c_socket.sendall(f"Handle {handle} registered successfully.".encode())
        elif command == "/store" and len(msg_parts) == 2:
            filename = msg_parts[1]
            self.receive_file(c_socket, filename)
        elif command == "/dir":
            self.send_directory_list(c_socket)
        elif command == "/get" and len(msg_parts) == 2:
            filename = msg_parts[1]
            self.send_file(c_socket, filename)
        elif command == "/leave":
            c_socket.close()
            self.clients.remove(c_socket)
            self.handles.pop(c_socket, None)
        elif command == "/shutdown":
            if c_socket in self.handles:
                self.shutdown()
            else:
                c_socket.sendall(f"Error: Unauthorized shutdown attempt.".encode())
        elif command == "/?":
            self.send_help(c_socket)
        else:
            c_socket.sendall(f"Unknown or invalid command: {command}".encode())

    def receive_file(self, c_socket: socket.socket, filename: str):
        filepath = os.path.join(self.server_directory, filename)
        try:
            with open(filepath, 'wb') as file:
                while True:
                    data = c_socket.recv(4096)
                    if data == b"EOF":
                        break
                    if not data:
                        break
                    file.write(data)
            handle = self.handles.get(c_socket, "Unknown")
            c_socket.sendall(f"File {filename} received from {handle}.".encode())
        except Exception as e:
            c_socket.sendall(f"Error: {e}".encode())

    def send_directory_list(self, c_socket: socket.socket):
        try:
            files = os.listdir(self.server_directory)
            if files:
                files_list = '\n'.join(files)
            else:
                files_list = "No files found."
            c_socket.sendall(files_list.encode())
        except Exception as e:
            c_socket.sendall(f"Error: {e}".encode())

    def send_file(self, c_socket: socket.socket, filename: str):
        filepath = os.path.join(self.server_directory, filename)
        try:
            with open(filepath, 'rb') as file:
                file_size = os.path.getsize(filepath)
                c_socket.sendall(str(file_size).encode())  # Send file size first
                while True:
                    data = file.read(4096)
                    if not data:
                        break
                    c_socket.sendall(data)
                    socket.close
            #socket.sendall(b"File transfer complete.")
        except FileNotFoundError:
            c_socket.sendall(f"Error: File {filename} not found.".encode())

    def send_help(self, c_socket: socket.socket):
        help_message = (
            "/join <server_ip> <port> - Connect to the server\n"
            "/leave - Disconnect from the server\n"
            "/register <handle> - Register your handle\n"
            "/store <filename> - Upload a file to the server\n"
            "/dir - List files on the server\n"
            "/get <filename> - Download a file from the server\n"
            "/shutdown - Shutdown the server (authorized users only)\n"
            "/? - Display this command list"
        )
        c_socket.sendall(help_message.encode())

def main():
    if len(sys.argv) < 2:
        print("No port specified. Using default port 12345.")
        port = 12345
    else:
        port = int(sys.argv[1])
    server = Server(port)
    server.start()

if __name__ == "__main__":
    main()
