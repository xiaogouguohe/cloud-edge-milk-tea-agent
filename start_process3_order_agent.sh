#!/bin/bash

# 进程3: OrderAgent (A2A Server)
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
echo "启动进程3: OrderAgent"
echo "=========================================="
echo ""
echo "说明:"
echo "  - 作为 A2A Server，接收 SupervisorAgent 的调用"
echo "  - 通过 MCP 协议调用 OrderMCPServer 的工具"
echo "  - 服务地址: http://localhost:10006"
echo ""

# 检查端口
echo "检查端口 10006..."
if ! check_port 10006; then
    echo ""
    echo "请先停止占用端口 10006 的服务，或使用其他端口"
    exit 1
fi
echo "✓ 端口检查通过"
echo ""

# 检查前置服务（可选）
check_service() {
    if curl -s $1 > /dev/null 2>&1; then
        echo "  ✓ $2 已启动"
        return 0
    else
        echo "  ⚠️  $2 未启动（可选，但建议先启动）"
        return 1
    fi
}

echo "检查前置服务（可选）..."
check_service "http://localhost:10002/mcp/health" "OrderMCPServer"
echo ""

# 启动 OrderAgent
echo "启动 OrderAgent..."
echo "=========================================="
echo ""

# 前台运行（可以看到日志）
python3 order_agent/run_order_agent.py

# 如果需要在后台运行，取消下面的注释
# python3 order_agent/run_order_agent.py > logs/order_agent.log 2>&1 &
# AGENT_PID=$!
# echo $AGENT_PID > logs/order_agent.pid
# echo "OrderAgent 已在后台启动 (PID: $AGENT_PID)"
# echo "日志文件: logs/order_agent.log"
