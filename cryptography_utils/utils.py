import os
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def generate_ecdh_pair():
    """Gera par de chaves efêmeras (ECDHE)"""
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return private_key, public_key_bytes

def compute_shared_secret(private_key, peer_public_key_bytes):
    """Calcula o segredo Z"""
    peer_public_key = serialization.load_pem_public_key(peer_public_key_bytes)
    shared_secret = private_key.exchange(ec.ECDH(), peer_public_key)
    return shared_secret

# --- HKDF (Derivação de Chaves) ---
def derive_keys(shared_secret, salt):
    """
    Deriva chaves no estilo TLS 1.3
    """

    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=b"handshake data",
    )

    key_material = hkdf.derive(shared_secret)

    key_c2s = key_material[:16]
    key_s2c = key_material[16:]

    return key_c2s, key_s2c


# --- AES-GCM ---
def encrypt_message(key, plaintext_bytes, sender_id, target_id, seq_no):
    """
    Header: [Nonce (12B)] + [SenderID (16B)] + [TargetID (16B)] + [SeqNo (8B)]
    """
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    
    # IDs convertidos para 16 bytes (big-endian)
    sender_bytes = sender_id.to_bytes(16, 'big')
    target_bytes = target_id.to_bytes(16, 'big')
    seq_bytes = seq_no.to_bytes(8, 'big')
    
    # AAD: sender_id | recipient_id | seq_no
    aad = sender_bytes + target_bytes + seq_bytes
    
    ciphertext = aesgcm.encrypt(nonce, plaintext_bytes, aad)
    
    # Retorna frame binário completo
    return nonce + aad + ciphertext

def decrypt_message(key, data_bytes):
    """
    Decifra o frame recebido.
    Retorna: (plaintext, sender_id, target_id, seq_no)
    """
    # Extrair campos do cabeçalho (12 + 16 + 16 + 8 = 52 bytes)
    if len(data_bytes) < 52:
        raise ValueError("Mensagem muito curta")
        
    nonce = data_bytes[:12]
    sender_bytes = data_bytes[12:28]
    target_bytes = data_bytes[28:44]
    seq_bytes = data_bytes[44:52]
    ciphertext = data_bytes[52:]
    
    sender_id = int.from_bytes(sender_bytes, 'big')
    target_id = int.from_bytes(target_bytes, 'big')
    seq_no = int.from_bytes(seq_bytes, 'big')
    
    aad = sender_bytes + target_bytes + seq_bytes
    aesgcm = AESGCM(key)
    
    plaintext = aesgcm.decrypt(nonce, ciphertext, aad)
    return plaintext, sender_id, target_id, seq_no