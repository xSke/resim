import sys
from argparse import ArgumentParser

from tqdm import tqdm

from data import get_feed_between
from resim import Resim
from rng import Rng

# (s0, s1), rng offset, event offset, start timestamp, end timestamp
FRAGMENTS = [
    (
        (2670250086919271083, 8757269136258650039),
        50,
        -5,
        "2021-03-05T00:10:18.239Z",
        "2021-03-05T18:50:00Z",
    ),
    (
        (5945355568923279984, 7388402007486996562),
        28,
        -5,
        "2021-03-09T22:03:16.896Z",
        "2021-03-10T17:50:00Z",
    ),
    (
        (970217006020175473, 10513538743922031200),
        1,
        -5,
        "2021-03-15T21:07:52.915Z",
        "2021-03-16T15:50:01.111345Z",
    ),
    (
        (5240931180015396439, 15582981864323664294),
        34,
        -5,
        "2021-03-16T21:01:06.567Z",
        "2021-03-17T18:50:07.535Z",
    ),
    (
        (7115146577326673400, 7903952808578774174),
        32,
        -5,
        "2021-03-19T01:13:39.399Z",
        "2021-03-19T18:40:01.593947Z",
    ),
    (
        (11017019589957063107, 16275118049868972219),
        47,
        -8,
        "2021-03-19T22:15:00.688Z",
        "2021-03-20T19:50:01.020Z",
    ),
    (
        (5081612056990435613, 1054488497740116294),
        25,
        -5,
        "2021-04-07T00:19:54.645Z",
        "2021-04-07T16:50:00.594684Z",
    ),
    (
        (7857558701325028241, 7841273482305469689),
        55,
        -4,
        "2021-04-08T20:04:27.501Z",
        "2021-04-09T19:40:40.804096Z",
    ),
]


def parse_args():
    parser = ArgumentParser("resim")

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

    print("Loading events...")
    total_events = sum(
        len(get_feed_between(start_time, end_time))
        for _, _, _, start_time, end_time in FRAGMENTS
    )
    processed_events = 0

    for rng_state, rng_offset, step, start_time, end_time in FRAGMENTS:
        rng = Rng(rng_state, rng_offset)
        rng.step(step)
        resim = Resim(rng, out_file)
        processed_events += resim.run(start_time, end_time, total_events, processed_events)

        tqdm.write(f"state at end: {rng.get_state_str()}")


if __name__ == "__main__":
    main()
