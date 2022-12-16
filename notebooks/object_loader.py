import json
from collections import defaultdict
from typing import Dict, Any, Set

import pandas as pd

import formulas
from data import PlayerData, TeamData, StadiumData, DataObject
from sin_values import SIN_PHASES

DataObjectMap = Dict[str, DataObject]


def combine_mods(data: Dict[str, Any]) -> Set[str]:
    return set(data['permAttr'] + data['seasAttr'] + data['weekAttr'] + data['gameAttr'])


def get_attribute(objects: DataObjectMap, attr_key: str, use_items: bool, use_broken_items: bool):
    def attribute_extractor(object_key: str):
        attr = objects[object_key].data[attr_key] or 0  # for cinnamon
        if use_items:
            for item in objects[object_key].items:
                if use_broken_items or item.health != 0:
                    attr += item.stats.get(attr_key, 0)

        return attr

    return attribute_extractor


def has_mod(objects: DataObjectMap, mod: str):
    def has_mod_extractor(object_key: str):
        return mod in objects[object_key].mods

    return has_mod_extractor


def get_vibe(objects: DataObjectMap):
    def vibe_extractor(row):
        object_key, day = row
        player = objects[object_key]
        if "SCATTERED" in player.mods:
            return 0

        frequency = 6 + round(10 * player.buoyancy)

        # Pull from pre-computed sin values
        sin_phase = SIN_PHASES[frequency][day]
        # Original formula:
        # sin_phase = math.sin(math.pi * ((2 / frequency) * day + 0.5))

        return 0.5 * ((sin_phase - 1) * player.pressurization + (sin_phase + 1) * player.cinnamon)

    return vibe_extractor


def get_multiplier(player_objects: DataObjectMap, team_objects: DataObjectMap, attr_key: str):
    def multiplier_extractor(row):
        player_key, team_key, *_ = row
        player, team = player_objects[player_key], team_objects[team_key]

        meta = formulas.StatRelevantData(
            weather=row["weather"],
            season=row["season"],
            day=row["day"],
            runner_count=row["runner_count"],
            top_of_inning=row["top_of_inning"],
            is_maximum_blaseball=row["is_maximum_blaseball"],
            batter_at_bats=row["batter_at_bats"],
        )

        return formulas.get_multiplier(player, team, player_key, attr_key, meta)

    return multiplier_extractor


def team_for_object(object_key: str) -> str:
    if object_key == "batter":
        return "batting_team"
    elif object_key == "pitcher":
        return "pitching_team"
    # TODO More of them
    raise ValueError(f"Object '{object_key}' does not have an associated team")


class ObjectLoader:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.object_cache: Dict[str, DataObjectMap] = {}
        self.vibe_cache: Dict[str, pd.Series] = {}
        self.multiplier_cache: Dict[str, Dict[str, pd.Series]] = defaultdict(lambda: {})

    def __call__(self, object_key, attr_key, *, vibes=True, mods=True, items=True, broken_items=False):
        objects = self._get_cached(object_key)
        object_paths = self.df[object_key + "_path"]
        attr = object_paths.apply(get_attribute(objects, attr_key, items, broken_items))
        if vibes:
            if object_key in self.vibe_cache:
                vibe = self.vibe_cache[object_key]
            else:
                vibe = self.df[[object_key + "_path", "day"]].apply(get_vibe(objects), axis=1)
                self.vibe_cache[object_key] = vibe
            attr = attr * (1 + 0.2 * vibe)

        if mods:
            if attr_key in self.multiplier_cache[object_key]:
                multiplier = self.multiplier_cache[object_key][attr_key]
            else:
                team_key = team_for_object(object_key)
                team_objects = self._get_cached(team_key)
                cols = [object_key + "_path", team_key + "_path", "weather", "season", "day", "runner_count",
                        "top_of_inning", "is_maximum_blaseball", "batter_at_bats"]
                multiplier = self.df[cols].apply(get_multiplier(objects, team_objects, attr_key), axis=1)
                self.multiplier_cache[object_key][attr_key] = multiplier
            attr = attr * multiplier

        return attr

    def _get_cached(self, object_key: str) -> DataObjectMap:
        if object_key in self.object_cache:
            return self.object_cache[object_key]

        filenames = self.df[object_key + '_path'].unique()
        object_map: DataObjectMap = {}
        for i, filename in enumerate(filenames):
            with open(f"../{filename}", "r") as f:
                obj = json.load(f)
            if obj["type"] == "player":
                object_map[filename] = PlayerData(obj["data"], obj["last_update_time"], None)
            elif obj["type"] == "team":
                object_map[filename] = TeamData(obj["data"], obj["last_update_time"], None)
            elif obj["type"] == "stadium":
                object_map[filename] = StadiumData.from_dict(obj["data"], obj["last_update_time"], None)
            else:
                raise ValueError(f"Cannot load object of unknown type '{obj['type']}'")

        self.object_cache[object_key] = object_map
        return object_map


def _test():
    import glob
    all_files = glob.glob("../roll_data/*-strikes.csv")
    print("Globbed files")

    df = pd.concat((pd.read_csv(f, dtype={"stadium_id": "string"}) for f in all_files), ignore_index=True)
    print("Loaded full dataframe")
    df = df[df['season'] == 17]
    print("Chopped dataframe")

    load = ObjectLoader(df)
    print("Made loader")
    df["ruth_scaled"] = load('pitcher', 'ruthlessness')
    print("Got ruth")
    df["musc_scaled"] = load('batter', 'musclitude', items=False)
    print("Got musc")

    pass


if __name__ == '__main__':
    _test()
