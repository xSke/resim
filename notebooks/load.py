import glob
import json
from typing import Dict, Union

import pandas as pd
import sys

# I don't want this to be required, but I don't know how to make the import work otherwise
sys.path.append('../')

import formulas
from data import PlayerData, TeamData, StadiumData, DataObject, EXCLUDE_FROM_CACHE
from sin_values import SIN_PHASES

DataObjectMap = Dict[str, DataObject]

PLAYER_OBJECTS = ['batter', 'pitcher', 'fielder', 'relevant_runner', 'runner_on_first', 'runner_on_second',
                  'runner_on_third', 'runner_on_third_hh']
TEAM_OBJECTS = ['batting_team', 'pitching_team']
OBJECTS = [*PLAYER_OBJECTS, *TEAM_OBJECTS, 'stadium']


def _get_player_attribute(attr_key: str, use_items: bool, use_broken_items: bool):
    def player_attribute_extractor(player: PlayerData):
        attr = player.data.get(attr_key) or 0  # for cinnamon
        if use_items:
            for item in player.items:
                if use_broken_items or item.health != 0:
                    attr += item.stats.get(attr_key) or 0

        return attr

    return player_attribute_extractor

def _get_stadium_attribute(attr_key: str):
    def stadium_attribute_extractor(stadium: StadiumData):
        return stadium.data.get(attr_key)

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


def _get_multiplier(attr_key: str, player_key: str, team_key: str):
    def multiplier_extractor(row):
        return formulas.get_multiplier(row[player_key + "_object"], row[team_key + "_object"], player_key, attr_key,
                                       row['stat_relevant_data'])

    return multiplier_extractor


def _get_stat_relevant_data(row):
    return formulas.StatRelevantData(
        weather=row["weather"],
        season=row["season"],
        day=row["day"],
        runner_count=row["runner_count"],
        top_of_inning=row["top_of_inning"],
        is_maximum_blaseball=row["is_maximum_blaseball"],
        batter_at_bats=row["batter_at_bats"],
    )


def _team_for_object(object_key: str) -> str:
    if object_key == "batter":
        return "batting_team"
    elif object_key == "pitcher":
        return "pitching_team"
    # TODO More of them
    raise ValueError(f"Object '{object_key}' does not have an associated team")


def _load_objects(df: pd.DataFrame, object_key: str) -> DataObjectMap:
    filenames = df[object_key + '_file'].unique()
    object_map: DataObjectMap = {}
    for i, filename in enumerate(filenames):
        with open("../" + filename, "r") as f:
            obj = json.load(f)
        # Fill in the data that's excluded from cache with dummy data to prevent key errors
        for key in EXCLUDE_FROM_CACHE[obj["type"]]:
            obj["data"][key] = None
        if obj["type"] == "player":
            object_map[filename] = PlayerData(obj["data"], obj["last_update_time"], None)
        elif obj["type"] == "team":
            object_map[filename] = TeamData(obj["data"], obj["last_update_time"], None)
        elif obj["type"] == "stadium":
            object_map[filename] = StadiumData.from_dict(obj["data"], obj["last_update_time"], None)
        else:
            raise ValueError(f"Cannot load object of unknown type '{obj['type']}'")

    return object_map


def data(roll_type: str, season: Union[None, int, list[int]]) -> pd.DataFrame:
    if season is None:
        season_str = ""
    elif isinstance(season, int):
        season_str = str(season)
    else:
        season_str = "{" + ",".join(str(s) for s in season) + "}"
    all_files = glob.glob(f"../roll_data/s{season}*-{roll_type}.csv")

    df = pd.concat((pd.read_csv(f, dtype={"stadium_id": "string"}) for f in all_files), ignore_index=True)

    df["stat_relevant_data"] = df.apply(_get_stat_relevant_data, axis=1)
    for object_key in OBJECTS:
        objects = _load_objects(df, object_key)
        df[object_key + "_object"] = df[object_key + "_file"].apply(lambda k: objects[k])
    # df.drop(f"{label}_file" for label in OBJECTS)
    for player_key in PLAYER_OBJECTS:
        df[player_key + "_vibes"] = df[[player_key + "_object", "day"]].apply(_get_vibes, axis=1)
        df[player_key + "_mods"] = df[player_key + "_object"].apply(_get_mods)
    for team_key in TEAM_OBJECTS:
        df[team_key + "_mods"] = df[team_key + "_object"].apply(_get_mods)

    return df


def player_attribute(df: pd.DataFrame, object_key: str, attr_key: str, *,
                     vibes: bool = True, mods: bool = True, items: bool = True, broken_items: bool = False):
    attr = df[object_key + "_object"].apply(_get_player_attribute(attr_key, items, broken_items))
    if vibes:
        vibe = df[object_key + "_vibes"]
        attr = attr * (1 + 0.2 * vibe)

    if mods:
        multiplier = df.apply(_get_multiplier(attr_key, object_key, _team_for_object(object_key)), axis=1)
        attr = attr * multiplier

    return attr


def stadium_attribute(df: pd.DataFrame, attr_key: str, *, center: bool = True):
    return df["stadium_object"].apply(_get_stadium_attribute(attr_key)) - 0.5 * center
