import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))  # can't figure out the module system rn

from redata.constants import *
from rng import Rng
from data import GameData, get_cached


game_id = "2221c202-9d98-40a4-af3b-57a83aa0d8ec"
team = JAZZ_HANDS
type = "rotation"

gd = GameData()
updates = gd.get_raw_game_updates(game_id)

before = [u for u in updates if u["data"]["gameStart"]][0]
after = [u for u in updates if u["data"]["finalized"]][0]
print(before["timestamp"], after["timestamp"])

gd.fetch_teams(before["timestamp"])
team_before = gd.teams[team]
gd.fetch_teams(after["timestamp"], delta_secs=60*20)
team_after = gd.teams[team]

if type == "completely":
    bef = team_before.lineup + team_before.rotation
    aft = team_after.lineup + team_after.rotation

    assert len(set(bef)) == len(set(aft))
    print([aft.index(bef[i]) for i in range(len(bef))])
elif type == "rotation":
    bef = team_before.rotation
    aft = team_after.rotation

    assert len(set(bef)) == len(set(aft))
    print([aft.index(bef[i]) for i in range(len(bef))])
elif type == "lineup":
    bef = team_before.lineup
    aft = team_after.lineup

    assert len(set(bef)) == len(set(aft))
    print([aft.index(bef[i]) for i in range(len(bef))])
