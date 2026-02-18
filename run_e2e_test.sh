#!/bin/bash
# 全链路 E2E 测试：先启动所有服务，再运行测试，退出时清理
# 用法: ./run_e2e_test.sh

cd "$(dirname "$0")"
mkdir -p logs

# 退出时清理进程（仅清理本脚本启动的进程）
cleanup() {
    echo ""
    echo "清理服务进程..."
    [[ -n $MCP_PID ]]    && kill $MCP_PID 2>/dev/null
    [[ -n $AGENT_PID ]] && kill $AGENT_PID 2>/dev/null
    [[ -n $SUP_PID ]]   && kill $SUP_PID 2>/dev/null
}
trap cleanup EXIT

echo "=========================================="
echo "全链路 E2E 测试"
echo "=========================================="
echo ""

# 1. 启动所有服务（source 以获取 MCP_PID/AGENT_PID/SUP_PID 用于清理）
source ./start_all_services.sh

echo ""
echo "运行 E2E 测试..."
echo "=========================================="
if [ -f "venv/bin/python" ]; then
    venv/bin/python -m unittest tests.test_e2e_order -v
else
    python3 -m unittest tests.test_e2e_order -v
fi
