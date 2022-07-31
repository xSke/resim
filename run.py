import os.path
import sys
from argparse import ArgumentParser
from multiprocessing import Pool, Queue
from queue import Empty
from typing import Optional

from tqdm import tqdm

from data import get_feed_between, clear_cache
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
    # missing S12, D59-60
    # deploy at 2021-03-04T04:50:00Z
    ((6354326472372730027, 3011744895320117042), 10, 0, "2021-03-04T05:00:00.000Z", "2021-03-04T18:50:00.000Z"),
    # deploy at 2021-03-04T18:55:00Z
    ((617776737860945499, 6965272805741501853), 10, 0, "2021-03-04T19:00:00.000Z", "2021-03-05T19:15:00.000Z"),
    # mid-game restart during S12D98, between 2021-03-05T19:14:36.000Z and 2021-03-05T19:15:10.091Z
    ((3038364565806058511, 15510617008273015236), 0, 0, "2021-03-05T19:15:00.000Z", "2021-03-05T21:50:16.083Z"),
    # SEASON 13 AND ONWARDS:
    ((15819463886378824242, 11850886188069526871), 9, 0, "2021-03-08T17:04:57.550Z", "2021-03-09T01:50:57.551Z"),
    ((15858664899397396766, 619122154140040263), 5, 0, "2021-03-09T02:02:36.382Z", "2021-03-09T15:55:36.383Z"),
    ((16364842411103381454, 16179153396435521255), 8, 0, "2021-03-09T17:03:06.563Z", "2021-03-09T20:55:06.564Z"),
    ((2154942915490753213, 4636043162326033301), 13, 0, "2021-03-09T21:00:00.000Z", "2021-03-10T21:20:00Z"),
    ((17639552178218848566, 8391217557840075372), 5, 0, "2021-03-10T23:11:23.218Z", "2021-03-11T14:50:23.219Z"),
    ((10731968714428277408, 12193732956530947526), 17, -5, "2021-03-11T15:02:16.420Z", "2021-03-12T00:55:00.732891Z"),
    ((14997421231000846557, 6948546834455329883), 4, -5, "2021-03-12T02:03:36.808Z", "2021-03-12T08:50:00.772Z"),
    ((17262598579754601440, 1372102753813730563), 34, -4, "2021-03-12T09:25:21.623Z", "2021-03-12T19:50:00.533701Z"),
    ((5095508329287756819, 32976085265396020), 42, -3, "2021-03-15T15:08:28.092Z", "2021-03-15T20:55:29.050219Z"),
    ((12335197627095558518, 4993735724122314585), 11, 0, "2021-03-15T21:00:00.000Z", "2021-03-16T15:50:01.111345Z"),
    ((16935077139086615170, 7227318407464058534), 12, 0, "2021-03-16T21:00:00.000Z", "2021-03-17T18:50:07.535Z"),
    ((14468423426837303405, 17356458140958552552), 32, -7, "2021-03-17T20:06:33.317Z", "2021-03-18T14:50:37.673409Z"),
    ((4403765249735152399, 17018887391322156297), 14, 0, "2021-03-18T17:04:00.965Z", "2021-03-18T17:40:00.966Z"),
    ((9733931392370034103, 16392834050372619327), 10, 0, "2021-03-18T18:00:41.486Z", "2021-03-18T18:50:51.385Z"),
    ((4843171135789851264, 15316903146384693430), 4, 0, "2021-03-18T19:13:02.179Z", "2021-03-18T21:50:02.180Z"),
    ((18280451156624678684, 16123465889931048163), 2, 0, "2021-03-18T22:01:16.566Z", "2021-03-19T00:56:16.567Z"),
    ((4369050506664465536, 4603334513036430167), 12, 0, "2021-03-19T01:00:00.000Z", "2021-03-19T18:40:01.593947Z"),
    ((4742777402478590244, 2004520124933634673), 22, 0, "2021-03-19T21:00:00.000Z", "2021-03-20T19:50:01.020Z"),
    ((6772988763998663109, 3994574971726895235), 9, 0, "2021-04-06T01:06:21.740Z", "2021-04-06T16:50:21.741Z"),
    ((705849102323218551, 7687257484569362016), 7, 0, "2021-04-06T17:14:23.856Z", "2021-04-06T22:50:01.740Z"),
    ((9668656808250152634, 9027125133720942837), 27, -25, "2021-04-07T00:00:00.000Z", "2021-04-07T16:50:00.594684Z"),
    ((16372771682748790520, 2579045391505814533), 2, 0, "2021-04-07T17:06:13.340Z", "2021-04-07T22:50:13.341Z"),
    ((873888464726294679, 5073549791281365445), 1, 0, "2021-04-07T23:02:56.945Z", "2021-04-08T01:50:56.946Z"),
    ((8647969112849402168, 10186261583749935565), 8, 0, "2021-04-08T02:02:46.445Z", "2021-04-08T14:50:46.446Z"),
    ((8489967719453290970, 3893844245093569562), 3, 0, "2021-04-08T15:00:51.613Z", "2021-04-08T17:26:00.000Z"),
    ((11947114742050313518, 14817598476034896117), 62, 0, "2021-04-08T20:00:00.000Z", "2021-04-09T19:40:40.804096Z"),
]

progress_queue: Optional[Queue] = None


def parse_args():
    parser = ArgumentParser("resim")

    parser.add_argument("outfile", nargs="?", default="-")
    parser.add_argument("--silent", default=False, action="store_true")
    parser.add_argument("--no-multiprocessing", default=False, action="store_true")

    return parser.parse_args()


def get_out_file(silent, out_file_name, start_time):
    if silent:
        return None
    elif out_file_name == "-":
        return sys.stdout

    basic_filename, extension = os.path.splitext(out_file_name)
    filename = f"{basic_filename}-{start_time.replace(':', '_')}{extension}"
    return open(filename, "w")


def main():
    args = parse_args()

    print("Loading events...")
    total_events = sum(len(get_feed_between(start_time, end_time)) for _, _, _, start_time, end_time in FRAGMENTS)

    with tqdm(total=total_events, unit="events") as progress:
        if args.no_multiprocessing:

            def progress_callback():
                progress.update()

            for fragment in FRAGMENTS:
                run_fragment(((args.silent, args.outfile), fragment), progress_callback=progress_callback)
        else:
            global progress_queue  # not really necessary but it gets rid of the shadowing warning in pycharm
            progress_queue = Queue()
            with Pool(initializer=init_pool_worker, initargs=(progress_queue,)) as pool:
                fragments_and_args = [((args.silent, args.outfile), fragment) for fragment in FRAGMENTS]
                result = pool.map_async(run_fragment, fragments_and_args)

                while not result.ready():
                    try:
                        new_progress = progress_queue.get(timeout=1)
                    except Empty:
                        pass  # Check loop condition and wait again
                    else:
                        progress.update(new_progress)


def init_pool_worker(init_args):
    global progress_queue
    progress_queue = init_args


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
            if progress_queue and unreported_progress > 100:
                progress_queue.put(unreported_progress)
                unreported_progress = 0

    resim.run(start_time, end_time, progress_callback)

    if out_file:
        out_file.close()

    if progress_queue:
        progress_queue.put(unreported_progress)
    print(f"state at end: {rng.get_state_str()}")
    clear_cache()


if __name__ == "__main__":
    main()
