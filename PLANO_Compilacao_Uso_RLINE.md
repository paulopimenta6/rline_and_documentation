# R-LINE v1.2 — Plano de Compilação e Uso

> Este documento descreve, passo a passo, como **compilar** o modelo R-LINE a partir do código-fonte e como **usá-lo** (1) com os dados de exemplo, (2) com os dados de avaliação disponíveis e (3) com **dados reais** de um novo estudo.

---

## 1. Pré-requisitos

| Requisito | Detalhe | Como verificar |
|---|---|---|
| Sistema Linux/macOS com compilador Fortran | `gfortran` (GNU Fortran) | `gfortran --version` |
| `make` | Utilitário de build | `make --version` |
| `pdftotext` (opcional) | Para ler os manuais PDF | `pdftotext -v` |

O código-fonte é em **Fortran 90** e **não depende de nenhuma biblioteca externa**. Os Makefiles originais (`Makefile.ifort`, `Makefile.pgf90`) foram feitos para os compiladores Intel (`ifort`) e PGI (`pgf90`), que **não estão instalados** neste ambiente. Por isso, foi criado o **`Makefile.gfortran`** (este projeto já inclui o arquivo compilado com sucesso).

> **Testado neste projeto:** Ubuntu 22.04, `gfortran 11.4.0`, `make` 4.3. Compilação sem warnings/erros. Os executáveis antigos (`RLINEv1_2.ifort.x`, `RLINEv1_2.pgf90.x`) são binários ELF de 2013 para outras plataformas e **não devem ser usados**; o `RLINEv1_2_g95.exe` e `RLINEv1_2_gfortran.exe` são para Windows.

---

## 2. Compilação do modelo

Tudo é feito dentro da pasta do código-fonte:
`RLINE_v1_2.Source/v1_2/`

### Passo 2.1 — Compilar

```bash
cd RLINE_v1_2.Source/v1_2
make -f Makefile.gfortran
```

O que o Makefile faz:

```make
FC      = gfortran          # compilador
FFLAGS  = -O1 -Wall -fbounds-check   # otimização + verificações de segurança
EXE     = RLINEv1_2_gfortran.x
```

Resultado esperado:
- 29 arquivos `.o`
- 2 arquivos de módulo (`.mod`)
- O executável **`RLINEv1_2_gfortran.x`**

> ⚠️ O programa **deve ser executado dentro da pasta onde estão os arquivos de entrada**, pois ele procura o arquivo `Line_Source_Inputs.txt` no diretório atual (não usa caminhos absolutos).

### Passo 2.2 — Limpar (recompilar do zero)

```bash
make -f Makefile.gfortran clean
```

### Passo 2.3 — Erros comuns de compilação

| Sintoma | Causa provável | Solução |
|---|---|---|
| `command not found: gfortran` | Compilador não instalado | `sudo apt install gfortran` (Debian/Ubuntu) ou `brew install gcc` (macOS) |
| `undefined reference to ...` | Ordem errada de compilação | Usar `make -f Makefile.gfortran` (ordem já correta) |
| `module not found: Data_Structures` | Módulos não compilados antes | Rodar `make clean` e depois `make` de novo |

---

## 3. Como rodar o modelo (regra geral)

O R-LINE não recebe argumentos: ele lê o arquivo **`Line_Source_Inputs.txt`** da pasta atual. Portanto:

1. Coloque os 4 arquivos de entrada **na mesma pasta**:
   - `Line_Source_Inputs.txt`
   - arquivo de fontes (nome livre)
   - arquivo de receptores (nome livre)
   - arquivo meteorológico `.sfc` (nome livre)
2. Coloque o executável `RLINEv1_2_gfortran.x` nessa pasta (ou chame pelo caminho completo).
3. Execute:

```bash
./RLINEv1_2_gfortran.x
```

4. Observe a saída no terminal (progresso por hora e tempo total) e confira os arquivos `.csv` gerados.

### Interpretando o cabeçalho de saída

O arquivo de saída começa com um resumo da execução:

```
RLINEv1_2
SOURCE FILE: Source_Example.txt (8 Sources)
RECEPTOR FILE: Receptor_Example.txt (196 Receptors)
SURFACE FILE: Met_Example.sfc
Error Limit:  1.000E-03
Displacement Height:      5.000*z0
Concentrations from: Plume and Meander
Integraton option: Numerical
```

Confirme sempre que "Sources", "Receptors" e a opção de integração estão como esperado antes de analisar os números.

---

## 4. Uso com os dados de exemplo

Pasta: `RLINE_v1_2.Example_Cases/Example_case/`

Este exemplo simula **duas rodovias que se cruzam** (4 pistas norte-sul = grupo G1; 4 pistas leste-oeste = grupo G2), com 196 receptores em uma grade ao redor do cruzamento, e 10 horas de meteorologia.

### Passo a passo

```bash
# 1) Crie uma pasta de trabalho (não modifique os arquivos originais)
mkdir -p ~/rline_trabalho/example
cd ~/rline_trabalho/example

# 2) Copie os arquivos do exemplo e o executável
cp <PROJETO>/RLINE_v1_2.Example_Cases/Example_case/* .
cp <PROJETO>/RLINE_v1_2.Source/v1_2/RLINEv1_2_gfortran.x .

# 3) Rode o modelo
./RLINEv1_2_gfortran.x
```

> Dica: os dados originais nunca devem ser modificados. Copie tudo para uma pasta de trabalho antes de rodar. Este procedimento foi validado em `/tmp/opencode/run_example`.

### Resultados esperados

| Arquivo gerado | Conteúdo |
|---|---|
| `Output_Example_Numerical.csv` | 10 horas × 196 receptores = 1960 linhas de dados |
| `Output_Example_Numerical_DailyAve.csv` | Médias diárias (10 horas usadas no dia) |

**Tempo de execução observado:** ~34 s (gfortran -O1, modo numérico).

As concentrações são altas (ordem de 10⁶ µg/m³) porque a emissão é **unitária** (1 g/(m·s)) — é um exemplo de funcionalidade, não um cenário realista. O importante é que **G1 e G2 saem em colunas separadas**, mostrando o efeito do agrupamento de fontes.

### Comparação entre os dois formatos de fonte

O exemplo traz `Source_Example.txt` (endpoints de cada pista) e `Source_Example_dCL.txt` (centro + offset `dCL`). Para testar a equivalência, troque o nome no `Line_Source_Inputs.txt` (linha 3) por `Source_Example_dCL.txt`, rode de novo e compare os `.csv` — os resultados devem ser os mesmos.

---

## 5. Uso com os dados de avaliação (experimentos reais)

Pasta: `RLINE_v1_2.Evaluation_Data/Evaluation_data/`

São 3 conjuntos de dados de **experimentos de campo reais**, usados para validar o modelo. Em todos, o modelo é rodado com **emissão unitária** e o fator real é aplicado no pós-processamento (por isso as saídas são adimensionais na etapa do modelo).

### 5.1 CALTRANS — Rodovia CA-99 (SF6, 1989)

- **Pasta:** `CALTRANS_RLINE/`
- **Cenário:** SF6 liberado ao longo da rodovia; 4 fontes (2 norte/sul NB, 2 norte/sul SB), 7 receptores, 56 horas de meteorologia.
- **Execução:** copie `Line_Source_Inputs.txt`, `CALTRANS99_Source.txt`, `CALTRANS99_ALLreceptors.txt`, `CALTRANS99_met.sfc` e o executável para uma pasta de trabalho e rode.
- **Saída esperada:** `CALTRANS99_Output.csv` com 2 colunas de grupo (`C_NB`, `C_SB`), 392 linhas de dados.
- **Tempo observado:** ~20 s.
- **Pós-processamento (do README do experimento):**
  1. Pegue os fatores de emissão de SF6 em `CALTRANS99_data.xlsx`.
  2. Multiplique a concentração de cada direção pelo seu fator.
  3. Some as duas direções (NB + SB) em cada receptor.
  4. Compare com a concentração medida (média das 4 medições da mediana).

### 5.2 Idaho Falls — SF6 com barreira (2009)

- **Pasta:** `IdahoFalls_RLINE/`
- **Cenário:** fonte de linha infinita (1 km, processada a partir de um experimento real), 7 receptores a distâncias perpendiculares, meteorologia em intervalos de 15 min (31 períodos). É o caso **sem barreira** do estudo.
- **Execução:** copie `Line_Source_Inputs.txt`, `IF2009_Source_INF.txt`, `IF2009_Receptors_INF.txt`, `IF2009_Case1235.sfc` e o executável para uma pasta de trabalho e rode.
- **Saída esperada:** `IF2009_Output_INF_Case1235.csv`, 217 linhas de dados.
- **Tempo observado:** ~0,2 s (poucas fontes/receptores).
- **Pós-processamento (do README):**
  1. Taxas de emissão de SF6 por dia: dia 1 = 0,05 g/s; dia 2 = 0,04 g/s; dia 3 = 0,03 g/s; dia 5 = 0,03 g/s.
  2. Emissão por metro = taxa (g/s) ÷ 54 m (comprimento da fonte).
  3. Multiplique as concentrações unitárias por esse valor.
  4. Divida pela densidade do SF6 (~5,34 kg/m³) → resultado em **ppb**, comparável às medições.

### 5.3 Raleigh — NO perto de rodovia (2006)

- **Pasta:** `Raleigh_RLINE/`
- **Cenário:** rodovia de 8 pistas (4 de cada lado do canteiro central), 5 receptores (2 locais, repetidos), 624 períodos de meteorologia de 10 min.
- **Execução:** copie `Line_Source_Inputs.txt`, `Ral2006_Source.txt`, `Ral2006_Receptors.txt`, `Ral_2006_NO.sfc` e o executável para uma pasta de trabalho e rode.
- **Saída esperada:** `Ral2006_Output.csv`, 1248 linhas de dados.
- **Tempo observado:** ~20 s.
- **Pós-processamento (do README):**
  1. Emissão em g/(m·s) = (volume de tráfego em veículo-milhas × fator de emissão) convertido para km, dividido pelo comprimento da fonte, pelos segundos do período e convertido km→m. Fator de emissão usado: **0,5 g/veíc/km** (Venkatram, 2007).
  2. Multiplique as concentrações unitárias pela emissão.
  3. Divida pela densidade do NO e converta para **ppb**.

### 5.4 Validação do build (já realizada)

Os três casos foram rodados com o executável compilado (`gfortran`) e comparados com os `.csv` de referência que acompanham o projeto:

| Caso | Linhas | Concordância |
|---|---|---|
| CALTRANS | 392 | Máx. diferença relativa 0,03% (arredondamento do compilador) |
| Idaho Falls | 217 | Idêntico |
| Raleigh | 1248 | Idêntico |

Isso confirma que o modelo compilado com gfortran reproduz os resultados oficiais.

---

## 6. Uso com dados reais (novo estudo)

Aqui está o passo a passo para preparar um cenário totalmente novo.

### Passo 6.1 — Defina o sistema de coordenadas

Escolha uma origem (pode ser UTM ou um sistema local centrado em um ponto de interesse). Todas as coordenadas X, Y (metros) e as alturas Z (metros, em relação ao nível local do solo) de fontes e receptores devem usar o **mesmo** sistema.

### Passo 6.2 — Prepare a meteorologia (arquivo `.sfc`)

É o arquivo mais difícil de gerar. Opções:

- **Opção recomendada:** rodar o **AERMET** (pré-processador do AERMOD) para obter o arquivo de superfície. Instale AERMET (https://www.epa.gov/scram/air-quality-dispersion-modeling-preprocessor-models-aermet) e gere o `.sfc` no formato padrão.
- **Alternativa:** criar o arquivo manualmente, desde que as colunas sigam a mesma ordem do AERMET. Campos usados pelo R-LINE (nesta ordem):
  1. `Ano Mês Dia DiaJuliano Hora` (apenas repassados à saída)
  2. `Hs` — fluxo de calor sensível (W/m²)
  3. `u*` — velocidade de atrito (m/s)
  4. `w*` — escala de velocidade convectiva (m/s)
  5. `CBL` — altura da camada limite convectiva (m)
  6. `SBL` — altura da camada limite estável (m)
  7. `Lmo` — comprimento de Monin-Obukhov (m)
  8. `z0` — rugosidade da superfície (m)
  9. `Bo` — razão de Bowen
  10. `Alb` — albedo
  11. `Ws` — velocidade do vento (m/s)
  12. `Wd` — direção do vento (graus)
  13. `zref` — altura de referência do vento (m)
  14. `Temp`, `ztemp` — temperatura e altura de referência

> ⚠️ Valores `-999` = dado ausente → a saída daquele período será `-99` em todos os receptores. Use o modelo **MOST_Wind** para verificar se os perfis de vento estão coerentes.

### Passo 6.3 — Prepare as fontes

Para cada trecho de rodovia (link):

1. **Geometria:** coordenadas de início e fim (X, Y, Z). Se preferir, use o centro da via + `dCL` para cada pista.
2. **σz0 (coluna 9):** espalhamento vertical inicial. A orientação da EPA sugere ≈ (altura média dos veículos × 1,7) / 2,15.
3. **Nº de faixas (coluna 10):** nº real de faixas (pode ser fracionário); usado para calcular σy0 se a opção beta 3 estiver ativa.
4. **Emissão (coluna 11):**
   - Direta: em **g/(m·s)**.
   - Ou em **AADT** (veículos/dia) — a saída ficará em unidades proporcionais e você aplica o fator depois.
   - Conversão comum (veículos → g/(m·s)):
     ```
     Emis (g/m/s) = [N_veículos/hora × fator_emissão (g/km)] / (1000 m/km × 3600 s/h)
     ```
5. **Grupo (coluna 1):** agrupe trechos que você quer somar na saída (ex.: todas as faixas de um sentido). Fontes do mesmo grupo podem ficar em qualquer ordem no arquivo.
6. **Barreiras/depressões (colunas 12–18):** preencha com `0` se não usar. Se usar, ative a opção beta 2 e informe `Hw1`, `dw1` (barreira) ou `Depth`, `Wtop`, `Wbottom` (via deprimida).

### Passo 6.4 — Prepare os receptores

Liste todos os pontos de interesse (escolas, residências, monitor de qualidade do ar, grade de análise) com X, Y, Z. Ex.: monitor a 2 m de altura, residência a 1,5 m.

### Passo 6.5 — Monte o `Line_Source_Inputs.txt`

Copie o modelo do caso de exemplo e ajuste:
- nomes dos 3 arquivos de entrada (linhas 3, 7, 10);
- nome base de saída (linha 13);
- `Error_Limit` (recomendado `1.0e-03`);
- `fac_dispht` (altura de deslocamento = fator × z0; use `0` para deslocamento nulo);
- opções de saída (pluma/meandro/total; média diária; horários);
- opções beta (analítica, barreiras, largura de pista).

**Orientação para valores urbanos (Grimmond & Oke, 1999):**

| Forma urbana | Altura média (m) | d (m) | z0 (m) |
|---|---|---|---|
| Baixa/baixa densidade | 5–8 | 2–4 | 0,3–0,8 |
| Média densidade | 7–14 | 3,5–8 | 0,7–1,5 |
| Alta densidade | 11–20 | 7–15 | 0,8–1,5 |
| Arranha-céus | >20 | >12 | >2,0 |

### Passo 6.6 — Rode e confira

```bash
./RLINEv1_2_gfortran.x
```

Verifique no cabeçalho da saída se contagens de fontes/receptores e opções estão corretos.

### Passo 6.7 — Pós-processamento

- Concentração (µg/m³) = saída do modelo × fator de emissão real (se você usou emissão unitária ou AADT).
- Para comparar com medições em **ppb**, divida pela densidade do poluente (ex.: SF6 ≈ 5,34 kg/m³) e converta unidades.

---

## 7. Opções beta — quando usar

| Opção | Quando usar | Observação |
|---|---|---|
| **1 — Analítica** | Cenários grandes, quando a velocidade é prioridade | Menos precisa perto da fonte e com vento quase paralelo à via |
| **2 — Barreiras / via deprimida** | Estudar barreiras de ruído ou rodovias em corte | Requer centro + `dCL`; só uma barreira a sotavento é usada |
| **3 — Largura da pista** | Rodovias multilane simuladas como 1 fonte | Informe a largura da faixa em metros |

---

## 8. Fluxograma de trabalho resumido

```
 ┌────────────┐   ┌──────────────┐   ┌─────────────┐   ┌─────────────────────┐
 │ meteorologia│   │  fontes      │   │  receptores │   │ Line_Source_Inputs  │
 │ (.sfc)      │   │  (link road) │   │  (X,Y,Z)    │   │ .txt (controle)     │
 └─────┬──────┘   └──────┬───────┘   └──────┬──────┘   └──────────┬──────────┘
       │                 │                  │                      │
       └─────────────────┴──────────────────┴──────────────────────┘
                                      │
                              ┌───────▼────────┐
                              │ RLINE v1.2      │  ← executável (gfortran)
                              │ (main program)  │
                              └───────┬────────┘
                                      │
                      ┌───────────────┼────────────────┐
                      │               │                │
                Horários         Mensais        Médias diárias
             Output_Base.csv   *_MM-YY.csv  *_DailyAve.csv
                      │
                      ▼
             Pós-processamento (fator de emissão, conversão ppb)
                      ▼
             Concentração final vs. medições/limites
```

---

## 9. Referências rápidas

- Manual oficial: `RLINE_UserGuide_11-13-2013.pdf` (neste projeto).
- GUIA de entendimento (conceitos): [`GUIA_RLINE.md`](GUIA_RLINE.md).
- Artigos: Snyder et al. (2013), Venkatram et al. (2013), Heist et al. (2013).

> 💡 **Para o pipeline completo com o AERMOD** (AERMET → AERMOD com a fonte `RLINE`,
> incluindo o formato exato do control file, a grade de receptores, a execução e a
> comparação com o RLINE v1.2 standalone), consulte o
> [`GUIA_PIPELINE_AERMET_AERMOD_RLINE.md`](GUIA_PIPELINE_AERMET_AERMOD_RLINE.md).
