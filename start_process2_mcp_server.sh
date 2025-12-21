#!/bin/bash

# 进程2: OrderMCPServer + 数据库 (SQLite)
# 方案A部署脚本

# 创建必要的目录
mkdir -p logs
mkdir -p data

# 检查端口是否被占用
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "⚠️  错误: 端口 $1 已被占用"
        return 1
    fi
    return 0
}

echo "=========================================="
echo "启动进程2: OrderMCPServer + 数据库"
echo "=========================================="
echo ""
echo "说明:"
echo "  - 提供订单相关的 MCP 工具"
echo "  - 管理数据库 (SQLite: ./data/milk_tea.db)"
echo "  - 服务地址: http://localhost:10002"
echo ""

# 检查端口
echo "检查端口 10002..."
if ! check_port 10002; then
    echo ""
    echo "请先停止占用端口 10002 的服务，或使用其他端口"
    exit 1
fi
echo "✓ 端口检查通过"
echo ""

# 检查数据库文件
if [ -f "data/milk_tea.db" ]; then
    echo "✓ 数据库文件已存在: data/milk_tea.db"
else
    echo "ℹ️  数据库文件不存在，将在首次启动时自动创建"
fi
echo ""

# 启动 OrderMCPServer
echo "启动 OrderMCPServer..."
echo "=========================================="
echo ""

# 前台运行（可以看到日志）
python3 order_mcp_server/run_order_mcp_server.py

# 如果需要在后台运行，取消下面的注释
# python3 order_mcp_server/run_order_mcp_server.py > logs/mcp_server.log 2>&1 &
# MCP_PID=$!
# echo $MCP_PID > logs/mcp_server.pid
# echo "OrderMCPServer 已在后台启动 (PID: $MCP_PID)"
# echo "日志文件: logs/mcp_server.log"
