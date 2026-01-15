import socket
import sys

class Client:
    def __init__(self, host='localhost', port=5000):
        """
        Inicializa o cliente com host e porta do servidor.
        """
        self.host = host
        self.port = port
        self.socket = None
    
    def connect(self):
        """
        Conecta ao servidor.
        """
        try:
            # Cria um socket TCP/IP
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # Conecta ao servidor
            self.socket.connect((self.host, self.port))
            print(f"[CLIENTE] Conectado a {self.host}:{self.port}")
            
            # Inicia o loop de comunicação
            self.communicate()
            
        except ConnectionRefusedError:
            print(f"[ERRO] Não foi possível conectar a {self.host}:{self.port}")
            print("[ERRO] Verifique se o servidor está rodando.")
        except Exception as e:
            print(f"[ERRO] Erro ao conectar: {e}")
        finally:
            self.close()
    
    def communicate(self):
        """
        Comunica com o servidor através de entrada do usuário.
        """
        print("[CLIENTE] Digite 'sair' para desconectar")
        print("-" * 50)
        
        while True:
            try:
                # Obtém entrada do usuário
                message = input("Você: ").strip()
                
                # Verifica comando de saída
                if message.lower() == 'sair':
                    print("[CLIENTE] Desconectando...")
                    break
                
                # Ignora mensagens vazias
                if not message:
                    continue
                
                # Envia a mensagem para o servidor
                self.socket.sendall(message.encode('utf-8'))
                
                # Recebe resposta do servidor
                response = self.socket.recv(1024)
                if response:
                    response_text = response.decode('utf-8')
                    print(f"Servidor: {response_text}")
                else:
                    print("[ERRO] Servidor desconectou")
                    break
                    
            except KeyboardInterrupt:
                print("\n[CLIENTE] Interrompido pelo usuário")
                break
            except Exception as e:
                print(f"[ERRO] Erro na comunicação: {e}")
                break
    
    def close(self):
        """
        Fecha a conexão com o servidor.
        """
        if self.socket:
            try:
                self.socket.close()
                print("[CLIENTE] Desconectado")
            except:
                pass


if __name__ == "__main__":
    # Define host e porta (pode ser alterado via argumentos)
    host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
    
    client = Client(host, port)
    client.connect()
