#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

IMAGE="ghcr.io/lillinlin/alicdt-manager:latest"
INSTALL_DIR="/app/alicdt-manager"

echo -e "${GREEN}=============================="
echo "   AliCDT Manager 一键安装"
echo -e "==============================${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}正在安装 Docker...${NC}"
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker && systemctl start docker
fi

mkdir -p "$INSTALL_DIR/data" && cd "$INSTALL_DIR"

read -p "服务端口 [8000]: " PORT
PORT=${PORT:-8000}

SECRET_KEY=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | head -c 48)

cat > docker-compose.yml << COMPOSEEOF
services:
  alicdt-manager:
    image: ${IMAGE}
    container_name: alicdt-manager
    restart: always
    ports:
      - "127.0.0.1:${PORT}:8000"
    volumes:
      - ./data:/app/data
    environment:
      - TZ=Asia/Shanghai
      - SECRET_KEY=${SECRET_KEY}
COMPOSEEOF

docker compose pull
docker compose up -d

echo -e "${GREEN}=============================="
echo "   安装完成！端口: ${PORT}"
echo "   首次访问请设置管理员账号"
echo -e "==============================${NC}"
