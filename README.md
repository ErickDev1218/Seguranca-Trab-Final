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

## Implementação dos Requisitos de Segurança

Esta seção detalha como o código fonte implementa os requisitos de segurança exigidos no projeto, mapeando a teoria (diagramas e especificações) para as funções práticas no Python.

### 1. Mapeamento do Fluxo de Handshake (Diagrama vs Código)

O handshake implementado no método `connect` do Cliente e `handle_client` do Servidor segue rigorosamente o diagrama de sequência proposto.

| Passo (Diagrama) | Implementação no Código (`client_with_crypt.py` / `server_with_crypt.py`) |
| :--- | :--- |
| **1) Envia pk_C_A** | **Cliente:** Gera par ECDH (`crypto_utils.generate_ecdh_pair`) e envia `pk_C_bytes` dentro do payload JSON `type: hello`. |
| **2) Envia pk_S + Assinatura** | **Servidor:** Recebe o hello, gera seu par ECDH, cria um `salt`, e assina digitalmente (`rsa_private_key.sign`) a concatenação das chaves e do ID. Envia tudo no `handshake_response`. |
| **3) Verifica assinatura RSA** | **Cliente:** Utiliza `self.server_rsa_public_key.verify(...)` com padding PSS para garantir que a chave pública do servidor realmente veio do portador da chave privada (autenticidade). |
| **Cálculo de Z (ECDH)** | **Ambos:** Executam `crypto_utils.compute_shared_secret(sk, pk_peer)` para obter o segredo compartilhado sem nunca transmiti-lo pela rede. |
| **Derivação de Chaves (HKDF)** | **Ambos:** Executam `crypto_utils.derive_keys(shared_secret, salt)` implementando o padrão TLS 1.3 para gerar chaves distintas de envio (`key_c2s`) e recebimento (`key_s2c`). |

### 2. Garantias Criptográficas Implementadas

Utilizamos a biblioteca `cryptography.hazmat` para garantir implementações robustas dos algoritmos:

*   **Confidencialidade & Integridade (AES-128-GCM):**
    *   *Código:* No cliente (`_send_encrypted_json`) e no servidor (`_send_secure_message`), as mensagens são cifradas.
    *   *Detalhe:* O modo GCM (Galois/Counter Mode) é um AEAD (Authenticated Encryption with Associated Data), garantindo que se o texto cifrado for alterado no meio do caminho (ataque de integridade), a decifragem falha automaticamente, lançando uma exceção capturada nos blocos `try...except`.

*   **Autenticidade do Servidor (RSA + Certificado):**
    *   *Código:* O cliente carrega o `server.crt` na inicialização (`x509.load_pem_x509_certificate`).
    *   *Segurança:* Isso impede ataques *Man-in-the-Middle* (MitM). Se um atacante tentar se passar pelo servidor, ele não terá a chave privada correspondente ao certificado público que o cliente possui, falhando na verificação da assinatura do handshake.

*   **Sigilo Perfeito (Forward Secrecy - ECDHE):**
    *   *Código:* As chaves `sk_C` e `pk_C` (e as do servidor) são geradas a cada nova conexão (`generate_ecdh_pair()`) e nunca são salvas em disco.
    *   *Benefício:* Se a chave privada RSA do servidor for roubada no futuro, as conversas passadas não podem ser decifradas, pois as chaves de sessão AES eram derivadas de pares efêmeros ECDH que já foram descartados da memória.

### 3. Defesa Contra Ataques de Replay

O sistema implementa contadores monotônicos para evitar que um atacante grave uma mensagem cifrada válida e a reenvie para o servidor ou cliente.

*   **No Cliente:** Mantém `self.seq_recv`. Ao receber mensagem, verifica:
    ```python
    if seq <= self.seq_recv and self.seq_recv != 0:
        print(f"...Pacote duplicado/antigo detectado...")
        continue
    ```
*   **No Servidor:** Mantém um dicionário `connected_clients[id]['seq_recv']`. Se o número de sequência recebido for menor ou igual ao último processado, o pacote é descartado como tentativa de replay.

### 4. Estrutura de Sessão Segura

O servidor mantém o estado seguro de cada cliente em memória, isolando as chaves criptográficas:

```python
self.connected_clients[client_id] = {
    'socket': client_socket,
    'key_c2s': key_c2s, # Chave exclusiva para decifrar mensagens Deste cliente
    'key_s2c': key_s2c, # Chave exclusiva para cifrar mensagens PARA este cliente
    'seq_recv': 0,      # Controle de Replay
    'seq_send': 0       # Controle de Ordenação
}
```

Isso garante que, mesmo que o Servidor seja comprometido em tempo de execução, o vazamento das chaves de um usuário não compromete a comunicação anterior (devido à rotação das chaves efêmeras a cada conexão) e não permite falsificação de mensagens de outros usuários sem as respectivas chaves de sessão.