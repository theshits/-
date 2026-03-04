#!/bin/bash
echo "========================================"
echo "  空气污染扩散模拟平台启动脚本"
echo "========================================"
echo

echo "[1/2] 启动后端服务..."
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

sleep 3

echo "[2/2] 启动前端服务..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo
echo "========================================"
echo "  服务启动完成！"
echo "  后端地址: http://localhost:8000"
echo "  前端地址: http://localhost:3000"
echo "  API文档: http://localhost:8000/docs"
echo "========================================"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
