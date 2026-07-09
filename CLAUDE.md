# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## O que é este projeto

Painel single-page (sem build system) que gerencia a grade de aulas/calendário do curso **"GRADE APC CFP3/2026"** — 3º Curso de Formação Profissional, cargo único **APF (Agente de Polícia Federal)**, **19 turmas** (`APF-A` a `APF-S`). Curso de 07/Set a 18/Dez/2026, semanas 3 a 17 (15 semanas).

Este projeto é uma adaptação do projeto irmão `GRADE_PRELIMINAR` (CFP2/2026, 4 cargos: EPF/DPF/PPF/PCF, 19 turmas ao todo). A UI (`index.html`) é praticamente idêntica em estrutura/JS — só a config (cargo único, turmas, semanas) e o conteúdo do calendário mudam. Ver esse projeto irmão se precisar entender alguma função da UI não documentada aqui.

## Arquivos do repositório

- `index.html` — a aplicação inteira (UI + dados + lógica), ~360KB.
- `index.html.orig.bak` — cópia intocada do `GRADE_PRELIMINAR` original (4 cargos), no estado em que foi copiado para este projeto. **Não é só um backup de segurança** — é o *input* que `build_grade.py` lê para reconstruir a estrutura HTML (nav de semanas, wrapper do calendário) a cada regeração. Não apagar.
- `build_grade.py` — script Python que gera a grade inteira (calendário + config) a partir do zero, aplicando as regras de agendamento descritas abaixo. Ver seção "Como regenerar a grade" mais adiante.
- `CFP 3 AGENTES.xlsx` — planilha-fonte do currículo (aba DESCRIÇÃO: código/descrição/horas de cada disciplina; aba HORÁRIO: os 7 horários do dia). Se as horas de alguma disciplina mudarem, atualizar a lista `DISCIPLINES` em `build_grade.py` e rerodar.
- `generate-csv.js` — script Node (`jsdom`) que extrai os dados do calendário de dentro do `index.html` e gera `calendario.csv`. Mantido do projeto original; `build_grade.py` já gera o CSV diretamente (mais simples, sem depender de Node), então normalmente não precisa rodar isso.
- `calendario.csv` — saída gerada; não editar manualmente.
- `disponibilidade-professor.html` + `generate-professor-data.py` — ferramenta separada de consulta de disponibilidade de professor; rodar `python3 generate-professor-data.py` depois de qualquer mudança no calendário do `index.html` para manter os dados embutidos sincronizados.
- `.github/workflows/generate-csv.yml` — herdado do projeto original; dispara `generate-csv.js` a cada push. Como este repo não tem remoto configurado ainda, é inofensivo mas pode ser removido se nunca for usado.

## Como regenerar a grade (`build_grade.py`)

Rodar com `python3 build_grade.py` (lê `index.html.orig.bak`, escreve `index.html` e `calendario.csv`; depois rodar `python3 generate-professor-data.py` para sincronizar o `disponibilidade-professor.html`). Use isso sempre que:
- A carga horária de alguma disciplina no `CFP 3 AGENTES.xlsx` mudar (atualizar `DISCIPLINES` no script primeiro).
- O número de turmas mudar (atualizar `TURMAS`).
- As datas do curso mudarem (`COURSE_START`, `START_WEEK`, `END_WEEK`).

O script recria a grade inteira do zero a cada execução — não faz sentido rodá-lo e depois tentar mesclar com edições manuais feitas na UI; se o usuário já editou a grade manualmente pela UI (drag-and-drop), rodar o script de novo **descarta essas edições**.

### Regras de agendamento (extraídas da grade original de 4 cargos)

A grade original (`GRADE_PRELIMINAR`, CFP2/2026) foi analisada célula a célula para servir de parâmetro. Padrão observado e replicado aqui:

1. **Preenchimento sequencial em cascata, com M2/M3 intercalados**: as disciplinas são processadas uma de cada vez, na ordem definida em `DISCIPLINES` (`build_grade.py`), preenchendo os 4 horários diurnos de cada dia antes de avançar para o próximo dia — quando uma disciplina termina de atender todas as turmas, a próxima já começa nos horários que sobraram naquele mesmo dia. **Módulo 1, 2 e 3 não são pré-requisito um do outro** — a sequência só precisa ser respeitada *dentro* de cada módulo (M2.1 antes de M2.2 antes de M2.3, etc.; idem para M3), mas M2 e M3 podem (e devem) se intercalar livremente. Por isso `DISCIPLINES` alterna entre as duas (M2.1, M3.1, M2.2, M3.2, M3.3, M2.3, M3.4, ...) em vez de rodar todo o M2 e só depois todo o M3 — isso espalha a carga de cada módulo ao longo do curso todo em vez de empilhar a carga do módulo mais pesado no fim. Confirmado na grade original: ver tabela da EPF abaixo, onde M2.x e M3.x já aparecem misturados na mesma semana desde a semana 4.

   **Referência — aulas da EPF por semana na grade original** (cargo com mais turmas, 9, o mais parecido em volume ao nosso caso de 19 turmas; código(nº de ocorrências)):

   | Semana | Aulas EPF |
   |---|---|
   | 3 | M1.1(8) |
   | 4 | M2.1(9), M3.1(9) |
   | 5 | M3.2(9), M2.2(9), M1.1(2) |
   | 6 | M2.3(5), M1.1(8) |
   | 7 | M2.3(4), M3.3(4) |
   | 8 | M3.3(14) |
   | 9 | M2.4(16), M1.2(6) |
   | 10 | M3.4(18), M2.4(2), M2.5(4), M2.6(4), M2.7(4) |
   | 11 | M2.5(5), M2.6(5), M2.7(5), M1.2(6) |
   | 12 | M3.5(9) |
   | 13 | M3.6(9), M3.7(8), M1.2(6) |
   | 14 | M3.7(10), M3.8(9), M3.9(9) |
   | 15 | M3.10(9) |
2. **Trilha noturna (M1.1 Plantão + M1.2 Sobreaviso)**: sempre à noite (5º/6º horário, a partir de 19h), nunca durante o dia, só em dias úteis (Seg-Qui). Regra explícita do usuário (não vem da grade original): **M1.1 primeiro, turmas em ordem alfabética, 8 turmas/semana** — como M1.1 só precisa de 1 horário (2h), cabem 2 turmas diferentes por dia (uma no 5º, outra no 6º) × 4 dias = 8/semana (sem.3=A-H, sem.4=I-P, sem.5=Q-S). **Depois M1.2 começa do zero na semana seguinte**, mesma lógica alfabética mas só **4 turmas/semana** (M1.2 tem 4h, precisa dos dois horários juntos para a mesma turma, então só 1 turma/dia × 4 dias) — sem.6=A-D, sem.7=E-H, sem.8=I-L, sem.9=M-P, sem.10=Q-S. Implementado em `m1_groups` no `build_grade.py`.
3. **M3.3 Aeroporto**: terça/quarta/quinta **somente à tarde** (a partir do 3º horário); sábado/domingo **manhã e tarde**. Roda em paralelo com M3.4 (IPED) nas semanas em que as duas se sobrepõem no fim de seu percurso, já que M3.3 só ocupa os horários 3º/4º nesses dias específicos, sobrando manhã e os demais dias para M3.4. Onde exatamente M3.3 *começa* hoje é regra explícita do usuário — ver regra 10 abaixo (não é mais "logo depois de M2.2/M3.2 terminarem": desde a regra 10, M3.3 é alocada *antes* de M2.2, começando fixo na Semana 5/terça).
4. **Regra geral de fim de semana**: por padrão, nenhuma disciplina (fora M3.3) usa sábado ou domingo. **Domingo nunca é usado** fora de M3.3. Sábado só é usado como último recurso, quando a disciplina genuinamente não cabe de segunda a sexta — e nesse caso, o sábado usado é sempre da **mesma semana** e com o **mesmo código** que já está rodando naquela semana (agrupado, não espalhado).
5. **Simultaneidade (repetição de turmas no mesmo horário)**: a grade original quase nunca repete a mesma disciplina simultaneamente (1 turma por vez). Simultaneidade (até 3 turmas ao mesmo tempo) só aparece nas 1-2 últimas semanas do curso, e só nos cargos com mais turmas (EPF=9, DPF=5); cargos menores (PCF=3, PPF=2) nunca precisaram. Replicado via `PACKED_CODES`: disciplinas cedo do currículo rodam em modo estrito (`max_cap=2`, nunca simultâneas na prática); só as disciplinas que caem na segunda metade do curso (hoje: `M3.4, M3.5, M2.5, M3.6, M2.6, M3.7, M2.7, M3.8, M3.9`) entram em modo "packed" (empilhamento permitido) — mesmo assim, restrito de fato às últimas semanas. Com 19 turmas (mais que o dobro do maior cargo antigo, 9), o teto de empilhamento (`STACK_CAP`) foi mantido em 6 como margem de segurança — ajuste proporcional à quantidade de turmas, autorizado explicitamente pelo usuário. Atualmente isso empurra 17 sessões de M3.9 para o sábado da última semana (regra 4); se a carga horária ficar mais folgada de novo isso pode voltar a caber 100% em dias úteis (já aconteceu antes). Se o script falhar com `RuntimeError: Ran out of days`, é sinal de que os parâmetros atuais não bastam.
6. **M2.1 (Eleitoral 1) e M3.1 (Fonte Humana) rodam em paralelo, 1 turma de cada por horário.** Regra explícita do usuário, mesmo padrão da regra 8 (M2.4/M3.5) — pediu para "associar" as duas, com a restrição explícita de que a mesma turma nunca pode estar nas duas ao mesmo tempo (garantido automaticamente pelo `turma_free()`, que já impede qualquer turma de ocupar 2 entradas no mesmo horário). **Isto substituiu a regra antiga** de que M3.1 sempre tinha 2 turmas simultâneas entre si (`DUAL_CODES` está vazio hoje — ver histórico no código). Implementado com o mesmo mecanismo da regra 8: M3.1 é pulada na sua própria passagem pelo loop (`if code == 'M3.1': continue`) e alocada dentro do bloco `if code == 'M2.1':`, começando em `lowest_used` (primeiro dia que M2.1 ocupou) com `lookahead` **calculado dinamicamente** como `highest - lowest_used + 1` (a janela exata do próprio M2.1) em vez do `PACKED_LOOKAHEAD` fixo de 10 dias — necessário porque M2.1 só usa 5 dias úteis, e uma janela de 10 dias corridos escaparia para dias genuinamente livres antes de forçar o empilhamento. Resultado: as 19 turmas de M3.1 caem exatamente nas mesmas células (semana,dia,horário) das 19 turmas de M2.1.
7. **M2.4 (Damaz): nunca 2 turmas de M2.4 ao mesmo tempo** (regra independente da 6) — pode dividir um horário com outra disciplina diferente, mas nunca com outra instância de si mesma. Implementado via `NO_SELF_STACK = {'M2.4'}`: `day_has_room()` agora rastreia não só *quantas* entradas ocupam um horário (`day_occ`), mas *quais códigos* (`day_codes`), e bloqueia a reserva se o código já estiver presente naquele horário, independente do `cap`. Por isso M2.4 saiu de `PACKED_CODES` (não tinha mais sentido lhe dar um teto de empilhamento alto, já que nunca empilha consigo mesma). Se outra disciplina precisar da mesma restrição, adicionar o código a `NO_SELF_STACK`.
8. **M2.4 (Damaz) e M3.5 (Planejamento de Operação) rodam em paralelo, no mesmo horário** — regra explícita do usuário (pedido para "associar" as duas disciplinas, já que M2.4 e M3.5 são vizinhas na sequência do currículo e ele vai continuar ajustando manualmente a partir daí). Implementado como um caso especial dentro do loop principal: quando `code == 'M2.4'` termina de alocar as 19 turmas, o loop dispara imediatamente a alocação de M3.5 (que é pulada na sua própria passagem — `if code == 'M3.5': continue`), começando a busca não em `disc_start` (que pode ter sobra de capacidade livre de antes de M2.4 começar) mas em `lowest_used`, o primeiro dia que M2.4 de fato ocupou. Isso garante que, dentro da janela de `PACKED_LOOKAHEAD`, toda célula já esteja com M2.4 em `cap=1`, forçando M3.5 (que tenta `cap=1` primeiro e falha em todo lugar) a cair em `cap=2`, ocupando a mesma célula (semana,dia,horário) de uma turma de Damaz — mesmo mecanismo de empilhamento usado em outras disciplinas, só que aplicado de propósito para forçar coincidência em vez de evitá-la. Resultado: as 19 turmas de M3.5 caem exatamente nos mesmos 5 dias (26–30/Out) que as primeiras 10 turmas de M2.4 usam, uma M3.5 por slot ao lado de cada M2.4. Se outro par de disciplinas precisar da mesma regra, replicar o padrão (pular a segunda disciplina no loop genérico, disparar sua alocação dentro do bloco `if code == '<primeira>':`, usando `lowest_used` da primeira como ponto de partida).
9. **M2.2 (Eleitoral 2) e M3.2 (Planejamento de Vigilância) rodam em paralelo, 1 turma de cada por horário** — mesmo padrão das regras 6 e 8. M3.2 é pulada na sua própria passagem (`if code == 'M3.2': continue`) e alocada dentro do bloco `if code == 'M2.2':`, começando em `lowest_used` com `lookahead` dinâmico (`highest - lowest_used + 1`, mesma razão da regra 6: a janela do M2.2 não é longa o bastante para o `PACKED_LOOKAHEAD` fixo não vazar para dias livres). Resultado: as 19 turmas de M3.2 caem nas mesmas células das 19 turmas de M2.2, sem sobra.
10. **M3.3 (Aeroporto) começa fixo na Semana 5/terça, antes de M2.2 ser alocada** — regra explícita do usuário: além de sábado/domingo (regra 3), M3.3 passou a usar também terça/quarta/quinta *da Semana 5* especificamente (não "onde quer que M2.2 esteja"), e as turmas de M2.2 (+ M3.2 pareada, regra 9) que usariam essas tardes são realocadas automaticamente para sexta e para a Semana 6. Implementado invertendo a ordem: dentro do bloco `if code == 'M2.2':`, **antes** do loop que aloca as 19 turmas de M2.2, roda primeiro a alocação completa de M3.3 (mesmos `aero_day_ok`/`aero_pool` da regra 3), com `aero_start = ALL_DAYS.index((5, 1))` — **semana 5 hardcoded**, não derivado de `disc_start`, porque o pedido foi para essa semana específica, não "onde o M2.2 cair". Como M3.3 reserva as tardes de terça/quarta/quinta primeiro, a busca `cap=1`-primeiro de M2.2 (que roda logo em seguida, mesmo `disc_start` de sempre) naturalmente pula essas células já ocupadas e usa as manhãs desses dias + segunda e sexta inteiras, transbordando para a Semana 6 quando a Semana 5 se esgota — sem nenhuma lógica extra de "liberar dias", só o mecanismo de busca cap=1 já existente encontrando outro lugar. Se a Semana 5 mudar de posição no calendário (`COURSE_START`/`START_WEEK`), esse `5` precisa ser revisado à mão.

Esses parâmetros (`STACK_CAP`, `STRICT_LOOKAHEAD`, `PACKED_LOOKAHEAD`, `PACKED_CODES`, `DUAL_CODES`, `NO_SELF_STACK`, `MAX_M1_PER_WEEK`) estão todos no topo/meio de `build_grade.py`, comentados. Se o número de turmas ou a carga horária mudar muito, pode ser necessário reajustar `STACK_CAP` e `PACKED_CODES` por tentativa — o script falha com `RuntimeError: Ran out of days placing ...` quando os parâmetros atuais não são suficientes para caber no curso; nesse caso, é hora de aumentar `STACK_CAP`, ampliar `PACKED_CODES`, ou negociar com o usuário exceções de dia/horário.

### Ajustes manuais pontuais feitos direto no `index.html` (fora do `build_grade.py`)

Nem todo ajuste vira regra geral no script — às vezes é uma edição pontual, feita direto no DOM do `index.html` (e replicada à mão no `calendario.csv`/`disponibilidade-professor.html`), quando o usuário só quer mexer num ponto específico da grade sem alterar o algoritmo. **Rodar `build_grade.py` de novo recalcula tudo do zero e descarta esses ajustes** — por isso ficam listados aqui, não no código.

Nenhum ajuste pontual ativo no momento. Histórico do que já passou por aqui e não se aplica mais:
- Consolidação do IPED de 23/Out em 22/Out (semana 9) — descartada quando a grade foi regenerada em 08/Jul/2026 para implementar a regra 8 (M2.4/M3.5 em paralelo).
- Duas turmas de M3.2 (Planejamento de Vigilância) que sobravam sozinhas em 25/Set foram movidas à mão para 18/Set (junto com M2.2) em 08/Jul/2026 — essa edição manual foi **descartada** por uma regeneração subsequente do `build_grade.py`, mas o problema que ela corrigia deixou de existir: a regra 9 (M2.2/M3.2 com `lookahead` dinâmico) já garante pareamento 1:1 sem sobra nenhuma toda vez que o script roda, então esse ajuste manual não precisa mais ser reaplicado.

## Arquitetura da UI (herdada do projeto original)

### Duas representações paralelas dos mesmos dados

Os dados das aulas existem em **dois lugares** dentro do `index.html`:

1. **Array `DADOS`** (`let DADOS = [...]`, dentro do `<script>` principal) — fonte "estruturada". Cada item é `[semana, codigoModulo, turma, dia, descricao, horario, horas]`. Alimenta gráficos/tabelas/Gantt via `filtrarDados()` → `renderAll()`. **É sobrescrito no carregamento** por `refreshDadosFromCalendario()`, que reconstrói `DADOS` a partir do DOM do calendário — então o array inicial no arquivo é só um snapshot inicial, não precisa estar manualmente sincronizado (mas `build_grade.py` já gera os dois consistentes, então não deveria haver diferença).
2. **Calendário renderizado em `#cal-container`** — HTML com `<div class="cal-entry">` dentro de `.cal-week`/`.cal-td`, editável na UI (duplo clique, drag-and-drop, Ctrl+C/V, Delete). Esta é a **fonte da verdade real** — é o que `extractCalendarRows()`/`generate-csv.js`/`refreshDadosFromCalendario()` leem.

### Config de cargo/turmas

`CARGOS=['APF']`, `COLS={APF:'#7a5ea8'}`, `BASE_TURMAS={APF:19}`, `DCIBER_PARES={APF:['M2.5','M2.6','M2.7']}`. `getCargo()`/`classCargo()` só reconhecem `APF` (qualquer outra coisa cai em `'outro'`/`'apf'` fallback).

### Filtros, abas e exports

Ver `GRADE_PRELIMINAR/CLAUDE.md` (projeto irmão) para os detalhes de `filtrarDados()`, `renderAll()`, as 6 abas (`panel-visao`, `panel-grade`, `panel-semanas`, `panel-gantt`, `panel-calendario`, `panel-graficos`), e os exports (XLSX via ExcelJS, CSV, HTML atualizado, GitHub) — tudo idêntico neste projeto, só os dados de cargo/turma mudam.

### Botão "Referência"

Botão na barra de filtros (`.ref-btn`, ao lado do filtro de Turma) abre um modal (`#ref-overlay`) com uma tabela de duas colunas por semana: a coluna estática "Aulas EPF · grade original" (extraída à mão uma vez da grade CFP2/2026, mesmos dados da tabela na regra 1 acima) e a coluna "Aulas APF · grade atual", **recalculada em toda regeração** a partir de `entries` no `build_grade.py` (agrupa por semana, conta ocorrências por código, ordena pela ordem de `DISCIPLINES`). Serve para o usuário comparar visualmente como a grade atual (19 turmas) ficou em relação ao parâmetro original (EPF, 9 turmas).

CSS/HTML/JS do botão e do modal vivem no **`index.html.orig.bak`** (não só no `index.html` gerado) — incluindo o placeholder `<tbody id="ref-tbody"><!--REF_ROWS--></tbody>`, que o `build_grade.py` localiza e substitui pelas linhas calculadas (`REF_EPF_ORIGINAL` + `_week_summary_atual()`, perto do final do script, antes de escrever `OUT_HTML`). Por estar no `.orig.bak`, o botão **sobrevive a qualquer regeneração** — diferente dos ajustes pontuais da seção acima, que são perdidos.

### Persistência local (localStorage)

- `gh_token` — Personal Access Token do GitHub (compartilhado entre os dois projetos de propósito).
- `gh_repo_cfp3` — repositório GitHub (`owner/repo`) para onde o botão "SALVAR NO GITHUB" envia o `index.html`. **Não hardcoded** — o `index.html.orig.bak` herdado do projeto irmão tinha isso fixo no repo antigo (`marcelmfpm-ai/GRADE_PRELIMINAR`), o que faria este projeto (CFP3) salvar por engano no repositório do CFP2. Corrigido em 08/Jul/2026: `saveToGithub()`/`fallbackDownloadAndUpload()` agora leem esse valor do localStorage, perguntando (`prompt`) e salvando na primeira vez que faltar — mesmo padrão do `gh_token`. O botão de engrenagem (⚙, `configureGithubToken()`) também passou a perguntar o repo depois do token. Sem esse valor configurado, nada é enviado a lugar nenhum.
- `grade_apc_cfp3_2026_calendar_dragdrop_print_v3` — layout do drag-and-drop (namespaced com `cfp3` para não colidir com o projeto CFP2 original se abertos no mesmo navegador).
- `semanas_marcadas_cfp3` — semanas marcadas como conferidas (idem, namespaced).
