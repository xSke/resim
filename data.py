import collections
import dataclasses
import re
from dataclasses import dataclass
import os
import json
import requests
from typing import Any, List, Dict, Iterable, Mapping, Optional, Set, Union, FrozenSet, TypeVar, Tuple
from datetime import datetime, timedelta
from enum import Enum, IntEnum, auto, unique
from sin_values import SIN_PHASES

from frozendict import frozendict

stat_indices = [
    "tragicness",
    "buoyancy",
    "thwackability",
    "moxie",
    "divinity",
    "musclitude",
    "patheticism",
    "martyrdom",
    "cinnamon",
    "baseThirst",
    "laserlikeness",
    "continuation",
    "indulgence",
    "groundFriction",
    "shakespearianism",
    "suppression",
    "unthwackability",
    "coldness",
    "overpowerment",
    "ruthlessness",
    "pressurization",
    "omniscience",
    "tenaciousness",
    "watchfulness",
    "anticapitalism",
    "chasiness",
]


def offset_timestamp(timestamp: str, delta_secs: float) -> str:
    timestamp = timestamp.replace("Z", "+00:00")
    dt = datetime.fromisoformat(timestamp)
    dt = dt + timedelta(seconds=delta_secs)
    timestamp = dt.isoformat()
    return timestamp.replace("+00:00", "Z")


def get_cached(key, url):
    key = key.replace(":", "_")

    path = os.path.join("cache", key + ".json")
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                return data
            except json.JSONDecodeError:
                pass

    data = requests.get(url).json()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return data


@unique
class Mod(Enum):
    """
    Modifications which are being used within Resim.
    Not an exhaustive list! Add here when necessary.
    """

    def _generate_next_value_(name, start, count, last_values):
        """Ensure Mod values match names"""
        return name

    ZERO = "0"
    AA = auto()
    AAA = auto()
    ACIDIC = auto()
    AFFINITY_FOR_CROWS = auto()
    ATTRACTOR = auto()
    BASE_INSTINCTS = auto()
    BIG_BUCKET = auto()
    BIRD_SEED = auto()
    CAREFUL = auto()
    CHUNKY = auto()
    COFFEE_PERIL = auto()
    DEBT_THREE = auto()
    ECHO = auto()
    ECHO_CHAMBER = auto()
    EGO1 = auto()
    EGO2 = auto()
    EGO3 = auto()
    EGO4 = auto()
    ELECTRIC = auto()
    ELSEWHERE = auto()
    FIRE_EATER = auto()
    FIREPROOF = auto()
    FLINCH = auto()
    FLOOD_PUMPS = auto()
    FRIEND_OF_CROWS = auto()
    FORCE = auto()
    GRIND_RAIL = auto()
    GROWTH = auto()
    H20 = auto()
    HAUNTED = auto()
    HIGH_PRESSURE = auto()
    HONEY_ROASTED = auto()
    HOTEL_MOTEL = auto()
    INHABITING = auto()
    LOVE = auto()
    MARKED = auto()
    MAXIMALIST = auto()
    MINIMALIST = auto()
    O_NO = auto()
    ON_FIRE = auto()
    OVERPERFORMING = auto()
    PARASITE = auto()
    PARTY_TIME = auto()
    PEANUT_MISTER = auto()
    PERK = auto()
    PSYCHIC = auto()
    PSYCHOACOUSTICS = auto()
    REDACTED = auto()
    REVERBERATING = auto()
    SALMON_CANNONS = auto()
    SCATTERED = auto()
    SECRET_BASE = auto()
    SEEKER = auto()
    SHELLED = auto()
    SINKING_SHIP = auto()
    SLOW_BUILD = auto()
    SMITHY = auto()
    SMOOTH = auto()
    SWEETENER = auto()
    SWIM_BLADDER = auto()
    TRAVELING = auto()
    TRIPLE_THREAT = auto()
    UNDERPERFORMING = auto()
    WILD = auto()

    @classmethod
    def coerce(cls, value):
        return cls(value) if value in cls.__members__ else None

    def __str__(self):
        return self.value


def get_feed_between(start, end):
    key = f"feed_range_{start}_{end}"
    resp = get_cached(
        key, f"https://api.sibr.dev/eventually/v2/events?after={start}&before={end}&sortorder=asc&limit=200000"
    )
    return resp


def get_game_feed(game_id):
    key = f"feed_game_{game_id}"
    resp = get_cached(key, f"https://api.sibr.dev/eventually/v2/events?gameTags={game_id}&sortorder=asc&limit=1000")
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
    TEAM_JOINED_LEAGUE = 135
    EXISTING_PLAYER_ADDED_TO_ILB = 136
    PLAYER_HATCHED = 137
    WON_INTERNET_SERIES = 141
    POSTSEASON_SPOT = 142
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
    LOVERS_LINEUP_OPTIMIZED = 166
    ECHO_MESSAGE = 169
    ECHO_INTO_STATIC = 170
    REMOVED_MULTIPLE_MODIFICATIONS_ECHO = 171
    ADDED_MULTIPLE_MODIFICATIONS_ECHO = 172
    PSYCHO_ACOUSTICS = 173
    RECEIVER_BECOMES_ECHO = 174
    INVESTIGATION_PROGRESS = 175
    GLITTER_CRATE_DROP = 177
    MIDDLING = 178
    PLAYER_HIDDEN_STAT_INCREASE = 179
    PLAYER_HIDDEN_STAT_DECREASE = 180
    ENTERING_CRIMESCENE = 181
    AMBITIOUS = 182
    ITEM_BREAKS = 185
    ITEM_DAMAGE = 186
    BROKEN_ITEM_REPAIRED = 187
    DAMAGED_ITEM_REPAIRED = 188
    COMMUNITY_CHEST_GAME_EVENT = 189
    FAX_MACHINE_ACTIVATION = 191
    HOLIDAY_INNING = 192
    PRIZE_MATCH = 193
    SMITHY_ACTIVATION = 195
    A_BLOOD_TYPE = 198
    HYPE_BUILT = 206
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
        print(f"!!! unknown type: {value}")
        return cls.NOT_YET_HANDLED_IN_ENUM


@unique
class Weather(IntEnum):
    VOID = 0
    SUN_2 = 1
    OVERCAST = 2
    RAINY = 3
    SANDSTORM = 4
    SNOWY = 5
    ACIDIC = 6
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
    SUPERNOVA_ECLIPSE = 26
    BLACK_HOLE_BLACK_HOLE = 27
    JAZZ = 28
    NIGHT = 29

    def is_coffee(self):
        return self.value in [self.COFFEE, self.COFFEE_2, self.COFFEE_3S]

    def is_polarity(self):
        return self.value in [self.POLARITY_PLUS, self.POLARITY_MINUS]

    def can_echo(self):
        return self.value in [self.FEEDBACK, self.REVERB]


@unique
class Base(IntEnum):
    """Yes, these are zero-indexed."""

    FIRST = 0
    SECOND = 1
    THIRD = 2
    FOURTH = 3


@unique
class Blood(IntEnum):
    A = 0
    AA = 1
    AAA = 2
    ACIDIC = 3
    BASIC = 4
    O = 5  # noqa: E741
    O_NO = 6
    H2O = 7
    ELECTRIC = 8
    LOVE = 9
    FIRE = 10
    PSYCHIC = 11
    GRASS = 12
    BALL = 13
    STRIKE = 14


@unique
class ModType(IntEnum):
    PERMANENT = 0
    SEASON = 1
    WEEK = 2
    GAME = 3
    ITEM = 4


camel_to_snake_re = re.compile('((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))')


def camel_to_snake_case(s: str) -> str:
    return camel_to_snake_re.sub(r'_\1', s).lower()


MOD_KEYS = {
    ModType.PERMANENT: "permAttr",
    ModType.SEASON: "seasAttr",
    ModType.WEEK: "weekAttr",
    ModType.GAME: "gameAttr",
    ModType.ITEM: "itemAttr",
}

TeamOrPlayer = TypeVar("TeamOrPlayer")


@dataclass(frozen=True)
class TeamOrPlayerMods:
    mods: FrozenSet[str]
    # Used internally only
    _mods_by_type: Dict[ModType, FrozenSet[str]]

    @staticmethod
    def mods_from_dict(data: Dict[str, Any]):
        mods_by_type = {}
        for (mod_type, key) in MOD_KEYS.items():
            mods_by_type[mod_type] = frozenset(data.get(key, []))
        mods = frozenset().union(*mods_by_type.values())

        return dict(
            mods=mods,
            _mods_by_type=mods_by_type
        )

    def has_mod(self, mod: Union[Mod, str], mod_type: Optional[ModType] = None) -> bool:
        mod = str(mod)
        if mod_type is None:
            return mod in self.mods
        return mod in self._mods_by_type[mod_type]

    def has_any(self, *mods: Mod) -> bool:
        return any(self.has_mod(mod) for mod in mods)

    def print_mods(self, mod_type: Optional[ModType] = None) -> str:
        return str(list(self._mods_by_type.get(mod_type) or self.mods))

    def _concatenate_mods_by_type(self) -> FrozenSet[str]:
        return frozenset().union(*self._mods_by_type.values())

    def without_mod(self: TeamOrPlayer, mod_name: str, mod_type: ModType, version_date: str) -> TeamOrPlayer:
        self._mods_by_type[mod_type] = self._mods_by_type[mod_type].difference({mod_name})
        return dataclasses.replace(self, version_date=version_date, mods=self._concatenate_mods_by_type())

    def with_mod(self: TeamOrPlayer, mod_name: str, mod_type: ModType, version_date: str) -> TeamOrPlayer:
        self._mods_by_type[mod_type] = self._mods_by_type[mod_type].intersection({mod_name})
        return dataclasses.replace(self, version_date=version_date, mods=self._concatenate_mods_by_type())


@dataclass(frozen=True)
class TeamData(TeamOrPlayerMods):
    id: Optional[str]
    version_date: str
    lineup: Tuple[str]
    rotation: Tuple[str]
    shadows: Tuple[str]
    eDensity: float = 0
    level: int = 0
    nickname: str = ""
    rotation_slot: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any], version_date: str):
        return cls(
            id=data["id"],
            version_date=version_date,
            lineup=tuple(data["lineup"]),
            rotation=tuple(data["rotation"]),
            shadows=tuple(data.get("shadows", []) + data.get("bullpen", []) + data.get("bench", [])),
            level=data.get("level") or 0,
            eDensity=data.get("eDensity") or 0,
            nickname=data.get("nickname") or "",
            rotation_slot=data.get("rotationSlot") or 0,
            **cls.mods_from_dict(data),
        )

    @staticmethod
    def null():
        return TeamData.from_dict(
            {
                "id": None,
                "nickname": "Null Team",
                # Using [None] rather than [] means things like fielder selection
                # won't get an index error
                "lineup": [None],
                "rotation": [None],
            },
            "1970-01-01T00:00:00Z"
        )


@dataclass(frozen=True)
class StadiumData:
    id: Optional[str]
    version_date: str
    mods: FrozenSet[str]
    name: str
    nickname: str
    mysticism: float
    viscosity: float
    elongation: float
    filthiness: float
    obtuseness: float
    forwardness: float
    grandiosity: float
    ominousness: float
    fortification: float
    inconvenience: float
    hype: float

    def has_mod(self, mod: Mod) -> bool:
        return mod.value in self.mods

    def print_mods(self):
        return list(self.mods)

    @staticmethod
    def from_dict(data, valid_from: str):
        return StadiumData(
            id=data["id"],
            version_date=valid_from,
            mods=frozenset(data["mods"]),
            name=data["name"],
            nickname=data["nickname"],
            mysticism=data["mysticism"],
            viscosity=data["viscosity"],
            elongation=data["elongation"],
            filthiness=data["filthiness"],
            obtuseness=data["obtuseness"],
            forwardness=data["forwardness"],
            grandiosity=data["grandiosity"],
            ominousness=data["ominousness"],
            fortification=data["fortification"],
            inconvenience=data["inconvenience"],
            hype=data["hype"],
        )

    @staticmethod
    def null():
        return StadiumData(
            id=None,
            version_date="1970-01-01T00:00:00Z",
            mods=frozenset(),
            name="Null Stadium",
            nickname="Null Stadium",
            mysticism=0.5,
            viscosity=0.5,
            elongation=0.5,
            filthiness=0,
            obtuseness=0.5,
            forwardness=0.5,
            grandiosity=0.5,
            ominousness=0.5,
            fortification=0.5,
            inconvenience=0.5,
            hype=0,
        )

    def with_hype(self, new_hype: float, version_date: str) -> "StadiumData":
        return dataclasses.replace(self, hype=new_hype, version_date=version_date)


@dataclass(frozen=True)
class ItemData:
    id: Optional[str]
    name: str
    health: int
    durability: int
    defense_rating: float
    hitting_rating: float
    pitching_rating: float
    baserunning_rating: float
    stats: frozendict

    @staticmethod
    def from_dict(data):
        stats = {}
        components = [data["root"], data["suffix"], data["prePrefix"], data["postPrefix"]] + (data["prefixes"] or [])
        for component in components:
            if not component:
                continue

            for adjustment in component["adjustments"]:
                if adjustment["type"] == 1:
                    stat_name = stat_indices[adjustment["stat"]]
                    value = adjustment["value"]
                    stats[stat_name] = stats.get(stat_name, 0) + value

        return ItemData(
            id=data["id"],
            name=data["name"],
            health=data["health"],
            durability=data["durability"],
            defense_rating=data["defenseRating"],
            hitting_rating=data["hittingRating"],
            pitching_rating=data["pitchingRating"],
            baserunning_rating=data["baserunningRating"],
            stats=frozendict(stats),
        )

    @staticmethod
    def null():
        return ItemData(
            id=None,
            name="Null Item",
            health=0,
            durability=0,
            defense_rating=0,
            hitting_rating=0,
            pitching_rating=0,
            baserunning_rating=0,
            stats=frozendict(),
        )

    def with_health(self, new_health: int) -> "ItemData":
        return dataclasses.replace(self, health=new_health)


@dataclass(frozen=True)
class PlayerData(TeamOrPlayerMods):
    id: Optional[str]
    version_date: str
    raw_name: str
    unscattered_name: Optional[str]
    data: frozendict
    # Player attributes
    buoyancy: float
    divinity: float
    martyrdom: float
    moxie: float
    musclitude: float
    patheticism: float
    thwackability: float
    tragicness: float
    ruthlessness: float
    overpowerment: float
    unthwackability: float
    shakespearianism: float
    suppression: float
    coldness: float
    base_thirst: float
    continuation: float
    ground_friction: float
    indulgence: float
    laserlikeness: float
    anticapitalism: float
    chasiness: float
    omniscience: float
    tenaciousness: float
    watchfulness: float
    pressurization: float
    cinnamon: float
    blood: Optional[Blood]
    consecutive_hits: int
    bat: Optional[str]
    soul: int
    eDensity: float
    items: Tuple[ItemData]
    season_mod_sources: frozendict[str, Tuple[str]]
    peanut_allergy: bool

    @classmethod
    def from_dict(cls, data: Dict[str, Any], version_date: str):
        data_state = data.get("state", {})
        items = [ItemData.from_dict(item) for item in data.get("items") or []]
        stats = cls.stats_with_items(data, items)
        return cls(
            data=frozendict(data),
            version_date=version_date,
            id=data["id"],
            raw_name=data["name"],
            unscattered_name=data_state.get("unscatteredName"),
            items=tuple(items),
            blood=data.get("blood") or None,
            consecutive_hits=data.get("consecutiveHits") or 0,
            bat=data.get("bat") or None,
            soul=data.get("soul") or 0,
            eDensity=data.get("eDensity") or 0,
            season_mod_sources=frozendict(data_state.get("seasModSources", {})),
            peanut_allergy=data.get("peanutAllergy"),
            **stats,
            **cls.mods_from_dict(data),
        )

    @property
    def name(self):
        return self.unscattered_name or self.raw_name

    def vibes(self, day) -> float:
        if self.has_mod(Mod.SCATTERED):
            return 0
        return self.raw_vibes(day)

    def raw_vibes(self, day) -> float:
        frequency = 6 + round(10 * self.buoyancy)
        # Pull from pre-computed sin values
        sin_phase = SIN_PHASES[frequency][day]
        # Original formula:
        # sin_phase = math.sin(math.pi * ((2 / frequency) * day + 0.5))

        pressurization = self.pressurization
        cinnamon = self.cinnamon or 0
        return 0.5 * ((sin_phase - 1) * pressurization + (sin_phase + 1) * cinnamon)

    @staticmethod
    def stats_with_items(data: Dict[str, Any], items: List[ItemData]) -> dict:
        stats = {camel_to_snake_case(stat): data[stat] for stat in stat_indices}
        for item in items:
            if item.health != 0:
                for stat, value in item.stats.items():
                    stats[camel_to_snake_case(stat)] += value

        stats['cinnamon'] = stats.get('cinnamon') or 0
        return stats

    @staticmethod
    def null():
        return PlayerData.from_dict(
            {
                "id": None,
                "name": "Null Player",
                "buoyancy": 0.5,
                "divinity": 0.5,
                "martyrdom": 0.5,
                "moxie": 0.5,
                "musclitude": 0.5,
                "patheticism": 0.5,
                "thwackability": 0.5,
                "tragicness": 0.5,
                "ruthlessness": 0.5,
                "overpowerment": 0.5,
                "unthwackability": 0.5,
                "shakespearianism": 0.5,
                "suppression": 0.5,
                "coldness": 0.5,
                "baseThirst": 0.5,
                "continuation": 0.5,
                "groundFriction": 0.5,
                "indulgence": 0.5,
                "laserlikeness": 0.5,
                "anticapitalism": 0.5,
                "chasiness": 0.5,
                "omniscience": 0.5,
                "tenaciousness": 0.5,
                "watchfulness": 0.5,
                "pressurization": 0.5,
                "cinnamon": 0.5,
                "blood": None,
                "consecutive_hits": 0,
                "bat": None,
                "soul": 0,
                "eDensity": 0,
                "items": [],
            },
            "1970-01-01T00:00:00Z"
        )

    def with_raw_name(self, name: str, version_date: str) -> "PlayerData":
        if name != self.raw_name:
            return dataclasses.replace(self, raw_name=name, version_date=version_date)
        else:
            return self

    def with_items(self, new_items: List[ItemData], version_date: str) -> "PlayerData":
        new_stats = self.stats_with_items(self.data, new_items)
        return dataclasses.replace(self, items=tuple(new_items), version_date=version_date, **new_stats)


CHRONICLER_URI = "https://api.sibr.dev/chronicler"


class NullUpdate(collections.defaultdict):
    def __init__(self, values: Optional[Union[Iterable, Mapping]] = None):
        if values is None:
            values = {"basesOccupied": [], "baseRunners": [], "weather": Weather.VOID}
        super().__init__(int, values)

    def __bool__(self):
        return False


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
        key = f"sim_at_{timestamp}"
        resp = get_cached(
            key,
            f"{CHRONICLER_URI}/v2/entities?type=sim&at={timestamp}",
        )
        self.sim = resp["items"][0]["data"]

    def fetch_teams(self, timestamp, delta_secs: float = 0):
        timestamp = offset_timestamp(timestamp, delta_secs)
        key = f"teams_at_{timestamp}"
        resp = get_cached(
            key,
            f"{CHRONICLER_URI}/v2/entities?type=team&at={timestamp}&count=1000",
        )
        self.teams = {e["entityId"]: TeamData.from_dict(e["data"], e["validFrom"]) for e in resp["items"]}

    def fetch_players(self, timestamp, delta_secs: float = 0):
        timestamp = offset_timestamp(timestamp, delta_secs)
        key = f"players_at_{timestamp}"
        resp = get_cached(
            key,
            f"{CHRONICLER_URI}/v2/entities?type=player&at={timestamp}&count=2000",
        )
        self.players = {e["entityId"]: PlayerData.from_dict(e["data"], e["validFrom"]) for e in resp["items"]}

    def fetch_stadiums(self, timestamp, delta_secs: float = 0):
        timestamp = offset_timestamp(timestamp, delta_secs)
        key = f"stadiums_at_{timestamp}"
        resp = get_cached(
            key,
            f"{CHRONICLER_URI}/v2/entities?type=stadium&at={timestamp}&count=1000",
        )
        self.stadiums = {e["entityId"]: StadiumData.from_dict(e["data"], e["validFrom"]) for e in resp["items"]}

    def fetch_player_after(self, player_id, timestamp):
        key = f"player_{player_id}_after_{timestamp}"
        resp = get_cached(
            key,
            f"{CHRONICLER_URI}/v2/versions?type=player&id={player_id}&after={timestamp}&count=1&order=asc",
        )
        for item in resp["items"]:
            self.players[item["entityId"]] = PlayerData.from_dict(item["data"], item["validFrom"])

    def fetch_game(self, game_id):
        key = f"game_updates_{game_id}"
        resp = get_cached(
            key,
            f"{CHRONICLER_URI}/v1/games/updates?count=2000&game={game_id}&started=true",
        )
        self.games[game_id] = resp["data"]
        for update in resp["data"]:
            play = update["data"]["playCount"]
            update["data"]["version_date"] = update["timestamp"]
            self.plays[(game_id, play)] = update["data"]

    def fetch_league_data(self, timestamp, delta_secs: float = 0):
        self.fetch_sim(timestamp, delta_secs)
        self.fetch_teams(timestamp, delta_secs)
        self.fetch_players(timestamp, delta_secs)
        self.fetch_stadiums(timestamp, delta_secs)

    def get_update(self, game_id, play):
        if game_id not in self.games:
            self.fetch_game(game_id)
        update = self.plays.get((game_id, play), NullUpdate())
        update["weather"] = Weather(update["weather"])
        return update

    def has_player(self, player_id) -> bool:
        return player_id in self.players

    def get_player(self, player_id) -> PlayerData:
        return self.players[player_id] if player_id else PlayerData.null()

    def set_player(self, player_id, new_player):
        self.players[player_id] = new_player

    def get_team(self, team_id) -> TeamData:
        return self.teams[team_id] if team_id else TeamData.null()

    def set_team(self, team_id, new_team):
        self.teams[team_id] = new_team

    def get_stadium(self, stadium_id) -> StadiumData:
        return self.stadiums[stadium_id] if stadium_id else StadiumData.null()

    def set_stadium(self, stadium_id, new_stadium):
        self.stadiums[stadium_id] = new_stadium

    def add_mod_to_player(self, player_id: str, mod_name: str, mod_type: ModType, version_date: str) -> PlayerData:
        player = self.get_player(player_id)
        new_player = player.with_mod(mod_name, mod_type, version_date)
        self.set_player(player_id, new_player)
        return new_player

    def add_mod_to_team(self, team_id: str, mod_name: str, mod_type: ModType, version_date: str) -> TeamData:
        team = self.get_team(team_id)
        new_team = team.with_mod(mod_name, mod_type, version_date)
        self.set_team(team_id, new_team)
        return new_team

    def remove_mod_from_player(self, player_id: str, mod_name: str, mod_type: ModType, version_date: str) -> PlayerData:
        player = self.get_player(player_id)
        new_player = player.without_mod(mod_name, mod_type, version_date)
        self.set_player(player_id, new_player)
        return new_player

    def remove_mod_from_team(self, team_id: str, mod_name: str, mod_type: ModType, version_date: str) -> TeamData:
        team = self.get_team(team_id)
        new_team = team.without_mod(mod_name, mod_type, version_date)
        self.set_team(team_id, new_team)
        return new_team

    def replace_player_on_team(self, team_id: str, location: int, player_to_remove: str, player_to_add: str,
                               version_date: str) -> TeamData:
        team = self.get_team(team_id)
        if location == 0:
            player_list = team.lineup
        elif location == 1:
            player_list = team.rotation
        else:
            player_list = team.shadows
        replace_idx = player_list.index(player_to_remove)
        new_player_list = player_list[:replace_idx] + (player_to_add,) + player_list[replace_idx + 1:]
        assert len(new_player_list) == len(player_list)
        return self._replace_player_list(team, location, new_player_list, version_date)

    def _replace_player_list(self, team: TeamData, location: int, new_player_list: Tuple[str],
                             version_date: str) -> TeamData:
        if location == 0:
            new_team = dataclasses.replace(team, lineup=new_player_list, version_date=version_date)
        elif location == 1:
            new_team = dataclasses.replace(team, rotation=new_player_list, version_date=version_date)
        else:
            new_team = dataclasses.replace(team, shadows=new_player_list, version_date=version_date)
        self.set_team(team.id, new_team)
        return new_team

    def remove_player_from_team(self, team_id: str, location: int, player_to_remove: str,
                                version_date: str) -> TeamData:
        team = self.get_team(team_id)
        if location == 0:
            player_list = team.lineup
        elif location == 1:
            player_list = team.rotation
        else:
            player_list = team.shadows
        replace_idx = player_list.index(player_to_remove)
        new_player_list = player_list[:replace_idx] + player_list[replace_idx + 1:]
        assert len(new_player_list) == len(player_list) - 1
        return self._replace_player_list(team, location, new_player_list, version_date)

    def append_player_to_team(self, team_id: str, location: int, player_to_add: str,
                              version_date: str) -> TeamData:
        team = self.get_team(team_id)
        if location == 0:
            player_list = team.lineup
        elif location == 1:
            player_list = team.rotation
        else:
            player_list = team.shadows
        new_player_list = player_list + (player_to_add,)
        assert len(new_player_list) == len(player_list) + 1
        return self._replace_player_list(team, location, new_player_list, version_date)
