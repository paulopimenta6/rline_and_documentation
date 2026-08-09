# AERMET + AERMOD com fonte RLINE — Guia do Pipeline Completo

> Este documento descreve o **pipeline completo de modelagem de qualidade do ar com fonte RLINE**
> (rodovia) rodado neste projeto: **AERMET** (geração de meteorologia de superfície) →
> **AERMOD** (dispersão com a fonte `RLINE`) → **pós-processamento e comparação com o RLINE standalone**.
> Complementa o [`GUIA_RLINE.md`](GUIA_RLINE.md) (conceitos do RLINE) e o
> [`PLANO_Compilacao_Uso_RLINE.md`](PLANO_Compilacao_Uso_RLINE.md) (uso do RLINE v1.2 standalone).

---

## 1. Visão geral do pipeline

```
┌──────────────────┐   ┌──────────────────────────────┐   ┌───────────────────────┐
│ ONSITE.MET       │   │ AERMET (Stage 1 + Stage 2)   │   │ ONSITE.SFC + .PFL     │
│ (obs. de torre,  │ → │  → BULK → MERGE → METPREP    │ → │ (meteorologia pronta) │
│ 3 níveis)        │   │                              │   │                       │
└──────────────────┘   └──────────────────────────────┘   └───────────┬───────────┘
                                                                      │
                                   ┌──────────────────────────────────┘
                                   ▼
                          ┌────────────────────┐
                          │ AERMOD (INP)       │  ← fonte RLINE + grade de receptores
                          │  → CONC PERIOD     │
                          └─────────┬──────────┘
                                    │
                      ┌─────────────┴──────────────┐
                      ▼                            ▼
              CONC_PLOT.PLT (806 rec.)     RLINE v1.2 standalone (comparação)
                      │                            │
                      └──────────────┬─────────────┘
                                     ▼
                          gráficos + análise comparativa
```

---

## 2. Compilação dos modelos

Tudo compilado com **gfortran 11.4** (Ubuntu 22.04). **Não usar `-ffixed-line-length-132`**
para o AERMOD: isso quebra o parsing de `rline.f` (erro "Invalid character(s) in ELSE
statement"). Usar o comprimento de linha fixa padrão (72 colunas).

### 2.1 AERMET v26135
```bash
cd aermet_and_aermod/aermet_source
gfortran -c -O2 aermet.f           # (ou via Makefile/script de build existente)
# gera: aermet
```

### 2.2 AERMOD v26135
```bash
cd aermet_and_aermod/aermod_source/aermod_source_v26135
# compilar TODOS os .f (ordem do Makefile/script original), SEM -ffixed-line-length-132
# gera: aermod
```

### 2.3 RLINE v1.2 standalone
```bash
cd RLINE_v1_2.Source/v1_2
make -f Makefile.gfortran
# gera: RLINEv1_2_gfortran.x
```

---

## 3. Geração dos dados meteorológicos de entrada (ONSITE.MET)

O script `Caso_Pipeline/scripts/gerar_dados_onsite.py` gera o `dados_aermet/ONSITE.MET`:
perfil de torre com 3 níveis (10, 50 e 100 m), formato livre, 5 dias (1988-03-01 a 03-05),
24 h/dia, com ciclo diurno realista (vento, temperatura, cobertura de nuvens, altura de
mistura, σθ e σw).

Formato de cada grupo de 3 linhas (conforme Tabela B-3/B-4 do AERMET User Guide):

```
linha 1:  dia mes ano hora  HT01 SA01 SW01 TT01 WD01 WS01 MHGT TSKC
linha 2:                        HT02 SA02 SW02 TT02 WD02 WS02
linha 3:                        HT03 SA03 SW03 TT03 WD03 WS03
```

---

## 4. AERMET (Stage 1 + Stage 2)

### 4.1 Stage 1 (ONSITE — observações de superfície)

Input de controle do Stage 1 (`dat.a1` / `aermet.inp`), com pontos importantes:

| Opção | Valor usado | Observação |
|---|---|---|
| `LOCATION` | `99999 74.0W 41.3N 0` | Estação ONSITE. **Usar `tadjust=0`** (com `tadjust=5` o AERMET descarta observações); a longitude `74.0W` define a zona GMT→LST (5 h) |
| `XDATES` | `03/01/88 03/05/88` | Obrigatório definir o período explicitamente |
| Sub-blocos de dados | níveis 10/50/100 m, formato livre (`FREE`) | igual ao ONSITE.MET |

Saída: `dados_aermet/ONSITE.MET` processada → `ONSITE.SFC` preliminar.

### 4.2 Stage 2 (METPREP — preparação final)

| Opção | Valor usado | Observação |
|---|---|---|
| `LOCATION` no METPREP | `99999 74.0W 41.3N` | **Obrigatório repetir no Stage 2.** Define a conversão GMT→LST (5 h para 74°W). Sem isso → erro de dados sem sobreposição de datas |
| `XDATES` | idem Stage 1 | Repetir explicitamente (senão erro `E70 PBL_TEST NO DATA PERIODS DATES OVERLAP`) |

Saída final:
- `ONSITE.SFC` — meteorologia de superfície (120 horas: 5 dias × 24 h)
- `ONSITE.PFL` — perfil vertical (níveis 10/50/100 m)

---

## 5. AERMOD com fonte RLINE

### 5.1 Formato do control file (formato de colunas fixas)

O AERMOD usa **formato de colunas fixas** (função `DEFINE` em `setup.f`):

- **colunas 1–2:** `PATH` (`CO`, `SO`, `RE`, `ME`, `OU`)
- **colunas 4–11:** `KEYWORD`
- **a partir da coluna 13:** dados

⚠️ A lista `KEYWD` (122 palavras, `modules.f:1632`) **NÃO contém** as sub-keywords
`XYINC`, `XPNTS`, `STA`, `END`. Por isso, **no bloco GRIDCART cada linha deve repetir o
prefixo `GRIDCART <netid>`** (as sub-keywords são lidas por `RECART`/`GENCAR` em `reset.f`,
que tomam a palavra-chave do campo 4). Sem isso → erro `RE E105 Invalid Keyword Specified`.

### 5.2 O control file final (`controles_aermod/RLINE_TEST.INP`)

```
CO STARTING
   TITLEONE   TESTE RLINE COM DADOS ONSITE SINTETICOS   ← obrigatória (senão CO E130)
   MODELOPT   DFAULT CONC
   AVERTIME   PERIOD
   POLLUTID   OTHER
   RUNORNOT   RUN
CO FINISHED

SO STARTING
   LOCATION   HWY1    RLINE  0.0  0.0  1000.0  0.0        ← fonte de linha
   SRCPARAM   HWY1   0.001  0.0   20.0                    ← QS (g/s/m²) altura largura
   SRCGROUP   ALL
SO FINISHED

RE STARTING
   GRIDCART   RCART STA
   GRIDCART   RCART XYINC  0.0  26  40.0  -300.0  31  20.0
   GRIDCART   RCART END
RE FINISHED

ME STARTING
   SURFFILE   ONSITE.SFC
   PROFFILE   ONSITE.PFL
   SURFDATA   99999  1988
   UAIRDATA   99999  1988
   SITEDATA   99999  1988
   PROFBASE   10.0 METERS
ME FINISHED

OU STARTING
   RECTABLE   ALLAVE FIRST
   PLOTFILE   PERIOD ALL CONC_PLOT.PLT
   MAXTABLE   ALLAVE 20
OU FINISHED
```

### 5.3 Pontos-chave de cada bloco

**`SO` — fonte RLINE**
- `LOCATION <id> RLINE XSB YSB XSE YSE`: segmento de reta da rodovia (2 pontos).
- `SRCPARAM <id> TEMP(1) TEMP(2) TEMP(3) [TEMP(4)]` (lógica RLPARM em `soset.f`):
  - `TEMP(1)` = **QS, emissão por área** em **g/(s·m²)**;
  - `TEMP(2)` = altura da liberação (ZSB/ZSE), m;
  - `TEMP(3)` = **WIDTH** (largura da rodovia), m;
  - `TEMP(4)` = σz inicial (opcional).
- **`RLSOURCE%QEMIS = TEMP(1) × TEMP(3)`** → emissão por unidade de comprimento em
  **g/(s·m)** (confirmado em `rline.f:128`). Ex.: `0.001 × 20 = 0.02 g/(s·m)`.
- `SRCGROUP ALL`: todas as fontes no grupo `ALL`.

**`RE` — grade de receptores**
- `GRIDCART <netid> STA` / `... XYINC ...` / `... END` (cada linha com o prefixo repetido).
- `XYINC XSTART XNUM XDELTA YSTART YNUM YDELTA` (`GENCAR`, `reset.f:471`).
- Exemplo: `XYINC 0.0 26 40.0 -300.0 31 20.0` → X de 0 a 1000 m (26 pts, Δ=40),
  Y de −300 a 300 m (31 pts, Δ=20) → **806 receptores**.

**`ME` — meteorologia**
- `SURFFILE`/`PROFFILE` apontam para `ONSITE.SFC`/`ONSITE.PFL` (mesma pasta da rodada).
- `SURFDATA`/`UAIRDATA`/`SITEDATA <id> <ano>`.
- `PROFBASE 10.0 METERS` = base do perfil.

**`OU` — saída**
- `PLOTFILE <AVEAVE> <GRPGRP> <FILNAM>`: **3 campos, não 4** (senão erro `OU E105`).
- `MAXTABLE <AVEAVE> <N>`: ex. `MAXTABLE ALLAVE 20` (2 parâmetros, não 1).
- `RECTABLE ALLAVE FIRST`: primeira ocorrência de cada média.

### 5.4 Execução

```bash
cd Caso_Pipeline/rodada_aermod      # onde estão ONSITE.SFC, ONSITE.PFL
setsid /caminho/aermod RLINE_TEST.INP > RLINE_TEST.out 2>&1 &
```

- O control file pode ficar em outra pasta (`controles_aermod/`); o AERMOD busca os
  arquivos `.SFC`/`.PFL` no diretório de trabalho.
- **806 receptores** rodam em ~5 min. Com 3111 receptores excede o timeout da shell;
  usar `setsid ... &` para background.
- Saída: `RLINE_TEST.out` — `AERMOD Finishes Successfully`, 0 erros fatais, 120 horas
  processadas, 5 warnings benignos (SO W205 ZS=0.0 default; RE W214 ELEV inconsistent;
  ME W531 Met Station ID missing; MX W403 SigA&SigW).

---

## 6. Saídas do AERMOD e pós-processamento

### 6.1 `CONC_PLOT.PLT`

Cabeçalho (8 linhas) e depois 806 linhas de dados. Formato (da linha 7 do arquivo):
`(3(1X,F13.5),3(1X,F8.2),2X,A6,2X,A8,2X,I8.8,2X,A8)` → colunas:
`X, Y, CONC, ZELEV, ZHILL, ZFLAG, AVE, GRP, NHRS, NETID`.

Leitura no Python (ver `scripts/plot_conc_aermod_rline.py`):
```python
d = pd.read_csv('CONC_PLOT.PLT', skiprows=8, sep=r'\s+',
                names=['X','Y','CONC','ZELEV','ZHILL','ZFLAG','AVE','GRP','NHRS','NET'])
```

### 6.2 Resultados do caso de teste

- Max **48966.6 µg/m³** em (X=600, Y=0) — sobre a rodovia
- Min **61.01 µg/m³** a Y=±300 m (afastado da rodovia)
- Grade 26×31 (806 receptores), PERIOD = média das 120 h

### 6.3 Gráficos

- `graficos/conc_periodo_rline.png` — mapa de contorno (escala limitada a P99) +
  transecto perpendicular em X=600 m (`scripts/plot_conc_aermod_rline.py`).
- `graficos/conc_aermod_vs_rline.png` — comparação AERMOD vs RLINE standalone
  (`scripts/plot_compare_aermod_rline.py`).

---

## 7. Comparação com o RLINE v1.2 standalone

### 7.1 Arquivos de entrada do RLINE (pasta `rodada_rline/`)

Mesma geometria do AERMOD, gerados por script (ver `Source_Road.txt`,
`Receptor_Road.txt`, `Line_Source_Inputs.txt`):

- **Fonte:** `HWY 0 0 0 1000 0 0 0 0 1 0.02 0 0 0 0 0 0 0`
  (`Emis = 0.02 g/(m·s)` = QS×WIDTH do AERMOD; 1 faixa).
- **Receptores:** grade 26×31 (806 pontos, Z=0).
- **Met:** aponta para `../dados_aermet/ONSITE.SFC`. O RLINE lê os **20 primeiros campos**
  do `.sfc` via read list-directed, pulando a linha de versão — compatível com o
  `VERSION 26135` (campos extras ignorados). `Wstar` e `CBL` com valores faltantes
  (`-9`, `-999`) são tratados por `max(...,0)` e `max(SBL,CBL)` em `Fill_Met.f90`.
- **Control file** (`Line_Source_Inputs.txt`): posições de linha **fixas** (lidas por
  `Read_Line_Source_Inputs.f90`); opções: total (`'T'`), média diária `'Y'`, todos os
  horários `'A'`, largura de pista `'Y' 20.0`.

### 7.2 Execução

```bash
cd Caso_Pipeline/rodada_rline
setsid ./RLINEv1_2_gfortran.x > /tmp/rline_run.log 2>&1 &
```

- Modo numérico com 806 receptores × 120 h leva ~4 min (214 s observados).
- Saídas: `Output_Road_Numerical.csv` (horário, 8 colunas com vírgula final → 7 colunas
  + espaço; dados a partir da linha 13) e `Output_Road_Numerical_DailyAve.csv`.

### 7.3 Resultados da comparação (806 receptores, PERIOD vs média das 120 h)

| Métrica | Valor |
|---|---|
| Receptores comparados | 806 |
| R² (log-log) | **0.96** |
| Razão média AERMOD/RLINE | **≈ 0.64** (mediana 0.64) |
| Conc. máx. AERMOD | 48 967 µg/m³ |
| Conc. máx. RLINE | 153 272 µg/m³ |
| Comportamento | converge p/ 1 longe da rodovia (Y ≥ 240 m); cai p/ ~0.32 no eixo (Y=0) |

A alta correlação espacial confirma que o AERMOD implementa a formulação RLINE de forma
consistente. As diferenças próximas à fonte são esperadas: o AERMOD usa a implementação
regulatória (sigmay inicial, tabulação, meandro) diferente do código standalone numérico.

---

## 8. Estrutura de pastas do caso

```
Caso_Pipeline/
├── dados_aermet/          ONSITE.MET (gerado), ONSITE.SFC/.PFL (AERMET), ONSITE_QAOUT.TXT
├── controles_aermod/      RLINE_TEST.INP
├── rodada_aermod/         ONSITE.SFC/.PFL, RLINE_TEST.out, CONC_PLOT.PLT
├── rodada_rline/          Source_Road.txt, Receptor_Road.txt, Line_Source_Inputs.txt,
│                          Output_Road_Numerical.csv(+_DailyAve), RLINEv1_2_gfortran.x
├── scripts/               gerar_dados_onsite.py, plot_conc_aermod_rline.py,
│                          compare_aermod_rline.py, plot_compare_aermod_rline.py
└── graficos/              conc_periodo_rline.png, conc_aermod_vs_rline.png
```

---

## 9. Referências-chave no código-fonte AERMOD v26135

| Local | Conteúdo |
|---|---|
| `setup.f` (`DEFINE`, ~linha 372) | parsing de colunas fixas (PATH 1–2, KEYWRD 4–11, dados ≥13) |
| `modules.f:1632` | lista `KEYWD` (122 keywords; `XYINC`/`XPNTS`/`STA`/`END` NÃO estão) |
| `reset.f` (`RECARD`/`RECART`/`GENCAR`, ~471) | lê sub-keywords do GRIDCART; NETIDT=FIELD(3), KTYPE=FIELD(4) |
| `soset.f` (`RLPARM` ~3934, `SOLOCA` ~2089) | lê `SRCPARAM`/`LOCATION` RLINE |
| `rline.f` (~116, ~253) | `QEMIS=TEMP(1)*WIDTH`; `SIGMAY0=0.5*WIDTH*cos(THETA_LINE)` |
