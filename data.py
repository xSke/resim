import collections
from dataclasses import dataclass, field
import os
import json
import requests
from dataclasses_json import DataClassJsonMixin, config
from typing import Any, List, Dict, Iterable, Mapping, Optional, Set, Union, ClassVar
from datetime import datetime, timedelta
from enum import Enum, IntEnum, auto, unique
from sin_values import SIN_PHASES

EXCLUDE_FROM_CACHE = {
    "team": {"runs", "wins", "eDensity"},
    "player": {"consecutiveHits", "eDensity"},
    "stadium": {"hype"},
}

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
    HOOPS = auto()
    HOTEL_MOTEL = auto()
    INHABITING = auto()
    LATE_TO_PARTY = auto()
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
    UNDERTAKER = auto()
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


def cacheable(data: Dict[str, Any], object_type: str) -> Dict[str, Any]:
    return {k: v for k, v in data.items() if k not in EXCLUDE_FROM_CACHE[object_type]}


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
    COASTING = 184
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


def mods_by_type_decoder(raw: Dict[str, List[str]]):
    return {ModType(int(k)): v for k, v in raw.items()}


@dataclass
class TeamOrPlayerMods(DataClassJsonMixin):
    mods: Set[str]
    # Used internally only
    _mods_by_type: Dict[ModType, Set[str]] = field(metadata=config(decoder=mods_by_type_decoder))

    @classmethod
    def mods_init_args(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        MOD_KEYS = {
            ModType.PERMANENT: "permAttr",
            ModType.SEASON: "seasAttr",
            ModType.WEEK: "weekAttr",
            ModType.GAME: "gameAttr",
            ModType.ITEM: "itemAttr",
        }
        mods_by_type = {}
        for (mod_type, key) in MOD_KEYS.items():
            mods_by_type[mod_type] = set(data.get(key, []))
        return dict(_mods_by_type=mods_by_type, mods=cls._concatenate_mods(mods_by_type))

    def add_mod(self, mod: Union[Mod, str], mod_type: ModType):
        mod = str(mod)
        if mod in self._mods_by_type[mod_type]:
            return
        self._mods_by_type[mod_type].add(mod)
        self._update_mods()

    def remove_mod(self, mod: Union[Mod, str], mod_type: ModType):
        mod = str(mod)
        if mod not in self._mods_by_type[mod_type]:
            return
        self._mods_by_type[mod_type].remove(mod)
        self._update_mods()

    def has_mod(self, mod: Union[Mod, str], mod_type: Optional[ModType] = None) -> bool:
        mod = str(mod)
        if mod_type is None:
            return mod in self.mods
        return mod in self._mods_by_type[mod_type]

    def has_any(self, *mods: Mod) -> bool:
        return any(self.has_mod(mod) for mod in mods)

    def print_mods(self, mod_type: Optional[ModType] = None) -> str:
        return str(list(self._mods_by_type.get(mod_type) or self.mods))

    def _update_mods(self):
        self.mods = self._concatenate_mods(self._mods_by_type)

    @staticmethod
    def _concatenate_mods(mods_by_type: Dict[ModType, Set[str]]) -> Set[str]:
        return set().union(*mods_by_type.values())


@dataclass
class TeamData(TeamOrPlayerMods):
    object_type: ClassVar[str] = "team"
    null: ClassVar["TeamData"]
    id: Optional[str]
    last_update_time: str
    lineup: List[str]
    rotation: List[str]
    shadows: List[str]
    eDensity: float = 0
    level: int = 0
    nickname: str = ""
    rotation_slot: int = 0

    @classmethod
    def from_chron(cls, data: Dict[str, Any], last_update_time: str, prev_team_data: Optional["TeamData"]):
        team_data = TeamData(
            id=data["id"],
            last_update_time=last_update_time,
            lineup=data["lineup"],
            rotation=data["rotation"],
            shadows=data.get("shadows", []) + data.get("bullpen", []) + data.get("bench", []),
            level=data.get("level") or 0,
            eDensity=data.get("eDensity") or 0,
            nickname=data.get("nickname") or "",
            rotation_slot=data.get("rotationSlot") or 0,
            **cls.mods_init_args(data),
        )

        if prev_team_data is not None:
            if prev_team_data.is_cache_equivalent(team_data):
                team_data.last_update_time = prev_team_data.last_update_time

        return team_data

    def is_cache_equivalent(self, other: "TeamData") -> bool:
        return (
            self.id == other.id
            and
            # Excluding last update time
            self.lineup == other.lineup
            and self.rotation == other.rotation
            and self.shadows == other.shadows
            and
            # Excluding eDensity
            self.level == other.level
            and self.nickname == other.nickname
            # Excluding rotation slot
        )

    @staticmethod
    def make_null():
        return TeamData.from_chron(
            {
                "id": None,
                "nickname": "Null Team",
                # Using [None] rather than [] means things like fielder selection
                # won't get an index error
                "lineup": [None],
                "rotation": [None],
            },
            "1970-01-01T00:00:00.000Z",
            None,
        )


TeamData.null = TeamData.make_null()


@dataclass
class StadiumData(DataClassJsonMixin):
    object_type: ClassVar[str] = "stadium"
    null: ClassVar["StadiumData"]
    id: Optional[str]
    last_update_time: str
    mods: Set[str]
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

    def print_mods(self) -> str:
        return list(set(self.mods))

    @classmethod
    def from_chron(cls, data, last_update_time: str, prev_stadium_data: Optional["StadiumData"]):
        stadium_data = StadiumData(
            id=data["id"],
            last_update_time=last_update_time,
            mods=set(data["mods"]),
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

        if prev_stadium_data is not None:
            if prev_stadium_data.is_cache_equivalent(stadium_data):
                stadium_data.last_update_time = prev_stadium_data.last_update_time

        return stadium_data

    def is_cache_equivalent(self, other: "StadiumData") -> bool:
        return (
            self.id == other.id
            and
            # Excluding last update time
            self.mods == other.mods
            and self.name == other.name
            and self.nickname == other.nickname
            and self.mysticism == other.mysticism
            and self.viscosity == other.viscosity
            and self.elongation == other.elongation
            and
            # Excluding filthiness
            self.obtuseness == other.obtuseness
            and self.forwardness == other.forwardness
            and self.grandiosity == other.grandiosity
            and self.ominousness == other.ominousness
            and self.fortification == other.fortification
            and self.inconvenience == other.inconvenience
            # Excluding hype
        )

    @staticmethod
    def make_null():
        return StadiumData(
            last_update_time="1970-01-01T00:00:00.000Z",
            id=None,
            mods=set(),
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


StadiumData.null = StadiumData.make_null()


@dataclass
class ItemData:
    id: Optional[str]
    name: str
    health: int
    durability: int
    # Some Items have None ratings (e.g. Lucky Air Bat)
    defense_rating: Optional[float]
    hitting_rating: Optional[float]
    pitching_rating: Optional[float]
    baserunning_rating: Optional[float]
    stats: dict

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
            stats=stats,
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
            stats={},
        )


@dataclass
class PlayerData(TeamOrPlayerMods):
    object_type: ClassVar[str] = "player"
    null: ClassVar["PlayerData"]
    id: Optional[str]
    last_update_time: str
    raw_name: str
    unscattered_name: Optional[str]
    data: Dict[str, Any]
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
    baseThirst: float
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
    items: List[ItemData]
    season_mod_sources: Dict[str, List[str]]
    # Old incinerations don't have a peanut allergy field
    peanut_allergy: Optional[bool]

    @classmethod
    def from_chron(cls, data: Dict[str, Any], last_update_time: str, prev_player_data: Optional["PlayerData"]):
        data_state = data.get("state", {})
        items = [ItemData.from_dict(item) for item in data.get("items") or []]
        player_data = PlayerData(
            id=data["id"],
            last_update_time=last_update_time,
            raw_name=data["name"],
            unscattered_name=data_state.get("unscatteredName"),
            data=data,
            items=items,
            blood=data.get("blood") or None,
            consecutive_hits=data.get("consecutiveHits") or 0,
            bat=data.get("bat") or None,
            soul=data.get("soul") or 0,
            eDensity=data.get("eDensity") or 0,
            season_mod_sources=data_state.get("seasModSources", {}),
            peanut_allergy=data.get("peanutAllergy"),
            **cls.mods_init_args(data),
            **cls.stats_init_args(data, items),
        )

        if prev_player_data is not None:
            if prev_player_data.is_cache_equivalent(player_data):
                player_data.last_update_time = prev_player_data.last_update_time

        return player_data

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

    def stats_with_items(self) -> Dict[str, float]:
        return self._get_stats_with_items(self.data, self.items)

    def is_cache_equivalent(self, other: "PlayerData") -> bool:
        return (
            self.id == other.id
            and
            # Excluding last update time
            self.raw_name == other.raw_name
            and self.unscattered_name == other.unscattered_name
            and
            # Excluding data
            self.buoyancy == other.buoyancy
            and self.divinity == other.divinity
            and self.martyrdom == other.martyrdom
            and self.moxie == other.moxie
            and self.musclitude == other.musclitude
            and self.patheticism == other.patheticism
            and self.thwackability == other.thwackability
            and self.tragicness == other.tragicness
            and self.ruthlessness == other.ruthlessness
            and self.overpowerment == other.overpowerment
            and self.unthwackability == other.unthwackability
            and self.shakespearianism == other.shakespearianism
            and self.suppression == other.suppression
            and self.coldness == other.coldness
            and self.baseThirst == other.baseThirst
            and self.continuation == other.continuation
            and self.ground_friction == other.ground_friction
            and self.indulgence == other.indulgence
            and self.laserlikeness == other.laserlikeness
            and self.anticapitalism == other.anticapitalism
            and self.chasiness == other.chasiness
            and self.omniscience == other.omniscience
            and self.tenaciousness == other.tenaciousness
            and self.watchfulness == other.watchfulness
            and self.pressurization == other.pressurization
            and self.cinnamon == other.cinnamon
            and self.blood == other.blood
            and
            # Excluding consecutive hits
            self.bat == other.bat
            and self.soul == other.soul
            and
            # Excluding eDensity
            self.items == other.items
            and self.season_mod_sources == other.season_mod_sources
            and self.peanut_allergy == other.peanut_allergy
        )

    @staticmethod
    def _get_stats_with_items(data: Dict[str, Any], items: List[ItemData]) -> Dict[str, float]:
        stats = {stat: data[stat] for stat in stat_indices}
        for item in items:
            # if item.health != 0:
            for stat, value in item.stats.items():
                if stat in ["patheticism", "tragicness"]:
                    # path increases from items seem to actually *decrease* path in the formulas (and the other way
                    # around for path decreases)... even though the star calculations on the site ding you for
                    # having an item that increases path! at least right now, through season 19.
                    # tragicness: also backwards
                    stats[stat] -= value
                elif stat not in ["buoyancy", "cinnamon", "pressurization"]:
                    stats[stat] += value
            # else:
            #     for stat, value in item.stats.items():
            #         # well aren't you special
            #         if stat == "thwackability":
            #             stats[stat] += value
        return stats

    def update_stats(self):
        stats = self.stats_with_items()

        self.buoyancy = stats["buoyancy"]
        self.divinity = stats["divinity"]
        self.martyrdom = stats["martyrdom"]
        self.moxie = stats["moxie"]
        self.musclitude = stats["musclitude"]
        self.patheticism = stats["patheticism"]
        self.thwackability = stats["thwackability"]
        self.tragicness = stats["tragicness"]
        self.ruthlessness = stats["ruthlessness"]
        self.overpowerment = stats["overpowerment"]
        self.unthwackability = stats["unthwackability"]
        self.shakespearianism = stats["shakespearianism"]
        self.suppression = stats["suppression"]
        self.coldness = stats["coldness"]
        self.baseThirst = stats["baseThirst"]
        self.continuation = stats["continuation"]
        self.ground_friction = stats["groundFriction"]
        self.indulgence = stats["indulgence"]
        self.laserlikeness = stats["laserlikeness"]
        self.anticapitalism = stats["anticapitalism"]
        self.chasiness = stats["chasiness"]
        self.omniscience = stats["omniscience"]
        self.tenaciousness = stats["tenaciousness"]
        self.watchfulness = stats["watchfulness"]
        self.pressurization = stats["pressurization"]
        self.cinnamon = stats.get("cinnamon") or 0

    @classmethod
    def stats_init_args(cls, data: Dict[str, Any], items: List[ItemData]) -> Dict[str, float]:
        stats = cls._get_stats_with_items(data, items)

        return dict(
            buoyancy=stats["buoyancy"],
            divinity=stats["divinity"],
            martyrdom=stats["martyrdom"],
            moxie=stats["moxie"],
            musclitude=stats["musclitude"],
            patheticism=stats["patheticism"],
            thwackability=stats["thwackability"],
            tragicness=stats["tragicness"],
            ruthlessness=stats["ruthlessness"],
            overpowerment=stats["overpowerment"],
            unthwackability=stats["unthwackability"],
            shakespearianism=stats["shakespearianism"],
            suppression=stats["suppression"],
            coldness=stats["coldness"],
            baseThirst=stats["baseThirst"],
            continuation=stats["continuation"],
            ground_friction=stats["groundFriction"],
            indulgence=stats["indulgence"],
            laserlikeness=stats["laserlikeness"],
            anticapitalism=stats["anticapitalism"],
            chasiness=stats["chasiness"],
            omniscience=stats["omniscience"],
            tenaciousness=stats["tenaciousness"],
            watchfulness=stats["watchfulness"],
            pressurization=stats["pressurization"],
            cinnamon=stats.get("cinnamon") or 0,
        )

    @staticmethod
    def make_null():
        return PlayerData.from_chron(
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
            "1970-01-01T00:00:00.000Z",
            None,
        )


PlayerData.null = PlayerData.make_null()

DataObject = Union[PlayerData, TeamData, StadiumData]

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
        self.teams = {
            e["entityId"]: TeamData.from_chron(e["data"], e["validFrom"], self.teams.get(e["entityId"]))
            for e in resp["items"]
        }

    def fetch_players(self, timestamp, delta_secs: float = 0):
        timestamp = offset_timestamp(timestamp, delta_secs)
        key = f"players_at_{timestamp}"
        resp = get_cached(
            key,
            f"{CHRONICLER_URI}/v2/entities?type=player&at={timestamp}&count=2000",
        )
        self.players = {
            e["entityId"]: PlayerData.from_chron(e["data"], e["validFrom"], self.players.get(e["entityId"]))
            for e in resp["items"]
        }

    def fetch_stadiums(self, timestamp, delta_secs: float = 0):
        timestamp = offset_timestamp(timestamp, delta_secs)
        key = f"stadiums_at_{timestamp}"
        resp = get_cached(
            key,
            f"{CHRONICLER_URI}/v2/entities?type=stadium&at={timestamp}&count=1000",
        )
        self.stadiums = {
            e["entityId"]: StadiumData.from_chron(e["data"], e["validFrom"], self.stadiums.get(e["entityId"]))
            for e in resp["items"]
        }

    def fetch_player_after(self, player_id, timestamp):
        key = f"player_{player_id}_after_{timestamp}"
        resp = get_cached(
            key,
            f"{CHRONICLER_URI}/v2/versions?type=player&id={player_id}&after={timestamp}&count=1&order=asc",
        )
        for item in resp["items"]:
            self.players[item["entityId"]] = PlayerData.from_chron(
                item["data"], item["validFrom"], self.players.get(item["entityId"])
            )

    def fetch_game(self, game_id):
        key = f"game_updates_{game_id}"
        resp = get_cached(
            key,
            f"{CHRONICLER_URI}/v1/games/updates?count=2000&game={game_id}&started=true",
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
        update = self.plays.get((game_id, play), NullUpdate())
        update["weather"] = Weather(update["weather"])
        return update

    def has_player(self, player_id) -> bool:
        return player_id in self.players

    def get_player(self, player_id) -> PlayerData:
        return self.players[player_id] if player_id else PlayerData.null

    def get_team(self, team_id) -> TeamData:
        return self.teams[team_id] if team_id else TeamData.null

    def get_stadium(self, stadium_id) -> StadiumData:
        return self.stadiums[stadium_id] if stadium_id else StadiumData.null
