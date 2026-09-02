# AERMET + AERMOD com fonte RLINE - Guia do Pipeline Completo

Este guia descreve o caso canônico implementado em `Caso_Pipeline/`: geração de
meteorologia, AERMET Stages 1 e 2, AERMOD v26135 com fonte `RLINE`, RLINE v1.2
standalone corrigido e pós-processamento. A fonte `RLINE` apareceu como beta no
AERMOD v19191, foi reformulada na v23132 e passou à configuração regulatória na
v24142; o pipeline usa a v26135.

Para os formatos próprios do standalone, consulte [`GUIA_RLINE.md`](GUIA_RLINE.md).
Para variantes e regressões EPA, consulte
[`PLANO_Compilacao_Uso_RLINE.md`](PLANO_Compilacao_Uso_RLINE.md).

## 1. Fluxo executado

```text
ONSITE.MET, 3 níveis e 120 horas
    |
    +-- AERMET Stage 1: QA/QC ------------> ONSITE_QAOUT.TXT
    |
    +-- AERMET Stage 2: METPREP ----------> ONSITE.SFC + ONSITE.PFL
                                                   |
                          +------------------------+-----------------------+
                          |                                                |
                          v                                                v
              AERMOD v26135, fonte RLINE                    RLINE v1.2 corrigido
                     CONC_PLOT.PLT                       Output_Road_Numerical.csv
                          |                                                |
                          +------------------------+-----------------------+
                                                   v
                                  métricas e dois gráficos comparativos
```

O comando canônico executa todas essas etapas:

```bash
make models
bash scripts/run_pipeline.sh
```

O pipeline usa por padrão:

```text
build/aermet/aermet
build/aermod/aermod
build/rline-patched/RLINEv1_2_patched.x
```

Ele não seleciona os binários históricos presentes nas árvores de fonte ou de
caso.

## 2. Compilação isolada

Compile a partir da raiz do repositório:

```bash
make models
make rline-debug
```

`make models` gera AERMET, AERMOD, RLINE original e RLINE corrigido release.
`make rline-debug` gera separadamente a variante corrigida de diagnóstico. Todos
os objetos, módulos, fontes de staging e executáveis ficam sob `build/`:

| Modelo | Saída |
|---|---|
| AERMET | `build/aermet/aermet` |
| AERMOD | `build/aermod/aermod` |
| RLINE original | `build/rline-original/RLINEv1_2_gfortran.x` |
| RLINE corrigido release | `build/rline-patched/RLINEv1_2_patched.x` |
| RLINE corrigido debug | `build/rline-patched-debug/RLINEv1_2_patched_debug.x` |

O AERMET é compilado a partir dos arquivos `.f90`, incluindo `aermet.f90`; não
existe um arquivo fonte `aermet.f` neste projeto. O `Makefile` do componente
declara as dependências entre módulos, inclusive `mod_pbl.o` em relação a
`mod_upperair.o`, e aceita build paralelo.

No AERMOD, não use `-ffixed-line-length-132`: o código distribuído espera o
comprimento fixo padrão de 72 colunas e essa opção quebra `rline.f`. O
`Makefile` já usa as flags corretas.

Antes dos builds corrigidos, a árvore upstream do RLINE é conferida pelo
manifesto SHA-256. Os oito patches são aplicados, sem fuzz, somente à cópia sob
`build/`; `RLINE_v1_2.Source/v1_2/` permanece intacto. Consulte
`patches/rline-v1.2/Makefile` e `BUILD-INFO.txt` em cada diretório de build.

## 3. Execução transacional

`scripts/run_pipeline.sh` cria um workspace exclusivo, gera um novo
`ONSITE.MET`, chama os wrappers AERMET/AERMOD/RLINE, executa os três scripts de
análise e publica os artefatos somente após todas as validações.

Os wrappers usam lock por destino, logs exclusivos, manifesto JSON, timeout e
encerramento do grupo inteiro de processos com `TERM` e `KILL`. Uma falha não
faz uma saída antiga passar por nova e não substitui resultados publicados.
Cada arquivo é substituído atomicamente por um temporário adjacente, com backups
mantidos até o manifesto ser gravado. Em uma publicação de vários caminhos, o
rollback é conjunto, mas leitores sem lock ainda podem observar substituições
intermediárias; não há um snapshot único nem journal contra `SIGKILL`.

Variáveis principais:

| Variável | Padrão |
|---|---|
| `PIPELINE_CASE_DIR` | `Caso_Pipeline` |
| `BIN_AERMET` | `build/aermet/aermet` |
| `BIN_AERMOD` | `build/aermod/aermod` |
| `BIN_RLINE` | `build/rline-patched/RLINEv1_2_patched.x` |
| `PIPELINE_STEP_TIMEOUT_SECONDS` | `7200` |
| `PYTHON_TIMEOUT_SECONDS` | `600` |

Caminhos absolutos e relativos à raiz são aceitos. Logs e manifestos ficam em
`Caso_Pipeline/logs/`, salvo configuração explícita de outro destino.

## 4. Meteorologia e AERMET

### 4.1 Geração de `ONSITE.MET`

`Caso_Pipeline/scripts/gerar_dados_onsite.py` usa semente fixa 42 e gera cinco
dias, de 1988-03-01 a 1988-03-05, com 24 horas por dia e três níveis de torre:
10, 50 e 100 m. São 120 períodos e 360 linhas.

Cada grupo tem o formato livre:

```text
linha 1: dia mes ano hora HT01 SA01 SW01 TT01 WD01 WS01 MHGT TSKC
linha 2:                  HT02 SA02 SW02 TT02 WD02 WS02
linha 3:                  HT03 SA03 SW03 TT03 WD03 WS03
```

O pipeline gera esse arquivo dentro do staging. A execução isolada do wrapper
AERMET pressupõe que `ONSITE.MET` e os dois controles já existam no diretório de
dados.

### 4.2 Stage 1

Controle: `Caso_Pipeline/dados_aermet/ONSITE_S1.INP`.

Pontos efetivos:

- `XDATES 1988/3/1 TO 1988/3/5`;
- `LOCATION 99999 74.0W 41.3N 0`;
- três grupos `READ` e `FORMAT FREE`;
- ranges físicos e `THRESHOLD 0.3`.

O Stage 1 produz `ONSITE_QAOUT.TXT` e os relatórios. Ele não produz a saída
meteorológica final.

### 4.3 Stage 2

Controle: `Caso_Pipeline/dados_aermet/ONSITE_S2.INP`.

Pontos efetivos:

- `QAOUT ONSITE_QAOUT.TXT`;
- `XDATES 1988/3/1 TO 1988/3/5`;
- `LOCATION MYSITE 74.00W 41.3N 5`;
- `METHOD WIND_DIR RANDOM`;
- 12 entradas `SITE_CHAR` com albedo 0,200, razão de Bowen 0,800 e rugosidade
  0,500 m.

O Stage 2 produz `ONSITE.SFC` e `ONSITE.PFL`. O wrapper exige mensagem de
sucesso nos dois relatórios, `ONSITE.SFC` com cabeçalho `VERSION:` e registros
válidos no perfil antes de publicar.

Execução isolada:

```bash
bash scripts/run_aermet.sh \
  Caso_Pipeline/dados_aermet \
  build/aermet/aermet
```

O timeout padrão desse wrapper é 1800 s e pode ser alterado com
`AERMET_TIMEOUT_SECONDS`.

## 5. AERMOD com fonte RLINE

### 5.1 Formato do controle

O AERMOD usa formato de colunas fixas:

- colunas 1-2: pathway `CO`, `SO`, `RE`, `ME` ou `OU`;
- colunas 4-11: palavra-chave;
- a partir da coluna 13: dados.

As subpalavras `STA`, `XYINC` e `END` não são palavras-chave independentes.
Cada linha da grade deve repetir `GRIDCART <netid>`.

O controle canônico é:

```text
CO STARTING
   TITLEONE   TESTE RLINE COM DADOS ONSITE SINTETICOS
   MODELOPT   DFAULT CONC
   AVERTIME   PERIOD
   POLLUTID   OTHER
   RUNORNOT   RUN
CO FINISHED

SO STARTING
   LOCATION   HWY1    RLINE  0.0  0.0  1000.0  0.0
   SRCPARAM   HWY1   0.001  0.0   20.0
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

### 5.2 Fonte e grade

`LOCATION <id> RLINE XSB YSB XSE YSE` define o segmento. Em `SRCPARAM`:

- `TEMP(1)` é `QS`, emissão por área em g/(s.m²);
- `TEMP(2)` é a altura de liberação em m;
- `TEMP(3)` é a largura em m;
- `TEMP(4)`, opcional, é o sigma-z inicial.

O AERMOD calcula `QEMIS = QS * WIDTH`. No caso canônico,
`0,001 * 20 = 0,02 g/(s.m)`.

`GRIDCART RCART XYINC 0.0 26 40.0 -300.0 31 20.0` gera X de 0 a 1000 m e Y de
-300 a 300 m, totalizando 806 receptores.

### 5.3 Wrapper

```bash
bash scripts/run_aermod.sh \
  Caso_Pipeline/rodada_aermod \
  build/aermod/aermod \
  Caso_Pipeline/controles_aermod/RLINE_TEST.INP \
  Caso_Pipeline/dados_aermet
```

O wrapper copia controle e meteorologia para seu workspace, remove relatórios e
plots antigos do staging, preserva o exit code e exige
`AERMOD Finishes Successfully` e um `CONC_PLOT.PLT` com assinatura válida. O
timeout padrão é 1800 s, configurável por `AERMOD_TIMEOUT_SECONDS`.

## 6. RLINE standalone

O caso usa a mesma fonte, emissão, meteorologia e grade do AERMOD:

- `Source_Road.txt`: fonte de 0 a 1000 m e `Emis = 0,02 g/(m.s)`;
- `Receptor_Road.txt`: os mesmos 806 receptores;
- `Line_Source_Inputs.txt`: modo numérico, total pluma + meandro, média diária,
  saída horária única e largura de 20 m;
- `ONSITE.SFC`: fornecido pelo AERMET.

Execução isolada com a variante corrigida padrão:

```bash
bash scripts/run_rline.sh \
  Caso_Pipeline/rodada_rline \
  build/rline-patched/RLINEv1_2_patched.x \
  Caso_Pipeline/dados_aermet/ONSITE.SFC
```

O terceiro argumento é opcional. Quando fornecido, o wrapper o copia como
`ONSITE.SFC` e reescreve apenas a cópia do controle no workspace. Ele valida os
arquivos referenciados, rejeita caminho de saída que escape do workspace e
publica o CSV horário e, quando gerado, o CSV diário. O timeout padrão é 1800 s,
configurável por `RLINE_TIMEOUT_SECONDS`.

Para uma comparação explícita com o upstream original, informe
`build/rline-original/RLINEv1_2_gfortran.x`. Essa escolha nunca é implícita.

## 7. Parsing, merge e gráficos

O pacote `rline_pipeline` é a implementação canônica do pós-processamento.

O parser AERMOD exige oito linhas de cabeçalho, dez colunas, média `PERIOD`,
`NHRS=120`, coordenadas únicas e a grade completa. O parser RLINE exige o
cabeçalho e as colunas esperadas, lê todas as linhas inclusive a última, rejeita
sentinelas negativas, verifica chaves de período únicas e exige exatamente 120
períodos por receptor. Ano, dia juliano e hora são validados pelo calendário;
horas AERMOD calm ou missing são aceitas somente com concentração zero.

A média temporal RLINE é combinada ao AERMOD por merge bijetivo
`validate="one_to_one"`. Não há arredondamento de coordenadas; a tolerância
padrão de 0,001 m só é aceita quando o mapeamento permanece unívoco nos dois
sentidos.

Os gráficos corrigidos:

- criam a matriz por `pivot(index="Y", columns="X")`, sem depender da ordem das
  linhas;
- desenham a rodovia entre seus endpoints reais;
- selecionam a coluna X de grade mais próxima do `transecto_x` válido;
- mostram Y no eixo do transecto perpendicular;
- calculam e rotulam `R²` global e no trecho real, sem trocar a métrica por uma
  razão.

Saídas canônicas:

```text
Caso_Pipeline/graficos/conc_periodo_rline.png
Caso_Pipeline/graficos/conc_aermod_vs_rline.png
```

## 8. Resultados históricos e resultados novos

Os resultados já versionados foram gerados pelo fluxo histórico com o RLINE
standalone original, antes de a variante corrigida se tornar o padrão dos
wrappers. Eles são preservados como baseline histórica e não comprovam a
variante de uma execução nova sem o respectivo manifesto.

Para a grade histórica completa de 806 receptores:

| Métrica | Valor histórico |
|---|---:|
| máximo AERMOD | 48 966,604 µg/m³ |
| máximo RLINE original na grade | 154 045,225 µg/m³ |
| correlação log | 0,9790 |
| R² log-log | 0,9584 |
| razão mediana AERMOD/RLINE | 0,643 |

O valor **153 272,168 µg/m³** registrado na documentação antiga não é o máximo
global: é a concentração histórica do RLINE original no ponto do transecto
`X=600 m, Y=0`. O máximo da grade histórica ocorre em outro receptor e é
154 045,225 µg/m³.

Uma execução atual de `scripts/run_pipeline.sh` usa o RLINE corrigido e deve ser
identificada pelo log e manifesto novos. Não compare números históricos e novos
sem registrar a variante.

## 9. Casos configurados e regressão científica

`bash scripts/run_todos_casos.sh` descobre os quatro `config.json`, regenera os
inputs, executa cada caso com AERMOD e RLINE corrigido, pós-processa, gera
`casos/comparativo_geral.png` e roda T1-T8. A execução é sequencial por padrão;
`MAX_PARALLEL_CASES` define um limite positivo de paralelismo. Cada etapa de um
caso usa 7200 s por padrão, e o lote completo tem orçamento de 21600 s.

Para a regressão completa:

```bash
make scientific-regression
RUN_FULL_PIPELINE=1 make scientific-regression
```

Com `RUN_FULL_PIPELINE=1`, a etapa adicional executa primeiro o pipeline
canônico completo, incluindo AERMET Stages 1/2, e depois os quatro casos
configurados. Em seguida, o relatório permite distinguir as comparações EPA e
as variantes executadas.

Máximas diferenças relativas observadas para o RLINE corrigido contra os
goldens:

| Caso | Observado | Limite |
|---|---:|---:|
| Example Case | 1,789152% | 1,9% |
| CALTRANS | 0,523329% | 0,55% |
| Idaho Falls | 0,088408% | 0,095% |
| Raleigh | 0,314472% | 0,33% |

Todos estão dentro dos limites definidos em `scripts/scientific_regression.py`.

## 10. Referências no código

| Local | Responsabilidade |
|---|---|
| `Makefile` | builds isolados e alvos de teste/qualidade/regressão |
| `scripts/lib/run_common.sh` | lock, staging, timeout, publicação, log e manifesto |
| `rline_pipeline/parsing.py` | parsers AERMOD/RLINE estritos |
| `rline_pipeline/analysis.py` | agregação, merge e métricas |
| `rline_pipeline/plotting.py` | mapas, transectos e comparativos |
| `setup.f` | parsing do controle AERMOD |
| `reset.f` | leitura de `GRIDCART` |
| `soset.f` | leitura de `LOCATION` e `SRCPARAM` RLINE |
| `rline.f` | implementação RLINE do AERMOD v26135 |
| `patches/rline-v1.2/` | proveniência e correções do standalone |
