#!/bin/bash

# 停止进程2: OrderMCPServer

echo "=========================================="
echo "停止进程2: OrderMCPServer"
echo "=========================================="
echo ""

# 方法1: 通过 PID 文件停止
if [ -f logs/mcp_server.pid ]; then
    MCP_PID=$(cat logs/mcp_server.pid)
    if ps -p $MCP_PID > /dev/null 2>&1; then
        echo "通过 PID 文件停止 OrderMCPServer (PID: $MCP_PID)..."
        kill $MCP_PID
        sleep 1
        if ps -p $MCP_PID > /dev/null 2>&1; then
            echo "强制停止..."
            kill -9 $MCP_PID
        fi
        echo "✓ OrderMCPServer 已停止"
        rm -f logs/mcp_server.pid
    else
        echo "OrderMCPServer 未运行（PID 文件存在但进程不存在）"
        rm -f logs/mcp_server.pid
    fi
else
    echo "未找到 PID 文件，尝试通过端口停止..."
fi

# 方法2: 通过端口停止
if lsof -Pi :10002 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "发现端口 10002 被占用，尝试停止..."
    lsof -ti:10002 | xargs kill -9 2>/dev/null
    echo "✓ 已停止占用端口 10002 的进程"
else
    echo "端口 10002 未被占用"
fi

echo ""
echo "=========================================="
echo "进程2已停止"
echo "=========================================="
