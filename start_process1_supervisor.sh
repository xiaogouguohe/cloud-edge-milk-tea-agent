#!/bin/bash

# 进程1: SupervisorAgent (用户对话入口)
# 方案A部署脚本

echo "=========================================="
echo "启动进程1: SupervisorAgent"
echo "=========================================="
echo ""
echo "说明:"
echo "  - 这是用户对话入口"
echo "  - 会路由请求到 OrderAgent"
echo "  - 通过 A2A 协议调用 OrderAgent (http://localhost:10006)"
echo ""
echo "前置条件:"
echo "  - 进程2 (OrderMCPServer) 应该已启动 (端口 10002)"
echo "  - 进程3 (OrderAgent) 应该已启动 (端口 10006)"
echo ""

# 检查前置服务是否启动
check_service() {
    if curl -s $1 > /dev/null 2>&1; then
        echo "  ✓ $2 已启动"
        return 0
    else
        echo "  ✗ $2 未启动"
        return 1
    fi
}

echo "检查前置服务..."
if ! check_service "http://localhost:10006/a2a/health" "OrderAgent"; then
    echo ""
    echo "⚠️  警告: OrderAgent 未启动"
    echo "请先启动进程3:"
    echo "  ./start_process3_order_agent.sh"
    echo ""
    read -p "是否继续启动 SupervisorAgent? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "已取消"
        exit 1
    fi
fi

if ! check_service "http://localhost:10002/mcp/health" "OrderMCPServer"; then
    echo ""
    echo "⚠️  警告: OrderMCPServer 未启动"
    echo "请先启动进程2:"
    echo "  ./start_process2_mcp_server.sh"
    echo ""
    read -p "是否继续启动 SupervisorAgent? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "已取消"
        exit 1
    fi
fi

echo ""
echo "=========================================="
echo "启动 SupervisorAgent..."
echo "=========================================="
echo ""

# 启动 SupervisorAgent
python3 chat.py
