import socket
import json
from datetime import datetime, timezone

def log_transaction(message):
    # Sử dụng múi giờ UTC
    with open('logs/nhat_ky_server2.txt', 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} - {message}\n")

def main():
    # Cấu hình
    host = 'localhost'
    port = 8002
    receiver_host = 'localhost'
    receiver_port = 8003

    # Tạo socket máy chủ
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(1)
    print(f"Server 2 đang lắng nghe tại {host}:{port}")

    while True:
        client, addr = server.accept()
        print(f"Kết nối từ {addr}")
        log_transaction(f"Kết nối từ {addr}")

        # Kết nối đến người nhận
        receiver = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        receiver.connect((receiver_host, receiver_port))

        # Bước 1: Bắt tay
        data = client.recv(1024).decode()
        log_transaction(f"Nhận được Hello! từ Server 1")
        receiver.send(data.encode())
        response = receiver.recv(1024).decode()
        log_transaction(f"Nhận được Ready! từ người nhận")
        client.send(response.encode())

        # Bước 2: Chuyển tiếp khóa công khai của người nhận
        public_key = receiver.recv(4096)
        log_transaction(f"Nhận được khóa công khai từ người nhận")
        client.send(public_key)

        # Bước 3: Chuyển tiếp khóa công khai của người gửi
        sender_public_key = client.recv(4096)
        log_transaction(f"Nhận được khóa công khai của người gửi từ Server 1")
        receiver.send(sender_public_key)
        log_transaction(f"Đã chuyển tiếp khóa công khai của người gửi đến người nhận")

        # Bước 4: Chuyển tiếp khóa phiên mã hóa
        encrypted_session_key = client.recv(4096)
        log_transaction(f"Nhận được khóa phiên mã hóa từ Server 1")
        receiver.send(encrypted_session_key)

        # Bước 5: Chuyển tiếp gói tin
        packet = client.recv(65536).decode()
        log_transaction(f"Nhận được gói tin từ Server 1")
        receiver.send(packet.encode())

        # Bước 6: Chuyển tiếp ACK/NACK
        response = receiver.recv(1024).decode()
        log_transaction(f"Nhận được {response} từ người nhận")
        client.send(response.encode())

        client.close()
        receiver.close()

if __name__ == "__main__":
    main()