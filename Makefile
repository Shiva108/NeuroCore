setup:
	python scripts/bootstrap.py

test:
	pytest

lint:
	black --check src tests
	flake8 src tests

validate:
	python -m neurocore.governance.validation

sentrux:
	sentrux check .
	sentrux gate .
