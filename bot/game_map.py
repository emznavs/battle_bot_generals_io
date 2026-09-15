"""Friendly view over a decoded game_update payload."""
from .client import TILE_EMPTY, TILE_FOG, TILE_FOG_OBSTACLE, TILE_MOUNTAIN

DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # up, down, left, right


class GameMap:
    def __init__(self, player_index):
        self.player_index = player_index
        self.rows = 0
        self.cols = 0
        self.armies = []
        self.terrain = []
        self.cities = set()
        self.generals = []  # tile index per player, -1 if unknown
        self.turn = 0
        self.scores = []

    def update(self, data):
        self.rows = data["rows"]
        self.cols = data["cols"]
        self.armies = data["armies"]
        self.terrain = data["terrain"]
        self.cities = set(data["cities"])
        self.generals = data.get("generals", self.generals)
        self.turn = data.get("turn", self.turn)
        self.scores = data.get("scores", self.scores)

    # -- coordinate helpers ------------------------------------------------
    def index(self, y, x):
        return y * self.cols + x

    def yx(self, index):
        return divmod(index, self.cols)

    def in_bounds(self, y, x):
        return 0 <= y < self.rows and 0 <= x < self.cols

    def neighbors(self, index):
        y, x = self.yx(index)
        for dy, dx in DIRECTIONS:
            ny, nx = y + dy, x + dx
            if self.in_bounds(ny, nx):
                ni = self.index(ny, nx)
                if self.terrain[ni] != TILE_MOUNTAIN:
                    yield ni

    # -- state queries -------------------------------------------------
    def is_mine(self, index):
        return self.terrain[index] == self.player_index

    def is_enemy(self, index):
        t = self.terrain[index]
        return t >= 0 and t != self.player_index

    def is_unclaimed(self, index):
        return self.terrain[index] in (TILE_EMPTY, TILE_FOG)

    def is_visible_unknown(self, index):
        return self.terrain[index] in (TILE_FOG, TILE_FOG_OBSTACLE)

    def is_city(self, index):
        return index in self.cities

    def my_general(self):
        idx = self.generals[self.player_index]
        return idx if idx != -1 else None

    def owned_tiles(self):
        return [i for i, t in enumerate(self.terrain) if t == self.player_index]
