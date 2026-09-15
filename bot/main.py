"""Entry point.

Testing loop (do this before the tournament starts):
  1. Open generals.io in your browser, start a Custom Game.
  2. Copy the game code from the lobby URL: generals.io/games/<CODE>
  3. Run:  python -m bot.main --game-id <CODE> --username MyBot
  4. Force-start in the browser tab too; watch your bot play against you.

At the tournament, organizers will give you the lobby code to join.
"""
import argparse
import os

from .client import GeneralsClient
from .game_map import GameMap
from .strategy import choose_move

BOT_ID_FILE = "bot_id.txt"


def get_or_create_user_id():
    if os.path.exists(BOT_ID_FILE):
        return open(BOT_ID_FILE).read().strip()
    from .client import gen_user_id
    user_id = gen_user_id()
    with open(BOT_ID_FILE, "w") as f:
        f.write(user_id)
    return user_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-id", required=True, help="custom lobby code from the generals.io URL")
    parser.add_argument("--username", default=None, help="only registers the name on first-ever run for this bot id")
    args = parser.parse_args()

    user_id = get_or_create_user_id()
    client = GeneralsClient(user_id=user_id, username=args.username)
    client.connect()
    client.join_private(args.game_id)

    gmap = None
    for event, data in client.updates():
        if event == "game_start":
            gmap = GameMap(data["playerIndex"])
            print(f"Game started. You are player {data['playerIndex']}. "
                  f"Replay: https://generals.io/replays/{data['replay_id']}")
        elif event == "game_update":
            gmap.update(data)
            move = choose_move(gmap)
            if move:
                start, end, is_half = move
                client.attack(start, end, is_half)
        elif event == "game_won":
            print("Victory!")
            break
        elif event == "game_lost":
            print("Defeated.")
            break


if __name__ == "__main__":
    main()
