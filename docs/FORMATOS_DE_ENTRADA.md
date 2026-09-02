# Formatos de entrada

Este documento define o contrato operacional dos arquivos aceitos pelo projeto.
Use UTF-8 e ponto como separador decimal, salvo quando o formato Fortran do
modelo exigir ASCII. Caminhos são relativos ao diretório da respectiva rodada.

## 1. Entrada principal do projeto: `config.json`

O schema normativo é
`rline_pipeline/schemas/case-config-v1.schema.json`. Campos desconhecidos são
rejeitados. Todos os números devem ser finitos.

| Campo | Tipo/unidade | Regra |
|---|---|---|
| `schema_version` | inteiro | exatamente `1` |
| `nome` | string | letras, números, `_` e `-`; não pode ser vazio |
| `descricao` | string | texto não vazio |
| `comprimento` | número, m | maior que zero |
| `y_rodovia` | número, m | dentro da extensão Y da grade |
| `qs` | número, g s⁻¹ m⁻² | maior que zero; usado por `SRCPARAM` |
| `width` | número, m | maior que zero |
| `emis_fator` | número ou `null`, g m⁻¹ s⁻¹ | opcional; se ausente, `qs × width` |
| `transecto_x` | número, m | sobre a rodovia e dentro da grade |
| `periodos_esperados` | inteiro | maior que zero e igual ao número de horas meteorológicas |
| `grid.xini`, `grid.yini` | número, m | origem da grade |
| `grid.xn`, `grid.yn` | inteiro | pelo menos 2; produto máximo 1.000.000 |
| `grid.xdelta`, `grid.ydelta` | número, m | maior que zero |

Exemplo mínimo funcional:

```json
{
  "schema_version": 1,
  "nome": "smoke-crosswind",
  "descricao": "Exemplo sintetico 24 h",
  "comprimento": 200.0,
  "y_rodovia": 0.0,
  "qs": 0.001,
  "width": 20.0,
  "grid": {
    "xini": 0.0,
    "xn": 5,
    "xdelta": 50.0,
    "yini": -100.0,
    "yn": 5,
    "ydelta": 50.0
  },
  "transecto_x": 100.0,
  "periodos_esperados": 24
}
```

Valide e gere os inputs derivados com:

```bash
python3 scripts/gerar_caso.py caminho/config.json
```

## 2. `ONSITE.MET` do AERMET

O caso do projeto usa formato `FREE`, três linhas por hora e três níveis de
torre. A ordem é fixada por `ONSITE_S1.INP`:

```text
linha 1: OSDY OSMO OSYR OSHR HT01 SA01 SW01 TT01 WD01 WS01 MHGT TSKC
linha 2:                     HT02 SA02 SW02 TT02 WD02 WS02
linha 3:                     HT03 SA03 SW03 TT03 WD03 WS03
```

| Código | Unidade | Significado |
|---|---|---|
| `OSDY OSMO OSYR OSHR` | dia, mês, ano, hora | hora no intervalo 1–24 |
| `HTnn` | m | altura do sensor |
| `SAnn` | grau | desvio-padrão da direção do vento |
| `SWnn` | m/s | desvio-padrão da velocidade vertical |
| `TTnn` | °C | temperatura |
| `WDnn` | grau desde norte | direção de origem do vento, 0–360 |
| `WSnn` | m/s | velocidade do vento |
| `MHGT` | m | altura de mistura observada |
| `TSKC` | décimos | cobertura total de nuvens |

O período de `ONSITE.MET`, `XDATES` nos controles AERMET e
`periodos_esperados` devem ser consistentes. Dados ausentes precisam usar os
códigos e faixas declarados no controle; não transforme ausência em zero.

## 3. Controles AERMET

- `ONSITE_S1.INP`: caminhos `REPORT`, `MESSAGES`, `DATA`, `QAOUT`, período
  `XDATES`, ordem `READ`, `FORMAT`, faixas `RANGE` e `THRESHOLD`.
- `ONSITE_S2.INP`: lê `QAOUT`; publica `ONSITE.SFC` e `ONSITE.PFL`; declara
  `XDATES`, localização, método de direção e características mensais do sítio.

Execute ambos por `scripts/run_aermet.sh`; não invoque o binário em uma pasta
que contenha resultados cuja proveniência precise ser preservada.

## 4. Controle AERMOD

`generation.py` deriva `controles_aermod/RLINE_TEST.INP` do JSON:

- `LOCATION ... RLINE Xb Yb Xe Ye`: segmento de rodovia;
- `SRCPARAM id QS Zinit WIDTH`: emissão areal, altura inicial e largura;
- `GRIDCART ... XYINC`: grade cartesiana;
- `SURFFILE`/`PROFFILE`: meteorologia AERMET;
- `PLOTFILE PERIOD ALL`: saída de período usada pelo parser.

O contrato atual exige `AVE=PERIOD`, `GRP=ALL`, `NETID=RCART`, o número exato de
horas e correspondência bijetiva com a grade configurada.

## 5. Entradas do RLINE standalone

### `Line_Source_Inputs.txt`

É um controle **posicional**, não um arquivo chave-valor. O projeto gera, nessa
ordem: fonte, receptores, meteorologia, saída, erro de integração, razão de
deslocamento, componente de concentração, médias diárias, saída horária,
supressão de avisos, solução analítica, algoritmos de rodovia rebaixada e uso da
largura. Preserve as linhas separadoras e aspas aceitas pelo programa.

### `Source_Road.txt`

Após três linhas de cabeçalho, cada registro contém:

```text
Group X_b Y_b Z_b X_e Y_e Z_e dCL sigmaz0 lanes Emis Hw1 dw1 Hw2 dw2 Depth Wtop Wbottom
```

Coordenadas e dimensões estão em metros. `Emis` é g m⁻¹ s⁻¹ no modo usado pelo
projeto. A fonte não pode ter comprimento nulo nem emissão negativa.

### `Receptor_Road.txt`

Após três linhas de cabeçalho, cada registro é `X Y Z` em metros. Pares X/Y
devem ser únicos. A ordem gerada varia X primeiro e depois Y; o parser não
depende dessa ordem, mas exige a mesma grade por correspondência bijetiva.

### `ONSITE.SFC`

É o arquivo de superfície produzido pelo AERMET. O parser extrai ano, mês, dia,
dia juliano e hora e rejeita calendário inconsistente, período duplicado ou
quantidade diferente de `periodos_esperados`.

## 6. Regras de segurança

- Gere experimentos com `scripts/gerar_dados_exemplo.py`; o destino padrão é
  `build/examples/`.
- Não edite entradas derivadas à mão: altere `config.json` e regenere.
- Não reutilize uma saída se um input mudou; `generate_case` invalida derivados.
- Preserve manifestos e hashes ao transportar resultados.
- Trate todos os bundles sintéticos como teste de software, nunca como medição.
