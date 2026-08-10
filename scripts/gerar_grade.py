#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera a grade de receptores (26 x 31 = 806 pontos) e os arquivos de entrada do
RLINE standalone (Receptor_Road.txt e Source_Road.txt), espelhando a geometria
do control file AERMOD (RLINE_TEST.INP).

Uso:
    python3 scripts/gerar_grade.py \
        --saida Caso_Pipeline/rodada_rline \
        --xini 0 --xn 26 --xdelta 40 \
        --yini -300 --yn 31 --ydelta 20 \
        --qs 0.001 --width 20.0 --comprimento 1000.0 --emis 0.02
"""
from __future__ import print_function
import argparse
import os


def main():
    ap = argparse.ArgumentParser(description="Gera grade de receptores e fonte RLINE")
    ap.add_argument("--saida", default="Caso_Pipeline/rodada_rline",
                    help="pasta onde gravar os arquivos (default: Caso_Pipeline/rodada_rline)")
    ap.add_argument("--xini", type=float, default=0.0)
    ap.add_argument("--xn", type=int, default=26)
    ap.add_argument("--xdelta", type=float, default=40.0)
    ap.add_argument("--yini", type=float, default=-300.0)
    ap.add_argument("--yn", type=int, default=31)
    ap.add_argument("--ydelta", type=float, default=20.0)
    ap.add_argument("--comprimento", type=float, default=1000.0,
                    help="comprimento da rodovia (m), de X=0 ate este valor")
    ap.add_argument("--qs", type=float, default=0.001,
                    help="QS (g/s/m2) usado no SRCPARAM do AERMOD")
    ap.add_argument("--width", type=float, default=20.0,
                    help="largura da rodovia (m), WIDTH do AERMOD")
    ap.add_argument("--emis", type=float, default=None,
                    help="Emis do RLINE (g/s/m). Default: QS x WIDTH")
    args = ap.parse_args()

    saida = os.path.abspath(args.saida)
    os.makedirs(saida, exist_ok=True)

    if args.emis is None:
        args.emis = args.qs * args.width

    xs = [round(args.xini + i * args.xdelta, 3) for i in range(args.xn)]
    ys = [round(args.yini + j * args.ydelta, 3) for j in range(args.yn)]

    # ---- Receptor_Road.txt (3 colunas: X Y Z)
    rec_file = os.path.join(saida, "Receptor_Road.txt")
    with open(rec_file, "w") as f:
        f.write("This file contains receptor locations\n")
        f.write("X_coordinate  Y_Coordinate  Z_Coordinate\n")
        f.write("----------------------------------------------\n")
        for y in ys:
            for x in xs:
                f.write("  %8.1f %8.1f %4.1f\n" % (x, y, 0.0))
    nrec = args.xn * args.yn

    # ---- Source_Road.txt (18 colunas)
    src_file = os.path.join(saida, "Source_Road.txt")
    with open(src_file, "w") as f:
        f.write("Source input file\n")
        f.write("Group  X_b    Y_b    Z_b    X_e    Y_e    Z_e  dCL  sigmaz0 "
                "#lanes  Emis  Hw1  dw1  Hw2  dw2 Depth  Wtop  Wbottom\n")
        f.write("----------------------------------------------\n")
        f.write("HWY 0.0 0.0 0.0 %.1f 0.0 0.0 0.0 0.0 1.0 %.4f 0.0 0.0 0.0 0.0 "
                "0.0 0.0 0.0\n" % (args.comprimento, args.emis))

    print("Receptores gerados:", nrec)
    print("Arquivo de receptores:", rec_file)
    print("Arquivo de fontes   :", src_file)
    print("Emis (g/s/m):", args.emis, "| comprimento (m):", args.comprimento)


if __name__ == "__main__":
    main()
