import sys
from argparse import ArgumentParser

from tqdm import tqdm

from data import get_feed_between
from resim import Resim
from rng import Rng

# (s0, s1), rng offset, event offset, start timestamp, end timestamp
FRAGMENTS = [
    (
        (617776737860945499, 6965272805741501853),
        10,
        0,
        "2021-03-04T19:00:00.000Z",
        "2021-03-05T18:50:00Z",
    ),
    (
        (2154942915490753213, 4636043162326033301),
        13,
        0,
        "2021-03-09T21:00:00.000Z",
        "2021-03-10T17:50:00Z",
    ),
    ((5095508329287756819, 32976085265396020), 42, -3, "2021-03-15T15:08:28.092Z", "2021-03-15T20:55:29.050219Z"),
    (
        (12335197627095558518, 4993735724122314585),
        11,
        0,
        "2021-03-15T21:00:00.000Z",
        "2021-03-16T15:50:01.111345Z",
    ),
    (
        (16935077139086615170, 7227318407464058534),
        12,
        0,
        "2021-03-16T21:00:00.000Z",
        "2021-03-17T18:50:07.535Z",
    ),
    ((14468423426837303405, 17356458140958552552), 32, -7, "2021-03-17T20:06:33.317Z", "2021-03-18T14:50:37.673409Z"),
    (
        (4369050506664465536, 4603334513036430167),
        12,
        0,
        "2021-03-19T01:00:00.000Z",
        "2021-03-19T18:40:01.593947Z",
    ),
    (
        (4742777402478590244, 2004520124933634673),
        22,
        0,
        "2021-03-19T21:00:00.000Z",
        "2021-03-20T19:50:01.020Z",
    ),
    (
        (9668656808250152634, 9027125133720942837),
        27,
        0,
        "2021-04-07T00:00:00.000Z",
        "2021-04-07T16:50:00.594684Z",
    ),
    (
        (11947114742050313518, 14817598476034896117),
        62,
        0,
        "2021-04-08T20:00:00.000Z",
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
    total_events = sum(len(get_feed_between(start_time, end_time)) for _, _, _, start_time, end_time in FRAGMENTS)

    with tqdm(total=total_events, unit="events") as progress:
        for rng_state, rng_offset, step, start_time, end_time in FRAGMENTS:
            rng = Rng(rng_state, rng_offset)
            rng.step(step)
            resim = Resim(rng, out_file, start_time)
            resim.run(
                start_time,
                end_time,
                progress,
            )

            tqdm.write(f"state at end: {rng.get_state_str()}")

        progress.close()


if __name__ == "__main__":
    main()
