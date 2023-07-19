from data import Mod, ModType, PlayerData, TeamData, StadiumData, Weather
import itertools
from dataclasses import dataclass


@dataclass
class StatRelevantData:
    weather: Weather
    season: int
    day: int
    runner_count: int
    top_of_inning: bool
    is_maximum_blaseball: bool
    batter_at_bats: int


def get_multiplier(player: PlayerData, team: TeamData, position: str, attr: str, meta: StatRelevantData):
    multiplier = 1
    for mod in itertools.chain(player.mods, team.mods):
        mod = Mod.coerce(mod)
        if mod == Mod.LATE_TO_PARTY:
            # fix for late to party silently activating...
            if meta.day == 72:
                # print(meta.day, team.mods, player.mods)
                if not team.has_mod(Mod.OVERPERFORMING):
                    # print("adding multiplier")
                    multiplier += 0.2
        if mod == Mod.OVERPERFORMING:
            multiplier += 0.2
        elif mod == Mod.UNDERPERFORMING:
            multiplier -= 0.2
        elif mod == Mod.GROWTH:
            # todo: do we ever want this for other positions?
            if attr not in [
                # still not sure what's up with those. swing on strikes s16+ requires them to be applied
                "patheticism" if meta.season < 15 else None,
                "thwackability" if meta.season < 15 else None,
                "buoyancy" if meta.season < 15 else None,
                # todo: when did they fix this? i think it's s19, right
                "ruthlessness" if meta.season < 15 else None,
            ]:  # , "ruthlessness"]:  #, "coldness"]:
                multiplier += min(0.05, 0.05 * (meta.day / 99))
        elif mod == Mod.HIGH_PRESSURE:
            # checks for flooding weather and baserunners
            if meta.weather == Weather.FLOODING and meta.runner_count > 0:
                # "won't this stack with the overperforming mod it gives the team" yes. yes it will.
                # "should we really boost the pitcher when the *other* team's batters are on base" yes.
                multiplier += 0.25
        elif mod == Mod.TRAVELING and not player.has_mod(Mod.TRAVELING):
            # ^^^ this gets rid of one outlier for triples (7750cd54-34a4-4cbe-8781-5fc8eaff16d3/108) where Don Mitchell has the traveling item mod
            # still unsure if traveling as a personal mod never applies, or only if it's specifically an item mod... more research needed :p
            if (meta.top_of_inning and position == "batter") or (not meta.top_of_inning and position == "pitcher"):
                if attr not in [
                    "patheticism",
                    "thwackability",
                    "ruthlessness",
                    "coldness",
                    "buoyancy",
                ]:
                    multiplier += 0.05

            if (not meta.top_of_inning) and position == "fielder":
                multiplier += 0.05
                pass

            # todo: do we ever want this?
            # elif not top_of_inning and position in ["fielder", "pitcher"]:
            # multiplier += 0.05
        elif mod == Mod.SINKING_SHIP:
            roster_size = len(team.lineup) + len(team.rotation)

            if attr not in []:
                multiplier += (14 - roster_size) * 0.01
        elif mod == Mod.AFFINITY_FOR_CROWS and meta.weather == Weather.BIRDS:
            # ???
            # i *believe* this consistently does not apply to fielders
            # so really the omni check is about excluding fielders and not excluding omni
            if position != "fielder" and attr not in ["buoyancy", "omniscience"]:
                multiplier += 0.5
        elif mod == Mod.CHUNKY and meta.weather == Weather.PEANUTS:
            # todo: handle carefully! historical blessings boosting "power" (Ooze, S6) boosted groundfriction
            #  by half of what the other two attributes got. (+0.05 instead of +0.10, in a "10% boost")
            # gfric boost hasn't been "tested" necessarily
            if attr in ["musclitude", "divinity"]:
                multiplier += 1.0
            elif attr in ["ground_friction", "groundFriction"]:  # todo: be consistent here
                multiplier += 0.5
        elif mod == Mod.SMOOTH and meta.weather == Weather.PEANUTS:
            # todo: handle carefully! historical blessings boosting "speed" (Spin Attack, S6) boosted everything in
            #  strange ways: for a "15% boost", musc got +0.0225, cont and gfric got +0.075, laser got +0.12.
            # the musc boost here has been "tested in the data", the others have not
            if attr == "musclitude":
                multiplier += 0.15
            elif attr == "continuation":
                multiplier += 0.50
            elif attr in ["ground_friction", "groundFriction"]:
                multiplier += 0.50
            elif attr == "laserlikeness":
                multiplier += 0.80
        elif mod == Mod.ON_FIRE:
            # still some room for error here (might include gf too)
            if attr == "thwackability":
                multiplier += 4 if meta.season >= 13 else 3
            if attr == "moxie":
                multiplier += 2 if meta.season >= 13 else 1
        elif mod == Mod.MINIMALIST:
            if meta.is_maximum_blaseball:
                multiplier -= 0.75
        elif mod == Mod.MAXIMALIST:
            # not "seen in the data" yet
            if meta.is_maximum_blaseball:
                multiplier += 2.50
        elif mod == Mod.SLOW_BUILD and position == "batter":
            # guessing at how this works
            multiplier += meta.batter_at_bats * 0.01
        elif mod == Mod.SHELLED and position == "fielder":
            # lol
            return 0

    if player.bat == "NIGHT_VISION_GOGGLES" and meta.weather == Weather.ECLIPSE:
        # Blessing description: Item. Random player on your team hits 50% better during Solar Eclipses.
        if attr == "thwackability":
            multiplier += 0.5
    return multiplier


def get_strike_threshold(
    batter: PlayerData,
    batting_team: TeamData,
    pitcher: PlayerData,
    pitching_team: TeamData,
    stadium: StadiumData,
    meta: StatRelevantData,
    is_flinching: bool,
):
    vibes = pitcher.vibes(meta.day)
    ruth = pitcher.multiplied("ruthlessness", get_multiplier(pitcher, pitching_team, "pitcher", "ruthlessness", meta))

    # todo: do this to the rest?
    cold = pitcher.multiplied("coldness", get_multiplier(pitcher, pitching_team, "pitcher", "coldness", meta))
    musc = batter.multiplied("musclitude", get_multiplier(batter, batting_team, "batter", "musclitude", meta))
    mox = batter.multiplied("moxie", get_multiplier(batter, batting_team, "batter", "moxie", meta))
    fwd = stadium.forwardness

    batter_hype = stadium.hype if not meta.top_of_inning else 0
    pitcher_hype = stadium.hype if meta.top_of_inning else 0
    hypediff = pitcher_hype - batter_hype

    # fmt: off
    constant, ruth_factor, fwd_factor, musc_factor, mox_factor, abs_factor, roll_cap = {
        11: (0.2,  0.35,    0.2,   0.1,    0,   0,  0.9),
        12: (0.2,  0.3,     0.2,   0.1,    0,   0,  0.85),
        13: (0.2,  0.3,     0.2,   0.1,    0,   0,  0.85),
        14: (0.2,  0.285,   0.2,   0.1,    0,   0,  0.86),
        15: (0.2,  0.285,   0.2,   0.1,    0,   0,  0.86),  # todo: not sure but seems right
        16: (0.2,  0.285,   0.2,   0.1,    0,   0,  0.86),  # todo: not sure but seems right
        17: (0.2,  0.285,   0.2,   0.1,    0,   0,  0.86),  # todo: not sure but seems right
        18: (0.25, 0.285,   0.2, 0.085, -0.085, -0.035,  0.86),  # todo: a solid starter guess
    }[meta.season]
    # fmt: on

    if is_flinching:
        constant += 0.2

    if meta.season >= 18:
        threshold = (
            (constant if fwd < 0.5 else constant + 0.05)
            + ruth_factor * ((10 * ruth + 1 * cold) / 11 + 0.2 * hypediff) * (1 + 0.2 * vibes)
            + (fwd_factor * fwd if fwd < 0.5 else (fwd_factor - 0.1) * fwd)
            + musc_factor * musc
            + mox_factor * mox
            + abs_factor * abs(musc - mox)
        )
    else:
        threshold = constant + ruth_factor * (ruth * (1 + 0.2 * vibes)) + fwd_factor * fwd + musc_factor * musc
    threshold = min(threshold, roll_cap)
    return threshold


def get_swing_strike_threshold(
    batter: PlayerData,
    batting_team: TeamData,
    pitcher: PlayerData,
    pitching_team: TeamData,
    stadium: StadiumData,
    meta: StatRelevantData,
):
    batter_vibes = batter.vibes(meta.day)
    pitcher_vibes = pitcher.vibes(meta.day)

    hype = stadium.hype * (1 if meta.top_of_inning else -1)
    batter_hype = -hype * (1 + 0.2 * batter_vibes)
    pitcher_hype = hype * (1 + 0.2 * pitcher_vibes)

    div = batter.multiplied("divinity", get_multiplier(batter, batting_team, "batter", "divinity", meta)) * (
        1 + 0.2 * batter_vibes
    )
    musc = batter.multiplied("musclitude", get_multiplier(batter, batting_team, "batter", "musclitude", meta)) * (
        1 + 0.2 * batter_vibes
    )
    thwack = batter.multiplied(
        "thwackability", get_multiplier(batter, batting_team, "batter", "thwackability", meta)
    ) * (1 + 0.2 * batter_vibes)
    path = batter.multiplied("patheticism", 1 / get_multiplier(batter, batting_team, "batter", "patheticism", meta))
    invpath = (1 - path) * (1 + 0.2 * batter_vibes)

    ruth = pitcher.multiplied(
        "ruthlessness", get_multiplier(pitcher, pitching_team, "pitcher", "ruthlessness", meta)
    ) * (1 + 0.2 * pitcher_vibes)

    visc = stadium.viscosity

    combined_batting = (div + musc + invpath + thwack) / 4
    if meta.season < 18:
        threshold = 0.7 + 0.35 * combined_batting - 0.4 * ruth + 0.2 * (visc - 0.5)
    else:
        threshold = (
            0.6 + 0.35 * (combined_batting + 0.2 * batter_hype) - 0.2 * (ruth + 0.2 * pitcher_hype) + 0.2 * (visc - 0.5)
        )
    return threshold


def get_swing_ball_threshold(
    batter: PlayerData,
    batting_team: TeamData,
    pitcher: PlayerData,
    pitching_team: TeamData,
    stadium: StadiumData,
    meta: StatRelevantData,
):
    batter_vibes = batter.vibes(meta.day)
    pitcher_vibes = pitcher.vibes(meta.day)

    moxie = batter.multiplied("moxie", get_multiplier(batter, batting_team, "batter", "moxie", meta)) * (
        1 + 0.2 * batter_vibes
    )
    path = batter.multiplied("patheticism", 1 / get_multiplier(batter, batting_team, "batter", "patheticism", meta))
    ruth = pitcher.multiplied(
        "ruthlessness", get_multiplier(pitcher, pitching_team, "pitcher", "ruthlessness", meta)
    ) * (1 + 0.2 * pitcher_vibes)
    visc = stadium.viscosity

    if meta.season < 18:
        combined = (12 * ruth - 5 * moxie + 5 * path + 4 * visc) / 20
    else:
        # this has some outliers even without hype, not sure what's up with it
        # with hype it's hopeless :)
        combined = 0.375 * (ruth**0.25) + 0.2 * visc - 0.25 * moxie + 0.25 * path

    if combined < 0:
        return float("nan")

    threshold = max(min(combined**1.5, 0.95), 0.1)
    return threshold


def get_contact_strike_threshold(
    batter: PlayerData,
    batting_team: TeamData,
    pitcher: PlayerData,
    pitching_team: TeamData,
    stadium: StadiumData,
    meta: StatRelevantData,
):
    batter_vibes = batter.vibes(meta.day)
    pitcher_vibes = pitcher.vibes(meta.day)

    div = batter.multiplied("divinity", get_multiplier(batter, batting_team, "batter", "divinity", meta))
    musc = batter.multiplied("musclitude", get_multiplier(batter, batting_team, "batter", "musclitude", meta))
    thwack = batter.multiplied("thwackability", get_multiplier(batter, batting_team, "batter", "thwackability", meta))
    path = batter.multiplied("patheticism", 1 / get_multiplier(batter, batting_team, "batter", "patheticism", meta))
    combined_batting = (div + musc + thwack - path) / 2 * (1 + 0.2 * batter_vibes)
    if combined_batting < 0:
        return float("nan")  # hi caleb

    ruth = pitcher.multiplied(
        "ruthlessness", get_multiplier(pitcher, pitching_team, "pitcher", "ruthlessness", meta)
    ) * (1 + 0.2 * pitcher_vibes)

    fort = stadium.fortification - 0.5
    visc = stadium.viscosity - 0.5
    fwd = stadium.forwardness - 0.5
    ballpark_sum = (fort + 3 * visc - 6 * fwd) / 10

    constant, batting_factor, cap = {
        11: (0.8, 0.16, 0.9),
        12: (0.8, 0.16, 0.9),
        13: (0.8, 0.16, 0.9),
        14: (0.78, 0.17, 0.925),
        15: (0.78, 0.17, 0.925),  # todo: we don't know
        16: (0.78, 0.17, 0.925),  # todo: we don't know
        17: (0.78, 0.17, 0.925),  # todo: we don't know
        18: (0.78, 0.17, 0.925),  # todo: we don't know
    }[meta.season]

    threshold = constant - 0.08 * ruth + 0.16 * ballpark_sum + batting_factor * (combined_batting**1.2)
    return min(cap, threshold)


def get_contact_ball_threshold(
    batter: PlayerData,
    batting_team: TeamData,
    pitcher: PlayerData,
    pitching_team: TeamData,
    stadium: StadiumData,
    meta: StatRelevantData,
):
    batter_vibes = batter.vibes(meta.day)
    pitcher_vibes = pitcher.vibes(meta.day)

    path = batter.multiplied("patheticism", 1 / get_multiplier(batter, batting_team, "batter", "patheticism", meta))
    invpath = max(
        (1 - path) * (1 + 0.2 * batter_vibes),
        0,
    )

    ruth = pitcher.multiplied(
        "ruthlessness", get_multiplier(pitcher, pitching_team, "pitcher", "ruthlessness", meta)
    ) * (1 + 0.2 * pitcher_vibes)

    fort = stadium.fortification - 0.5
    visc = stadium.viscosity - 0.5
    fwd = stadium.forwardness - 0.5
    ballpark_sum = (fort + 3 * visc - 6 * fwd) / 10

    constant, path_factor, cap = {
        11: (0.35, 0.4, 1),
        12: (0.35, 0.4, 1),
        13: (0.4, 0.35, 1),
        14: (0.4, 0.35, 1),
        15: (0.4, 0.35, 1),  # todo: we don't know
        16: (0.4, 0.35, 1),  # todo: we don't know
        17: (0.4, 0.35, 1),  # todo: we don't know
        18: (0.4, 0.35, 1),  # todo: we don't know
    }[meta.season]

    threshold = constant - 0.1 * ruth + path_factor * (invpath**1.5) + 0.14 * ballpark_sum
    return min(cap, threshold)


def get_foul_threshold(
    batter: PlayerData,
    batting_team: TeamData,
    stadium: StadiumData,
    meta: StatRelevantData,
):
    vibes = batter.vibes(meta.day)
    fwd = stadium.forwardness
    obt = stadium.obtuseness
    musc = batter.multiplied("musclitude", get_multiplier(batter, batting_team, "batter", "musclitude", meta)) * (
        1 + 0.2 * vibes
    )
    thwack = batter.multiplied(
        "thwackability", get_multiplier(batter, batting_team, "batter", "thwackability", meta)
    ) * (1 + 0.2 * vibes)
    div = batter.multiplied("divinity", get_multiplier(batter, batting_team, "batter", "divinity", meta)) * (
        1 + 0.2 * vibes
    )
    batter_sum = (musc + thwack + div) / 3

    batter_hype = stadium.hype if not meta.top_of_inning else 0
    pitcher_hype = stadium.hype if meta.top_of_inning else 0
    hypediff = (batter_hype - pitcher_hype) * (1 + 0.2 * vibes)

    threshold = 0.25 + 0.1 * fwd - 0.1 * obt + 0.1 * batter_sum + 0.02 * hypediff
    return threshold


def get_hr_threshold(
    batter: PlayerData,
    batting_team: TeamData,
    pitcher: PlayerData,
    pitching_team: TeamData,
    stadium: StadiumData,
    meta: StatRelevantData,
):
    batter_vibes = batter.vibes(meta.day)
    pitcher_vibes = pitcher.vibes(meta.day)

    div = batter.multiplied("divinity", get_multiplier(batter, batting_team, "batter", "divinity", meta)) * (
        1 + 0.2 * batter_vibes
    )
    opw = pitcher.multiplied(
        "overpowerment", get_multiplier(pitcher, pitching_team, "pitcher", "overpowerment", meta)
    ) * (1 + 0.2 * pitcher_vibes)
    supp = pitcher.multiplied("suppression", get_multiplier(pitcher, pitching_team, "pitcher", "suppression", meta)) * (
        1 + 0.2 * pitcher_vibes
    )

    grand = stadium.grandiosity - 0.5
    fort = stadium.fortification - 0.5
    visc = stadium.viscosity - 0.5
    om = stadium.ominousness - 0.5
    fwd = stadium.forwardness - 0.5
    ballpark_sum = 0.4 * grand + 0.2 * fort + 0.08 * visc + 0.08 * om - 0.24 * fwd

    opw_supp = (10 * opw + supp) / 11
    threshold = 0.12 + 0.16 * div - 0.08 * opw_supp - 0.18 * ballpark_sum
    return threshold


def get_fly_or_ground_threshold(
    batter: PlayerData,
    batting_team: TeamData,
    pitcher: PlayerData,
    pitching_team: TeamData,
    stadium: StadiumData,
    meta: StatRelevantData,
):
    # no vibes, flipped for some reason?
    buoy = batter.multiplied("buoyancy", 1 / get_multiplier(batter, batting_team, "batter", "buoyancy", meta))

    # note: passing the *batter* as the player and the *pitching team* as the team
    # this is as weird as it sounds. we can only assume tgb accidentally passed the wrong player in or something
    # since we use the batter suppression even if it makes more sense to use *pitcher* suppression here
    supp = batter.multiplied("suppression", get_multiplier(batter, pitching_team, "pitcher", "suppression", meta))
    omi = stadium.ominousness - 0.5

    # applying hype this way works and i don't know why
    hype = stadium.hype * (1 if meta.top_of_inning else -1)

    threshold = 0.18 + 0.3 * (buoy + 0.2 * hype) - 0.16 * (supp + 0.2 * hype) - 0.1 * omi
    return max(threshold, 0.01)  # todo: 0.01 might be 0.033?


def get_out_threshold(
    batter: PlayerData,
    batting_team: TeamData,
    pitcher: PlayerData,
    pitching_team: TeamData,
    fielder: PlayerData,
    stadium: StadiumData,
    meta: StatRelevantData,
):
    batter_vibes = batter.vibes(meta.day)
    pitcher_vibes = pitcher.vibes(meta.day)
    fielder_vibes = fielder.vibes(meta.day)

    batter_thwack = batter.multiplied(
        "thwackability", get_multiplier(batter, batting_team, "batter", "thwackability", meta)
    ) * (1 + 0.2 * batter_vibes)
    pitcher_unthwack = pitcher.multiplied(
        "unthwackability", get_multiplier(pitcher, pitching_team, "pitcher", "unthwackability", meta)
    ) * (1 + 0.2 * pitcher_vibes)
    fielder_omni = fielder.multiplied(
        "omniscience", get_multiplier(fielder, pitching_team, "fielder", "omniscience", meta)
    ) * (1 + 0.2 * fielder_vibes)

    grand = stadium.grandiosity - 0.5
    omi = stadium.ominousness - 0.5
    incon = stadium.inconvenience - 0.5
    visc = stadium.viscosity - 0.5
    fwd = stadium.forwardness - 0.5
    obt = stadium.obtuseness - 0.5

    if meta.season in [11, 12]:
        # 4 outliers on this dataset
        return (
            0.315
            + 0.1 * batter_thwack
            - 0.08 * pitcher_unthwack
            - 0.07 * fielder_omni
            + 0.0145 * grand
            + 0.0085 * omi
            - 0.011 * incon
            - 0.005 * visc
            + 0.01 * fwd
        )
    elif meta.season == 13:
        return (
            0.3115
            + 0.1 * batter_thwack
            - 0.08 * pitcher_unthwack
            - 0.065 * fielder_omni
            + 0.011 * grand
            + 0.008 * obt
            - 0.0033 * omi
            - 0.002 * incon
            - 0.0033 * visc
            + 0.01 * fwd
        )
    else:
        # works s15-s18, but i'm not happy with the coefficients on the ballpark stuff at all
        # this sucks. they don't even sum to 100
        bp_sum = (55 * grand + 51 * fwd + 40 * obt - 17 * visc - 17 * omi - 10 * incon) / 100
        return 0.311 + 0.1 * batter_thwack - 0.08 * pitcher_unthwack - 0.064 * fielder_omni + 0.02 * bp_sum


def get_double_threshold(
    batter: PlayerData,
    batting_team: TeamData,
    pitcher: PlayerData,
    pitching_team: TeamData,
    fielder: PlayerData,
    stadium: StadiumData,
    meta: StatRelevantData,
):
    batter_vibes = batter.vibes(meta.day)
    pitcher_vibes = pitcher.vibes(meta.day)
    fielder_vibes = fielder.vibes(meta.day)

    batter_musc = batter.multiplied(
        "musclitude", get_multiplier(batter, batting_team, "batter", "musclitude", meta)
    ) * (1 + 0.2 * batter_vibes)
    pitcher_opw = pitcher.multiplied(
        "overpowerment", get_multiplier(pitcher, pitching_team, "pitcher", "overpowerment", meta)
    ) * (1 + 0.2 * pitcher_vibes)
    fielder_chase = fielder.multiplied(
        "chasiness", get_multiplier(fielder, pitching_team, "fielder", "chasiness", meta)
    ) * (1 + 0.2 * fielder_vibes)

    fwd = stadium.forwardness - 0.5
    elong = stadium.elongation - 0.5
    visc = stadium.viscosity - 0.5
    omi = stadium.ominousness - 0.5

    ballpark_sum = 0.027 * fwd - 0.015 * elong - 0.01 * omi - 0.008 * visc

    if meta.season in [11, 12]:
        return 0.17 + 0.2 * batter_musc - 0.04 * pitcher_opw - 0.1 * fielder_chase + ballpark_sum
    elif meta.season == 13:
        return 0.165 + 0.2 * batter_musc - 0.04 * pitcher_opw - 0.09 * fielder_chase + ballpark_sum
    else:
        # accurate up to s18 at least
        return 0.16 + 0.2 * batter_musc - 0.04 * pitcher_opw - 0.08 * fielder_chase + ballpark_sum


def get_triple_threshold(
    batter: PlayerData,
    batting_team: TeamData,
    pitcher: PlayerData,
    pitching_team: TeamData,
    fielder: PlayerData,
    stadium: StadiumData,
    meta: StatRelevantData,
):
    batter_vibes = batter.vibes(meta.day)
    pitcher_vibes = pitcher.vibes(meta.day)
    fielder_vibes = fielder.vibes(meta.day)

    hype = stadium.hype * (1 if meta.top_of_inning else -1)

    batter_gf = batter.multiplied(
        "ground_friction", get_multiplier(batter, batting_team, "batter", "ground_friction", meta)
    )
    batter_gf = (batter_gf - 0.2 * hype) * (1 + 0.2 * batter_vibes)

    pitcher_opw = pitcher.multiplied(
        "overpowerment", get_multiplier(pitcher, pitching_team, "pitcher", "overpowerment", meta)
    )
    pitcher_opw = (pitcher_opw + 0.2 * hype) * (1 + 0.2 * pitcher_vibes)

    fielder_chase = fielder.multiplied(
        "chasiness", get_multiplier(fielder, pitching_team, "fielder", "chasiness", meta)
    )
    fielder_chase = (fielder_chase + 0.2 * hype) * (1 + 0.2 * fielder_vibes)

    fwd = stadium.forwardness - 0.5
    grand = stadium.grandiosity - 0.5
    obt = stadium.obtuseness - 0.5
    visc = stadium.viscosity - 0.5
    omi = stadium.ominousness - 0.5

    ballpark_sum = (3 * fwd + 5 * grand + 5 * obt - visc - omi) / 15

    if meta.season in [11, 12]:
        return 0.05 + 0.2 * batter_gf - 0.04 * pitcher_opw - 0.06 * fielder_chase + 0.1 * ballpark_sum
    elif meta.season in [13, 14, 15, 16, 17]:
        return 0.045 + 0.2 * batter_gf - 0.04 * pitcher_opw - 0.05 * fielder_chase + 0.1 * ballpark_sum
    else:
        if pitcher_opw < 0:
            # ...did this ever happen?
            return float("nan")
        opw_pow = pitcher_opw**1.5
        return 0.042 + 0.2 * batter_gf - 0.056 * opw_pow - 0.05 * fielder_chase + 0.1 * ballpark_sum
