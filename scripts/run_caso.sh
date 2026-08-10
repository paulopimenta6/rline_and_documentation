#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# scripts/run_caso.sh
# Executa o pipeline de PROCESSAMENTO + POS-PROCESSAMENTO para um caso de uso.
#
# Pre-processamento (AERMET Stage 1+2) NÃO é repetido: a meteorologia gerada
# em Caso_Pipeline/dados_aermet (ONSITE.SFC/.PFL) é compartilhada por todos
# os casos.
#
# Uso:
#   bash scripts/run_caso.sh <pasta_do_caso> [transecto_x]
#   Ex.: bash scripts/run_caso.sh casos/caso2_rodovia_curta 300
# ---------------------------------------------------------------------------
set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="$(cd "$AQUI/.." && pwd)"

CASO="${1:?Uso: run_caso.sh <pasta_do_caso> [transecto_x]}"
TRANSECTO="${2:-}"

case "$CASO" in
    /*) CASO_ABS="$CASO" ;;
    *)  CASO_ABS="$RAIZ/$CASO" ;;
esac

BIN_AERMOD="$RAIZ/aermet_and_aermod/aermod_source/aermod_source_v26135/aermod"
BIN_RLINE="$RAIZ/RLINE_v1_2.Source/v1_2/RLINEv1_2_gfortran.x"
DIR_DADOS_AERMET="$RAIZ/Caso_Pipeline/dados_aermet"
DIR_RODADA_AERMOD="$CASO_ABS/rodada_aermod"
DIR_RODADA_RLINE="$CASO_ABS/rodada_rline"
INP_AERMOD="$CASO_ABS/controles_aermod/RLINE_TEST.INP"

if [ ! -f "$INP_AERMOD" ]; then
    echo "ERRO: dados do caso nao gerados. Rode: python3 scripts/gerar_caso.py $CASO_ABS/config.json" >&2
    exit 1
fi
if [ ! -f "$DIR_DADOS_AERMET/ONSITE.SFC" ] || [ ! -f "$DIR_DADOS_AERMET/ONSITE.PFL" ]; then
    echo "ERRO: meteorologia ausente. Rode antes: bash scripts/run_pipeline.sh (ou run_aermet.sh)" >&2
    exit 1
fi

echo "=== CASO: $CASO_ABS ==="
echo "BIN AERMOD : $BIN_AERMOD"
echo "BIN RLINE  : $BIN_RLINE"

# ---- 1. PROCESSAMENTO: AERMOD ---------------------------------------------
echo ""
echo "[1/3] AERMOD (fonte RLINE)..."
bash "$AQUI/run_aermod.sh" "$CASO_ABS/rodada_aermod" "$BIN_AERMOD" \
     "$INP_AERMOD" "$DIR_DADOS_AERMET"

# ---- 2. PROCESSAMENTO: RLINE standalone ------------------------------------
echo ""
echo "[2/2] RLINE v1.2 standalone..."
cp -f "$DIR_DADOS_AERMET/ONSITE.SFC" "$DIR_RODADA_RLINE/ONSITE.SFC"
bash "$AQUI/run_rline.sh" "$CASO_ABS/rodada_rline" "$BIN_RLINE"

# ---- 3. POS-PROCESSAMENTO ----------------------------------------------------
echo ""
echo "[3/3] Pos-processamento (mapas, graficos, resumo)..."
if [ -n "$TRANSECTO" ]; then
    python3 "$AQUI/postprocess_caso.py" "$CASO_ABS" --transecto "$TRANSECTO"
else
    python3 "$AQUI/postprocess_caso.py" "$CASO_ABS"
fi

echo ""
echo "=== CASO CONCLUIDO: $CASO_ABS ==="
echo "  - rodada_aermod/CONC_PLOT.PLT"
echo "  - rodada_rline/Output_Road_Numerical.csv"
echo "  - graficos/*.png"
echo "  - resumo.txt"
