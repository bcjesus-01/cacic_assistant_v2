# Deploy em produção (VM Hetzner Cloud)

Roteiro para subir o Assistente CACIC numa VM (testado para Hetzner Cloud, servidor CX23 —
x86_64, Ubuntu). Os Dockerfiles do projeto não têm nada específico de arquitetura, então o
mesmo roteiro vale pra qualquer VM Ubuntu/Debian x86_64 ou ARM64 de outro provedor, trocando
só o passo 2 (firewall).

Este roteiro assume que você já tem a VM criada e acesso SSH a ela. Tudo aqui é executado
**na VM**, não no seu notebook — exceto o passo 5 (`rsync`), que roda do notebook.

## 1. Instalar o Docker

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

(Saia e entre de novo via SSH para o grupo `docker` valer, ou use `newgrp docker`.)

**Atenção**: o comando em produção é `docker compose` (plugin v2, sem hífen) — diferente do
`docker-compose` (v1) usado no seu notebook. Os arquivos YAML são compatíveis; só muda a forma
de chamar.

## 2. Abrir o firewall

Uma VM nova da Hetzner, por padrão, **não tem nenhum Firewall Cloud anexado** — todas as
portas ficam acessíveis de fora até você anexar um. Diferente do Oracle (duas camadas
restritivas por padrão), aqui o risco é o oposto: esquecer de restringir.

**a) No Hetzner Console**: crie um Firewall (*Firewall* → *Create Firewall*) com regras de
entrada (*Inbound*) permitindo TCP nas portas 22 (SSH), 80 e 443, origem `0.0.0.0/0` (e
`::/0` para IPv6) — depois anexe esse Firewall ao servidor (*Resources* → selecione a VM).
Sem isso, qualquer porta exposta no sistema fica acessível para qualquer IP.

**b) Na própria VM** (`ufw`, instalado mas inativo por padrão no Ubuntu):

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## 3. Clonar o repositório

```bash
git clone https://github.com/bcjesus-01/cacic_assistant_v2.git
cd cacic_assistant_v2
```

## 4. Criar o `.env`

```bash
cp .env.example .env
nano .env   # preencher GOOGLE_API_KEY e POSTGRES_PASSWORD de verdade
```

Nunca comitar esse arquivo — ele só existe no seu notebook e na VM.

## 5. Copiar o índice do Qdrant já pronto

O `qdrant_data/` não vem no `git clone` (é ignorado no repositório, contém dados
institucionais). Ele representa todo o trabalho de chunking das últimas etapas — **copie-o em
vez de reprocessar os PDFs do zero na VM**. Rode isto do seu notebook, com a VM já acessível
por SSH:

```bash
rsync -avz --progress ./qdrant_data/ usuario@IP_DA_VM:~/cacic_assistant_v2/qdrant_data/
```

(`pgdata/`, o histórico de conversas de teste, não precisa ir — a VM começa com banco vazio,
que é o certo para produção.)

## 6. Subir os containers

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

A primeira subida demora: builda as duas imagens e baixa o bge-m3 (~2 GB) uma vez.

## 7. Verificar

```bash
docker compose -f docker-compose.prod.yml ps                     # tudo "Up"
docker exec cacic_assistant_v2-backend-1 python -c \
  "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read().decode())"
```

**Atenção**: `curl http://localhost/health` (via Caddy, porta 80) dá 404 — o Caddyfile só
roteia `/api/*` pro backend, `/health` nunca foi exposto publicamente. Pra testar de fora,
use a API de verdade:

```bash
curl -N -X POST http://IP_DA_VM/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"thread_id":"teste-deploy-01","message":"Quantas horas complementares preciso?"}'
```

De fora, acesse `http://IP_DA_VM/` no navegador pra ver a interface.

## 8. RAM esperada

Medido no notebook (`docker stats`, stack completo em uso normal): backend ~720 MB, frontend
~140 MB, Postgres ~20 MB, Qdrant ~20 MB — pouco menos de 1 GB no total. O CX23 (4 GB) tem
folga real, mesmo contando o sistema operacional e picos de uso concorrente. Confira com
`free -h` na VM depois da subida, por garantia.

## Quando houver um domínio

1. Compre o domínio e aponte um registro DNS **A** para o IP público da VM.
2. No `Caddyfile`, troque `:80` pelo domínio (ex.: `cacic.seudominio.com`).
3. `docker compose -f docker-compose.prod.yml restart caddy`.

O Caddy provisiona o certificado Let's Encrypt automaticamente — nada mais muda.

## Atualizar depois de um novo commit

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```
