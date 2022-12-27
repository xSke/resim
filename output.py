import copy
import json
import os
from csv import DictWriter
from typing import Dict

import pandas as pd

from data import DataObject, cacheable, PlayerData
from formulas import StatRelevantData


class SaveCsv:
    def __init__(self, run_name: str, category_name: str, last_saved_update: Dict[str, DataObject]):
        self.object_dir = f"object_data/{run_name}"
        os.makedirs(self.object_dir, exist_ok=True)
        self.final_filename = f"roll_data/{run_name}-{category_name}.csv"
        self.partial_filename = f"{self.final_filename}.partial"
        # Created when first row is written
        self.file = None
        self.csv = None
        self.last_saved_object = last_saved_update
        self.last_saved_object_mods = {}
        try:
            (_, old_run_name) = run_name.split("-", maxsplit=1)
            self.reference_csv = pd.read_csv(f"roll_data_reference/{old_run_name}-{category_name}.csv")
        except FileNotFoundError:
            self.reference_csv = None
        self.i = 0

    def write(
            self,
            event_type: str,
            roll: float,
            passed: bool,
            update,
            what1: float,
            what2: float,
            is_strike: bool,
            strike_roll: float,
            strike_threshold: float,
            fielder_roll,
            baserunners_next,
            meta: StatRelevantData,
            save_objects: Dict[str, DataObject],
            event_time,
    ):
        # fmt: off
        row = {
            "event_type": event_type,
            "event_time": event_time,
            "roll": roll,
            "passed": passed,
            "what1": what1,
            "what2": what2,
            "batting_team_hype": save_objects['stadium'].hype if not update["topOfInning"] else 0,
            "pitching_team_hype": save_objects['stadium'].hype if update["topOfInning"] else 0,
            "game_id": update["id"],
            "play_count": update["playCount"],
            "ball_count": update["atBatBalls"],
            "strike_count": update["atBatStrikes"],
            "out_count": update["halfInningOuts"],
            "home_score": update["homeScore"],
            "away_score": update["awayScore"],
            "inning": update["inning"],
            "baserunner_count": update["baserunnerCount"],
            "baserunners": str(update["basesOccupied"]),
            "baserunners_next": str(baserunners_next),
            "is_strike": is_strike,
            "strike_roll": strike_roll,
            "strike_threshold": strike_threshold,
            "fielder_roll": fielder_roll,
            "batter_consecutive_hits": save_objects['batter'].consecutive_hits,
            "weather": meta.weather,
            "season": meta.season,
            "day": meta.day,
            "runner_count": meta.runner_count,
            "top_of_inning": meta.top_of_inning,
            "is_maximum_blaseball": meta.is_maximum_blaseball,
            "batter_at_bats": meta.batter_at_bats,
        }
        # fmt: on

        for save_key, obj in save_objects.items():
            saved_new_json = False
            if obj.id in self.last_saved_object:
                prev_last_saved_object_mods = ";".join(self.last_saved_object[obj.id].mods)
            else:
                prev_last_saved_object_mods = None
            file_path = f"{self.object_dir}/{obj.id}-{obj.last_update_time}.json".replace(":", "_")
            if (
                    obj.id not in self.last_saved_object
                    or self.last_saved_object[obj.id].last_update_time != obj.last_update_time
            ):
                to_save = {
                    "type": obj.object_type,
                    "last_update_time": obj.last_update_time,
                    # yes, there's JSON in the JSON. yo dawg
                    "data": obj.to_json(),
                }
                with open(file_path, "w") as f:
                    json.dump(to_save, f)
                saved_new_json = True
                self.last_saved_object[obj.id] = copy.deepcopy(obj)
                self.last_saved_object_mods[obj.id] = ";".join(obj.mods)
            row[save_key + "_file"] = file_path

            if save_key == "pitcher" and self.reference_csv is not None and self.final_filename.endswith("-strikes.csv"):

                # Read it right back again to check
                with open(file_path, "r") as f:
                    saved = json.load(f)

                saved_player = PlayerData.from_json(saved["data"])

                # Make sure we got the right row
                if abs(self.reference_csv.loc[self.i, "roll"] - roll) < 1e-12:
                    # print("Right roll")
                    reference_mods = self.reference_csv.loc[self.i, "pitcher_mods"]
                    if pd.isna(reference_mods):
                        assert not obj.mods  # assert that it's empty
                    else:
                        assert set(reference_mods.split(";")) == saved_player.mods
                else:
                    print("WRONG ROLL", abs(self.reference_csv.loc[self.i, "roll"] - roll))
                # print("WRONG ROLL", event_time, self.final_filename)

        if self.csv is None:
            self.file = open(self.partial_filename, "w", newline="", encoding="utf-8")
            self.csv = DictWriter(self.file, fieldnames=list(row.keys()), extrasaction="ignore")
            self.csv.writeheader()

        self.csv.writerow(row)
        self.i += 1

    def close(self):
        if not self.file:
            return
        self.file.close()
        self.file = None
        self.csv = None

        os.replace(self.partial_filename, self.final_filename)
