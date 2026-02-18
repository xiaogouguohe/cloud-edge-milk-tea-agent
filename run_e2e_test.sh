#!/bin/bash
# 全链路 E2E 测试：先启动所有服务，再运行测试，退出时清理
# 用法:
#   ./run_e2e_test.sh              # 运行全部
#   ./run_e2e_test.sh insufficient_stock   # 仅运行库存不足用例
#   ./run_e2e_test.sh -k "菜单"     # 仅运行名称包含「菜单」的用例

cd "$(dirname "$0")"
mkdir -p logs

# 可选：过滤测试用例（传给 unittest -k）
TEST_FILTER="$1"

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
source ./start_all.sh

echo ""
echo "运行 E2E 测试..."
echo "=========================================="
if [ -n "$TEST_FILTER" ]; then
    echo "筛选: -k $TEST_FILTER"
    echo ""
fi

if [ -f "venv/bin/python" ]; then
    PYTHON="venv/bin/python"
else
    PYTHON="python3"
fi

if [ -n "$TEST_FILTER" ]; then
    $PYTHON -m unittest tests.test_e2e_order -v -k "$TEST_FILTER"
else
    $PYTHON -m unittest tests.test_e2e_order -v
fi
