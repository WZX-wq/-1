#!/bin/bash

# BatchAiCutter 更新服务器部署脚本 (Linux/Mac)

echo "============================================================"
echo "🚀 BatchAiCutter 更新服务器部署脚本"
echo "============================================================"
echo ""

# 设置变量
SERVER_DIR="/var/www/batch-server"
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "📁 服务器目录: $SERVER_DIR"
echo "📁 源文件目录: $SOURCE_DIR"
echo ""

# 检查是否有 root 权限
if [[ $EUID -ne 0 ]]; then
   echo "⚠️  此脚本需要 root 权限"
   echo "请使用: sudo $0"
   exit 1
fi

# 创建服务器目录
if [ ! -d "$SERVER_DIR" ]; then
    echo "📁 创建服务器目录..."
    mkdir -p "$SERVER_DIR"
    mkdir -p "$SERVER_DIR/downloads"
    mkdir -p "$SERVER_DIR/resources"
    echo "✅ 目录创建成功"
    echo ""
fi

# 备份原文件
echo "📦 备份原文件..."
if [ -f "$SERVER_DIR/server.js" ]; then
    BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
    cp "$SERVER_DIR/server.js" "$SERVER_DIR/server.js.backup.$BACKUP_DATE"
    echo "✅ 已备份 server.js"
fi

if [ -f "$SERVER_DIR/package.json" ]; then
    cp "$SERVER_DIR/package.json" "$SERVER_DIR/package.json.backup"
    echo "✅ 已备份 package.json"
fi
echo ""

# 复制新文件
echo "📋 复制新文件..."
cp "$SOURCE_DIR/server.js" "$SERVER_DIR/server.js"
if [ $? -eq 0 ]; then
    echo "✅ server.js 复制成功"
else
    echo "❌ server.js 复制失败"
    exit 1
fi

cp "$SOURCE_DIR/package.json" "$SERVER_DIR/package.json"
if [ $? -eq 0 ]; then
    echo "✅ package.json 复制成功"
else
    echo "❌ package.json 复制失败"
    exit 1
fi
echo ""

# 设置权限
echo "🔐 设置权限..."
chown -R www-data:www-data "$SERVER_DIR"
chmod -R 755 "$SERVER_DIR"
echo "✅ 权限设置成功"
echo ""

# 检查 Node.js
echo "🔍 检查 Node.js..."
if ! command -v node &> /dev/null; then
    echo "❌ 未安装 Node.js"
    echo "Ubuntu/Debian: sudo apt install nodejs npm"
    echo "CentOS/RHEL: sudo yum install nodejs npm"
    exit 1
else
    NODE_VERSION=$(node --version)
    echo "✅ Node.js 版本: $NODE_VERSION"
fi
echo ""

# 安装依赖
echo "📦 安装依赖..."
cd "$SERVER_DIR"
npm install
if [ $? -ne 0 ]; then
    echo "❌ 依赖安装失败"
    exit 1
fi
echo "✅ 依赖安装成功"
echo ""

# 创建 systemd 服务文件
echo "🔧 创建 systemd 服务..."
cat > /etc/systemd/system/batch-server.service << EOF
[Unit]
Description=BatchAiCutter Update Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=$SERVER_DIR
ExecStart=/usr/bin/node $SERVER_DIR/server.js
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=batch-server

[Install]
WantedBy=multi-user.target
EOF

echo "✅ systemd 服务文件创建成功"
echo ""

# 重载 systemd
systemctl daemon-reload

# 显示下一步操作
echo "============================================================"
echo "✅ 部署完成！"
echo "============================================================"
echo ""
echo "📋 下一步操作:"
echo ""
echo "1. 将更新文件放入相应目录:"
echo "   - 主程序: $SERVER_DIR/downloads/"
echo "   - 资源包: $SERVER_DIR/resources/"
echo ""
echo "2. 创建/更新 manifest.json:"
echo "   - 位置: $SERVER_DIR/manifest.json"
echo ""
echo "3. 启动服务:"
echo "   systemctl start batch-server"
echo "   systemctl enable batch-server  # 开机自启"
echo ""
echo "4. 查看状态:"
echo "   systemctl status batch-server"
echo ""
echo "5. 查看日志:"
echo "   journalctl -u batch-server -f"
echo ""
echo "6. 或使用 PM2 (推荐):"
echo "   npm install -g pm2"
echo "   pm2 start server.js --name batch-server"
echo "   pm2 startup"
echo "   pm2 save"
echo ""
echo "============================================================"
echo ""
