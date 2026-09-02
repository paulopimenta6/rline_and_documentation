#!/usr/bin/env bash
# Run AERMOD transactionally. Inputs are staged, stale outputs are excluded and
# the report/plot are published only after exit-code and content validation.

set -euo pipefail

AQUI="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="$(cd -- "$AQUI/.." && pwd)"
source "$AQUI/lib/run_common.sh"

PIPELINE_DIR="${PIPELINE_CASE_DIR:-$RAIZ/Caso_Pipeline}"
DIR_RODADA_ARG="${1:-${DIR_RODADA_AERMOD:-$PIPELINE_DIR/rodada_aermod}}"
BIN_AERMOD_ARG="${2:-${BIN_AERMOD:-$RAIZ/build/aermod/aermod}}"
INP_ARG="${3:-${INP_AERMOD:-$PIPELINE_DIR/controles_aermod/RLINE_TEST.INP}}"
DIR_DADOS_ARG="${4:-${DIR_DADOS_AERMET:-$PIPELINE_DIR/dados_aermet}}"
TIMEOUT_SECONDS="${AERMOD_TIMEOUT_SECONDS:-${RUN_TIMEOUT_SECONDS:-1800}}"

DIR_RODADA_ABS="$(resolve_project_path "$DIR_RODADA_ARG")"
BIN_AERMOD_ABS="$(resolve_project_path "$BIN_AERMOD_ARG")"
INP_ABS="$(resolve_project_path "$INP_ARG")"
DIR_DADOS_ABS="$(resolve_project_path "$DIR_DADOS_ARG")"
run_init "aermod" "$DIR_RODADA_ABS" "$BIN_AERMOD_ABS"

if [[ ! -x "$BIN_AERMOD_ABS" ]]; then
    run_fail 69 "ERRO: binario AERMOD nao encontrado em $BIN_AERMOD_ABS; execute 'make aermod' ou defina BIN_AERMOD"
fi
if ! require_nonempty_file "$INP_ABS"; then
    run_fail 66 "ERRO: control file AERMOD ausente ou vazio: $INP_ABS"
fi
for met_name in ONSITE.SFC ONSITE.PFL; do
    if ! require_nonempty_file "$DIR_DADOS_ABS/$met_name"; then
        run_fail 66 "ERRO: input meteorologico ausente ou vazio: $DIR_DADOS_ABS/$met_name"
    fi
done
run_add_input "$INP_ABS"
run_add_input "$DIR_DADOS_ABS/ONSITE.SFC"
run_add_input "$DIR_DADOS_ABS/ONSITE.PFL"

CONTROL_NAME="$(basename -- "$INP_ABS")"
CONTROL_STEM="${CONTROL_NAME%.*}"
MODEL_REPORT="$CONTROL_STEM.out"
WORK_DIR="$RUN_WORKSPACE/rodada_aermod"
mkdir -p -- "$WORK_DIR"
if ! copy_tree_without_runtime "$DIR_RODADA_ABS" "$WORK_DIR"; then
    run_fail 73 "ERRO: falha ao preparar workspace AERMOD: $WORK_DIR"
fi
rm -f -- "$WORK_DIR/$MODEL_REPORT" "$WORK_DIR/CONC_PLOT.PLT" "$WORK_DIR/AERMOD_RUN.out"
cp -f -- "$INP_ABS" "$WORK_DIR/$CONTROL_NAME"
cp -f -- "$DIR_DADOS_ABS/ONSITE.SFC" "$WORK_DIR/ONSITE.SFC"
cp -f -- "$DIR_DADOS_ABS/ONSITE.PFL" "$WORK_DIR/ONSITE.PFL"
run_add_output "$WORK_DIR/$MODEL_REPORT"
run_add_output "$WORK_DIR/CONC_PLOT.PLT"

if run_timed_command "$WORK_DIR" "$TIMEOUT_SECONDS" "AERMOD" \
    "$BIN_AERMOD_ABS" "$CONTROL_NAME"; then
    :
else
    command_status=$?
    run_fail_command "AERMOD" "$command_status"
fi

if ! require_file_contains "$WORK_DIR/$MODEL_REPORT" \
    'AERMOD[[:space:]]+Finishes[[:space:]]+Successfully'; then
    run_fail 65 "ERRO: AERMOD nao gerou $MODEL_REPORT novo com mensagem de sucesso"
fi
if ! require_file_contains "$WORK_DIR/CONC_PLOT.PLT" 'AERMOD|PLOT[[:space:]]+FILE'; then
    run_fail 65 "ERRO: AERMOD nao gerou CONC_PLOT.PLT novo, nao vazio e com cabecalho valido"
fi
if PYTHONPATH="$RAIZ" python3 - "$WORK_DIR/$MODEL_REPORT" "$WORK_DIR/CONC_PLOT.PLT" <<'PY'
import sys

from rline_pipeline import parse_aermod, validate_aermod_completion

plot = parse_aermod(sys.argv[2])
hours = plot["NHRS"].unique().tolist()
if len(hours) != 1:
    raise ValueError(f"CONC_PLOT.PLT has inconsistent NHRS values: {hours}")
validate_aermod_completion(sys.argv[1], int(hours[0]))
PY
then
    :
else
    validation_status=$?
    run_fail "$validation_status" "ERRO: outputs AERMOD falharam na validacao estrutural estrita"
fi

PUBLISH=("$CONTROL_NAME" ONSITE.SFC ONSITE.PFL "$MODEL_REPORT" CONC_PLOT.PLT)
if publish_files "$WORK_DIR" "$DIR_RODADA_ABS" "${PUBLISH[@]}"; then
    :
else
    publish_status=$?
    run_fail "$publish_status" "ERRO: falha ao publicar outputs validados do AERMOD"
fi

run_set_outputs "$DIR_RODADA_ABS/$MODEL_REPORT" "$DIR_RODADA_ABS/CONC_PLOT.PLT"
run_log ">>> AERMOD OK: CONC_PLOT.PLT publicado em $DIR_RODADA_ABS"
run_log ">>> Log exclusivo: $RUN_LOG"
run_mark_success
