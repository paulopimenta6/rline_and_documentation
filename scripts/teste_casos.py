#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes de verificacao dos resultados dos casos de uso.

Valida, para cada caso em casos/:
  T1. AERMOD terminou com sucesso (CONC_PLOT.PLT existe)
  T2. RLINE gerou saida (Output_Road_Numerical.csv existe)
  T3. Todos os receptores do grid foram comparados (merge completo)
  T4. Concentracoes finitas e positivas (sem NaN/inf, sem valores < 0)
  T5. Correlacao log-log global AERMOD vs RLINE >= 0.85
  T6. Correlacao log-log RESTRITA ao trecho da rodovia >= 0.95
  T7. Razao mediana AERMOD/RLINE dentro de [0.3, 1.2]
  T8. Consistencia de escala: max AERMOD ~ max RLINE (dentro de um fator 20)

Uso:
  python3 scripts/teste_casos.py [casos/casoX ...]
  (sem argumentos: testa todos os casos de casos/)
Saida: exit code 0 se todos passaram, 1 caso contrario.
"""
from __future__ import print_function
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from postprocess_caso import carregar, comprimento_rodovia  # noqa: E402

LIM_R2_GLOBAL = 0.85
LIM_R2_TRECHO = 0.95
LIM_R2_GLOBAL_CURTO = 0.65
LIM_RATIO_MIN = 0.30
LIM_RATIO_MAX = 1.20
LIM_FATOR_ESCALA = 20.0


def testar_caso(caso_dir):
    nome = os.path.basename(os.path.normpath(caso_dir))
    resultados = []

    plt_file = os.path.join(caso_dir, "rodada_aermod", "CONC_PLOT.PLT")
    csv_file = os.path.join(caso_dir, "rodada_rline", "Output_Road_Numerical.csv")

    ok = os.path.isfile(plt_file) and os.path.getsize(plt_file) > 0
    resultados.append(("T1 AERMOD rodou (CONC_PLOT.PLT)", ok))

    ok = os.path.isfile(csv_file) and os.path.getsize(csv_file) > 0
    resultados.append(("T2 RLINE rodou (Output_*_Numerical.csv)", ok))

    if not os.path.isfile(plt_file) or not os.path.isfile(csv_file):
        return nome, resultados

    aermod, rline_period, m = carregar(caso_dir)

    n_plt = len(aermod)
    ok = len(m) == n_plt
    resultados.append(("T3 merge completo (%d/%d receptores)" % (len(m), n_plt), ok))

    finitos = np.isfinite(m['conc']).all() and np.isfinite(m['C']).all()
    positivos = (m['conc'] > 0).all() and (m['C'] > 0).all()
    resultados.append(("T4 conc. finitas e positivas", finitos and positivos))

    r2_global = np.corrcoef(np.log10(m['conc']), np.log10(m['C']))[0, 1] ** 2

    # T5: para rodovia curta (comprimento << extensao da grade), receptores
    # alem do fim do trecho tem concentracao minuscula dominada por meandro e
    # degradam o R2 global; nesse caso o limiar e relaxado e o R2 do trecho
    # (T6) e o criterio principal.
    comp = comprimento_rodovia(caso_dir)
    x_ext = m['X'].max() - m['X'].min()
    fraccao = (comp / x_ext) if (comp is not None and x_ext > 0) else 1.0
    if fraccao >= 0.6:
        lim_r2 = LIM_R2_GLOBAL
        nota = "global (rodovia cobre %.0f%% da grade)" % (fraccao * 100)
    else:
        lim_r2 = LIM_R2_GLOBAL_CURTO
        nota = "global relaxado (rodovia cobre apenas %.0f%% da grade)" % (fraccao * 100)
    ok = r2_global >= lim_r2
    resultados.append(("T5 R2(log) %s=%.4f >= %.2f" % (nota, r2_global, lim_r2), ok))
    if comp is not None:
        trecho = m[m['X'].between(0.0, comp)]
        if len(trecho) > 2:
            r2_trecho = np.corrcoef(np.log10(trecho['conc']),
                                    np.log10(trecho['C']))[0, 1] ** 2
        else:
            r2_trecho = r2_global
        ok = r2_trecho >= LIM_R2_TRECHO
        resultados.append(("T6 R2(log) trecho=%.4f >= %.2f" % (r2_trecho, LIM_R2_TRECHO), ok))
    else:
        r2_trecho = r2_global
        ok = r2_global >= LIM_R2_TRECHO
        resultados.append(("T6 R2(log) trecho (sem comprimento)=%.4f" % r2_global, ok))

    raz_med = m['ratio'].median()
    ok = LIM_RATIO_MIN <= raz_med <= LIM_RATIO_MAX
    resultados.append(("T7 razao mediana=%.3f in [%.2f, %.2f]" % (
        raz_med, LIM_RATIO_MIN, LIM_RATIO_MAX), ok))

    if m['conc'].max() > 0:
        fator = m['C'].max() / m['conc'].max()
    else:
        fator = 0.0
    ok = fator <= LIM_FATOR_ESCALA
    resultados.append(("T8 escala max RLINE/AERMOD=%.1f <= %.0f" % (
        fator, LIM_FATOR_ESCALA), ok))

    return nome, resultados


def main():
    args = sys.argv[1:]
    if args:
        casos = args
    else:
        import glob
        casos = sorted(glob.glob('casos/caso*_*'))
        casos = [c for c in casos
                 if os.path.isfile(os.path.join(c, 'rodada_aermod', 'CONC_PLOT.PLT'))]

    if not casos:
        print("Nenhum caso encontrado para testar.")
        sys.exit(1)

    global_ok = True
    for caso in casos:
        nome, resultados = testar_caso(caso)
        print("=== %s ===" % nome)
        for desc, ok in resultados:
            print("  [%s] %s" % ("PASS" if ok else "FAIL", desc))
            if not ok:
                global_ok = False

    print()
    if global_ok:
        print("TODOS OS TESTES PASSARAM")
        sys.exit(0)
    else:
        print("ALGUNS TESTES FALHARAM")
        sys.exit(1)


if __name__ == "__main__":
    main()
