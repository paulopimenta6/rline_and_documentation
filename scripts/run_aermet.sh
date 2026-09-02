#!/usr/bin/env bash
# Run AERMET stages 1 and 2 in an isolated workspace and publish only validated
# outputs. Relative paths are resolved from the repository root.

set -euo pipefail

AQUI="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="$(cd -- "$AQUI/.." && pwd)"
source "$AQUI/lib/run_common.sh"

DIR_DADOS_ARG="${1:-${DIR_DADOS_AERMET:-$RAIZ/Caso_Pipeline/dados_aermet}}"
BIN_AERMET_ARG="${2:-${BIN_AERMET:-$RAIZ/build/aermet/aermet}}"
TIMEOUT_SECONDS="${AERMET_TIMEOUT_SECONDS:-${RUN_TIMEOUT_SECONDS:-1800}}"

DIR_DADOS_ABS="$(resolve_project_path "$DIR_DADOS_ARG")"
BIN_AERMET_ABS="$(resolve_project_path "$BIN_AERMET_ARG")"
run_init "aermet" "$DIR_DADOS_ABS" "$BIN_AERMET_ABS"

if [[ ! -x "$BIN_AERMET_ABS" ]]; then
    run_fail 69 "ERRO: binario AERMET nao encontrado em $BIN_AERMET_ABS; execute 'make aermet' ou defina BIN_AERMET"
fi
for input_name in ONSITE_S1.INP ONSITE_S2.INP; do
    if ! require_nonempty_file "$DIR_DADOS_ABS/$input_name"; then
        run_fail 66 "ERRO: input AERMET ausente ou vazio: $DIR_DADOS_ABS/$input_name"
    fi
    run_add_input "$DIR_DADOS_ABS/$input_name"
done
if [[ -s "$DIR_DADOS_ABS/ONSITE.MET" ]]; then
    run_add_input "$DIR_DADOS_ABS/ONSITE.MET"
fi

WORK_DIR="$RUN_WORKSPACE/dados_aermet"
mkdir -p -- "$WORK_DIR"
if ! copy_tree_without_runtime "$DIR_DADOS_ABS" "$WORK_DIR"; then
    run_fail 73 "ERRO: falha ao preparar workspace AERMET: $WORK_DIR"
fi

GENERATED=(
    ONSITE_S1_REPORT.TXT
    ONSITE_S1_MESSAGE.TXT
    ONSITE_QAOUT.TXT
    ONSITE_S2_REPORT.RPT
    ONSITE_S2_MESSAGE.TXT
    ONSITE.SFC
    ONSITE.PFL
)
for output_name in "${GENERATED[@]}"; do
    rm -f -- "$WORK_DIR/$output_name"
done
run_add_output "$WORK_DIR/ONSITE_S1_REPORT.TXT"
run_add_output "$WORK_DIR/ONSITE_QAOUT.TXT"
run_add_output "$WORK_DIR/ONSITE_S2_REPORT.RPT"
run_add_output "$WORK_DIR/ONSITE.SFC"
run_add_output "$WORK_DIR/ONSITE.PFL"

run_log ">>> AERMET Stage 1 em workspace exclusivo"
if run_timed_command "$WORK_DIR" "$TIMEOUT_SECONDS" "AERMET Stage 1" \
    "$BIN_AERMET_ABS" ONSITE_S1.INP; then
    :
else
    command_status=$?
    run_fail_command "AERMET Stage 1" "$command_status"
fi
if ! require_file_contains "$WORK_DIR/ONSITE_S1_REPORT.TXT" \
    'AERMET[[:space:]]+FINISHED[[:space:]]+SUCCESSFULLY'; then
    run_fail 65 "ERRO: ONSITE_S1_REPORT.TXT novo, nao vazio e com mensagem de sucesso nao foi gerado"
fi
if ! require_nonempty_file "$WORK_DIR/ONSITE_QAOUT.TXT"; then
    run_fail 65 "ERRO: Stage 1 nao gerou ONSITE_QAOUT.TXT novo e nao vazio"
fi

run_log ">>> AERMET Stage 2 em workspace exclusivo"
if run_timed_command "$WORK_DIR" "$TIMEOUT_SECONDS" "AERMET Stage 2" \
    "$BIN_AERMET_ABS" ONSITE_S2.INP; then
    :
else
    command_status=$?
    run_fail_command "AERMET Stage 2" "$command_status"
fi
if ! require_file_contains "$WORK_DIR/ONSITE_S2_REPORT.RPT" \
    'AERMET[[:space:]]+FINISHED[[:space:]]+SUCCESSFULLY'; then
    run_fail 65 "ERRO: ONSITE_S2_REPORT.RPT novo, nao vazio e com mensagem de sucesso nao foi gerado"
fi
if ! require_file_contains "$WORK_DIR/ONSITE.SFC" 'VERSION:'; then
    run_fail 65 "ERRO: Stage 2 nao gerou ONSITE.SFC novo com cabecalho AERMET valido"
fi
if ! require_file_contains "$WORK_DIR/ONSITE.PFL" \
    '^[[:space:]]*[0-9]{4}[[:space:]]+[0-9]'; then
    run_fail 65 "ERRO: Stage 2 nao gerou ONSITE.PFL novo com registros meteorologicos validos"
fi

PUBLISH=(ONSITE_S1_REPORT.TXT ONSITE_QAOUT.TXT ONSITE_S2_REPORT.RPT ONSITE.SFC ONSITE.PFL)
for optional_name in ONSITE_S1_MESSAGE.TXT ONSITE_S2_MESSAGE.TXT; do
    if [[ -s "$WORK_DIR/$optional_name" ]]; then
        PUBLISH+=("$optional_name")
    fi
done
if publish_files "$WORK_DIR" "$DIR_DADOS_ABS" "${PUBLISH[@]}"; then
    :
else
    publish_status=$?
    run_fail "$publish_status" "ERRO: falha ao publicar outputs validados do AERMET"
fi

FINAL_OUTPUTS=()
for output_name in "${PUBLISH[@]}"; do
    FINAL_OUTPUTS+=("$DIR_DADOS_ABS/$output_name")
done
run_set_outputs "${FINAL_OUTPUTS[@]}"
run_log ">>> AERMET OK: ONSITE.SFC e ONSITE.PFL publicados"
run_log ">>> Log exclusivo: $RUN_LOG"
run_mark_success
