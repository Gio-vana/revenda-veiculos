#!/usr/bin/env bash
# Prepara um servidor Ubuntu (ex.: AWS EC2 Ubuntu 24.04) para receber o deploy.
# Rode uma única vez no servidor:  bash preparar-servidor.sh
# Pode ser usado também como "User data" na criação da instância EC2.
set -euo pipefail

USUARIO="${SUDO_USER:-${USER:-ubuntu}}"
[ "$USUARIO" = "root" ] && USUARIO=ubuntu

echo ">> Instalando Docker Engine e Compose (repositório oficial da Docker)"
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl rsync
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker "$USUARIO"

echo ">> Criando swap de 2 GB (instâncias pequenas têm pouca memória)"
if ! swapon --show | grep -q /swapfile; then
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo "/swapfile none swap sw 0 0" | sudo tee -a /etc/fstab > /dev/null
fi

echo ">> Criando a rede compartilhada entre os dois repositórios"
sudo docker network inspect revenda-net > /dev/null 2>&1 || sudo docker network create revenda-net

echo ">> Pronto. Saia e entre de novo no SSH para o usuário $USUARIO usar o docker sem sudo."
