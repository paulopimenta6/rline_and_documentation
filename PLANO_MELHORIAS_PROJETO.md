# Plano de Melhorias do Projeto RLINE/AERMET/AERMOD

## 1. Finalidade

Este documento registra o diagnóstico técnico do repositório e organiza o
trabalho necessário para torná-lo cientificamente confiável, reproduzível e
mais simples de manter.

O objetivo não é modificar imediatamente os modelos, mas deixar um roteiro de
implementação que possa ser executado e validado em etapas futuras. A ordem das
fases foi definida para corrigir primeiro os riscos que podem produzir
resultados numericamente incorretos ou aceitar artefatos antigos como se fossem
novos.

## 2. Escopo do Projeto

O repositório implementa o seguinte fluxo:

```text
ONSITE.MET
    |
    v
AERMET Stage 1 e Stage 2
    |
    +--> ONSITE.SFC
    +--> ONSITE.PFL
             |
             +--> AERMOD com fonte RLINE --> CONC_PLOT.PLT
             |
             +--> RLINE v1.2 standalone --> Output_*_Numerical.csv
                                                    |
                                                    v
                                      métricas, gráficos e testes T1-T8
```

Os principais componentes são:

| Componente | Local | Responsabilidade |
|---|---|---|
| AERMET v26135 | `aermet_and_aermod/aermet_source/` | Processamento meteorológico |
| AERMOD v26135 | `aermet_and_aermod/aermod_source/aermod_source_v26135/` | Modelo regulatório de dispersão |
| RLINE v1.2 | `RLINE_v1_2.Source/v1_2/` | Implementação standalone usada como referência |
| Caso canônico | `Caso_Pipeline/` | Meteorologia, controles e resultados de referência |
| Cenários | `casos/` | Quatro casos parametrizados por `config.json` |
| Automação | `scripts/` | Geração, execução, pós-processamento e testes |
| Dados oficiais | `RLINE_v1_2.Example_Cases/` e `RLINE_v1_2.Evaluation_Data/` | Casos EPA para regressão científica |

## Status da implementação em 2026-08-27

As fases deste plano foram implementadas. As seções seguintes preservam o
diagnóstico e a sequência originalmente propostos; portanto, expressões como
"correção planejada" e "implementação futura" descrevem o estado auditado antes
das mudanças, não o estado atual do workspace.

| Fase | Status | Evidência implementada |
|---|---|---|
| Fase 0 - baseline e proveniência | Implementada | snapshot RLINE original preservado, 30 checksums em `UPSTREAM_SHA256.txt`, builds original/corrigido separados e manifestos de execução |
| Fase 1 - correções numéricas críticas | Implementada | oito patches ordenados e auditáveis, aplicados somente em `build/`; builds corrigidos release e debug |
| Fase 2 - execução segura e transacional | Implementada | workspaces exclusivos, locks, exit code preservado, timeout com `TERM`/`KILL` do grupo, substituição atômica por arquivo com rollback do conjunto, logs e manifestos exclusivos |
| Fase 3 - dados, parsing e configuração | Implementada | pacote `rline_pipeline`, JSON Schema v1, geração determinística, parsers estritos, última linha RLINE preservada e merge bijetivo `one_to_one` |
| Fase 4 - testes científicos | Implementada | T1-T8 reforçados, inclusive `1/20 <= max(AERMOD)/max(RLINE) <= 20` no T8; 72 testes rápidos coletados; quatro regressões EPA automatizadas |
| Fase 5 - build, dependências e CI | Implementada | `Makefile` raiz, artefatos isolados em `build/`, `pyproject.toml`, `uv.lock`, CI rápida e regressão semanal/manual |
| Fase 6 - visualização e documentação | Implementada | geometria, pivot, transectos e rótulos corrigidos; guias, `CONTRIBUTING.md`, `NOTICE` e documentação de reprodutibilidade atualizados sem inferir licença para componentes de terceiros |

Os máximos de diferença relativa da variante RLINE corrigida contra os goldens
são 1,789152% no Example Case, 0,523329% no CALTRANS, 0,088408% em Idaho Falls e
0,314472% em Raleigh. Os respectivos limites são 1,9%, 0,55%, 0,095% e 0,33%;
todos os casos estão dentro de seus limites documentados.

Comandos de verificação do estado implementado:

```bash
make models
make rline-debug
make test
make quality
python3 scripts/teste_casos.py
make scientific-regression
RUN_FULL_PIPELINE=1 make scientific-regression
```

Com `RUN_FULL_PIPELINE=1`, a etapa de pipeline completo executa primeiro o caso
canônico, incluindo AERMET Stages 1/2, AERMOD, RLINE corrigido e
pós-processamento, e depois regenera, executa e valida os quatro casos
configurados. Os wrappers usam por padrão os binários de `build/`, não os
executáveis históricos rastreados.

## 3. Decisão de Proveniência do RLINE

O código RLINE v1.2 distribuído pela EPA deve permanecer disponível sem
alterações para preservar sua proveniência e permitir a reprodução do upstream.
As correções locais não devem ser aplicadas diretamente nessa cópia.

A implementação futura deverá:

1. Registrar a origem, versão e checksum da distribuição original.
2. Manter `RLINE_v1_2.Source/v1_2/` como snapshot imutável do upstream.
3. Armazenar correções locais como patches pequenos e revisáveis, por exemplo em
   `patches/rline-v1.2/`.
4. Aplicar os patches em uma árvore temporária sob `build/`, ignorada pelo Git.
5. Produzir binários com nomes que distingam claramente `original` e `patched`.
6. Registrar nos resultados qual variante, compilador, flags e commit foram
   utilizados.

Essa estratégia evita duplicar toda a fonte, mantém o histórico das correções
auditável e permite comparar a versão original, a versão corrigida e o AERMOD
regulatório.

## 4. Diagnóstico Priorizado

### 4.1 Prioridade crítica

#### C1. Velocidade efetiva do vento usada antes da inicialização

`Effective_Wind` chama `sigmaz(xd)` antes de calcular `ueff`:

- `RLINE_v1_2.Source/v1_2/Effective_Wind.f90:43-52`
- `RLINE_v1_2.Source/v1_2/Sigmaz.f90:43-51`

`sigmaz` usa `ueff` como denominador. Na primeira chamada, o valor é indefinido;
nas chamadas seguintes, pode ser um valor residual de outro receptor ou período
meteorológico.

Impactos possíveis:

- divisão por zero, infinito ou NaN;
- dependência da ordem dos receptores;
- diferenças entre compiladores e níveis de otimização;
- resultados cientificamente não determinísticos.

A implementação do RLINE integrada ao AERMOD calcula `UEFF` antes de `SIGMAZ`,
fornecendo uma referência para a correção:

- `aermet_and_aermod/aermod_source/aermod_source_v26135/rline.f:1314-1336`

Correção planejada:

1. Calcular a estimativa inicial de `ueff` antes da primeira chamada a `sigmaz`.
2. Inicializar explicitamente variáveis globais usadas no cálculo.
3. Proteger divisões contra velocidades não positivas ou não finitas.
4. Adicionar teste de invariância à ordem dos receptores.
5. Executar teste com inicialização de reais em NaN e traps IEEE.

Critério de aceite:

- nenhuma leitura de `ueff` ocorre antes da atribuição no período atual;
- permutar receptores não altera os resultados além da tolerância numérica;
- o caso oficial e os quatro cenários não produzem NaN ou infinito.

### 4.2 Prioridade alta

#### A1. Divisão por zero para fonte paralela ao vento

O modo numérico calcula uma interseção dividindo por
`Ysend - Ysbegin`:

- `RLINE_v1_2.Source/v1_2/Numerical_Line_Source.f90:59-91`

Após a rotação para o sistema alinhado ao vento, uma rodovia paralela ao vento
pode ter `Ysend == Ysbegin`. Esse é um caso físico normal, não uma entrada
inválida.

Correção planejada:

1. Substituir a formulação por distância ponto-segmento baseada em vetores.
2. Tratar explicitamente fonte de comprimento zero.
3. Evitar comparações exatas com zero, usando tolerância coerente com a escala.
4. Cobrir ângulos relativos de 0, 90 e valores próximos desses limites.

Critério de aceite:

- nenhuma divisão por zero ocorre para qualquer orientação válida;
- os resultados variam continuamente para ângulos próximos de paralelo;
- fontes degeneradas são rejeitadas com mensagem objetiva.

#### A2. Índice incorreto no algoritmo de rodovia deprimida

`Translate_Rotate` chama `Depressed_Displacement(theta_line, index)`, mas a
função recebe somente `theta_line` e consulta `Source(indq)`:

- `RLINE_v1_2.Source/v1_2/Translate_Rotate.f90:80-86`
- `RLINE_v1_2.Source/v1_2/Depressed_Displacement.f90:16-40`
- `RLINE_v1_2.Source/v1_2/RLINE_Main.f90:87-95`

Durante a rotação, `indq` ainda não representa a fonte que está sendo
processada. Com interfaces implícitas, a incompatibilidade de argumentos pode
não ser detectada pelo compilador.

Correção planejada:

1. Adicionar `source_index` à interface da função.
2. Usar exclusivamente `Source(source_index)` no cálculo.
3. Mover a função para um módulo ou fornecer interface explícita.
4. Calcular o deslocamento uma vez por fonte, evitando quatro chamadas iguais.
5. Criar caso com duas fontes deprimidas de geometrias diferentes.

Critério de aceite:

- build com verificação de interfaces não apresenta incompatibilidades;
- cada fonte usa exclusivamente seus próprios parâmetros;
- a ordem das fontes não altera o resultado físico.

#### A3. Timeout deixa processos órfãos

Os wrappers iniciam os modelos com `setsid`, mas, ao atingir o timeout, saem sem
encerrar o processo ou seu grupo:

- `scripts/run_aermod.sh:58-72`
- `scripts/run_rline.sh:41-54`

Correção planejada:

1. Instalar `trap` para saída normal, erro e sinais.
2. Enviar `TERM` para o grupo de processos.
3. Aguardar um período curto e enviar `KILL` se necessário.
4. Sempre executar `wait` e preservar o código de saída real.
5. Criar teste com executável falso que excede o timeout.

Critério de aceite:

- nenhum processo filho permanece após timeout ou interrupção;
- o wrapper retorna código diferente de zero;
- uma nova execução não concorre com uma anterior no mesmo diretório.

#### A4. Saídas antigas podem ser aceitas como novas

Os wrappers ignoram o status retornado pelos modelos e validam principalmente a
existência de arquivos ou mensagens:

- `scripts/run_aermod.sh:72-85`
- `scripts/run_rline.sh:54-63`
- `scripts/run_aermet.sh:32-47`

Uma execução pode falhar antes de substituir a saída, deixando um arquivo da
execução anterior que satisfaz a validação.

Correção planejada:

1. Executar cada modelo em diretório temporário exclusivo.
2. Remover ou isolar outputs esperados antes da execução.
3. Preservar e validar o código de saída.
4. Verificar existência, tamanho, estrutura e tempo de criação dos resultados.
5. Mover outputs para o destino final somente após sucesso completo.
6. Usar logs por execução, eliminando `/tmp/rline_run.log` global.
7. Incluir lock ou rejeitar duas execuções simultâneas no mesmo caso.

Critério de aceite:

- falha do executável nunca resulta em sucesso do wrapper;
- arquivos anteriores permanecem identificados como anteriores ou são
  substituídos atomicamente;
- cada resultado pode ser associado a uma execução específica.

#### A5. Casos ausentes são omitidos pelos testes

Sem argumentos, `teste_casos.py` remove da lista os casos que não possuem
`CONC_PLOT.PLT`:

- `scripts/teste_casos.py:111-123`

Assim, T1 não é executado exatamente para os cenários que deveriam falhar.

Correção planejada:

1. Descobrir casos pela presença de `config.json`.
2. Não filtrar casos por outputs existentes.
3. Informar quantidade de casos descobertos, executados e aprovados.
4. Fazer ausência de resultado produzir falha explícita.

Critério de aceite:

- remover a saída de qualquer caso faz a suíte falhar;
- todos os `config.json` encontrados aparecem no relatório.

#### A6. Pós-processamento descarta uma observação válida

O parser usa `skipfooter=1`, mas o escritor RLINE não produz rodapé:

- `scripts/postprocess_caso.py:46-48`
- `scripts/plot_casos_resumo.py:32-34`
- `Caso_Pipeline/scripts/compare_aermod_rline.py:16-19`
- `Caso_Pipeline/scripts/plot_compare_aermod_rline.py:16-19`
- `RLINE_v1_2.Source/v1_2/Write_Hourly_All.f90:68-76`

O arquivo canônico termina em uma observação válida:

- `Caso_Pipeline/rodada_rline/Output_Road_Numerical.csv:96732`

Correção planejada:

1. Remover `skipfooter=1` de todos os parsers.
2. Centralizar a leitura do CSV RLINE em um único módulo Python.
3. Validar número de colunas, tipos, períodos e receptores.
4. Rejeitar linhas inválidas com diagnóstico em vez de descartá-las
   silenciosamente.

Critério de aceite:

- cada receptor válido possui exatamente o número esperado de períodos;
- a última observação do arquivo é incluída na média;
- todos os consumidores usam o mesmo parser.

## 5. Problemas de Prioridade Média

### M1. Dependência incompleta no Makefile do AERMET

`mod_pbl.f90` usa o módulo `upperair`, mas `mod_pbl.o` não depende de
`mod_upperair.o`:

- `aermet_and_aermod/aermet_source/Makefile:25-35`

Planejamento:

- adicionar a dependência ausente;
- preferir geração automática de dependências Fortran;
- validar repetidamente um build limpo com `make -j$(nproc)`.

### M2. Segunda barreira aceita, mas ignorada

Os campos `hwall2` e `dCL_wall2` estão no formato de entrada, porém não são
usados no cálculo:

- `RLINE_v1_2.Source/v1_2/Data_Structures.f90:96-100`

Planejamento:

- confirmar o comportamento esperado na documentação técnica;
- implementar a segunda barreira com testes físicos ou rejeitar esses campos
  explicitamente;
- nunca aceitar silenciosamente uma opção sem efeito.

### M3. Erros de entrada e alocação são ignorados

Diversas rotinas capturam `IOSTAT` ou `STAT`, mas continuam executando sem
validar o valor:

- `Read_Line_Source_Inputs.f90`
- `Read_Met_Inputs.f90`
- `Read_Receptors.f90`
- `Read_Sources.f90`
- `RLINE_Main.f90:64`
- `Write_Hourly_All.f90:35`

Planejamento:

- validar toda abertura, leitura, escrita, alocação e desalocação;
- usar `error_unit` e `error stop 1`;
- incluir arquivo, registro e operação na mensagem de erro;
- rejeitar contagens nulas ou negativas antes de alocar.

### M4. Meteorologia ausente é validada parcialmente

O período é invalidado somente para `ustar <= 0` ou `Hs == -999`:

- `RLINE_v1_2.Source/v1_2/RLINE_Main.f90:80-85`

Outros campos obrigatórios podem conter sentinelas e entrar em logaritmos,
divisões e rotações.

Planejamento:

- centralizar a validação meteorológica;
- documentar sentinelas aceitas pelo AERMET;
- verificar finitude e domínio físico de cada variável obrigatória;
- marcar o período como inválido ou encerrar conforme a natureza do erro.

### M5. Solução analítica pode usar variável não inicializada

`xwd_lim` não recebe valor quando `xrL == 0`:

- `RLINE_v1_2.Source/v1_2/Analytical_Line_Source.f90:136-177`

Planejamento:

- inicializar a variável;
- tratar o limite com tolerância numérica;
- testar receptor alinhado com cada extremidade da fonte.

### M6. Vazamento de memória quando não há convergência

Os vetores `h` e `Conc` são desalocados apenas no retorno por convergência:

- `RLINE_v1_2.Source/v1_2/Numerical_Line_Source.f90:104-148`

Planejamento:

- garantir desalocação em um caminho único de saída;
- retornar status de convergência;
- propagar falha ou warning ao chamador;
- testar tolerância artificialmente restrita.

### M7. Validação T3-T8 permite falsos positivos

Problemas atuais em `scripts/teste_casos.py:54-106`:

- T3 compara apenas contagens e não garante unicidade;
- não há verificação de 120 períodos por receptor;
- arredondar coordenadas pode colapsar receptores diferentes;
- elevar a correlação ao quadrado aceita correlação negativa;
- T8 testa somente o limite superior do fator 20;
- existência do arquivo não demonstra que ele pertence à execução atual.

Planejamento:

- usar merge com `validate="one_to_one"`;
- conferir as coordenadas contra a grade declarada no JSON;
- verificar unicidade e identidade dos períodos;
- exigir correlação positiva antes de calcular R²;
- exigir `1/20 <= max_RLINE/max_AERMOD <= 20`;
- registrar e verificar o manifesto da execução.

### M8. `config.json` não é a fonte de verdade efetiva

`run_todos_casos.sh` só gera entradas quando o INP ainda não existe:

- `scripts/run_todos_casos.sh:20-27`

Editar emissão, largura, comprimento ou grade pode não alterar a rodada.

Planejamento:

- regenerar entradas deterministicamente em toda execução;
- adicionar schema e validação física do JSON;
- registrar hash da configuração nos artefatos;
- testar que alterar cada campo relevante muda a entrada correspondente.

### M9. Caminhos configuráveis são aplicados de forma inconsistente

`run_pipeline.sh` aceita variáveis de ambiente, mas geradores e
pós-processadores ainda usam caminhos fixos:

- `scripts/run_pipeline.sh:17-69`
- `scripts/run_aermet.sh:19-30`
- `Caso_Pipeline/scripts/gerar_dados_onsite.py`
- scripts de comparação em `Caso_Pipeline/scripts/`

Planejamento:

- normalizar caminhos absolutos e relativos uma única vez;
- passar diretórios por argumentos explícitos;
- remover caminhos hardcoded dos scripts Python;
- testar uma execução fora da raiz e com diretórios absolutos.

### M10. Gráficos representam geometria e métricas incorretamente

Problemas identificados:

- rodovia desenhada até o fim da grade, e não até o fim da fonte;
- transecto com eixo Y recebe elementos posicionados por X;
- reshape depende da ordem das linhas do AERMOD;
- razão mediana é rotulada como `R²(trecho)`.

Referências:

- `scripts/postprocess_caso.py:81-112`
- `scripts/plot_casos_resumo.py:38-49`
- `scripts/plot_casos_resumo.py:67-77`

Planejamento:

- ler a geometria real de `config.json` ou do arquivo de fonte;
- usar `pivot(index='Y', columns='X', values='conc')`;
- validar células ausentes e duplicadas;
- calcular `r2_trecho` de fato ou corrigir o rótulo;
- adicionar teste estrutural dos dados usados em cada gráfico.

## 6. Reprodutibilidade, Build e Organização

### 6.1 Dependências Python

Não existe manifesto instalável das dependências Python.

Planejamento:

1. Adicionar `pyproject.toml` com a versão mínima suportada do Python.
2. Declarar `numpy`, `pandas` e `matplotlib` com faixas testadas.
3. Separar dependências de execução e desenvolvimento.
4. Gerar lockfile conforme a ferramenta escolhida.
5. Documentar criação e ativação do ambiente virtual.

### 6.2 Artefatos de compilação

Binários reconstruíveis são versionados e `make clean` remove arquivos
rastreados.

Planejamento:

1. Produzir binários e módulos em `build/`.
2. Ignorar artefatos locais no Git.
3. Publicar binários somente como release versionada, acompanhada de checksum.
4. Registrar versão do compilador e flags de compilação.
5. Manter resultados golden separados de resultados comuns de execução.

### 6.3 Manifesto de execução

Cada execução deverá produzir um arquivo de proveniência em formato JSON com:

- data e identificador da execução;
- commit Git e indicação de worktree limpa ou modificada;
- modelo e variante executados;
- checksum do executável;
- compilador e flags;
- versões das dependências Python;
- hashes de todos os inputs;
- configuração efetiva;
- códigos de saída e duração;
- hashes dos outputs publicados.

## 7. Estratégia de Testes

### 7.1 Testes unitários Python

Cobrir:

- validação e geração de `config.json`;
- cálculo `Emis = QS * WIDTH`;
- criação da grade de receptores;
- parser AERMOD;
- parser RLINE sem descarte da última linha;
- validação de períodos e coordenadas;
- merge um-para-um;
- métricas, razões e R²;
- seleção de transecto;
- geometria usada nos gráficos.

### 7.2 Testes dos wrappers Shell

Usar executáveis falsos para simular:

- sucesso com outputs válidos;
- exit code não zero;
- ausência de output;
- output antigo;
- timeout;
- interrupção por sinal;
- duas execuções concorrentes;
- caminho absoluto e caminho contendo espaços.

### 7.3 Testes numéricos do RLINE corrigido

Cobrir:

- vento paralelo, perpendicular e quase paralelo;
- receptor no início, fim e centro da fonte;
- permutação da ordem dos receptores;
- permutação da ordem das fontes;
- duas fontes com configurações diferentes;
- rodovia deprimida;
- uma e duas barreiras;
- meteorologia ausente ou fisicamente inválida;
- integração que não converge;
- solução analítica e numérica;
- fonte de comprimento zero, que deve ser rejeitada.

### 7.4 Invariantes físicas

Validar automaticamente:

- multiplicar a emissão por cinco multiplica a concentração por cinco dentro da
  tolerância;
- aumentar a emissão efetiva pela largura produz escala coerente;
- concentrações válidas são finitas e não negativas;
- geometrias simétricas produzem respostas simétricas quando a meteorologia
  também é simétrica;
- pequenas variações angulares não causam descontinuidades artificiais.

### 7.5 Regressão EPA

Automatizar os conjuntos já presentes no repositório:

- Example Case;
- CALTRANS;
- Idaho Falls;
- Raleigh.

As comparações devem usar tolerâncias documentadas e nunca substituir os
arquivos golden durante um teste comum. Atualizações de golden devem exigir um
comando e revisão específicos.

### 7.6 Build de diagnóstico

Para o RLINE corrigido, manter um alvo de diagnóstico com opções equivalentes a:

```text
-O0 -g -Wall -Wextra -Wimplicit-interface -fcheck=all
-finit-real=snan -ffpe-trap=invalid,zero,overflow
```

As flags finais devem ser confirmadas com a versão mínima suportada do
`gfortran`. O build de release deve permanecer separado do build de diagnóstico.

## 8. Integração Contínua

A CI deverá ser introduzida gradualmente:

### Pipeline rápido por alteração

- validação de sintaxe Shell;
- lint e testes unitários Python;
- build limpo dos três modelos;
- build de diagnóstico do RLINE corrigido;
- smoke test com conjunto pequeno;
- verificação de que o repositório continua limpo após testes.

### Pipeline completo agendado

- quatro casos parametrizados;
- regressão EPA;
- builds paralelos repetidos;
- comparação original versus corrigido versus AERMOD;
- armazenamento de logs e manifestos como artefatos da CI.

## 9. Documentação e Governança

### 9.1 Documentos a revisar

- `README.md`;
- `GUIA_RLINE.md`;
- `GUIA_PIPELINE_AERMET_AERMOD_RLINE.md`;
- `PLANO_Compilacao_Uso_RLINE.md`;
- `PIPELINE_IMPLEMENTACAO.txt`.

### 9.2 Inconsistências a corrigir

- comando inválido de compilação manual do AERMET;
- versões divergentes sobre a inclusão do RLINE no AERMOD;
- métricas antigas diferentes dos resumos atuais;
- quantidade incorreta de scripts;
- funcionalidades existentes descritas como ainda não implementadas;
- interface incompleta de `run_aermod.sh`;
- exemplo de transecto divergente da configuração.

### 9.3 Arquivos de governança

Adicionar:

- `LICENSE` e/ou `NOTICE` com a licença de cada componente;
- origem e versão dos códigos e dados EPA;
- política para alterações no código upstream;
- `CONTRIBUTING.md`;
- `SECURITY.md`;
- processo de atualização de golden files;
- definição do que constitui resultado regulatório e resultado experimental.

## 10. Sequência de Implementação

### Fase 0. Baseline e proveniência

Objetivo: congelar o estado atual antes de alterar cálculos.

Entregas:

- checksums dos fontes, binários, inputs e resultados atuais;
- execução baseline identificada por manifesto;
- snapshot RLINE original documentado;
- separação conceitual entre original e corrigido.

Saída esperada: é possível reproduzir e identificar exatamente o estado anterior
às correções.

### Fase 1. Correções numéricas críticas

Objetivo: eliminar comportamento indefinido e casos de divisão por zero.

Entregas:

- patch de inicialização de `ueff`;
- patch de geometria para vento paralelo;
- patch do índice de rodovia deprimida;
- correção de `xwd_lim`;
- desalocação e status de convergência;
- interfaces explícitas nas rotinas alteradas;
- testes numéricos correspondentes.

Saída esperada: build de diagnóstico sem erro e cenários-limite aprovados.

### Fase 2. Execução segura e transacional

Objetivo: garantir que sucesso signifique resultado produzido pela execução
atual.

Entregas:

- wrappers com exit code preservado;
- timeout com encerramento do grupo;
- diretório temporário por execução;
- substituição atômica de cada output e rollback do conjunto em falha tratada;
- logs exclusivos;
- manifesto e proteção contra concorrência;
- testes com executáveis falsos.

Saída esperada: nenhuma saída antiga ou processo órfão é aceito.

### Fase 3. Dados, parsing e configuração

Objetivo: estabelecer contratos explícitos para entradas e saídas.

Entregas:

- schema de `config.json`;
- geração incondicional e determinística;
- parsers centralizados;
- remoção de `skipfooter`;
- validação de cardinalidade, coordenadas e períodos;
- caminhos totalmente parametrizados.

Saída esperada: mudar a configuração sempre muda os inputs corretos e qualquer
saída estruturalmente incompleta é rejeitada.

### Fase 4. Testes científicos

Objetivo: transformar os casos existentes em evidência automatizada.

Entregas:

- T1-T8 corrigidos;
- testes unitários Python;
- invariantes físicas;
- casos-limite do RLINE;
- regressão Example Case, CALTRANS, Idaho Falls e Raleigh;
- comparação das três variantes.

Saída esperada: alterações numéricas intencionais e regressões são claramente
distinguidas.

### Fase 5. Build, dependências e CI

Objetivo: permitir reconstrução limpa em ambiente novo.

Entregas:

- build em `build/`;
- Makefiles corrigidos;
- dependências Python declaradas;
- CI rápida e CI agendada;
- release de binários com checksums e proveniência.

Saída esperada: checkout limpo pode compilar, testar e reproduzir resultados
sem arquivos manuais ocultos.

### Fase 6. Visualização e documentação

Objetivo: garantir que gráficos, métricas e instruções representem o sistema
real.

Entregas:

- gráficos com geometria correta;
- rótulos estatísticos corretos;
- documentação consolidada;
- licença, NOTICE e guias de contribuição;
- resultados documentais gerados automaticamente quando possível.

Saída esperada: documentação e visualizações não divergem do código ou das
configurações.

## 11. Critérios Globais de Conclusão

O plano estará concluído quando:

1. O RLINE original permanecer reproduzível e separado da variante corrigida.
2. Não houver uso conhecido de variável não inicializada ou divisão por zero em
   entradas válidas.
3. Timeouts e falhas encerrarem todos os processos e retornarem erro.
4. Outputs antigos não puderem satisfazer uma execução nova.
5. Todos os casos definidos por JSON forem sempre enumerados pelos testes.
6. Cada receptor possuir exatamente os períodos esperados.
7. Os casos EPA fizerem parte da regressão automatizada.
8. Builds limpos e paralelos forem executados em CI.
9. Cada resultado publicado possuir manifesto de proveniência.
10. Gráficos e métricas utilizarem a geometria e os conceitos estatísticos
    corretos.
11. Um ambiente novo puder instalar dependências e reproduzir o pipeline apenas
    com instruções versionadas.
12. Licenças e origem de todos os componentes distribuídos estiverem claras.

## 12. Riscos da Implementação

| Risco | Mitigação |
|---|---|
| Correções alterarem resultados históricos | Preservar baseline, original e golden files; documentar deltas |
| Tolerâncias esconderem regressões | Definir tolerância por caso com justificativa científica |
| Patches divergirem do upstream | Manter patches pequenos, numerados e acompanhados de testes |
| CI completa ser lenta | Separar smoke tests por alteração e regressão agendada |
| Resultados versionados ficarem obsoletos | Manifestos, hashes e geração automatizada |
| Mudança de layout quebrar scripts externos | Levantar consumidores antes de mover caminhos públicos |
| Código Fortran antigo gerar muitos warnings | Introduzir flags gradualmente e tratar primeiro warnings de correção |

## 13. Ordem Recomendada para os Primeiros Commits

1. `docs: register upstream provenance and baseline`
2. `build: add patched rline build workflow`
3. `fix(rline): initialize effective wind before dispersion`
4. `fix(rline): handle wind parallel to line source`
5. `fix(rline): use explicit depressed-source index`
6. `fix(runners): make model execution transactional`
7. `fix(parser): preserve all rline observations`
8. `test: validate every configured scenario`
9. `test: add numerical edge cases and epa regression`
10. `ci: build and run smoke tests from clean checkout`
11. `docs: align guides with reproducible workflow`

Cada commit deve conter uma única mudança lógica, seus testes e a atualização
documental necessária. Mudanças numéricas não devem ser misturadas com
reorganizações de diretórios ou reformatação ampla.

## 14. Limitações desta Auditoria

A auditoria que originou este plano foi estática e somente leitura. Foram
examinados fontes Fortran, scripts Shell e Python, Makefiles, configurações,
documentação textual, logs e resultados existentes. Builds e pipelines não
foram executados porque sobrescrevem artefatos atualmente rastreados.

Executáveis e documentos binários não foram tratados como prova de que os
resultados correspondem aos fontes atuais. A primeira atividade da Fase 0 deve,
portanto, criar uma baseline executada e registrar essa correspondência.
