#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera o arquivo ONSITE.MET (dados meteorológicos de um perfil de torre com 3 níveis:
10, 50 e 100 m) para alimentar o AERMET Stage 1 (via pathway ONSITE).

Período: 5 dias (1988-03-01 a 1988-03-05), horas 1..24, formato de colunas livre
(FREE), com ciclo diurno realista:

  linha 1: dia mes ano hora  HT01 SA01 SW01 TT01 WD01 WS01 MHGT TSKC
  linha 2:                    HT02 SA02 SW02 TT02 WD02 WS02
  linha 3:                    HT03 SA03 SW03 TT03 WD03 WS03

Variáveis (conforme Tabela B-3/B-4 do AERMET User Guide):
  HTnn  -> altura do nível (m)
  SAnn  -> desvio padrão da direção do vento, sigma_theta (graus)
  SWnn  -> desvio padrão da componente vertical, sigma_w (m/s)
  TTnn  -> temperatura (graus C)
  WDnn  -> direção do vento (graus desde o norte)
  WSnn  -> velocidade do vento (m/s)
  MHGT  -> altura de mistura observada (m)  [single-level]
  TSKC  -> cobertura total de nuvens (décimos)  [single-level]

Saída: dados_aermet/ONSITE.MET
"""
from __future__ import print_function
import math
import os
import random

random.seed(42)

SAIDA = os.path.join(os.path.dirname(__file__), "..", "dados_aermet", "ONSITE.MET")

ANO = 88
MES = 3
DIAS = [1, 2, 3, 4, 5]
ALTURAS = [10.0, 50.0, 100.0]

# Direção dominante do vento (graus) e variação com a altura (veering)
WD_BASE = 265.0
VEERING = [0.0, 6.0, 12.0]          # giro com a altura (graus)

# Lei de potência para o perfil de vento (p ~ 0.20 neutro) + ciclo diurno
REF_WSPD_10 = 3.5                    # velocidade média a 10 m (m/s)
P_EXP = 0.20

# Perfil de temperatura de referência a 10 m (C) com ciclo diurno
T_BASE = 8.0
T_AMP = 7.0

linhas = []
for dia in DIAS:
    for hora in range(1, 25):
        # Ciclo diurno: dia = horas 8..20, noite = resto
        # Fator de convecção (0..1): maximo perto de 14h, zero à noite
        conv = max(0.0, math.sin(math.pi * (hora - 6.0) / 16.0)) if 7 <= hora <= 22 else 0.0

        # Velocidade do vento a 10 m: mais forte durante o dia
        ws10 = REF_WSPD_10 * (0.55 + 0.45 * conv) + random.uniform(-0.4, 0.4)
        ws10 = max(0.8, ws10)

        # Temperatura a 10 m com ciclo diurno
        tt10 = T_BASE + T_AMP * math.sin(math.pi * (hora - 7.0) / 14.0) + random.uniform(-0.5, 0.5)

        # Cobertura de nuvens (décimos): aleatória entre 0 e 8
        tskc = random.choice([0, 0, 1, 2, 3, 4, 4, 5, 6])

        # Altura de mistura: convectiva durante o dia (~300 a 1500 m), mecânica à noite (~150-400 m)
        if conv > 0.02:
            mhgt = 300.0 + conv * 1200.0 + random.uniform(-80, 80)
        else:
            mhgt = 150.0 + 250.0 * random.random()
        mhgt = max(100.0, mhgt)

        # Direcao do vento com pequena flutuacao horaria
        wd10 = WD_BASE + random.uniform(-8, 8)
        if wd10 < 0:
            wd10 += 360.0
        if wd10 > 360:
            wd10 -= 360.0

        # sigma_theta: maior em condicoes estaveis (meandramento), menor na conveccao
        sa10 = 5.0 + 40.0 * (1.0 - conv) + random.uniform(-3, 3)
        sa10 = max(2.0, min(85.0, sa10))

        # sigma_w: maior na conveccao
        sw10 = 0.06 + 0.70 * conv + random.uniform(-0.05, 0.05)
        sw10 = max(0.02, sw10)

        # Perfis com a altura
        ws = []
        tt = []
        sa = []
        sw = []
        wd = []
        for i, alt in enumerate(ALTURAS):
            ws.append(ws10 * (alt / 10.0) ** P_EXP)
            wd.append((wd10 + VEERING[i]) % 360.0)
            if conv > 0.05:
                # Dia bem misturado: temperatura quase constante com a altura
                tt.append(tt10 - 0.3 * i)
            else:
                # Noite: inversao termica, temperatura aumenta com a altura
                tt.append(tt10 + 0.8 * (i + 1))
            sa.append(sa10 * (0.85 + 0.15 * i))
            sw.append(sw10 * (0.85 + 0.15 * i))

        # Linhas do arquivo (formato livre, espacos simples)
        l1 = "%d %d %d %d %5.1f %5.1f %6.3f %6.2f %7.2f %6.2f %7.1f %2d" % (
            dia, MES, ANO, hora,
            ALTURAS[0], sa[0], sw[0], tt[0], wd[0], ws[0], mhgt, tskc)
        l2 = "%5.1f %5.1f %6.3f %6.2f %7.2f %6.2f" % (
            ALTURAS[1], sa[1], sw[1], tt[1], wd[1], ws[1])
        l3 = "%5.1f %5.1f %6.3f %6.2f %7.2f %6.2f" % (
            ALTURAS[2], sa[2], sw[2], tt[2], wd[2], ws[2])
        linhas.append(l1)
        linhas.append(l2)
        linhas.append(l3)

os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
with open(SAIDA, "w") as f:
    f.write("\n".join(linhas) + "\n")

print("Arquivo gerado:", os.path.abspath(SAIDA))
print("Numero de observacoes (horas):", len(DIAS) * 24)
print("Numero de linhas:", len(linhas))
