.PHONY: all
all: lint test

.PHONY: lint
lint:
	pre-commit run --all-files

.PHONY: test tests
test tests: venv
	. venv-venv_update/bin/activate && ./test $(ARGS)

.PHONY: tox
tox:
	tox -e lint,test

.PHONY: venv
venv:
	./venv_update.py --python=python2.7 venv-venv_update requirements.d/dev.txt


.PHONY: clean
clean:
	rm -rf .tox
	find -name '*.pyc' -print0 | xargs -0 -r -P4 rm
