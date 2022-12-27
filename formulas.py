from data import Mod, PlayerData, TeamData, StadiumData, Weather
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
                multiplier += 0.2
        if mod == Mod.OVERPERFORMING:
            multiplier += 0.2
        elif mod == Mod.UNDERPERFORMING:
            multiplier -= 0.2
        elif mod == Mod.GROWTH:
            # todo: do we ever want this for other positions?
            if attr not in ["patheticism", "thwackability"]:  # , "ruthlessness"]:  #, "coldness"]:
                multiplier += min(0.05, 0.05 * (meta.day / 99))
        elif mod == Mod.HIGH_PRESSURE:
            # checks for flooding weather and baserunners
            if meta.weather == "Weather.FLOODING" and meta.runner_count > 0:
                # "won't this stack with the overperforming mod it gives the team" yes. yes it will.
                # "should we really boost the pitcher when the *other* team's batters are on base" yes.
                multiplier += 0.25
        elif mod == Mod.TRAVELING:
            if (meta.top_of_inning and position == "batter") or (not meta.top_of_inning and position == "pitcher"):
                if attr not in ["patheticism", "thwackability", "ruthlessness", "coldness"]:
                    multiplier += 0.05

            # todo: do we ever want this?
            # elif not top_of_inning and position in ["fielder", "pitcher"]:
            # multiplier += 0.05
        elif mod == Mod.SINKING_SHIP:
            roster_size = len(team.lineup) + len(team.rotation)

            if attr not in []:
                multiplier += (14 - roster_size) * 0.01
        elif mod == Mod.AFFINITY_FOR_CROWS and meta.weather == "Weather.BIRDS":
            multiplier += 0.5
        elif mod == Mod.CHUNKY and meta.weather == "Weather.PEANUTS":
            # todo: handle carefully! historical blessings boosting "power" (Ooze, S6) boosted groundfriction
            #  by half of what the other two attributes got. (+0.05 instead of +0.10, in a "10% boost")
            # gfric boost hasn't been "tested" necessarily
            if attr in ["musclitude", "divinity"]:
                multiplier += 1.0
            elif attr == "ground_friction":
                multiplier += 0.5
        elif mod == Mod.SMOOTH and meta.weather == "Weather.PEANUTS":
            # todo: handle carefully! historical blessings boosting "speed" (Spin Attack, S6) boosted everything in
            #  strange ways: for a "15% boost", musc got +0.0225, cont and gfric got +0.075, laser got +0.12.
            # the musc boost here has been "tested in the data", the others have not
            if attr == "musclitude":
                multiplier += 0.15
            elif attr == "continuation":
                multiplier += 0.50
            elif attr == "ground_friction":
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

    if player.bat == "NIGHT_VISION_GOGGLES" and meta.weather == "Weather.ECLIPSE":
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
    ruth = pitcher.ruthlessness * get_multiplier(pitcher, pitching_team, "pitcher", "ruthlessness", meta)
    cold = pitcher.coldness * get_multiplier(pitcher, pitching_team, "pitcher", "coldness", meta)
    musc = batter.musclitude * get_multiplier(batter, batting_team, "batter", "musclitude", meta)
    mox = batter.moxie * get_multiplier(batter, batting_team, "batter", "moxie", meta)
    fwd = stadium.forwardness

    batter_hype = stadium.hype if not meta.top_of_inning else 0
    pitcher_hype = stadium.hype if meta.top_of_inning else 0

    # fmt: off
    constant, ruth_factor, cold_factor, fwd_factor, musc_factor, mox_factor, abs_factor, roll_cap = {
        11: (0.2,  0.35,  0,    0.2,   0.1,    0,   0,  0.9),
        12: (0.2,  0.3,   0,    0.2,   0.1,    0,   0,  0.85),
        13: (0.2,  0.3,   0,    0.2,   0.1,    0,   0,  0.85),
        14: (0.2,  0.285, 0,    0.2,   0.1,    0,   0,  0.86),
        15: (0.2,  0.285, 0,    0.2,   0.1,    0,   0,  0.86),  # todo: not sure but seems right
        16: (0.2,  0.285, 0,    0.2,   0.1,    0,   0,  0.86),  # todo: not sure but seems right
        17: (0.2,  0.285, 0,    0.2,   0.1,    0,   0,  0.86),  # todo: not sure but seems right
        18: (0.25, 0.285*10/11, 0.285/11, 0.2, 0.085, -0.085, -0.035,  0.86),  # todo: a solid starter guess
    }[meta.season]
    # fmt: on

    if is_flinching:
        constant += 0.2

    if meta.season >= 18:
        threshold = (
                (constant if fwd < 0.5 else constant + 0.05)
                + ruth_factor * (ruth * (1 + 0.2 * vibes))
                + cold_factor * (cold * (1 + 0.2 * vibes))
                + (fwd_factor * fwd if fwd < 0.5 else (fwd_factor - 0.1) * fwd)
                + musc_factor * musc
                + mox_factor * mox
                + abs_factor * abs(musc - mox)
                + 0.06 * pitcher_hype * (1 + 0.2 * vibes)
                - 0.06 * batter_hype * (1 + 0.2 * vibes)
        )
    else:
        threshold = (
            constant
            + ruth_factor * (ruth * (1 + 0.2 * vibes))
            # + cold_factor * (cold * (1 + 0.2 * vibes))
            + fwd_factor * fwd
            + musc_factor * musc
            # + mox_factor * mox
            # + abs_factor * abs(musc - mox)
            + 0.06 * pitcher_hype * (1 + 0.2 * vibes)
            - 0.06 * batter_hype * (1 + 0.2 * vibes)
        )
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

    div = batter.divinity * get_multiplier(batter, batting_team, "batter", "divinity", meta) * (1 + 0.2 * batter_vibes)
    musc = (
        batter.musclitude
        * get_multiplier(batter, batting_team, "batter", "musclitude", meta)
        * (1 + 0.2 * batter_vibes)
    )
    thwack = (
        batter.thwackability
        * get_multiplier(batter, batting_team, "batter", "thwackability", meta)
        * (1 + 0.2 * batter_vibes)
    )
    invpath = (1 - batter.patheticism / get_multiplier(batter, batting_team, "batter", "patheticism", meta)) * (
        1 + 0.2 * batter_vibes
    )
    ruth = (
        pitcher.ruthlessness
        * get_multiplier(pitcher, pitching_team, "pitcher", "ruthlessness", meta)
        * (1 + 0.2 * pitcher_vibes)
    )
    visc = stadium.viscosity

    combined_batting = (div + musc + invpath + thwack) / 4
    threshold = 0.7 + 0.35 * combined_batting - 0.4 * ruth + 0.2 * (visc - 0.5)
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

    moxie = batter.moxie * get_multiplier(batter, batting_team, "batter", "moxie", meta) * (1 + 0.2 * batter_vibes)
    path = batter.patheticism / get_multiplier(batter, batting_team, "batter", "patheticism", meta)
    ruth = (
        pitcher.ruthlessness
        * get_multiplier(pitcher, pitching_team, "pitcher", "ruthlessness", meta)
        * (1 + 0.2 * pitcher_vibes)
    )
    visc = stadium.viscosity

    combined = (12 * ruth - 5 * moxie + 5 * path + 4 * visc) / 20
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

    div = batter.divinity * get_multiplier(batter, batting_team, "batter", "divinity", meta)
    musc = batter.musclitude * get_multiplier(batter, batting_team, "batter", "musclitude", meta)
    thwack = batter.thwackability * get_multiplier(batter, batting_team, "batter", "thwackability", meta)
    path = batter.patheticism / get_multiplier(batter, batting_team, "batter", "patheticism", meta)
    combined_batting = (div + musc + thwack - path) / 2 * (1 + 0.2 * batter_vibes)
    if combined_batting < 0:
        return float("nan")  # hi caleb

    ruth = (
        pitcher.ruthlessness
        * get_multiplier(pitcher, pitching_team, "pitcher", "ruthlessness", meta)
        * (1 + 0.2 * pitcher_vibes)
    )

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

    invpath = max(
        (1 - batter.patheticism / get_multiplier(batter, batting_team, "batter", "patheticism", meta))
        * (1 + 0.2 * batter_vibes),
        0,
    )

    ruth = (
        pitcher.ruthlessness
        * get_multiplier(pitcher, pitching_team, "pitcher", "ruthlessness", meta)
        * (1 + 0.2 * pitcher_vibes)
    )

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


def get_foul_threshold(batter: PlayerData, batting_team: TeamData, stadium: StadiumData, meta: StatRelevantData):
    vibes = batter.vibes(meta.day)
    fwd = stadium.forwardness
    obt = stadium.obtuseness
    musc = batter.musclitude * get_multiplier(batter, batting_team, "batter", "musclitude", meta) * (1 + 0.2 * vibes)
    thwack = (
        batter.thwackability * get_multiplier(batter, batting_team, "batter", "thwackability", meta) * (1 + 0.2 * vibes)
    )
    div = batter.divinity * get_multiplier(batter, batting_team, "batter", "divinity", meta) * (1 + 0.2 * vibes)
    batter_sum = (musc + thwack + div) / 3

    threshold = 0.25 + 0.1 * fwd - 0.1 * obt + 0.1 * batter_sum
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

    div = batter.divinity * get_multiplier(batter, batting_team, "batter", "divinity", meta) * (1 + 0.2 * batter_vibes)
    opw = (
        pitcher.overpowerment
        * get_multiplier(pitcher, pitching_team, "pitcher", "overpowerment", meta)
        * (1 + 0.2 * pitcher_vibes)
    )
    supp = (
        pitcher.suppression
        * get_multiplier(pitcher, pitching_team, "pitcher", "suppression", meta)
        * (1 + 0.2 * pitcher_vibes)
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
