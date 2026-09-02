#!/usr/bin/env bash
# End-to-end transactional orchestration for the canonical pipeline. Configured
# directories may be absolute or relative to the repository root.

set -euo pipefail

AQUI="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="$(cd -- "$AQUI/.." && pwd)"
source "$AQUI/lib/run_common.sh"

PIPELINE_DIR_ABS="$(resolve_project_path "${PIPELINE_CASE_DIR:-$RAIZ/Caso_Pipeline}")"
BIN_AERMET_ABS="$(resolve_project_path "${BIN_AERMET:-$RAIZ/build/aermet/aermet}")"
BIN_AERMOD_ABS="$(resolve_project_path "${BIN_AERMOD:-$RAIZ/build/aermod/aermod}")"
BIN_RLINE_ABS="$(resolve_project_path "${BIN_RLINE:-$RAIZ/build/rline-patched/RLINEv1_2_patched.x}")"
DIR_DADOS_ABS="$(resolve_project_path "${DIR_DADOS_AERMET:-${DIR_DADOS:-$PIPELINE_DIR_ABS/dados_aermet}}")"
DIR_AERMOD_ABS="$(resolve_project_path "${DIR_RODADA_AERMOD:-$PIPELINE_DIR_ABS/rodada_aermod}")"
DIR_RLINE_ABS="$(resolve_project_path "${DIR_RODADA_RLINE:-$PIPELINE_DIR_ABS/rodada_rline}")"
DIR_GRAFICOS_ABS="$(resolve_project_path "${DIR_GRAFICOS:-$PIPELINE_DIR_ABS/graficos}")"
INP_AERMOD_ABS="$(resolve_project_path "${INP_AERMOD:-$PIPELINE_DIR_ABS/controles_aermod/RLINE_TEST.INP}")"
STEP_TIMEOUT_SECONDS="${PIPELINE_STEP_TIMEOUT_SECONDS:-7200}"
PYTHON_TIMEOUT_SECONDS="${PYTHON_TIMEOUT_SECONDS:-600}"

run_init "pipeline" "$PIPELINE_DIR_ABS" "$AQUI/run_pipeline.sh"
run_acquire_lock "$DIR_DADOS_ABS" "aermet"
run_acquire_lock "$DIR_AERMOD_ABS" "aermod"
run_acquire_lock "$DIR_RLINE_ABS" "rline"

if [[ ! -x "$BIN_AERMET_ABS" ]]; then
    run_fail 69 "ERRO: binario AERMET nao encontrado em $BIN_AERMET_ABS; execute 'make models' ou defina BIN_AERMET"
fi
if [[ ! -x "$BIN_AERMOD_ABS" ]]; then
    run_fail 69 "ERRO: binario AERMOD nao encontrado em $BIN_AERMOD_ABS; execute 'make models' ou defina BIN_AERMOD"
fi
if [[ ! -x "$BIN_RLINE_ABS" ]]; then
    run_fail 69 "ERRO: binario RLINE corrigido nao encontrado em $BIN_RLINE_ABS; execute 'make rline-release' ou defina BIN_RLINE"
fi
for required_file in \
    "$DIR_DADOS_ABS/ONSITE_S1.INP" \
    "$DIR_DADOS_ABS/ONSITE_S2.INP" \
    "$INP_AERMOD_ABS" \
    "$DIR_RLINE_ABS/Line_Source_Inputs.txt" \
    "$DIR_RLINE_ABS/Source_Road.txt" \
    "$DIR_RLINE_ABS/Receptor_Road.txt" \
    "$PIPELINE_DIR_ABS/scripts/gerar_dados_onsite.py" \
    "$PIPELINE_DIR_ABS/scripts/_pipeline_common.py" \
    "$PIPELINE_DIR_ABS/scripts/compare_aermod_rline.py" \
    "$PIPELINE_DIR_ABS/scripts/plot_conc_aermod_rline.py" \
    "$PIPELINE_DIR_ABS/scripts/plot_compare_aermod_rline.py"; do
    if ! require_nonempty_file "$required_file"; then
        run_fail 66 "ERRO: input do pipeline ausente ou vazio: $required_file"
    fi
    run_add_input "$required_file"
done
if [[ ! -d "$RAIZ/rline_pipeline" ]]; then
    run_fail 66 "ERRO: pacote de analise ausente: $RAIZ/rline_pipeline"
fi
run_add_input "$RAIZ/rline_pipeline"

STAGED_PIPELINE="$RUN_WORKSPACE/Caso_Pipeline"
STAGED_DADOS="$STAGED_PIPELINE/dados_aermet"
STAGED_AERMOD="$STAGED_PIPELINE/rodada_aermod"
STAGED_RLINE="$STAGED_PIPELINE/rodada_rline"
STAGED_GRAFICOS="$STAGED_PIPELINE/graficos"
STAGED_SCRIPTS="$STAGED_PIPELINE/scripts"
STAGED_CONTROLS="$STAGED_PIPELINE/controles_aermod"
mkdir -p -- "$STAGED_DADOS" "$STAGED_AERMOD" "$STAGED_RLINE" \
    "$STAGED_GRAFICOS" "$STAGED_SCRIPTS" "$STAGED_CONTROLS"
if ! copy_tree_without_runtime "$DIR_DADOS_ABS" "$STAGED_DADOS"; then
    run_fail 73 "ERRO: falha ao preparar inputs AERMET no staging"
fi
if ! copy_tree_without_runtime "$DIR_RLINE_ABS" "$STAGED_RLINE"; then
    run_fail 73 "ERRO: falha ao preparar inputs RLINE no staging"
fi
rm -f -- "$STAGED_DADOS/ONSITE.MET" "$STAGED_DADOS/ONSITE.SFC" "$STAGED_DADOS/ONSITE.PFL" \
    "$STAGED_DADOS/ONSITE_QAOUT.TXT" "$STAGED_DADOS/ONSITE_S1_REPORT.TXT" \
    "$STAGED_DADOS/ONSITE_S2_REPORT.RPT"
rm -f -- "$STAGED_RLINE"/Output_*_Numerical*.csv
CONTROL_NAME="$(basename -- "$INP_AERMOD_ABS")"
CONTROL_STEM="${CONTROL_NAME%.*}"
cp -f -- "$INP_AERMOD_ABS" "$STAGED_CONTROLS/$CONTROL_NAME"
for python_name in gerar_dados_onsite.py _pipeline_common.py compare_aermod_rline.py \
    plot_conc_aermod_rline.py plot_compare_aermod_rline.py; do
    cp -f -- "$PIPELINE_DIR_ABS/scripts/$python_name" "$STAGED_SCRIPTS/$python_name"
done
cp -a -- "$RAIZ/rline_pipeline" "$RUN_WORKSPACE/rline_pipeline"

run_log "=== PIPELINE AERMET -> AERMOD/RLINE ==="
run_log "BIN AERMET: $BIN_AERMET_ABS"
run_log "BIN AERMOD: $BIN_AERMOD_ABS"
run_log "BIN RLINE : $BIN_RLINE_ABS"

if run_timed_command "$STAGED_PIPELINE" "$PYTHON_TIMEOUT_SECONDS" \
    "geracao de ONSITE.MET" python3 "$STAGED_SCRIPTS/gerar_dados_onsite.py"; then
    :
else
    step_status=$?
    run_fail_command "geracao de ONSITE.MET" "$step_status"
fi
if ! require_file_contains "$STAGED_DADOS/ONSITE.MET" \
    '^[[:space:]]*[0-9]+[[:space:]]+[0-9]+'; then
    run_fail 65 "ERRO: gerador nao produziu ONSITE.MET novo com registros validos"
fi

if run_child_command "$RAIZ" "$STEP_TIMEOUT_SECONDS" "wrapper AERMET" \
    env RUN_LOG_DIR="$PIPELINE_DIR_ABS/logs" RUN_TIMEOUT_SECONDS="$STEP_TIMEOUT_SECONDS" \
    bash "$AQUI/run_aermet.sh" \
    "$STAGED_DADOS" "$BIN_AERMET_ABS"; then
    :
else
    step_status=$?
    run_fail_command "wrapper AERMET" "$step_status"
fi
if run_child_command "$RAIZ" "$STEP_TIMEOUT_SECONDS" "wrapper AERMOD" \
    env RUN_LOG_DIR="$PIPELINE_DIR_ABS/logs" RUN_TIMEOUT_SECONDS="$STEP_TIMEOUT_SECONDS" \
    bash "$AQUI/run_aermod.sh" \
    "$STAGED_AERMOD" "$BIN_AERMOD_ABS" "$STAGED_CONTROLS/$CONTROL_NAME" \
    "$STAGED_DADOS"; then
    :
else
    step_status=$?
    run_fail_command "wrapper AERMOD" "$step_status"
fi
if run_child_command "$RAIZ" "$STEP_TIMEOUT_SECONDS" "wrapper RLINE" \
    env RUN_LOG_DIR="$PIPELINE_DIR_ABS/logs" RUN_TIMEOUT_SECONDS="$STEP_TIMEOUT_SECONDS" \
    bash "$AQUI/run_rline.sh" \
    "$STAGED_RLINE" "$BIN_RLINE_ABS" "$STAGED_DADOS/ONSITE.SFC"; then
    :
else
    step_status=$?
    run_fail_command "wrapper RLINE" "$step_status"
fi

if ! require_nonempty_file "$STAGED_RLINE/Output_Road_Numerical.csv"; then
    run_fail 65 "ERRO: scripts de analise requerem Output_Road_Numerical.csv, mas o RLINE nao o gerou"
fi
if run_timed_command "$STAGED_PIPELINE" "$PYTHON_TIMEOUT_SECONDS" \
    "comparacao AERMOD/RLINE" python3 "$STAGED_SCRIPTS/compare_aermod_rline.py"; then
    :
else
    step_status=$?
    run_fail_command "comparacao AERMOD/RLINE" "$step_status"
fi
if run_timed_command "$STAGED_AERMOD" "$PYTHON_TIMEOUT_SECONDS" \
    "grafico de concentracao" python3 "$STAGED_SCRIPTS/plot_conc_aermod_rline.py"; then
    :
else
    step_status=$?
    run_fail_command "grafico de concentracao" "$step_status"
fi
if run_timed_command "$STAGED_PIPELINE" "$PYTHON_TIMEOUT_SECONDS" \
    "grafico comparativo" python3 "$STAGED_SCRIPTS/plot_compare_aermod_rline.py"; then
    :
else
    step_status=$?
    run_fail_command "grafico comparativo" "$step_status"
fi
for graph_name in conc_periodo_rline.png conc_aermod_vs_rline.png; do
    if ! require_png "$STAGED_GRAFICOS/$graph_name"; then
        run_fail 65 "ERRO: pipeline nao gerou PNG valido: $graph_name"
    fi
done

AERMET_PUBLISH=(ONSITE.MET ONSITE_S1_REPORT.TXT ONSITE_QAOUT.TXT ONSITE_S2_REPORT.RPT ONSITE.SFC ONSITE.PFL)
for optional_name in ONSITE_S1_MESSAGE.TXT ONSITE_S2_MESSAGE.TXT; do
    if [[ -s "$STAGED_DADOS/$optional_name" ]]; then
        AERMET_PUBLISH+=("$optional_name")
    fi
done
AERMOD_PUBLISH=("$CONTROL_NAME" ONSITE.SFC ONSITE.PFL "$CONTROL_STEM.out" CONC_PLOT.PLT)
RLINE_PUBLISH=(ONSITE.SFC)
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
for rline_output in "${rline_outputs[@]}"; do
    RLINE_PUBLISH+=("$(basename -- "$rline_output")")
done

PIPELINE_PUBLISH=()
for relative in "${AERMET_PUBLISH[@]}"; do
    PIPELINE_PUBLISH+=("$STAGED_DADOS/$relative" "$DIR_DADOS_ABS/$relative")
done
for relative in "${AERMOD_PUBLISH[@]}"; do
    PIPELINE_PUBLISH+=("$STAGED_AERMOD/$relative" "$DIR_AERMOD_ABS/$relative")
done
for relative in "${RLINE_PUBLISH[@]}"; do
    PIPELINE_PUBLISH+=("$STAGED_RLINE/$relative" "$DIR_RLINE_ABS/$relative")
done
PIPELINE_PUBLISH+=(
    "$STAGED_GRAFICOS/conc_periodo_rline.png" "$DIR_GRAFICOS_ABS/conc_periodo_rline.png"
    "$STAGED_GRAFICOS/conc_aermod_vs_rline.png" "$DIR_GRAFICOS_ABS/conc_aermod_vs_rline.png"
)

if publish_mapped_files "${PIPELINE_PUBLISH[@]}"; then
    :
else
    publish_status=$?
    run_fail "$publish_status" "ERRO: falha ao publicar o conjunto de outputs do pipeline"
fi

FINAL_OUTPUTS=(
    "$DIR_DADOS_ABS/ONSITE.SFC"
    "$DIR_DADOS_ABS/ONSITE.PFL"
    "$DIR_AERMOD_ABS/$CONTROL_STEM.out"
    "$DIR_AERMOD_ABS/CONC_PLOT.PLT"
    "$DIR_GRAFICOS_ABS/conc_periodo_rline.png"
    "$DIR_GRAFICOS_ABS/conc_aermod_vs_rline.png"
)
for rline_output in "${rline_outputs[@]}"; do
    FINAL_OUTPUTS+=("$DIR_RLINE_ABS/$(basename -- "$rline_output")")
done
run_set_outputs "${FINAL_OUTPUTS[@]}"
run_log "=== PIPELINE CONCLUIDO E PUBLICADO COM SUCESSO ==="
run_log ">>> Log exclusivo: $RUN_LOG"
run_mark_success
