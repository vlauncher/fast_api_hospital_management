.PHONY: install venv run test migrate db-up db-down clean

install:
	python3 -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt

venv:
	python3 -m venv venv

run:
	./venv/bin/uvicorn app.main:app --reload

test:
	./venv/bin/pytest

migrate:
	./venv/bin/alembic revision --autogenerate -m "Auto-generated migration"
	./venv/bin/alembic upgrade head

db-up:
	./venv/bin/alembic upgrade head

db-down:
	./venv/bin/alembic downgrade base

clean:
	rm -rf venv
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
