FILES := pipegen setup.py

lint:
	pylint ${FILES}
	black --check ${FILES}
	isort ${FILES} --check-only

test:
	# pytest --cov pipegen
	mypy pipegen

fix:
	black ${FILES}
	isort ${FILES}
	$(MAKE) lint
