import os
from cryptography.fernet import Fernet

# Vercel Environment Variable se key uthana
# Agar key nahi milti toh default generate hogi (testing ke liye)
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', Fernet.generate_key().decode())

def encrypt_message(message: str) -> bytes:
    f = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)
    return f.encrypt(message.encode())

def decrypt_message(token: bytes) -> str:
    f = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)
    return f.decrypt(token).decode()