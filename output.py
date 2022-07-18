from dataclasses import dataclass
import itertools
import math


def calculate_vibes(player, day, multiplier):
    frequency = 6 + round(10 * player['buoyancy'] * multiplier)
    phase = math.pi * ((2 / frequency) * day + 0.5)

    pressurization = player['pressurization'] * multiplier
    cinnamon = (player['cinnamon'] if player['cinnamon'] is not None else 0) * multiplier
    range = 0.5 * (pressurization + cinnamon)
    return (range * math.sin(phase)) - (0.5 * pressurization) + (0.5 * cinnamon)


@dataclass
class RollLog:
    event_type: str
    roll: float
    passed: bool

    batter_buoyancy: float
    batter_divinity: float
    batter_martyrdom: float
    batter_moxie: float
    batter_musclitude: float
    batter_patheticism: float
    batter_thwackability: float
    batter_tragicness: float
    batter_coldness: float
    batter_overpowerment: float
    batter_ruthlessness: float
    batter_shakespearianism: float
    batter_suppression: float
    batter_unthwackability: float
    batter_base_thirst: float
    batter_continuation: float
    batter_ground_friction: float
    batter_indulgence: float
    batter_laserlikeness: float
    batter_anticapitalism: float
    batter_chasiness: float
    batter_omniscience: float
    batter_tenaciousness: float
    batter_watchfulness: float
    batter_pressurization: float
    batter_cinnamon: float
    batter_multiplier: float

    pitcher_buoyancy: float
    pitcher_divinity: float
    pitcher_martyrdom: float
    pitcher_moxie: float
    pitcher_musclitude: float
    pitcher_patheticism: float
    pitcher_thwackability: float
    pitcher_tragicness: float
    pitcher_ruthlessness: float
    pitcher_overpowerment: float
    pitcher_unthwackability: float
    pitcher_shakespearianism: float
    pitcher_suppression: float
    pitcher_coldness: float
    pitcher_base_thirst: float
    pitcher_continuation: float
    pitcher_ground_friction: float
    pitcher_indulgence: float
    pitcher_laserlikeness: float
    pitcher_anticapitalism: float
    pitcher_chasiness: float
    pitcher_omniscience: float
    pitcher_tenaciousness: float
    pitcher_watchfulness: float
    pitcher_pressurization: float
    pitcher_cinnamon: float
    pitcher_multiplier: float

    defense_avg_anticapitalism: float
    defense_avg_chasiness: float
    defense_avg_omniscience: float
    defense_avg_tenaciousness: float
    defense_avg_watchfulness: float

    ballpark_grandiosity: float
    ballpark_fortification: float
    ballpark_obtuseness: float
    ballpark_ominousness: float
    ballpark_inconvenience: float
    ballpark_viscosity: float
    ballpark_forwardness: float
    ballpark_mysticism: float
    ballpark_elongation: float
    ballpark_filthiness: float

    what1: float
    what2: float

    batting_team_hype: float
    pitching_team_hype: float

    batter_name: str
    pitcher_name: str

    batter_vibes: float
    batter_vibes_multiplied: float
    pitcher_vibes: float
    pitcher_vibes_multiplied: float

    batter_mods: str
    batting_team_mods: str
    pitcher_mods: str
    pitching_team_mods: str

    game_id: str
    stadium_id: str
    play_count: int
    weather: int
    ball_count: int
    strike_count: int
    season: int
    day: int
    top_of_inning: bool
    home_score: float
    away_score: float
    inning: int
    batting_team_roster_size: int
    pitching_team_roster_size: int
    baserunner_count: int
    is_strike: bool
    strike_roll: float
    strike_threshold: float


def make_roll_log(event_type: str, roll: float, passed: bool, batter, batting_team, pitcher,
                  pitching_team, stadium, players, update, what1: float, what2: float, batter_multiplier: float,
                  pitcher_multiplier: float, is_strike: bool, strike_roll: float, strike_threshold: float):
    defense_lineup = pitching_team.data['lineup']
    return RollLog(
        event_type=event_type,
        roll=roll,
        passed=passed,

        batter_name=batter.data["name"],
        pitcher_name=pitcher.data["name"],

        batter_buoyancy=batter.data["buoyancy"],
        batter_divinity=batter.data["divinity"],
        batter_martyrdom=batter.data["martyrdom"],
        batter_moxie=batter.data["moxie"],
        batter_musclitude=batter.data["musclitude"],
        batter_patheticism=batter.data["patheticism"],
        batter_thwackability=batter.data["thwackability"],
        batter_tragicness=batter.data["tragicness"],
        batter_coldness=batter.data["coldness"],
        batter_overpowerment=batter.data["overpowerment"],
        batter_ruthlessness=batter.data["ruthlessness"],
        batter_shakespearianism=batter.data["shakespearianism"],
        batter_suppression=batter.data["suppression"],
        batter_unthwackability=batter.data["unthwackability"],
        batter_base_thirst=batter.data["baseThirst"],
        batter_continuation=batter.data["continuation"],
        batter_ground_friction=batter.data["groundFriction"],
        batter_indulgence=batter.data["indulgence"],
        batter_laserlikeness=batter.data["laserlikeness"],
        batter_anticapitalism=batter.data["anticapitalism"],
        batter_chasiness=batter.data["chasiness"],
        batter_omniscience=batter.data["omniscience"],
        batter_tenaciousness=batter.data["tenaciousness"],
        batter_watchfulness=batter.data["watchfulness"],
        batter_pressurization=batter.data["pressurization"],
        batter_cinnamon=(batter.data.get("cinnamon") or 0),
        batter_multiplier=batter_multiplier,

        pitcher_buoyancy=pitcher.data["buoyancy"],
        pitcher_divinity=pitcher.data["divinity"],
        pitcher_martyrdom=pitcher.data["martyrdom"],
        pitcher_moxie=pitcher.data["moxie"],
        pitcher_musclitude=pitcher.data["musclitude"],
        pitcher_patheticism=pitcher.data["patheticism"],
        pitcher_thwackability=pitcher.data["thwackability"],
        pitcher_tragicness=pitcher.data["tragicness"],
        pitcher_coldness=pitcher.data["coldness"],
        pitcher_overpowerment=pitcher.data["overpowerment"],
        pitcher_ruthlessness=pitcher.data["ruthlessness"],
        pitcher_shakespearianism=pitcher.data["shakespearianism"],
        pitcher_suppression=pitcher.data["suppression"],
        pitcher_unthwackability=pitcher.data["unthwackability"],
        pitcher_base_thirst=pitcher.data["baseThirst"],
        pitcher_continuation=pitcher.data["continuation"],
        pitcher_ground_friction=pitcher.data["groundFriction"],
        pitcher_indulgence=pitcher.data["indulgence"],
        pitcher_laserlikeness=pitcher.data["laserlikeness"],
        pitcher_anticapitalism=pitcher.data["anticapitalism"],
        pitcher_chasiness=pitcher.data["chasiness"],
        pitcher_omniscience=pitcher.data["omniscience"],
        pitcher_tenaciousness=pitcher.data["tenaciousness"],
        pitcher_watchfulness=pitcher.data["watchfulness"],
        pitcher_pressurization=pitcher.data["pressurization"],
        pitcher_cinnamon=pitcher.data["cinnamon"],
        pitcher_multiplier=pitcher_multiplier,

        defense_avg_anticapitalism=sum(
            players[pid]['anticapitalism'] for pid in defense_lineup) / len(defense_lineup),
        defense_avg_chasiness=sum(
            players[pid]['chasiness'] for pid in defense_lineup) / len(defense_lineup),
        defense_avg_omniscience=sum(
            players[pid]['omniscience'] for pid in defense_lineup) / len(defense_lineup),
        defense_avg_tenaciousness=sum(
            players[pid]['tenaciousness'] for pid in defense_lineup) / len(defense_lineup),
        defense_avg_watchfulness=sum(
            players[pid]['watchfulness'] for pid in defense_lineup) / len(defense_lineup),

        ballpark_grandiosity=stadium.data["grandiosity"],
        ballpark_fortification=stadium.data["fortification"],
        ballpark_obtuseness=stadium.data["obtuseness"],
        ballpark_ominousness=stadium.data["ominousness"],
        ballpark_inconvenience=stadium.data["inconvenience"],
        ballpark_viscosity=stadium.data["viscosity"],
        ballpark_forwardness=stadium.data["forwardness"],
        ballpark_mysticism=stadium.data["mysticism"],
        ballpark_elongation=stadium.data["elongation"],
        ballpark_filthiness=stadium.data["filthiness"],

        batting_team_hype=stadium.data["hype"] if not update["topOfInning"] else 0,
        pitching_team_hype=stadium.data["hype"] if update["topOfInning"] else 0,

        batter_vibes=calculate_vibes(batter.data, update["day"], 1),
        batter_vibes_multiplied=calculate_vibes(batter.data, update["day"], batter_multiplier),
        pitcher_vibes=calculate_vibes(pitcher.data, update["day"], 1),
        pitcher_vibes_multiplied=calculate_vibes(pitcher.data, update["day"], pitcher_multiplier),

        batter_mods=";".join(batter.mods),
        batting_team_mods=";".join(batting_team.mods),
        pitcher_mods=";".join(pitcher.mods),
        pitching_team_mods=";".join(pitching_team.mods),

        game_id=update['id'],
        stadium_id=update['stadiumId'],
        play_count=update['playCount'],
        weather=update["weather"],
        ball_count=update["atBatBalls"],
        strike_count=update["atBatStrikes"],
        baserunner_count=update["baseRunners"],

        season=update["season"],
        day=update["day"],
        top_of_inning=update["topOfInning"],
        home_score=update["homeScore"],
        away_score=update["awayScore"],
        inning=update["inning"],

        what1=what1,
        what2=what2,
        batting_team_roster_size=len(batting_team.data["lineup"]) + len(batting_team.data["rotation"]),
        pitching_team_roster_size=len(pitching_team.data["lineup"]) + len(pitching_team.data["rotation"]),
        is_strike=is_strike,
        strike_roll=strike_roll,
        strike_threshold=strike_threshold
    )
