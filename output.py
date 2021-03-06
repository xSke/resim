import csv
import os
from data import calculate_vibes


class SaveCsv:
    def __init__(self, run_name: str, category_name: str):
        self.final_filename = f"roll_data/{run_name}-{category_name}.csv"
        self.partial_filename = f"{self.final_filename}.partial"
        self.file = open(self.partial_filename, "w", newline="", encoding="utf-8")

        self.csv = csv.writer(self.file)

        # Write header
        columns = [
            "event_type",
            "roll",
            "passed",
            "batter_buoyancy",
            "batter_divinity",
            "batter_martyrdom",
            "batter_moxie",
            "batter_musclitude",
            "batter_patheticism",
            "batter_thwackability",
            "batter_tragicness",
            "batter_coldness",
            "batter_overpowerment",
            "batter_ruthlessness",
            "batter_shakespearianism",
            "batter_suppression",
            "batter_unthwackability",
            "batter_base_thirst",
            "batter_continuation",
            "batter_ground_friction",
            "batter_indulgence",
            "batter_laserlikeness",
            "batter_anticapitalism",
            "batter_chasiness",
            "batter_omniscience",
            "batter_tenaciousness",
            "batter_watchfulness",
            "batter_pressurization",
            "batter_cinnamon",
            "batter_multiplier",
            "runner_on_first_base_thirst",
            "runner_on_first_continuation",
            "runner_on_first_ground_friction",
            "runner_on_first_indulgence",
            "runner_on_first_laserlikeness",
            "runner_on_first_multiplier",
            "runner_on_second_base_thirst",
            "runner_on_second_continuation",
            "runner_on_second_ground_friction",
            "runner_on_second_indulgence",
            "runner_on_second_laserlikeness",
            "runner_on_second_multiplier",
            "runner_on_third_base_thirst",
            "runner_on_third_continuation",
            "runner_on_third_ground_friction",
            "runner_on_third_indulgence",
            "runner_on_third_laserlikeness",
            "runner_on_third_multiplier",
            "pitcher_buoyancy",
            "pitcher_divinity",
            "pitcher_martyrdom",
            "pitcher_moxie",
            "pitcher_musclitude",
            "pitcher_patheticism",
            "pitcher_thwackability",
            "pitcher_tragicness",
            "pitcher_ruthlessness",
            "pitcher_overpowerment",
            "pitcher_unthwackability",
            "pitcher_shakespearianism",
            "pitcher_suppression",
            "pitcher_coldness",
            "pitcher_base_thirst",
            "pitcher_continuation",
            "pitcher_ground_friction",
            "pitcher_indulgence",
            "pitcher_laserlikeness",
            "pitcher_anticapitalism",
            "pitcher_chasiness",
            "pitcher_omniscience",
            "pitcher_tenaciousness",
            "pitcher_watchfulness",
            "pitcher_pressurization",
            "pitcher_cinnamon",
            "pitcher_multiplier",
            "fielder_anticapitalism",
            "fielder_chasiness",
            "fielder_omniscience",
            "fielder_tenaciousness",
            "fielder_watchfulness",
            "fielder_multiplier",
            "ballpark_grandiosity",
            "ballpark_fortification",
            "ballpark_obtuseness",
            "ballpark_ominousness",
            "ballpark_inconvenience",
            "ballpark_viscosity",
            "ballpark_forwardness",
            "ballpark_mysticism",
            "ballpark_elongation",
            "ballpark_filthiness",
            "what1",
            "what2",
            "batting_team_hype",
            "pitching_team_hype",
            "batter_name",
            "pitcher_name",
            "fielder_name",
            "runner_on_first_name",
            "runner_on_second_name",
            "runner_on_third_name",
            "batter_vibes",
            "pitcher_vibes",
            "fielder_vibes",
            "runner_on_first_vibes",
            "runner_on_second_vibes",
            "runner_on_third_vibes",
            "batter_mods",
            "batting_team_mods",
            "pitcher_mods",
            "pitching_team_mods",
            "fielder_mods",
            "runner_on_first_mods",
            "runner_on_second_mods",
            "runner_on_third_mods",
            "game_id",
            "stadium_id",
            "play_count",
            "weather",
            "ball_count",
            "strike_count",
            "out_count",
            "season",
            "day",
            "top_of_inning",
            "home_score",
            "away_score",
            "inning",
            "batting_team_roster_size",
            "pitching_team_roster_size",
            "baserunner_count",
            "is_strike",
            "strike_roll",
            "strike_threshold",
            "fielder_roll",
            "batter_consecutive_hits",
        ]
        self.num_columns = len(columns)
        self.csv.writerow(columns)

    def write(
        self,
        event_type: str,
        roll: float,
        passed: bool,
        batter,
        batting_team,
        pitcher,
        pitching_team,
        stadium,
        update,
        what1: float,
        what2: float,
        batter_multiplier: float,
        pitcher_multiplier: float,
        is_strike: bool,
        strike_roll: float,
        strike_threshold: float,
        fielder_roll,
        fielder,
        fielder_multiplier,
        runner_on_first,
        runner_on_first_multiplier,
        runner_on_second,
        runner_on_second_multiplier,
        runner_on_third,
        runner_on_third_multiplier,
    ):
        row = [
            event_type,
            roll,
            passed,
            batter.data["buoyancy"],
            batter.data["divinity"],
            batter.data["martyrdom"],
            batter.data["moxie"],
            batter.data["musclitude"],
            batter.data["patheticism"],
            batter.data["thwackability"],
            batter.data["tragicness"],
            batter.data["coldness"],
            batter.data["overpowerment"],
            batter.data["ruthlessness"],
            batter.data["shakespearianism"],
            batter.data["suppression"],
            batter.data["unthwackability"],
            batter.data["baseThirst"],
            batter.data["continuation"],
            batter.data["groundFriction"],
            batter.data["indulgence"],
            batter.data["laserlikeness"],
            batter.data["anticapitalism"],
            batter.data["chasiness"],
            batter.data["omniscience"],
            batter.data["tenaciousness"],
            batter.data["watchfulness"],
            batter.data["pressurization"],
            batter.data.get("cinnamon", 0),
            batter_multiplier,
            runner_on_first.data["baseThirst"] if runner_on_first is not None else 0,
            runner_on_first.data["continuation"] if runner_on_first is not None else 0,
            runner_on_first.data["groundFriction"] if runner_on_first is not None else 0,
            runner_on_first.data["indulgence"] if runner_on_first is not None else 0,
            runner_on_first.data["laserlikeness"] if runner_on_first is not None else 0,
            runner_on_first_multiplier,
            runner_on_second.data["baseThirst"] if runner_on_second is not None else 0,
            runner_on_second.data["continuation"] if runner_on_second is not None else 0,
            runner_on_second.data["groundFriction"] if runner_on_second is not None else 0,
            runner_on_second.data["indulgence"] if runner_on_second is not None else 0,
            runner_on_second.data["laserlikeness"] if runner_on_second is not None else 0,
            runner_on_second_multiplier,
            runner_on_third.data["baseThirst"] if runner_on_third is not None else 0,
            runner_on_third.data["continuation"] if runner_on_third is not None else 0,
            runner_on_third.data["groundFriction"] if runner_on_third is not None else 0,
            runner_on_third.data["indulgence"] if runner_on_third is not None else 0,
            runner_on_third.data["laserlikeness"] if runner_on_third is not None else 0,
            runner_on_third_multiplier,
            pitcher.data["buoyancy"],
            pitcher.data["divinity"],
            pitcher.data["martyrdom"],
            pitcher.data["moxie"],
            pitcher.data["musclitude"],
            pitcher.data["patheticism"],
            pitcher.data["thwackability"],
            pitcher.data["tragicness"],
            pitcher.data["ruthlessness"],
            pitcher.data["overpowerment"],
            pitcher.data["unthwackability"],
            pitcher.data["shakespearianism"],
            pitcher.data["suppression"],
            pitcher.data["coldness"],
            pitcher.data["baseThirst"],
            pitcher.data["continuation"],
            pitcher.data["groundFriction"],
            pitcher.data["indulgence"],
            pitcher.data["laserlikeness"],
            pitcher.data["anticapitalism"],
            pitcher.data["chasiness"],
            pitcher.data["omniscience"],
            pitcher.data["tenaciousness"],
            pitcher.data["watchfulness"],
            pitcher.data["pressurization"],
            pitcher.data["cinnamon"],
            pitcher_multiplier,
            fielder.data["anticapitalism"] if fielder is not None else 0,
            fielder.data["chasiness"] if fielder is not None else 0,
            fielder.data["omniscience"] if fielder is not None else 0,
            fielder.data["tenaciousness"] if fielder is not None else 0,
            fielder.data["watchfulness"] if fielder is not None else 0,
            fielder_multiplier,
            stadium.data["grandiosity"],
            stadium.data["fortification"],
            stadium.data["obtuseness"],
            stadium.data["ominousness"],
            stadium.data["inconvenience"],
            stadium.data["viscosity"],
            stadium.data["forwardness"],
            stadium.data["mysticism"],
            stadium.data["elongation"],
            stadium.data["filthiness"],
            what1,
            what2,
            stadium.data["hype"] if not update["topOfInning"] else 0,
            stadium.data["hype"] if update["topOfInning"] else 0,
            batter.data["name"],
            pitcher.data["name"],
            fielder.data["name"] if fielder is not None else "",
            runner_on_first.data["name"] if runner_on_first is not None else "",
            runner_on_second.data["name"] if runner_on_second is not None else "",
            runner_on_third.data["name"] if runner_on_third is not None else "",
            calculate_vibes(batter.data, update["day"]),
            calculate_vibes(pitcher.data, update["day"]),
            calculate_vibes(fielder.data, update["day"]) if fielder is not None else 0,
            calculate_vibes(runner_on_first.data, update["day"]) if runner_on_first is not None else 0,
            calculate_vibes(runner_on_second.data, update["day"]) if runner_on_second is not None else 0,
            calculate_vibes(runner_on_third.data, update["day"]) if runner_on_third is not None else 0,
            ";".join(batter.mods),
            ";".join(batting_team.mods),
            ";".join(pitcher.mods),
            ";".join(pitching_team.mods),
            ";".join(fielder.mods) if fielder is not None else "",
            ";".join(runner_on_first.mods) if runner_on_first is not None else "",
            ";".join(runner_on_second.mods) if runner_on_second is not None else "",
            ";".join(runner_on_third.mods) if runner_on_third is not None else "",
            update["id"],
            update["stadiumId"],
            update["playCount"],
            update["weather"],
            update["atBatBalls"],
            update["atBatStrikes"],
            update["halfInningOuts"],
            update["season"],
            update["day"],
            update["topOfInning"],
            update["homeScore"],
            update["awayScore"],
            update["inning"],
            len(batting_team.data["lineup"]) + len(batting_team.data["rotation"]),
            len(pitching_team.data["lineup"]) + len(pitching_team.data["rotation"]),
            update["baserunnerCount"],
            is_strike,
            strike_roll,
            strike_threshold,
            fielder_roll,
            batter.data["consecutiveHits"],
        ]
        assert len(row) == self.num_columns
        self.csv.writerow(row)

    def close(self):
        self.file.close()
        self.file = None
        self.csv = None

        os.replace(self.partial_filename, self.final_filename)
