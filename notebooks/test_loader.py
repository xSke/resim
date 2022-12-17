from notebooks import load


def _test():
    print("Loading data")
    df = load.data("strikes", season=18)
    print("Loaded dataframe")

    df["ruth_scaled"] = load.attribute(
        # These values are mandatory: the dataframe, the player role, and the attribute
        df, 'pitcher', 'ruthlessness',
        # These are all optional, and the default values are as they appear here
        vibes=True, mods=True, items=True, broken_items=False
    )
    print("Got ruth")
    df["musc_scaled"] = load.attribute(df, 'batter', 'musclitude', items=False)
    print("Got musc")

    pass


if __name__ == '__main__':
    _test()
