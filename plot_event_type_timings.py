import glob
import itertools
import json
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np
from dateutil import parser

from data import EventType

def load_data(season=None):
    for file in glob.glob("cache/feed_range_*.json"):
        with open(file) as f:
            for event in json.load(f):
                metadata = event.get("metadata") or {}  # needs to be or!
                if (season is None or event["season"] == season) and "play" in metadata and not "parent" in metadata:
                    yield event

def main():
    def game_extractor(e):
        return e["gameTags"][0]

    first_day = parser.isoparse("2021-03-02T23:00:00.528Z").replace(microsecond=0, second=0, minute=0)
    event_groups = itertools.groupby(sorted(load_data(11), key=game_extractor), key=game_extractor)

    timings = defaultdict(lambda: [])
    for _, events in event_groups:
        events = list(events)  # realize iterator
        diffs = np.diff([(parser.isoparse(e["created"]) - first_day).total_seconds() for e in events])
        for event, diff in zip(events, diffs):
            timings[event["type"]].append(diff)

    fig, ax = plt.subplots(1)
    x_labels = list(timings.keys())
    x_map = {k: i for i, k in enumerate(x_labels)}
    # x, y = zip(*[(x_map[type_num], time) for type_num, type_timings in timings.items() for time in type_timings])

    ax.violinplot(timings.values(), positions=range(len(x_labels)))
    ax.set_xticks(range(len(x_labels)))
    ax.set_xticklabels([EventType(l).name for l in x_labels], rotation='vertical')
    ax.set_ylabel("Time Visible (s)")
    ax.set_xlabel("Event type")
    ax.grid(visible=True, which="major", axis="x")
    plt.show()


if __name__ == '__main__':
    main()