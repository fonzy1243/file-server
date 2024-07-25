import socket
import sys
import os
import tkinter as tk
from tkinter import scrolledtext, messagebox
from datetime import datetime
import time

COMMANDS = [
    "/join <server_ip> <port> - Connect to the server",
    "/leave - Disconnect from the server",
    "/register <handle> - Register your handle",
    "/store <filename> - Upload a file to the server",
    "/dir - List files on the server",
    "/get <filename> - Download a file from the server",
    "/shutdown - Shutdown the server",
    "/close - Close the client",
    "/? or /help - Display this command list"
]

HANDLE_REQUIRED = [
    "/store", "/dir", "/get", "/shutdown"
]

class Client:
    def __init__(self) -> None:
        self.sck = None
        self.handle = None
        self.connected = False
        self.addr = None
        self.port = None
        self.create_ui()

    def create_ui(self):
        self.root = tk.Tk()
        self.root.title("File Exchange Client")

        self.output_area = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, width=50, height=20)
        self.output_area.grid(row=0, column=0, columnspan=2, padx=10, pady=10)
        self.output_area.config(state=tk.DISABLED)

        self.input_field = tk.Entry(self.root, width=50)
        self.input_field.grid(row=1, column=0, padx=10, pady=10)
        self.input_field.bind("<Return>", self.execute_command)

        self.send_button = tk.Button(self.root, text="Send", command=self.execute_command)
        self.send_button.grid(row=1, column=1, padx=10, pady=10)

        self.root.protocol("WM_DELETE_WINDOW", self.close_client)  # Handle window close event
        self.root.mainloop()

    def execute_command(self, event=None):
        cmd = self.input_field.get()
        self.input_field.delete(0, tk.END)
        self.get_command(cmd)

    def display_message(self, message):
        self.output_area.config(state=tk.NORMAL)
        self.output_area.insert(tk.END, message + "\n")
        self.output_area.yview(tk.END)
        self.output_area.config(state=tk.DISABLED)
        print(message)  # Print message to the command line

    def get_command(self, cmd: str):
        try:
            cmd_words = cmd.strip().split()
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
                self.connect(self.addr, self.port)
            elif command == "/leave" and len(cmd_words) == 1:
                self.disconnect()
            elif command == "/register" and len(cmd_words) == 2:
                handle = cmd_words[1]
                self.register(handle)
            elif command == "/store" and len(cmd_words) == 2:
                fname = cmd_words[1]
                start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.send_file(fname, start_time)
            elif command == "/dir" and len(cmd_words) == 1:
                self.get_dir()
            elif command == "/get" and len(cmd_words) == 2:
                fname = cmd_words[1]
                self.get_file(fname)
            elif command == "/shutdown" and len(cmd_words) == 1:
                self.shutdown_server()
            elif command == "/close" and len(cmd_words) == 1:
                self.close_client()
            else:
                raise Exception("Error: Unknown command. Type /? or /help for the command list.")
        except Exception as e:
            self.display_message(str(e))

    def connect(self, addr, port):
        try:
            self.sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sck.connect((addr, port))
            self.connected = True
            self.display_message("Connection to the File Exchange Server is successful!")
        except Exception as e:
            self.display_message(f"Error: Connection to the Server has failed! {e}")

    def disconnect(self):
        try:
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
            if "registered successfully" in confirmation:
                self.display_message(f"Welcome {handle}!")
                os.makedirs(handle, exist_ok=True)  # Create directory for the user
            else:
                raise Exception("Error: Registration failed. Handle or alias already exists.")
        except Exception as e:
            self.display_message(f"Error: {e}")

    def send_file(self, filename, start_time):
        try:
            with open(filename, 'rb') as file:
                data = file.read()
                self.sck.sendall(f"/store {filename}".encode())
                self.sck.sendall(data)
            
            self.display_message(f"{self.handle}<{start_time}>: Uploaded {filename}")
            
            self.reconnect()  # Reconnect the client after file upload
        except FileNotFoundError:
            self.display_message(f"Error: File {filename} not found.")
            self.reconnect()
        except Exception as e:
            self.display_message(f"Error: File upload failed. {e}")
            self.reconnect()

    def get_dir(self):
        try:
            self.sck.sendall("/dir".encode())
            data = self.sck.recv(4096).decode()
            self.display_message("Server Directory:\n" + data)
        except Exception as e:
            self.display_message(f"Error: {e}")

    def get_file(self, filename):
        try:
            self.sck.sendall(f"/get {filename}".encode())

            # First, get the file size
            file_size = int(self.sck.recv(4096).decode())
            self.display_message(f"File size: {file_size} bytes")

            file_path = os.path.join(self.handle, filename)
            with open(file_path, 'wb') as file:
                received_size = 0
                while received_size < file_size:
                    data = self.sck.recv(4096)
                    if not data:
                        break
                    file.write(data)
                    received_size += len(data)
            
            self.display_message(f"File {filename} downloaded.")
        except Exception as e:
            self.display_message(f"Error: File {filename} download failed. {e}")

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

    def reconnect(self):
        last_handle = self.handle
        self.disconnect()
        self.connect(self.addr, self.port)
        if last_handle:
            self.display_message(f"Welcome back, {last_handle}!")
            self.handle = last_handle

    def close_client(self):
        try:
            self.display_message("Closing client. Goodbye!")
            if self.connected:
                self.disconnect()
            print("Closing client. Goodbye!")  # Print message to the command line
            time.sleep(2)  # Wait for  seconds before closing the window
            self.root.destroy()  # Close the Tkinter window
        except Exception as e:
            self.display_message(f"Error: Could not close the client. {e}")

def main():
    client = Client()

if __name__ == "__main__":
    main()
