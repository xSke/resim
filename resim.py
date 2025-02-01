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
    get_triple_threshold,
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


class Resim:
    def __init__(self, rng, out_file, run_name, raise_on_errors=True, csvs_to_log=[]):
        object_cache = {}
        self.rng = rng
        self.out_file = out_file
        self.data = GameData()
        self.fetched_days = set()
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

        if run_name:
            os.makedirs("roll_data", exist_ok=True)
            run_name = run_name.replace(":", "_")
            csvs_to_log = csvs_to_log or list(Csv)
            self.csvs = {csv: SaveCsv(run_name, csv.value, object_cache) for csv in Csv if csv in csvs_to_log}
        else:
            self.csvs = {}
        self.roll_log: List[LoggedRoll] = []

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

        # I have no idea why there's an extra roll here, but it works.
        if self.game_id == "e1fda957-f4ac-4188-835d-265a67b9585d" and self.play == 145:
            self.roll("???")

        event_adjustments = {
            "2021-03-01T20:22:00.461Z": -1,  # fix for missing data
            "2021-03-01T21:00:16.006Z": -1,  # fix for missing data
            "2021-03-02T12:24:43.753Z": 1,  # fix for missing data
            "2021-03-02T13:25:06.682Z": -1,  # fix for missing data
            "2021-03-02T14:00:15.843Z": 1,
            "2021-04-05T15:23:26.102Z": 1,
            "2021-04-12T15:19:56.073Z": -2,
            "2021-04-12T15:22:50.866Z": 1,
            "2021-04-14T15:08:13.155Z": -1,  # fix for missing data
            "2021-04-14T17:06:28.047Z": -2,  # i don't know
            "2021-04-14T19:07:51.129Z": -2,  # may be attractor-related?
            "2021-04-20T12:00:00.931Z": -1,  # item damage at end of game??
            "2021-05-10T18:05:08.668Z": 1,
            "2021-05-10T20:21:59.360Z": 1,
            "2021-05-10T21:29:20.815Z": 1,
            "2021-05-10T22:26:11.164Z": 1,
            "2021-05-11T00:00:17.142Z": 1,
            "2021-05-11T01:00:16.921Z": 1,
            "2021-05-12T06:00:17.186Z": 1,
            "2021-05-12T12:24:31.667Z": 1,
            "2021-05-12T13:01:28.057Z": 1,
            "2021-05-12T15:20:57.747Z": 1,
            "2021-05-13T08:07:07.199Z": -1,
            "2021-05-13T13:03:37.832Z": 1,
            "2021-05-13T15:00:17.580Z": -1,
            "2021-05-13T16:38:59.820Z": 387,  # skipping latesiesta
            "2021-05-14T11:21:37.843Z": 1,  # instability?
            "2021-05-14T13:07:02.411Z": 1,
            "2021-05-14T15:17:08.833Z": 1,
            "2021-05-17T17:20:09.894Z": 1,
            "2021-05-17T23:10:48.902Z": 1,  # dp item damage rolls...?
            "2021-05-20T04:20:24.586Z": -1,  # item damage
            "2021-06-14T19:13:49.970Z": 1,
            "2021-06-15T08:22:16.606Z": 1,
            "2021-06-15Tz20:00:18.367Z": -1,
            "2021-06-16T06:22:08.507Z": 1,
            "2021-06-16T12:04:04.468Z": 1,  # dp item damage?
            "2021-06-16T20:00:20.027Z": -1,
            "2021-06-17T02:00:04.148Z": -1,
            "2021-06-17T19:09:41.707Z": 1,
            "2021-06-17T19:09:42.498Z": 1,
            "2021-06-17T19:09:45.885Z": 1,
            "2021-06-18T07:01:54.628Z": -1,
            "2021-06-18T17:01:00.415Z": -1,
            "2021-06-18T19:18:22.631Z": -1,

            "2021-06-21T21:21:54.412Z": 1, # sun 30? or something funky with the single after it...?
            "2021-06-21T21:21:59.425Z": -1, # wat
            "2021-06-21T21:24:18.953Z": -1, # this is wrong
            "2021-06-21T22:17:23.159Z": 2, # the flooding?
            "2021-06-21T23:23:06.016Z": 1, # sun 30?
            "2021-06-21T23:23:13.523Z": -1, # why is this so weird...
            "2021-06-24T04:21:11.177Z": 1, # Huber Frumple hit into a double play! Jaxon Buckley scores! The Oven inflates 1 Balloons! ?
            "2021-06-25T22:10:22.558Z": 2, # extra roll for consumers, maybe a defense?
            "2021-06-26T20:00:16.596Z": 1, # start?
            "2021-06-24T10:13:01.619Z": 4, # sac or something?
        }
        to_step = event_adjustments.get(self.event["created"])
        if to_step is not None:
            self.rng.step(to_step)
            time = self.event["created"]
            self.print(f"!!! CORRECTION: stepping {to_step} @ {time}")

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
        if self.pitcher.has_mod(Mod.DEBT_THREE) and not self.batter.has_mod(Mod.COFFEE_PERIL):
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

    def handle_misc(self):
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
            self.print("away team mods:", self.away_team.print_mods(ModType.PERMANENT))
            self.roll("echo team mod")
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
            if self.ty == EventType.PSYCHO_ACOUSTICS:
                self.roll("which mod?")
            if self.ty == EventType.A_BLOOD_TYPE:
                self.roll("a blood type")

            if self.ty == EventType.PRIZE_MATCH:
                self.create_item(self.event, ItemRollType.PRIZE, self.prev_event)

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
        ]:
            # skipping mod added/removed
            return True
        if self.ty in [
            EventType.BLACK_HOLE,
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
        ]:
            return True

        if self.ty == EventType.EXISTING_PLAYER_ADDED_TO_ILB:
            if "pulled through the Rift" in self.desc:
                # The Second Wyatt Masoning
                # The rolls normally assigned to "Let's Go" happen before the Second Wyatt Masoning
                if self.desc == "Wyatt Mason was pulled through the Rift.":
                    for _ in range(12):
                        self.roll("game start")
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
        if self.ty in [EventType.HALF_INNING]:
            # skipping top-of/bottom-of
            is_holiday = self.next_update.get("state", {}).get("holidayInning")
            # if this was a holiday inning then we already rolled in the block below
            if is_holiday:
                return True

            if self.weather == Weather.SALMON:
                self.try_roll_salmon()

            if self.next_update["topOfInning"]:
                # if this was a holiday inning then we already rolled in the block below

                # hm was ratified in the season 18 election
                has_hotel_motel = self.stadium.has_mod(Mod.HOTEL_MOTEL) or self.season >= 18
                if has_hotel_motel and self.day < 27:
                    hotel_roll = self.roll("hotel motel")
                    self.log_roll(Csv.MODPROC, "Notel", hotel_roll, False)

            return True

        if self.ty == EventType.SALMON_SWIM:
            salmon_roll = self.roll("salmon")
            self.log_roll(Csv.WEATHERPROC, "Salmon", salmon_roll, True)

            # special case for a weird starting point with missing data
            last_inning = self.update["inning"]
            last_inning_away_score, last_inning_home_score = self.find_start_of_inning_score(self.game_id, last_inning)
            current_away_score, current_home_score = (
                self.update["awayScore"],
                self.update["homeScore"],
            )

            # todo: figure out order here
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
                        if player.raw_name not in self.desc and player.has_mod(Mod.UNDERTAKER) and not player.has_mod(Mod.ELSEWHERE):
                            has_undertaker = True
                            break
                    if has_undertaker:
                        self.roll("undertaker")
                        self.roll("undertaker")
            return True

        if self.ty == EventType.HOLIDAY_INNING:
            if self.weather == Weather.SALMON:
                self.try_roll_salmon(holiday_inning=True)
            hotel_roll = self.roll("hotel motel")  # success
            self.log_roll(Csv.MODPROC, "Hotel", hotel_roll, True)
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
            EventType.SUN_30,
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
        if self.ty in [EventType.LETS_GO]:
            # game start - probably like, postseason weather gen
            if self.event["day"] >= 99:
                self.roll("game start")

            if self.event["day"] != 98 and (
                # These rolls happen before the Second Wyatt Masoning
                self.event["season"] != 13
                or self.event["day"] != 72
            ):
                # *why*
                self.roll("game start")

            # todo: figure out the real logic here, i'm sure there's some
            extra_start_rolls = {
                "e07d8602-ec51-4ef6-be20-4a07da6b457e": 1,
                "3c1b4d10-78af-4b8e-a9f5-e6ea2d50e5c4": 1,
                "196f195c-f8b2-44e9-b117-a7a46de390cd": 1,
                "502d6a06-1975-4c70-94d6-bdf9e31aaec6": 1,
                "2dff1e11-c2b9-4423-9930-6bb96d1a72d7": 1,
                "c09fbaf1-c068-45a5-b644-e481f18be0bd": 216,  # ...earlsiesta reading???
                "94785708-7b40-47b7-a258-9ce10a157395": 9,  # earlsiesta reading
                "e39803d0-add7-43cb-b472-04f04e4b0935": 1,
                "3ff91111-7862-442e-aa59-c338871c63fe": 2,
                "1514e79b-e14b-45e0-aada-dad2ba4d753d": 1,
                "a327e425-aaf4-4199-8292-bba0ec4a226a": 2,
                "d03ad239-25ee-41bf-a1d3-6e087f302171": 1,
                "b2bb8e5c-358f-448b-bbf3-7c8c33148107": 1,
                "bf35c2a3-61f3-49e2-b693-9e7ead9a2f8e": 1,
                "5b9dcdb4-db02-400a-9d6d-55713939332f": 1,
                "9ded2295-da80-4395-9f70-92f5bdae38a1": 1,
                "893edab1-9100-4164-a72c-3d2ace026f8a": 1,
                "adcbbf30-de0d-4df2-ad93-7d91d6daaa6a": 1,
                "cb7dd13c-bf04-4bb1-a53a-cf478bc2e26c": 2,
                "2fabc7aa-8c17-4b8b-aa10-bb1a7af90d82": 1,
                "eb441ce0-6768-4463-a997-817381b176fe": 1,
                "0633f858-d1cb-4ba2-a04b-6b035767bed5": 1,
                "e2a7f575-b165-485f-b1c9-39a3c8edacbf": 1,
                "883b56f8-d470-4a9f-b709-7647ffcac4cc": 1,
                "f39fc061-5485-4140-9ec0-92d716c1fa67": 1,
                "ca53fd25-ed06-4d6d-b0ae-80d0a1b58ed1": 2,
                "a581bfd7-725f-49a3-83ff-dc98806ef262": 1,
                "0cde3960-b7dd-4df2-b469-5274be158563": 1,
                "8a90bd4b-9f51-4c2e-9c24-882dabdfe932": 1,
                "0a79fdbb-73ca-4b8e-8696-10776d75cd0f": 1,
                "42fb4a2e-c471-4f2c-96b4-e0319e3f9aa0": 1,
                "a2d9e7c4-9a4e-4573-ac13-90f1fa64c13d": 0,
                "662e2383-1b5e-4a46-9598-da4a574f58ae": 1,
                "c27b5393-4910-4a8c-a6a5-93cce32fe30a": 1,
                "bd9c9d74-39c8-4195-8777-06b49c2f912a": 1,
                "0aa716c9-9745-4606-bbdc-34d4b1845f0c": 1,
                "1ae97925-6db8-47ad-8216-fc872b12a7dc": 2,
                "957acc90-52f2-4c07-bac2-a92696acea37": 220,  # earlsiesta reading
                "3e35defb-51c0-48ad-87bc-3a36c63b951c": 1,
                "be04f619-f595-46c5-8b8c-87befc1418fa": 221,  # earlsiesta reading
                "9b46f551-1e5c-4482-8ac1-81d4e36df31a": 1,
                "e7387f25-31f7-4047-83b7-7770f166a6ef": 1,
                "f628e63b-dcc2-45bc-b16a-ff053d4ece0b": 1,
                "72b41d5c-7e97-4ee1-b5a3-5a01aaf5f043": 2,
                "54055971-2287-4f34-abb1-0a21aeb1a994": 1,
                "de996e83-6584-4312-8e2b-613e4c8bb0ee": 1,
                "78838e9a-16b2-4733-8194-c629eb57d803": 1,
                "4ed7ce17-f47d-41ce-aad3-1089ab54bd2c": 2,
                "9a5b1658-0924-43ef-a417-e7de8076a57c": 1,
                "e1c383ab-efc0-49ad-91e2-3d29cca47a90": 1,
                "b62e2bd0-333e-4462-a84d-5aecabd0c1bc": 1,
                "45f65a7f-ed58-4482-8139-92d2e2ef7bfa": 1,
                "9291e5ce-a49f-44dc-9bb4-747bc783c351": 1,
                "33415dda-9822-4bfd-b943-b8f7c4fb3af4": 1,
                "0b82745a-e797-4256-9ce7-9868253a9e4b": 1,
                "4f8ce860-fb5e-4cff-8111-d687fa438876": 2,
                "e0880bb0-60b2-4778-a209-977bd4b23ab6": 1,
                "a12bbed2-68b4-4db0-b408-6727b28743c3": 1,
                "fa320c4c-ceab-48a5-b3a1-8a064977d974": 217,  # earlsiesta reading
                "426196ac-8600-4929-af6f-d750517eec87": 1,
                "0486ea3c-9a94-4fdc-82cd-78feca6e00d7": 1,
                "9485f77d-3c78-40dc-a6ba-d56e231a5902": 1,
                "3dfdcc5d-f3f5-49ae-a826-451843e1177b": 1,
                "48c355e1-b656-4afb-b05b-17e0e9b13f07": 1,
                "2a712340-9a47-430a-8645-5ab61a4fa6da": 2,
                "2d4465c0-60e4-42e3-a630-712d9bcfb253": 1,
                "9df98fb5-e015-497b-bc47-6a6701a5e69a": 1,
                "3954b1cc-01bc-48a5-b2d1-936ae28997db": 1,
                "30f866e2-af0d-4609-8973-19d1c9be96d2": 1,
                "75961c1b-d2e1-4ed3-bd44-0a2d49ad9962": 1,
                "2c64f251-fc1f-4c38-bd10-af37f39de0b6": 1,
                "3445c14f-87ee-49a0-8fa0-53bcb940bc02": 2,
                "178842c6-56f6-42c2-b4b1-a729c6e7ca9a": 2,
                "41a1a650-e904-4680-931e-32668eacf05c": 1,
                "87734e6d-ef2f-4fd8-b500-07a28be7460d": 1,
                "df4179c0-2f9e-404d-b0bf-533d9dba8708": 1,
                "b02f8c3e-af15-4b9c-ad9e-9d7b4e89f668": 1,
                "d8804067-5e97-4021-8751-16522cf441d2": 1,
                "ee4e79c5-0c7e-4b39-842a-b40aa789eb40": 1,
                "431c5898-80ef-4ab3-9b39-a613cf19cb40": 1,
                "965970f3-50c5-4505-a4ac-edd2d363ee46": 13,
                "6413415b-5d99-4d0b-bf4a-78b78ec9a189": 13,
                "381dece4-f588-4ce0-8888-10b18ba5569c": 1,
                "c4e1ea58-db25-4718-97a0-579358db09f5": 1,
                "357c47f2-ab96-4415-92b2-a9ef4dd2fe7d": 10,
                "7521166b-c4fc-4304-a1d8-d43df64eb6e2": 1,
                "45056362-eb46-4241-a42d-f2854bc99f2d": 230,  # earlsiesta
                "60fd2130-3119-4745-9161-6bd5327f4195": 11,
                "f914bf59-da58-4446-a3c4-37b0ab5afb10": 1,
                "ca709402-4d02-4cc4-ba3f-2fcc58a6bbc2": 10,
                "7680cb25-e5ca-4f2d-b145-37fffdcc3fed": 2,
                "9015bf17-2df6-4411-9acc-09fcfeb01b5f": 1,
                "16c44f72-f840-46e3-820f-36047dc1634c": 1,
                "42c2f144-11d6-4bb0-90a2-50f299eca0d2": 1,
                "c6251d2b-7afe-459b-86cb-a7a19b5393af": 1,
                "a12b9078-e542-4a8f-9945-f6277df5aa07": 1,
                "4ef2e44d-eeb9-409b-9045-642fe7c0ee59": 1,
                "4bf61772-c2df-4686-9faa-f2a63eab3315": 1,
                "468165ed-e121-4b74-b3a0-1296c2be96df": 1,
                "516c3340-397f-4286-b602-56ee1768718b": 1,
                "57d6b2e4-16a3-4003-819c-3e9ccc782f1c": 1,
                "00bb09d0-6ecc-4689-8d34-9b0b08d909d2": 1,
                "ca97b3dc-37b3-4869-844d-c99bc39a2dbc": 1,
                "668acb2d-5ae4-464e-b0c2-e4a9e23ab772": 1,
                "a71c3990-83ad-47d3-a1e8-4356f033d69e": 3,
                "2256478e-b398-4490-9094-7a26ece0a401": 1,
                "f8d36399-62dd-4ace-b260-4eee3d35bf1c": 1,
                "3277b36c-31a4-4149-9830-17cccbe9369c": 1,
                "ad03ae0e-5ab1-48f2-8888-c10fbea85945": 1,
                "f65e2d08-c9e8-42a5-8b85-0c92f5f3bd07": 2,
                "c5d9a884-9cfa-450a-a091-cb467207de12": 10,
                "d56e0ad0-77fe-43fa-853d-52cf46b2ef79": 1,
                "721f52d0-742a-4fdd-9f02-4693062b8d81": 2,
                "32b31491-a4ba-4808-8518-17e89938bc77": 1,
                "c38db87d-bcc1-463f-b7dc-0a47b769ac22": 2,
                "9e2570e5-2a82-4be6-96d8-a49240c12be6": 1,
                "a95681ab-d4fd-4bf7-b94d-3b23622405ee": 10,
                "f95f63ac-a16e-4530-8661-27a8a0a35e13": 2,
                "6f911d0d-485e-46b4-a84e-63d4fa945feb": 10,
                "56e1fdc9-6783-4c17-9af1-f247f0465fa5": 2,
                "e1fc776b-53b7-467e-a5ff-a16b5321ec65": 1,
                "0963b86c-e41a-45fa-8c7c-833f8da656d2": 2,
                "797d2159-8e7e-4a2c-b2af-77d59e471327": 11,
                "9f4f720c-2b44-4cd6-b29d-8e6abc030cd7": 2,
                "424c9086-32bb-4caa-bec9-8f264c6b64f1": 1,
                "43aa3ff0-705d-4e8e-ac8e-3b3a1d6c074e": 1,
                "49df1a13-d770-42c6-b91c-57dd5f90ffe8": 1,
                "4bfa5f12-3e9c-47f1-ab7f-e89b973dfac2": 1,
                "aababc2b-23f5-42bd-8fe4-540b6b2f052e": 1,
                "7a90ffd3-1883-4f95-8636-c41f5776dc80": 3,
                "0765690d-0747-42ca-ad37-5087e5768128": 8,
                "0fb2d2a8-1eeb-4944-a544-54df0a13146c": 1,
                "fbabc311-4197-47fc-b571-075538abea76": 1,
                "cc20b7c4-991d-450d-93ed-48e1fdd3a3e9": 1,
                "76fca743-30e6-4602-882d-3bafa39ab3f1": 1,
            }

            for _ in range(extra_start_rolls.get(self.game_id, 0)):
                self.roll(f"align start {self.game_id} day {self.day}")

            return True
        if self.ty in [EventType.PLAY_BALL]:
            # play ball (already handled above but we want to fetch a tiny tick later)
            if self.event["day"] not in self.fetched_days:
                self.fetched_days.add(self.event["day"])

                timestamp = self.event["created"]
                self.data.fetch_league_data(timestamp, 20)

            for team_id in [self.next_update["homeTeam"], self.next_update["awayTeam"]]:
                team = self.data.get_team(team_id)
                prev_pitcher_id = team.rotation[(team.rotation_slot - 2) % len(team.rotation)]
                prev_pitcher = self.data.get_player(prev_pitcher_id)
                if prev_pitcher.has_mod(Mod.SHELLED):
                    # don't roll immediately after sixpack receives shelled, for some reason that doesn't trigger it
                    # and not in postseason either
                    if self.game_id != "31ae7c75-b30a-49b1-bddd-b40e3ebd518e" and self.day < 99:
                        self.roll("extra roll for shelled pitcher")
            return True
        if self.ty in [EventType.FLAG_PLANTED]:
            for _ in range(11):
                self.roll("flag planted")
            return True
        if self.ty in [EventType.RENOVATION_BUILT]:
            if "% more " in self.desc or "% less " in self.desc:
                self.roll("stat change")
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
        if self.ty in [
            EventType.ITEM_BREAKS,
            EventType.ITEM_DAMAGE,
            EventType.PLAYER_GAINED_ITEM,
            EventType.PLAYER_LOST_ITEM,
            EventType.BROKEN_ITEM_REPAIRED,
            EventType.DAMAGED_ITEM_REPAIRED,
            EventType.TUNNEL_STOLE_ITEM,
        ]:
            if self.ty == EventType.PLAYER_GAINED_ITEM and "gained the Prized" in self.desc:
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

    def handle_polarity(self):
        if self.weather.is_polarity():
            # polarity +/-
            polarity_roll = self.roll("polarity")

            if self.ty == EventType.POLARITY_SHIFT:
                self.log_roll(Csv.WEATHERPROC, "Switch", polarity_roll, True)
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
                self.roll("charm item damage???")
                self.roll("charm item damage???")

                # doesn't happen for Kennedy Loser at 2021-04-06T23:12:09.244Z, but does at 2021-05-21T01:22:53.936Z and again later for Don
                if self.season > 14:
                    self.handle_batter_reverb()

                if self.batting_team.has_mod(Mod.PSYCHIC):
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

    def handle_mild(self):
        mild_roll = self.roll("mild")
        if self.ty == EventType.MILD_PITCH:
            # skipping mild proc

            self.log_roll(Csv.MODPROC, "Mild", mild_roll, True)

            for base, runner_id in zip(self.update["basesOccupied"], self.update["baseRunners"]):
                runner = self.data.get_player(runner_id)
                self.damage(runner, "runner")
                if base == Base.THIRD:
                    self.damage(runner, "runner")

            if "draws a walk." in self.desc and self.event["created"] != "2021-06-16T14:12:09.582Z":
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
                    psychiccontact_roll = self.roll("psychiccontact")  # noqa: F841

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
        else:
            self.damage(self.pitcher, "pitcher")

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
        if (self.batter.has_mod(Mod.DEBT_THREE) or self.batter.has_mod(Mod.DEBT_ZERO)) and fielder and not fielder.has_mod(Mod.COFFEE_PERIL):
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
                            for base, runner_id in zip(self.update["basesOccupied"], self.update["baseRunners"]):
                                runner = self.data.get_player(runner_id)
                                if base == Base.THIRD or base == Base.SECOND:
                                    self.damage(runner, "runner")

                        if "scores!" in self.desc:
                            # todo: is this also a runner?
                            self.damage(self.batter, "batter")

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

                        self.damage(self.pitcher, "pitcher")

                        for rbase in damage_runners:
                            idx = self.update["basesOccupied"].index(rbase)
                            runner_id = self.update["baseRunners"][idx]
                            runner = self.data.get_player(runner_id)
                            self.damage(runner, "runner")

                        return

            self.damage(self.pitcher, "pitcher")
            # there's some weird stuff with damage rolls in the first fragment of s16
            # this seems to work for groundouts but something similar might be up for flyouts
            if (self.season, self.day) >= (15, 3):
                self.damage(self.batter, "fielder")
                self.damage(fielder, "fielder")
            self.try_roll_batter_debt(fielder)

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
            # work around missing data in next_update
            if self.event["created"] == "2021-04-14T15:11:04.159Z":
                roll_outcome = False
            roll = self.roll(f"adv ({base}, {roll_outcome}")
            runner = self.data.get_player(runner_id)

            if runner.undefined():
                self.roll("undefined (runner adv?)")
                pass

            fielder = self.get_fielder_for_roll(defender_roll)
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
            ]

            out_roll, out_threshold = self.roll_out(False)
            if self.season >= 20 and out_roll > out_threshold and self.event["created"] not in fakeout_overrides:
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

                if upgrade_roll > 0.025: # real threshold probably 0.015ish
                    self.error("something is misaligned, this is definitely a real home run")

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
        ]

        fakeout_opposite_overrides = [
            # these ones are ACTUALLY fake
            "2021-06-21T20:06:14.133Z",
            "2021-06-23T22:13:01.358Z",
            "2021-06-24T03:05:50.319Z",
            "2021-06-24T05:09:20.868Z",
        ]

        is_fake_single = False
        if self.season >= 20 and "a Single" in self.desc and (out_roll > out_threshold and self.event["created"] not in fakeout_override) or (self.event["created"] in fakeout_opposite_overrides):
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
            if upgrade_roll > 0.02: # real threshold probably 0.015ish
                self.error("something is misaligned, this is definitely a real hit")
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
            # self.roll("undefined (foul)")            
            # self.roll("undefined (foul)")            
            # self.roll("undefined (foul)")            
            # self.roll("undefined (foul)")            
            # self.roll("undefined (foul)")            

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

        self.damage(self.pitcher, "pitcher")
        self.damage(self.batter, "batter")

    def check_filth_delta(self):
        self.data.fetch_stadiums(self.event["created"])
        filth_before = self.data.get_stadium(self.stadium.id).filthiness
        self.data.fetch_stadiums(self.event["created"], 10)
        filth_after = self.data.get_stadium(self.stadium.id).filthiness
        if filth_before != filth_after:
            self.print(f"!!!FILTH CHANGED: {filth_before} -> {filth_after}")


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

            return True

    def handle_weather(self):
        if self.weather == Weather.SUN_2:
            pass

        elif self.weather == Weather.ECLIPSE:
            threshold = self.get_eclipse_threshold()
            rolled_unstable = False
            eclipse_roll = self.roll("eclipse")

            if self.batter.has_mod(Mod.MARKED):
                self.roll(f"unstable {self.batter.name}")
                rolled_unstable = True
            if self.pitcher.has_mod(Mod.MARKED):
                self.roll(f"unstable {self.pitcher.name}")
                rolled_unstable = True

            if self.ty == EventType.INCINERATION:
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

                if self.pitching_team.has_mod(Mod.FIREPROOF) and self.ty == EventType.INCINERATION_BLOCKED:
                    self.roll("target")
                    return True

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
                if player.has_mod(Mod.FIRE_EATER) and not player.has_mod(Mod.ELSEWHERE):
                    self.roll(f"fire eater ({player.name})")

                    if self.ty == EventType.INCINERATION_BLOCKED:
                        # fire eater proc - target roll maybe?
                        self.roll("target")
                        return True
                    break

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

            if self.batter.has_mod(Mod.HONEY_ROASTED):
                roast_roll = self.roll("honey roasted")
                if self.ty == EventType.TASTE_THE_INFINITE:
                    self.log_roll(
                        Csv.MODPROC,
                        "shelled1",
                        roast_roll,
                        True,
                    )
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
                else:
                    self.log_roll(
                        Csv.MODPROC,
                        "no shell2",
                        poast_roll,
                        False,
                    )

            if self.ty == EventType.TASTE_THE_INFINITE:
                self.roll("target")  # might be team or index
                self.roll("target")  # probably player
                return True

        elif self.weather == Weather.BIRDS:
            bird_roll = self.roll("birds")

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

            # threshold is at 0.0125 at 0.5 fort
            bird_threshold = 0.0125 - 0.02 * (self.stadium.fortification - 0.5)
            if self.event["created"] in ["2021-05-11T09:09:08.543Z"]:
                # might have changed in s18?
                bird_threshold = 1

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
                # handle flood
                swept_players = []
                for runner_id in self.update["baseRunners"]:
                    runner = self.data.get_player(runner_id)

                    exempt_mods = [Mod.EGO1, Mod.SWIM_BLADDER]

                    # unsure when this change was made
                    # we have Pitching Machine (with ego2) swept elsewhere on season 16 day 10
                    # and Aldon Cashmoney (also ego2) kept on base on season 16 day 65
                    if (self.season, self.day) >= (15, 64):
                        exempt_mods += [Mod.EGO2, Mod.EGO3, Mod.EGO4, Mod.LEGENDARY]
                    if not runner.has_any(*exempt_mods):
                        self.roll(f"sweep ({runner.name})")

                        if f"{runner.raw_name} was swept Elsewhere" in self.desc:
                            swept_players.append(runner_id)

                if self.stadium.id and not self.stadium.has_mod(Mod.FLOOD_PUMPS):
                    self.roll("filthiness")
                    self.check_filth_delta()

                if swept_players:
                    # todo: what are the criteria here
                    if not any(filter(lambda p: not self.data.get_player(p).has_mod(Mod.NEGATIVE), swept_players)):
                        return True

                    has_undertaker = False
                    players = (
                        self.batting_team.lineup + self.batting_team.rotation
                    )  # + self.pitching_team.lineup + self.pitching_team.rotation
                    for player_id in players:
                        player = self.data.get_player(player_id)
                        if (
                            player.has_mod(Mod.UNDERTAKER)
                            and not player.has_any(Mod.ELSEWHERE)
                            and player_id not in swept_players
                        ):
                            has_undertaker = True

                    if has_undertaker:
                        self.roll("undertaker")
                        self.roll("undertaker")

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

                for seeker in seekers:
                    self.roll(f"seeker ({seeker.raw_name} {player.raw_name})")
                    if pulled_back and seeker.raw_name in self.desc:
                        self.do_elsewhere_return(player)
                        did_elsewhere_return = True

                if not pulled_back:
                    self.roll(f"elsewhere ({player.raw_name})")

                    if returned:
                        self.do_elsewhere_return(player)
                        did_elsewhere_return = True
        if did_elsewhere_return:
            return

        for player_id in players:
            player = self.data.get_player(player_id)

            if player.has_mod(Mod.SCATTERED):
                unscatter_roll = self.roll(f"unscatter ({player.raw_name})")

                # todo: find actual threshold
                threshold = {
                    12: 0.00061,
                    13: 0.0005,
                    14: 0.0004,
                    15: 0.0004,
                    16: 0.0004,  # todo: we don't know
                    17: 0.00041,  # we have a 0.0004054748749369175
                    18: 0.00042,  # we have a 0.00041710056345256596
                    19: 0.00042,  # 0.00041647177941306346 < t < 0.00042578004132232117
                    20: 0.000485,  # we have a positive at 0.00046131203268795495 and 0.00048491029900765703
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
            if self.event["created"] not in ["2021-04-05T16:24:45.346Z", "2021-04-05T20:08:23.286Z"]:
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

        order_roll = self.roll("consumer team order")
        if order_roll < 0.5:
            teams = [self.away_team, self.home_team]
        else:
            teams = [self.home_team, self.away_team]

        for team in teams:
            if team.level >= 5:
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

                        acc = 0
                        for target, density in zip(roster, densities):
                            acc += density
                            if acc > target_roll * total_density:
                                break
                        self.print(f"(rolled target: {target.name})")
                        if target.id != attacked_player.id:
                            self.error(
                                f"incorrect consumer target (rolled {target.name}, expected {attacked_player.name})"
                            )

                        if self.stadium.has_mod(Mod.SALMON_CANNONS):
                            self.roll("salmon cannons?")
                        if "CONSUMER EXPELLED" in self.desc:
                            return True

                        if "DEFENDS" in self.desc:
                            self.roll("defend item?")
                            return True

                        # todo: kapow etc
                        if "SLAM!" not in self.desc:
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
                        else:
                            # one of these might be a roll for the text?
                            self.roll("uh, what, etc")
                            self.roll("uh, what, etc")
                            
                        return True
                    else:
                        self.log_roll(Csv.CONSUMERS, "Miss", attack_roll, False)
                else:
                    self.log_roll(Csv.CONSUMERS, "Miss", attack_roll, False, attacked_team=team)

    def handle_party(self):
        if self.season != 16 or self.day >= 85:
            # lol. turns out it just rolls party all the time and throws out the roll if the team isn't partying
            party_roll = self.roll("party time")
        else:
            party_roll = 1

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

        # we have a positive case at 0.005210187516443421 (2021-03-19T14:22:26.078Z)
        # and one at 0.005465967826364659 (2021-03-19T07:09:38.068Z)
        # and one at 0.0054753553805302335 (2021-03-17T11:13:54.609Z)
        # and one at 0.005489946742006868 (2021-04-07T16:25:17.109Z)
        # and one at 0.0054976162782947036 (2021-03-05T01:04:16.078Z), pre-ballparks??
        # this is probably influenced by ballpark myst or something (or not??)
        # although a negative case at 2021-06-26T15:05:38.315Z (0.00537)
        elif party_roll < 0.0055 and self.event["created"] not in [
            "2021-06-26T15:05:38.315Z",
            "2021-06-26T16:18:59.850Z",
            "2021-06-26T20:11:44.065Z",
            "2021-06-26T03:26:55.260Z",
            "2021-06-21T19:19:11.857Z",
            "2021-06-21T21:06:09.786Z",
            "2021-06-23T23:15:32.729Z",
            "2021-06-24T02:20:11.278Z",
            "2021-06-24T06:09:46.048Z",
            "2021-06-24T06:14:41.289Z",
            "2021-06-24T07:05:35.942Z",
        ]:
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
            # all firefighters games, where alx is in the ffs shadows
            and self.game_id
            not in [
                "377f87df-36aa-4fac-bc97-59c24efb684b",
                "bfd8dc98-f35a-49d0-b810-2ee38fb6886f",
                "1ad48feb-eb1e-43eb-b28f-aff79d7a3473",
                "4bd6671d-4b6f-4e1f-bff2-34cc1ab96c5e",
                "d12e21ba-5779-44f1-aa83-b788e5da8655",
            ]
        ):
            secret_base_exit_eligible = False
        if (
            self.season >= 18
            and secret_runner_id == "114100a4-1bf7-4433-b304-6aad75904055"
            and secret_runner_id not in self.batting_team.shadows
        ):
            secret_base_exit_eligible = False

        if (
            (17, 27) <= (self.season, self.day)
            and secret_runner_id == "114100a4-1bf7-4433-b304-6aad75904055"
            and secret_runner_id not in self.batting_team.shadows
        ):
            secret_base_exit_eligible = False

        # weird order issues here. when an attractor is placed in the secret base, it only applies the *next* tick
        # likely because of some kinda async function that fills in the field between ticks
        # so we need to do this play count/next check nonsense to get the right roll order
        attractor_eligible = not secret_runner_id
        if attractor_eligible:
            attract_roll = self.roll("secret base attract")
            if attract_roll < 0.00035:  # guessing at threshold, was 0.0002 in s15/s16?
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

                self.roll("trick 1 name")

                m = re.search("They do a .*? \(([0-9]+)\)", self.desc)
                expected_score_1 = int(m.group(1))
                pro_factor = 2 if "Pro Skater" in self.desc else 1
                lo1 = runner.pressurization * 200
                hi1 = runner.cinnamon * 1500 + 500
                expected_roll_lo_1 = (expected_score_1 // pro_factor - lo1) / (hi1 - lo1)
                expected_roll_hi_1 = (expected_score_1 // pro_factor + 1 - lo1) / (hi1 - lo1)
                score_1_roll = self.roll("trick 1 score", expected_roll_lo_1, expected_roll_hi_1)
                score_1 = int((hi1 - lo1) * score_1_roll + lo1) * pro_factor
                self.print(f"(score: {score_1})")

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
                "2021-05-21T05:32:00.224Z": True,
                "2021-06-16T01:14:32.242Z": True,
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
            team = self.data.get_team(meta["teamId"])

            a_player = meta["aPlayerId"]
            b_player = meta["bPlayerId"]
            a_location = (
                team.rotation if meta["aLocation"] == 1 else (team.lineup if meta["aLocation"] == 0 else team.shadows)
            )
            b_location = (
                team.rotation if meta["bLocation"] == 1 else (team.lineup if meta["bLocation"] == 0 else team.shadows)
            )
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
