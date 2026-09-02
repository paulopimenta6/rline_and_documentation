# R-LINE — Guia de Entendimento

> **R-LINE** (Research LINE source model) é um modelo computacional de dispersão de poluentes no ar, desenvolvido pela Agência de Proteção Ambiental dos Estados Unidos (US EPA). Esta documentação foi escrita para que qualquer pessoa — mesmo sem experiência com modelagem atmosférica — entenda o que ele é, como funciona e o que existe neste projeto.

---

## 1. O que é o R-LINE? 🛣️ → 💨

Imagine uma avenida movimentada. Cada carro que passa solta gases e partículas (poluentes). O vento "carrega" essa fumaça para os lados, formando uma nuvem que se espalha pelo ar. As pessoas que moram perto da avenida respiram parte desse poluente.

O **R-LINE** é um programa de computador que **calcula, para cada hora do dia, quanto de poluente uma pessoa em determinado local vai respirar** por causa do tráfego de uma ou mais avenidas (as chamadas "fontes de linha").

Ele foi criado para **pesquisa** — por exemplo, para estudar a poluição perto de rodovias, avaliar o efeito de barreiras de ruído, ou comparar com medições feitas em campo. **Não é um modelo regulatório oficial** (ou seja, não serve como instrumento legal para licenciamento), mas é uma ferramenta científica muito utilizada.

**Em resumo:**

| O que entra (entrada) | O que o modelo faz | O que sai (saída) |
|---|---|---|
| Rodovias (posição, emissão de poluente) | Calcula como o vento e a turbulência do ar espalham o poluente | Concentração do poluente em cada receptor (µg/m³) |
| Pontos onde queremos saber a concentração ("receptores") | Soma a contribuição de todas as avenidas | Para cada hora e cada receptor |
| Meteorologia (vento, estabilidade, etc.) | Aplica fórmulas de dispersão atmosférica | |

---

## 2. Como o modelo funciona? (Explicação simples)

O R-LINE usa uma fórmula clássica de dispersão atmosférica (a **formulação Gaussiana em estado estacionário**). Não se assuste com o nome — a ideia é simples:

1. **Uma avenida inteira é "fatia" em vários trechinhos**, como se cada trechinho fosse uma fonte pontual (um "cano" soltando fumaça). O modelo soma a contribuição de todos os trechinhos para obter o efeito da avenida inteira. A quantidade de fatias é escolhida automaticamente pelo programa, de forma a garantir precisão (com um critério de erro configurável).

2. **O vento e a atmosfera são levados em conta.** O R-LINE usa meteorologia de superfície (um arquivo no formato do AERMET, o pré-processador meteorológico usado pelo modelo AERMOD). Desse arquivo ele aproveita, por exemplo: velocidade e direção do vento, altura de mistura da camada limite, comprimento de Monin-Obukhov (mede estabilidade térmica do ar), velocidade de atrito, etc.

3. **O resultado tem duas partes**, somadas para dar a concentração total:
   - **Pluma direta** (`P`): o poluente que vai "arrastado" na direção do vento.
   - **Meandro** (`M`): em dias de vento fraco, o poluente se espalha em todas as direções de forma irregular — o modelo também calcula essa parcela.
   - **Total** (`T`): pluma + meandro.

4. **Recursos importantes do modelo:**
   - Perfil de vento calculado pela teoria de semelhança de **Monin-Obukhov** (calcula como o vento muda com a altura perto do solo).
   - **Velocidade do vento "ponderada pela pluma"** — o vento que efetivamente transporta o poluente é calculado na altura média da nuvem.
   - Novas formulações de espalhamento vertical e lateral baseadas em experimentos de campo e túnel de vento.

### O que o R-LINE **NÃO** faz (limitações):

- ❌ **Terreno plano apenas** — não considera variações de elevação do terreno.
- ❌ **Somente fontes de linha** (rodovias) — não modela fontes de área, volume ou pontuais.
- ❌ É um modelo de **estado estacionário** — calcula hora a hora, não a evolução contínua no tempo.
- ❌ Fontes e receptores devem estar a, no mínimo, **1 metro** de distância (o modelo ajusta automaticamente).
- ⚠️ No upstream original, as opções analítica, de barreira e de rodovia
  deprimida são marcadas como **beta**. A variante corrigida deste repositório
  adiciona validações e correções, mas rejeita explicitamente uma segunda
  barreira, que o cálculo v1.2 não implementa.

---

## 3. Estrutura do projeto

```
rline_and_documentation/
├── RLINE_UserGuide_11-13-2013.pdf        ← manual do RLINE v1.2
├── RLINE_v1_2.Source/v1_2/               ← snapshot upstream preservado
│   ├── *.f90                             ← 29 arquivos Fortran
│   └── Makefile.gfortran                 ← build da variante original
├── patches/rline-v1.2/
│   ├── UPSTREAM_SHA256.txt               ← identidade dos 29 fontes + Makefile
│   ├── 0001-...patch a 0008-...patch     ← oito correções auditáveis
│   └── Makefile                          ← staging e builds corrigidos
├── build/                                ← artefatos locais, ignorados pelo Git
│   ├── rline-original/
│   ├── rline-patched/
│   └── rline-patched-debug/
├── RLINE_v1_2.Example_Cases/Example_case/
├── RLINE_v1_2.Evaluation_Data/Evaluation_data/
│   ├── CALTRANS_RLINE/
│   ├── IdahoFalls_RLINE/
│   └── Raleigh_RLINE/
├── rline_pipeline/                       ← parsing, métricas e gráficos
└── scripts/                              ← wrappers e orquestração
```

Os executáveis antigos rastreados nas distribuições são preservados como
material histórico, mas não são o padrão dos wrappers.

### 3.1 Variantes construídas

```bash
make rline-original
make rline-release
make rline-debug
```

| Variante | Binário |
|---|---|
| upstream original | `build/rline-original/RLINEv1_2_gfortran.x` |
| corrigida release | `build/rline-patched/RLINEv1_2_patched.x` |
| corrigida debug | `build/rline-patched-debug/RLINEv1_2_patched_debug.x` |

O checksum do snapshot é validado antes da aplicação dos patches. As correções
são aplicadas somente em `build/`, e cada build corrigido grava
`BUILD-INFO.txt`.

### 3.2 Arquivos de código (resumo dos `.f90`)

| Arquivo | Função |
|---|---|
| `RLINE_Main.f90` | Programa principal: lê tudo, calcula e grava as saídas |
| `Data_Structures.f90`, `Line_Source_Data.f90` | Definem os tipos de dados e variáveis globais |
| `Read_Line_Source_Inputs.f90`, `Read_Met_Inputs.f90`, `Read_Receptors.f90`, `Read_Sources.f90` | Leem os 4 arquivos de entrada |
| `Numerical_Line_Source.f90`, `Point_Conc.f90`, `Meander.f90`, `Sigmay.f90`, `Sigmaz.f90`, `MOST_Wind.f90`, `Effective_Wind.f90`, `Compute_Met.f90` | Coração do cálculo: integram a linha, calculam pluma, meandro e espalhamento |
| `Analytical_Line_Source.f90`, `Analytical_Line_Parallel.f90` | Opção beta: solução analítica (mais rápida, menos precisa) |
| `Barrier_Displacement.f90`, `Depressed_Displacement.f90` | Opção beta: barreiras e rodovias deprimidas |
| `Write_Hourly_All.f90`, `Write_Hourly_by_Month.f90`, `Write_Daily_Ave.f90` | Escrevem os arquivos de saída |
| `RLINE_Validation.f90` | Adicionado pelo patch `0004` somente à árvore corrigida em `build/` |

---

## 4. Os 4 arquivos de entrada

O R-LINE usa **4 arquivos de texto**. Três deles são lidos pelo programa e o quarto (`Line_Source_Inputs.txt`) é o "painel de controle", onde você diz ao programa onde estão os outros arquivos e quais opções usar.

### 4.1 `Line_Source_Inputs.txt` — o painel de controle (nome fixo)

Exemplo real (do caso de exemplo):

```
User control file for RLINEv1_2
Source File Name
'Source_Example.txt'          ← nome do arquivo de fontes
Receptor File Name
'Receptor_Example.txt'        ← nome do arquivo de receptores
Input Met File
'Met_Example.sfc'             ← nome do arquivo de meteorologia
Receptor Output File
'Output_Example_Numerical.csv'← nome base dos arquivos de saída
Error_Limit (suggested 1.0e-03)
1.0e-03                       ← critério de convergência da integração
Ratio of displacement height to roughness length (fac_dispht)
5.0                           ← altura de deslocamento = 5 × z0
```

**Opções de saída (4):**

| Opção | O que controla | Valores |
|---|---|---|
| 1 | Que componente de concentração sai | `P` (pluma), `M` (meandro), `T` (total) |
| 2 | Média diária de 24 h | `Y` (sim) / `N` (não) |
| 3 | Arquivos horários | `A` (um arquivo só), `M` (um por mês), `N` (nenhum) |
| 4 | Suprimir avisos de proximidade fonte-receptor | `Y` / `N` |

**Opções beta (3):**

| Opção | O que faz |
|---|---|
| 1 | Usa a **solução analítica** em vez da numérica (mais rápida, menos precisa) |
| 2 | Ativa algoritmos de **barreira lateral e rodovia deprimida** |
| 3 | Ativa **largura inicial da pluma** (para simular rodovias largas como uma única fonte). Você também informa a **largura da faixa em metros** (ex.: `'Y' 3.6`) |

⚠️ Cuidado: se a média diária (opção de saída 2) for `N` e a saída horária
(opção de saída 3) também for `N`, o programa não gera arquivo de concentração.

### 4.2 Arquivo de fontes (ex.: `Source_Example.txt`)

Define as avenidas. Cada linha = uma pista/fonte. As 3 primeiras linhas são cabeçalho (ignoradas). 18 colunas:

| Col | Campo | O que é |
|---|---|---|
| 1 | `group` | Nome do grupo (até 40 caracteres). Fontes do mesmo grupo têm suas concentrações **somadas** na saída |
| 2–4 | `X_b, Y_b, Z_b` | Coordenadas (m) do **início** do trecho |
| 5–7 | `X_e, Y_e, Z_e` | Coordenadas (m) do **fim** do trecho |
| 8 | `dCL` | Distância (m) da pista ao centro da via. `0` = sem deslocamento. Positivo = leste/norte, negativo = oeste/sul |
| 9 | `sigmaz0` | Espalhamento vertical inicial (m). Recomenda-se ≈ altura média dos veículos × 1,7 / 2,15 |
| 10 | `#lanes` | Número de faixas (não precisa ser inteiro; cada faixa ≈ 3,5 m) |
| 11 | `Emis` | Taxa de emissão. Em **g/(m·s)** → resultado em **µg/m³**. Ou em **AADT** (veículos/dia), para aplicar fator depois |
| 12–18 | `Hw1 dw1 Hw2 dw2 Depth Wtop Wbottom` | Parâmetros de barreiras e rodovias deprimidas (só para opção beta 2). Preencher com `0` se não usar |

Linhas iniciadas com `!` são comentários e podem ser intercaladas. Exemplo real:

```
G1    -8.5 -500.0   1.0   -8.5  500.0   1.0    0      2.0    1.0   1.0    0    0    0    0      0    0        0
```

(Leia: pista do grupo G1, começando em (-8.5, -500, 1) e terminando em (-8.5, 500, 1), sem offset, σz0 = 2 m, 1 faixa, emissão de 1 g/(m·s), sem barreiras/depressões.)

**Duas maneiras de escrever as fontes:**
- **a)** Endpoints de cada pista (`Source_Example.txt`): você dá as coordenadas de cada pista.
- **b)** Centro + deslocamento (`Source_Example_dCL.txt`): você dá o centro da via e usa `dCL` para posicionar cada pista. Produz o **mesmo resultado**.

### 4.3 Arquivo de receptores (ex.: `Receptor_Example.txt`)

Define os pontos onde queremos saber a concentração. 3 linhas de cabeçalho, depois **uma linha por receptor** com `X, Y, Z` (metros):

```
  10    10  1.5
  10    20  1.5
  ...
```

### 4.4 Arquivo de meteorologia (ex.: `Met_Example.sfc`)

Arquivo no formato de superfície do **AERMET**. A primeira linha é cabeçalho. Cada linha seguinte representa um período (geralmente 1 hora) com valores separados por espaços/tabs. Os campos usados pelo R-LINE são:

| Campo | Significado |
|---|---|
| Ano, Mês, Dia, Dia Juliano, Hora | Identificação do período (não usados no cálculo, apenas repassados à saída) |
| `Hs` | Fluxo de calor sensível (W/m²) |
| `u*` | Velocidade de atrito (m/s) |
| `w*` | Escala de velocidade convectiva (m/s) |
| `CBL` / `SBL` | Altura da camada limite convectiva / estável (m) |
| `Lmo` | Comprimento de Monin-Obukhov (m) |
| `z0` | Rugosidade da superfície (m) |
| `Ws`, `Wd` | Velocidade (m/s) e direção (graus) do vento na altura de referência |
| `zref` | Altura de referência do vento (m) |

No upstream original, a hora é marcada como ausente principalmente quando
`u* <= 0` ou `Hs == -999`; outros campos inválidos podiam alcançar os cálculos.
A variante corrigida valida finitude, data/hora e domínios físicos de `Hs`,
`u*`, `w*`, alturas de mistura, `Lmo`, `z0`, vento e altura de referência. Um
registro meteorológico inválido gera aviso e concentração **-99** para todos os
receptores daquele período. Os parsers do pipeline rejeitam essa sentinela em
casos que exigem todos os períodos válidos.

---

## 5. Arquivos de saída

O nome base é informado no `Line_Source_Inputs.txt`. Arquivos gerados:

| Arquivo | Conteúdo |
|---|---|
| `Output_Base.csv` | Concentrações horárias (opção 3 = `A`), todas as horas em um arquivo |
| `Output_Base_MM-YY.csv` | Concentrações horárias divididas por mês/ano (opção 3 = `M`) |
| `Output_Base_DailyAve.csv` | Médias diárias de 24 h (opção 2 = `Y`) |

Cada arquivo começa com um cabeçalho com a versão, os arquivos usados, o erro, a altura de deslocamento e as opções. Depois vêm as linhas de dados.

**Formato das linhas horárias:**

```
Ano, DiaJuliano, Hora, X, Y, Z, C_grupo1, C_grupo2, ...
```

**Formato das linhas de média diária:**

```
Ano, DiaJuliano, Nº_horas, X, Y, Z, C_grupo1, C_grupo2, ...
```

As colunas finais são as concentrações de cada grupo de fontes. Unidade: **µg/m³**, se a emissão foi dada em g/(m·s).

---

## 6. Execução segura neste repositório

O RLINE continua sem argumentos próprios e lê `Line_Source_Inputs.txt` do
diretório corrente. Para uso normal, não copie nem execute um binário histórico
manualmente. Use o wrapper transacional:

```bash
make rline-release
bash scripts/run_rline.sh <diretorio_do_caso>
```

Sem um segundo argumento, o wrapper usa
`build/rline-patched/RLINEv1_2_patched.x`. Para uma comparação explícita com o
upstream:

```bash
bash scripts/run_rline.sh \
  <diretorio_do_caso> \
  build/rline-original/RLINEv1_2_gfortran.x
```

O wrapper valida os arquivos referenciados pelo controle, executa em workspace
exclusivo, usa lock, mata o grupo de processos em timeout e só publica saídas
novas validadas. Cada tentativa produz log e manifesto JSON em
`<diretorio_do_caso>/logs/`.

O pacote `rline_pipeline` lê todas as observações, inclusive a última linha do
CSV, exige o conjunto completo de períodos por receptor e faz merge AERMOD/RLINE
um-para-um sem arredondar coordenadas.

## 7. Guia rápido de referência (tabela-resumo)

| Conceito | Explicação |
|---|---|
| **Fonte de linha** | Um trecho reto de rodovia, definido por 2 pontos (início e fim) |
| **Receptor** | Ponto onde se quer a concentração (X, Y, Z) |
| **Grupo** | Rótulo que junta várias fontes na saída |
| **Pluma direta (P)** | Poluente arrastado pelo vento |
| **Meandro (M)** | Espalhamento em ventos fracos |
| **Total (T)** | P + M |
| **σy0, σz0** | Espalhamento lateral/vertical inicial da pluma |
| **dCL** | Offset da pista em relação ao centro da via |
| **MOST** | Teoria de Monin-Obukhov (perfil de vento perto do solo) |
| **AERMET** | Pré-processador meteorológico do AERMOD; formato do arquivo `.sfc` |

---

## 8. Referências científicas

- Snyder, M. G., Venkatram, A., Heist, D. K., Perry, S. G., Petersen, W. B., Isakov, V., 2013. *RLINE: A Line Source Dispersion Model for Near-Surface Releases.* Atmospheric Environment, 77, 748-756.
- Venkatram, A., Snyder, M. G., Heist, D. K., Perry, S. G., Petersen, W. B., Isakov, V., 2013. *Re-formulation of Plume Spread for Near-Surface Dispersion.* Atmospheric Environment, 77, 846-855.
- Heist, D., et al., 2013. *Estimating near-road pollutant dispersion: a model inter-comparison.* Transportation Research Part D, 25, 93-105.
- Cimorelli, A. J., et al., 2005. *AERMOD: a dispersion model for industrial source applications.* J. Appl. Meteorol., 44, 682-693.
- Grimmond, C. S. B., Oke, T. R., 1999. *Aerodynamic properties of urban areas derived from analysis of surface form.* J. Appl. Meteorol., 38, 1262-1292.

---

## 9. Próximo passo

Veja o documento **[`PLANO_Compilacao_Uso_RLINE.md`](PLANO_Compilacao_Uso_RLINE.md)** para aprender a **compilar o modelo** e **rodá-lo** com os dados de exemplo, com os dados de avaliação e com **seus próprios dados**.

> A fonte `RLINE` apareceu como opção beta no AERMOD v19191, foi reformulada na
> v23132 e passou à configuração regulatória na v24142. Para o
> pipeline AERMET -> AERMOD v26135 -> RLINE standalone corrigido, incluindo
> execução transacional, resultados históricos e regressão científica,
> consulte
> [`GUIA_PIPELINE_AERMET_AERMOD_RLINE.md`](GUIA_PIPELINE_AERMET_AERMOD_RLINE.md).
