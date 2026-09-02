#!/usr/bin/env bash
# Run RLINE in an isolated workspace with process-group timeout handling. The
# optional third argument supplies meteorology and is staged as ./ONSITE.SFC.

set -euo pipefail

AQUI="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="$(cd -- "$AQUI/.." && pwd)"
source "$AQUI/lib/run_common.sh"

extract_rline_values() {
    local control_file="$1"
    local line
    local trimmed
    RLINE_QUOTED_VALUES=()
    while IFS= read -r line || [[ -n "$line" ]]; do
        trimmed="${line#"${line%%[![:space:]]*}"}"
        trimmed="${trimmed%"${trimmed##*[![:space:]]}"}"
        if (( ${#trimmed} >= 2 )) && \
            { [[ "${trimmed:0:1}" == "'" && "${trimmed: -1}" == "'" ]] || \
              [[ "${trimmed:0:1}" == '"' && "${trimmed: -1}" == '"' ]]; }; then
            RLINE_QUOTED_VALUES+=("${trimmed:1:${#trimmed}-2}")
        fi
    done < "$control_file"
}

rewrite_rline_input_paths() {
    local control_file="$1"
    local source_name="$2"
    local receptor_name="$3"
    local met_name="$4"
    local temporary_file="$control_file.wrapper-new"
    local line
    local trimmed
    local quoted_count=0
    : > "$temporary_file"
    while IFS= read -r line || [[ -n "$line" ]]; do
        trimmed="${line#"${line%%[![:space:]]*}"}"
        trimmed="${trimmed%"${trimmed##*[![:space:]]}"}"
        if (( ${#trimmed} >= 2 )) && \
            { [[ "${trimmed:0:1}" == "'" && "${trimmed: -1}" == "'" ]] || \
              [[ "${trimmed:0:1}" == '"' && "${trimmed: -1}" == '"' ]]; }; then
            quoted_count=$((quoted_count + 1))
            case "$quoted_count" in
                1) line="'./$source_name'" ;;
                2) line="'./$receptor_name'" ;;
                3) line="'./$met_name'" ;;
            esac
        fi
        printf '%s\n' "$line" >> "$temporary_file"
    done < "$control_file"
    mv -f -- "$temporary_file" "$control_file"
}

append_output_relative() {
    local candidate="$1"
    local existing
    for existing in "${OUTPUT_RELS[@]}"; do
        if [[ "$existing" == "$candidate" ]]; then
            return 0
        fi
    done
    OUTPUT_RELS+=("$candidate")
}

PIPELINE_DIR="${PIPELINE_CASE_DIR:-$RAIZ/Caso_Pipeline}"
DIR_RLINE_ARG="${1:-${DIR_RODADA_RLINE:-$PIPELINE_DIR/rodada_rline}}"
BIN_RLINE_ARG="${2:-${BIN_RLINE:-$RAIZ/build/rline-patched/RLINEv1_2_patched.x}}"
MET_OVERRIDE_ARG="${3:-${RLINE_MET_FILE:-}}"
TIMEOUT_SECONDS="${RLINE_TIMEOUT_SECONDS:-${RUN_TIMEOUT_SECONDS:-1800}}"

DIR_RLINE_ABS="$(resolve_project_path "$DIR_RLINE_ARG")"
BIN_RLINE_ABS="$(resolve_project_path "$BIN_RLINE_ARG")"
MET_OVERRIDE_ABS=""
if [[ -n "$MET_OVERRIDE_ARG" ]]; then
    MET_OVERRIDE_ABS="$(resolve_project_path "$MET_OVERRIDE_ARG")"
fi
run_init "rline" "$DIR_RLINE_ABS" "$BIN_RLINE_ABS"

if [[ ! -x "$BIN_RLINE_ABS" ]]; then
    run_fail 69 "ERRO: binario RLINE corrigido nao encontrado em $BIN_RLINE_ABS; execute 'make rline-release' ou defina BIN_RLINE"
fi
CONTROL_FILE="$DIR_RLINE_ABS/Line_Source_Inputs.txt"
if ! require_nonempty_file "$CONTROL_FILE"; then
    run_fail 66 "ERRO: Line_Source_Inputs.txt ausente ou vazio em $DIR_RLINE_ABS"
fi
run_add_input "$CONTROL_FILE"

extract_rline_values "$CONTROL_FILE"
if (( ${#RLINE_QUOTED_VALUES[@]} < 4 )); then
    run_fail 65 "ERRO: Line_Source_Inputs.txt nao contem source, receptor, meteorologia e output validos"
fi
SOURCE_REF="${RLINE_QUOTED_VALUES[0]}"
RECEPTOR_REF="${RLINE_QUOTED_VALUES[1]}"
MET_REF="${RLINE_QUOTED_VALUES[2]}"
OUTPUT_REL="${RLINE_QUOTED_VALUES[3]}"
if ! _safe_relative_path "$OUTPUT_REL"; then
    run_fail 65 "ERRO: output RLINE deve ser relativo e permanecer no workspace: $OUTPUT_REL"
fi
case "$OUTPUT_REL" in
    Line_Source_Inputs.txt|Source_Road.txt|Receptor_Road.txt|ONSITE.SFC|wrapper_*|logs/*|*/logs/*|*.lock|*/*.lock)
        run_fail 65 "ERRO: output RLINE colide com caminho reservado do wrapper: $OUTPUT_REL"
        ;;
esac

SOURCE_ABS="$(resolve_path_from "$DIR_RLINE_ABS" "$SOURCE_REF")"
RECEPTOR_ABS="$(resolve_path_from "$DIR_RLINE_ABS" "$RECEPTOR_REF")"
MET_ABS="$(resolve_path_from "$DIR_RLINE_ABS" "$MET_REF")"
for referenced_input in "$SOURCE_ABS" "$RECEPTOR_ABS"; do
    if ! require_nonempty_file "$referenced_input"; then
        run_fail 66 "ERRO: input referenciado por Line_Source_Inputs.txt ausente ou vazio: $referenced_input"
    fi
    run_add_input "$referenced_input"
done
if [[ -n "$MET_OVERRIDE_ABS" ]]; then
    if ! require_nonempty_file "$MET_OVERRIDE_ABS"; then
        run_fail 66 "ERRO: meteorologia RLINE informada esta ausente ou vazia: $MET_OVERRIDE_ABS"
    fi
    run_add_input "$MET_OVERRIDE_ABS"
    MET_INPUT_ABS="$MET_OVERRIDE_ABS"
else
    if ! require_nonempty_file "$MET_ABS"; then
        run_fail 66 "ERRO: meteorologia referenciada por Line_Source_Inputs.txt ausente ou vazia: $MET_ABS"
    fi
    run_add_input "$MET_ABS"
    MET_INPUT_ABS="$MET_ABS"
fi

WORK_DIR="$RUN_WORKSPACE/rodada_rline"
mkdir -p -- "$WORK_DIR"
if ! copy_tree_without_runtime "$DIR_RLINE_ABS" "$WORK_DIR"; then
    run_fail 73 "ERRO: falha ao preparar workspace RLINE: $WORK_DIR"
fi
rm -f -- "$WORK_DIR"/Output_*_Numerical*.csv
rm -f -- "$WORK_DIR/$OUTPUT_REL"
if [[ "$OUTPUT_REL" == *.csv ]]; then
    DAILY_REL="${OUTPUT_REL%.csv}_DailyAve.csv"
else
    DAILY_REL="${OUTPUT_REL}_DailyAve.csv"
fi
rm -f -- "$WORK_DIR/$DAILY_REL"

STAGED_SOURCE_NAME="wrapper_source_input.txt"
STAGED_RECEPTOR_NAME="wrapper_receptor_input.txt"
STAGED_MET_NAME="ONSITE.SFC"
cp -f -- "$SOURCE_ABS" "$WORK_DIR/$STAGED_SOURCE_NAME"
cp -f -- "$RECEPTOR_ABS" "$WORK_DIR/$STAGED_RECEPTOR_NAME"
cp -f -- "$MET_INPUT_ABS" "$WORK_DIR/$STAGED_MET_NAME"
rewrite_rline_input_paths "$WORK_DIR/Line_Source_Inputs.txt" \
    "$STAGED_SOURCE_NAME" "$STAGED_RECEPTOR_NAME" "$STAGED_MET_NAME"
run_add_output "$WORK_DIR/$OUTPUT_REL"

if run_timed_command "$WORK_DIR" "$TIMEOUT_SECONDS" "RLINE" "$BIN_RLINE_ABS"; then
    :
else
    command_status=$?
    run_fail_command "RLINE" "$command_status"
fi

if ! require_file_contains "$WORK_DIR/$OUTPUT_REL" 'RLINEv?1[_ .-]*2|RLINE'; then
    run_fail 65 "ERRO: RLINE nao gerou output novo com assinatura RLINE: $OUTPUT_REL"
fi
if ! require_file_contains "$WORK_DIR/$OUTPUT_REL" 'Julian_Day|X-Coordinate'; then
    run_fail 65 "ERRO: output RLINE novo nao contem cabecalho numerico esperado: $OUTPUT_REL"
fi
if PYTHONPATH="$RAIZ" python3 - "$WORK_DIR/$OUTPUT_REL" \
    "$WORK_DIR/$STAGED_RECEPTOR_NAME" "$WORK_DIR/$STAGED_MET_NAME" <<'PY'
import sys

from rline_pipeline import validate_rline_output

validate_rline_output(sys.argv[1], sys.argv[2], sys.argv[3])
PY
then
    :
else
    validation_status=$?
    run_fail "$validation_status" "ERRO: output RLINE falhou na validacao estrutural estrita"
fi

OUTPUT_RELS=()
append_output_relative "$OUTPUT_REL"
if [[ -s "$WORK_DIR/$DAILY_REL" ]]; then
    append_output_relative "$DAILY_REL"
fi
restore_nullglob=0
if shopt -q nullglob; then
    :
else
    shopt -s nullglob
    restore_nullglob=1
fi
generated_files=("$WORK_DIR"/Output_*_Numerical*.csv)
if (( restore_nullglob == 1 )); then
    shopt -u nullglob
fi
for generated_file in "${generated_files[@]}"; do
    if ! require_nonempty_file "$generated_file"; then
        run_fail 65 "ERRO: RLINE gerou output vazio: $generated_file"
    fi
    append_output_relative "${generated_file#"$WORK_DIR/"}"
done

PUBLISH_RELS=("${OUTPUT_RELS[@]}" ONSITE.SFC)
if publish_files "$WORK_DIR" "$DIR_RLINE_ABS" "${PUBLISH_RELS[@]}"; then
    :
else
    publish_status=$?
    run_fail "$publish_status" "ERRO: falha ao publicar outputs validados do RLINE"
fi

FINAL_OUTPUTS=()
for output_relative in "${OUTPUT_RELS[@]}"; do
    FINAL_OUTPUTS+=("$DIR_RLINE_ABS/$output_relative")
    run_log ">>> RLINE output publicado: $DIR_RLINE_ABS/$output_relative"
done
run_set_outputs "${FINAL_OUTPUTS[@]}"
run_log ">>> Log exclusivo: $RUN_LOG"
run_mark_success
