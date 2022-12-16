import json
import os
from csv import DictWriter
from typing import Dict, Union, Tuple

from data import DataObject, cacheable, UNCACHEABLE_PLAYER_KEYS


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

        self.n_saved = 0
        self.n_referenced = 0

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
        save_objects: Dict[str, DataObject],
    ):
        # fmt: off
        row = {
            "event_type": event_type,
            "roll": roll,
            "passed": passed,
            "what1": what1,
            "what2": what2,
            "batting_team_hype": save_objects['stadium'].hype if not update["topOfInning"] else 0,
            "pitching_team_hype": save_objects['stadium'].hype if update["topOfInning"] else 0,
            "game_id": update["id"],
            "play_count": update["playCount"],
            "weather": update["weather"],
            "ball_count": update["atBatBalls"],
            "strike_count": update["atBatStrikes"],
            "out_count": update["halfInningOuts"],
            "season": update["season"],
            "day": update["day"],
            "top_of_inning": update["topOfInning"],
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
        }
        # fmt: on

        for save_key, obj in save_objects.items():
            self.n_referenced += 1
            file_path = f"{self.object_dir}/{obj.id}-{obj.last_update_time}.json"
            if (
                obj.id not in self.last_saved_object
                or self.last_saved_object[obj.id].last_update_time != obj.last_update_time
            ):
                self.n_saved += 1
                to_save = cacheable(obj.data, UNCACHEABLE_PLAYER_KEYS)
                with open(file_path, "w") as f:
                    json.dump(to_save, f)
                self.last_saved_object[obj.id] = obj
            row[save_key + "_path"] = file_path

        if self.csv is None:
            self.file = open(self.partial_filename, "w", newline="", encoding="utf-8")
            self.csv = DictWriter(self.file, fieldnames=list(row.keys()), extrasaction="ignore")
            self.csv.writeheader()

        self.csv.writerow(row)

    def close(self):
        if self.n_referenced > 0:
            print(f"This csv saved objects {100 * self.n_saved/self.n_referenced}% of the time")
        if not self.file:
            return
        self.file.close()
        self.file = None
        self.csv = None

        os.replace(self.partial_filename, self.final_filename)
