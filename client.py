import socket
import sys
import threading

class Client:
    def __init__(self, host='localhost', port=5000):
        """
        Inicializa o cliente com host e porta do servidor.
        """
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
    
    def connect(self):
        """
        Conecta ao servidor.
        """
        try:
            # Cria um socket TCP/IP
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # Conecta ao servidor
            self.socket.connect((self.host, self.port))
            self.connected = True
            print(f"[CLIENTE] Conectado a {self.host}:{self.port}")
            
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
        Recebe mensagens do servidor/outro cliente em uma thread separada.
        """
        try:
            while self.connected:
                data = self.socket.recv(1024)
                
                if not data:
                    break
                
                message = data.decode('utf-8')
                print(f"\n{message}", end='')
                
                # Se a mensagem indica desconexão, interrompe
                if "Seu parceiro desconectou" in message or "Conexão encerrada" in message:
                    self.connected = False
                    break
                
                print("Você: ", end='', flush=True)
                
        except Exception as e:
            if self.connected:
                print(f"\n[ERRO] Erro ao receber mensagem: {e}")
        finally:
            self.connected = False
    
    def send_messages(self):
        """
        Envia mensagens para o servidor.
        """
        print("[CLIENTE] Digite 'sair' para desconectar")
        print("-" * 50)
        print("Você: ", end='', flush=True)
        
        try:
            while self.connected:
                # Obtém entrada do usuário
                message = input("").strip()
                
                # Verifica comando de saída
                if message.lower() == 'sair':
                    print("\n[CLIENTE] Desconectando...")
                    break
                
                # Ignora mensagens vazias
                if not message:
                    print("Você: ", end='', flush=True)
                    continue
                
                # Envia a mensagem para o servidor
                self.socket.sendall(message.encode('utf-8'))
                print("Você: ", end='', flush=True)
                    
        except KeyboardInterrupt:
            print("\n[CLIENTE] Interrompido pelo usuário")
        except Exception as e:
            if self.connected:
                print(f"[ERRO] Erro ao enviar mensagem: {e}")
        finally:
            self.connected = False
    
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
