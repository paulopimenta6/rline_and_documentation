#!/usr/bin/env bash
# Execute one generated case transactionally. Model and post-processing outputs
# remain in staging until all three steps have succeeded and been validated.

set -euo pipefail

AQUI="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="$(cd -- "$AQUI/.." && pwd)"
source "$AQUI/lib/run_common.sh"

if (( $# < 1 )); then
    printf 'Uso: %s <pasta_do_caso> [transecto_x] [diretorio_de_logs]\n' "$0" >&2
    exit 64
fi

CASO_ABS="$(resolve_project_path "$1")"
TRANSECTO="${2:-}"
CASE_LOG_DIR_ARG="${3:-${CASE_LOG_DIR:-}}"
BIN_AERMOD_ABS="$(resolve_project_path "${BIN_AERMOD:-$RAIZ/build/aermod/aermod}")"
BIN_RLINE_ABS="$(resolve_project_path "${BIN_RLINE:-$RAIZ/build/rline-patched/RLINEv1_2_patched.x}")"
DIR_DADOS_AERMET_ABS="$(resolve_project_path "${DIR_DADOS_AERMET:-$RAIZ/Caso_Pipeline/dados_aermet}")"
INP_AERMOD_ABS="$(resolve_project_path "${INP_AERMOD:-$CASO_ABS/controles_aermod/RLINE_TEST.INP}")"
STEP_TIMEOUT_SECONDS="${CASE_STEP_TIMEOUT_SECONDS:-7200}"
POSTPROCESS_TIMEOUT_SECONDS="${POSTPROCESS_TIMEOUT_SECONDS:-600}"
if [[ -n "$CASE_LOG_DIR_ARG" ]]; then
    RUN_LOG_DIR="$(resolve_project_path "$CASE_LOG_DIR_ARG")"
    export RUN_LOG_DIR
fi

run_init "caso" "$CASO_ABS" "$AQUI/run_caso.sh"
run_acquire_lock "$CASO_ABS/rodada_aermod" "aermod"
run_acquire_lock "$CASO_ABS/rodada_rline" "rline"

if [[ ! -x "$BIN_AERMOD_ABS" ]]; then
    run_fail 69 "ERRO: binario AERMOD nao encontrado em $BIN_AERMOD_ABS; execute 'make aermod' ou defina BIN_AERMOD"
fi
if [[ ! -x "$BIN_RLINE_ABS" ]]; then
    run_fail 69 "ERRO: binario RLINE corrigido nao encontrado em $BIN_RLINE_ABS; execute 'make rline-release' ou defina BIN_RLINE"
fi
if ! require_nonempty_file "$INP_AERMOD_ABS"; then
    run_fail 66 "ERRO: dados do caso nao gerados; control file ausente ou vazio: $INP_AERMOD_ABS"
fi
for met_name in ONSITE.SFC ONSITE.PFL; do
    if ! require_nonempty_file "$DIR_DADOS_AERMET_ABS/$met_name"; then
        run_fail 66 "ERRO: meteorologia compartilhada ausente ou vazia: $DIR_DADOS_AERMET_ABS/$met_name"
    fi
    run_add_input "$DIR_DADOS_AERMET_ABS/$met_name"
done
for rline_input in Line_Source_Inputs.txt Source_Road.txt Receptor_Road.txt; do
    if ! require_nonempty_file "$CASO_ABS/rodada_rline/$rline_input"; then
        run_fail 66 "ERRO: input RLINE do caso ausente ou vazio: $CASO_ABS/rodada_rline/$rline_input"
    fi
    run_add_input "$CASO_ABS/rodada_rline/$rline_input"
done
run_add_input "$INP_AERMOD_ABS"
if [[ -s "$CASO_ABS/config.json" ]]; then
    run_add_input "$CASO_ABS/config.json"
fi

STAGED_CASE="$RUN_WORKSPACE/caso"
STAGED_AERMOD="$STAGED_CASE/rodada_aermod"
STAGED_RLINE="$STAGED_CASE/rodada_rline"
STAGED_CONTROL_DIR="$STAGED_CASE/controles_aermod"
mkdir -p -- "$STAGED_AERMOD" "$STAGED_RLINE" "$STAGED_CONTROL_DIR" "$STAGED_CASE/graficos"
CONTROL_NAME="$(basename -- "$INP_AERMOD_ABS")"
CONTROL_STEM="${CONTROL_NAME%.*}"
cp -f -- "$INP_AERMOD_ABS" "$STAGED_CONTROL_DIR/$CONTROL_NAME"
if ! copy_tree_without_runtime "$CASO_ABS/rodada_rline" "$STAGED_RLINE"; then
    run_fail 73 "ERRO: falha ao preparar inputs RLINE do caso em staging"
fi
rm -f -- "$STAGED_RLINE"/Output_*_Numerical*.csv
if [[ -s "$CASO_ABS/config.json" ]]; then
    cp -f -- "$CASO_ABS/config.json" "$STAGED_CASE/config.json"
fi

run_log "=== CASO: $CASO_ABS ==="
run_log "BIN AERMOD: $BIN_AERMOD_ABS"
run_log "BIN RLINE : $BIN_RLINE_ABS"

if run_child_command "$RAIZ" "$STEP_TIMEOUT_SECONDS" "wrapper AERMOD do caso" \
    env RUN_LOG_DIR="$RUN_LOG_DIR" RUN_TIMEOUT_SECONDS="$STEP_TIMEOUT_SECONDS" \
    bash "$AQUI/run_aermod.sh" \
    "$STAGED_AERMOD" "$BIN_AERMOD_ABS" "$STAGED_CONTROL_DIR/$CONTROL_NAME" \
    "$DIR_DADOS_AERMET_ABS"; then
    :
else
    step_status=$?
    run_fail_command "wrapper AERMOD do caso" "$step_status"
fi

if run_child_command "$RAIZ" "$STEP_TIMEOUT_SECONDS" "wrapper RLINE do caso" \
    env RUN_LOG_DIR="$RUN_LOG_DIR" RUN_TIMEOUT_SECONDS="$STEP_TIMEOUT_SECONDS" \
    bash "$AQUI/run_rline.sh" \
    "$STAGED_RLINE" "$BIN_RLINE_ABS" "$DIR_DADOS_AERMET_ABS/ONSITE.SFC"; then
    :
else
    step_status=$?
    run_fail_command "wrapper RLINE do caso" "$step_status"
fi

if [[ -n "$TRANSECTO" ]]; then
    POSTPROCESS_COMMAND=(python3 "$AQUI/postprocess_caso.py" "$STAGED_CASE" --transecto "$TRANSECTO")
else
    POSTPROCESS_COMMAND=(python3 "$AQUI/postprocess_caso.py" "$STAGED_CASE")
fi
if run_timed_command "$RAIZ" "$POSTPROCESS_TIMEOUT_SECONDS" "pos-processamento do caso" \
    "${POSTPROCESS_COMMAND[@]}"; then
    :
else
    step_status=$?
    run_fail_command "pos-processamento do caso" "$step_status"
fi

if ! require_nonempty_file "$STAGED_AERMOD/$CONTROL_STEM.out"; then
    run_fail 65 "ERRO: relatorio AERMOD validado desapareceu do staging: $CONTROL_STEM.out"
fi
if ! require_file_contains "$STAGED_AERMOD/CONC_PLOT.PLT" 'AERMOD|PLOT[[:space:]]+FILE'; then
    run_fail 65 "ERRO: CONC_PLOT.PLT do caso esta ausente ou invalido no staging"
fi
if ! require_nonempty_file "$STAGED_CASE/resumo.txt"; then
    run_fail 65 "ERRO: pos-processamento nao gerou resumo.txt novo e nao vazio"
fi
for graph_name in conc_periodo_rline.png conc_aermod_vs_rline.png; do
    if ! require_png "$STAGED_CASE/graficos/$graph_name"; then
        run_fail 65 "ERRO: pos-processamento nao gerou PNG valido: graficos/$graph_name"
    fi
done

PUBLISH=(
    "rodada_aermod/$CONTROL_NAME"
    rodada_aermod/ONSITE.SFC
    rodada_aermod/ONSITE.PFL
    "rodada_aermod/$CONTROL_STEM.out"
    rodada_aermod/CONC_PLOT.PLT
    rodada_rline/ONSITE.SFC
    graficos/conc_periodo_rline.png
    graficos/conc_aermod_vs_rline.png
    resumo.txt
)
restore_nullglob=0
if shopt -q nullglob; then
    :
else
    shopt -s nullglob
    restore_nullglob=1
fi
rline_outputs=("$STAGED_RLINE"/Output_*_Numerical*.csv)
if (( restore_nullglob == 1 )); then
    shopt -u nullglob
fi
if (( ${#rline_outputs[@]} == 0 )); then
    run_fail 65 "ERRO: nenhum Output_*_Numerical*.csv novo foi produzido pelo RLINE"
fi
for rline_output in "${rline_outputs[@]}"; do
    if ! require_nonempty_file "$rline_output"; then
        run_fail 65 "ERRO: output RLINE vazio no staging: $rline_output"
    fi
    PUBLISH+=("rodada_rline/$(basename -- "$rline_output")")
done

if publish_files "$STAGED_CASE" "$CASO_ABS" "${PUBLISH[@]}"; then
    :
else
    publish_status=$?
    run_fail "$publish_status" "ERRO: falha ao publicar resultado transacional do caso"
fi

FINAL_OUTPUTS=(
    "$CASO_ABS/rodada_aermod/$CONTROL_STEM.out"
    "$CASO_ABS/rodada_aermod/CONC_PLOT.PLT"
    "$CASO_ABS/graficos/conc_periodo_rline.png"
    "$CASO_ABS/graficos/conc_aermod_vs_rline.png"
    "$CASO_ABS/resumo.txt"
)
for rline_output in "${rline_outputs[@]}"; do
    FINAL_OUTPUTS+=("$CASO_ABS/rodada_rline/$(basename -- "$rline_output")")
done
run_set_outputs "${FINAL_OUTPUTS[@]}"
run_log "=== CASO CONCLUIDO E PUBLICADO: $CASO_ABS ==="
run_log ">>> Log exclusivo: $RUN_LOG"
run_mark_success
