setup:
	pip install --user virtualenv
	virtualenv virtualenv
	( \
	    source virtualenv/bin/activate; \
	    pip install -r requirements.txt; \
	)

install:
	pip install --user --force .

run:
	( \
	    source virtualenv/bin/activate; \
	    python -m voodoo config/config.yaml; \
	)

run-debug:
	( \
	    source virtualenv/bin/activate; \
	    python -m voodoo config/config.yaml --debug; \
	)

.PHONY: setup install run run-debug