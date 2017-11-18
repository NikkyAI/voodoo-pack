install-required:
	pip install --user -r requirements.txt

install:
	pip install --user --force .

run:
	python -m voodoo

run-debug:
	python -m voodoo --debug

.PHONY: install-required install run run-debug