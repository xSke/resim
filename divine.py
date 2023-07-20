import dataclasses
import json
from resim import LoggedRoll, Resim
from io import StringIO

# from multiprocessing import Pool
from rng import Rng
from rng_solver import solve_in_math_random_order


class StubRng:
    def __init__(self):
        self.state = (0, 0)
        self.offset = 0

    def next(self):
        # shouldn't be too low, otherwise we'll trigger the "roll again on low rolls" cases and throw things off
        return 0.5

    def get_state_str(self):
        return "[STUB]"

    def step(self, step=1):
        return 0.5


def get_rng_url(solution):
    state = solution["state"]
    return f"https://rng.sibr.dev/?state=({state[0]},{state[1]})+{solution['offset']}"


def inner(window):
    start_time = min(w.timestamp for w in window)
    end_time = max(w.timestamp for w in window)

    knowns = []
    for roll in window:
        if roll.lower_bound == roll.upper_bound:
            knowns.append(roll.lower_bound)
        elif roll.lower_bound > 0 or roll.upper_bound < 1:
            knowns.append((roll.lower_bound, roll.upper_bound))
        else:
            knowns.append(None)

    print(f"trying window {start_time} - {end_time}")

    solutions = solve_in_math_random_order(knowns)
    for solution in solutions:
        rng = Rng(solution["state"], solution["offset"])
        for roll in window:
            if roll and roll.index == 0:
                rng.step(-1)  # account for our indexing being the coords *before* consuming the roll
                print(
                    f"found event at {roll.timestamp} ({roll.roll_name}): "
                    f"{rng.get_state_str()}, first roll {rng.next()}"
                )
                break
            rng.step(1)


def main():
    start_timestamp = "2021-04-14T16:01:37.236Z"
    end_timestamp = "2021-04-14T16:22:37.236Z"

    cache_file = f"cache/divine_rolls_{start_timestamp.replace(':', '_')}-" f"{end_timestamp.replace(':', '_')}.json"
    try:
        with open(cache_file, "r") as f:
            roll_log = list(map(lambda roll: LoggedRoll(**roll), json.load(f)))
            print(f"got {len(roll_log)} rolls from cache")
    except Exception as e:
        roll_log = None

    if not roll_log:
        out_file = StringIO()

        stub_rng = StubRng()
        resim = Resim(stub_rng, out_file, run_name=None, raise_on_errors=False)
        resim.run(start_timestamp, end_timestamp, None)
        roll_log = resim.roll_log
        print(f"got {len(roll_log)} rolls")

        with open(cache_file, "w") as f:
            json.dump(list(map(dataclasses.asdict, roll_log)), f)

    # todo: parallelize this in a way that doesn't make ctrl-c explode, and that supports tqdm
    # with Pool(1) as p:
    args = []

    # window size and step size are kinda arbitrary
    # but we don't want it to waste too much time on a range that def. doesn't work
    window_size = 2800
    step_size = 100
    for window_pos in range(0, len(roll_log) - window_size, step_size):
        window = roll_log[window_pos : window_pos + window_size]
        args.append(window)

    for w in args:
        inner(w)
    # p.map(inner, args)


if __name__ == "__main__":
    main()
