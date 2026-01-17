import socket
import threading
import sys
import json
import struct
import base64
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
import os

import cryptography_utils.utils as crypto_utils

class Server:
    def __init__(self, host='localhost', port=5000):
        self.host = host
        self.port = port
        self.server_socket = None
        # Estrutura: {client_id: {'socket': sock, 'name': name, 'keys': (c2s, s2c), 'seq_recv': 0, 'seq_send': 0}}
        self.connected_clients = {}
        self.client_lock = threading.Lock()
        self.client_id_counter = 0
        
        try:
            with open("cryptography_utils/server_private_key.pem", "rb") as key_file:
                self.rsa_private_key = serialization.load_pem_private_key(
                    key_file.read(), password=None
                )
            with open("cryptography_utils/server.crt", "rb") as cert_file:
                self.cert_pem = cert_file.read()
            print("[SISTEMA] Chaves RSA carregadas com sucesso.")
        except FileNotFoundError:
            print("[ERRO] Chaves não encontradas! Rode o script generate_keys.py primeiro.")
            sys.exit(1)

    def _generate_client_id(self):
        with self.client_lock:
            self.client_id_counter += 1
            return self.client_id_counter
        
    def start(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            print(f"[SERVIDOR] Iniciado em {self.host}:{self.port} (Seguro)")
            
            while True:
                client_socket, client_address = self.server_socket.accept()
                print(f"[CONEXÃO] Nova conexão: {client_address}")
                
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address),
                    daemon=True
                )
                client_thread.start()
        except KeyboardInterrupt:
            print("\n[SERVIDOR] Encerrando...")
        finally:
            self.close()

    def handle_client(self, client_socket, client_address):
        client_id = None
        try:
            header = client_socket.recv(4)
            if not header: return
            msg_len = struct.unpack('!I', header)[0]
            data = client_socket.recv(msg_len)
            
            client_hello = json.loads(data.decode('utf-8'))
            client_name = client_hello.get('name', 'Anonimo')
            client_pk_pem = client_hello['public_key'].encode()
            
            client_id = self._generate_client_id()
            server_sk, server_pk_pem = crypto_utils.generate_ecdh_pair()
            salt = os.urandom(16)
            
            transcript = client_pk_pem
            
            data_to_sign = server_pk_pem + str(client_id).encode() + transcript + salt
            
            signature = self.rsa_private_key.sign(
                data_to_sign,
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                hashes.SHA256()
            )
            
            response = {
                'type': 'handshake_response',
                'client_id': client_id,
                'public_key': server_pk_pem.decode(),
                'salt': base64.b64encode(salt).decode(),
                'signature': base64.b64encode(signature).decode(),
                'cert': self.cert_pem.decode()
            }
            resp_bytes = json.dumps(response).encode('utf-8')
            client_socket.sendall(struct.pack('!I', len(resp_bytes)) + resp_bytes)
            
            shared_secret = crypto_utils.compute_shared_secret(server_sk, client_pk_pem)
            key_c2s, key_s2c = crypto_utils.derive_keys(shared_secret, salt)
            
            with self.client_lock:
                self.connected_clients[client_id] = {
                    'socket': client_socket,
                    'name': client_name,
                    'key_c2s': key_c2s,
                    'key_s2c': key_s2c,
                    'seq_recv': 0, # Esperado do cliente
                    'seq_send': 0  # Próximo a enviar
                }
            
            print(f"[HANDSHAKE] Sucesso com {client_name} (ID: {client_id})")
            
            while True:
                len_bytes = client_socket.recv(4)
                if not len_bytes: break
                frame_len = struct.unpack('!I', len_bytes)[0]
                
                encrypted_frame = b''
                while len(encrypted_frame) < frame_len:
                    chunk = client_socket.recv(frame_len - len(encrypted_frame))
                    if not chunk: break
                    encrypted_frame += chunk

                
                try:
                    plaintext, sid, tid, seq = crypto_utils.decrypt_message(
                        key_c2s, encrypted_frame
                    )
                    
                    current_seq = self.connected_clients[client_id]['seq_recv']
                    if seq <= current_seq and current_seq != 0:
                        print(f"[ALERTA] Replay detectado de ID {client_id}")
                        continue 
                    self.connected_clients[client_id]['seq_recv'] = seq
                    
                    msg_data = json.loads(plaintext.decode('utf-8'))
                    msg_type = msg_data.get('type')
                    
                    if msg_type == 'send_message':
                        target_id = msg_data.get('target_id')
                        content = msg_data.get('message')
                        self._send_secure_message(client_id, target_id, content)
                        
                    elif msg_type == 'get_online_clients':
                        self._send_online_list_secure(client_id)
                        
                except Exception as e:
                    print(f"[ERRO CRIPTO] Cliente {client_id}: {e}")
                    break
                    
        except Exception as e:
            print(f"[ERRO] Falha na conexão: {e}")
        finally:
            self.disconnect_client(client_id)

    def _send_secure_message(self, sender_id, target_id, content):
        with self.client_lock:
            if target_id not in self.connected_clients:
                return
            
            target_info = self.connected_clients[target_id]
            sender_name = self.connected_clients[sender_id]['name']
            
            payload = json.dumps({
                'type': 'message',
                'from_id': sender_id,
                'from_name': sender_name,
                'message': content
            }).encode('utf-8')
            
            key = target_info['key_s2c']
            seq = target_info['seq_send'] + 1
            target_info['seq_send'] = seq
            
            encrypted_frame = crypto_utils.encrypt_message(key, payload, sender_id, target_id, seq)
            
            try:
                target_info['socket'].sendall(struct.pack('!I', len(encrypted_frame)) + encrypted_frame)
                print(f"[ENCAMINHADO] {sender_id} -> {target_id}")
            except:
                pass

    def _send_online_list_secure(self, requestor_id):
        with self.client_lock:
            clients_list = [{'id': c, 'name': i['name']} for c, i in self.connected_clients.items() if c != requestor_id]
            
            payload = json.dumps({
                'type': 'online_clients',
                'clients': clients_list
            }).encode('utf-8')
            
            info = self.connected_clients[requestor_id]
            key = info['key_s2c']
            seq = info['seq_send'] + 1
            info['seq_send'] = seq
            
            encrypted_frame = crypto_utils.encrypt_message(key, payload, 0, requestor_id, seq)
            info['socket'].sendall(struct.pack('!I', len(encrypted_frame)) + encrypted_frame)

    def disconnect_client(self, client_id):
        if client_id in self.connected_clients:
            with self.client_lock:
                try:
                    self.connected_clients[client_id]['socket'].close()
                except: pass
                del self.connected_clients[client_id]
            print(f"[DESCONEXÃO] Cliente {client_id} saiu.")
    
    def close(self):
        if self.server_socket: self.server_socket.close()

if __name__ == "__main__":
    server = Server()
    server.start()