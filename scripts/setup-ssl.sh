#!/bin/bash
# Let's Encrypt SSL 证书获取脚本
# 使用前请安装 certbot: apt-get install certbot

set -e

DOMAIN=${1:-"your-domain.com"}
EMAIL=${2:-"admin@${DOMAIN}"}
SSL_DIR="./front/ssl"

echo "=== 为 ${DOMAIN} 获取 SSL 证书 ==="

# 创建 SSL 目录
mkdir -p "${SSL_DIR}"

# 使用 certbot 获取证书 (standalone 模式)
sudo certbot certonly --standalone \
  -d "${DOMAIN}" \
  --email "${EMAIL}" \
  --agree-tos \
  --non-interactive

# 复制证书到项目目录
sudo cp /etc/letsencrypt/live/${DOMAIN}/fullchain.pem "${SSL_DIR}/"
sudo cp /etc/letsencrypt/live/${DOMAIN}/privkey.pem "${SSL_DIR}/"
sudo chmod 644 "${SSL_DIR}/fullchain.pem"
sudo chmod 600 "${SSL_DIR}/privkey.pem"

echo "=== 证书已保存到 ${SSL_DIR}/ ==="
echo "请将 SSL 目录挂载到 Docker 容器 /etc/nginx/ssl/"
