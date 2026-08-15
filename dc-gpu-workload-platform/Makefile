.PHONY: setup lint test

setup:
	python -m venv .venv
	. .venv/bin/activate && pip install -r requirements/dev.txt

lint:
	ruff check .
	black --check .

test:
	pytest tests/
