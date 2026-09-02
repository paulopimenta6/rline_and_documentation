# Política de validação científica

## Classes de evidência

A política executável está em
`rline_pipeline/policies/validation-policy-v1.json` e separa três perguntas:

| Classe | Gate? | Pergunta respondida | Limite da alegação |
|---|---:|---|---|
| regressão de software | sim | o código corrigido preservou um baseline aprovado dentro da tolerância? | compatibilidade e determinismo |
| intercomparação de modelos | não | onde e quanto AERMOD e RLINE diferem? | descrição; não equivalência |
| validação de campo | não, por enquanto | o modelo representa observações independentes? | descritiva até pré-registro |

T1–T4 verificam conclusão, cardinalidade, período, identidade dos inputs, merge
bijetivo, finitude e não negatividade. T5–T8 relatam resultados; não escolhem um
limiar depois de observar os quatro casos.

## Métricas reportadas

Para pares `A` (AERMOD) e `R` (RLINE):

- viés fracional: `FB = 2(mean(A)-mean(R))/(mean(A)+mean(R))`;
- erro fracional absoluto médio por par;
- `NMSE = mean((A-R)²)/(mean(A)mean(R))` quando definido;
- `FAC2`: fração dos pares positivos com `0,5 <= A/R <= 2`;
- correlação de Pearson e seu quadrado em `log10`, somente para pares positivos;
- mediana e percentil 95 de `abs(log10(A/R))`;
- FB entre os 25 maiores valores de cada série;
- contagem de pares zero/zero e de zero discordante.

Zeros são valores possíveis e não causam rejeição estrutural. Métricas em log
ficam `null` quando há menos de três pares positivos ou variância degenerada.
Correlação alta não exclui grande viés: multiplicar quase metade de uma série por
dez pode manter R²(log) alto; por isso nenhuma métrica isolada é usada como
evidência de validade.

## Baselines e proveniência

Cada pasta em `casos/` possui `baseline-manifest.json`. O carregador canônico
verifica SHA-256 dos controles e resultados e liga explicitamente a meteorologia
compartilhada. Essas baselines usam o RLINE original histórico. Uma rodada nova
usa por padrão a variante corrigida e recebe manifesto de execução próprio.

A regressão em `scripts/scientific_regression.py` compara todas as chaves e
concentrações dos casos Example, CALTRANS, Idaho Falls e Raleigh. Os limites
atuais são limites de regressão definidos a partir da divergência observada da
correção local; não são critérios universais de desempenho ambiental.

## Validação com observações de campo

Antes de transformar os dados, fixe por escrito:

1. poluente, unidade, base temporal e período;
2. geometria, receptores, fundo e tratamento de valores ausentes;
3. fatores de emissão e conversões dimensionais;
4. métricas primárias, incerteza e critérios de aceitação;
5. análises de sensibilidade e exclusões permitidas.

Transformações indicadas nos READMEs/PDFs locais, a confirmar em uma auditoria
reprodutível:

- CALTRANS: combinar sentidos/faixas com fatores de emissão e comparar a média
  dos quatro valores medianos medidos com a mediana modelada correspondente;
- Idaho Falls: aplicar as taxas diárias de SF₆ por comprimento e converter a
  concentração usando densidade de 5,34 kg/m³; o arquivo observado presente é
  CSV, apesar de uma descrição histórica mencionar XLSX;
- Raleigh: converter veículo-milha por hora e fator de 0,5 g/veículo-km para
  g/m/s, aplicar ao resultado e converter com a densidade de NO indicada.

Essas operações não estão promovidas a gate porque ainda faltam um protocolo
pré-registrado, rastreabilidade completa das unidades e testes de sensibilidade.

## Painel de qualidade

`make quality-report` cria `build/reports/quality-summary.json`, validado pelo
schema `quality-summary-v1.schema.json`. O contrato contém indicadores, política
e métricas por caso. Cobertura, determinismo e conformidade golden permanecem
`null` quando seus relatórios não foram fornecidos; o painel não inventa zeros.

Metas desejadas para CI:

- 100% de casos estruturalmente válidos;
- 100% de manifests verificados;
- 100% de execuções repetidas determinísticas;
- 100% das regressões dentro da tolerância;
- pelo menos 90% de cobertura de linhas Python.

## Referências

- [EPA — Model Evaluation Guidance](https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=P100BKID.TXT)
- [EPA — Meteorological Guidance](https://www.epa.gov/scram/air-modeling-meteorological-guidance)
- [EPA — 2024 Appendix W Final Rule](https://www.epa.gov/scram/2024-appendix-w-final-rule)
