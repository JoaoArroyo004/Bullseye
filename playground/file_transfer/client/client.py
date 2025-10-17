import socket
import os

SERVER_IP = "127.0.0.1"
PORT = 5000

def main():
    filepath = "test_image.jpg"
    filename = os.path.basename(filepath)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((SERVER_IP, PORT))
        print(f"[CLIENT] Connected to {SERVER_IP}:{PORT}")
        
        s.sendall(filename.encode().ljust(256, b" "))

        with open(filepath, "rb") as f:
            s.sendfile(f)

        print(f"[CLIENT] File '{filename}' sent successfully!")

if __name__ == "__main__":
    main()
