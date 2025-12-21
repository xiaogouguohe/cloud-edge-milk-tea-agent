#!/bin/bash

# 进程3: OrderAgent (后台运行)
# 方案A部署脚本

# 创建必要的目录
mkdir -p logs

# 检查端口是否被占用
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "⚠️  错误: 端口 $1 已被占用"
        return 1
    fi
    return 0
}

echo "=========================================="
echo "启动进程3: OrderAgent (后台)"
echo "=========================================="
echo ""

# 检查端口
echo "检查端口 10006..."
if ! check_port 10006; then
    echo ""
    echo "请先停止占用端口 10006 的服务"
    exit 1
fi
echo "✓ 端口检查通过"
echo ""

# 检查前置服务（可选）
if curl -s http://localhost:10002/mcp/health > /dev/null 2>&1; then
    echo "✓ OrderMCPServer 已启动"
else
    echo "⚠️  OrderMCPServer 未启动（建议先启动进程2）"
fi
echo ""

# 启动 OrderAgent（后台运行）
echo "启动 OrderAgent..."
python3 order_agent/run_order_agent.py > logs/order_agent.log 2>&1 &
AGENT_PID=$!
echo $AGENT_PID > logs/order_agent.pid

sleep 3

# 检查是否启动成功
if curl -s http://localhost:10006/a2a/health > /dev/null 2>&1; then
    echo "✓ OrderAgent 启动成功"
    echo ""
    echo "服务信息:"
    echo "  - PID: $AGENT_PID"
    echo "  - 端口: 10006"
    echo "  - 地址: http://localhost:10006"
    echo "  - 日志: logs/order_agent.log"
    echo ""
    echo "停止服务:"
    echo "  ./stop_process3_order_agent.sh"
else
    echo "⚠️  OrderAgent 可能未成功启动"
    echo "请检查日志: logs/order_agent.log"
    exit 1
fi
