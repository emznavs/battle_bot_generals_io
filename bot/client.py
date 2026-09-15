"""Minimal generals.io bot transport: hand-rolled Socket.IO v2 framing over
a raw websocket. No socketio client library, so no version-compat surprises.

Protocol (reverse engineered from known-working community bot clients):
  - connect to wss://botws.generals.io/socket.io/?EIO=3&transport=websocket
  - recv "0{...}"      -> engine.io open packet
  - send "40"          -> connect default namespace
  - recv "40{...}"     -> namespace ack, now ready to emit/receive events
  - send "2" every ~10s -> heartbeat
  - emit:  "42" + json.dumps(["event_name", arg1, arg2, ...])
  - recv:  "42" + json array -> dispatch by event name
"""
import json
import random
import string
import threading
import time

import websocket

WS_URL = "wss://botws.generals.io/socket.io/?EIO=3&transport=websocket"

TILE_EMPTY = -1
TILE_MOUNTAIN = -2
TILE_FOG = -3
TILE_FOG_OBSTACLE = -4


def gen_user_id():
    return "".join(random.choices(string.ascii_letters + string.digits, k=16))


def _patch(old, diff):
    """Apply generals.io's run-length diff format to reconstruct an array.

    diff alternates: [matching_len, mismatch_len, *new_values, matching_len, ...]
    """
    out = []
    i = 0
    while i < len(diff):
        if diff[i] > 0:
            out.extend(old[len(out): len(out) + diff[i]])
        i += 1
        if i < len(diff) and diff[i] > 0:
            out.extend(diff[i + 1: i + 1 + diff[i]])
            i += diff[i]
        i += 1
    return out


class GeneralsClient:
    def __init__(self, user_id=None, username=None):
        self.user_id = user_id or gen_user_id()
        self.username = username
        self.ws = None
        self._move_id = 0
        self._lock = threading.RLock()
        self._connected = threading.Event()
        self._raw_map = []
        self._raw_cities = []
        self.player_index = None
        self.usernames = []
        self.replay_id = None

    # -- connection -------------------------------------------------
    def connect(self, timeout=10):
        self.ws = websocket.create_connection(
            WS_URL,
            timeout=timeout,
            header=["Origin: https://generals.io"],
        )
        self.ws.recv()  # "0{...}" open packet
        self.ws.send("40")
        self.ws.recv()  # "40{...}" namespace ack
        self._connected.set()
        threading.Thread(target=self._heartbeat, daemon=True).start()
        if self.username:
            self._emit("set_username", self.user_id, self.username)

    def _heartbeat(self):
        while self._connected.is_set():
            time.sleep(10)
            with self._lock:
                try:
                    self.ws.send("2")
                except Exception:
                    return

    def _emit(self, event, *args):
        with self._lock:
            self.ws.send("42" + json.dumps([event, *args], separators=(",", ":")))

    # -- joining games ------------------------------------------------
    def join_private(self, game_id, force_start=True):
        self._emit("join_private", game_id, self.user_id)
        if force_start:
            self._emit("set_force_start", game_id, True)

    def join_1v1(self):
        self._emit("join_1v1", self.user_id)

    def force_start(self, game_id, value=True):
        self._emit("set_force_start", game_id, value)

    # -- moves ----------------------------------------------------------
    def attack(self, start_index, end_index, is_half=False):
        self._emit("attack", start_index, end_index, is_half, self._move_id)
        self._move_id += 1

    # -- receiving updates ----------------------------------------------
    def updates(self):
        """Generator yielding (event_name, data) tuples. `data` for
        'game_update' is a dict with decoded 'armies', 'terrain', 'cities',
        'rows', 'cols' merged in (see game_map.GameMap for a friendlier
        wrapper)."""
        while True:
            msg = self.ws.recv()
            if not msg:
                continue
            if msg[0] == "2":  # server ping -> pong
                self.ws.send("3")
                continue
            if not msg.startswith("42"):
                continue
            event, *args = json.loads(msg[2:])
            if event == "game_start":
                data = args[0]
                self.player_index = data.get("playerIndex")
                self.usernames = data.get("usernames", [])
                self.replay_id = data.get("replay_id")
                self._raw_map = []
                self._raw_cities = []
                yield event, data
            elif event == "game_update":
                data = args[0]
                self._raw_map = _patch(self._raw_map, data["map_diff"])
                self._raw_cities = _patch(self._raw_cities, data.get("cities_diff", []))
                cols, rows = self._raw_map[0], self._raw_map[1]
                size = rows * cols
                armies = self._raw_map[2:2 + size]
                terrain = self._raw_map[2 + size:2 + 2 * size]
                decoded = dict(data)
                decoded.update(
                    rows=rows,
                    cols=cols,
                    armies=armies,
                    terrain=terrain,
                    cities=self._raw_cities,
                )
                yield event, decoded
            elif event in ("game_won", "game_lost", "game_over"):
                yield event, (args[0] if args else None)
                if event != "game_over":
                    return
            else:
                yield event, (args[0] if args else None)
