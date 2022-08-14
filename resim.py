import math
import os
import sys
import itertools

from data import EventType, GameData, Mod, NullUpdate, Weather, get_feed_between
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
    HAUNTED = "haunted"


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
                jands.data["permAttr"].append(Mod.OVERPERFORMING.value)
                jands.update_mods()

        # another workaround for bad data
        if self.game_id == "c608b5db-29ad-4216-a703-8f0627057523":
            caleb_novak = self.data.get_player("0eddd056-9d72-4804-bd60-53144b785d5c")
            if caleb_novak.has_mod(Mod.ELSEWHERE):
                caleb_novak.data["permAttr"].remove(Mod.ELSEWHERE.value)
                caleb_novak.update_mods()

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

        if self.handle_misc():
            return

        if self.handle_elsewhere_scattered():
            return

        if self.ty in [
            EventType.BATTER_SKIPPED,
            EventType.RETURN_FROM_ELSEWHERE,
        ]:
            # skipping elsewhere/elsewhere return
            return

        if self.batter:
            self.print("- batter mods: {} + {} ({})".format(self.batter.mods, self.batting_team.mods, self.batter.name))
        if self.pitcher:
            self.print(
                "- pitcher mods: {} + {} ({})".format(self.pitcher.mods, self.pitching_team.mods, self.pitcher.name)
            )
        self.print("- stadium mods: {} ({})".format(self.stadium.mods, self.stadium.nickname))

        if self.ty == EventType.BATTER_UP:
            self.handle_batter_up()
            return

        if self.handle_weather():
            return

        if self.handle_party():
            return

        # has to be rolled after party
        if self.handle_flooding():
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

        # todo: don't know where this actually is - seems to be before mild at least
        if self.pitcher.has_mod(Mod.DEBT_THREE) and not self.batter.has_mod(Mod.COFFEE_PERIL):
            self.roll("debt")
            if self.ty == EventType.HIT_BY_PITCH:
                # debt success
                return True

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

        if self.was_attractor_placed_in_secret_base_async():
            self.roll("attractor pitching stars")
            self.roll("attractor batting stars")
            self.roll("attractor baserunning stars")
            self.roll("attractor defense stars")

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
        ]:
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
            # skip party/consumer stat change
            return True
        if self.ty in [
            EventType.PLAYER_BORN_FROM_INCINERATION,
            EventType.ENTER_HALL_OF_FLAME,
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
            # skip liquid/plasma plot nonsense
            if self.ty == EventType.ENTERING_CRIMESCENE:
                for _ in range(25):
                    self.roll("stat")

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
        if self.ty in [EventType.REVERB_ROTATION_SHUFFLE, EventType.REVERB_FULL_SHUFFLE]:
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
                    "home pitcher mods: {} ({})".format(self.home_pitcher.data["permAttr"], self.home_pitcher.name)
                )
                self.print(
                    "away pitcher mods: {} ({})".format(self.away_pitcher.data["permAttr"], self.away_pitcher.name)
                )
                if "TRIPLE_THREAT" in self.home_pitcher.data["permAttr"] or self.weather == Weather.COFFEE_3S:
                    self.roll("remove home pitcher triple threat")
                if "TRIPLE_THREAT" in self.away_pitcher.data["permAttr"] or self.weather == Weather.COFFEE_3S:
                    self.roll("remove away pitcher triple threat")
            # todo: salmon
            return True
        if self.ty in [EventType.HALF_INNING]:
            # skipping top-of/bottom-of
            if self.next_update["topOfInning"]:
                pass

            if self.weather == Weather.SALMON:
                self.try_roll_salmon()
            return True
        if self.ty == EventType.SALMON_SWIM:
            self.roll("salmon")

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
        ]:
            # skipping game end

            if self.ty == EventType.GAME_END and self.weather.is_coffee():
                # end of coffee game redaction
                rosters = (
                    self.home_team.lineup + self.home_team.rotation + self.away_team.lineup + self.away_team.rotation
                )
                for player_id in rosters:
                    player = self.data.get_player(player_id)
                    if player.has_mod(Mod.COFFEE_PERIL):
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
                "608b496a-1b2c-4d5e-9251-011f949baafa": 1,
                "fa9dab2a-409c-4886-979c-f1c584518d5d": 1,
                "3244b12f-838a-4d75-abde-88874b75ab04": 0,
                "a47f2a8b-0bde-42c8-bdd0-0513da92a6b1": 1,
                "e07d8602-ec51-4ef6-be20-4a07da6b457e": 2,
                "f7985270-455e-4bf7-83fb-948ac326c8af": 2,
                "6c5396bd-bbe4-45df-842b-72d9a01fff4b": 1,
                "20cd1579-e8b8-488f-8579-d1c11c95218e": 0,
                "dcbc2123-c46a-4d21-8501-302f84ca8207": 1,
                "fb3add1d-c711-42b3-8ca8-a5d1086c0429": 1,
                "9eaf6ba7-14b0-4570-917b-acd6ff6a425b": 1,
                "a89f342d-7014-4f11-bb90-ecdb6fe73de6": 1,
                "080e5fb4-0322-44db-8407-3761f84600a3": 2,
                "3e4f43d3-2f5a-4283-8065-ff5fa881c888": 1,
                "3c1b4d10-78af-4b8e-a9f5-e6ea2d50e5c4": 2,
                "c84df551-f639-470a-8435-bd305af0847f": 1,
                "4d898adc-8085-406b-967d-e36321eb2a14": 1,
                "5491123b-9d35-4cf1-9db2-422378e1541e": 1,
                "96d81673-e752-4fc3-8e32-6068f330a278": 1,
                "65949d33-9b8f-4422-9b63-70af548e1fbf": 1,
                "0575b652-a5a9-40b6-ac20-3d92c72044bc": 1,
                "1095a2fd-f0b7-4d07-a0e2-e91d7fa3f5ea": 1,
                "e9fc696d-6c4c-4bca-bbfa-301a50b7917c": 1,
                "6c986027-2100-4372-bc90-1adad22489e2": 1,
                "741b5632-fbf8-49e7-9a64-9c92e636ea7a": 1,
                "cc2d060c-c0a4-471b-a848-d9038c1881e0": 1,
                "e1748a76-eb68-4cd7-a0a4-9132155142a6": 1,
                "15097b04-c186-4402-a7f2-e373dceb8ed6": 1,
                "7efb55e2-8009-46da-a9aa-ca92a120d59e": 1,
                "ec1ab96f-40e2-4335-bb7a-945cbeadb75e": 1,
                "dcd6d171-a761-494e-a4e0-95abc4e28a60": 1,
                "d00b2402-3756-4489-aeba-5f771da9868b": 1,
                "3b3ad672-3846-496e-8c8a-9ac19a563644": 1,
                "196f195c-f8b2-44e9-b117-a7a46de390cd": 1,
                "c7a63a95-53bc-44a7-a5e3-c3d9d1bf8779": 1,
                "d022b5e3-3ab2-48e9-baae-85cc48e3d01a": 1,
                "502d6a06-1975-4c70-94d6-bdf9e31aaec6": 1,
                "d41babda-81bd-4992-a0e6-b389db1b080d": 1,
                "bf7d15e6-62b2-4e03-a752-dd51beffd519": 1,
                "c9c94bc2-7c34-4803-9df2-0c3c3bfe183c": 1,
                "6a00cc1f-9f26-4528-9a84-e6f253a28635": 1,
                "2dff1e11-c2b9-4423-9930-6bb96d1a72d7": 1,
                "c09fbaf1-c068-45a5-b644-e481f18be0bd": 217,  # ...earlsiesta reading???
                "936a0ceb-5027-4a1a-a608-2c7e58bf387b": 1,
                "2898a325-68c1-4521-a531-8437b86feb91": 1,
                "3f5507e4-7058-4fc5-afa2-4be16e681c24": 1,
                "f03707f1-8612-4b8c-bfcb-e84c5d9cc760": 1,
                "24ff0b2e-ecb7-4f4c-aac2-18dac4911109": 1,
                "f1925518-e056-46f6-be9a-fefd09c0c259": 1,
                "94785708-7b40-47b7-a258-9ce10a157395": 9,  # earlsiesta reading
                "e39803d0-add7-43cb-b472-04f04e4b0935": 1,
                "12b62fd9-36ac-4744-8d67-20820bb68e77": 1,
                "d5d3d040-571c-42cd-8e45-a79c2c8255ac": 1,
                "483c8a63-4925-46b4-954d-c9cdebb4591a": 1,
                "657f5360-7875-4abf-b2f5-54c4c25e170e": 1,
                "fa25ee09-7889-4276-8b52-ac46f0e51cf5": 1,
                "0b4929f8-68ed-4c99-b3bd-b65a7d8bc63e": 1,
                "5a350a9d-8c13-49be-b4ca-845d5573ff6d": 1,
                "f15ace24-7fae-46f2-b16e-c18bb4bd630f": 1,
                "3ff91111-7862-442e-aa59-c338871c63fe": 2,
                "1514e79b-e14b-45e0-aada-dad2ba4d753d": 1,
                "6173c3f5-f244-405d-b9a3-62fe8c48e656": 1,
                "7fda4e9c-a20e-4163-aba3-6ad1663a747f": 1,
                "b35f095d-9bc9-4a1c-822a-3749a7b83bcb": 1,
                "a327e425-aaf4-4199-8292-bba0ec4a226a": 2,
                "9e28de60-f139-43fd-ad75-f9ef757a53b6": 1,
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

            if self.weather in [
                Weather.FEEDBACK,
                Weather.REVERB,
            ] and self.stadium.has_mod(Mod.PSYCHOACOUSTICS):
                self.print("away team mods:", self.away_team.data["permAttr"])
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

    def handle_bird_ambush(self):
        if self.weather == Weather.BIRDS:
            # todo: does this go here or nah
            # self.print("bird ambush eligible? {}s/{}b/{}o".format(self.strikes, self.balls, self.outs))
            if self.strikes == 0:
                self.roll("bird ambush")
                if self.ty == EventType.FRIEND_OF_CROWS:
                    self.handle_batter_reverb()  # i guess???
                    return True

    def handle_charm(self):
        pitch_charm_eligible = self.update["atBatBalls"] == 0 and self.update["atBatStrikes"] == 0
        batter_charm_eligible = self.batting_team.has_mod(Mod.LOVE) and pitch_charm_eligible
        pitcher_charm_eligible = self.pitching_team.has_mod(Mod.LOVE) and pitch_charm_eligible

        # before season 16, love blood only proc'd when the player also had love blood
        if self.event["season"] < 15:
            if self.batter.data["blood"] != 9:
                batter_charm_eligible = False

            if self.pitcher.data["blood"] != 9:
                pitcher_charm_eligible = False

        # todo: figure out logic order when both teams have charm
        if self.event["created"] == "2021-03-19T06:16:10.085Z":
            self.roll("charm 2?")

        if batter_charm_eligible or pitcher_charm_eligible:
            self.roll("charm")
            if " charms " in self.desc:
                self.handle_batter_reverb()  # apparently don mitchell can do this.
                return True
            if " charmed " in self.desc:
                # self.roll("charm proc")
                # self.roll("charm proc")
                # self.roll("charm proc")
                return True

    def handle_electric(self):
        # todo: don't roll this if <s15 and batter doesn't have electric blood?
        # only case here would be baldwin breadwinner in s14 but it seems to work okay?
        if self.batting_team.has_mod(Mod.ELECTRIC) and self.update["atBatStrikes"] > 0:
            self.roll("electric")

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
        self.roll("mild")
        if self.ty == EventType.MILD_PITCH:
            # skipping mild proc
            return True

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

        if not (self.batting_team.has_mod(Mod.O_NO) and self.strikes == self.max_strikes - 1):
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

        if self.ty == EventType.WALK and self.batting_team.has_mod(Mod.BASE_INSTINCTS):
            self.roll("base instincts")

            if "Base Instincts take them directly to" in self.desc:
                self.roll("which base")
                self.roll("which base")

    def handle_strike(self):
        if ", swinging" in self.desc or "strikes out swinging." in self.desc:
            self.throw_pitch()
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
        elif ", flinching" in self.desc:
            value = self.throw_pitch("strike")
            self.log_roll(Csv.STRIKES, "StrikeFlinching", value, True)
        pass

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
                self.roll("salmon")

    def is_flinching(self):
        return self.batter.has_mod(Mod.FLINCH) and self.strikes == 0

    def get_fielder_for_roll(self, fielder_roll: float):
        candidates = [self.data.get_player(player) for player in self.pitching_team.lineup]
        candidates = [c for c in candidates if not c.has_mod(Mod.ELSEWHERE)]

        return candidates[math.floor(fielder_roll * len(candidates))]

    def handle_out(self):
        self.throw_pitch()
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

        fielder = None
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
            fielder = fly_fielder
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
            fielder = ground_fielder

        if self.outs < self.max_outs - 1:
            self.handle_out_advances(fielder)

        if not is_fc_dp and self.batter.has_mod(Mod.DEBT_THREE) and fielder and not fielder.has_mod(Mod.COFFEE_PERIL):
            self.roll("debt")

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

        bases_before = make_base_map(self.update)
        bases_after = make_base_map(self.next_update)

        if self.ty == EventType.FLY_OUT:
            # flyouts are NOT nice and simple
            # -If there are baserunners:
            #     -Roll advancement
            #         -Check roll against most advanced runner
            #         -If fail, end.
            #         -If pass and no other baserunners, end.
            #         -If pass and there are other baserunners...
            #         -If most advanced runner was on 2nd aka initial state was [1, 0], end. <--- This is the weird part
            #         -Roll advancement again
            #             -Check roll against second most advanced runner
            #             -end <--- also kind of weird

            # rolls_advance = []
            # if self.update(['basesOccupied']):
            #     base =
            #     rolls_advance.append(self.roll(f"adv ({base}, {roll_outcome})"))
            # rolls_advance.append()

            rolls_advance = []
            for runner_id, base, roll_outcome in calculate_advances(bases_before, bases_after, 0):
                rolls_advance.append(self.roll(f"adv ({base}, {roll_outcome})"))

                # todo: check to make sure this doesn't break later stuff
                if self.update["basesOccupied"] == [2, 2] and base == 2 and not roll_outcome and "scores!" in self.desc:
                    rolls_advance.append(self.roll("holding hands case 2"))

                # or are they? [2,0] -> [2,0] = 1 roll?
                # [1, 0] -> [2, 0] = 1 roll?
                # but a [2, 0] -> [0] score is 2, so it's not like it never rolls twice (unless it's special cased...)
                if not roll_outcome or base == 1:
                    break

                # our code doesn't handle each baserunner twice so i'm cheating here
                # rerolling for the "second" player on third's advance if the first successfully advanced,
                # since it's possible for both
                if self.update["basesOccupied"] == [2, 2] and base == 2 and roll_outcome:
                    rolls_advance.append(self.roll("holding hands"))
            self.log_roll(Csv.FLYOUT, "flyout", rolls_advance, False, fielder=fielder)

        elif self.ty == EventType.GROUND_OUT:
            # All groundout baserunner situations and the number of extra rolls used
            # "!" means this roll is solved, "?" means good hunch and we should confirm
            # DP can end the inning!
            # DP always has an out at 1st
            # Successful DP always have 2 rolls (DP check + where check)
            extras = {
                (tuple(), tuple()): 0,
                ((0,), tuple()): 2,  # !DP roll (pass), DP where (unused)
                ((0,), (0,)): 2,  # !DP roll (fail), !martyr roll (fail)
                ((0,), (1,)): 3,  # !DP roll (fail), !martyr roll (pass) + advance (unused)
                ((1,), (1,)): 2,  # !unused, !advance (fail)
                ((1,), (2,)): 2,  # !unused, !advance (pass)
                ((2,), tuple()): 2,  # !unused, !advance (pass)
                ((2,), (2,)): 2,  # !unused, !advance (fail)
                ((1, 0), tuple()): 2,  # !DP roll (pass), DP where (unused)
                ((1, 0), (1,)): 2,  # !DP roll (pass), !roll<0.50 out at 3rd
                ((1, 0), (2,)): 2,  # !DP roll (pass), !roll>0.50 out at 2nd
                ((1, 0), (1, 0)): 2,  # !DP roll (fail), !martyr roll (fail)
                ((1, 0), (2, 1)): 4,  # !DP roll (fail), !martyr roll (pass), advancex2 (unused)
                ((2, 0), tuple()): 2,  # !DP roll (pass), DP where (unused)
                ((2, 0), (0,)): 4,  # !DP roll (fail), !martyr roll (pass), !3rd advance (pass), !1st advance (fail)
                ((2, 0), (1,)): 4,  # !DP roll (fail), !martyr roll (pass), !3rd advance (pass), !1st advance (pass)
                ((2, 0), (2, 1)): 4,  # !DP roll (fail), !martyr roll (pass), !3rd advance (fail), advance (unused)
                ((2, 1), (1,)): 3,  # !unused, !3rd advance (pass), !2nd advance (fail)
                ((2, 1), (2,)): 3,  # !unused, !3rd advance (pass), !2nd advance (pass)
                ((2, 1), (2, 1)): 3,  # !unused, !3rd advance (fail), !2nd advance (fail)
                ((2, 1), (2, 2)): 3,  # !unused, !3rd advance (fail), !2nd advance (pass)
                ((2, 2), tuple()): 3,  # !unused, !3rd advance (pass), !3rd advance (pass)
                ((2, 2), (2,)): 3,  # !unused !3rd advance (fail/pass), !3rd advance (pass/fail)
                ((2, 2), (2, 2)): 3,  # !unused, !3rd advance (fail), !3rd advance (fail)
                ((2, 1, 0), tuple()): 2,  # !DP roll (pass), DP where (unused)
                ((2, 1, 0), (1,)): 2,  # !DP roll (pass), !0.33<roll<0.67 out at 3rd
                ((2, 1, 0), (2,)): 2,  # !DP roll (pass), !roll>0.67 out at 2nd
                ((2, 1, 0), (2, 1)): 5,  # !DP roll (fail), !martyr roll (pass), advancex3 (unused);NOT DP!
                ((2, 1, 0), (2, 1, 0)): 2,  # !DP roll (fail), !martyr roll (fail)
                ((2, 1, 2, 0), (2, 0)): 2,  # ?DP roll (fail), ?martyr roll(fail)
            }

            event_type = "Out"
            if "reaches on fielder's choice" in self.desc:
                # !DP roll (fail), !martyr roll (fail)
                extras[((2, 0), (0,))] = 2  # what
                event_type = "FC"

            if "into a double play!" in self.desc:
                # !DP roll (pass), !roll<0.33 out at home
                extras[((2, 1, 0), (2, 1))] = 2
                event_type = "DP"

            extra_roll_desc = extras[
                (
                    tuple(self.update["basesOccupied"]),
                    tuple(self.next_update["basesOccupied"]),
                )
            ]
            extra_rolls = [self.roll("extra") for _ in range(extra_roll_desc)]

            # DP rolls
            if 0 in self.update["basesOccupied"]:
                self.log_roll(Csv.GROUNDOUT_FORMULAS, "DP", extra_rolls[0], event_type == "DP", fielder=fielder)

            # Martyr/Sacrifice rolls
            if (
                ((self.update["basesOccupied"] in [[0]]) and (self.next_update["basesOccupied"] in [[0], [1]]))
                or (
                    (self.update["basesOccupied"] in [[1, 0]])
                    and (self.next_update["basesOccupied"] in [[1, 0], [2, 1]])
                )
                or (
                    (self.update["basesOccupied"] in [[2, 0]])
                    and (self.next_update["basesOccupied"] in [[0], [1], [2, 1]])
                )
                or (
                    (self.update["basesOccupied"] in [[2, 1, 0]])
                    and (self.next_update["basesOccupied"] in [[2, 1], [2, 1, 0]])
                    and (event_type != "DP")
                )
            ):

                passed = (
                    ((self.update["basesOccupied"] in [[0]]) and (self.next_update["basesOccupied"] in [[1]]))
                    or ((self.update["basesOccupied"] in [[1, 0]]) and (self.next_update["basesOccupied"] in [[2, 1]]))
                    or ((self.update["basesOccupied"] in [[2, 0]]) and (len(extra_rolls) == 4))
                    or (
                        (self.update["basesOccupied"] in [[2, 1, 0]])
                        and (self.next_update["basesOccupied"] in [[2, 1]])
                    )
                )

                self.log_roll(Csv.GROUNDOUT_FORMULAS, "Sac", extra_rolls[1], passed, fielder=fielder)

            # Advance from 1st base
            if (
                (self.update["basesOccupied"] in [[2, 0]])
                and (self.next_update["basesOccupied"] in [[0], [1]])
                and (len(extra_rolls) == 4)
            ):
                runner = self.data.get_player(self.update["baseRunners"][1])
                passed = self.next_update["basesOccupied"] == [1]
                self.log_roll(
                    Csv.GROUNDOUT_FORMULAS, "advance", extra_rolls[3], passed, fielder=fielder, relevant_runner=runner
                )

            # Advance from 2nd base
            if self.update["basesOccupied"] in [[2, 1]]:
                runner = self.data.get_player(self.update["baseRunners"][1])
                passed = self.next_update["basesOccupied"] in [[2], [2, 2]]
                self.log_roll(
                    Csv.GROUNDOUT_FORMULAS, "advance", extra_rolls[2], passed, fielder=fielder, relevant_runner=runner
                )

            # Advance from 3rd base
            # [2,0] situation
            if (
                (self.update["basesOccupied"] in [[2, 0]])
                and (self.next_update["basesOccupied"] in [[0], [1], [2, 1]])
                and (len(extra_rolls) == 4)
            ):
                runner = self.data.get_player(self.update["baseRunners"][0])
                passed = self.next_update["basesOccupied"] in [[0], [1]]
                self.log_roll(
                    Csv.GROUNDOUT_FORMULAS, "advance", extra_rolls[2], passed, fielder=fielder, relevant_runner=runner
                )
            # [2,1] situation
            if self.update["basesOccupied"] in [[2, 1]]:
                runner = self.data.get_player(self.update["baseRunners"][0])
                passed = self.next_update["basesOccupied"] in [[1], [2]]
                self.log_roll(
                    Csv.GROUNDOUT_FORMULAS, "advance", extra_rolls[1], passed, fielder=fielder, relevant_runner=runner
                )
            # [2,2] situation
            if self.update["basesOccupied"] in [[2, 2]]:
                if self.next_update["basesOccupied"] in [
                    [],
                    [2, 2],
                ]:  # Can't tell with [2] final state! Need to check actual runners
                    passed = self.next_update["basesOccupied"] in [[]]
                    runner = self.data.get_player(self.update["baseRunners"][0])
                    self.log_roll(
                        Csv.GROUNDOUT_FORMULAS,
                        "advance",
                        extra_rolls[1],
                        passed,
                        fielder=fielder,
                        relevant_runner=runner,
                    )
                    runner = self.data.get_player(self.update["baseRunners"][1])
                    self.log_roll(
                        Csv.GROUNDOUT_FORMULAS,
                        "advance",
                        extra_rolls[2],
                        passed,
                        fielder=fielder,
                        relevant_runner=runner,
                    )

            # Here's a csv for looking at *any* groundout
            # No Implied pass/fail, and contains ALL extra rolls
            # Use selections in notebooks to look at different cases!
            self.log_roll(Csv.GROUNDOUT, "groundout", extra_rolls, False, fielder=fielder)

            # FLOWCHART:
            # -Always roll for DP. Always. Ignore the roll if no runner on first.
            # -If runner on first (DP is possible):
            #     -Roll Where.
            #     -If DP pass:
            #         -If this ends the inning, DONE
            #         -If only forced runner is on first: Doesn't matter
            #         -Elif two forced runners:
            #             -Roll < 1/2 -> Out at third
            #             -Roll > 1/2 -> Out at second
            #         -Elif three forced runners:
            #             -Roll < 1/3 -> Out at home
            #             -Roll > 1/3, < 2/3 -> Out at third
            #             -Roll > 2/3 -> Out at second
            #         -Advance all other runners
            #     -Elif DP fail:
            #         -Roll Sacrifice
            #         -If Sacrifice fail:
            #             -Most advanced runner is out.
            #             -Advance everyone else
            #         -Elif Sacrifice pass:
            #             -Roll Advancement for every baserunner
            #             -For each runner:
            #                  -If not forced:
            #                      -Check advancement roll. Rolls apply in basesOccupied order
            #                       aka most advanced first ([2,1,2,0] untested!!!)
            #                  -Elif forced:
            #                      -If initial baserunners were [2,0] AND 3rd base PASSED advancement (:ballclark:):
            #                          -Check advancement roll for 1st base.
            #                      -Elif any other baserunner configuration:
            #                          -Advance
            # -Elif no runner on first:
            #      -For each runner:
            #         -If not forced:
            #             -Check advancement roll. Rolls apply in basesOccupied order
            #              aka most advanced first ([2,1,2,0] untested!!!)
            #         -Elif forced:
            #             -If initial baserunners were [2,0] AND 3rd base PASSED advancement (:ballclark:):
            #                 -Check advancement roll for 1st base.
            #             -Elif any other baserunner configuration:
            #                 -Advance
            #
            # todo: make this not use a lookup table
            # Requires a LOT more knowledge about each situation
            # adv_eligible_runners = dict(bases_before)
            # if 0 in bases_before:
            #     # do force play
            #     self.roll("fc")
            #     if "hit a ground out to" not in self.desc:
            #         # it's either fc or dp, roll for which
            #         self.roll("dp")

            #     for base in range(5):
            #         if base in bases_before:
            #             self.print(f"base {base} force advance")
            #             del adv_eligible_runners[base]
            #         else:
            #             self.print(f"base {base} is clear, stopping")
            #             break

            # self.print("after force:", adv_eligible_runners)
            # # do "regular" adv for rest
            # for runner_id, base, roll_outcome in calculate_advances(adv_eligible_runners, bases_after, 0):
            #     self.roll(f"adv ({base}, {roll_outcome})")

            #     if base == 1:
            #         self.print("extra adv 1?")
            #     if base == 2:
            #         self.roll("extra adv 2?")

        self.print(
            "OUT {} {} -> {}".format(
                self.ty.value,
                self.update["basesOccupied"],
                self.next_update["basesOccupied"],
            )
        )

    def handle_hit_advances(self, bases_hit, defender_roll):
        bases_before = make_base_map(self.update)
        bases_after = make_base_map(self.next_update)
        for runner_id, base, roll_outcome in calculate_advances(bases_before, bases_after, bases_hit):
            roll = self.roll(f"adv ({base}, {roll_outcome}")
            runner = self.data.get_player(runner_id)
            fielder = self.get_fielder_for_roll(defender_roll)
            if base == 1:
                self.log_roll(
                    Csv.HITADVANCE,
                    "second",
                    roll,
                    roll_outcome,
                    relevant_runner=runner,
                    fielder_roll=defender_roll,
                    fielder=fielder,
                )
            elif base == 2:
                self.log_roll(
                    Csv.HITADVANCE,
                    "third",
                    roll,
                    roll_outcome,
                    relevant_runner=runner,
                    fielder_roll=defender_roll,
                    fielder=fielder,
                )

    def handle_hr(self):
        if " is Magmatic!" not in self.desc:
            self.throw_pitch()
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

        if self.stadium.has_mod(Mod.BIG_BUCKET):
            self.roll("big buckets")

    def handle_base_hit(self):
        self.throw_pitch()
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

        self.handle_hit_advances(hit_bases, defender_roll)

    def get_stat_meta(self):
        is_maximum_blaseball = (
            self.strikes == self.max_strikes - 1
            and self.balls == self.max_balls - 1
            and self.outs == self.max_outs - 1
            and self.update["basesOccupied"] == [2, 1, 0]
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

    def handle_batter_up(self):
        if self.batter and self.batter.has_mod(Mod.HAUNTED):
            haunt_roll = self.roll("haunted")
            self.log_roll(Csv.HAUNTED, "NoHaunt", haunt_roll, False)

        # if the haunting is successful the batter won't be the haunted player lol
        if "is Inhabiting" in self.event["description"]:
            haunt_roll = self.roll("haunted")
            self.log_roll(Csv.HAUNTED, "YesHaunt", haunt_roll, True)

            self.roll("haunter selection")

    def handle_weather(self):
        if self.weather == Weather.SUN_2:
            pass

        elif self.weather == Weather.ECLIPSE:

            threshold = self.get_eclipse_threshold()
            eclipse_roll = self.roll("eclipse")

            if self.batter.has_mod(Mod.MARKED):
                self.roll("unstable")

            if self.ty == EventType.INCINERATION:
                self.roll("target")
                self.generate_player()
                return True

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

                    if self.ty == EventType.INCINERATION_BLOCKED:
                        # fire eater proc - target roll maybe?
                        self.roll("target")
                        return True
                    break
        elif self.weather == Weather.GLITTER:
            self.roll("glitter")

        elif self.weather == Weather.BLOODDRAIN:
            self.roll("blooddrain")

            if self.ty == EventType.BLOODDRAIN_SIPHON:
                self.roll("siphon proc")
                self.roll("siphon proc")
                self.roll("siphon proc")
                self.roll("siphon proc")

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
                    self.roll("siphon proc 2?")
                return True

            if self.ty == EventType.BLOODDRAIN:
                self.roll("blooddrain proc")
                self.roll("blooddrain proc")
                self.roll("blooddrain proc")

                # todo: why are these shorter?
                if self.event["created"] not in [
                    "2021-03-09T10:27:56.571Z",
                    "2021-03-11T03:12:13.124Z",
                    "2021-03-12T01:07:27.467Z",
                ]:
                    self.roll("blooddrain proc")

                # todo: ???
                if self.event["created"] in [
                    "2021-03-12T01:10:43.414Z",
                ]:
                    self.roll("blooddrain proc")
                return True

        elif self.weather == Weather.PEANUTS:
            self.roll("peanuts")

            if self.ty == EventType.PEANUT_FLAVOR_TEXT:
                self.roll("peanut message")
                return True

            self.roll("peanuts")
            if self.ty == EventType.ALLERGIC_REACTION:
                self.roll("target")
                return True

            if self.batter.has_mod(Mod.HONEY_ROASTED):
                self.roll("honey roasted")
            elif self.pitcher.has_mod(Mod.HONEY_ROASTED):
                self.roll("honey roasted")

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
                # also must be specifically permAttr - moses mason (shelled in s15 through receiver, so seasonal mod)
                # is exempt
                if Mod.SHELLED.value in player.data["permAttr"]:
                    has_shelled_player = True

            if self.ty == EventType.BIRDS_CIRCLE:
                # the birds circle...
                self.log_roll(Csv.BIRD_MESSAGE, "Circle", bird_roll, True)
                return True
            elif not has_shelled_player:
                self.log_roll(Csv.BIRD_MESSAGE, "NoCircle", bird_roll, False)

            # threshold is at 0.0125 at 0.5 fort
            bird_threshold = 0.0125 - 0.02 * (self.stadium.fortification - 0.5)

            if has_shelled_player and bird_roll < bird_threshold:
                self.roll("extra bird roll")
                if self.ty == EventType.BIRDS_UNSHELL:
                    # ???
                    self.roll("extra bird roll")
                    return True
                pass

        elif self.weather == Weather.FEEDBACK:
            self.roll("feedback")  # apply to batter/pitcher? seems to be about 60/40 or 55/45 split
            self.roll("feedback")  # feedback event y/n

            if self.ty == EventType.FEEDBACK_SWAP:
                # todo: how many rolls?
                self.roll("target")
                self.roll("player 1 fate")
                self.roll("player 2 fate")
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
                self.roll("echo chamber")
                if self.ty == EventType.ECHO_CHAMBER:
                    self.roll("echo chamber")
                    return True

            self.roll("reverb")
            if self.ty == EventType.REVERB_ROSTER_SHUFFLE:
                # todo: how many rolls? this needs a refactor and doesn't support lineup shuffles rn

                if "were shuffled in the Reverb!" in self.desc:
                    for _ in range(16):
                        self.roll("reverb shuffle?")
                else:
                    for _ in range(2):
                        self.roll("reverb shuffle?")

                    for _ in range(len(self.pitching_team.rotation)):
                        self.roll("reverb shuffle?")

                return True

            if self.ty == EventType.REVERB_BESTOWS_REVERBERATING:
                # todo: how many rolls?
                self.roll("more reverb?")
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

        elif self.weather == Weather.BLACK_HOLE:
            pass

        elif self.weather == Weather.COFFEE:
            self.roll("coffee")
            if self.ty == EventType.COFFEE_BEAN:
                self.roll("coffee proc")
                self.roll("coffee proc")

                return True

            if self.batter.has_mod(Mod.COFFEE_PERIL):
                self.roll("observed?")

        elif self.weather == Weather.COFFEE_2:
            self.roll("coffee 2")

            if self.ty == EventType.GAIN_FREE_REFILL:
                self.roll("coffee 2 proc")
                self.roll("coffee 2 proc")
                self.roll("coffee 2 proc")
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
            # polarity +/-
            self.roll("polarity")
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
                    player.mods,
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
                self.roll("flooding")

            if self.ty == EventType.FLOODING_SWEPT:
                # handle flood
                for runner_id in self.update["baseRunners"]:
                    runner = self.data.get_player(runner_id)
                    if not runner.has_any(Mod.EGO1, Mod.SWIM_BLADDER):
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
                threshold = 0.0005
                if self.season == 14:
                    threshold = 0.0004
                if self.season == 12:
                    threshold = 0.00061

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

    def was_attractor_placed_in_secret_base_async(self):
        update_one_after_next = self.data.get_update(self.game_id, self.play + 2)

        # [rob voice] ugh. this line sucks
        # basically "do we observe an attractor enter a secret base on the tick *after* this one". because it does it
        # weird and async or something
        if (
            self.next_update
            and not self.next_update["secretBaserunner"]
            and update_one_after_next
            and update_one_after_next["secretBaserunner"]
            and "enters the Secret Base" not in update_one_after_next["lastUpdate"]
        ):
            attractor = self.data.get_player(update_one_after_next["secretBaserunner"])
            return attractor

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
            level = team.data.get("level") or 0
            if level >= 5:
                attack_roll = self.roll(f"consumers ({team.data['nickname']})")

                if self.ty == EventType.CONSUMERS_ATTACK:
                    attacked_player_id = self.event["playerTags"][0]
                    is_on_team = attacked_player_id in (team.lineup + team.rotation)
                    if is_on_team:
                        self.log_roll(Csv.CONSUMERS, "Attack", attack_roll, True, attacked_team=team)

                        attacked_player = self.data.get_player(attacked_player_id)

                        target_roll = self.roll("target")
                        self.log_roll(Csv.CONSUMERS, attacked_player.name, target_roll, True)

                        roster = [self.data.get_player(p) for p in team.lineup + team.rotation]
                        densities = [p.data["eDensity"] for p in roster]
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

                        for _ in range(25):
                            self.roll("stat change")

                            if attacked_player.data["soul"] == 1:
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
        # lol. turns out it just rolls party all the time and throws out the roll if the team isn't partying
        party_roll = self.roll("party time")
        if self.ty == EventType.PARTY:
            self.log_roll(Csv.PARTY, "Party", party_roll, True)
            team_roll = self.roll("target team")  # <0.5 for home, >0.5 for away
            self.roll("target player")
            for _ in range(25):
                self.roll("stat")

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
            self.roll("peanut mister")

            if self.ty == EventType.PEANUT_MISTER:
                self.roll("target")
                return True

        if self.stadium.has_mod(Mod.SMITHY):
            self.roll("smithy")

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

        # if an attractor appeared between this tick and next, and this isn't a "real" enter...
        did_attractor_enter_this_tick = (
            not self.update["secretBaserunner"]
            and self.next_update["secretBaserunner"]
            and self.ty != EventType.ENTER_SECRET_BASE
        )
        if did_attractor_enter_this_tick:
            secret_runner_id = self.next_update["secretBaserunner"]

        secret_base_enter_eligible = 1 in bases and not secret_runner_id
        secret_base_exit_eligible = 1 not in bases and secret_runner_id
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

        # weird order issues here. when an attractor is placed in the secret base, it only applies the *next* tick
        # likely because of some kinda async function that fills in the field between ticks
        # so we need to do this play count/next check nonsense to get the right roll order
        attractor_eligible = not secret_runner_id
        if attractor_eligible:
            self.roll("secret base attract")

            attractor = self.was_attractor_placed_in_secret_base_async()
            if attractor:
                # todo: some of these rolls seem to be done async
                self.print(f"!!! attractor placed in secret base:{attractor.name}")
                self.roll("choose attractor")
                return

        if secret_base_exit_eligible:
            self.roll("secret base exit")
            if self.ty == EventType.EXIT_SECRET_BASE:
                return True

        if secret_base_enter_eligible:
            self.roll("secret base enter")
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
                runner.data["permAttr"].append("REDACTED")
                runner.update_mods()

                # and just as a cherry on top let's hack this so we don't roll for steal as well
                self.update["basesOccupied"].remove(1)
                self.update["baseRunners"].remove(runner_id)

    def handle_grind_rail(self):
        if 0 in self.update["basesOccupied"] and 2 not in self.update["basesOccupied"]:
            # i have no idea why this rolls twice but it definitely *does*
            self.roll("grind rail")
            self.roll("grind rail")

            if self.ty == EventType.GRIND_RAIL:
                runner = self.data.get_player(self.update["baseRunners"][-1])

                self.roll("trick 1 name")

                score_1_roll = self.roll("trick 1 score")
                lo1 = runner.pressurization * 200
                hi1 = runner.cinnamon * 1500 + 500
                score_1 = int((hi1 - lo1) * score_1_roll + lo1)
                self.print(f"(score: {score_1})")

                self.roll("trick 1 success")

                if "lose their balance and bail!" not in self.desc:
                    self.roll("trick 2 name")
                    score_2_roll = self.roll("trick 2 score")
                    lo2 = runner.pressurization * 500
                    hi2 = runner.cinnamon * 3000 + 1000
                    score_2 = int((hi2 - lo2) * score_2_roll + lo2)
                    self.print(f"(score: {score_2})")

                    self.roll("trick 2 success")
                return True

    def handle_steal(self):
        steal_fielder_roll = self.roll("steal fielder")
        bases = self.update["basesOccupied"]
        self.print(f"- base states: {bases}")

        base_stolen = None
        if "second base" in self.desc:
            base_stolen = 1
        elif "third base" in self.desc:
            base_stolen = 2
        elif "fourth base" in self.desc:
            base_stolen = 3

        for i, base in enumerate(bases):
            if base + 1 not in bases or (
                # This is weird, but adding an extra roll here seems like the only way to get S15D75 to line up.
                # https://reblase.sibr.dev/game/9d224696-6775-42c0-8259-b4de84f850a8#b65483bc-a07f-88e3-9e30-6ff9365f865b
                bases == [2, 0, 1]
                and base == 0
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
                    fielder=self.get_fielder_for_roll(steal_fielder_roll),
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
                        fielder=self.get_fielder_for_roll(steal_fielder_roll),
                    )
                    return True

            if bases == [2, 2] or bases == [2, 1, 2] or bases == [1, 0, 1]:
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
            self.roll("acidic")

        self.is_strike = roll < threshold
        self.strike_roll = roll
        self.strike_threshold = threshold

        if known_result == "strike" and roll > threshold:
            self.print(f"!!! warn: too high strike roll (threshold {threshold})")
        elif known_result == "ball" and roll < threshold:
            self.print(f"!!! warn: too low strike roll (threshold {threshold})")

        # todo: double strike

        return roll

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
        runner_1st = [r for base, r in zip(self.update["basesOccupied"], self.update["baseRunners"]) if base == 0]
        runner_2nd = [r for base, r in zip(self.update["basesOccupied"], self.update["baseRunners"]) if base == 1]
        runners_3rd = [r for base, r in zip(self.update["basesOccupied"], self.update["baseRunners"]) if base == 2]
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
        self.csvs[csv].write(
            event_type,
            roll,
            passed,
            relevant_batter or self.batter,
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
            fielder,
            self.get_fielder_multiplier(fielder) if fielder else 1,
            relevant_runner,
            relevant_runner_multiplier,
            runner_on_first,
            runner_on_first_multiplier,
            runner_on_second,
            runner_on_second_multiplier,
            runner_on_third,
            runner_on_third_multiplier,
            runner_on_third_hh,
            runner_on_third_hh_multiplier,
            self.next_update["basesOccupied"] if self.next_update else None,
            attacked_team,
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
            and Mod.OVERPERFORMING.value not in self.batter.data["gameAttr"]
            and not self.batter.has_mod(Mod.INHABITING)
            and self.ty != EventType.BATTER_UP
        ):
            self.batter.data["gameAttr"].append(Mod.OVERPERFORMING.value)
            self.batter.update_mods()

    def apply_event_changes(self, event):
        # maybe move this function to data.py?
        meta = event.get("metadata", {})
        mod_positions = ["permAttr", "seasAttr", "weekAttr", "gameAttr"]
        desc = event["description"]

        # player or team mod added
        if event["type"] in [
            EventType.ADDED_MOD,
            EventType.ADDED_MOD_FROM_OTHER_MOD,
        ]:
            position = mod_positions[meta["type"]]

            if event["playerTags"]:
                player = self.data.get_player(event["playerTags"][0])
                if meta["mod"] not in player.data[position]:
                    player.data[position].append(meta["mod"])
                    player.update_mods()
            else:
                team = self.data.get_team(event["teamTags"][0])
                if meta["mod"] not in team.data[position]:
                    team.data[position].append(meta["mod"])
                    team.update_mods()

        # player or team mod removed
        if event["type"] in [
            EventType.REMOVED_MOD,
            EventType.REMOVED_MODIFICATION,
        ]:
            position = mod_positions[meta["type"]]

            if event["playerTags"]:
                player = self.data.get_player(event["playerTags"][0])

                if meta["mod"] not in player.data[position]:
                    self.print(f"!!! warn: trying to remove mod {meta['mod']} but can't find it")
                else:
                    player.data[position].remove(meta["mod"])
                    player.update_mods()
            else:
                team = self.data.get_team(event["teamTags"][0])

                if meta["mod"] not in team.data[position]:
                    self.print(f"!!! warn: trying to remove mod {meta['mod']} but can't find it")
                else:
                    team.data[position].remove(meta["mod"])
                    team.update_mods()

        # mod replaced
        if event["type"] in [EventType.CHANGED_MODIFIER]:
            position = mod_positions[meta["type"]]

            if event["playerTags"]:
                player = self.data.get_player(event["playerTags"][0])
                player.data[position].remove(meta["from"])
                player.data[position].append(meta["to"])
                player.update_mods()
            else:
                team = self.data.get_team(event["teamTags"][0])
                team.data[position].remove(meta["from"])
                team.data[position].append(meta["to"])
                team.update_mods()

        # timed mods wore off
        if event["type"] in [EventType.MOD_EXPIRES]:
            position = mod_positions[meta["type"]]

            if event["playerTags"]:
                for mod in meta["mods"]:
                    player = self.data.get_player(event["playerTags"][0])
                    if mod not in player.data[position]:
                        self.print(f"!!! warn: trying to remove mod {mod} but can't find it")
                    else:
                        player.data[position].remove(mod)
                        player.update_mods()

            else:
                for mod in meta["mods"]:
                    team = self.data.get_team(event["teamTags"][0])
                    team.data[position].remove(mod)
                    team.update_mods()

        # echo mods added/removed
        if event["type"] in [
            EventType.REMOVED_MULTIPLE_MODIFICATIONS_ECHO,
            EventType.ADDED_MULTIPLE_MODIFICATIONS_ECHO,
        ]:
            player = self.data.get_player(event["playerTags"][0])
            for mod in meta.get("adds", []):
                player.data[mod_positions[mod["type"]]].append(mod["mod"])
            for mod in meta.get("removes", []):
                player.data[mod_positions[mod["type"]]].remove(mod["mod"])
            player.update_mods()

        # cases where the tagged player needs to be refetched (party, consumer, incin replacement)
        if event["type"] in [
            EventType.PLAYER_STAT_INCREASE,
            EventType.PLAYER_STAT_DECREASE,
            EventType.PLAYER_HATCHED,
        ]:
            for player_id in event["playerTags"]:
                if self.data.has_player(player_id):
                    stats_before = dict(self.data.get_player(player_id).data)
                else:
                    stats_before = {}

                self.data.fetch_player_after(player_id, event["created"])
                # stats_after = dict(self.data.get_player(player_id).data)

                for k, v in stats_before.items():
                    if type(v) != float:
                        continue
                    # delta = stats_after[k] - v
                    # self.print(f"stat delta: {k} {delta}")

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
            player.data[mod_positions[meta["type"]]].remove(meta["from"])
            player.data[mod_positions[meta["type"]]].append(meta["to"])

            # todo: do this in other cases too?
            if meta["from"] == "RECEIVER":
                for mod, source in player.data["state"]["seasModSources"].items():
                    if source == ["RECEIVER"]:
                        if mod in player.data["seasAttr"]:
                            player.data["seasAttr"].remove(mod)
            player.update_mods()

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
