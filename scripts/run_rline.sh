#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# scripts/run_rline.sh
# Roda o RLINE v1.2 standalone em background (setsid) na pasta rodada_rline e
# aguarda o Output_*_Numerical.csv. O binario SEMPRE le Line_Source_Inputs.txt
# do diretorio de trabalho corrente.
#
# Uso:
#   bash scripts/run_rline.sh <dir_rodada_rline> <bin_rline>
#   Ex.: bash scripts/run_rline.sh Caso_Pipeline/rodada_rline \
#            RLINE_v1_2.Source/v1_2/RLINEv1_2_gfortran.x
# ---------------------------------------------------------------------------
set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="$(cd "$AQUI/.." && pwd)"

DIR_RLINE="${1:?Uso: run_rline.sh <dir_rodada_rline> <bin_rline>}"
BIN_RLINE="${2:?Uso: run_rline.sh <dir_rodada_rline> <bin_rline>}"

case "$BIN_RLINE" in
    /*) BIN_RLINE_ABS="$BIN_RLINE" ;;
    *)  BIN_RLINE_ABS="$RAIZ/$BIN_RLINE" ;;
esac
case "$DIR_RLINE" in
    /*) DIR_RLINE_ABS="$DIR_RLINE" ;;
    *)  DIR_RLINE_ABS="$RAIZ/$DIR_RLINE" ;;
esac

if [ ! -x "$BIN_RLINE_ABS" ]; then
    echo "ERRO: binario RLINE nao encontrado: $BIN_RLINE_ABS" >&2
    exit 1
fi
if [ ! -f "$DIR_RLINE_ABS/Line_Source_Inputs.txt" ]; then
    echo "ERRO: Line_Source_Inputs.txt nao encontrado em $DIR_RLINE_ABS" >&2
    exit 1
fi

cd "$DIR_RLINE_ABS"

echo ">>> RLINE em $(pwd) (setsid, background)"
setsid "$BIN_RLINE_ABS" > /tmp/rline_run.log 2>&1 &
PID=$!
echo ">>> PID=$PID  aguardando termino..."

SECONDS=0
while kill -0 "$PID" 2>/dev/null; do
    if [ "$SECONDS" -gt 1800 ]; then
        echo "ERRO: timeout (30 min) aguardando o RLINE" >&2
        exit 1
    fi
    sleep 5
done
wait "$PID" || true

echo ">>> Log (tail /tmp/rline_run.log):"
tail -15 /tmp/rline_run.log

if ! ls Output_*_Numerical.csv >/dev/null 2>&1; then
    echo "ERRO: nenhum Output_*_Numerical.csv gerado" >&2
    exit 1
fi
echo ">>> RLINE OK: $(ls Output_*_Numerical.csv)"
