#!/bin/bash
# 全链路 E2E 测试：一键启动服务 + 运行测试 + 清理
# 用法: ./run_e2e_test.sh

cd "$(dirname "$0")"
mkdir -p logs

# 优先使用 venv 中的 Python（若存在）
if [ -f "venv/bin/python" ]; then
    PYTHON="venv/bin/python"
else
    PYTHON="python3"
fi

# 退出时清理进程
cleanup() {
    echo ""
    echo "清理服务进程..."
    [[ -n $MCP_PID ]]    && kill $MCP_PID 2>/dev/null
    [[ -n $AGENT_PID ]] && kill $AGENT_PID 2>/dev/null
    [[ -n $SUP_PID ]]   && kill $SUP_PID 2>/dev/null
}
trap cleanup EXIT

# 若服务已运行则跳过启动
wait_ready() {
    local url=$1 name=$2
    for i in {1..20}; do
        curl -s "$url" >/dev/null 2>&1 && return 0
        sleep 1
    done
    echo "✗ $name 启动超时"
    return 1
}

echo "=========================================="
echo "全链路 E2E 测试"
echo "=========================================="
echo ""

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

echo ""
echo "运行 E2E 测试..."
echo "=========================================="
$PYTHON -m unittest tests.test_e2e_order -v
