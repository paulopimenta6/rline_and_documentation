#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# scripts/run_todos_casos.sh
# Roda o pipeline de todos os casos de uso em casos/ e valida com teste_casos.py
#
# Pre-requisitos:
#   - Pre-processamento feito (Caso_Pipeline/dados_aermet/ONSITE.SFC/.PFL),
#     por exemplo via: bash scripts/run_aermet.sh Caso_Pipeline/dados_aermet \
#          aermet_and_aermod/aermet_source/aermet
#   - Dados dos casos gerados (python3 scripts/gerar_caso.py casos/casoX/config.json)
#
# Uso: bash scripts/run_todos_casos.sh
# ---------------------------------------------------------------------------
set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="$(cd "$AQUI/.." && pwd)"
cd "$RAIZ"

# Gera dados dos casos que ainda nao foram gerados
for cfg in casos/caso*_*/config.json; do
    caso_dir="$(dirname "$cfg")"
    if [ ! -f "$caso_dir/controles_aermod/RLINE_TEST.INP" ]; then
        echo ">>> Gerando dados de $caso_dir"
        python3 "$AQUI/gerar_caso.py" "$cfg"
    fi
done

# Roda o pipeline de cada caso
for cfg in casos/caso*_*/config.json; do
    caso_dir="$(dirname "$cfg")"
    tx="$(python3 -c "import json; print(json.load(open('$cfg')).get('transecto_x',600))")"
    echo ""
    echo "##############################"
    echo "# CASO: $caso_dir  (transecto $tx)"
    echo "##############################"
    bash "$AQUI/run_caso.sh" "$caso_dir" "$tx"
done

# Grafico comparativo geral
echo ""
echo ">>> Gerando comparativo geral entre casos..."
python3 "$AQUI/plot_casos_resumo.py"

# Testes de verificacao
echo ""
echo ">>> Rodando testes de verificacao..."
python3 "$AQUI/teste_casos.py"

echo ""
echo "=== TODOS OS CASOS PROCESSADOS E VALIDADOS ==="
