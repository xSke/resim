import bisect
import datetime
import io
import re
from argparse import ArgumentParser

from tqdm import tqdm

from data import get_feed_between
from resim import Csv, Resim
from rng import Rng
from run import FRAGMENTS_WITH_SEASON


class RngCountContext:
    def __init__(self, rng: Rng):
        self.rng = rng
        self.count = 0
        self.rng_step = rng.step

    def __enter__(self):
        self.rng.step = self.step
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.rng.step = self.rng_step

    def step(self, step: int = -1):
        self.count += step
        return self.rng_step(step)


def parse_args():
    parser = ArgumentParser("jump_back")

    parser.add_argument("start")
    parser.add_argument("--start_time", default="")
    parser.add_argument("--jump_hours", type=int, default=0)
    parser.add_argument("--rolls", nargs="?", type=int, default=-1)
    parser.add_argument(
        "--csv",
        nargs="+",
        default=[],
        metavar="CSV",
        help="Only log these CSV types. Default is logging all CSV types. Use --csv-list to see possible CSVs.",
    )
    parser.add_argument("--csv-list", default=False, action="store_true", help="List the CSVs which can be included")
    parser.add_argument(
        "--ignore-deploys",
        default=False,
        action="store_true",
        help="Try running even if it crosses a known deploy time.",
    )
    parser.add_argument("--no-retry", default=False, action="store_true")

    args = parser.parse_args()
    args.csv = [Csv(Csv.__members__.get(csv, csv)) for csv in args.csv]
    return args


def main():
    args = parse_args()
    if args.csv_list:
        print("Current CSV options:")
        for csv in Csv:
            print(f"  {csv.name}")
        return
    out_file = io.StringIO()

    fragment = None

    if args.start:
        match = re.match(r"[sS]([0-9]{1,2})[fF]([0-9]{1,3})", args.start)
        if match:
            season = int(match[1])
            fragment_index = int(match[2])
            season_fragments = list(filter(lambda x: x[0] == season, FRAGMENTS_WITH_SEASON))
            print(season_fragments[fragment_index])
            if fragment_index < len(season_fragments):
                fragment = season_fragments[fragment_index]
            else:
                print(f"unknown fragment: season {season} has {len(season_fragments)}.")
                exit()
        else:
            print("invalid fragement. Must be in the form 'S[season]F[fragment number]'")
            exit()

    end_time = fragment[4]

    with open("deploys.txt", "r") as deploys_file:
        deploy_times = sorted([line.strip() for line in deploys_file])

    if args.start_time:
        start_time = args.start_time
    else:
        start_time = datetime.datetime.fromisoformat(fragment[4][:-1])
        start_time = start_time.replace(minute=0, second=0, microsecond=0) - datetime.timedelta(hours=args.jump_hours)
        start_time = start_time.isoformat() + "Z"

    i = bisect.bisect_left(deploy_times, start_time)
    if i != len(deploy_times) and deploy_times[i] < end_time:
        print(f"This range spans a known deploy time at {deploy_times[i]}! It probably won't work.")
        if not args.ignore_deploys:
            return

    print("Loading events...")
    total_events = len(get_feed_between(start_time, end_time))

    _, rng_state, rng_offset, step, _, fragment_end_time = fragment

    if args.rolls > 0:
        rolls = args.rolls
    else:
        print("Estimating roll count...")

        rng = Rng(rng_state, rng_offset)
        rng.step(step)
        with RngCountContext(rng) as rng_counter, tqdm(total=total_events, unit="events") as _:
            resim = Resim(rng, None, run_name=start_time, raise_on_errors=False, csvs_to_log=args.csv)
            resim.run(start_time, end_time, progress_callback=None)
            rolls = rng_counter.count
            tqdm.write(f"rolls used: {rolls}")

    rng = Rng(rng_state, rng_offset)
    rng.step(step)
    print(f"Starting at state: {rng.get_state_str()} and jumping back {rolls}")
    rng.step(-rolls)
    print(f"to state {rng.get_state_str()}")
    s0, s1, offset = rng.get_state()
    with RngCountContext(rng) as rng_counter, tqdm(total=total_events, unit="events") as _:
        resim = Resim(rng, out_file, run_name=start_time, raise_on_errors=False, csvs_to_log=args.csv)
        resim.run(start_time, end_time, progress_callback=None)
        tqdm.write(f"rolls used: {rng_counter.count}/{rolls}")
        tqdm.write(f"state at end: {rng.get_state_str()}")

    found_incorrect = False
    offsets = {n for n in range(-63, 64)}
    out_file.seek(0)
    for line in out_file:
        if not found_incorrect:
            if re.match(r"Error:\s*incorrect fielder!", line):
                found_incorrect = True
        else:
            pattern = r"\(matching offsets: \[([-0-9,\s]+)\]\)"
            match = re.match(pattern, line)
            if match:
                print(sorted(int(n) for n in match[1].split(",")))
                offsets &= {int(n) for n in match[1].split(",")}
                if not offsets:
                    print("Couldn't find guess offset. It might not be reachable or may have other errors.")
                    with open("jump.txt", "w") as out:
                        out.write(out_file.getvalue())
                    return
                if len(offsets) == 1:
                    rolls -= list(offsets)[0]
                    break
    else:
        if not found_incorrect:
            print(f'Looks correct to me! ({season}, ({s0}, {s1}), {offset}, 0, "{start_time}", "{fragment_end_time}"),')
            with open("jump.txt", "w") as out:
                out.write(out_file.getvalue())
        else:
            possible_rolls = [rolls - offset for offset in offsets]
            print(f"Multiple offsets possible. Try again with --rolls set to one of {possible_rolls}")
            with open("jump.txt", "w") as out:
                out.write(out_file.getvalue())
        return

    if args.no_retry:
        with open("jump.txt", "w") as out:
            out.write(out_file.getvalue())
        return

    rng = Rng(rng_state, rng_offset)
    rng.step(step)

    print(f"Trying again, from state {rng.get_state_str()} jumping back {rolls}")
    rng.step(-rolls)
    s0, s1, offset = rng.get_state()
    out_file.close()
    out_file = io.StringIO()
    with RngCountContext(rng) as rng_counter, tqdm(total=total_events, unit="events") as _:
        resim = Resim(rng, out_file, run_name=start_time, raise_on_errors=False, csvs_to_log=args.csv)
        resim.run(start_time, end_time, progress_callback=None)
        tqdm.write(f"rolls used: {rng_counter.count}/{rolls}")
        tqdm.write(f"state at end: {rng.get_state_str()}")

    out_file.seek(0)
    for line in out_file:
        if re.match(r"Error:\s*incorrect fielder!", line):
            print("That didn't work! It might not be reachable or may have other errors.")
            with open("jump.txt", "w") as out:
                out.write(out_file.getvalue())
            return

    print(f'Looks correct to me! ({season}, ({s0}, {s1}), {offset}, 0, "{start_time}", "{fragment_end_time}"),')
    with open("jump.txt", "w") as out:
        out.write(out_file.getvalue())


if __name__ == "__main__":
    main()
