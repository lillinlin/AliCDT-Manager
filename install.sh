#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

GITHUB_USER="YOUR_GITHUB_USERNAME"
IMAGE="ghcr.io/${GITHUB_USER}/aliyun-guard:latest"
INSTALL_DIR="/app/aliyun-guard"

echo -e "${GREEN}=================================="
echo "   Aliyun Guard 一键安装"
echo -e "==================================${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}正在安装 Docker...${NC}"
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker && systemctl start docker
fi

mkdir -p "$INSTALL_DIR/data" && cd "$INSTALL_DIR"

read -p "用户名 [admin]: " ADMIN_USER; ADMIN_USER=${ADMIN_USER:-admin}
read -s -p "密码 [admin123]: " ADMIN_PASS; echo; ADMIN_PASS=${ADMIN_PASS:-admin123}
read -p "服务端口 [8000]: " PORT; PORT=${PORT:-8000}

SECRET_KEY=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | head -c 32)

cat > docker-compose.yml << EOF
services:
  aliyun-guard:
    image: ${IMAGE}
    container_name: aliyun-guard
    restart: always
    ports:
      - "127.0.0.1:${PORT}:8000"
    volumes:
      - ./data:/app/data
    environment:
      - TZ=Asia/Shanghai
      - ADMIN_USERNAME=${ADMIN_USER}
      - ADMIN_PASSWORD=${ADMIN_PASS}
      - SECRET_KEY=${SECRET_KEY}
    dns:
      - 8.8.8.8
      - 1.1.1.1
EOF

docker compose pull && docker compose up -d

echo -e "${GREEN}=================================="
echo "   安装完成！端口: ${PORT} 用户名: ${ADMIN_USER}"
echo -e "==================================${NC}"
