#!/bin/bash

# 停止进程3: OrderAgent

echo "=========================================="
echo "停止进程3: OrderAgent"
echo "=========================================="
echo ""

# 方法1: 通过 PID 文件停止
if [ -f logs/order_agent.pid ]; then
    AGENT_PID=$(cat logs/order_agent.pid)
    if ps -p $AGENT_PID > /dev/null 2>&1; then
        echo "通过 PID 文件停止 OrderAgent (PID: $AGENT_PID)..."
        kill $AGENT_PID
        sleep 1
        if ps -p $AGENT_PID > /dev/null 2>&1; then
            echo "强制停止..."
            kill -9 $AGENT_PID
        fi
        echo "✓ OrderAgent 已停止"
        rm -f logs/order_agent.pid
    else
        echo "OrderAgent 未运行（PID 文件存在但进程不存在）"
        rm -f logs/order_agent.pid
    fi
else
    echo "未找到 PID 文件，尝试通过端口停止..."
fi

# 方法2: 通过端口停止
if lsof -Pi :10006 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "发现端口 10006 被占用，尝试停止..."
    lsof -ti:10006 | xargs kill -9 2>/dev/null
    echo "✓ 已停止占用端口 10006 的进程"
else
    echo "端口 10006 未被占用"
fi

echo ""
echo "=========================================="
echo "进程3已停止"
echo "=========================================="
