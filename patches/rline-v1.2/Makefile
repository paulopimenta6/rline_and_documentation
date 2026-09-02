ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)
UPSTREAM_DIR := $(ROOT)/RLINE_v1_2.Source/v1_2
PATCH_DIR := $(ROOT)/patches/rline-v1.2

FC = gfortran
MODE ?= release
BUILD_ROOT ?= $(ROOT)/build/rline-patched
BUILD_ROOT := $(abspath $(BUILD_ROOT))
SOURCE_DIR := $(BUILD_ROOT)/src
OBJECT_DIR := $(BUILD_ROOT)/obj
MODULE_DIR := $(BUILD_ROOT)/mod
PATCH_STAMP := $(SOURCE_DIR)/.patched
BUILD_INFO := $(BUILD_ROOT)/BUILD-INFO.txt

COMMON_FLAGS := -std=legacy -ffree-line-length-none -Wall -Wextra \
	-Wimplicit-interface
RELEASE_FLAGS := -O2 $(COMMON_FLAGS)
DEBUG_FLAGS := -O0 -g3 $(COMMON_FLAGS) -fcheck=all \
	-fbacktrace -finit-real=snan -finit-integer=-2147483647 \
	-ffpe-trap=invalid,zero,overflow

ifeq ($(MODE),release)
FFLAGS := $(RELEASE_FLAGS)
EXE := $(BUILD_ROOT)/RLINEv1_2_patched.x
else ifeq ($(MODE),debug)
FFLAGS := $(DEBUG_FLAGS)
EXE := $(BUILD_ROOT)/RLINEv1_2_patched_debug.x
else
$(error MODE must be release or debug, got '$(MODE)')
endif

UPSTREAM_SOURCES := $(sort $(wildcard $(UPSTREAM_DIR)/*.f90))
PATCH_NAMES := \
	0001-initialize-effective-wind.patch \
	0002-robust-numerical-geometry.patch \
	0003-explicit-depressed-source-index.patch \
	0004-validate-meteorology-and-critical-resources.patch \
	0005-validate-control-input.patch \
	0006-validate-source-and-receptor-input.patch \
	0007-check-output-io-and-daily-allocation.patch \
	0008-support-long-file-paths.patch
PATCHES := $(addprefix $(PATCH_DIR)/,$(PATCH_NAMES))
SOURCE_NAMES := \
	Data_Structures.f90 \
	RLINE_Validation.f90 \
	Line_Source_Data.f90 \
	RLINE_Main.f90 \
	Read_Line_Source_Inputs.f90 \
	Read_Met_Inputs.f90 \
	Read_Receptors.f90 \
	Read_Sources.f90 \
	Compute_File_Size.f90 \
	Create_Exp_Table.f90 \
	Expx.f90 \
	Fill_Met.f90 \
	Compute_Met.f90 \
	Translate_Rotate.f90 \
	Numerical_Line_Source.f90 \
	Point_Conc.f90 \
	Meander.f90 \
	Polyinterp.f90 \
	Sigmay.f90 \
	Sigmaz.f90 \
	MOST_Wind.f90 \
	Effective_Wind.f90 \
	Analytical_Line_Source.f90 \
	Analytical_Line_Parallel.f90 \
	Barrier_Displacement.f90 \
	Depressed_Displacement.f90 \
	Write_Hourly_All.f90 \
	Write_Hourly_by_Month.f90 \
	Write_Daily_Ave.f90 \
	Deallocate_arrays.f90
STAGED_SOURCES := $(addprefix $(SOURCE_DIR)/,$(SOURCE_NAMES))
OBJECTS := $(addprefix $(OBJECT_DIR)/,$(SOURCE_NAMES:.f90=.o))

DATA_OBJECT := $(OBJECT_DIR)/Data_Structures.o
VALIDATION_OBJECT := $(OBJECT_DIR)/RLINE_Validation.o
LINE_DATA_OBJECT := $(OBJECT_DIR)/Line_Source_Data.o
OTHER_OBJECTS := $(filter-out $(DATA_OBJECT) $(VALIDATION_OBJECT) \
	$(LINE_DATA_OBJECT),$(OBJECTS))

.PHONY: all prepare clean

all: $(EXE) $(BUILD_INFO)

prepare: $(PATCH_STAMP)

$(PATCH_STAMP): $(UPSTREAM_SOURCES) $(PATCHES) $(PATCH_DIR)/Makefile \
		$(PATCH_DIR)/UPSTREAM_SHA256.txt
	rm -rf "$(BUILD_ROOT)"
	mkdir -p "$(SOURCE_DIR)" "$(OBJECT_DIR)" "$(MODULE_DIR)"
	cp $(UPSTREAM_SOURCES) "$(SOURCE_DIR)/"
	@set -eu; for source_file in "$(SOURCE_DIR)"/*.f90; do \
		sed -i 's/\r$$//' "$${source_file}"; \
	done
	@set -eu; for patch_file in $(PATCHES); do \
		printf 'Applying %s\n' "$${patch_file}"; \
		patch --batch --fuzz=0 --no-backup-if-mismatch \
			--directory="$(SOURCE_DIR)" -p1 < "$${patch_file}"; \
	done
	touch "$@"

$(STAGED_SOURCES): $(PATCH_STAMP)
	@test -f "$@"

$(OBJECT_DIR)/%.o: $(SOURCE_DIR)/%.f90 $(PATCH_STAMP)
	$(FC) $(FFLAGS) -J"$(MODULE_DIR)" -I"$(MODULE_DIR)" -c "$<" -o "$@"

$(VALIDATION_OBJECT): $(DATA_OBJECT)
$(LINE_DATA_OBJECT): $(DATA_OBJECT)
$(OTHER_OBJECTS): $(VALIDATION_OBJECT) $(LINE_DATA_OBJECT)

$(EXE): $(OBJECTS)
	$(FC) $(FFLAGS) -J"$(MODULE_DIR)" -I"$(MODULE_DIR)" -o "$@" $(OBJECTS)

$(BUILD_INFO): $(EXE) $(PATCHES)
	@{ \
		printf 'variant=%s\n' "$(MODE)"; \
		printf 'flags=%s\n' "$(FFLAGS)"; \
		printf 'compiler='; "$(FC)" --version; \
		printf '\nchecksums:\n'; \
		sha256sum "$(EXE)" $(PATCHES); \
	} > "$@"

clean:
	rm -rf "$(BUILD_ROOT)"
