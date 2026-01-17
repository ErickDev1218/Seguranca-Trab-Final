import socket
import sys
import threading
import json

class Client:
    def __init__(self, host='localhost', port=5000):
        """
        Inicializa o cliente com host e porta do servidor.
        """
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.client_id = None
        self.client_name = None
        self.online_clients = {}  # {client_id: client_name}
        self.clients_lock = threading.Lock()
    
    def connect(self):
        """
        Conecta ao servidor e inicia a comunicação.
        """
        try:
            # Cria um socket TCP/IP
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # Conecta ao servidor
            self.socket.connect((self.host, self.port))
            
            # Solicita nome do usuário
            self.client_name = input("Digite seu nome: ").strip()
            if not self.client_name:
                self.client_name = "Usuário"
            
            # Envia o nome para o servidor
            self.socket.sendall(self.client_name.encode('utf-8'))
            
            # Recebe confirmação e ID
            data = self.socket.recv(1024)
            response = json.loads(data.decode('utf-8'))
            
            self.client_id = response.get('client_id')
            print(f"\n{response.get('message')}")
            print(f"[CLIENTE] Conectado a {self.host}:{self.port}")
            
            self.connected = True
            
            # Inicia thread para receber mensagens
            receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
            receive_thread.start()
            
            # Loop para enviar mensagens
            self.send_messages()
            
        except ConnectionRefusedError:
            print(f"[ERRO] Não foi possível conectar a {self.host}:{self.port}")
            print("[ERRO] Verifique se o servidor está rodando.")
        except Exception as e:
            print(f"[ERRO] Erro ao conectar: {e}")
        finally:
            self.close()
    
    def receive_messages(self):
        """
        Recebe mensagens do servidor em uma thread separada.
        """
        try:
            while self.connected:
                data = self.socket.recv(1024)
                
                if not data:
                    break
                
                message_str = data.decode('utf-8')
                
                try:
                    message_data = json.loads(message_str)
                    message_type = message_data.get('type')
                    
                    if message_type == 'connection_confirmed':
                        # Já foi tratado na conexão
                        pass
                    
                    elif message_type == 'online_clients':
                        # Atualiza lista de clientes online
                        self._handle_online_clients_list(message_data)
                    
                    elif message_type == 'message':
                        # Recebe mensagem direcionada
                        self._handle_incoming_message(message_data)
                    
                    elif message_type == 'client_joined':
                        # Um novo cliente conectou
                        self._handle_client_joined(message_data)
                    
                    elif message_type == 'client_left':
                        # Um cliente desconectou
                        self._handle_client_left(message_data)
                    
                    elif message_type == 'error':
                        # Erro do servidor
                        print(f"\n[ERRO SERVIDOR] {message_data.get('message')}")
                    
                except json.JSONDecodeError:
                    print(f"\n[MENSAGEM] {message_str}")
                
                print(">> ", end='', flush=True)
                    
        except Exception as e:
            if self.connected:
                print(f"\n[ERRO] Erro ao receber mensagem: {e}")
        finally:
            self.connected = False
    
    def send_messages(self):
        """
        Envia mensagens para o servidor.
        """
        print("\n" + "=" * 60)
        print("COMANDOS:")
        print("  /listar - Mostra clientes online")
        print("  /enviar <ID> <mensagem> - Envia mensagem para cliente com ID")
        print("  /sair - Desconecta do servidor")
        print("=" * 60)
        print(">> ", end='', flush=True)
        
        try:
            while self.connected:
                # Obtém entrada do usuário
                user_input = input("").strip()
                
                # Verifica comando de saída
                if user_input.lower() == '/sair':
                    print("\n[CLIENTE] Desconectando...")
                    break
                
                # Comando para listar clientes online
                elif user_input.lower() == '/listar':
                    self._show_online_clients()
                    print(">> ", end='', flush=True)
                    continue
                
                # Comando para enviar mensagem
                elif user_input.lower().startswith('/enviar '):
                    parts = user_input.split(' ', 2)
                    if len(parts) >= 3:
                        try:
                            target_id = int(parts[1])
                            message_content = parts[2]
                            self._send_direct_message(target_id, message_content)
                        except ValueError:
                            print("[ERRO] ID inválido. Use: /enviar <ID> <mensagem>")
                    else:
                        print("[ERRO] Use: /enviar <ID> <mensagem>")
                    print(">> ", end='', flush=True)
                    continue
                
                # Ignora mensagens vazias
                if not user_input:
                    print(">> ", end='', flush=True)
                    continue
                
                print("[INFO] Use /enviar <ID> <mensagem> para enviar uma mensagem")
                print(">> ", end='', flush=True)
                    
        except KeyboardInterrupt:
            print("\n[CLIENTE] Interrompido pelo usuário")
        except Exception as e:
            if self.connected:
                print(f"[ERRO] Erro ao enviar mensagem: {e}")
        finally:
            self.connected = False
    
    def _send_direct_message(self, target_id, message_content):
        """
        Envia uma mensagem direcionada para um cliente específico.
        """
        try:
            message = json.dumps({
                'type': 'send_message',
                'target_id': target_id,
                'message': message_content
            })
            self.socket.sendall(message.encode('utf-8'))
            print(f"[ENVIADO] Mensagem enviada para cliente ID {target_id}: {message_content}")
        except Exception as e:
            print(f"[ERRO] Erro ao enviar mensagem: {e}")
    
    def _handle_online_clients_list(self, data):
        """
        Processa a lista de clientes online.
        """
        clients = data.get('clients', [])
        with self.clients_lock:
            self.online_clients = {client['id']: client['name'] for client in clients}
        
        print("\n[CLIENTES ONLINE]")
        if not self.online_clients:
            print("  Nenhum outro cliente online")
        else:
            for client_id, client_name in self.online_clients.items():
                print(f"  ID: {client_id} - Nome: {client_name}")
    
    def _show_online_clients(self):
        """
        Exibe a lista de clientes online atuais.
        """
        print("\n[CLIENTES ONLINE]")
        with self.clients_lock:
            if not self.online_clients:
                print("  Nenhum outro cliente online")
            else:
                for client_id, client_name in self.online_clients.items():
                    print(f"  ID: {client_id} - Nome: {client_name}")
    
    def _handle_incoming_message(self, data):
        """
        Processa uma mensagem recebida.
        """
        from_id = data.get('from_id')
        from_name = data.get('from_name')
        message_content = data.get('message')
        
        print(f"\n[MENSAGEM] De {from_name} (ID: {from_id}): {message_content}")
    
    def _handle_client_joined(self, data):
        """
        Processa notificação de cliente que se conectou.
        """
        client_id = data.get('client_id')
        client_name = data.get('client_name')
        
        with self.clients_lock:
            self.online_clients[client_id] = client_name
        
        print(f"\n[NOTIFICAÇÃO] {client_name} (ID: {client_id}) conectou!")
    
    def _handle_client_left(self, data):
        """
        Processa notificação de cliente que desconectou.
        """
        client_id = data.get('client_id')
        client_name = data.get('client_name')
        
        with self.clients_lock:
            if client_id in self.online_clients:
                del self.online_clients[client_id]
        
        print(f"\n[NOTIFICAÇÃO] {client_name} (ID: {client_id}) desconectou!")
    
    def close(self):
        """
        Fecha a conexão com o servidor.
        """
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
                print("\n[CLIENTE] Desconectado")
            except:
                pass


if __name__ == "__main__":
    # Define host e porta (pode ser alterado via argumentos)
    host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
    
    client = Client(host, port)
    client.connect()
