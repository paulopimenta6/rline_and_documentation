SHELL := /bin/bash

.PHONY: all release debug aermet aermod rline-original models \
	build-aermet build-aermod build-rline-original \
	rline-release rline-debug rline-prepare-release rline-prepare-debug \
	rline-provenance-check aermet-provenance-check aermod-provenance-check \
	model-provenance-check clean clean-aermet clean-aermod \
	clean-rline-original rline-clean test test-rline quality \
	scientific-regression quality-report example-data

PYTHON ?= python3
BUILD_DIR := build

AERMET_SOURCE_DIR := aermet_and_aermod/aermet_source
AERMET_BUILD_DIR := $(BUILD_DIR)/aermet
AERMET_EXE := $(AERMET_BUILD_DIR)/aermet
AERMET_MANIFEST := provenance/AERMET_v26135_SNAPSHOT_SHA256.txt
AERMET_SOURCES := $(shell awk 'NF == 2 {print $$2}' $(AERMET_MANIFEST))

AERMOD_SOURCE_DIR := aermet_and_aermod/aermod_source/aermod_source_v26135
AERMOD_BUILD_DIR := $(BUILD_DIR)/aermod
AERMOD_EXE := $(AERMOD_BUILD_DIR)/aermod
AERMOD_MANIFEST := provenance/AERMOD_v26135_SNAPSHOT_SHA256.txt
AERMOD_SOURCES := $(shell awk 'NF == 2 {print $$2}' $(AERMOD_MANIFEST))

RLINE_ORIGINAL_SOURCE_DIR := RLINE_v1_2.Source/v1_2
RLINE_ORIGINAL_BUILD_DIR := $(BUILD_DIR)/rline-original
RLINE_ORIGINAL_EXE := $(RLINE_ORIGINAL_BUILD_DIR)/RLINEv1_2_gfortran.x
RLINE_ORIGINAL_SOURCES := $(wildcard $(RLINE_ORIGINAL_SOURCE_DIR)/*.f90)

RLINE_BUILD_MAKEFILE := patches/rline-v1.2/Makefile
RLINE_MANIFEST := patches/rline-v1.2/UPSTREAM_SHA256.txt

all: models

release: rline-release

debug: rline-debug

models: aermet aermod rline-original rline-release

aermet: aermet-provenance-check $(AERMET_EXE)

build-aermet: aermet

$(AERMET_EXE): $(AERMET_SOURCES) $(AERMET_SOURCE_DIR)/Makefile
	rm -rf "$(AERMET_BUILD_DIR)"
	mkdir -p "$(AERMET_BUILD_DIR)"
	cp $(AERMET_SOURCES) "$(AERMET_SOURCE_DIR)/Makefile" "$(AERMET_BUILD_DIR)/"
	$(MAKE) --no-print-directory -C "$(AERMET_BUILD_DIR)" all
	test -x "$@"

aermod: aermod-provenance-check $(AERMOD_EXE)

build-aermod: aermod

$(AERMOD_EXE): $(AERMOD_SOURCES) $(AERMOD_SOURCE_DIR)/Makefile
	rm -rf "$(AERMOD_BUILD_DIR)"
	mkdir -p "$(AERMOD_BUILD_DIR)"
	cp $(AERMOD_SOURCES) "$(AERMOD_SOURCE_DIR)/Makefile" "$(AERMOD_BUILD_DIR)/"
	$(MAKE) --no-print-directory -C "$(AERMOD_BUILD_DIR)" all
	test -x "$@"

rline-original: $(RLINE_ORIGINAL_EXE)

build-rline-original: rline-original

$(RLINE_ORIGINAL_EXE): $(RLINE_ORIGINAL_SOURCES) \
		$(RLINE_ORIGINAL_SOURCE_DIR)/Makefile.gfortran
	rm -rf "$(RLINE_ORIGINAL_BUILD_DIR)"
	mkdir -p "$(RLINE_ORIGINAL_BUILD_DIR)"
	cp $(RLINE_ORIGINAL_SOURCES) \
		"$(RLINE_ORIGINAL_SOURCE_DIR)/Makefile.gfortran" \
		"$(RLINE_ORIGINAL_BUILD_DIR)/"
	$(MAKE) --no-print-directory -C "$(RLINE_ORIGINAL_BUILD_DIR)" \
		-f Makefile.gfortran all
	test -x "$@"

rline-provenance-check:
	sha256sum --check --strict "$(RLINE_MANIFEST)"

aermet-provenance-check:
	sha256sum --check --strict "$(AERMET_MANIFEST)"

aermod-provenance-check:
	sha256sum --check --strict "$(AERMOD_MANIFEST)"

model-provenance-check: aermet-provenance-check aermod-provenance-check \
	rline-provenance-check

rline-release: rline-provenance-check
	$(MAKE) --no-print-directory -f "$(RLINE_BUILD_MAKEFILE)" \
		MODE=release BUILD_ROOT=$(BUILD_DIR)/rline-patched all

rline-debug: rline-provenance-check
	$(MAKE) --no-print-directory -f "$(RLINE_BUILD_MAKEFILE)" \
		MODE=debug BUILD_ROOT=$(BUILD_DIR)/rline-patched-debug all

rline-prepare-release: rline-provenance-check
	$(MAKE) --no-print-directory -f "$(RLINE_BUILD_MAKEFILE)" \
		MODE=release BUILD_ROOT=$(BUILD_DIR)/rline-patched prepare

rline-prepare-debug: rline-provenance-check
	$(MAKE) --no-print-directory -f "$(RLINE_BUILD_MAKEFILE)" \
		MODE=debug BUILD_ROOT=$(BUILD_DIR)/rline-patched-debug prepare

clean-aermet:
	rm -rf "$(AERMET_BUILD_DIR)"

clean-aermod:
	rm -rf "$(AERMOD_BUILD_DIR)"

clean-rline-original:
	rm -rf "$(RLINE_ORIGINAL_BUILD_DIR)"

rline-clean:
	rm -rf $(BUILD_DIR)/rline-patched $(BUILD_DIR)/rline-patched-debug

clean:
	rm -rf "$(BUILD_DIR)"

test:
	$(PYTHON) -m pytest -m "not scientific"

test-rline:
	$(PYTHON) -m pytest -q tests/test_rline_build.py

quality:
	$(PYTHON) -m ruff check .
	git ls-files -z --cached --others --exclude-standard -- '*.sh' | \
		xargs -0 -r -n 1 bash -n

scientific-regression: models
	$(PYTHON) scripts/scientific_regression.py

quality-report:
	$(PYTHON) scripts/gerar_resumo_qualidade.py

example-data:
	$(PYTHON) scripts/gerar_dados_exemplo.py
