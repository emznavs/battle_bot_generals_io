# battle_bot_generals_io

A minimal, working generals.io bot for the AI Tinkerers London "AI Battle Bot
Tournament" (15 Sep 2026). Connects to the real generals.io servers over its
native Socket.IO protocol — no dependency on any third-party competition
platform.

## Layout

```
bot/
  client.py    transport: websocket framing, diff decoding, connect/join/attack
  game_map.py  friendly view over decoded state (rows, cols, armies, terrain,
               cities, generals, owned_tiles(), neighbors())
  strategy.py  choose_move(GameMap) -> (start, end, is_half) | None
               <- this is the file to gut and rebuild during the hackathon
  main.py      glue: connect, join lobby, feed updates to strategy, send moves
```

## Quickstart

```
pip install -r requirements.txt

# 1. Open https://generals.io in a browser, click "Custom Game".
# 2. Copy the code from the lobby URL: generals.io/games/<CODE>
python -m bot.main --game-id <CODE> --username MyBot

# 3. Force-start in the browser tab too. Watch it play against you.
```

At the event, organizers give you the lobby code to join instead.

`--username` only takes effect the **first time** this bot's persistent id
(cached in `bot_id.txt`, gitignored) registers a name — generals.io
usernames are permanent per id. Omit it to play anonymously while testing.

## How the game works

- Fog of war: you see only tiles you own plus their 8 neighbors.
- Your general produces +1 army/turn. Owned cities produce +1/turn.
  Ordinary land produces +1 army every 25 turns — territory alone is a slow
  economy, cities and compact expansion matter more.
- Attacking a tile with more army than it defends with captures it, and you
  keep the leftover army. Attacking with less/equal just burns your force.
- Capturing the enemy general instantly gives you their whole
  army/territory and wins the game — that's the actual objective, everything
  else is leverage toward it.

## Current baseline strategy (`bot/strategy.py`)

Deliberately conservative: never attacks from the general's own tile (keeps
it defended by default), prefers claiming empty/fog tiles over fighting,
only attacks something it can actually beat, and always moves its
biggest available army so moves are decisive. It will reliably finish a
game without giving away the general — build on top of that rather than
from scratch.

## Ideas to layer on, in order of effort

1. **Don't overextend the general's neighborhood.** Keep a reserve near
   home; today's bot has none.
2. **Target city capture once safely ahead on army**, not opportunistically —
   cities cost ~40-50 army upfront but pay off in a long match.
3. **General-hunt heuristics**: watch `scores` for a player whose tile count
   is shrinking fast (usually means they're losing to someone else, or dead
   already) and probe fog aggressively near where their army last was seen.
4. **Swap `choose_move` for a search** (minimax/greedy lookahead over a few
   plies) once the simple version is solid — don't do this first, a search
   over a broken heuristic is wasted effort.
5. **LLM-driven**: feed `GameMap` state as compact text/JSON to a model each
   turn, have it emit a move — interesting for the "LLM-driven" track, but
   validate it will not exceed the tournament's per-move time budget before
   relying on it live.
