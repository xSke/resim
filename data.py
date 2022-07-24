from dataclasses import dataclass
import os
import json
import requests
import math
from typing import Any, Dict
from datetime import datetime, timedelta
from enum import IntEnum, unique


def parse_timestamp(timestamp):
    timestamp = timestamp.replace("Z", "+00:00")
    return datetime.fromisoformat(timestamp)


def format_timestamp(dt: datetime):
    return dt.isoformat()


def offset_timestamp(timestamp: str, delta_secs: float) -> str:
    dt = parse_timestamp(timestamp)
    dt = dt + timedelta(seconds=delta_secs)
    timestamp = format_timestamp(dt)
    return timestamp.replace("+00:00", "Z")


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
            try:
                data = json.load(f)
                cache[key] = data
                return data
            except json.JSONDecodeError:
                pass

    data = requests.get(url).json()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    cache[key] = data
    return data


def get_mods(entity):
    return (
        entity.get("permAttr", [])
        + entity.get("seasAttr", [])
        + entity.get("weekAttr", [])
        + entity.get("gameAttr", [])
        + entity.get("itemAttr", [])
    )


def get_feed_between(start, end):
    key = "feed_range_{}_{}".format(start, end)
    resp = get_cached(
        key,
        "https://api.sibr.dev/eventually/v2/events?after={}&before={}&sortorder=asc&limit=100000".format(start, end),
    )
    return resp


@unique
class EventType(IntEnum):
    # Can't use -1 because the Feed uses it for
    # "Undefined type; used in the Library for Leaders
    # and Postseason series matchups (plus currently-redacted messages)"
    NOT_YET_HANDLED_IN_ENUM = -99999
    # Pulled from https://www.blaseball.wiki/w/SIBR:Feed#Event_types
    # and https://github.com/beiju/blarser/blob/main/blarser/src/api/eventually_schema.rs#L143
    LETS_GO = 0
    PLAY_BALL = 1
    HALF_INNING = 2
    PITCHER_CHANGE = 3
    STOLEN_BASE = 4
    WALK = 5
    STRIKEOUT = 6
    FLY_OUT = 7
    GROUND_OUT = 8
    HOME_RUN = 9
    HIT = 10
    GAME_END = 11
    BATTER_UP = 12
    STRIKE = 13
    BALL = 14
    FOUL_BALL = 15
    SHAMING_RUN = 20
    HOME_FIELD_ADVANTAGE = 21
    HIT_BY_PITCH = 22
    BATTER_SKIPPED = 23
    PARTY = 24
    STRIKE_ZAPPED = 25
    WEATHER_CHANGE = 26
    MILD_PITCH = 27
    INNING_END = 28
    BIG_DEAL = 29
    BLACK_HOLE = 30
    SUN2 = 31
    BIRDS_CIRCLE = 33
    FRIEND_OF_CROWS = 34
    BIRDS_UNSHELL = 35
    BECOME_TRIPLE_THREAT = 36
    GAIN_FREE_REFILL = 37
    COFFEE_BEAN = 39
    FEEDBACK_BLOCKED = 40
    FEEDBACK_SWAP = 41
    SUPERALLERGIC_REACTION = 45
    ALLERGIC_REACTION = 47
    REVERB_BESTOWS_REVERBERATING = 48
    REVERB_ROSTER_SHUFFLE = 49
    BLOODDRAIN = 51
    BLOODDRAIN_SIPHON = 52
    BLOODDRAIN_BLOCKED = 53
    INCINERATION = 54
    INCINERATION_BLOCKED = 55
    FLAG_PLANTED = 56
    RENOVATION_BUILT = 57
    LIGHT_SWITCH_TOGGLED = 58
    DECREE_PASSED = 59
    BLESSING_OR_GIFT_WON = 60
    WILL_RECIEVED = 61
    FLOODING_SWEPT = 62
    SALMON_SWIM = 63
    POLARITY_SHIFT = 64
    ENTER_SECRET_BASE = 65
    EXIT_SECRET_BASE = 66
    CONSUMERS_ATTACK = 67
    ECHO_CHAMBER = 69
    GRIND_RAIL = 70
    TUNNELS_USED = 71
    PEANUT_MISTER = 72
    PEANUT_FLAVOR_TEXT = 73
    TASTE_THE_INFINITE = 74
    EVENT_HORIZON_ACTIVATION = 76
    EVENT_HORIZON_AWAITS = 77
    SOLAR_PANELS_AWAIT = 78
    SOLAR_PANELS_ACTIVATION = 79
    TAROT_READING = 81
    EMERGENCY_ALERT = 82
    RETURN_FROM_ELSEWHERE = 84
    OVER_UNDER = 85
    UNDER_OVER = 86
    UNDERSEA = 88
    HOMEBODY = 91
    SUPERYUMMY = 92
    PERK = 93
    EARLBIRD = 96
    LATE_TO_THE_PARTY = 97
    SHAME_DONOR = 99
    ADDED_MOD = 106
    REMOVED_MOD = 107
    MOD_EXPIRES = 108
    PLAYER_ADDED_TO_TEAM = 109
    PLAYER_REPLACED_BY_NECROMANCY = 110
    PLAYER_REPLACES_RETURNED = 111
    PLAYER_REMOVED_FROM_TEAM = 112
    PLAYER_TRADED = 113
    PLAYER_SWAP = 114
    PLAYER_MOVE = 115
    PLAYER_BORN_FROM_INCINERATION = 116
    PLAYER_STAT_INCREASE = 117
    PLAYER_STAT_DECREASE = 118
    PLAYER_STAT_REROLL = 119
    PLAYER_STAT_DECREASE_FROM_SUPERALLERGIC = 122
    PLAYER_MOVE_FAILED_FORCE = 124
    ENTER_HALL_OF_FLAME = 125
    EXIT_HALL_OF_FLAME = 126
    PLAYER_GAINED_ITEM = 127
    PLAYER_LOST_ITEM = 128
    REVERB_FULL_SHUFFLE = 130
    REVERB_LINEUP_SHUFFLE = 131
    REVERB_ROTATION_SHUFFLE = 132
    PLAYER_HATCHED = 137
    FINAL_STANDINGS = 143
    MODIFICATION_CHANGE = 144
    ADDED_MOD_FROM_OTHER_MOD = 146
    REMOVED_MODIFICATION = 147
    CHANGED_MODIFIER = 148
    TEAM_WAS_SHAMED = 154
    TEAM_DID_SHAME = 155
    SUN_2_OUTCOME = 156
    BLACK_HOLE_OUTCOME = 157
    ELIMINATED_FROM_POSTSEASON = 158
    POSTSEASON_ADVANCE = 159
    HIGH_PRESSURE_ON_OFF = 165
    ECHO_MESSAGE = 169
    ECHO_INTO_STATIC = 170
    REMOVED_MULTIPLE_MODIFICATIONS_ECHO = 171
    ADDED_MULTIPLE_MODIFICATIONS_ECHO = 172
    PSYCHO_ACOUSTICS = 173
    RECEIVER_BECOMES_ECHO = 174
    INVESTIGATION_PROGRESS = 175
    AMBITIOUS = 182
    RUNS_SCORED = 209
    WIN_COLLECTED_REGULAR = 214
    WIN_COLLECTED_POSTSEASON = 215
    GAME_OVER = 216
    STORM_WARNING = 263
    SNOWFLAKES = 264

    # Ensure that not-yet-handled values warn us,
    # then default to a safe value
    @classmethod
    def _missing_(cls, value):
        print("!!! unknown type: {}".format(value))
        return cls.NOT_YET_HANDLED_IN_ENUM


@unique
class Weather(IntEnum):
    SUN_2 = 1
    ECLIPSE = 7
    GLITTER = 8
    BLOODDRAIN = 9
    PEANUTS = 10
    BIRDS = 11
    FEEDBACK = 12
    REVERB = 13
    BLACK_HOLE = 14
    COFFEE = 15
    COFFEE_2 = 16
    COFFEE_3S = 17
    FLOODING = 18
    SALMON = 19
    POLARITY_PLUS = 20
    POLARITY_MINUS = 21
    SUN_90 = 23
    SUN_POINT_1 = 24
    SUM_SUN = 25

    def is_coffee(self):
        return self.value in [
            self.COFFEE,
            self.COFFEE_2,
            self.COFFEE_3S,
        ]

    def is_polarity(self):
        return self.value in [
            self.POLARITY_PLUS,
            self.POLARITY_MINUS,
        ]

    def can_echo(self):
        return self.value in [
            self.FEEDBACK,
            self.REVERB,
        ]


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


null_stadium = StadiumData(
    {
        "id": None,
        "mods": [],
        "name": "Null Stadium",
        "nickname": "Null Stadium",
        "mysticism": 0.5,
        "viscosity": 0.5,
        "elongation": 0.5,
        "filthiness": 0,
        "obtuseness": 0.5,
        "forwardness": 0.5,
        "grandiosity": 0.5,
        "ominousness": 0.5,
        "fortification": 0.5,
        "inconvenience": 0.5,
        "hype": 0,
    }
)


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

    def vibes(self, day):
        frequency = 6 + round(10 * self.data["buoyancy"])
        phase = math.pi * ((2 / frequency) * day + 0.5)

        pressurization = self.data["pressurization"]
        cinnamon = self.data["cinnamon"] if self.data["cinnamon"] is not None else 0
        viberange = 0.5 * (pressurization + cinnamon)
        vibes = (viberange * math.sin(phase)) - (0.5 * pressurization) + (0.5 * cinnamon)
        return vibes if not self.has_mod("SCATTERED") else 0


class GameData:
    def __init__(self):
        self.teams = {}
        self.players = {}
        self.stadiums = {}
        self.plays = {}
        self.games = {}
        self.sim = None

    def fetch_sim(self, timestamp, delta_secs: float = 0):
        timestamp = offset_timestamp(timestamp, delta_secs)
        key = "sim_at_{}".format(timestamp)
        resp = get_cached(
            key,
            "https://api.sibr.dev/chronicler/v2/entities?type=sim&at={}".format(timestamp),
        )
        self.sim = resp["items"][0]["data"]

    def fetch_teams(self, timestamp, delta_secs: float = 0):
        timestamp = offset_timestamp(timestamp, delta_secs)
        key = "teams_at_{}".format(timestamp)
        resp = get_cached(
            key,
            "https://api.sibr.dev/chronicler/v2/entities?type=team&at={}&count=1000".format(timestamp),
        )
        self.teams = {e["entityId"]: e["data"] for e in resp["items"]}

    def fetch_players(self, timestamp, delta_secs: float = 0):
        timestamp = offset_timestamp(timestamp, delta_secs)
        key = "players_at_{}".format(timestamp)
        resp = get_cached(
            key,
            "https://api.sibr.dev/chronicler/v2/entities?type=player&at={}&count=2000".format(timestamp),
        )
        self.players = {e["entityId"]: e["data"] for e in resp["items"]}

    def fetch_stadiums(self, timestamp, delta_secs: float = 0):
        timestamp = offset_timestamp(timestamp, delta_secs)
        key = "stadiums_at_{}".format(timestamp)
        resp = get_cached(
            key,
            "https://api.sibr.dev/chronicler/v2/entities?type=stadium&at={}&count=1000".format(timestamp),
        )
        self.stadiums = {e["entityId"]: e["data"] for e in resp["items"]}

    def fetch_player_after(self, player_id, timestamp):
        key = "player_{}_after_{}".format(player_id, timestamp)
        resp = get_cached(
            key,
            "https://api.sibr.dev/chronicler/v2/versions?type=player&id={}&after={}&count=1&order=asc".format(
                player_id, timestamp
            ),
        )
        for item in resp["items"]:
            self.players[item["entityId"]] = item["data"]

    def fetch_game(self, game_id):
        key = "game_updates_{}".format(game_id)
        resp = get_cached(
            key,
            "https://api.sibr.dev/chronicler/v1/games/updates?count=2000&game={}&started=true".format(game_id),
        )
        self.games[game_id] = resp["data"]
        for update in resp["data"]:
            play = update["data"]["playCount"]
            self.plays[(game_id, play)] = update["data"]

    def fetch_league_data(self, timestamp, delta_secs: float = 0):
        self.fetch_sim(timestamp, delta_secs)
        self.fetch_teams(timestamp, delta_secs)
        self.fetch_players(timestamp, delta_secs)
        self.fetch_stadiums(timestamp, delta_secs)

    def get_update(self, game_id, play):
        if game_id not in self.games:
            self.fetch_game(game_id)
        update = self.plays.get((game_id, play))
        if update:
            update["weather"] = Weather(update["weather"])
        return update

    def get_player(self, player_id) -> PlayerData:
        return PlayerData(self.players[player_id])

    def has_player(self, player_id) -> bool:
        return player_id in self.players

    def get_team(self, team_id) -> TeamData:
        return TeamData(self.teams[team_id])

    def get_stadium(self, stadium_id) -> StadiumData:
        return StadiumData(self.stadiums[stadium_id])
