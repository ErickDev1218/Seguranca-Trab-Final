import socket
import threading
import sys

class Server:
    def __init__(self, host='localhost', port=5000):
        """
        Inicializa o servidor com host e porta especificados.
        """
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = []
        self.lock = threading.Lock()
        
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
                    
                    # Adiciona à lista de clientes
                    with self.lock:
                        self.clients.append((client_socket, client_address))
                    
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
        Trata a comunicação com um cliente específico.
        """
        try:
            while True:
                # Recebe dados do cliente (até 1024 bytes)
                data = client_socket.recv(1024)
                
                if not data:
                    break
                
                # Decodifica a mensagem
                message = data.decode('utf-8')
                print(f"[{client_address[0]}:{client_address[1]}] {message}")
                
                # Envia resposta de volta
                response = f"Servidor recebeu: {message}"
                client_socket.sendall(response.encode('utf-8'))
                
        except Exception as e:
            print(f"[ERRO] Erro ao comunicar com {client_address}: {e}")
        finally:
            # Remove cliente da lista e fecha a conexão
            with self.lock:
                self.clients = [(s, addr) for s, addr in self.clients if addr != client_address]
            client_socket.close()
            print(f"[DESCONEXÃO] Cliente desconectado: {client_address}")
    
    def close(self):
        """
        Fecha todas as conexões e encerra o servidor.
        """
        print("[SERVIDOR] Fechando conexões...")
        
        with self.lock:
            for client_socket, _ in self.clients:
                try:
                    client_socket.close()
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
