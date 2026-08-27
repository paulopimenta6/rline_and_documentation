# 🛣️ rline_and_documentation

> *"Quanta poluição aquela rodovia está deixando na vizinhança?"* — agora respondido
> com modelagem de qualidade do ar de verdade, rodando do zero na sua máquina.

Pipeline completo de **modelagem da dispersão de poluentes emitidos por uma rodovia**,
com os três mosqueteiros da EPA na versão open-source:

| Modelo | Versão | Papel | Apelido |
|---|---|---|---|
| **AERMET** | v26135 | Pré-processador meteorológico (Stage 1 + Stage 2) | o meteorologista ☁️ |
| **AERMOD** | v26135 | Modelo de dispersão com a fonte `RLINE` nativa | o cérebro 🧠 |
| **RLINE** | v1.2 standalone | Implementação original (referência de validação) | o juiz ⚖️ |

Sistema testado: **Ubuntu 22.04 · x86-64 · gfortran 11.4 · GNU Make 4.3 · Python 3.11+**
(`numpy`, `pandas`, `matplotlib`).

---

## 🎯 O que este projeto faz

1. **Compila** os três modelos em paralelo (Makefiles com dependências declaradas).
2. **Pré-processa** uma torre meteorológica sintética de 3 níveis (10/50/100 m, 120 horas)
   com o AERMET até gerar `ONSITE.SFC` + `ONSITE.PFL`.
3. **Processa** a dispersão da rodovia duas vezes:
   - AERMOD, com a fonte de linha RLINE implementada nativamente;
   - RLINE v1.2 standalone, como referência independente.
4. **Pós-processa**: mapas de concentração, transectos, scatter log-log e métricas.
5. **Valida** com 8 testes automatizados (T1–T8).
6. **Explora cenários** através de 4 casos de uso parametrizados.

O resultado: dois modelos independentes que "concordam" (correlação log-log > 0.95 no
trecho da rodovia), e você ainda ganha mapas bonitos de brinde. 🎁

---

## 🚀 Começando em 3 passos

```bash
# 1. Compilar (paralelo)
make -C aermet_and_aermod/aermet_source -j$(nproc)
make -C aermet_and_aermod/aermod_source/aermod_source_v26135 -j$(nproc)
make -C RLINE_v1_2.Source/v1_2 -f Makefile.gfortran -j$(nproc)

# 2. Pipeline fim-a-fim (AERMET → AERMOD → RLINE → gráficos)
bash scripts/run_pipeline.sh

# 3. Casos de uso + testes
bash scripts/run_todos_casos.sh
```

> ⚠️ **Atenção (AERMOD):** NÃO use `-ffixed-line-length-132` — quebra o `rline.f`.
> Os Makefiles já fazem a coisa certa.

---

## 🗺️ Como tudo flui

```
ONSITE.MET (torre 3 níveis, 120 h)
     │  AERMET Stage 1 (QA/QC) ──► ONSITE_QAOUT.TXT
     │  AERMET Stage 2 (METPREP) ──► ONSITE.SFC + ONSITE.PFL
     ▼
AERMOD (RLINE_TEST.INP) ──► CONC_PLOT.PLT  (conc. PERIOD)
RLINE v1.2 standalone   ──► Output_Road_Numerical.csv (horário)
     │
     ▼
scripts Python ──► métricas + mapas + gráficos comparativos
```

A meteorologia processada é **compartilhada por todos os casos**: cada cenário só muda
a geometria da rodovia, a emissão ou a grade de receptores.

---

## 🧪 Casos de uso (cenários)

Quatro "experimentos" definidos como dados (`config.json`) — para trocar um cenário,
edite o JSON e rode de novo:

| Caso | Rodovia | Emissão | Largura | Grade | O que investiga |
|---|---|---|---|---|---|
| `caso1_referencia` | 0–1000 m | QS 0.001 | 20 m | 26×31 (806 rec.) | linha de base |
| `caso2_rodovia_curta` | 0–300 m | QS 0.001 | 20 m | 21×21 (441 rec.) | trecho urbano curto |
| `caso3_emissao_alta` | 0–1000 m | QS 0.005 (5×) | 20 m | 21×21 | congestionamento 🚗💨 |
| `caso4_rodovia_larga` | 0–1000 m | QS 0.001 | 40 m (2×) | 21×21 | pista dupla 🛣️ |

**Resultados validados** (PERIOD de 120 h, março/1988):

| Caso | máx. AERMOD (µg/m³) | máx. RLINE (µg/m³) | R²(log) no trecho | razão mediana |
|---|---|---|---|---|
| caso1 | ~48 967 | ~154 045 | 0.958 | 0.64 |
| caso2 | ~48 379 | ~150 077 | 0.979 | 0.50 |
| caso3 | ~244 833 (5×) | ~770 226 | 0.964 | 0.58 |
| caso4 | ~90 142 (2×) | ~256 728 | 0.955 | 0.61 |

Note como `caso3` e `caso4` escalam com a emissão por comprimento — o pipeline se
comporta fisicamente. ✅

### Comandos dos casos

```bash
python3 scripts/gerar_caso.py casos/caso1_referencia/config.json   # gera os dados
bash scripts/run_caso.sh casos/caso1_referencia 600                # roda AERMOD+RLINE+pós
python3 scripts/plot_casos_resumo.py                               # painel comparativo
python3 scripts/teste_casos.py                                     # T1–T8 em todos
```

---

## ✅ Testes de verificação (T1–T8)

| # | O que valida | Limite |
|---|---|---|
| T1 | AERMOD rodou | `CONC_PLOT.PLT` existe |
| T2 | RLINE rodou | `Output_*_Numerical.csv` existe |
| T3 | Merge completo | todos os receptores comparados |
| T4 | Valores válidos | finitos e positivos |
| T5 | Correlação global | R²(log) ≥ 0.85 (≥ 0.65 p/ grade ≫ rodovia) |
| T6 | Correlação no trecho | R²(log) ≥ 0.95 |
| T7 | Razão mediana | 0.30 – 1.20 |
| T8 | Escala máx. | max RLINE / max AERMOD ≤ 20 |

```bash
python3 scripts/teste_casos.py   # → "TODOS OS TESTES PASSARAM" ✅
```

A razão AERMOD/RLINE ~0.6 no eixo da rodovia é **esperada**: as duas implementações
usam discretizações numéricas diferentes (AERMOD é a versão regulatória; o standalone
é o código numérico original). Longe da rodovia a razão converge para 1.

---

## 📁 Estrutura do projeto

```
rline_and_documentation/
├── PLANO_MELHORIAS_PROJETO.md        # diagnóstico e roteiro de implementação
├── PIPELINE_IMPLEMENTACAO.txt        # especificação + automação + validação
├── GUIA_RLINE.md                     # conceitos RLINE
├── GUIA_PIPELINE_AERMET_AERMOD_RLINE.md
├── PLANO_Compilacao_Uso_RLINE.md
├── aermet_and_aermod/                # fontes + Makefiles + binários
├── RLINE_v1_2.Source/v1_2/           # fontes + Makefile.gfortran + binário
├── RLINE_v1_2.Example_Cases/         # caso de exemplo (validado vs EPA)
├── RLINE_v1_2.Evaluation_Data/       # CALTRANS, Idaho Falls, Raleigh (T8 EPA)
├── Caso_Pipeline/                    # caso de referência (dados, rodadas, gráficos)
├── casos/                            # 4 casos de uso + comparativo_geral.png
└── scripts/                          # automação completa (12 scripts)
    ├── run_pipeline.sh               # pipeline fim-a-fim (caso de referência)
    ├── run_todos_casos.sh            # todos os casos + comparativo + testes
    ├── gerar_caso.py / run_caso.sh   # um caso parametrizado
    ├── postprocess_caso.py           # mapas/gráficos/resumo por caso
    ├── plot_casos_resumo.py          # painel comparativo geral
    └── teste_casos.py                # verificação T1–T8
```

---

## 📚 Documentação e referências

- [PLANO_MELHORIAS_PROJETO.md](PLANO_MELHORIAS_PROJETO.md) — diagnóstico técnico,
  prioridades, critérios de aceite e roteiro para as próximas implementações.
- [PIPELINE_IMPLEMENTACAO.txt](PIPELINE_IMPLEMENTACAO.txt) — a bíblia: especificação,
  automação e validação T1–T8 (incl. EPA).
- [GUIA_RLINE.md](GUIA_RLINE.md) — conceitos do modelo RLINE e uso standalone.
- [GUIA_PIPELINE_AERMET_AERMOD_RLINE.md](GUIA_PIPELINE_AERMET_AERMOD_RLINE.md) —
  pipeline completo validado.
- [PLANO_Compilacao_Uso_RLINE.md](PLANO_Compilacao_Uso_RLINE.md) — compilação e uso.
- PDFs oficiais: `RLINE_UserGuide_11-13-2013.pdf`, `aermet_userguide.pdf`,
  `aermod_implementation_guide.pdf`, `appendix_w-2024.pdf`.

---

## 🏗️ Como compilar (detalhes)

```bash
# AERMET (livre-forma, f2008)
make -C aermet_and_aermod/aermet_source -j4

# AERMOD (formato fixo — cuidado com o flag de comprimento de linha!)
make -C aermet_and_aermod/aermod_source/aermod_source_v26135 -j4

# RLINE v1.2 standalone
make -C RLINE_v1_2.Source/v1_2 -f Makefile.gfortran -j4
```

Binários gerados (`file` confirma): `aermet`, `aermod`, `RLINEv1_2_gfortran.x`
— todos ELF 64-bit LSB PIE executáveis.

## ⚙️ O que é "RLINE" afinal?

É a formulação **RLINE** da EPA (Snyder & Heist, RLINE 1.2) para **fontes de linha**:
rodovias, pistas, rampas. Em vez de modelar cada carro, a rodovia inteira é um
segmento com emissão por metro por segundo (g/m/s). O AERMOD a partir da v22112 a
incorpora nativamente; este projeto roda as duas implementações lado a lado para
**validar uma com a outra** — ciência reprodutível do jeito certo. 🔬

---

*Feito com ☕, gfortran e muita paciência para descobrir por que `GRIDCART` não estava
na lista `KEYWD` do módulo `modules.f`.*
