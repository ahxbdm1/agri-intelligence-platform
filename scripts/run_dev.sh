#!/usr/bin/env bash
set -euo pipefail

python scripts/generate_demo_data.py
python scripts/train_models.py
uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload &
cd frontend
npm install
npm run dev
