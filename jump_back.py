import bisect
import datetime
import io
import re
import sys
from argparse import ArgumentParser

from tqdm import tqdm

from data import get_feed_between
from resim import Resim
from rng import Rng

# (season1indexed, day1indexed): (s0, s1), rng offset, event offset, start timestamp, end timestamp
FRAGMENTS = {
    (12, 31): (
        (2887724892689068370, 7824040834361231079),
        49,
        0,
        "2021-03-02T23:00:00.000Z",
        "2021-03-03T16:50:00.000Z",
    ),
    (12, 49): (
        (9516845697228190797, 6441957190109821557),
        10,
        0,
        "2021-03-03T17:00:00.000Z",
        "2021-03-04T02:50:00.000Z",
    ),
    (12, 59): ((3898039635056169634, 13636121169112427915), 10, 0, "2021-03-04T03:00:00.000Z", "2021-03-04T04:50:00Z"),
    (12, 61): (
        (6354326472372730027, 3011744895320117042),
        10,
        0,
        "2021-03-04T05:00:00.000Z",
        "2021-03-04T18:50:00.000Z",
    ),
    (12, 74): (
        (617776737860945499, 6965272805741501853),
        10,
        0,
        "2021-03-04T19:00:00.000Z",
        "2021-03-05T18:50:00.000Z",
    ),
    (12, 99): (
        (3038364565806058511, 15510617008273015236),
        0,
        0,
        "2021-03-05T19:15:00.000Z",
        "2021-03-05T21:50:16.083Z",
    ),
    (12, 100): (
        (11460721463282082147, 11936110632627786929),
        53,
        0,
        "2021-03-05T22:00:00Z",
        "2021-03-06T18:50:00.000Z",
    ),
    (12, 113): (
        (15344562644745423164, 10882960106955666841),
        23,
        0,
        "2021-03-06T20:00:00Z",
        "2021-03-06T23:50:00.000Z",
    ),
    (13, 1): (
        (2300985152363521761, 16070535759624553037),
        0,
        0,
        "2021-03-08T16:00:00.000Z",
        "2021-03-09T01:50:00.000Z",
    ),
    (13, 11): (
        (12625543386802094591, 8574312021167992434),
        12,
        0,
        "2021-03-09T02:00:00.000Z",
        "2021-03-09T15:55:36.383Z",
    ),
    (13, 26): (
        (2011003944438535900, 1095087939505767591),
        3,
        0,
        "2021-03-09T17:00:00.000Z",
        "2021-03-09T20:55:06.564Z",
    ),
    (13, 29): (
        (2154942915490753213, 4636043162326033301),
        13,
        0,
        "2021-03-09T21:00:00.000Z",
        "2021-03-10T17:50:00.000Z",
    ),
    (13, 55): (
        (1143687300213917959, 12208036940695363993),
        14,
        0,
        "2021-03-10T23:00:00.000Z",
        "2021-03-11T14:50:23.219Z",
    ),
    (13, 71): (
        (7021708722608607714, 3158314368145462130),
        12,
        0,
        "2021-03-11T15:00:00.000Z",
        "2021-03-12T00:55:00.000Z",
    ),
    (13, 80): ((14557622918943320291, 14569056651611896317), 12, 0, "2021-03-12T01:00:00.000Z", "2021-03-12T01:50:00Z"),
    (13, 81): (
        (11529751786223941563, 7398827681552859473),
        12,
        0,
        "2021-03-12T02:00:00.000Z",
        "2021-03-12T08:50:00.000Z",
    ),
    (13, 88): (
        (15495895054824058759, 4871154255711180465),
        20,
        0,
        "2021-03-12T09:24:10.000Z",
        "2021-03-12T19:50:00.000Z",
    ),
    (13, 99): ((12600639729467795539, 6003152159250863900), 0, 0, "2021-03-12T20:00:00.000Z", "2021-03-13T01:50:00Z"),
    (13, 103): (
        (12572462612291142032, 12133846605477681375),
        8,
        0,
        "2021-03-13T02:00:00.000Z",
        "2021-03-13T03:50:00.000Z",
    ),
    (14, 1): (
        (8640116423355544309, 9923965671729542710),
        0,
        0,
        "2021-03-15T15:00:00.000Z",
        "2021-03-15T20:55:29.050219Z",
    ),
    (14, 7): (
        (12335197627095558518, 4993735724122314585),
        11,
        0,
        "2021-03-15T21:00:00.000Z",
        "2021-03-16T15:50:01.111345Z",
    ),
    (14, 27): ((3707231913994734955, 16004224931998739944), 51, 0, "2021-03-16T18:00:00Z", "2021-03-16T20:50:00.000Z"),
    (14, 30): (
        (16935077139086615170, 7227318407464058534),
        12,
        0,
        "2021-03-16T21:00:00.000Z",
        "2021-03-17T18:50:07.535Z",
    ),
    (14, 53): (
        (5750154725705680658, 7572065454551339919),
        12,
        0,
        "2021-03-17T20:00:00Z",
        "2021-03-18T14:50:37.673409Z",
    ),
    (14, 72): ((14329231552902792263, 18343048993884457641), 12, 0, "2021-03-18T15:00:00Z", "2021-03-18T17:40:00.966Z"),
    (14, 74): ((16471765453082535911, 290065450250321384), 12, 0, "2021-03-18T18:00:00Z", "2021-03-18T18:50:51.385Z"),
    (14, 75): (
        (4843171135789851264, 15316903146384693430),
        4,
        0,
        "2021-03-18T19:13:02.179Z",
        "2021-03-18T21:50:02.180Z",
    ),
    (14, 78): (
        (18280451156624678684, 16123465889931048163),
        2,
        0,
        "2021-03-18T22:01:16.566Z",
        "2021-03-19T00:56:16.567Z",
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
    (15, 11): ((1572775861984790377, 14927238043745363817), 3, 0, "2021-04-06T01:00:00Z", "2021-04-06T16:50:21.741Z"),
    (15, 27): ((705849102323218551, 7687257484569362016), 7, 0, "2021-04-06T17:14:23.856Z", "2021-04-06T22:50:01.740Z"),
    (15, 32): (
        (13606427098695492650, 9537038708173591254),
        62,
        0,
        "2021-04-06T23:00:00Z",
        "2021-04-07T16:50:00.594684Z",
    ),
    (15, 50): ((6033393494486318410, 6992320288130472062), 62, 0, "2021-04-07T17:00:00Z", "2021-04-07T22:50:13.341Z"),
    (15, 56): ((873888464726294679, 5073549791281365445), 1, 0, "2021-04-07T23:02:56.945Z", "2021-04-08T01:50:56.946Z"),
    (15, 59): (
        (8647969112849402168, 10186261583749935565),
        8,
        0,
        "2021-04-08T02:02:46.445Z",
        "2021-04-08T14:50:46.446Z",
    ),
    (15, 72): (
        (8489967719453290970, 3893844245093569562),
        3,
        0,
        "2021-04-08T15:00:51.613Z",
        "2021-04-08T17:26:00.000Z",
    ),
    (15, 78): (
        (11947114742050313518, 14817598476034896117),
        62,
        0,
        "2021-04-08T20:00:00.000Z",
        "2021-04-09T19:40:40.804096Z",
    ),
    (15, 100): (
        (11741473536472310906, 13138857156664992063),
        50,
        0,
        "2021-04-09T21:00:00Z",
        "2021-04-10T20:50:43.708Z",
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
    parser.add_argument("--rolls", nargs="?", type=int, default=-1)

    return parser.parse_args()


def main():
    args = parse_args()
    out_file = io.StringIO()

    fragment_key = None

    if args.start:
        match = re.match(r"[sS]([0-9]{1,2})[dD]([0-9]{1,3})", args.start)
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
            print(f"S{season}D{day}")
        exit()

    fragment = FRAGMENTS[fragment_key]
    end_time = fragment[3]

    with open("deploys.txt", "r") as deploys_file:
        deploy_times = sorted([line.strip() for line in deploys_file])

    if args.start_time:
        start_time = args.start_time
    else:
        start_time = datetime.datetime.fromisoformat(fragment[3][:-1])
        start_time = start_time.replace(minute=0, second=0, microsecond=0) - datetime.timedelta(hours=args.jump_hours)
        start_time = start_time.isoformat() + "Z"

    i = bisect.bisect_left(deploy_times, start_time)
    if i != len(deploy_times) and deploy_times[i] < end_time:
        print(f"This range spans a known deploy time at {deploy_times[i]}! It probably won't work.")
        return

    print("Loading events...")
    total_events = len(get_feed_between(start_time, end_time))

    rng_state, rng_offset, step, _, fragment_end_time = fragment

    if args.rolls > 0:
        rolls = args.rolls
    else:
        print(f"Estimating roll count...")

        rng = Rng(rng_state, rng_offset)
        rng.step(step)
        with (RngCountContext(rng) as rng_counter, tqdm(total=total_events, unit="events") as _):
            resim = Resim(rng, None, start_time, raise_on_errors=False)
            resim.run(start_time, end_time, progress_callback=None)
            rolls = rng_counter.count
            tqdm.write(f"rolls used: {rolls}")

    rng = Rng(rng_state, rng_offset)
    rng.step(step)
    print(f"Starting at state: {rng.get_state_str()} and jumping back {rolls}")
    rng.step(-rolls)
    print(f"to state {rng.get_state_str()}")
    s0, s1, offset = rng.get_state()
    with (RngCountContext(rng) as rng_counter, tqdm(total=total_events, unit="events") as _):
        resim = Resim(rng, out_file, start_time, raise_on_errors=False)
        resim.run(start_time, end_time, progress_callback=None)
        tqdm.write(f"rolls used: {rng_counter.count}/{rolls}")
        tqdm.write(f"state at end: {rng.get_state_str()}")

    found_incorrect = False
    offsets = {n for n in range(-63, 64)}
    out_file.seek(0)
    for line in out_file:
        if not found_incorrect:
            if re.match("Error:\s*incorrect fielder!", line):
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
            print(f'Looks correct to me! (({s0}, {s1}), {offset}, 0, "{start_time}", "{fragment_end_time}")')
            with open("jump.txt", "w") as out:
                out.write(out_file.getvalue())
        else:
            possible_rolls = [rolls - offset for offset in offsets]
            print(f"Multiple offsets possible. Try again with --rolls set to one of {possible_rolls}")
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
    with (RngCountContext(rng) as rng_counter, tqdm(total=total_events, unit="events") as _):
        resim = Resim(rng, out_file, start_time, raise_on_errors=False)
        resim.run(start_time, end_time, progress_callback=None)
        tqdm.write(f"rolls used: {rng_counter.count}/{rolls}")
        tqdm.write(f"state at end: {rng.get_state_str()}")

    out_file.seek(0)
    for line in out_file:
        if re.match("Error:\s*incorrect fielder!", line):
            print("That didn't work! It might not be reachable or may have other errors.")
            with open("jump.txt", "w") as out:
                out.write(out_file.getvalue())
            return

    print(f'Looks correct to me! (({s0}, {s1}), {offset}, 0, "{start_time}", "{fragment_end_time}")')
    with open("jump.txt", "w") as out:
        out.write(out_file.getvalue())


if __name__ == "__main__":
    main()
