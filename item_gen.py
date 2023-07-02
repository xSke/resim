import dataclasses
from enum import Enum, auto
import math

from collections.abc import Mapping
from typing import Any, Optional, Protocol, Union


class RollFn(Protocol):
    def __call__(self, label: str, lower: float = 0, upper: float = 1) -> float:
        ...


@dataclasses.dataclass
class StatRoll:
    stat: str
    slope: Optional[float]
    intercept: Optional[float]

    def apply(self, roll: float):
        if not self.slope or not self.intercept:
            return None
        return self.slope * roll + self.intercept


class ItemRollType(Enum):
    GLITTER = auto()
    CHEST = auto()
    PRIZE = auto()


BASE_TYPES = {
    "Base": "baseThirst",
    "Bat": "thwackability",
    "Board": "groundFriction",
    "Broom": "divinity",
    "Cannon": "overpowerment",
    "Cap": "unthwackability",
    "Cape": "watchfulness",
    "Chair": "suppression",
    "Egg": "tragicness",
    "Field": "tenaciousness",
    "Glove": "omniscience",
    "Helmet": "pressurization",
    "Jacket": "musclitude",
    "Jersey": "musclitude",
    "Necklace": "moxie",
    "Phone": "omniscience",
    "Potion": "indulgence",
    "Quill": "shakespearianism",
    "Ring": "ruthlessness",
    "Shoes": "laserlikeness",
    "Socks": "continuation",
    "Sunglasses": "cinnamon",
}


ELEMENTS_S15 = {
    "Chaotic": [
        StatRoll("thwackability", -0.03, -0.01),
        StatRoll("unthwackability", -0.03, -0.01),
        StatRoll("patheticism", -0.03, -0.01),
        StatRoll("moxie", 0.1, 0.2),
    ],
    "Cryogenic": [
        StatRoll("suppression", 0.075, 0.075),
        StatRoll("coldness", 0.075, 0.075),
        StatRoll("overpowerment", 0.06, 0.06),
    ],
    "Golden": [],
    "Metaphorical": [
        StatRoll("Shakespearianism", 0.05, 0.07),
        StatRoll("watchfulness", 0.05, 0.07),
        StatRoll("chasiness", 0.05, 0.07),
        StatRoll("continuation", 0.05, -0.1),
    ],
    "Frosty": [
        StatRoll("coldness", 0.05, 0.1),
        # I couldn't figure these two out.
        StatRoll("chasiness", None, None),
        StatRoll("watchfulness", None, None),
    ],
    "Inflatable": [
        StatRoll("buoyancy", 0.075, 0.075),
        StatRoll("overpowerment", 0.04, -0.08),
        StatRoll("patheticism", 0.075, 0.075),
    ],
    "Leg": [
        StatRoll("laserlikeness", 0.05, 0.05),
        StatRoll("chasiness", 0.05, 0.05),
    ],
    "Parasitic": [],
    "Plant-Based": [
        StatRoll("watchfulness", 0.1, 0.1),
        StatRoll("suppression", 0.1, 0.1),
        StatRoll("buoyancy", -0.14, -0.075),
    ],
    # suffixes
    "Blaserunning": [],
    "Vanity": [
        StatRoll("martyrdom", 0.05, -0.1),
        StatRoll("musclitude", 0.05, 0.05),
    ],
}


ELEMENTS = {
    # Pre-prefixes
    "Catcher's": [
        StatRoll("omniscience", None, None),
        StatRoll("tenaciousness", None, None),
    ],
    # Prefixes
    "Actual": [
        StatRoll("continuation", None, None),
        StatRoll("indulgence", None, None),
        StatRoll("laserlikeness", None, None),
    ],
    "Aluminum": [
        StatRoll("groundFriction", None, None),
        StatRoll("musclitude", None, None),
        StatRoll("buoyancy", None, None),
    ],
    "Ambitious": [],
    "Birthday": [
        StatRoll("cinnamon", None, None),
        StatRoll("divinity", None, None),
        StatRoll("omniscience", None, None),
    ],
    "Brambly": [
        StatRoll("ruthlessness", 0.1, 0.1),
        StatRoll("anticapitalism", 0.1, 0.1),
    ],
    "Bright": [
        StatRoll("cinnamon", None, None),
        StatRoll("divinity", None, None),
    ],
    "Business": [
        StatRoll("unthwackability", None, None),
        StatRoll("pressurization", None, None),
        StatRoll("anticapitalism", None, None),
    ],
    "Careful": [],
    "Casual": [
        StatRoll("cinnamon", None, None),
        StatRoll("thwackability", None, None),
        StatRoll("moxie", None, None),
    ],
    "Chaotic": [
        StatRoll("moxie", None, None),
        StatRoll("unthwackability", None, None),
        StatRoll("thwackability", None, None),
        StatRoll("patheticism", None, None),
    ],
    "Charitable": [
        StatRoll("anticapitalism", None, None),
        StatRoll("martyrdom", None, None),
        StatRoll("tragicness", None, None),
    ],
    "Chunky": [],
    "Clutch": [],
    "Coasting": [],
    "Confetti": [
        StatRoll("indulgence", None, None),
        StatRoll("continuation", None, None),
        StatRoll("cinnamon", None, None),
    ],
    "Cool": [
        StatRoll("moxie", 0.05, 0.1),
        StatRoll("coldness", 0.05, 0.1),
        StatRoll("laserlikeness", 0.05, 0.1),
    ],
    "Crow-Cursed": [],
    "Cryogenic": [
        StatRoll("suppression", 0.1, 0.15),
        StatRoll("coldness", 0.05, 0.2),
        StatRoll("overpowerment", 0.09, 0.06),
    ],
    "Dancing": [
        StatRoll("cinnamon", None, None),
        StatRoll("moxie", None, None),
        StatRoll("laserlikeness", None, None),
    ],
    "Fancy": [
        StatRoll("shakespearianism", None, None),
        StatRoll("coldness", None, None),
        StatRoll("pressurization", None, None),
    ],
    "Fire Eating": [],
    "Fireproof": [],
    "Flickering": [],
    "Fliickerrriiing": [],
    "Frosty": [
        StatRoll("coldness", 0.05, 0.1),
        StatRoll("chasiness", 0.3, 0.1),
        StatRoll("watchfulness", 0.3, 0.1),
    ],
    "Golden": [],
    "Gravity": [],
    "Greedy": [
        StatRoll("indulgence", 0.1, 0.15),
        StatRoll("continuation", 0.1, 0.15),
        StatRoll("baseThirst", 0.1, 0.15),
        StatRoll("laserlikeness", 0.1, -0.2),
    ],
    "Hard": [
        StatRoll("ruthlessness", 0.1, 0.15),
        StatRoll("musclitude", 0.1, 0.15),
        StatRoll("omniscience", 0.075, -0.15),
    ],
    "Hearty": [
        StatRoll("tenaciousness", 0.12, 0.08),
        StatRoll("pressurization", 0.12, 0.08),
        StatRoll("indulgence", 0.12, 0.08),
    ],
    "Holey": [
        StatRoll("divinity", 0.15, 0.1),
        StatRoll("overpowerment", -0.1, -0.15),
        StatRoll("patheticism", 0.1, 0.1),
        StatRoll("tragicness", 0.1, 0.1),
    ],
    "Hot": [
        StatRoll("thwackability", 0.2, 0.2),
        StatRoll("coldness", -0.11, -0.04),
        StatRoll("tenaciousness", -0.11, -0.04),
    ],
    "Inflatable": [
        StatRoll("buoyancy", 0.1, 0.15),
        StatRoll("overpowerment", 0.05, -0.1),
        StatRoll("patheticism", 0.075, 0.075),
    ],
    "Limestone": [
        StatRoll("unthwackability", 0.2, 0.15),
        StatRoll("overpowerment", 0.08, -0.1),
    ],
    "Literal": [
        StatRoll("overpowerment", None, None),
        StatRoll("unthwackability", None, None),
    ],
    "Lucky": [
        StatRoll("thwackability", 0.1, 0.1),
        StatRoll("divinity", 0.1, 0.1),
        StatRoll("moxie", 0.1, -0.2),
        StatRoll("patheticism", 0.1, 0.1),
    ],
    "Maxi": [],
    "Mesh": [
        StatRoll("moxie", 0.15, 0.2),
        StatRoll("overpowerment", 0.1, -0.15),
    ],
    "Metaphorical": [
        StatRoll("Shakespearianism", 0.3, 0.2),
        StatRoll("watchfulness", 0.2, 0.2),
        StatRoll("chasiness", 0.2, 0.2),
        StatRoll("continuation", 0.15, -0.2),
    ],
    "Noise-Cancelling": [],
    "Offworld": [],
    "Parasitic": [],
    "Party": [
        StatRoll("pressurization", None, None),
        StatRoll("moxie", None, None),
    ],
    "Passionate": [
        StatRoll("baseThirst", 0.1, 0.15),
        StatRoll("continuation", 0.1, 0.1),
    ],
    "Plant-Based": [
        StatRoll("watchfulness", 0.2, 0.2),
        StatRoll("suppression", 0.1, 0.15),
        StatRoll("buoyancy", 0.05, -0.1),
    ],
    "Protector": [],
    "Repeating": [],
    "Replica": [],
    "Rubber": [
        StatRoll("Ground Friction", 0.11, -0.15),
        StatRoll("laserlikeness", 0.11, -0.15),
        StatRoll("unthwackability", 0.15, 0.25),
        StatRoll("overpowerment", 0.05, -0.15),
    ],
    "Sharp": [
        StatRoll("thwackability", 0.1, 0.1),
        StatRoll("unthwackability", 0.1, 0.1),
        StatRoll("Ground Friction", 0.1, 0.1),
        StatRoll("tenaciousness", 0.1, -0.2),
    ],
    "Slimy": [
        StatRoll("laserlikeness", 0.1, -0.2),
        StatRoll("watchfulness", 0.1, 0.1),
        StatRoll("omniscience", 0.1, 0.1),
        StatRoll("tenaciousness", 0.1, 0.1),
    ],
    "Smokey": [
        StatRoll("ruthlessness", 0.1, 0.1),
        StatRoll("tragicness", 0.1, 0.1),
    ],
    "Smooth": [],
    "Snow": [
        StatRoll("coldness", None, None),
    ],
    "Spicy": [],
    "Spirit": [StatRoll("buoyancy", None, None), StatRoll("divinity", None, None), StatRoll("martyrdom", None, None)],
    "Squiddish": [],
    "Super Roamin'": [],
    "Trader": [],
    "Traitor": [],
    "Travelling": [],
    "Unambitious": [],
    "Uncertain": [],
    "Underhanded": [],
    "Unfreezable": [],
    "Weird": [
        StatRoll("tragicness", 0.24, 0.01),
        StatRoll("Shakespearianism", 0.24, 0.01),
        StatRoll("Ground Friction", 0.24, 0.01),
        StatRoll("patheticism", 0.24, 0.01),
        StatRoll("Cinnamon", 0.24, 0.01),
    ],
    "Wooden": [
        StatRoll("thwackability", 0.2, 0.2),
        StatRoll("laserlikeness", -0.1, -0.05),
        StatRoll("tenaciousness", -0.1, -0.05),
    ],
    # Post prefixes
    "Air": [
        StatRoll("buoyancy", 0.075, 0.075),
        StatRoll("divinity", 0.075, 0.075),
        StatRoll("laserlikeness", 0.075, 0.075),
    ],
    "Arm": [
        StatRoll("thwackability", 0.1, 0.1),
        StatRoll("unthwackability", 0.1, 0.1),
    ],
    "Bash": [
        StatRoll("musclitude", None, None),
        StatRoll("cinnamon", None, None),
    ],
    "Batter": [
        StatRoll("buoyancy", None, None),
        StatRoll("divinity", None, None),
        StatRoll("martyrdom", None, None),
        StatRoll("moxie", None, None),
        StatRoll("musclitude", None, None),
        StatRoll("thwackability", None, None),
        StatRoll("patheticism", None, None),
        StatRoll("tragicness", None, None),
    ],
    "Blood": [
        StatRoll("Martyrdom", 0.15, 0.1),
        StatRoll("baseThirst", 0.075, -0.15),
        StatRoll("divinity", 0.15, 0.1),
    ],
    "Boom": [
        StatRoll("divinity", None, None),
        StatRoll("cinnamon", None, None),
        StatRoll("tragicness", None, None),
    ],
    "Concrete": [
        StatRoll("???", None, None),
    ],
    "Force": [],
    "Glass": [],
    "Gunblade": [
        StatRoll("thwackability", None, None),
        StatRoll("divinity", None, None),
    ],
    "Head": [
        StatRoll("moxie", 0.1, 0.1),
        StatRoll("omniscience", 0.1, 0.1),
    ],
    "Leg": [
        StatRoll("laserlikeness", 0.1, 0.15),
        StatRoll("chasiness", 0.1, 0.15),
    ],
    "Night Vision": [],
    "Paper": [
        StatRoll("???", None, None),
    ],
    "Plastic": [],
    "Rock": [
        StatRoll("???", None, None),
    ],
    "Rocket": [
        StatRoll("laserlikeness", None, None),
    ],
    "Shoveling": [
        StatRoll("thwackability", None, None),
        StatRoll("martyrdom", None, None),
    ],
    "Skate": [],
    "Slowdance": [
        StatRoll("pressurization", None, None),
    ],
    "Steel": [],
    # Suffixes
    "Bass": [
        StatRoll("pressurization", None, None),
    ],
    "Bird Seed": [],
    "Blaserunning": [],
    "Charisma": [
        StatRoll("moxie", 0.1, 0.1),
        StatRoll("Cinnamon", 0.1, 0.1),
        StatRoll("divinity", 0.1, 0.1),
    ],
    "Containment": [],
    "Dexterity": [
        StatRoll("thwackability", 0.1, 0.1),
        StatRoll("omniscience", 0.1, 0.1),
        StatRoll("continuation", 0.1, 0.1),
    ],
    "Entanglement": [],
    "the Famine": [
        StatRoll("thwackability", 0.15, -0.25),
        StatRoll("unthwackability", 0.15, 0.1),
    ],
    "the Feast": [
        StatRoll("thwackability", None, None),
        StatRoll("unthwackability", None, None),
    ],
    "Fourtitude": [],
    "Good Vibes": [
        StatRoll("cinnamon", None, None),
        StatRoll("pressurization", None, None),
    ],
    "Intelligence": [
        StatRoll("ruthlessness", 0.1, 0.1),
        StatRoll("anticapitalism", 0.1, 0.1),
        StatRoll("Shakespearianism", 0.1, 0.1),
    ],
    "Invitation": [
        StatRoll("cinnamon", None, None),
    ],
    "Minimization": [],
    "Observation": [],
    "RAM": [],
    "Strength": [
        StatRoll("musclitude", 0.15, 0.1),
        StatRoll("overpowerment", 0.15, 0.1),
    ],
    "Stamina": [
        StatRoll("tenaciousness", 0.1, 0.1),
        StatRoll("chasiness", 0.1, 0.1),
        StatRoll("continuation", 0.1, 0.1),
        StatRoll("baseThirst", 0.1, 0.1),
    ],
    "Subtraction": [],
    "Vanity": [
        StatRoll("musclitude", None, None),
        StatRoll("martyrdom", None, None),
    ],
    "Vitality": [
        StatRoll("Ground Friction", 0.1, 0.1),
        StatRoll("baseThirst", 0.1, 0.1),
        StatRoll("pressurization", 0.1, 0.1),
    ],
    "Wisdom": [
        StatRoll("omniscience", 0.1, 0.1),
        StatRoll("watchfulness", 0.1, 0.1),
        StatRoll("Indulence", 0.1, 0.1),
    ],
}


BASE_STAT_PARAMS = {15: (0.1, 0.05), 16: (0.1, 0.1), 17: (0.1, 0.1), 18: (0.1, 0.1)}
BASE_TYPE_POOL = {
    15: (
        "Necklace",
        "Sunglasses",
        "Glove",
        "Jersey",
        "Bat",
        "Cap",
        "Shoes",
        "Ring",
    ),
    16: (
        "Bat",
        "Cap",
        "Necklace",
        "Ring",
        "Glove",
        "Shoes",
        "Jersey",
        "Sunglasses",
    ),
    17: (
        "Bat",
        "Cap",
        "Necklace",
        "Ring",
        "Glove",
        "Shoes",
        "Jersey",
        "Sunglasses",
        "Helmet",
        "Socks",
    ),
    18: (
        "Bat",
        "Cap",
        "Necklace",
        "Ring",
        "Glove",
        "Shoes",
        "Jersey",
        "Sunglasses",
        "Helmet",
        "Socks",
    ),
}


NUM_ELEMENTS_FN = {
    (15, 0): {ItemRollType.GLITTER: lambda x: 0 if x < 0.5 else 1},
    (16, 0): {
        ItemRollType.CHEST: lambda x: 0 if x < 0.05 else 1 if x < 0.55 else 2 if x < 0.95 else 3,
        ItemRollType.GLITTER: lambda x: 0 if x < 0.333 else 1 if x < 0.8 else 2,
    },
    (16, 27): {
        ItemRollType.CHEST: lambda x: 0 if x < 0.05 else 1 if x < 0.55 else 2 if x < 0.95 else 3,
        ItemRollType.GLITTER: lambda x: 0 if x < 0.5 else 1,
    },
    (17, 0): {
        ItemRollType.CHEST: lambda x: 0 if x < 0.05 else 1 if x < 0.55 else 2 if x < 0.95 else 3,
        ItemRollType.GLITTER: lambda x: 0 if x < 0.35 else 1,
        ItemRollType.PRIZE: lambda x: 1 if x < 0.5 else 2 if x < 0.95 else 3,
    },
    (18, 0): {
        ItemRollType.CHEST: lambda x: 0 if x < 0.05 else 1 if x < 0.55 else 2 if x < 0.95 else 3,
        ItemRollType.GLITTER: lambda x: 0 if x < 0.5 else 1 if x < 0.9 else 2,
        ItemRollType.PRIZE: lambda x: 1 if x < 0.45 else 2 if x < 0.95 else 3,
    },
}


PREFIX_POOL = {
    # This is almost certainly wrong, but we don't have enough items in this season to be sure.
    # It almost certainly contains 37 elements, but exactly which ones and the order are unclear.
    (15, 0): (
        "Lucky",
        "Sharp",
        "Chaotic",
        "Wooden",
        "Cool",
        "Frosty",
        "Hot",
        "Brambly",
        "Hard",
        "Passionate",
        "Greedy",
        "Slimy",
        "Smokey",
        "Weird",
        "Aluminum",
        "Inflatable",
        "Rubber",
        "Mesh",
        "Holey",
        "Hearty",
        "?????",
        "Metaphorical",
        "Plant-Based",
        "Cryogenic",
        "Gravity",
        "Noise-Cancelling",
        "Fireproof",
        "Repeating",
        "?????",
        "Chunky",
        "Parasitic",
        "Clutch",
        "Golden",
        "Travelling",
        "Squiddish",
        "Fire Eating",
        "Ambitious",
    ),
    (16, 0): (
        "Careful",
        "Ambitious",
        "Fire Eating",
        "Golden",
        "Squiddish",
        "Travelling",
        "?????",
        "Clutch",
        "Chunky",
        "Parasitic",
        "Repeating",
        "Fireproof",
        "Noise-Cancelling",
        "Gravity",
        "Cryogenic",
        "Plant-Based",
        #'?????',
        "Hearty",
        "Metaphorical",
        "Holey",
        "Limestone",
        "Mesh",
        "Rubber",
        "Aluminum",
        "Weird",
        "Smokey",
        "Inflatable",
        "Slimy",
        "Greedy",
        "Passionate",
        "Hard",
        "Frosty",
        "Brambly",
        "Hot",
        "Cool",
        "Wooden",
        "Sharp",
        "Chaotic",
        #'Lucky',
    ),
    (16, 27): (
        "Careful",
        "Ambitious",
        "Fire Eating",
        "Golden",
        "Squiddish",
        "Travelling",
        "?????",
        "Clutch",
        "Chunky",
        "Parasitic",
        "Repeating",
        "Fireproof",
        "Noise-Cancelling",
        "Gravity",
        "Cryogenic",
        "Plant-Based",
        "Metaphorical",
        "?????",
        "Hearty",
        "Holey",
        "Limestone",
        "Mesh",
        "Rubber",
        "Aluminum",
        "Weird",
        "Smokey",
        "Inflatable",
        "Slimy",
        "Greedy",
        "Passionate",
        "Hard",
        "Brambly",
        "Frosty",
        "Hot",
        "Cool",
        "Wooden",
        "Sharp",
        "Chaotic",
        "Lucky",
    ),
    (16, 60): (
        "Careful",
        "Ambitious",
        "Fire Eating",
        "Golden",
        "Squiddish",
        "Travelling",
        "Parasitic",
        "Clutch",
        "Chunky",
        "Smooth",
        "Repeating",
        "Fireproof",
        "Noise-Cancelling",
        "Gravity",
        "Cryogenic",
        "Plant-Based",
        "Metaphorical",
        "?????",
        "Hearty",
        "Holey",
        "Limestone",
        "Mesh",
        "Rubber",
        "Aluminum",
        "Weird",
        "Smokey",
        "Inflatable",
        "Slimy",
        "Greedy",
        "Passionate",
        "Hard",
        "Brambly",
        "Frosty",
        "Hot",
        "Cool",
        "Wooden",
        "Sharp",
        "Chaotic",
        "Lucky",
    ),
    # Sigh. This is just to change one item from Wooden to Cool.
    (16, 76): (
        "Careful",
        "Ambitious",
        "Fire Eating",
        "Golden",
        "Squiddish",
        "Travelling",
        "Parasitic",
        "Clutch",
        "Chunky",
        "Smooth",
        "Repeating",
        "Fireproof",
        "Noise-Cancelling",
        "Gravity",
        "Cryogenic",
        "Plant-Based",
        "Metaphorical",
        "?????",
        "Hearty",
        "Holey",
        "Limestone",
        "Mesh",
        "Rubber",
        "Aluminum",
        "Weird",
        "Smokey",
        "Inflatable",
        "Slimy",
        "Greedy",
        "Passionate",
        "Hard",
        "Brambly",
        "Frosty",
        "Hot",
        "Cool",
        "Wooden",
        "Sharp",
        "Chaotic",
        # "Lucky",
    ),
    (16, 77): (
        "Careful",
        "Ambitious",
        "Fire Eating",
        "Golden",
        "Squiddish",
        "Travelling",
        "Parasitic",
        "Clutch",
        "Chunky",
        "Smooth",
        "Repeating",
        "Fireproof",
        "Noise-Cancelling",
        "Gravity",
        "Cryogenic",
        "Plant-Based",
        "Metaphorical",
        "?????",
        "Hearty",
        "Holey",
        "Limestone",
        "Mesh",
        "Rubber",
        "Aluminum",
        "Weird",
        "Smokey",
        "Inflatable",
        "Slimy",
        "Greedy",
        "Passionate",
        "Hard",
        "Brambly",
        "Frosty",
        "Hot",
        "Cool",
        "Wooden",
        "Sharp",
        "Chaotic",
        "Lucky",
    ),
    (17, 0): (
        "Careful",
        "Ambitious",
        "Fire Eating",
        "Golden",
        "Squiddish",
        "Travelling",
        "Parasitic",
        "Clutch",
        "Chunky",
        "Smooth",
        "Repeating",
        "Fireproof",
        "Noise-Cancelling",
        "Gravity",
        "Cryogenic",
        "Plant-Based",
        "Metaphorical",
        "Actual",
        "Hearty",
        "Holey",
        "Limestone",
        "Mesh",
        "Rubber",
        "Aluminum",
        "Weird",
        "Smokey",
        "Inflatable",
        "Slimy",
        "Greedy",
        "Passionate",
        "Hard",
        "Brambly",
        "Frosty",
        "Hot",
        "Cool",
        "Wooden",
        "Sharp",
        "Chaotic",
        "Lucky",
    ),
    # This makes no sense, but need more data to figure out what's actually changed here.
    (17, 27): (
        "Careful",
        "Coasting",
        "Ambitious",
        "Fire Eating",
        "Golden",
        "Squiddish",
        "Travelling",
        "Parasitic",
        "Clutch",
        "Chunky",
        "Smooth",
        "Fireproof",
        "Noise-Cancelling",
        "Gravity",
        "Repeating",
        "Plant-Based",
        "Metaphorical",
        "Actual",
        "Hearty",
        "Holey",
        "Limestone",
        "Mesh",
        "Rubber",
        "Aluminum",
        "Weird",
        "Smokey",
        "Inflatable",
        "Slimy",
        "Greedy",
        "Passionate",
        "Hard",
        "Brambly",
        "Frosty",
        "Hot",
        "Cool",
        "Wooden",
        "Sharp",
        "Chaotic",
        "Lucky",
    ),
    (17, 58): (
        "Careful",
        "Ambitious",
        "Fire Eating",
        "Golden",
        "Squiddish",
        "Travelling",
        "Parasitic",
        "Clutch",
        "Chunky",
        "Smooth",
        "Repeating",
        "Fireproof",
        "Noise-Cancelling",
        "Gravity",
        "Cryogenic",
        "Plant-Based",
        "Metaphorical",
        "Actual",
        "Hearty",
        "Holey",
        "Limestone",
        "Mesh",
        "Rubber",
        "Aluminum",
        "Weird",
        "Smokey",
        "Charitable",
        "Slimy",
        "Greedy",
        "Passionate",
        "Hard",
        "Brambly",
        "Frosty",
        "Hot",
        "Cool",
        "Wooden",
        "Sharp",
        "Chaotic",
        "Lucky",
    ),
    (17, 63): (
        "Careful",
        "Coasting",
        "Ambitious",
        "Fire Eating",
        "Golden",
        "Squiddish",
        "Parasitic",
        "Clutch",
        "Chunky",
        "Smooth",
        "Travelling",
        "Fireproof",
        "Noise-Cancelling",
        "Gravity",
        "Repeating",
        "Plant-Based",
        "Metaphorical",
        "Actual",
        "Hearty",
        "Holey",
        "Limestone",
        "Mesh",
        "Rubber",
        "Aluminum",
        "Weird",
        "Smokey",
        "Inflatable",
        "Slimy",
        "Greedy",
        "Charitable",
        "Passionate",
        "Hard",
        "Brambly",
        "Frosty",
        "Hot",
        "Cool",
        "Wooden",
        "Sharp",
        "Chaotic",
        "Lucky",
    ),
    (17, 94): (
        "Careful",
        "Ambitious",
        "Fire Eating",
        "Golden",
        "Squiddish",
        "Travelling",
        "Parasitic",
        "Clutch",
        "Chunky",
        "Smooth",
        "Repeating",
        "Fireproof",
        "Noise-Cancelling",
        "Gravity",
        "Cryogenic",
        "Plant-Based",
        "Metaphorical",
        "Actual",
        "Hearty",
        "Holey",
        "Limestone",
        "Mesh",
        "Rubber",
        "Aluminum",
        "Weird",
        "Smokey",
        "Charitable",
        "Slimy",
        "Greedy",
        "Passionate",
        "Hard",
        "Brambly",
        "Frosty",
        "Hot",
        "Cool",
        "Wooden",
        "Sharp",
        "Chaotic",
        "Lucky",
    ),
    (18, 0): (
        "Careful",
        "Ambitious",
        "Fire Eating",
        "Golden",
        "Squiddish",
        "Travelling",
        "Parasitic",
        "Clutch",
        "Chunky",
        "Smooth",
        "Repeating",
        "Fireproof",
        "Noise-Cancelling",
        "Gravity",
        "Cryogenic",
        "Plant-Based",
        "Metaphorical",
        "Actual",
        "Hearty",
        "Holey",
        "Limestone",
        "Mesh",
        "Rubber",
        "Aluminum",
        "Weird",
        "Smokey",
        "Charitable",
        "Slimy",
        "Greedy",
        "Passionate",
        "Hard",
        "Brambly",
        "Frosty",
        "Hot",
        "Cool",
        "Wooden",
        "Sharp",
        "Chaotic",
        "Lucky",
    ),
    (18, 57): (
        "Careful",
        "Ambitious",
        "Fire Eating",
        "Golden",
        "Squiddish",
        "Travelling",
        "Parasitic",
        "Clutch",
        "Chunky",
        "Smooth",
        "Repeating",
        "Fireproof",
        "Noise-Cancelling",
        "Actual",
        "Hearty",
        "Holey",
        "Gravity",
        "Cryogenic",
        "Plant-Based",
        "Metaphorical",
        "Limestone",
        "Mesh",
        "Rubber",
        "Aluminum",
        "Weird",
        "Smokey",
        "Charitable",
        "Slimy",
        "Greedy",
        "Passionate",
        "Hard",
        "Brambly",
        "Frosty",
        "Hot",
        "Cool",
        "Wooden",
        "Sharp",
        "Chaotic",
        "Lucky",
    ),
    (18, 72): (
        "Careful",
        "Ambitious",
        "Fire Eating",
        "Golden",
        "Flickering",
        "Travelling",
        "Parasitic",
        "Clutch",
        "Chunky",
        "Smooth",
        "Repeating",
        "Fireproof",
        "Noise-Cancelling",
        "Gravity",
        "Cryogenic",
        "Plant-Based",
        "Metaphorical",
        "Actual",
        "Hearty",
        "Holey",
        "Limestone",
        "Mesh",
        "Rubber",
        "Aluminum",
        "Weird",
        "Smokey",
        "Charitable",
        "Slimy",
        "Greedy",
        "Passionate",
        "Hard",
        "Brambly",
        "Frosty",
        "Hot",
        "Cool",
        "Wooden",
        "Sharp",
        "Chaotic",
        "Lucky",
    ),
    # This makes no sense, but need more data to figure out what's actually changed here.
    (18, 85): (
        "Careful",
        "Coasting",
        "Fire Eating",
        "Golden",
        "Flickering",
        "Squiddish",
        "Travelling",
        "Parasitic",
        "Clutch",
        "Chunky",
        # "Smooth",
        "Repeating",
        "Fireproof",
        "Noise-Cancelling",
        "Gravity",
        "Cryogenic",
        "Plant-Based",
        "Metaphorical",
        "Actual",
        "Hearty",
        "Holey",
        "Limestone",
        "Mesh",
        "Rubber",
        "Aluminum",
        "Weird",
        "Smokey",
        "Inflatable",
        "Slimy",
        "Greedy",
        "Passionate",
        "Hard",
        "Brambly",
        "Frosty",
        "Hot",
        "Cool",
        "Wooden",
        "Sharp",
        "Chaotic",
        "Lucky",
    ),
}

# I don't know what the deal is with these changes. The only way I can get it to work with a uniform distribution
# Is to add and remove Paper for some reason, but maybe there's something more complicated going on.
POST_PREFIX_POOL = {
    (15, 0): ("Skate", "Rock", "Concrete", "Arm", "Leg", "Head", "Blood", "Air"),
    (16, 0): ("Skate", "Rock", "Concrete", "Arm", "Leg", "Paper", "Plastic", "Head", "Blood", "Air"),
    (16, 27): ("Skate", "Rock", "Concrete", "Arm", "Leg", "Head", "Blood", "Air"),
    (16, 60): ("Skate", "Rock", "Concrete", "Arm", "Paper", "Leg", "Head", "Blood", "Air"),
    (16, 72): ("Skate", "Rock", "Concrete", "Arm", "Leg", "Head", "Blood", "Air"),
    (17, 0): ("Skate", "Rock", "Concrete", "Arm", "Leg", "Head", "Blood", "Air"),
    (18, 0): ("Skate", "Rock", "Concrete", "Paper", "Arm", "Leg", "Head", "Blood", "Air"),
    (18, 72): ("Skate", "Rock", "Concrete", "Arm", "Leg", "Head", "Blood", "Air"),
    (18, 85): ("Rock", "Leg", "Arm", "Head", "Blood", "Air"),  # WTF???
}

SUFFIX_POOL = {
    (15, 0): (
        "Unknown",
        "Unknown",
        "Vanity",
        "Blaserunning",
    ),
    (16, 0): (
        "Blaserunning",
        "Fourtitude",
        "Stamina",
        "Vanity",
        "Vitality",
        "Intelligence",
        "Strength",
        "Charisma",
        "Wisdom",
        "Dexterity",
        "the Feast",
        "the Famine",
    ),
}


DELTA = 0.00000000000001

# TODO: pass in the actual item, so we can compare with expected rolls
def roll_item(
    season: int,
    day: int,
    roll_type: ItemRollType,
    roll: RollFn,
    expected: Optional[Union[str, Mapping[str, Any]]] = None,
):
    elements_roll = roll("num_elements")

    num_elements_key = max(filter(lambda key: key <= (season, day), NUM_ELEMENTS_FN))
    num_elements = NUM_ELEMENTS_FN[num_elements_key][roll_type](elements_roll)

    base_type_pool = BASE_TYPE_POOL[season]
    if expected:
        if isinstance(expected, str):
            expected_base = expected.rsplit(" of ", 1)[0].split()[-1]
        else:
            expected_base = expected["root"]["name"]
        index = base_type_pool.index(expected_base)
        lower = index / len(base_type_pool)
        upper = (index + 1) / len(base_type_pool)
    else:
        lower = 0
        upper = 1

    value = roll("base type", lower, upper)

    base_type = base_type_pool[math.floor(value * len(base_type_pool))]

    base_stat = BASE_TYPES[base_type]
    if expected and isinstance(expected, Mapping):
        base_stat_value = expected["root"]["adjustments"][0]["value"]
        slope, intercept = BASE_STAT_PARAMS[season]
        expected_roll = (base_stat_value - intercept) / slope

        lower = expected_roll - DELTA
        upper = expected_roll + DELTA
    else:
        lower = 0
        upper = 1

    value = roll(f"base stat({base_stat})", lower, upper)

    post_prefix = ""
    suffix = ""
    prefixes = []

    prefix_pool = list(PREFIX_POOL[max(filter(lambda key: key <= (season, day), PREFIX_POOL))])
    post_prefix_pool = POST_PREFIX_POOL[max(filter(lambda key: key <= (season, day), POST_PREFIX_POOL))]
    suffix_pool = SUFFIX_POOL[max(filter(lambda key: key <= (season, day), SUFFIX_POOL))]
    for _ in range(num_elements):
        value = roll(f"pre-prefix???")
        if value < 0.25:
            roll(f"pre-prefix???")

        found = False
        pool = prefix_pool
        if not post_prefix:
            value = roll("post prefix?")
            found = value < 0.25
            if found:
                pool = post_prefix_pool
        if not found and not suffix:
            value = roll("suffix?")
            found = value < 0.25
            if found:
                pool = suffix_pool

        value = roll("element")
        index = math.floor(value * len(pool))
        element = pool[index]
        if pool == post_prefix_pool:
            post_prefix = element
        elif pool == suffix_pool:
            suffix = element
        else:
            prefixes.append(element)
            prefix_pool.remove(element)

        elements = ELEMENTS if season > 15 else ELEMENTS_S15
        for stat_roll in elements[element]:
            value = roll(f"{element} {stat_roll.stat}")
            expected = stat_roll.apply(value)

    if roll_type != ItemRollType.PRIZE:
        roll("???")

    post_prefixes = [post_prefix] if post_prefix else []
    suffixes = ["of", suffix] if suffix else []

    return " ".join(prefixes + post_prefixes + [base_type] + suffixes)
