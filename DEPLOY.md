# i茅台Web项目部署指南

本文档指导如何使用Docker将i茅台Web项目部署到阿里云服务器。

## 前提条件

- 已有阿里云服务器（公网IP：8.136.110.97）
- 操作系统：CentOS/Ubuntu/Debian等Linux系统
- 已安装Docker和Docker Compose

## 安装Docker和Docker Compose（如未安装）

### 安装Docker

```bash
# CentOS系统
curl -fsSL https://get.docker.com | bash -s docker

# Ubuntu/Debian系统
apt-get update
apt-get install -y docker.io
```

### 安装Docker Compose

```bash
curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
```

## 部署步骤

1. 登录到阿里云服务器

```bash
ssh root@8.136.110.97
```

2. 创建项目目录并进入

```bash
mkdir -p /opt/imaotai-web
cd /opt/imaotai-web
```

3. 下载项目代码

```bash
git clone https://github.com/lu553178681/iMaoTai-web.git .
# 或手动上传项目文件到此目录
```

4. 修改配置文件（如有必要）

编辑.env文件，设置必要的API Key和密钥：

```bash
nano .env
```

5. 配置SSL证书（用于HTTPS）

创建SSL证书目录：

```bash
mkdir -p ssl
```

有两种方式获取SSL证书：

- **方法1：使用自签名证书（测试用途）**

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout ssl/key.pem -out ssl/cert.pem
```

- **方法2：使用Let's Encrypt免费证书（推荐，需要域名）**

如果有自己的域名，可以使用certbot获取免费证书：

```bash
apt-get install certbot
certbot certonly --standalone -d yourdomain.com
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/cert.pem
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/key.pem
```

6. 使用Docker Compose启动服务

```bash
docker-compose up -d
```

7. 验证服务是否正常运行

```bash
docker-compose ps
```

8. 访问Web界面

- HTTP: `http://8.136.110.97`（将自动重定向到HTTPS）
- HTTPS: `https://8.136.110.97`

## 防火墙配置

配置防火墙，只开放必要端口：

```bash
# Ubuntu/Debian系统
apt-get install -y ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw enable

# CentOS系统
firewall-cmd --permanent --add-service=ssh
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --reload
```

## 系统安全加固

1. **更新系统包**

```bash
# Ubuntu/Debian
apt-get update && apt-get upgrade -y

# CentOS
yum update -y
```

2. **设置强密码**

```bash
passwd
```

3. **禁用root SSH登录**

编辑SSH配置文件：

```bash
nano /etc/ssh/sshd_config
```

找到并修改：

```
PermitRootLogin no
```

重启SSH服务：

```bash
systemctl restart sshd
```

## 常用操作命令

- 查看容器日志：`docker-compose logs -f`
- 重启服务：`docker-compose restart`
- 停止服务：`docker-compose down`
- 更新代码后重建容器：`docker-compose up -d --build`

## 数据备份

定期备份数据库和配置文件：

```bash
# 创建备份目录
mkdir -p /backup/imaotai-web

# 备份脚本
cat > /backup/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_DIR="/backup/imaotai-web/$DATE"
mkdir -p $BACKUP_DIR
cp -r /opt/imaotai-web/instance $BACKUP_DIR/
cp /opt/imaotai-web/.env $BACKUP_DIR/
EOF

chmod +x /backup/backup.sh

# 添加到定时任务
echo "0 2 * * * /backup/backup.sh" >> /var/spool/cron/crontabs/root
```

## 常见问题排查

1. **无法访问网站**
   - 检查容器状态：`docker-compose ps`
   - 查看容器日志：`docker-compose logs -f`
   - 检查防火墙配置：`ufw status` 或 `firewall-cmd --list-all`

2. **SSL证书问题**
   - 检查证书路径是否正确
   - 确认证书权限：`chmod 644 ssl/*`

3. **数据库问题**
   - 检查instance目录权限：`chmod -R 755 instance`

## 数据持久化

数据库文件存储在`./instance`目录中，该目录已通过volume挂载到容器内部，确保数据持久化。

## 技术支持

如有任何问题，请参考原项目的GitHub仓库：https://github.com/lu553178681/iMaoTai-web