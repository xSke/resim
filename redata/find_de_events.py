# VERY nasty ad-hoc code just for outputting the events json files
# which themselves are very ad-hoc and can/should be refactored once the data is known-good 

import sys, os

from rng_solver import get_mantissa, solve_in_math_random_order, state_to_double

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))  # can't figure out the module system rn

from data import GameData, TeamData, get_cached
from redata.constants import *
from rng import Rng, seed_str

from dataclasses import dataclass

@dataclass
class Outcome:
    game_id: str
    timestamp: str
    text: str
    update: dict

gd = GameData()
all_games = get_cached("all_games", f"https://api.sibr.dev/chronicler/v1/games?sim=thisidisstaticyo")["data"]

def find_game_outcomes(game_id):
    updates = gd.get_raw_game_updates(game_id)

    last_outcomes = []
    for upd in updates:
        outcomes = upd["data"]["outcomes"]
        if outcomes != last_outcomes:
            for new_outcome in outcomes[len(last_outcomes):]:
                yield Outcome(game_id=game_id, timestamp=upd["timestamp"], text=new_outcome, update=upd)
        last_outcomes = outcomes

def player_by_name(name: str):
    matching = [p for p in gd.players.values() if p.name == name]
    return matching[0]

def player_team(player_id: str, team_ids: list[str]) -> TeamData:
    for t in team_ids:
        team = gd.teams[t]
        if player_id in team.lineup or player_id in team.rotation:
            return team

def game_bounds(game_id: str):
    updates = gd.get_raw_game_updates(game_id)
    before = [u for u in updates if u["data"]["gameStart"]][0]
    after = [u for u in updates if u["data"]["finalized"]][0]
    return before["timestamp"], after["timestamp"]

def get_permutation(a: list, b: list):
    assert set(a) == set(b)
    assert len(set(a)) == len(set(b)) == len(a) == len(b)

    perm = [a.index(b[i]) for i in range(len(a))]
    assert [a[i] for i in perm] == b
    return perm

def rescale(val: float, min: float, max: float) -> float:
    range = max - min
    return ((val - min) / range)

def bit_range(val: float, mask_bits: int) -> tuple[float, float]:
    mant = get_mantissa(val)
    valf = state_to_double(mant<<12)

    mask = (1 << mask_bits) - 1
    lo = mant & (mask ^ 0xFFFFFFFFFFFFFFFF)
    hi = lo ^ mask

    lof, hif = state_to_double(lo<<12), state_to_double(hi<<12)
    assert lof <= valf
    assert hif >= valf
    return lof, hif

def roster(team: TeamData) -> list[str]:
    return team.lineup + team.rotation

def solve_windowed(known_rolls):
    ws = 5
    for wi in range(len(known_rolls)-ws+1):
        w = known_rolls[wi:wi+ws]
        if not all(x for x in w):
            continue

        sol = solve_in_math_random_order(w)
        if sol:
            # to fix alignment...
            rng = Rng(sol[0]["state"], sol[0]["offset"])
            seed, offset = rng.find_seed()
            return seed_str(seed, offset-wi)

def solve_diff(player_before, player_after, range, stat_order):
    lo, hi = range

    known_rolls = []
    for attr in stat_order:
        val_before = player_before.data[attr]
        val_after = player_after.data[attr]
        diff = val_after - val_before
        if attr == "tragicness":
            known_rolls.append(None)
            continue

        diff_flip = -diff if attr in ["patheticism"] else diff
        rescaled = rescale(diff_flip, lo, hi)
        if rescaled < 0 or rescaled >= 1:
            known_rolls.append(None)
            continue
        known_rolls.append(bit_range(rescaled, 8))
        
    sol = solve_windowed(known_rolls)
    return sol

ATTR_ORDER_GEN = [
    "thwackability",
    "moxie",
    "divinity",
    "musclitude",
    "patheticism",
    "buoyancy",
    "baseThirst",
    "laserlikeness",
    "groundFriction",
    "continuation",
    "indulgence",
    "martyrdom",
    "tragicness",
    "shakespearianism",
    "suppression",
    "unthwackability",
    "coldness",
    "overpowerment",
    "ruthlessness",
    "omniscience",
    "tenaciousness",
    "watchfulness",
    "anticapitalism",
    "chasiness",
    "pressurization",
    # "cinnamon"
]



def handle_outcome(outcome: Outcome):
    # print(outcome.text)
    ht = outcome.update["data"]["homeTeam"]
    at = outcome.update["data"]["awayTeam"]
    htn = outcome.update["data"]["homeTeamNickname"]
    atn = outcome.update["data"]["awayTeamNickname"]

    game_start, game_end = game_bounds(outcome.game_id)

    if "their lineup shuffled" in outcome.text:
        target_team = ht if htn in outcome.text else at
        target_team_name = htn if htn in outcome.text else atn

        gd.fetch_teams(game_start, -60*5)
        team_before = gd.teams[target_team]
        gd.fetch_teams(game_end, 60*5)
        team_after = gd.teams[target_team]

        # print(team_before.lineup, team_after.lineup)
        assert team_before.lineup != team_after.lineup

        perm = get_permutation(team_before.lineup, team_after.lineup)
        return dict(type="reverb_lineup", team_id=target_team, permutation=perm)

        # print(outcome.text, target_team_name, perm)
    elif "their rotation shuffled" in outcome.text:
        target_team = ht if htn in outcome.text else at
        target_team_name = htn if htn in outcome.text else atn

        gd.fetch_teams(game_start, -60*5)
        team_before = gd.teams[target_team]
        gd.fetch_teams(game_end, 60*10)
        team_after = gd.teams[target_team]

        # print(team_before.lineup, team_after.lineup)
        assert team_before.rotation != team_after.rotation

        perm = get_permutation(team_before.rotation, team_after.rotation)

        return dict(type="reverb_rotation", team_id=target_team, permutation=perm)

    elif "were completely shuffled" in outcome.text or "had several players shuffled" in outcome.text:
        type = "completely" if "completely" in outcome.text else "several"

        target_team = ht if htn in outcome.text else at
        target_team_name = htn if htn in outcome.text else atn

        gd.fetch_teams(game_start, -60*5)
        team_before = gd.teams[target_team]
        gd.fetch_teams(game_end, 60*5)
        team_after = gd.teams[target_team]

        # print(team_before.lineup, team_after.lineup)
        # assert team_before.rotation != team_after.rotation

        roster_before = team_before.lineup + team_before.rotation
        roster_after = team_after.lineup + team_after.rotation
        assert roster_before != roster_after

        perm = get_permutation(roster_before, roster_after)
        return dict(type="reverb_full", team_id=target_team, permutation=perm)
    elif "is now Reverberating wildly" in outcome.text:
        pass
    elif "resists!" in outcome.text:
        immune_name = outcome.text.split("...but ")[1].split(" resists!")[0]
        source_name = outcome.text.split("resists! ")[1].split(" is affect")[0]

        immune = player_by_name(immune_name)
        source = player_by_name(source_name)
        return dict(type="feedback_failed", immune_player_id=immune.id, source_player_id=source.id)
    elif "is Red Hot!" in outcome.text:
        pass
    elif "is no longer Red Hot." in outcome.text:
        pass
    elif "switched teams in the feedback" in outcome.text:
        trimmed = outcome.text
        if "flickers! " in trimmed:
            trimmed = trimmed.split(" flickers! ")[1]

        player_a_name = trimmed.split(" and ")[0]
        player_b_name = trimmed.split(" and ")[1].split(" switched")[0]
        # print(outcome.text)

        gd.fetch_players(outcome.timestamp, -15)
        player_a = player_by_name(player_a_name)
        player_b = player_by_name(player_b_name)


        gd.fetch_teams(game_start, -60*3)
        ht_before, at_before = gd.teams[ht], gd.teams[at]
        gd.fetch_teams(game_end, 60*3)
        ht_after, at_after = gd.teams[ht], gd.teams[at]

        player_a_team = ht if player_a.id in (ht_before.lineup + ht_before.rotation) else at
        player_b_team = ht if player_b.id in (ht_before.lineup + ht_before.rotation) else at

        if "Eugenia Garbage and Simon Haley" in outcome.text:
            # dunno. special case.
            player_a_team = SHOE_THIEVES
            player_b_team = MOIST_TALKERS

        if "Eduardo Woodman and Alyssa Harrell" in outcome.text:
            # hardcoded
            if outcome.timestamp.startswith("2020-09-25T09:04"):
                player_a_team = PIES
                player_b_team = FRIDAYS
            elif outcome.timestamp.startswith("2020-09-25T09:12"):
                player_a_team = FRIDAYS
                player_b_team = PIES
        assert player_a_team != player_b_team

        gd.fetch_player_after(player_a.id, outcome.timestamp)
        gd.fetch_player_after(player_b.id, outcome.timestamp)
        player_a_after = gd.players[player_a.id]
        player_b_after = gd.players[player_b.id]

        res = dict(type="feedback", player_a_team=player_a_team, player_a_id=player_a.id, player_b_team=player_b_team, player_b_id=player_b.id)
        if player_a_after.data["fate"] != player_a.data["fate"]:
            res["player_a_fate"] = player_a_after.data["fate"]
            # print("!!! new fate")
        if player_b_after.data["fate"] != player_b.data["fate"]:
            res["player_b_fate"] = player_b_after.data["fate"]
            # print("!!! new fate")
        return res

    elif "is Partying!" in outcome.text:
        partying_player = outcome.text.split(" is Partying")[0]

        gd.fetch_teams(outcome.timestamp, -15)
        gd.fetch_players(outcome.timestamp, -15)
        player = player_by_name(partying_player)

        team = player_team(player.id, [ht, at])

        gd.fetch_player_after(player.id, outcome.timestamp)
        player_after = gd.players[player.id]

        stat_order = DEFENSE_ATTR_BLOCK + PITCHING_ATTR_BLOCK + BASERUNNING_ATTR_BLOCK + BATTING_ATTR_BLOCK + ["cinnamon"]

        season = outcome.update["data"]["season"]

        if season == 6:
            lohi = (0.06, 0.1)
            if team.id == DALE:
                lohi = lohi[0]*1.1, lohi[1]*1.1
        else:
            lohi = 0.04, 0.08
            if team.id == DALE:
                lohi = lohi[0]*1.1, lohi[1]*1.1

        # diffs = []
        for s in stat_order:
            bef = player.data[s]
            aft = player_after.data[s]
            # diff = aft-bef
        # diffs = [player_after.data[s] - player.data[s] for s in stat_order]
        # print()
        # print("party solving", player.name, lohi)
        sol = solve_diff(player, player_after, lohi, stat_order)
        if sol:
            r = Rng.parse(sol)
            r.step(-1)
            lo, hi = lohi
            for attr in stat_order:
                val = r.next() * (hi-lo) + lo
                if attr in ["tragicness", "patheticism"]:
                    new_value = player.data[attr] - val
                else:
                    new_value = player.data[attr] + val

                guess_diff = new_value - player.data[attr]
                real_diff = player_after.data[attr] - player.data[attr]
                # if real_diff != guess_diff:
                    # print(f"!!! mismatch: {player.name} {attr}, rolled {val}, got {real_diff}")

        # if sol:
        #     print(sol)
        # else:
        #     print("!!! no sol found")
        return dict(type="party", team_id=team.id, player_id=player.id, seed=sol)

        # print(outcome.text, player.name, team.nickname)
    elif "Blooddrain gurgled!" in outcome.text:
        sipper_name = outcome.text.split("gurgled! ")[1].split(" siphoned ")[0]
        sippee_name = outcome.text.split("siphoned some of ")[1].split("'s")[0]

        gd.fetch_players(outcome.timestamp, -15)
        gd.fetch_teams(outcome.timestamp, -15)

        sipper = player_by_name(sipper_name)
        sippee = player_by_name(sippee_name)

        sipper_team = player_team(sipper.id, [ht, at])
        sippee_team = player_team(sippee.id, [ht, at])
        assert sipper_team.id != sippee_team.id
        assert sipper_team.id in [ht, at]
        assert sippee_team.id in [ht, at]

        ability = outcome.text.split("'s ")[1].split(" ability!")[0]

        return dict(type="blooddrain", category=ability, sippee_team_id=sippee_team.id, sipper_team_id=sipper_team.id, sipper_id=sipper.id, sippee_id=sippee.id)
    elif "with a pitch!" in outcome.text:
        pitcher_name = outcome.text.split(" hits ")[0]
        target_name = outcome.text.split(" hits ")[1].split(" with a pitch!")[0]

        gd.fetch_players(outcome.timestamp, -15)
        gd.fetch_teams(outcome.timestamp, -15)
        pitcher = player_by_name(pitcher_name)
        target = player_by_name(target_name)

        res = dict(type="hbp", pitcher_id=pitcher.id, target_id=target.id)
        return res
            # t(pitcher.name, target.name)
    # elif "A Debt was collected." in outcome.text:
    #     print(outcome.text)
    #     pass
    elif "Rogue Umpire incinerated" in outcome.text:
        was_debt = "A Debt was collected" in outcome.text
        if " hitter " in outcome.text:
            target_name = outcome.text.split(" hitter ")[1].split("!")[0]
            target_team_name = outcome.text.split(" hitter ")[0].split("incinerated ")[1]
        elif " pitcher " in outcome.text:
            target_name = outcome.text.split(" pitcher ")[1].split("!")[0]
            target_team_name = outcome.text.split(" pitcher ")[0].split("incinerated ")[1]
        new_player_name = outcome.text.split("Replaced by ")[1]

        gd.fetch_players(outcome.timestamp, -15)
        gd.fetch_teams(outcome.timestamp, -15)
        target = player_by_name(target_name)
        target_team = player_team(target.id, [ht, at])
        assert target_team_name == target_team.nickname

        gd.fetch_players(outcome.timestamp, 60*60)
        new_player_id = player_by_name(new_player_name).id
        gd.fetch_player_after(new_player_id, outcome.timestamp)
        new_player = gd.players[new_player_id]

        known_rolls = [new_player.data[k] for k in ATTR_ORDER_GEN]
        sol = solve_windowed(known_rolls)
        if sol:
            rng = Rng.parse(sol)
            rng.step(-3)
            seed, offset = rng.find_seed()
            sol = seed_str(seed, offset)

        # print(outcome.update["lastUpdate"])
        lu = outcome.update["data"]["lastUpdate"]
        res = dict(type="incineration", was_debt=was_debt, target_team_id=target_team.id, target_id=target.id, replacement_id=new_player.id, replacement_name=new_player.name, seed=sol)
        if "The Instability" in lu:
            chain_team_name = lu.split(" to the ")[1].split("'s")[0]
            chain_player_name = lu.split("'s ")[-1].split("!")[0]
            # print(chain_player_name)
            chain_player = player_by_name(chain_player_name)
            chain_team = player_team(chain_player.id, [ht, at])
            assert chain_team.nickname == chain_team_name
            # print("chain", chain_team.nickname, chain_player.name)

            res["instability_chain_team_id"] = chain_team.id
            res["instability_chain_player_id"] = chain_player.id
        # print("NORMAL INCIN", target.name, target_team.nickname, new_player.name, sol)
        return res
    elif "The Instability chains" in outcome.text or "The Instability spreads" in outcome.text:
        pass
    elif "The Birds pecked" in outcome.text:
        target_name = outcome.text.split(" pecked ")[1].split(" free!")[0]
        player = player_by_name(target_name)
        team = player_team(player.id, [ht, at])
        return dict(type="pecked_free", player_id=player.id, team_id=team.id)
        # literally once
        pass
    elif "swallowed a stray Peanut" in outcome.text:
        gd.fetch_teams(outcome.timestamp)
        
        assert htn in outcome.text or atn in outcome.text
        if " hitter " in outcome.text:
            player_name = outcome.text.split(" hitter ")[1].split(" swallowed")[0]
        elif " pitcher " in outcome.text:
            player_name = outcome.text.split(" pitcher ")[1].split(" swallowed")[0]

        type = "peanut_yummy" if "yummy reaction" in outcome.text else "peanut_allergic"

        gd.fetch_players(outcome.timestamp, -15)
        player = player_by_name(player_name)
        team = player_team(player.id, [ht, at])

        return dict(type=type, player_id=player.id, team_id=team.id)
    elif "but they're Fireproof!" in outcome.text:
        player_name = outcome.text.split(" hitter ")[1].split(", ")[0]
        player = player_by_name(player_name)

        return dict(type="fireproof", player_id=player.id)
    elif "A Big Peanut " in outcome.text:
        player_name = outcome.text.split(" encasing ")[1].split("!")[0]
        player = player_by_name(player_name)
        return dict(type="encased", player_id=player.id)
    else:
        pass
        print("!!!!!", outcome.text)
    pass

outcome_jsons = []
for season in [8]:
    season_games = [g for g in all_games if g["data"]["season"] == season]
    # season_games = [g for g in season_games if g["gameId"] == "b9a32210-3598-4650-8a4d-7c443733f2c3"]

    for game in season_games:
        for outcome in find_game_outcomes(game["gameId"]):
            res = handle_outcome(outcome)
            if res:
                res["game_id"] = outcome.game_id
                res["timestamp"] = outcome.timestamp
                res["season"] = outcome.update["data"]["season"]
                res["day"] = outcome.update["data"]["day"]
                res["outcome_text"] = outcome.text
                outcome_jsons.append(res)

outcome_jsons = sorted(outcome_jsons, key=lambda x: x["timestamp"])

import json
print(json.dumps(outcome_jsons, indent=4))
# for out in outcome_jsons:
#     print(json.dumps(out))
                