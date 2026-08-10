#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera todos os dados de entrada de um caso de uso a partir de um config.json:

    casos/<nome>/config.json

Estrutura do config.json:
{
  "nome": "caso1_base",
  "descricao": "Rodovia de 1000 m com emissao media",
  "comprimento": 1000.0,      # comprimento da rodovia (m), ao longo de X
  "y_rodovia": 0.0,           # posicao Y da rodovia (m)
  "qs": 0.001,                # Lnemis no AERMOD (g/s/m2)
  "width": 20.0,              # largura da rodovia (m)
  "grid": {"xini": 0.0, "xn": 26, "xdelta": 40.0,
           "yini": -300.0, "yn": 31, "ydelta": 20.0},
  "transecto_x": 600.0,       # transecto perpendicular (opcional)
  "emis_fator": null           # override do Emis RLINE (default: qs*width)
}

Saida (na pasta do caso):
  controles_aermod/RLINE_TEST.INP
  rodada_aermod/               (vazia, usada pelo AERMOD)
  rodada_rline/Source_Road.txt
  rodada_rline/Receptor_Road.txt
  rodada_rline/Line_Source_Inputs.txt   (met: ./ONSITE.SFC)
  graficos/                    (vazia)
  metadados.txt
"""
from __future__ import print_function
import argparse
import json
import os
import sys


def gerar(config_path):
    with open(config_path) as f:
        cfg = json.load(f)

    caso = os.path.dirname(os.path.abspath(config_path))
    nome = cfg.get("nome", os.path.basename(caso))
    comp = float(cfg["comprimento"])
    y_rod = float(cfg["y_rodovia"])
    qs = float(cfg["qs"])
    width = float(cfg["width"])
    emis = cfg.get("emis_fator")
    if emis is None:
        emis = qs * width
    grid = cfg["grid"]
    tx = cfg.get("transecto_x")
    if tx is None:
        tx = round(comp / 2.0, 3)

    os.makedirs(os.path.join(caso, "controles_aermod"), exist_ok=True)
    os.makedirs(os.path.join(caso, "rodada_aermod"), exist_ok=True)
    os.makedirs(os.path.join(caso, "rodada_rline"), exist_ok=True)
    os.makedirs(os.path.join(caso, "graficos"), exist_ok=True)

    # ---- AERMOD control file
    inp = os.path.join(caso, "controles_aermod", "RLINE_TEST.INP")
    with open(inp, "w") as f:
        f.write("CO STARTING\n")
        f.write("   TITLEONE   %s\n" % nome.upper())
        f.write("   MODELOPT   DFAULT CONC\n")
        f.write("   AVERTIME   PERIOD\n")
        f.write("   POLLUTID   OTHER\n")
        f.write("   RUNORNOT   RUN\n")
        f.write("CO FINISHED\n\n")
        f.write("SO STARTING\n")
        f.write("   LOCATION   HWY1    RLINE  0.0  %.3f  %.3f  %.3f\n"
                % (y_rod, comp, y_rod))
        f.write("   SRCPARAM   HWY1   %.6f  0.0   %.3f\n" % (qs, width))
        f.write("   SRCGROUP   ALL\n")
        f.write("SO FINISHED\n\n")
        f.write("RE STARTING\n")
        f.write("   GRIDCART   RCART STA\n")
        f.write("   GRIDCART   RCART XYINC  %.3f  %d  %.3f  %.3f  %d  %.3f\n" % (
            grid["xini"], grid["xn"], grid["xdelta"],
            grid["yini"], grid["yn"], grid["ydelta"]))
        f.write("   GRIDCART   RCART END\n")
        f.write("RE FINISHED\n\n")
        f.write("ME STARTING\n")
        f.write("   SURFFILE   ONSITE.SFC\n")
        f.write("   PROFFILE   ONSITE.PFL\n")
        f.write("   SURFDATA   99999  1988\n")
        f.write("   UAIRDATA   99999  1988\n")
        f.write("   SITEDATA   99999  1988\n")
        f.write("   PROFBASE   10.0 METERS\n")
        f.write("ME FINISHED\n\n")
        f.write("OU STARTING\n")
        f.write("   RECTABLE   ALLAVE FIRST\n")
        f.write("   PLOTFILE   PERIOD ALL CONC_PLOT.PLT\n")
        f.write("   MAXTABLE   ALLAVE 20\n")
        f.write("OU FINISHED\n")

    # ---- RLINE receptor grid (mesma ordem do AERMOD GRIDCART)
    xini, xn, xd = grid["xini"], grid["xn"], grid["xdelta"]
    yini, yn, yd = grid["yini"], grid["yn"], grid["ydelta"]
    xs = [round(xini + i * xd, 3) for i in range(xn)]
    ys = [round(yini + j * yd, 3) for j in range(yn)]

    rec_file = os.path.join(caso, "rodada_rline", "Receptor_Road.txt")
    with open(rec_file, "w") as f:
        f.write("This file contains receptor locations\n")
        f.write("X_coordinate  Y_Coordinate  Z_Coordinate\n")
        f.write("----------------------------------------------\n")
        for y in ys:
            for x in xs:
                f.write("  %8.1f %8.1f %4.1f\n" % (x, y, 0.0))

    # ---- RLINE source
    src_file = os.path.join(caso, "rodada_rline", "Source_Road.txt")
    with open(src_file, "w") as f:
        f.write("Source input file\n")
        f.write("Group  X_b    Y_b    Z_b    X_e    Y_e    Z_e  dCL  sigmaz0 "
                "#lanes  Emis  Hw1  dw1  Hw2  dw2 Depth  Wtop  Wbottom\n")
        f.write("----------------------------------------------\n")
        f.write("HWY 0.0 %.3f 0.0 %.3f %.3f 0.0 0.0 0.0 1.0 %.6f "
                "0.0 0.0 0.0 0.0 0.0 0.0 0.0\n"
                % (y_rod, comp, y_rod, emis))

    # ---- RLINE Line_Source_Inputs.txt (met local ./ONSITE.SFC)
    lsi = os.path.join(caso, "rodada_rline", "Line_Source_Inputs.txt")
    with open(lsi, "w") as f:
        f.write("User control file for RLINEv1_2\n")
        f.write("Source File Name\n")
        f.write("'Source_Road.txt'\n")
        f.write("Input Emiss can be in AADT or g/m (see user guide)\n")
        f.write("--------------------------------------------------\n")
        f.write("Receptor File Name\n")
        f.write("'Receptor_Road.txt'\n")
        f.write("--------------------------------------------------\n")
        f.write("Input Met File\n")
        f.write("'./ONSITE.SFC'\n")
        f.write("--------------------------------------------------\n")
        f.write("Receptor Output File\n")
        f.write("'Output_Road_Numerical.csv'\n")
        f.write("--------------------------------------------------\n")
        f.write("Error_Limit (suggested 1.0e-03)\n")
        f.write("1.0e-03\n")
        f.write("--------------------------------------------------\n")
        f.write("Ratio of displacement height to roughness length (fac_dispht)\n")
        f.write("5.0\n")
        f.write("--------------------------------------------------\n")
        f.write("--- OUTPUT OPTION(S) BELOW: ----------------------\n")
        f.write("--------------------------------------------------\n")
        f.write("(1) Include concentrations from ['M'] Meander ONLY, "
                "['P'] Plume ONLY, ['T'] Total = Plume+Meander\n")
        f.write("'T'\n")
        f.write("--------------------------------------------------\n")
        f.write("(2) Outout daily 24-hour averages? ('Y'/'N')\n")
        f.write("'Y'\n")
        f.write("--------------------------------------------------\n")
        f.write("(3) ['M'] Monthly Output Files, ['N'] No Hourly Files, "
                "['A'] All hourly in one file\n")
        f.write("'A'\n")
        f.write("--------------------------------------------------\n")
        f.write("(4) Supress source/receptor proximity warnings? ('Y'/'N')\n")
        f.write("'Y'\n")
        f.write("--------------------------------------------------\n")
        f.write("--- BETA OPTION(S) BELOW: ------------------------\n")
        f.write("--------------------------------------------------\n")
        f.write("(1) Use analytical solution ('Y'/'N'), speeds up run time, "
                "but less accurate\n")
        f.write("'N'\n")
        f.write("--------------------------------------------------\n")
        f.write("(2) Use barrier and depressed roadway algorithms? ('Y'/'N')\n")
        f.write("'N'\n")
        f.write("--------------------------------------------------\n")
        f.write("(3) Use non-zero roadwidth? ('Y'/'N')Lane width [m]\n")
        f.write("'Y' %.2f\n" % width)
        f.write("--------------------------------------------------\n")

    # ---- metadados
    meta = os.path.join(caso, "metadados.txt")
    with open(meta, "w") as f:
        f.write("nome        : %s\n" % nome)
        f.write("descricao   : %s\n" % cfg.get("descricao", ""))
        f.write("comprimento : %.1f m\n" % comp)
        f.write("y_rodovia   : %.1f m\n" % y_rod)
        f.write("qs (Lnemis) : %.6f g/s/m2\n" % qs)
        f.write("width       : %.2f m\n" % width)
        f.write("emis RLINE  : %.6f g/m/s\n" % emis)
        f.write("receptores  : %d (grid %dx%d)\n" % (xn * yn, xn, yn))
        f.write("transecto_x : %.1f m\n" % tx)

    nrec = xn * yn
    print("Caso gerado:", nome)
    print("  - controles_aermod/RLINE_TEST.INP")
    print("  - rodada_rline/{Source_Road,Receptor_Road,Line_Source_Inputs}.txt")
    print("  - %d receptores (grid %dx%d), rodovia 0..%.0f m em Y=%.0f" % (
        nrec, xn, yn, comp, y_rod))
    print("  - Emis RLINE = %.6f g/m/s  (= QS x WIDTH = %.6f x %.1f)" % (
        emis, qs, width))


def main():
    ap = argparse.ArgumentParser(description="Gera dados de um caso de uso")
    ap.add_argument("config", help="caminho do config.json do caso")
    args = ap.parse_args()
    if not os.path.isfile(args.config):
        print("ERRO: config nao encontrado: %s" % args.config, file=sys.stderr)
        sys.exit(1)
    gerar(args.config)


if __name__ == "__main__":
    main()
