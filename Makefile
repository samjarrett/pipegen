FILES := pipegen tests setup.py

lint:
	pylint ${FILES}
	black --check ${FILES}
	isort ${FILES} --check-only

test:
	python -m pytest --cov pipegen --cov-report term --cov-report html
	mypy pipegen tests

fix:
	black ${FILES}
	isort ${FILES}
	$(MAKE) lint
