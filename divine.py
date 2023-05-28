from resim import Resim
from io import StringIO

# from multiprocessing import Pool
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
        print(f"found event at {window[0].timestamp}: " f"{get_rng_url(solution)} ; " f"first roll {solution['roll']}")


def main():
    start_timestamp = "2021-04-14T16:01:37.236Z"
    end_timestamp = "2021-04-14T16:22:37.236Z"

    out_file = StringIO()

    stub_rng = StubRng()
    resim = Resim(stub_rng, out_file, run_name=None, raise_on_errors=False)
    resim.run(start_timestamp, end_timestamp, None)

    print(f"got {len(resim.roll_log)} rolls")

    # todo: parallelize this in a way that doesn't make ctrl-c explode, and that supports tqdm
    # with Pool(1) as p:
    args = []

    # window size and step size are kinda arbitrary
    # but we don't want it to waste too much time on a range that def. doesn't work
    window_size = 2800
    step_size = 100
    for window_pos in range(0, len(resim.roll_log) - window_size, step_size):
        window = resim.roll_log[window_pos : window_pos + window_size]
        args.append(window)

    for w in args:
        inner(w)
    # p.map(inner, args)


if __name__ == "__main__":
    main()
