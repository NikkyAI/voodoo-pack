mkfile_path := $(abspath $(lastword $(MAKEFILE_LIST)))
current_dir := $(patsubst %/,%,$(dir $(mkfile_path)))
path:
	echo ${current_dir}
venv: virtualenv/bin/activate
virtualenv/bin/activate: ${current_dir}/requirements.txt
	test -d ${current_dir}/virtualenv || virtualenv ${current_dir}/virtualenv
	${current_dir}/virtualenv/bin/pip install -r ${current_dir}/requirements.txt
	touch ${current_dir}/virtualenv/bin/activate

install:
	pip uninstall voodoo -y; true
	pip install --user ${current_dir}

uninstall:
	pip uninstall voodoo -y

run: venv
	( \
	    source ${current_dir}/virtualenv/bin/activate; \
	    PYTHONPATH=PYTHONPATH:${current_dir} python -m voodoo -c config/config.yaml; \
	)

run-debug: venv
	( \
	    source ${current_dir}/virtualenv/bin/activate; \
	    PYTHONPATH=PYTHONPATH:${current_dir} python -m voodoo -c config/config.yaml --debug; \
	)

gui: venv
	( \
	    source ${current_dir}/virtualenv/bin/activate; \
	    PYTHONPATH=PYTHONPATH:${current_dir} python -m voodoo-gui ; \
	)

.PHONY: setup install run run-debug