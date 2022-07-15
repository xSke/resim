from dataclasses import dataclass
import itertools
import math


def calculate_vibes(player, day):
    frequency = 6 + round(10 * player['buoyancy'])
    phase = math.pi * ((2 / frequency) * day + 0.5)

    cinnamon = player['cinnamon'] if player['cinnamon'] is not None else 0
    range = 0.5 * (player['pressurization'] + cinnamon)
    return (range * math.sin(phase)) - (0.5 * player['pressurization']) + (0.5 * cinnamon)


@dataclass
class RollLog:
    event_type: str
    roll: float
    passed: bool

    batter_name: str
    batter_buoyancy: float
    batter_divinity: float
    batter_martyrdom: float
    batter_moxie: float
    batter_musclitude: float
    batter_patheticism: float
    batter_thwackability: float
    batter_tragicness: float
    batter_multiplier: float
    batter_mods: str

    pitcher_name: str
    pitcher_ruthlessness: float
    pitcher_overpowerment: float
    pitcher_unthwackability: float
    pitcher_shakespearianism: float
    pitcher_suppression: float
    pitcher_coldness: float
    pitcher_multiplier: float

    # on a lark
    pitcher_chasiness: float
    pitcher_mods: str


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

    batting_team_hype: float
    pitching_team_hype: float

    batter_vibes: float
    pitcher_vibes: float

    game_id: str
    play_count: int
    weather: int

def make_roll_log(event_type: str, roll: float, passed: bool, batter, batting_team, pitcher,
                  pitching_team, stadium, players, update):

    batter_multiplier = 1
    for mod in itertools.chain(batter.mods, batting_team.mods):
        if mod == 'OVERPERFORMING':
            batter_multiplier += 0.2
        elif mod == 'UNDERPERFORMING':
            batter_multiplier -= 0.2
        elif mod == 'GROWTH':
            batter_multiplier += min(0.05, 0.05 * (update["day"] / 99))
        elif mod == 'HIGH_PRESSURE':
            # checks for flooding weather and baserunners
            if update["weather"] == 18 and len(update['baseRunners']) > 0:
                batter_multiplier += 0.25

                # In season 14 High Pressure adds Overperforming but makes it worth 0.25 instead of
                # 0.2. This should cancel that out.
                if update["season"] == 13:
                    batter_multiplier -= 0.2
        elif mod == 'TRAVELING':
            if update["topOfInning"]:
                batter_multiplier += 0.05
        elif mod == 'SINKING_SHIP':
            roster_size = len(batting_team.data["lineup"]) + len(batting_team.data["rotation"])
            batter_multiplier += (14 - roster_size) * 0.01

    pitcher_multiplier = 1
    for mod in itertools.chain(pitcher.mods, pitching_team.mods):
        if mod == 'OVERPERFORMING':
            pitcher_multiplier += 0.2
        elif mod == 'UNDERPERFORMING':
            pitcher_multiplier -= 0.2
        elif mod == 'GROWTH':
            pitcher_multiplier += min(0.05, 0.05 * (update["day"] / 99))
        elif mod == 'TRAVELING':
            if not update["topOfInning"]:
                pitcher_multiplier += 0.05
        elif mod == 'SINKING_SHIP':
            roster_size = len(pitching_team.data["lineup"]) + len(pitching_team.data["rotation"])
            pitcher_multiplier += (14 - roster_size) * 0.01


    defense_lineup = pitching_team.data['lineup']
    return RollLog(
        event_type=event_type,
        roll=roll,
        passed=passed,

        batter_name=batter.data["name"],
        batter_buoyancy=batter.data["buoyancy"] * batter_multiplier,
        batter_divinity=batter.data["divinity"] * batter_multiplier,
        batter_martyrdom=batter.data["martyrdom"] * batter_multiplier,
        batter_moxie=batter.data["moxie"] * batter_multiplier,
        batter_musclitude=batter.data["musclitude"] * batter_multiplier,
        batter_patheticism=batter.data["patheticism"] * batter_multiplier,
        batter_thwackability=batter.data["thwackability"] * batter_multiplier,
        batter_tragicness=batter.data["tragicness"] * batter_multiplier,
        batter_multiplier=batter_multiplier,
        batter_mods=";".join(batter.mods),

        pitcher_name=pitcher.data["name"],
        pitcher_ruthlessness=pitcher.data["ruthlessness"] * pitcher_multiplier,
        pitcher_overpowerment=pitcher.data["overpowerment"] * pitcher_multiplier,
        pitcher_unthwackability=pitcher.data["unthwackability"] * pitcher_multiplier,
        pitcher_shakespearianism=pitcher.data["shakespearianism"] * pitcher_multiplier,
        pitcher_suppression=pitcher.data["suppression"] * pitcher_multiplier,
        pitcher_coldness=pitcher.data["coldness"] * pitcher_multiplier,
        pitcher_chasiness=pitcher.data["chasiness"] * pitcher_multiplier,
        pitcher_multiplier=pitcher_multiplier,
        pitcher_mods=";".join(pitcher.mods),

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

        batting_team_hype=stadium.data["hype"] if not update["topOfInning"] else 0,
        pitching_team_hype=stadium.data["hype"] if update["topOfInning"] else 0,

        batter_vibes=calculate_vibes(batter.data, update["day"]),
        pitcher_vibes=calculate_vibes(pitcher.data, update["day"]),

        game_id=update['id'],
        play_count=update['playCount'],
        weather=update["weather"]
    )
