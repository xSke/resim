import requests
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import rng_solver, rng

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

s = requests.Session()
rr = s.get(f"https://api.sibr.dev/chronicler/v2/entities?type=player&at=2021-03-20T00:00:00Z&count=2000").json()


for player in rr["items"]:
    player_id = player["entityId"]

    r = s.get(f"https://api.sibr.dev/chronicler/v2/versions?type=player&id={player_id}&order=asc&count=1").json()

    first_player_obj = r["items"][0]["data"]
    ts = r["items"][0]["validFrom"]
    attr_values = [float(first_player_obj[a]) for a in ATTR_ORDER_GEN]
    for wi in range(len(ATTR_ORDER_GEN)-4):
        w = attr_values[wi:wi+4]
        sols = rng_solver.solve_in_math_random_order(w)
        if not sols:
            continue

        for sol in sols:
            r = rng.Rng(sol["state"], 0)
            seed, offset = r.find_seed()

            # weird way to step back 2 and print that, for fn/ln rolls
            seed_str = rng.seed_str(seed, offset-2)
            print(f"{ts},{player_id},{first_player_obj['name']},{seed_str}")
        break
