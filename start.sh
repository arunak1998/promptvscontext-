#!/usr/bin/env bash
# Starts the demo. Open http://localhost:5173. Ctrl+C stops it.
# Frontend only: all data and AI answers are pre-saved in frontend/public/data. No backend, no AI model.
set -e
cd "$(dirname "$0")/frontend"
[ -d node_modules ] || npm install --no-audit --no-fund
npm run dev
