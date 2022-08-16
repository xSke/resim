import glob
import itertools
import json

import matplotlib.pyplot as plt
from dateutil import parser


def load_data(season=None):
    for file in glob.glob("cache/feed_range_*.json"):
        with open(file) as f:
            for event in json.load(f):
                metadata = event.get("metadata") or {}  # needs to be or!
                if (season is None or event["season"] == season) and "play" in metadata and "parent" not in metadata:
                    yield event


def main():
    def game_extractor(e):
        return e["gameTags"][0]

    first_day = parser.isoparse("2021-03-02T23:00:00.528Z").replace(microsecond=0, second=0, minute=0)
    event_groups = itertools.groupby(sorted(load_data(11), key=game_extractor), key=game_extractor)

    fig, ax = plt.subplots(1)
    lines = {}
    for _, events in event_groups:
        events = list(events)  # realize iterator
        (line,) = ax.plot(
            [(parser.isoparse(e["created"]) - first_day).total_seconds() for e in events],
            [e["metadata"]["play"] for e in events],
            marker="o",
            picker=True,
        )
        lines[line] = events

    ax.set_title("Time vs. Play")
    ax.set_xlabel("seconds past start of era")
    ax.set_ylabel("play")

    def onpick1(event):
        nonlocal lines
        pass

    fig.canvas.mpl_connect("pick_event", onpick1)

    plt.show()


if __name__ == "__main__":
    main()
