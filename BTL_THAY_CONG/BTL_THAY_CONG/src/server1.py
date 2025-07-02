import socket
import json
from datetime import datetime, timezone

def log_transaction(message):
    # Sử dụng múi giờ UTC
    with open('logs/nhat_ky_server1.txt', 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} - {message}\n")

def main():
    # Cấu hình
    host = 'localhost'
    port = 8001
    server2_host = 'localhost'
    server2_port = 8002

    # Tạo socket máy chủ
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(1)
    print(f"Server 1 đang lắng nghe tại {host}:{port}")

    while True:
        client, addr = server.accept()
        print(f"Kết nối từ {addr}")
        log_transaction(f"Kết nối từ {addr}")

        # Kết nối đến Server 2
        server2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server2.connect((server2_host, server2_port))

        # Bước 1: Bắt tay
        data = client.recv(1024).decode()
        log_transaction(f"Nhận được Hello! từ người gửi")
        server2.send(data.encode())
        response = server2.recv(1024).decode()
        log_transaction(f"Nhận được Ready! từ Server 2")
        client.send(response.encode())

        # Bước 2: Chuyển tiếp khóa công khai của người nhận
        public_key = server2.recv(4096)
        log_transaction(f"Nhận được khóa công khai của người nhận từ Server 2")
        client.send(public_key)

        # Bước 3: Chuyển tiếp khóa công khai của người gửi
        sender_public_key = client.recv(4096)
        log_transaction(f"Nhận được khóa công khai của người gửi")
        server2.send(sender_public_key)
        log_transaction(f"Đã chuyển tiếp khóa công khai của người gửi đến Server 2")

        # Bước 4: Chuyển tiếp khóa phiên mã hóa
        encrypted_session_key = client.recv(4096)
        log_transaction(f"Nhận được khóa phiên mã hóa từ người gửi")
        server2.send(encrypted_session_key)

        # Bước 5: Chuyển tiếp gói tin
        packet = client.recv(65536).decode()
        log_transaction(f"Nhận được gói tin từ người gửi")
        server2.send(packet.encode())

        # Bước 6: Chuyển tiếp ACK/NACK
        response = server2.recv(1024).decode()
        log_transaction(f"Nhận được {response} từ Server 2")
        client.send(response.encode())

        client.close()
        server2.close()

if __name__ == "__main__":
    main()