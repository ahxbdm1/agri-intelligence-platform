.PHONY: install-backend install-frontend init-data train-models backend frontend dev docker-up docker-down batch test

install-backend:
	cd backend && python -m pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

init-data:
	python scripts/generate_demo_data.py

train-models:
	python scripts/train_models.py
	python backend/ml/train/train_disease_model.py

backend:
	uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload

frontend:
	cd frontend && npm run dev

dev:
	@echo "Run backend and frontend in two terminals: make backend / make frontend"

docker-up:
	docker compose up --build

docker-down:
	docker compose down

batch:
	python batch_jobs/pandas_jobs/risk_aggregation_job.py

test:
	PYTHONPATH=backend pytest -q backend/tests
