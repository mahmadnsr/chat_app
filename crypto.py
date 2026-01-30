from cryptography.fernet import Fernet


# Each user generates and stores this locally


def generate_key():
  return Fernet.generate_key()




def encrypt_message(key: bytes, message: str) -> bytes:
  f = Fernet(key)
  return f.encrypt(message.encode())




def decrypt_message(key: bytes, token: bytes) -> str:
  f = Fernet(key)
  return f.decrypt(token).decode()