# ATANACIO, ANJELO PATRICK ASUNCION - S12
# FERMIN, ALFONSO GABRIELLI TAROY - S12
# Server side
import socket
import sys
import threading
import os
import logging
import shutil
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Server:
    def __init__(self, port):
        self.host = "127.0.0.1"
        self.port = port
        self.file_port = 5001  # Separate port for file transfers
        self.dir_port = 5002  # Separate port for directory listing
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.file_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.dir_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = []
        self.handles = {}
        self.threads = []
        self.running = False
        self.shutdown_event = threading.Event()
        self.server_directory = 's_files'
        os.makedirs(self.server_directory, exist_ok=True)

    def start(self):
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen()
            self.file_socket.bind((self.host, self.file_port))
            self.file_socket.listen()
            self.dir_socket.bind((self.host, self.dir_port))
            self.dir_socket.listen()
            logging.info(f"Server listening on {self.host}:{self.port} for commands, {self.host}:{self.file_port} for file transfers, and {self.host}:{self.dir_port} for directory listing")
            self.running = True

            threading.Thread(target=self.accept_file_connections, daemon=True).start()
            threading.Thread(target=self.accept_dir_connections, daemon=True).start()

            while self.running:
                try:
                    self.socket.settimeout(1.0)
                    c_socket, c_address = self.socket.accept()
                    logging.info(f"New connection from {c_address[0]}:{c_address[1]}")
                    c_thread = threading.Thread(target=self.handle_client, args=(c_socket,))
                    c_thread.start()
                    self.clients.append(c_socket)
                    self.threads.append(c_thread)
                except socket.timeout:
                    if self.shutdown_event.is_set():
                        self.running = False
                except Exception as e:
                    logging.error(f"Error: {e}")
        except KeyboardInterrupt:
            logging.info("Shutting down server...")
        except ConnectionResetError:
            logging.error("Error: Connection forcefully terminated by client.")
        except socket.error as e:
            logging.error(f"Error: Error starting server {e}")
        finally:
            self.shutdown()


    def accept_dir_connections(self):
        while self.running:
            try:
                d_socket, d_address = self.dir_socket.accept()
                logging.info(f"New directory listing connection from {d_address[0]}:{d_address[1]}")
                d_thread = threading.Thread(target=self.handle_dir_request, args=(d_socket,))
                d_thread.start()
            except Exception as e:
                logging.error(f"Error: {e}")

    def handle_dir_request(self, d_socket: socket.socket):
        try:
            msg = d_socket.recv(1024).decode()
            if msg == "/dir":
                self.send_directory_list(d_socket)
        except Exception as e:
            logging.error(f"Error: {e}")
        finally:
            d_socket.close()



    def accept_file_connections(self):
        while self.running:
            try:
                f_socket, f_address = self.file_socket.accept()
                logging.info(f"New file transfer connection from {f_address[0]}:{f_address[1]}")
                f_thread = threading.Thread(target=self.handle_file_transfer, args=(f_socket,))
                f_thread.start()
            except Exception as e:
                logging.error(f"Error: {e}")
                

    def broadcast_message(self, message: str):
        for client in self.clients:
            client.sendall(message.encode())

    def shutdown(self):
        for i in range(10, 0, -1):
            self.broadcast_message(f"Server shutting down in {i} seconds...")
            time.sleep(1)
        self.broadcast_message("Server has been shutdown by admin for maintenance.")
        self.shutdown_event.set()
        self.running = False
        for c in self.clients:
            c.close()
        for t in self.threads:
            t.join()
        self.socket.close()
        self.file_socket.close()
        self.dir_socket.close()
        logging.info("Server closed.")

    def handle_client(self, c_socket: socket.socket):
        try:
            while True:
                msg = c_socket.recv(1024).decode()
                if not msg:
                    break
                
                logging.info(f"Received message: {msg}")
                self.process_command(c_socket, msg)
        except Exception as e:
            logging.error(f"Error: {e}")
        finally:
            if c_socket in self.clients:
                self.clients.remove(c_socket)
            if c_socket in self.handles:
                self.handles.pop(c_socket, None)
            c_socket.close()

    def handle_file_transfer(self, f_socket: socket.socket):
        try:
            msg = f_socket.recv(1024).decode()
            if msg.startswith("/get"):
                _, filename = msg.split()
                self.send_file(f_socket, filename)
        except Exception as e:
            logging.error(f"Error: {e}")
        finally:
            f_socket.close()

    def process_command(self, c_socket: socket.socket, msg: str):
        msg_parts = msg.split()
        command = msg_parts[0]

        if command == "/register" and len(msg_parts) == 2:
            handle = msg_parts[1]
            if handle in self.handles.values():
                c_socket.sendall(f"Error: Handle {handle} already exists.".encode())
            else:
                self.handles[c_socket] = handle
                user_directory = os.path.join(os.getcwd(), handle)  # Create user-specific directory
                os.makedirs(user_directory, exist_ok=True)
                c_socket.sendall(f"Handle {handle} registered successfully.".encode())
        elif command == "/store" and len(msg_parts) == 2:
            filename = msg_parts[1]
            self.receive_file(c_socket, filename)
        elif command == "/dir":
            if c_socket in self.handles:
                self.send_directory_list(c_socket)
            else:
                c_socket.sendall("Error: You must be registered to use this command.".encode())
        elif command == "/leave":
            c_socket.close()
            self.clients.remove(c_socket)
            self.handles.pop(c_socket, None)
        elif command == "/shutdown":
            if self.handles.get(c_socket) == "ADMIN":  # Replace "admin" to change the actual authorized handle
                self.broadcast_message("Server is shutting down for maintenance by admin.")
                threading.Thread(target=self.shutdown).start()
            else:
                c_socket.sendall(f"Error: Unauthorized shutdown attempt.".encode())
        elif command == "/unicast" and len(msg_parts) > 2:
            target_handle = msg_parts[1]
            unicast_message = ' '.join(msg_parts[2:])
            self.send_unicast(c_socket, target_handle, unicast_message)
        elif command == "/broadcast" and len(msg_parts) > 1:
            broadcast_message = ' '.join(msg_parts[1:])
            self.send_broadcast(c_socket, broadcast_message)
        elif command == "/?":
            self.send_help(c_socket)
        else:
            c_socket.sendall(f"Unknown or invalid command: {command}".encode())

    def send_unicast(self, c_socket: socket.socket, target_handle: str, message: str):
        sender_handle = self.handles[c_socket]
        for client, handle in self.handles.items():
            if handle == target_handle:
                client.sendall(f"Unicast from {sender_handle}: {message}".encode())
                return
        c_socket.sendall(f"Error: Handle {target_handle} not found.".encode())

    def send_broadcast(self, c_socket: socket.socket, message: str):
        sender_handle = self.handles[c_socket]
        for client, handle in self.handles.items():
            if client != c_socket:
                client.sendall(f"Broadcast from {sender_handle}: {message}".encode())

    def receive_file(self, c_socket: socket.socket, filename: str):
        filepath = os.path.join(self.server_directory, filename)  # Save file in s_files directory
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
            #c_socket.sendall(f"File {filename} received from {handle}.".encode())
        except Exception as e:
            c_socket.sendall(f"Error: {e}".encode())


    def send_directory_list(self, c_socket: socket.socket):
        try:
            logging.info("Preparing to send directory listing")
            files = os.listdir(self.server_directory)
            if files:
                files_list = "Server Directory:\n" + '\n'.join(files)
            else:
                files_list = "Server Directory:\nNo files found."
            c_socket.sendall(files_list.encode())
            logging.info(f"Sent directory listing: {files_list}")  # Log as INFO
        except FileNotFoundError as e:
            error_message = f"Error: Directory not found: {e}"
            c_socket.sendall(error_message.encode())
            logging.error(error_message)
        except OSError as e:
            error_message = f"Error: OS error: {e}"
            c_socket.sendall(error_message.encode())
            logging.error(error_message)
        except Exception as e:
            error_message = f"Error sending directory listing: {e}"
            c_socket.sendall(error_message.encode())
            logging.error(error_message)




    def send_file(self, f_socket: socket.socket, filename: str):
        filepath = os.path.join(self.server_directory, filename)
        try:
            with open(filepath, 'rb') as file:
                with f_socket.makefile('wb') as out:
                    shutil.copyfileobj(file, out)
                logging.info(f"File {filename} sent successfully.")
        except FileNotFoundError:
            error_message = f"Error: File {filename} not found."
            f_socket.sendall(error_message.encode())
            logging.error(f"File not found: {filename}")
        except Exception as e:
            error_message = f"Error: {str(e)}"
            f_socket.sendall(error_message.encode())
            logging.error(f"Error sending file {filename}: {e}")


    def send_help(self, c_socket: socket.socket):
        help_message = (
            "/join <server_ip> <port> - Connect to the server\n"
            "/leave - Disconnect from the server\n"
            "/register <handle> - Register your handle\n"
            "/unicast <handle> <message> - Send a message to a specific user\n"
            "/broadcast <message> - Send a message to all users\n"
            "/store <filename> - Upload a file to the server\n"
            "/dir - List files on the server\n"
            "/get <filename> - Download a file from the server\n"
            "/shutdown - Shutdown the server (authorized users only)\n"
            "/? - Display this command list"
        )
        c_socket.sendall(help_message.encode())

def main():
    if len(sys.argv) < 2:
        logging.info("No port specified. Using default port 12345.")
        port = 12345
    else:
        port = int(sys.argv[1])
    server = Server(port)
    server.start()

if __name__ == "__main__":
    main()
