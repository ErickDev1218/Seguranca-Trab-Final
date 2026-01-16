# Seguranca-Trab-Final

Repositório do trabalho final de segurança ministrada pelo Prof. Michel na UFC.

## Sistema de Chat com Mensagens Direcionadas

Um servidor de chat que permite múltiplos clientes se conectarem e enviarem mensagens direcionadas por ID.

### Características

- **Servidor Central**: Mantém lista de todos os clientes conectados
- **ID Único por Cliente**: Cada cliente recebe um ID único ao se conectar
- **Mensagens Direcionadas**: Mensagens são enviadas apenas para o cliente destinatário
- **Lista de Clientes Online**: Todos os clientes podem visualizar quem está online
- **Notificações em Tempo Real**: Notificações quando clientes se conectam ou desconectam

### Como Usar

#### Iniciar o Servidor

```bash
python server.py [host] [porta]
```

Exemplo:
```bash
python server.py localhost 5000
```

#### Conectar um Cliente

```bash
python client.py [host] [porta]
```

Exemplo:
```bash
python client.py localhost 5000
```

Quando conectar, será solicitado que você digite seu nome.

### Comandos do Cliente

- `/listar` - Exibe a lista de clientes conectados
- `/enviar <ID> <mensagem>` - Envia uma mensagem para um cliente específico
- `/sair` - Desconecta do servidor

### Exemplo de Uso

1. Terminal 1 - Servidor:
```
python server.py localhost 5000
```

2. Terminal 2 - Cliente 1:
```
python client.py localhost 5000
Digite seu nome: Alice
[CLIENTE] Bem-vindo Alice! Seu ID é 1
```

3. Terminal 3 - Cliente 2:
```
python client.py localhost 5000
Digite seu nome: Bob
[CLIENTE] Bem-vindo Bob! Seu ID é 2
```

4. Cliente 1 (Alice):
```
>> /listar
[CLIENTES ONLINE]
  ID: 2 - Nome: Bob

>> /enviar 2 Olá Bob!
[ENVIADO] Mensagem enviada para cliente ID 2: Olá Bob!
```

5. Cliente 2 (Bob) recebe:
```
[MENSAGEM] De Alice (ID: 1): Olá Bob!
```

### Protocolo de Comunicação

As mensagens entre cliente e servidor são em formato JSON:

**Cliente enviando mensagem:**
```json
{
  "type": "send_message",
  "target_id": 2,
  "message": "Olá!"
}
```

**Servidor enviando mensagem:**
```json
{
  "type": "message",
  "from_id": 1,
  "from_name": "Alice",
  "message": "Olá!"
}
```

**Lista de clientes online:**
```json
{
  "type": "online_clients",
  "clients": [
    {"id": 1, "name": "Alice"},
    {"id": 2, "name": "Bob"}
  ]
}
```
