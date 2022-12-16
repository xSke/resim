import json
from typing import Dict, Any, Set

import pandas as pd

from sin_values import SIN_PHASES

JsonDict = Dict[str, Any]
JsonDictMap = Dict[str, JsonDict]


def combine_mods(data: Dict[str, Any]) -> Set[str]:
    return set(data['permAttr'] + data['seasAttr'] + data['weekAttr'] + data['gameAttr'])


def extract(objects: JsonDictMap, attr_key: str, default=None):
    def attr_extractor(object_key: str):
        return objects[object_key][attr_key]

    def attr_extractor_with_default(object_key: str):
        return objects[object_key].get(attr_key, default)

    if default is not None:
        return attr_extractor
    else:
        return attr_extractor_with_default


def has_mod(objects: JsonDictMap, mod: str):
    def mod_extractor(object_key: str):
        return mod in objects[object_key]['mods']

    return mod_extractor
def get_vibe(objects: JsonDictMap):
    def vibe_extractor(row):
        object_key, day = row
        if "SCATTERED" in objects[object_key]['mods']:
            return 0

        frequency = 6 + round(10 * objects[object_key]["buoyancy"])

        # Pull from pre-computed sin values
        sin_phase = SIN_PHASES[frequency][day]
        # Original formula:
        # sin_phase = math.sin(math.pi * ((2 / frequency) * day + 0.5))

        pressurization = objects[object_key]["pressurization"]
        cinnamon = objects[object_key].get("cinnamon") or 0
        return 0.5 * ((sin_phase - 1) * pressurization + (sin_phase + 1) * cinnamon)

    return vibe_extractor


def get_sin_phase(row):
    frequency, day = row
    return SIN_PHASES[int(frequency)][int(day)]

class ObjectLoader:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.object_cache: Dict[str, JsonDictMap] = {}
        self.vibe_cache: Dict[str, pd.Series] = {}

    def __call__(self, object_key, attr_key, *, vibes=True, mods=True, items=True, ignore_broken=False, ):
        objects = self._get_cached(object_key)
        object_paths = self.df[object_key + "_path"]
        attr = object_paths.apply(extract(objects, attr_key))
        if vibes:
            if object_key in self.vibe_cache:
                vibe = self.vibe_cache[object_key]
            else:
                vibe = self.df[[object_key + "_path", "day"]].apply(get_vibe(objects), axis=1)
                self.vibe_cache[object_key] = vibe
            attr = attr * (1 + 0.2 * vibe)

        return attr

    def _get_cached(self, object_key: str) -> JsonDictMap:
        if object_key in self.object_cache:
            return self.object_cache[object_key]

        filenames = self.df[object_key + '_path'].unique()
        object_map: JsonDictMap = {}
        for filename in filenames:
            with open(f"../{filename}", "r") as f:
                object_map[filename] = json.load(f)
            object_map[filename]['mods'] = combine_mods(object_map[filename])

        self.object_cache[object_key] = object_map
        return object_map


def _test():
    import glob
    all_files = glob.glob("../roll_data/*-strikes.csv")

    df = pd.concat((pd.read_csv(f, dtype={"stadium_id": "string"}) for f in all_files), ignore_index=True)
    # df = df[df['season'] == 14]

    load = ObjectLoader(df)
    df["ruth_scaled"] = load('pitcher', 'ruthlessness')
    df["musc_scaled"] = load('batter', 'musclitude')

    pass


if __name__ == '__main__':
    _test()
