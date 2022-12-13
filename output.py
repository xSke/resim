import dataclasses
import hashlib
import json
import os
from csv import DictWriter
from typing import Set, Dict

# https://stackoverflow.com/a/22281062
def set_to_list_default_fn(obj):
    if isinstance(obj, set):
        return list(obj)
    raise TypeError

class SaveCsv:
    def __init__(self, run_name: str, category_name: str, cached_objects: Set[str]):
        self.cached_objects = cached_objects
        self.final_filename = f"roll_data/{run_name}-{category_name}.csv"
        self.partial_filename = f"{self.final_filename}.partial"
        # Created when first row is written
        self.file = None
        self.csv = None

    def write(
            self,
            event_type: str,
            roll: float,
            passed: bool,
            update,
            baserunners_next,
            what1: float,
            what2: float,
            is_strike: bool,
            strike_roll: float,
            strike_threshold: float,
            fielder_roll,
            objects: Dict[str, dict],
    ):

        # fmt: off
        row = {
            "event_type": event_type,
            "roll": roll,
            "passed": passed,
            "what1": what1,
            "what2": what2,
            "batting_team_hype": objects['stadium'].hype if not update["topOfInning"] else 0,
            "pitching_team_hype": objects['stadium'].hype if update["topOfInning"] else 0,
            "game_id": update["id"],
            "stadium_id": update["stadiumId"],
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
            "batting_team_roster_size": len(objects['batting_team'].lineup) + len(objects['batting_team'].rotation),
            "pitching_team_roster_size": len(objects['pitching_team'].lineup) + len(objects['pitching_team'].rotation),
            "baserunner_count": update["baserunnerCount"],
            "baserunners": str(update["basesOccupied"]),
            "baserunners_next": str(baserunners_next),
            "is_strike": is_strike,
            "strike_roll": strike_roll,
            "strike_threshold": strike_threshold,
            "fielder_roll": fielder_roll,
        }

        # fmt: on
        for key, obj in objects.items():
            # Any object you want to save in a CSV must have a version_id function
            version_id = obj.id, obj.version_date
            row[key] = version_id
            if version_id not in self.cached_objects:
                filename = f"object_data/{obj.id}-{obj.version_date}.json"
                with open(filename, "w") as f:
                    json.dump(dataclasses.asdict(obj), f, default=set_to_list_default_fn)
                self.cached_objects.add(version_id)

        if self.csv is None:
            self.file = open(self.partial_filename, "w", newline="", encoding="utf-8")
            self.csv = DictWriter(self.file, fieldnames=list(row.keys()), extrasaction="ignore")
            self.csv.writeheader()

        self.csv.writerow(row)

        hasher = hashlib.md5()

    def close(self):
        if not self.file:
            return
        self.file.close()
        self.file = None
        self.csv = None

        os.replace(self.partial_filename, self.final_filename)
