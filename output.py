import json
import os
from csv import DictWriter
from typing import Dict

from data import DataObject
from formulas import StatRelevantData


class SaveCsv:
    def __init__(self, run_name: str, category_name: str, last_saved_update: Dict[str, str]):
        self.object_dir = f"object_data/{run_name}"
        os.makedirs(self.object_dir, exist_ok=True)
        self.final_filename = f"roll_data/{run_name}-{category_name}.csv"
        self.partial_filename = f"{self.final_filename}.partial"
        # Created when first row is written
        self.file = None
        self.csv = None
        self.last_saved_object = last_saved_update

    def write(
        self,
        event_type: str,
        roll: float,
        passed: bool,
        update,
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
            # S20 (1-based) spends a ridiculous amount of time repeatedly
            # converting NullPlayer to JSON without this check.
            # I think it's because of KLoNGs whose stats aren't available yet.
            if obj.id == None and obj.last_update_time == "1970-01-01T00:00:00.000Z":
                continue
            file_path = f"{self.object_dir}/{obj.id}-{obj.last_update_time}.json".replace(":", "_")
            if obj.id not in self.last_saved_object or self.last_saved_object[obj.id] != obj.last_update_time:
                to_save = {
                    "type": obj.object_type,
                    "last_update_time": obj.last_update_time,
                    # yes, there's JSON in the JSON. yo dawg
                    "data": obj.to_json(),
                }
                with open(file_path, "w") as f:
                    json.dump(to_save, f)
                self.last_saved_object[obj.id] = obj.last_update_time
            row[save_key + "_file"] = file_path

        if self.csv is None:
            # for the first row we need this defined, otherwise areas where only some stadiums exist (~s13) will break
            if "stadium_file" not in row:
                row["stadium_file"] = None

            self.file = open(self.partial_filename, "w", newline="", encoding="utf-8")
            self.csv = DictWriter(self.file, fieldnames=list(row.keys()), extrasaction="ignore")
            self.csv.writeheader()

        self.csv.writerow(row)

    def writeItem(
        self, element: str, roll: float, season: int, day: int, roll_type: str, category: str, prefix_index: int = -1
    ):
        row = {
            "season": season,
            "day": day,
            "roll_type": roll_type,
            "category": category,
            "element": element,
            "roll": roll,
            "prefix_index": prefix_index,
        }

        if self.csv is None:
            self.file = open(self.partial_filename, "w", newline="", encoding="utf-8")
            self.csv = DictWriter(self.file, fieldnames=list(row.keys()), extrasaction="ignore")
            self.csv.writeheader()

        self.csv.writerow(row)

    def close(self):
        if not self.file:
            return
        self.file.close()
        self.file = None
        self.csv = None

        os.replace(self.partial_filename, self.final_filename)
