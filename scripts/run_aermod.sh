#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# scripts/run_aermod.sh
# Copia ONSITE.SFC/.PFL para a pasta de rodada, executa o AERMOD em background
# (setsid) com o control file RLINE_TEST.INP e valida
# "AERMOD Finishes Successfully".
#
# Uso:
#   bash scripts/run_aermod.sh <dir_rodada> <bin_aermod> [control_file]
#   Ex.: bash scripts/run_aermod.sh Caso_Pipeline/rodada_aermod \
#            aermet_and_aermod/aermod_source/aermod_source_v26135/aermod \
#            Caso_Pipeline/controles_aermod/RLINE_TEST.INP
# ---------------------------------------------------------------------------
set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="$(cd "$AQUI/.." && pwd)"

DIR_RODADA="${1:?Uso: run_aermod.sh <dir_rodada> <bin_aermod> [control_file]}"
BIN_AERMOD="${2:?Uso: run_aermod.sh <dir_rodada> <bin_aermod> [control_file]}"
INP="${3:-Caso_Pipeline/controles_aermod/RLINE_TEST.INP}"
DIR_DADOS_AERMET="${4:-Caso_Pipeline/dados_aermet}"

case "$BIN_AERMOD" in
    /*) BIN_AERMOD_ABS="$BIN_AERMOD" ;;
    *)  BIN_AERMOD_ABS="$RAIZ/$BIN_AERMOD" ;;
esac
case "$INP" in
    /*) INP_ABS="$INP" ;;
    *)  INP_ABS="$RAIZ/$INP" ;;
esac
case "$DIR_RODADA" in
    /*) DIR_RODADA_ABS="$DIR_RODADA" ;;
    *)  DIR_RODADA_ABS="$RAIZ/$DIR_RODADA" ;;
esac

if [ ! -x "$BIN_AERMOD_ABS" ]; then
    echo "ERRO: binario AERMOD nao encontrado: $BIN_AERMOD_ABS" >&2
    exit 1
fi
if [ ! -f "$INP_ABS" ]; then
    echo "ERRO: control file AERMOD nao encontrado: $INP_ABS" >&2
    exit 1
fi

mkdir -p "$DIR_RODADA_ABS"
cd "$DIR_RODADA_ABS"

# Met pronta do AERMET (aceita caminho absoluto ou relativo a raiz)
case "$DIR_DADOS_AERMET" in
    /*) DADOS_AERMET_ABS="$DIR_DADOS_AERMET" ;;
    *)  DADOS_AERMET_ABS="$RAIZ/$DIR_DADOS_AERMET" ;;
esac
cp -f "$DADOS_AERMET_ABS/ONSITE.SFC" .
cp -f "$DADOS_AERMET_ABS/ONSITE.PFL" .
cp -f "$INP_ABS" ./

echo ">>> AERMOD em $(pwd) (setsid, background)"
setsid "$BIN_AERMOD_ABS" "$(basename "$INP_ABS")" > AERMOD_RUN.out 2>&1 &
PID=$!
echo ">>> PID=$PID  aguardando termino..."

# Aguarda o processo sair (timeout de 30 min)
SECONDS=0
while kill -0 "$PID" 2>/dev/null; do
    if [ "$SECONDS" -gt 1800 ]; then
        echo "ERRO: timeout (30 min) aguardando o AERMOD" >&2
        exit 1
    fi
    sleep 5
done
wait "$PID" || true

OUT="$(basename "$INP_ABS")"
OUT="${OUT%.INP}.out"
if [ ! -f "$OUT" ]; then
    OUT="AERMOD_RUN.out"
fi
echo ">>> Log de saida: $OUT"
if ! grep -qi "AERMOD Finishes Successfully" "$OUT"; then
    echo "ERRO: AERMOD nao terminou com sucesso (ver $OUT)" >&2
    grep -i "error" "$OUT" | head -20 || true
    exit 1
fi
echo ">>> AERMOD OK (CONC_PLOT.PLT gerado)"
