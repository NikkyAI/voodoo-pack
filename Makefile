install-required:
	pip install --user -r requirements.txt

install:
	pip install --user --force .

run:
	python -m voodoo config/config.yaml

run-debug:
	python -m voodoo config/config.yaml --debug

.PHONY: install-required install run run-debug