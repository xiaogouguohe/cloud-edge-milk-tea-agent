#!/bin/bash

# 停止所有服务脚本

echo "=========================================="
echo "停止云边奶茶铺 AI Agent 服务"
echo "=========================================="
echo ""

# 从 PID 文件读取进程 ID
if [ -f logs/mcp_server.pid ]; then
    MCP_PID=$(cat logs/mcp_server.pid)
    if ps -p $MCP_PID > /dev/null 2>&1; then
        echo "停止 OrderMCPServer (PID: $MCP_PID)..."
        kill $MCP_PID
        echo "✓ OrderMCPServer 已停止"
    else
        echo "OrderMCPServer 未运行"
    fi
    rm -f logs/mcp_server.pid
else
    echo "未找到 OrderMCPServer PID 文件"
fi

if [ -f logs/order_agent.pid ]; then
    AGENT_PID=$(cat logs/order_agent.pid)
    if ps -p $AGENT_PID > /dev/null 2>&1; then
        echo "停止 OrderAgent (PID: $AGENT_PID)..."
        kill $AGENT_PID
        echo "✓ OrderAgent 已停止"
    else
        echo "OrderAgent 未运行"
    fi
    rm -f logs/order_agent.pid
else
    echo "未找到 OrderAgent PID 文件"
fi

if [ -f logs/consult_mcp_server.pid ]; then
    CONSULT_MCP_PID=$(cat logs/consult_mcp_server.pid)
    if ps -p $CONSULT_MCP_PID > /dev/null 2>&1; then
        echo "停止 Consult MCP Server (PID: $CONSULT_MCP_PID)..."
        kill $CONSULT_MCP_PID
        echo "✓ Consult MCP Server 已停止"
    else
        echo "Consult MCP Server 未运行"
    fi
    rm -f logs/consult_mcp_server.pid
else
    echo "未找到 Consult MCP Server PID 文件"
fi

if [ -f logs/consult_agent.pid ]; then
    CONSULT_AGENT_PID=$(cat logs/consult_agent.pid)
    if ps -p $CONSULT_AGENT_PID > /dev/null 2>&1; then
        echo "停止 Consult Agent (PID: $CONSULT_AGENT_PID)..."
        kill $CONSULT_AGENT_PID
        echo "✓ Consult Agent 已停止"
    else
        echo "Consult Agent 未运行"
    fi
    rm -f logs/consult_agent.pid
else
    echo "未找到 Consult Agent PID 文件"
fi

if [ -f logs/supervisor.pid ]; then
    SUP_PID=$(cat logs/supervisor.pid)
    if ps -p $SUP_PID > /dev/null 2>&1; then
        echo "停止 Supervisor API (PID: $SUP_PID)..."
        kill $SUP_PID
        echo "✓ Supervisor API 已停止"
    else
        echo "Supervisor API 未运行"
    fi
    rm -f logs/supervisor.pid
else
    echo "未找到 Supervisor API PID 文件"
fi

# 如果 PID 文件不存在，尝试通过端口查找并停止
if lsof -Pi :10002 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "发现端口 10002 被占用，尝试停止..."
    lsof -ti:10002 | xargs kill -9 2>/dev/null
fi

if lsof -Pi :10006 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "发现端口 10006 被占用，尝试停止..."
    lsof -ti:10006 | xargs kill -9 2>/dev/null
fi

if lsof -Pi :10003 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "发现端口 10003 被占用，尝试停止..."
    lsof -ti:10003 | xargs kill -9 2>/dev/null
fi

if lsof -Pi :10005 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "发现端口 10005 被占用，尝试停止..."
    lsof -ti:10005 | xargs kill -9 2>/dev/null
fi

if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "发现端口 8000 被占用，尝试停止..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null
fi

echo ""
echo "=========================================="
echo "所有服务已停止"
echo "=========================================="
