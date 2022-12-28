import load


def _test():
    df = load.data("strikes", season=18)

    df["ruth_scaled"] = load.player_attribute(
        # These values are mandatory: the dataframe, the player role, and the attribute
        df, 'pitcher', 'ruthlessness',
        # These are all optional, and the default values are as they appear here
        vibes=True, mods=True, items=True, broken_items=False
    )
    df["musc_scaled"] = load.player_attribute(df, 'batter', 'musclitude', items=False)
    df["musc_scaled_n"] = load.player_attribute(df, 'batter', 'musclitude', items="negative")

    # center=True is the default
    df["forwardness"] = load.stadium_attribute(df, 'forwardness', center=True)

    pass


if __name__ == '__main__':
    _test()
