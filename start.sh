#!/bin/bash
echo "🚆 RailIQ v3 — Starting..."

# Backend
echo "► Starting backend on :8000"
cd "$(dirname "$0")"
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Frontend dev server
echo "► Starting frontend on :5173"
cd frontend && npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ RailIQ is running:"
echo "   Frontend: http://localhost:5173"
echo "   Backend:  http://localhost:8000"
echo "   API docs: http://localhost:8000/docs"
echo "   WS Live:  ws://localhost:8000/ws/live"
echo ""
echo "Press Ctrl+C to stop."
wait
