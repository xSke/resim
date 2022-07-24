import os
import itertools
from typing import List

import pandas as pd
from tqdm import tqdm

from data import EventType, GameData, Weather, get_feed_between, null_stadium
from output import RollLog, make_roll_log
from rng import Rng


def no_op(*_, **__):
    pass


class Resim:
    def __init__(self, rng, out_file):
        self.rng = rng
        self.out_file = out_file
        if out_file is None:
            # I am being too clever here, in hopes that this is faster
            self.print = no_op
        self.data = GameData()
        self.fetched_days = set()

        self.score_at_inning_start = {}

        self.is_strike = None
        self.strike_roll = None
        self.strike_threshold = None
        self.strike_rolls: List[RollLog] = []
        self.foul_rolls: List[RollLog] = []
        self.triple_rolls: List[RollLog] = []
        self.swing_on_ball_rolls: List[RollLog] = []
        self.swing_on_strike_rolls: List[RollLog] = []
        self.contact_rolls: List[RollLog] = []
        self.hr_rolls: List[RollLog] = []
        self.steal_attempt_rolls: List[RollLog] = []
        self.steal_success_rolls: List[RollLog] = []
        self.out_rolls: List[RollLog] = []
        self.fly_rolls: List[RollLog] = []
        self.party_rolls: List[RollLog] = []
        self.fc_dp_rolls: List[RollLog] = []

        self.what1 = None
        self.what2 = None

    def print(self, *args, **kwargs):
        print(*args, **kwargs, file=self.out_file)

    def handle(self, event):
        self.setup_data(event)

        self.print()
        self.print(
            "===== {} {}/{} {}".format(
                event["created"],
                self.update["id"],
                self.update["playCount"],
                self.weather.name,
            )
        )
        self.print("===== {} {}".format(self.ty.value, self.desc))
        self.print("===== rng pos: {}".format(self.rng.get_state_str()))

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
            self.print("- pitcher mods: {} + {} ({})".format(self.pitcher.mods, self.pitching_team.mods, self.pitcher.name))
        self.print("- stadium mods: {} ({})".format(self.stadium.mods, self.stadium.data["nickname"]))

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

        self.what2 = self.roll("???")

        if self.handle_steal():
            return

        if self.handle_electric():
            return

        if self.handle_bird_ambush():
            return

        # todo: don't know where this actually is - seems to be before mild at least
        if self.pitcher.has_mod("DEBT_THREE") and not self.batter.has_mod("COFFEE_PERIL"):
            self.roll("debt")
            if self.ty == EventType.HIT_BY_PITCH:
                # debt success
                return True

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
            self.print("!!! unknown type: {}".format(self.ty.value))
        pass

        self.handle_batter_reverb()

        if self.was_attractor_placed_in_secret_base_async():
            self.roll("attractor?")  # this roll might be up by the trigger, idk yet
            self.roll("attractor pitching stars")
            self.roll("attractor batting stars")
            self.roll("attractor baserunning stars")
            self.roll("attractor defense stars")

    def handle_misc(self):
        if self.ty in [
            EventType.HOME_FIELD_ADVANTAGE,
            EventType.BECOME_TRIPLE_THREAT,
            EventType.SOLAR_PANELS_AWAIT,
            EventType.HOMEBODY,
            EventType.SUPERYUMMY,
            EventType.PERK,
            EventType.SHAME_DONOR,
            EventType.PSYCHO_ACOUSTICS,
            EventType.AMBITIOUS,
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
            # skipping sun 2 / black hole proc
            return True
        if self.ty in [
            EventType.PLAYER_STAT_INCREASE,
            EventType.PLAYER_STAT_DECREASE,
        ]:
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
        ]:
            # skip liquid/plasma plot nonsense
            return True
        if self.ty == EventType.REVERB_ROTATION_SHUFFLE:
            # skip reverb
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
                self.print("home pitcher mods: {} ({})".format(self.home_pitcher.data["permAttr"], self.home_pitcher.name))
                self.print("away pitcher mods: {} ({})".format(self.away_pitcher.data["permAttr"], self.away_pitcher.name))
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
            if self.event["created"] == "2021-04-08T20:06:02.627Z":
                self.roll("salmon")
                return True

            last_inning = self.update["inning"]
            last_inning_away_score, last_inning_home_score = self.score_at_inning_start[(self.game_id, last_inning)]
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
                    self.home_team.data["lineup"]
                    + self.home_team.data["rotation"]
                    + self.away_team.data["lineup"]
                    + self.away_team.data["rotation"]
                )
                for player_id in rosters:
                    player = self.data.get_player(player_id)
                    if player.has_mod("COFFEE_PERIL"):
                        self.roll("redaction ({})".format(player.name))

            return True
        if self.ty in [EventType.LETS_GO]:
            # game start - probably like, postseason weather gen
            if self.event["day"] >= 99:
                self.roll("game start")

            if self.event["day"] != 98:
                # *why*
                self.roll("game start")

            # todo: figure out the real logic here, i'm sure there's some
            extra_start_rolls = {
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
            }

            for _ in range(extra_start_rolls.get(self.game_id, 0)):
                self.roll("align start {} day {}".format(self.game_id, self.day))

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
            ] and self.stadium.has_mod("PSYCHOACOUSTICS"):
                self.print("away team mods:", self.away_team.data["permAttr"])
                self.roll("echo team mod")
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
        batter_charm_eligible = self.batting_team.has_mod("LOVE") and pitch_charm_eligible
        pitcher_charm_eligible = self.pitching_team.has_mod("LOVE") and pitch_charm_eligible

        # before season 16, love blood only proc'd when the player also had love blood
        if self.event["season"] < 15:
            if self.batter.data["blood"] != 9:
                if batter_charm_eligible:
                    self.print("!!! warn: batter does not have love blood, skipping")
                batter_charm_eligible = False

            if self.pitcher.data["blood"] != 9:
                if pitcher_charm_eligible:
                    self.print("!!! warn: pitcher does not have love blood, skipping")
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
        if self.batting_team.has_mod("ELECTRIC") and self.update["atBatStrikes"] > 0:
            self.roll("electric")
            if self.batter.data["blood"] != 8:
                self.print("!!! warn: batter does not have electric blood")

            if self.ty == EventType.STRIKE_ZAPPED:
                # successful zap!
                return True

    def handle_batter_reverb(self):
        if self.batter and self.batter.has_mod("REVERBERATING"):
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
                self.print("!!! warn: no reverb on hit?")
                is_at_bat_end = False

            if is_at_bat_end:
                self.roll("at bat reverb")

    def handle_mild(self):
        self.roll("mild")
        if self.ty == EventType.MILD_PITCH:
            # skipping mild proc
            return True

    def handle_ball(self):
        value = self.throw_pitch("ball")
        self.log_roll(self.strike_rolls, "Ball", value, False)

        if not self.is_flinching():
            swing_roll = self.roll("swing")
            if swing_roll < 0.05:
                self.print("!!! very low swing roll on ball")
            self.log_roll(self.swing_on_ball_rolls, "Ball", swing_roll, False)
        else:
            self.print("!!! warn: flinching ball")

        if self.ty == EventType.WALK and self.batting_team.has_mod("BASE_INSTINCTS"):
            self.roll("base instincts")

            if "Base Instincts take them directly to" in self.desc:
                self.roll("which base")
                self.roll("which base")

    def handle_strike(self):
        if ", swinging" in self.desc or "strikes out swinging." in self.desc:
            self.throw_pitch()
            swing_roll = self.roll("swing")
            self.log_roll(
                self.swing_on_strike_rolls if self.is_strike else self.swing_on_ball_rolls,
                "StrikeSwinging",
                swing_roll,
                True,
            )

            contact_roll = self.roll("contact")
            self.log_roll(self.contact_rolls, "StrikeSwinging", contact_roll, False)
        elif ", looking" in self.desc or "strikes out looking." in self.desc:
            value = self.throw_pitch("strike")
            self.log_roll(self.strike_rolls, "StrikeLooking", value, True)

            if not self.is_flinching():
                swing_roll = self.roll("swing")
                self.log_roll(self.swing_on_strike_rolls, "StrikeLooking", swing_roll, False)
        elif ", flinching" in self.desc:
            value = self.throw_pitch("strike")
            self.log_roll(self.strike_rolls, "StrikeFlinching", value, True)
        pass

    def try_roll_salmon(self):
        # don't reroll if we *just* reset
        if "The Salmon swim upstream!" in self.update["lastUpdate"]:
            return

        # special case for a weird starting point with missing data
        if self.event["created"] in [
            "2021-04-08T20:05:02.637Z",
            "2021-04-08T20:08:33.340Z",
        ]:
            self.roll("salmon")
            return

        last_inning = self.next_update["inning"] - 1
        inning_key = (self.game_id, last_inning)
        if self.weather == Weather.SALMON and last_inning >= 0 and not self.update["topOfInning"]:
            last_inning_away_score, last_inning_home_score = self.score_at_inning_start[inning_key]
            current_away_score, current_home_score = (
                self.next_update["awayScore"],
                self.next_update["homeScore"],
            )

            # only roll salmon if the last inning had any scores, but also we have to dig into game history to find this
            # how does the sim do it? no idea. i'm cheating.
            if current_away_score != last_inning_away_score or current_home_score != last_inning_home_score:
                self.roll("salmon")

    def is_flinching(self):
        return self.batter.has_mod("FLINCH") and self.strikes == 0

    def get_fielder_for_roll(self, fielder_roll: float):
        candidates = self.pitching_team.data["lineup"]
        candidates = [self.data.get_player(player) for player in candidates]
        candidates = [c for c in candidates if not c.has_mod("ELSEWHERE")]
        weights = [1] * len(candidates)
        sum_weights = sum(weights)
        weights = [weight / sum_weights for weight in weights]
        roll_remaining = fielder_roll
        for i, weight in enumerate(weights):
            if roll_remaining < weight:
                return candidates[i]
            roll_remaining -= weight

        # Should never get here, I think
        return candidates[-1]

    def handle_out(self):
        self.throw_pitch()
        swing_roll = self.roll("swing")
        self.log_roll(
            self.swing_on_strike_rolls if self.is_strike else self.swing_on_ball_rolls,
            "Out",
            swing_roll,
            True,
        )
        contact_roll = self.roll("contact")
        self.log_roll(self.contact_rolls, "Out", contact_roll, True)
        self.roll_foul(False)

        fielder = None
        if self.ty == EventType.FLY_OUT:  # flyout
            out_fielder_roll = self.roll("out fielder")
            out_roll = self.roll("out")
            fly_fielder_roll, fly_fielder = self.roll_fielder()
            fly_roll = self.roll("fly")
            self.log_roll(
                self.fly_rolls,
                "Flyout",
                fly_roll,
                True,
                fielder_roll=out_fielder_roll,
                fielder=self.get_fielder_for_roll(out_fielder_roll),
            )
            self.log_roll(
                self.out_rolls,
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
            ground_fielder_roll, ground_fielder = self.roll_fielder()
            self.log_roll(
                self.fly_rolls,
                "GroundOut",
                fly_roll,
                False,
                fielder_roll=out_fielder_roll,
                fielder=self.get_fielder_for_roll(out_fielder_roll),
            )
            self.log_roll(
                self.out_rolls,
                "GroundOut",
                out_roll,
                False,
                fielder_roll=out_fielder_roll,
                fielder=self.get_fielder_for_roll(out_fielder_roll),
            )
            fielder = ground_fielder

        if self.outs < self.max_outs - 1:
            self.handle_out_advances()

        is_fc_dp = "into a double play!" in self.desc or "reaches on fielder's choice" in self.desc
        if not is_fc_dp and self.batter.has_mod("DEBT_THREE") and fielder and not fielder.has_mod("COFFEE_PERIL"):
            self.roll("debt")

    def roll_fielder(self, check_name=True):
        roll_value = self.roll("fielder")

        eligible_fielders = []
        fielder_idx = None
        for fielder_id in self.pitching_team.data["lineup"]:
            fielder = self.data.get_player(fielder_id)
            if fielder.has_mod("ELSEWHERE"):
                continue

            if check_name and fielder.raw_name in self.desc:
                fielder_idx = len(eligible_fielders)
            eligible_fielders.append(fielder)

        rolled_idx = int(roll_value * len(eligible_fielders))

        if fielder_idx is not None:

            if rolled_idx != fielder_idx:
                expected_min = fielder_idx / len(eligible_fielders)
                expected_max = (fielder_idx + 1) / len(eligible_fielders)
                self.print(
                    "!!! incorrect fielder! expected {}, got {}, needs to be {:.3f}-{:.3f}".format(
                        fielder_idx, rolled_idx, expected_min, expected_max
                    )
                )
                self.print(self.rng.get_state_str())

            matching = []
            r2 = Rng(self.rng.state, self.rng.offset)
            check_range = 50
            r2.step(-check_range)
            for i in range(check_range * 2):
                val = r2.next()
                if int(val * len(eligible_fielders)) == fielder_idx:
                    matching.append(i - check_range + 1)
            self.print("(matching offsets: {})".format(matching))
        elif check_name:
            if "fielder's choice" not in self.desc and "double play" not in self.desc:
                self.print("!!! could not find fielder (name wrong?)")

        return roll_value, eligible_fielders[rolled_idx]

    def handle_out_advances(self):
        # special case for a chron data gap - ground out with no runners (so no rolls), but the game update is missing
        if self.event["created"] == "2021-04-07T08:02:52.078Z":
            return

        bases_before = make_base_map(self.update)
        bases_after = make_base_map(self.next_update)

        if self.ty == EventType.FLY_OUT:
            # flyouts are nice and simple
            for runner_id, base, roll_outcome in calculate_advances(bases_before, bases_after, 0):
                self.roll("adv ({}, {})".format(base, roll_outcome))

                # or are they? [2,0] -> [2,0] = 1 roll?
                # [1, 0] -> [2, 0] = 1 roll?
                # but a [2, 0] -> [0] score is 2, so it's not like it never rolls twice (unless it's special cased...)
                if not roll_outcome or base == 1:
                    break

                # our code doesn't handle each baserunner twice so i'm cheating here
                # rerolling for the "second" player on third's advance if the first successfully advanced,
                # since it's possible for both
                if self.update["basesOccupied"] == [2, 2] and base == 2 and roll_outcome:
                    self.roll("holding hands")

        elif self.ty == EventType.GROUND_OUT:
            # ground out
            extras = {
                (tuple(), tuple()): 0,
                ((0,), (0,)): 2,  # fielder's choice (successful)
                ((0,), (1,)): 3,
                ((1,), (1,)): 2,
                ((2, 0), (2, 1)): 4,
                ((1,), (2,)): 2,
                ((2, 1), (2,)): 3,
                ((0,), tuple()): 2,  # double play (successful)
                ((2,), tuple()): 2,  # sac
                ((1, 0), (2, 1)): 4,
                ((1, 0), (1, 0)): 2,
                ((2, 0), (0,)): 4,
                ((2,), (2,)): 2,
                ((1, 0), tuple()): 2,  # double play + second, 2 or 3 rolls?
                ((2, 1, 0), (2, 1, 0)): 2,
                ((2, 1, 0), (2, 1)): 5,  # guessing
                ((2, 1, 0), (2,)): 2,
                ((2, 1, 0), (1,)): 2,  # guessing
                ((2, 1, 0), tuple()): 2,  # dp
                ((2, 1), (1,)): 3,  # guessing
                ((2, 0), tuple()): 2,  # double play + sac?
                ((1, 0), (1,)): 2,  # double play but they stay?
                ((2, 0), (1,)): 4,
                ((2, 1), (2, 1)): 3,
                ((1, 0), (2,)): 2,  # dp
                ((2, 1), (2, 2)): 3,  # holding hands
                ((2, 2), tuple()): 3,  # two players holding hands, both sac scoring???
            }

            fc_dp_event_type = "Out"
            if "reaches on fielder's choice" in self.desc:
                extras[((2, 0), (0,))] = 2  # what
                fc_dp_event_type = "FC"

            if "into a double play!" in self.desc:
                # not [2, 1, 0], 2 scores, everyone advances, but instead just a dp, which is 3 shorter...?
                extras[((2, 1, 0), (2, 1))] = 2
                fc_dp_event_type = "DP"

            extra_roll_desc = extras[
                (
                    tuple(self.update["basesOccupied"]),
                    tuple(self.next_update["basesOccupied"]),
                )
            ]
            extra_rolls = [self.roll("extra") for _ in range(extra_roll_desc)]

            if extra_rolls:
                self.log_roll(
                    self.fc_dp_rolls,
                    fc_dp_event_type,
                    extra_rolls[1],  # we'll see if this array is ever exactly 1 long
                    fc_dp_event_type != "Out",
                )

            # todo: make this not use a lookup table
            # adv_eligible_runners = dict(bases_before)
            # if 0 in bases_before:
            #     # do force play
            #     self.roll("fc")
            #     if "hit a ground out to" not in self.desc:
            #         # it's either fc or dp, roll for which
            #         self.roll("dp")

            #     for base in range(5):
            #         if base in bases_before:
            #             self.print("base {} force advance".format(base))
            #             del adv_eligible_runners[base]
            #         else:
            #             self.print("base {} is clear, stopping".format(base))
            #             break

            # self.print("after force:", adv_eligible_runners)
            # # do "regular" adv for rest
            # for runner_id, base, roll_outcome in calculate_advances(adv_eligible_runners, bases_after, 0):
            #     self.roll("adv ({}, {})".format(base, roll_outcome))

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

    def handle_hit_advances(self, bases_hit):
        bases_before = make_base_map(self.update)
        bases_after = make_base_map(self.next_update)
        for runner_id, base, roll_outcome in calculate_advances(bases_before, bases_after, bases_hit):
            self.roll("adv ({}, {})".format(base, roll_outcome))

    def handle_hr(self):
        if not self.batter.has_mod("MAGMATIC"):
            self.throw_pitch()
            swing_roll = self.roll("swing")
            self.log_roll(
                self.swing_on_strike_rolls if self.is_strike else self.swing_on_ball_rolls,
                "HR",
                swing_roll,
                True,
            )

            contact_roll = self.roll("contact")
            self.log_roll(self.contact_rolls, "HomeRun", contact_roll, True)

            self.roll_foul(False)
            fielder_roll = self.roll("out fielder")
            out_roll = self.roll("out")

            self.log_roll(
                self.out_rolls,
                "HR",
                out_roll,
                True,
                fielder_roll=fielder_roll,
                fielder=self.get_fielder_for_roll(fielder_roll),
            )

            hr_roll = self.roll("home run")
            self.log_roll(self.hr_rolls, "HomeRun", hr_roll, True)
        else:
            # not sure why we need this
            self.roll("magmatic")

        if self.stadium.has_mod("BIG_BUCKET"):
            self.roll("big buckets")

    def handle_base_hit(self):
        self.throw_pitch()
        swing_roll = self.roll("swing")
        self.log_roll(
            self.swing_on_strike_rolls if self.is_strike else self.swing_on_ball_rolls,
            "BaseHit",
            swing_roll,
            True,
        )

        contact_roll = self.roll("contact")
        self.log_roll(self.contact_rolls, "BaseHit", contact_roll, True)

        self.roll_foul(False)

        fielder_roll = self.roll("out fielder")
        out_roll = self.roll("out")

        self.log_roll(
            self.out_rolls,
            "BaseHit",
            out_roll,
            True,
            fielder_roll=fielder_roll,
            fielder=self.get_fielder_for_roll(fielder_roll),
        )

        hr_roll = self.roll("home run")
        self.log_roll(self.hr_rolls, "BaseHit", hr_roll, False)

        self.roll("hit fielder?")
        self.roll("double?")
        triple_roll = self.roll("triple?")

        hit_bases = 0
        if "hits a Single!" in self.desc:
            hit_bases = 1
        elif "hits a Double!" in self.desc:
            hit_bases = 2
        elif "hits a Triple!" in self.desc:
            hit_bases = 3

        self.log_roll(self.triple_rolls, f"Hit{hit_bases}", triple_roll, hit_bases == 3)

        self.handle_hit_advances(hit_bases)

    def roll_foul(self, known_outcome: bool):
        vibes = self.batter.vibes(self.day)
        fwd = self.stadium.data["forwardness"]
        obt = self.stadium.data["obtuseness"]
        musc = (
            self.batter.data["musclitude"] * self.get_batter_multiplier(relevant_attr="musclitude") * (1 + 0.2 * vibes)
        )
        thwack = (
            self.batter.data["thwackability"]
            * self.get_batter_multiplier(relevant_attr="thwackability")
            * (1 + 0.2 * vibes)
        )
        div = self.batter.data["divinity"] * self.get_batter_multiplier(relevant_attr="divinity") * (1 + 0.2 * vibes)
        foul_threshold = 0.25 + 0.1 * fwd - 0.1 * obt + (1 / 30) * musc + (1 / 30) * thwack + (1 / 30) * div

        foul_roll = self.roll("foul")
        is_0_no_eligible = self.batting_team.has_mod("O_NO") and self.strikes == 2 and self.balls == 0
        if not is_0_no_eligible:
            if known_outcome and foul_roll > foul_threshold:
                self.print("!!! too high foul roll ({} > {})".format(foul_roll, foul_threshold))
            elif not known_outcome and foul_roll < foul_threshold:
                self.print("!!! too low foul roll ({} < {})".format(foul_roll, foul_threshold))
        self.log_roll(self.foul_rolls, "uhhhhh", foul_roll, known_outcome)

    def handle_foul(self):
        self.throw_pitch()

        swing_roll = self.roll("swing")
        self.log_roll(
            self.swing_on_strike_rolls if self.is_strike else self.swing_on_ball_rolls,
            "Foul",
            swing_roll,
            True,
        )

        contact_roll = self.roll("contact")
        self.log_roll(self.contact_rolls, "Foul", contact_roll, True)

        self.roll_foul(True)

    def handle_batter_up(self):
        if self.batter.has_mod("HAUNTED"):
            self.roll("haunted")

        if "is Inhabiting" in self.event["description"]:
            self.roll("haunted")
            self.roll("haunter selection")

    def handle_weather(self):
        if self.weather == Weather.SUN_2:
            pass

        elif self.weather == Weather.ECLIPSE:
            self.roll("eclipse")

            if self.batter.has_mod("MARKED"):
                self.roll("unstable")

            if self.ty == EventType.INCINERATION:
                self.roll("target")
                # self.roll("target")
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
                return True

            fire_eater_eligible = self.pitching_team.data["lineup"] + [
                self.batter.id,
                self.pitcher.id,
            ]
            for player_id in fire_eater_eligible:
                player = self.data.get_player(player_id)

                if player.has_mod("FIRE_EATER") and not player.has_mod("ELSEWHERE"):
                    self.roll("fire eater ({})".format(player.name))

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

                # this one is 1 more for some reason. don't know
                if self.event["created"] in [
                    "2021-03-17T03:20:31.620Z",
                    "2021-04-07T13:02:47.102Z",
                ]:
                    self.roll("siphon proc 2?")
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

            if self.batter.has_mod("HONEY_ROASTED"):
                self.roll("honey roasted")
            if self.pitcher.has_mod("HONEY_ROASTED"):
                self.roll("honey roasted")

            if self.ty == EventType.TASTE_THE_INFINITE:
                self.roll("target")  # might be team or index
                self.roll("target")  # probably player
                return True

        elif self.weather == Weather.BIRDS:
            bird_roll = self.roll("birds")

            has_shelled_player = False
            for player_id in (
                self.pitching_team.data["lineup"]
                + self.pitching_team.data["rotation"]
                + self.batting_team.data["lineup"]
                + self.batting_team.data["rotation"]
            ):
                # if low roll and shelled player present, roll again
                # in s14 this doesn't seem to check (inactive) pitchers
                # (except all shelled pitchers are inactive so idk)
                player = self.data.get_player(player_id)
                # also must be specifically permAttr - moses mason (shelled in s15 through receiver, so seasonal mod)
                # is exempt
                if "SHELLED" in player.data["permAttr"]:
                    has_shelled_player = True

            if self.ty == EventType.BIRDS_CIRCLE:
                # the birds circle...
                return True

            # wild guess at how this maybe kinda works. might just be myst idk
            bird_threshold = 0.015 if self.batting_team.has_mod("BIRD_SEED") else 0.012
            if has_shelled_player and bird_roll < bird_threshold:
                # potentially roll for player to unshell?
                self.roll("extra bird roll")
                pass

        elif self.weather == Weather.FEEDBACK:
            self.roll("feedback")
            self.roll("feedback")  # this is probably echo y/n? but ignored if the mod isn't there?

            if self.ty == EventType.FEEDBACK_SWAP:
                # todo: how many rolls?
                self.roll("feedback")
                self.roll("feedback")
                self.roll("feedback")
                return True

            if self.weather.can_echo() and (self.batter.has_mod("ECHO") or self.pitcher.has_mod("ECHO")):
                # echo vs static, or batter echo vs pitcher echo?
                if self.ty == EventType.ECHO_MESSAGE:
                    self.roll("echo target")

                    target_team = self.batting_team if self.pitcher.has_mod("ECHO") else self.pitching_team
                    players = target_team.data["lineup"] + target_team.data["rotation"]
                    all_players = []
                    players_with_mods = []
                    for player_id in players:
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

                    return True
                if self.ty in [
                    EventType.ECHO_INTO_STATIC,
                    EventType.RECEIVER_BECOMES_ECHO,
                ]:
                    self.roll("echo target")
                    self.roll("echo target")
                    return True
        elif self.weather == Weather.REVERB:
            if self.stadium.has_mod("ECHO_CHAMBER"):
                self.roll("echo chamber")
                if self.ty == EventType.ECHO_CHAMBER:
                    self.roll("echo chamber")
                    return True

            self.roll("reverb")
            if self.ty == EventType.REVERB_ROSTER_SHUFFLE:
                # todo: how many rolls?
                for _ in range(2):
                    self.roll("reverb shuffle?")
                for _ in range(len(self.pitching_team.data["rotation"])):
                    self.roll("reverb shuffle?")
                return True

        elif self.weather == Weather.BLACK_HOLE:
            pass

        elif self.weather == Weather.COFFEE:
            self.roll("coffee")
            if self.ty == EventType.COFFEE_BEAN:
                self.roll("coffee proc")
                self.roll("coffee proc")

                return True

            if self.batter.has_mod("COFFEE_PERIL"):
                self.roll("observed?")

        elif self.weather == Weather.COFFEE_2:
            self.roll("coffee 2")

            if self.ty == EventType.GAIN_FREE_REFILL:
                self.roll("coffee 2 proc")
                self.roll("coffee 2 proc")
                self.roll("coffee 2 proc")
                return True

            if self.batter.has_mod("COFFEE_PERIL"):
                self.roll("observed?")

        elif self.weather == Weather.COFFEE_3S:
            if self.batter.has_mod("COFFEE_PERIL"):
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
            self.print("error: {} weather not implemented".format(self.weather.name))

    def handle_flooding(self):
        if self.weather == Weather.FLOODING:
            if self.update["basesOccupied"]:
                self.roll("flooding")

            if self.ty == EventType.FLOODING_SWEPT:
                # handle flood
                for runner_id in self.update["baseRunners"]:
                    runner = self.data.get_player(runner_id)
                    if not runner.has_any("EGO1", "SWIM_BLADDER"):
                        self.roll("sweep ({})".format(runner.name))

                if self.stadium.id and not self.stadium.has_mod("FLOOD_PUMPS"):
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

        players = team.data["lineup"] + team.data["rotation"]
        did_elsewhere_return = False
        for player_id in players:
            player = self.data.get_player(player_id)

            if player.has_mod("ELSEWHERE"):
                self.roll("elsewhere ({})".format(player.raw_name))

                if self.ty == EventType.RETURN_FROM_ELSEWHERE and player.raw_name in self.desc:
                    self.do_elsewhere_return(player)
                    did_elsewhere_return = True
        if did_elsewhere_return:
            return

        for player_id in players:
            player = self.data.get_player(player_id)

            if player.has_mod("SCATTERED"):
                unscatter_roll = self.roll("unscatter ({})".format(player.raw_name))

                # todo: find actual threshold
                threshold = 0.0005
                if self.season == 14:  # seems to be lower in s15?
                    threshold = 0.0004
                if unscatter_roll < threshold:
                    self.roll("unscatter letter ({})".format(player.raw_name))

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
        if (self.season, self.day) > (13, 24):
            self.what1 = self.roll("???")
        else:
            self.what1 = 0

        # todo: roll order (might be home/away?)
        if self.what1 < 0.5:
            teams = [self.away_team, self.home_team]
        else:
            teams = [self.home_team, self.away_team]

        for team in teams:
            level = team.data.get("level", 0)
            if level >= 5:
                self.roll("consumers ({})".format(team.data["nickname"]))
                if self.ty == EventType.CONSUMERS_ATTACK:
                    attacked_player_id = self.event["playerTags"][0]
                    is_on_team = attacked_player_id in (team.data["lineup"] + team.data["rotation"])
                    if is_on_team:
                        attacked_player = self.data.get_player(attacked_player_id)

                        self.roll("target")
                        for _ in range(25):
                            self.roll("stat change")

                        if attacked_player.data["soul"] == 1:
                            # lost their last soul, redact :<
                            self.print("!!! {} lost last soul, redacting".format(attacked_player.name))
                            if attacked_player_id in team.data["lineup"]:
                                team.data["lineup"].remove(attacked_player_id)
                            if attacked_player_id in team.data["rotation"]:
                                team.data["rotation"].remove(attacked_player_id)

                        return True

    def handle_party(self):
        # lol. turns out it just rolls party all the time and throws out the roll if the team isn't partying
        party_roll = self.roll("party time")
        if self.ty == EventType.PARTY:
            self.log_roll(self.party_rolls, "Party", party_roll, True)
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
            if team_roll < 0.5 and self.home_team.has_mod("PARTY_TIME"):
                self.print("!!! home team is in party time")
            elif team_roll > 0.5 and self.away_team.has_mod("PARTY_TIME"):
                self.print("!!! away team is in party time")

    def handle_ballpark(self):
        if self.stadium.has_mod("PEANUT_MISTER"):
            self.roll("peanut mister")

            if self.ty == EventType.PEANUT_MISTER:
                self.roll("target")
                return True

        if self.stadium.has_mod("SMITHY"):
            self.roll("smithy")

        if self.stadium.has_mod("SECRET_BASE"):
            if self.handle_secret_base():
                return True

        if self.stadium.has_mod("GRIND_RAIL"):
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
            pitching_lineup = self.pitching_team.data["lineup"]
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
                self.print("!!! attractor placed in secret base:", attractor.name)
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
                self.print("!!! redacted baserunner:", runner.name)

                # remove baserunner from roster so fielder math works.
                # should probably move this logic into a function somehow
                lineup = self.batting_team.data["lineup"]
                lineup.remove(runner_id)
                runner.data["permAttr"].append("REDACTED")

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
                lo1 = runner.data["pressurization"] * 200
                hi1 = runner.data["cinnamon"] * 1500 + 500
                score_1 = int((hi1 - lo1) * score_1_roll + lo1)
                self.print("(score: {})".format(score_1))

                self.roll("trick 1 success")

                if "lose their balance and bail!" not in self.desc:
                    self.roll("trick 2 name")
                    score_2_roll = self.roll("trick 2 score")
                    lo2 = runner.data["pressurization"] * 500
                    hi2 = runner.data["cinnamon"] * 3000 + 1000
                    score_2 = int((hi2 - lo2) * score_2_roll + lo2)
                    self.print("(score: {})".format(score_2))

                    self.roll("trick 2 success")
                return True

    def handle_steal(self):
        bases = self.update["basesOccupied"]
        self.print("- base states: {}".format(bases))

        base_stolen = None
        if "second base" in self.desc:
            base_stolen = 1
        elif "third base" in self.desc:
            base_stolen = 2
        elif "fourth base" in self.desc:
            base_stolen = 3

        for i, base in enumerate(bases):
            if base + 1 not in bases:
                runner = self.data.get_player(self.update["baseRunners"][i])

                steal_roll = self.roll("steal ({})".format(base))

                was_success = self.ty == EventType.STOLEN_BASE and base + 1 == base_stolen
                self.log_roll(
                    self.steal_attempt_rolls,
                    "StealAttempt{}".format(base),
                    steal_roll,
                    was_success,
                    runner,
                )

                if was_success:
                    success_roll = self.roll("steal success")
                    was_caught = "caught stealing" in self.desc

                    self.log_roll(
                        self.steal_success_rolls,
                        "StealSuccess{}".format(base),
                        success_roll,
                        not was_caught,
                        runner,
                    )
                    return True

            if bases == [2, 2]:
                # don't roll twice when holding hands
                break

    def throw_pitch(self, known_result=None):
        roll = self.roll("strike")
        if self.pitching_team.has_mod("ACIDIC"):
            self.roll("acidic")

        vibes = self.pitcher.vibes(self.day)
        ruth = self.pitcher.data["ruthlessness"] * self.get_pitcher_multiplier(relevant_attr="ruthlessness")
        musc = self.batter.data["musclitude"] * self.get_batter_multiplier(relevant_attr="musclitude")
        fwd = self.stadium.data["forwardness"]

        constant = 0.2 if not self.is_flinching() else 0.4
        ruth_factor = 0.3 if self.season == 13 else 0.285  # 0.3 in s14, 0.285 in s15
        threshold = constant + ruth_factor * (ruth * (1 + 0.2 * vibes)) + 0.2 * fwd + 0.1 * musc
        threshold = min(threshold, 0.85)

        self.is_strike = roll < threshold
        self.strike_roll = roll
        self.strike_threshold = threshold

        if known_result == "strike" and roll > threshold:
            self.print(
                "!!! warn: too high strike roll (threshold {})".format(threshold)
            )
        elif known_result == "ball" and roll < threshold:
            self.print("!!! warn: too low strike roll (threshold {})".format(threshold))

        # todo: double strike

        return roll

    def log_roll(
        self,
        roll_list: List[RollLog],
        event_type: str,
        roll: float,
        passed: bool,
        relevant_batter=None,
        fielder_roll=None,
        fielder=None,
    ):

        roll_list.append(
            make_roll_log(
                event_type,
                roll,
                passed,
                relevant_batter or self.batter,
                self.batting_team,
                self.pitcher,
                self.pitching_team,
                self.stadium,
                self.update,
                self.what1,
                self.what2,
                self.get_batter_multiplier(relevant_batter),
                self.get_pitcher_multiplier(),
                self.is_strike,
                self.strike_roll,
                self.strike_threshold,
                fielder_roll,
                fielder,
            )
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
            return
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

        self.batter = self.data.get_player(batter_id) if batter_id else None
        self.pitcher = self.data.get_player(pitcher_id) if pitcher_id else None

        home_pitcher_id = update["homePitcher"] or next_update["homePitcher"]
        away_pitcher_id = update["awayPitcher"] or next_update["awayPitcher"]
        self.home_pitcher = self.data.get_player(home_pitcher_id) if home_pitcher_id else None
        self.away_pitcher = self.data.get_player(away_pitcher_id) if away_pitcher_id else None

        self.stadium = self.data.get_stadium(update["stadiumId"]) if update["stadiumId"] else null_stadium

        self.outs = update["halfInningOuts"]
        self.max_outs = update["awayOuts"] if update["topOfInning"] else update["homeOuts"]
        self.strikes = update["atBatStrikes"]
        self.max_strikes = update["awayStrikes"] if update["topOfInning"] else update["homeStrikes"]
        self.balls = update["atBatBalls"]
        self.max_balls = update["awayBalls"] if update["topOfInning"] else update["homeBalls"]

        # handle player name unscattering etc, not perfect but helps a lot
        if self.batter and self.pitcher:
            if update["topOfInning"]:
                self.batter.data["name"] = self.update["awayBatterName"]
                self.pitcher.data["name"] = self.update["homePitcherName"]
            else:
                self.batter.data["name"] = self.update["homeBatterName"]
                self.pitcher.data["name"] = self.update["awayPitcherName"]

        if self.next_update:
            inning_key = (self.game_id, self.next_update["inning"])
            if inning_key not in self.score_at_inning_start:
                self.score_at_inning_start[inning_key] = (
                    self.next_update["awayScore"],
                    self.next_update["homeScore"],
                )

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
            else:
                team = self.data.get_team(event["teamTags"][0])
                team.data[position].append(meta["mod"])

        # player or team mod removed
        if event["type"] in [
            EventType.REMOVED_MOD,
            EventType.REMOVED_MODIFICATION,
        ]:
            position = mod_positions[meta["type"]]

            if event["playerTags"]:
                player = self.data.get_player(event["playerTags"][0])
                player.data[position].remove(meta["mod"])
            else:
                team = self.data.get_team(event["teamTags"][0])

                if meta["mod"] not in team.data[position]:
                    self.print("!!! warn: trying to remove mod {} but can't find it".format(meta["mod"]))
                else:
                    team.data[position].remove(meta["mod"])

        # mod replaced
        if event["type"] in [EventType.CHANGED_MODIFIER]:
            position = mod_positions[meta["type"]]

            if event["playerTags"]:
                player = self.data.get_player(event["playerTags"][0])
                player.data[position].remove(meta["from"])
                player.data[position].append(meta["to"])
            else:
                team = self.data.get_team(event["teamTags"][0])
                team.data[position].remove(meta["from"])
                team.data[position].append(meta["to"])

        # timed mods wore off
        if event["type"] in [EventType.MOD_EXPIRES]:
            position = mod_positions[meta["type"]]

            if event["playerTags"]:
                for mod in meta["mods"]:
                    player = self.data.get_player(event["playerTags"][0])
                    if mod not in player.data[position]:
                        self.print("!!! warn: trying to remove mod {} but can't find it".format(mod))
                    else:
                        player.data[position].remove(mod)

            else:
                for mod in meta["mods"]:
                    team = self.data.get_team(event["teamTags"][0])
                    team.data[position].remove(mod)

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
                    # self.print("stat delta: {} {}".format(k, delta))

        # scatter player name
        if event["type"] == EventType.ADDED_MOD and "was Scattered..." in desc:
            new_name = desc.split(" was Scattered")[0]
            player = self.data.get_player(event["playerTags"][0])
            player.data["name"] = new_name

        # player removed from roster
        if event["type"] == EventType.PLAYER_REMOVED_FROM_TEAM:
            team_id = meta["teamId"]
            player_id = meta["playerId"]
            team = self.data.get_team(team_id)
            if player_id in team.data["lineup"]:
                team.data["lineup"].remove(player_id)
            if player_id in team.data["rotation"]:
                team.data["rotation"].remove(player_id)

        # mod changed from one to other
        if event["type"] == EventType.MODIFICATION_CHANGE:
            player = self.data.get_player(event["playerTags"][0])
            player.data[mod_positions[meta["type"]]].remove(meta["from"])
            player.data[mod_positions[meta["type"]]].append(meta["to"])

            # todo: do this in other cases too?
            if meta["from"] == "RECEIVER":
                for mod, source in player.data["state"]["seasModSources"].items():
                    if source == ["RECEIVER"]:
                        player.data["seasAttr"].remove(mod)

        # roster swap
        if event["type"] == EventType.PLAYER_TRADED:
            a_team = self.data.get_team(meta["aTeamId"])
            b_team = self.data.get_team(meta["bTeamId"])
            a_location = ["lineup", "rotation"][meta["aLocation"]]
            b_location = ["lineup", "rotation"][meta["bLocation"]]
            a_player = meta["aPlayerId"]
            b_player = meta["bPlayerId"]
            a_idx = a_team.data[a_location].index(a_player)
            b_idx = b_team.data[b_location].index(b_player)

            b_team.data[b_location][b_idx] = a_player
            a_team.data[a_location][a_idx] = b_player

    def run(self, start_timestamp, end_timestamp, total_events, prev_processed_events):
        tqdm.write(f"Starting fragment at {start_timestamp}")
        self.data.fetch_league_data(start_timestamp)
        feed_events = get_feed_between(start_timestamp, end_timestamp)

        processed_events = 0
        for event in tqdm(
            feed_events,
            total=total_events,
            initial=prev_processed_events,
            unit="events",
        ):
            processed_events += 1
            event["type"] = EventType(event["type"])
            self.handle(event)

        self.save_data(start_timestamp)

        return processed_events

    def roll(self, label) -> float:
        value = self.rng.next()
        self.print("{}: {}".format(label, value))
        return value

    def get_batter_multiplier(self, relevant_batter=None, relevant_attr=None):
        batter = relevant_batter or self.batter
        # attr = relevant_attr

        batter_multiplier = 1
        for mod in itertools.chain(batter.mods, self.batting_team.mods):
            if mod == "OVERPERFORMING":
                batter_multiplier += 0.2
            elif mod == "UNDERPERFORMING":
                batter_multiplier -= 0.2
            elif mod == "GROWTH":
                batter_multiplier += min(0.05, 0.05 * (self.day / 99))
            elif mod == "HIGH_PRESSURE":
                # checks for flooding weather and baserunners
                if self.weather == Weather.FLOODING and len(self.update["baseRunners"]) > 0:
                    # "won't this stack with the overperforming mod it gives the team" yes. yes it will.
                    batter_multiplier += 0.25
            elif mod == "TRAVELING":
                if self.update["topOfInning"]:
                    batter_multiplier += 0.05
            elif mod == "SINKING_SHIP":
                roster_size = len(self.batting_team.data["lineup"]) + len(self.batting_team.data["rotation"])
                batter_multiplier += (14 - roster_size) * 0.01
            elif mod == "AFFINITY_FOR_CROWS" and self.weather == Weather.BIRDS:
                batter_multiplier += 0.5
            elif mod == "CHUNKY" and self.weather == Weather.PEANUTS:
                # todo: handle carefully! historical blessings boosting "power" (Ooze, S6) boosted groundfriction
                #  by half of what the other two attributes got. (+0.05 instead of +0.10, in a "10% boost")
                if relevant_attr in ["musclitude", "divinity", "ground_friction"]:
                    batter_multiplier += 1.0
            elif mod == "SMOOTH" and self.weather == Weather.PEANUTS:
                # todo: handle carefully! historical blessings boosting "speed" (Spin Attack, S6) boosted everything in
                #  strange ways: for a "15% boost", musc got +0.0225, cont and gfric got +0.075, laser got +0.12.
                if relevant_attr in [
                    "musclitude",
                    "continuation",
                    "ground_friction",
                    "laserlikeness",
                ]:
                    batter_multiplier += 1.0
            elif mod == "ON_FIRE":
                # todo: figure out how the heck "on fire" works
                pass
        return batter_multiplier

    def get_pitcher_multiplier(self, relevant_attr=None):
        pitcher_multiplier = 1
        # attr = relevant_attr
        # growth or traveling do not work for pitchers as of s14
        for mod in itertools.chain(self.pitcher.mods, self.pitching_team.mods):
            if mod == "OVERPERFORMING":
                pitcher_multiplier += 0.2
            elif mod == "UNDERPERFORMING":
                pitcher_multiplier -= 0.2
            elif mod == "SINKING_SHIP":
                roster_size = len(self.pitching_team.data["lineup"]) + len(self.pitching_team.data["rotation"])
                pitcher_multiplier += (14 - roster_size) * 0.01
            elif mod == "AFFINITY_FOR_CROWS" and self.weather == Weather.BIRDS:
                pitcher_multiplier += 0.5
            elif mod == "HIGH_PRESSURE":
                # "should we really boost the pitcher when the *other* team's batters are on base" yes.
                if self.weather == Weather.FLOODING and len(self.update["baseRunners"]) > 0:
                    pitcher_multiplier += 0.25
        return pitcher_multiplier

    def save_data(self, run_name):
        os.makedirs("roll_data", exist_ok=True)
        run_name = run_name.replace(":", "_")

        to_save = [
            # ("strikes", self.strike_rolls),
            # ("fouls", self.foul_rolls),
            # ("triples", self.triple_rolls),
            # ("swing-on-ball", self.swing_on_ball_rolls),
            # ("swing-on-strike", self.swing_on_strike_rolls),
            # ("contact", self.contact_rolls),
            # ("hr", self.hr_rolls),
            # ("steal_attempt", self.steal_attempt_rolls),
            # ("steal_success", self.steal_success_rolls),
            # ("party", self.party_rolls),
            # ("out", self.out_rolls),
            # ("fly", self.fly_rolls),
            ("fc-dp", self.fc_dp_rolls),
        ]
        for category_name, data in to_save:
            tqdm.write(f"Saving {category_name} csv...")
            pd.DataFrame(data).to_csv(f"roll_data/{run_name}-{category_name}.csv")


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
