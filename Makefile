venv: virtualenv/bin/activate
virtualenv/bin/activate: requirements.txt
	test -d virtualenv || virtualenv virtualenv
	virtualenv/bin/pip install -r requirements.txt
	touch virtualenv/bin/activate

install:
	pip uninstall voodoo -y; true
	pip install --user .

uninstall:
	pip uninstall voodoo -y

run: venv
	( \
	    source virtualenv/bin/activate; \
	    python -m voodoo -c config/config.yaml; \
	)

run-debug: venv
	( \
	    source virtualenv/bin/activate; \
	    python -m voodoo -c config/config.yaml --debug; \
	)

.PHONY: setup install run run-debug