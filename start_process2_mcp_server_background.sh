#!/bin/bash

# 进程2: OrderMCPServer + 数据库 (后台运行)
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
echo "启动进程2: OrderMCPServer + 数据库 (后台)"
echo "=========================================="
echo ""

# 检查端口
echo "检查端口 10002..."
if ! check_port 10002; then
    echo ""
    echo "请先停止占用端口 10002 的服务"
    exit 1
fi
echo "✓ 端口检查通过"
echo ""

# 启动 OrderMCPServer（后台运行）
echo "启动 OrderMCPServer..."
python3 order_mcp_server/run_order_mcp_server.py > logs/mcp_server.log 2>&1 &
MCP_PID=$!
echo $MCP_PID > logs/mcp_server.pid

sleep 3

# 检查是否启动成功
if curl -s http://localhost:10002/mcp/health > /dev/null 2>&1; then
    echo "✓ OrderMCPServer 启动成功"
    echo ""
    echo "服务信息:"
    echo "  - PID: $MCP_PID"
    echo "  - 端口: 10002"
    echo "  - 地址: http://localhost:10002"
    echo "  - 日志: logs/mcp_server.log"
    echo ""
    echo "停止服务:"
    echo "  ./stop_process2_mcp_server.sh"
else
    echo "⚠️  OrderMCPServer 可能未成功启动"
    echo "请检查日志: logs/mcp_server.log"
    exit 1
fi
