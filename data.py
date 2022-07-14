from dataclasses import dataclass
import os, json, requests
from typing import Any, Dict

cache = {}
def get_cached(key, url):
    key = key.replace(":", "_")
    if key in cache:
        return cache[key]

    path = os.path.join("cache", key + ".json")
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = requests.get(url).json()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
    cache[key] = data
    return data

def get_mods(entity):
    return entity.get("permAttr", []) + entity.get("seasAttr", []) + entity.get("weekAttr", []) + entity.get("gameAttr", []) + entity.get("itemAttr", [])

def get_feed_between(start, end):
    key = "feed_range_{}_{}".format(start, end)
    resp = get_cached(key, "https://api.sibr.dev/eventually/v2/events?after={}&before={}&sortorder=asc&limit=100000".format(start, end))
    return resp

weather_names = {
    1: "sun 2",
    7: "eclipse",
    8: "glitter",
    9: "blooddrain",
    10: "peanuts",
    11: "birds",
    12: "feedback",
    13: "reverb",
    14: "black hole",
    15: "coffee",
    16: "coffee 2",
    17: "coffee 3s",
    18: "flooding",
    19: "salmon",
    20: "polarity +",
    21: "polarity -",
    23: "sun 90",
    24: "sun .1",
    25: "sum sun"
}

@dataclass
class TeamData:
    data: Dict[str, Any]

    @property
    def id(self):
        return self.data["id"]

    @property
    def mods(self):
        return get_mods(self.data)

    def has_mod(self, mod) -> bool:
        return mod in self.mods

@dataclass
class StadiumData:
    data: Dict[str, Any]

    @property
    def id(self):
        return self.data["id"]

    @property
    def mods(self):
        return self.data["mods"]

    def has_mod(self, mod) -> bool:
        return mod in self.mods

@dataclass
class PlayerData:
    data: Dict[str, Any]

    @property
    def id(self):
        return self.data["id"]

    @property
    def mods(self):
        return get_mods(self.data)

    @property
    def name(self):
        unscattered_name = self.data.get("state", {}).get("unscatteredName")
        return unscattered_name or self.data["name"]

    @property
    def raw_name(self):
        return self.data["name"]

    def has_mod(self, mod) -> bool:
        return mod in self.mods

    def has_any(self, *mods) -> bool:
        for mod in mods:
            if mod in self.mods:
                return True
        return False

class GameData:
    def __init__(self):
        self.teams = {}
        self.players = {}
        self.stadiums = {}
        self.plays = {}
        self.games = {}
        self.sim = None

    def fetch_sim(self, timestamp):
        key = "sim_at_{}".format(timestamp)
        resp = get_cached(key, "https://api.sibr.dev/chronicler/v2/entities?type=sim&at={}".format(timestamp))
        self.sim = resp["items"][0]["data"]

    def fetch_teams(self, timestamp):
        key = "teams_at_{}".format(timestamp)
        resp = get_cached(key, "https://api.sibr.dev/chronicler/v2/entities?type=team&at={}&count=1000".format(timestamp))
        self.teams = {e["entityId"]: e["data"] for e in resp["items"]}

    def fetch_players(self, timestamp):
        key = "players_at_{}".format(timestamp)
        resp = get_cached(key, "https://api.sibr.dev/chronicler/v2/entities?type=player&at={}&count=2000".format(timestamp))
        self.players = {e["entityId"]: e["data"] for e in resp["items"]}

    def fetch_stadiums(self, timestamp):
        key = "stadiums_at_{}".format(timestamp)
        resp = get_cached(key, "https://api.sibr.dev/chronicler/v2/entities?type=stadium&at={}&count=1000".format(timestamp))
        self.stadiums = {e["entityId"]: e["data"] for e in resp["items"]}

    def fetch_game(self, game_id):
        key = "game_updates_{}".format(game_id)
        resp = get_cached(key, "https://api.sibr.dev/chronicler/v1/games/updates?count=2000&game={}&started=true".format(game_id))
        self.games[game_id] = resp["data"]
        for update in resp["data"]:
            play = update["data"]["playCount"]
            self.plays[(game_id, play)] = update["data"]

    def fetch_league_data(self, timestamp):
        self.fetch_sim(timestamp)
        self.fetch_teams(timestamp)
        self.fetch_players(timestamp)
        self.fetch_stadiums(timestamp)

    def get_update(self, game_id, play):
        if game_id not in self.games:
            self.fetch_game(game_id)
        return self.plays.get((game_id, play))

    def get_player(self, player_id) -> PlayerData:
        return PlayerData(self.players[player_id])

    def get_team(self, team_id) -> TeamData:
        return TeamData(self.teams[team_id])

    def get_stadium(self, stadium_id) -> StadiumData:
        return StadiumData(self.stadiums[stadium_id])