#!/bin/bash
# 这是一个快速部署脚本，用于在阿里云服务器上部署iMaoTai-web项目

# 1. 安装依赖
echo "=== 安装必要的依赖 ==="
apt-get update
apt-get install -y curl git openssl

# 2. 安装Docker
echo "=== 安装Docker ==="
curl -fsSL https://get.docker.com | bash -s docker
systemctl enable docker
systemctl start docker

# 3. 安装Docker Compose
echo "=== 安装Docker Compose ==="
curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 4. 创建项目目录
echo "=== 创建项目目录 ==="
mkdir -p /opt/imaotai-web
cd /opt/imaotai-web

# 5. 克隆代码
echo "=== 克隆项目代码 ==="
git clone https://github.com/lu553178681/iMaoTai-web.git .

# 6. 创建SSL证书目录
echo "=== 创建SSL证书目录 ==="
mkdir -p ssl

# 7. 生成自签名SSL证书（如需使用Let's Encrypt，请手动配置）
echo "=== 生成自签名SSL证书 ==="
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout ssl/key.pem -out ssl/cert.pem -subj "/CN=8.136.110.97"

# 8. 创建必要的目录
echo "=== 创建必要目录 ==="
mkdir -p logs/nginx
mkdir -p instance

# 9. 设置目录权限
echo "=== 设置目录权限 ==="
chmod -R 755 instance
chmod -R 755 logs
chmod 644 ssl/*

# 10. 配置防火墙
echo "=== 配置防火墙 ==="
if command -v ufw &> /dev/null; then
    # Ubuntu/Debian
    ufw allow ssh
    ufw allow http
    ufw allow https
    ufw --force enable
elif command -v firewall-cmd &> /dev/null; then
    # CentOS
    firewall-cmd --permanent --add-service=ssh
    firewall-cmd --permanent --add-service=http
    firewall-cmd --permanent --add-service=https
    firewall-cmd --reload
else
    echo "无法识别防火墙类型，请手动配置防火墙"
fi

# 11. 启动服务
echo "=== 启动服务 ==="
docker-compose up -d

# 12. 显示服务状态
echo "=== 服务状态 ==="
docker-compose ps

echo "=== 部署完成 ==="
echo "现在可以通过以下地址访问应用："
echo "HTTP: http://8.136.110.97"
echo "HTTPS: https://8.136.110.97" 