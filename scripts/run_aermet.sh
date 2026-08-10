#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# scripts/run_aermet.sh
# Roda o AERMET (Stage 1 + Stage 2) e valida "AERMET FINISHED SUCCESSFULLY".
#
# Uso:
#   bash scripts/run_aermet.sh <dir_dados_aermet> <bin_aermet>
#   Ex.: bash scripts/run_aermet.sh Caso_Pipeline/dados_aermet \
#            aermet_and_aermod/aermet_source/aermet
# ---------------------------------------------------------------------------
set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="$(cd "$AQUI/.." && pwd)"

DIR_DADOS="${1:?Uso: run_aermet.sh <dir_dados_aermet> <bin_aermet>}"
BIN_AERMET="${2:?Uso: run_aermet.sh <dir_dados_aermet> <bin_aermet>}"

# Resolve caminho absoluto (aceita relativo a raiz do projeto ou absoluto)
case "$BIN_AERMET" in
    /*) BIN_AERMET_ABS="$BIN_AERMET" ;;
    *)  BIN_AERMET_ABS="$RAIZ/$BIN_AERMET" ;;
esac

if [ ! -x "$BIN_AERMET_ABS" ]; then
    echo "ERRO: binario AERMET nao encontrado: $BIN_AERMET_ABS" >&2
    exit 1
fi

cd "$RAIZ/$DIR_DADOS"

for S in 1 2; do
    echo ">>> AERMET Stage $S em $(pwd)"
    "$BIN_AERMET_ABS" "ONSITE_S${S}.INP"
    if [ "$S" = "1" ]; then
        if ! grep -qi "AERMET FINISHED SUCCESSFULLY" ONSITE_S1_REPORT.TXT; then
            echo "ERRO: Stage 1 nao terminou com sucesso (ver ONSITE_S1_REPORT.TXT)" >&2
            exit 1
        fi
        echo ">>> Stage 1 OK (ONSITE_QAOUT.TXT gerado)"
    else
        if ! grep -qi "AERMET FINISHED SUCCESSFULLY" ONSITE_S2_REPORT.RPT; then
            echo "ERRO: Stage 2 nao terminou com sucesso (ver ONSITE_S2_REPORT.RPT)" >&2
            exit 1
        fi
        echo ">>> Stage 2 OK (ONSITE.SFC e ONSITE.PFL gerados)"
    fi
done
