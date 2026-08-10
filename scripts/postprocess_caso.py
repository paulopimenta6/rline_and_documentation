#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pos-processamento parametrizado de um caso de uso.

Uso:
    python3 scripts/postprocess_caso.py <caso_dir> [--transecto X]

Le:
    <caso_dir>/rodada_aermod/CONC_PLOT.PLT
    <caso_dir>/rodada_rline/Output_Road_Numerical.csv

Gera:
    <caso_dir>/graficos/conc_periodo_rline.png   (mapa + transecto AERMOD)
    <caso_dir>/graficos/conc_aermod_vs_rline.png (transecto/scatter/razao)
    <caso_dir>/resumo.txt                        (metricas de validacao)
"""
from __future__ import print_function
import argparse
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def carregar(caso_dir):
    plt_file = os.path.join(caso_dir, "rodada_aermod", "CONC_PLOT.PLT")
    csv_file = os.path.join(caso_dir, "rodada_rline", "Output_Road_Numerical.csv")
    if not os.path.isfile(plt_file):
        print("ERRO: %s nao existe (rode o AERMOD antes)" % plt_file, file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(csv_file):
        print("ERRO: %s nao existe (rode o RLINE antes)" % csv_file, file=sys.stderr)
        sys.exit(1)

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
    rline_period['X'] = rline_period['X'].round(1)
    rline_period['Y'] = rline_period['Y'].round(1)

    m = aermod.merge(rline_period, on=['X', 'Y'], suffixes=('_AERMOD', '_RLINE'))
    m['ratio'] = m['conc'] / m['C']
    return aermod, rline_period, m


def comprimento_rodovia(caso_dir):
    src = os.path.join(caso_dir, "rodada_rline", "Source_Road.txt")
    try:
        with open(src) as f:
            for line in f:
                if line.strip().upper().startswith('HWY'):
                    return float(line.split()[4])
    except Exception:
        pass
    return None


def gerar_graficos(caso_dir, transecto_x=600.0):
    aermod, rline_period, m = carregar(caso_dir)
    graficos = os.path.join(caso_dir, "graficos")
    os.makedirs(graficos, exist_ok=True)
    nome = os.path.basename(os.path.normpath(caso_dir))

    # escolhe transecto: o X do grid mais proximo de transecto_x
    xs_disp = np.unique(m['X'])
    tx = xs_disp[np.argmin(np.abs(xs_disp - transecto_x))]

    # ---- 1) Mapa + transecto (AERMOD)
    x = aermod['X'].values
    y = aermod['Y'].values
    c = aermod['conc'].values
    xi = np.unique(x)
    yi = np.unique(y)
    X, Y = np.meshgrid(xi, yi)
    C = c.reshape(len(yi), len(xi))

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    pc = axes[0].contourf(X, Y, C, levels=np.linspace(0, np.percentile(c, 99), 40),
                          cmap='inferno')
    cb = fig.colorbar(pc, ax=axes[0])
    cb.set_label('Conc. PERIOD (µg/m³)')
    axes[0].plot([0, m['X'].max()], [m['Y'].median(), m['Y'].median()],
                 'c-', lw=3, label='Rodovia')
    axes[0].set_title('%s — Mapa de conc. PERIOD (AERMOD RLINE)' % nome)
    axes[0].set_xlabel('X (m)'); axes[0].set_ylabel('Y (m)')
    axes[0].grid(alpha=0.3); axes[0].legend(loc='upper right')
    axes[0].set_aspect('equal')

    axes[1].plot([0, m['X'].max()], [m['Y'].median(), m['Y'].median()],
                 'c-', lw=3, label='Rodovia')
    axes[1].axvline(tx, color='k', ls='--', lw=1, label='Transecto X=%.0f m' % tx)
    xt = m[m['X'] == tx].sort_values('Y')
    axes[1].plot(xt['Y'], xt['conc'], 'o-', ms=3, lw=1.5, color='firebrick',
                 label='AERMOD (PERIOD)')
    axes[1].plot(xt['Y'], xt['C'], 's-', ms=3, lw=1.2, color='royalblue',
                 label='RLINE (média 120 h)')
    axes[1].set_xlabel('Y (m)'); axes[1].set_ylabel('Conc. (µg/m³)')
    axes[1].set_title('Transecto perpendicular em X=%.0f m' % tx)
    axes[1].legend(); axes[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(graficos, 'conc_periodo_rline.png'), dpi=150)
    plt.close(fig)

    # ---- 2) Comparacao AERMOD vs RLINE
    m2 = m.sort_values('Y')
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    tr = m2[m2['X'] == tx].sort_values('Y')
    axes[0].plot(tr['Y'], tr['conc'], '-o', ms=3, label='AERMOD RLINE (PERIOD)')
    axes[0].plot(tr['Y'], tr['C'], '-s', ms=3, label='RLINE standalone (média)')
    axes[0].set_xlabel('Distância transversal Y (m) [X=%.0f m]' % tx)
    axes[0].set_ylabel('Concentração (µg/m³)')
    axes[0].set_title('Transecto em X=%.0f m' % tx)
    axes[0].legend(); axes[0].grid(alpha=0.3)

    ax = axes[1]
    ax.loglog(m2['C'], m2['conc'], '.', ms=4, alpha=0.6)
    lims = (m2[['C', 'conc']].min().min(), m2[['C', 'conc']].max().max())
    ax.plot([lims[0], lims[1]], [lims[0], lims[1]], 'k--', lw=0.8, label='1:1')
    ax.loglog([lims[0], lims[1]], [lims[0] * 0.64, lims[1] * 0.64], 'r:', lw=0.8,
              label='fator 0.64')
    ax.set_xlabel('RLINE standalone (µg/m³)')
    ax.set_ylabel('AERMOD RLINE (µg/m³)')
    r2 = np.corrcoef(np.log10(m2['conc']), np.log10(m2['C']))[0, 1] ** 2
    # R2 restrito ao trecho da rodovia (receptores sob o alinhamento)
    comp = comprimento_rodovia(caso_dir)
    if comp is not None:
        trecho = m2[m2['X'].between(0.0, comp)]
        r2_trecho = (np.corrcoef(np.log10(trecho['conc']), np.log10(trecho['C']))[0, 1] ** 2
                     if len(trecho) > 2 else np.nan)
        lbl_r2 = 'R²(log) global=%.3f\nR²(log) trecho=%.3f' % (r2, r2_trecho)
    else:
        r2_trecho = np.nan
        lbl_r2 = 'R²(log)=%.3f' % r2
    ax.set_title('Scatter log-log (%d receptores)\n%s' % (len(m2), lbl_r2))
    ax.legend(); ax.grid(alpha=0.3, which='both')

    axes[2].plot(tr['Y'], tr['ratio'], '-o', ms=4, label='X=%.0f m' % tx)
    axes[2].axhline(1.0, color='k', ls='--', lw=0.8)
    axes[2].axhline(0.64, color='r', ls=':', lw=0.8)
    axes[2].set_xlabel('Distância transversal Y (m)')
    axes[2].set_ylabel('Razão AERMOD / RLINE')
    axes[2].set_title('Razão de concentrações')
    axes[2].legend(); axes[2].grid(alpha=0.3)

    fig.suptitle('Comparação: AERMOD (RLINE) vs RLINE v1.2 standalone — %s' % nome,
                 fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(graficos, 'conc_aermod_vs_rline.png'), dpi=150)
    plt.close(fig)

    # ---- 3) resumo
    resumo = os.path.join(caso_dir, 'resumo.txt')
    with open(resumo, 'w') as f:
        f.write('Caso: %s\n' % nome)
        f.write('Receptores comparados: %d\n' % len(m2))
        f.write('AERMOD PERIOD max: %.1f | RLINE media max: %.1f\n' % (
            m2['conc'].max(), m2['C'].max()))
        f.write('Media AERMOD: %.1f | Media RLINE: %.1f\n' % (
            m2['conc'].mean(), m2['C'].mean()))
        f.write('Ratio AERMOD/RLINE: media %.3f mediana %.3f\n' % (
            m2['ratio'].mean(), m2['ratio'].median()))
        f.write('R2(log-log) global : %.4f\n' % r2)
        if comp is not None and len(trecho) > 2:
            f.write('R2(log-log) trecho (0..%.0f m): %.4f  [n=%d]\n' % (
                comp, r2_trecho, len(trecho)))
    print('Figuras salvas em %s/' % graficos)
    print('Resumo em %s' % resumo)


def main():
    ap = argparse.ArgumentParser(description="Pos-processamento de um caso")
    ap.add_argument("caso_dir", help="pasta do caso (ex.: casos/caso1_base)")
    ap.add_argument("--transecto", type=float, default=600.0,
                    help="X do transecto (default 600)")
    args = ap.parse_args()
    if not os.path.isdir(args.caso_dir):
        print("ERRO: caso nao encontrado: %s" % args.caso_dir, file=sys.stderr)
        sys.exit(1)
    gerar_graficos(os.path.normpath(args.caso_dir), args.transecto)


if __name__ == "__main__":
    main()
