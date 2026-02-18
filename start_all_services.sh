#!/bin/bash
# 启动所有服务：Order MCP Server、Order Agent、Supervisor API
# 用法:
#   source ./start_all_services.sh   # 被 E2E 或其它脚本调用，变量 MCP_PID/AGENT_PID/SUP_PID 在父 shell
#   ./start_all_services.sh         # 独立运行，PID 写入 logs/*.pid，可用 stop_all.sh 停止

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
mkdir -p logs

# 优先使用 venv 中的 Python（若存在）
if [ -f "venv/bin/python" ]; then
    PYTHON="venv/bin/python"
else
    PYTHON="python3"
fi

# 等待服务就绪
wait_ready() {
    local url=$1 name=$2
    for i in {1..20}; do
        curl -s "$url" >/dev/null 2>&1 && return 0
        sleep 1
    done
    echo "✗ $name 启动超时"
    return 1
}

# 若被其它脚本 source，不打印大标题（由调用方决定）
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "=========================================="
    echo "启动云边奶茶铺所有服务"
    echo "=========================================="
    echo ""
fi

# 强制重启：先停止占用端口的旧进程，确保加载最新代码
echo "检查并清理旧服务进程..."
for port in 10002 10006 8000; do
    if lsof -ti:$port >/dev/null 2>&1; then
        echo "  停止端口 $port 上的进程..."
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
        sleep 2
    fi
done

# 初始化 PID 变量（供 source 时使用）
MCP_PID=""
AGENT_PID=""
SUP_PID=""

# 1. 启动 Order MCP Server
if ! curl -s http://localhost:10002/mcp/health >/dev/null 2>&1; then
    echo "启动 Order MCP Server (10002)..."
    $PYTHON order_mcp_server/run_order_mcp_server.py >> logs/e2e_mcp.log 2>&1 &
    MCP_PID=$!
    wait_ready "http://localhost:10002/mcp/health" "Order MCP Server" || exit 1
    echo "  ✓ Order MCP Server 就绪"
else
    echo "  ✓ Order MCP Server 已运行"
fi

# 2. 启动 Order Agent
if ! curl -s http://localhost:10006/a2a/health >/dev/null 2>&1; then
    echo "启动 Order Agent (10006)..."
    $PYTHON order_agent/run_order_agent.py >> logs/e2e_agent.log 2>&1 &
    AGENT_PID=$!
    wait_ready "http://localhost:10006/a2a/health" "Order Agent" || exit 1
    echo "  ✓ Order Agent 就绪"
else
    echo "  ✓ Order Agent 已运行"
fi

# 3. 启动 Supervisor API
if ! curl -s http://localhost:8000/api/health >/dev/null 2>&1; then
    echo "启动 Supervisor API (8000)..."
    $PYTHON -m supervisor_agent.api >> logs/e2e_supervisor.log 2>&1 &
    SUP_PID=$!
    wait_ready "http://localhost:8000/api/health" "Supervisor API" || exit 1
    echo "  ✓ Supervisor API 就绪"
else
    echo "  ✓ Supervisor API 已运行"
fi

# 独立运行时，写入 PID 文件供 stop_all.sh 使用
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    [[ -n "$MCP_PID" ]] && echo "$MCP_PID" > logs/mcp_server.pid
    [[ -n "$AGENT_PID" ]] && echo "$AGENT_PID" > logs/order_agent.pid
    [[ -n "$SUP_PID" ]] && echo "$SUP_PID" > logs/supervisor.pid
    echo ""
    echo "=========================================="
    echo "所有服务已启动"
    echo "=========================================="
    echo "  Order MCP Server:  http://localhost:10002"
    echo "  Order Agent:       http://localhost:10006"
    echo "  Supervisor API:    http://localhost:8000"
    echo ""
    echo "停止服务: ./stop_all.sh"
fi
