# Roadmap de melhorias

## Entregue nesta revisão

- índice espacial de memória linear no merge por tolerância, testado com
  100.000 coordenadas;
- validação explícita de `GRP=ALL`, `NETID=RCART`, período e meteorologia;
- baselines versionadas com SHA-256 e snapshots de fonte verificados antes do
  build;
- zeros aceitos e conjunto de métricas complementares;
- separação formal entre regressão, intercomparação e validação de campo;
- gerador sintético importável, RNG local, três cenários e publicação segura;
- contrato JSON do painel e documentação dos formatos.

## Próximas etapas priorizadas

| Prioridade | Entrega | Critério de conclusão |
|---|---|---|
| P0 | CI em checkout limpo | suíte, manifests e exemplo passam sem arquivos ignorados preexistentes |
| P0 | auditoria do ZIP oficial v26135 | URL, data, hash do ZIP e comparação arquivo a arquivo registrados |
| P1 | adaptadores de campo | CALTRANS, Idaho Falls e Raleigh transformados com unidades tipadas e testes golden |
| P1 | protocolo pré-registrado | critérios de campo fixados antes de inspecionar métricas finais |
| P1 | cobertura >= 90% | relatório de CI alimenta `python_line_coverage` no painel |
| P2 | dashboard renderizado | consumidor HTML/XLSX lê exclusivamente `quality-summary.json` e exibe `null` como “não medido” |
| P2 | análise de sensibilidade | semente, estabilidade, direção, largura, emissão e grade com intervalos reportados |

## Sequência segura

1. Crie um worktree limpo e confirme `make model-provenance-check`.
2. Execute `make test`, `make quality` e gere o resumo de qualidade.
3. Gere `smoke-crosswind` e `smoke-near-parallel`; compile os modelos uma vez.
4. Rode cada exemplo duas vezes em destinos distintos e compare manifests e
   hashes de saída.
5. Só então execute a regressão científica completa.
6. Importe dados de campo em uma árvore separada, preserve os originais
   somente-leitura e gere tabelas transformadas com provenance sidecar.
7. Faça revisão independente de unidades e critérios antes de habilitar gates.

Um arquivo de planilha não foi adicionado ao repositório: o ambiente desta
revisão não forneceu a capacidade de planilhas exigida pelo template solicitado.
O contrato JSON torna essa renderização posterior mecânica e auditável.
