import math
import os
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
)
from output import SaveCsv
from rng import Rng
from dataclasses import dataclass
from enum import Enum, unique
from typing import List
from formulas import (
    get_contact_strike_threshold,
    get_contact_ball_threshold,
    get_hr_threshold,
    get_strike_threshold,
    get_foul_threshold,
    StatRelevantData,
    get_swing_ball_threshold,
    get_swing_strike_threshold,
)


@unique
class Csv(Enum):
    """
    Tracks the .csv files we can log rolls for in Resim.
    """

    STRIKES = "strikes"
    FOULS = "fouls"
    TRIPLES = "triples"
    DOUBLES = "doubles"
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
    FLAVOR = "flavor"
    SWEET1 = "sweet1"
    SWEET2 = "sweet2"
    WEATHERPROC = "weatherproc"
    MODPROC = "modproc"
    BASE = "base"
    INSTINCTS = "instincts"
    PSYCHIC = "psychic"
    BSYCHIC = "bsychic"


class Resim:
    def __init__(self, rng, out_file, run_name, raise_on_errors=True, csvs_to_log=[]):
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

        if run_name:
            os.makedirs("roll_data", exist_ok=True)
            run_name = run_name.replace(":", "_")
            csvs_to_log = csvs_to_log or list(Csv)
            self.csvs = {csv: SaveCsv(run_name, csv.value) for csv in Csv if csv in csvs_to_log}
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

        # another workaround for bad data
        if self.game_id == "c608b5db-29ad-4216-a703-8f0627057523":
            caleb_novak = self.data.get_player("0eddd056-9d72-4804-bd60-53144b785d5c")
            if caleb_novak.has_mod(Mod.ELSEWHERE):
                caleb_novak.remove_mod(Mod.ELSEWHERE, ModType.PERMANENT)


        self.print()
        if not self.update:
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
            "2021-05-10T19:28:42.723Z": 1,
            "2021-05-11T05:03:22.874Z": 1,

            "2021-05-17T23:10:48.610Z": 1, # something wrong with item damage rolls
            "2021-05-18T02:04:07.079Z": -1, # double strike
            "2021-05-18T02:11:28.932Z": 1, # idk?
            "2021-05-18T02:14:14.532Z": 1, # somewhere around this
            "2021-05-18T02:17:40.187Z": 1, # somewhere around this
            "2021-05-18T02:22:44.148Z": 1, # idk
            "2021-05-18T03:20:25.483Z": 1, # def double strike

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
        if self.ty == EventType.FAX_MACHINE_ACTIVATION:
            # this also interrupts late
            return

        if self.handle_steal():
            return

        if self.handle_electric():
            return

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
        if self.ty in [
            EventType.HOME_FIELD_ADVANTAGE,
            EventType.BECOME_TRIPLE_THREAT,
            EventType.SOLAR_PANELS_AWAIT,
            EventType.SOLAR_PANELS_ACTIVATION,
            EventType.HOMEBODY,
            EventType.SUPERYUMMY,
            EventType.PERK,
            EventType.SHAME_DONOR,
            EventType.PSYCHO_ACOUSTICS,
            EventType.AMBITIOUS,
            EventType.LATE_TO_THE_PARTY,
            EventType.MIDDLING,
            EventType.SHAMING_RUN,
            EventType.EARLBIRD,
            EventType.PRIZE_MATCH,
            EventType.A_BLOOD_TYPE,
        ]:
            if self.ty == EventType.PSYCHO_ACOUSTICS:
                self.roll("which mod?")
            if self.ty == EventType.A_BLOOD_TYPE:
                self.roll("a blood type")

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

            # todo: clean this up, see if we can find a better check for "is this a holiday inning party" elsewhere
            if "is Partying" in self.desc:
                team = self.data.get_team(self.event["teamTags"][0])
                if not team.has_mod(Mod.PARTY_TIME) and self.day < 27:
                    # this is a holiday inning party (why 26?)
                    for _ in range(26):
                        self.roll("stat")

            if "entered the Shadows" in self.desc:
                # fax machine dunk
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
            if self.weather == Weather.SALMON:
                self.try_roll_salmon()


            if self.next_update["topOfInning"]:
                is_holiday = self.next_update.get("state", {}).get("holidayInning")
                # if this was a holiday inning then we already rolled in the block below

                # hm was ratified in the season 18 election
                has_hotel_motel = self.stadium.has_mod(Mod.HOTEL_MOTEL) or self.season >= 18
                if has_hotel_motel and not is_holiday:
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

            if "was restored!" in self.desc or "was repaired." in self.desc or "were repaired." in self.desc:
                self.roll("restore item??")
                self.roll("restore item??")
                self.roll("restore item??")

            if self.stadium.has_mod(Mod.SALMON_CANNONS):
                self.roll("salmon cannons")

                if "caught in the bind!" in self.desc:
                    self.roll("salmon cannons player")
            return True

        if self.ty == EventType.HOLIDAY_INNING:
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

            if self.season >= 17:
                self.roll("prize match")

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
                "5deffffd-97bd-44b3-bb5d-6a03e91065b0": 1,
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
                "09aa60b8-aa2a-42ab-92c2-e00a0954c25d": 8, # prize match??
                "e2a7f575-b165-485f-b1c9-39a3c8edacbf": 16, # prize match
                "883b56f8-d470-4a9f-b709-7647ffcac4cc": 1,
                "f39fc061-5485-4140-9ec0-92d716c1fa67": 1,
                "ca53fd25-ed06-4d6d-b0ae-80d0a1b58ed1": 9,
                "24506e8e-e774-4566-a1d5-ecfb2616efc2": 19,
                "a581bfd7-725f-49a3-83ff-dc98806ef262": 16,
                "88147839-a9c7-44f8-a5aa-e3c733a5013a": 10, # prize match
                "2b9d87df-a76a-48d1-aea2-d0be9876c857": 11, # prize match
                "0cde3960-b7dd-4df2-b469-5274be158563": 1,
                "8a90bd4b-9f51-4c2e-9c24-882dabdfe932": 1,
                "1a84542b-abd4-42aa-86b3-1a89a80184f6": 14, # prize match
                "0a79fdbb-73ca-4b8e-8696-10776d75cd0f": 1,
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

            if self.weather in [
                Weather.FEEDBACK,
                Weather.REVERB,
            ] and self.stadium.has_mod(Mod.PSYCHOACOUSTICS):
                self.print("away team mods:", self.away_team.print_mods(ModType.PERMANENT))
                self.roll("echo team mod")
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
        ]:
            if self.ty in [EventType.ITEM_BREAKS, EventType.ITEM_DAMAGE] and "CONSUMERS" not in self.desc:
                self.roll("which item")

            if self.ty == EventType.PLAYER_GAINED_ITEM and "gained the Prized" in self.desc:
                # prize match reward
                self.roll("prize target")
            return True
        if self.ty == EventType.PLAYER_SWAP:
            return True
        if self.ty in [EventType.PLAYER_HIDDEN_STAT_INCREASE, EventType.PLAYER_HIDDEN_STAT_DECREASE]:
            return True
        if self.ty == EventType.WEATHER_CHANGE:
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

            if " charmed " in self.desc:
                self.log_roll(
                    Csv.MODPROC,
                    "Charmed",
                    charm_roll,
                    True,
                )
                self.damage(self.batter, "batter")
                self.damage(self.batter, "batter")
                self.damage(self.batter, "batter")
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
                self.log_roll(
                    Csv.MODPROC,
                    "Zap",
                    electric_roll, 
                    True
                )
            if self .ty != EventType.STRIKE_ZAPPED:
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

            return True

        elif self.pitcher.has_mod(Mod.WILD) and self.ty != EventType.MILD_PITCH:
            self.log_roll(Csv.MODPROC, "NoMild", mild_roll, False)

    def roll_hr(self, is_hr):
        roll = self.roll("home run")

        threshold = get_hr_threshold(
            self.batter, self.batting_team, self.pitcher, self.pitching_team, self.stadium, self.get_stat_meta()
        )
        if is_hr and roll > threshold:
            self.print("!!! warn: home run roll too high ({} > {})".format(roll, threshold))
        elif not is_hr and roll < threshold:
            self.print("!!! warn: home run roll too low ({} < {})".format(roll, threshold))
        return roll

    def roll_swing(self, did_swing: bool):
        roll = self.roll("swing")

        if self.is_strike:
            threshold = get_swing_strike_threshold(
                self.batter, self.batting_team, self.pitcher, self.pitching_team, self.stadium, self.get_stat_meta()
            )
        else:
            threshold = get_swing_ball_threshold(
                self.batter, self.batting_team, self.pitcher, self.pitching_team, self.stadium, self.get_stat_meta()
            )

        can_swing = True
        if self.batting_team.has_mod(Mod.O_NO) and self.strikes == self.max_strikes - 1:
            can_swing = False

        if can_swing:
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
        roll = self.roll("contact")

        if self.is_strike:
            threshold = get_contact_strike_threshold(
                self.batter, self.batting_team, self.pitcher, self.pitching_team, self.stadium, self.get_stat_meta()
            )
        else:
            threshold = get_contact_ball_threshold(
                self.batter, self.batting_team, self.pitcher, self.pitching_team, self.stadium, self.get_stat_meta()
            )

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
        value = self.throw_pitch("ball")
        self.log_roll(Csv.STRIKES, "Ball", value, False)

        if not self.is_flinching():
            swing_roll = self.roll_swing(False)
            if swing_roll < 0.05:
                self.print("!!! very low swing roll on ball")
            self.log_roll(Csv.SWING_ON_BALL, "Ball", swing_roll, False)

        if self.ty == EventType.WALK:
            # pitchers: convert walk to strikeout (failed)
            if self.pitching_team.has_mod("PSYCHIC"):
                psychic_roll = self.roll("walk-strikeout")
                self.log_roll(Csv.PSYCHIC,
                "Fail",
                psychic_roll,
                False
                )
                
            if "uses a Mind Trick" in self.desc:
                # batter successfully converted strikeout to walk
                psychiccontact_roll = self.roll("psychiccontact")

                if "strikes out swinging." in self.desc:
                    bsychic_roll = self.roll("bsychic")
                    self.log_roll(Csv.BSYCHIC,
                        "Success",
                        bsychic_roll,
                        True
                        )

        if self.ty == EventType.WALK:

            if self.batting_team.has_mod(Mod.BASE_INSTINCTS):
                instinct_roll = self.roll("base instincts")

                if "Base Instincts take them directly to" in self.desc:
                    self.log_roll(Csv.MODPROC, "Walk", instinct_roll, True)
                    base_roll = self.roll("which base")
                    base_two_roll = self.roll("which base")

                    if "Base Instincts take them directly to second base!" in self.desc:
                        #Note: The fielder roll is used here as the formula multiplies two rolls together and this is the easiest way to log two rolls at once
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
                did_score = runner_id not in self.next_update["baseRunners"]
                if did_score:
                    runner = self.data.get_player(runner_id)
                    self.damage(runner, "runner")

            self.damage(self.batter, "batter")
        self.damage(self.pitcher, "pitcher")

    def handle_strike(self):
        if ", swinging" in self.desc or "strikes out swinging." in self.desc:
            self.throw_pitch()
            if not self.is_flinching():
                swing_roll = self.roll_swing(True)
                self.log_roll(
                    Csv.SWING_ON_STRIKE if self.is_strike else Csv.SWING_ON_BALL,
                    "StrikeSwinging",
                    swing_roll,
                    True,
                )

            contact_roll = self.roll_contact(False)
            self.log_roll(Csv.CONTACT, "StrikeSwinging", contact_roll, False)
        elif ", looking" in self.desc or "strikes out looking." in self.desc:
            value = self.throw_pitch("strike")
            self.log_roll(Csv.STRIKES, "StrikeLooking", value, True)

            if not self.is_flinching():
                swing_roll = self.roll_swing(False)
                self.log_roll(Csv.SWING_ON_STRIKE, "StrikeLooking", swing_roll, False)

        if "strikes out thinking." in self.desc:
            # pitcher: convert walk to strikeout (success)
            # not logging these rn
            self.roll("strike")
            self.roll("swing")
            mindtrick_roll = self.roll("Psychic")
            self.log_roll(Csv.PSYCHIC,
            "Success",
            mindtrick_roll,
            True
            )

        elif ", flinching" in self.desc:
            value = self.throw_pitch("strike")
            self.log_roll(Csv.STRIKES, "StrikeFlinching", value, True)

        if "strikes out" in self.desc:
            # batters: convert strikeout to walk (failed)
            if self.batting_team.has_mod(Mod.PSYCHIC):
                bpsychic_roll = self.roll("strikeout-walk")
                self.log_roll(Csv.BSYCHIC,
                "Fail",
                bpsychic_roll,
                False,
                )

            if self.pitcher.has_mod(Mod.PARASITE) and self.weather == Weather.BLOODDRAIN:
                self.roll("parasite") # can't remember what this is

        self.damage(self.pitcher, "pitcher")

    def try_roll_salmon(self):
        # don't reroll if we *just* reset
        if "The Salmon swim upstream!" in self.update["lastUpdate"]:
            return

        last_inning = self.next_update["inning"] - 1
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

    def get_fielder_for_roll(self, fielder_roll: float):
        candidates = [self.data.get_player(player) for player in self.pitching_team.lineup]
        candidates = [c for c in candidates if not c.has_mod(Mod.ELSEWHERE)]

        return candidates[math.floor(fielder_roll * len(candidates))]

    def handle_out(self):
        self.throw_pitch()
        if not self.is_flinching():
            swing_roll = self.roll_swing(True)
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

        named_fielder = None
        if self.ty == EventType.FLY_OUT:  # flyout
            out_fielder_roll = self.roll("out fielder")
            out_roll = self.roll("out")
            fly_fielder_roll, fly_fielder = self.roll_fielder(check_name=not is_fc_dp)
            fly_roll = self.roll("fly")
            self.log_roll(
                Csv.FLY,
                "Flyout",
                fly_roll,
                True,
                fielder_roll=out_fielder_roll,
                fielder=self.get_fielder_for_roll(out_fielder_roll),
            )
            self.log_roll(
                Csv.OUT,
                "Flyout",
                out_roll,
                False,
                fielder_roll=out_fielder_roll,
                fielder=self.get_fielder_for_roll(out_fielder_roll),
            )
            named_fielder = fly_fielder
        elif self.ty == EventType.GROUND_OUT:  # ground out
            out_fielder_roll = self.roll("out fielder")
            out_roll = self.roll("out")
            fly_fielder_roll, fly_fielder = self.roll_fielder(check_name=False)
            fly_roll = self.roll("fly")
            ground_fielder_roll, ground_fielder = self.roll_fielder(check_name=not is_fc_dp)
            self.log_roll(
                Csv.FLY,
                "GroundOut",
                fly_roll,
                False,
                fielder_roll=out_fielder_roll,
                fielder=self.get_fielder_for_roll(out_fielder_roll),
            )
            self.log_roll(
                Csv.OUT,
                "GroundOut",
                out_roll,
                False,
                fielder_roll=out_fielder_roll,
                fielder=self.get_fielder_for_roll(out_fielder_roll),
            )
            named_fielder = ground_fielder

        if self.outs < self.max_outs - 1:
            self.handle_out_advances(named_fielder)
        elif not is_fc_dp:
            self.try_roll_batter_debt(named_fielder)

        # some of these are "in between" the advancement rolls when applicable
        # not entirely sure where, so leaving them out here for now
        # the order of these three (relatively) *is* correct though, definitely pitcher-batter-fielder.
        self.damage(self.pitcher, "pitcher")
        if not is_fc_dp:
            self.damage(self.batter, "fielder")
        if named_fielder and not is_fc_dp:
            self.damage(named_fielder, "fielder")

    def try_roll_batter_debt(self, fielder):
        if self.batter.has_mod(Mod.DEBT_THREE) and fielder and not fielder.has_mod(Mod.COFFEE_PERIL):
            self.roll("batter debt")

    def roll_fielder(self, check_name=True):
        eligible_fielders = []
        fielder_idx = None
        for fielder_id in self.pitching_team.lineup:
            fielder = self.data.get_player(fielder_id)
            if fielder.has_mod(Mod.ELSEWHERE):
                continue

            # cut off extra parts with potential name collisions
            if check_name:
                # self.print(desc)
                desc = self.desc
                desc = desc.split("out to ")[1]
                if "advances on the sacrifice" in desc:
                    desc = desc.rsplit(". ", 1)[0]  # damn you kaj statter jr.
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
                        Csv.FLYOUT, "advance", adv_roll, roll_outcome, fielder=fielder, relevant_runner=runner
                    )

                    if roll_outcome:
                        self.damage(runner, "batter")

                        # the logic does properly "remove" the runner when scoring from third, though
                        if base == Base.THIRD:
                            is_third_free = True
                            self.damage(runner, "batter")
                    else:
                        break

        elif self.ty == EventType.GROUND_OUT:
            if len(self.update["basesOccupied"]) > 0:
                dp_roll = self.roll("dp?")

                if Base.FIRST in self.update["basesOccupied"]:
                    is_dp = "into a double play!" in self.desc
                    self.log_roll(Csv.GROUNDOUT_FORMULAS, "DP", dp_roll, is_dp, fielder=fielder)

                    if is_dp:
                        self.roll("dp where")  # (index into basesOccupied)

                        # todo: this might be the *pitcher*? we know there's one less roll if the pitcher is careful
                        self.damage(self.pitcher, "pitcher")

                        if self.outs < self.max_outs - 2:
                            for base, runner_id in zip(self.update["basesOccupied"], self.update["baseRunners"]):
                                runner = self.data.get_player(runner_id)
                                if base == Base.THIRD or base == Base.SECOND:
                                    self.damage(runner, "runner")

                        if "scores!" in self.desc:
                            # todo: is this also a runner?
                            self.damage(self.batter, "batter")
                        return

                    fc_roll = self.roll("martyr?")  # high = fc
                    is_fc = "on fielder's choice" in self.desc
                    self.log_roll(Csv.GROUNDOUT_FORMULAS, "Sac", fc_roll, not is_fc, fielder=fielder)

                    if is_fc:
                        if Base.THIRD in self.update["basesOccupied"]:
                            third_id = self.update["baseRunners"][0]
                            third = self.data.get_player(third_id)
                            self.damage(third, "batter")
                            self.damage(third, "batter")
                        elif Base.SECOND in self.update["basesOccupied"]:
                            second_id = self.update["baseRunners"][0]
                            second = self.data.get_player(second_id)
                            self.damage(self.batter, "batter") # uhhhhhhh also needed for careful but this prob isn't the right way
                        return

            self.try_roll_batter_debt(fielder)

            forced_bases = 0
            while forced_bases in self.update["basesOccupied"]:
                forced_bases += 1

            for base, runner_id in zip(self.update["basesOccupied"], self.update["baseRunners"]):
                runner = self.data.get_player(runner_id)

                was_forced = base < forced_bases
                roll_outcome = did_advance(base, runner_id) if not was_forced else None

                adv_roll = self.roll(f"adv? {base}/{runner.name} ({roll_outcome})")

                if roll_outcome and base == Base.THIRD and not was_forced:
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

                    if base == Base.THIRD:
                        self.damage(runner, "batter")

    def handle_hit_advances(self, bases_hit, defender_roll):
        bases_before = make_base_map(self.update)
        bases_after = make_base_map(self.next_update)
        for runner_id, base, roll_outcome in calculate_advances(bases_before, bases_after, bases_hit):
            roll = self.roll(f"adv ({base}, {roll_outcome}")
            runner = self.data.get_player(runner_id)
            fielder = self.get_fielder_for_roll(defender_roll)
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

            # damage scores on extra advances
            if base == Base.THIRD and roll_outcome:
                self.damage(runner, "runner")

    def handle_hr(self):
        if " is Magmatic!" not in self.desc:
            self.throw_pitch()
            if not self.is_flinching():
                swing_roll = self.roll_swing(True)
                self.log_roll(
                    Csv.SWING_ON_STRIKE if self.is_strike else Csv.SWING_ON_BALL,
                    "HR",
                    swing_roll,
                    True,
                )

            contact_roll = self.roll_contact(True)
            self.log_roll(Csv.CONTACT, "HomeRun", contact_roll, True)

            self.roll_foul(False)
            fielder_roll = self.roll("out fielder")
            out_roll = self.roll("out")

            self.log_roll(
                Csv.OUT,
                "HR",
                out_roll,
                True,
                fielder_roll=fielder_roll,
                fielder=self.get_fielder_for_roll(fielder_roll),
            )

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
            buckets_roll = self.roll("big buckets")
            if "lands in a Big Bucket." in self.desc:
                self.log_roll(
                    Csv.MODPROC,
                    "Bucket",
                    buckets_roll,
                    True,
                )
            else:
                self.log_roll(
                    Csv.MODPROC,
                    "NoBucket",
                    buckets_roll,
                    False,
                )

    def handle_base_hit(self):
        self.throw_pitch()
        if not self.is_flinching():
            swing_roll = self.roll_swing(True)
            self.log_roll(
                Csv.SWING_ON_STRIKE if self.is_strike else Csv.SWING_ON_BALL,
                "BaseHit",
                swing_roll,
                True,
            )

        contact_roll = self.roll_contact(True)
        self.log_roll(Csv.CONTACT, "BaseHit", contact_roll, True)

        self.roll_foul(False)

        fielder_roll = self.roll("out fielder")
        out_roll = self.roll("out")

        self.log_roll(
            Csv.OUT,
            "BaseHit",
            out_roll,
            True,
            fielder_roll=fielder_roll,
            fielder=self.get_fielder_for_roll(fielder_roll),
        )

        hr_roll = self.roll_hr(False)
        self.log_roll(Csv.HR, "BaseHit", hr_roll, False)

        defender_roll = self.roll("hit fielder")

        double_roll = self.roll("double")
        triple_roll = self.roll("triple")

        hit_bases = 0
        if "hits a Single!" in self.desc:
            hit_bases = 1
        elif "hits a Double!" in self.desc:
            hit_bases = 2
        elif "hits a Triple!" in self.desc:
            hit_bases = 3

        if hit_bases < 3:
            self.log_roll(
                Csv.DOUBLES,
                f"Hit{hit_bases}",
                double_roll,
                hit_bases == 2,
                fielder_roll=fielder_roll,
                fielder=self.get_fielder_for_roll(defender_roll),
            )

        self.log_roll(
            Csv.TRIPLES,
            f"Hit{hit_bases}",
            triple_roll,
            hit_bases == 3,
            fielder_roll=fielder_roll,
            fielder=self.get_fielder_for_roll(defender_roll),
        )

        self.damage(self.pitcher, "pitcher")
        self.damage(self.batter, "batter")
        self.handle_hit_advances(hit_bases, defender_roll)

        # tentative: damage every runner at least once?
        for base, runner_id in zip(self.update["basesOccupied"], self.update["baseRunners"]):
            runner = self.data.get_player(runner_id)
            self.damage(runner, "batter")

            is_force_score = base >= (3 - hit_bases)  # fifth base lol
            if is_force_score:
                self.damage(runner, "batter")

        if self.batting_team.has_mod(Mod.AAA) and hit_bases == 3:
            # todo: figure out if this checks mod origin or not
            if not self.batter.has_mod(Mod.OVERPERFORMING):
                self.roll("power chAAArge")

        if self.batting_team.has_mod(Mod.AA) and hit_bases == 2:
            # todo: figure out if this checks mod origin or not
            if not self.batter.has_mod(Mod.OVERPERFORMING):
                self.roll("power chAArge")

    def get_stat_meta(self):
        is_maximum_blaseball = (
            self.strikes == self.max_strikes - 1
            and self.balls == self.max_balls - 1
            and self.outs == self.max_outs - 1
            and self.update["basesOccupied"] == [Base.THIRD, Base.SECOND, Base.FIRST]
        )
        return StatRelevantData(
            self.weather,
            self.season,
            self.day,
            len(self.update["basesOccupied"]),
            self.update["topOfInning"],
            is_maximum_blaseball,
        )

    def roll_foul(self, known_outcome: bool):
        is_0_no_eligible = self.batting_team.has_mod(Mod.O_NO) and self.strikes == 2 and self.balls == 0
        if is_0_no_eligible or self.batter.has_any(Mod.CHUNKY, Mod.SMOOTH):
            known_outcome = None

        meta = self.get_stat_meta()
        threshold = get_foul_threshold(self.batter, self.batting_team, self.stadium, meta)
        lower_bound = threshold if known_outcome is False else 0
        upper_bound = threshold if known_outcome is True else 1

        foul_roll = self.roll("foul", lower=lower_bound, upper=upper_bound)
        if known_outcome is not None:
            if known_outcome and foul_roll > threshold:
                self.print(f"!!! too high foul roll ({foul_roll} > {threshold})")
            elif not known_outcome and foul_roll < threshold:
                self.print(f"!!! too low foul roll ({foul_roll} < {threshold})")
        outcomestr = "Foul" if known_outcome else "Fair"
        self.log_roll(Csv.FOULS, outcomestr, foul_roll, known_outcome)

    def handle_foul(self):
        self.throw_pitch()

        if not self.is_flinching():
            swing_roll = self.roll_swing(True)
            self.log_roll(
                Csv.SWING_ON_STRIKE if self.is_strike else Csv.SWING_ON_BALL,
                "Foul",
                swing_roll,
                True,
            )

        contact_roll = self.roll_contact(True)
        self.log_roll(Csv.CONTACT, "Foul", contact_roll, True)

        self.roll_foul(True)

        self.damage(self.pitcher, "pitcher")
        self.damage(self.batter, "batter")

    def handle_batter_up(self):
        batter = self.batter
        if self.ty == EventType.BATTER_SKIPPED:
            # find the batter that *would* have been at bat
            lineup = self.batting_team.lineup
            index = self.next_update["awayTeamBatterCount"] if self.next_update["topOfInning"] else self.next_update["homeTeamBatterCount"]
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
            eclipse_roll = self.roll("eclipse")

            if self.batter.has_mod(Mod.MARKED):
                self.roll("unstable")
            if self.pitcher.has_mod(Mod.MARKED):
                self.roll("unstable")

            if self.ty == EventType.INCINERATION:
                if "A Debt was collected" not in self.desc:
                    self.log_roll(Csv.WEATHERPROC, "Burn", eclipse_roll, True)
                    
                    self.roll("target")

                    if self.season >= 16:
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

            fire_eater_eligible = self.pitching_team.lineup + [
                self.batter.id,
                self.pitcher.id,
            ]
            for player_id in fire_eater_eligible:
                player = self.data.get_player(player_id)

                if player.has_mod(Mod.FIRE_EATER) and not player.has_mod(Mod.ELSEWHERE):
                    self.roll(f"fire eater ({player.name})")

                    if player.has_mod(Mod.MARKED) and not self.batter.has_mod(Mod.MARKED):
                        self.roll("extra roll just for basilio fig")

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

            if self.ty == EventType.BLOODDRAIN_SIPHON:
                self.roll("siphon proc1")
                self.roll("siphon proc2")
                self.roll("siphon proc3")
                self.roll("siphon proc4")

                # these ones are 1 more for some reason. don't know
                if self.event["created"] in [
                    "2021-03-17T03:20:31.620Z",
                    "2021-04-07T13:02:47.102Z",
                    "2021-03-03T03:17:25.555Z",
                    "2021-03-03T05:17:29.552Z",
                    "2021-03-03T06:13:25.353Z",
                    "2021-03-03T18:26:00.538Z",
                    "2021-03-09T06:07:27.564Z",
                    "2021-03-04T06:05:07.060Z",
                    "2021-03-11T06:16:24.968Z",
                    "2021-04-07T18:07:53.969Z",
                ]:
                    self.roll("siphon proc 5?")
                return True

            if self.ty == EventType.BLOODDRAIN:
                self.roll("blooddrain proc1")
                self.roll("blooddrain proc2")
                self.roll("blooddrain proc3")

                # todo: why are these shorter?
                if self.event["created"] not in [
                    "2021-03-09T10:27:56.571Z",
                    "2021-03-11T03:12:13.124Z",
                    "2021-03-12T01:07:27.467Z",
                ]:
                    self.roll("blooddrain proc4")

                # todo: ???
                if self.event["created"] in [
                    "2021-03-12T01:10:43.414Z",
                    "2021-04-21T18:00:46.683Z",
                    "2021-05-18T10:20:04.864Z",
                ]:
                    self.roll("blooddrain proc")
                return True
            
            if self.ty == EventType.BLOODDRAIN_BLOCKED:
                self.roll("blooddrain proc1")
                self.roll("blooddrain proc2")
                self.roll("blooddrain proc3")
                self.roll("blooddrain proc4")
                return True

        elif self.weather == Weather.PEANUTS:
            flavor_roll = self.roll("peanuts")
            if self.ty == EventType.PEANUT_FLAVOR_TEXT:
                self.log_roll(
                    Csv.FLAVOR,
                    "Text",
                    flavor_roll,
                    True,
                )
            else:
                self.log_roll(
                    Csv.FLAVOR,
                    "NoText",
                    flavor_roll,
                    False,
                )

            if self.ty == EventType.PEANUT_FLAVOR_TEXT:
                self.roll("peanut message")
                return True

            allergy_roll = self.roll("peanuts")
            if self.ty == EventType.ALLERGIC_REACTION:
                self.log_roll(
                    Csv.WEATHERPROC,
                    "Allergy",
                    allergy_roll,
                    True,
                )
                self.roll("target")
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
            select_roll = self.roll("feedbackselection")  #60/40 Batter/Pitcher
            feedback_roll = self.roll("feedback")  # feedback event y/n
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

                # i think it would be extremely funny if these are item damage rolls
                # imagine getting feedbacked to charleston *and* you lose your shoes.
                if self.event["created"] == "2021-04-14T00:19:59.567Z":
                    self.roll("feedback???")
                    self.roll("feedback???")
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
                # todo: how many rolls? this needs a refactor and doesn't support lineup shuffles rn

                if "were shuffled in the Reverb!" in self.desc:
                    for _ in range(16):
                        self.roll("reverb shuffle?")
                elif "several players shuffled" in self.desc:
                    # 2021-04-15T01:08:22.391Z
                    for _ in range(9):
                        self.roll("reverb shuffle?")
                elif "lineup shuffled in the Reverb!" in self.desc:
                    # 2021-04-15T20:06:11.850Z
                    self.print(f"(lineup length: {len(self.pitching_team.lineup)})")

                    amount = 10
                    if self.event["created"] == "2021-05-11T02:19:07.285Z":
                        amount = 8
                    if self.event["created"] == "2021-05-18T03:10:44.033Z":
                        amount = 11
                    for _ in range(amount):
                        self.roll("reverb shuffle?")

                    if self.event["created"] == "2021-04-16T02:10:17.885Z":
                        self.roll("reverb shuffle?")
                else:
                    for _ in range(2):
                        self.roll("reverb shuffle?")

                    for _ in range(len(self.pitching_team.rotation)):
                        self.roll("reverb shuffle?")

                    if self.event["created"] == "2021-04-14T02:17:09.483Z":
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
                quality_roll = self.roll("coffee proc1")
                flavor_roll = self.roll("coffee proc")

                return True

            if self.batter.has_mod(Mod.COFFEE_PERIL):
                self.roll("observed?")

        elif self.weather == Weather.COFFEE_2:
            coffee2_roll = self.roll("coffee 2")
            if self.ty == EventType.GAIN_FREE_REFILL and not self.stadium.has_mod(Mod.SWEETENER):
                self.log_roll(
                    Csv.WEATHERPROC,
                    "Refill",
                    coffee2_roll,
                    True
                )
            if self.ty != EventType.GAIN_FREE_REFILL and not self.stadium.has_mod(Mod.SWEETENER):
                self.log_roll(
                    Csv.WEATHERPROC,
                    "NoRefill",
                    coffee2_roll,
                    False
                )
            if self.ty == EventType.GAIN_FREE_REFILL and self.stadium.has_mod(Mod.SWEETENER):
                self.log_roll(
                    Csv.SWEET2,
                    "Refill",
                    coffee2_roll,
                    True
                )
            if self.ty != EventType.GAIN_FREE_REFILL and self.stadium.has_mod(Mod.SWEETENER):
                self.log_roll(
                    Csv.SWEET2,
                    "NoRefill",
                    coffee2_roll,
                    False
                )

            if self.ty == EventType.GAIN_FREE_REFILL:
                quality_roll = self.roll("coffee 2 proc1")
                flavor_one_roll = self.roll("coffee 2 proc2")
                flavor_two_roll = self.roll("coffee 2 proc3")
                return True

            if self.batter.has_mod(Mod.COFFEE_PERIL):
                self.roll("observed?")

        elif self.weather == Weather.COFFEE_3S:
            if self.batter.has_mod(Mod.COFFEE_PERIL):
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
                for runner_id in self.update["baseRunners"]:
                    runner = self.data.get_player(runner_id)

                    exempt_mods = [Mod.EGO1, Mod.SWIM_BLADDER]
                    if self.season >= 15:
                        exempt_mods += [Mod.EGO2, Mod.EGO3, Mod.EGO4]
                    if not runner.has_any(*exempt_mods):
                        self.roll(f"sweep ({runner.name})")

                if self.stadium.id and not self.stadium.has_mod(Mod.FLOOD_PUMPS):
                    self.roll("filthiness")
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
        for player_id in players:
            player = self.data.get_player(player_id)

            if player.has_mod(Mod.ELSEWHERE):
                self.roll(f"elsewhere ({player.raw_name})")

                if self.ty == EventType.RETURN_FROM_ELSEWHERE and player.raw_name in self.desc:
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
                    16: 0.0004, # todo: we don't know
                    17: 0.00041, # we have a 0.0004054748749369175
                    18: 0.00041, # todo: we don't know
                }[self.season]

                if unscatter_roll < threshold:
                    self.roll(f"unscatter letter ({player.raw_name})")

    def do_elsewhere_return(self, player):
        scatter_times = 0
        should_scatter = False
        if "days" in self.desc:
            elsewhere_time = int(self.desc.split("after ")[1].split(" days")[0])
            if elsewhere_time > 18:
                should_scatter = True
        if "season" in self.desc:
            should_scatter = True

        if should_scatter:
            scatter_times = (len(player.raw_name) - 2) * 2
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

                        for item in attacked_player.items:
                            if item.health > 0:
                                # pick item to break maybe? or something??
                                self.roll("???")
                                return True

                        # todo: find out where this is
                        if self.stadium.has_mod(Mod.SALMON_CANNONS):
                            self.roll("salmon cannons?")

                        for _ in range(25):
                            self.roll("stat change")

                            if attacked_player.soul == 1:
                                # lost their last soul, redact :<
                                self.print(f"!!! {attacked_player.name} lost last soul, " f"redacting")
                                if attacked_player_id in team.lineup:
                                    team.lineup.remove(attacked_player_id)
                                if attacked_player_id in team.rotation:
                                    team.rotation.remove(attacked_player_id)

                        return True
                    else:
                        self.log_roll(Csv.CONSUMERS, "Miss", attack_roll, False)
                else:
                    self.log_roll(Csv.CONSUMERS, "Miss", attack_roll, False, attacked_team=team)

    def handle_party(self):
        if self.season != 16:
            # lol. turns out it just rolls party all the time and throws out the roll if the team isn't partying
            party_roll = self.roll("party time")
        else:
            # todo: what do we do in s17? i haven't gotten that far
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
        elif party_roll < 0.0055:
            team_roll = self.roll("target team (not partying)")
            if team_roll < 0.5 and self.home_team.has_mod(Mod.PARTY_TIME):
                self.print("!!! home team is in party time")
            elif team_roll > 0.5 and self.away_team.has_mod(Mod.PARTY_TIME):
                self.print("!!! away team is in party time")

    def handle_ballpark(self):

        if self.stadium.has_mod(Mod.PEANUT_MISTER):
            mister_roll = self.roll("peanut mister")
            if self.ty == EventType.PEANUT_MISTER:
                self.log_roll(Csv.MODPROC, "Cure", mister_roll, True)
            if self.ty != EventType.PEANUT_MISTER:
                self.log_roll(Csv.MODPROC, "NoCure", mister_roll, False)

            if self.ty == EventType.PEANUT_MISTER:
                self.roll("target")
                return True

        if self.stadium.has_mod(Mod.SMITHY):
            smithy_roll = self.roll("smithy")

            if self.ty == EventType.SMITHY_ACTIVATION:
                self.log_roll(Csv.MODPROC, "Fix", smithy_roll, True)

                player_roll = self.roll("smithy1")
                item_roll = self.roll("smithy2")
                return True
            else: 
                self.log_roll(Csv.MODPROC, "NoFix", smithy_roll, False)

        # WHY DOES GLITTER ROLL HERE
        if self.weather == Weather.GLITTER:
            glitter_roll = self.roll("glitter")

            if self.ty == EventType.GLITTER_CRATE_DROP:
                self.log_roll(Csv.WEATHERPROC, "LootDrop", glitter_roll, True)
                self.roll("receiving team")
                self.roll("receiving player")

                # fmt: off
                glitter_lengths = {
                    "2021-04-13T23:09:03.266Z": 11,  # Inflatable Sunglasses
                    "2021-04-13T23:15:49.175Z": 5,   # Cap
                    "2021-04-14T03:02:56.577Z": 5,   # Cap
                    "2021-04-14T03:08:02.423Z": 4,   # Sunglasses
                    "2021-04-14T11:03:16.318Z": 4,   # Sunglasses
                    "2021-04-14T11:11:16.266Z": 11,  # Bat of Vanity
                    "2021-04-14T15:11:14.466Z": 5,   # Bat
                    "2021-04-14T21:13:25.144Z": 4,   # Necklace
                    "2021-04-15T07:04:22.275Z": 5,   # Shoes
                    "2021-04-15T07:08:27.800Z": 10,  # Leg Glove
                    "2021-04-15T07:09:02.365Z": 12,  # Cryogenic Shoes
                    "2021-04-15T07:11:27.306Z": 5,   # Ring
                    "2021-04-15T09:21:46.071Z": 9,   # Golden Bat
                    "2021-04-15T15:11:08.363Z": 5,   # Shoes
                    "2021-04-15T22:21:35.826Z": 9,   # Shoes of Blaserunning
                    "2021-04-16T04:02:46.484Z": 9,   # Parasitic Ring
                    "2021-04-16T04:11:23.475Z": 13,  # Chaotic Jersey
                    "2021-04-16T13:06:47.014Z": 14,  # Metaphorical Shoes
                }
                # fmt: on
                for _ in range(glitter_lengths[self.event["created"]]):
                    self.roll("item")
                return True

            else: 
                self.log_roll(Csv.WEATHERPROC, "NootDrop", glitter_roll, False)

        if self.stadium.has_mod(Mod.SECRET_BASE):
            if self.handle_secret_base():
                return True

        if self.stadium.has_mod(Mod.GRIND_RAIL):
            if self.handle_grind_rail():
                return True

        league_mods = self.data.sim["attr"]
        if "SECRET_TUNNELS" in league_mods:
            self.roll("tunnels")

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
        secret_base_exit_eligible = Base.SECOND not in bases and secret_runner_id
        if secret_runner_id:
            # what is the exact criteria here?
            # we have ghost Elijah Bates entering a secret base in 42a824ba-bd7b-4b63-aeb5-a60173df136e
            # (null leagueTeamId) and that *does* have an exit roll on the "wrong side"
            # so maybe it just checks "if present on opposite team" rather than "is not present on current team"? or
            # it's special handling for null team
            pitching_lineup = self.pitching_team.lineup
            secret_runner = self.data.get_player(secret_runner_id)
            if secret_runner_id in pitching_lineup:
                self.print("can't exit secret base on wrong team", secret_runner.name)
                secret_base_exit_eligible = False

        # todo: figure out how to query "player in active team's shadow" and exclude those properly
        if self.season >= 17 and secret_runner_id == "070758a0-092a-4a2c-8a16-253c835887cb":
            secret_base_exit_eligible = False
        if self.season >= 18 and secret_runner_id == "114100a4-1bf7-4433-b304-6aad75904055":
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
                    self.print("!!! warn: should add attractor but could not find any")

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
                runner_idx = self.update["basesOccupied"].index(1)
                runner_id = self.update["baseRunners"][runner_idx]
                runner = self.data.get_player(runner_id)
                self.print(f"!!! redacted baserunner: {runner.name}")

                # remove baserunner from roster so fielder math works.
                # should probably move this logic into a function somehow
                self.batting_team.lineup.remove(runner_id)
                runner.add_mod(Mod.REDACTED, ModType.PERMANENT)

                # and just as a cherry on top let's hack this so we don't roll for steal as well
                self.update["basesOccupied"].remove(1)
                self.update["baseRunners"].remove(runner_id)

    def handle_grind_rail(self):
        if Base.FIRST in self.update["basesOccupied"] and Base.THIRD not in self.update["basesOccupied"]:
            # i have no idea why this rolls twice but it definitely *does*
            grindfielder_roll = self.roll("grindfielder")

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

                score_1_roll = self.roll("trick 1 score")
                lo1 = runner.pressurization * 200
                hi1 = runner.cinnamon * 1500 + 500
                score_1 = int((hi1 - lo1) * score_1_roll + lo1)
                self.print(f"(score: {score_1})")

                firsttrick_roll = self.roll("trick 1 success")
                if "but lose their balance and bail!" in self.desc:
                    self.log_roll(Csv.TRICK_ONE, 
                    "Fail", 
                    firsttrick_roll,
                    False, 
                    relevant_batter=self.batter,
                    relevant_runner=runner, 
                    )

                else:
                    self.log_roll(Csv.TRICK_ONE, 
                    "Pass", 
                    firsttrick_roll,
                    True,
                    relevant_batter=self.batter,
                    relevant_runner=runner,
                    ) 

                if "lose their balance and bail!" not in self.desc:
                    self.roll("trick 2 name")
                    score_2_roll = self.roll("trick 2 score")
                    lo2 = runner.pressurization * 500
                    hi2 = runner.cinnamon * 3000 + 1000
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
        self.print(f"- base states: {bases}")

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

        for i, base in enumerate(bases):
            if base + 1 not in bases or (
                # This is weird, but adding an extra roll here seems like the only way to get S15D75 to line up.
                # https://reblase.sibr.dev/game/9d224696-6775-42c0-8259-b4de84f850a8#b65483bc-a07f-88e3-9e30-6ff9365f865b
                bases == [Base.THIRD, Base.FIRST, Base.SECOND]
                and base == Base.FIRST
            ):
                runner = self.data.get_player(self.update["baseRunners"][i])

                steal_roll = self.roll(f"steal ({base})")

                was_success = self.ty == EventType.STOLEN_BASE and base + 1 == base_stolen
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

                    self.damage(runner, "batter")
                    if was_caught and self.season >= 15:
                        self.damage(steal_fielder, "fielder")

                    return True

            if (
                bases == [Base.THIRD, Base.THIRD]
                or bases == [Base.THIRD, Base.SECOND, Base.THIRD]
                or bases == [Base.SECOND, Base.FIRST, Base.SECOND]
            ):
                # don't roll twice when holding hands
                break

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

        lower_bound = threshold if known_result == "ball" else 0
        upper_bound = threshold if known_result == "strike" else 1

        roll = self.roll("strike", lower=lower_bound, upper=upper_bound)
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

        if self.pitching_team.has_mod("FIERY") and self.strikes < self.max_strikes - 1:
            if self.is_strike:
                double_strike_roll = self.roll("double strike")
                success = "fires a Double Strike" in self.desc
                self.log_roll(Csv.MODPROC, "Double Strike" if success else "Single Strike", double_strike_roll, success)
            else:
                self.print("!!! double strike eligible!")

        return roll

    def damage(self, player: PlayerData, position: str):
        if self.season < 15:
            return

        if player.has_mod(Mod.CAREFUL):
            self.print(f"item damage skipped ({player.name} is careful)")
            return

        # threshold seems to vary between 0.0002 and >0.0015
        # depending on which position or which type of roll?
        # i tried a few things here but i'm not confident in anything
        # so the "which item to break" is just moved into the misc handler for now
        self.roll(f"item damage ({player.name})")

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
        relevant_runner_multiplier = self.get_runner_multiplier(relevant_runner)
        runners_on_bases = zip(self.update["basesOccupied"], self.update["baseRunners"])
        runner_1st = [r for base, r in runners_on_bases if base == Base.FIRST]
        runner_2nd = [r for base, r in runners_on_bases if base == Base.SECOND]
        runners_3rd = [r for base, r in runners_on_bases if base == Base.THIRD]
        if runner_1st:
            runner_on_first = self.data.get_player(runner_1st[0])
            runner_on_first_multiplier = self.get_runner_multiplier(runner_on_first)
        else:
            runner_on_first, runner_on_first_multiplier = None, 1
        if runner_2nd:
            runner_on_second = self.data.get_player(runner_2nd[0])
            runner_on_second_multiplier = self.get_runner_multiplier(runner_on_second)
        else:
            runner_on_second, runner_on_second_multiplier = None, 1
        if runners_3rd:
            runner_on_third = self.data.get_player(runners_3rd[0])
            runner_on_third_multiplier = self.get_runner_multiplier(runner_on_third)
        else:
            runner_on_third, runner_on_third_multiplier = None, 1
        if len(runners_3rd) == 2:  # Holding hands
            runner_on_third_hh = self.data.get_player(runners_3rd[1])
            runner_on_third_hh_multiplier = self.get_runner_multiplier(runner_on_third_hh)
        else:
            runner_on_third_hh, runner_on_third_hh_multiplier = None, 1
        null_player = PlayerData.null()
        null_team = TeamData.null()
        self.csvs[csv].write(
            event_type,
            roll,
            passed,
            relevant_batter or self.batter or null_player,
            self.batting_team,
            self.pitcher,
            self.pitching_team,
            self.stadium,
            self.update,
            0,
            0,
            self.get_batter_multiplier(relevant_batter),
            self.get_pitcher_multiplier(),
            self.is_strike,
            self.strike_roll,
            self.strike_threshold,
            fielder_roll,
            fielder or null_player,
            self.get_fielder_multiplier(fielder) if fielder else 1,
            relevant_runner or null_player,
            relevant_runner_multiplier,
            runner_on_first or null_player,
            runner_on_first_multiplier,
            runner_on_second or null_player,
            runner_on_second_multiplier,
            runner_on_third or null_player,
            runner_on_third_multiplier,
            runner_on_third_hh or null_player,
            runner_on_third_hh_multiplier,
            self.next_update["basesOccupied"] if self.next_update else None,
            attacked_team or null_team,
        )

    def setup_data(self, event):
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
        if not update and not next_update:
            if self.play <= 0:
                return
            prev_update = self.data.get_update(self.game_id, self.play - 1)
            if not prev_update:
                return
            # use the previous values as a guess, but be able to distinguish that there's missing data
            update = NullUpdate(prev_update)
        if not update:
            update = next_update

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
                self.batter.raw_name = self.update["awayBatterName"]
                self.pitcher.raw_name = self.update["homePitcherName"]
            else:
                self.batter.raw_name = self.update["homeBatterName"]
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
            else:
                team = self.data.get_team(event["teamTags"][0])
                team.add_mod(meta["mod"], meta["type"])

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
            else:
                team = self.data.get_team(event["teamTags"][0])

                if not team.has_mod(meta["mod"], meta["type"]):
                    self.print(f"!!! warn: trying to remove mod {meta['mod']} but can't find it")
                else:
                    team.remove_mod(meta["mod"], meta["type"])

        # mod replaced
        if event["type"] in [EventType.CHANGED_MODIFIER]:
            if event["playerTags"]:
                player = self.data.get_player(event["playerTags"][0])
                player.remove_mod(meta["from"], meta["type"])
                player.add_mod(meta["to"], meta["type"])
            else:
                team = self.data.get_team(event["teamTags"][0])
                team.remove_mod(meta["from"], meta["type"])
                team.add_mod(meta["to"], meta["type"])

        # timed mods wore off
        if event["type"] in [EventType.MOD_EXPIRES]:
            if event["playerTags"]:
                for mod in meta["mods"]:
                    player = self.data.get_player(event["playerTags"][0])
                    if not player.has_mod(mod, meta["type"]):
                        self.print(f"!!! warn: trying to remove mod {mod} but can't find it")
                    else:
                        player.remove_mod(mod, meta["type"])

            else:
                for mod in meta["mods"]:
                    team = self.data.get_team(event["teamTags"][0])
                    team.remove_mod(mod, meta["type"])

        # echo mods added/removed
        if event["type"] in [
            EventType.REMOVED_MULTIPLE_MODIFICATIONS_ECHO,
            EventType.ADDED_MULTIPLE_MODIFICATIONS_ECHO,
        ]:
            player = self.data.get_player(event["playerTags"][0])
            for mod in meta.get("adds", []):
                player.add_mod(mod["mod"], mod["type"])
            for mod in meta.get("removes", []):
                player.remove_mod(mod["mod"], mod["type"])

        # cases where the tagged player needs to be refetched (party, consumer, incin replacement)
        if event["type"] in [
            EventType.PLAYER_STAT_INCREASE,
            EventType.PLAYER_STAT_DECREASE,
            EventType.PLAYER_HATCHED,
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

        if event["type"] in [EventType.ITEM_BREAKS, EventType.ITEM_DAMAGE, EventType.BROKEN_ITEM_REPAIRED, EventType.DAMAGED_ITEM_REPAIRED]:
            player_id = event["playerTags"][0]
            player = self.data.get_player(player_id)
            for item in player.items:
                if item.id == meta["itemId"]:
                    item.health = meta["itemHealthAfter"]
            player.update_stats()
    
        if event["type"] == EventType.HYPE_BUILT:
            self.stadium.hype = meta["after"]


    def find_start_of_inning_score(self, game_id, inning):
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

    def roll(self, label, lower: float = 0, upper: float = 1) -> float:
        value = self.rng.next()
        self.print(f"{label}: {value}")

        # hacky way to figure out what index this roll is in the overall list
        idx = 0
        if self.roll_log:
            if self.roll_log[-1].event_id == self.event["id"]:
                idx = self.roll_log[-1].index + 1

        log_obj = LoggedRoll(self.event["id"], idx, self.event["created"], label, lower, upper)
        self.roll_log.append(log_obj)
        return value

    def get_batter_multiplier(self, relevant_batter=None, relevant_attr=None):
        # todo: retire in favor of get_multiplier() in formulas.py? this is only being used for logging right now...
        batter = relevant_batter or self.batter

        batter_multiplier = 1
        for mod in itertools.chain(batter.mods, self.batting_team.mods):
            mod = Mod.coerce(mod)
            if mod == Mod.OVERPERFORMING:
                batter_multiplier += 0.2
            elif mod == Mod.UNDERPERFORMING:
                batter_multiplier -= 0.2
            elif mod == Mod.GROWTH:
                batter_multiplier += min(0.05, 0.05 * (self.day / 99))
            elif mod == Mod.HIGH_PRESSURE:
                # checks for flooding weather and baserunners
                if self.weather == Weather.FLOODING and len(self.update["baseRunners"]) > 0:
                    # "won't this stack with the overperforming mod it gives the team" yes. yes it will.
                    batter_multiplier += 0.25
            elif mod == Mod.TRAVELING:
                if self.update["topOfInning"]:
                    batter_multiplier += 0.05
            elif mod == Mod.SINKING_SHIP:
                roster_size = len(self.batting_team.lineup) + len(self.batting_team.rotation)
                batter_multiplier += (14 - roster_size) * 0.01
            elif mod == Mod.AFFINITY_FOR_CROWS and self.weather == Weather.BIRDS:
                batter_multiplier += 0.5
            elif mod == Mod.CHUNKY and self.weather == Weather.PEANUTS:
                # todo: handle carefully! historical blessings boosting "power" (Ooze, S6) boosted groundfriction
                #  by half of what the other two attributes got. (+0.05 instead of +0.10, in a "10% boost")
                # gfric boost hasn't been "tested" necessarily
                if relevant_attr in ["musclitude", "divinity"]:
                    batter_multiplier += 1.0
                elif relevant_attr == "ground_friction":
                    batter_multiplier += 0.5
            elif mod == Mod.SMOOTH and self.weather == Weather.PEANUTS:
                # todo: handle carefully! historical blessings boosting "speed" (Spin Attack, S6) boosted everything in
                #  strange ways: for a "15% boost", musc got +0.0225, cont and gfric got +0.075, laser got +0.12.
                # the musc boost here has been "tested in the data", the others have not
                if relevant_attr == "musclitude":
                    batter_multiplier += 0.15
                elif relevant_attr == "continuation":
                    batter_multiplier += 0.50
                elif relevant_attr == "ground_friction":
                    batter_multiplier += 0.50
                elif relevant_attr == "laserlikeness":
                    batter_multiplier += 0.80
            elif mod == Mod.ON_FIRE:
                # still some room for error here (might include gf too)
                if relevant_attr == "thwackability":
                    batter_multiplier += 4 if self.season >= 13 else 3
                if relevant_attr == "moxie":
                    batter_multiplier += 2 if self.season >= 13 else 1
        return batter_multiplier

    def get_pitcher_multiplier(self, relevant_attr=None):
        # todo: retire in favor of get_multiplier() in formulas.py? this is only being used for logging right now...
        pitcher_multiplier = 1

        # growth or traveling do not work for pitchers as of s14
        for mod in itertools.chain(self.pitcher.mods, self.pitching_team.mods):
            mod = Mod.coerce(mod)
            if mod == Mod.OVERPERFORMING:
                pitcher_multiplier += 0.2
            elif mod == Mod.UNDERPERFORMING:
                pitcher_multiplier -= 0.2
            elif mod == Mod.SINKING_SHIP:
                roster_size = len(self.pitching_team.lineup) + len(self.pitching_team.rotation)
                pitcher_multiplier += (14 - roster_size) * 0.01
            elif mod == Mod.AFFINITY_FOR_CROWS and self.weather == Weather.BIRDS:
                pitcher_multiplier += 0.5
            elif mod == Mod.HIGH_PRESSURE:
                # "should we really boost the pitcher when the *other* team's batters are on base" yes.
                if self.weather == Weather.FLOODING and len(self.update["baseRunners"]) > 0:
                    pitcher_multiplier += 0.25
        return pitcher_multiplier

    def get_fielder_multiplier(self, relevant_fielder=None, relevant_attr=None):
        # todo: retire in favor of get_multiplier() in formulas.py? this is only being used for logging right now...
        if not relevant_fielder:
            return 1
        fielder = relevant_fielder

        fielder_multiplier = 1
        for mod in itertools.chain(fielder.mods, self.pitching_team.mods):
            mod = Mod.coerce(mod)
            if mod == Mod.OVERPERFORMING:
                fielder_multiplier += 0.2
            elif mod == Mod.UNDERPERFORMING:
                fielder_multiplier -= 0.2
            elif mod == Mod.GROWTH:
                fielder_multiplier += min(0.05, 0.05 * (self.day / 99))
            elif mod == Mod.HIGH_PRESSURE:
                # checks for flooding weather and baserunners
                if self.weather == Weather.FLOODING and len(self.update["baseRunners"]) > 0:
                    # "won't this stack with the overperforming mod it gives the team" yes. yes it will.
                    fielder_multiplier += 0.25
            elif mod == Mod.TRAVELING:
                if not self.update["topOfInning"]:
                    fielder_multiplier += 0.05
            elif mod == Mod.SINKING_SHIP:
                roster_size = len(self.pitching_team.lineup) + len(self.pitching_team.rotation)
                fielder_multiplier += (14 - roster_size) * 0.01
            # elif mod == Mod.AFFINITY_FOR_CROWS and self.weather == Weather.BIRDS:
            #     fielder_multiplier += 0.5
            elif mod == Mod.SHELLED:
                # lol, lmao
                # is it this, or is it "mul = 0", I wonder
                fielder_multiplier -= 1.0
        return fielder_multiplier

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

        if self.event["created"] == "2021-04-12T16:22:20.933Z":
            self.roll("!!! todo")

    def get_runner_multiplier(self, runner, relevant_attr=None):

        runner_multiplier = 1

        # It looks like no multipliers apply based on hit advancement.

        return runner_multiplier

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


def calculate_advances(bases_before, bases_after, bases_hit):
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
        for base in range(3, 6):
            if base in bases:
                del bases[base]

    third_scored = len(bases_after) < len(bases)

    rolls = []
    occupied = sorted(bases.keys(), reverse=True)
    for runner in occupied:
        player = bases[runner]

        is_eligible = runner + 1 not in bases
        if is_eligible:
            if runner == 2:
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