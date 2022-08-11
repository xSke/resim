from argparse import ArgumentParser
from multiprocessing import Pool, Queue
from os.path import splitext
from queue import Empty
from sys import stdout
from tqdm import tqdm
from typing import Optional

from data import get_feed_between
from resim import Resim
from rng import Rng

# (s0, s1), rng offset, event offset, start timestamp, end timestamp
FRAGMENTS = [
    # SEASON 12:
    # missing S12 D1-30. many deploys in this range, and some missing chron events
    ((2887724892689068370, 7824040834361231079), 49, 0, "2021-03-02T23:00:00.000Z", "2021-03-03T16:50:00.000Z"),
    # deploy at 2021-03-03T16:50:00Z
    ((9516845697228190797, 6441957190109821557), 10, 0, "2021-03-03T17:00:00.000Z", "2021-03-04T02:50:00.000Z"),
    # deploy at 2021-03-04T02:45:00Z
    ((3898039635056169634, 13636121169112427915), 10, 0, "2021-03-04T03:00:00.000Z", "2021-03-04T04:50:00Z"),
    # deploy at 2021-03-04T04:50:00Z
    ((6354326472372730027, 3011744895320117042), 10, 0, "2021-03-04T05:00:00.000Z", "2021-03-04T18:50:00.000Z"),
    # deploy at 2021-03-04T18:55:00Z
    ((617776737860945499, 6965272805741501853), 10, 0, "2021-03-04T19:00:00.000Z", "2021-03-05T19:15:00.000Z"),
    # mid-game restart during S12D98, between 2021-03-05T19:14:36.000Z and 2021-03-05T19:15:10.091Z
    ((3038364565806058511, 15510617008273015236), 0, 0, "2021-03-05T19:15:00.000Z", "2021-03-05T21:50:16.083Z"),
    ((11460721463282082147, 11936110632627786929), 53, 0, "2021-03-05T22:00:00Z", "2021-03-06T18:50:00.000Z"),
    ((15344562644745423164, 10882960106955666841), 23, 0, "2021-03-06T20:00:00Z", "2021-03-06T23:50:00.000Z"),
    # SEASON 13:
    ((2300985152363521761, 16070535759624553037), 0, 0, "2021-03-08T16:00:00.000Z", "2021-03-09T01:50:00.000Z"),
    # deploy at 2021-03-09T01:55:00Z
    ((12625543386802094591, 8574312021167992434), 12, 0, "2021-03-09T02:00:00.000Z", "2021-03-09T15:50:00.000Z"),
    # we're missing most of day 25 for some reason. resume on day 26
    ((2011003944438535900, 1095087939505767591), 3, 0, "2021-03-09T17:00:00.000Z", "2021-03-09T20:50:00.000Z"),
    # deploy at 2021-03-09T20:50:00Z
    ((2154942915490753213, 4636043162326033301), 13, 0, "2021-03-09T21:00:00.000Z", "2021-03-10T21:22:00.000Z"),
    # mid-game restart during S13D53, between 2021-03-10T21:21:45.575Z and 2021-03-10T21:22:18.985Z
    ((15380396381966399715, 13714309750257610776), 0, 0, "2021-03-10T21:22:00.000Z", "2021-03-11T14:50:00.000Z"),
    # deploy at 2021-03-11T14:55:00Z
    ((7021708722608607714, 3158314368145462130), 12, 0, "2021-03-11T15:00:00.000Z", "2021-03-12T00:55:00.000Z"),
    # S13 D80 is a separate fragment for some reason
    ((14557622918943320291, 14569056651611896317), 12, 0, "2021-03-12T01:00:00.000Z", "2021-03-12T01:50:00Z"),
    # deploy at 2021-03-12T01:50:00Z
    ((11529751786223941563, 7398827681552859473), 12, 0, "2021-03-12T02:00:00.000Z", "2021-03-12T09:21:30.000Z"),
    # mid-game restart during S12D88, between 2021-03-12T09:21:22.163Z and 2021-03-12T09:21:46.082Z.
    # For some reason the range 09:24:00-09:24:10 is impossible for me to align with what's after it.
    # I don't know why! So there's about 4 minutes missing in day 88.
    ((17262598579754601440, 1372102753813730563), 34, -4, "2021-03-12T09:25:21.623Z", "2021-03-12T19:50:00.000Z"),
    # deploy at 2021-03-12T19:50:00Z
    ((12600639729467795539, 6003152159250863900), 0, 0, "2021-03-12T20:00:00.000Z", "2021-03-13T01:50:00Z"),
    # No listed deploy, but there seems to be a break between S13D103 and D104
    ((12572462612291142032, 12133846605477681375), 8, 0, "2021-03-13T02:00:00.000Z", "2021-03-14T04:05:00Z"),
    # deploy at 2021-03-14T04:05:00Z
    # SEASON 14:
    ((8640116423355544309, 9923965671729542710), 0, 0, "2021-03-15T15:00:00.000Z", "2021-03-15T20:55:29.050219Z"),
    ((12335197627095558518, 4993735724122314585), 11, -1, "2021-03-15T21:00:00.000Z", "2021-03-16T15:50:01.111345Z"),
    # deploy at 2021-03-16T16:20:00Z
    ((3707231913994734955, 16004224931998739944), 51, 0, "2021-03-16T18:00:00Z", "2021-03-16T20:50:00.000Z"),
    ((16935077139086615170, 7227318407464058534), 12, 0, "2021-03-16T21:00:00.000Z", "2021-03-17T18:50:07.535Z"),
    # deploy at 2021-03-17T18:50:00Z
    # deploy at 2021-03-17T19:55:00Z
    ((5750154725705680658, 7572065454551339919), 12, 0, "2021-03-17T20:00:00Z", "2021-03-18T14:50:37.673409Z"),
    # deploy at 2021-03-18T14:50:00Z
    ((14329231552902792263, 18343048993884457641), 12, 0, "2021-03-18T15:00:00Z", "2021-03-18T17:40:00.966Z"),
    # deploy at 2021-03-18T17:40:00Z
    ((16471765453082535911, 290065450250321384), 12, 0, "2021-03-18T18:00:00Z", "2021-03-18T18:50:51.385Z"),
    # deploy at 2021-03-18T18:50:00Z
    # deploy at 2021-03-18T19:10:00Z
    ((4843171135789851264, 15316903146384693430), 4, 0, "2021-03-18T19:13:02.179Z", "2021-03-18T21:50:02.180Z"),
    # deploy at 2021-03-18T22:00:00Z
    ((18280451156624678684, 16123465889931048163), 2, 0, "2021-03-18T22:01:16.566Z", "2021-03-19T00:56:16.567Z"),
    ((4369050506664465536, 4603334513036430167), 12, 0, "2021-03-19T01:00:00.000Z", "2021-03-19T18:40:01.593947Z"),
    # 2021-03-19T18:50:00Z
    ((1705402211782391315, 14786618665043368424), 63, 0, "2021-03-19T19:00:00Z", "2021-03-19T19:19:26.102Z"),
    # Mid-game restart during S14D99
    ((17332235655028997556, 6510596254177638633), 6, 0, "2021-03-19T19:20:09.000Z", "2021-03-20T19:50:01.020Z"),
    # SEASON 15:
    ((1572775861984790377, 14927238043745363817), 3, 0, "2021-04-06T01:00:00Z", "2021-04-06T16:50:21.741Z"),
    # deploy at 2021-04-06T16:50:00Z
    ((705849102323218551, 7687257484569362016), 7, 0, "2021-04-06T17:14:23.856Z", "2021-04-06T22:50:01.740Z"),
    # deploy at 2021-04-06T22:50:00Z
    ((13606427098695492650, 9537038708173591254), 62, 0, "2021-04-06T23:00:00Z", "2021-04-07T16:50:00.594684Z"),
    # deploy at 2021-04-07T16:55:00Z
    ((6033393494486318410, 6992320288130472062), 62, 0, "2021-04-07T17:00:00Z", "2021-04-07T22:50:13.341Z"),
    ((5082886454574003662, 2374945375831325277), 62, 0, "2021-04-07T23:00:00Z", "2021-04-08T01:50:56.946Z"),
    # deploy at 2021-04-08T02:00:00Z
    ((818230392324657822, 13958695923778937231), 50, -12, "2021-04-08T02:00:00.000Z", "2021-04-08T14:50:46.446Z"),
    ((14089361583866000722, 2263563325949770448), 62, 0, "2021-04-08T15:00:00Z", "2021-04-08T17:26:00.000Z"),
    # deploy at 2021-04-08T19:50:00Z
    ((11947114742050313518, 14817598476034896117), 62, 0, "2021-04-08T20:00:00.000Z", "2021-04-09T19:40:40.804096Z"),
    ((11741473536472310906, 13138857156664992063), 50, 0, "2021-04-09T21:00:00Z", "2021-04-10T20:50:43.708Z"),
]

PROGRESS_QUEUE: Optional[Queue] = None


def parse_args():
    parser = ArgumentParser("resim")

    parser.add_argument("outfile", nargs="?", default="-")
    parser.add_argument("--silent", default=False, action="store_true")
    parser.add_argument("--no-multiprocessing", "-no", default=False, action="store_true")
    parser.add_argument("--jobs", "-j", default=None)

    return parser.parse_args()


def get_out_file(silent, out_file_name, start_time):
    if silent:
        return None
    if out_file_name == "-":
        return stdout

    basic_filename, extension = splitext(out_file_name)
    filename = f"{basic_filename}-{start_time.replace(':', '_')}{extension}"
    return open(filename, "w")


def main():
    args = parse_args()

    print("Counting events...")
    total_events = sum(
        len(get_feed_between(start_time, end_time))
        for _, _, _, start_time, end_time in tqdm(FRAGMENTS, unit=" fragments")
    )

    print("Running resim...")
    with tqdm(total=total_events, unit=" events", unit_scale=True) as progress:
        all_pool_args = [((args.silent, args.outfile), fragment) for fragment in FRAGMENTS]
        if args.no_multiprocessing:
            for pool_args in all_pool_args:
                run_fragment(pool_args, progress_callback=lambda: progress.update())
        else:
            global PROGRESS_QUEUE  # not really necessary but it gets rid of the shadowing warning in pycharm
            PROGRESS_QUEUE = Queue()
            processes = int(args.jobs) if args.jobs else None
            with Pool(processes=processes, initializer=init_pool_worker, initargs=(PROGRESS_QUEUE,)) as pool:
                result = pool.map_async(run_fragment, all_pool_args)
                while not result.ready():
                    try:
                        new_progress = PROGRESS_QUEUE.get(timeout=1)
                    except Empty:
                        pass  # Check loop condition and wait again
                    else:
                        progress.update(new_progress)
                result.get()  # reraise any exception from the processes
    print("Finished")


def init_pool_worker(init_args):
    global PROGRESS_QUEUE
    PROGRESS_QUEUE = init_args


def run_fragment(pool_args, progress_callback=None):
    (silent, out_file_name), (rng_state, rng_offset, step, start_time, end_time) = pool_args
    out_file = get_out_file(silent, out_file_name, start_time)
    rng = Rng(rng_state, rng_offset)
    rng.step(step)
    resim = Resim(rng, out_file, start_time, False)

    unreported_progress = 0

    if progress_callback is None:

        def progress_callback():
            nonlocal unreported_progress
            unreported_progress += 1
            if PROGRESS_QUEUE and unreported_progress > 100:
                PROGRESS_QUEUE.put(unreported_progress)
                unreported_progress = 0

    resim.run(start_time, end_time, progress_callback)

    if out_file:
        out_file.close()

    if PROGRESS_QUEUE:
        PROGRESS_QUEUE.put(unreported_progress)


if __name__ == "__main__":
    main()
