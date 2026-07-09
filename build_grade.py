#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re, datetime

PROJ = "/Users/marcelfelipeprocopiodemoura/Documents/PROJETOS CLAUDE/GRADE PRELIMINAR 3 CFP"
IN_HTML = PROJ + "/index.html.orig.bak"
OUT_HTML = PROJ + "/index.html"
OUT_CSV = PROJ + "/calendario.csv"

# ---------- Basic data ----------
TURMAS = [f"APF-{chr(65+i)}" for i in range(19)]  # APF-A .. APF-S

MONTH_ABBR = {1:'Jan',2:'Fev',3:'Mar',4:'Abr',5:'Mai',6:'Jun',7:'Jul',8:'Ago',9:'Set',10:'Out',11:'Nov',12:'Dez'}
MONTH_FULL = {1:'Janeiro',2:'Fevereiro',3:'Março',4:'Abril',5:'Maio',6:'Junho',7:'Julho',8:'Agosto',9:'Setembro',10:'Outubro',11:'Novembro',12:'Dezembro'}
DAY_ABBR = ['Seg','Ter','Qua','Qui','Sex','Sáb','Dom']

COURSE_START = datetime.date(2026,9,7)  # Monday, week 3
START_WEEK = 3
END_WEEK = 17

def week_monday(n):
    return COURSE_START + datetime.timedelta(days=7*(n-START_WEEK))

WEEKS = list(range(START_WEEK, END_WEEK+1))

SLOTS = [
    ('EXTRA','06:00','07:40'),
    ('1','08:00','09:40'),
    ('2','10:00','11:40'),
    ('3','13:50','15:30'),
    ('4','15:50','17:30'),
    ('5','19:00','20:40'),
    ('6','20:50','22:30'),
]
SLOT_LABELS = ['EXTRA','1º','2º','3º','4º','5º','6º']

# code, description, hours, kind
# kind: 'plantao'/'sobreaviso' = night track; 'aeroporto' = constrained-day track;
#       'free' = sequential daytime track (cascading fill)
#
# Order matters here: the internal sequence *within* a module (M2.1 before
# M2.2 before M2.3, etc.; same for M3) must be respected, but M2 and M3 are
# NOT prerequisites of each other, so they're interleaved rather than run as
# "all of M2 then all of M3" — that spreads each module's load across the
# whole term instead of stacking the heavier module's demand at the tail.
DISCIPLINES = [
    ('M1.1', 'Plantão', 2, 'plantao'),
    ('M1.2', 'Sobreaviso', 4, 'sobreaviso'),
    ('M2.1', 'Eleitoral 1', 2, 'free'),
    ('M3.1', 'Fonte Humana', 2, 'free'),
    ('M2.2', 'Eleitoral 2', 4, 'free'),
    ('M3.2', 'Planejamento de Vigilância', 2, 'free'),
    ('M3.3', 'Aeroporto', 4, 'aeroporto'),
    ('M2.3', 'Previdenciário', 2, 'free'),
    ('M3.4', 'IPED', 4, 'free'),
    ('M2.4', 'Damaz', 4, 'free'),
    ('M3.5', 'Planejamento de Operação', 2, 'free'),
    ('M2.5', 'DCiber', 2, 'free'),
    ('M3.6', 'Desencadeamento', 4, 'free'),
    ('M2.6', 'DCiber', 2, 'free'),
    ('M3.7', 'Análise de Material Apreendido', 4, 'free'),
    ('M2.7', 'DCiber', 2, 'free'),
    ('M3.8', 'Audiência de Instrução', 2, 'free'),
    ('M3.9', 'Revisão', 2, 'free'),
]

MOD_COLORS = {
    'M1': ('#eeecfc', '#4a3fb0'),
    'M2': ('#fce8f0', '#8a2050'),
    'M3': ('#fdf3e3', '#8a5a10'),
}

def mod_of(code):
    return code.split('.')[0]

total_hours = sum(d[2] for d in DISCIPLINES)
print(f"Total hours per turma: {total_hours}")

# ---------- Scheduling ----------
# Design mirrors the original grade's observed pattern (extracted from the old
# 4-cargo course): for a given track, one discipline is filled to capacity
# across successive DAYS (cascading — a new discipline picks up mid-day right
# where the previous one left off) rather than being pinned to one fixed slot
# and spread thinly across the whole term. Night (M1) and the day-track are
# independent (different slot numbers, run concurrently in time); M3.3 has its
# own constrained day-set but shares the same day/slot occupancy bookkeeping
# so it never collides with the sequential day-track around it.

ALL_DAYS = [(w, d) for w in WEEKS for d in range(7)]  # every day, Mon(0)..Sun(6), whole term

# The original grade mostly puts one turma per (day,slot) cell, and stacks up
# to 3 only in its final crammed weeks. With 19 turmas on a single curriculum
# (vs. the original's 4 parallel cargos, max 9 turmas each, splitting the same
# 4-slots/day resource four ways) fitting the same weekly rhythm needs more
# concurrent rooms per slot than 3 in this course's own final week — the
# "ajuste necessário à quantidade de turmas" the adjustment explicitly called
# for. Verified this only ever gets used in the last few weeks (see PACKED_CODES
# below), never spread across the bulk of the course, same as the original.
STACK_CAP = 6

occupied = {t: set() for t in TURMAS}   # turma -> set of (week,day,slot)
day_occ = {}                             # (week,day) -> Counter of slot -> count (1-4 daytime, 5-6 night)
day_codes = {}                           # (week,day,slot) -> set of codes already placed there
entries = []

# Codes that may share a slot with a *different* discipline, but must never
# stack with another instance of themselves (explicit user rule for M2.4).
NO_SELF_STACK = {'M2.4'}

def reserve(week, day_idx, slot_start_idx, span, code, desc, turma):
    entries.append(dict(week=week, day=day_idx, slot=slot_start_idx, span=span, code=code, desc=desc, turma=turma))
    from collections import Counter as _Counter
    occ = day_occ.setdefault((week, day_idx), _Counter())
    for s in range(slot_start_idx, slot_start_idx + span):
        occupied[turma].add((week, day_idx, s))
        occ[s] += 1
        day_codes.setdefault((week, day_idx, s), set()).add(code)

def day_has_room(week, day_idx, slot_start_idx, span, cap=1, code=None):
    occ = day_occ.get((week, day_idx), {})
    if not all(occ.get(slot_start_idx + i, 0) < cap for i in range(span)):
        return False
    if code in NO_SELF_STACK:
        for i in range(span):
            if code in day_codes.get((week, day_idx, slot_start_idx + i), ()):
                return False
    return True

def turma_free(turma, week, day_idx, slot_start_idx, span):
    return all((week, day_idx, slot_start_idx + i) not in occupied[turma] for i in range(span))

# --- M1 track (night, slots 5/6): M1.1 first, alphabetical, then M1.2 picks up
# the same way starting the week after M1.1 finishes. M1.1 is only 1 slot (2h),
# so two *different* turmas fit per day — one in 5º, another in 6º — for 8
# turmas/week (sem.3=A-H, sem.4=I-P, ...). M1.2 is 4h (needs both slots for the
# same turma), so only 1 turma/day fits — 4 turmas/week, same alphabetical
# pattern, starting the week right after M1.1's last turma.
m1_groups = [
    ([(t, 'M1.1', 'Plantão', 1) for t in TURMAS], 2),   # 2 turmas/day (slot 5, slot 6)
    ([(t, 'M1.2', 'Sobreaviso', 2) for t in TURMAS], 1),  # 1 turma/day (slots 5+6 together)
]
wi = 0
for group, per_day in m1_groups:
    ti = 0
    while ti < len(group):
        week = WEEKS[wi]
        for day_idx in range(4):  # Mon-Thu
            for slot_offset in range(per_day):
                if ti >= len(group):
                    break
                turma, code, desc, span = group[ti]
                reserve(week, day_idx, 5 + slot_offset, span, code, desc, turma)
                ti += 1
        wi += 1

# --- Sequential daytime track (slots 1-4): curriculum order, cascading fill ---
cursor = 0  # index into ALL_DAYS, shared/advancing across disciplines

# Extracted from the *original* 4-cargo grade: most disciplines never repeated
# simultaneously (1 turma at a time); stacking only ever showed up in a handful
# of disciplines, concentrated in the final 1-2 weeks once several cargos'
# tracks were finishing at once — never in cargos with few turmas (PCF/PPF),
# only the ones with the most (EPF 9, DPF 5). Mirrored here with an explicit
# split: early/mid disciplines run "strict" (cap=1 only, long lookahead — never
# simultaneous), and only the disciplines that land late enough in the
# curriculum for the term's day budget to actually run tight switch to "packed"
# (short lookahead, stacking allowed) — same late, turma-count-driven crunch
# the original shows, not stacking sprinkled arbitrarily throughout.
STRICT_LOOKAHEAD = 40
PACKED_LOOKAHEAD = 10
# Chosen empirically so the switch to "packed" lands only in the course's last
# stretch (M3.4 on is where the running weekday-slot demand actually starts
# exceeding the plain, unstacked capacity of the remaining term — M3.4 also
# overlaps M3.3's slot-pair on shared days, same as the original's own
# DPF-M3.4). Everything before this stays strict — never simultaneous.
PACKED_CODES = {'M3.4', 'M2.5', 'M3.6', 'M2.6', 'M3.7', 'M2.7', 'M3.8', 'M3.9'}
# M2.4 stays out of PACKED_CODES on purpose: NO_SELF_STACK already blocks it
# from ever sharing a slot with *another* M2.4, so a high cap wouldn't help it
# stack with itself anyway — it only ever needs enough cap (2, from strict
# mode below) to piggyback on a slot a *different* discipline (e.g. M3.5) is
# already using.
# M3.5 is also NOT in PACKED_CODES: it isn't scheduled through the generic
# per-discipline path at all (skipped in the loop below) — it's placed
# explicitly right after M2.4, reusing M2.4's window, so the two land on the
# same days/slots (explicit user request to run them in parallel, same
# pattern as M3.3/M3.4 already sharing a week).
# DUAL_CODES: kept empty for now — M3.1 (Fonte Humana) used to be here (always
# 2 turmas of M3.1 together), but that was superseded by the explicit user
# request to pair M3.1 1:1 with M2.1 in the same slot instead (see the M2.1
# block below). If another discipline needs the old "always 2 of itself"
# behavior, add its code here.
DUAL_CODES = set()

def place_turma(turma, span, day_ok, pool_for_day, search_start, code, desc, lookahead, max_cap, min_cap=1):
    """Find room for `span` consecutive slots for this turma, on or after
    `search_start`. Within a bounded lookahead window, prefers an unstacked
    slot (cap=1) over stacking, and a nearer day over a farther one — unless
    `min_cap` > 1, which skips straight past the unstacked option (used for
    disciplines explicitly meant to always pair 2 turmas per slot). Only
    allows weekends when `day_ok` says so. Returns the ALL_DAYS index used."""
    window_end = min(search_start + lookahead, len(ALL_DAYS))
    for cap in range(min_cap, max_cap + 1):
        for idx in range(search_start, window_end):
            week, day_idx = ALL_DAYS[idx]
            if not day_ok(day_idx):
                continue
            for start in pool_for_day(day_idx):
                if day_has_room(week, day_idx, start, span, cap, code) and turma_free(turma, week, day_idx, start, span):
                    reserve(week, day_idx, start, span, code, desc, turma)
                    return idx
    # window exhausted even at max stacking — widen to the rest of the term
    for idx in range(search_start, len(ALL_DAYS)):
        week, day_idx = ALL_DAYS[idx]
        if not day_ok(day_idx):
            continue
        for start in pool_for_day(day_idx):
            if day_has_room(week, day_idx, start, span, max_cap, code) and turma_free(turma, week, day_idx, start, span):
                reserve(week, day_idx, start, span, code, desc, turma)
                return idx
    raise RuntimeError(f"Ran out of days placing {code} for {turma}")

WEEKDAY_ONLY = lambda d: d < 5
WEEKDAY_PLUS_SAT = lambda d: d < 6  # Mon-Sat; Sunday stays off-limits even as a fallback

free_disc = [d for d in DISCIPLINES if d[3] == 'free']
for code, desc, hours, kind in free_disc:
    if code == 'M3.5':
        continue  # placed together with M2.4 below, not on its own pass
    if code == 'M3.1':
        continue  # placed together with M2.1 below, not on its own pass
    if code == 'M3.2':
        continue  # placed together with M2.2 below, not on its own pass
    span = hours // 2
    start_pool = [1, 3] if span == 2 else [1, 2, 3, 4]
    min_cap = 1
    if code in PACKED_CODES:
        lookahead, max_cap = PACKED_LOOKAHEAD, STACK_CAP
    elif code in DUAL_CODES:
        # explicitly authorized by the user to always pair 2 turmas per slot —
        # min_cap=2 skips the unstacked option entirely (so it actually happens,
        # rather than only if cap=1 alone ever ran short), which also halves
        # M3.1's footprint, freeing days earlier in the term for what follows.
        lookahead, max_cap, min_cap = STRICT_LOOKAHEAD, 2, 2
    else:
        # cap=1 is tried across the whole window before cap=2 is ever considered,
        # so this stays non-simultaneous in practice; cap=2 is just a safety valve
        # for edge cases (e.g. M3.3 sharing a slot-pair with a nearby discipline)
        # rather than a real allowance to stack routinely.
        lookahead, max_cap = STRICT_LOOKAHEAD, 2

    disc_start = cursor  # fixed window start for this discipline; stacking revisits it, doesn't just chase the tail

    # --- M3.3 Aeroporto now runs BEFORE M2.2 is placed, starting fixed at
    # Semana 5 / Tue (explicit user request), instead of splicing in after
    # M2.2+M3.2 finish like it used to. Placing it first means it claims
    # Tue/Wed/Thu afternoons + weekends starting that week; M2.2's own
    # cap=1-first search (right below) then naturally routes around those
    # now-occupied afternoon slots — no extra bookkeeping needed to "free up"
    # days for it, M2.2 just spills whatever doesn't fit on to Friday and
    # into Semana 6 on its own, same as any other cap=1-exhausted day.
    # Week 5 is hardcoded here (not derived from disc_start) because the user
    # asked for this specific week, not "wherever M2.2 happens to land".
    if code == 'M2.2':
        aero_code, aero_desc = 'M3.3', 'Aeroporto'
        aero_day_ok = lambda d: d in (1, 2, 3, 5, 6)  # Tue/Wed/Thu or Sat/Sun
        aero_pool = lambda d: [1, 3] if d >= 5 else [3]  # weekend: morning+afternoon; weekday: afternoon only
        aero_start = ALL_DAYS.index((5, 1))  # Semana 5, Tue
        aero_highest = aero_start
        for turma in TURMAS:
            used_idx = place_turma(turma, 2, aero_day_ok, aero_pool, aero_start, aero_code, aero_desc, STRICT_LOOKAHEAD, 1)
            aero_highest = max(aero_highest, used_idx)
        # `cursor`/`disc_start` deliberately untouched by aero_highest — M3.3
        # only ever claims slots 3-4 on Tue/Wed/Thu (or both periods on
        # weekends), so M2.2 (right below) and M3.4+ after it can keep filling
        # Mon/Fri and slots 1-2 concurrently in the same day range.

    highest = disc_start
    lowest_used = None
    for turma in TURMAS:
        try:
            used_idx = place_turma(turma, span, WEEKDAY_ONLY, lambda d: start_pool, disc_start, code, desc, lookahead, max_cap, min_cap)
        except RuntimeError:
            # rule says no weekends, but if a discipline's queue genuinely can't
            # fit Mon-Fri, spill onto that same week's Saturday with the same
            # code/turma sequence — keeps it grouped with the rest of that
            # discipline's run instead of scattering it elsewhere. Sunday stays off-limits.
            used_idx = place_turma(turma, span, WEEKDAY_PLUS_SAT, lambda d: start_pool, disc_start, code, desc, lookahead, max(max_cap, STACK_CAP), min_cap)
        highest = max(highest, used_idx)
        lowest_used = used_idx if lowest_used is None else min(lowest_used, used_idx)
    cursor = highest  # next discipline starts at/after the latest day this one actually used

    # --- M3.5 Planejamento de Operação runs in parallel with M2.4 (explicit
    # user request), starting the search at the first day M2.4 itself actually
    # landed on (lowest_used), not the pre-M2.4 disc_start — disc_start can
    # still have leftover free capacity from before M2.4 kicks in, which would
    # let M3.5 grab it at cap=1 and end up on a day with no Damaz at all.
    # Starting exactly where M2.4 starts means every slot in the lookahead
    # window is already occupied by M2.4 at cap=1, so M3.5's own cap=1 pass
    # fails everywhere and it falls through to cap=2 — landing squarely in the
    # same (week,day,slot) cell as a Damaz turma. Same mechanism that lets
    # M3.3 and M3.4 already share a week, just via stacking instead of
    # disjoint days.
    # --- M3.1 Fonte Humana runs in parallel with M2.1 (explicit user request:
    # pair 1 turma of M3.1 with each M2.1 session in the same slot; the same
    # turma is never double-booked into both, since turma_free() already
    # guarantees a turma can't hold two entries in the same slot). Same
    # lowest_used-start mechanism as M3.5/M2.4 above — but here the lookahead
    # is sized exactly to M2.1's own window (highest-lowest_used+1), not the
    # generic PACKED_LOOKAHEAD=10: M2.1 only takes 5 business days, so a
    # 10-calendar-day window would reach past it into genuinely free days,
    # which cap=1 would grab before ever trying to stack onto M2.1 — same
    # failure mode fixed for M3.5/M2.4, just needed a tighter window here
    # because that pair's own window happens to be shorter than 10 days.
    if code == 'M2.1':
        m31_code, m31_desc, m31_span = 'M3.1', 'Fonte Humana', 1
        m31_pool = lambda d: [1, 2, 3, 4]
        m31_start = lowest_used
        m31_lookahead = highest - lowest_used + 1
        m31_highest = m31_start
        for turma in TURMAS:
            try:
                used_idx = place_turma(turma, m31_span, WEEKDAY_ONLY, m31_pool, m31_start, m31_code, m31_desc, m31_lookahead, STACK_CAP)
            except RuntimeError:
                used_idx = place_turma(turma, m31_span, WEEKDAY_PLUS_SAT, m31_pool, m31_start, m31_code, m31_desc, m31_lookahead, STACK_CAP)
            m31_highest = max(m31_highest, used_idx)
        cursor = max(cursor, m31_highest)

    if code == 'M2.4':
        m35_code, m35_desc, m35_span = 'M3.5', 'Planejamento de Operação', 1
        m35_pool = lambda d: [1, 2, 3, 4]
        m35_start = lowest_used
        m35_highest = m35_start
        for turma in TURMAS:
            try:
                used_idx = place_turma(turma, m35_span, WEEKDAY_ONLY, m35_pool, m35_start, m35_code, m35_desc, PACKED_LOOKAHEAD, STACK_CAP)
            except RuntimeError:
                used_idx = place_turma(turma, m35_span, WEEKDAY_PLUS_SAT, m35_pool, m35_start, m35_code, m35_desc, PACKED_LOOKAHEAD, STACK_CAP)
            m35_highest = max(m35_highest, used_idx)
        cursor = max(cursor, m35_highest)

    # --- M3.2 Planejamento de Vigilância runs in parallel with M2.2 (explicit
    # user request), same 1:1 pairing pattern as M3.1/M2.1 and M3.5/M2.4:
    # search starts at lowest_used (M2.2's own first day), with a lookahead
    # sized exactly to M2.2's own window, so M3.2's cap=1 pass can't escape
    # into free days beyond it and is forced to stack (cap=2) onto the same
    # (week,day,slot) cell a M2.2 turma already occupies.
    if code == 'M2.2':
        m32_code, m32_desc, m32_span = 'M3.2', 'Planejamento de Vigilância', 1
        m32_pool = lambda d: [1, 2, 3, 4]
        m32_start = lowest_used
        m32_lookahead = highest - lowest_used + 1
        m32_highest = m32_start
        for turma in TURMAS:
            try:
                used_idx = place_turma(turma, m32_span, WEEKDAY_ONLY, m32_pool, m32_start, m32_code, m32_desc, m32_lookahead, STACK_CAP)
            except RuntimeError:
                used_idx = place_turma(turma, m32_span, WEEKDAY_PLUS_SAT, m32_pool, m32_start, m32_code, m32_desc, m32_lookahead, STACK_CAP)
            m32_highest = max(m32_highest, used_idx)
        cursor = max(cursor, m32_highest)

print(f"Total entries placed: {len(entries)}")
weeks_used = sorted(set(e['week'] for e in entries))
print(f"Weeks used: {weeks_used}")
from collections import Counter
cell_counts = Counter((e['week'], e['day'], s) for e in entries for s in range(e['slot'], e['slot']+e['span']))
print(f"Max entries stacked in a single (week,day,slot) cell: {max(cell_counts.values())}")

# ---------- Build calendar HTML ----------
def titulo_semana(n):
    mon = week_monday(n)
    sun = mon + datetime.timedelta(days=6)
    last = " (Última Semana)" if n == END_WEEK else ""
    if mon.month == sun.month:
        return f"Semana {n} · {mon.day:02d}–{sun.day:02d} de {MONTH_FULL[mon.month]} de {mon.year}{last}"
    else:
        return f"Semana {n} · {mon.day:02d} {MONTH_ABBR[mon.month]}–{sun.day:02d} de {MONTH_FULL[sun.month]} de {sun.year}{last}"

def sem_info_short(n):
    mon = week_monday(n)
    sun = mon + datetime.timedelta(days=6)
    if mon.month == sun.month:
        return f"{mon.day:02d}–{sun.day:02d} {MONTH_ABBR[mon.month]}"
    else:
        return f"{mon.day:02d} {MONTH_ABBR[mon.month]}–{sun.day:02d} {MONTH_ABBR[sun.month]}"

occupies_slot = {}
for e in entries:
    for s in range(e['slot'], e['slot']+e['span']):
        occupies_slot.setdefault((e['week'], e['day'], s), []).append(e)

def entry_html(e, is_continuation):
    color_bg, color_border = MOD_COLORS[mod_of(e['code'])]
    cod_html = e['code'] + (' <span style="font-size:8px;opacity:.5">↓</span>' if is_continuation else '')
    return (f'<div class="cal-entry" style="background:{color_bg}; border-left: 3px solid {color_border};">'
            f'<span class="cal-cod">{cod_html}</span>'
            f'<span class="cal-turma">{e["turma"]}</span>'
            f'<span class="cal-desc">{e["desc"]}</span></div>')

def build_week_block(n):
    mon = week_monday(n)
    dates = [mon + datetime.timedelta(days=i) for i in range(7)]
    ths = ''.join(f'<th class="cal-th-dia">{DAY_ABBR[i]} {dates[i].day:02d}/{MONTH_ABBR[dates[i].month]}</th>' for i in range(7))
    rows = []
    for slot_idx in range(0, 7):
        label, start, end = SLOTS[slot_idx]
        row_class = ''
        if slot_idx == 0:
            row_class = ' class="cal-row-extra"'
        elif slot_idx in (5,6):
            row_class = ' class="cal-row-noite"'
        tds = []
        for day_idx in range(7):
            cell_entries = occupies_slot.get((n, day_idx, slot_idx), [])
            html_parts = []
            for e in cell_entries:
                is_cont = (slot_idx != e['slot'])
                html_parts.append(entry_html(e, is_cont))
            tds.append(f'<td class="cal-td" style="">{"".join(html_parts)}</td>')
        periodo_label = 'EXTRA' if slot_idx == 0 else SLOT_LABELS[slot_idx]
        rows.append(f'<tr{row_class}><td class="cal-td-periodo">{periodo_label}</td><td class="cal-td-hor">{start}–{end}</td>{"".join(tds)}</tr>')
    table = ('<table class="cal-table">'
             '<colgroup><col style="width:68px"><col style="width:90px"><col style="width:150px"><col style="width:150px"><col style="width:150px"><col style="width:150px"><col style="width:150px"><col style="width:150px"><col style="width:150px"></colgroup>'
             f'<thead><tr><th class="cal-th-periodo">Período</th><th class="cal-th-hor">Horário</th>{ths}</tr></thead>'
             f'<tbody>{"".join(rows)}</tbody></table>')
    return (f'<div class="cal-week" id="cal-sem-{n}">'
            f'<div class="cal-titulo">{titulo_semana(n)}</div>'
            f'<div style="overflow-x:auto">{table}</div></div>')

week_blocks = ''.join(build_week_block(n) for n in WEEKS)

def build_nav():
    parts = []
    for n in WEEKS:
        active = ' active' if n == START_WEEK else ''
        tem_aula = ' tem-aula' if n in weeks_used else ''
        parts.append(
            f'<span class="sem-tick-wrap"><span class="sem-tick" data-sem="{n}" title="Marcar/desmarcar semana {n}">'
            f'<svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
            f'<polyline points="2.5,8 6.5,12.5 13.5,4"></polyline></svg></span>'
            f'<button class="cal-nav-btn{active}{tem_aula}" onclick="mostrarSem({n},this)">Sem. {n}</button></span>'
        )
    return ''.join(parts)

nav_inner = build_nav()

# ---------- Load and patch index.html ----------
html = open(IN_HTML, encoding='utf-8').read()

# --- Replace cal-nav inner content (precise boundaries) ---
nav_start_tag = '<div class="cal-nav">'
nav_start = html.index(nav_start_tag)
cal_container_tag = '<div class="cal-panel" id="cal-container">'
cal_container_start = html.index(cal_container_tag, nav_start)
# nav block = [nav_start_tag] + inner + '</div>' immediately before cal_container_start
nav_content_start = nav_start + len(nav_start_tag)
# the closing </div> of cal-nav is the last thing before cal_container_start
nav_close = html.rindex('</div>', nav_content_start, cal_container_start)
html = html[:nav_content_start] + nav_inner + html[nav_close:]

# recompute cal_container_start (positions shifted)
cal_container_start = html.index(cal_container_tag)
container_content_start = cal_container_start + len(cal_container_tag)
first_week_pos = html.index('<div class="cal-week" id="cal-sem-3">', container_content_start)
last_week_marker = '<div class="cal-week" id="cal-sem-15">'
last_week_pos = html.index(last_week_marker, container_content_start)
m_end = re.search(r'</table>\s*</div>\s*</div>', html[last_week_pos:])
assert m_end
container_content_end = last_week_pos + m_end.end()

html = html[:first_week_pos] + week_blocks + html[container_content_end:]

# 1b. Replace hardcoded initial `let DADOS = [...]` literal with data matching new calendar
dados_start = html.index('let DADOS = [')
dados_end = html.index('\n];', dados_start) + 3

def dia_label(week, day_idx):
    mon = week_monday(week)
    date = mon + datetime.timedelta(days=day_idx)
    return f"{DAY_ABBR[day_idx]} {date.day:02d}/{MONTH_ABBR[date.month]}"

dados_rows = []
for e in entries:
    horarios = '+'.join([SLOTS[s][1]+'–'+SLOTS[s][2] for s in [e['slot']]]) if e['span']==1 else (SLOTS[e['slot']][1]+'–'+SLOTS[e['slot']+e['span']-1][2])
    if e['span'] == 1:
        horarios_str = f"{SLOTS[e['slot']][1]}–{SLOTS[e['slot']][2]}"
    else:
        horarios_str = f"{SLOTS[e['slot']][1]}–{SLOTS[e['slot']][2]} + {SLOTS[e['slot']+1][1]}–{SLOTS[e['slot']+1][2]}"
    horas = e['span'] * 2
    row = [str(e['week']), e['code'], e['turma'], dia_label(e['week'], e['day']), e['desc'], horarios_str, horas]
    dados_rows.append(row)

def js_str(v):
    if isinstance(v, int):
        return str(v)
    return "'" + str(v).replace("\\", "\\\\").replace("'", "\\'") + "'"

dados_js = 'let DADOS = [\n' + ',\n'.join('  [' + ','.join(js_str(v) for v in row) + ']' for row in dados_rows) + '\n]'
html = html[:dados_start] + dados_js + html[dados_end:]

# 2. Config constants
html = html.replace(
    "const CARGOS=['EPF','DPF','PPF','PCF'];",
    "const CARGOS=['APF'];"
)
html = html.replace(
    "const COLS={EPF:'#3a9475',DPF:'#5b8ec4',PPF:'#d4a843',PCF:'#c96b5a'};",
    "const COLS={APF:'#7a5ea8'};"
)
html = html.replace(
    "const BASE_TURMAS={EPF:9,DPF:5,PPF:2,PCF:3};",
    "const BASE_TURMAS={APF:19};"
)
html = re.sub(r"const DCIBER_PARES=\{.*?\};", "const DCIBER_PARES={APF:['M2.5','M2.6','M2.7']};", html, count=1)

# 3. SEM_INFO / SEMS
sem_info_obj = ", ".join(f'"{n}":"{sem_info_short(n)}"' for n in WEEKS)
html = re.sub(r'const SEM_INFO=\{.*?\};', f'const SEM_INFO={{{sem_info_obj}}};', html)
sems_arr = ", ".join(f"'{n}'" for n in WEEKS)
html = re.sub(r"const SEMS=\[.*?\];", f"const SEMS=[{sems_arr}];", html)

# 4. getCargo / classCargo
html = re.sub(
    r"function getCargo\(t\)\{.*?\n\}",
    "function getCargo(t){\n  if(t.indexOf('APF')>=0) return 'APF';\n  return 'outro';\n}",
    html, count=1, flags=re.S
)
html = html.replace(
    "function classCargo(c){return {EPF:'epf',DPF:'dpf',PPF:'ppf',PCF:'pcf'}[c]||'epf';}",
    "function classCargo(c){return {APF:'apf'}[c]||'apf';}"
)

# 5. CSS additions
html = html.replace(
    ".bdg.epf{background:#e8f5f0;color:#1a6e56}.bdg.dpf{background:#e8eef7;color:#1a3d7a}",
    ".bdg.apf{background:#f0ebf7;color:#5a3f80}"
)
html = html.replace(
    ".bdg.ppf{background:#fdf3e3;color:#8a5a10}.bdg.pcf{background:#fdf0ec;color:#8a3020}",
    ""
)
html = html.replace(
    ".gdot.epf{background:#3a9475}.gdot.dpf{background:#5b8ec4}.gdot.ppf{background:#d4a843}.gdot.pcf{background:#c96b5a}",
    ".gdot.apf{background:#7a5ea8}"
)
html = html.replace(
    ".tag.epf{background:#e8f5f0;color:#1a6e56;border-color:#a8dcca}",
    ".tag.apf{background:#f0ebf7;color:#5a3f80;border-color:#c9b3e0}"
)
html = html.replace(".tag.dpf{background:#e8eef7;color:#1a3d7a;border-color:#a8bede}", "")
html = html.replace(".tag.ppf{background:#fdf3e3;color:#8a5a10;border-color:#e8c878}", "")
html = html.replace(".tag.pcf{background:#fdf0ec;color:#8a3020;border-color:#e8b0a0}", "")

# 6. Filtros bar cargo tags
old_tags = ('<span class="tag all" onclick="filtrarCargo(\'all\',this)">Todos</span>\n'
            '<span class="tag epf" onclick="filtrarCargo(\'EPF\',this)">EPF</span>\n'
            '<span class="tag dpf" onclick="filtrarCargo(\'DPF\',this)">DPF</span>\n'
            '<span class="tag ppf" onclick="filtrarCargo(\'PPF\',this)">PPF</span>\n'
            '<span class="tag pcf active" onclick="filtrarCargo(\'PCF\',this)">PCF</span>\n'
            '<span class="tag dciber" onclick="filtrarDCIBER(this)">DCIBER</span>')
new_tags = ('<span class="tag all active" onclick="filtrarCargo(\'all\',this)">Todos</span>\n'
            '<span class="tag apf" onclick="filtrarCargo(\'APF\',this)">APF</span>\n'
            '<span class="tag dciber" onclick="filtrarDCIBER(this)">DCIBER</span>')
assert old_tags in html, "old tags block not found"
html = html.replace(old_tags, new_tags)

# 7. sel-aula options
codes_ordered = [d[0] for d in DISCIPLINES]
old_sel_aula = re.search(r'<select id="sel-aula"[^>]*>.*?</select>', html, re.S).group(0)
new_options = '<option value="all">Todas</option>' + ''.join(f'<option value="{c}">{c}</option>' for c in codes_ordered)
new_sel_aula = re.sub(r'(<select id="sel-aula"[^>]*>).*?(</select>)', lambda m2: m2.group(1)+new_options+m2.group(2), old_sel_aula, flags=re.S)
html = html.replace(old_sel_aula, new_sel_aula)

# 8. sel-sem options
old_sel_sem = re.search(r'<select id="sel-sem"[^>]*>.*?</select>', html, re.S).group(0)
sem_opts = '<option value="all">Todas</option>' + ''.join(f'<option value="{n}">Sem. {n}</option>' for n in WEEKS)
new_sel_sem = re.sub(r'(<select id="sel-sem"[^>]*>).*?(</select>)', lambda m2: m2.group(1)+sem_opts+m2.group(2), old_sel_sem, flags=re.S)
html = html.replace(old_sel_sem, new_sel_sem)

# 9. sel-turma options
old_sel_turma = re.search(r'<select id="sel-turma"[^>]*>.*?</select>', html, re.S).group(0)
turma_opts = '<option value="all">Todas</option>' + ''.join(f'<option value="{t}">{t}</option>' for t in TURMAS)
new_sel_turma = re.sub(r'(<select id="sel-turma"[^>]*>).*?(</select>)', lambda m2: m2.group(1)+turma_opts+m2.group(2), old_sel_turma, flags=re.S)
html = html.replace(old_sel_turma, new_sel_turma)

# 10. Titles / filenames / storage keys
html = html.replace("GRADE APC CFP2/2026", "GRADE APC CFP3/2026")
html = html.replace("Gantt_APC_CFP2_2026.xlsx", "Gantt_APC_CFP3_2026.xlsx")
html = html.replace("GRADE_APC_CFP2_2026_atualizada_", "GRADE_APC_CFP3_2026_atualizada_")
html = html.replace("grade_apc_cfp2_2026_calendar_dragdrop_print_v3", "grade_apc_cfp3_2026_calendar_dragdrop_print_v3")
html = html.replace("'semanas_marcadas'", "'semanas_marcadas_cfp3'")

# 9b. Chart/export fallback cargo references
html = html.replace("CARGOS.find(c=>cols.some(col=>col.segs.some(s=>s.cargo===c))) || 'EPF';",
                     "CARGOS.find(c=>cols.some(col=>col.segs.some(s=>s.cargo===c))) || 'APF';")
html = html.replace("sc[s]={EPF:0,DPF:0,PPF:0,PCF:0};", "sc[s]={APF:0};")
html = html.replace("""const CARGO_FILL={
    EPF:{argb:'FF1A6E56'},  // verde escuro
    DPF:{argb:'FF1A3D7A'},  // azul escuro
    PPF:{argb:'FF8A5A10'},  // âmbar escuro
    PCF:{argb:'FF8A3020'},  // vermelho escuro
  };
  const CARGO_BG={
    EPF:{argb:'FFE8F5F0'},
    DPF:{argb:'FFE8EEF7'},
    PPF:{argb:'FFFDF3E3'},
    PCF:{argb:'FFFDF0EC'},
  };""", """const CARGO_FILL={
    APF:{argb:'FF5A3F80'},  // roxo escuro
  };
  const CARGO_BG={
    APF:{argb:'FFF0EBF7'},
  };""")
html = html.replace("""const CARGO_STYLE = {
      EPF: { bg:'C8DFF5', font:'1C4A7A' },
      DPF: { bg:'D5EDD5', font:'1A5C1A' },
      PPF: { bg:'FAE8B0', font:'7A5200' },
      PCF: { bg:'F5C9C3', font:'7A1C1C' },
    };""", """const CARGO_STYLE = {
      APF: { bg:'E5D9F2', font:'5A3F80' },
    };""")

# 10b. hardcoded turma lists (appears in filtrarDCIBER AND filtrarCargo)
turma_list_js = ",".join(f"'{t}'" for t in TURMAS)
html = re.sub(
    r"const _allT=\[.*?\];",
    f"const _allT=[{turma_list_js}];",
    html, flags=re.S
)

# 11. semana-ref placeholder
html = re.sub(r'(<span id="semana-ref"[^>]*>).*?(</span>)', r'\1-\2', html)

# 12. "Referência" modal table rows: left column is the static original-grade
# EPF reference (extracted by hand once from the old 4-cargo course, see
# CLAUDE.md); right column is this course's actual current schedule,
# recomputed fresh from `entries` on every regeneration so it never drifts
# out of sync with whatever the scheduling rules above produce.
REF_EPF_ORIGINAL = {
    3: 'M1.1(8)',
    4: 'M2.1(9), M3.1(9)',
    5: 'M3.2(9), M2.2(9), M1.1(2)',
    6: 'M2.3(5), M1.1(8)',
    7: 'M2.3(4), M3.3(4)',
    8: 'M3.3(14)',
    9: 'M2.4(16), M1.2(6)',
    10: 'M3.4(18), M2.4(2), M2.5(4), M2.6(4), M2.7(4)',
    11: 'M2.5(5), M2.6(5), M2.7(5), M1.2(6)',
    12: 'M3.5(9)',
    13: 'M3.6(9), M3.7(8), M1.2(6)',
    14: 'M3.7(10), M3.8(9), M3.9(9)',
    15: 'M3.10(9)',
}
_code_order = [d[0] for d in DISCIPLINES]
def _code_sort_key(c):
    return _code_order.index(c) if c in _code_order else len(_code_order)

_week_code_counts = {}
for e in entries:
    _week_code_counts.setdefault(e['week'], {}).setdefault(e['code'], 0)
    _week_code_counts[e['week']][e['code']] += 1

def _week_summary_atual(w):
    counts = _week_code_counts.get(w)
    if not counts:
        return '—'
    codes = sorted(counts.keys(), key=_code_sort_key)
    return ', '.join(f"{c}({counts[c]})" for c in codes)

ref_rows_html = ''.join(
    f'<tr><td>{n}</td><td>{REF_EPF_ORIGINAL.get(n, "—")}</td><td>{_week_summary_atual(n)}</td></tr>'
    for n in WEEKS
)
ref_rows_start = html.index('<tbody id="ref-tbody">') + len('<tbody id="ref-tbody">')
ref_rows_end = html.index('</tbody>', ref_rows_start)
html = html[:ref_rows_start] + ref_rows_html + html[ref_rows_end:]

open(OUT_HTML, 'w', encoding='utf-8').write(html)
print("index.html patched and written.")

# ---------- Build calendario.csv ----------
csv_rows = []
for e in entries:
    week = e['week']
    mon = week_monday(week)
    date = mon + datetime.timedelta(days=e['day'])
    label, start, end = SLOTS[e['slot']]
    end_label = SLOTS[e['slot'] + e['span'] - 1][2]
    cargo = 'APF'
    turma_letter = e['turma'].split('-')[1]
    codigo = e['code']
    codigo_padded = re.sub(r'\.(\d)(?!\d)', r'.0\1', codigo)
    data_str = date.strftime('%d/%m/%Y')
    csv_rows.append((cargo, codigo_padded, turma_letter, data_str, start, end_label))

def sort_key(r):
    d = r[3].split('/')
    iso = f"{d[2]}-{d[1]}-{d[0]}"
    return (iso, r[4])
csv_rows.sort(key=sort_key)

lines = ['"cargo";"codigo";"turma";"data";"horaInicio";"horaFim"']
for r in csv_rows:
    lines.append(';'.join('"' + str(v).replace('"','""') + '"' for v in r))
csv_content = '﻿' + '\r\n'.join(lines)
open(OUT_CSV, 'w', encoding='utf-8', newline='').write(csv_content)
print(f"calendario.csv written: {len(csv_rows)} rows")
