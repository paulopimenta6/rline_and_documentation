#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comparativo geral entre os casos de uso: gera um painel com
  (a) mapa de cada caso (2x2)
  (b) barras da concentracao maxima (AERMOD vs RLINE) por caso
Salva em casos/comparativo_geral.png
"""
from __future__ import print_function
import glob
import json
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def ler_caso(caso_dir):
    plt_file = os.path.join(caso_dir, "rodada_aermod", "CONC_PLOT.PLT")
    csv_file = os.path.join(caso_dir, "rodada_rline", "Output_Road_Numerical.csv")
    cfg_file = os.path.join(caso_dir, "config.json")

    aermod = pd.read_csv(plt_file, sep=r'\s+',
                         names=['X', 'Y', 'conc', 'ZELEV', 'ZHILL', 'ZFLAG',
                                'AVE', 'GRP', 'NHRS', 'NETID'], skiprows=8)
    aermod['X'] = aermod['X'].round(1)
    aermod['Y'] = aermod['Y'].round(1)

    rline = pd.read_csv(csv_file, skiprows=12, skipfooter=1, engine='python',
                        header=None, usecols=[0, 1, 2, 3, 4, 5, 6],
                        names=['Year', 'JD', 'Hour', 'X', 'Y', 'Z', 'C'])
    rline = rline[rline['C'] > -99.0]
    rline_period = rline.groupby(['X', 'Y'])['C'].mean().reset_index()

    m = aermod.merge(rline_period, on=['X', 'Y'], suffixes=('_A', '_R'))
    m['ratio'] = m['conc'] / m['C']

    cfg = json.load(open(cfg_file)) if os.path.isfile(cfg_file) else {}
    return {
        'nome': cfg.get('nome', os.path.basename(caso_dir)),
        'descricao': cfg.get('descricao', ''),
        'max_aermod': m['conc'].max(),
        'max_rline': m['C'].max(),
        'media_aermod': m['conc'].mean(),
        'ratio_mediana': m['ratio'].median(),
        'n': len(m),
        'm': m,
        'x': aermod['X'].values, 'y': aermod['Y'].values, 'c': aermod['conc'].values,
    }


def main():
    casos = sorted(glob.glob('casos/caso*_*'))
    dados = [ler_caso(c) for c in casos if os.path.isfile(os.path.join(c, 'resumo.txt'))]
    if not dados:
        print("Nenhum caso processado encontrado em casos/")
        return
    print("Casos carregados:", len(dados))

    fig = plt.figure(figsize=(13, 10))
    gs = fig.add_gridspec(3, 2, height_ratios=[3, 3, 2])

    # ---- mapas (2x2)
    for i, d in enumerate(dados):
        ax = fig.add_subplot(gs[i // 2, i % 2])
        x, y, c = d['x'], d['y'], d['c']
        xi, yi = np.unique(x), np.unique(y)
        X, Y = np.meshgrid(xi, yi)
        C = c.reshape(len(yi), len(xi))
        ax.contourf(X, Y, C, levels=np.linspace(0, np.percentile(c, 99), 40),
                    cmap='inferno')
        ax.plot([0, xi.max()], [np.median(yi), np.median(yi)], 'c-', lw=3)
        ax.set_title('%s\nR²(trecho)=%.3f' % (d['nome'],
                     d.get('ratio_mediana', 0) or 0), fontsize=9)
        ax.set_aspect('equal')
        ax.tick_params(labelsize=7)
    fig.suptitle('Mapas de concentração PERIOD (AERMOD RLINE) por caso de uso',
                 fontsize=12)

    # ---- barras de concentracao maxima
    ax = fig.add_subplot(gs[2, :])
    names = [d['nome'] for d in dados]
    xpos = np.arange(len(names))
    w = 0.38
    a_max = [d['max_aermod'] for d in dados]
    r_max = [d['max_rline'] for d in dados]
    b1 = ax.bar(xpos - w / 2, a_max, w, label='AERMOD RLINE (PERIOD)', color='#d62728')
    b2 = ax.bar(xpos + w / 2, r_max, w, label='RLINE standalone (média 120 h)',
                color='#1f77b4')
    ax.set_yscale('log')
    ax.set_xticks(xpos)
    ax.set_xticklabels(names, rotation=15, ha='right', fontsize=8)
    ax.set_ylabel('Concentração máx. (µg/m³, log)')
    ax.set_title('Concentração máxima por caso (fator de emissão varia: caso3=5x, '
                 'caso4=2x via largura)')
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3, axis='y')

    for i, d in enumerate(dados):
        ax.text(i - w / 2, a_max[i] * 1.25, '%.0f' % a_max[i], ha='center',
                va='bottom', fontsize=6.5, rotation=45)
        ax.text(i + w / 2, r_max[i] * 1.25, '%.0f' % r_max[i], ha='center',
                va='bottom', fontsize=6.5, rotation=45)

    fig.tight_layout()
    out = os.path.join('casos', 'comparativo_geral.png')
    fig.savefig(out, dpi=150)
    print('Figura salva em', out)

    # tabela resumida
    print()
    print('%-22s %10s %10s %10s %10s' % ('caso', 'max_AERMOD', 'max_RLINE',
                                         'mediana_R', 'n'))
    for d in dados:
        print('%-22s %10.1f %10.1f %10.3f %10d' % (
            d['nome'], d['max_aermod'], d['max_rline'], d['ratio_mediana'], d['n']))


if __name__ == "__main__":
    main()
