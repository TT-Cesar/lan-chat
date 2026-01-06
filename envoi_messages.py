import socket
import json
from crypto_functions import encrypt_bytes, decrypt_bytes  # Le code de votre camarade

def send_encrypted_message(sock, key, message):
    """Envoie un message chiffré via socket"""
    # 1. Convertir le message texte en bytes
    message_bytes = message.encode('utf-8')
    
    # 2. Chiffrer
    nonce_b64, ciphertext_b64 = encrypt_bytes(key, message_bytes)
    
    # 3. Créer un paquet JSON
    packet = {
        'nonce': nonce_b64,
        'ciphertext': ciphertext_b64
    }
    
    # 4. Envoyer via socket
    sock.sendall(json.dumps(packet).encode('utf-8') + b'\n')

def receive_encrypted_message(sock, key):
    """Reçoit et déchiffre un message"""
    # 1. Recevoir les données
    data = sock.recv(4096).decode('utf-8').strip()
    
    # 2. Parser le JSON
    packet = json.loads(data)
    
    # 3. Déchiffrer
    plaintext_bytes = decrypt_bytes(key, packet['nonce'], packet['ciphertext'])
    
    # 4. Convertir en texte
    return plaintext_bytes.decode('utf-8')