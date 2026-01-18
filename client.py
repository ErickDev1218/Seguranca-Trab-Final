import socket
import threading
import sys
import json
import struct
import base64
import os
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

import cryptography_utils.utils as crypto_utils

class Client:
    def __init__(self, host='localhost', port=5000):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.client_id = None
        self.client_name = None
        
        # Estados de Segurança
        self.key_c2s = None # Chave Cliente
        self.key_s2c = None # Chave Servidor
        self.seq_send = 0
        self.seq_recv = 0
        
        try:
            with open("cryptography_utils/server.crt", "rb") as f:
                self.trusted_cert_bytes = f.read()
                self.trusted_cert = x509.load_pem_x509_certificate(
                    self.trusted_cert_bytes, default_backend()
                )
                self.server_rsa_public_key = self.trusted_cert.public_key()
        except FileNotFoundError:
            print("[ERRO] Arquivo 'server.crt' não encontrado. É necessário para verificar a autenticidade do servidor.")
            sys.exit(1)

    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            
            self.client_name = input("Digite seu nome: ").strip() or "Usuario"
            
            #HANDSHAKE SEGURO AGORA!
            print("[SEGURANÇA] Iniciando Handshake seguro...")
            
            sk_C, pk_C_bytes = crypto_utils.generate_ecdh_pair()
            
            hello_payload = json.dumps({
                "type": "hello", 
                "name": self.client_name,
                "public_key": pk_C_bytes.decode('utf-8')
            }).encode('utf-8')
            self._send_raw_frame(hello_payload)
            
            response_data = self._recv_raw_frame()
            if not response_data:
                raise Exception("Conexão fechada pelo servidor durante handshake")
            
            response = json.loads(response_data.decode('utf-8'))
            
            # Extrair dados do handshake
            self.client_id = response['client_id']
            server_pk_pem = response['public_key'].encode()
            salt = base64.b64decode(response['salt'])
            signature = base64.b64decode(response['signature'])
            
            # O transcript aqui é simplificado apenas com pk_C para vincular a sessão
            transcript = pk_C_bytes
            data_to_verify = server_pk_pem + str(self.client_id).encode() + transcript + salt
            
            try:
                self.server_rsa_public_key.verify(
                    signature,
                    data_to_verify,
                    padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                    hashes.SHA256()
                )
                print("[SEGURANÇA] Assinatura do servidor VÁLIDA. Identidade confirmada.")
            except Exception as e:
                print(f"[ERRO FATAL] Assinatura do servidor INVÁLIDA! Possível ataque MitM.")
                return
            
            shared_secret = crypto_utils.compute_shared_secret(sk_C, server_pk_pem)
            self.key_c2s, self.key_s2c = crypto_utils.derive_keys(shared_secret, salt)
            
            print(f"[CLIENTE] Conectado e Criptografado! Seu ID é {self.client_id}")
            self.connected = True
            
            # Iniciar threads
            receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
            receive_thread.start()
            
            self.send_messages()
            
        except Exception as e:
            print(f"[ERRO] Falha na conexão: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.close()

    def receive_messages(self):
        """Recebe e decifra mensagens do servidor."""
        try:
            while self.connected:
                encrypted_frame = self._recv_raw_frame()
                if not encrypted_frame: break
                
                try:
                    plaintext, sender_id, target_id, seq = crypto_utils.decrypt_message(
                        self.key_s2c, encrypted_frame
                    )
                    
                    if seq <= self.seq_recv and self.seq_recv != 0:
                        print(f"\n[ALERTA SEGURANÇA] Pacote duplicado/antigo detectado (Seq: {seq}). Ignorando.")
                        continue
                    self.seq_recv = seq
                    
                    message_data = json.loads(plaintext.decode('utf-8'))
                    self._process_message(message_data)
                    
                    print(">> ", end='', flush=True)
                    
                except Exception as e:
                    print(f"\n[ERRO CRIPTO] Falha ao decifrar mensagem: {e}")
                    
        except Exception as e:
            if self.connected: print(f"\n[ERRO] Loop de recebimento: {e}")
        finally:
            self.connected = False

    def _process_message(self, data):
        m_type = data.get('type')
        if m_type == 'message':
            print(f"\n[MENSAGEM] De {data['from_name']} (ID: {data['from_id']}): {data['message']}")
        elif m_type == 'online_clients':
            print("\n[CLIENTES ONLINE]")
            for c in data.get('clients', []):
                print(f"  ID: {c['id']} - Nome: {c['name']}")
        elif m_type == 'client_joined':
            print(f"\n[NOTIFICAÇÃO] {data['client_name']} (ID: {data['client_id']}) conectou!")
        elif m_type == 'error':
            print(f"\n[ERRO SERVIDOR] {data.get('message')}")

    def send_messages(self):
        print("\n" + "=" * 60)
        print("COMANDOS SEGUROS:")
        print("  /listar - Ver quem está online")
        print("  /enviar <ID> <msg> - Enviar mensagem cifrada")
        print("  /sair - Desconectar")
        print("=" * 60)
        print(">> ", end='', flush=True)
        
        try:
            while self.connected:
                user_input = input("").strip()
                if not user_input: continue
                
                if user_input.lower() == '/sair':
                    break
                
                payload = None
                target_header_id = 0
                
                if user_input.lower() == '/listar':
                    payload = {"type": "get_online_clients"}
                    
                elif user_input.lower().startswith('/enviar '):
                    parts = user_input.split(' ', 2)
                    if len(parts) >= 3:
                        try:
                            tid = int(parts[1])
                            msg = parts[2]
                            payload = {
                                "type": "send_message",
                                "target_id": tid,
                                "message": msg
                            }
                            target_header_id = tid
                        except ValueError:
                            print("ID inválido.")
                    else:
                        print("Uso: /enviar <ID> <mensagem>")
                
                if payload:
                    self._send_encrypted_json(payload, target_header_id)
                
                print(">> ", end='', flush=True)
                
        except KeyboardInterrupt:
            pass
        finally:
            self.connected = False

    def _send_encrypted_json(self, data_dict, target_id):
        json_bytes = json.dumps(data_dict).encode('utf-8')
        
        self.seq_send += 1
        
        encrypted_frame = crypto_utils.encrypt_message(
            self.key_c2s, json_bytes, self.client_id, target_id, self.seq_send
        )
        
        self._send_raw_frame(encrypted_frame)

    def _send_raw_frame(self, data):
        """Envia dados com prefixo de tamanho (4 bytes)."""
        if self.socket:
            self.socket.sendall(struct.pack('!I', len(data)) + data)

    def _recv_raw_frame(self):
        """Lê prefixo de 4 bytes e depois o corpo da mensagem."""
        try:
            len_bytes = self.socket.recv(4)
            if not len_bytes: return None
            length = struct.unpack('!I', len_bytes)[0]
            
            data = b''
            while len(data) < length:
                chunk = self.socket.recv(length - len(data))
                if not chunk: return None
                data += chunk
            return data
        except:
            return None

    def close(self):
        self.connected = False
        if self.socket:
            try: self.socket.close()
            except: pass

if __name__ == "__main__":
    client = Client()
    client.connect()