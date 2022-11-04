import os
from csv import DictWriter


class SaveCsv:
    def __init__(self, run_name: str, category_name: str):
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
        runner,
        runner_multiplier,
        runner_on_first,
        runner_on_first_multiplier,
        runner_on_second,
        runner_on_second_multiplier,
        runner_on_third,
        runner_on_third_multiplier,
        runner_on_third_hh,
        runner_on_third_hh_multiplier,
        baserunners_next,
        attacked_team,
    ):
        # fmt: off
        row = {
            "event_type": event_type,
            "roll": roll,
            "passed": passed,
            "batter_buoyancy": batter.buoyancy,
            "batter_divinity": batter.divinity,
            "batter_martyrdom": batter.martyrdom,
            "batter_moxie": batter.moxie,
            "batter_musclitude": batter.musclitude,
            "batter_patheticism": batter.patheticism,
            "batter_thwackability": batter.thwackability,
            "batter_tragicness": batter.tragicness,
            "batter_coldness": batter.coldness,
            "batter_overpowerment": batter.overpowerment,
            "batter_ruthlessness": batter.ruthlessness,
            "batter_shakespearianism": batter.shakespearianism,
            "batter_suppression": batter.suppression,
            "batter_unthwackability": batter.unthwackability,
            "batter_base_thirst": batter.baseThirst,
            "batter_continuation": batter.continuation,
            "batter_ground_friction": batter.ground_friction,
            "batter_indulgence": batter.indulgence,
            "batter_laserlikeness": batter.laserlikeness,
            "batter_anticapitalism": batter.anticapitalism,
            "batter_chasiness": batter.chasiness,
            "batter_omniscience": batter.omniscience,
            "batter_tenaciousness": batter.tenaciousness,
            "batter_watchfulness": batter.watchfulness,
            "batter_pressurization": batter.pressurization,
            "batter_cinnamon": batter.cinnamon,
            "batter_multiplier": batter_multiplier,
            "runner_buoyancy": runner.buoyancy,
            "runner_divinity": runner.divinity,
            "runner_martyrdom": runner.martyrdom,
            "runner_moxie": runner.moxie,
            "runner_musclitude": runner.musclitude,
            "runner_patheticism": runner.patheticism,
            "runner_thwackability": runner.thwackability,
            "runner_tragicness": runner.tragicness,
            "runner_coldness": runner.coldness,
            "runner_overpowerment": runner.overpowerment,
            "runner_ruthlessness": runner.ruthlessness,
            "runner_shakespearianism": runner.shakespearianism,
            "runner_suppression": runner.suppression,
            "runner_unthwackability": runner.unthwackability,
            "runner_base_thirst": runner.baseThirst,
            "runner_continuation": runner.continuation,
            "runner_ground_friction": runner.ground_friction,
            "runner_indulgence": runner.indulgence,
            "runner_laserlikeness": runner.laserlikeness,
            "runner_pressurization": runner.pressurization,
            "runner_anticapitalism": runner.anticapitalism,
            "runner_chasiness": runner.chasiness,
            "runner_omniscience": runner.omniscience,
            "runner_tenaciousness": runner.tenaciousness,
            "runner_watchfulness": runner.watchfulness,
            "runner_cinnamon": runner.cinnamon,
            "runner_multiplier": runner_multiplier,
            "runner_on_first_base_thirst": runner_on_first.baseThirst,
            "runner_on_first_continuation": runner_on_first.continuation,
            "runner_on_first_ground_friction": runner_on_first.ground_friction,
            "runner_on_first_indulgence": runner_on_first.indulgence,
            "runner_on_first_laserlikeness": runner_on_first.laserlikeness,
            "runner_on_first_multiplier": runner_on_first_multiplier,
            "runner_on_second_base_thirst": runner_on_second.baseThirst,
            "runner_on_second_continuation": runner_on_second.continuation,
            "runner_on_second_ground_friction": runner_on_second.ground_friction,
            "runner_on_second_indulgence": runner_on_second.indulgence,
            "runner_on_second_laserlikeness": runner_on_second.laserlikeness,
            "runner_on_second_pressurization": runner_on_second.pressurization,
            "runner_on_second_cinnamon": runner_on_second.cinnamon,
            "runner_on_second_multiplier": runner_on_second_multiplier,
            "runner_on_third_base_thirst": runner_on_third.baseThirst,
            "runner_on_third_continuation": runner_on_third.continuation,
            "runner_on_third_ground_friction": runner_on_third.ground_friction,
            "runner_on_third_indulgence": runner_on_third.indulgence,
            "runner_on_third_laserlikeness": runner_on_third.laserlikeness,
            "runner_on_third_multiplier": runner_on_third_multiplier,
            "runner_on_third_hh_base_thirst": runner_on_third_hh.baseThirst,
            "runner_on_third_hh_continuation": runner_on_third_hh.continuation,
            "runner_on_third_hh_ground_friction": runner_on_third_hh.ground_friction,
            "runner_on_third_hh_indulgence": runner_on_third_hh.indulgence,
            "runner_on_third_hh_laserlikeness": runner_on_third_hh.laserlikeness,
            "runner_on_third_hh_multiplier": runner_on_third_hh_multiplier,
            "pitcher_buoyancy": pitcher.buoyancy,
            "pitcher_divinity": pitcher.divinity,
            "pitcher_martyrdom": pitcher.martyrdom,
            "pitcher_moxie": pitcher.moxie,
            "pitcher_musclitude": pitcher.musclitude,
            "pitcher_patheticism": pitcher.patheticism,
            "pitcher_thwackability": pitcher.thwackability,
            "pitcher_tragicness": pitcher.tragicness,
            "pitcher_ruthlessness": pitcher.ruthlessness,
            "pitcher_overpowerment": pitcher.overpowerment,
            "pitcher_unthwackability": pitcher.unthwackability,
            "pitcher_shakespearianism": pitcher.shakespearianism,
            "pitcher_suppression": pitcher.suppression,
            "pitcher_coldness": pitcher.coldness,
            "pitcher_base_thirst": pitcher.baseThirst,
            "pitcher_continuation": pitcher.continuation,
            "pitcher_ground_friction": pitcher.ground_friction,
            "pitcher_indulgence": pitcher.indulgence,
            "pitcher_laserlikeness": pitcher.laserlikeness,
            "pitcher_anticapitalism": pitcher.anticapitalism,
            "pitcher_chasiness": pitcher.chasiness,
            "pitcher_omniscience": pitcher.omniscience,
            "pitcher_tenaciousness": pitcher.tenaciousness,
            "pitcher_watchfulness": pitcher.watchfulness,
            "pitcher_pressurization": pitcher.pressurization,
            "pitcher_cinnamon": pitcher.cinnamon,
            "pitcher_multiplier": pitcher_multiplier,
            "fielder_buoyancy": fielder.buoyancy,
            "fielder_divinity": fielder.divinity,
            "fielder_martyrdom": fielder.martyrdom,
            "fielder_moxie": fielder.moxie,
            "fielder_musclitude": fielder.musclitude,
            "fielder_patheticism": fielder.patheticism,
            "fielder_thwackability": fielder.thwackability,
            "fielder_tragicness": fielder.tragicness,
            "fielder_coldness": fielder.coldness,
            "fielder_overpowerment": fielder.overpowerment,
            "fielder_ruthlessness": fielder.ruthlessness,
            "fielder_shakespearianism": fielder.shakespearianism,
            "fielder_suppression": fielder.suppression,
            "fielder_unthwackability": fielder.unthwackability,
            "fielder_base_thirst": fielder.baseThirst,
            "fielder_continuation": fielder.continuation,
            "fielder_ground_friction": fielder.ground_friction,
            "fielder_indulgence": fielder.indulgence,
            "fielder_laserlikeness": fielder.laserlikeness,
            "fielder_pressurization": fielder.pressurization,
            "fielder_anticapitalism": fielder.anticapitalism,
            "fielder_chasiness": fielder.chasiness,
            "fielder_omniscience": fielder.omniscience,
            "fielder_tenaciousness": fielder.tenaciousness,
            "fielder_watchfulness": fielder.watchfulness,
            "fielder_cinnamon": fielder.cinnamon,
            "fielder_multiplier": fielder_multiplier,
            "ballpark_grandiosity": stadium.grandiosity,
            "ballpark_fortification": stadium.fortification,
            "ballpark_obtuseness": stadium.obtuseness,
            "ballpark_ominousness": stadium.ominousness,
            "ballpark_inconvenience": stadium.inconvenience,
            "ballpark_viscosity": stadium.viscosity,
            "ballpark_forwardness": stadium.forwardness,
            "ballpark_mysticism": stadium.mysticism,
            "ballpark_elongation": stadium.elongation,
            "ballpark_filthiness": stadium.filthiness,
            "what1": what1,
            "what2": what2,
            "batting_team_hype": stadium.hype if not update["topOfInning"] else 0,
            "pitching_team_hype": stadium.hype if update["topOfInning"] else 0,
            "batter_id": batter.id,
            "pitcher_id": pitcher.id,
            "fielder_id": fielder.id,
            "runner_id": runner.id,
            "runner_on_first_id": runner_on_first.id,
            "runner_on_second_id": runner_on_second.id,
            "runner_on_third_id": runner_on_third.id,
            "runner_on_third_hh_id": runner_on_third_hh.id,
            "batter_name": batter.name,
            "pitcher_name": pitcher.name,
            "fielder_name": fielder.name,
            "runner_name": runner.name,
            "runner_on_first_name": runner_on_first.name,
            "runner_on_second_name": runner_on_second.name,
            "runner_on_third_name": runner_on_third.name,
            "runner_on_third_hh_name": runner_on_third_hh.name,
            "batter_vibes": batter.raw_vibes(update["day"]),
            "pitcher_vibes": pitcher.raw_vibes(update["day"]),
            "fielder_vibes": fielder.raw_vibes(update["day"]),
            "runner_vibes": runner.raw_vibes(update["day"]),
            "runner_on_first_vibes": runner_on_first.raw_vibes(update["day"]),
            "runner_on_second_vibes": runner_on_second.raw_vibes(update["day"]),
            "runner_on_third_vibes": runner_on_third.raw_vibes(update["day"]),
            "runner_on_third_hh_vibes": runner_on_third_hh.raw_vibes(update["day"]),
            "batter_mods": ";".join(batter.mods),
            "batting_team_mods": ";".join(batting_team.mods),
            "pitcher_mods": ";".join(pitcher.mods),
            "pitching_team_mods": ";".join(pitching_team.mods),
            "fielder_mods": ";".join(fielder.mods),
            "runner_mods": ";".join(runner.mods),
            "runner_on_first_mods": ";".join(runner_on_first.mods),
            "runner_on_second_mods": ";".join(runner_on_second.mods),
            "runner_on_third_mods": ";".join(runner_on_third.mods),
            "runner_on_third_hh_mods": ";".join(runner_on_third_hh.mods),
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
            "batting_team_roster_size": len(batting_team.lineup) + len(batting_team.rotation),
            "pitching_team_roster_size": len(pitching_team.lineup) + len(pitching_team.rotation),
            "baserunner_count": update["baserunnerCount"],
            "baserunners": str(update["basesOccupied"]),
            "baserunners_next": str(baserunners_next),
            "is_strike": is_strike,
            "strike_roll": strike_roll,
            "strike_threshold": strike_threshold,
            "fielder_roll": fielder_roll,
            "batter_consecutive_hits": batter.consecutive_hits,
            "team_level": attacked_team.level,
            "team_eDensity": attacked_team.eDensity,
            "team_name": attacked_team.nickname,
        }
        # fmt: on

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
