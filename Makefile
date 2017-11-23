setup:
	pip install --user virtualenv
	virtualenv virtualenv
	( \
	    source virtualenv/bin/activate; \
	    pip install -r requirements.txt; \
	)

install:
	pip install --user subzero
	pip uninstall voodoo -y; true
	pip install --user --force .

uninstall:
	pip uninstall voodoo -y

run:
	( \
	    source virtualenv/bin/activate; \
	    python -m voodoo -c config/config.yaml; \
	)

run-debug:
	( \
	    source virtualenv/bin/activate; \
	    python -m voodoo -c config/config.yaml --debug; \
	)

.PHONY: setup install run run-debug