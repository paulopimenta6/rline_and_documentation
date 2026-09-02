#!/usr/bin/env bash
# Regenerate every case from config.json, execute it and validate the complete
# discovered set. JSON paths are passed as data, never interpolated into code.

set -euo pipefail

AQUI="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="$(cd -- "$AQUI/.." && pwd)"
source "$AQUI/lib/run_common.sh"

read_transect_from_json() {
    python3 - "$1" <<'PY'
import json
import math
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    config = json.load(stream)
value = float(config.get("transecto_x", 600.0))
if not math.isfinite(value):
    raise ValueError("transecto_x must be finite")
print(value)
PY
}

CASES_DIR_ABS="$(resolve_project_path "${CASES_DIR:-$RAIZ/casos}")"
CASE_TIMEOUT_SECONDS="${ALL_CASES_STEP_TIMEOUT_SECONDS:-21600}"
PYTHON_TIMEOUT_SECONDS="${PYTHON_TIMEOUT_SECONDS:-600}"
MAX_PARALLEL_CASES="${MAX_PARALLEL_CASES:-1}"
CASE_CHILD_KILL_GRACE_SECONDS="${CASE_KILL_GRACE_SECONDS:-${RUN_KILL_GRACE_SECONDS:-5}}"
ALL_CASES_KILL_GRACE_SECONDS="${ALL_CASES_KILL_GRACE_SECONDS:-15}"
run_init "todos-casos" "$CASES_DIR_ABS" "$AQUI/run_todos_casos.sh"

if [[ ! "$MAX_PARALLEL_CASES" =~ ^[1-9][0-9]*$ ]]; then
    run_fail 64 "ERRO: MAX_PARALLEL_CASES deve ser um inteiro positivo: $MAX_PARALLEL_CASES"
fi
if ! command -v xargs >/dev/null 2>&1; then
    run_fail 69 "ERRO: comando obrigatorio nao encontrado: xargs"
fi

restore_nullglob=0
if shopt -q nullglob; then
    :
else
    shopt -s nullglob
    restore_nullglob=1
fi
CONFIGS=("$CASES_DIR_ABS"/caso*_*/config.json)
if (( restore_nullglob == 1 )); then
    shopt -u nullglob
fi
if (( ${#CONFIGS[@]} == 0 )); then
    run_fail 66 "ERRO: nenhum config.json encontrado em $CASES_DIR_ABS/caso*_*/"
fi

STAGED_CASES_ROOT="$RUN_WORKSPACE/cases"
mkdir -p -- "$STAGED_CASES_ROOT"
CASE_DIRS=()
CASE_DESTINATIONS=()
TRANSECTS=()
case_index=0
for config_path in "${CONFIGS[@]}"; do
    case_index=$((case_index + 1))
    destination_case_dir="$(dirname -- "$config_path")"
    run_acquire_lock "$destination_case_dir" "caso"
    run_acquire_lock "$destination_case_dir/rodada_aermod" "aermod"
    run_acquire_lock "$destination_case_dir/rodada_rline" "rline"

    case_dir="$STAGED_CASES_ROOT/$(basename -- "$destination_case_dir")"
    mkdir -p -- "$case_dir"
    cp -f -- "$config_path" "$case_dir/config.json"
    run_add_input "$config_path"

    run_log ">>> Regenerando integralmente $destination_case_dir a partir de $config_path"
    if run_timed_command "$RAIZ" "$PYTHON_TIMEOUT_SECONDS" \
        "geracao do caso $(basename -- "$destination_case_dir")" \
        python3 "$AQUI/gerar_caso.py" "$case_dir/config.json"; then
        :
    else
        generation_status=$?
        run_fail_command "geracao do caso $(basename -- "$case_dir")" "$generation_status"
    fi

    GENERATED_INPUTS=(
        controles_aermod/RLINE_TEST.INP
        rodada_rline/Source_Road.txt
        rodada_rline/Receptor_Road.txt
        rodada_rline/Line_Source_Inputs.txt
        metadados.txt
    )
    for generated_input in "${GENERATED_INPUTS[@]}"; do
        if ! require_nonempty_file "$case_dir/$generated_input"; then
            run_fail 65 "ERRO: gerar_caso.py nao produziu input valido: $generated_input ($config_path)"
        fi
        run_add_input "$case_dir/$generated_input"
    done

    if transect="$(read_transect_from_json "$case_dir/config.json")"; then
        :
    else
        json_status=$?
        run_fail "$json_status" "ERRO: config.json invalido ao ler transecto: $config_path"
    fi
    CASE_DIRS+=("$case_dir")
    CASE_DESTINATIONS+=("$destination_case_dir")
    TRANSECTS+=("$transect")
done

CASE_ARGUMENTS="$RUN_WORKSPACE/case-arguments"
CASE_STATUS_DIR="$RUN_WORKSPACE/case-status"
mkdir -p -- "$CASE_STATUS_DIR"
CASE_STATUS_FILES=()
: > "$CASE_ARGUMENTS"
for ((case_index = 0; case_index < ${#CASE_DIRS[@]}; case_index++)); do
    case_dir="${CASE_DIRS[$case_index]}"
    destination_case_dir="${CASE_DESTINATIONS[$case_index]}"
    transect="${TRANSECTS[$case_index]}"
    status_file="$CASE_STATUS_DIR/$case_index.status"
    CASE_STATUS_FILES+=("$status_file")
    run_log ">>> Agendando $(basename -- "$case_dir") (transecto $transect)"
    printf '%s\0%s\0%s\0%s\0%s\0' "$case_dir" "$transect" \
        "$destination_case_dir/logs" "$status_file" \
        "$CASE_CHILD_KILL_GRACE_SECONDS" >> "$CASE_ARGUMENTS"
done
previous_kill_grace="${RUN_KILL_GRACE_SECONDS:-}"
RUN_KILL_GRACE_SECONDS="$ALL_CASES_KILL_GRACE_SECONDS"
export RUN_KILL_GRACE_SECONDS
if run_timed_command "$RAIZ" "$CASE_TIMEOUT_SECONDS" \
    "pipelines de ${#CASE_DIRS[@]} casos (paralelismo $MAX_PARALLEL_CASES)" \
    env RUN_CASE_SCRIPT="$AQUI/run_caso.sh" \
    xargs --null --arg-file="$CASE_ARGUMENTS" --max-args=5 \
    --max-procs="$MAX_PARALLEL_CASES" bash -c '
set -u
case_dir="$1"
transect="$2"
log_dir="$3"
status_file="$4"
child_grace="$5"
if env RUN_KILL_GRACE_SECONDS="$child_grace" \
    bash "$RUN_CASE_SCRIPT" "$case_dir" "$transect" "$log_dir"; then
    status=0
else
    status=$?
fi
temporary_status="${status_file}.tmp.$$"
printf "%s\n" "$status" > "$temporary_status"
if ! mv -f -- "$temporary_status" "$status_file"; then
    exit 70
fi
exit "$status"
' run-case; then
    case_status=0
    batch_timed_out=0
else
    xargs_status=$?
    batch_timed_out="$RUN_LAST_TIMED_OUT"
    case_status="$xargs_status"
fi
if [[ -n "$previous_kill_grace" ]]; then
    RUN_KILL_GRACE_SECONDS="$previous_kill_grace"
    export RUN_KILL_GRACE_SECONDS
else
    unset RUN_KILL_GRACE_SECONDS
fi
if (( batch_timed_out == 0 )); then
    for status_file in "${CASE_STATUS_FILES[@]}"; do
        if [[ ! -s "$status_file" ]]; then
            case_status=70
            break
        fi
        child_status="$(<"$status_file")"
        if [[ ! "$child_status" =~ ^[0-9]+$ ]]; then
            case_status=70
            break
        fi
        if (( child_status != 0 )); then
            case_status="$child_status"
            break
        fi
    done
    if (( case_status == 124 )); then
        RUN_LAST_TIMED_OUT=1
    fi
fi
if (( case_status != 0 )); then
    run_fail_command "pipelines dos casos" "$case_status"
fi

SUMMARY_ROOT="$RUN_WORKSPACE/summary"
SUMMARY_CASES="$SUMMARY_ROOT/casos"
mkdir -p -- "$SUMMARY_CASES"
for case_dir in "${CASE_DIRS[@]}"; do
    ln -s -- "$case_dir" "$SUMMARY_CASES/$(basename -- "$case_dir")"
done
if run_timed_command "$SUMMARY_ROOT" "$PYTHON_TIMEOUT_SECONDS" \
    "comparativo geral dos casos" python3 "$AQUI/plot_casos_resumo.py" \
    --casos "$SUMMARY_CASES" --saida "$SUMMARY_CASES/comparativo_geral.png"; then
    :
else
    summary_status=$?
    run_fail_command "comparativo geral dos casos" "$summary_status"
fi
if ! require_png "$SUMMARY_CASES/comparativo_geral.png"; then
    run_fail 65 "ERRO: plot_casos_resumo.py nao gerou comparativo_geral.png valido"
fi

if run_timed_command "$RAIZ" "$PYTHON_TIMEOUT_SECONDS" \
    "testes de verificacao de todos os casos" \
    python3 "$AQUI/teste_casos.py" "${CASE_DIRS[@]}"; then
    :
else
    verification_status=$?
    run_fail_command "testes de verificacao de todos os casos" "$verification_status"
fi

cp -f -- "$SUMMARY_CASES/comparativo_geral.png" "$STAGED_CASES_ROOT/comparativo_geral.png"
CASE_PUBLISH=(comparativo_geral.png)
FINAL_OUTPUTS=("$CASES_DIR_ABS/comparativo_geral.png")
for ((case_index = 0; case_index < ${#CASE_DIRS[@]}; case_index++)); do
    case_dir="${CASE_DIRS[$case_index]}"
    destination_case_dir="${CASE_DESTINATIONS[$case_index]}"
    case_name="$(basename -- "$case_dir")"
    CASE_PUBLISH+=(
        "$case_name/controles_aermod/RLINE_TEST.INP"
        "$case_name/rodada_rline/Source_Road.txt"
        "$case_name/rodada_rline/Receptor_Road.txt"
        "$case_name/rodada_rline/Line_Source_Inputs.txt"
        "$case_name/metadados.txt"
        "$case_name/rodada_aermod/RLINE_TEST.INP"
        "$case_name/rodada_aermod/ONSITE.SFC"
        "$case_name/rodada_aermod/ONSITE.PFL"
        "$case_name/rodada_aermod/RLINE_TEST.out"
        "$case_name/rodada_aermod/CONC_PLOT.PLT"
        "$case_name/rodada_rline/ONSITE.SFC"
        "$case_name/graficos/conc_periodo_rline.png"
        "$case_name/graficos/conc_aermod_vs_rline.png"
        "$case_name/resumo.txt"
    )
    restore_nullglob=0
    if shopt -q nullglob; then
        :
    else
        shopt -s nullglob
        restore_nullglob=1
    fi
    staged_rline_outputs=("$case_dir"/rodada_rline/Output_*_Numerical*.csv)
    if (( restore_nullglob == 1 )); then
        shopt -u nullglob
    fi
    for staged_rline_output in "${staged_rline_outputs[@]}"; do
        CASE_PUBLISH+=("$case_name/rodada_rline/$(basename -- "$staged_rline_output")")
    done
    FINAL_OUTPUTS+=(
        "$destination_case_dir/rodada_aermod/CONC_PLOT.PLT"
        "$destination_case_dir/rodada_rline/Output_Road_Numerical.csv"
        "$destination_case_dir/resumo.txt"
    )
done
if publish_files "$STAGED_CASES_ROOT" "$CASES_DIR_ABS" "${CASE_PUBLISH[@]}"; then
    :
else
    publish_status=$?
    run_fail "$publish_status" "ERRO: falha ao publicar o conjunto validado de casos"
fi
run_set_outputs "${FINAL_OUTPUTS[@]}"
run_log "=== TODOS OS CASOS REGENERADOS, PROCESSADOS E VALIDADOS ==="
run_log ">>> Log exclusivo: $RUN_LOG"
run_mark_success
