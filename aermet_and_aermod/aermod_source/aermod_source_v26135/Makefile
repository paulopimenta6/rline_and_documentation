# ---------------------------------------------------------------------------
# Makefile para compilacao do AERMOD v26135 (gfortran, formato fixo)
#
# ATENCAO CRITICA: NAO usar `-ffixed-line-length-132` (quebra rline.f).
# Usar comprimento de linha fixa padrao de 72 colunas.
#
# Todos os modulos (MAIN1, RLINE_DATA, BUOYANT_LINE, PRIME_*, GRSMMOD) estao
# definidos em modules.f. Portanto modules.o precisa ser compilado primeiro;
# os demais objetos dependem apenas de modules.o e compilam em paralelo.
#   Binario gerado: aermod
#   Limpeza:        make clean
# ---------------------------------------------------------------------------
FC      = gfortran
FFLAGS  = -O2
LDFLAGS = -O2

EXE = aermod

SRCS = modules.f grsm.f aermod.f setup.f coset.f soset.f reset.f meset.f \
       ouset.f inpsum.f metext.f iblval.f siggrid.f tempgrid.f windgrid.f \
       calc1.f calc2.f prise.f arise.f prime.f sigmas.f pitarea.f uninam.f \
       output.f evset.f evcalc.f evoutput.f rline.f bline.f
OBJS = $(SRCS:.f=.o)

# modules.f gera todos os .mod; os demais dependem dele
MODULES_OBJ = modules.o
OTHER_OBJS  = $(filter-out $(MODULES_OBJ),$(OBJS))
$(OTHER_OBJS): $(MODULES_OBJ)

.DEFAULT_GOAL := all

all: $(EXE)

%.o: %.f
	$(FC) $(FFLAGS) -c $<

$(EXE): $(OBJS)
	$(FC) $(LDFLAGS) -o $@ $(OBJS)

clean:
	rm -f *.o *.mod $(EXE)
