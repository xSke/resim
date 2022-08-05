from data import PlayerData, TeamData, StadiumData, Weather
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


def get_multiplier(player: PlayerData, team: TeamData, position: str, attr: str, meta: StatRelevantData):
    multiplier = 1
    for mod in itertools.chain(player.mods, team.mods):
        if mod == "OVERPERFORMING":
            multiplier += 0.2
        elif mod == "UNDERPERFORMING":
            multiplier -= 0.2
        elif mod == "GROWTH":
            # todo: do we ever want this for other positions?
            if attr not in ["patheticism", "thwackability", "ruthlessness"]:
                multiplier += min(0.05, 0.05 * (meta.day / 99))
        elif mod == "HIGH_PRESSURE":
            # checks for flooding weather and baserunners
            if meta.weather == Weather.FLOODING and meta.runner_count > 0:
                # "won't this stack with the overperforming mod it gives the team" yes. yes it will.
                # "should we really boost the pitcher when the *other* team's batters are on base" yes.
                multiplier += 0.25
        elif mod == "TRAVELING":
            if (meta.top_of_inning and position == "batter") or (not meta.top_of_inning and position == "pitcher"):
                if attr not in ["patheticism", "thwackability", "ruthlessness"]:
                    multiplier += 0.05

            # todo: do we ever want this?
            # elif not top_of_inning and position in ["fielder", "pitcher"]:
            # multiplier += 0.05
        elif mod == "SINKING_SHIP":
            roster_size = len(team.data["lineup"]) + len(team.data["rotation"])

            if attr not in []:
                multiplier += (14 - roster_size) * 0.01
        elif mod == "AFFINITY_FOR_CROWS" and meta.weather == Weather.BIRDS:
            multiplier += 0.5
        elif mod == "CHUNKY" and meta.weather == Weather.PEANUTS:
            # todo: handle carefully! historical blessings boosting "power" (Ooze, S6) boosted groundfriction
            #  by half of what the other two attributes got. (+0.05 instead of +0.10, in a "10% boost")
            # gfric boost hasn't been "tested" necessarily
            if attr in ["musclitude", "divinity"]:
                multiplier += 1.0
            elif attr == "ground_friction":
                multiplier += 0.5
        elif mod == "SMOOTH" and meta.weather == Weather.PEANUTS:
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
        elif mod == "ON_FIRE":
            # todo: figure out how the heck "on fire" works
            pass
        elif mod == "MINIMALIST":
            if meta.is_maximum_blaseball:
                multiplier -= 0.75
        elif mod == "MAXIMALIST":
            # not "seen in the data" yet
            if meta.is_maximum_blaseball:
                multiplier += 2.50

    if player.data.get("bat") == "NIGHT_VISION_GOGGLES" and meta.weather == Weather.ECLIPSE:
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
    ruth = pitcher.data["ruthlessness"] * get_multiplier(pitcher, pitching_team, "pitcher", "ruthlessness", meta)
    musc = batter.data["musclitude"] * get_multiplier(batter, batting_team, "batter", "musclitude", meta)
    fwd = stadium.data["forwardness"]

    constant = 0.2 if not is_flinching else 0.4

    ruth_factor, roll_cap = {11: (0.35, 0.9), 12: (0.3, 0.85), 13: (0.3, 0.85), 14: (0.285, 0.86)}[meta.season]

    threshold = constant + ruth_factor * (ruth * (1 + 0.2 * vibes)) + 0.2 * fwd + 0.1 * musc
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

    div = (
        batter.data["divinity"]
        * get_multiplier(batter, batting_team, "batter", "divinity", meta)
        * (1 + 0.2 * batter_vibes)
    )
    musc = (
        batter.data["musclitude"]
        * get_multiplier(batter, batting_team, "batter", "musclitude", meta)
        * (1 + 0.2 * batter_vibes)
    )
    thwack = (
        batter.data["thwackability"]
        * get_multiplier(batter, batting_team, "batter", "thwackability", meta)
        * (1 + 0.2 * batter_vibes)
    )
    invpath = (1 - batter.data["patheticism"] / get_multiplier(batter, batting_team, "batter", "patheticism", meta)) * (
        1 + 0.2 * batter_vibes
    )
    ruth = (
        pitcher.data["ruthlessness"]
        * get_multiplier(pitcher, pitching_team, "pitcher", "ruthlessness", meta)
        * (1 + 0.2 * pitcher_vibes)
    )
    visc = stadium.data["viscosity"]

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

    moxie = (
        batter.data["moxie"] * get_multiplier(batter, batting_team, "batter", "moxie", meta) * (1 + 0.2 * batter_vibes)
    )
    path = batter.data["patheticism"] / get_multiplier(batter, batting_team, "batter", "patheticism", meta)
    ruth = (
        pitcher.data["ruthlessness"]
        * get_multiplier(pitcher, pitching_team, "pitcher", "ruthlessness", meta)
        * (1 + 0.2 * pitcher_vibes)
    )
    visc = stadium.data["viscosity"]

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

    div = batter.data["divinity"] * get_multiplier(batter, batting_team, "batter", "divinity", meta)
    musc = batter.data["musclitude"] * get_multiplier(batter, batting_team, "batter", "musclitude", meta)
    thwack = batter.data["thwackability"] * get_multiplier(batter, batting_team, "batter", "thwackability", meta)
    path = batter.data["patheticism"] / get_multiplier(batter, batting_team, "batter", "patheticism", meta)
    combined_batting = (div + musc + thwack - path) / 2 * (1 + 0.2 * batter_vibes)
    if combined_batting < 0:
        return float("nan")  # hi caleb

    ruth = (
        pitcher.data["ruthlessness"]
        * get_multiplier(pitcher, pitching_team, "pitcher", "ruthlessness", meta)
        * (1 + 0.2 * pitcher_vibes)
    )

    fort = stadium.data["fortification"] - 0.5
    visc = stadium.data["viscosity"] - 0.5
    fwd = stadium.data["forwardness"] - 0.5
    ballpark_sum = (fort + 3 * visc - 6 * fwd) / 10

    constant, batting_factor, cap = {
        11: (0.8, 0.16, 0.9),
        12: (0.8, 0.16, 0.9),
        13: (0.8, 0.16, 0.9),
        14: (0.78, 0.17, 0.925),
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

    invpath = (1 - batter.data["patheticism"] / get_multiplier(batter, batting_team, "batter", "patheticism", meta)) * (
        1 + 0.2 * batter_vibes
    )
    ruth = (
        pitcher.data["ruthlessness"]
        * get_multiplier(pitcher, pitching_team, "pitcher", "ruthlessness", meta)
        * (1 + 0.2 * pitcher_vibes)
    )

    fort = stadium.data["fortification"] - 0.5
    visc = stadium.data["viscosity"] - 0.5
    fwd = stadium.data["forwardness"] - 0.5
    ballpark_sum = (fort + 3 * visc - 6 * fwd) / 10

    constant, path_factor, cap = {11: (0.35, 0.4, 1), 12: (0.35, 0.4, 1), 13: (0.4, 0.35, 1), 14: (0.4, 0.35, 1)}[
        meta.season
    ]

    threshold = constant - 0.1 * ruth + path_factor * (invpath**1.5) + 0.14 * ballpark_sum
    return min(cap, threshold)


def get_foul_threshold(batter: PlayerData, batting_team: TeamData, stadium: StadiumData, meta: StatRelevantData):
    vibes = batter.vibes(meta.day)
    fwd = stadium.data["forwardness"]
    obt = stadium.data["obtuseness"]
    musc = (
        batter.data["musclitude"]
        * get_multiplier(batter, batting_team, "batter", "musclitude", meta)
        * (1 + 0.2 * vibes)
    )
    thwack = (
        batter.data["thwackability"]
        * get_multiplier(batter, batting_team, "batter", "thwackability", meta)
        * (1 + 0.2 * vibes)
    )
    div = batter.data["divinity"] * get_multiplier(batter, batting_team, "batter", "divinity", meta) * (1 + 0.2 * vibes)
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

    div = (
        batter.data["divinity"]
        * get_multiplier(batter, batting_team, "batter", "divinity", meta)
        * (1 + 0.2 * batter_vibes)
    )
    opw = (
        pitcher.data["overpowerment"]
        * get_multiplier(pitcher, pitching_team, "pitcher", "overpowerment", meta)
        * (1 + 0.2 * pitcher_vibes)
    )
    supp = (
        pitcher.data["suppression"]
        * get_multiplier(pitcher, pitching_team, "pitcher", "suppression", meta)
        * (1 + 0.2 * pitcher_vibes)
    )

    grand = stadium.data["grandiosity"] - 0.5
    fort = stadium.data["fortification"] - 0.5
    visc = stadium.data["viscosity"] - 0.5
    om = stadium.data["ominousness"] - 0.5
    fwd = stadium.data["forwardness"] - 0.5
    ballpark_sum = 0.4 * grand + 0.2 * fort + 0.08 * visc + 0.08 * om - 0.24 * fwd

    opw_supp = (10 * opw + supp) / 11
    threshold = 0.12 + 0.16 * div - 0.08 * opw_supp - 0.18 * ballpark_sum
    return threshold
