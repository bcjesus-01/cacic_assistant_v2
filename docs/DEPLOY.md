# Deploy em produção (VM Oracle Cloud)

Roteiro para subir o Assistente CACIC numa VM (testado para Oracle Cloud, instância Ampere
A1 — ARM64, Oracle Linux). Os comandos de `dnf`/`firewalld` abaixo são específicos do Oracle
Linux; numa VM Ubuntu, trocar por `apt`/`ufw`.

Este roteiro assume que você já tem a VM criada e acesso SSH a ela. Tudo aqui é executado
**na VM**, não no seu notebook — exceto o passo 5 (`rsync`), que roda do notebook.

## 1. Instalar o Docker

```bash
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

(Saia e entre de novo via SSH para o grupo `docker` valer, ou use `newgrp docker`.)

**Atenção**: o comando em produção é `docker compose` (plugin v2, sem hífen) — diferente do
`docker-compose` (v1) usado no seu notebook. Os arquivos YAML são compatíveis; só muda a forma
de chamar.

## 2. Abrir o firewall — nas duas camadas

O Oracle Cloud tem duas camadas de firewall independentes. Faltar qualquer uma dá "conexão
recusada" de fora, mesmo com todos os containers rodando.

**a) No console do Oracle Cloud**: na *Security List* (ou *Network Security Group*) da VCN
da sua instância, adicione uma regra de entrada (*ingress*) permitindo TCP nas portas 80 e 443,
origem `0.0.0.0/0`.

**b) Na própria VM** (firewalld, ligado por padrão no Oracle Linux):

```bash
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --reload
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
docker compose -f docker-compose.prod.yml ps   # tudo "Up"
curl http://localhost/health                   # dentro da VM: {"status":"ok"}
```

De fora, acesse `http://IP_DA_VM/` no navegador.

## 8. Checar a RAM disponível

O bge-m3 (modelo de embeddings) precisa de pelo menos 4 GB de RAM só para ele. Confirme com
`free -h` na VM que a forma do Ampere A1 escolhida tem isso disponível.

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
