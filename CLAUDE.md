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

## ⚠️ Status atual: fase de edição manual, `build_grade.py` congelado

**Desde 08/Jul/2026, o projeto saiu do modo "gerado por script" e entrou em modo de ajuste manual semana a semana.** O usuário confirmou explicitamente: todas as regras algorítmicas iniciais já foram aplicadas, e a partir daí ele ajusta a grade manualmente, semana por semana, e cada ajuste **deve permanecer fixo** — inclusive quando semanas posteriores forem ajustadas depois.

**Isso significa: NÃO rodar `python3 build_grade.py` neste projeto a partir de agora, a menos que o usuário peça explicitamente uma regeneração completa.** Rodar o script descarta *todos* os ajustes manuais feitos desde então (ver log completo na seção "Ajustes manuais aplicados" abaixo) — ele recria a grade do zero a partir de `index.html.orig.bak` + a lógica de `build_grade.py`, que não sabe nada sobre o que foi feito manualmente depois.

`index.html` (+ `calendario.csv` + `disponibilidade-professor.html`) é agora a **base fixa e definitiva**. Qualquer pedido de ajuste ("mude a semana N para tal") deve ser implementado como edição pontual, direta, escopada exatamente à semana/célula pedida — sem tocar em mais nada, e sem rodar o script. Depois de qualquer edição manual no calendário do `index.html`, ainda é preciso rodar `python3 generate-professor-data.py` para ressincronizar o `disponibilidade-professor.html` (esse script só lê o `index.html`, não mexe em nada, é seguro rodar sempre).

### Como fazer uma edição pontual com segurança

Editar HTML minificado de ~360KB numa única linha por semana à mão é arriscado (`str.replace` ingênuo já corrompeu uma linha do CSV nesta sessão, ao operar sobre o arquivo inteiro em vez de por linha — ver histórico). Padrão que funcionou de forma confiável, usado em toda a fase manual:

1. **`calendario.csv`**: ler o arquivo respeitando exatamente o formato (`﻿` BOM + linhas `\r\n`, sem usar `open(..., newline='')` misturado com split ingênuo — leitura sem `newline=''` faz o Python traduzir `\r\n`→`\n` silenciosamente e quebra qualquer split subsequente por `\r\n`). Processar **linha a linha** (nunca `str.replace` no conteúdo inteiro do arquivo), filtrar/reconstruir só as linhas do(s) código(s) afetado(s), re-somar as datas/turmas, re-ordenar por `(data, horaInicio)` e reescrever com o mesmo BOM/CRLF. Sempre validar depois: contagem de 19 linhas por código (`awk -F';' 'NR>1{print $2}' calendario.csv | sort | uniq -c`).
2. **`index.html`**: localizar o bloco `<div class="cal-week" id="cal-sem-N">...` da semana via string search (não regex gulosa sobre o arquivo inteiro), extrair as `<tr>` (linha 0 = cabeçalho de dias, linha 1 = EXTRA, linha 2 = 1º, linha 3 = 2º, linha 4 = 3º, linha 5 = 4º, linha 6 = 5º, linha 7 = 6º — **8 linhas**, não 7, por causa do `<tr>` de cabeçalho) e depois as `<td>` de cada linha (índice 0=período, 1=horário, 2=Seg...8=Dom). Remover os `cal-entry` antigos do(s) código(s) afetado(s) por regex específica (cor + código + descrição, não um regex genérico), inserir os novos entries no fechamento `</td>` da célula certa. Validar contagem de divs por turma depois (`grep`/regex contando ocorrências de `APF-X` por código, esperando 2 por turma para disciplinas de 4h/2 slots, 1 para disciplinas de 2h/1 slot).
3. Sempre conferir visualmente antes de considerar concluído: renderizar a semana afetada com Chrome headless (`--headless --screenshot`) injetando um `mostrarSem(N, ...)` no `load`, e comparar com o que foi pedido.
4. Rodar `python3 generate-professor-data.py` por último.

## Como regenerar a grade (`build_grade.py`) — histórico/referência, NÃO USAR sem confirmar com o usuário

Rodar com `python3 build_grade.py` (lê `index.html.orig.bak`, escreve `index.html` e `calendario.csv`; depois rodar `python3 generate-professor-data.py` para sincronizar o `disponibilidade-professor.html`). Antes da fase manual (ver aviso acima), isso era usado sempre que:
- A carga horária de alguma disciplina no `CFP 3 AGENTES.xlsx` mudava (atualizar `DISCIPLINES` no script primeiro).
- O número de turmas mudava (atualizar `TURMAS`).
- As datas do curso mudavam (`COURSE_START`, `START_WEEK`, `END_WEEK`).

O script recria a grade inteira do zero a cada execução — não faz sentido rodá-lo e depois tentar mesclar com edições manuais feitas na UI; se o usuário já editou a grade manualmente (pela UI ou por mim), rodar o script de novo **descarta essas edições**. As regras abaixo descrevem a lógica do script tal como ficou configurada quando a fase manual começou — ainda é a base de como a grade *começou*, mas o estado atual do `index.html` já diverge bastante dela a partir da semana 7 (ver log de ajustes manuais).

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

### Ajustes manuais aplicados (fase de edição manual, a partir de 08/Jul/2026)

**Este é o estado real e atual da grade a partir da semana 7.** As regras 1-10 acima descrevem como `build_grade.py` gerou a base do curso (e ainda são precisas até por volta da semana 6); a partir daí, tudo listado abaixo foi aplicado como edição manual direta (`index.html` + `calendario.csv` + `disponibilidade-professor.html`), **sem** passar pelo script, e **substitui** o que o script teria produzido. Se o script rodar de novo por engano, tudo isto se perde — ver aviso no topo do arquivo.

- **Semana 7 (05–11/Out)**: M2.3 (Previdenciário) e M3.4 (IPED) rodam simultâneas, uma turma de cada por horário, segunda a quinta (mesmo padrão de pareamento das regras 6/8/9, só que feito à mão em vez de no script). Sexta 09/Out concentra as 4 turmas de M3.4 que sobraram sem par de M2.3 (F,G empilhadas de manhã; H,I empilhadas à tarde).
- **Semana 8 (12–18/Out)**: M3.4 continua (turmas J–S). As turmas de M2.4 (Damaz) que estavam na semana 9 (A–J) foram trazidas pra cá, simultâneas com M3.4 em cada célula.
- **Semana 9 (19–25/Out)**: as turmas de M2.4 que estavam na semana 10 (K–S) foram trazidas pra cá, simultâneas com M3.5 (Planejamento de Operação), que já estava nessa semana.
- **Semanas 10–11 (26/Out–06/Nov)**: M2.5, M2.6 e M2.7 (DCiber) inteiras reorganizadas — só 2 turmas/dia, cada uma fazendo as 3 partes do DCiber em sequência no mesmo turno: manhã (Extra→M2.5, 1º→M2.6, 2º→M2.7) e tarde (3º→M2.5, 4º→M2.6, 5º→M2.7, este último já em horário noturno). Turma A começa segunda 26/Out; turma S (a 19ª, sozinha) fecha na sexta 06/Nov de manhã.
- **Semanas 12–13 (09–20/Nov)**: M3.6 (Desencadeamento) reconstruída do zero começando na turma A, segunda a sexta, sem empilhamento — 1º+2º horário de manhã, 3º+4º à tarde, 2 turmas/dia. Termina na turma S, sexta 20/Nov de manhã. (Motivo original do deslocamento: a semana 11 passou a ser só DCiber; a versão final foi reconstruída do zero a pedido do usuário, não é mais o deslocamento "+1 dia útil" que foi tentado primeiro.)
- **M3.7 (Análise de Material Apreendido)**: as turmas que ocupavam 20/Nov (que hoje é semana de M3.6) foram deslocadas para a sexta seguinte (27/Nov), empilhadas com o que já estava lá. Depois, a **semana 14 inteira (23–29/Nov)** foi reordenada em sequência A→S pela posição no calendário (mesmos dias/horários de antes, só a letra da turma mudou para ficar em ordem).
- **Semana 15 (30/Nov–04/Dez)**: M3.8 (Audiência de Instrução) reconstruída inteira dentro da semana, começando na turma A — segunda a sexta, 4 turmas/dia (1º ao 4º horário, sem Extra/5º/6º), termina em S na sexta.
- **Semana 16 (07–11/Dez)**: M3.9 (Revisão) reconstruída do mesmo jeito, começando na turma A.
- **Referência histórica (já obsoleta)**: consolidação do IPED de 23/Out em 22/Out (semana 9) — feita antes da fase manual atual, depois substituída pelo que está descrito acima. Duas turmas de M3.2 que sobravam em 25/Set também já foram resolvidas (ver regra 9).

Sempre que uma nova semana for ajustada manualmente, adicionar um item aqui (não é opcional — é a única forma de uma sessão futura saber o que já foi fixado e não deve ser mexido sem pedido explícito).

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

Botão na barra de filtros (`.ref-btn`, ao lado do filtro de Turma) abre um modal (`#ref-overlay`) com uma tabela comparando grade original × grade atual, por semana. **Desde 09/Jul/2026, a tabela tem 6 colunas de dados** (não mais 2): 3 colunas por módulo (M1/M2/M3) para a "Grade Original (EPF)" e 3 colunas por módulo para a "Grade Atual (APF)", com cabeçalho de dois níveis (`colspan="3"` agrupando cada bloco + uma linha com M1/M2/M3) e cores diferentes por bloco (`.ref-grp-orig` roxo claro, `.ref-grp-atual` roxo mais escuro) — pedido explícito do usuário para melhorar a comparação visual módulo a módulo, já que antes cada célula misturava M1/M2/M3 no mesmo texto.

A coluna EPF é estática (extraída à mão uma vez da grade CFP2/2026, mesmos dados da tabela na regra 1 acima, só reparticionada por módulo). **A coluna APF não é mais recalculada automaticamente** — `build_grade.py` está congelado (ver aviso no topo do arquivo), então o mecanismo antigo (`REF_EPF_ORIGINAL` + `_week_summary_atual()` no script) não roda mais. A partir da fase manual, essa coluna é **atualizada à mão direto no `index.html`** toda vez que uma semana é ajustada: recalcular a partir do `calendario.csv` (agrupar por semana pela data, contar ocorrências por código — despadronizando `M2.04`→`M2.4` etc. —, separar por módulo M1/M2/M3, ordenar dentro de cada módulo pela ordem de `DISCIPLINES` em `build_grade.py`) e substituir `<thead>`+`<tbody id="ref-tbody">` por regex no `index.html`. **Isso significa que, depois de qualquer ajuste manual de semana, vale a pena perguntar ao usuário se quer o botão Referência atualizado também** — não acontece sozinho.

CSS/HTML/JS do botão e do modal ainda vivem no `index.html.orig.bak` também (herdado de quando o botão era gerado pelo script), mas isso deixou de importar na prática enquanto `build_grade.py` estiver congelado — a fonte da verdade agora é só o `index.html` atual.

### Persistência local (localStorage)

- `gh_token` — Personal Access Token do GitHub (compartilhado entre os dois projetos de propósito).
- `gh_repo_cfp3` — repositório GitHub (`owner/repo`) para onde o botão "SALVAR NO GITHUB" envia o `index.html`. **Não hardcoded** — o `index.html.orig.bak` herdado do projeto irmão tinha isso fixo no repo antigo (`marcelmfpm-ai/GRADE_PRELIMINAR`), o que faria este projeto (CFP3) salvar por engano no repositório do CFP2. Corrigido em 08/Jul/2026: `saveToGithub()`/`fallbackDownloadAndUpload()` agora leem esse valor do localStorage, perguntando (`prompt`) e salvando na primeira vez que faltar — mesmo padrão do `gh_token`. O botão de engrenagem (⚙, `configureGithubToken()`) também passou a perguntar o repo depois do token. Sem esse valor configurado, nada é enviado a lugar nenhum.
- `grade_apc_cfp3_2026_calendar_dragdrop_print_v3` — layout do drag-and-drop (namespaced com `cfp3` para não colidir com o projeto CFP2 original se abertos no mesmo navegador).
- `semanas_marcadas_cfp3` — semanas marcadas como conferidas (idem, namespaced).
