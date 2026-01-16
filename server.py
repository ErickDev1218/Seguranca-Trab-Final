import socket
import threading
import sys

class ChatRoom:
    def __init__(self):
        """
        Representa uma sala de chat com dois clientes.
        """
        self.client1 = None
        self.client2 = None
        self.lock = threading.Lock()
    
    def is_full(self):
        """
        Verifica se a sala está cheia (2 clientes conectados).
        """
        return self.client1 is not None and self.client2 is not None
    
    def add_client(self, client_info):
        """
        Adiciona um cliente à sala. Retorna True se adicionado, False se sala cheia.
        """
        with self.lock:
            if self.client1 is None:
                self.client1 = client_info
                return True
            elif self.client2 is None:
                self.client2 = client_info
                return True
            return False
    
    def get_other_client(self, current_client):
        """
        Retorna o outro cliente da sala.
        """
        with self.lock:
            if current_client == self.client1:
                return self.client2
            else:
                return self.client1
    
    def remove_client(self, client_info):
        """
        Remove um cliente da sala.
        """
        with self.lock:
            if self.client1 == client_info:
                self.client1 = None
            elif self.client2 == client_info:
                self.client2 = None

class Server:
    def __init__(self, host='localhost', port=5000):
        """
        Inicializa o servidor com host e porta especificados.
        """
        self.host = host
        self.port = port
        self.server_socket = None
        self.waiting_client = None
        self.waiting_lock = threading.Lock()
        self.active_rooms = []
        self.rooms_lock = threading.Lock()
        
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
                        target=self.match_clients,
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
    
    def match_clients(self, client_socket, client_address):
        """
        Tenta fazer matching de dois clientes. Se houver um cliente aguardando,
        cria uma sala de chat. Caso contrário, coloca este cliente em espera.
        """
        client_info = {
            'socket': client_socket,
            'address': client_address
        }
        
        with self.waiting_lock:
            if self.waiting_client is None:
                # Este é o primeiro cliente, coloca em espera
                self.waiting_client = client_info
                print(f"[AGUARDANDO] Cliente {client_address} aguardando parceiro...")
                
                try:
                    # Envia mensagem de espera
                    message = "[SERVIDOR] Aguardando outro cliente se conectar...\n"
                    client_socket.sendall(message.encode('utf-8'))
                except:
                    pass
            else:
                # Há um cliente aguardando, faz o matching
                other_client = self.waiting_client
                self.waiting_client = None
                
                print(f"[MATCH] Conectando {client_address} com {other_client['address']}")
                
                # Cria uma nova sala de chat
                room = ChatRoom()
                room.add_client(client_info)
                room.add_client(other_client)
                
                with self.rooms_lock:
                    self.active_rooms.append(room)
                
                # Inicia chat para ambos os clientes
                thread1 = threading.Thread(
                    target=self.handle_chat,
                    args=(room, client_info),
                    daemon=True
                )
                thread2 = threading.Thread(
                    target=self.handle_chat,
                    args=(room, other_client),
                    daemon=True
                )
                thread1.start()
                thread2.start()
    
    def handle_chat(self, room, client_info):
        """
        Gerencia a comunicação entre dois clientes.
        """
        client_socket = client_info['socket']
        client_address = client_info['address']
        
        try:
            # Envia mensagem de sucesso
            message = f"[SERVIDOR] Conectado! Você está em chat com {room.get_other_client(client_info)['address']}\n"
            client_socket.sendall(message.encode('utf-8'))
            
            while True:
                # Recebe dados do cliente (até 1024 bytes)
                data = client_socket.recv(1024)
                
                if not data:
                    break
                
                # Decodifica a mensagem
                message = data.decode('utf-8').strip()
                print(f"[{client_address[0]}:{client_address[1]}] {message}")
                
                # Obtém o outro cliente
                other_client = room.get_other_client(client_info)
                
                if other_client is None:
                    print(f"[ERRO] Outro cliente desconectou para {client_address}")
                    break
                
                # Envia a mensagem para o outro cliente
                try:
                    formatted_message = f"{client_address[0]}:{client_address[1]} -> {message}\n"
                    other_client['socket'].sendall(formatted_message.encode('utf-8'))
                except Exception as e:
                    print(f"[ERRO] Não foi possível enviar mensagem: {e}")
                    break
                    
        except Exception as e:
            print(f"[ERRO] Erro ao comunicar com {client_address}: {e}")
        finally:
            self.disconnect_client(room, client_info)
    
    def disconnect_client(self, room, client_info):
        """
        Desconecta um cliente e notifica o outro.
        """
        client_address = client_info['address']
        other_client = room.get_other_client(client_info)
        
        # Remove cliente da sala
        room.remove_client(client_info)
        
        # Fecha a conexão
        try:
            client_info['socket'].close()
        except:
            pass
        
        print(f"[DESCONEXÃO] Cliente desconectado: {client_address}")
        
        # Notifica o outro cliente
        if other_client is not None:
            try:
                message = "\n[SERVIDOR] Seu parceiro desconectou. Conexão encerrada.\n"
                other_client['socket'].sendall(message.encode('utf-8'))
                other_client['socket'].close()
            except:
                pass
    
    def close(self):
        """
        Fecha todas as conexões e encerra o servidor.
        """
        print("[SERVIDOR] Fechando conexões...")
        
        # Fecha todas as salas ativas
        with self.rooms_lock:
            for room in self.active_rooms:
                if room.client1:
                    try:
                        room.client1['socket'].close()
                    except:
                        pass
                if room.client2:
                    try:
                        room.client2['socket'].close()
                    except:
                        pass
        
        # Fecha cliente em espera
        with self.waiting_lock:
            if self.waiting_client:
                try:
                    self.waiting_client['socket'].close()
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
