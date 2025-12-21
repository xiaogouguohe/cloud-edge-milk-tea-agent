#!/bin/bash

# 启动后台服务（进程2和进程3）
# 用于方案A部署

# 创建日志目录
mkdir -p logs

# 检查端口是否被占用
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "⚠️  警告: 端口 $1 已被占用"
        return 1
    fi
    return 0
}

echo "=========================================="
echo "启动后台服务（方案A）"
echo "=========================================="
echo ""
echo "将启动:"
echo "  进程2: OrderMCPServer + 数据库"
echo "  进程3: OrderAgent"
echo ""

# 检查端口
echo "检查端口..."
if ! check_port 10002; then
    echo "请先停止占用端口 10002 的服务"
    exit 1
fi
if ! check_port 10006; then
    echo "请先停止占用端口 10006 的服务"
    exit 1
fi
echo "✓ 端口检查通过"
echo ""

# 启动 OrderMCPServer（进程2，后台运行）
echo "进程2: 启动 OrderMCPServer + 数据库 (端口 10002)..."
python3 order_mcp_server/run_order_mcp_server.py > logs/mcp_server.log 2>&1 &
MCP_PID=$!
echo "   OrderMCPServer PID: $MCP_PID"
sleep 3

# 检查 MCP Server 是否启动成功
if curl -s http://localhost:10002/mcp/health > /dev/null 2>&1; then
    echo "   ✓ OrderMCPServer 启动成功"
else
    echo "   ⚠️  MCP Server 可能未成功启动，请检查日志: logs/mcp_server.log"
fi
echo ""

# 启动 OrderAgent（进程3，后台运行）
echo "进程3: 启动 OrderAgent (端口 10006)..."
python3 business_agent/run_business_agent.py > logs/order_agent.log 2>&1 &
AGENT_PID=$!
echo "   OrderAgent PID: $AGENT_PID"
sleep 3

# 检查 OrderAgent 是否启动成功
if curl -s http://localhost:10006/a2a/health > /dev/null 2>&1; then
    echo "   ✓ OrderAgent 启动成功"
else
    echo "   ⚠️  OrderAgent 可能未成功启动，请检查日志: logs/order_agent.log"
fi
echo ""

# 保存 PID 到文件
echo $MCP_PID > logs/mcp_server.pid
echo $AGENT_PID > logs/order_agent.pid

echo "=========================================="
echo "后台服务已启动"
echo "=========================================="
echo ""
echo "服务状态:"
echo "  进程2 - OrderMCPServer: http://localhost:10002 (PID: $MCP_PID)"
echo "  进程3 - OrderAgent:     http://localhost:10006 (PID: $AGENT_PID)"
echo ""
echo "日志文件:"
echo "  - OrderMCPServer: logs/mcp_server.log"
echo "  - OrderAgent:     logs/order_agent.log"
echo ""
echo "现在可以在另一个终端运行:"
echo "  python3 chat.py"
echo ""
