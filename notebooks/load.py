from glob import glob
import itertools
import json
from typing import Dict, Union, Iterable
from braceexpand import braceexpand

import pandas as pd
import numpy as np
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
    paths = []
    for x in braceexpand(path):
        paths.extend(glob(x))

    return paths


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
    if player.has_mod("SCATTERED"):
        return 0

    # must be pre-item
    buoy = _get_player_attribute("buoyancy", False, False)(player)
    press = _get_player_attribute("pressurization", False, False)(player)
    cinn = _get_player_attribute("cinnamon", False, False)(player)

    frequency = 6 + round(10 * buoy)

    # Pull from pre-computed sin values
    sin_phase = SIN_PHASES[frequency][day]
    # Original formula:
    # sin_phase = math.sin(math.pi * ((2 / frequency) * day + 0.5))

    return 0.5 * ((sin_phase - 1) * press + (sin_phase + 1) * cinn)


def _get_mods(item: Union[PlayerData, TeamData]):
    return ";".join(item.mods)


def _get_multiplier(position, attr):
    def multiplier_extractor(row):
        player, team, meta, stadium = row
        return formulas.get_multiplier(player, team, position, attr, meta, stadium)

    return multiplier_extractor


def _get_stat_relevant_data(row):
    (weather, season, day, runner_count, top_of_inning, is_maximum_blaseball, batter_at_bats) = row
    if isinstance(weather, int):
        weather = Weather(weather)
    else:
        weather = Weather[weather.replace("Weather.", "")]
    return formulas.StatRelevantData(
        weather=weather,
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
    elif object_key == "fielder":
        return "pitching_team"
    elif object_key == "relevant_runner":
        return "batting_team"
    elif object_key == "runner_on_first":
        return "batting_team"
    elif object_key == "runner_on_second":
        return "batting_team"
    elif object_key == "runner_on_third":
        return "batting_team"
    elif object_key == "runner_on_third_hh":
        return "batting_team"
    raise ValueError(f"Object '{object_key}' does not have an associated team")


NULL_OBJECTS = (
    {k: PlayerData.make_null() for k in PLAYER_OBJECTS}
    | {k: TeamData.make_null() for k in TEAM_OBJECTS}
    | {
        "stadium": StadiumData.make_null(),
    }
)


def _load_objects(df: pd.DataFrame, object_key: str) -> DataObjectMap:
    filenames = df[object_key + "_file"].dropna().unique()
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

    object_map[np.nan] = NULL_OBJECTS[object_key]
    object_map[pd.NA] = NULL_OBJECTS[object_key]

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

    df = pd.concat(
        (pd.read_csv(f, dtype={"stadium_id": "string", "is_strike": "boolean", "stadium_file": "string"}) for f in all_files), ignore_index=True
    )
    
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
    invert: bool = False,
    broken_items: bool = False,
    override_mod_team: str = None,
    hype_coef: float = 0,
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

    attr = df[object_key + "_object"].apply(_get_player_attribute(attr_key, items, True))
    attr_without_broken_items = df[object_key + "_object"].apply(_get_player_attribute(attr_key, items, False))
    attr_raw = df[object_key + "_object"].apply(_get_player_attribute(attr_key, False, False))

    attr_broken_items = attr - attr_without_broken_items
    attr_unbroken_items = (attr - attr_raw) - attr_broken_items

    if mods:
        if mods == "negative":
            cols = [
                object_key + "_object",
                _team_for_object(object_key) + "_object",
                "stat_relevant_data",
                "stadium_object",
            ]
            multiplier = df[cols].apply(_get_multiplier(object_key, attr_key), axis=1)

            attr = attr_raw / multiplier
        else:
            # todo: hardcoding this sucks but i can't think of a cleaner way to express this. it's real bad
            if attr_key != "suppression":
                cols = [
                    object_key + "_object",
                    override_mod_team or _team_for_object(object_key) + "_object",
                    "stat_relevant_data",
                    "stadium_object",
                ]
                multiplier = df[cols].apply(_get_multiplier(override_mod_team or object_key, attr_key), axis=1)
            else:
                cols = [object_key + "_object", "pitching_team" + "_object", "stat_relevant_data", "stadium_object"]
                multiplier = df[cols].apply(_get_multiplier("pitcher", attr_key), axis=1)

            attr = attr_raw * multiplier

    if items:
        attr += attr_unbroken_items  # *multiplier
    if broken_items:
        attr += attr_broken_items  # *multiplier

    hype = df["pitching_team_hype"] - df["batting_team_hype"]
    attr += hype * hype_coef

    if invert:
        attr = 1 - attr

    if vibes:
        vibe = df[object_key + "_vibes"]
        attr = attr * (1 + 0.2 * vibe)

    return attr


def player_attribute_group(
    df: pd.DataFrame,
    object_key: str,
    attr_group: Union[str, list[str]],
    *,
    vibes: bool = True,
    mods: bool = True,
    items: Union[bool, str] = True,
    broken_items: bool = False,
):
    if not (items is True or items is False or items == "negative"):
        raise ValueError(
            f'Invalid value {items!r} for argument "items" passed to load.player_attribute. '
            'Valid values: True, False, "negative"'
        )

    attr_keys = []
    if attr_group == "all":
        attr_group = ["batting", "pitching", "baserunning", "fielding", "other"]
    if "batting" in attr_group:
        attr_keys.extend(["divinity", "martyrdom", "moxie", "musclitude", "patheticism", "thwackability", "tragicness"])
    if "pitching" in attr_group:
        attr_keys.extend(
            ["ruthlessness", "overpowerment", "unthwackability", "shakespearianism", "suppression", "coldness"]
        )
    if "baserunning" in attr_group:
        attr_keys.extend(["basethirst", "laserlikeness", "continuation", "groundfriction", "indulgence"])
    if "fielding" in attr_group:
        attr_keys.extend(["anticapitalism", "chasiness", "omniscience", "tenaciousness", "watchfulness"])
    if "other" in attr_group:
        attr_keys.extend(["buoyancy", "cinnamon", "pressurization"])

    for attr_key in attr_keys:
        attr = player_attribute(
            df, object_key, attr_key, vibes=vibes, mods=mods, items=items, broken_items=broken_items
        )

        attr_name = object_key + "_" + attr_key
        if vibes:
            attr_name += "_vibes"
        if not mods:
            attr_name += "_nomods"
        if not items:
            attr_name += "_noitems"
        if broken_items:
            attr_name += "_wbroken"

        df[attr_name] = attr

    return


def stadium_attribute(df: pd.DataFrame, attr_key: str, *, center: bool = True):
    return df["stadium_object"].apply(_get_stadium_attribute(attr_key)) - 0.5 * center


def stadium_attribute_all(df: pd.DataFrame, *, center: bool = True):
    attr_keys = [
        "grandiosity",
        "fortification",
        "obtuseness",
        "ominousness",
        "inconvenience",
        "viscosity",
        "forwardness",
        "mysticism",
        "elongation",
        "filthiness",
        "hype",
    ]
    for attr_key in attr_keys:
        attr_name = "ballpark_" + attr_key
        df[attr_name] = stadium_attribute(df, attr_key, center=center)
    return
