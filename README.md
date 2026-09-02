# Pipeline AERMET, AERMOD e RLINE

Pipeline reproduzível para modelagem de dispersão de emissões rodoviárias. O
repositório compila AERMET v26135, AERMOD v26135 e duas variantes do RLINE v1.2,
executa os modelos em áreas temporárias e valida os resultados antes de
publicá-los.

A fonte `RLINE` apareceu como opção beta no AERMOD v19191, foi reformulada na
v23132 e passou à configuração regulatória na v24142. Este projeto usa AERMOD
v26135 e o compara com o RLINE v1.2 standalone histórico. São implementações e
épocas diferentes: a comparação é descritiva, não prova equivalência, aprovação
regulatória nem endosso da EPA.

## Estado atual

| Componente | Variante | Binário gerado |
|---|---|---|
| AERMET v26135 | fonte distribuída no repositório | `build/aermet/aermet` |
| AERMOD v26135 | fonte distribuída no repositório | `build/aermod/aermod` |
| RLINE v1.2 | upstream original, sem patches | `build/rline-original/RLINEv1_2_gfortran.x` |
| RLINE v1.2 | corrigido, release | `build/rline-patched/RLINEv1_2_patched.x` |
| RLINE v1.2 | corrigido, debug | `build/rline-patched-debug/RLINEv1_2_patched_debug.x` |

O `Makefile` da raiz compila cada modelo em uma árvore isolada sob `build/`.
Ele não grava objetos, módulos ou executáveis nas árvores de fonte. Os wrappers
usam por padrão os binários de `build/`; os binários históricos rastreados no
repositório não são usados implicitamente.

## Início rápido

Pré-requisitos: Linux, Python 3.11 ou superior, GNU Make, `gfortran`, `patch`,
`flock` e `setsid`. Para instalar o pacote Python e as ferramentas de
desenvolvimento:

```bash
python3 -m venv .venv
. .venv/bin/activate
bash .github/scripts/install-python-deps.sh
```

Esse helper fixa `uv==0.12.2`, resolve `uv.lock` com `--frozen`, instala as
dependências exportadas e então instala o projeto editável sem re-resolver o
ambiente. `python -m pip install -e '.[dev]'` continua disponível para
desenvolvimento exploratório, mas não é uma instalação congelada.

Compile os modelos e as variantes operacionais usadas pelo pipeline:

```bash
make models
```

`make models` gera AERMET, AERMOD, RLINE original e RLINE corrigido release.
O build de diagnóstico é separado:

```bash
make rline-debug
```

Execute o pipeline canônico, que inclui AERMET Stages 1 e 2, AERMOD, RLINE
corrigido e pós-processamento:

```bash
bash scripts/run_pipeline.sh
```

Execute ou valide os quatro casos parametrizados:

```bash
bash scripts/run_todos_casos.sh
python3 scripts/teste_casos.py
```

Os modelos podem levar vários minutos. Para não alterar resultados versionados,
rode pipelines completos em um worktree descartável, conforme
[`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md).

## Comandos principais

| Comando | O que verifica |
|---|---|
| `make models` | builds isolados de AERMET, AERMOD, RLINE original e RLINE corrigido release |
| `make model-provenance-check` | identidade SHA-256 dos snapshots locais AERMET, AERMOD e RLINE |
| `make rline-debug` | RLINE corrigido com checks, inicialização sentinela e traps IEEE |
| `make test` | suíte rápida, excluindo testes marcados como científicos |
| `make quality` | Ruff e sintaxe de todos os scripts Shell rastreados ou não ignorados |
| `make quality-report` | contrato JSON do painel em `build/reports/quality-summary.json` |
| `make example-data` | exemplo sintético 24 h e grade 5 x 5 em `build/examples/` |
| `make scientific-regression` | testes rápidos, casos versionados e regressões EPA em diretórios temporários |
| `RUN_FULL_PIPELINE=1 make scientific-regression` | acrescenta o pipeline canônico completo e, depois, os quatro casos configurados |
| `make clean` | remove somente a árvore reconstruível `build/` |

O relatório científico local é gravado por padrão em
`build/scientific-regression/scientific-regression-report.json`, com logs no
mesmo diretório de artefatos.

## Fluxo de dados

```text
ONSITE.MET
    |
    +-- AERMET Stage 1 (QA/QC) --> ONSITE_QAOUT.TXT
    |
    +-- AERMET Stage 2 (METPREP) --> ONSITE.SFC + ONSITE.PFL
                                          |
                     +--------------------+--------------------+
                     |                                         |
                     v                                         v
          AERMOD v26135, fonte RLINE              RLINE v1.2 corrigido
                 CONC_PLOT.PLT                 Output_*_Numerical.csv
                     |                                         |
                     +--------------------+--------------------+
                                          v
                         parsing, merge, métricas e gráficos
```

O pipeline canônico gera 120 horas de meteorologia sintética em três níveis
(10, 50 e 100 m). Os quatro casos reutilizam `ONSITE.SFC` e `ONSITE.PFL`, mas
regeneram deterministicamente seus controles, fontes e receptores a partir de
`config.json` antes de cada execução.

## Builds e patches do RLINE

`RLINE_v1_2.Source/v1_2/` permanece como snapshot upstream. Antes de preparar
uma variante corrigida, `make rline-release` ou `make rline-debug` executa
`sha256sum --check --strict patches/rline-v1.2/UPSTREAM_SHA256.txt`. Os oito
patches são aplicados, sem fuzz, somente a uma cópia em `build/`:

| Patch | Correção principal |
|---|---|
| `0001` | inicializa e valida a velocidade efetiva antes de `sigmaz` |
| `0002` | remove a singularidade geométrica para vento paralelo e trata convergência/alocação |
| `0003` | usa índice explícito na via deprimida e inicializa o limite analítico |
| `0004` | valida meteorologia, I/O e recursos críticos |
| `0005` | valida o arquivo de controle e suas opções |
| `0006` | valida fontes e receptores; rejeita fonte nula e segunda barreira não implementada |
| `0007` | verifica escrita/fechamento das saídas e alocações das médias diárias |
| `0008` | amplia os caminhos de entrada e saída aceitos pelo RLINE |

Cada build corrigido inclui `BUILD-INFO.txt` com variante, flags, compilador e
checksums do executável e dos patches. O build debug usa, entre outras opções,
`-fcheck=all`, `-finit-real=snan` e
`-ffpe-trap=invalid,zero,overflow`.

## Execução transacional

Os wrappers `run_aermet.sh`, `run_aermod.sh`, `run_rline.sh`, `run_caso.sh` e
`run_pipeline.sh` compartilham `scripts/lib/run_common.sh`. Eles:

- normalizam caminhos absolutos ou relativos à raiz;
- adquirem um lock não bloqueante por componente e destino;
- copiam entradas para um workspace exclusivo ao lado do destino;
- removem do workspace saídas potencialmente antigas;
- executam cada comando em um novo grupo de processos;
- aplicam timeout, `TERM`, período de graça e `KILL` ao grupo inteiro;
- validam exit code, assinatura e estrutura mínima dos artefatos;
- copiam cada saída validada para um temporário no filesystem do destino e
  substituem cada arquivo atomicamente;
- mantêm backups até o manifesto ser gravado e revertem o conjunto quando a
  publicação ou o manifesto falha;
- geram log e manifesto JSON exclusivos em `<destino>/logs/`.

Uma publicação com vários caminhos não é um único snapshot atômico: leitores
sem lock podem observar substituições intermediárias. Os locks serializam os
escritores, e falhas tratadas são revertidas; `SIGKILL` e falha de energia não
são uma transação durável com journal.

O manifesto usa `schema_version: 1` e registra commit/estado do Git, duração,
exit codes, timeout, checksum do executável, inputs, outputs e log. Os timeouts
podem ser ajustados por `RUN_TIMEOUT_SECONDS` ou pelas variáveis específicas
`AERMET_TIMEOUT_SECONDS`, `AERMOD_TIMEOUT_SECONDS` e
`RLINE_TIMEOUT_SECONDS`. Os wrappers isolados usam 1800 s por comando de modelo;
`run_pipeline.sh` e `run_caso.sh` usam 7200 s por etapa. O lote
`run_todos_casos.sh` usa um orçamento agregado de 21600 s e execução sequencial
por padrão; `MAX_PARALLEL_CASES` habilita paralelismo limitado.

Interfaces principais:

```bash
bash scripts/run_aermet.sh [dir_dados] [bin_aermet]
bash scripts/run_aermod.sh [dir_rodada] [bin_aermod] [control.inp] [dir_meteorologia]
bash scripts/run_rline.sh [dir_rodada] [bin_rline] [arquivo.sfc]
bash scripts/run_caso.sh <dir_caso> [transecto_x]
```

Sem argumentos de binário, os três primeiros wrappers selecionam os executáveis
de `build/`, e o RLINE selecionado é a variante corrigida release.

## Pacote Python e contratos de dados

O pacote instalável `rline_pipeline` concentra a lógica antes duplicada nos
scripts:

- `config.py`: carrega o schema JSON v1, aplica restrições físicas e gera a
  grade com aritmética decimal;
- `generation.py`: gera controles AERMOD, fonte, receptores, controle RLINE e
  metadados de forma determinística, e invalida resultados derivados quando um
  input efetivo do modelo muda;
- `parsing.py`: valida cabeçalhos, colunas, finitude, coordenadas, horas e
  cardinalidade das saídas AERMOD/RLINE, sem descartar a última observação;
- `analysis.py`: agrega o RLINE e faz merge bijetivo `one_to_one`, sem arredondar
  coordenadas;
- `plotting.py`: usa `pivot(Y, X)`, a geometria real da rodovia, transecto em Y
  no X configurado e rótulos de métricas coerentes.

O schema está em
`rline_pipeline/schemas/case-config-v1.schema.json`. Campos desconhecidos,
números não finitos, eixos com menos de dois pontos, coordenadas repetidas após
conversão para `float`, grades acima de 1.000.000 de receptores, rodovia fora da
grade e transecto fora da interseção rodovia/grade são rejeitados.

## Casos parametrizados

| Caso | Rodovia | `QS` | Largura | Grade | Questão |
|---|---:|---:|---:|---:|---|
| `caso1_referencia` | 1000 m | 0,001 | 20 m | 26 x 31 | referência |
| `caso2_rodovia_curta` | 300 m | 0,001 | 20 m | 21 x 21 | trecho urbano curto |
| `caso3_emissao_alta` | 1000 m | 0,005 | 20 m | 21 x 21 | emissão cinco vezes maior |
| `caso4_rodovia_larga` | 1000 m | 0,001 | 40 m | 21 x 21 | largura duas vezes maior |

Os resultados versionados abaixo pertencem ao fluxo histórico com o RLINE
original. Eles são preservados como baseline; uma execução nova dos wrappers
usa o RLINE corrigido e deve ser identificada por seu manifesto.

| Caso | máx. AERMOD (µg/m³) | máx. RLINE original (µg/m³) | R²(log) no trecho | razão mediana AERMOD/RLINE |
|---|---:|---:|---:|---:|
| caso 1 | 48 966,6 | 154 045,2 | 0,9584 | 0,643 |
| caso 2 | 48 378,6 | 150 076,9 | 0,9790 | 0,499 |
| caso 3 | 244 833,0 | 770 226,2 | 0,9638 | 0,581 |
| caso 4 | 90 142,0 | 256 727,6 | 0,9551 | 0,608 |

## Verificação T1-T8

`python3 scripts/teste_casos.py` descobre todos os casos pela presença de
`config.json`; um caso sem resultado não é omitido.

| Teste | Contrato atual |
|---|---|
| T1 | relatório AERMOD concluído, zero erros fatais, horas, grade e receptores completos |
| T2 | RLINE com todos os receptores e exatamente todos os períodos esperados |
| T3 | merge AERMOD/RLINE bijetivo e completo (`one_to_one`) |
| T4 | concentrações finitas e não negativas; zeros são contabilizados |
| T5 | informação: correlação e R² em log, com número de pares positivos |
| T6 | informação: FB, NMSE e FAC2 |
| T7 | informação: mediana e percentil 95 do erro log absoluto |
| T8 | informação: FB dos 25 maiores valores e concordância/discordância de zeros |

Somente T1–T4 são gates estruturais. T5–T8 caracterizam a intercomparação entre
modelos e não têm limiar de aprovação pós-hoc. A política versionada está em
`rline_pipeline/policies/validation-policy-v1.json`.

## Regressão EPA

A regressão científica executa cada caso em diretório temporário, compara todas
as chaves e colunas de concentração com os arquivos golden e nunca substitui os
goldens. As variantes corrigida e original são executadas duas vezes por padrão;
a original é diagnóstica, enquanto a aprovação exige que todas as repetições da
corrigida permaneçam determinísticas e dentro dos limites.

| Caso | máxima diferença relativa observada | limite |
|---|---:|---:|
| Example Case | 1,789152% | 1,9% |
| CALTRANS | 0,523329% | 0,55% |
| Idaho Falls | 0,088408% | 0,095% |
| Raleigh | 0,314472% | 0,33% |

Todos os valores observados estão dentro dos limites documentados em
`scripts/scientific_regression.py`.

## Integração contínua

- `.github/workflows/ci.yml`: em push, pull request e execução manual, roda a
  suíte rápida, valida Shell e recompila AERMET, AERMOD e as variantes original,
  corrigida release e corrigida debug.
- `.github/workflows/scientific-regression.yml`: semanal e manual, cria um
  worktree isolado, executa a regressão completa com `RUN_FULL_PIPELINE=1`,
  verifica que resultados versionados não mudaram e publica apenas diagnósticos.

## Estrutura principal

```text
Makefile                         builds e alvos de verificação
pyproject.toml                   pacote e dependências Python
rline_pipeline/                  schema, geração, parsing, análise e gráficos
scripts/                         wrappers e interfaces de linha de comando
scripts/lib/run_common.sh        locks, timeout, publicação, logs e manifestos
patches/rline-v1.2/              checksums, oito patches e build corrigido
tests/                           testes rápidos e fixtures
.github/workflows/               CI rápida e regressão científica
Caso_Pipeline/                   pipeline canônico
casos/                           quatro cenários parametrizados
RLINE_v1_2.Source/v1_2/          snapshot original do RLINE
RLINE_v1_2.Example_Cases/        Example Case e golden
RLINE_v1_2.Evaluation_Data/      CALTRANS, Idaho Falls e Raleigh
build/                           artefatos locais ignorados pelo Git
```

## Documentação

- [`GUIA_PIPELINE_AERMET_AERMOD_RLINE.md`](GUIA_PIPELINE_AERMET_AERMOD_RLINE.md):
  arquivos e etapas do pipeline canônico.
- [`GUIA_RLINE.md`](GUIA_RLINE.md): conceitos e formatos do RLINE.
- [`PLANO_Compilacao_Uso_RLINE.md`](PLANO_Compilacao_Uso_RLINE.md): variantes,
  compilação e execução do standalone.
- [`PIPELINE_IMPLEMENTACAO.txt`](PIPELINE_IMPLEMENTACAO.txt): especificação
  operacional detalhada.
- [`PLANO_MELHORIAS_PROJETO.md`](PLANO_MELHORIAS_PROJETO.md): diagnóstico
  histórico e status de implementação.
- [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md): política de
  reprodutibilidade e goldens.
- [`docs/GUIA_PROJETO.md`](docs/GUIA_PROJETO.md): arquitetura, execução segura,
  limitações e manutenção.
- [`docs/FORMATOS_DE_ENTRADA.md`](docs/FORMATOS_DE_ENTRADA.md): contrato do
  `config.json` e formatos de entrada dos três modelos.
- [`docs/VALIDACAO_CIENTIFICA.md`](docs/VALIDACAO_CIENTIFICA.md): classes de
  evidência, métricas e critérios para validação de campo.
- [`CONTRIBUTING.md`](CONTRIBUTING.md): regras para contribuições.
- [`NOTICE`](NOTICE): proveniência e avisos; consulte também os termos presentes
  em cada distribuição upstream.
