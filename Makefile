PYTHON_VERSION=$(shell python3 -c "import platform; print('.'.join(platform.python_version_tuple()[:-1]))")
VENV_DIR=.venv_$(PYTHON_VERSION)

ifeq ($(PYTHON_VERSION),)
	$(error No Python 3 interpreter found!)
endif

ifeq ($(OS),Windows_NT)
	VENV_BIN_DIR=scripts
else
	VENV_BIN_DIR=bin
endif

# Generate virtualenv
$(VENV_DIR)/install.indicator: pyproject.toml requirements/development.txt
	$(VENV_DIR)/$(VENV_BIN_DIR)/python3 -m piptools sync requirements/development.txt
	$(VENV_DIR)/$(VENV_BIN_DIR)/python3 -m pip install -r requirements/development.txt
	$(VENV_DIR)/$(VENV_BIN_DIR)/python3 -m pip install -e .
	touch $@

$(VENV_DIR):
	python3 -m venv $@
	$(VENV_DIR)/$(VENV_BIN_DIR)/python3 -m pip install -r requirements/development.txt
	ln -sf $(VENV_DIR) .venv

.PHONY: venv
venv: $(VENV_DIR) $(VENV_DIR)/install.indicator

pyproject.toml: $(VENV_DIR)

# Generate requirements
requirements/%.txt: pyproject.toml
	mkdir requirements; touch $@
	$(VENV_DIR)/$(VENV_BIN_DIR)/python3 -m piptools compile --extra $(basename $(notdir $@)) --output-file $@ $<

.PHONY: requirements
requirements: $(VENV_DIR) requirements/development.txt

.coverage: venv
	$(VENV_DIR)/$(VENV_BIN_DIR)/py.test --cov=pyfatfs tests

.PHONY: tests
tests: venv .coverage

.PHONY: flake8
flake8: venv
	$(VENV_DIR)/$(VENV_BIN_DIR)/flake8 pyfatfs tests --count --show-source --statistics

.PHONY: docs
docs: venv
	. $(VENV_DIR)/$(VENV_BIN_DIR)/activate; $(MAKE) -C docs html
	xdg-open docs/_build/html/index.html

.PHONY: build
build: venv
	$(VENV_DIR)/$(VENV_BIN_DIR)/python3 -m build .

.PHONY: twine_upload
twine_upload: clean build
	python3 -m venv $(VENV_DIR)/twine_venv
	$(VENV_DIR)/twine_venv/$(VENV_BIN_DIR)/python3 -m pip install twine==5.0.0
	$(VENV_DIR)/twine_venv/$(VENV_BIN_DIR)/twine upload dist/*

.PHONY: coveralls_parallel
coveralls_parallel: venv
	$(VENV_DIR)/$(VENV_BIN_DIR)/coveralls --service=github

.PHONY: coveralls_finish
coveralls_finish: venv
	$(VENV_DIR)/$(VENV_BIN_DIR)/coveralls --service=github --finish

.PHONY: clean
.NOTPARALLEL: clean
clean:
	rm -rf $(VENV_DIR) docs/_build/ build/ dist/ pyfatfs.egg-info/
