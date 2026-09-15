"""Decision logic, kept separate from the transport so it's easy to rip out
and replace during the hackathon (rule-based / ML / LLM-driven all plug in
here as a function: GameMap -> (start, end, is_half) or None).

This baseline is deliberately conservative, per the event's own advice:
"A reliable bot with one good trick could beat an ambitious one that
forgets to defend its general." It:
  1. never attacks *from* the general tile (keeps it defended by default)
  2. prefers expanding into unclaimed/fog tiles over fighting
  3. only attacks an enemy/neutral tile it can actually beat
  4. picks its biggest army each turn so moves are decisive, not wasted
"""


def choose_move(gmap):
    general = gmap.my_general()
    best = None  # (priority, start, end)

    for start in gmap.owned_tiles():
        army = gmap.armies[start]
        if army <= 1:
            continue
        if start == general:
            continue  # keep the general's army home

        for end in gmap.neighbors(start):
            if gmap.is_mine(end):
                continue  # reinforcing own tiles is handled implicitly by growth

            if gmap.is_unclaimed(end):
                priority = 2  # explore / claim empty land and fog
            elif (gmap.is_enemy(end) or gmap.terrain[end] == -1) and army - 1 > gmap.armies[end]:
                priority = 3 if not gmap.is_city(end) else 1  # cheap kills first, cities cost more
            else:
                continue  # can't win this fight, skip

            candidate = (priority, army, start, end)
            if best is None or candidate > best:
                best = candidate

    if best is None:
        return None
    _, _, start, end = best
    return start, end, False
