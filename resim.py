from typing import List

import pandas as pd

from data import GameData, get_feed_between, weather_names
from output import RollLog, make_roll_log
from rng import Rng

class Resim:
    def __init__(self, rng):
        self.rng = rng
        self.data = GameData()
        self.fetched_days = set()

        self.strike_rolls: List[RollLog] = []

    def handle(self, event):
        self.setup_data(event)
        
        print()
        print("===== {} {} {}".format(event["created"], self.update["id"], weather_names[self.update["weather"]]))
        print("===== {} {}".format(self.ty, self.desc))

        if self.handle_misc():
            return            

        if self.handle_elsewhere_scattered():
            return

        if self.ty in [23, 84]:
            # skipping elsewhere/elsewhere return
            return

        if self.batter:
            print("- batter mods: {} + {}".format(self.batter.mods, self.batting_team.mods))
        if self.pitcher:
            print("- pitcher mods: {} + {}".format(self.pitcher.mods, self.pitching_team.mods))
        print("- stadium mods: {}".format(self.stadium.mods))

        if self.ty == 12:
            self.handle_batter_up()
            return

        if self.handle_weather():
            return

        if self.handle_party():
            return

        # has to be rolled after party
        if self.handle_flooding():
            return

        self.roll("???")

        if self.handle_consumers():
            return

        if self.handle_ballpark():
            return

        if self.ty == 165:
            # s14 high pressure proc, not sure when this should interrupt
            return

        self.roll("???")

        if self.handle_steal():
            return

        if self.handle_electric():
            return

        if self.handle_bird_ambush():
            return

        if self.handle_mild():
            return
        
        if self.handle_charm():
            return

        if self.ty in [5, 14, 27]:
            self.handle_ball()
        elif self.ty in [7, 8]:
            self.handle_out()
        elif self.ty in [6, 13]:
            self.handle_strike()
        elif self.ty in [9]:
            self.handle_hr()
        elif self.ty in [10]:
            self.handle_base_hit()
        elif self.ty in [15]:
            self.handle_foul()
        else:
            print("!!! unknown type: {}".format(self.ty))
        pass

        self.handle_batter_reverb()


    def handle_misc(self):
        if self.ty in [21, 78, 91, 92, 93, 99, 173, 182, 36]:
            # skipping pregame messages
            return True
        if self.ty in [85, 86, 146, 147, 171, 172]:
            # skipping mod added/removed
            return True
        if self.ty in [30, 31, 156]:
            # skipping sun 2 / black hole proc
            return True
        if self.ty in [117, 118]:
            # skipping consumer/party stat change
            return True
        if self.ty in [28]:
            # skipping inning outing
            if self.update["inning"] == 2:
                if self.home_pitcher.has_mod("TRIPLE_THREAT"):
                    self.roll("remove home pitcher triple threat")
                if self.away_pitcher.has_mod("TRIPLE_THREAT"):
                    self.roll("remove away pitcher triple threat")
            # todo: salmon
            return True
        if self.ty in [2]:
            # skipping top-of
            if self.update["weather"] == 19:
                self.try_roll_salmon()
            return True
        if self.ty in [11, 158, 159, 106, 154, 155, 108, 107]:
            # skipping game end
            return True
        if self.ty in [0]:                
            # game start - probably like, postseason weather gen 
            if self.event["day"] >= 99:
                self.roll("game start")
            self.roll("game start")

            extra_start_rolls = {
                "17651ff0-3b87-48d6-b7a8-7e5fe115f463": 2,
                "606166b9-2aef-47e8-aa4a-52f863880408": 2,
                "fa9dab2a-409c-4886-979c-f1c584518d5d": 1,
                "3244b12f-838a-4d75-abde-88874b75ab04": 2,
                "a47f2a8b-0bde-42c8-bdd0-0513da92a6b1": 1,
            }

            for _ in range(extra_start_rolls.get(self.game_id, 0)):
                self.roll("align start")

            return True
        if self.ty in [1]:
            # play ball (already handled above but we want to fetch a tiny tick later)
            if self.event["day"] not in self.fetched_days:
                self.fetched_days.add(self.event["day"])

                timestamp = self.event["created"]
                if self.event["day"] == 96:
                    timestamp = "2021-03-19T17:00:26.298Z"
                if self.event["day"] == 97:
                    timestamp = "2021-03-19T18:00:26.298Z"

                self.data.fetch_league_data(timestamp)

            if self.weather in [12, 13] and self.stadium.has_mod("PSYCHOACOUSTICS"):
                print("away team mods:", self.away_team.data["permAttr"])
                if self.away_team.data["permAttr"]:
                    self.roll("echo team mod")
            return True

    def handle_bird_ambush(self):
        if self.weather == 11:
            # todo: does this go here or nah
            # print("bird ambush eligible? {}s/{}b/{}o".format(self.strikes, self.balls, self.outs))
            if self.strikes == 0:
                self.roll("bird ambush")
                if self.ty == 34:
                    return True

    def handle_charm(self):
        pitch_charm_eligible = self.update["atBatBalls"] == 0 and self.update["atBatStrikes"] == 0
        batter_charm_eligible = self.batting_team.has_mod("LOVE") and pitch_charm_eligible
        pitcher_charm_eligible = self.pitching_team.has_mod("LOVE") and pitch_charm_eligible

        # before season 16, love blood only proc'd when the player also had love blood
        if self.event["season"] < 15:
            if self.batter.data["blood"] != 9:
                batter_charm_eligible = False

            if self.pitcher.data["blood"] != 9:
                pitcher_charm_eligible = False

        if batter_charm_eligible:
            self.roll("charm")
            if " charms " in self.desc:
                # self.roll("charm proc")
                # self.roll("charm proc")
                # self.roll("charm proc")
                return True


        if pitcher_charm_eligible:
            self.roll("charm")
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
                print("!!! warn: batter does not have electric blood")

            if self.ty == 25:
                # successful zap!
                return True

    def handle_batter_reverb(self):
        if self.batter and self.batter.has_mod("REVERBERATING"):
            is_at_bat_end = self.ty in [5, 6, 7, 8]
            # s14: hrs/hits (type 9/10) do not trigger reverberating, this probably changed later
            # home runs might not either?

            if self.ty in [9, 10]:
                print("!!! warn: no reverb on hit?")
                is_at_bat_end = False

            if is_at_bat_end:
                self.roll("at bat reverb")


    def handle_mild(self):
        self.roll("mild")
        if self.ty == 27:
            # skipping mild proc
            return True

    def handle_ball(self):
        value = self.throw_pitch("ball")
        self.log_roll("Ball", value, False)

        if not self.is_flinching():
            self.roll("swing")

        if self.ty == 5 and self.batting_team.has_mod("BASE_INSTINCTS"):
            self.roll("base instincts")

            if "Base Instincts take them directly to" in self.desc:
                self.roll("which base")
                self.roll("which base")

    def handle_strike(self):
        if ", swinging" in self.desc or "strikes out swinging." in self.desc:
            self.throw_pitch()
            self.roll("swing")
            self.roll("contact")
        elif ", looking" in self.desc or "strikes out looking." in self.desc:
            value = self.throw_pitch("strike")
            self.log_roll("StrikeLooking", value, True)

            if not self.is_flinching():
                self.roll("swing")
        elif ", flinching" in self.desc:
            self.throw_pitch("strike")
        pass

    def try_roll_salmon(self):
        if self.weather == 19 and self.next_update["inning"] > 0 and not self.update["topOfInning"]:
            last_play = self.data.get_update(self.game_id, self.play-2)

            # only roll salmon if the last inning had any scores, but also we have to dig into game history to find this
            # how does the sim do it? no idea. i'm cheating.
            # print("salmon state", last_play["topInningScore"], last_play["bottomInningScore"], last_play["halfInningScore"], last_play["newInningPhase"])
            if last_play["topInningScore"] or last_play["bottomInningScore"]:
                self.roll("salmon")

                if self.ty == 63:
                    self.roll("salmon effect")
                    self.roll("salmon effect")
                    self.roll("salmon effect")
                    self.roll("salmon effect")

    
    def is_flinching(self):
        return self.batter.has_mod("FLINCH") and self.strikes == 0

    def handle_out(self):
        self.throw_pitch()
        self.roll("swing")
        self.roll("contact")
        self.roll("foul")

        if self.ty == 7:
            self.roll("???")
            self.roll("???")
        elif self.ty == 8:
            self.roll("???")
            self.roll("???")
            self.roll("???")
            self.roll("???")

        self.roll_fielder()

        if self.ty == 7:
            # extra flyout roll
            self.roll("???")

        if self.outs < self.max_outs - 1:
            self.handle_out_advances()

        if self.batter.has_mod("DEBT_THREE"):
            self.roll("debt")

    def roll_fielder(self):
        roll_value = self.roll("fielder")

        eligible_fielders = []
        fielder_idx = None
        for fielder_id in self.pitching_team.data["lineup"]:
            fielder = self.data.get_player(fielder_id)
            if fielder.has_mod("ELSEWHERE"):
                continue

            if fielder.raw_name in self.desc:
                fielder_idx = len(eligible_fielders)
            eligible_fielders.append(fielder)

        if fielder_idx is not None:
            rolled_idx = int(roll_value * len(eligible_fielders))

            if rolled_idx != fielder_idx:
                expected_min = fielder_idx / len(eligible_fielders)
                expected_max = (fielder_idx + 1) / len(eligible_fielders)
                print("!!! incorrect fielder! expected {}, got {}, needs to be {:.3f}-{:.3f}".format(fielder_idx, rolled_idx, expected_min, expected_max))

            matching = []
            r2 = Rng(self.rng.state, self.rng.offset)
            check_range = 50
            r2.step(-check_range)
            for i in range(check_range * 2):
                val = r2.next()
                if int(val * len(eligible_fielders)) == fielder_idx:
                    matching.append(i - check_range + 1)
            print("(matching offsets: {})".format(matching))
        else:
            if "fielder's choice" not in self.desc and "double play" not in self.desc:
                print("!!! could not find fielder (name wrong?)")

    def handle_out_advances(self):
        bases_before = make_base_map(self.update)
        bases_after = make_base_map(self.next_update)

        if self.ty == 7:
            # flyouts are nice and simple
            for runner_id, base, roll_outcome in calculate_advances(bases_before, bases_after, 0):
                self.roll("adv ({}, {})".format(base, roll_outcome))

                # or are they? [2,0] -> [2,0] = 1 roll?
                # [1, 0] -> [2, 0] = 1 roll?
                # but a [2, 0] -> [0] score is 2, so it's not like it never rolls twice (unless it's special cased...)
                if not roll_outcome or base == 1:
                    break

        elif self.ty == 8:
            # ground out
            extras = {
                (tuple(), tuple()): 0,
                ((0,), (0,)): 2, # fielder's choice (successful)
                ((0,), (1,)): 3,
                ((1,), (1,)): 2,
                
                ((2, 0), (2, 1)): 4, 
                ((1,), (2,)): 2,
                ((2, 1), (2,)): 3,
                ((0,), tuple()): 2, # double play (successful)
                ((2,), tuple()): 2, # sac
                ((1, 0), (2, 1)): 4,
                ((1, 0), (1, 0)): 2,
                ((2, 0), (0,)): 4,
                ((2,), (2,)): 2,
                ((1, 0), tuple()): 2, # double play + second, 2 or 3 rolls?
                ((2, 1, 0), (2, 1, 0)): 2,
                ((2, 1, 0), (2, 1)): 5, # guessing
                ((2, 1, 0), tuple()): 2, # dp
                ((2, 1), (1,)): 3, # guessing
                ((2, 0), tuple()): 2, # double play + sac?
                ((1, 0), (1,)): 2, # double play but they stay?
            }

            if "reaches on fielder's choice" in self.desc:
                extras[((2, 0), (0,))] = 2 # what
            
            rolls = extras[(tuple(self.update["basesOccupied"]), tuple(self.next_update["basesOccupied"]))]
            for _ in range(rolls):
                self.roll("extra")

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
            #             print("base {} force advance".format(base))
            #             del adv_eligible_runners[base]
            #         else:
            #             print("base {} is clear, stopping".format(base))
            #             break

            # print("after force:", adv_eligible_runners)
            # # do "regular" adv for rest
            # for runner_id, base, roll_outcome in calculate_advances(adv_eligible_runners, bases_after, 0):
            #     self.roll("adv ({}, {})".format(base, roll_outcome))

            #     if base == 1:
            #         print("extra adv 1?")
            #     if base == 2:
            #         self.roll("extra adv 2?")


        print("OUT {} {} -> {}".format(self.ty, self.update["basesOccupied"], self.next_update["basesOccupied"]))


    def handle_hit_advances(self, bases_hit):
        bases_before = make_base_map(self.update)
        bases_after = make_base_map(self.next_update)
        for runner_id, base, roll_outcome in calculate_advances(bases_before, bases_after, bases_hit):
            self.roll("adv ({}, {})".format(base, roll_outcome))

    def handle_hr(self):
        if not self.batter.has_mod("MAGMATIC"):
            self.throw_pitch()
            self.roll("swing")
            self.roll("contact")
            self.roll("foul")
            self.roll("???")
            self.roll("???")
            self.roll("home run")
        else:
            # not sure why we need this
            self.roll("magmatic")
            self.roll("magmatic")


        if self.stadium.has_mod("BIG_BUCKET"):
            self.roll("big buckets")

    def handle_base_hit(self):
        self.throw_pitch()
        self.roll("swing")
        self.roll("contact")
        self.roll("foul")

        self.roll("???")
        self.roll("???")
        self.roll("???")
        self.roll("???")
        self.roll("???")
        self.roll("???")

        hit_bases = 0
        if "hits a Single!" in self.desc:
            hit_bases = 1
        elif "hits a Double!" in self.desc:
            hit_bases = 2
        elif "hits a Triple!" in self.desc:
            hit_bases = 3

        self.handle_hit_advances(hit_bases)

    def handle_foul(self):
        self.throw_pitch()
        self.roll("swing")
        self.roll("contact")

        foul_roll = self.roll("foul")

        is_0_no_eligible = self.batting_team.has_mod("O_NO") and self.strikes == 2 and self.balls == 0
        if foul_roll > 0.5 and not is_0_no_eligible:
            print("!!! too high foul roll ({})".format(foul_roll))

    def handle_batter_up(self):
        if self.batter.has_mod("HAUNTED"):
            self.roll("haunted")

        if "is Inhabiting" in self.event["description"]:
            self.roll("haunted")
            self.roll("haunter selection")

    def handle_weather(self):
        if self.weather == 1:
            # sun 2
            pass
        elif self.weather == 7:
            # eclipse
            self.roll("eclipse")

            fire_eater_eligible = self.pitching_team.data["lineup"] + [self.batter.id, self.pitcher.id]
            for player_id in fire_eater_eligible:
                player = self.data.get_player(player_id)

                if player.has_mod("FIRE_EATER") and not player.has_mod("ELSEWHERE"):
                    self.roll("fire eater ({})".format(player.name))

                    if self.ty == 55:
                        # fire eater proc - target roll maybe?
                        self.roll("target")
                        return True
                    break
        elif self.weather == 8:
            # glitter
            self.roll("glitter")
        elif self.weather == 9:
            # blooddrain
            self.roll("blooddrain")
        elif self.weather == 10:
            # peanuts
            self.roll("peanuts")

            if self.ty == 73:
                self.roll("peanut message")
                return True

            self.roll("peanuts")
            
            if self.batter.has_mod("HONEY_ROASTED"):
                self.roll("honey roasted")

        elif self.weather == 11:
            # birds
            self.roll("birds")

            if self.ty == 33:
                # the birds circle...
                return True
        elif self.weather == 12:
            # feedback
            self.roll("feedback")
            self.roll("feedback") # this is probably echo y/n? but ignored if the mod isn't there

            if self.weather in [12, 13] and self.batter.has_mod("ECHO"):
                if self.ty == 169:
                    self.roll("echo target")
                    return True
        elif self.weather == 13:
            # reverb
            self.roll("reverb")
        elif self.weather == 14:
            # black hole
            pass
        elif self.weather == 15:
            # coffee
            self.roll("coffee")
        elif self.weather == 16:
            # coffee 2
            self.roll("coffee 2")

            if self.ty == 37:
                self.roll("coffee 2 proc")
                self.roll("coffee 2 proc")
                self.roll("coffee 2 proc")
                return True
        elif self.weather == 17:
            # coffee 3s
            pass
        elif self.weather == 18:
            # flooding
            pass
        elif self.weather == 19:
            # salmon
            pass
        elif self.weather in [20, 21]:
            # polarity +/-
            self.roll("polarity")
        else:
            print("error: {} weather not implemented".format(weather_names[self.weather]))
        
    def handle_flooding(self):
        if self.weather == 18:
            if self.update["basesOccupied"]:
                self.roll("flooding")

            if self.ty == 62:
                # handle flood
                for runner_id in self.update["baseRunners"]:
                    runner = self.data.get_player(runner_id)
                    if not runner.has_any("EGO1", "EGO2", "EGO3", "EGO4", "SWIM_BLADDER"):
                        self.roll("sweep ({})".format(runner.name))
                self.roll("filthiness")
                return True

    def handle_elsewhere_scattered(self):
        # looks like elsewhere and scattered get rolled separately at least in s14?
        # not sure what the cancel logic is here
        players = self.batting_team.data["lineup"] + self.batting_team.data["rotation"]
        did_elsewhere_return = False
        for player_id in players:
            player = self.data.get_player(player_id)

            if player.has_mod("ELSEWHERE"):
                self.roll("elsewhere ({})".format(player.raw_name))

                if self.ty == 84 and player.raw_name in self.desc:
                    self.do_elsewhere_return(player)
                    did_elsewhere_return = True
        if did_elsewhere_return:
            return

        for player_id in players:
            player = self.data.get_player(player_id)

            if player.has_mod("SCATTERED"):
                unscatter_roll = self.roll("unscatter ({})".format(player.raw_name))
                if unscatter_roll < 0.0005: # todo: find threshold
                    self.roll("unscatter letter ({})".format(player.raw_name))
                    
                    # lol. (just to make fielder selection work through unscatters)
                    if player.raw_name == "Sand-e T--ne-":
                        player.data["name"] = "Sand-e T--ner"
                    if player.raw_name == "Igneus -elacru-":
                        player.data["name"] = "Igneus Delacru-"


    def do_elsewhere_return(self, player):
        scatter_times = 0
        if "days" in self.desc:
            elsewhere_time = int(self.desc.split("after ")[1].split(" days")[0])
            if elsewhere_time >= 18:
                scatter_times = elsewhere_time + 2 # ???
        if "season" in self.desc:
            scatter_times = 32 # guessing for now

        for _ in range(scatter_times):
            # todo: figure out what these are
            self.roll("scatter letter")

        # hardcoded for now
        if player.raw_name == "Sandie Turner":
            player.data["name"] = "Sand-e T--ne-"

    
    def handle_consumers(self):
        # todo: roll order (might be home/away?)
        teams = [self.batting_team, self.pitching_team]

        for team in teams:
            if team.data["level"] >= 5:
                self.roll("consumers ({})".format(team.data["nickname"]))

            if self.ty == 67:
                # can we trust ordering here
                attacked_team = self.event["teamTags"][0]
                if team.id == attacked_team:
                    self.roll("target")
                    for _ in range(25):
                        self.roll("stat change")

                    return True

    def handle_party(self):
        # lol. turns out it just rolls party all the time and throws out the roll if the team isn't partying
        party_roll = self.roll("party time")
        if self.ty == 24:
            team_roll = self.roll("target team") # <0.5 for home, >0.5 for away
            self.roll("target player")
            for _ in range(25):
                self.roll("stat")
            return True

        # we have a positive case at 0.005210187516443421 (2021-03-19T14:22:26.078Z)
        # this is probably influenced by ballpark myst or something
        elif party_roll < 0.00522:
            self.roll("target team (not partying)")

    def handle_ballpark(self):
        if self.stadium.has_mod("PEANUT_MISTER"):
            self.roll("peanut mister")

            if self.ty == 72:
                self.roll("target")
                return True

        if self.stadium.has_mod("SMITHY"):
            self.roll("smithy")

        if self.stadium.has_mod("SECRET_BASE"):
            if self.handle_secret_base():
                return True

        if self.stadium.has_mod("GRIND_RAIL"):
            print("todo: grind rail handling")
            pass # todo

        league_mods = self.data.sim["attr"]
        if "SECRET_TUNNELS" in league_mods:
            self.roll("tunnels")

    def handle_secret_base(self):
        # not sure this works
        secret_runner = self.update["secretBaserunner"]
        bases = self.update["basesOccupied"]

        secret_base_enter_eligible = 1 in bases and not secret_runner
        secret_base_exit_eligible = 1 not in bases and secret_runner
        secret_base_wrong_side = False
        if secret_runner:
            secret_runner = self.data.get_player(secret_runner)
            if secret_runner.data["leagueTeamId"] != self.batting_team.id:
                print("can't exit secret base on wrong team")
                secret_base_exit_eligible = False
                secret_base_wrong_side = True

        attractor_eligible = not secret_runner and 1 not in bases

        if secret_base_exit_eligible:
            self.roll("secret base exit")
        if secret_base_enter_eligible:
            # why does this roll twice?
            self.roll("secret base enter")
            self.roll("secret base enter")
        if attractor_eligible:
            self.roll("secret base attract")


    def handle_steal(self):
        bases = self.update["basesOccupied"]
        print("- base states: {}".format(bases))

        base_stolen = None
        if "second base" in self.desc:
            base_stolen = 1
        elif "third base" in self.desc:
            base_stolen = 2
        elif "fourth base" in self.desc:
            base_stolen = 3

        for base in bases:
            if base + 1 not in bases:
                self.roll("steal ({})".format(base))

                if self.ty == 4 and base + 1 == base_stolen:
                    self.roll("steal success")
                    return True

            if bases == [2, 2]:
                # don't roll twice when holding hands
                break

    def throw_pitch(self, known_result=None):
        value = self.roll("strike")
        if self.pitching_team.has_mod("ACIDIC"):
            self.roll("acidic")

        # todo: double strike

        return value

    def log_roll(self, event_type: str, roll: float, passed: bool):
        self.strike_rolls.append(make_roll_log(
            event_type,
            roll,
            passed,
            self.batter,
            self.batting_team,
            self.pitcher,
            self.pitching_team,
            self.stadium,
            self.data.players,
            self.update,
        ))

    def setup_data(self, event):
        meta = event.get("metadata") or {}
        if meta.get("subPlay", -1) != -1:
            print("=== EXTRA:", event["type"], event["description"], meta)

            mod_positions = ["permAttr", "seasAttr", "weekAttr", "gameAttr"]

            # player mod added
            if event["type"] == 106:
                player = self.data.get_player(event["playerTags"][0])
                position = mod_positions[meta["type"]]
                player.data[position].append(meta["mod"])

            # player mod removed
            if event["type"] == 107:
                player = self.data.get_player(event["playerTags"][0])
                position = mod_positions[meta["type"]]
                if meta["mod"] in player.data[position]:
                    player.data[position].remove(meta["mod"])

            # player or team mod added
            if event["type"] == 146:
                position = mod_positions[meta["type"]]

                if event["playerTags"]:
                    player = self.data.get_player(event["playerTags"][0])
                    player.data[position].append(meta["mod"])
                else:
                    team = self.data.get_team(event["teamTags"][0])
                    team.data[position].append(meta["mod"])

            # echo mods added
            if event["type"] in [171, 172]:
                player = self.data.get_player(event["playerTags"][0])
                for mod in meta.get("adds", []):
                    player.data[mod_positions[mod["type"]]].append(mod["mod"])
                for mod in meta.get("removes", []):
                    player.data[mod_positions[mod["type"]]].remove(mod["mod"])

        self.event = event
        self.ty = event["type"]
        self.desc = event["description"].replace("\n", " ").strip()

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
        if not batter_id:
            batter_id = next_update["awayBatter"] if next_update["topOfInning"] else next_update["homeBatter"]
        pitcher_id = update["homePitcher"] if update["topOfInning"] else update["awayPitcher"]
        if not pitcher_id:
            pitcher_id = next_update["homePitcher"] if next_update["topOfInning"] else next_update["awayPitcher"]

        self.batter = self.data.get_player(batter_id) if batter_id else None
        self.pitcher = self.data.get_player(pitcher_id) if pitcher_id else None

        home_pitcher_id = update["homePitcher"] or next_update["homePitcher"]
        away_pitcher_id = update["awayPitcher"] or next_update["awayPitcher"]
        self.home_pitcher = self.data.get_player(home_pitcher_id) if home_pitcher_id else None
        self.away_pitcher = self.data.get_player(away_pitcher_id) if away_pitcher_id else None

        self.stadium = self.data.get_stadium(update["stadiumId"])

        self.outs = update["halfInningOuts"]
        self.max_outs = update["awayOuts"] if update["topOfInning"] else update["homeOuts"]
        self.strikes = update["atBatStrikes"]
        self.max_strikes = update["awayStrikes"] if update["topOfInning"] else update["homeStrikes"]
        self.balls = update["atBatBalls"]
        self.max_balls = update["awayBalls"] if update["topOfInning"] else update["homeBalls"]


    def run(self, start_timestamp, end_timestamp):
        self.data.fetch_league_data(start_timestamp)
        feed_events = get_feed_between(start_timestamp, end_timestamp)
        for event in feed_events:
            self.handle(event)

        self.save_data(start_timestamp)

    def roll(self, label) -> float:
        value = self.rng.next()
        print("{}: {}".format(label, value))
        return value

    def save_data(self, run_name):
        strike_roll_df = pd.DataFrame(self.strike_rolls)
        strike_roll_df.to_csv(f"roll_data/{run_name}-strikes.csv")


def advance_bases(occupied, amount, up_to=4):
    occupied = [b+(amount if b < up_to else 0) for b in occupied]
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
            new_bases[i+1] = bases[i]
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

        is_eligible = runner+1 not in bases
        if is_eligible:
            if runner == 2:
                did_advance = third_scored 
            else:
                did_advance = runner+1 in bases_after

            rolls.append((player, runner, did_advance))
            if did_advance:
                bases[runner+1] = bases[runner]
                del bases[runner]
    
    return rolls