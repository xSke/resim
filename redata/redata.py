import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))  # can't figure out the module system rn

from rng import Rng
from data import GameData, get_cached
from redata.constants import (
    S3_ALLERGY_FIXUP,
    ATTR_ORDER_GEN,
    S1_PLAYER_NAMES,
    ORIGINAL_TEAM_ORDER,
    S1_TEAM_DATA,
    BATTING_ATTR_BLOCK,
    PITCHING_ATTR_BLOCK,
    BASERUNNING_ATTR_BLOCK,
    DEFENSE_ATTR_BLOCK,
)

LOVERS = "b72f3061-f573-40d7-832a-5ad475bd7909"
TACOS = "878c1bf6-0d21-4659-bfee-916c8314d69c"
STEAKS = "b024e975-1c4a-4575-8936-a3754a08806a"
BREATH_MINTS = "adc5b394-8f76-416d-9ce9-813706877b84"
FIREFIGHTERS = "ca3f1c8c-c025-4d8e-8eef-5be6accbeb16"
SHOE_THIEVES = "bfd38797-8404-4b38-8b82-341da28b1f83"
FLOWERS = "3f8bbb15-61c0-4e3f-8e4a-907a5fb1565e"
FRIDAYS = "979aee4a-6d80-4863-bf1c-ee1a78e06024"
MAGIC = "7966eb04-efcc-499b-8f03-d13916330531"
MILLENNIALS = "36569151-a2fb-43c1-9df7-2df512424c82"
CRABS = "8d87c468-699a-47a8-b40d-cfb73a5660ad"
PIES = "23e4cbc1-e9cd-47fa-a35b-bfa06f726cb7"
SUNBEAMS = "f02aeae2-5e6a-4098-9842-02d2273f25c7"
WILD_WINGS = "57ec08cc-0411-4643-b304-0e80dbc15ac7"
TIGERS = "747b8e4a-7e50-4638-a973-ea7950a3e739"
MOIST_TALKERS = "eb67ae5e-c4bf-46ca-bbbc-425cd34182ff"
SPIES = "9debc64f-74b7-4ae1-a4d6-fce0144b6ea5"
DALE = "b63be8c2-576a-4d6e-8daf-814f8bcea96f"
GARAGES = "105bc3ff-1320-4e37-8ef0-8d595cb95dd0"
JAZZ_HANDS = "a37f9158-7f82-46bc-908c-c9e2dda7c33b"

CHRONICLER_URI = "https://api.sibr.dev/chronicler"


def generate_player(rng: Rng, id: str, name: str, roll_cinnamon=False, roll_s3=False):
    # we expect an rng value that's pointed to the roll just *before* the first-name roll
    # so that .next() returns that roll
    _first_name_roll = rng.next()
    _last_name_roll = rng.next()
    player = {
        "id": id,
        "name": name,
        "totalFingers": 10,
    }
    for stat in ATTR_ORDER_GEN:
        player[stat] = rng.next()

    if roll_cinnamon:
        player["cinnamon"] = rng.next()

    soul_roll = rng.next()
    player["soul"] = int(soul_roll * 8 + 2)
    return player

def batting_rating(p):
    return ((1 - p["tragicness"]) ** 0.01) * (p["thwackability"] ** 0.35) * (p["moxie"] ** 0.075) * (p["divinity"] ** 0.35) * (p["musclitude"] ** 0.075) * ((1 - p["patheticism"]) ** 0.05) * (p["martyrdom"] ** 0.02)

def pitching_rating(p):
    return (p["shakespearianism"] ** 0.1) * (p["unthwackability"] ** 0.5) * (p["coldness"] ** 0.025) * (p["overpowerment"] ** 0.15) * (p["ruthlessness"] ** 0.4)

def baserunning_rating(p):
    return (p["laserlikeness"] ** 0.5) * (p["continuation"] ** 0.1) * (p["baseThirst"] ** 0.1) * (p["indulgence"] ** 0.1) * (p["groundFriction"] ** 0.1)

def defense_rating(p):
    return (p["omniscience"] ** 0.2) * (p["tenaciousness"] ** 0.2) * (p["watchfulness"] ** 0.1) * (p["anticapitalism"] ** 0.1) * (p["chasiness"] ** 0.1)

def round_rating(rating):
    return round(rating*5*2) / 2

class Redata:
    def __init__(self):
        self.event_log = []

        self.players = {}
        self.teams = {}

        self.gd = GameData()
        pass

    def create_team(self, timestamp, data):
        self._append({"type": "create_team", "timestamp": timestamp, "data": data})

    def create_player(self, timestamp, data):
        self._append({"type": "create_player", "timestamp": timestamp, "data": data})

    def update_team(self, timestamp, id: str, delta: dict):
        self._append({"type": "update_team", "timestamp": timestamp, "team_id": id, "delta": delta})

    def update_player(self, timestamp, id: str, delta: dict):
        self._append({"type": "update_player", "timestamp": timestamp, "player_id": id, "delta": delta})

    def replace_player(self, timestamp: str, team_id: str, old_player_id: str, new_player_id: str):
        self._append(
            {
                "type": "replace_player",
                "timestamp": timestamp,
                "team_id": team_id,
                "old_player_id": old_player_id,
                "new_player_id": new_player_id,
            }
        )

    def player_attr_change(self, timestamp: str, player_id: str, delta: dict, attr_floor=0.01, path_cap=0.99):
        assert all(isinstance(v, float) or isinstance(v, int) for v in delta.values())

        player = self.players[player_id]
        for attr in ATTR_ORDER_GEN + ["cinnamon"]:
            if attr in delta:
                if player[attr] + delta[attr] < attr_floor:
                    delta.pop(attr)
                    self._append(
                        {
                            "type": "update_player",
                            "timestamp": timestamp,
                            "player_id": player_id,
                            "delta": {attr: attr_floor},
                        }
                    )

        if "patheticism" in delta:
            if player["patheticism"] + delta["patheticism"] > path_cap:
                delta.pop("patheticism")
                self._append(
                    {
                        "type": "update_player",
                        "timestamp": timestamp,
                        "player_id": player_id,
                        "delta": {"patheticism": path_cap},
                    }
                )

        self._append(
            {
                "type": "player_attr_change",
                "timestamp": timestamp,
                "player_id": player_id,
                "delta": delta,
            }
        )

    def swap_player(self, timestamp: str, team_a: str, player_a: str, team_b: str, player_b: str):
        self._append(
            {
                "type": "swap_player",
                "timestamp": timestamp,
                "team_a": team_a,
                "player_a": player_a,
                "team_b": team_b,
                "player_b": player_b,
            }
        )

    def incineration(
        self,
        timestamp: str,
        team_id: str,
        old_player_id: str,
        new_player_rng: str,
        new_player_id: str,
        new_player_name: str,
    ):
        rng = Rng.parse(new_player_rng)

        roll_cinnamon = timestamp > "2020-08-03T00:00:00Z"  # s3+
        new_player = generate_player(rng, new_player_id, new_player_name, roll_cinnamon=roll_cinnamon)

        self.create_player(timestamp, new_player)
        self.replace_player(timestamp, team_id, old_player_id, new_player_id)

    def peanut_reaction(self, timestamp: str, player_id: str, amount: float):
        delta = {}
        for attr in BATTING_ATTR_BLOCK + PITCHING_ATTR_BLOCK + BASERUNNING_ATTR_BLOCK + DEFENSE_ATTR_BLOCK:
            if attr == "patheticism":
                delta[attr] = -amount
            else:
                delta[attr] = amount
        delta["totalFingers"] = 1
        self.player_attr_change(timestamp, player_id, delta)

    def yummy(self, timestamp: str, _team_id: str, player_id: str):
        self.peanut_reaction(timestamp, player_id, 0.2)

    def allergic(self, timestamp: str, _team_id: str, player_id: str):
        self.peanut_reaction(timestamp, player_id, -0.2)

    def reroll_attributes(self, timestamp: str, player_id: str, rng: Rng, attributes: list[str]):
        delta = {}
        for attr in attributes:
            delta[attr] = rng.next()
        self.update_player(timestamp, player_id, delta)

    def team_id(self, name: str):
        for t in self.teams.values():
            if t["nickname"] == name:
                return t["id"]
        raise ValueError(f"team not found: {name}")

    def player_id(self, team_name: str, player_name: str):
        team_id = self.team_id(team_name)
        for group_type in ["lineup", "rotation", "bullpen", "bench"]:
            for player_id in self.teams[team_id][group_type]:
                player = self.players[player_id]
                if player["name"] == player_name:
                    return player_id
        raise ValueError(f"player not found: {player_name} (on {team_name})")

    def _append(self, event):
        # player events must apply in ascending timestamp order
        if self.event_log:
            assert self.event_log[-1]["timestamp"] <= event["timestamp"]
        self.event_log.append(event)
        self._replay(event)

    def _replay(self, event):
        ty = event["type"]
        if ty == "create_team":
            self.teams[event["data"]["id"]] = event["data"]
        elif ty == "create_player":
            self.players[event["data"]["id"]] = event["data"]
        elif ty == "update_team":
            # todo: deep update?
            self.teams[event["team_id"]].update(event["delta"])
        elif ty == "update_player":
            # todo: deep update?
            self.players[event["player_id"]].update(event["delta"])
        elif ty == "replace_player":
            team = self.teams[event["team_id"]]
            old_player_id = event["old_player_id"]
            new_player_id = event["new_player_id"]
            for group_type in ["lineup", "rotation", "bullpen", "bench"]:
                if old_player_id in team[group_type]:
                    index = team[group_type].index(old_player_id)
                    team[group_type][index] = new_player_id
                    break
            else:
                raise ValueError(f"couldn't find {old_player_id} in {event['team_id']} roster")
        elif ty == "swap_player":
            team_a = self.teams[event["team_a"]]
            team_b = self.teams[event["team_b"]]

            player_a_pos = self.find_player_in_team(event["team_a"], event["player_a"])
            player_b_pos = self.find_player_in_team(event["team_b"], event["player_b"])
            team_a[player_a_pos[0]][player_a_pos[1]] = event["player_b"]
            team_b[player_b_pos[0]][player_b_pos[1]] = event["player_a"]
        elif ty == "player_attr_change":
            player = self.players[event["player_id"]]
            for k, v in event["delta"].items():
                player[k] += v
                # print(f"{player['name']}/{k} += {v}")

    def find_player_in_team(self, team_id: str, player_id: str):
        team = self.teams[team_id]
        for group_type in ["lineup", "rotation", "bullpen", "bench"]:
            if player_id in team[group_type]:
                index = team[group_type].index(player_id)
                return group_type, index
        raise ValueError(f"could not find player {player_id} in team {team_id} ({team['nickname']})")

    def assert_consistency(self, chron_timestamp: str):

        teams_resp = get_cached(
            f"teams_at_{chron_timestamp}",
            f"{CHRONICLER_URI}/v2/entities?type=team&at={chron_timestamp}&count=1000",
        )
        players_resp = get_cached(
            f"players_at_{chron_timestamp}",
            f"{CHRONICLER_URI}/v2/entities?type=player&at={chron_timestamp}&count=2000",
        )
        chron_teams = {t["entityId"]: t["data"] for t in teams_resp["items"]}
        chron_players = {t["entityId"]: t["data"] for t in players_resp["items"]}

        errors = []
        for player_id, player in self.players.items():
            if player_id not in chron_players:
                # mostly for cases like tyreek olive, etc
                continue
            chron_player = chron_players[player_id]

            for attr in ATTR_ORDER_GEN + ["soul", "name", "totalFingers", "fate", "peanutAllergy", "cinnamon"]:
                if attr == "tragicness":
                    # todo: check this?
                    continue
                if attr not in player or attr not in chron_player:
                    continue
                if chron_player[attr] != player[attr]:
                    errors.append(
                        f"player inconsistent @ {chron_timestamp} @ {player_id}/{attr} ({player['name']}): {chron_player[attr]} (chron) != {player[attr]} (redata)"
                    )

        for team_id, team in self.teams.items():
            chron_team = chron_teams[team_id]

            for attr in ["fullName", "location", "nickname", "lineup", "rotation", "bullpen", "bench", "shorthand"]:
                if chron_team[attr] != team[attr]:
                    errors.append(
                        f"team {team['nickname']} inconsistent @ {chron_timestamp} @ {team_id}/{attr}: {chron_team[attr]} != {team[attr]}"
                    )

        if errors:
            raise ValueError(f"errors:\n{chr(0xa).join(errors)}")


def season_1_election(rd: Redata):
    S1_ELECTION_TIMESTAMP = "2020-07-26T19:00:00Z"

    # The Book Opens.
    # Solar Eclipse.
    # Umpires' eyes turn white.

    # Star player Jaylen Hotdogfingers is incinerated...
    rd.incineration(
        S1_ELECTION_TIMESTAMP,
        GARAGES,
        "04e14d7b-5021-4250-a3cd-932ba8e0a889",
        "6e9cecada970c54f+1",
        "bd9d1d6e-7822-4ad9-bac4-89b8afd8a630",
        "Derrick Krueger",
    )

    # ... Hellmouth swallows the Moab desert...
    rd.update_team(
        S1_ELECTION_TIMESTAMP,
        SUNBEAMS,
        {
            "fullName": "Hellmouth Sunbeams",
            "location": "Hellmouth",
        },
    )

    # THE DISCIPLINE ERA BEGINS.

    # Max out PolkaDot Patterson
    for _ in range(77):
        rd.player_attr_change(
            S1_ELECTION_TIMESTAMP,
            "338694b7-6256-4724-86b6-3884299a5d9e",
            dict(
                shakespearianism=0.01,
                suppression=0.01,
                unthwackability=0.01,
                coldness=0.01,
                overpowerment=0.01,
                ruthlessness=0.01,
                totalFingers=1,
            ),
        )

    # Max out Jessica Telephone
    # IMPORTANT: Jessica did *NOT* receive the Steaks hitting blessing below
    # ...but August Mina didn't either?
    # if you apply this in a way that makes sense (flat 0.1 + 31x 0.01s for max-out), the float bits are wrong
    for _ in range(41):
        rd.player_attr_change(
            S1_ELECTION_TIMESTAMP,
            "083d09d4-7ed3-4100-b021-8fbe30dd43e8",
            dict(
                thwackability=0.01,
                moxie=0.01,
                divinity=0.01,
                musclitude=0.01,
                patheticism=-0.01,
                buoyancy=0.01,
                martyrdom=0.01,
            ),
        )

    for player_id in rd.teams[STEAKS]["lineup"]:
        # Skip JT, see above
        if player_id == "083d09d4-7ed3-4100-b021-8fbe30dd43e8":
            continue
        rd.player_attr_change(
            S1_ELECTION_TIMESTAMP,
            player_id,
            dict(
                thwackability=0.1,
                moxie=0.1,
                divinity=0.1,
                musclitude=0.1,
                patheticism=-0.1,
                buoyancy=0.1,
                martyrdom=0.1,
            ),
        )

    for player_id in rd.teams[CRABS]["lineup"]:
        rd.player_attr_change(
            S1_ELECTION_TIMESTAMP,
            player_id,
            dict(
                thwackability=0.06,
                moxie=0.06,
                divinity=0.06,
                musclitude=0.06,
                patheticism=-0.06,
                buoyancy=0.06,
                baseThirst=0.06,
                laserlikeness=0.06,
                groundFriction=0.06,
                continuation=0.06,
                indulgence=0.06,
                martyrdom=0.06,
                omniscience=0.06,
                tenaciousness=0.06,
                watchfulness=0.06,
                anticapitalism=0.06,
                chasiness=0.06,
            ),
        )

    for player_id in rd.teams[CRABS]["rotation"]:
        rd.player_attr_change(
            S1_ELECTION_TIMESTAMP,
            player_id,
            dict(
                shakespearianism=0.06,
                suppression=0.06,
                unthwackability=0.06,
                coldness=0.06,
                overpowerment=0.06,
                ruthlessness=0.06,
                omniscience=0.06,
                tenaciousness=0.06,
                watchfulness=0.06,
                anticapitalism=0.06,
                chasiness=0.06,
                totalFingers=1,
            ),
        )

    for player_id in rd.teams[TIGERS]["rotation"]:
        rd.player_attr_change(
            S1_ELECTION_TIMESTAMP,
            player_id,
            dict(
                shakespearianism=0.1,
                suppression=0.1,
                unthwackability=0.1,
                coldness=0.1,
                overpowerment=0.1,
                ruthlessness=0.1,
                totalFingers=1,
            ),
        )

    # The Philly Pies stole the best hitter in the league, Jessica Telephone, from the Dallas Steaks. They sent back August Mina.
    rd.swap_player(
        S1_ELECTION_TIMESTAMP,
        STEAKS,
        "083d09d4-7ed3-4100-b021-8fbe30dd43e8",
        PIES,
        "c17a4397-4dcc-440e-8c53-d897e971cae9",
    )

    # The Baltimore Crabs stole the best pitcher in the league, PolkaDot Patterson, from the Kansas City Breath Mints. They sent back Winnie Hess.
    rd.swap_player(
        S1_ELECTION_TIMESTAMP,
        BREATH_MINTS,
        "338694b7-6256-4724-86b6-3884299a5d9e",
        CRABS,
        "f2a27a7e-bf04-4d31-86f5-16bfa3addbe7",
    )

    # "During the elections, after blessings were processed, Nicholas Mora and Yazmin Mason swapped teams, with no indication as to why. This may have been a third mystery blessing that was never recorded.[2]"
    rd.swap_player(
        S1_ELECTION_TIMESTAMP,
        PIES,
        "afc90398-b891-4cdf-9dea-af8a3a79d793",
        TIGERS,
        "b082ca6e-eb11-4eab-8d6a-30f8be522ec4",
    )

    # Nagomi Mcdaniel mysteriously defected to the Hawai'i Fridays. Nolanestophia Patterson swapped to the Tigers. There's still no clear answer for why this happened.
    rd.swap_player(
        S1_ELECTION_TIMESTAMP,
        TIGERS,
        "c0732e36-3731-4f1a-abdc-daa9563b6506",
        FRIDAYS,
        "7e9a514a-7850-4ed0-93ab-f3a6e2f41c03",
    )

    for player_id, seed in [
        # Peck timeline
        ("5ff66eae-7111-4e3b-a9b8-a9579165b0a5", "8171ff73601510ff+38"),  # Daniel Duffy
        ("2e86de11-a2dd-4b28-b5fe-f4d0c38cd20b", "8171ff73601510ff+46"),  # Zion Aliciakeyes
        ("80de2b05-e0d4-4d33-9297-9951b2b5c950", "8171ff73601510ff+54"),  # Alyssa Harrell
        ("70ccff1e-6b53-40e2-8844-0a28621cb33e", "8171ff73601510ff+70"),  # Moody Cookbook
    ]:
        r = Rng.parse(seed)
        rd.update_player(
            S1_ELECTION_TIMESTAMP,
            player_id,
            dict(
                buoyancy=r.next(),
                thwackability=r.next(),
                moxie=r.next(),
                divinity=r.next(),
                musclitude=r.next(),
                patheticism=r.next(),
                martyrdom=r.next(),
            ),
        )

    # Derrick timeline - Winnie Hess mystery boost
    r = Rng.parse("6e9cecada970c54f+51")
    rd.update_player(
        S1_ELECTION_TIMESTAMP,
        "f2a27a7e-bf04-4d31-86f5-16bfa3addbe7",
        dict(
            shakespearianism=r.next(),
            suppression=r.next(),
            unthwackability=r.next(),
            coldness=r.next(),
            overpowerment=r.next(),
            ruthlessness=r.next(),
        ),
    )


def season_2(rd: Redata):
    # Season 2 (mostly incinerations - hardcoding these for now)

    # 2020-07-28T04:00:00Z ['Rogue Umpire incinerated Fridays hitter Fitzgerald Massey! Replaced by Hendricks Rangel']
    rd.incineration(
        "2020-07-28T04:00:00Z",
        FRIDAYS,
        "ef32eb48-4866-49d0-ae58-9c4982e01142",
        "9333d7ace2424f45+183656",
        "b3d518b9-dc68-4902-b68c-0022ceb25aa0",
        "Hendricks Rangel",
    )

    # 2020-07-28T13:00:00Z ['Rogue Umpire incinerated Dalé hitter Jenna Maldonado! Replaced by Randy Dennis']
    rd.incineration(
        "2020-07-28T13:00:00Z",
        DALE,
        "8ba7e1ff-4c6d-4963-8e0f-7096d14f4b12",
        "9333d7ace2424f45+326101",
        "5a26fc61-d75d-4c01-9ce2-1880ffb5550f",
        "Randy Dennis",
    )

    # 2020-07-28T15:00:00Z ['Rogue Umpire incinerated Firefighters hitter Tyreek Olive! Replaced by Paula Mason']
    rd.incineration(
        "2020-07-28T15:00:00Z",
        FIREFIGHTERS,
        "31f83a89-44e3-47b7-8c9e-0dfdcd8bd30f",
        "9333d7ace2424f45+345651",
        "c0177f76-67fc-4316-b650-894159dede45",
        "Paula Mason",
    )

    # 2020-07-28T16:00:00Z ['Rogue Umpire incinerated Crabs hitter Nora Perez! Replaced by Holden Stanton']
    rd.incineration(
        "2020-07-28T16:00:00Z",
        CRABS,
        "a071a713-a6a1-4b4c-bb3f-45d9fba7a08c",
        "9333d7ace2424f45+365796",
        "817dee99-9ccf-4f41-84e3-dc9773237bc8",
        "Holden Stanton",
    )

    # 2020-07-29T08:00:00Z ['Rogue Umpire incinerated Millennials pitcher Scrap Murphy! Replaced by Felix Garbage']
    rd.incineration(
        "2020-07-29T08:00:00Z",
        MILLENNIALS,
        "40db1b0b-6d04-4851-adab-dd6320ad2ed9",
        "dd9100191d939ab7+113862",
        "18af933a-4afa-4cba-bda5-45160f3af99b",
        "Felix Garbage",
    )

    # 2020-07-29T22:00:00Z ['Rogue Umpire incinerated Steaks hitter Lars Mendoza! Replaced by Marco Stink']
    # it's not illegal for bugs
    rd.incineration(
        "2020-07-29T22:00:00Z",
        STEAKS,
        "76c4853b-7fbc-4688-8cda-c5b8de1724e4",
        "9c7ed877842aff25+21113",
        "87e6ae4b-67de-4973-aa56-0fc9835a1e1e",
        "Marco Stink",
    )

    # 2020-07-30T10:00:00Z ['Rogue Umpire incinerated Magic hitter Sosa Elftower! Replaced by Halexandrey Walton']
    rd.incineration(
        "2020-07-30T10:00:00Z",
        MAGIC,
        "c86b5add-6c9a-40e0-aa43-e4fd7dd4f2c7",
        "9c7ed877842aff25+199097",
        "03b80a57-77ea-4913-9be4-7a85c3594745",
        "Halexandrey Walton",
    )

    # 2020-07-30T11:00:00Z ['Rogue Umpire incinerated Magic pitcher Famous Oconnor! Replaced by Cory Twelve']
    rd.incineration(
        "2020-07-30T11:00:00Z",
        MAGIC,
        "bca38809-81de-42ff-94e3-1c0ebfb1e797",
        "9c7ed877842aff25+212738",
        "2da49de2-34e5-49d0-b752-af2a2ee061be",
        "Cory Twelve",
    )

    # 2020-07-30T11:00:00Z ['Rogue Umpire incinerated Spies hitter Dickerson Greatness! Replaced by Collins Melon']
    rd.incineration(
        "2020-07-30T11:00:00Z",
        SPIES,
        "3afb30c1-1b12-466a-968a-5a9a21458c7f",
        "9c7ed877842aff25+222003",
        "ef9f8b95-9e73-49cd-be54-60f84858a285",
        "Collins Melon",
    )

    # 2020-07-30T18:00:00Z ['Rogue Umpire incinerated Moist Talkers hitter Trevino Merritt! Replaced by Simon Haley']
    rd.incineration(
        "2020-07-30T18:00:00Z",
        MOIST_TALKERS,
        "70a458ed-25ca-4ff8-97fc-21cbf58f2c2a",
        "9c7ed877842aff25+321893",
        "020ed630-8bae-4441-95cc-0e4ecc27253b",
        "Simon Haley",
    )

    # 2020-07-30T18:00:00Z ['Rogue Umpire incinerated Steaks hitter Zi Delacruz! Replaced by Thomas Kirby']
    rd.incineration(
        "2020-07-30T18:00:00Z",
        STEAKS,
        "c83a13f6-ee66-4b1c-9747-faa67395a6f1",
        "9c7ed877842aff25+323565",
        "f73009c5-2ede-4dc4-b96d-84ba93c8a429",
        "Thomas Kirby",
    )

    # 2020-07-30T20:00:00Z ['Rogue Umpire incinerated Fridays hitter Jessi Wise! Replaced by York Silk']
    rd.incineration(
        "2020-07-30T20:00:00Z",
        FRIDAYS,
        "57448b62-f952-40e2-820c-48d8afe0f64d",
        "9c7ed877842aff25+354824",
        "86d4e22b-f107-4bcf-9625-32d387fcb521",
        "York Silk",
    )

    # 2020-07-30T22:00:00Z ['Rogue Umpire incinerated Flowers hitter Hurley Pacheco! Replaced by Nic Winkler']
    rd.incineration(
        "2020-07-30T22:00:00Z",
        FLOWERS,
        "b86237bb-ade6-4b1d-9199-a3cc354118d9",
        "9c7ed877842aff25+386103",
        "855775c1-266f-40f6-b07b-3a67ccdf8551",
        "Nic Winkler",
    )

    # 2020-07-31T02:00:00Z ['Rogue Umpire incinerated Jazz Hands hitter Alexandria Dracaena! Replaced by Hendricks Richardson']
    rd.incineration(
        "2020-07-31T02:00:00Z",
        JAZZ_HANDS,
        "262c49c6-8301-487d-8356-747023fa46a9",
        "9c7ed877842aff25+437352",
        "cf8e152e-2d27-4dcc-ba2b-68127de4e6a4",
        "Hendricks Richardson",
    )

    # 2020-07-31T10:00:00Z ['Rogue Umpire incinerated Dalé hitter Aldon Anthony! Replaced by Murray Pony']
    rd.incineration(
        "2020-07-31T10:00:00Z",
        DALE,
        "4bda6584-6c21-4185-8895-47d07e8ad0c0",
        "9c7ed877842aff25+565027",
        "2ca0c790-e1d5-4a14-ab3c-e9241c87fc23",
        "Murray Pony",
    )

    # 2020-07-31T15:00:00Z ['Rogue Umpire incinerated Pies hitter Cedric Gonzalez! Replaced by Dan Holloway']
    # lka. Peanut
    rd.incineration(
        "2020-07-31T15:00:00Z",
        PIES,
        "6fc3689f-bb7d-4382-98a2-cf6ddc76909d",
        "9c7ed877842aff25+637535",
        "667cb445-c288-4e62-b603-27291c1e475d",
        "Dan Holloway",
    )


def season_2_election(rd: Redata):
    S2_ELECTION_TIMESTAMP = "2020-08-02T19:00:00Z"

    # Peanuts passed with 4441 votes, 36% of all Decree Votes.
    rd.update_player(S2_ELECTION_TIMESTAMP, "667cb445-c288-4e62-b603-27291c1e475d", dict(name="Peanut Holloway"))
    rd.update_player(S2_ELECTION_TIMESTAMP, "9820f2c5-f9da-4a07-b610-c2dd7bee2ef6", dict(name="Peanut Bong"))
    rd.update_player(S2_ELECTION_TIMESTAMP, "5ff66eae-7111-4e3b-a9b8-a9579165b0a5", dict(name="Peanutiel Duffy"))

    # this is where cinnamon, fate, and allergies were rolled
    r = Rng.parse("01b73d5d48bdcfc9+1")
    for team_id in ORIGINAL_TEAM_ORDER:
        team = rd.teams[team_id]
        for player_id in team["lineup"] + team["rotation"] + team["bench"] + team["bullpen"]:
            cinnamon = r.next()
            allergy = r.next() < 0.5
            fate = int(r.next() * 100)
            rd.update_player(
                S2_ELECTION_TIMESTAMP,
                player_id,
                dict(
                    cinnamon=cinnamon,
                    peanutAllergy=allergy,
                    fate=fate,
                ),
            )

    # TODO: The Fourth Strike was granted to the New York Millennials, the Kansas City Breath Mints, the Hellmouth Sunbeams, and the San Francisco Lovers.

    # The Tigers stole Jessica Telephone from the Philly Pies and sent back Nolanestophia Patterson.
    rd.swap_player(
        S2_ELECTION_TIMESTAMP,
        PIES,
        "083d09d4-7ed3-4100-b021-8fbe30dd43e8",
        TIGERS,
        "7e9a514a-7850-4ed0-93ab-f3a6e2f41c03",
    )

    # The Rack blessed the Philly Pies. Their defense was improved 15%.
    for player_id in rd.teams[PIES]["lineup"] + rd.teams[PIES]["rotation"]:
        rd.player_attr_change(
            S2_ELECTION_TIMESTAMP,
            player_id,
            dict(
                omniscience=0.15,
                tenaciousness=0.15,
                watchfulness=0.15,
                anticapitalism=0.15,
                chasiness=0.15,
            ),
        )

    # Blood Sacrifice blessed the Philly Pies. They were boosted to the top of the tiebreakers.
    # TODO: how did DF work? internal tiebreaker list?

    # The Moist Talkers stole PolkaDot Patterson from the Baltimore Crabs and sent back Oliver Notarobot.
    rd.swap_player(
        S2_ELECTION_TIMESTAMP,
        MOIST_TALKERS,
        "542af915-79c5-431c-a271-f7185e37c6ae",
        CRABS,
        "338694b7-6256-4724-86b6-3884299a5d9e",
    )

    # Yes Plz! blessed the Charleston Shoe Thieves. Their hitting was improved 10%.
    for player_id in rd.teams[SHOE_THIEVES]["lineup"]:
        rd.player_attr_change(
            S2_ELECTION_TIMESTAMP,
            player_id,
            dict(
                thwackability=0.1,
                moxie=0.1,
                divinity=0.1,
                musclitude=0.1,
                patheticism=-0.1,
                buoyancy=0.1,
                martyrdom=0.1,
            ),
        )

    # Pseudo-Thumbs blessed the Seattle Garages. Their pitching was improved 10%.
    for player_id in rd.teams[GARAGES]["rotation"]:
        rd.player_attr_change(
            S2_ELECTION_TIMESTAMP,
            player_id,
            dict(
                shakespearianism=0.1,
                suppression=0.1,
                unthwackability=0.1,
                coldness=0.1,
                overpowerment=0.1,
                ruthlessness=0.1,
                totalFingers=1,
            ),
        )

    # Gunblade Bat blessed the Hawai'i Fridays. This led to York Silk's hitting stats being maxed out.
    for _ in range(20):
        rd.player_attr_change(
            S2_ELECTION_TIMESTAMP,
            "86d4e22b-f107-4bcf-9625-32d387fcb521",
            dict(
                thwackability=0.01,
                moxie=0.01,
                divinity=0.01,
                musclitude=0.01,
                patheticism=-0.01,
                buoyancy=0.01,
                martyrdom=0.01,
            ),
        )

    # Soul Swap blessed the New York Millennials.
    r = Rng.parse("01b73d5d48bdcfc9+1515")
    for player_id in [
        "ae4acebd-edb5-4d20-bf69-f2d5151312ff",  # Theodore Cervantes
        "378c07b0-5645-44b5-869f-497d144c7b35",  # Fynn Doyle
    ]:
        rd.update_player(
            S2_ELECTION_TIMESTAMP,
            player_id,
            dict(
                shakespearianism=r.next(),
                suppression=r.next(),
                unthwackability=r.next(),
                coldness=r.next(),
                overpowerment=r.next(),
                ruthlessness=r.next(),
            ),
        )
    for player_id in [
        "b1b141fc-e867-40d1-842a-cea30a97ca4f",  # Richardson Games
        "413b3ddb-d933-4567-a60e-6d157480239d",  # Winnie Mccall
        "5dbf11c0-994a-4482-bd1e-99379148ee45",  # Conrad Vaughan
    ]:
        rd.update_player(
            S2_ELECTION_TIMESTAMP,
            player_id,
            dict(
                tragicness=r.next(),
                buoyancy=r.next(),
                thwackability=r.next(),
                moxie=r.next(),
                divinity=r.next(),
                musclitude=r.next(),
                patheticism=r.next(),
                martyrdom=r.next(),
            ),
        )

    # Wind Sprints blessed the Kansas City Breath Mints. Their baserunning was improved 15%.
    for player_id in rd.teams[BREATH_MINTS]["lineup"]:
        rd.player_attr_change(
            S2_ELECTION_TIMESTAMP,
            player_id,
            dict(
                baseThirst=0.15,
                laserlikeness=0.15,
                groundFriction=0.15,
                continuation=0.15,
                indulgence=0.15,
            ),
        )

    # Literal Arm Cannon blessed the Kansas City Breath Mints. This led to Axel Trololol's pitching stats being maxed out.
    for _ in range(54):
        rd.player_attr_change(
            S2_ELECTION_TIMESTAMP,
            "3af96a6b-866c-4b03-bc14-090acf6ecee5",
            dict(
                shakespearianism=0.01,
                suppression=0.01,
                unthwackability=0.01,
                coldness=0.01,
                overpowerment=0.01,
                ruthlessness=0.01,
                totalFingers=1,
            ),
        )

    # Performance Enhancing Demons blessed the San Francisco Lovers. This improved the Lovers overall 8%.
    for player_id in rd.teams[LOVERS]["lineup"]:
        rd.player_attr_change(
            S2_ELECTION_TIMESTAMP,
            player_id,
            dict(
                thwackability=0.08,
                moxie=0.08,
                divinity=0.08,
                musclitude=0.08,
                patheticism=-0.08,
                buoyancy=0.08,
                baseThirst=0.08,
                laserlikeness=0.08,
                groundFriction=0.08,
                continuation=0.08,
                indulgence=0.08,
                martyrdom=0.08,
                omniscience=0.08,
                tenaciousness=0.08,
                watchfulness=0.08,
                anticapitalism=0.08,
                chasiness=0.08,
            ),
        )
    for player_id in rd.teams[LOVERS]["rotation"]:
        rd.player_attr_change(
            S2_ELECTION_TIMESTAMP,
            player_id,
            dict(
                shakespearianism=0.08,
                suppression=0.08,
                unthwackability=0.08,
                coldness=0.08,
                overpowerment=0.08,
                ruthlessness=0.08,
                omniscience=0.08,
                tenaciousness=0.08,
                watchfulness=0.08,
                anticapitalism=0.08,
                chasiness=0.08,
                totalFingers=1,
            ),
        )

    # Bloodlust blessed the San Francisco Lovers. This led to Kichiro Guerra's hitting stats being maxed out.
    for _ in range(58):
        rd.player_attr_change(
            S2_ELECTION_TIMESTAMP,
            "58c9e294-bd49-457c-883f-fb3162fc668e",
            dict(
                thwackability=0.01,
                moxie=0.01,
                divinity=0.01,
                musclitude=0.01,
                patheticism=-0.01,
                buoyancy=0.01,
                martyrdom=0.01,
            ),
        )

    # ...at some point in here, Sosa Hayes' path was capped at 0.99
    # todo: is this a "cronjob" to cap them across the board? when specifically was this?
    rd.update_player(S2_ELECTION_TIMESTAMP, "b7267aba-6114-4d53-a519-bf6c99f4e3a9", dict(patheticism=0.99))


def season_2_election_postfix(rd: Redata):
    S2_ELECTION_POSTFIX_TIMESTAMP = "2020-08-02T21:20:00Z"
    for player_id in [
        "58c9e294-bd49-457c-883f-fb3162fc668e",
        "11de4da3-8208-43ff-a1ff-0b3480a0fbf1",
        "bd24e18b-800d-4f15-878d-e334fb4803c4",
        "db33a54c-3934-478f-bad4-fc313ac2580e",
        "0e27df51-ad0c-4546-acf5-96b3cb4d7501",
        "f1185b20-7b4a-4ccc-a977-dc1afdfd4cb9",
        "bf6a24d1-4e89-4790-a4ba-eeb2870cbf6f",
        "5149c919-48fe-45c6-b7ee-bb8e5828a095",
        "937c1a37-4b05-4dc5-a86d-d75226f8490a",
        "10ea5d50-ec88-40a0-ab53-c6e11cc1e479",
        "f0594932-8ef7-4d70-9894-df4be64875d8",
        "17397256-c28c-4cad-85f2-a21768c66e67",
        "f73009c5-2ede-4dc4-b96d-84ba93c8a429",
        "14d88771-7a96-48aa-ba59-07bae1733e96",
        "05bd08d5-7d9f-450b-abfa-1788b8ee8b91",
        "c17a4397-4dcc-440e-8c53-d897e971cae9",
        "94baa9ac-ff96-4f56-a987-10358e917d91",
        "13cfbadf-b048-4c4f-903d-f9b52616b15c",
        "c6bd21a8-7880-4c00-8abe-33560fe84ac5",
        "b39b5aae-8571-4c90-887a-6a00f2a2f6fd",
        "c73d59dd-32a0-49ce-8ab4-b2dbb7dc94ec",
        "a8a5cf36-d1a9-47d1-8d22-4a665933a7cc",
        "6e373fca-b8ab-4848-9dcc-50e92cd732b7",
        "c0177f76-67fc-4316-b650-894159dede45",
        "e4e4c17d-8128-4704-9e04-f244d4573c4d",
        "d46abb00-c546-4952-9218-4f16084e3238",
        "c182f33c-aea5-48a2-97ed-dc74fa29b3c0",
        "3c051b92-4a86-4157-988a-e334bf6dc691",
        "c8de53a4-d90f-4192-955b-cec1732d920e",
        "54e5f222-fb16-47e0-adf9-21813218dafa",
        "88ca603e-b2e5-4916-bef5-d6bba03235f5",
        "b4505c48-fc75-4f9e-8419-42b28dcc5273",
        "36786f44-9066-4028-98d9-4fa84465ab9e",
        "3531c282-cb48-43df-b549-c5276296aaa7",
        "7dcf6902-632f-48c5-936a-7cf88802b93a",
        "d35ccee1-9559-49a1-aaa4-7809f7b5c46e",
        "97dfc1f6-ac94-4cdc-b0d5-1cb9f8984aa5",
        "5915b7bb-e532-4036-9009-79f1e80c0e28",
        "dd8a43a4-a024-44e9-a522-785d998b29c3",
        "d2f827a5-0133-4d96-b403-85a5e50d49e0",
        "1ba715f2-caa3-44c0-9118-b045ea702a34",
        "26cfccf2-850e-43eb-b085-ff73ad0749b8",
        "06ced607-7f96-41e7-a8cd-b501d11d1a7e",
        "9786b2c9-1205-4718-b0f7-fc000ce91106",
        "b082ca6e-eb11-4eab-8d6a-30f8be522ec4",
        "0672a4be-7e00-402c-b8d6-0b813f58ba96",
        "62111c49-1521-4ca7-8678-cd45dacf0858",
        "906a5728-5454-44a0-adfe-fd8be15b8d9b",
        "8604e861-d784-43f0-b0f8-0d43ea6f7814",
        "8e1fd784-99d5-41c1-a6c5-6b947cec6714",
        "df4da81a-917b-434f-b309-f00423ee4967",
        "4562ac1f-026c-472c-b4e9-ee6ff800d701",
        "4204c2d1-ca48-4af7-b827-e99907f12d61",
        "7951836f-581a-49d5-ae2f-049c6bcc575e",
        "4542f0b0-3409-4a4a-a9e1-e8e8e5d73fcf",
        "6bd4cf6e-fefe-499a-aa7a-890bcc7b53fa",
        "d74a2473-1f29-40fa-a41e-66fa2281dfca",
        "083d09d4-7ed3-4100-b021-8fbe30dd43e8",
        "5ff66eae-7111-4e3b-a9b8-a9579165b0a5",
        "2e86de11-a2dd-4b28-b5fe-f4d0c38cd20b",
        "afc90398-b891-4cdf-9dea-af8a3a79d793",
        "2720559e-9173-4042-aaa0-d3852b72ab2e",
        "7aeb8e0b-f6fb-4a9e-bba2-335dada5f0a3",
        "77a41c29-8abd-4456-b6e0-a034252700d2",
        "d744f534-2352-472b-9e42-cd91fa540f1b",
        "d4a10c2a-0c28-466a-9213-38ba3339b65e",
        "25f3a67c-4ed5-45b6-94b1-ce468d3ead21",
        "a691f2ba-9b69-41f8-892c-1acd42c336e4",
        "64f59d5f-8740-4ebf-91bd-d7697b542a9f",
        "3ebb5361-3895-4a50-801e-e7a0ee61750c",
        "c3b1b4e5-4b88-4245-b2b1-ae3ade57349e",
        "90c6e6ca-77fc-42b7-94d8-d8afd6d299e5",
        "e111a46d-5ada-4311-ac4f-175cca3357da",
        "446a3366-3fe3-41bb-bfdd-d8717f2152a9",
        "32551e28-3a40-47ae-aed1-ff5bc66be879",
        "e972984c-2895-451c-b518-f06a0d8bd375",
        "a8530be5-8923-4f74-9675-bf8a1a8f7878",
        "57b4827b-26b0-4384-a431-9f63f715bc5b",
        "97981e86-4a42-4f85-8783-9f29833c192b",
        "b7c4f986-e62a-4a8f-b5f0-8f30ecc35c5d",
        "68462bfa-9006-4637-8830-2e7840d9089a",
        "f0bcf4bb-74b3-412e-a54c-04c12ad28ecb",
        "9820f2c5-f9da-4a07-b610-c2dd7bee2ef6",
        "8903a74f-f322-41d2-bd75-dbf7563c4abb",
        "0cc5bd39-e90d-42f9-9dd8-7e703f316436",
        "0daf04fc-8d0d-4513-8e98-4f610616453b",
        "4aa843a4-baa1-4f35-8748-63aa82bd0e03",
        "97ec5a2f-ac1a-4cde-86b7-897c030a1fa8",
        "d5192d95-a547-498a-b4ea-6770dde4b9f5",
        "b7adbbcc-0679-43f3-a939-07f009a393db",
        "495a6bdc-174d-4ad6-8d51-9ee88b1c2e4a",
        "1c73f91e-0562-480d-9543-2aab1d5e5acd",
        "f968532a-bf06-478e-89e0-3856b7f4b124",
        "864b3be8-e836-426e-ae56-20345b41d03d",
        "90c2cec7-0ed5-426a-9de8-754f34d59b39",
        "cf8e152e-2d27-4dcc-ba2b-68127de4e6a4",
        "d5b6b11d-3924-4634-bd50-76553f1f162b",
        "f4a5d734-0ade-4410-abb6-c0cd5a7a1c26",
        "3de17e21-17db-4a6b-b7ab-0b2f3c154f42",
        "f10ba06e-d509-414b-90cd-4d70d43c75f9",
        "5fbf04bb-f5ec-4589-ab19-1d89cda056bd",
    ]:
        rd.update_player(S2_ELECTION_POSTFIX_TIMESTAMP, player_id, dict(peanutAllergy=True))

    rd.update_player(S2_ELECTION_POSTFIX_TIMESTAMP, "75f9d874-5e69-438d-900d-a3fcb1d429b3", {"fate": 54})
    rd.update_player(S2_ELECTION_POSTFIX_TIMESTAMP, "10ea5d50-ec88-40a0-ab53-c6e11cc1e479", {"fate": 57})
    rd.update_player(S2_ELECTION_POSTFIX_TIMESTAMP, "ecb8d2f5-4ff5-4890-9693-5654e00055f6", {"fate": 14})
    rd.update_player(S2_ELECTION_POSTFIX_TIMESTAMP, "f6342729-a38a-4204-af8d-64b7accb5620", {"fate": 40})


def season_2_election_postfix_2(rd: Redata):
    S2_ELECTION_POSTFIX_2_TIMESTAMP = "2020-08-02T23:30:00Z"
    for player_id in [
        "3064c7d6-91cc-4c2a-a433-1ce1aabc1ad4",
        "24f6829e-7bb4-4e1e-8b59-a07514657e72",
        "a938f586-f5c1-4a35-9e7f-8eaab6de67a6",
        "c771abab-f468-46e9-bac5-43db4c5b410f",
        "4941976e-31fc-49b5-801a-18abe072178b",
        "8a6fc67d-a7fe-443b-a084-744294cec647",
        "9ac2e7c5-5a34-4738-98d8-9f917bc6d119",
        "62823073-84b8-46c2-8451-28fd10dff250",
        "805ba480-df4d-4f56-a4cf-0b99959111b5",
        "4e6ad1a1-7c71-49de-8bd5-c286712faf9e",
        "9397ed91-608e-4b13-98ea-e94c795f651e",
        "1ded0384-d290-4ea1-a72b-4f9d220cbe37",
        "945974c5-17d9-43e7-92f6-ba49064bbc59",
        "ac57cf28-556f-47af-9154-6bcea2ace9fc",
        "7310c32f-8f32-40f2-b086-54555a2c0e86",
        "4ffd2e50-bb5b-45d0-b7c4-e24d41b2ff5d",
        "a1628d97-16ca-4a75-b8df-569bae02bef9",
        "ae4acebd-edb5-4d20-bf69-f2d5151312ff",
        "29bf512a-cd8c-4ceb-b25a-d96300c184bb",
        "6a869b40-be99-4520-89e5-d382b07e4a3c",
        "b3d518b9-dc68-4902-b68c-0022ceb25aa0",
        "18af933a-4afa-4cba-bda5-45160f3af99b",
        "855775c1-266f-40f6-b07b-3a67ccdf8551",
    ]:
        rd.update_player(S2_ELECTION_POSTFIX_2_TIMESTAMP, player_id, dict(peanutAllergy=True))


def season_3(rd: Redata):
    rd.incineration(
        "2020-08-03T17:20:51.379Z",
        "f02aeae2-5e6a-4098-9842-02d2273f25c7",
        "472f50c0-ef98-4d05-91d0-d6359eec3946",
        "c80bcdf4616e9156+30091",
        "2b5f5dd7-e31f-4829-bec5-546652103bc0",
        "Dudley Mueller",
    )
    rd.incineration(
        "2020-08-03T22:20:58.61Z",
        "105bc3ff-1320-4e37-8ef0-8d595cb95dd0",
        "03097200-0d48-4236-a3d2-8bdb153aa8f7",
        "88eabf638715ddf4+5307",
        "3d4545ed-6217-4d7a-9c4a-209265eb6404",
        "Tiana Cash",
    )
    rd.yummy("2020-08-03T22:23:46.627Z", "b024e975-1c4a-4575-8936-a3754a08806a", "87e6ae4b-67de-4973-aa56-0fc9835a1e1e")
    rd.incineration(
        "2020-08-03T23:04:19.373Z",
        "b72f3061-f573-40d7-832a-5ad475bd7909",
        "80a2f015-9d40-426b-a4f6-b9911ba3add8",
        "88eabf638715ddf4+12758",
        "f2c477fb-28ea-4fcb-943a-9fab22df3da0",
        "Sandford Garner",
    )
    rd.incineration(
        "2020-08-03T23:10:42.072Z",
        "3f8bbb15-61c0-4e3f-8e4a-907a5fb1565e",
        "0fe896e1-108c-4ce9-97be-3470dde73c21",
        "88eabf638715ddf4+16551",
        "2175cda0-a427-40fd-b497-347edcc1cd61",
        "Hotbox Sato",
    )
    rd.incineration(
        "2020-08-03T23:11:03.71Z",
        "23e4cbc1-e9cd-47fa-a35b-bfa06f726cb7",
        "1ba715f2-caa3-44c0-9118-b045ea702a34",
        "88eabf638715ddf4+16780",
        "32810dca-825c-4dbc-8b65-0702794c424e",
        "Eduardo Woodman",
    )
    rd.incineration(
        "2020-08-04T00:04:29.227Z",
        "b63be8c2-576a-4d6e-8daf-814f8bcea96f",
        "64b055d1-b691-4e0c-8583-fc08ba663846",
        "b3677c2d432b46d4+2521",
        "a38ada0a-aeac-4a3d-b9a5-968687ccd2f9",
        "Sixpack Santiago",
    )
    rd.yummy("2020-08-04T02:11:41.969Z", "23e4cbc1-e9cd-47fa-a35b-bfa06f726cb7", "32810dca-825c-4dbc-8b65-0702794c424e")
    rd.allergic(
        "2020-08-04T02:12:58.059Z", "eb67ae5e-c4bf-46ca-bbbc-425cd34182ff", "020ed630-8bae-4441-95cc-0e4ecc27253b"
    )
    rd.allergic(
        "2020-08-04T05:11:58.863Z", "a37f9158-7f82-46bc-908c-c9e2dda7c33b", "cf8e152e-2d27-4dcc-ba2b-68127de4e6a4"
    )
    rd.incineration(
        "2020-08-04T05:18:10.865Z",
        "b72f3061-f573-40d7-832a-5ad475bd7909",
        "43bf6a6d-cc03-4bcf-938d-620e185433e1",
        "b3677c2d432b46d4+87404",
        "23110c0f-2cf9-4d9c-ab2d-634f2f18867e",
        "Kennedy Meh",
    )
    rd.allergic(
        "2020-08-04T07:20:42.649Z", "adc5b394-8f76-416d-9ce9-813706877b84", "4b6f0a4e-de18-44ad-b497-03b1f470c43c"
    )
    rd.allergic(
        "2020-08-04T07:24:54.811Z", "adc5b394-8f76-416d-9ce9-813706877b84", "64f4cd75-0c1e-42cf-9ff0-e41c4756f22a"
    )
    rd.incineration(
        "2020-08-04T08:15:49.685Z",
        "36569151-a2fb-43c1-9df7-2df512424c82",
        "a1628d97-16ca-4a75-b8df-569bae02bef9",
        "b3677c2d432b46d4+132467",
        "766dfd1e-11c3-42b6-a167-9b2d568b5dc0",
        "Sandie Turner",
    )
    rd.allergic(
        "2020-08-04T09:08:52.142Z", "adc5b394-8f76-416d-9ce9-813706877b84", "c73d59dd-32a0-49ce-8ab4-b2dbb7dc94ec"
    )
    rd.yummy("2020-08-04T09:26:50.485Z", "36569151-a2fb-43c1-9df7-2df512424c82", "4ffd2e50-bb5b-45d0-b7c4-e24d41b2ff5d")
    rd.incineration(
        "2020-08-04T10:07:04.983Z",
        "878c1bf6-0d21-4659-bfee-916c8314d69c",
        "773712f6-d76d-4caa-8a9b-56fe1d1a5a68",
        "b3677c2d432b46d4+158506",
        "21d52455-6c2c-4ee4-8673-ab46b4b926b4",
        "Emmett Owens",
    )
    rd.incineration(
        "2020-08-04T13:11:47.474Z",
        "eb67ae5e-c4bf-46ca-bbbc-425cd34182ff",
        "5b9727f7-6a20-47d2-93d9-779f0a85c4ee",
        "b3677c2d432b46d4+205252",
        "9f85676a-7411-444a-8ae2-c7f8f73c285c",
        "Lachlan Shelton",
    )
    rd.allergic(
        "2020-08-04T14:11:07.131Z", "ca3f1c8c-c025-4d8e-8eef-5be6accbeb16", "d23a1f7e-0071-444e-8361-6ae01f13036f"
    )
    rd.allergic(
        "2020-08-04T14:16:45.295Z", "ca3f1c8c-c025-4d8e-8eef-5be6accbeb16", "69196296-f652-42ff-b2ca-0d9b50bd9b7b"
    )
    rd.allergic(
        "2020-08-04T14:24:41.569Z", "ca3f1c8c-c025-4d8e-8eef-5be6accbeb16", "c0177f76-67fc-4316-b650-894159dede45"
    )
    rd.incineration(
        "2020-08-04T17:07:20.583Z",
        "a37f9158-7f82-46bc-908c-c9e2dda7c33b",
        "d5b6b11d-3924-4634-bd50-76553f1f162b",
        "b3677c2d432b46d4+262795",
        "ae81e172-801a-4236-929a-b990fc7190ce",
        "August Sky",
    )
    rd.incineration(
        "2020-08-04T17:15:54.787Z",
        "f02aeae2-5e6a-4098-9842-02d2273f25c7",
        "8e1fd784-99d5-41c1-a6c5-6b947cec6714",
        "b3677c2d432b46d4+267803",
        "c9e4a49e-e35a-4034-a4c7-293896b40c58",
        "Alexander Horne",
    )
    rd.allergic(
        "2020-08-04T20:16:13.868Z", "b63be8c2-576a-4d6e-8daf-814f8bcea96f", "2e6d4fa9-f930-47bd-971a-dd54a3cf7db1"
    )
    rd.yummy("2020-08-05T01:14:19.659Z", "eb67ae5e-c4bf-46ca-bbbc-425cd34182ff", "d1a7c13f-8e78-4d2e-9cae-ebf3a5fcdb5d")
    rd.yummy("2020-08-05T04:07:35.235Z", "979aee4a-6d80-4863-bf1c-ee1a78e06024", "c0732e36-3731-4f1a-abdc-daa9563b6506")
    rd.allergic(
        "2020-08-05T04:17:01.358Z", "b63be8c2-576a-4d6e-8daf-814f8bcea96f", "5a26fc61-d75d-4c01-9ce2-1880ffb5550f"
    )
    rd.yummy("2020-08-05T07:00:38.291Z", "bfd38797-8404-4b38-8b82-341da28b1f83", "bd4c6837-eeaa-4675-ae48-061efa0fd11a")
    rd.allergic(
        "2020-08-05T08:01:33.209Z", "3f8bbb15-61c0-4e3f-8e4a-907a5fb1565e", "855775c1-266f-40f6-b07b-3a67ccdf8551"
    )
    rd.incineration(
        "2020-08-05T10:19:31.38Z",
        "bfd38797-8404-4b38-8b82-341da28b1f83",
        "b4505c48-fc75-4f9e-8419-42b28dcc5273",
        "34d5b554d0dd9bd0+71127",
        "f44a8b27-85c1-44de-b129-1b0f60bcb99c",
        "Atlas Jonbois",
    )
    rd.incineration(
        "2020-08-05T13:29:59.445Z",
        "bfd38797-8404-4b38-8b82-341da28b1f83",
        "f44a8b27-85c1-44de-b129-1b0f60bcb99c",
        "34d5b554d0dd9bd0+120505",
        "15d3a844-df6b-4193-a8f5-9ab129312d8d",
        "Sebastian Woodman",
    )
    rd.incineration(
        "2020-08-05T14:11:32.707Z",
        "eb67ae5e-c4bf-46ca-bbbc-425cd34182ff",
        "d744f534-2352-472b-9e42-cd91fa540f1b",
        "34d5b554d0dd9bd0+127167",
        "8c8cc584-199b-4b76-b2cd-eaa9a74965e5",
        "Ziwa Mueller",
    )
    rd.allergic(
        "2020-08-05T16:08:35.796Z", "a37f9158-7f82-46bc-908c-c9e2dda7c33b", "4f328502-d347-4d2c-8fad-6ae59431d781"
    )
    rd.incineration(
        "2020-08-05T17:04:13.506Z",
        "105bc3ff-1320-4e37-8ef0-8d595cb95dd0",
        "3d4545ed-6217-4d7a-9c4a-209265eb6404",
        "34d5b554d0dd9bd0+167072",
        "6c346d8b-d186-4228-9adb-ae919d7131dd",
        "Greer Gwiffin",
    )
    rd.yummy("2020-08-05T17:09:31.52Z", "f02aeae2-5e6a-4098-9842-02d2273f25c7", "190a0f31-d686-4ac4-a7f3-cfc87b72c145")
    rd.incineration(
        "2020-08-05T17:09:41.638Z",
        "3f8bbb15-61c0-4e3f-8e4a-907a5fb1565e",
        "3064c7d6-91cc-4c2a-a433-1ce1aabc1ad4",
        "34d5b554d0dd9bd0+170067",
        "f7715b05-ee69-43e5-a0e5-8e3d34270c82",
        "Caligula Lotus",
    )
    rd.yummy("2020-08-05T18:03:54.95Z", "eb67ae5e-c4bf-46ca-bbbc-425cd34182ff", "8c8cc584-199b-4b76-b2cd-eaa9a74965e5")
    rd.allergic(
        "2020-08-05T20:10:36.758Z", "878c1bf6-0d21-4659-bfee-916c8314d69c", "1f159bab-923a-4811-b6fa-02bfde50925a"
    )
    rd.allergic(
        "2020-08-05T22:23:02.434Z", "bfd38797-8404-4b38-8b82-341da28b1f83", "f9c0d3cb-d8be-4f53-94c9-fc53bcbce520"
    )
    rd.allergic(
        "2020-08-06T04:02:38.465Z", "23e4cbc1-e9cd-47fa-a35b-bfa06f726cb7", "9786b2c9-1205-4718-b0f7-fc000ce91106"
    )
    rd.incineration(
        "2020-08-06T04:07:20.788Z",
        "bfd38797-8404-4b38-8b82-341da28b1f83",
        "f9c0d3cb-d8be-4f53-94c9-fc53bcbce520",
        "6ddef1597f857540+34758",
        "34267632-8c32-4a8b-b5e6-ce1568bb0639",
        "Gunther O'Brian",
    )
    rd.allergic(
        "2020-08-06T09:06:10.179Z", "878c1bf6-0d21-4659-bfee-916c8314d69c", "5ca7e854-dc00-4955-9235-d7fcd732ddcf"
    )
    rd.allergic(
        "2020-08-06T10:07:24.81Z", "878c1bf6-0d21-4659-bfee-916c8314d69c", "1f159bab-923a-4811-b6fa-02bfde50925a"
    )
    rd.allergic(
        "2020-08-06T10:22:29.133Z", "878c1bf6-0d21-4659-bfee-916c8314d69c", "ea44bd36-65b4-4f3b-ac71-78d87a540b48"
    )
    rd.incineration(
        "2020-08-06T14:15:15.54Z",
        "979aee4a-6d80-4863-bf1c-ee1a78e06024",
        "bd549bfe-b395-4dc0-8546-5c04c08e24a5",
        "6ddef1597f857540+194769",
        "a5f8ce83-02b2-498c-9e48-533a1d81aebf",
        "Evelton McBlase",
    )
    rd.incineration(
        "2020-08-06T22:21:13.646Z",
        "105bc3ff-1320-4e37-8ef0-8d595cb95dd0",
        "495a6bdc-174d-4ad6-8d51-9ee88b1c2e4a",
        "a1fde487f20d92e4+7377",
        "c31d874c-1b4d-40f2-a1b3-42542e934047",
        "Cedric Spliff",
    )
    rd.incineration(
        "2020-08-07T00:18:45.68Z",
        "bfd38797-8404-4b38-8b82-341da28b1f83",
        "7b0f91aa-4d66-4362-993d-6ff60f7ce0ef",
        "14ba1c3c7915336f+10570",
        "f7847de2-df43-4236-8dbe-ae403f5f3ab3",
        "Blood Hamburger",
    )
    rd.incineration(
        "2020-08-07T01:03:38.524Z",
        "979aee4a-6d80-4863-bf1c-ee1a78e06024",
        "b3d518b9-dc68-4902-b68c-0022ceb25aa0",
        "39d9d7e4e0c459dc+2002",
        "c755efce-d04d-4e00-b5c1-d801070d3808",
        "Basilio Fig",
    )
    rd.incineration(
        "2020-08-07T01:06:14.567Z",
        "979aee4a-6d80-4863-bf1c-ee1a78e06024",
        "4941976e-31fc-49b5-801a-18abe072178b",
        "39d9d7e4e0c459dc+3639",
        "21cbbfaa-100e-48c5-9cea-7118b0d08a34",
        "Juice Collins",
    )
    rd.incineration(
        "2020-08-07T01:11:47.134Z",
        "9debc64f-74b7-4ae1-a4d6-fce0144b6ea5",
        "90c6e6ca-77fc-42b7-94d8-d8afd6d299e5",
        "39d9d7e4e0c459dc+6748",
        "8ecea7e0-b1fb-4b74-8c8c-3271cb54f659",
        "Fitzgerald Blackburn",
    )
    rd.allergic(
        "2020-08-07T02:19:05.533Z", "ca3f1c8c-c025-4d8e-8eef-5be6accbeb16", "bfd9ff52-9bf6-4aaf-a859-d308d8f29616"
    )
    rd.incineration(
        "2020-08-07T05:20:18.606Z",
        "105bc3ff-1320-4e37-8ef0-8d595cb95dd0",
        "bd9d1d6e-7822-4ad9-bac4-89b8afd8a630",
        "39d9d7e4e0c459dc+71869",
        "c6e2e389-ed04-4626-a5ba-fe398fe89568",
        "Henry Marshallow",
    )
    rd.yummy("2020-08-07T06:25:00.034Z", "3f8bbb15-61c0-4e3f-8e4a-907a5fb1565e", "7a75d626-d4fd-474f-a862-473138d8c376")
    rd.yummy("2020-08-07T06:30:20.149Z", "3f8bbb15-61c0-4e3f-8e4a-907a5fb1565e", "ff5a37d9-a6dd-49aa-b6fb-b935fd670820")
    rd.incineration(
        "2020-08-07T07:10:21.61Z",
        "3f8bbb15-61c0-4e3f-8e4a-907a5fb1565e",
        "2b1cb8a2-9eba-4fce-85cf-5d997ec45714",
        "39d9d7e4e0c459dc+96560",
        "2e13249e-38ff-46a2-a55e-d15fa692468a",
        "Vito Kravitz",
    )
    rd.allergic(
        "2020-08-07T08:25:44.447Z", "bfd38797-8404-4b38-8b82-341da28b1f83", "36786f44-9066-4028-98d9-4fa84465ab9e"
    )
    rd.allergic(
        "2020-08-07T09:06:35.239Z", "b63be8c2-576a-4d6e-8daf-814f8bcea96f", "a38ada0a-aeac-4a3d-b9a5-968687ccd2f9"
    )
    rd.allergic(
        "2020-08-07T14:12:38.592Z", "b72f3061-f573-40d7-832a-5ad475bd7909", "58c9e294-bd49-457c-883f-fb3162fc668e"
    )
    rd.allergic(
        "2020-08-08T03:03:11.194Z", "9debc64f-74b7-4ae1-a4d6-fce0144b6ea5", "fa477c92-39b6-4a52-b065-40af2f29840a"
    )
    rd.yummy("2020-08-08T03:14:55.338Z", "8d87c468-699a-47a8-b40d-cfb73a5660ad", "c675fcdf-6117-49a6-ac32-99a89a3a88aa")
    rd.allergic(
        "2020-08-08T03:20:11.524Z", "23e4cbc1-e9cd-47fa-a35b-bfa06f726cb7", "13a05157-6172-4431-947b-a058217b4aa5"
    )
    rd.incineration(
        "2020-08-08T16:19:13.325Z",
        "b024e975-1c4a-4575-8936-a3754a08806a",
        "c83f0fe0-44d1-4342-81e8-944bb38f8e23",
        "09202d25e7ec6e51+71088",
        "97f5a9cd-72f0-413e-9e68-a6ee6a663489",
        "Kline Greenlemon",
    )
    rd.incineration(
        "2020-08-09T00:17:04.079Z",
        "747b8e4a-7e50-4638-a973-ea7950a3e739",
        "d74a2473-1f29-40fa-a41e-66fa2281dfca",
        "6f8db8bad7c7452f+2259",
        "5bcfb3ff-5786-4c6c-964c-5c325fcc48d7",
        "Paula Turnip",
    )


def season_3_early_fixup(rd: Redata):
    ALLERGY_FIX_TIMESTAMP = "2020-08-03T04:20:00Z"
    for player_id, allergy in S3_ALLERGY_FIXUP.items():
        rd.update_player(ALLERGY_FIX_TIMESTAMP, player_id, {"peanutAllergy": allergy})

    # this is also around when this happened :)
    rd.update_player(ALLERGY_FIX_TIMESTAMP, "a1628d97-16ca-4a75-b8df-569bae02bef9", {"soul": 1777})

def season_3_election(rd: Redata):
    S3_ELECTION_TIMESTAMP = "2020-08-09T19:00:00Z"

    # ...Spacetime Tears over Los Angeles...
    # ...The Infinite cit(ies) shine...
    rd.update_team(S3_ELECTION_TIMESTAMP, TACOS, {
        "fullName": "Unlimited Tacos",
        "location": "Unlimited"
    })
    for player_id in rd.teams[TACOS]["lineup"] + rd.teams[TACOS]["rotation"]:
        rd.update_player(S3_ELECTION_TIMESTAMP, player_id, {"name": "Wyatt Mason"})

    # Bloodlust blessed the Hades Tigers. Yazmin Mason's pitching stats were maxed out.
    for _ in range(76):
        rd.player_attr_change(S3_ELECTION_TIMESTAMP, "afc90398-b891-4cdf-9dea-af8a3a79d793", dict(
            shakespearianism=0.01,
            suppression=0.01,
            unthwackability=0.01,
            coldness=0.01,
            overpowerment=0.01,
            ruthlessness=0.01,
        ))

    # Hades Tigers sent their worst hitter, Alyssa Harrell, to the New York Millennials and received Mclaughlin Scorpler in return.
    rd.swap_player(S3_ELECTION_TIMESTAMP, TIGERS, "80de2b05-e0d4-4d33-9297-9951b2b5c950", MILLENNIALS, "a311c089-0df4-46bd-9f5d-8c45c7eb5ae2")

    # Philly Pies sent away their worst pitcher, Kevin Dudley, to the Charleston Shoe Thieves and received Forrest Bookbaby in return.
    rd.swap_player(S3_ELECTION_TIMESTAMP, PIES, "9786b2c9-1205-4718-b0f7-fc000ce91106", SHOE_THIEVES, "2ae8cbfc-2155-4647-9996-3f2591091baf")

    # Evil Wind Sprints blessed the Breckenridge Jazz Hands. Their baserunning was increased by 15%
    for player_id in rd.teams[JAZZ_HANDS]["lineup"]:
        rd.player_attr_change(S3_ELECTION_TIMESTAMP, player_id, dict(
            baseThirst=0.15,
            laserlikeness=0.15,
            groundFriction=0.15,
            continuation=0.15,
            indulgence=0.15,
        ))

    # The Jazz hands stole Nagomi Mcdaniel from the Hawai'i Fridays and sent Bevan Underbuck in return.
    rd.swap_player(S3_ELECTION_TIMESTAMP, FRIDAYS, "c0732e36-3731-4f1a-abdc-daa9563b6506", JAZZ_HANDS, "e6114fd4-a11d-4f6c-b823-65691bb2d288")

    # Summoning Circle blessed the Kansas City Breath Mints
    election_rng = Rng.parse("ff7c8068a29e94e9+27")
    # Rodriguez Internet's hitting was randomized from ½ to ★★½.
    rd.reroll_attributes(S3_ELECTION_TIMESTAMP, "4b6f0a4e-de18-44ad-b497-03b1f470c43c", election_rng, ["buoyancy", "thwackability", "moxie", "divinity", "musclitude", "patheticism", "martyrdom"])
    election_rng.step(1)
    # Grey Alvarado's hitting was randomized from ½ to ★★.
    rd.reroll_attributes(S3_ELECTION_TIMESTAMP, "64f4cd75-0c1e-42cf-9ff0-e41c4756f22a", election_rng, ["buoyancy", "thwackability", "moxie", "divinity", "musclitude", "patheticism", "martyrdom"])
    election_rng.step(1)
    # Eduardo Ingram's hitting was randomized from ★ to ★★★.
    rd.reroll_attributes(S3_ELECTION_TIMESTAMP, "c73d59dd-32a0-49ce-8ab4-b2dbb7dc94ec", election_rng, ["buoyancy", "thwackability", "moxie", "divinity", "musclitude", "patheticism", "martyrdom"])

    # The Rack blessed the Kansas City Breath Mints. Their defense was increased by 15%.
    for player_id in rd.teams[BREATH_MINTS]["lineup"] + rd.teams[BREATH_MINTS]["rotation"]:
        rd.player_attr_change(S3_ELECTION_TIMESTAMP, player_id, dict(
            omniscience=0.15,
            tenaciousness=0.15,
            watchfulness=0.15,
            anticapitalism=0.15,
            chasiness=0.15,
        ))

    # The Canada Moist Talkers, Miami Dale, Seattle Garages, and Breckenridge Jazz Hands had their baserunning decreased by 10%.
    for player_id in rd.teams[MOIST_TALKERS]["lineup"] + rd.teams[DALE]["lineup"] + rd.teams[GARAGES]["lineup"] + rd.teams[JAZZ_HANDS]["lineup"]:
        rd.player_attr_change(S3_ELECTION_TIMESTAMP, player_id, dict(
            baseThirst=0.1,
            laserlikeness=0.1,
            groundFriction=0.1,
            continuation=0.1,
            indulgence=0.1,
        ))

    # Feed your hitters coffee grounds. Team hitting changes from -5% to +15%
    # Pretty Plz? blessed the Seattle Garages. Their hitting was improved by 3%.
    pretty_plz = election_rng.next() * 0.2 - 0.05
    for player_id in rd.teams[GARAGES]["lineup"]:
        rd.player_attr_change(S3_ELECTION_TIMESTAMP, player_id, dict(
            thwackability=pretty_plz,
            moxie=pretty_plz,
            divinity=pretty_plz,
            musclitude=pretty_plz,
            patheticism=-pretty_plz,
            buoyancy=pretty_plz,
            martyrdom=pretty_plz,
        ))

    # Pseudo-Thumbs blessed the Seattle Garages. Their pitching was improved by 10%.
    for player_id in rd.teams[GARAGES]["rotation"]:
        rd.player_attr_change(S3_ELECTION_TIMESTAMP, player_id, dict(
            shakespearianism=0.1,
            suppression=0.1,
            unthwackability=0.1,
            coldness=0.1,
            overpowerment=0.1,
            ruthlessness=0.1,
            totalFingers=1
        ))

    # The Crabs stole Nagomi Mcdaniel from the Breckenridge Jazz Hands and sent Holden Stanton in return.
    rd.swap_player(S3_ELECTION_TIMESTAMP, JAZZ_HANDS, "c0732e36-3731-4f1a-abdc-daa9563b6506", CRABS, "817dee99-9ccf-4f41-84e3-dc9773237bc8")

    # Anticapitalism, brought to you by Friends at the Table. The Tacos maxed out their Anticapitalism attribute.
    for player_id in rd.teams[TACOS]["lineup"] + rd.teams[TACOS]["rotation"] + rd.teams[TACOS]["bench"] + rd.teams[TACOS]["bullpen"]:
        rd.update_player(S3_ELECTION_TIMESTAMP, player_id, dict(
            anticapitalism=1.0
        ))


    # Exploratory Surgeries blessed the Unlimited Tacos.
    # ... you know what, let's do this.
    comfort_glover = "e16c3f28-eecd-4571-be1a-606bbac36b2b" # (Comfort Glover)
    # r = Rng.parse("ff7c8068a29e94e9+51")
    assert round_rating(pitching_rating(rd.players[comfort_glover])) == 0.5

    # Wyatt Mason's pitching was randomized from ½ to ½.
    rd.reroll_attributes(S3_ELECTION_TIMESTAMP, comfort_glover, election_rng, ["shakespearianism", "suppression", "unthwackability", "coldness", "overpowerment", "ruthlessness"])
    assert round_rating(pitching_rating(rd.players[comfort_glover])) == 0.5

    # Wyatt Mason's pitching was randomized from ½ to ½.
    rd.reroll_attributes(S3_ELECTION_TIMESTAMP, comfort_glover, election_rng, ["shakespearianism", "suppression", "unthwackability", "coldness", "overpowerment", "ruthlessness"])
    assert round_rating(pitching_rating(rd.players[comfort_glover])) == 0.5
    
    # Wyatt Mason's pitching was randomized from ½ to 0.
    rd.reroll_attributes(S3_ELECTION_TIMESTAMP, comfort_glover, election_rng, ["shakespearianism", "suppression", "unthwackability", "coldness", "overpowerment", "ruthlessness"])
    assert round_rating(pitching_rating(rd.players[comfort_glover])) == 0

    # The Firefighters stole Axel Trololol from the Kansas City Breath Mints and sent Atlas Guerra in return.
    rd.swap_player(S3_ELECTION_TIMESTAMP, FIREFIGHTERS, "d46abb00-c546-4952-9218-4f16084e3238", BREATH_MINTS, "3af96a6b-866c-4b03-bc14-090acf6ecee5")

    # Team-Building Exercise blessed the Chicago Firefighters
    # election_rng = Rng.parse("ff7c8068a29e94e9+70")
    election_rng.step(1)
    # Joshua Butt's hitting was randomized from 0 to ★★½.
    rd.reroll_attributes(S3_ELECTION_TIMESTAMP, "69196296-f652-42ff-b2ca-0d9b50bd9b7b", election_rng, ["buoyancy", "thwackability", "moxie", "divinity", "musclitude", "patheticism", "martyrdom"])
    election_rng.step(1)
    # Edric Tosser's hitting was randomized from ½ to ★★★½.
    rd.reroll_attributes(S3_ELECTION_TIMESTAMP, "d23a1f7e-0071-444e-8361-6ae01f13036f", election_rng, ["buoyancy", "thwackability", "moxie", "divinity", "musclitude", "patheticism", "martyrdom"])
    election_rng.step(1)
    # Paula Mason's hitting was randomized from ½ to ★★★½.
    rd.reroll_attributes(S3_ELECTION_TIMESTAMP, "c0177f76-67fc-4316-b650-894159dede45", election_rng, ["buoyancy", "thwackability", "moxie", "divinity", "musclitude", "patheticism", "martyrdom"])

    # Performance Enhancing Demons blessed the Chicago Firefighters. Their overall attributes were raised by 8%.
    for player_id in rd.teams[FIREFIGHTERS]["lineup"]:
        rd.player_attr_change(S3_ELECTION_TIMESTAMP, player_id, dict(
            thwackability=0.08,
            moxie=0.08,
            divinity=0.08,
            musclitude=0.08,
            patheticism=-0.08,
            buoyancy=0.08,
            baseThirst=0.08,
            laserlikeness=0.08,
            groundFriction=0.08,
            continuation=0.08,
            indulgence=0.08,
            martyrdom=0.08,
            omniscience=0.08,
            tenaciousness=0.08,
            watchfulness=0.08,
            anticapitalism=0.08,
            chasiness=0.08,
        ))

    for player_id in rd.teams[FIREFIGHTERS]["rotation"]:
        rd.player_attr_change(S3_ELECTION_TIMESTAMP, player_id, dict(
            shakespearianism=0.08,
            suppression=0.08,
            unthwackability=0.08,
            coldness=0.08,
            overpowerment=0.08,
            ruthlessness=0.08,
            omniscience=0.08,
            tenaciousness=0.08,
            watchfulness=0.08,
            anticapitalism=0.08,
            chasiness=0.08,
            totalFingers=1,
        ))


    pass

def main():
    rd = Redata()

    # Season 1 start setup
    S1_START_TIMESTAMP = "2020-07-20T00:00:00Z"
    player_name_queue = list(S1_PLAYER_NAMES)
    rng = Rng.parse("0eeb2966d0cf3cfd+1")
    for team_id in ORIGINAL_TEAM_ORDER:
        team_player_ids = []
        for _ in range(25):
            player_id, player_name = player_name_queue.pop(0)
            player = generate_player(rng, player_id, player_name)
            rd.create_player(S1_START_TIMESTAMP, player)
            team_player_ids.append(player_id)
        team_data = dict(S1_TEAM_DATA[team_id])
        team_data["lineup"] = team_player_ids[0:9]
        team_data["rotation"] = team_player_ids[9:14]
        team_data["bullpen"] = team_player_ids[14:22]
        team_data["bench"] = team_player_ids[22:25]
        assert len(team_data["lineup"]) == 9
        assert len(team_data["rotation"]) == 5
        assert len(team_data["bullpen"]) == 8
        assert len(team_data["bench"]) == 3
        rd.create_team(S1_START_TIMESTAMP, team_data)

    season_1_election(rd)
    season_2(rd)

    rd.assert_consistency("2020-08-01T00:00:00Z")

    season_2_election(rd)
    rd.assert_consistency("2020-08-02T19:40:00Z")
    # on sim restart, it would find all players without an allergy and roll to give them an allergy
    # this ran at least a few times before being turned off...
    # we haven't been able to crack those RNG locations yet so those are hardcoded
    season_2_election_postfix(rd)
    rd.assert_consistency("2020-08-02T21:40:00Z")
    season_2_election_postfix_2(rd)
    rd.assert_consistency("2020-08-02T23:40:00Z")

    season_3_early_fixup(rd)
    season_3(rd)
    rd.assert_consistency("2020-08-09T03:00:00Z")

    season_3_election(rd)
    rd.assert_consistency("2020-08-10T03:00:00Z")

    pass


if __name__ == "__main__":
    main()
