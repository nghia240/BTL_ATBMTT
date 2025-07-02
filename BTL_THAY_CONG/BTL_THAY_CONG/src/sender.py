import socket
import json
import base64
import os
import time
from datetime import datetime, timezone
from Crypto.Cipher import DES, PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA512
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad

def generate_session_key():
    return get_random_bytes(8)  # Khóa DES là 8 byte

def encrypt_file(file_path, session_key, iv):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Tệp {file_path} không tồn tại!")
    cipher = DES.new(session_key, DES.MODE_CBC, iv)
    with open(file_path, 'rb') as f:
        plaintext = f.read()
    padded_data = pad(plaintext, DES.block_size)
    ciphertext = cipher.encrypt(padded_data)
    return ciphertext

def log_transaction(message):
    # Sử dụng múi giờ UTC
    with open('logs/nhat_ky_sender.txt', 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} - {message}\n")

def main():
    # Cấu hình
    server1_host = 'localhost'
    server1_port = 8001
    file_path = 'docs/legal_doc.txt'
    transaction_id = 'TXN_' + str(int(time.time()))

    try:
        # Tạo cặp khóa RSA cho người gửi
        sender_key = RSA.generate(2048)
        sender_private_key = sender_key
        sender_public_key = sender_key.publickey()

        # Tạo socket
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((server1_host, server1_port))

        # Bước 1: Bắt tay
        client.send("Hello!".encode())
        response = client.recv(1024).decode()
        log_transaction(f"Nhận được: {response}")
        if response != "Ready!":
            print("Bắt tay thất bại")
            log_transaction("Bắt tay thất bại")
            client.close()
            return

        # Bước 2: Nhận khóa công khai của người nhận và gửi khóa công khai của người gửi
        receiver_public_key_data = client.recv(4096)
        receiver_public_key = RSA.import_key(receiver_public_key_data)
        log_transaction("Nhận được khóa công khai của người nhận")
        client.send(sender_public_key.export_key())  # Gửi khóa công khai của người gửi
        log_transaction("Đã gửi khóa công khai của người gửi")

        # Bước 3: Tạo khóa phiên và IV
        session_key = generate_session_key()
        iv = get_random_bytes(8)

        # Mã hóa khóa phiên bằng khóa công khai của người nhận
        cipher_rsa = PKCS1_v1_5.new(receiver_public_key)
        encrypted_session_key = cipher_rsa.encrypt(session_key)
        client.send(base64.b64encode(encrypted_session_key))
        log_transaction("Đã gửi khóa phiên mã hóa")

        # Bước 4: Mã hóa tệp và tính toán băm
        ciphertext = encrypt_file(file_path, session_key, iv)
        hash_obj = SHA512.new()
        hash_obj.update(iv + ciphertext)
        file_hash = hash_obj.hexdigest()

        # Tạo siêu dữ liệu và ký
        metadata = {
            "ten_tep": os.path.basename(file_path),
            "thoi_gian": datetime.now(timezone.utc).isoformat(),  # Sử dụng UTC cho metadata
            "id_giao_dich": transaction_id
        }
        metadata_json = json.dumps(metadata, sort_keys=True).encode()  # Sử dụng sort_keys=True
        hash_metadata = SHA512.new(metadata_json)
        signature = pkcs1_15.new(sender_private_key).sign(hash_metadata)
        log_transaction("Đã tạo chữ ký cho metadata")

        # Tạo gói tin
        packet = {
            "iv": base64.b64encode(iv).decode(),
            "cipher": base64.b64encode(ciphertext).decode(),
            "hash": file_hash,
            "sig": base64.b64encode(signature).decode(),
            "metadata": metadata
        }

        # Gửi gói tin
        client.send(json.dumps(packet).encode())
        log_transaction("Đã gửi gói tin")

        # Bước 5: Nhận ACK/NACK
        response = client.recv(1024).decode()
        print(f"Nhận được: {response}")
        log_transaction(f"Nhận được: {response}")

    except FileNotFoundError as e:
        print(f"Lỗi: {e}")
        log_transaction(f"Lỗi: {e}")
    except Exception as e:
        print(f"Lỗi kết nối hoặc xử lý: {e}")
        log_transaction(f"Lỗi: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    main()