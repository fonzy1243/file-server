import socket
import os
import tkinter as tk
from tkinter import scrolledtext, ttk
import threading
import queue
import logging
import shutil
import time

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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Client:
    def __init__(self) -> None:
        self.sck = None
        self.file_sck = None
        self.handle = None
        self.connected = False
        self.addr = None
        self.port = None
        self.file_port = None
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

        # Add Progress Bar
        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=400, mode="determinate")
        self.progress.grid(row=2, column=0, columnspan=2, padx=10, pady=10)
        self.progress_label = tk.Label(self.root, text="")
        self.progress_label.grid(row=3, column=0, columnspan=2, padx=10, pady=10)

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
        logging.info(f"User entered command: {cmd}")  # Log the user command
        threading.Thread(target=self.get_command, args=(cmd,)).start()

    def display_message(self, message):
        self.queue.put(message)
        logging.info(message)  # Log message for better debugging

    def get_command(self, cmd: str):
        try:
            cmd_words = cmd.strip().split()
            if not cmd_words:
                raise Exception("Error: Command cannot be empty.")
            command = cmd_words[0]
            
            
            # List of valid commands
            valid_commands = ["/?", "/help", "/join", "/leave", "/register", "/unicast", "/broadcast", 
                            "/store", "/dir", "/get", "/shutdown", "/close"]

            if command not in valid_commands:
                raise Exception("Error: Command not found.")

            if command == "/?" or command == "/help" and len(cmd_words) == 1:
                self.get_help()
                return

            if command == "/leave" and not self.connected:
                raise Exception("Error: Disconnection failed. Please connect to the server first.")

            if command != "/join" and not self.connected:
                raise Exception("Error: You are not connected to the server.")
            
            if command in HANDLE_REQUIRED and self.handle is None:
                raise Exception("Error: You must be registered to use this command.")

            if command == "/join" and len(cmd_words) == 3:
                self.addr = cmd_words[1]
                self.port = int(cmd_words[2])
                if self.port == 5001 or self.port == 5002:
                    raise Exception("Error: Port 5001 and 5002 is reserved and cannot be used.")
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
                threading.Thread(target=self.send_file, args=(fname,)).start()
            elif command == "/dir" and len(cmd_words) == 1:
                self.get_dir()  # Handle /dir command synchronously
            elif command == "/get" and len(cmd_words) == 2:
                fname = cmd_words[1]
                threading.Thread(target=self.get_file, args=(fname,)).start()
            elif command == "/shutdown" and len(cmd_words) == 1:
                threading.Thread(target=self.shutdown_server).start()
            elif command == "/close" and len(cmd_words) == 1:
                self.close_client()
            else:
                raise Exception("Error: Unknown command or incorrect number of arguments or Command parameters do not match or is not allowed.. Type /? or /help for the command list.")
        except Exception as e:
            self.display_message(str(e))
            logging.error(str(e))

    def connect(self, addr, port):
        try:
            self.sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sck.connect((addr, port))
            self.file_port = 5001  # Set the file transfer port
            self.dir_port = 5002  # Separate port for directory listing
            self.connected = True
            self.display_message("Connection to the Messaging Server is successful!")
            threading.Thread(target=self.receive_messages, daemon=True).start()
        except Exception as e:
            self.display_message(f"Error: Connection to the Server has failed! Please check IP Address and Port Number.{e}")
            #self.display_message(f"Error: Connection to the Server has failed! Please check IP Address and Port Number. {e}") # Uncomment for detailed error message
            
    def disconnect(self):
        try:
            if self.connected:
                self.sck.close()
                self.connected = False
                self.display_message("Connection closed. Thank you!")
        except socket.error as e:
            if e.errno != 10053:  # Ignore specific WinError 10053
                self.display_message(f"Error: Disconnection failed. {e}")


    def register(self, handle):
        #self.display_message(f"Welcome {handle}!")
        try:
            self.handle = handle
            self.sck.sendall(f"/register {handle}".encode())
            self.display_message(f"Welcome {self.handle}!")
            confirmation = self.sck.recv(4096).decode()
            
            
            if "Handle registered successfully." in confirmation:
                os.makedirs(handle, exist_ok=True)  # Create directory for the user
            elif "Error: Handle" in confirmation and "already exists" in confirmation:
                raise Exception("Error: Registration failed. Handle or alias already exists.")
            else:
               logging.error(confirmation)  # Display any other server response
                #self.display_message(confirmation)  # Display any other server response
        except Exception as e:
           # self.display_message(f"Error: {e}") # Uncomment for detailed error message to be displayed on the client GUI
            logging.error(f"Error: {e}")

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

    def send_file(self, filename):
        def upload_file():
            try:
                user_directory = os.path.join(os.getcwd(), self.handle)
                file_path = os.path.join(user_directory, filename)
                with open(file_path, 'rb') as file:
                    self.sck.sendall(f"/store {filename}".encode())
                    time.sleep(0.1)  # Small delay to ensure command is sent before file data
                    while True:
                        data = file.read(4096)
                        if not data:
                            break
                        self.sck.sendall(data)
                    self.sck.sendall(b"EOF")

                # Send the upload notification with a timestamp
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                notification_message = f"{self.handle}<{timestamp}>: Uploaded {filename}"
                self.sck.sendall(f"/broadcast {notification_message}".encode())

                self.display_message(f"{self.handle}<{timestamp}>: Uploaded {filename}")
                self.display_message(f"Uploaded {filename} to server.")
                self.progress_label["text"] = f"Upload of {filename} complete."
            except FileNotFoundError:
                self.display_message(f"Error: File {filename} not found.")
                self.progress_label["text"] = f"Error uploading {filename}."
            except Exception as e:
                self.display_message(f"Error: File upload failed. {e}")
                self.progress_label["text"] = f"Error uploading {filename}."

        threading.Thread(target=upload_file).start()


    def get_dir(self):
        try:
            self.open_dir_socket()
            logging.info("Sending /dir command to server")
            self.dir_sck.sendall("/dir".encode())
            raw_response = self.dir_sck.recv(4096)
            response = raw_response.decode()
            logging.info(f"Raw response: {raw_response}")
            logging.info(f"Received directory listing: {response}")
            self.display_message(response)
        except UnicodeDecodeError as e:
            error_message = f"Error decoding response: {e}"
            logging.error(error_message)
            self.display_message("Received non-text data.")
        except Exception as e:
            error_message = f"Error: {e}"
            logging.error(error_message)
            self.display_message(error_message)
        finally:
            self.close_dir_socket()






    def get_file(self, filename: str):
        threading.Thread(target=self.download_file, args=(filename,)).start()

    def open_file_socket(self):
        self.file_sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.file_sck.connect((self.addr, 5001))

    def close_file_socket(self):
        self.file_sck.close()


    def open_dir_socket(self):
        self.dir_sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.dir_sck.connect((self.addr, 5002))

    def close_dir_socket(self):
        self.dir_sck.close()


    def download_file(self, filename: str):
        try:
            self.open_file_socket()
            self.file_sck.sendall(f"/get {filename}".encode())

            # Receive the first response from the server to check for errors
            initial_response = self.file_sck.recv(4096).decode()
            if initial_response.startswith("Error:"):
                self.display_message(initial_response)
                logging.error(initial_response)
                return

            file_path = os.path.join(self.handle, filename)

            with open(file_path, 'wb') as file:
                file.write(initial_response.encode())  # Write the initial response to the file
                with self.file_sck.makefile('rb') as inp:
                    shutil.copyfileobj(inp, file, length=1024*1024)  # 1MB buffer for better performance


            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            self.display_message(f"{self.handle}<{timestamp}>: Downloaded {filename}")
            self.display_message(f"File {filename} downloaded successfully and received from Server.")
            self.progress_label["text"] = f"Upload of {filename} complete."
            logging.info(f"File {filename} downloaded successfully.")
        
        except Exception as e:
            #self.display_message(f"Error: {e}")
            logging.error(f"Error: {e}")
            logging.error(f"Error while downloading file: {e}")
            self.display_message(f"Error while downloading file: {e}")
        finally:
            self.close_file_socket()

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
                message = self.sck.recv(4096).decode()
                logging.info(f"Received message: {message}")
                self.display_message(message)
            except UnicodeDecodeError:
                error_message = "Received non-text data."
                logging.error(error_message)
                self.display_message(error_message)
            except Exception as e:
                error_message = f"Receive error: {e}"
                logging.error(error_message)
                break








    def is_control_message(self, message):
        if message.isdigit():
            return True
        return False

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
