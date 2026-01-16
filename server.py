import socket
import threading
import sys
import json
import time

class Server:
    def __init__(self, host='localhost', port=5000):
        """
        Inicializa o servidor com host e porta especificados.
        """
        self.host = host
        self.port = port
        self.server_socket = None
        self.connected_clients = {}  # {client_id: {'socket': socket, 'address': address, 'name': name}}
        self.client_lock = threading.Lock()
        self.client_id_counter = 0
        
    def _generate_client_id(self):
        """
        Gera um ID único para cada cliente.
        """
        with self.client_lock:
            self.client_id_counter += 1
            return self.client_id_counter
        
    def start(self):
        """
        Inicia o servidor e começa a aceitar conexões.
        """
        try:
            # Cria um socket TCP/IP
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # Permite reutilizar o endereço
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Liga o socket ao host e porta
            self.server_socket.bind((self.host, self.port))
            
            # Coloca o socket em modo de escuta (máximo 5 conexões pendentes)
            self.server_socket.listen(5)
            
            print(f"[SERVIDOR] Iniciado em {self.host}:{self.port}")
            print("[SERVIDOR] Aguardando conexões...")
            
            # Aceita conexões indefinidamente
            while True:
                try:
                    # Aceita uma conexão de cliente
                    client_socket, client_address = self.server_socket.accept()
                    
                    print(f"[CONEXÃO] Cliente conectado: {client_address}")
                    
                    # Cria uma thread para lidar com o cliente
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_address),
                        daemon=True
                    )
                    client_thread.start()
                    
                except KeyboardInterrupt:
                    print("\n[SERVIDOR] Encerrando...")
                    break
                except Exception as e:
                    print(f"[ERRO] Erro ao aceitar conexão: {e}")
                    
        except OSError as e:
            print(f"[ERRO] Erro ao iniciar servidor: {e}")
        finally:
            self.close()
    
    def handle_client(self, client_socket, client_address):
        """
        Gerencia a conexão e comunicação com um cliente.
        """
        client_id = None
        
        try:
            # Recebe o nome do cliente
            data = client_socket.recv(1024)
            if not data:
                return
            
            client_name = data.decode('utf-8').strip()
            client_id = self._generate_client_id()
            
            # Registra o cliente
            with self.client_lock:
                self.connected_clients[client_id] = {
                    'socket': client_socket,
                    'address': client_address,
                    'name': client_name
                }
            
            print(f"[CLIENTE CONECTADO] ID: {client_id}, Nome: {client_name}, Endereço: {client_address}")
            
            # Envia confirmação com o ID
            response = json.dumps({
                'type': 'connection_confirmed',
                'client_id': client_id,
                'message': f'Bem-vindo {client_name}! Seu ID é {client_id}'
            })
            client_socket.sendall(response.encode('utf-8'))
            
            # Envia lista inicial de clientes online
            self._send_online_clients_list(client_id)
            
            # Notifica outros clientes que um novo cliente conectou
            self._broadcast_client_joined(client_id)
            
            # Loop para receber mensagens
            while True:
                data = client_socket.recv(1024)
                
                if not data:
                    break
                
                message_str = data.decode('utf-8').strip()
                
                try:
                    message_data = json.loads(message_str)
                    message_type = message_data.get('type')
                    
                    if message_type == 'get_online_clients':
                        # Cliente solicita lista de clientes online
                        self._send_online_clients_list(client_id)
                    
                    elif message_type == 'send_message':
                        # Cliente envia mensagem direcionada
                        target_id = message_data.get('target_id')
                        content = message_data.get('message')
                        
                        self._send_direct_message(client_id, target_id, content)
                    
                except json.JSONDecodeError:
                    print(f"[ERRO] Mensagem inválida de cliente {client_id}")
                    
        except Exception as e:
            print(f"[ERRO] Erro ao comunicar com cliente {client_id}: {e}")
        finally:
            self.disconnect_client(client_id)
    
    def _send_online_clients_list(self, client_id):
        """
        Envia a lista de clientes online para um cliente específico.
        """
        try:
            with self.client_lock:
                if client_id not in self.connected_clients:
                    return
                
                clients_list = []
                for cid, info in self.connected_clients.items():
                    if cid != client_id:  # Não inclui o próprio cliente na lista
                        clients_list.append({
                            'id': cid,
                            'name': info['name']
                        })
                
                response = json.dumps({
                    'type': 'online_clients',
                    'clients': clients_list
                })
                
                client_socket = self.connected_clients[client_id]['socket']
                client_socket.sendall(response.encode('utf-8'))
        except Exception as e:
            print(f"[ERRO] Erro ao enviar lista de clientes para {client_id}: {e}")
    
    def _send_direct_message(self, sender_id, target_id, message_content):
        """
        Envia uma mensagem de um cliente para outro cliente específico.
        """
        try:
            with self.client_lock:
                if target_id not in self.connected_clients:
                    # Cliente alvo não existe ou desconectou
                    if sender_id in self.connected_clients:
                        response = json.dumps({
                            'type': 'error',
                            'message': f'Cliente com ID {target_id} não está online'
                        })
                        self.connected_clients[sender_id]['socket'].sendall(response.encode('utf-8'))
                    return
                
                # Prepara a mensagem
                sender_info = self.connected_clients.get(sender_id)
                sender_name = sender_info['name'] if sender_info else 'Desconhecido'
                
                message = json.dumps({
                    'type': 'message',
                    'from_id': sender_id,
                    'from_name': sender_name,
                    'message': message_content
                })
                
                # Envia apenas para o cliente alvo
                self.connected_clients[target_id]['socket'].sendall(message.encode('utf-8'))
                
                print(f"[MENSAGEM] {sender_name} (ID: {sender_id}) -> Cliente ID {target_id}: {message_content}")
                
        except Exception as e:
            print(f"[ERRO] Erro ao enviar mensagem direta: {e}")
    
    def _broadcast_client_joined(self, new_client_id):
        """
        Notifica todos os clientes que um novo cliente conectou.
        """
        try:
            with self.client_lock:
                new_client_info = self.connected_clients[new_client_id]
                
                notification = json.dumps({
                    'type': 'client_joined',
                    'client_id': new_client_id,
                    'client_name': new_client_info['name']
                })
                
                # Envia notificação para todos os clientes
                for client_id, client_info in self.connected_clients.items():
                    if client_id != new_client_id:  # Não notifica o próprio cliente
                        try:
                            client_info['socket'].sendall(notification.encode('utf-8'))
                        except:
                            pass
        except Exception as e:
            print(f"[ERRO] Erro ao notificar clientes sobre nova conexão: {e}")
    
    def disconnect_client(self, client_id):
        """
        Desconecta um cliente e notifica os outros.
        """
        if client_id is None:
            return
        
        try:
            with self.client_lock:
                if client_id in self.connected_clients:
                    client_info = self.connected_clients[client_id]
                    client_name = client_info['name']
                    
                    # Fecha a conexão
                    try:
                        client_info['socket'].close()
                    except:
                        pass
                    
                    # Remove da lista
                    del self.connected_clients[client_id]
                    
                    print(f"[DESCONEXÃO] Cliente desconectado: ID {client_id}, Nome: {client_name}")
                    
                    # Notifica outros clientes
                    notification = json.dumps({
                        'type': 'client_left',
                        'client_id': client_id,
                        'client_name': client_name
                    })
                    
                    for cid, info in self.connected_clients.items():
                        try:
                            info['socket'].sendall(notification.encode('utf-8'))
                        except:
                            pass
        except Exception as e:
            print(f"[ERRO] Erro ao desconectar cliente {client_id}: {e}")
    
    def close(self):
        """
        Fecha todas as conexões e encerra o servidor.
        """
        print("[SERVIDOR] Fechando conexões...")
        
        with self.client_lock:
            for client_id, client_info in self.connected_clients.items():
                try:
                    client_info['socket'].close()
                except:
                    pass
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        print("[SERVIDOR] Encerrado!")


if __name__ == "__main__":
    # Define host e porta (pode ser alterado via argumentos)
    host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
    
    server = Server(host, port)
    server.start()
