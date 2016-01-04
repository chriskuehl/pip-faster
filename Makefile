.PHONY: all
all: lint test

.PHONY: lint
lint: venv
	./venv/bin/pre-commit run --all-files

.PHONY: test tests
test tests: venv
	. venv/bin/activate && ./test $(ARGS)

.PHONY: tox
tox:
	tox -e lint,test

venv: setup.py requirements.txt requirements.d/* Makefile
	./venv_update.py --python=python2.7
	venv/bin/pre-commit install

.PHONY: clean
clean:
	rm -rf .tox
	find -name '*.pyc' -print0 | xargs -0 -r -P4 rm
