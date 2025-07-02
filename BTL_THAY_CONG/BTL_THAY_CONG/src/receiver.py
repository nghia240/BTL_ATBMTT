import socket
import json
import base64
from Crypto.Cipher import DES, PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA512
from Crypto.Util.Padding import unpad
from datetime import datetime, timezone

def decrypt_file(ciphertext, session_key, iv):
    try:
        cipher = DES.new(session_key, DES.MODE_CBC, iv)
        padded_data = cipher.decrypt(ciphertext)
        return unpad(padded_data, DES.block_size)
    except ValueError as e:
        raise ValueError(f"Lỗi giải mã: {str(e)}")

def log_transaction(message):
    # Sử dụng múi giờ UTC
    with open('logs/nhat_ky_receiver.txt', 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} - {message}\n")

def main():
    # Cấu hình
    host = 'localhost'
    port = 8003

    # Tạo cặp khóa RSA cho người nhận
    receiver_key = RSA.generate(2048)
    receiver_private_key = receiver_key
    receiver_public_key = receiver_key.publickey()

    # Tạo socket máy chủ
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(1)
    print(f"Người nhận đang lắng nghe tại {host}:{port}")
    log_transaction(f"Người nhận bắt đầu lắng nghe tại {host}:{port}")

    while True:
        client, addr = server.accept()
        print(f"Kết nối từ {addr}")
        log_transaction(f"Kết nối từ {addr}")

        # Bước 1: Bắt tay
        data = client.recv(1024).decode()
        if data == "Hello!":
            client.send("Ready!".encode())
            log_transaction("Bắt tay thành công")
        else:
            log_transaction("Bắt tay thất bại")
            client.send("NACK: Bắt tay thất bại".encode())
            client.close()
            continue

        # Bước 2: Gửi khóa công khai của người nhận
        client.send(receiver_public_key.export_key())
        log_transaction("Đã gửi khóa công khai của người nhận")

        # Bước 3: Nhận khóa công khai của người gửi
        sender_public_key_data = client.recv(4096)
        try:
            sender_public_key = RSA.import_key(sender_public_key_data)
            log_transaction("Nhận được khóa công khai của người gửi")
        except Exception as e:
            print(f"Lỗi nhận khóa công khai của người gửi: {e}")
            log_transaction(f"Lỗi nhận khóa công khai của người gửi: {e}")
            client.send("NACK: Lỗi khóa công khai người gửi".encode())
            client.close()
            continue

        # Bước 4: Nhận khóa phiên mã hóa
        encrypted_session_key = base64.b64decode(client.recv(4096))
        cipher_rsa = PKCS1_v1_5.new(receiver_private_key)
        session_key = cipher_rsa.decrypt(encrypted_session_key, None)
        if session_key is None or len(session_key) < 8:
            print("Giải mã khóa phiên thất bại")
            log_transaction("Giải mã khóa phiên thất bại")
            client.send("NACK: Lỗi giải mã khóa phiên".encode())
            client.close()
            continue
        session_key = session_key[:8]  # Trích xuất khóa DES 8 byte
        log_transaction("Nhận và giải mã khóa phiên thành công")

        # Bước 5: Nhận gói tin
        packet_data = client.recv(65536).decode()
        try:
            packet = json.loads(packet_data)
        except json.JSONDecodeError as e:
            print(f"Lỗi phân tích gói tin: {e}")
            log_transaction(f"Lỗi phân tích gói tin: {e}")
            client.send("NACK: Lỗi gói tin".encode())
            client.close()
            continue

        iv = base64.b64decode(packet['iv'])
        ciphertext = base64.b64decode(packet['cipher'])
        received_hash = packet['hash']
        signature = base64.b64decode(packet['sig'])
        metadata = packet['metadata']
        log_transaction("Nhận được gói tin")

        # Kiểm tra băm
        hash_obj = SHA512.new()
        hash_obj.update(iv + ciphertext)
        computed_hash = hash_obj.hexdigest()

        if computed_hash != received_hash:
            print("Kiểm tra băm thất bại")
            log_transaction("Kiểm tra băm thất bại")
            client.send("NACK: Băm không khớp".encode())
            client.close()
            continue
        log_transaction("Kiểm tra băm thành công")

        # Kiểm tra chữ ký số của metadata
        try:
            metadata_json = json.dumps(metadata, sort_keys=True).encode()
            hash_metadata = SHA512.new(metadata_json)
            pkcs1_15.new(sender_public_key).verify(hash_metadata, signature)
            log_transaction("Kiểm tra chữ ký số thành công")
        except Exception as e:
            print(f"Kiểm tra chữ ký thất bại: {e}")
            log_transaction(f"Kiểm tra chữ ký thất bại: {e}")
            client.send(f"NACK: Chữ ký không hợp lệ - {str(e)}".encode())
            client.close()
            continue

        # Giải mã tệp
        try:
            plaintext = decrypt_file(ciphertext, session_key, iv)
            with open('docs/tai_lieu_phap_ly_nhan_duoc.txt', 'wb') as f:
                f.write(plaintext)
            print("Giải mã và ghi file thành công")
            log_transaction("Giải mã và ghi file thành công")
            client.send("ACK: Tệp đã nhận và xác minh".encode())
        except Exception as e:
            print(f"Giải mã thất bại: {e}")
            log_transaction(f"Giải mã thất bại: {e}")
            client.send(f"NACK: Lỗi giải mã - {str(e)}".encode())

        client.close()

if __name__ == "__main__":
    main()