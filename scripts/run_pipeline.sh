#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# scripts/run_pipeline.sh
# Orquestrador fim-a-fim do pipeline:
#   1. gera ONSITE.MET (gerar_dados_onsite.py)
#   2. AERMET Stage 1 + Stage 2 (run_aermet.sh)
#   3. AERMOD com fonte RLINE (run_aermod.sh)
#   4. RLINE v1.2 standalone (run_rline.sh)
#   5. pos-processamento (compare + graficos)
# Uso: bash scripts/run_pipeline.sh
# ---------------------------------------------------------------------------
set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="$(cd "$AQUI/.." && pwd)"

# ---- Parametros padrao (configuraveis por variavel de ambiente) -------------
BIN_AERMET="${BIN_AERMET:-$RAIZ/aermet_and_aermod/aermet_source/aermet}"
BIN_AERMOD="${BIN_AERMOD:-$RAIZ/aermet_and_aermod/aermod_source/aermod_source_v26135/aermod}"
BIN_RLINE="${BIN_RLINE:-$RAIZ/RLINE_v1_2.Source/v1_2/RLINEv1_2_gfortran.x}"

DIR_DADOS="${DIR_DADOS:-Caso_Pipeline/dados_aermet}"
DIR_RODADA_AERMOD="${DIR_RODADA_AERMOD:-Caso_Pipeline/rodada_aermod}"
DIR_RODADA_RLINE="${DIR_RODADA_RLINE:-Caso_Pipeline/rodada_rline}"
DIR_GRAFICOS="${DIR_GRAFICOS:-Caso_Pipeline/graficos}"
INP_AERMOD="${INP_AERMOD:-Caso_Pipeline/controles_aermod/RLINE_TEST.INP}"

echo "=== PIPELINE AERMET -> AERMOD/RLINE ==="
echo "RAIZ        : $RAIZ"
echo "BIN AERMET  : $BIN_AERMET"
echo "BIN AERMOD  : $BIN_AERMOD"
echo "BIN RLINE   : $BIN_RLINE"

# ---- 1. Dados brutos ---------------------------------------------------------
echo ""
echo "[1/7] Gerando ONSITE.MET..."
python3 "$RAIZ/Caso_Pipeline/scripts/gerar_dados_onsite.py"

# ---- 2. AERMET ---------------------------------------------------------------
echo ""
echo "[2/7] AERMET Stage 1 + Stage 2..."
bash "$AQUI/run_aermet.sh" "$DIR_DADOS" "$BIN_AERMET"

# ---- 3. AERMOD ---------------------------------------------------------------
echo ""
echo "[3/7] AERMOD com fonte RLINE..."
bash "$AQUI/run_aermod.sh" "$DIR_RODADA_AERMOD" "$BIN_AERMOD" "$INP_AERMOD" "$DIR_DADOS"

# ---- 4. RLINE standalone -----------------------------------------------------
echo ""
echo "[4/7] RLINE v1.2 standalone..."
bash "$AQUI/run_rline.sh" "$DIR_RODADA_RLINE" "$BIN_RLINE"

# ---- 5. Pos-processamento ----------------------------------------------------
echo ""
echo "[5/7] Comparacao AERMOD vs RLINE..."
mkdir -p "$RAIZ/$DIR_GRAFICOS"
cd "$RAIZ"
python3 Caso_Pipeline/scripts/compare_aermod_rline.py

echo ""
echo "[6/7] Grafico de concentracao (mapa + transecto)..."
cd "$RAIZ/$DIR_RODADA_AERMOD"
python3 "$RAIZ/Caso_Pipeline/scripts/plot_conc_aermod_rline.py"

echo ""
echo "[7/7] Grafico de comparacao AERMOD vs RLINE..."
cd "$RAIZ"
python3 Caso_Pipeline/scripts/plot_compare_aermod_rline.py

echo ""
echo "=== PIPELINE CONCLUIDO COM SUCESSO ==="
echo "Resultados em:"
echo "  - $DIR_RODADA_AERMOD/CONC_PLOT.PLT"
echo "  - $DIR_RODADA_RLINE/Output_Road_Numerical.csv"
echo "  - $DIR_GRAFICOS/*.png"
