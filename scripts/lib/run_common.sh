#!/usr/bin/env bash

# Shared runtime support for the model wrappers. Callers must define RAIZ before
# sourcing this file and must call run_init before using the remaining helpers.

RUN_LIB_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RUN_SCRIPTS_DIR="$(cd -- "$RUN_LIB_DIR/.." && pwd)"
RUN_MANIFEST_WRITER="${RUN_MANIFEST_WRITER:-$RUN_SCRIPTS_DIR/write_run_manifest.py}"

resolve_project_path() {
    local path="$1"
    if [[ "$path" = /* ]]; then
        realpath -m -- "$path"
    else
        realpath -m -- "$RAIZ/$path"
    fi
}

resolve_path_from() {
    local base="$1"
    local path="$2"
    if [[ "$path" = /* ]]; then
        realpath -m -- "$path"
    else
        realpath -m -- "$base/$path"
    fi
}

run_log() {
    printf '%s\n' "$*" | tee -a -- "$RUN_LOG"
}

run_error() {
    printf '%s\n' "$*" | tee -a -- "$RUN_LOG" >&2
}

_restore_run_signal_traps() {
    trap '_run_signal_handler 129 HUP' HUP
    trap '_run_signal_handler 130 INT' INT
    trap '_run_signal_handler 143 TERM' TERM
}

_defer_run_signal() {
    local code="$1"
    local signal_name="$2"
    if [[ -z "${RUN_PENDING_SIGNAL_CODE:-}" ]]; then
        RUN_PENDING_SIGNAL_CODE="$code"
        RUN_PENDING_SIGNAL_NAME="$signal_name"
    fi
}

_enter_run_critical_section() {
    trap '_defer_run_signal 129 HUP' HUP
    trap '_defer_run_signal 130 INT' INT
    trap '_defer_run_signal 143 TERM' TERM
}

_leave_run_critical_section() {
    local pending_code="${RUN_PENDING_SIGNAL_CODE:-}"
    local pending_name="${RUN_PENDING_SIGNAL_NAME:-}"
    _restore_run_signal_traps
    if [[ -n "$pending_code" ]]; then
        RUN_PENDING_SIGNAL_CODE=""
        RUN_PENDING_SIGNAL_NAME=""
        _run_signal_handler "$pending_code" "$pending_name"
    fi
}

_capture_git_state() {
    local status_output
    RUN_GIT_COMMIT=""
    RUN_GIT_DIRTY="unknown"

    if command -v git >/dev/null 2>&1; then
        if RUN_GIT_COMMIT="$(git -C "$RAIZ" rev-parse HEAD 2>/dev/null)"; then
            if status_output="$(git -C "$RAIZ" status --porcelain --untracked-files=normal 2>/dev/null)"; then
                if [[ -n "$status_output" ]]; then
                    RUN_GIT_DIRTY="true"
                else
                    RUN_GIT_DIRTY="false"
                fi
            fi
        fi
    fi
}

run_init() {
    local component="$1"
    local destination="$2"
    local executable="${3:-}"
    local requested_log_dir="${RUN_LOG_DIR:-}"
    local workspace_parent
    local timestamp

    RUN_COMPONENT="$component"
    RUN_STARTED_NS="$(date +%s%N)"
    RUN_STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    RUN_STATUS="running"
    RUN_EXIT_CODE=""
    RUN_EXECUTABLE=""
    RUN_WORKSPACE=""
    RUN_PUBLISH_DIR=""
    RUN_PUBLISH_TARGETS=()
    RUN_PUBLISH_BACKUPS=()
    RUN_PUBLISH_STAGED=()
    RUN_PUBLISH_INSTALLED=0
    RUN_LOCK_FDS=()
    RUN_LOCK_FILES=()
    RUN_PENDING_SIGNAL_CODE=""
    RUN_PENDING_SIGNAL_NAME=""
    RUN_ACTIVE_MODEL_PID=""
    RUN_ACTIVE_MODEL_PGID=""
    RUN_ACTIVE_CHILD_PID=""
    RUN_ACTIVE_TIMER_PID=""
    RUN_ACTIVE_TIMER_PGID=""
    RUN_LAST_TIMED_OUT=0
    RUN_LAST_EXIT_CODE=0
    RUN_COMMAND_INDEX=0
    RUN_INPUTS=()
    RUN_OUTPUTS=()
    RUN_COMMAND_RESULTS=()

    _capture_git_state

    if ! RUN_DESTINATION="$(resolve_project_path "$destination")"; then
        printf 'ERRO: nao foi possivel resolver o destino: %s\n' "$destination" >&2
        exit 72
    fi
    if [[ -n "$executable" ]]; then
        if ! RUN_EXECUTABLE="$(resolve_project_path "$executable")"; then
            printf 'ERRO: nao foi possivel resolver o executavel: %s\n' "$executable" >&2
            exit 72
        fi
    fi
    if ! mkdir -p -- "$RUN_DESTINATION"; then
        printf 'ERRO: nao foi possivel criar o destino: %s\n' "$RUN_DESTINATION" >&2
        exit 73
    fi

    if [[ -n "$requested_log_dir" ]]; then
        if ! RUN_LOG_DIR="$(resolve_project_path "$requested_log_dir")"; then
            printf 'ERRO: nao foi possivel resolver o diretorio de logs: %s\n' "$requested_log_dir" >&2
            exit 72
        fi
    else
        RUN_LOG_DIR="$RUN_DESTINATION/logs"
    fi
    if ! mkdir -p -- "$RUN_LOG_DIR"; then
        printf 'ERRO: nao foi possivel criar o diretorio de logs: %s\n' "$RUN_LOG_DIR" >&2
        exit 73
    fi

    timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
    if ! RUN_LOG="$(mktemp -- "$RUN_LOG_DIR/${component}-${timestamp}-XXXXXX.log")"; then
        printf 'ERRO: nao foi possivel criar log exclusivo em %s\n' "$RUN_LOG_DIR" >&2
        exit 73
    fi
    RUN_ID="$(basename -- "${RUN_LOG%.log}")"
    RUN_MANIFEST="${RUN_LOG%.log}.manifest.json"

    trap '_run_exit_handler $?' EXIT
    _restore_run_signal_traps

    for required_command in flock sync; do
        if ! command -v "$required_command" >/dev/null 2>&1; then
            run_fail 69 "ERRO: comando obrigatorio nao encontrado: $required_command"
        fi
    done
    run_acquire_lock "$RUN_DESTINATION" "$component"

    workspace_parent="$(dirname -- "$RUN_DESTINATION")"
    if ! RUN_WORKSPACE="$(mktemp -d -- "$workspace_parent/.${component}-workspace.XXXXXX")"; then
        run_fail 73 "ERRO: nao foi possivel criar workspace exclusivo em $workspace_parent"
    fi

    printf 'run_id=%s\ncomponent=%s\ndestination=%s\nworkspace=%s\n' \
        "$RUN_ID" "$RUN_COMPONENT" "$RUN_DESTINATION" "$RUN_WORKSPACE" >> "$RUN_LOG"
}

run_acquire_lock() {
    local destination="$1"
    local component="$2"
    local lock_file
    local lock_fd
    local existing

    if ! destination="$(resolve_project_path "$destination")"; then
        run_fail 72 "ERRO: nao foi possivel resolver destino de lock: $destination"
    fi
    if ! mkdir -p -- "$destination"; then
        run_fail 73 "ERRO: nao foi possivel criar destino de lock: $destination"
    fi
    lock_file="$destination/.${component}.lock"
    for existing in "${RUN_LOCK_FILES[@]}"; do
        if [[ "$existing" == "$lock_file" ]]; then
            return 0
        fi
    done
    if [[ -L "$lock_file" ]]; then
        run_fail 65 "ERRO: lock nao pode ser link simbolico: $lock_file"
    fi
    if ! exec {lock_fd}>"$lock_file"; then
        run_fail 73 "ERRO: nao foi possivel abrir o lock: $lock_file"
    fi
    if ! flock -n "$lock_fd"; then
        eval "exec ${lock_fd}>&-"
        run_fail 75 "ERRO: ja existe uma execucao de $component no destino: $destination"
    fi
    RUN_LOCK_FDS+=("$lock_fd")
    RUN_LOCK_FILES+=("$lock_file")
}

_close_inherited_lock_fds() {
    local lock_fd
    for lock_fd in "${RUN_LOCK_FDS[@]}"; do
        eval "exec ${lock_fd}>&-"
    done
}

run_add_input() {
    RUN_INPUTS+=("$1")
}

run_add_output() {
    RUN_OUTPUTS+=("$1")
}

run_set_outputs() {
    RUN_OUTPUTS=("$@")
}

run_mark_success() {
    RUN_STATUS="success"
    RUN_EXIT_CODE=0
}

run_fail() {
    local code="$1"
    local message="$2"
    local status="${3:-failed}"
    if (( code == 0 )); then
        code=1
    fi
    RUN_STATUS="$status"
    RUN_EXIT_CODE="$code"
    run_error "$message"
    exit "$code"
}

run_fail_command() {
    local label="$1"
    local code="$2"
    if (( RUN_LAST_TIMED_OUT == 1 )); then
        run_fail "$code" "ERRO: timeout executando $label; grupo de processos encerrado (log: $RUN_LOG)" "timeout"
    fi
    if (( code == 125 )); then
        run_fail "$code" "ERRO: $label deixou processos ativos; grupo encerrado (log: $RUN_LOG)"
    fi
    run_fail "$code" "ERRO: $label terminou com exit code $code (log: $RUN_LOG)"
}

validate_timeout_value() {
    local value="$1"
    [[ "$value" =~ ^[0-9]+([.][0-9]+)?$ ]]
}

_process_group_alive() {
    local pgid="$1"
    [[ -n "$pgid" ]] && kill -0 -- "-$pgid" 2>/dev/null
}

_terminate_process_group() {
    local pgid="$1"
    local grace="$2"
    local label="${3:-processo}"

    if ! _process_group_alive "$pgid"; then
        return 0
    fi
    printf 'Encerrando grupo %s (%s) com TERM\n' "$pgid" "$label" >> "$RUN_LOG"
    if kill -TERM -- "-$pgid" 2>/dev/null; then
        :
    fi
    sleep "$grace"
    if _process_group_alive "$pgid"; then
        printf 'Grupo %s ainda ativo; enviando KILL\n' "$pgid" >> "$RUN_LOG"
        if kill -KILL -- "-$pgid" 2>/dev/null; then
            :
        fi
    fi
}

_stop_active_timer() {
    local ignored_status
    if [[ -z "$RUN_ACTIVE_TIMER_PID" ]]; then
        return 0
    fi
    if _process_group_alive "$RUN_ACTIVE_TIMER_PGID"; then
        if kill -TERM -- "-$RUN_ACTIVE_TIMER_PGID" 2>/dev/null; then
            :
        fi
    fi
    if wait "$RUN_ACTIVE_TIMER_PID"; then
        ignored_status=0
    else
        ignored_status=$?
    fi
    RUN_ACTIVE_TIMER_PID=""
    RUN_ACTIVE_TIMER_PGID=""
    return 0
}

run_timed_command() {
    local workdir="$1"
    local timeout_seconds="$2"
    local label="$3"
    shift 3
    local grace_seconds="${RUN_KILL_GRACE_SECONDS:-5}"
    local marker
    local command_started_ns
    local command_finished_ns
    local command_duration_ns
    local model_status
    local remaining_group=0
    local timer_script
    local command_display

    if ! validate_timeout_value "$timeout_seconds"; then
        run_fail 64 "ERRO: timeout invalido para $label: $timeout_seconds"
    fi
    if ! validate_timeout_value "$grace_seconds"; then
        run_fail 64 "ERRO: RUN_KILL_GRACE_SECONDS invalido: $grace_seconds"
    fi
    if ! command -v setsid >/dev/null 2>&1; then
        run_fail 69 "ERRO: comando obrigatorio nao encontrado: setsid"
    fi
    if [[ ! -d "$workdir" ]]; then
        run_fail 72 "ERRO: diretorio de execucao nao encontrado para $label: $workdir"
    fi
    if (( $# == 0 )); then
        run_fail 64 "ERRO: comando vazio para $label"
    fi

    RUN_COMMAND_INDEX=$((RUN_COMMAND_INDEX + 1))
    marker="$RUN_WORKSPACE/.timeout-${RUN_COMMAND_INDEX}"
    command_started_ns="$(date +%s%N)"
    printf -v command_display '%q ' "$@"
    command_display="${command_display% }"
    run_log ">>> $label (timeout ${timeout_seconds}s)"

    (
        if ! cd -- "$workdir"; then
            exit 72
        fi
        _close_inherited_lock_fds
        exec setsid --wait "$@"
    ) >> "$RUN_LOG" 2>&1 &
    RUN_ACTIVE_MODEL_PID=$!
    RUN_ACTIVE_MODEL_PGID="$RUN_ACTIVE_MODEL_PID"

    timer_script='
sleep "$1"
if kill -0 -- "-$2" 2>/dev/null; then
    : > "$4"
    printf "Timeout de %ss: TERM para o grupo %s (%s)\\n" "$1" "$2" "$6" >> "$5"
    if kill -TERM -- "-$2" 2>/dev/null; then :; fi
    sleep "$3"
    if kill -0 -- "-$2" 2>/dev/null; then
        printf "Grace period de %ss esgotado: KILL para o grupo %s\\n" "$3" "$2" >> "$5"
        if kill -KILL -- "-$2" 2>/dev/null; then :; fi
    fi
fi'
    (
        _close_inherited_lock_fds
        exec setsid --wait bash -c "$timer_script" run-timer \
            "$timeout_seconds" "$RUN_ACTIVE_MODEL_PGID" "$grace_seconds" \
            "$marker" "$RUN_LOG" "$label"
    ) >> "$RUN_LOG" 2>&1 &
    RUN_ACTIVE_TIMER_PID=$!
    RUN_ACTIVE_TIMER_PGID="$RUN_ACTIVE_TIMER_PID"

    if wait "$RUN_ACTIVE_MODEL_PID"; then
        model_status=0
    else
        model_status=$?
    fi

    _stop_active_timer

    if [[ -e "$marker" ]]; then
        RUN_LAST_TIMED_OUT=1
    else
        RUN_LAST_TIMED_OUT=0
    fi

    if _process_group_alive "$RUN_ACTIVE_MODEL_PGID"; then
        remaining_group=1
        _terminate_process_group "$RUN_ACTIVE_MODEL_PGID" "$grace_seconds" "$label"
    fi
    RUN_ACTIVE_MODEL_PID=""
    RUN_ACTIVE_MODEL_PGID=""

    if (( RUN_LAST_TIMED_OUT == 1 )); then
        model_status=124
    elif (( remaining_group == 1 && model_status == 0 )); then
        model_status=125
    fi

    command_finished_ns="$(date +%s%N)"
    command_duration_ns=$((command_finished_ns - command_started_ns))
    RUN_LAST_EXIT_CODE="$model_status"
    RUN_COMMAND_RESULTS+=("${label}"$'\t'"${model_status}"$'\t'"${RUN_LAST_TIMED_OUT}"$'\t'"${command_duration_ns}"$'\t'"${workdir}"$'\t'"${timeout_seconds}"$'\t'"${command_display}")
    return "$model_status"
}

run_child_command() {
    local workdir="$1"
    local child_timeout_seconds="$2"
    local label="$3"
    shift 3
    local command_started_ns
    local command_finished_ns
    local command_duration_ns
    local child_status
    local command_display

    if ! validate_timeout_value "$child_timeout_seconds"; then
        run_fail 64 "ERRO: timeout invalido para $label: $child_timeout_seconds"
    fi
    if [[ ! -d "$workdir" ]]; then
        run_fail 72 "ERRO: diretorio de execucao nao encontrado para $label: $workdir"
    fi
    if (( $# == 0 )); then
        run_fail 64 "ERRO: comando vazio para $label"
    fi

    command_started_ns="$(date +%s%N)"
    printf -v command_display '%q ' "$@"
    command_display="${command_display% }"
    run_log ">>> $label (timeout administrado pelo wrapper filho: ${child_timeout_seconds}s)"
    (
        if ! cd -- "$workdir"; then
            exit 72
        fi
        _close_inherited_lock_fds
        exec "$@"
    ) >> "$RUN_LOG" 2>&1 &
    RUN_ACTIVE_CHILD_PID=$!
    if wait "$RUN_ACTIVE_CHILD_PID"; then
        child_status=0
    else
        child_status=$?
    fi
    RUN_ACTIVE_CHILD_PID=""

    if (( child_status == 124 )); then
        RUN_LAST_TIMED_OUT=1
    else
        RUN_LAST_TIMED_OUT=0
    fi
    RUN_LAST_EXIT_CODE="$child_status"
    command_finished_ns="$(date +%s%N)"
    command_duration_ns=$((command_finished_ns - command_started_ns))
    RUN_COMMAND_RESULTS+=("${label}"$'\t'"${child_status}"$'\t'"${RUN_LAST_TIMED_OUT}"$'\t'"${command_duration_ns}"$'\t'"${workdir}"$'\t'"${child_timeout_seconds}"$'\t'"${command_display}")
    return "$child_status"
}

require_nonempty_file() {
    local file="$1"
    [[ -f "$file" && ! -L "$file" && -s "$file" ]]
}

require_file_contains() {
    local file="$1"
    local pattern="$2"
    [[ -s "$file" && ! -L "$file" ]] && grep -Eiq -- "$pattern" "$file"
}

require_png() {
    local file="$1"
    local signature
    if [[ ! -s "$file" || -L "$file" ]]; then
        return 1
    fi
    if ! signature="$(od -An -tx1 -N8 -- "$file" | tr -d ' \n')"; then
        return 1
    fi
    [[ "$signature" == "89504e470d0a1a0a" ]]
}

copy_tree_without_runtime() {
    local source="$1"
    local target="$2"
    local restore_dotglob=0
    local item
    local base

    if [[ ! -d "$source" ]]; then
        return 66
    fi
    if ! mkdir -p -- "$target"; then
        return 73
    fi
    if shopt -q dotglob; then
        :
    else
        shopt -s dotglob
        restore_dotglob=1
    fi
    for item in "$source"/*; do
        if [[ ! -e "$item" && ! -L "$item" ]]; then
            continue
        fi
        base="$(basename -- "$item")"
        case "$base" in
            logs|.*.lock|.publish.*|.*-workspace.*)
                continue
                ;;
        esac
        if [[ -L "$item" ]] || { [[ -d "$item" ]] && find "$item" -type l -print -quit | read -r; }; then
            if (( restore_dotglob == 1 )); then
                shopt -u dotglob
            fi
            return 65
        fi
        if ! cp -a -- "$item" "$target/"; then
            if (( restore_dotglob == 1 )); then
                shopt -u dotglob
            fi
            return 73
        fi
    done
    if (( restore_dotglob == 1 )); then
        shopt -u dotglob
    fi
}

_safe_relative_path() {
    local path="$1"
    local component
    local components=()
    [[ -n "$path" && "$path" != /* && "$path" != */ && "$path" != *$'\n'* ]] || return 1
    IFS='/' read -r -a components <<< "$path"
    for component in "${components[@]}"; do
        [[ -n "$component" && "$component" != "." && "$component" != ".." && "$component" != .* ]] || return 1
    done
}

publish_files() {
    local source="$1"
    local destination="$2"
    shift 2
    local relative
    local mappings=()

    if (( $# == 0 )); then
        return 0
    fi
    for relative in "$@"; do
        if ! _safe_relative_path "$relative"; then
            printf 'Caminho de publicacao inseguro: %s\n' "$relative" >> "$RUN_LOG"
            return 64
        fi
        mappings+=("$source/$relative" "$destination/$relative")
    done
    publish_mapped_files "${mappings[@]}"
}

publish_mapped_files() {
    local source
    local target
    local target_parent
    local backup_path
    local staged_path
    local target_name
    local index
    local mappings=("$@")
    local -A seen_targets=()

    if (( ${#mappings[@]} == 0 || ${#mappings[@]} % 2 != 0 )); then
        return 64
    fi
    if [[ -n "$RUN_PUBLISH_DIR" ]]; then
        printf 'Ja existe uma publicacao pendente nesta execucao\n' >> "$RUN_LOG"
        return 70
    fi
    if ! RUN_PUBLISH_DIR="$(mktemp -d -- "$RUN_WORKSPACE/.publish.${RUN_ID}.XXXXXX")"; then
        return 73
    fi
    RUN_PUBLISH_TARGETS=()
    RUN_PUBLISH_BACKUPS=()
    RUN_PUBLISH_STAGED=()
    RUN_PUBLISH_INSTALLED=0

    for ((index = 0; index < ${#mappings[@]}; index += 2)); do
        source="${mappings[$index]}"
        target="${mappings[$((index + 1))]}"
        if [[ "$source" != /* || "$target" != /* ]]; then
            printf 'Mapeamento de publicacao deve usar caminhos absolutos: %s -> %s\n' \
                "$source" "$target" >> "$RUN_LOG"
            _discard_prepared_publish
            return 64
        fi
        if [[ -L "$source" || ! -f "$source" ]]; then
            printf 'Artefato deve ser arquivo regular, sem link simbolico: %s\n' "$source" >> "$RUN_LOG"
            _discard_prepared_publish
            return 66
        fi
        if ! target="$(realpath -m -- "$target")"; then
            _discard_prepared_publish
            return 72
        fi
        if [[ -n "${seen_targets[$target]:-}" ]]; then
            printf 'Destino de publicacao duplicado: %s\n' "$target" >> "$RUN_LOG"
            _discard_prepared_publish
            return 64
        fi
        seen_targets[$target]=1
        target_parent="$(dirname -- "$target")"
        target_name="$(basename -- "$target")"
        if ! mkdir -p -- "$target_parent"; then
            _discard_prepared_publish
            return 73
        fi
        if [[ -L "$target" || ( -e "$target" && ! -f "$target" ) ]]; then
            printf 'Destino deve ser arquivo regular, sem link simbolico: %s\n' "$target" >> "$RUN_LOG"
            _discard_prepared_publish
            return 65
        fi
        if ! staged_path="$(mktemp -- "$target_parent/.${target_name}.publish.${RUN_ID}.XXXXXX")"; then
            _discard_prepared_publish
            return 73
        fi
        if ! cp -p -- "$source" "$staged_path" || ! sync -f -- "$staged_path"; then
            rm -f -- "$staged_path"
            _discard_prepared_publish
            return 73
        fi
        backup_path=""
        if [[ -e "$target" ]]; then
            if ! backup_path="$(mktemp -- "$target_parent/.${target_name}.backup.${RUN_ID}.XXXXXX")"; then
                rm -f -- "$staged_path"
                _discard_prepared_publish
                return 73
            fi
            if ! cp -p -- "$target" "$backup_path" || ! sync -f -- "$backup_path"; then
                rm -f -- "$staged_path" "$backup_path"
                _discard_prepared_publish
                return 73
            fi
        fi
        RUN_PUBLISH_TARGETS+=("$target")
        RUN_PUBLISH_BACKUPS+=("$backup_path")
        RUN_PUBLISH_STAGED+=("$staged_path")
    done

    _enter_run_critical_section
    for ((index = 0; index < ${#RUN_PUBLISH_TARGETS[@]}; index++)); do
        target="${RUN_PUBLISH_TARGETS[$index]}"
        staged_path="${RUN_PUBLISH_STAGED[$index]}"
        if ! mv -f -- "$staged_path" "$target"; then
            if ! _rollback_publish; then
                printf 'ERRO: rollback incompleto; backups preservados para recuperacao manual\n' >> "$RUN_LOG"
            fi
            _leave_run_critical_section
            return 73
        fi
        RUN_PUBLISH_INSTALLED=$((RUN_PUBLISH_INSTALLED + 1))
        if ! sync -f -- "$(dirname -- "$target")"; then
            if ! _rollback_publish; then
                printf 'ERRO: rollback incompleto; backups preservados para recuperacao manual\n' >> "$RUN_LOG"
            fi
            _leave_run_critical_section
            return 73
        fi
    done

    _leave_run_critical_section
    return 0
}

_commit_publish() {
    local path
    local cleanup_status=0
    for path in "${RUN_PUBLISH_STAGED[@]}" "${RUN_PUBLISH_BACKUPS[@]}"; do
        if [[ -n "$path" ]] && ! rm -f -- "$path"; then
            cleanup_status=73
        fi
    done
    if [[ -n "$RUN_PUBLISH_DIR" && -d "$RUN_PUBLISH_DIR" ]] && ! rmdir -- "$RUN_PUBLISH_DIR"; then
        cleanup_status=73
    fi
    RUN_PUBLISH_DIR=""
    RUN_PUBLISH_TARGETS=()
    RUN_PUBLISH_BACKUPS=()
    RUN_PUBLISH_STAGED=()
    RUN_PUBLISH_INSTALLED=0
    return "$cleanup_status"
}

_rollback_publish() {
    local index
    local target
    local backup_path
    local staged_path
    local rollback_status=0

    if [[ -z "$RUN_PUBLISH_DIR" ]]; then
        return 0
    fi
    for ((index = RUN_PUBLISH_INSTALLED - 1; index >= 0; index--)); do
        target="${RUN_PUBLISH_TARGETS[$index]}"
        backup_path="${RUN_PUBLISH_BACKUPS[$index]}"
        if [[ -n "$backup_path" && -f "$backup_path" ]]; then
            if ! mv -f -- "$backup_path" "$target"; then
                rollback_status=73
                continue
            fi
        elif ! rm -f -- "$target"; then
            rollback_status=73
            continue
        fi
        sync -f -- "$(dirname -- "$target")" || rollback_status=73
    done
    for staged_path in "${RUN_PUBLISH_STAGED[@]}"; do
        if [[ -n "$staged_path" ]] && ! rm -f -- "$staged_path"; then
            rollback_status=73
        fi
    done
    if (( rollback_status != 0 )); then
        return "$rollback_status"
    fi
    for backup_path in "${RUN_PUBLISH_BACKUPS[@]}"; do
        if [[ -n "$backup_path" ]]; then
            rm -f -- "$backup_path" || return 73
        fi
    done
    RUN_PUBLISH_TARGETS=()
    RUN_PUBLISH_BACKUPS=()
    RUN_PUBLISH_STAGED=()
    RUN_PUBLISH_INSTALLED=0
    if [[ -n "$RUN_PUBLISH_DIR" && -d "$RUN_PUBLISH_DIR" ]]; then
        rmdir -- "$RUN_PUBLISH_DIR" || return 73
    fi
    RUN_PUBLISH_DIR=""
}

_discard_prepared_publish() {
    local path
    for path in "${RUN_PUBLISH_STAGED[@]}" "${RUN_PUBLISH_BACKUPS[@]}"; do
        if [[ -n "$path" ]]; then
            rm -f -- "$path"
        fi
    done
    RUN_PUBLISH_TARGETS=()
    RUN_PUBLISH_BACKUPS=()
    RUN_PUBLISH_STAGED=()
    RUN_PUBLISH_INSTALLED=0
    if [[ -n "$RUN_PUBLISH_DIR" && -d "$RUN_PUBLISH_DIR" ]]; then
        rmdir -- "$RUN_PUBLISH_DIR" 2>/dev/null || true
    fi
    RUN_PUBLISH_DIR=""
}

_cleanup_active_processes() {
    local ignored_status
    local grace_seconds="${RUN_KILL_GRACE_SECONDS:-5}"

    _stop_active_timer
    if [[ -n "$RUN_ACTIVE_CHILD_PID" ]]; then
        kill -TERM -- "$RUN_ACTIVE_CHILD_PID" 2>/dev/null || true
        if wait "$RUN_ACTIVE_CHILD_PID"; then
            ignored_status=0
        else
            ignored_status=$?
        fi
        RUN_ACTIVE_CHILD_PID=""
    fi
    if [[ -n "$RUN_ACTIVE_MODEL_PGID" ]]; then
        _terminate_process_group "$RUN_ACTIVE_MODEL_PGID" "$grace_seconds" "$RUN_COMPONENT"
    fi
    if [[ -n "$RUN_ACTIVE_MODEL_PID" ]]; then
        if wait "$RUN_ACTIVE_MODEL_PID"; then
            ignored_status=0
        else
            ignored_status=$?
        fi
    fi
    RUN_ACTIVE_MODEL_PID=""
    RUN_ACTIVE_MODEL_PGID=""
}

_write_run_manifest() {
    local finished_ns="$1"
    local exit_code="$2"
    local args
    local item

    args=(
        "$RUN_MANIFEST_WRITER"
        --manifest "$RUN_MANIFEST"
        --repo-root "$RAIZ"
        --run-id "$RUN_ID"
        --component "$RUN_COMPONENT"
        --status "$RUN_STATUS"
        --exit-code "$exit_code"
        --started-at "$RUN_STARTED_AT"
        --started-ns "$RUN_STARTED_NS"
        --finished-ns "$finished_ns"
        --git-commit "$RUN_GIT_COMMIT"
        --git-dirty "$RUN_GIT_DIRTY"
        --log "$RUN_LOG"
        --kill-grace-seconds "${RUN_KILL_GRACE_SECONDS:-5}"
    )
    if [[ -n "$RUN_EXECUTABLE" ]]; then
        args+=(--executable "$RUN_EXECUTABLE")
    fi
    for item in "${RUN_INPUTS[@]}"; do
        args+=(--input "$item")
    done
    for item in "${RUN_OUTPUTS[@]}"; do
        args+=(--output "$item")
    done
    for item in "${RUN_COMMAND_RESULTS[@]}"; do
        args+=(--command-result "$item")
    done
    python3 "${args[@]}"
}

_run_signal_handler() {
    local code="$1"
    local signal_name="$2"
    RUN_STATUS="interrupted"
    RUN_EXIT_CODE="$code"
    printf 'Execucao interrompida por %s\n' "$signal_name" >> "$RUN_LOG"
    exit "$code"
}

_run_exit_handler() {
    local shell_status="$1"
    local final_status
    local finished_ns
    local manifest_status=0
    local rollback_status=0

    trap - EXIT
    _enter_run_critical_section
    set +e
    _cleanup_active_processes

    if [[ -n "$RUN_EXIT_CODE" ]]; then
        final_status="$RUN_EXIT_CODE"
    else
        final_status="$shell_status"
    fi
    if [[ "$RUN_STATUS" == "running" ]]; then
        RUN_STATUS="failed"
        if (( final_status == 0 )); then
            final_status=70
        fi
    fi
    if (( final_status != 0 )); then
        if ! _rollback_publish; then
            rollback_status=73
            final_status=74
            RUN_STATUS="failed"
        fi
    fi

    if [[ -n "${RUN_PENDING_SIGNAL_CODE:-}" ]]; then
        final_status="$RUN_PENDING_SIGNAL_CODE"
        RUN_STATUS="interrupted"
    fi

    finished_ns="$(date +%s%N)"
    if [[ -x "$RUN_MANIFEST_WRITER" || -f "$RUN_MANIFEST_WRITER" ]]; then
        if _write_run_manifest "$finished_ns" "$final_status"; then
            manifest_status=0
        else
            manifest_status=$?
            printf 'ERRO: falha ao escrever manifesto %s (exit code %s)\n' \
                "$RUN_MANIFEST" "$manifest_status" >&2
        fi
    else
        manifest_status=66
        printf 'ERRO: utilitario de manifesto ausente: %s\n' "$RUN_MANIFEST_WRITER" >&2
    fi

    if [[ -n "${RUN_PENDING_SIGNAL_CODE:-}" && "$final_status" == "0" ]]; then
        final_status="$RUN_PENDING_SIGNAL_CODE"
        RUN_STATUS="interrupted"
        if ! _rollback_publish; then
            rollback_status=73
            final_status=74
            RUN_STATUS="failed"
        fi
        finished_ns="$(date +%s%N)"
        if ! _write_run_manifest "$finished_ns" "$final_status"; then
            manifest_status=70
        fi
    fi

    if (( final_status == 0 && manifest_status == 0 )); then
        if ! _commit_publish; then
            printf 'AVISO: outputs publicados, mas temporarios de backup nao foram removidos\n' >&2
        fi
    else
        if ! _rollback_publish; then
            rollback_status=73
            final_status=74
            RUN_STATUS="failed"
        fi
    fi

    if (( rollback_status == 0 )) && [[ -n "$RUN_WORKSPACE" && -d "$RUN_WORKSPACE" ]]; then
        rm -rf -- "$RUN_WORKSPACE"
    fi

    if (( final_status == 0 && manifest_status != 0 )); then
        final_status=70
    fi
    trap '' HUP INT TERM
    exit "$final_status"
}
