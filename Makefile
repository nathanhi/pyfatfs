PYTHON_VERSION=$(shell python3 -c "import platform; print(platform.python_version())")
VENV_DIR=.venv_$(PYTHON_VERSION)

ifeq ($(PYTHON_VERSION),)
	$(error No Python 3 interpreter found!)
endif

# Generate virtualenv
$(VENV_DIR)/install.indicator: requirements
	$(VENV_DIR)/bin/pip install -r requirements/development.txt
	$(VENV_DIR)/bin/pip install -e .
	touch $@

$(VENV_DIR):
	virtualenv -p python3 $@

.PHONY: make_venv
make_venv: $(VENV_DIR) $(VENV_DIR)/install.indicator

# Generate requirements
requirements/%.txt: requirements/in/%.in
	$(VENV_DIR)/bin/pip-compile --header --annotate --upgrade --output-file $@ $<

.PHONY: update_requirements
update_requirements: make_venv requirements/install.txt requirements/tasks.txt requirements/test.txt
