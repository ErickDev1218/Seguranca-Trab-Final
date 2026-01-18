# Sistema de Chat Seguro (Trabalho Final - Segurança da Informação)

Implementação de uma aplicação de mensageria multi-cliente segura, desenvolvida como trabalho final da disciplina de Segurança da Informação (UFC - Prof. Michel).

O sistema garante **confidencialidade**, **integridade**, **autenticidade** e **sigilo perfeito (forward secrecy)** utilizando uma arquitetura híbrida de criptografia (RSA + ECDHE + AES-GCM).

## Características do Sistema

- **Arquitetura Cliente-Servidor Seguro**: O servidor atua como um _trusted relay_, gerenciando conexões e roteando mensagens.
- **Criptografia Hop-by-Hop**:
  - A comunicação Cliente $\leftrightarrow$ Servidor é totalmente criptografada.
  - O servidor decifra a mensagem de origem e a re-cifra para o destinatário (garantindo validação e log de tráfego seguro).
- **Protocolo de Handshake Seguro (TLS-like)**:
  - Troca de chaves efêmeras via **ECDH** (Elliptic Curve Diffie-Hellman).
  - Autenticação do servidor via assinatura **RSA-2048**.
  - Derivação de chaves de sessão via **HKDF-SHA256**.
- **Proteção de Dados**:
  - **Confidencialidade & Integridade**: Uso de **AES-128-GCM** (Authenticated Encryption).
  - **Anti-Replay**: Controle rigoroso com números de sequência (`seq_no`) para rejeitar pacotes duplicados ou antigos.
- **Funcionalidades de Chat**:
  - Mensagens direcionadas (Unicast) por ID.
  - Listagem de usuários online segura.

## Tecnologias e Dependências

O projeto utiliza **Python 3.10+** e o gerenciador de pacotes **uv** para alta performance na resolução de dependências.

### Gerenciador de Pacotes: `uv`

Optamos pelo uso do [uv](https://github.com/astral-sh/uv) por ser extremamente rápido, escrito em Rust, e substituir o pip/virtualenv com uma gestão de _lockfile_ mais robusta e determinística.

### Bibliotecas Principais

- **`cryptography`**: Primitivas criptográficas (X.509, Hazmat, RSA, AES-GCM).
- **`socket` / `threading`**: Gerenciamento de rede e concorrência.

## Instalação e Execução

### 1. Pré-requisitos

Certifique-se de ter o Python instalado. Recomenda-se instalar o `uv`:

```bash
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Instalar Dependências

Na raiz do projeto, sincronize o ambiente virtual:

```bash
uv sync
```

_Isso criará automaticamente o `.venv` e instalará a biblioteca `cryptography` conforme definido no `pyproject.toml`._

### 3. Geração de Chaves (Setup Inicial)

Antes de rodar o servidor pela primeira vez, é necessário gerar o par de chaves RSA do servidor e seu certificado autoassinado.

```bash
uv run cryptography_utils/generate_keys.py
```

_Saída esperada:_ Arquivos `server_private_key.pem` e `server.crt` criados em `cryptography_utils/`.

### 4. Iniciando o Servidor

O servidor ficará aguardando conexões e gerenciando a troca de chaves.

```bash
uv run server.py
# Opcional: uv run server.py [host] [porta]
```

### 5. Iniciando Clientes

Abra novos terminais para simular múltiplos clientes (Alice, Bob, etc.). O cliente precisará do `server.crt` gerado anteriormente para validar a autenticidade do servidor.

```bash
uv run client.py
# Opcional: uv run client.py [host] [porta]
```

## Guia de Uso

Ao conectar, digite seu nome. O sistema realizará automaticamente o handshake criptográfico.

### Comandos Disponíveis

- `/listar`: Solicita ao servidor a lista de usuários online (a resposta vem cifrada).
- `/enviar <ID> <mensagem>`: Envia uma mensagem cifrada para um destino específico.
- `/sair`: Encerra a conexão segura e destrói as chaves de sessão locais.

### Exemplo de Fluxo

**Terminal 1 (Servidor):**

```text
[SERVIDOR] Iniciado em localhost:5000 (Seguro)
[CONEXÃO] Nova conexão...
[HANDSHAKE] Sucesso com Alice (ID: 1)
```

**Terminal 2 (Alice):**

```text
Digite seu nome: Alice
[SEGURANÇA] Assinatura do servidor VÁLIDA. Identidade confirmada.
[CLIENTE] Conectado e Criptografado! Seu ID é 1
>> /listar
[CLIENTES ONLINE]
  ID: 2 - Nome: Bob
>> /enviar 2 Olá, Bob!
```

**Terminal 3 (Bob):**

```text
[NOTIFICAÇÃO] Alice (ID: 1) conectou!
...
[MENSAGEM] De Alice (ID: 1): Olá, Bob!
```

## Detalhes da Implementação de Segurança

O protocolo implementado segue os requisitos estritos do trabalho:

### 1. Handshake (Estabelecimento de Sessão)

1.  **Cliente Hello**: Envia sua chave pública efêmera ECDH (`pk_C`).
2.  **Server Hello**: Servidor gera seu par ECDH, assina os parâmetros (`pk_S + client_id + transcript + salt`) com sua **Chave Privada RSA**.
3.  **Verificação**: Cliente valida a assinatura usando o `server.crt` (Certificado Pinado). Isso previne ataques _Man-in-the-Middle_.
4.  **Derivação**: Ambos calculam o segredo compartilhado e usam **HKDF** para derivar duas chaves simétricas de 128-bits:
    - `Key_C2S`: Para cifrar dados do Cliente -> Servidor.
    - `Key_S2C`: Para cifrar dados do Servidor -> Cliente.

### 2. Transporte de Mensagens (AES-GCM)

Cada mensagem enviada possui a seguinte estrutura de pacote binário:
`[Tamanho 4B] [Nonce/IV] [Ciphertext + Tag de Autenticação]`

- **AES-128-GCM**: Garante que apenas quem tem a chave da sessão pode ler (Confidencialidade) e que a mensagem não foi alterada no caminho (Integridade).
- **Sigilo Perfeito**: Como as chaves são efêmeras (geradas a cada conexão via ECDH) e nunca salvas em disco, o comprometimento da chave RSA do servidor no futuro não permite decifrar conversas passadas.

### 3. Prevenção de Replay Attack

O sistema mantém contadores de sequência (`seq_send` e `seq_recv`) para cada cliente.

- Se o servidor ou cliente receberem uma mensagem com `seq` menor ou igual ao último recebido, o pacote é descartado imediatamente e um alerta de segurança é gerado:
  `[ALERTA SEGURANÇA] Pacote duplicado/antigo detectado`.

## Estrutura de Arquivos 📂

```
.
├── server.py                   # Lógica do servidor (Socket + Cripto + Roteamento)
├── client.py                   # Cliente (Interface + Cripto + Handshake)
├── cryptography_utils/
│   ├── generate_keys.py        # Script auxiliar para gerar RSA e X.509
│   ├── utils.py                # Wrapper das primitivas (AES, ECDH, HKDF)
│   ├── server.crt              # Certificado público (distribuído aos clientes)
│   └── server_private_key.pem  # Chave privada (apenas no servidor)
├── pyproject.toml              # Definição do projeto e dependências (UV)
└── uv.lock                     # Lockfile para garantir reprodutibilidade
```
