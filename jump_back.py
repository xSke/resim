import bisect
import datetime
import re
import sys
from argparse import ArgumentParser

from tqdm import tqdm

from data import get_feed_between
from resim import Resim
from rng import Rng

# (season0indexed, day0indexed): (s0, s1), rng offset, event offset, start timestamp, end timestamp
FRAGMENTS = {

    (12, 74): (
        (617776737860945499, 6965272805741501853),
        10,
        0,
        "2021-03-04T19:00:00.000Z",
        "2021-03-05T18:50:00Z",
    ),
    (13, 29):  (
        (2154942915490753213, 4636043162326033301),
        13,
        0,
        "2021-03-09T21:00:00.000Z",
        "2021-03-10T17:50:00Z",
    ),
    (14, 7): (
        (12335197627095558518, 4993735724122314585),
        11,
        0,
        "2021-03-15T21:00:00.000Z",
        "2021-03-16T15:50:01.111345Z",
    ),
    (14, 30): (
        (16935077139086615170, 7227318407464058534),
        12,
        0,
        "2021-03-16T21:00:00.000Z",
        "2021-03-17T18:50:07.535Z",
    ),
    (14, 81): (
        (4369050506664465536, 4603334513036430167),
        12,
        0,
        "2021-03-19T01:00:00.000Z",
        "2021-03-19T18:40:01.593947Z",
    ),
    (14, 100): (
        (4742777402478590244, 2004520124933634673),
        22,
        0,
        "2021-03-19T21:00:00.000Z",
        "2021-03-20T19:50:01.020Z",
    ),
    (15, 33): (
        (9668656808250152634, 9027125133720942837),
        27,
        0,
        "2021-04-07T00:00:00.000Z",
        "2021-04-07T16:50:00.594684Z",
    ),
    (15, 78): (
        (11947114742050313518, 14817598476034896117),
        62,
        0,
        "2021-04-08T20:00:00.000Z",
        "2021-04-09T19:40:40.804096Z",
    ),
}


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
        self.rng_step(step)


def parse_args():
    parser = ArgumentParser("jump_back")

    parser.add_argument("start")
    parser.add_argument("--start_time", default="")
    parser.add_argument("--jump_hours", type=int, default=0)
    parser.add_argument("jump_rolls", nargs="?", type=int, default=1000)
    parser.add_argument("outfile", nargs="?", default="-")
    parser.add_argument("--silent", default=False, action="store_true")

    return parser.parse_args()


def main():
    args = parse_args()
    if args.silent:
        out_file = None
    elif args.outfile == "-":
        out_file = sys.stdout
    else:
        out_file = open(args.outfile, "w")

    fragment_key = None

    if args.start:    
        match = re.match(r'[sS]([0-9]{1,2})[dD]([0-9]{1,3})', args.start)
        if match:
            season = int(match[1])
            day = int(match[2])
            if (season, day) in FRAGMENTS.keys():
                fragment_key = (season, day)
            else:
                print("unknown fragment")
        else:
            print("invalid fragement")

    if not fragment_key:
        print("Known fragments are")
        for season, day in FRAGMENTS:
            print(f'S{season}D{day}')
        exit()

    fragment = FRAGMENTS[fragment_key]
    end_time = fragment[3]

    with open('deploys.txt', 'r') as deploys_file:
        deploy_times = sorted([line.strip() for line in deploys_file])

    if args.start_time:
        start_time = args.start_time
    else:
        start_time = datetime.datetime.fromisoformat(fragment[3][:-1])
        start_time = start_time.replace(minute = 0, second = 0, microsecond = 0) - datetime.timedelta(hours = args.jump_hours)
        start_time = start_time.isoformat() + 'Z'

    i = bisect.bisect_left(deploy_times, start_time)
    if i != len(deploy_times) and deploy_times[i] < end_time:
       print(f"This range spans a known deploy time at {deploy_times[i]}! It probably won't work.")
       return

    print("Loading events...")
    total_events = len(get_feed_between(start_time, end_time))

    rng_state, rng_offset, step, _, _ = fragment
    rng = Rng(rng_state, rng_offset)
    rng.step(step)
    print(f'starting at state: {rng.get_state_str()} and jumping back {args.jump_rolls}')
    rng.step(-args.jump_rolls)
    print(f'to state {rng.get_state_str()}')

    with (
        RngCountContext(rng) as rng_counter,
        tqdm(total=total_events, unit="events") as progress
        ):
            resim = Resim(rng, out_file, start_time, raise_on_errors=False)
            resim.run(start_time, end_time, progress)
            tqdm.write(f"steps used: {rng_counter.count}/{args.jump_rolls}")
            tqdm.write(f"state at end: {rng.get_state_str()}")

if __name__ == "__main__":
    main()
