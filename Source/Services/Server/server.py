# TODO:
# Develop a communication protocol between rasp. and the client (mobile app). Depending on certain header,
# it should be interpreted as either photos from a specific person (given for training) or as a 

import socket

HOST = "127.0.0.1"
PORT = 5000

def server_handler():    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen(1)
        print(f"[SERVER] Listening on {HOST or '0.0.0.0'}:{PORT} ...")

        conn, addr = s.accept()
        with conn:
            print(f"[SERVER] Connected by {addr}")

            filename = conn.recv(256).decode().strip()
            print(f"[SERVER] Receiving file: {filename}")            
            
            with open(filename, "wb") as f:
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break
                    f.write(data)
            print(f"[SERVER] File '{filename}' received successfully!")    
        