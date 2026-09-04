#!/usr/bin/env bash
# Diagnostico somente-leitura para quem esta preparando o projeto pela primeira vez.

set -u

missing=0

ok() {
    printf '[OK]    %s\n' "$1"
}

fail() {
    printf '[FALTA] %s\n' "$1"
    missing=1
}

check_command() {
    local command_name="$1"
    local purpose="$2"
    if command -v "$command_name" >/dev/null 2>&1; then
        ok "$command_name — $purpose"
    else
        fail "$command_name — $purpose"
    fi
}

printf '%s\n' '=== Diagnóstico do ambiente RLINE/AERMOD ==='
printf '%s\n' 'Este comando apenas consulta o sistema; ele não instala nem altera arquivos.'
printf '\n'

if [[ "$(uname -s 2>/dev/null || true)" == "Linux" ]]; then
    ok 'Linux detectado'
else
    fail 'Linux não detectado — no Windows, execute dentro do Ubuntu/WSL 2'
fi

check_command git 'baixa e versiona o projeto'
check_command python3 'executa geração, validação e gráficos'
check_command make 'coordena a compilação'
check_command gfortran 'compila AERMET, AERMOD e RLINE'
check_command patch 'aplica as correções locais do RLINE'
check_command sha256sum 'confere a integridade dos fontes'
check_command realpath 'normaliza caminhos usados pelos wrappers'
check_command timeout 'limita comandos externos'
check_command flock 'impede duas gravações simultâneas no mesmo destino'
check_command setsid 'isola processos dos modelos'

if command -v python3 >/dev/null 2>&1; then
    if python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 11))'; then
        ok "Python compatível: $(python3 --version 2>&1)"
    else
        fail "Python 3.11 ou mais recente é necessário; encontrado: $(python3 --version 2>&1)"
    fi
    if python3 -m venv --help >/dev/null 2>&1; then
        ok 'módulo venv — cria o ambiente Python isolado'
    else
        fail 'módulo venv — no Ubuntu, instale python3-venv'
    fi
fi

printf '\n'
if (( missing == 0 )); then
    printf '%s\n' '✅ Ambiente básico pronto. Continue em docs/PRIMEIROS_PASSOS.md.'
    exit 0
fi

printf '%s\n' '❌ Ainda faltam requisitos.'
printf '%s\n' 'No Ubuntu/WSL, consulte a seção “Instalar os pré-requisitos” do guia.'
exit 1
