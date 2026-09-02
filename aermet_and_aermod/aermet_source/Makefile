# ---------------------------------------------------------------------------
# Makefile para compilacao do AERMET v26135 (gfortran, livre-forma)
# Com dependencias de modulos expressas para permitir `make -j$(nproc)`.
# Ordem de compilacao garantida pela cadeia de .o (os .mod sao gerados como
# efeito colateral da compilacao do arquivo que define cada modulo).
#   Binario gerado: aermet
#   Limpeza:        make clean
# ---------------------------------------------------------------------------
FC      = gfortran
FFLAGS  = -O2 -ffree-form
LDFLAGS = -O2

EXE = aermet

SRCS = mod_file_units.f90 mod_main1.f90 mod_upperair.f90 mod_surface.f90 \
       mod_onsite.f90 mod_pbl.f90 mod_read_input.f90 mod_reports.f90 \
       mod_misc.f90 aermet.f90
OBJS = $(SRCS:.f90=.o)

all: $(EXE)

%.o: %.f90
	$(FC) $(FFLAGS) -c $<

# --- Dependencias de modulos (cadeia topologica via .o) --------------------
mod_main1.o:      mod_file_units.o

mod_upperair.o:   mod_main1.o mod_file_units.o
mod_surface.o:    mod_main1.o mod_file_units.o
mod_onsite.o:     mod_main1.o mod_file_units.o

mod_pbl.o:        mod_main1.o mod_file_units.o mod_upperair.o mod_onsite.o mod_surface.o

mod_read_input.o: mod_main1.o mod_file_units.o mod_upperair.o mod_surface.o \
                  mod_onsite.o mod_pbl.o

mod_misc.o:       mod_file_units.o mod_upperair.o mod_surface.o mod_onsite.o \
                  mod_pbl.o

mod_reports.o:    mod_file_units.o mod_main1.o mod_upperair.o mod_surface.o \
                  mod_onsite.o mod_pbl.o mod_read_input.o

aermet.o:         mod_file_units.o mod_main1.o mod_upperair.o mod_surface.o \
                  mod_onsite.o mod_pbl.o mod_read_input.o mod_reports.o \
                  mod_misc.o

$(EXE): $(OBJS)
	$(FC) $(LDFLAGS) -o $@ $(OBJS)

clean:
	rm -f *.o *.mod $(EXE)
