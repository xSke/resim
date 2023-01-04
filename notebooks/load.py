from glob import glob
import itertools
import json
from typing import Dict, Union, Iterable
from braceexpand import braceexpand

import pandas as pd
import sys

# I don't want this to be required, but I don't know how to make the import work otherwise
sys.path.append("../")

import formulas  # noqa: E402
from data import PlayerData, TeamData, StadiumData, DataObject, Weather  # noqa: E402
from sin_values import SIN_PHASES  # noqa: E402

DataObjectMap = Dict[str, DataObject]

PLAYER_OBJECTS = [
    "batter",
    "pitcher",
    "fielder",
    "relevant_runner",
    "runner_on_first",
    "runner_on_second",
    "runner_on_third",
    "runner_on_third_hh",
]
TEAM_OBJECTS = ["batting_team", "pitching_team"]
OTHER_OBJECTS = ["stadium"]
STAT_RELEVANT_DATA_KEYS = [
    "weather",
    "season",
    "day",
    "runner_count",
    "top_of_inning",
    "is_maximum_blaseball",
    "batter_at_bats",
]


def braced_glob(path):
    l = []
    for x in braceexpand(path):
        l.extend(glob(x))
            
    return l

def _get_player_attribute(attr_key: str, use_items: Union[bool, str], use_broken_items: bool):
    def player_attribute_extractor(player: PlayerData):
        attr = player.data.get(attr_key) or 0  # for cinnamon
        if use_items:
            for item in player.items:
                if use_broken_items or item.health != 0:
                    item_attr = item.stats.get(attr_key) or 0
                    if use_items == "negative":
                        attr -= item_attr
                    else:
                        attr += item_attr

        return attr

    return player_attribute_extractor


def _get_stadium_attribute(attr_key: str):
    def stadium_attribute_extractor(stadium: StadiumData):
        return getattr(stadium, attr_key)

    return stadium_attribute_extractor


def _get_vibes(row):
    player, day = row
    if "SCATTERED" in player.mods:
        return 0

    frequency = 6 + round(10 * player.buoyancy)

    # Pull from pre-computed sin values
    sin_phase = SIN_PHASES[frequency][day]
    # Original formula:
    # sin_phase = math.sin(math.pi * ((2 / frequency) * day + 0.5))

    return 0.5 * ((sin_phase - 1) * player.pressurization + (sin_phase + 1) * player.cinnamon)


def _get_mods(item: Union[PlayerData, TeamData]):
    return ";".join(item.mods)


def _get_multiplier(position, attr):
    def multiplier_extractor(row):
        player, team, meta = row
        return formulas.get_multiplier(player, team, position, attr, meta)

    return multiplier_extractor


def _get_stat_relevant_data(row):
    (weather, season, day, runner_count, top_of_inning, is_maximum_blaseball, batter_at_bats) = row
    return formulas.StatRelevantData(
        weather=Weather[weather.replace("Weather.", "")],
        season=season,
        day=day,
        runner_count=runner_count,
        top_of_inning=top_of_inning,
        is_maximum_blaseball=is_maximum_blaseball,
        batter_at_bats=batter_at_bats,
    )


def _team_for_object(object_key: str) -> str:
    if object_key == "batter":
        return "batting_team"
    elif object_key == "pitcher":
        return "pitching_team"
    # TODO More of them
    raise ValueError(f"Object '{object_key}' does not have an associated team")


def _load_objects(df: pd.DataFrame, object_key: str) -> DataObjectMap:
    filenames = df[object_key + "_file"].unique()
    object_map: DataObjectMap = {}
    for i, filename in enumerate(filenames):
        with open("../" + filename, "r") as f:
            obj = json.load(f)
        if obj["type"] == "player":
            object_map[filename] = PlayerData.from_json(obj["data"])
        elif obj["type"] == "team":
            object_map[filename] = TeamData.from_json(obj["data"])
        elif obj["type"] == "stadium":
            object_map[filename] = StadiumData.from_json(obj["data"])
        else:
            raise ValueError(f"Cannot load object of unknown type '{obj['type']}'")

    return object_map


def data(
    roll_type: str, season: Union[None, int, list[int]], roles: Iterable[str] = ("pitcher", "batter")
) -> pd.DataFrame:
    """
    Loads a dataframe with all the roll data for a particular type of roll
    :param roll_type: Type of roll. This is the thing that appears in the csv filenames, like "strikes" or "party"
    :param season: Which season to load. Can be an integer, list, or None, for one season, multiple seasons, or all
        seasons respectively
    :param roles: Which player roles to load. Valid values of this are listed in PLAYER_OBJECTS. Defaults to loading
        pitcher and batter
    :return: A populated dataframe
    """

    if season is None:
        season_str = ""
    elif isinstance(season, int):
        season_str = str(season)
    else:
        season_str = "{" + ",".join(str(s) for s in season) + "}"
    all_files = braced_glob(f"../roll_data/s{season_str}*-{roll_type}.csv")

    df = pd.concat((pd.read_csv(f, dtype={"stadium_id": "string"}) for f in all_files), ignore_index=True)

    df["stat_relevant_data"] = df[STAT_RELEVANT_DATA_KEYS].apply(_get_stat_relevant_data, axis=1)
    for object_key in itertools.chain(roles, TEAM_OBJECTS, OTHER_OBJECTS):
        objects = _load_objects(df, object_key)
        df[object_key + "_object"] = df[object_key + "_file"].apply(lambda k: objects[k])
    # df.drop(f"{label}_file" for label in OBJECTS)
    for player_key in roles:
        if player_key not in PLAYER_OBJECTS:
            raise ValueError(f"Unknown player key '{player_key}'")
        df[player_key + "_vibes"] = df[[player_key + "_object", "day"]].apply(_get_vibes, axis=1)
        df[player_key + "_mods"] = df[player_key + "_object"].apply(_get_mods)
        df[player_key + "_name"] = df[player_key + "_object"].apply(lambda obj: obj.name)
    for team_key in TEAM_OBJECTS:
        df[team_key + "_mods"] = df[team_key + "_object"].apply(_get_mods)
        df[team_key + "_name"] = df[team_key + "_object"].apply(lambda obj: obj.nickname)

    return df


def player_attribute(
    df: pd.DataFrame,
    object_key: str,
    attr_key: str,
    *,
    vibes: bool = True,
    mods: Union[bool, str] = True,
    items: Union[bool, str] = True,
    broken_items: bool = False,
):
    if not (items is True or items is False or items == "negative"):
        raise ValueError(
            f'Invalid value {items!r} for argument "items" passed to load.player_attribute. '
            'Valid values: True, False, "negative"'
        )
    if not (mods is True or mods is False or mods == "negative"):
        raise ValueError(
            f'Invalid value {mods!r} for argument "mods" passed to load.player_attribute. '
            'Valid values: True, False, "negative"'
        )

    attr = df[object_key + "_object"].apply(_get_player_attribute(attr_key, items, broken_items))
    attr_raw = df[object_key + "_object"].apply(_get_player_attribute(attr_key, False, False))
    attr_item = attr - attr_raw
    # print(attr_item)
    if vibes:
        vibe = df[object_key + "_vibes"]
        attr_raw = attr_raw * (1 + 0.2 * vibe)
        attr_item = attr_item * (1 + 0.2 * vibe)

    if mods:
        if mods == "negative":
            cols = [object_key + "_object", _team_for_object(object_key) + "_object", "stat_relevant_data"]
            multiplier = df[cols].apply(_get_multiplier(object_key, attr_key), axis=1)
            # attr = attr_raw * multiplier + attr_item * multiplier
            broken_item = df[object_key + "_object"].apply(lambda obj: any(item.health == 0 for item in obj.items))
            attr = attr_raw / multiplier + attr_item * (~broken_item * multiplier + broken_item)
        else:
            cols = [object_key + "_object", _team_for_object(object_key) + "_object", "stat_relevant_data"]
            multiplier = df[cols].apply(_get_multiplier(object_key, attr_key), axis=1)
            # attr = attr_raw * multiplier + attr_item * multiplier
            broken_item = df[object_key + "_object"].apply(lambda obj: any(item.health == 0 for item in obj.items))
            attr = attr_raw * multiplier + attr_item * (~broken_item * multiplier + broken_item)

    return attr


def stadium_attribute(df: pd.DataFrame, attr_key: str, *, center: bool = True):
    return df["stadium_object"].apply(_get_stadium_attribute(attr_key)) - 0.5 * center
