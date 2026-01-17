# Seguranca-Trab-Final

Repositório do trabalho final de segurança ministrada pelo Prof. Michel na UFC.

## Versões Disponíveis

### 1. Sistema de Chat Básico
- **`server.py`** e **`client.py`**: Versão básica sem criptografia
- Comunicação em texto simples
- Ideal para entender a arquitetura

### 2. Sistema de Chat Seguro (Recomendado)
- **`server_with_crypt.py`** e **`client_with_crypt.py`**: Versão com criptografia end-to-end
- Implementa ECDH + AES-128-GCM para segurança
- Autenticação RSA do servidor
- Proteção contra replay attacks com sequência de números

## Sistema de Chat com Mensagens Direcionadas

Um servidor de chat que permite múltiplos clientes se conectarem e enviarem mensagens direcionadas por ID.

### Características

- **Servidor Central**: Mantém lista de todos os clientes conectados
- **ID Único por Cliente**: Cada cliente recebe um ID único ao se conectar
- **Mensagens Direcionadas**: Mensagens são enviadas apenas para o cliente destinatário
- **Lista de Clientes Online**: Todos os clientes podem visualizar quem está online
- **Notificações em Tempo Real**: Clientes são notificados quando:
  - Um novo cliente se conecta
  - Um cliente desconecta
  - Novos clientes entram no chat
- **Criptografia End-to-End**: Na versão segura, toda comunicação é criptografada

### Como Usar

#### Opção 1: Versão Básica (Sem Criptografia)

**Iniciar o Servidor:**
```bash
python server.py [host] [porta]
```

Exemplo:
```bash
python server.py localhost 5000
```

**Conectar um Cliente:**
```bash
python client.py [host] [porta]
```

#### Opção 2: Versão Segura (Com Criptografia) - RECOMENDADA

**Preparação (primeira vez):**
```bash
python cryptography_utils/generate_keys.py
```

**Iniciar o Servidor:**
```bash
python server_with_crypt.py [host] [porta]
```

Exemplo:
```bash
python server_with_crypt.py localhost 5000
```

**Conectar um Cliente:**
```bash
python client_with_crypt.py [host] [porta]
```

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

### Sistema de Notificações em Tempo Real

Quando um novo cliente se conecta ao servidor, todos os clientes conectados recebem uma notificação:

```
[NOTIFICAÇÃO] Alice (ID: 1) conectou!
```

Isso permite que os clientes saibam imediatamente quando novos usuários entram no chat, sem precisar usar `/listar`.

### Exemplo de Uso

1. Terminal 1 - Servidor:
```
python server_with_crypt.py localhost 5000
[SERVIDOR] Iniciado em localhost:5000 (Seguro)
```

2. Terminal 2 - Cliente Alice:
```
python client_with_crypt.py localhost 5000
Digite seu nome: Alice
[CLIENTE] Conectado e Criptografado! Seu ID é 1
>> 
```

3. Terminal 3 - Cliente Bob (conecta depois):
```
python client_with_crypt.py localhost 5000
Digite seu nome: Bob
[CLIENTE] Conectado e Criptografado! Seu ID é 2
>> 
```

**Alice recebe automaticamente:**
```
[NOTIFICAÇÃO] Bob (ID: 2) conectou!
>>
```

4. Terminal 4 - Cliente Charlie (conecta depois):
```
python client_with_crypt.py localhost 5000
Digite seu nome: Charlie
[CLIENTE] Conectado e Criptografado! Seu ID é 3
>> 
```

**Alice e Bob recebem automaticamente:**
```
[NOTIFICAÇÃO] Charlie (ID: 3) conectou!
>>
```

5. Alice visualiza clientes online:
```
>> /listar
[CLIENTES ONLINE]
  ID: 2 - Nome: Bob
  ID: 3 - Nome: Charlie
>>
```

6. Alice envia mensagem criptografada para Bob:
```
>> /enviar 2 Oi Bob, como vai?
[ENVIADO] Mensagem enviada para cliente ID 2: Oi Bob, como vai?
>>
```

7. Bob recebe a mensagem (criptografada em trânsito):
```
[MENSAGEM] De Alice (ID: 1): Oi Bob, como vai?
>>
```

**Note:** Charlie não vê a mensagem entre Alice e Bob - é uma comunicação direcionada e privada.

### Protocolo de Comunicação

As mensagens entre cliente e servidor são em formato JSON (opcionalmente criptografadas):

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

**Notificação de novo cliente:**
```json
{
  "type": "client_joined",
  "client_id": 3,
  "client_name": "Charlie"
}
```

**Lista de clientes online:**
```json
{
  "type": "online_clients",
  "clients": [
    {"id": 1, "name": "Alice"},
    {"id": 2, "name": "Bob"},
    {"id": 3, "name": "Charlie"}
  ]
}
```

## Segurança (Versão com Criptografia)

A versão `*_with_crypt.py` implementa os seguintes mecanismos de segurança:

### 1. **Handshake Seguro (TLS-like)**
- Cliente e servidor realizam handshake seguro ao conectar
- Troca de chaves públicas ECDH
- Autenticação do servidor com RSA-2048
- Validação de certificado do servidor

### 2. **Criptografia End-to-End**
- **Algoritmo**: AES-128 em modo GCM (Galois/Counter Mode)
- **Derivação de Chaves**: HKDF-SHA256
- Chaves diferentes para cada direção (C2S e S2C)
- Cada sessão tem chaves únicas

### 3. **Proteção contra Replay Attacks**
- Números de sequência em cada mensagem
- Rejeição automática de pacotes duplicados ou antigos
- Detecta: `[ALERTA SEGURANÇA] Pacote duplicado/antigo detectado`

### 4. **Integridade de Mensagens**
- GCM fornece autenticação de mensagens
- Detecta manipulação ou corrupção de dados
- Mensagens inválidas são rejeitadas

### 5. **Geração Segura de Chaves**
```bash
python cryptography_utils/generate_keys.py
```

Gera:
- Chave privada RSA-2048 (`server_private_key.pem`)
- Certificado X.509 autossignado (`server.crt`)

## Estrutura de Arquivos

```
.
├── server.py                           # Servidor básico (sem criptografia)
├── client.py                           # Cliente básico (sem criptografia)
├── server_with_crypt.py               # Servidor com criptografia
├── client_with_crypt.py               # Cliente com criptografia
├── cryptography_utils/
│   ├── generate_keys.py               # Gera chaves de segurança
│   ├── utils.py                       # Funções criptográficas
│   ├── server_private_key.pem         # Chave privada do servidor (gerada)
│   └── server.crt                     # Certificado do servidor (gerado)
├── README.md                          # Este arquivo
├── MUDANCAS.md                        # Histórico de mudanças
└── GUIA_DE_USO.txt                    # Guia detalhado de uso
```

## Requisitos

- Python 3.8+
- Bibliotecas:
  - `cryptography` (para versão segura)
  - `socket` (built-in)
  - `threading` (built-in)
  - `json` (built-in)
  - `struct` (built-in)

Instale dependências:
```bash
pip install cryptography
```

## Testando o Sistema

### Teste Manual
```bash
# Terminal 1 - Servidor
python3 server_with_crypt.py

# Terminal 2 - Alice
python3 client_with_crypt.py

# Terminal 3 - Bob (depois de Alice conectar)
python3 client_with_crypt.py

# Terminal 4 - Charlie (depois de Bob conectar)
python3 client_with_crypt.py
```

Observe as notificações de novo cliente em tempo real.

### Observações de Segurança

✅ **O que está protegido:**
- Confidencialidade das mensagens (AES-128-GCM)
- Autenticidade do servidor (RSA-2048)
- Integridade das mensagens (GCM)
- Privacidade das conversas (direcionadas)
- Proteção contra replay attacks (sequência)

⚠️ **O que não está protegido (por design):**
- Identidades dos clientes (IDs são públicos)
- Existência de conversas (conhecer quem está online)
- Nomes dos clientes (visíveis para todos)
- Metadados de tempo/sequência
