import socket
import sys
import os
import time
import tkinter as tk
from tkinter import scrolledtext
from datetime import datetime
import threading
import queue

COMMANDS = [
    "/join <server_ip> <port> - Connect to the server",
    "/leave - Disconnect from the server",
    "/register <handle> - Register your handle",
    "/unicast <handle> <message> - Send a message to a specific user",
    "/broadcast <message> - Send a message to all users",
    "/store <filename> - Upload a file to the server",
    "/dir - List files on the server",
    "/get <filename> - Download a file from the server",
    "/shutdown - Shutdown the server",
    "/close - Close the client",
    "/? or /help - Display this command list"
]

HANDLE_REQUIRED = [
    "/store", "/dir", "/get", "/shutdown", "/unicast", "/broadcast"
]

class Client:
    def __init__(self) -> None:
        self.sck = None
        self.handle = None
        self.connected = False
        self.addr = None
        self.port = None
        self.queue = queue.Queue()
        self.create_ui()

    def create_ui(self):
        self.root = tk.Tk()
        self.root.title("Messaging Client")

        self.output_area = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, width=50, height=20)
        self.output_area.grid(row=0, column=0, columnspan=2, padx=10, pady=10)
        self.output_area.config(state=tk.DISABLED)

        self.input_field = tk.Entry(self.root, width=50)
        self.input_field.grid(row=1, column=0, padx=10, pady=10)
        self.input_field.bind("<Return>", self.execute_command)

        self.send_button = tk.Button(self.root, text="Send", command=self.execute_command)
        self.send_button.grid(row=1, column=1, padx=10, pady=10)

        self.root.protocol("WM_DELETE_WINDOW", self.close_client)  # Handle window close event

        self.update_ui()
        self.root.mainloop()

    def update_ui(self):
        while not self.queue.empty():
            message = self.queue.get()
            self.output_area.config(state=tk.NORMAL)
            self.output_area.insert(tk.END, message + "\n")
            self.output_area.yview(tk.END)
            self.output_area.config(state=tk.DISABLED)
        self.root.after(100, self.update_ui)

    def execute_command(self, event=None):
        cmd = self.input_field.get()
        self.input_field.delete(0, tk.END)
        threading.Thread(target=self.get_command, args=(cmd,)).start()

    def display_message(self, message):
        self.queue.put(message)
        print(message)  # Print message to the command line

    def get_command(self, cmd: str):
        try:
            cmd_words = cmd.strip().split()
            if not cmd_words:
                raise Exception("Error: Command cannot be empty.")
            command = cmd_words[0]

            if command == "/?" or command == "/help" and len(cmd_words) == 1:
                self.get_help()
                return

            if command != "/join" and not self.connected:
                raise Exception("Error: You are not connected to the server.")

            if command in HANDLE_REQUIRED and self.handle is None:
                raise Exception("Error: You must be registered to use this command.")

            if command == "/join" and len(cmd_words) == 3:
                self.addr = cmd_words[1]
                self.port = int(cmd_words[2])
                threading.Thread(target=self.connect, args=(self.addr, self.port)).start()
            elif command == "/leave" and len(cmd_words) == 1:
                self.disconnect()
            elif command == "/register" and len(cmd_words) == 2:
                handle = cmd_words[1]
                threading.Thread(target=self.register, args=(handle,)).start()
            elif command == "/unicast" and len(cmd_words) > 2:
                target_handle = cmd_words[1]
                message = ' '.join(cmd_words[2:])
                threading.Thread(target=self.send_unicast, args=(target_handle, message)).start()
            elif command == "/broadcast" and len(cmd_words) > 1:
                message = ' '.join(cmd_words[1:])
                threading.Thread(target=self.send_broadcast, args=(message,)).start()
            elif command == "/store" and len(cmd_words) == 2:
                fname = cmd_words[1]
                start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                threading.Thread(target=self.send_file, args=(fname, start_time)).start()
            elif command == "/dir" and len(cmd_words) == 1:
                threading.Thread(target=self.get_dir).start()
            elif command == "/get" and len(cmd_words) == 2:
                fname = cmd_words[1]
                threading.Thread(target=self.get_file, args=(fname,)).start()
            elif command == "/shutdown" and len(cmd_words) == 1:
                threading.Thread(target=self.shutdown_server).start()
            elif command == "/close" and len(cmd_words) == 1:
                self.close_client()
            else:
                raise Exception("Error: Unknown command or incorrect number of arguments. Type /? or /help for the command list.")
        except Exception as e:
            self.display_message(str(e))

    def connect(self, addr, port):
        try:
            self.sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sck.connect((addr, port))
            self.connected = True
            self.display_message("Connection to the Messaging Server is successful!")
            threading.Thread(target=self.receive_messages, daemon=True).start()
        except Exception as e:
            self.display_message(f"Error: Connection to the Server has failed! {e}")

    def disconnect(self):
        try:
            if self.connected:
                self.sck.close()
                self.connected = False
                self.display_message("Connection closed. Thank you!")
        except Exception as e:
            self.display_message(f"Error: Disconnection failed. {e}")

    def register(self, handle):
        try:
            self.handle = handle
            self.sck.sendall(f"/register {handle}".encode())
            confirmation = self.sck.recv(4096).decode()
            if "Handle registered successfully." in confirmation:
                self.display_message(f"Welcome {handle}!")
                os.makedirs(handle, exist_ok=True)  # Create directory for the user
            elif "Error: Handle" in confirmation and "already exists" in confirmation:
                raise Exception("Error: Registration failed. Handle or alias already exists.")
            else:
                self.display_message(confirmation)  # Display any other server response
        except Exception as e:
            self.display_message(f"Error: {e}")

    def send_unicast(self, target_handle, message):
        try:
            self.sck.sendall(f"/unicast {target_handle} {message}".encode())
            self.display_message(f"Unicast to {target_handle}: {message}")
        except Exception as e:
            self.display_message(f"Error: Failed to send unicast message. {e}")

    def send_broadcast(self, message):
        try:
            self.sck.sendall(f"/broadcast {message}".encode())
            self.display_message(f"Broadcast: {message}")
        except Exception as e:
            self.display_message(f"Error: Failed to send broadcast message. {e}")

    def send_file(self, filename, start_time):
        try:
            with open(filename, 'rb') as file:
                self.sck.sendall(f"/store {filename}".encode())
                time.sleep(0.1)  # Small delay to ensure command is sent before file data
                while True:
                    data = file.read(4096)
                    if not data:
                        break
                    self.sck.sendall(data)
                self.sck.sendall(b"EOF")
            
            self.display_message(f"{self.handle}<{start_time}>: Uploaded {filename}")
        except FileNotFoundError:
            self.display_message(f"Error: File {filename} not found.")
        except Exception as e:
            self.display_message(f"Error: File upload failed. {e}")

    def get_dir(self):
        try:
            self.sck.sendall("/dir".encode())
            response = self.sck.recv(4096).decode()
            if response.startswith("Server Directory:"):
                self.display_message(response)
            else:
                self.display_message(f"Unexpected server response: {response}")
        except Exception as e:
            self.display_message(f"Error: {e}")

    def get_file(self, filename):
        def download_file():
            try:
                self.sck.sendall(f"/get {filename}".encode())

                # Receive file size first
                file_size_data = self.sck.recv(4096).decode()
                if not file_size_data.isdigit():
                    raise Exception(f"Unexpected server response: {file_size_data}")

                file_size = int(file_size_data)
                self.sck.sendall(b"ACK")  # Send acknowledgment

                user_directory = os.path.join(os.getcwd(), self.handle)
                os.makedirs(user_directory, exist_ok=True)

                file_path = os.path.join(user_directory, filename)
                received_size = 0
                with open(file_path, 'wb') as file:
                    while received_size < file_size:
                        data = self.sck.recv(4096)
                        if data == b"EOF":
                            break
                        file.write(data)
                        received_size += len(data)

                self.display_message(f"File {filename} downloaded.")
            except Exception as e:
                self.display_message(f"Error: File {filename} download failed. {e}")

        threading.Thread(target=download_file).start()

    def shutdown_server(self):
        try:
            self.sck.sendall("/shutdown".encode())
            self.display_message("Shutdown command sent to the server.")
        except Exception as e:
            self.display_message(f"Error: Could not send shutdown command. {e}")

    def get_help(self):
        self.display_message("Available commands:")
        for command in COMMANDS:
            self.display_message(command)

    def receive_messages(self):
        while self.connected:
            try:
                message = self.sck.recv(4096)
                try:
                    decoded_message = message.decode()
                    self.display_message(decoded_message)
                except UnicodeDecodeError:
                    # Handle non-decodable message (binary data)
                    self.display_message("Received non-text data.")
            except Exception as e:
                self.display_message(f"Receive error: {e}")
                break

    def reconnect(self):
        last_handle = self.handle
        self.disconnect()
        self.connect(self.addr, self.port)
        if last_handle:
            self.display_message(f"Welcome back, {last_handle}!")
            self.register(last_handle)

    def close_client(self):
        try:
            self.display_message("Closing client. Goodbye!")
            if self.connected:
                self.disconnect()
            print("Closing client. Goodbye!")  # Print message to the command line
            time.sleep(2)  # Wait for 2 seconds before closing the window
            self.root.destroy()  # Close the Tkinter window
        except Exception as e:
            self.display_message(f"Error: Could not close the client. {e}")

def main():
    Client()

if __name__ == "__main__":
    main()
