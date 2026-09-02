# R-LINE v1.2 - Compilação e Uso

Este documento descreve as variantes RLINE existentes no repositório, o build
isolado, a execução transacional, os casos EPA e a preparação de um estudo novo.

## 1. Pré-requisitos

| Requisito | Uso | Verificação |
|---|---|---|
| Python 3.11 ou superior | pacote, testes e regressão | `python3 --version` |
| GNU Fortran | compilação | `gfortran --version` |
| GNU Make | orquestração | `make --version` |
| `patch` e `sha256sum` | preparação da variante corrigida | `patch --version` |
| `flock` e `setsid` | lock e controle do grupo de processos | `command -v flock setsid` |

Instale o pacote Python e as dependências declaradas:

```bash
python3 -m venv .venv
. .venv/bin/activate
bash .github/scripts/install-python-deps.sh
```

O helper fixa `uv==0.12.2` e exporta `uv.lock` com `--frozen`. A instalação
direta com `python -m pip install -e '.[dev]'` não congela a resolução.

O código RLINE é Fortran e não depende de biblioteca científica externa. O
ambiente historicamente usado pelo projeto é Ubuntu 22.04, x86-64, GNU Fortran
11.4 e GNU Make 4.3. A CI usa Ubuntu 22.04 e registra as versões efetivamente
instaladas.

## 2. Variantes do RLINE

O repositório separa explicitamente:

| Variante | Origem | Finalidade |
|---|---|---|
| original | cópia de `RLINE_v1_2.Source/v1_2/` | reprodução e diagnóstico do upstream |
| corrigida release | upstream + oito patches | padrão dos wrappers e das regressões |
| corrigida debug | mesmos patches + checks de runtime | diagnóstico numérico e de memória/I/O |

Os binários são:

```text
build/rline-original/RLINEv1_2_gfortran.x
build/rline-patched/RLINEv1_2_patched.x
build/rline-patched-debug/RLINEv1_2_patched_debug.x
```

Executáveis históricos rastreados nas distribuições não são selecionados pelos
wrappers.

## 3. Compilação

Execute os builds a partir da raiz:

```bash
make rline-original
make rline-release
make rline-debug
```

Ou compile AERMET, AERMOD, RLINE original e RLINE corrigido release de uma vez:

```bash
make models
```

Todos os artefatos ficam em `build/`. `make clean` remove essa árvore
reconstruível sem limpar as árvores upstream.

### 3.1 Original

O alvo `rline-original` copia os 29 arquivos `.f90` e
`Makefile.gfortran` para `build/rline-original/` e compila a cópia com:

```text
-O1 -Wall -fbounds-check
```

O snapshot em `RLINE_v1_2.Source/v1_2/` permanece sem objetos ou executáveis
novos.

### 3.2 Corrigido release e debug

Antes de preparar as fontes corrigidas, o `Makefile` executa:

```bash
sha256sum --check --strict patches/rline-v1.2/UPSTREAM_SHA256.txt
```

O manifesto cobre os 29 fontes Fortran e o `Makefile.gfortran`. Depois da
verificação, os oito patches são aplicados com `--fuzz=0` somente a uma cópia em
`build/`:

1. inicialização e validação da velocidade efetiva;
2. geometria robusta para vento paralelo, convergência e desalocação;
3. índice explícito de rodovia deprimida e limite analítico inicializado;
4. validação meteorológica, de I/O e de alocação;
5. validação do arquivo de controle;
6. validação de fontes e receptores;
7. verificação das saídas e das médias diárias;
8. suporte a caminhos de arquivo longos.

Release usa `-O2` com warnings e interfaces implícitas diagnosticadas. Debug usa
`-O0 -g3`, `-fcheck=all`, backtrace, inicialização sentinela e
`-ffpe-trap=invalid,zero,overflow`. Cada diretório recebe um `BUILD-INFO.txt`
com variante, flags, compilador e checksums.

## 4. Como executar

O programa RLINE não recebe argumentos. Ele lê `Line_Source_Inputs.txt` do
diretório corrente. O método recomendado é o wrapper:

```bash
bash scripts/run_rline.sh [diretorio_do_caso] [binario] [meteorologia.sfc]
```

Exemplo com todos os padrões do caso canônico:

```bash
make rline-release
bash scripts/run_rline.sh
```

Sem argumentos, são usados:

```text
diretório: Caso_Pipeline/rodada_rline
binário:   build/rline-patched/RLINEv1_2_patched.x
```

O terceiro argumento, quando informado, é copiado para o workspace como
`ONSITE.SFC`; apenas a cópia temporária do controle é ajustada.

### 4.1 Garantias do wrapper

`run_rline.sh`:

- aceita caminhos absolutos ou relativos à raiz, inclusive com espaços;
- valida controle, fonte, receptores, meteorologia e caminho de saída;
- impede duas execuções simultâneas no mesmo destino com `flock`;
- executa em workspace exclusivo sem saídas antigas;
- preserva o exit code do modelo;
- encerra todo o grupo com `TERM` e `KILL` em timeout/interrupção;
- exige assinatura e cabeçalho numérico RLINE no CSV novo;
- substitui atomicamente cada output validado por um temporário adjacente e
  reverte o conjunto em falha tratada de publicação ou manifesto;
- grava log e manifesto JSON exclusivos em `<caso>/logs/`.

Os vários arquivos publicados não formam um snapshot atômico único para
leitores sem lock, e não há journal durável contra `SIGKILL` ou falha de energia.

O timeout padrão é 1800 s. Ajuste-o com `RLINE_TIMEOUT_SECONDS` ou
`RUN_TIMEOUT_SECONDS`; ajuste o período entre `TERM` e `KILL` com
`RUN_KILL_GRACE_SECONDS`.

### 4.2 Execução direta para diagnóstico

Para reproduzir explicitamente o comportamento original em uma cópia
descartável do caso:

```bash
cd /caminho/para/a-copia-do-caso
/caminho/do/projeto/build/rline-original/RLINEv1_2_gfortran.x
```

Esse modo não fornece lock, timeout, publicação transacional, log exclusivo nem
manifesto. Não o use sobre os diretórios de referência.

## 5. Arquivos de entrada e saída

O controle posicional referencia quatro itens:

1. arquivo de fontes;
2. arquivo de receptores;
3. arquivo meteorológico `.sfc`;
4. nome base da saída.

Ele também define limite de integração, fator de altura de deslocamento,
componentes de concentração, média diária, saída horária e opções beta.

### 5.1 Fontes

Cada fonte possui 18 campos:

```text
Group X_b Y_b Z_b X_e Y_e Z_e dCL sigmaz0 #lanes Emis
      Hw1 dw1 Hw2 dw2 Depth Wtop Wbottom
```

`Emis` é a emissão por comprimento em g/(m.s) quando se deseja saída em µg/m³.
No pipeline AERMOD/RLINE, ela deve ser coerente com:

```text
Emis_RLINE = QS_AERMOD * WIDTH_AERMOD
```

A variante corrigida rejeita números não finitos, fonte de comprimento zero,
segunda barreira solicitada e rodovia deprimida com larguras inválidas.

### 5.2 Receptores

Após três linhas de cabeçalho, cada registro contém `X Y Z` em metros. A
variante corrigida exige ao menos um receptor e coordenadas finitas.

### 5.3 Meteorologia

O RLINE lê o arquivo de superfície AERMET. Os campos obrigatórios incluem data e
hora, `Hs`, `u*`, `w*`, alturas CBL/SBL, `Lmo`, `z0`, velocidade/direção do vento
e altura de referência.

Na variante corrigida, um período inválido é marcado com concentração `-99` e
um aviso objetivo. O pipeline estrito rejeita essa sentinela quando o caso exige
todos os períodos válidos.

### 5.4 Saídas

| Opção | Arquivo |
|---|---|
| horários em um único arquivo (`A`) | nome definido no controle |
| horários por mês (`M`) | `*_MM-YY.csv` |
| média diária (`Y`) | `*_DailyAve.csv` |

O CSV horário contém:

```text
Year, Julian_Day, Hour, X-Coordinate, Y-Coordinate, Z-Coordinate, C_<grupo>...
```

O arquivo não possui rodapé. A vírgula final é aceita apenas como uma coluna
vazia opcional. O parser central lê a última observação e exige o conjunto
completo de períodos para cada receptor.

## 6. Example Case

Pasta de referência:
`RLINE_v1_2.Example_Cases/Example_case/`.

O caso possui oito fontes em dois grupos, 196 receptores e dez períodos. As
saídas golden têm 1960 linhas horárias e 196 linhas diárias.

Não execute sobre a pasta de referência. Use a regressão automatizada:

```bash
make models
python3 scripts/scientific_regression.py --case example-case
```

Ou copie o caso para uma pasta descartável e use `run_rline.sh` com caminho
absoluto. `Source_Example.txt` usa endpoints; `Source_Example_dCL.txt` descreve
a mesma geometria por centro e deslocamento.

## 7. Dados de avaliação EPA

Os três conjuntos estão em
`RLINE_v1_2.Evaluation_Data/Evaluation_data/`:

| Caso | Fontes/receptores/períodos | Golden |
|---|---|---|
| CALTRANS | 4 fontes, 7 receptores, 56 horas | `CALTRANS99_Output.csv`, 392 linhas |
| Idaho Falls | fonte de linha longa, 7 receptores, 31 períodos | `IF2009_Output_INF_Case1235.csv`, 217 linhas |
| Raleigh | 8 fontes, 2 receptores, 624 registros meteorológicos | `Ral2006_Output.csv`, 1248 linhas |

A regressão do repositório executa o RLINE corrigido em diretórios
temporários e compara chaves ordenadas e todas as colunas de concentração:

```bash
make scientific-regression
```

| Caso | máxima diferença relativa observada | limite documentado |
|---|---:|---:|
| Example Case | 1,789152% | 1,9% |
| CALTRANS | 0,523329% | 0,55% |
| Idaho Falls | 0,088408% | 0,095% |
| Raleigh | 0,314472% | 0,33% |

Todos estão dentro dos limites. A tolerância absoluta é `1e-6` unidade de
saída, usada perto de golden zero. O script executa ainda a variante original
duas vezes por padrão para diagnosticar não determinismo, mas o resultado
original não é requisito de aprovação da variante corrigida.

Os relatos antigos de concordância praticamente exata pertencem às execuções
históricas da variante original. Eles continuam como histórico e não substituem
os limites atuais da variante corrigida.

## 8. Uso com dados de um novo estudo

### 8.1 Sistema de coordenadas

Use o mesmo sistema métrico para fontes e receptores. Pode ser UTM ou um sistema
local, desde que X, Y e Z sejam coerentes.

### 8.2 Meteorologia

Gere o `.sfc` com AERMET sempre que possível. O pipeline canônico demonstra
Stages 1 e 2 com dados ONSITE:

```bash
make aermet
bash scripts/run_aermet.sh <diretorio_dos_controles_e_dados>
```

Não trate apenas a existência do `.sfc` como sucesso. Verifique os relatórios do
AERMET e os domínios físicos exigidos pelo RLINE corrigido.

### 8.3 Fontes

Para cada trecho:

1. informe início e fim em X, Y e Z;
2. defina `sigmaz0` e o número de faixas;
3. converta a emissão para g/(m.s), quando aplicável;
4. atribua grupos que devam ser somados na saída;
5. deixe parâmetros de barreira/depressão em zero quando não forem usados.

Conversão comum:

```text
Emis (g/m/s) = veículos_por_hora * fator_emissão (g/km)
               / (1000 m/km * 3600 s/h)
```

### 8.4 Receptores

Liste pontos de interesse ou uma grade com X, Y e Z. Para casos comparados ao
AERMOD, gere os dois conjuntos a partir da mesma configuração para garantir
identidade de coordenadas.

### 8.5 Configuração versionada

Para cenários do pipeline, prefira `config.json` schema v1 e gere os insumos:

```bash
python3 scripts/gerar_caso.py casos/<nome>/config.json
bash scripts/run_caso.sh casos/<nome>
```

O gerador valida finitude, pelo menos dois pontos distintos em cada eixo, limite
de 1.000.000 de receptores, interseção da rodovia com a grade, transecto e
emissão. Ele produz deterministicamente o controle AERMOD, a fonte, os
receptores, o controle RLINE e os metadados, e invalida resultados derivados
quando um input efetivo muda.

### 8.6 Pós-processamento

```bash
python3 scripts/postprocess_caso.py casos/<nome>
python3 scripts/teste_casos.py casos/<nome>
```

O parser exige períodos e receptores completos, faz merge `one_to_one` e gera
gráficos somente depois que o caso inteiro foi validado.

## 9. Opções beta

| Opção | Uso | Estado da variante corrigida |
|---|---|---|
| analítica | aproximação mais rápida | limite `xwd` inicializado e fonte nula rejeitada |
| barreira/via deprimida | configurações próximas à fonte | índice de fonte corrigido; segunda barreira rejeitada |
| largura não nula | rodovia representada por uma fonte | valor finito validado |

Essas correções não transformam as opções beta em funcionalidades regulatórias.
Registre a variante e valide o cenário específico.

## 10. Verificação e referências

```bash
make test
make quality
make scientific-regression
```

- Conceitos e formatos: [`GUIA_RLINE.md`](GUIA_RLINE.md).
- Pipeline AERMET/AERMOD/RLINE:
  [`GUIA_PIPELINE_AERMET_AERMOD_RLINE.md`](GUIA_PIPELINE_AERMET_AERMOD_RLINE.md).
- Reprodutibilidade: [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md).
- Manual distribuído: `RLINE_UserGuide_11-13-2013.pdf`.
- Implementação e tolerâncias: `scripts/scientific_regression.py`.
