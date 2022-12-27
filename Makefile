PYTHON_VERSION=$(shell python3 -c "import platform; print('.'.join(platform.python_version_tuple()[:-1]))")
VENV_DIR=.venv_$(PYTHON_VERSION)
PIP_VERSION=21.3

ifeq ($(PYTHON_VERSION),)
	$(error No Python 3 interpreter found!)
endif

# Generate virtualenv
$(VENV_DIR)/install.indicator: pyproject.toml requirements/develop.txt
	$(VENV_DIR)/bin/pip install -r requirements/develop.txt
	$(VENV_DIR)/bin/python -m piptools sync requirements/develop.txt
	$(VENV_DIR)/bin/pip install -e .
	touch $@

$(VENV_DIR):
	python3 -m venv $@
	$(VENV_DIR)/bin/pip install -U pip~=$(PIP_VERSION)
	ln -sf $(VENV_DIR) .venv

.PHONY: venv
venv: $(VENV_DIR) $(VENV_DIR)/install.indicator

pyproject.toml: $(VENV_DIR)

# Generate requirements
requirements/%.txt: pyproject.toml
	mkdir requirements; touch $@
	$(VENV_DIR)/bin/python -m piptools compile --extra $(basename $(notdir $@)) --output-file $@ $<

.PHONY: requirements
requirements: $(VENV_DIR) requirements/develop.txt

.coverage: venv
	$(VENV_DIR)/bin/py.test --cov=pyfatfs tests

.PHONY: tests
tests: venv .coverage

.PHONY: flake8
flake8: venv
	$(VENV_DIR)/bin/flake8 pyfatfs tests --count --show-source --statistics

.PHONY: docs
docs: venv
	. $(VENV_DIR)/bin/activate; $(MAKE) -C docs html
	xdg-open docs/_build/html/index.html

.PHONY: clean
.NOTPARALLEL: clean
clean:
	rm -rf $(VENV_DIR) docs/_build/ build/ dist/ pyfatfs.egg-info/
