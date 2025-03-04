import json
import math
import os
import re
import sys
import itertools

from data import (
    Base,
    Blood,
    EventType,
    GameData,
    Mod,
    ModType,
    NullUpdate,
    PlayerData,
    TeamData,
    Weather,
    get_feed_between,
    stat_indices,
)
from output import SaveCsv
from rng import Rng
from dataclasses import dataclass
from enum import Enum, unique
from typing import List, Optional
from formulas import (
    get_contact_strike_threshold,
    get_contact_ball_threshold,
    get_hr_threshold,
    get_strike_threshold,
    get_foul_threshold,
    StatRelevantData,
    get_swing_ball_threshold,
    get_swing_strike_threshold,
    get_fly_or_ground_threshold,
    get_out_threshold,
    get_double_threshold,
    get_triple_threshold, get_advance_on_hit_threshold,
)
from item_gen import ItemRollType, roll_item


@unique
class Csv(Enum):
    """
    Tracks the .csv files we can log rolls for in Resim.
    """

    STRIKES = "strikes"
    FOULS = "fouls"
    TRIPLES = "triples"
    DOUBLES = "doubles"
    QUADRUPLES = "quadruples"
    SWING_ON_BALL = "swing-on-ball"
    SWING_ON_STRIKE = "swing-on-strike"
    CONTACT = "contact"
    HR = "hr"
    STEAL_ATTEMPT = "steal_attempt"
    STEAL_SUCCESS = "steal_success"
    OUT = "out"
    FLY = "fly"
    PARTY = "party"
    BIRD_MESSAGE = "bird-message"
    CONSUMERS = "consumers"
    HITADVANCE = "hitadvance"
    FLYOUT = "flyout"
    GROUNDOUT = "groundout"
    GROUNDOUT_FORMULAS = "groundout_formulas"
    EXIT = "exit"
    ENTER = "enter"
    TRICK_ONE = "trick_one"
    TRICK_TWO = "trick_two"
    SWEET1 = "sweet1"
    SWEET2 = "sweet2"
    WEATHERPROC = "weatherproc"
    MODPROC = "modproc"
    BASE = "base"
    INSTINCTS = "instincts"
    PSYCHIC = "psychic"
    BSYCHIC = "bsychic"
    ITEM_CREATION = "item_creation"
    UPGRADE_OUT = "upgrade_out"
    SWEEP = "sweep"

# todo: get rid of this crime, it breaks under multiprocessing anyway
seen_odds = {}

class Resim:
    def __init__(self, rng, out_file, run_name, raise_on_errors=True, csvs_to_log=[], stream_file_dir=None):
        object_cache = {}
        self.rng = rng
        self.out_file = out_file
        if stream_file_dir is None:
            self.stream_file = None
        else:
            self.stream_file = open(stream_file_dir / (run_name + ".ndjson"), "w")
        self.data = GameData()
        self.fetched_days = set()
        self.started_days = set()
        self.raise_on_errors = raise_on_errors
        self.update = NullUpdate()
        self.next_update = NullUpdate()

        self.is_strike = None
        self.strike_roll = None
        self.strike_threshold = None
        self.strikes = 0
        self.max_strikes = 3
        self.balls = 0
        self.max_balls = 4
        self.outs = 0
        self.max_outs = 3
        self.game_id = None
        self.play = None
        self.weather = Weather.VOID
        self.batter = self.data.get_player(None)
        self.pitcher = self.data.get_player(None)
        self.batting_team = self.data.get_team(None)
        self.pitching_team = self.data.get_team(None)
        self.home_team = self.data.get_team(None)
        self.away_team = self.data.get_team(None)
        self.stadium = self.data.get_stadium(None)
        self.pending_attractor = None
        self.event = None
        self.prev_event = None

        self.run_name = run_name.replace(":", "_")

        if run_name:
            os.makedirs("roll_data", exist_ok=True)
            run_name = run_name.replace(":", "_")
            csvs_to_log = csvs_to_log or list(Csv)
            self.csvs = {csv: SaveCsv(run_name, csv.value, object_cache) for csv in Csv if csv in csvs_to_log}
        else:
            self.csvs = {}
        self.roll_log: List[LoggedRoll] = []
        self.odds_log: List[OddsLog] = []

    def print(self, *args, **kwargs):
        if self.out_file is None:
            return
        print(*args, **kwargs, file=self.out_file)

    def error(self, *args, **kwargs):
        if not self.out_file:
            return
        if self.out_file != sys.stdout:
            print("Error: ", *args, **kwargs, file=self.out_file)
        print("Error: ", *args, **kwargs, file=sys.stderr)
        if self.raise_on_errors:
            error_string = " ".join(args)
            raise RuntimeError(error_string)

    def handle(self, event):
        self.setup_data(event)

        # hardcoding a fix for a data error - jands don't get the overperforming mod from earlbirds
        # in chron until after the game ends, but we need it earlier
        if self.game_id == "8577919c-4288-4404-bde2-694f5e7a38d1":
            jands = self.data.get_team("a37f9158-7f82-46bc-908c-c9e2dda7c33b")
            if not jands.has_mod(Mod.OVERPERFORMING):
                jands.add_mod(Mod.OVERPERFORMING, ModType.PERMANENT)
                jands.last_update_time = self.event["created"]

        # another workaround for bad data
        if self.game_id == "c608b5db-29ad-4216-a703-8f0627057523":
            caleb_novak = self.data.get_player("0eddd056-9d72-4804-bd60-53144b785d5c")
            if caleb_novak.has_mod(Mod.ELSEWHERE):
                caleb_novak.remove_mod(Mod.ELSEWHERE, ModType.PERMANENT)
                caleb_novak.last_update_time = self.event["created"]

        # missed a "happy to be home" event 45 secs before the fragment starts
        if self.game_id == "ee0066a5-8408-4270-a5d8-8e66abf55d03":
            vela = self.data.get_player("4ca52626-58cd-449d-88bb-f6d631588640")
            if not vela.has_mod(Mod.OVERPERFORMING):
                vela.add_mod(Mod.OVERPERFORMING, ModType.PERMANENT)
                vela.remove_mod(Mod.UNDERPERFORMING, ModType.PERMANENT)

        # sometimes we start a fragment in the middle of a game and we wanna make sure we have the proper blood type
        a_blood_type_overrides = {
            "0aa57b7d-d78f-4090-8f0e-9273c285e698": Mod.PSYCHIC,
            "d2e75d15-0348-4a2b-88ad-5a9205173494": Mod.PSYCHIC,
            "bb5ad5c8-22b7-41a4-83f9-47b8ed8825b2": Mod.LOVE,
            "61ac8e12-0c98-4d21-b827-eac77c0b407f": Mod.ACIDIC,
            "d18f5735-17f2-40ed-949c-6ccfb69828be": Mod.FIERY,
            "ff050ef3-c532-42bb-8c74-551a31784142": Mod.FIERY,
            "55b8be59-93ac-4756-8f24-7a0ba0e0499f": Mod.AA,
            "5007d0ef-2404-490f-97d7-69b98b08979a": Mod.PSYCHIC,
            "2a7247fb-62cd-4f84-9f4e-77a1949bc1fb": Mod.BASE_INSTINCTS,
            "bbd0c719-b6f9-45ae-946e-0d674d3811a9": Mod.H20,
            "fe105cf7-ff56-42c7-b918-0ee3ab394f58": Mod.ELECTRIC,
            "48ad61f1-a231-4061-bb84-331ce891626a": Mod.ZERO,
            "b0a8c4c3-eeca-49a7-bf47-771a614bb3f3": Mod.LOVE,
            "a0e2ba91-16d5-4f39-9bc8-7ee35042fae0": Mod.AAA,
        }
        if self.game_id in a_blood_type_overrides:
            blood_type = a_blood_type_overrides[self.game_id]
            shoe_thieves = self.data.get_team("bfd38797-8404-4b38-8b82-341da28b1f83")
            if not shoe_thieves.has_mod(blood_type):
                shoe_thieves.add_mod(blood_type, ModType.GAME)
                shoe_thieves.last_update_time = self.event["created"]

        self.print()
        if not self.update and self.play and self.play > 1:
            self.print("!!! missing update data")
        self.print(
            "===== {} {}/{} {}".format(
                event["created"],
                self.update["id"],
                self.update["playCount"],
                self.weather.name,
            )
        )
        self.print(f"===== {self.ty.value} {self.desc}")
        self.print(f"===== rng pos: {self.rng.get_state_str()}")

        event_adjustments = {
            "2021-03-01T20:22:00.461Z": -1,  # fix for missing data
            "2021-03-01T21:00:16.006Z": -1,  # fix for missing data
            "2021-03-02T12:24:43.753Z": 1,  # fix for missing data
            "2021-03-02T13:25:06.682Z": -1,  # fix for missing data
            "2021-03-02T14:00:15.843Z": 1,
            "2021-04-05T15:23:26.102Z": 1,
            "2021-04-12T15:19:56.073Z": -2,
            "2021-04-12T15:22:50.866Z": 1, # there's a low roll on the item damage here
            "2021-05-13T15:00:17.580Z": -1,
            "2021-05-13T16:38:59.820Z": 387,  # skipping latesiesta
            "2021-06-16T06:22:07.019Z": 1, # caused by Seeker returning from Elsewhere and immediately rolling Seeker for the other Elsewhere player

            "2021-06-24T10:13:01.619Z": 4, # Caused by Advance & Item Damage handling. Two Siobhan's on base. Needs 3 more damage rolls. 2 rolls for Siobhan #1 scoring, and 1 roll for Siobhan #2 advancing bases.

            "2021-07-26T17:36:38.281Z": 4, # maxi socks item gem broken
            "2021-07-26T18:09:17.129Z": 2, # observed?
            "2021-07-26T18:20:09.430Z": 1, # consumer attack item defend push?

            # the roll in 2021-07-26T17:09:56.933Z really happens earlier, this event being delayed breaks some stuff
            "2021-07-26T17:09:54.480Z": 1,
            "2021-07-26T17:09:57.341Z": -1,
            # "2021-07-22T09:18:04.585Z": 3, # no idea
            "2021-07-23T08:27:00.305Z": 1, # grand slam weird? Amphitheater is only stadium with both balloon mods - Hot Air Balloon Pop Check?
            "2021-07-23T09:11:48.567Z": 1, # grand slam weird? Amphitheater is only stadium with both balloon mods - Hot Air Balloon Pop Check?
            "2021-07-23T10:19:55.173Z": 1, # grand slam weird? Amphitheater is only stadium with both balloon mods - Hot Air Balloon Pop Check?
            "2021-07-22T10:07:23.346Z": -1, # no idea

            "2021-07-23T14:22:51.364Z": -1, # there's a couple different places this can go, not sure where the problem is

            "2021-07-19T18:11:34.836Z": 1, # ??
            "2021-07-21T11:13:17.022Z": 3, # ??? i think this home run is actually fake somehow
            "2021-07-21T21:08:45.629Z": 1, # elsewhere scattering?
            "2021-07-23T22:07:38.888Z": 2, # fix for item gen problem
        }
        to_step = event_adjustments.get(self.event["created"])
        if to_step is not None:
            self.rng.step(to_step)
            time = self.event["created"]
            self.print(f"!!! CORRECTION: stepping {to_step} @ {time}")
            self.emit_correction_to_stream(to_step)

        if self.handle_misc():
            return

        if self.handle_elsewhere_scattered():
            return

        if self.ty in [
            EventType.RETURN_FROM_ELSEWHERE,
        ]:
            # skipping elsewhere return
            return

        if self.batter:
            self.print(
                f"- batter mods: {self.batter.print_mods()} + "
                f"{self.batting_team.print_mods()} ({self.batter.name}) "
            )
        if self.pitcher:
            self.print(
                f"- pitcher mods: {self.pitcher.print_mods()} + "
                f"{self.pitching_team.print_mods()} ({self.pitcher.name})"
            )
        self.print(f"- stadium mods: {self.stadium.print_mods()} ({self.stadium.nickname})")

        if self.ty == EventType.STUCK:
            return

        if self.handle_batter_up():
            return

        if self.handle_weather():
            return

        if self.handle_party():
            return
        
        # has to be rolled after party
        if self.handle_flooding():
            return

        if self.handle_polarity():
            return
        
        if self.handle_consumers():
            return
                
        if self.handle_ballpark():
            return

        if self.ty == EventType.HIGH_PRESSURE_ON_OFF:
            # s14 high pressure proc, not sure when this should interrupt
            return

        if self.handle_steal():
            return

        if self.handle_electric():
            return
                
        # # todo: also don't know where this is
        # if self.batter.has_mod(Mod.SCATTERED) and self.batter.has_mod(Mod.UNDEFINED):
            # self.roll("undefined?") # 50-100% better...

        # todo: don't know where this actually is - seems to be before mild at least
        if (self.pitcher.has_mod(Mod.DEBT_THREE) or self.pitcher.has_mod(Mod.DEBT_ZERO)) and not self.batter.has_mod(Mod.COFFEE_PERIL):
            debt_roll = self.roll("debt")
            if self.ty == EventType.HIT_BY_PITCH:
                self.log_roll(
                    Csv.MODPROC,
                    "Bonk",
                    debt_roll,
                    True,
                )
                # debt success
                return True
            else:
                self.log_roll(
                    Csv.MODPROC,
                    "No Bonk",
                    debt_roll,
                    False,
                )

        if self.handle_bird_ambush():
            return

        if self.handle_mild():
            return

        if self.handle_charm():
            return

        self.is_strike = None
        if self.ty in [
            EventType.WALK,
            EventType.BALL,
            EventType.MILD_PITCH,
        ]:
            self.handle_ball()

        elif self.ty in [
            EventType.FLY_OUT,
            EventType.GROUND_OUT,
        ]:
            self.handle_out()

        elif self.ty in [
            EventType.STRIKEOUT,
            EventType.STRIKE,
        ]:
            self.handle_strike()

        elif self.ty in [EventType.HOME_RUN]:
            self.handle_hr()

        elif self.ty in [EventType.HIT]:
            self.handle_base_hit()

        elif self.ty in [EventType.FOUL_BALL]:
            self.handle_foul()

        else:
            self.print(f"!!! unknown type: {self.ty.value}")
        pass

        self.handle_batter_reverb()

        if self.pending_attractor:
            if self.pending_attractor and self.pending_attractor.has_mod(Mod.REDACTED):
                self.roll("attractor pitching stars")
                self.roll("attractor batting stars")
                self.roll("attractor baserunning stars")
                self.roll("attractor defense stars")
            self.pending_attractor = None

    def handle_inning_start(self):
        last_phase = self.update["newInningPhase"]
        next_phase = self.next_update["newInningPhase"]
        if self.ty == EventType.HALF_INNING and self.next_update["topOfInning"]:
            next_phase = 10 # making up a high number, the game sets this back to -1 before starting tick otherwise

        # fix for missing update data
        if self.event["created"] == "2021-04-07T08:02:52.530Z":
            last_phase = 0

        for cur_phase in range(last_phase+1, next_phase+1):
            if cur_phase == 0 and self.weather == Weather.SALMON:
                self.handle_salmon()

            if cur_phase == 2:
                has_hotel_motel = self.stadium.has_mod(Mod.HOTEL_MOTEL) or self.season >= 18
                if has_hotel_motel and self.day < 27:
                    hotel_roll = self.roll("hotel motel")

                    if self.ty == EventType.HOLIDAY_INNING:
                        self.log_roll(Csv.MODPROC, "Hotel", hotel_roll, True)
                    else:
                        self.log_roll(Csv.MODPROC, "Notel", hotel_roll, False)
                    return True
                
            if cur_phase == 3:
                # sun 30 message doesn't do anything
                pass

    def handle_salmon(self):
        last_inning = self.update["inning"]
        if last_inning < 0:
            # don't roll at start of game
            return

        last_inning_away_score, last_inning_home_score = self.find_start_of_inning_score(self.game_id, last_inning)
        current_away_score, current_home_score = (
            self.update["awayScore"],
            self.update["homeScore"],
        )
        self.print(f"(last away: {last_inning_away_score}, last home: {last_inning_home_score}, cur away: {current_away_score}, cur home: {current_home_score})")

        if current_away_score != last_inning_away_score or current_home_score != last_inning_home_score:
            salmon_roll = self.roll("salmon")

            if self.ty == EventType.SALMON_SWIM:
                self.log_roll(Csv.WEATHERPROC, "Salmon", salmon_roll, True)

                if current_away_score != last_inning_away_score:
                    self.roll("reset runs (away)")
                if current_home_score != last_inning_home_score:
                    self.roll("reset runs (home)")

                if self.season >= 15:
                    self.roll("reset items? idk?")

                if self.event["created"] in [
                    # these two are probably not the same reason
                    "2021-04-13T01:06:52.165Z",
                    "2021-04-13T01:28:04.005Z",
                ]:
                    self.roll("extra for some reason")

                if (
                    "was restored!" in self.desc
                    or "were restored!" in self.desc
                    or "were restored!" in self.desc
                    or "was repaired." in self.desc
                    or "were repaired." in self.desc
                ):
                    self.roll("restore item??")
                    self.roll("restore item??")
                    self.roll("restore item??")

                if self.stadium.has_mod(Mod.SALMON_CANNONS):
                    self.roll("salmon cannons")

                    if "caught in the bind!" in self.desc:
                        self.roll("salmon cannons player")

                        has_undertaker = False
                        for player_id in self.away_team.lineup + self.away_team.rotation:
                            player = self.data.get_player(player_id)
                            # undertakers can't undertake themselves
                            if (player.raw_name + " is caught") not in self.desc and player.has_mod(Mod.UNDERTAKER) and not player.has_mod(Mod.ELSEWHERE):
                                has_undertaker = True
                                self.print(f"(have undertaker: {player.name})")
                                break
                        if has_undertaker:
                            self.roll("undertaker")
                            self.roll("undertaker")

            else:
                self.log_roll(Csv.WEATHERPROC, "Salmon", salmon_roll, False)
    
    def start_game_day(self, season, day):
        # happens end of last game day, really
        self.print(f"=== starting game day s{season+1}d{day+1} ({season,day})")
        current_game_order = self.data.fetch_game_order(season, day)
        has_mismatch = False
        for game_id in current_game_order: 
            raw_updates = self.data.get_raw_game_updates(game_id)
            predicted_home_pitcher = [u["data"]["homePitcher"] for u in raw_updates if u["data"]["homePitcher"]][0]
            real_home_pitcher = [u["data"]["homePitcher"] for u in raw_updates if u["data"]["homePitcher"] and u["data"]["gameStart"]][0]
            predicted_away_pitcher = [u["data"]["awayPitcher"] for u in raw_updates if u["data"]["awayPitcher"]][0]
            real_away_pitcher = [u["data"]["awayPitcher"] for u in raw_updates if u["data"]["awayPitcher"] and u["data"]["gameStart"]][0]
            
            self.print(f"predicted home pitcher: {predicted_home_pitcher}, predicted away pitcher: {predicted_away_pitcher}")
            self.print(f"real home pitcher: {real_home_pitcher}, real away pitcher: {real_away_pitcher}")
            mismatch = predicted_home_pitcher != real_home_pitcher or predicted_away_pitcher != real_away_pitcher

            if mismatch:
                self.print(f"!!! warn: mispredicted pitchers on {season, day}")
                has_mismatch = True
                self.calc_next_game_odds(game_id, use_early_data=False, data_invalid=True)

        if day >= 99:
            for game_id in current_game_order:
                game = self.data.get_update(game_id, 5)
                weather = Weather(game["weather"])
                stadium = self.data.get_stadium(game['stadiumId'])
                self.roll(f"postseason weather ({weather.name}) day {day}, upgrades: {stadium.weather}")

                self.calc_next_game_odds(game_id, use_early_data=False)

        # happens start of game day
        # calculating odds for the upcoming batch of games (hence: not on day 99)
        if day < 98:
            upcoming_game_order = self.data.fetch_game_order(season, day+1)
            self.print(f"next day order: {upcoming_game_order}")
            for upcoming_game_id in upcoming_game_order:
                self.calc_next_game_odds(upcoming_game_id, data_invalid=has_mismatch)
        pass

    def calc_next_game_odds(self, game_id, use_early_data=True, data_invalid=False):
        # todo: merge this into data.py, it belongs there
        # yes we are intentionally fetching standings for the "previous" day
        # when doing upcoming-game odds, because that's what it'd have available
        season = self.data.fetch_season_at(self.data.sim["seasonId"], self.event["created"])["data"]
        standings = self.data.fetch_standings_at(season["standings"], self.event["created"])["data"]

        raw_updates = self.data.get_raw_game_updates(game_id)

        game_data = [u['data'] for u in raw_updates if u['data']['homeOdds'] > 0 and u['data']['homePitcher']][0]
        if not use_early_data:
            game_data = [u['data'] for u in raw_updates if u['data']['gameStart'] and u['data']['homePitcher']][0]
        
        data_known_invalid = data_invalid
        # missing the "early" event so we don't get the wrong odds
        if game_id == "c8bfd47f-3fbb-48fb-a1f7-5c95daf26f81" and use_early_data:
            data_known_invalid = True
        if len(self.started_days) < 2:
            # first rolls of each fragment seem broken, this is our heuristic
            data_known_invalid = True
        if self.day in [0, 27, 72, 99]:
            # skip problematic roll ordering for now
            data_known_invalid = True

        home_odds = game_data['homeOdds']
        away_odds = game_data['awayOdds']

        self.print("===")

        fuzz_roll = self.roll("odds fuzzing")
        delta = (0.03+fuzz_roll*0.07)-0.05

        self.print(f"=== matchup: s{game_data['season']+1}d{game_data['day']+1}, game {game_id}, {game_data['awayTeamNickname']}@{game_data['homeTeamNickname']}")
        self.print(f"=== {game_data['awayPitcherName']} @ {game_data['homePitcherName']}")
        self.print(f"home odds: {game_data['homeOdds']}")
        self.print(f"away odds: {game_data['awayOdds']}")

        home_wins = standings["wins"].get(game_data["homeTeam"], 0)
        away_wins = standings["wins"].get(game_data["awayTeam"], 0)

        # assuming team data will be correct as of time-of-call
        home_team = self.data.get_team(game_data["homeTeam"])
        away_team = self.data.get_team(game_data["awayTeam"])

        # make sure players have right hitting ratings?
        self.data.fetch_players(self.event['created'])

        def batting_stars(p):
            return p.data['hittingRating']
            # return ((1 - p.data['tragicness']) ** 0.01) * (p.data['thwackability'] ** 0.35) * (p.data['moxie'] ** 0.075) * (p.data['divinity'] ** 0.35) * (p.data['musclitude'] ** 0.075) * ((1 - p.data['patheticism']) ** 0.05) * (p.data['martyrdom'] ** 0.02)

        def pitching_stars(p):
            return p.data['pitchingRating']
            # return (p.data["shakespearianism"] ** 0.1) * (p.data["unthwackability"] ** 0.5) * (p.data["coldness"] ** 0.025) * (p.data["overpowerment"] ** 0.15) * (p.data["ruthlessness"] ** 0.4)
        def running_stars(p):
            return p.data['baserunningRating']
        def defense_stars(p):
            return p.data['defenseRating']
        
        def geom(vals):
            prod = 1
            count = 0
            for v in vals:
                prod *= v
                count += 1
            return prod**(1/count)

        home_batting_stars = sum(batting_stars(self.data.get_player(batter_id)) for batter_id in home_team.lineup)
        away_batting_stars = sum(batting_stars(self.data.get_player(batter_id)) for batter_id in away_team.lineup)
        home_batting_stars_geom = geom(batting_stars(self.data.get_player(batter_id)) for batter_id in home_team.lineup)
        away_batting_stars_geom = geom(batting_stars(self.data.get_player(batter_id)) for batter_id in away_team.lineup)
        home_batting_stars_csv = ",".join(str(batting_stars(self.data.get_player(batter_id))) for batter_id in home_team.lineup)
        away_batting_stars_csv = ",".join(str(batting_stars(self.data.get_player(batter_id))) for batter_id in away_team.lineup)
        home_pitching_stars = pitching_stars(self.data.get_player(game_data['homePitcher']))
        away_pitching_stars = pitching_stars(self.data.get_player(game_data['awayPitcher']))
                
        home_running_stars = sum(running_stars(self.data.get_player(batter_id)) for batter_id in home_team.lineup)
        away_running_stars = sum(running_stars(self.data.get_player(batter_id)) for batter_id in away_team.lineup)
        home_defense_stars = sum(defense_stars(self.data.get_player(batter_id)) for batter_id in home_team.lineup)
        away_defense_stars = sum(defense_stars(self.data.get_player(batter_id)) for batter_id in away_team.lineup)

        self.print(f"home wins: {home_wins}, away wins: {away_wins}")
        self.print(f"home bstars: {home_batting_stars}, away bstars: {away_batting_stars}")
        self.print(f"home pstars: {home_pitching_stars}, away pstars: {away_pitching_stars}")
        self.print(f"fuzz roll: {fuzz_roll} (delta: {delta})")

        if abs(delta) < abs(home_odds-0.5) or delta > 0:
            # unambiguous
            if home_odds > away_odds:
                unfuzzed_home_odds = home_odds - delta
                unfuzzed_away_odds = away_odds + delta
            else:
                unfuzzed_home_odds = home_odds + delta
                unfuzzed_away_odds = away_odds - delta

            self.print(f"unambiguous unfuzzed home odds: {unfuzzed_home_odds}")
            self.print(f"unambiguous unfuzzed away odds: {unfuzzed_away_odds}")

            if not data_known_invalid:
                self.odds_log.append(OddsLog(
                    game_id=game_id,
                    season=game_data["season"],
                    day=game_data["day"],
                    home_batting_stars=home_batting_stars,
                    away_batting_stars=away_batting_stars,
                    home_batting_stars_geom=home_batting_stars_geom,
                    away_batting_stars_geom=away_batting_stars_geom,
                    home_batting_stars_csv=home_batting_stars_csv,
                    away_batting_stars_csv=away_batting_stars_csv,
                    home_pitching_stars=home_pitching_stars,
                    away_pitching_stars=away_pitching_stars,
                    home_wins=home_wins,
                    away_wins=away_wins,
                    home_odds=unfuzzed_home_odds,
                    away_odds=unfuzzed_away_odds,
                    home_batters=len(home_team.lineup),
                    away_batters=len(away_team.lineup),
                    home_pitcher_id=game_data['homePitcher'],
                    away_pitcher_id=game_data['awayPitcher'],
                    home_team=home_team.id,
                    away_team=away_team.id,
                    home_team_name=game_data['homeTeamNickname'],
                    away_team_name=game_data['awayTeamNickname'],
                    home_pitcher_name=game_data['homePitcherName'],
                    away_pitcher_name=game_data['awayPitcherName'],
                    fuzz_roll=fuzz_roll,
                    delta=delta,
                    home_baserunning_stars=home_running_stars,
                    away_baserunning_stars=away_running_stars,
                    home_defense_stars=home_defense_stars,
                    away_defense_stars=away_defense_stars
                ))

            for odd in [unfuzzed_home_odds, unfuzzed_away_odds]:
                rounded = str(odd)[:10]
                if rounded in seen_odds:
                    self.print(f"odds {rounded} already seen at: {seen_odds[rounded]}")
                    seen_odds[rounded].append(game_id)
                else:
                    seen_odds[rounded] = [game_id]
        else:
            # ambiguous
            for sign in [-1, 1]:
                unfuzzed_home_odds = home_odds + delta*sign
                unfuzzed_away_odds = away_odds - delta*sign
                self.print(f"*possible* unfuzzed home odds: {unfuzzed_home_odds}")
                self.print(f"*possible* unfuzzed away odds: {unfuzzed_away_odds}")
                for odd in [unfuzzed_home_odds, unfuzzed_away_odds]:
                    rounded = str(odd)[:10]
                    if rounded in seen_odds:
                        self.print(f"odds {rounded} already seen at: {seen_odds[rounded]}")
                        seen_odds[rounded].append(game_id)
                    else:
                        seen_odds[rounded] = [game_id]

    def handle_misc(self):
        if self.update["gameStartPhase"] != self.next_update["gameStartPhase"]:
            self.print(f"GAME START PHASE: {self.update['gameStartPhase']} -> {self.next_update['gameStartPhase']} phase")
        if self.update["newInningPhase"] != self.next_update["newInningPhase"]:
            self.print(f"NEW INNING PHASE: {self.update['newInningPhase']} -> {self.next_update['newInningPhase']} inphase")

        if (
            self.season >= 17
            and self.update["gameStartPhase"] < 0
            and self.next_update["gameStartPhase"] >= 0
            and self.ty
            not in [
                EventType.ADDED_MOD_FROM_OTHER_MOD,
                EventType.REMOVED_MODIFICATION,
                EventType.RUNS_SCORED,
            ]
        ):
            min_roll, max_roll = (0, 0.02) if self.ty == EventType.PRIZE_MATCH else (0.02, 1)
            self.roll("prize match", min_roll, max_roll)

        PSYCHO_ACOUSTICS_PHASE_BY_SEASON = {
            13: 10,
            14: 11,
            15: 11,
            16: 11,
            17: 13,
            18: 13,
            19: 13,
            20: 13,
            21: 14,
            22: 14,
            23: 14
        }
        psycho_acoustics_phase = PSYCHO_ACOUSTICS_PHASE_BY_SEASON.get(self.season, 13)
        if (
            self.update["gameStartPhase"] < psycho_acoustics_phase
            and self.next_update["gameStartPhase"] >= psycho_acoustics_phase
            and self.ty != EventType.ADDED_MOD_FROM_OTHER_MOD
            and self.weather
            in [
                Weather.FEEDBACK,
                Weather.REVERB,
            ]
            and self.stadium.has_mod(Mod.PSYCHOACOUSTICS)
        ):
            self.print("away team mods:", self.away_team._raw_mods)
            self.roll("echo team mod")

        if self.ty in [
            EventType.HALF_INNING,
            EventType.SUN_30,
            EventType.HOLIDAY_INNING,
            EventType.SALMON_SWIM,
        ]:
            self.handle_inning_start()
            return True

        if self.ty in [
            EventType.HOME_FIELD_ADVANTAGE,
            EventType.BECOME_TRIPLE_THREAT,
            EventType.SOLAR_PANELS_AWAIT,
            EventType.SOLAR_PANELS_ACTIVATION,
            EventType.EVENT_HORIZON_AWAITS,
            EventType.EVENT_HORIZON_ACTIVATION,
            EventType.HOMEBODY,
            EventType.SUPERYUMMY,
            EventType.PERK,
            EventType.SHAME_DONOR,
            EventType.PSYCHO_ACOUSTICS,
            EventType.AMBITIOUS,
            EventType.UNAMBITIOUS,
            EventType.LATE_TO_THE_PARTY,
            EventType.MIDDLING,
            EventType.SHAMING_RUN,
            EventType.EARLBIRD,
            EventType.PRIZE_MATCH,
            EventType.A_BLOOD_TYPE,
            EventType.COASTING,
            EventType.TEAM_RECEIVED_GIFT,
            EventType.BLESSING_OR_GIFT_WON,
            EventType.PLAYER_SOUL_INCREASED,
        ]:
            if self.ty == EventType.PRIZE_MATCH:
                self.create_item(self.event, ItemRollType.PRIZE, self.prev_event)

            if self.ty == EventType.BLESSING_OR_GIFT_WON:
                if "aDense" in self.desc or "eDense" in self.desc:
                    team_id = self.event["teamTags"][0]
                    team = self.data.get_team(team_id)

                    eligible_items = []
                    for player_id in team.lineup + team.rotation + team.shadows:
                        player = self.data.get_player(player_id)
                        for item in player.items:
                            if "aDense" in self.desc and "aDense" not in item.elements:
                                eligible_items.append(item)
                            if "eDense" in self.desc and "eDense" not in item.elements:
                                eligible_items.append(item)
                    self.print(f"eligible items: {len(eligible_items)}, 20% is {len(eligible_items)*0.2}, children: {len(self.event['metadata']['children'])}")

            # skipping pregame messages
            return True
        if self.ty in [
            EventType.OVER_UNDER,
            EventType.UNDER_OVER,
            EventType.UNDERSEA,
            EventType.ADDED_MOD_FROM_OTHER_MOD,
            EventType.REMOVED_MODIFICATION,
            EventType.CHANGED_MODIFIER,
            EventType.REMOVED_MULTIPLE_MODIFICATIONS_ECHO,
            EventType.ADDED_MULTIPLE_MODIFICATIONS_ECHO,
            EventType.LEAGUE_MODIFICATION_REMOVED,
        ]:
            # skipping mod added/removed
            
            # a blood type is here so we can query subevent
            if self.ty == EventType.ADDED_MOD_FROM_OTHER_MOD:
                if self.event["metadata"]["source"] == "A":
                    added_mod = Mod(self.event["metadata"]["mod"])
                    blood_mods = [Mod.AAA, Mod.AA, Mod.ACIDIC, Mod.BASE_INSTINCTS, Mod.ZERO, Mod.O_NO, Mod.H20, Mod.ELECTRIC, Mod.LOVE, Mod.FIERY, Mod.PSYCHIC, Mod.GROWTH]
                    
                    expected_index = blood_mods.index(added_mod)
                    self.roll("a blood type", expected_index/len(blood_mods), (expected_index+1)/len(blood_mods))

                if self.event["metadata"]["source"] == "PSYCHOACOUSTICS":
                    added_mod = self.event["metadata"]["mod"]
                    mod_pool = [str(m) for group in self.away_team._raw_mods for m in group]
                    
                    expected_index = mod_pool.index(added_mod)
                    self.roll("which mod?", expected_index/len(mod_pool), (expected_index+1)/len(mod_pool))
            return True
        if self.ty in [
            EventType.BLACK_HOLE,
            EventType.BLACK_HOLE_BLACK_HOLE,
            EventType.SUN2,
            EventType.SUN_2_OUTCOME,
            EventType.BLACK_HOLE_OUTCOME,
            EventType.SUN_SUN_PRESSURE,
        ]:
            if self.ty == EventType.SUN2 and "catches some rays" in self.desc:
                self.roll("sun dialed target")

            if self.ty == EventType.BLACK_HOLE:
                if "is compressed by gamma" in self.desc:
                    self.roll("unholey target")

            if self.ty == EventType.BLACK_HOLE_BLACK_HOLE:
                # uhhhh what etc
                self.roll("bhbh target?")
                self.roll("bhbh target?")
            # skipping sun 2 / black hole proc
            return True
        if self.ty in [
            EventType.PLAYER_STAT_INCREASE,
            EventType.PLAYER_STAT_DECREASE,
            EventType.PLAYER_STAT_DECREASE_FROM_SUPERALLERGIC,
        ]:
            if "are Bottom Dwellers" in self.desc:
                team = self.data.get_team(self.event["teamTags"][0])
                # boost amounts are 0.04 * roll + 0.01, rolled in this order:
                # Omniscience, Tenaciousness, Watchfulness, Anticapitalism, Chasiness,
                # Shakespearianism, Suppression, Unthwackability, Coldness, Overpowerment, Ruthlessness,
                # Base Thirst, Laserlikeness, Ground Friction, Continuation, Indulgence,
                # Tragicness, Buoyancy, Thwackability, Moxie, Divinity, Musclitude, Patheticism, Martyrdom, Cinnamon
                for player_id in team.lineup:
                    for _ in range(25):
                        self.roll("stat")
                for player_id in team.rotation:
                    for _ in range(25):
                        self.roll("stat")

            if "re-congealed differently" in self.desc:
                for _ in range(25):
                    self.roll("stat")

            if "is Partying" in self.desc:
                # we want to roll this only if this is a *holiday inning* party,
                # and we currently have no nice way of seeing that
                # we can check the date, but after_party is also a thing.
                # and there's at least one occasion where a player has both, and we can't disambiguate
                team = self.data.get_team(self.event["teamTags"][0])
                if (
                    not team.has_mod(Mod.PARTY_TIME) and not team.has_mod(Mod.AFTER_PARTY) and self.day < 27
                ) or self.event["created"] in [
                    "2021-05-17T21:21:21.303Z",
                    "2021-05-17T21:22:11.076Z",
                ]:
                    # this is a holiday inning party (why 26?)
                    for _ in range(26):
                        self.roll("stat")

            if "entered the Shadows" in self.desc:
                # fax machine dunk
                # boost amounts are 0.04 * roll + 0.01, rolled in this order:
                # Shakespearianism, Suppression, Unthwackability, Coldness, Overpowerment, Ruthlessness, Tragicness,
                # Buoyancy, Thwackability, Moxie, Divinity, Musclitude, Patheticism, Martyrdom,
                # Base Thirst, Laserlikeness, Ground Friction, Continuation, Indulgence,
                # Omniscience, Tenaciousness, Watchfulness, Anticapitalism, Chasiness, Cinnamon

                for _ in range(25):
                    self.roll("stat")
            if "clocked in" in self.desc:
                for _ in range(25):
                    self.roll("stat")

            # skip party/consumer stat change
            return True
        if self.ty in [
            EventType.PLAYER_BORN_FROM_INCINERATION,
            EventType.ENTER_HALL_OF_FLAME,
            EventType.EXIT_HALL_OF_FLAME,
            EventType.PLAYER_HATCHED,
        ]:
            # skipping incineration stuff
            return True
        if self.ty in [
            EventType.PLAYER_REMOVED_FROM_TEAM,
            EventType.MODIFICATION_CHANGE,
        ]:
            # skipping echo/static
            return True
        if self.ty == EventType.INCINERATION and "parent" in self.event["metadata"]:
            # incin has two events and one's a subevent so ignore one of them
            return True
        if self.ty == EventType.PITCHER_CHANGE:
            # s skipping pitcher change?
            return True
        if self.ty in [
            EventType.REMOVED_MOD,
            EventType.PLAYER_MOVE,
            EventType.INVESTIGATION_PROGRESS,
            EventType.ENTERING_CRIMESCENE,
            EventType.WEATHER_EVENT,
            EventType.RUNS_SCORED,
            EventType.TUNNEL_FLED_ELSEWHERE,
            EventType.TUNNEL_FOUND_NOTHING,
            EventType.TRADE_FAILED,
            EventType.TRADE_SUCCESS,
            EventType.PLAYER_MOVE_FAILED_FORCE,
        ]:
            return True

        if self.ty == EventType.EXISTING_PLAYER_ADDED_TO_ILB:
            if "pulled through the Rift" in self.desc:
                # The Second Wyatt Masoning
                # The rolls normally assigned to "Let's Go" happen before the Second Wyatt Masoning
                if self.desc == "Wyatt Mason was pulled through the Rift.":
                    self.started_days.add((13, 72))

                    self.start_game_day(13, 72)
                self.generate_player()
            return True
        if self.ty in [
            EventType.PLAYER_ADDED_TO_TEAM,
            EventType.BIG_DEAL,
            EventType.WON_INTERNET_SERIES,
            EventType.UNDEFINED_TYPE,
        ]:
            # skip postseason
            return True
        if self.ty == EventType.POSTSEASON_SPOT:
            self.generate_player()
            return True
        if self.ty in [
            EventType.REVERB_ROTATION_SHUFFLE,
            EventType.REVERB_FULL_SHUFFLE,
            EventType.REVERB_LINEUP_SHUFFLE,
        ]:
            # skip reverb
            self.data.fetch_teams(self.event["created"], 30)
            return True
        if self.ty == EventType.PLAYER_TRADED:
            # skip feedback
            return True
        if self.ty in [EventType.INNING_END]:
            # skipping inning outing
            if self.update["inning"] == 2:
                # so if this *is* a coffee 3s game the pitchers are definitely gonna have the mod
                # even if we pulled too early to catch it getting added. so i'm cheating here who cares

                # it's also specifically permanent mods, not seasonal mods that may or may not be echoed/received
                self.print(
                    f"home pitcher mods: {self.home_pitcher.print_mods(ModType.PERMANENT)} "
                    f"({self.home_pitcher.name})"
                )
                self.print(
                    f"away pitcher mods: {self.away_pitcher.print_mods(ModType.PERMANENT)} "
                    f"({self.away_pitcher.name})"
                )
                if self.home_pitcher.has_mod(Mod.TRIPLE_THREAT, ModType.PERMANENT) or self.weather == Weather.COFFEE_3S:
                    self.roll("remove home pitcher triple threat")
                if self.away_pitcher.has_mod(Mod.TRIPLE_THREAT, ModType.PERMANENT) or self.weather == Weather.COFFEE_3S:
                    self.roll("remove away pitcher triple threat")
            # todo: salmon
            return True

        if self.ty in [
            EventType.GAME_END,
            EventType.ADDED_MOD,
            EventType.REMOVED_MOD,
            EventType.MOD_EXPIRES,
            EventType.FINAL_STANDINGS,
            EventType.TEAM_WAS_SHAMED,
            EventType.TEAM_DID_SHAME,
            EventType.ELIMINATED_FROM_POSTSEASON,
            EventType.POSTSEASON_ADVANCE,
            EventType.HYPE_BUILT,
            EventType.PRACTICING_MODERATION,
            EventType.WIN_COLLECTED_REGULAR,
            EventType.WIN_COLLECTED_POSTSEASON,
            EventType.GAME_OVER,
            EventType.BALLOONS_INFLATED,
            EventType.VOICEMAIL,
        ]:
            # skipping game end

            if self.ty == EventType.GAME_END and self.weather.is_coffee():
                # end of coffee game redaction
                rosters = (
                    self.home_team.lineup + self.home_team.rotation + self.away_team.lineup + self.away_team.rotation
                )
                for player_id in rosters:
                    player = self.data.get_player(player_id)
                    if player.has_mod(Mod.COFFEE_PERIL) and not player.has_mod(Mod.FORCE):
                        self.roll(f"redaction ({player.name})")

            return True
        if self.ty == EventType.THIEVES_GUILD_PLAYER:
            self.roll("thieves guild?")
            self.roll("thieves guild?")

            if self.event["created"] in ["2021-07-19T18:38:17.282Z", "2021-07-22T12:24:29.719Z", "2021-07-22T21:24:03.118Z", "2021-07-23T03:26:25.413Z", "2021-07-20T14:31:06.765Z", "2021-07-21T10:27:28.256Z", "2021-07-21T11:34:52.841Z"]:
                self.roll("thieves guild?")
            else:
                self.print(f"no extra thieves guild roll?")

            return True
        if self.ty == EventType.THIEVES_GUILD_ITEM:
            self.roll("thieves guild?")
            self.roll("thieves guild?")
            return True
        if self.ty in [EventType.LETS_GO]:
            # todo: figure out the real logic here, i'm sure there's some
            # a lot of these seem to be end-of-week rolls, eg. super roamin procs
            extra_start_rolls = {
                (12, 27): 9,
                (12, 99): 2,
                (12, 113): 1,
                (13, 99): 2,
                (14, 3): 2,
                (14, 27): 216, # earlsiesta reading
                (15, 27): 220, # earlsiesta reading
                (15, 57): 2,
                (15, 99): 2,
                (16, 27): 220, # earlsiesta reading
                (16, 99): 2,
                (16, 106): 1,
                (17, 27): 218, # earlsiesta reading
                # (17, 88): 1,
                (17, 99): 2,
                (18, 0): 1,
                (18, 99): 2,
                (19, 18): 13,
                (19, 27): 229, # earlsiesta reading
                (19, 36): 13,
                (19, 45): 10,
                (19, 54): 10,
                (19, 63): 10,
                (19, 81): 10,
                (19, 108): 10,
                (19, 113): 2,
                (20, 9): 10,
                (20, 63): 10,
                (20, 108): 10,
                (20, 112): 1,
                (22, 9): 14,
                (22, 18): 14,
                (22, 36): 14,
                (22, 45): 14,
                (22, 63): 14,
                (22, 72): 17569, # latesiesta (what the heck)
                (22, 81): 14,
                (22, 90): 14,
                (22, 99): 14+4, # what's the extra 4? wild card picks?
            }

            game_id = self.event["gameTags"][0] # state not setup yet

            sd = (self.event['season'], self.event['day'])
            self.print(f"game start: {sd} (zero-indexed)")  
            if sd not in self.started_days:
                self.started_days.add(sd)

                # todo: when does this go before, when does it go after?                
                for _ in range(extra_start_rolls.get(sd, 0)):
                    self.roll(f"align start {game_id} day {self.day}")

                self.start_game_day(self.event['season'], self.event['day'])


            return True
        if self.ty in [EventType.PLAY_BALL]:
            # play ball (already handled above but we want to fetch a tiny tick later)
            if self.event["day"] not in self.fetched_days:
                self.fetched_days.add(self.event["day"])

                timestamp = self.event["created"]
                self.data.fetch_league_data(timestamp, 20)

            self.print(self.stadium.mods)

            return True
        if self.ty in [EventType.FLAG_PLANTED]:
            for _ in range(11):
                self.roll("flag planted")
            return True
        if self.ty in [EventType.RENOVATION_BUILT]:
            if "% more " in self.desc or "% less " in self.desc:
                self.roll("stat change")
            return True
        if self.ty in [EventType.LIGHT_SWITCH_TOGGLED]:
            return True
        if self.ty == EventType.ELEMENT_ADDED_TO_ITEM:
            # self.print()
            return True
        if self.ty == EventType.TAROT_READING:
            return True
        if self.ty == EventType.LOVERS_LINEUP_OPTIMIZED:
            return True
        if self.ty in [EventType.EMERGENCY_ALERT, EventType.BIG_DEAL]:
            if "NEW CHALLENGERS SURFACE" in self.desc:
                # might be placing teams into divisions? divine favor? idk
                self.roll("breach team stuff")
                self.roll("breach team stuff")
                self.roll("breach team stuff")
                self.roll("breach team stuff")
                self.roll("breach team stuff")
                self.roll("breach team stuff")
                self.roll("breach team stuff")
                self.roll("breach team stuff")
                self.roll("breach team stuff")
                self.roll("breach team stuff")

                for i in range(3):  # worms-mechs-georgias
                    for j in range(9 + 5 + 11):  # lineup+rotation+shadows
                        for k in range(2 + 26 + 6):  # name+stats+interview
                            # todo: label this nicer, but these *do* line up as expected
                            self.roll(f"breach team player gen (team {i} player {j})")

                # i have no clue what this is but it makes day 73 line up.
                for _ in range(339):
                    self.roll("something else")
            return True
        if self.ty == EventType.TEAM_JOINED_LEAGUE:
            return True
        if self.ty == EventType.TEAM_INCINERATION_REPLACEMENT:
            return True
        if self.ty == EventType.TEAM_FORMED:
            return True
        if self.ty in [
            EventType.ITEM_BREAKS,
            EventType.ITEM_DAMAGE,
            EventType.PLAYER_GAINED_ITEM,
            EventType.PLAYER_LOST_ITEM,
            EventType.BROKEN_ITEM_REPAIRED,
            EventType.DAMAGED_ITEM_REPAIRED,
            EventType.TUNNEL_STOLE_ITEM,
        ]:
            if self.ty == EventType.PLAYER_GAINED_ITEM and ("gained the Prized" in self.desc or "won the Prize Match!" in self.desc):
                # prize match reward
                self.roll("prize target")

            if self.ty == EventType.PLAYER_GAINED_ITEM and "The Community Chest Opens" in self.desc:
                self.create_item(self.event, ItemRollType.CHEST, self.prev_event)
            return True
        if self.ty == EventType.PLAYER_SWAP:
            return True
        if self.ty in [EventType.PLAYER_HIDDEN_STAT_INCREASE, EventType.PLAYER_HIDDEN_STAT_DECREASE]:
            return True
        if self.ty == EventType.WEATHER_CHANGE:
            return True
        if self.ty == EventType.JAZZ:
            self.print(f"(season {self.season+1} day {self.day+1}, game {self.game_id}, {self.away_team.nickname}@{self.home_team.nickname}, at {self.stadium.nickname})")
            self.print(f"(ballpark weather: {self.stadium.weather})")
            result_weather = self.data.get_update(self.game_id, self.play+3)["weather"]

            if self.season == 23:
                riff_pool = "bah boo bee bip ska ski sha shoo skoo da doo dah dee la bow bah bop wah do doh boh louie ooie ooo ah".split()
            else:
                riff_pool = "bah boo bee bip ska ski sha shoo da doo dah dee la bow bah bop wah do doh boh louie ooie ooo ah".split()

            riff = self.desc.split("\U0001f3b5")[1]
            riff_words = [r for r in riff.split() if r in riff_pool]

            # todo: extract some kind of "scan for this roll pattern"
            found_offset = None
            for check_offset in range(25):
                r2 = Rng(self.rng.state, self.rng.offset)
                r2.step(check_offset)
                
                # i love flow control
                count = 3 + int(r2.next() * 3)
                if count != len(riff_words):
                    continue
                for word in riff_words:
                    word_roll = r2.next()
                    rolled_word = riff_pool[int(word_roll*len(riff_pool))]
                    if word != rolled_word:
                        break
                else:
                    found_offset = check_offset
                    break

            if found_offset:
                self.print(f"(found jazz riff at offset {found_offset})")
                for _ in range(check_offset-1):
                    self.roll("jazz extra?")
                weather_roll = self.roll("jazz weather")
                self.print(f"(weather index: {int(weather_roll*38)})")
                self.roll("riff length", (len(riff_words)-3)/3, (len(riff_words)-3+1)/3)

                # with open("jazz.json", "a") as f:
                #     import json
                #     f.write(json.dumps({"season": self.season, "day": self.day, "weather": result_weather, "roll": weather_roll, "upgrades": {k.value: v for k, v in self.stadium.weather.items()}}) + "\n")
                
                for word in riff_words:
                    lo, hi = 0, 1
                    if riff_pool.count(word) == 1:
                        expected_idx = riff_pool.index(word)
                        lo, hi = expected_idx/len(riff_pool), (expected_idx+1)/len(riff_pool)
                    self.roll(F"riff word ({word})", lo, hi)
            else:
                self.error(f"could not find jazz riff")

            return True
        if self.ty == EventType.COMMUNITY_CHEST_GAME_EVENT:
            # It looks like before season 18 there are 12 rolls after all of the items are created
            # regardless of the number of COMMUNITY_CHEST_GAME_EVENTs,
            # except the one at 2021-04-20T21:43:13.835Z, which has 0.
            # After that, it's apparently 1 per event.
            chests = {
                "2021-04-22T06:15:48.986Z": 12,
                "2021-04-23T14:06:46.795Z": 12,
            }

            time = self.event["created"]
            to_step = chests.get(time)
            if to_step:
                self.print(f"!!! stepping {to_step} @ {time} for Community Chest")
                self.rng.step(to_step)
            elif self.season >= 17:
                self.roll("?????")

            # todo: properly handle the item changes
            if self.event["created"] == "2021-05-11T16:05:03.662Z":
                steph_weeks = self.data.get_player("18f45a1b-76eb-4b59-a275-c64cf62afce0")
                steph_weeks.add_mod(Mod.CAREFUL, ModType.ITEM)
                steph_weeks.last_update_time = self.event["created"]

            if self.event["created"] == "2021-05-18T13:07:33.068Z":
                aldon_cashmoney_ii = self.data.get_player("194a78fd-3aa7-4356-8ba0-b9fdcbc0ea85")
                aldon_cashmoney_ii.add_mod(Mod.CAREFUL, ModType.ITEM)
                aldon_cashmoney_ii.last_update_time = self.event["created"]
            return True
        if self.ty == EventType.BALLPARK_MOD_RATIFIED:
            return True
        if self.ty == EventType.RELOAD_PROC:
            return True
        
    def handle_trader(self):
        # idk where to put this
        if self.batter.has_mod(Mod.TRADER):
            self.roll("trader (batter)")
        if self.batter.has_mod(Mod.TRAITOR):
            self.roll("traitor (batter)")
        if self.pitcher.has_mod(Mod.TRADER):
            self.roll("trader (pitcher)")
        if self.pitcher.has_mod(Mod.TRAITOR):
            self.roll("traitor (pitcher)")

        if self.ty == EventType.TRADER_TRAITOR:
            # success maybe? need to find out when this procs more specifically
            if self.season == 21:
                self.roll("trader?")
            return True

    def handle_polarity(self):
        if self.weather.is_polarity():
            # polarity +/-
            polarity_roll = self.roll("polarity")

            if self.ty == EventType.POLARITY_SHIFT:
                self.log_roll(Csv.WEATHERPROC, "Switch", polarity_roll, True)

                if "The Band began to play" in self.desc:
                    self.roll("polarity jazz")

                return True
            else:
                self.log_roll(Csv.WEATHERPROC, "NoSwitch", polarity_roll, False)

    def handle_bird_ambush(self):
        if self.weather == Weather.BIRDS:
            # todo: does this go here or nah
            # self.print("bird ambush eligible? {}s/{}b/{}o".format(self.strikes, self.balls, self.outs))
            if self.strikes == 0:
                ambush_roll = self.roll("bird ambush")
                if self.ty == EventType.FRIEND_OF_CROWS:
                    self.log_roll(
                        Csv.MODPROC,
                        "Ambushed",
                        ambush_roll,
                        True,
                    )
                    self.handle_batter_reverb()  # i guess???

                    self.damage(self.batter, "batter")  # todo: who?
                    return True

                if self.pitcher.has_mod(Mod.FRIEND_OF_CROWS) and self.ty != EventType.FRIEND_OF_CROWS:
                    self.log_roll(
                        Csv.MODPROC,
                        "NoBush",
                        ambush_roll,
                        False,
                    )

    def handle_charm(self):
        pitch_charm_eligible = self.update["atBatBalls"] == 0 and self.update["atBatStrikes"] == 0
        batter_charm_eligible = self.batting_team.has_mod(Mod.LOVE) and pitch_charm_eligible
        pitcher_charm_eligible = self.pitching_team.has_mod(Mod.LOVE) and pitch_charm_eligible

        # before season 16, love blood only proc'd when the player also had love blood
        if self.event["season"] < 15:
            if self.batter.blood != Blood.LOVE:
                batter_charm_eligible = False

            if self.pitcher.blood != Blood.LOVE:
                pitcher_charm_eligible = False

        if pitcher_charm_eligible:
            charm_roll = self.roll("charm")

            if self.batter.undefined():
                pass
                # self.roll("undefined (charm)")
                # self.roll("undefined (charm)")
                # self.roll("undefined (charm)")


            if " charmed " in self.desc:
                self.log_roll(
                    Csv.MODPROC,
                    "Charmed",
                    charm_roll,
                    True,
                )

                if not self.batter.has_mod(Mod.CAREFUL):
                    self.damage(self.batter, "batter")
                if self.season >= 15:
                    # i thought we rolled item damage 3 times
                    # but undefined tells us it's only once (for the batter)
                    # so this might be 3 rolls and 2 of them are the pitcher or something
                    self.roll("charm item damage???")
                    self.roll("charm item damage???")

                self.handle_batter_reverb()

                if self.batting_team.has_mod(Mod.PSYCHIC):
                    if self.batter.undefined():
                        self.roll("undefined (strikeout-walk)")
                        self.roll("undefined (strikeout-walk)")

                    bpsychic_roll = self.roll("strikeout-walk")
                    bpsychic_success = "uses a Mind Trick" in self.desc

                    self.log_roll(
                        Csv.BSYCHIC,
                        "Success" if bpsychic_success else "Fail",
                        bpsychic_roll,
                        bpsychic_success,
                    )
                    if bpsychic_success:
                        self.roll("charm-bpsychic item damage??")
                return True

            else:
                self.log_roll(
                    Csv.MODPROC,
                    "NoCharm",
                    charm_roll,
                    False,
                )

        if batter_charm_eligible:
            charm_roll = self.roll("charm")
            if " charms " in self.desc:
                self.log_roll(
                    Csv.MODPROC,
                    "Charmed",
                    charm_roll,
                    True,
                )
                self.damage(self.batter, "batter")
                self.damage(self.batter, "batter")
                self.damage(self.pitcher, "pitcher")
                self.damage(self.pitcher, "pitcher")

                if "scores!" in self.desc:
                    last_runner = self.data.get_player(self.update["baseRunners"][0])
                    self.damage(last_runner, "runner")

                self.handle_batter_reverb()  # apparently don mitchell can do this.
                return True

    def handle_electric(self):
        # todo: don't roll this if <s15 and batter doesn't have electric blood?
        # only case here would be baldwin breadwinner in s14 but it seems to work okay?
        if self.batting_team.has_mod(Mod.ELECTRIC) and self.update["atBatStrikes"] > 0:
            electric_roll = self.roll("electric")
            if self.ty == EventType.STRIKE_ZAPPED:
                self.log_roll(Csv.MODPROC, "Zap", electric_roll, True)
            if self.ty != EventType.STRIKE_ZAPPED:
                self.log_roll(Csv.MODPROC, "NoZap", electric_roll, False)

        if self.ty == EventType.STRIKE_ZAPPED:
            # successful zap!
            return True

    def handle_batter_reverb(self):
        if self.batter and self.batter.has_mod(Mod.REVERBERATING):
            is_at_bat_end = self.ty in [
                EventType.WALK,
                EventType.STRIKEOUT,
                EventType.FLY_OUT,
                EventType.GROUND_OUT,
                EventType.FRIEND_OF_CROWS,
            ]  # ambush i guess
            # s14: hrs/hits (type 9/10) do not trigger reverberating, this probably changed later
            # home runs might not either?

            if self.ty in [
                EventType.HOME_RUN,
                EventType.HIT,
            ]:
                # self.print("!!! warn: no reverb on hit?")
                is_at_bat_end = False

            if is_at_bat_end:
                self.roll("at bat reverb")
            if "draws a walk" in self. desc and "strikes out thinking" in self.desc:
                self.roll("psychic bug reverb")

    def handle_mild(self):
        mild_roll = self.roll("mild")
        if self.ty == EventType.MILD_PITCH:
            # skipping mild proc

            self.log_roll(Csv.MODPROC, "Mild", mild_roll, True)

            if "advance on the pathetic play" in self.desc:
                for base, runner_id in zip(self.update["basesOccupied"], self.update["baseRunners"]):
                    runner = self.data.get_player(runner_id)
                    self.damage(runner, "runner")
                    if base == Base.THIRD:
                        self.damage(runner, "runner")

            if "draws a walk." in self.desc:
                # todo: what are these? we may never know... sample size etc
                self.damage(self.batter, "batter")
                self.damage(self.batter, "batter")

            return True

        elif self.pitcher.has_mod(Mod.WILD) and self.ty != EventType.MILD_PITCH:
            self.log_roll(Csv.MODPROC, "NoMild", mild_roll, False)

    def roll_hr(self, is_hr):
        threshold = get_hr_threshold(
            self.batter, self.batting_team, self.pitcher, self.pitching_team, self.stadium, self.get_stat_meta()
        )

        roll = self.roll("home run", threshold=threshold, passed=is_hr)
        if is_hr and roll > threshold:
            self.print("!!! warn: home run roll too high ({} > {})".format(roll, threshold))
        elif not is_hr and roll < threshold:
            self.print("!!! warn: home run roll too low ({} < {})".format(roll, threshold))
        return roll

    def is_swing_check_relevant(self):
        if self.is_flinching():
            return False
        if self.batting_team.has_mod(Mod.O_NO) and self.strikes == self.max_strikes - 1:
            return False
        if self.batting_team.has_mod(Mod.ZERO) and self.is_strike and self.balls == 0 and self.strikes == 0:
            return False
        if self.batting_team.has_mod(Mod.H20) and self.is_strike and self.outs == self.max_outs - 1:
            return False
        return True

    def roll_swing(self, did_swing: bool):
        if self.is_strike:
            if self.batter.undefined():
                # div/musc/path/thwack
                self.roll("undefined (swing on strike)")            
                self.roll("undefined (swing on strike)")            
                self.roll("undefined (swing on strike)")            
                self.roll("undefined (swing on strike)")            
        else:
            if self.batter.undefined():
                # moxie/path
                self.roll("undefined (swing on ball)")            
                self.roll("undefined (swing on ball)")            

        roll = self.roll("swing")

        if self.is_strike:
            threshold = get_swing_strike_threshold(
                self.batter, self.batting_team, self.pitcher, self.pitching_team, self.stadium, self.get_stat_meta()
            )
        else:
            threshold = get_swing_ball_threshold(
                self.batter, self.batting_team, self.pitcher, self.pitching_team, self.stadium, self.get_stat_meta()
            )

        if self.is_swing_check_relevant() and "Mind Trick" not in self.desc:  # i give up
            if did_swing and roll > threshold:
                self.print(
                    "!!! warn: swing on {} roll too high ({} > {})".format(
                        "strike" if self.is_strike else "ball", roll, threshold
                    )
                )
            elif not did_swing and roll < threshold:
                self.print(
                    "!!! warn: swing on {} roll too low ({} < {})".format(
                        "strike" if self.is_strike else "ball", roll, threshold
                    )
                )

        return roll

    def roll_contact(self, did_contact: bool):
        if self.is_strike:
            threshold = get_contact_strike_threshold(
                self.batter, self.batting_team, self.pitcher, self.pitching_team, self.stadium, self.get_stat_meta()
            )

            if self.batter.undefined():
                # div/musc/path/thwack
                self.roll("undefined (contact on strike)")            
                self.roll("undefined (contact on strike)")            
                self.roll("undefined (contact on strike)")            
                self.roll("undefined (contact on strike)")            

        else:
            threshold = get_contact_ball_threshold(
                self.batter, self.batting_team, self.pitcher, self.pitching_team, self.stadium, self.get_stat_meta()
            )

            if self.batter.undefined():
                # only path?
                self.roll("undefined (contact on ball)")            

        roll = self.roll("contact")

        if not (self.batting_team.has_mod(Mod.O_NO) and self.strikes == self.max_strikes - 1):
            if did_contact and roll > threshold:
                self.print(
                    "!!! warn: contact on {} roll too high ({} > {})".format(
                        "strike" if self.is_strike else "ball", roll, threshold
                    )
                )
            elif not did_contact and roll < threshold:
                self.print(
                    "!!! warn: contact on {} roll too low ({} < {})".format(
                        "strike" if self.is_strike else "ball", roll, threshold
                    )
                )

        return roll

    def handle_ball(self):
        if "senses foul play" in self.desc:
            # does this just immediately exit???
            # happens when pitcher is hard boiled and batter has debt_zero
            self.damage(self.batter, "batter") # guessing which damage
            return

        known_outcome = "ball"
        if "strikes out" in self.desc and "uses a Mind Trick" in self.desc:
            # this was really rolled as a strike????? but not always????
            known_outcome = None

        value = self.throw_pitch(known_outcome)
        if "uses a Mind Trick" not in self.desc:
            self.log_roll(Csv.STRIKES, "Ball", value, False)

        if not self.is_flinching():
            did_swing = False
            if "strikes out looking" in self.desc:
                # i hate mind trick so much
                did_swing = True
            if "strikes out swinging" in self.desc:
                # i hate mind trick so much
                did_swing = True

            swing_roll = self.roll_swing(did_swing)
            if swing_roll < 0.05:
                ball_threshold = get_swing_ball_threshold(
                    self.batter, self.batting_team, self.pitcher, self.pitching_team, self.stadium, self.get_stat_meta()
                )

                # lol. lmao.
                if not math.isnan(ball_threshold):
                    self.print("!!! very low swing roll on ball (threshold should be {})".format(ball_threshold))
            if self.is_swing_check_relevant() and "uses a Mind Trick" not in self.desc:
                self.log_roll(Csv.SWING_ON_BALL, "Ball", swing_roll, False)

        if self.ty == EventType.WALK:
            if "uses a Mind Trick" in self.desc:
                # batter successfully converted strikeout to walk
                if "strikes out swinging." in self.desc:
                    if self.batter.undefined():
                        self.roll("undefined (psychiccontact)")
                    psychiccontact_roll = self.roll("psychiccontact")  # noqa: F841

                if self.batter.undefined() and self.batting_team.has_mod("PSYCHIC"):
                    self.roll("undefined (psychic)")
                    self.roll("undefined (psychic)")
                bsychic_roll = self.roll("bsychic")
                self.log_roll(Csv.BSYCHIC, "Success", bsychic_roll, True)

                if "draws a walk." in self.desc:
                    # a walk converted to a strikeout, that still registers as a walk type
                    # this shouldn't even be possible but occurs exactly 8 times ever...?
                    self.roll("i don't even know anymore")                
            # pitchers: convert walk to strikeout (failed)
            elif self.pitching_team.has_mod("PSYCHIC"):
                psychic_roll = self.roll("walk-strikeout")
                self.log_roll(Csv.PSYCHIC, "Fail", psychic_roll, False)

        if self.ty == EventType.WALK:
            self.handle_walk()
        else:
            self.damage(self.pitcher, "pitcher")

    def handle_walk(self):
        if self.batting_team.has_mod(Mod.BASE_INSTINCTS):
            instinct_roll = self.roll(
                "base instincts", threshold=0.2, passed="Base Instincts take them directly to" in self.desc
            )

            if "Base Instincts take them directly to" in self.desc:
                self.log_roll(Csv.MODPROC, "Walk", instinct_roll, True)
                base_roll = self.roll("which base")
                base_two_roll = self.roll("which base")

                if "Base Instincts take them directly to second base!" in self.desc:
                    # Note: The fielder roll is used here as the formula multiplies two rolls together
                    # and this is the easiest way to log two rolls at once
                    self.log_roll(
                        Csv.INSTINCTS,
                        "Second",
                        base_two_roll,
                        False,
                        fielder_roll=base_roll,
                        fielder=self.get_fielder_for_roll(base_roll),
                    )
                if "Base Instincts take them directly to third base!" in self.desc:
                    self.log_roll(
                        Csv.INSTINCTS,
                        "Third",
                        base_two_roll,
                        True,
                        fielder_roll=base_roll,
                        fielder=self.get_fielder_for_roll(base_roll),
                    )
            if "Base Instincts take them directly to" not in self.desc:
                self.log_roll(Csv.MODPROC, "Balk", instinct_roll, False)

        for base, runner_id in zip(self.update["basesOccupied"], self.update["baseRunners"]):
            runner = self.data.get_player(runner_id)
            if base == Base.THIRD:
                if runner.raw_name in self.desc and "scores" in self.desc:
                    self.damage(runner, "runner")
            if base == Base.SECOND and "Base Instincts" in self.desc and "scores" in self.desc:
                if runner.raw_name in self.desc:
                    self.damage(runner, "runner")
            if base == Base.FIRST and "Base Instincts" in self.desc and "scores" in self.desc:
                if runner.raw_name in self.desc:
                    self.damage(runner, "runner")

        self.damage(self.pitcher, "pitcher")
        self.damage(self.batter, "batter")

    def handle_strike(self):
        if ", swinging" in self.desc or "strikes out swinging." in self.desc:
            if self.batter.undefined():
                self.print(f"UNDEFINED STRIKE SWINGING")

            self.throw_pitch()

            if not self.is_flinching():
                swing_roll = self.roll_swing(True)

                if self.is_swing_check_relevant():
                    self.log_roll(
                        Csv.SWING_ON_STRIKE if self.is_strike else Csv.SWING_ON_BALL,
                        "StrikeSwinging",
                        swing_roll,
                        True,
                    )

            contact_roll = self.roll_contact(False)
            self.log_roll(Csv.CONTACT, "StrikeSwinging", contact_roll, False)
        elif ", looking" in self.desc or "strikes out looking." in self.desc:
            if self.batter.undefined():
                self.print(f"UNDEFINED STRIKE LOOKING")
            value = self.throw_pitch("strike")
            if "uses a Mind Trick" not in self.desc:
                self.log_roll(Csv.STRIKES, "StrikeLooking", value, True)
            if "uses a Mind Trick" in self.desc:
                self.log_roll(Csv.STRIKES, "PsyBall", value, False)

            if not self.is_flinching():
                swing_roll = self.roll_swing(False)

                if self.is_swing_check_relevant():
                    self.log_roll(Csv.SWING_ON_STRIKE, "StrikeLooking", swing_roll, False)

        if "strikes out thinking." in self.desc:
            # pitcher: convert walk to strikeout (success)
            # not logging these rn
            self.roll("strike")
            self.roll("swing")
            mindtrick_roll = self.roll("Psychic")
            self.log_roll(Csv.PSYCHIC, "Success", mindtrick_roll, True)

        elif ", flinching" in self.desc:
            value = self.throw_pitch("strike")
            self.log_roll(Csv.STRIKES, "StrikeFlinching", value, True)

        elif "strikes out" in self.desc:
            if self.batter.undefined():
                self.print(f"UNDEFINED STRIKEOUT")

            # batters: convert strikeout to walk (failed)
            if self.batting_team.has_mod(Mod.PSYCHIC):
                if self.batter.undefined():
                    self.roll("undefined (strikeout-walk)")
                    self.roll("undefined (strikeout-walk)")

                bpsychic_roll = self.roll("strikeout-walk")
                self.log_roll(
                    Csv.BSYCHIC,
                    "Fail",
                    bpsychic_roll,
                    False,
                )

            if self.pitcher.has_mod(Mod.PARASITE) and self.weather == Weather.BLOODDRAIN:
                self.roll("parasite")  # can't remember what this is

        self.damage(self.pitcher, "pitcher")

    def try_roll_salmon(self, holiday_inning=False):
        # don't reroll if we *just* reset
        if "The Salmon swim upstream!" in self.update["lastUpdate"]:
            return

        last_inning = self.next_update["inning"] - 1
        # If we're rolling during the holiday Inning update,
        # the next inning hasn't started yet.
        if holiday_inning:
            last_inning += 1
        if self.weather == Weather.SALMON and last_inning >= 0 and not self.update["topOfInning"]:
            last_inning_away_score, last_inning_home_score = self.find_start_of_inning_score(self.game_id, last_inning)
            current_away_score, current_home_score = (
                self.next_update["awayScore"],
                self.next_update["homeScore"],
            )

            # only roll salmon if the last inning had any scores, but also we have to dig into game history to find this
            # how does the sim do it? no idea. i'm cheating.
            if current_away_score != last_inning_away_score or current_home_score != last_inning_home_score:
                salmon_roll = self.roll("salmon")
                self.log_roll(Csv.WEATHERPROC, "NoSalmon", salmon_roll, False)

    def is_flinching(self):
        return self.batter.has_mod(Mod.FLINCH) and self.strikes == 0

    def get_fielder_for_roll(self, fielder_roll: float, ignore_elsewhere: bool = True):
        candidates = [self.data.get_player(player) for player in self.pitching_team.lineup]
        if ignore_elsewhere:
            candidates = [c for c in candidates if not c.has_mod(Mod.ELSEWHERE)]

        player = candidates[math.floor(fielder_roll * len(candidates))]
        return player

    def roll_out(self, was_out):
        out_fielder_roll, out_fielder = self.roll_fielder(check_name=False)
        out_threshold = get_out_threshold(
            self.batter,
            self.batting_team,
            self.pitcher,
            self.pitching_team,
            out_fielder,
            self.stadium,
            self.get_stat_meta(),
        )

        if out_fielder.undefined():
            self.roll("undefined (fielder out threshold)")

        if self.batter.undefined():
            self.roll("undefined (batter out threshold)")


        # high roll = out, low roll = not out
        out_roll = self.roll(f"out (to {out_fielder.name})", threshold=out_threshold, passed=not was_out)

        if was_out:
            self.log_roll(
                Csv.OUT,
                "Out",
                out_roll,
                False,
                fielder_roll=out_fielder_roll,
                fielder=out_fielder,
            )
        else:
            self.log_roll(
                Csv.OUT,
                "In",
                out_roll,
                True,
                fielder_roll=out_fielder_roll,
                fielder=out_fielder,
            )

        return out_roll, out_threshold

    def handle_out(self):
        self.throw_pitch()

        if not self.is_flinching():
            swing_roll = self.roll_swing(True)
            if self.is_swing_check_relevant():
                self.log_roll(
                    Csv.SWING_ON_STRIKE if self.is_strike else Csv.SWING_ON_BALL,
                    "Out",
                    swing_roll,
                    True,
                )
        contact_roll = self.roll_contact(True)
        self.log_roll(Csv.CONTACT, "Out", contact_roll, True)
        self.roll_foul(False)

        is_fc_dp = "into a double play!" in self.desc or "reaches on fielder's choice" in self.desc

        fly_threshold = get_fly_or_ground_threshold(
            self.batter, self.batting_team, self.pitcher, self.pitching_team, self.stadium, self.get_stat_meta()
        )

        named_fielder = None
        if self.ty == EventType.FLY_OUT:  # flyout
            self.roll_out(True)

            if self.batter.undefined():
                # buoy/supp
                # self.roll("undefined (fly?)")
                pass

            fly_fielder_roll, fly_fielder = self.roll_fielder(check_name=not is_fc_dp)

            if self.batter.undefined():
                self.roll("undefined (fly?)")
                self.roll("undefined (fly?)")
            fly_roll = self.roll("fly", threshold=fly_threshold, passed=True)

            self.log_roll(
                Csv.FLY,
                "Flyout",
                fly_roll,
                True,
                fielder_roll=fly_fielder_roll,
                fielder=fly_fielder,
            )
            named_fielder = fly_fielder
        elif self.ty == EventType.GROUND_OUT:  # ground out
            self.roll_out(True)
            fly_fielder_roll, fly_fielder = self.roll_fielder(check_name=False)
            self.print(f"(fly fielder is {fly_fielder.name})")
            
            if self.batter.undefined():
                # buoy/supp
                self.roll("undefined (fly?)")
                self.roll("undefined (fly?)")
            fly_roll = self.roll("fly", threshold=fly_threshold, passed=False)

            ground_fielder_roll, ground_fielder = self.roll_fielder(check_name=not is_fc_dp)
            self.print(f"(ground fielder is {ground_fielder.name})")
            self.log_roll(
                Csv.FLY,
                "GroundOut",
                fly_roll,
                False,
                fielder_roll=ground_fielder_roll,
                fielder=ground_fielder,
            )
            named_fielder = ground_fielder

        if self.season >= 20:
            if self.batter.undefined():
                self.roll("undefined (upgrade out)")
                self.roll("undefined (upgrade out)")
            upgrade_roll = self.roll("upgrade out?")

            self.log_roll(Csv.UPGRADE_OUT, "ToHit" if self.ty == EventType.GROUND_OUT else "ToHomeRun", upgrade_roll, False)
            if upgrade_roll < 0.01:
                self.error("something is misaligned, this should have been upgraded to a hit/hr")

        if self.outs < self.max_outs - 1:
            if self.ty == EventType.FLY_OUT:
                self.damage(self.pitcher, "pitcher")
                self.damage(self.batter, "fielder")
                self.damage(named_fielder, "fielder")
            self.handle_out_advances(named_fielder)
        if not self.outs < self.max_outs - 1:
            self.try_roll_batter_debt(named_fielder)
            self.damage(self.pitcher, "pitcher")
            if not is_fc_dp:
                self.damage(self.batter, "fielder")
            if named_fielder and not is_fc_dp:
                self.damage(named_fielder, "fielder")

        
        if self.batter.undefined():
            # self.roll("undefined (idk yet)")
            # self.roll("undefined (idk yet)")

            if "into a double play!" not in self.desc:
                pass
                # self.roll("undefined (idk yet)")

            if not is_fc_dp:
                pass
                # self.roll("undefined (idk yet)")
                # for _ in self.update["baseRunners"]:
                    # self.roll("undefined (idk yet)")
                    # self.roll("undefined (idk yet)")

        if self.ty == EventType.GROUND_OUT and self.stadium.has_mod(Mod.FLOOD_BALLOONS):
            # i think this roll is after damage but the other one is before, judging by 2021-06-26T19:07:03.771Z
            self.roll("flood balloons?")
            if "was struck and popped" in self.desc:
                self.roll("how many popped?")

    def try_roll_batter_debt(self, fielder):
        if (self.batter.has_mod(Mod.DEBT_THREE) or self.batter.has_mod(Mod.DEBT_ZERO)) and fielder and not (fielder.has_mod(Mod.COFFEE_PERIL) or fielder.has_mod(Mod.MARKED)):
            self.roll("batter debt")

    def roll_fielder(self, check_name=True, skip_elsewhere=True):
        eligible_fielders = []
        fielder_idx = None
        desc = ""
        # cut off extra parts with potential name collisions
        if check_name:
            desc = self.desc.split("out to ")[1]
            if "advances on the sacrifice" in desc or "tags up and scores!" in desc:
                desc = desc.rsplit(". ", 1)[0]  # damn you kaj statter jr.

        for fielder_id in self.pitching_team.lineup:
            fielder = self.data.get_player(fielder_id)
            if skip_elsewhere and fielder.has_mod(Mod.ELSEWHERE):
                continue

            if check_name:
                if fielder.raw_name in desc:
                    fielder_idx = len(eligible_fielders)
            eligible_fielders.append(fielder)

        if check_name and fielder_idx is not None:
            expected_min = fielder_idx / len(eligible_fielders)
            expected_max = (fielder_idx + 1) / len(eligible_fielders)
        else:
            expected_min = 0
            expected_max = 1
        roll_value = self.roll("fielder", lower=expected_min, upper=expected_max)

        rolled_idx = int(roll_value * len(eligible_fielders))

        if fielder_idx is not None:
            if rolled_idx != fielder_idx:
                self.error(
                    f"incorrect fielder! expected {fielder_idx}, got {rolled_idx}, "
                    f"needs to be {expected_min:.3f}-{expected_max:.3f}\n"
                    f"{self.rng.get_state_str()}"
                )

            matching = []
            r2 = Rng(self.rng.state, self.rng.offset)
            check_range = 50
            r2.step(-check_range)
            for i in range(check_range * 2):
                val = r2.next()
                if int(val * len(eligible_fielders)) == fielder_idx:
                    matching.append(i - check_range + 1)
            self.print(f"(matching offsets: {matching})")
        elif check_name:
            if "fielder's choice" not in self.desc and "double play" not in self.desc:
                self.print("!!! could not find fielder (name wrong?)")

        return roll_value, eligible_fielders[rolled_idx]

    def handle_out_advances(self, fielder):
        # special case for a chron data gap - ground out with no runners (so no rolls), but the game update is missing
        if self.event["created"] == "2021-04-07T08:02:52.078Z":
            return

        def did_advance(base, runner_id):
            if runner_id not in self.update["baseRunners"]:
                return False
            if runner_id not in self.next_update["baseRunners"]:
                return True
            new_runner_idx = self.next_update["baseRunners"].index(runner_id)
            new_runner_base = self.next_update["basesOccupied"][new_runner_idx]
            return new_runner_base != base

        self.print(
            "OUT {} {} -> {}".format(
                self.ty.value,
                self.update["basesOccupied"],
                self.next_update["basesOccupied"],
            )
        )

        if self.ty == EventType.FLY_OUT:
            self.try_roll_batter_debt(fielder)
            base_before_home = Base.FOURTH if self.stadium.has_mod(Mod.EXTRA_BASE) else Base.THIRD

            # this might be bugged for fifth base? see: 2021-06-24T10:13:01.604Z
            is_third_free = 2 not in self.update["basesOccupied"]
            for base, runner_id in zip(self.update["basesOccupied"], self.update["baseRunners"]):
                runner = self.data.get_player(runner_id)

                # yes, *not* checking self.next_update
                # this is my explanation for why [1, 0] -> [2, 1] never happens
                # (it still thinks second is occupied even when they move)
                is_next_free = (base + 1) not in self.update["basesOccupied"]
                if base == Base.SECOND and is_third_free:
                    is_next_free = True

                roll_outcome = did_advance(base, runner_id)

                if is_next_free:
                    adv_roll = self.roll(f"adv? {base}/{runner.name} ({roll_outcome})")
                    self.log_roll(
                        Csv.FLYOUT, f"advance_{base}", adv_roll, roll_outcome, fielder=fielder, relevant_runner=runner
                    )

                    if runner.undefined():
                        self.roll("undefined (runner advance)")

                    if roll_outcome:
                        self.damage(runner, "batter")

                        # the logic does properly "remove" the runner when scoring from third, though
                        if base == base_before_home:
                            is_third_free = True
                            self.damage(runner, "batter")
                    else:
                        break

        elif self.ty == EventType.GROUND_OUT:
            if len(self.update["basesOccupied"]) > 0:
                # roll needs batter tragicness, fielder tenaciousness, pitcher shakespearianism
                dp_roll = self.roll("dp?")
                if self.batter.undefined():
                    # tragicness?
                    # the control flow is really weird here
                    # if there's no player on first, why would it roll for batter but not for fielder...?
                    # unless it's something else, i guess
                    self.roll("undefined (dp batter)")

                if Base.FIRST in self.update["basesOccupied"]:
                    if fielder.undefined():
                        self.roll("undefined (dp fielder)")
                        pass

                    is_dp = "into a double play!" in self.desc
                    is_fc = "on fielder's choice" in self.desc
                    self.log_roll(Csv.GROUNDOUT_FORMULAS, "DP", dp_roll, is_dp, fielder=fielder)

                    if is_dp:
                        # ...wait, is this just the martyr? roll?
                        self.roll("dp where")  # (index into basesOccupied)

                        # todo:this interacts weirdly with undefined
                        self.damage(self.pitcher, "pitcher")

                        if self.outs < self.max_outs - 2:
                            for base, runner_id in zip(self.next_update["basesOccupied"], self.next_update["baseRunners"]):
                                runner = self.data.get_player(runner_id)
                                self.damage(runner, "runner")

                        if "scores!" in self.desc:
                            # assuming this is always first?
                            scoring_runner = self.data.get_player(self.update["baseRunners"][0])

                            # "surviving" player takes damage (including scoring) but they get swept from bases
                            # so we just roll twice here
                            self.damage(scoring_runner, "runner")
                            self.damage(scoring_runner, "runner")

                        self.damage(self.pitcher, "pitcher")

                        return

                    if self.batter.undefined():
                        self.roll("undefined (martyr?)")

                    # needs batter martyrdom, runner indulgence
                    fc_roll = self.roll("martyr?")  # high = fc
                    self.log_roll(Csv.GROUNDOUT_FORMULAS, "Sac", fc_roll, not is_fc, fielder=fielder)

                    if is_fc:
                        # so this is a rough outline, we could probably clean up this logic
                        damage_runners = []

                        if self.update["basesOccupied"] == [2, 1, 0]:
                            damage_runners = [1, 0]  # does not include a 2 atvl
                        elif self.update["basesOccupied"] == [1, 0]:
                            damage_runners = [0]  # unsure
                        elif self.update["basesOccupied"] == [2, 0]:
                            damage_runners = [2, 2]  # this one is correct... or maybe not?
                            if self.stadium.has_mod(Mod.EXTRA_BASE):
                                damage_runners = [2]
                        elif self.update["basesOccupied"] == [0]:
                            damage_runners = []
                        elif self.update["basesOccupied"] == [3, 0]:
                            damage_runners = [3, 3]  # unsure
                        elif self.update["basesOccupied"] == [3, 1, 0]:
                            damage_runners = [3, 3, 1]  # unsure but there's 3
                        elif self.update["basesOccupied"] == [3, 2, 0]:
                            damage_runners = [3, 3, 2] # also unsure but there's 3

                        self.damage(self.pitcher, "pitcher")

                        for rbase in damage_runners:
                            idx = self.update["basesOccupied"].index(rbase)
                            runner_id = self.update["baseRunners"][idx]
                            runner = self.data.get_player(runner_id)
                            self.damage(runner, "runner")

                        return

            # as of s24, this is before item rolls for sure
            # see: 2021-07-28T10:08:43.892Z
            self.try_roll_batter_debt(fielder)

            self.damage(self.pitcher, "pitcher")
            # there's some weird stuff with damage rolls in the first fragment of s16
            # this seems to work for groundouts but something similar might be up for flyouts
            if (self.season, self.day) >= (15, 3):
                self.damage(self.batter, "fielder")
                self.damage(fielder, "fielder")

            forced_bases = 0
            while forced_bases in self.update["basesOccupied"]:
                forced_bases += 1

            base_before_home = Base.FOURTH if self.stadium.has_mod(Mod.EXTRA_BASE) else Base.THIRD
            for base, runner_id in zip(self.update["basesOccupied"], self.update["baseRunners"]):
                runner = self.data.get_player(runner_id)

                was_forced = base < forced_bases
                if self.event["created"] in ["2021-05-12T13:20:27.312Z", "2021-05-17T19:19:27.034Z"]:
                    # did_advance gets confused because the same runner is on two bases.
                    roll_outcome = True
                else:
                    roll_outcome = did_advance(base, runner_id) if not was_forced else None

                # needs... fielder tenaciousness and runner indulgence?
                adv_roll = self.roll(f"adv? {base}/{runner.name} ({roll_outcome})")
                if self.batter.undefined() and base == base_before_home: # sac?
                    # self.roll("undefined (advance batter)")
                    pass
                if runner.undefined():
                    self.roll("undefined (advance runner)")
                if fielder.undefined():
                    self.roll("undefined (runner adv fielder)")

                if roll_outcome and base == base_before_home and not was_forced:
                    # when a runner scores from third, it "ignores" forcing logic
                    # ie. [2, 0] -> [0] is possible! (first *isn't* forced to second. even if they probably should)
                    forced_bases = 0

                if roll_outcome is not None:
                    self.log_roll(
                        Csv.GROUNDOUT_FORMULAS,
                        "advance",
                        adv_roll,
                        roll_outcome,
                        fielder=fielder,
                        relevant_runner=runner,
                    )

                if roll_outcome or was_forced:
                    self.damage(runner, "batter")

                    if base == base_before_home:
                        if (self.season, self.day) >= (15, 3):
                            self.damage(runner, "batter")

                        else:
                            self.damage(self.batter, "batter")

            if (self.season, self.day) < (15, 3):
                self.damage(self.batter, "fielder")
                self.damage(fielder, "fielder")
                pass

    def handle_hit_advances(self, bases_hit, defender_roll):
        bases_before = make_base_map(self.update)
        bases_after = make_base_map(self.next_update)
        base_before_home = Base.FOURTH if self.stadium.has_mod(Mod.EXTRA_BASE) else Base.THIRD
        for runner_id, base, roll_outcome in calculate_advances(
            bases_before, bases_after, bases_hit, base_before_home + 1
        ):
            runner = self.data.get_player(runner_id)
            fielder = self.get_fielder_for_roll(defender_roll)

            advance_threshold = get_advance_on_hit_threshold(
                runner,
                fielder,
                self.pitching_team,
                self.stadium,
                self.get_stat_meta(),
            )
            # work around missing data in next_update
            if self.event["created"] == "2021-04-14T15:11:04.159Z":
                roll_outcome = False
            roll = self.roll(f"adv ({base}, {roll_outcome}", passed=roll_outcome, threshold=advance_threshold)

            if runner.undefined():
                self.roll("undefined (runner adv?)")
                pass

            if fielder.undefined():
                self.roll("undefined (runner adv? from fielder)")

            if base == Base.SECOND:
                self.log_roll(
                    Csv.HITADVANCE,
                    "second",
                    roll,
                    roll_outcome,
                    relevant_runner=runner,
                    fielder_roll=defender_roll,
                    fielder=fielder,
                )
            elif base == Base.THIRD:
                self.log_roll(
                    Csv.HITADVANCE,
                    "third",
                    roll,
                    roll_outcome,
                    relevant_runner=runner,
                    fielder_roll=defender_roll,
                    fielder=fielder,
                )
            elif base == Base.FOURTH:
                self.log_roll(
                    Csv.HITADVANCE,
                    "fourth (of five)",
                    roll,
                    roll_outcome,
                    relevant_runner=runner,
                    fielder_roll=defender_roll,
                    fielder=fielder,
                )

            # damage scores on extra advances
            if base == base_before_home and roll_outcome:
                self.damage(runner, "runner")
    
    # run this after the out roll. maybe this should just be in there...?
    def get_predicted_upgrade_roll(self):
        if self.ty == EventType.HIT:
            step_count = 3
        elif self.ty == EventType.HOME_RUN:
            step_count = 2
            
        if self.batter.undefined():
            step_count += 4

        self.rng.step(step_count)
        predicted_upgrade_roll = self.rng.next()
        self.rng.step(-step_count-1)
        return predicted_upgrade_roll

    def handle_hr(self):
        if " is Magmatic!" not in self.desc:
            self.throw_pitch()
            if not self.is_flinching():
                swing_roll = self.roll_swing(True)
                if self.is_swing_check_relevant():
                    self.log_roll(
                        Csv.SWING_ON_STRIKE if self.is_strike else Csv.SWING_ON_BALL,
                        "HR",
                        swing_roll,
                        True,
                    )

            contact_roll = self.roll_contact(True)
            self.log_roll(Csv.CONTACT, "HomeRun", contact_roll, True)

            self.roll_foul(False)

            # if this is a REAL home run, and not an UPGRADED home run, add here
            # (will only be applicable when formula guesses wrong)
            fakeout_overrides = [
                "2021-06-26T16:26:38.648Z",
                "2021-06-21T19:25:24.958Z",
                "2021-06-21T18:05:12.440Z",
                "2021-06-24T01:00:44.658Z",
                "2021-06-24T11:01:45.168Z",
                "2021-07-22T04:30:17.323Z",
                "2021-07-22T04:30:58.532Z",
                "2021-07-22T05:13:12.739Z",
                "2021-07-22T05:14:53.149Z",
                "2021-07-22T05:22:34.266Z",
                "2021-07-22T07:22:09.275Z",
                "2021-07-28T10:09:47.050Z",
                "2021-07-22T23:15:19.145Z",
                "2021-07-23T02:01:52.146Z",
                "2021-07-23T04:14:53.537Z",
            ]

            out_roll, out_threshold = self.roll_out(False)

            # assuming this can never be >0.04
            predicted_upgrade_roll = self.get_predicted_upgrade_roll()

            if self.season >= 20 and out_roll > out_threshold and self.event["created"] not in fakeout_overrides and predicted_upgrade_roll < 0.04:
                fly_threshold = get_fly_or_ground_threshold(
                    self.batter, self.batting_team, self.pitcher, self.pitching_team, self.stadium, self.get_stat_meta()
                )

                self.print("--- fake home run")
                self.roll("out/fielder")
                if self.batter.undefined():
                    self.roll("undefined (fly?)")
                    self.roll("undefined (fly?)")
                self.roll("out/fly", threshold=fly_threshold, passed=True)
                if self.batter.undefined():
                    self.roll("undefined (upgrade out)")
                    self.roll("undefined (upgrade out)")
                upgrade_roll = self.roll("upgrade out? (to hr)") # this roll is definitely the one that handles upgrades
                self.log_roll(Csv.UPGRADE_OUT, "ToHomeRun", upgrade_roll, True)
                self.roll("???") # ...so then, what is this?
            else:
                if self.batter.undefined():
                    # just divinity?
                    self.roll("undefined (home run)")
                hr_roll = self.roll_hr(True)
                self.log_roll(Csv.HR, "HomeRun", hr_roll, True)
        else:
            # not sure why we need this
            self.roll("magmatic")

        for runner_id in self.update["baseRunners"]:
            runner = self.data.get_player(runner_id)
            self.damage(runner, "batter")

        self.damage(self.batter, "batter")

        if self.stadium.has_mod(Mod.BIG_BUCKET):
            if self.batter.undefined():
                self.roll("undefined (big bucket)")

            buckets_roll = self.roll("big buckets")
            if "lands in a Big Bucket." in self.desc:
                self.log_roll(
                    Csv.MODPROC,
                    "Bucket",
                    buckets_roll,
                    True,
                )
                return
            else:
                self.log_roll(
                    Csv.MODPROC,
                    "NoBucket",
                    buckets_roll,
                    False,
                )

        if self.stadium.has_mod(Mod.HOOPS):
            if self.batter.undefined():
                self.roll("undefined (hoops)")
                self.roll("undefined (hoops)")

            hoops_roll = self.roll("hoops")

            if "went up for the alley oop" in self.desc:
                self.log_roll(
                    Csv.MODPROC,
                    "HoopsAttempt",
                    hoops_roll,
                    True,
                )

                hoops_success_roll = self.roll("hoop success")

                if self.batter.undefined():
                    self.roll("undefined (hoop success)")

                if "slammed it down for an extra Run" in self.desc:
                    self.log_roll(
                        Csv.MODPROC,
                        "HoopsSuccess",
                        hoops_success_roll,
                        True,
                    )
                    return
                else:
                    self.log_roll(
                        Csv.MODPROC,
                        "HoopsFailed",
                        hoops_success_roll,
                        False,
                    )
            else:
                self.log_roll(
                    Csv.MODPROC,
                    "NoHoopsAttempt",
                    hoops_roll,
                    False,
                )

        # air balloons were ratified in s21 latesiesta so would turn into a sim mod (todo: make sim mod check nicer)
        if self.stadium.has_mod(Mod.AIR_BALLOONS) or Mod.AIR_BALLOONS.name in self.data.sim["attr"]:
            self.roll("pop balloon?")
            if "struck and popped" in self.desc:
                self.roll("num birds scared")

    def handle_base_hit(self):
        self.throw_pitch()
        if not self.is_flinching():
            swing_roll = self.roll_swing(True)
            if self.is_swing_check_relevant():
                self.log_roll(
                    Csv.SWING_ON_STRIKE if self.is_strike else Csv.SWING_ON_BALL,
                    "BaseHit",
                    swing_roll,
                    True,
                )

        hit_bases = 0
        if "hits a Single!" in self.desc:
            hit_bases = 1
        elif "hits a Double!" in self.desc:
            hit_bases = 2
        elif "hits a Triple!" in self.desc:
            hit_bases = 3
        elif "hits a Quadruple!" in self.desc:
            hit_bases = 4

        contact_roll = self.roll_contact(True)
        self.log_roll(Csv.CONTACT, "BaseHit", contact_roll, True)

        self.roll_foul(False)
        out_roll, out_threshold = self.roll_out(False)

        if self.batter.undefined():
            self.print("UNDEFINED BASE HIT")

        # if this is a REAL hit, and not an UPGRADED hit, add here
        # (will only be applicable when formula guesses wrong)
        # i think these can only be singles, too, so might need to skip the double/triple checks
        fakeout_override = [
            "2021-06-25T22:15:33.133Z",
            "2021-06-26T20:19:15.403Z",
            "2021-06-26T17:02:37.346Z",
            "2021-06-26T17:08:22.349Z",
            "2021-06-25T23:07:27.894Z",
            "2021-06-25T23:20:26.239Z", # nandy messes with this one
            "2021-06-21T18:15:43.297Z",
            "2021-06-21T18:31:21.376Z",
            "2021-06-21T19:07:43.405Z",
            "2021-06-21T17:24:40.494Z",
            "2021-06-21T20:19:22.784Z",
            "2021-06-21T22:36:07.964Z",
            "2021-06-21T23:22:37.547Z",
            "2021-06-22T00:08:40.094Z",
            "2021-06-23T22:22:31.785Z",
            "2021-06-23T23:11:56.372Z",
            "2021-06-23T23:33:42.272Z",
            "2021-06-24T01:10:31.261Z",
            "2021-06-24T02:13:40.364Z",
            "2021-06-24T03:05:20.852Z",
            "2021-06-24T04:04:15.335Z",
            "2021-06-24T04:20:18.197Z",
            "2021-06-24T04:23:15.438Z",
            "2021-06-24T04:29:20.787Z",
            "2021-06-24T05:05:50.921Z",
            "2021-06-24T12:10:52.501Z",
            "2021-06-29T05:11:15.911Z",
            "2021-06-29T05:17:16.187Z",
            "2021-06-29T06:20:31.478Z",
            "2021-06-29T07:13:11.048Z",
            "2021-06-29T08:09:20.717Z",
            "2021-06-29T08:14:11.799Z",
            "2021-07-22T03:16:12.216Z",
            "2021-07-22T03:17:37.595Z",
            "2021-07-22T04:05:28.163Z",
            "2021-07-22T05:04:25.970Z",
            "2021-07-22T05:08:31.085Z",
            "2021-07-22T06:07:32.321Z",
            "2021-07-22T06:13:08.081Z",
            "2021-07-22T06:16:15.006Z",
            "2021-07-22T07:19:01.756Z",
            "2021-07-22T07:19:08.939Z",
            "2021-07-22T07:22:54.380Z",
            "2021-07-22T07:23:08.516Z",
            "2021-07-30T12:19:39.626Z",
            "2021-07-28T10:00:51.442Z",
            "2021-07-28T10:03:16.709Z",
            "2021-07-28T10:04:32.487Z",
            "2021-07-28T10:20:46.023Z",
            "2021-07-28T10:21:55.166Z",
            "2021-07-28T10:25:05.937Z",
        ]

        fakeout_opposite_overrides = [
            # these ones are ACTUALLY fake
            "2021-06-21T20:06:14.133Z",
            "2021-06-23T22:13:01.358Z",
            "2021-06-24T03:05:50.319Z",
            "2021-06-24T05:09:20.868Z",
            "2021-07-28T09:24:31.243Z",
            "2021-07-23T04:09:42.750Z",
            "2021-07-22T09:18:04.254Z",
            "2021-07-20T07:02:43.599Z",
            "2021-07-20T05:04:09.215Z",
        ]

        # cheating a little to predict the future etc
        # we're assuming this can never roll >0.04 and still pass, as a heuristic to avoid too many manual overrides
        predicted_upgrade_roll = self.get_predicted_upgrade_roll()

        is_fake_single = False
        if self.season >= 20 and "a Single" in self.desc and predicted_upgrade_roll < 0.04 and (out_roll > out_threshold and self.event["created"] not in fakeout_override) or (self.event["created"] in fakeout_opposite_overrides):
            is_fake_single = True
            
            fly_threshold = get_fly_or_ground_threshold(
                self.batter, self.batting_team, self.pitcher, self.pitching_team, self.stadium, self.get_stat_meta()
            )

            self.print("--- fake single")
            self.roll("out/fielder")

            if self.batter.undefined():
                self.roll("undefined (fly?)")
                self.roll("undefined (fly?)")
            self.roll("out/fly", threshold=fly_threshold, passed=False)
            self.roll("out/fielder")
            if self.batter.undefined():
                self.roll("undefined (upgrade out)")
                self.roll("undefined (upgrade out)")

            upgrade_roll = self.roll("upgrade out? (to hit)")
            self.log_roll(Csv.UPGRADE_OUT, "ToHit", upgrade_roll, True)
        else:
            if self.batter.undefined():
                # div?
                self.roll("undefined (hr)")

            hr_roll = self.roll_hr(False)                
            self.log_roll(Csv.HR, "BaseHit", hr_roll, False)

        fielder_roll, fielder = self.roll_fielder(check_name=False)

        double_threshold = get_double_threshold(
            self.batter,
            self.batting_team,
            self.pitcher,
            self.pitching_team,
            fielder,
            self.stadium,
            self.get_stat_meta(),
        )
        triple_threshold = get_triple_threshold(
            self.batter,
            self.batting_team,
            self.pitcher,
            self.pitching_team,
            fielder,
            self.stadium,
            self.get_stat_meta(),
        )

        if is_fake_single:
            # fake singles can only ever be singles - we still roll for them but results are ignored, so the roll logs aren't useful
            double_threshold = None
            triple_threshold = None

        if self.batter.undefined():
            # musc and gf?
            self.roll("undefined (base hit)")
            self.roll("undefined (base hit)")

        if fielder.undefined():
            # chasiness
            self.roll("undefined (double?)")
            # self.roll("undefined (double?)")
            self.roll("undefined (triple?)")
            # self.roll("undefined (triple?)")

        double_passed = {1: False, 2: True, 3: None, 4: None}[hit_bases]
        double_roll = self.roll(f"double (to {fielder.name})", threshold=double_threshold, passed=double_passed)
        triple_passed = hit_bases == 3 if hit_bases < 4 else None
        triple_roll = self.roll(f"triple (to {fielder.name})", threshold=triple_threshold, passed=triple_passed)

        quadruple_roll = None
        if self.stadium.has_mod(Mod.EXTRA_BASE):
            quadruple_roll = self.roll("quadruple")

        if not is_fake_single:
            if hit_bases < 3:
                self.log_roll(
                    Csv.DOUBLES,
                    f"Hit{hit_bases}",
                    double_roll,
                    hit_bases == 2,
                    fielder_roll=fielder_roll,
                    fielder=fielder,
                )

            self.log_roll(
                Csv.TRIPLES,
                f"Hit{hit_bases}",
                triple_roll,
                hit_bases == 3,
                fielder_roll=fielder_roll,
                fielder=fielder,
            )

            if quadruple_roll:
                self.log_roll(
                    Csv.QUADRUPLES,
                    f"Hit{hit_bases}",
                    quadruple_roll,
                    hit_bases == 4,
                    fielder_roll=fielder_roll,
                    fielder=fielder,
                )

        self.damage(self.pitcher, "pitcher")
        self.damage(self.batter, "batter")

        if self.batting_team.has_mod(Mod.AAA) and hit_bases == 3:
            # todo: figure out if this checks mod origin or not
            if not self.batter.has_mod(Mod.OVERPERFORMING, ModType.GAME):
                self.roll("power chAAArge")

        if self.batting_team.has_mod(Mod.AA) and hit_bases == 2:
            # todo: figure out if this checks mod origin or not
            if not self.batter.has_mod(Mod.OVERPERFORMING, ModType.GAME):
                self.roll("power chAArge")

        self.handle_hit_advances(hit_bases, fielder_roll)

        # tentative: damage every runner at least once?
        for base, runner_id in zip(self.update["basesOccupied"], self.update["baseRunners"]):
            runner = self.data.get_player(runner_id)
            self.damage(runner, "batter")

            last_base = 4 if self.stadium.has_mod(Mod.EXTRA_BASE) else 3
            is_force_score = base >= (last_base - hit_bases)  # fifth base lol
            if is_force_score and self.event["created"] != "2021-04-23T13:30:43.331Z":
                self.damage(runner, "batter")

    def get_stat_meta(self):
        is_maximum_blaseball = (
            self.strikes == self.max_strikes - 1
            and self.balls == self.max_balls - 1
            and self.outs == self.max_outs - 1
            and self.update["basesOccupied"] == [Base.THIRD, Base.SECOND, Base.FIRST]
        )
        batter_count = (
            self.next_update["awayTeamBatterCount"]
            if self.next_update["topOfInning"]
            else self.next_update["homeTeamBatterCount"]
        )
        batter_at_bats = batter_count // len(self.batting_team.lineup)  # todo: +1?
        return StatRelevantData(
            self.weather,
            self.season,
            self.day,
            len(self.update["basesOccupied"]),
            self.update["topOfInning"],
            is_maximum_blaseball,
            batter_at_bats,
        )

    def roll_foul(self, known_outcome: bool):
        is_0_no_eligible = self.batting_team.has_mod(Mod.O_NO) and self.strikes == 2 and self.balls == 0
        if is_0_no_eligible:  # or self.batter.has_any(Mod.CHUNKY, Mod.SMOOTH):
            known_outcome = None

        meta = self.get_stat_meta()
        threshold = get_foul_threshold(self.batter, self.batting_team, self.stadium, meta)

        if self.batter.undefined():
            # musc/thwack/div
            self.roll("undefined (foul)")
            self.roll("undefined (foul)")
            self.roll("undefined (foul)")

        foul_roll = self.roll("foul", threshold=threshold, passed=known_outcome)
        if known_outcome is not None:
            if known_outcome and foul_roll > threshold:
                self.print(f"!!! too high foul roll ({foul_roll} > {threshold})")

                if foul_roll > 0.5:
                    self.print("!!! very too high foul roll")
            elif not known_outcome and foul_roll < threshold:
                self.print(f"!!! too low foul roll ({foul_roll} < {threshold})")
        outcomestr = "Foul" if known_outcome else "Fair"

        if self.batter.undefined():
            pass

        self.log_roll(Csv.FOULS, outcomestr, foul_roll, known_outcome)

    def handle_foul(self):
        self.throw_pitch()

        if self.batter.undefined():
            self.print("!UNDEFINED FOUL")

        if not self.is_flinching():
            swing_roll = self.roll_swing(True)
            if self.is_swing_check_relevant():
                self.log_roll(
                    Csv.SWING_ON_STRIKE if self.is_strike else Csv.SWING_ON_BALL,
                    "Foul",
                    swing_roll,
                    True,
                )

        contact_roll = self.roll_contact(True)
        self.log_roll(Csv.CONTACT, "Foul", contact_roll, True)

        self.roll_foul(True)

        if self.batter.undefined():
            self.roll("undefined (foul?)")
            self.roll("undefined (filth tenac)")
            # self.data.fetch_stadiums(self.event["created"])
            # filth_before = self.data.get_stadium(self.stadium.id).filthiness
            # self.data.fetch_stadiums(self.event["created"], 10)
            # filth_after = self.data.get_stadium(self.stadium.id).filthiness

            # tenac_mul = get_multiplier(self.batter, self.batting_team, "batter", "tenaciousness", self.get_stat_meta(), self.stadium)
            # tenac = self.batter.multiplied("tenaciousness", tenac_mul)
            # indul_mul = get_multiplier(self.batter, self.batting_team, "batter", "indulgence", self.get_stat_meta(), self.stadium)
            # indul = self.batter.indulgence
            # calc_delta = (6 - 4*(tenac - indul)) * 0.00001 * 5
            # real_delta = filth_after-filth_before
            
            # self.print(f"filth: {filth_before} -> {filth_after}, delta {filth_after-filth_before}, expected delta {calc_delta}")
            # self.print(f"tenac: {tenac}, mul: {tenac_mul}, indul: {indul}, mul: {indul_mul}")
            # self.print(self.batter.items)

            # if self.batter.undefined():
            #     possible_stat_rolls = [self.roll('undefined (foul)') for _ in range(5)]

            #     for i, tenac_roll in enumerate(possible_stat_rolls):
            #         # for j, indul_roll in enumerate(possible_stat_rolls):
            #         mod_tenac = tenac * (1.5 + 0.5*tenac_roll) #self.batter.multiplied("tenaciousness", tenac_mul + 0.5 + 0.5*tenac_roll)
            #         mod_indul = indul# * (1.5 + 0.5*indul_roll)
            #         modified_delta = (6 - 4*(mod_tenac - mod_indul)) * 0.00001 * 5
            #         self.print(f"delta using rolls {i}/{tenac_roll} = {modified_delta}, matches? {abs(modified_delta-real_delta)<0.000001}")

        if self.batter.has_mod(Mod.OFFWORLD):
            self.roll("offworld")
            self.roll("offworld")

        self.damage(self.pitcher, "pitcher")
        self.damage(self.batter, "batter")

    def check_filth_delta(self, expected_change=None):
        # todo: this is very unreliable because of fetch resolution
        pass
        # self.data.fetch_stadiums(self.event["created"])
        # filth_before = self.data.get_stadium(self.stadium.id).filthiness
        # self.data.fetch_stadium_after(self.stadium.id, self.event["created"])
        # filth_after = self.data.get_stadium(self.stadium.id).filthiness
        # if filth_before != filth_after:
        #     self.print(f"!!!FILTH CHANGED: {filth_before} -> {filth_after}")
            
        #     delta = filth_after - filth_before
        #     if expected_change and abs(expected_change - delta) > 0.000001:
        #         self.print(f"!!! warn: expected filth change of {expected_change}, found {delta}")


    def handle_batter_up(self):
        batter = self.batter
        if self.ty == EventType.BATTER_SKIPPED:
            # find the batter that *would* have been at bat
            lineup = self.batting_team.lineup
            index = (
                self.next_update["awayTeamBatterCount"]
                if self.next_update["topOfInning"]
                else self.next_update["homeTeamBatterCount"]
            )
            batter_id = lineup[index % len(lineup)]
            batter = self.data.get_player(batter_id)

        if self.ty in [EventType.BATTER_UP, EventType.BATTER_SKIPPED]:
            if batter and batter.has_mod(Mod.HAUNTED):
                haunt_roll = self.roll("haunted")
                self.log_roll(Csv.MODPROC, "NoHaunt", haunt_roll, False)

            # if the haunting is successful the batter won't be the haunted player lol
            if "is Inhabiting" in self.event["description"]:
                haunt_roll = self.roll("haunted")
                self.log_roll(Csv.MODPROC, "YesHaunt", haunt_roll, True)

                self.roll("haunter selection")

            if self.ty == EventType.BATTER_UP:
                # no proc on elsewhere
                if batter.has_mod(Mod.SKIPPING):
                    self.roll("skipping")
                    self.roll("skipping")

            return True
        

    # fire eater and unstable players on roster?
    def handle_fire_eater(self, rolled_unstable=False):
        # unstable fire eaters take priority over stable fire eaters.
        fire_eater_eligible = itertools.chain(
            filter(lambda p: self.data.get_player(p).has_mod(Mod.MARKED), self.pitching_team.lineup),
            filter(lambda p: not self.data.get_player(p).has_mod(Mod.MARKED), self.pitching_team.lineup),
            [
                self.batter.id,
                self.pitcher.id,
            ],
        )

        for player_id in fire_eater_eligible:
            player = self.data.get_player(player_id)

            if player.has_mod(Mod.MARKED) and player_id != self.batter.id and not rolled_unstable and not player.has_mod(Mod.ELSEWHERE):
                self.roll(f"unstable {player.name}")
                rolled_unstable = True

                if self.ty == EventType.INCINERATION:
                    # todo: merge this block with the one in the incineration block one once we understand how flow works
                    self.roll("instability target?")
                    self.roll("instability target?")
                    self.generate_player()
                    self.roll("extra instability stuff??")
                    self.roll("extra instability stuff??")
                    return True
            if player.has_mod(Mod.FIRE_EATER) and not player.has_mod(Mod.ELSEWHERE):
                self.roll(f"fire eater ({player.name})")

                if self.ty == EventType.INCINERATION_BLOCKED:
                    # fire eater proc - target roll maybe?
                    self.roll("target")
                    return True
                break

    def handle_weather(self):
        if self.weather == Weather.SUN_2:
            pass

        elif self.weather in [Weather.ECLIPSE, Weather.SUPERNOVA_ECLIPSE]:
            # this block needs a big refactor, we can probably make the unstable checks generic
            threshold = self.get_eclipse_threshold()
            rolled_unstable = False
            eclipse_roll = self.roll("eclipse")

            if self.batter.has_mod(Mod.MARKED):
                self.roll(f"unstable {self.batter.name}")
                rolled_unstable = True
            if self.pitcher.has_mod(Mod.MARKED):
                self.roll(f"unstable {self.pitcher.name}")
                rolled_unstable = True

            target = None
            if self.event["playerTags"]:
                target = self.data.get_player(self.event["playerTags"][0])

            # this really needs a refactor, helga and jon's instability incins need to proc in the sub function (and they do)
            if self.ty == EventType.INCINERATION and "Kansas City Breath Mints" not in self.desc and self.event["created"] not in ["2021-07-22T06:03:17.918Z", "2021-07-22T06:06:08.970Z", "2021-07-23T10:04:54.389Z", "2021-05-14T11:21:35.835Z"]:
                if "A Debt was collected" not in self.desc:
                    self.log_roll(Csv.WEATHERPROC, "Burn", eclipse_roll, True)

                    self.roll("target")

                    if self.season >= 15:
                        self.roll("extra target?")
                else:
                    self.roll("instability target?")
                    self.roll("instability target?")

                self.generate_player()

                # there are def two extra rolls earlier and two extra down here, but i don't know what they would be
                if "A Debt was collected" in self.desc:
                    self.roll("extra instability stuff??")
                    self.roll("extra instability stuff??")

                if "An Ambush." in self.desc:
                    self.roll("ambush target")

                return True

            else:
                self.log_roll(Csv.WEATHERPROC, "NoBurn", eclipse_roll, False)

            if eclipse_roll < threshold:
                # blocked "natural" incineration due to fireproof
                # self.print(f"!!! too low eclipse roll ({eclipse_roll} < {threshold})")

                if self.ty == EventType.INCINERATION_BLOCKED and (self.pitching_team.has_mod(Mod.FIREPROOF) or target.has_mod(Mod.FIREPROOF)):
                    self.roll("target")
                    return True
                
            if self.handle_fire_eater(rolled_unstable):
                return True
            
            if self.weather == Weather.SUPERNOVA_ECLIPSE:
                self.roll("supernova eclipse (team incin)")
                if self.ty == EventType.INCINERATION:
                    # riv
                    if "Kansas City Breath Mints" in self.desc:
                        for _ in range(8):
                            self.roll("where are the paws, joel?")

                        self.data.fetch_league_data(self.event["created"], 10)
                        # correction for fetch league data
                        self.data.fetch_player_after("df4da81a-917b-434f-b309-f00423ee4967", self.event["created"])
                    return True


        elif self.weather == Weather.GLITTER:
            # this is handled inside the ballpark proc block(?????)
            pass

        elif self.weather == Weather.BLOODDRAIN:
            blood_roll = self.roll("blooddrain")
            drain_threshold = 0.00065 - 0.001 * self.stadium.fortification
            if self.ty != EventType.BLOODDRAIN and blood_roll < drain_threshold:
                self.print("NoDrain?")
            if self.ty == EventType.BLOODDRAIN:
                self.log_roll(
                    Csv.WEATHERPROC,
                    "Drain",
                    blood_roll,
                    True,
                )
            else:
                self.log_roll(
                    Csv.WEATHERPROC,
                    "NoDrain",
                    blood_roll,
                    False,
                )

            # Drained Stat for both Siphon & Blooddrain is:
            # Pitching 0-0.25, Batting 0.25-0.5, Defense 0.5-0.75, Baserunning 0.75-1
            if self.ty == EventType.BLOODDRAIN_SIPHON:
                self.roll("which siphon")
                target_roll = self.roll("Active or Passive Target")
                pitchers = self.pitching_team.lineup + self.pitching_team.rotation
                batters = self.batting_team.lineup

                # Siphon on Siphon Violence - They all conveniently fall into the same roll length
                if self.event["created"] in [
                    "2021-03-11T16:07:06.900Z",
                    "2021-04-16T02:23:37.186Z",
                    "2021-05-19T14:06:37.515Z",
                    "2021-06-14T21:06:33.264Z",
                ]:
                    self.roll("siphon1")
                    self.roll("siphon2")

                else:
                    for player_id in pitchers:
                        pitcher = self.data.get_player(player_id)
                        if pitcher.has_mod(Mod.SIPHON) and pitcher.raw_name in self.desc:
                            pitchersiphon = True

                            if pitchersiphon:
                                if target_roll > 0.5 and len(self.update["baseRunners"]) > 0:
                                    self.roll("siphon target")
                                    self.roll("which stat drained")
                                    self.roll("effect")
                                else:
                                    self.roll("which stat drained")
                                    self.roll("effect")

                    for player_id in batters:
                        batter = self.data.get_player(player_id)
                        if batter.has_mod(Mod.SIPHON) and batter.raw_name in self.desc:
                            battersiphon = True

                            if battersiphon:
                                for base, runner_id in zip(self.update["basesOccupied"], self.update["baseRunners"]):
                                    runner = self.data.get_player(runner_id)
                                if len(self.update["baseRunners"]) > 0 and runner.raw_name in self.desc:
                                    self.roll("which stat drained")
                                    self.roll("effect")
                                else:
                                    if target_roll > 0.5 or player_id == self.batter.id:
                                        self.roll("siphon target")
                                        self.roll("which stat drained")
                                        self.roll("effect")
                                    else:
                                        self.roll("which stat drained")
                                        self.roll("effect")

                if self.event["created"] == "2021-04-12T22:01:16.338Z":
                    # this... might be item damage on siphon strikeout...?
                    self.roll("sorry kidror idk why")
                return True

            if self.ty == EventType.BLOODDRAIN or self.ty == EventType.BLOODDRAIN_BLOCKED:
                # This one thinks that an on base runner is the batter
                if self.event["created"] in ["2021-04-20T06:31:02.337Z"]:
                    self.roll("blooddrain proc1")
                    self.roll("blooddrain proc2")
                    self.roll("blooddrain proc3")
                    self.roll("Drained Stat")
                elif (
                    len(self.update["baseRunners"]) > 0
                    and self.batter.raw_name not in self.desc
                    and self.pitcher.raw_name not in self.desc
                ):
                    self.roll("blooddrain proc1")
                    self.roll("blooddrain proc2")
                    self.roll("blooddrain proc3")
                    self.roll("blooddrain proc4")
                    self.roll("Drained Stat")
                elif self.batter.raw_name in self.desc and self.pitcher.raw_name in self.desc:
                    self.roll("blooddrain proc1")
                    self.roll("blooddrain proc2")
                    self.roll("Drained Stat")
                else:
                    self.roll("blooddrain proc1")
                    self.roll("blooddrain proc2")
                    self.roll("blooddrain proc3")
                    self.roll("Drained Stat")
                return True

        elif self.weather == Weather.PEANUTS:
            flavor_roll = self.roll("peanuts")

            if self.ty == EventType.PEANUT_FLAVOR_TEXT:
                self.roll("peanut message")
                return True
            
            has_allergic_players = False

            # need to do this the annoying way because inhabiting players don't exist
            batter_id = self.update["awayBatter"] if self.update["topOfInning"] else self.update["homeBatter"]
            for player_id in (
                self.batting_team.lineup
                + self.batting_team.rotation
                + self.pitching_team.lineup
                + self.pitching_team.rotation
                + self.update["baseRunners"] + [batter_id]
            ):
                player = self.data.get_player(player_id)
                # in game da1fd5a4-45bb-4dd3-811a-ebfb34fddd07, Kaylee Boyea haunts, who's the only allergic player "in the game", and thus needs an extra roll
                if player.peanut_allergy or player_id in ["cab95673-f31b-4fb1-9764-25ceb03dd761"]:
                    has_allergic_players = True

            if has_allergic_players:
                allergy_roll = self.roll("peanuts")
                if self.ty == EventType.ALLERGIC_REACTION or self.ty == EventType.SUPERALLERGIC_REACTION:
                    self.log_roll(
                        Csv.WEATHERPROC,
                        "Allergy",
                        allergy_roll,
                        True,
                    )
                    self.roll("target")
                    if self.ty == EventType.SUPERALLERGIC_REACTION:
                        self.roll("superallergy???")
                    return True
                else:
                    self.log_roll(
                        Csv.WEATHERPROC,
                        "NoAllergy",
                        allergy_roll,
                        False,
                    )

            # def has_allergies(team):
                # return any(self.data.get_player(p).peanut_allergy for p in team.lineup + team.rotation)
            batter_threshold = 0.00076 # at least 2021-05-17T17:20:09.894Z 
            pitcher_threshold = 0.00061
            extras = [
                "2021-05-12T15:20:57.747Z", # not impossible this is something else because this threshold is 10x higher???
            ]
            if self.batter.has_mod(Mod.HONEY_ROASTED):
                roast_roll = self.roll("honey roasted")

                if self.ty == EventType.TASTE_THE_INFINITE:
                    self.log_roll(
                        Csv.MODPROC,
                        "shelled1",
                        roast_roll,
                        True,
                    )
                elif roast_roll < batter_threshold or self.event["created"] in extras:
                    self.roll("honey roasted extra")
                else:
                    self.log_roll(
                        Csv.MODPROC,
                        "no shell1",
                        roast_roll,
                        False,
                    )
            elif self.pitcher.has_mod(Mod.HONEY_ROASTED):
                poast_roll = self.roll("honey roasted")
                if self.ty == EventType.TASTE_THE_INFINITE:
                    self.log_roll(
                        Csv.MODPROC,
                        "shelled2",
                        poast_roll,
                        True,
                    )
                elif poast_roll < pitcher_threshold or self.event["created"] in extras:
                    self.roll("honey roasted extra")
                else:
                    self.log_roll(
                        Csv.MODPROC,
                        "no shell2",
                        poast_roll,
                        False,
                    )

            if self.ty == EventType.TASTE_THE_INFINITE:
                # *really* can't figure out what this is for
                self.roll("target")
                self.roll("target")
                return True

        elif self.weather == Weather.BIRDS:
            # threshold is at 0.0125 at 0.5 fort
            bird_threshold = 0.0125 - 0.02 * (self.stadium.fortification - 0.5)
            if self.season == 17:
                # in season 18 *specifically*, threshold changed a little (then changed back)
                bird_threshold = 0.015 - 0.02 * (self.stadium.fortification - 0.5)

            bird_roll = self.roll("birds", threshold=bird_threshold)

            has_shelled_player = False
            for player_id in (
                self.pitching_team.lineup
                + self.pitching_team.rotation
                + self.batting_team.lineup
                + self.batting_team.rotation
            ):
                # if low roll and shelled player present, roll again
                # in s14 this doesn't seem to check (inactive) pitchers
                # (except all shelled pitchers are inactive so idk)
                player = self.data.get_player(player_id)
                # also must be specifically PERMANENT mods - moses mason
                # (shelled in s15 through receiver, so seasonal mod) is exempt
                if player.has_mod(Mod.SHELLED, ModType.PERMANENT):
                    has_shelled_player = True

            if self.ty == EventType.BIRDS_CIRCLE:
                # the birds circle...
                self.log_roll(Csv.BIRD_MESSAGE, "Circle", bird_roll, True)
                return True
            elif not has_shelled_player:
                self.log_roll(Csv.BIRD_MESSAGE, "NoCircle", bird_roll, False)

            if has_shelled_player and bird_roll < bird_threshold:
                self.roll("extra bird roll")
                if self.ty == EventType.BIRDS_UNSHELL:
                    # ???
                    self.roll("extra bird roll")
                    return True
                pass

        elif self.weather == Weather.FEEDBACK:
            select_roll = self.roll("feedbackselection")  # noqa: F841 60/40 Batter/Pitcher
            feedback_roll = self.roll("feedback")  # noqa: F841 feedback event y/n
            if self.ty == EventType.FEEDBACK_SWAP:
                self.log_roll(
                    Csv.WEATHERPROC,
                    "Swap",
                    feedback_roll,
                    True,
                )
            else:
                self.log_roll(
                    Csv.WEATHERPROC,
                    "NoSwap",
                    feedback_roll,
                    False,
                )

            if self.ty == EventType.FEEDBACK_SWAP:
                # todo: how many rolls?
                self.roll("target")
                self.roll("player 1 fate")
                self.roll("player 2 fate")

                if "LCD Soundsystem" in self.desc:
                    for _ in range(50):
                        self.roll("stat")
                # i think it would be extremely funny if these are item damage rolls
                # imagine getting feedbacked to charleston *and* you lose your shoes.
                if self.season >= 15:
                    # todo: ideally should replace with self.damage; need player references for that
                    self.roll("feedback item damage")
                    self.roll("feedback item damage")

                return True

            if self.ty == EventType.FEEDBACK_BLOCKED:
                self.roll("target")
                for _ in range(25):
                    self.roll("stat")
                return True

            if self.weather.can_echo() and (
                (self.batter and self.batter.has_mod(Mod.ECHO)) or (self.pitcher and self.pitcher.has_mod(Mod.ECHO))
            ):
                # echo vs static, or batter echo vs pitcher echo?
                if self.ty in [EventType.ECHO_MESSAGE, EventType.ECHO_INTO_STATIC, EventType.RECEIVER_BECOMES_ECHO]:
                    eligible_players = []
                    if self.pitcher.has_mod(Mod.ECHO):
                        eligible_players.extend(self.batting_team.rotation)
                        eligible_players = [self.batter.id] + eligible_players

                        # opposite_pitcher = self.away_pitcher if self.update["topOfInning"] else self.home_pitcher
                        # eligible_players.remove(opposite_pitcher.id)
                        # eligible_players = [opposite_pitcher.id] + eligible_players
                    else:
                        eligible_players.extend(self.pitching_team.lineup)

                        if (self.season, self.day) > (13, 74):
                            eligible_players.extend(self.pitching_team.rotation)
                            eligible_players.remove(self.pitcher.id)

                        eligible_players = [self.pitcher.id] + eligible_players

                    self.handle_echo_target_selection(eligible_players)

                    if self.ty in [
                        EventType.ECHO_INTO_STATIC,
                        EventType.RECEIVER_BECOMES_ECHO,
                    ]:
                        self.roll("echo target 2?")
                    return True
        elif self.weather == Weather.REVERB:
            if self.stadium.has_mod(Mod.ECHO_CHAMBER):
                chamber_roll = self.roll("echo chamber")
                if self.ty == EventType.ECHO_CHAMBER:
                    self.log_roll(
                        Csv.MODPROC,
                        "Copy",
                        chamber_roll,
                        True,
                    )
                if self.ty != EventType.ECHO_CHAMBER:
                    self.log_roll(
                        Csv.MODPROC,
                        "NoCopy",
                        chamber_roll,
                        False,
                    )
                if self.ty == EventType.ECHO_CHAMBER:
                    self.roll("echo chamber")
                    return True
            # This might not be the right place to remove it, but ECHO_MESSAGE events with ECHO_CHAMBERs seem to have one fewer roll.
            if not self.stadium.has_mod(Mod.ECHO_CHAMBER) or self.ty != EventType.ECHO_MESSAGE:
                wiggle_roll = self.roll("reverbproc")
                if self.ty == EventType.REVERB_ROSTER_SHUFFLE:
                    self.log_roll(
                        Csv.WEATHERPROC,
                        "Shuffle",
                        wiggle_roll,
                        True,
                    )
                else:
                    self.log_roll(
                        Csv.WEATHERPROC,
                        "NoShuffle",
                        wiggle_roll,
                        False,
                    )
            if self.ty == EventType.REVERB_ROSTER_SHUFFLE:
                # approx. ranges for reverb type:
                # S13–16:
                # 0–0.15: Add reverberating mod
                # 0.15–0.25: full team shuffle
                # 0.25-0.35: several players shuffled
                # 0.35–0.4: lineup shuffle
                # 0.4–0.7: unknown (no rolls in this range)
                # 0.7–1: rotation shuffle
                #
                # S17+
                # No reverberating mod events observed
                # 0–0.09: full team shuffle
                # 0.09–0.55: several players shuffled
                # 0.55–0.95: lineup shuffled
                # 0.95–1: rotation shuffled
                self.roll("Reverb Type")
                target_roll = self.roll("target team")
                target_team = self.home_team if target_roll < 0.5 else self.away_team

                if "were shuffled in the Reverb!" in self.desc:
                    # Steph Weeks has gravity mod from armor, but we don't handle mods from old-style items.
                    if self.event["created"] == "2021-03-11T08:24:46.288Z":
                        amount = 14
                    else:
                        amount = sum(
                            1
                            for p in target_team.lineup + target_team.rotation
                            if not self.data.get_player(p).has_mod(Mod.GRAVITY)
                        )
                    for _ in range(amount):
                        self.roll("reverb shuffle?")
                elif "several players shuffled" in self.desc:
                    num_swaps = math.ceil(self.roll("num swaps") * 3) + 1
                    amount = num_swaps * 2
                    for _ in range(amount):
                        self.roll("reverb shuffle?")
                elif "lineup shuffled in the Reverb!" in self.desc:
                    amount = sum(1 for p in target_team.lineup if not self.data.get_player(p).has_mod(Mod.GRAVITY))
                    for _ in range(amount):
                        self.roll("reverb shuffle?")
                else:
                    amount = sum(1 for p in target_team.rotation if not self.data.get_player(p).has_mod(Mod.GRAVITY))
                    for _ in range(amount):
                        self.roll("reverb shuffle?")

                return True

            if self.ty == EventType.REVERB_BESTOWS_REVERBERATING:
                self.roll("Reverb Type")
                return True

            if self.batter.has_mod(Mod.ECHO):
                self.roll("echo?")

                if self.ty in [EventType.ECHO_MESSAGE, EventType.ECHO_INTO_STATIC, EventType.RECEIVER_BECOMES_ECHO]:
                    eligible_players = self.batting_team.lineup + self.batting_team.rotation
                    eligible_players.remove(self.batter.id)
                    self.handle_echo_target_selection(eligible_players)

                    if self.ty in [EventType.ECHO_INTO_STATIC, EventType.RECEIVER_BECOMES_ECHO]:
                        self.roll("echo target 2?")
                    return True
            if self.pitcher.has_mod(Mod.ECHO):
                self.roll("echo?")

                if self.ty in [EventType.ECHO_MESSAGE, EventType.ECHO_INTO_STATIC, EventType.RECEIVER_BECOMES_ECHO]:
                    eligible_players = self.pitching_team.lineup + self.pitching_team.rotation
                    eligible_players.remove(self.pitcher.id)
                    self.handle_echo_target_selection(eligible_players)
                    return True

        elif self.weather == Weather.BLACK_HOLE:
            pass

        elif self.weather == Weather.COFFEE:
            coffee1_roll = self.roll("coffee")
            if self.ty == EventType.COFFEE_BEAN and not self.stadium.has_mod(Mod.SWEETENER):
                self.log_roll(
                    Csv.WEATHERPROC,
                    "Bean",
                    coffee1_roll,
                    True,
                )
            if self.ty != EventType.COFFEE_BEAN and not self.stadium.has_mod(Mod.SWEETENER):
                self.log_roll(
                    Csv.WEATHERPROC,
                    "NoBean",
                    coffee1_roll,
                    False,
                )
            if self.ty == EventType.COFFEE_BEAN and self.stadium.has_mod(Mod.SWEETENER):
                self.log_roll(
                    Csv.SWEET1,
                    "Bean",
                    coffee1_roll,
                    True,
                )
            if self.ty != EventType.COFFEE_BEAN and self.stadium.has_mod(Mod.SWEETENER):
                self.log_roll(
                    Csv.SWEET1,
                    "NoBean",
                    coffee1_roll,
                    False,
                )

            if self.ty == EventType.COFFEE_BEAN:
                quality_roll = self.roll("coffee proc1")  # noqa: F841
                flavor_roll = self.roll("coffee proc")  # noqa: F841

                return True

            if self.batter.has_mod(Mod.COFFEE_PERIL) or self.pitcher.has_mod(Mod.COFFEE_PERIL):
                self.roll("observed?")

        elif self.weather == Weather.COFFEE_2:
            coffee2_roll = self.roll("coffee 2")
            if self.ty == EventType.GAIN_FREE_REFILL and not self.stadium.has_mod(Mod.SWEETENER):
                self.log_roll(Csv.WEATHERPROC, "Refill", coffee2_roll, True)
            if self.ty != EventType.GAIN_FREE_REFILL and not self.stadium.has_mod(Mod.SWEETENER):
                self.log_roll(Csv.WEATHERPROC, "NoRefill", coffee2_roll, False)
            if self.ty == EventType.GAIN_FREE_REFILL and self.stadium.has_mod(Mod.SWEETENER):
                self.log_roll(Csv.SWEET2, "Refill", coffee2_roll, True)
            if self.ty != EventType.GAIN_FREE_REFILL and self.stadium.has_mod(Mod.SWEETENER):
                self.log_roll(Csv.SWEET2, "NoRefill", coffee2_roll, False)

            if self.ty == EventType.GAIN_FREE_REFILL:
                quality_roll = self.roll("coffee 2 proc1")  # noqa: F841
                flavor_one_roll = self.roll("coffee 2 proc2")  # noqa: F841
                flavor_two_roll = self.roll("coffee 2 proc3")  # noqa: F841
                return True

            if self.batter.has_mod(Mod.COFFEE_PERIL) or self.pitcher.has_mod(Mod.COFFEE_PERIL):
                self.roll("observed?")

        elif self.weather == Weather.COFFEE_3S:
            if self.batter.has_mod(Mod.COFFEE_PERIL) or self.pitcher.has_mod(Mod.COFFEE_PERIL):
                self.roll("observed?")
            pass

        elif self.weather == Weather.FLOODING:
            pass

        elif self.weather == Weather.SALMON:
            pass

        elif self.weather.is_polarity():
            # this is handled after party roll...?
            pass

        elif self.weather == Weather.NIGHT:
            # rolled at least after party time?
            pass
        elif self.weather == Weather.BLACK_HOLE_BLACK_HOLE:
            pass
        else:
            self.print(f"error: {self.weather.name} weather not implemented")

    def handle_echo_target_selection(self, target_ids):
        target_roll = self.roll("echo target")

        all_players = []
        players_with_mods = []
        for player_id in target_ids:
            player = self.data.get_player(player_id)
            all_players.append(player)
            if player.mods:
                players_with_mods.append(player)

        self.print("all players:")
        for i, player in enumerate(all_players):
            self.print(
                "- {} ({}/{}, {:.03f}-{:.03f}) {}".format(
                    player.name,
                    i,
                    len(all_players),
                    i / len(all_players),
                    (i + 1) / len(all_players),
                    player.print_mods(),
                )
            )
        self.print("players with mods:")
        for i, player in enumerate(players_with_mods):
            self.print(
                "- {} ({}/{}, {:.03f}-{:.03f})".format(
                    player.name,
                    i,
                    len(players_with_mods),
                    i / len(players_with_mods),
                    (i + 1) / len(players_with_mods),
                )
            )

        self.print(f"(hit {players_with_mods[int(target_roll * len(players_with_mods))].name})")

    def handle_flooding(self):
        if self.weather == Weather.FLOODING:
            if self.update["basesOccupied"]:
                flood_roll = self.roll("flooding")
                if self.ty == EventType.FLOODING_SWEPT:
                    self.log_roll(
                        Csv.WEATHERPROC,
                        "Swept",
                        flood_roll,
                        True,
                    )
                else:
                    self.log_roll(
                        Csv.WEATHERPROC,
                        "NoSweep",
                        flood_roll,
                        False,
                    )

            if self.ty == EventType.FLOODING_SWEPT:
                undertakers = []
                players = (
                    self.batting_team.lineup + self.batting_team.rotation
                )  # + self.pitching_team.lineup + self.pitching_team.rotation
                for player_id in players:
                    player = self.data.get_player(player_id)
                    if (
                        player.has_mod(Mod.UNDERTAKER)
                        and not player.has_any(Mod.ELSEWHERE)
                    ):
                        self.print(f"(have undertaker: {player.name})")
                        undertakers.append(player)

                # handle flood
                swept_players = []
                successful_undertakers = set()
                for runner_id in self.update["baseRunners"]:
                    runner = self.data.get_player(runner_id)

                    exempt_mods = [Mod.EGO1, Mod.SWIM_BLADDER]

                    # unsure when this change was made
                    # we have Pitching Machine (with ego2) swept elsewhere on season 16 day 10
                    # and Aldon Cashmoney (also ego2) kept on base on season 16 day 65
                    if (self.season, self.day) >= (15, 64):
                        exempt_mods += [Mod.EGO2, Mod.EGO3, Mod.EGO4, Mod.LEGENDARY]
                    if not runner.has_any(*exempt_mods):
                        sweep_roll = self.roll(f"sweep ({runner.name})")

                        if f"{runner.raw_name} was swept Elsewhere" in self.desc or f"{runner.raw_name} is swept Elsewhere" in self.desc:
                            self.log_roll(Csv.SWEEP, "Sweep", sweep_roll, True, relevant_runner=runner)
                            swept_players.append(runner_id)

                            if not runner.has_mod(Mod.NEGATIVE):
                                for undertaker in undertakers:
                                    if runner_id != undertaker.id and undertaker.id not in successful_undertakers:
                                        was_successful_dive = (undertaker.raw_name + " dove in") in self.desc
                                        undertaker_threshold = 0.65 if self.season > 18 else 0.4

                                        self.roll("undertaker")
                                        self.roll("undertaker", threshold=undertaker_threshold, passed=was_successful_dive)

                                        if was_successful_dive:
                                            successful_undertakers.add(undertaker.id)
                                            break
                        else:
                            self.log_roll(Csv.SWEEP, "NoSweep", sweep_roll, False, relevant_runner=runner)

                if self.stadium.id and not self.stadium.has_mod(Mod.FLOOD_PUMPS):
                    filth_roll = self.roll("filthiness")
                    expected_filth_delta = 0.00008 + filth_roll*0.00007 if self.season > 13 else 0.00005 + filth_roll*0.00005
                    if self.stadium.has_mod(Mod.ANTI_FLOOD_PUMPS):
                        expected_filth_delta *= 5
                    self.check_filth_delta(expected_filth_delta)

                return True

    def handle_elsewhere_scattered(self):
        # looks like elsewhere and scattered get rolled separately at least in s14?
        # not sure what the cancel logic is here

        # "why not use self.batting_team"
        # well! there's a bug with half-inning-ending grind rail outs that they won't properly reset the inning state
        # and the other team's batter isn't reset. and for some reason, this means the game doesn't roll elsewhere for
        # the next half inning
        # see: https://reblase.sibr.dev/game/027f022e-eecc-48db-a25e-5dfb01f91c7c#55f2d7c5-846b-8dfc-66a2-cd6586dd980f
        team = self.batting_team
        plate_types = [
            EventType.BATTER_UP,
            EventType.BATTER_SKIPPED,
        ]
        if self.update["awayBatter"] and not self.update["topOfInning"] and self.ty not in plate_types:
            return
        if self.update["homeBatter"] and self.update["topOfInning"] and self.ty not in plate_types:
            return

        players = team.lineup + team.rotation
        did_elsewhere_return = False

        seekers = []

        # Event at 2021-06-16T12:22:05.398Z has 3 elsewhere players & 1 seeker.
        # The result is the seeker pulling a player back, and it seems to use 5 rolls.
        # The first roll is low, so it must be the seeker. Unclear if
        # it does all seeker rolls first or interleaves them.
        for player_id in players:
            player = self.data.get_player(player_id)
            if player.has_mod(Mod.SEEKER) and not player.has_mod(Mod.ELSEWHERE):
                seekers.append(player)

        for player_id in players:
            player = self.data.get_player(player_id)

            if player.has_mod(Mod.ELSEWHERE):
                pulled_back = (
                    self.ty == EventType.RETURN_FROM_ELSEWHERE and f"{player.raw_name} was pulled back" in self.desc
                )
                returned = (
                    self.ty == EventType.RETURN_FROM_ELSEWHERE and not pulled_back and player.raw_name in self.desc
                )

                if pulled_back and len(seekers) > 1:
                    self.print(f"!!! multiple seekers in play")

                # it seems to roll seeker for all eligible elsewhere players
                # but if it finds one, it does *not* roll seeker for the next seeker (if there are multiple)
                # see: 2021-07-22T20:13:49.263Z
                # it's possible there's a cleaner way to implement this, but the ordering is tricky...
                for seeker in seekers:
                    was_seek_successful = pulled_back and seeker.raw_name in self.desc
                    # guessing at threshold here, it seems to have changed at least once, but this lets us search warns
                    self.roll(f"seeker ({seeker.raw_name} {player.raw_name})", passed=was_seek_successful, threshold=0.005)
                    if was_seek_successful:
                        self.do_elsewhere_return(player)
                        did_elsewhere_return = True
                        break # <-- load-bearing

                if not pulled_back:
                    self.roll(f"elsewhere ({player.raw_name})")

                    if returned:
                        self.do_elsewhere_return(player)
                        did_elsewhere_return = True
        if did_elsewhere_return:
            return

        for player_id in players:
            player = self.data.get_player(player_id)
            if player.has_mod(Mod.SCATTERED) and not team.has_mod(Mod.SCATTERED):
                unscatter_roll = self.roll(f"unscatter ({player.raw_name})")

                # todo: find actual threshold
                threshold = {
                    12: 0.00061,
                    13: 0.0005,
                    14: 0.0004,
                    15: 0.0004,
                    16: 0.0004,  # todo: we don't know
                    17: 0.00042,  # we have a 0.004184916648748427
                    18: 0.00042,  # we have a 0.00041710056345256596
                    19: 0.00042,  # 0.00041647177941306346 < t < 0.00042578004132232117
                    20: 0.000485,  # we have a positive at 0.00046131203268795495 and 0.00048491029900765703
                    21: 0.000485,  # guessing
                    22: 0.000495,  # have a 0.0004946038449742396
                    23: 0.000495,  # guessing
                }[self.season]

                # Seems to not get rolled when Wyatt Mason IV echoes scattered.
                if unscatter_roll < threshold and (not player.has_mod(Mod.ECHO) or player.raw_name != player.name):
                    self.roll(f"unscatter letter ({player.raw_name})")

    def do_elsewhere_return(self, player):
        scatter_times = 0
        should_scatter = False
        if "days" in self.desc:
            elsewhere_time = int(self.desc.split("after ")[1].split(" days")[0])
            if elsewhere_time > 18:
                should_scatter = True
        if "season" in self.desc:
            if self.event["created"] not in ["2021-04-05T16:24:45.346Z", "2021-04-05T20:08:23.286Z", "2021-07-26T17:13:07.143Z", "2021-07-19T21:10:44.664Z"]:
                should_scatter = True

        if should_scatter:
            scatter_times = (len(player.raw_name.replace(" ", "")) - 1) * 2
            for _ in range(scatter_times):
                # todo: figure out what these are
                self.roll("scatter letter")

    def handle_consumers(self):
        # deploy some time around s14 earlsiesta added this roll - unsure exactly when but it'll be somewhere between
        # day 25 and day 30 (1-indexed)
        if (self.season, self.day) <= (13, 24):
            return
        
        # s24 earlsiesta removed this
        if (self.season, self.day) >= (23, 27):
            return

        order_roll = self.roll("consumer team order")
        if order_roll < 0.5:
            teams = [self.away_team, self.home_team]
        else:
            teams = [self.home_team, self.away_team]

        for team in teams:
            if (self.season < 23 and team.level >= 5) or (self.season == 23 and team.level < 5):
                attack_roll = self.roll(f"consumers ({team.nickname})")

                if self.ty == EventType.CONSUMERS_ATTACK:
                    attacked_player_id = self.event["playerTags"][0]
                    is_on_team = attacked_player_id in (team.lineup + team.rotation)
                    if is_on_team:
                        self.log_roll(Csv.CONSUMERS, "Attack", attack_roll, True, attacked_team=team)

                        attacked_player = self.data.get_player(attacked_player_id)

                        target_roll = self.roll("target")
                        self.log_roll(Csv.CONSUMERS, attacked_player.name, target_roll, True)

                        roster = [self.data.get_player(p) for p in team.lineup + team.rotation]
                        densities = [p.eDensity for p in roster]
                        total_density = sum(densities)
                        self.print(f"total density: {total_density}, densities: {densities}, target acc is {target_roll * total_density}")
                        acc = 0
                        target = None
                        for iter_target, density in zip(roster, densities):
                            acc += density
                            self.print(f"acc is at {acc} for {iter_target.name}, roll between {(acc-density)/total_density}-{acc/total_density}, {iter_target.mods}, {[f'{i.name},{i.health}' for i in iter_target.items]}")
                            if acc > target_roll * total_density and not target:
                                target = iter_target
                                # break
                        self.print(f"(rolled target: {target.name})")
                        if target.id != attacked_player.id:
                            self.error(
                                f"incorrect consumer target (rolled {target.name}, expected {attacked_player.name})"
                            )

                        if "DEFENDS" in self.desc:
                            self.roll("defend item?")

                        if self.stadium.has_mod(Mod.SALMON_CANNONS):
                            self.roll("salmon cannons?")
                            # return True

                        if "CONSUMER EXPELLED" in self.desc:
                            return True

                        if "DEFENDS" in self.desc:
                            return True

                        if "COUNTERED WITH" in self.desc:
                            self.roll("defend item?")
                            self.roll("defend item?")
                            return True

                        if "A CONSUMER!" in self.desc:
                            # this is liquid/plasma kapowing consumers
                            # one of these might be a roll for the text?
                            self.roll("kapow")
                            self.roll("kapow")
                            return True
                        
                        for _ in range(25):
                            self.roll("stat change")

                            if attacked_player.soul == 1:
                                # lost their last soul, redact :<
                                self.print(f"!!! {attacked_player.name} lost last soul, " f"redacting")
                                if attacked_player_id in team.lineup:
                                    team.lineup.remove(attacked_player_id)
                                if attacked_player_id in team.rotation:
                                    team.rotation.remove(attacked_player_id)
                                team.last_update_time = self.event["created"] 

                        return True
                    else:
                        self.log_roll(Csv.CONSUMERS, "Miss", attack_roll, False)
                else:
                    self.log_roll(Csv.CONSUMERS, "Miss", attack_roll, False, attacked_team=team)

    def handle_party(self):
        if self.season == 23 and "SIM_PARTY_TIME" not in self.data.sim["attr"]:
            return        
        if self.season != 16 or self.day >= 85:
            # lol. turns out it just rolls party all the time and throws out the roll if the team isn't partying
            party_roll = self.roll("party time")
        else:
            party_roll = 1

        party_threshold = 0.0055 if self.season < 20 else 0.00525

        if self.ty == EventType.PARTY:
            self.log_roll(Csv.PARTY, "Party", party_roll, True)
            team_roll = self.roll("target team")  # <0.5 for home, >0.5 for away
            self.roll("target player")
            for _ in range(25):
                self.roll("stat")

            if self.season >= 15:
                # probably damage roll for receiver? which i think is very funny
                self.roll("extra party?")

            return True
        elif party_roll < party_threshold and self.event["created"] not in []:
            team_roll = self.roll("target team (not partying)")
            if team_roll < 0.5 and self.home_team.has_mod(Mod.PARTY_TIME):
                self.print("!!! home team is in party time")
            elif team_roll > 0.5 and self.away_team.has_mod(Mod.PARTY_TIME):
                self.print("!!! away team is in party time")

    def handle_ballpark(self):
        league_mods = self.data.sim["attr"]
        if "SECRET_TUNNELS" in league_mods:
            if self.update["awayScore"] >= 1 and self.event["created"]:
                self.roll("tunnels?")
                self.roll("tunnels?")
                self.roll("tunnels?") # actual success roll

            if self.ty == EventType.TUNNELS_USED:
                self.roll("tunnels?")
                if "caught their eye" in self.desc:
                    self.roll("tunnels?")
                return True

        if self.stadium.has_mod(Mod.PEANUT_MISTER):
            eligible_players = self.home_team.lineup + self.home_team.rotation + self.away_team.lineup + self.away_team.rotation
            has_eligible = any(self.data.get_player(p).peanut_allergy for p in eligible_players)
            if has_eligible or True:
                mister_roll = self.roll("peanut mister", threshold=0.0005, passed=self.ty == EventType.PEANUT_MISTER)
                if self.ty == EventType.PEANUT_MISTER:
                    self.log_roll(Csv.MODPROC, "Cure", mister_roll, True)
                if self.ty != EventType.PEANUT_MISTER:
                    self.log_roll(Csv.MODPROC, "NoCure", mister_roll, False)

                if self.ty == EventType.PEANUT_MISTER:
                    self.roll("target")
                    return True
            else:
                self.print("NO ELIGIBLE ALLERGIC PLAYERS")

        if self.stadium.has_mod(Mod.SMITHY):
            smithy_roll = self.roll("smithy", threshold=0.0004, passed=self.ty == EventType.SMITHY_ACTIVATION)

            if self.ty == EventType.SMITHY_ACTIVATION:
                self.log_roll(Csv.MODPROC, "Fix", smithy_roll, True)

                player_roll = self.roll("smithy1")  # noqa: F841
                item_roll = self.roll("smithy2")  # noqa: F841
                return True
            else:
                self.log_roll(Csv.MODPROC, "NoFix", smithy_roll, False)

        if self.ty == EventType.FAX_MACHINE_ACTIVATION:
            # this is definitely before secret base and after smithy
            return True

        # why does THIS roll here? it does. but why
        if self.handle_trader():
            return True
        
        # has to be rolled after party, too
        if self.weather == Weather.NIGHT:
            self.roll("night")
            
            if self.ty == EventType.NIGHT_SHIFT:
                self.roll("night shift")
                self.roll("night shift")
                return True

        # WHY DOES GLITTER ROLL HERE
        if self.weather == Weather.GLITTER:
            glitter_roll = self.roll("glitter")

            if self.ty == EventType.GLITTER_CRATE_DROP:
                self.log_roll(Csv.WEATHERPROC, "LootDrop", glitter_roll, True)
                self.roll("receiving team")
                self.roll("receiving player")
                self.create_item(self.event, ItemRollType.GLITTER, self.prev_event)
                return True

            else:
                self.log_roll(Csv.WEATHERPROC, "NootDrop", glitter_roll, False)

        if self.stadium.has_mod(Mod.SECRET_BASE):
            if self.handle_secret_base():
                return True

        if self.stadium.has_mod(Mod.GRIND_RAIL):
            if self.handle_grind_rail():
                return True

    def handle_secret_base(self):
        # not sure this works
        secret_runner_id = self.update["secretBaserunner"]
        bases = self.update["basesOccupied"]

        # todo: refactor this block, it might be vestigial
        if self.season == 14:
            # if an attractor appeared between this tick and next, and this isn't a "real" enter...
            did_attractor_enter_this_tick = (
                not self.update["secretBaserunner"]
                and self.next_update["secretBaserunner"]
                and self.ty != EventType.ENTER_SECRET_BASE
            )
            if did_attractor_enter_this_tick:
                secret_runner_id = self.next_update["secretBaserunner"]

        # more consequences of the weird attractor async thing
        # one tick before these events, the game chose an attractor and "put them" in the secret base
        # but for some reason we don't see the secret base id until the next tick
        # however, per roll counts, there is still someone in the base, so we should NOT roll for secret base
        # i think this might be the same situation as the above block, but there's an inning switch in between, so our lookahead breaks
        if self.event["created"] == "2021-04-14T19:07:51.129Z":
            # forrest best
            secret_runner_id = "d35ccee1-9559-49a1-aaa4-7809f7b5c46e"
        if self.event["created"] == "2021-04-14T17:06:27.921Z":
            # peanut holloway
            secret_runner_id = "667cb445-c288-4e62-b603-27291c1e475d"

        secret_base_enter_eligible = Base.SECOND in bases and not secret_runner_id
        # "fifth", but it's between third and fourth...
        secret_base_exit_eligible = (
            Base.SECOND not in bases or (self.stadium.has_mod(Mod.EXTRA_BASE) and Base.FOURTH not in bases)
        ) and secret_runner_id
        if secret_runner_id:
            # what is the exact criteria here?
            # we have ghost Elijah Bates entering a secret base in 42a824ba-bd7b-4b63-aeb5-a60173df136e
            # (null leagueTeamId) and that *does* have an exit roll on the "wrong side"
            # so maybe it just checks "if present on opposite team" rather than
            # "is not present on current team"? or it's special handling for null team
            # update as of s19 d33: it definitely also accounts for *shadows*
            # - alx keming can exit when the ffs are batting but not pitching
            pitching_lineup = self.pitching_team.lineup + self.pitching_team.shadows
            secret_runner = self.data.get_player(secret_runner_id)
            if secret_runner_id in pitching_lineup:
                self.print("can't exit secret base on wrong team", secret_runner.name)
                secret_base_exit_eligible = False

        # todo: figure out how to query "player in active team's shadow" and exclude those properly
        if (
            (17, 0) <= (self.season, self.day)
            and secret_runner_id == "070758a0-092a-4a2c-8a16-253c835887cb"
            # all firefighters games, where alx is in the ffs shadows (or magic!)
            and self.game_id
            not in [
                "377f87df-36aa-4fac-bc97-59c24efb684b",
                "bfd8dc98-f35a-49d0-b810-2ee38fb6886f",
                "1ad48feb-eb1e-43eb-b28f-aff79d7a3473",
                "4bd6671d-4b6f-4e1f-bff2-34cc1ab96c5e",
                "d12e21ba-5779-44f1-aa83-b788e5da8655",
                "7b7cc1fb-d730-4bca-8b03-e5658be61136",
                "7bdc5ef4-49aa-4052-961e-b2ea724d9ffb",
                "7b81a595-2f49-4cc5-8ed0-1ea7283cdf5f",
            ]
        ):
            secret_base_exit_eligible = False
        if (
            # kurt crueller ruins this again??
            self.season >= 18
            and secret_runner_id == "114100a4-1bf7-4433-b304-6aad75904055"
            and (secret_runner_id not in self.batting_team.shadows and secret_runner_id not in self.batting_team.lineup)
        ):
            secret_base_exit_eligible = False

        if (
            (17, 27) <= (self.season, self.day)
            and secret_runner_id == "114100a4-1bf7-4433-b304-6aad75904055"
            and (secret_runner_id not in self.batting_team.shadows and secret_runner_id not in self.batting_team.lineup)
        ):
            secret_base_exit_eligible = False

        # weird order issues here. when an attractor is placed in the secret base, it only applies the *next* tick
        # likely because of some kinda async function that fills in the field between ticks
        # so we need to do this play count/next check nonsense to get the right roll order
        attractor_eligible = not secret_runner_id
        if attractor_eligible:
            attract_roll = self.roll("secret base attract")
            if attract_roll < 0.00035 or attract_roll < 0.001 and self.season>=22:  # guessing at threshold, was 0.0002 in s15/s16?
                update_one_after_next = self.data.get_update(self.game_id, self.play + 2)
                attractor_id = self.next_update.get("secretBaserunner") or update_one_after_next.get("secretBaserunner")
                if attractor_id:
                    self.roll("choose attractor")
                    self.pending_attractor = self.data.get_player(attractor_id)
                    return
                else:
                    self.print("(note: should add attractor but could not find any)")

        if secret_base_exit_eligible:
            exit_roll = self.roll("secret base exit")
            if "exits the Secret Base" in self.desc:
                self.log_roll(
                    Csv.EXIT,
                    "Exit",
                    exit_roll,
                    True,
                )
            else:
                self.log_roll(
                    Csv.EXIT,
                    "NoExit",
                    exit_roll,
                    False,
                )

            if self.ty == EventType.EXIT_SECRET_BASE:
                return True

        if secret_base_enter_eligible:
            enter_roll = self.roll("secret base enter")

            runner_idx = self.update["basesOccupied"].index(1)
            runner_id = self.update["baseRunners"][runner_idx]
            runner = self.data.get_player(runner_id)

            if runner.undefined():
                # this *might* be secret base?
                self.roll(f"undefined (secret base enter)")
                self.roll(f"undefined (secret base enter)")

            if "enters the Secret Base..." in self.desc:
                self.log_roll(
                    Csv.ENTER,
                    "Enter",
                    enter_roll,
                    True,
                )
            else:
                self.log_roll(
                    Csv.ENTER,
                    "NoEnter",
                    enter_roll,
                    False,
                )

            if self.ty == EventType.ENTER_SECRET_BASE:
                return True

            # if the player got redacted it doesn't interrupt the pitch and keeps going
            # so the event type won't be 65 but the message will be there
            if "enters the Secret Base..." in self.desc:
                self.print(f"!!! redacted baserunner: {runner.name}")

                # remove baserunner from roster so fielder math works.
                # should probably move this logic into a function somehow
                self.batting_team.lineup.remove(runner_id)
                runner.add_mod(Mod.REDACTED, ModType.PERMANENT)
                self.batting_team.last_update_time = self.event["created"]
                runner.last_update_time = self.event["created"]

                # and just as a cherry on top let's hack this so we don't roll for steal as well
                self.update["basesOccupied"].remove(1)
                self.update["baseRunners"].remove(runner_id)

    def handle_grind_rail(self):
        if Base.FIRST in self.update["basesOccupied"] and Base.THIRD not in self.update["basesOccupied"]:
            # i have no idea why this rolls twice but it definitely *does*
            grindfielder_roll = self.roll("grindfielder")
            grindfielder = self.get_fielder_for_roll(grindfielder_roll, ignore_elsewhere=False)

            if grindfielder.undefined():
                self.roll(f"undefined (grindfielder) ({grindfielder.name})")

            grinder = self.data.get_player(self.update["baseRunners"][-1])
            if grinder.undefined():
                self.roll("undefined (grinder)")
            grindrail_roll = self.roll("grindrail")

            if self.ty == EventType.GRIND_RAIL:
                self.log_roll(
                    Csv.MODPROC,
                    "Grind",
                    grindrail_roll,
                    True,
                    fielder_roll=grindfielder_roll,
                    fielder=self.get_fielder_for_roll(grindfielder_roll),
                )
            else:
                self.log_roll(
                    Csv.MODPROC,
                    "NoGrind",
                    grindrail_roll,
                    False,
                    fielder_roll=grindfielder_roll,
                    fielder=self.get_fielder_for_roll(grindfielder_roll),
                )

            if self.ty == EventType.GRIND_RAIL:
                runner = self.data.get_player(self.update["baseRunners"][-1])
                # finding new and funny ways to detect if this is a ghost
                if runner.pressurization == 0.5 and runner.cinnamon == 0.5:
                    self.data.fetch_player_after(self.update["baseRunners"][-1], self.event["created"])
                    runner = self.data.get_player(self.update["baseRunners"][-1])
                    
                self.roll("trick 1 name")

                m = re.search("They do a .*? \(([0-9]+)\)", self.desc)
                expected_score_1 = int(m.group(1))
                pro_factor = 2 if "Pro Skater" in self.desc else 1
                self.print(f"(press: {runner.pressurization}, cinn: {runner.cinnamon})")
                lo1 = runner.pressurization * 200
                hi1 = runner.cinnamon * 1500 + 500
                expected_roll_lo_1 = (expected_score_1 // pro_factor - lo1) / (hi1 - lo1)
                expected_roll_hi_1 = (expected_score_1 // pro_factor + 1 - lo1) / (hi1 - lo1)
                score_1_roll = self.roll("trick 1 score", expected_roll_lo_1, expected_roll_hi_1)
                score_1 = int((hi1 - lo1) * score_1_roll + lo1) * pro_factor
                self.print(f"(score: {score_1})")

                if runner.undefined():
                    self.roll("undefined (grinder)")

                firsttrick_roll = self.roll("trick 1 success")
                if "but lose their balance and bail!" in self.desc:
                    self.log_roll(
                        Csv.TRICK_ONE,
                        "Fail",
                        firsttrick_roll,
                        False,
                        relevant_batter=self.batter,
                        relevant_runner=runner,
                    )

                else:
                    self.log_roll(
                        Csv.TRICK_ONE,
                        "Pass",
                        firsttrick_roll,
                        True,
                        relevant_batter=self.batter,
                        relevant_runner=runner,
                    )

                if "lose their balance and bail!" not in self.desc:
                    self.roll("trick 2 name")
                    m = re.search("They(?: land|'re tagged out doing) a .*? \(([0-9]+)\)", self.desc)
                    expected_score_2 = int(m.group(1))
                    lo2 = runner.pressurization * 500
                    hi2 = runner.cinnamon * 3000 + 1000
                    expected_roll_lo_2 = (expected_score_2 - lo2) / (hi2 - lo2)
                    expected_roll_hi_2 = (expected_score_2 + 1 - lo2) / (hi2 - lo2)
                    score_2_roll = self.roll("trick 2 score", expected_roll_lo_2, expected_roll_hi_2)
                    score_2 = int((hi2 - lo2) * score_2_roll + lo2)
                    self.print(f"(score: {score_2})")

                    trick2_roll = self.roll("trick 2 success")

                    if runner.undefined():
                        self.roll("undefined (grinder)")

                    if "tagged out doing a" not in self.desc:
                        self.log_roll(
                            Csv.TRICK_TWO,
                            "Success",
                            trick2_roll,
                            True,
                            relevant_batter=self.batter,
                            relevant_runner=runner,
                        )
                    else:
                        self.log_roll(
                            Csv.TRICK_TWO,
                            "Fail",
                            trick2_roll,
                            False,
                            relevant_batter=self.batter,
                            relevant_runner=runner,
                        )
                return True

    def handle_steal(self):
        steal_fielder_roll = self.roll("steal fielder")
        steal_fielder = self.get_fielder_for_roll(steal_fielder_roll)

        bases = self.update["basesOccupied"]

        secret_runner_id = self.update.get("secretBaserunner")
        if secret_runner_id:
            secret_runner = self.data.get_player(secret_runner_id)
            self.print(f"- secret runner: {secret_runner_id} ({secret_runner.name})")

        base_stolen = None
        if "second base" in self.desc:
            base_stolen = Base.SECOND
        elif "third base" in self.desc:
            base_stolen = Base.THIRD
        elif "fourth base" in self.desc:
            base_stolen = Base.FOURTH
        elif "The Fifth Base" in self.desc:
            base_stolen = Base.FIFTH

        for i, base in enumerate(bases):
            if base + 1 not in bases or (
                # This is weird, but adding an extra roll here seems like the only way to get S15D75 to line up.
                # https://reblase.sibr.dev/game/9d224696-6775-42c0-8259-b4de84f850a8#b65483bc-a07f-88e3-9e30-6ff9365f865b
                bases == [Base.THIRD, Base.FIRST, Base.SECOND]
                and base == Base.FIRST
            ):
                runner = self.data.get_player(self.update["baseRunners"][i])

                steal_roll = self.roll(f"steal ({base})")
                if steal_fielder.undefined():
                    self.roll("undefined (fielder steal)")
                if runner.undefined():
                    self.roll(f"undefined (runner steal {base})")
                    self.roll(f"undefined (runner steal {base})")

                was_success = self.ty == EventType.STOLEN_BASE and (
                    base + 1 == base_stolen
                    or base_stolen == Base.FIFTH
                    and filter(lambda i: i.name == "The Fifth Base", runner.items)
                )
                self.log_roll(
                    Csv.STEAL_ATTEMPT,
                    f"StealAttempt{base}",
                    steal_roll,
                    was_success,
                    relevant_batter=self.batter,
                    relevant_runner=runner,
                    fielder_roll=steal_fielder_roll,
                    fielder=steal_fielder,
                )

                if was_success:
                    if steal_fielder.undefined():
                        self.roll("undefined (steal success fielder)")
                    if runner.undefined():
                        self.roll("undefined (steal success runner)")

                    success_roll = self.roll("steal success")
                    was_caught = "caught stealing" in self.desc

                    self.log_roll(
                        Csv.STEAL_SUCCESS,
                        f"StealSuccess{base}",
                        success_roll,
                        not was_caught,
                        relevant_batter=self.batter,
                        relevant_runner=runner,
                        fielder_roll=steal_fielder_roll,
                        fielder=steal_fielder,
                    )

                    # stealing 5th seems to be 1 roll shorter. Not sure if it's for getting caught or damage that's being omitted.
                    if base_stolen != Base.FIFTH:
                        self.damage(runner, "batter")

                    if was_caught and self.season >= 15:
                        self.damage(steal_fielder, "fielder")

                    return True

            if (
                bases == [Base.THIRD, Base.THIRD]
                or bases == [Base.THIRD, Base.SECOND, Base.THIRD]
                or bases == [Base.SECOND, Base.FIRST, Base.SECOND]
                or bases == [Base.SECOND, Base.SECOND]
            ):
                # don't roll twice when holding hands
                break

    def create_item(self, event, roll_type: ItemRollType, prev_event):
        match = re.search("(?:gained|The Winner gets) (.+?)( and ditched| and dropped|\.?$)", self.desc)

        expected_item_name = match.group(1) if match else ""
        if roll_type == ItemRollType.PRIZE:
            item_id = self.next_update["state"].get("prizeMatch", {}).get("itemId")
        elif roll_type == ItemRollType.CHEST:
            meta = event.get("metadata") or {}
            item_id = meta["itemId"]
        else:
            # For a glitter drop, we would need to get the item id from the child event
            item_id = ""
        if item_id:
            expected = self.data.fetch_item_at(item_id, event["created"])
        else:
            expected = expected_item_name

        try:
            item_name = roll_item(
                self.season, self.day, roll_type, self.roll, expected, self.csvs.get(Csv.ITEM_CREATION, None)
            )
        except KeyError as e:
            self.error(
                f"Unknown element {e} for item created at {event['created']}. This probably means either the roll is in the wrong position or the item pool needs to be updated."
            )
            raise
        if event["created"] in [
            "2021-04-20T21:43:04.935Z",
        ]:
            self.roll("????")

        if expected_item_name != item_name:
            self.error(f"incorrect item! expected {expected_item_name}, got {item_name}.")

        if roll_type == ItemRollType.PRIZE:
            return
        if roll_type == ItemRollType.CHEST:
            self.roll("chest target???")

        playerTags = self.event.get("playerTags")
        player = self.data.get_player(playerTags[0]) if playerTags else None
        if player:
            max_items = player.data.get("evolution", 0) + 1
            if self.prev_event and self.prev_event["type"] == EventType.PLAYER_LOST_ITEM:
                self.roll("item to replace???")
        elif match.group(2) in (" and ditched", " and dropped"):
            self.roll("item to replace???")

    def get_eclipse_threshold(self):
        fort = self.stadium.fortification
        if self.season == 11:
            constant = 0.0002  # maybe???
        else:
            constant = 0.00025
        threshold = constant - 0.0003 * (fort - 0.5)
        return threshold

    def throw_pitch(self, known_result=None):
        meta = self.get_stat_meta()
        threshold = get_strike_threshold(
            self.batter, self.batting_team, self.pitcher, self.pitching_team, self.stadium, meta, self.is_flinching()
        )
        if self.batter.undefined():
            # musc and mox
            self.roll("undefined (strike formula)")
            self.roll("undefined (strike formula)")
            self.print(f"--- threshold is {threshold}")

        passed_check = None
        if known_result == "ball":
            passed_check = False
        elif known_result == "strike":
            passed_check = True

        roll = self.roll("strike", threshold=threshold, passed=passed_check)
        if self.pitching_team.has_mod(Mod.ACIDIC):
            acidic_roll = self.roll("acidic")
            success = "Acidic pitch" in self.desc
            self.log_roll(Csv.MODPROC, "Acidic Pitch" if success else "Not Acidic Pitch", acidic_roll, success)

        self.is_strike = roll < threshold
        self.strike_roll = roll
        self.strike_threshold = threshold

        if known_result == "strike" and roll > threshold:
            self.print(f"!!! warn: too high strike roll (threshold {threshold})")
            self.is_strike = True
        elif known_result == "ball" and roll < threshold:
            self.print(f"!!! warn: too low strike roll (threshold {threshold})")
            self.is_strike = False

        known_result_overrides = {
            "2021-06-21T20:17:23.768Z": True,
            "2021-06-24T03:00:24.613Z": True,
            "2021-06-24T04:12:06.096Z": True,
            "2021-06-21T23:09:15.837Z": True,
            "2021-06-26T03:06:40.110Z": True,
            "2021-06-24T05:15:00.980Z": True,
            "2021-06-24T08:12:41.052Z": True,
            "2021-06-24T09:20:42.736Z": True,
            "2021-06-24T11:10:24.784Z": True,
        }
        if self.event["created"] in known_result_overrides:
            self.is_strike = known_result_overrides[self.event["created"]]

        if self.pitching_team.has_mod("FIERY") and self.strikes < self.max_strikes - 1:
            # event where our formula registers a ball but we know it's a strike by roll count
            # ideally we'd get rid of these and our formula would just guess right but alas
            double_strike_overrides = {
                #"2021-05-21T05:32:00.224Z": True, now unnecessary due to strike formula improvements
                #"2021-06-16T01:14:32.242Z": True, Last Double strike override goodbye!
                # "2021-07-22T10:07:27.012Z": False, # removed as realigns later with a party roll
                # "2021-06-22T17:19:20.764Z": True,
            }

            if self.event["created"] in double_strike_overrides:
                override_is_strike = double_strike_overrides[self.event["created"]]
                if override_is_strike != self.is_strike:
                    self.is_strike = override_is_strike
                    self.print("!!! overriding double strike to {}".format(override_is_strike))
                else:
                    self.print("!!! unnecessary double strike override")

            if self.is_strike:
                double_strike_roll = self.roll("double strike")
                success = "fires a Double Strike" in self.desc
                self.log_roll(Csv.MODPROC, "Double Strike" if success else "Single Strike", double_strike_roll, success)
            else:
                self.print("!!! double strike eligible! (threshold is {})".format(threshold))

        return roll

    def damage(self, player: PlayerData, position: str):
        if self.season < 15:
            return
        
        if player.undefined():
            # unknown position here
            self.roll("undefined (item damage)")
            self.roll("undefined (item damage)")
            self.roll("undefined (item damage)")

        if player.has_mod(Mod.CAREFUL):
            self.print(f"item damage skipped ({player.name} is careful)")
            return

        # threshold seems to vary between 0.0002 and >0.0015
        # depending on which position or which type of roll?
        damage_roll = self.roll(f"item damage ({player.name})")

        was_item_broken_this_event = (
            " broke!" in self.desc or " were damaged" in self.desc or " was damaged" in self.desc
        )

        # so, there are a few(?) cases in early s16 where an item was damaged and broke,
        # and no event was logged or displayed.
        if (self.event["created"], player.id) in [
            ("2021-04-12T16:22:51.087Z", "c09e64b6-8248-407e-b3af-1931b880dbee")  # Lenny Spruce
        ]:
            was_item_broken_this_event = True

        # assuming threshold upper bound
        # if an item was broken, we need to guess whether *this particular roll* is the one that did it
        damage_roll_successful = was_item_broken_this_event and damage_roll < 0.003

        manual_damage_overrides = {
            # gloria bugsnax must NOT trigger break here (pitcher threshold lower??)
            ("2021-05-11T09:09:39.742Z", "8cd06abf-be10-4a35-a3ab-1a408a329147"): False,
        }
        damage_roll_successful = manual_damage_overrides.get((self.event["created"], player.id), damage_roll_successful)

        if damage_roll_successful:
            self.roll(f"which item? ({player.name})")

            if f"{player.raw_name}'s " not in self.desc and f"{player.raw_name}' " not in self.desc:
                self.print(f"!!! warn: wrong item damage player? (expected {player.raw_name})")

    def log_roll(
        self,
        csv: Csv,
        event_type: str,
        roll: float,
        passed: bool,
        relevant_batter=None,
        relevant_runner=None,
        fielder_roll=None,
        fielder=None,
        attacked_team=None,
    ):
        if csv not in self.csvs:
            return
        runners_on_bases = zip(self.update["basesOccupied"], self.update["baseRunners"])
        runner_1st = [r for base, r in runners_on_bases if base == Base.FIRST]
        runner_2nd = [r for base, r in runners_on_bases if base == Base.SECOND]
        runners_3rd = [r for base, r in runners_on_bases if base == Base.THIRD]
        if runner_1st:
            runner_on_first = self.data.get_player(runner_1st[0])
        else:
            runner_on_first = None
        if runner_2nd:
            runner_on_second = self.data.get_player(runner_2nd[0])
        else:
            runner_on_second = None
        if runners_3rd:
            runner_on_third = self.data.get_player(runners_3rd[0])
        else:
            runner_on_third = None
        if len(runners_3rd) == 2:  # Holding hands
            runner_on_third_hh = self.data.get_player(runners_3rd[1])
        else:
            runner_on_third_hh = None
        null_player = PlayerData.null
        null_team = TeamData.null
        save_objects = {
            "batter": relevant_batter or self.batter or null_player,
            "batting_team": self.batting_team,
            "pitcher": self.pitcher,
            "pitching_team": self.pitching_team,
            "stadium": self.stadium,
            "fielder": fielder or null_player,
            "relevant_runner": relevant_runner or null_player,
            "runner_on_first": runner_on_first or null_player,
            "runner_on_second": runner_on_second or null_player,
            "runner_on_third": runner_on_third or null_player,
            "runner_on_third_hh": runner_on_third_hh or null_player,
            "attacked_team": attacked_team or null_team,
        }
        self.csvs[csv].write(
            event_type,
            roll,
            passed,
            self.update,
            self.is_strike,
            self.strike_roll,
            self.strike_threshold,
            fielder_roll,
            self.next_update["basesOccupied"] if self.next_update else None,
            self.get_stat_meta(),
            save_objects,
            self.event["created"],
        )

    def setup_data(self, event):
        self.prev_event = self.event
        self.apply_event_changes(event)

        meta = event.get("metadata") or {}
        if meta.get("subPlay", -1) != -1:
            self.print("=== EXTRA:", event["type"], event["description"], meta)
            pass

        self.event = event
        self.ty = event["type"]
        self.desc = event["description"].replace("\n", " ").strip()
        self.season = event["season"]
        self.day = event["day"]

        if not event["gameTags"]:
            return

        self.game_id = event["gameTags"][0]
        self.play = meta["play"]
        update = self.data.get_update(self.game_id, self.play)
        next_update = self.data.get_update(self.game_id, self.play + 1)
        if not update:
            # This list is events where using the prev_event is more accurate.
            if next_update and self.event["created"] not in [
                "2021-03-01T16:31:50.029Z",
                "2021-03-01T17:23:04.303Z",
                "2021-03-01T20:21:59.527Z",
                "2021-03-01T20:28:29.487Z",
                "2021-03-01T20:30:01.929Z",
                "2021-03-01T21:19:19.226Z",
                "2021-03-01T21:19:52.469Z",
                "2021-03-01T21:19:52.494Z",
                "2021-03-01T21:33:49.349Z",
                "2021-03-01T22:07:52.618Z",
                "2021-03-01T22:07:53.281Z",
                "2021-03-01T22:07:53.307Z",
                "2021-03-01T22:24:36.120Z",
                "2021-03-01T22:24:37.784Z",
                "2021-03-02T08:02:06.414Z",
                "2021-03-02T08:02:06.485Z",
                "2021-03-02T09:21:45.373Z",
                "2021-03-02T11:26:53.751Z",
                "2021-03-02T11:26:56.343Z",
                "2021-03-02T12:23:40.536Z",
                "2021-03-02T12:24:43.753Z",
                "2021-03-02T12:26:07.445Z",
                "2021-03-02T13:25:06.682Z",
                "2021-03-02T14:00:17.408Z",
            ]:
                update = NullUpdate(next_update)
            else:
                if self.play <= 0:
                    return
                prev_update = self.data.get_update(self.game_id, self.play - 1)
                if not prev_update:
                    return
                # use the previous values as a guess, but be able to distinguish that there's missing data
                update = NullUpdate(prev_update)

        # manual fixes for missing data
        if self.game_id == "9b1c6091-7f04-46c7-af78-0a7af4d31991" and self.play == 250:
            update = NullUpdate(self.data.get_update(self.game_id, 252))
        elif self.game_id == "bdb1aacf-a6be-4003-b018-10ef94c50c78" and self.play == 249:
            update = NullUpdate(self.data.get_update(self.game_id, 251))
            update["basesOccupied"] = [0]

        missing_update_adjustments = {
            "2021-03-01T20:21:57.896Z": {"homeBatter": "5eac7fd9-0d19-4bf4-a013-994acc0c40c0"},
            "2021-03-01T20:31:34.705Z": {"homeBatter": "cbd19e6f-3d08-4734-b23f-585330028665"},
            "2021-03-02T08:02:06.485Z": {"homeBatter": "cc11963b-a05b-477b-b154-911dc31960df"},
            "2021-03-02T13:25:04.036Z": {"awayBatter": "126fb128-7c53-45b5-ac2b-5dbf9943d71b"},
            "2021-03-02T08:02:06.107Z": {"awayBatter": "8ecea7e0-b1fb-4b74-8c8c-3271cb54f659"},
            "2021-03-02T14:00:17.408Z": {"awayBatter": "32810dca-825c-4dbc-8b65-0702794c424e"},
            "2021-03-02T14:00:17.613Z": {"awayBatter": "cbd19e6f-3d08-4734-b23f-585330028665"},
            "2021-03-02T14:24:41.163Z": {"homeBatter": "7932c7c7-babb-4245-b9f5-cdadb97c99fb"},
            "2021-03-02T14:24:41.888Z": {"homeBatter": "d89da2d2-674c-4b85-8959-a4bd406f760a"},
            "2021-03-02T14:24:43.752Z": {"homeBatter": "413b3ddb-d933-4567-a60e-6d157480239d"},
            "2021-03-02T14:24:45.582Z": {"awayBatter": "4ecee7be-93e4-4f04-b114-6b333e0e6408"},
            "2021-03-02T14:24:46.430Z": {"awayBatter": "4ecee7be-93e4-4f04-b114-6b333e0e6408"},
            "2021-03-02T14:24:50.559Z": {"homeBatter": "e16c3f28-eecd-4571-be1a-606bbac36b2b"},
            "2021-03-02T14:24:51.485Z": {"homeBatter": "7932c7c7-babb-4245-b9f5-cdadb97c99fb"},
            "2021-04-14T15:08:13.123Z": {
                "basesOccupied": [1],
                "atBatStrikes": 1,
                "halfInningOuts": 1,
            },
            "2021-04-14T15:21:12.199Z": {
                "basesOccupied": [2, 0],
                "baseRunners": ["4b01cc3f-c59f-486d-9c00-b8a82624e620", "5361e381-6658-488b-8236-dde6a264554f"],
            },
            "2021-04-14T15:21:10.904Z": {"basesOccupied": [0]},
            "2021-04-14T15:21:15.954Z": {"basesOccupied": [1]},
            "2021-04-14T15:21:16.255Z": {"basesOccupied": [0]},
            "2021-04-14T15:21:16.683Z": {
                "basesOccupied": [1],
                "baseRunners": ["b643a520-af38-42e3-8f7b-f660e52facc9"],
                "secretBaserunner": [],
            },
        }

        if self.event["created"] in missing_update_adjustments:
            for k, v in missing_update_adjustments[self.event["created"]].items():
                update[k] = v

        self.update = update
        self.next_update = next_update
        self.weather = update["weather"]

        self.away_team = self.data.get_team(update["awayTeam"])
        self.home_team = self.data.get_team(update["homeTeam"])

        self.batting_team = self.away_team if update["topOfInning"] else self.home_team
        self.pitching_team = self.home_team if update["topOfInning"] else self.away_team

        batter_id = update["awayBatter"] if update["topOfInning"] else update["homeBatter"]
        if not batter_id and next_update:
            batter_id = next_update["awayBatter"] if next_update["topOfInning"] else next_update["homeBatter"]
        pitcher_id = update["homePitcher"] if update["topOfInning"] else update["awayPitcher"]
        if not pitcher_id and next_update:
            pitcher_id = next_update["homePitcher"] if next_update["topOfInning"] else next_update["awayPitcher"]

        self.batter = self.data.get_player(batter_id)
        self.pitcher = self.data.get_player(pitcher_id)

        home_pitcher_id = update["homePitcher"] or next_update["homePitcher"]
        away_pitcher_id = update["awayPitcher"] or next_update["awayPitcher"]
        self.home_pitcher = self.data.get_player(home_pitcher_id)
        self.away_pitcher = self.data.get_player(away_pitcher_id)

        self.stadium = self.data.get_stadium(update["stadiumId"])

        self.outs = update["halfInningOuts"]
        self.max_outs = update["awayOuts"] if update["topOfInning"] else update["homeOuts"]
        self.strikes = update["atBatStrikes"]
        self.max_strikes = update["awayStrikes"] if update["topOfInning"] else update["homeStrikes"]
        self.balls = update["atBatBalls"]
        self.max_balls = update["awayBalls"] if update["topOfInning"] else update["homeBalls"]

        # handle player name unscattering etc, not perfect but helps a lot
        if self.batter and self.pitcher:
            if update["topOfInning"]:
                if self.update["awayBatterName"]:
                    self.batter.raw_name = self.update["awayBatterName"]
                if self.update["homePitcherName"]:
                    self.pitcher.raw_name = self.update["homePitcherName"]
            else:
                if self.update["homeBatterName"]:
                    self.batter.raw_name = self.update["homeBatterName"]
                if self.update["awayPitcherName"]:
                    self.pitcher.raw_name = self.update["awayPitcherName"]

        # hardcoding another fix - if we missed the "perks up" event apply it "manually". but not to ghosts
        if (
            self.batter
            and self.batter.has_mod(Mod.PERK)
            and self.weather.is_coffee()
            and not self.batter.has_mod(Mod.OVERPERFORMING, ModType.GAME)
            and not self.batter.has_mod(Mod.INHABITING)
            and self.ty != EventType.BATTER_UP
        ):
            self.batter.add_mod(Mod.OVERPERFORMING, ModType.GAME)
            self.batter.last_update_time = self.event["created"]

    def apply_event_changes(self, event):
        # maybe move this function to data.py?
        meta = event.get("metadata", {})
        desc = event["description"]

        # player or team mod added
        if event["type"] in [
            EventType.ADDED_MOD,
            EventType.ADDED_MOD_FROM_OTHER_MOD,
        ]:
            if event["playerTags"]:
                player = self.data.get_player(event["playerTags"][0])
                player.add_mod(meta["mod"], meta["type"])
                player.last_update_time = self.event["created"]
            else:

                if meta["mod"] == "EXTRA_BASE":
                    self.stadium.mods.add(meta["mod"])
                    self.stadium.last_update_time = self.event["created"]
                else:
                    team = self.data.get_team(event["teamTags"][0])
                    team.add_mod(meta["mod"], meta["type"])
                    team.last_update_time = self.event["created"]

        # player or team mod removed
        if event["type"] in [
            EventType.REMOVED_MOD,
            EventType.REMOVED_MODIFICATION,
        ]:
            # super roamin' fifth base baybee
            if meta["mod"] == "EXTRA_BASE":
                self.stadium.remove_mod(Mod.EXTRA_BASE)
                # might be "what to drop instead", maybe?
                self.roll("stealing fifth base")
                return
            
            # bhbh nullifying mods
            if meta["mod"] in self.stadium.mods:
                self.stadium.remove_mod(meta["mod"])

            if event["playerTags"]:
                player = self.data.get_player(event["playerTags"][0])

                if not player.has_mod(meta["mod"], meta["type"]):
                    self.print(f"!!! warn: trying to remove mod {meta['mod']} but can't find it")
                else:
                    player.remove_mod(meta["mod"], meta["type"])
                player.last_update_time = self.event["created"]

            else:
                team = self.data.get_team(event["teamTags"][0])

                if not team.has_mod(meta["mod"], meta["type"]):
                    self.print(f"!!! warn: trying to remove mod {meta['mod']} but can't find it")
                else:
                    team.remove_mod(meta["mod"], meta["type"])
                team.last_update_time = self.event["created"]

        # mod replaced
        if event["type"] in [EventType.CHANGED_MODIFIER]:
            if event["playerTags"]:
                player = self.data.get_player(event["playerTags"][0])
                player.remove_mod(meta["from"], meta["type"])
                player.add_mod(meta["to"], meta["type"])
                player.last_update_time = self.event["created"]
            else:
                team = self.data.get_team(event["teamTags"][0])
                team.remove_mod(meta["from"], meta["type"])
                team.add_mod(meta["to"], meta["type"])
                team.last_update_time = self.event["created"]

        # timed mods wore off
        if event["type"] in [EventType.MOD_EXPIRES]:
            if event["playerTags"]:
                player = self.data.get_player(event["playerTags"][0])
                for mod in meta["mods"]:
                    if not player.has_mod(mod, meta["type"]):
                        self.print(f"!!! warn: trying to remove mod {mod} but can't find it")
                    else:
                        player.remove_mod(mod, meta["type"])
                player.last_update_time = self.event["created"]
            else:
                team = self.data.get_team(event["teamTags"][0])
                for mod in meta["mods"]:
                    team.remove_mod(mod, meta["type"])
                team.last_update_time = self.event["created"]

        # echo mods added/removed
        if event["type"] in [
            EventType.REMOVED_MULTIPLE_MODIFICATIONS_ECHO,
            EventType.ADDED_MULTIPLE_MODIFICATIONS_ECHO,
        ]:
            if event["playerTags"]:
                player = self.data.get_player(event["playerTags"][0])
                for mod in meta.get("adds", []):
                    player.add_mod(mod["mod"], mod["type"])
                for mod in meta.get("removes", []):
                    player.remove_mod(mod["mod"], mod["type"])

                    # see Wyatt Mason X, s19d28, echoing Magi Ruiz, getting rid of Homebody, and then losing OP
                    for secondary_mod, source in player.permanent_mod_sources.items():
                        if source == [mod["mod"]]:  # todo: what if multiple?
                            player.remove_mod(secondary_mod, ModType.PERMANENT)

                player.last_update_time = self.event["created"]

        # cases where the tagged player needs to be refetched (party, consumer, incin replacement)
        if event["type"] in [
            EventType.PLAYER_STAT_INCREASE,
            EventType.PLAYER_STAT_DECREASE,
            EventType.PLAYER_STAT_DECREASE_FROM_SUPERALLERGIC,
            EventType.PLAYER_HATCHED,
            EventType.PLAYER_GAINED_ITEM,
            EventType.PLAYER_LOST_ITEM,
            EventType.TRADE_SUCCESS,
        ]:
            for player_id in event["playerTags"]:
                self.data.fetch_player_after(player_id, event["created"])

        # scatter player name
        if event["type"] == EventType.ADDED_MOD and "was Scattered..." in desc:
            new_name = desc.split(" was Scattered")[0]
            player = self.data.get_player(event["playerTags"][0])
            player.raw_name = new_name

        # player removed from roster
        if event["type"] == EventType.PLAYER_REMOVED_FROM_TEAM:
            team_id = meta["teamId"]
            player_id = meta["playerId"]
            team = self.data.get_team(team_id)
            if player_id in team.lineup:
                team.lineup.remove(player_id)
            if player_id in team.rotation:
                team.rotation.remove(player_id)
            team.last_update_time = self.event["created"]

        # mod changed from one to other
        if event["type"] == EventType.MODIFICATION_CHANGE:
            player = self.data.get_player(event["playerTags"][0])
            player.remove_mod(meta["from"], meta["type"])
            player.add_mod(meta["to"], meta["type"])

            # todo: do this in other cases too?
            if meta["from"] == "RECEIVER":
                for mod, source in player.season_mod_sources.items():
                    if source == ["RECEIVER"]:
                        player.remove_mod(mod, ModType.SEASON)
            player.last_update_time = self.event["created"]

        # roster swap
        if event["type"] == EventType.PLAYER_TRADED:
            a_team = self.data.get_team(meta["aTeamId"])
            b_team = self.data.get_team(meta["bTeamId"])
            a_player = meta["aPlayerId"]
            b_player = meta["bPlayerId"]
            a_location = a_team.rotation if meta["aLocation"] else a_team.lineup
            b_location = b_team.rotation if meta["bLocation"] else b_team.lineup
            a_idx = a_location.index(a_player)
            b_idx = b_location.index(b_player)

            b_location[b_idx] = a_player
            a_location[a_idx] = b_player
            a_team.last_update_time = self.event["created"]
            b_team.last_update_time = self.event["created"]

        # carcinization etc
        if event["type"] == EventType.PLAYER_MOVE:
            send_team = self.data.get_team(meta["sendTeamId"])
            receive_team = self.data.get_team(meta["receiveTeamId"])
            player_id = meta["playerId"]

            if player_id in send_team.lineup:
                send_team.lineup.remove(player_id)
                receive_team.lineup.append(player_id)
            if player_id in send_team.rotation:
                send_team.rotation.remove(player_id)
                receive_team.rotation.append(player_id)
            send_team.last_update_time = self.event["created"]
            receive_team.last_update_time = self.event["created"]

        if event["type"] == EventType.PLAYER_SWAP:
            # For some reason, this swap doesn't actually happen. Possibly a bug with a player getting swapped multiple times?
            if event["created"] in ["2021-04-20T15:01:43.671Z", "2021-06-18T03:11:33.191Z"]:
                return
            if event["created"] in ["2021-07-26T18:16:26.686Z", "2021-07-20T04:31:50.511Z"]:
                # by the time we get this event it's already happened in our data??
                return
            team = self.data.get_team(meta["teamId"])
            a_player = meta["aPlayerId"]
            b_player = meta["bPlayerId"]
            a_location = (
                team.rotation if meta["aLocation"] == 1 else (team.lineup if meta["aLocation"] == 0 else team.shadows)
            )
            b_location = (
                team.rotation if meta["bLocation"] == 1 else (team.lineup if meta["bLocation"] == 0 else team.shadows)
            )
            if a_player not in a_location or b_player not in b_location:
                self.error("could not execute player swap, didn't find the players in that spot!!!")
            else:
                a_idx = a_location.index(a_player)
                b_idx = b_location.index(b_player)
                b_location[b_idx] = a_player
                a_location[a_idx] = b_player
                team.last_update_time = self.event["created"]

        if event["type"] == EventType.PLAYER_BORN_FROM_INCINERATION:
            # Roscoe Sundae replaced the incinerated Case Sports. etc
            team = self.data.get_team(meta["teamId"])

            location = (
                team.rotation if meta["location"] == 1 else (team.lineup if meta["location"] == 0 else team.shadows)
            )

            out_player = meta["outPlayerId"]
            in_player = meta["inPlayerId"]

            replace_idx = location.index(out_player)
            location[replace_idx] = in_player
            team.last_update_time = self.event["created"]

        if event["type"] in [
            EventType.ITEM_BREAKS,
            EventType.ITEM_DAMAGE,
            EventType.BROKEN_ITEM_REPAIRED,
            EventType.DAMAGED_ITEM_REPAIRED,
        ]:
            player_id = event["playerTags"][0]
            player = self.data.get_player(player_id)
            for item in player.items:
                if item.id == meta["itemId"]:
                    item.health = meta["itemHealthAfter"]
                    if event["type"] == EventType.ITEM_BREAKS:
                        for mod in meta["mods"]:
                            # This is probably wrong if they have 2 items with the same mod.
                            player.remove_mod(mod, ModType.ITEM)
                    elif event["type"] == EventType.BROKEN_ITEM_REPAIRED:
                        for mod in meta["mods"]:
                            player.add_mod(mod, ModType.ITEM)
            player.update_stats()
            player.last_update_time = self.event["created"]

        if event["type"] == EventType.HYPE_BUILT:
            self.stadium.hype = meta["after"]
            self.stadium.last_update_time = self.event["created"]

        if event["type"] in [EventType.PLAYER_HIDDEN_STAT_INCREASE, EventType.PLAYER_HIDDEN_STAT_DECREASE]:
            player_id = event["playerTags"][0]
            player = self.data.get_player(player_id)

            attr_name = stat_indices[meta["type"]]

            # we just set to "after" so doesn't matter if it's increase or decrease
            player.data[attr_name] = meta["after"]
            player.update_stats()
            player.last_update_time = self.event["created"]

    def find_start_of_inning_score(self, game_id, inning):
        # Home Field Advantage and such happen before the first inning, but can still be reset.
        if inning == 0:
            return 0, 0
        for play in range(1000):
            update = self.data.get_update(game_id, play)
            if update:
                if update["inning"] == inning:
                    return update["awayScore"], update["homeScore"]

    def run(self, start_timestamp, end_timestamp, progress_callback):
        self.data.fetch_league_data(start_timestamp)
        feed_events = get_feed_between(start_timestamp, end_timestamp)

        for event in feed_events:
            if progress_callback:
                progress_callback()
            event["type"] = EventType(event["type"])
            self.handle(event)

        self.save_data()

    def emit_roll_to_stream(self, label: str, value: float, passed: Optional[bool], threshold: Optional[float]):
        if self.stream_file is None:
            return
        self.stream_file.write(json.dumps({
            "label": label,
            "roll": value,
            "passed": passed,
            "threshold": threshold
        }) + "\n")

    def emit_correction_to_stream(self, to_step: int):
        if self.stream_file is None:
            return
        self.stream_file.write(json.dumps({
            "correction": to_step
        }) + "\n")

    def roll(
        self,
        label,
        lower: float = 0,
        upper: float = 1,
        passed: Optional[bool] = None,
        threshold: Optional[float] = None,
    ) -> float:
        value = self.rng.next()
        self.print(f"{label}: {value}")
        self.emit_roll_to_stream(label, value, passed, threshold)

        if threshold is not None and passed is not None:
            if passed:
                upper = threshold
            else:
                lower = threshold

        if value < lower or value > upper:
            self.print(
                "!!! warn: value {}={} out of bounds (should be within {}-{})".format(label, value, lower, upper)
            )

        # hacky way to figure out what index this roll is in the overall list
        idx = 0
        if self.roll_log:
            if self.roll_log[-1].event_id == self.event["id"]:
                idx = self.roll_log[-1].index + 1

        log_obj = LoggedRoll(self.event["id"], idx, self.event["created"], label, lower, upper)
        self.roll_log.append(log_obj)
        return value

    def generate_player(self):
        self.roll("first name")
        self.roll("last name")
        for _ in range(26):
            self.roll("stat")
        self.roll("soul")
        self.roll("allergy")
        self.roll("fate")
        self.roll("ritual")
        self.roll("blood")
        self.roll("coffee")

    def save_data(self):
        for csv in self.csvs.values():
            csv.close()

        if self.stream_file is not None:
            self.stream_file.close()

        import csv, dataclasses
        if self.odds_log:
            with open(f"roll_data/odds_{self.run_name}.csv", "w", newline="") as f:
                dw = csv.DictWriter(f, fieldnames=list(self.odds_log[0].__dict__.keys()))
                dw.writeheader()
                dw.writerows((dataclasses.asdict(ol) for ol in self.odds_log))


def advance_bases(occupied, amount, up_to=4):
    occupied = [b + (amount if b < up_to else 0) for b in occupied]
    return [b for b in occupied if b < 3]


def make_base_map(update):
    bases = {}
    for i, pos in enumerate(update["basesOccupied"]):
        bases[pos] = update["baseRunners"][i]
    return bases


def force_advance(bases, start_at=0):
    new_bases = {}
    for i in range(start_at, 5):
        if i in bases:
            new_bases[i + 1] = bases[i]
    return new_bases


def calculate_advances(bases_before, bases_after, bases_hit, home_base=Base.FOURTH):
    # this code sucks so much. i hate runner advances. they're nasty
    # (and i'm not even really using it)
    bases = dict(bases_before)
    for i in range(bases_hit):
        bases = force_advance(bases, i)

    if bases_hit > 0:
        # ignore the batter
        for i in range(bases_hit):
            if i in bases_after:
                del bases_after[i]
        # and anyone past home. todo for fifth base lmao
        for base in range(home_base, 8):
            if base in bases:
                del bases[base]

    third_scored = len(bases_after) < len(bases)

    rolls = []
    occupied = sorted(bases.keys(), reverse=True)
    for runner in occupied:
        player = bases[runner]

        is_eligible = runner + 1 not in bases
        if is_eligible:
            if runner == home_base - 1:
                did_advance = third_scored
            else:
                did_advance = runner + 1 in bases_after

            rolls.append((player, runner, did_advance))
            if did_advance:
                bases[runner + 1] = bases[runner]
                del bases[runner]

    return rolls


@dataclass
class LoggedRoll:
    event_id: str
    index: int
    timestamp: str
    roll_name: str
    lower_bound: float
    upper_bound: float

@dataclass
class OddsLog:
    game_id: str
    season: int
    day: int
    home_batting_stars: float
    away_batting_stars: float
    home_batting_stars_geom: float
    away_batting_stars_geom: float
    home_batting_stars_csv: str
    away_batting_stars_csv: str
    home_batters: int
    away_batters: int
    home_pitching_stars: float
    away_pitching_stars: float
    fuzz_roll: float
    delta: float
    home_baserunning_stars: float
    away_baserunning_stars: float
    home_defense_stars: float
    away_defense_stars: float
    home_pitcher_id: str
    away_pitcher_id: str
    home_team: str
    away_team: str
    home_team_name: str
    away_team_name: str
    home_pitcher_name: str
    away_pitcher_name: str
    home_wins: float
    away_wins: float
    home_odds: float
    away_odds: float
