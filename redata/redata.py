import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))  # can't figure out the module system rn

from rng import Rng
from data import GameData, get_cached

# Lawful Good -> Chaotic Good -> Lawful Evil -> Chaotic Evil
ORIGINAL_TEAM_ORDER = [
    "b72f3061-f573-40d7-832a-5ad475bd7909",  # Lovers
    "878c1bf6-0d21-4659-bfee-916c8314d69c",  # Tacos
    "b024e975-1c4a-4575-8936-a3754a08806a",  # Steaks
    "adc5b394-8f76-416d-9ce9-813706877b84",  # Breath Mints
    "ca3f1c8c-c025-4d8e-8eef-5be6accbeb16",  # Firefighters
    "bfd38797-8404-4b38-8b82-341da28b1f83",  # Shoe Thieves
    "3f8bbb15-61c0-4e3f-8e4a-907a5fb1565e",  # Flowers
    "979aee4a-6d80-4863-bf1c-ee1a78e06024",  # Fridays
    "7966eb04-efcc-499b-8f03-d13916330531",  # Magic
    "36569151-a2fb-43c1-9df7-2df512424c82",  # Millennials
    "8d87c468-699a-47a8-b40d-cfb73a5660ad",  # Crabs
    "23e4cbc1-e9cd-47fa-a35b-bfa06f726cb7",  # Pies
    "f02aeae2-5e6a-4098-9842-02d2273f25c7",  # Sunbeams
    "57ec08cc-0411-4643-b304-0e80dbc15ac7",  # Wild Wings
    "747b8e4a-7e50-4638-a973-ea7950a3e739",  # Tigers
    "eb67ae5e-c4bf-46ca-bbbc-425cd34182ff",  # Moist Talkers
    "9debc64f-74b7-4ae1-a4d6-fce0144b6ea5",  # Spies
    "b63be8c2-576a-4d6e-8daf-814f8bcea96f",  # Dale
    "105bc3ff-1320-4e37-8ef0-8d595cb95dd0",  # Garages
    "a37f9158-7f82-46bc-908c-c9e2dda7c33b",  # Jazz Hands
]


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

# Order of generation
ATTR_ORDER_GEN = [
    "thwackability",
    "moxie",
    "divinity",
    "musclitude",
    "patheticism",
    "buoyancy",
    "baseThirst",
    "laserlikeness",
    "groundFriction",
    "continuation",
    "indulgence",
    "martyrdom",
    "tragicness",
    "shakespearianism",
    "suppression",
    "unthwackability",
    "coldness",
    "overpowerment",
    "ruthlessness",
    "omniscience",
    "tenaciousness",
    "watchfulness",
    "anticapitalism",
    "chasiness",
    "pressurization",
    # "cinnamon"
]

BATTING_ATTR_BLOCK = "tragicness buoyancy thwackability moxie divinity musclitude patheticism martyrdom".split()
PITCHING_ATTR_BLOCK = "shakespearianism suppression unthwackability coldness overpowerment ruthlessness".split()
BASERUNNING_ATTR_BLOCK = "baseThirst laserlikeness groundFriction continuation indulgence".split()
DEFENSE_ATTR_BLOCK = "omniscience tenaciousness watchfulness anticapitalism chasiness".split()


S1_START_TIMESTAMP = "2020-07-20T00:00:00Z"
S1_TEAM_DATA = {
    "105bc3ff-1320-4e37-8ef0-8d595cb95dd0": {
        "id": "105bc3ff-1320-4e37-8ef0-8d595cb95dd0",
        "emoji": "0x1F3B8",
        "slogan": "Smells like Team Spirit.",
        "fullName": "Seattle Garages",
        "location": "Seattle",
        "nickname": "Garages",
        "mainColor": "#2b4075",
        "secondaryColor": "#543d04",
        "shorthand": "SEA",
    },
    "23e4cbc1-e9cd-47fa-a35b-bfa06f726cb7": {
        "id": "23e4cbc1-e9cd-47fa-a35b-bfa06f726cb7",
        "emoji": "0x1F967",
        "slogan": "Pie or Die.",
        "fullName": "Philly Pies",
        "location": "Philly",
        "nickname": "Pies",
        "mainColor": "#399d8f",
        "secondaryColor": "#ffffff",
        "shorthand": "PHIL",
    },
    "36569151-a2fb-43c1-9df7-2df512424c82": {
        "id": "36569151-a2fb-43c1-9df7-2df512424c82",
        "emoji": "0x1F4F1",
        "slogan": "Youth Will Save Us",
        "fullName": "New York Millennials",
        "location": "New York",
        "nickname": "Millennials",
        "mainColor": "#ffd4d8",
        "secondaryColor": "#543d04",
        "shorthand": "NYMI",
    },
    "3f8bbb15-61c0-4e3f-8e4a-907a5fb1565e": {
        "id": "3f8bbb15-61c0-4e3f-8e4a-907a5fb1565e",
        "emoji": "0x1F339",
        "slogan": "Bloom Goes The Dynamite!",
        "fullName": "Boston Flowers",
        "location": "Boston",
        "nickname": "Flowers",
        "mainColor": "#f7d1ff",
        "secondaryColor": "#ffbaba",
        "shorthand": "BOF",
    },
    "57ec08cc-0411-4643-b304-0e80dbc15ac7": {
        "id": "57ec08cc-0411-4643-b304-0e80dbc15ac7",
        "emoji": "0x1F357",
        "slogan": "Wings. Beer. Blaseball.",
        "fullName": "Mexico City Wild Wings",
        "location": "Mexico City",
        "nickname": "Wild Wings",
        "mainColor": "#d15700",
        "secondaryColor": "#e8e8e8",
        "shorthand": "MCWW",
    },
    "747b8e4a-7e50-4638-a973-ea7950a3e739": {
        "id": "747b8e4a-7e50-4638-a973-ea7950a3e739",
        "emoji": "0x1F405",
        "slogan": "Never Look Back.",
        "fullName": "Hades Tigers",
        "location": "Hades",
        "nickname": "Tigers",
        "mainColor": "#5c1c1c",
        "secondaryColor": "#919191",
        "shorthand": "HAT",
    },
    "7966eb04-efcc-499b-8f03-d13916330531": {
        "id": "7966eb04-efcc-499b-8f03-d13916330531",
        "emoji": "0x2728",
        "slogan": "As Above, So Below",
        "fullName": "Yellowstone Magic",
        "location": "Yellowstone",
        "nickname": "Magic",
        "mainColor": "#bf0043",
        "secondaryColor": "#16756f",
        "shorthand": "YELL",
    },
    "878c1bf6-0d21-4659-bfee-916c8314d69c": {
        "id": "878c1bf6-0d21-4659-bfee-916c8314d69c",
        "emoji": "0x1F32E",
        "slogan": "72° and Spicy",
        "fullName": "Los Angeles Tacos",
        "location": "Los Angeles",
        "nickname": "Tacos",
        "mainColor": "#64376e",
        "secondaryColor": "#dbd26e",
        "shorthand": "LATA",
    },
    "8d87c468-699a-47a8-b40d-cfb73a5660ad": {
        "id": "8d87c468-699a-47a8-b40d-cfb73a5660ad",
        "emoji": "0x1F980",
        "slogan": "Soft Shells. Hard Balls.",
        "fullName": "Baltimore Crabs",
        "location": "Baltimore",
        "nickname": "Crabs",
        "mainColor": "#593037",
        "secondaryColor": "#c48b41",
        "shorthand": "BALC",
    },
    "979aee4a-6d80-4863-bf1c-ee1a78e06024": {
        "id": "979aee4a-6d80-4863-bf1c-ee1a78e06024",
        "emoji": "0x1F3DD",
        "slogan": "It's Island Time!",
        "fullName": "Hawaii Fridays",
        "location": "Hawaii",
        "nickname": "Fridays",
        "mainColor": "#3ee652",
        "secondaryColor": "#e67575",
        "shorthand": "HF",
    },
    "9debc64f-74b7-4ae1-a4d6-fce0144b6ea5": {
        "id": "9debc64f-74b7-4ae1-a4d6-fce0144b6ea5",
        "emoji": "0x1F575",
        "slogan": "Bang BANG",
        "fullName": "Houston Spies",
        "location": "Houston",
        "nickname": "Spies",
        "mainColor": "#67556b",
        "secondaryColor": "#d1bece",
        "shorthand": "HOU",
    },
    "a37f9158-7f82-46bc-908c-c9e2dda7c33b": {
        "id": "a37f9158-7f82-46bc-908c-c9e2dda7c33b",
        "emoji": "0x1F450",
        "slogan": "We’ve Got Winning to Do. Just for You.",
        "fullName": "Breckenridge Jazz Hands",
        "location": "Breckenridge",
        "nickname": "Jazz Hands",
        "mainColor": "#6388ad",
        "secondaryColor": "#9182C4",
        "shorthand": "BJAZ",
    },
    "adc5b394-8f76-416d-9ce9-813706877b84": {
        "id": "adc5b394-8f76-416d-9ce9-813706877b84",
        "emoji": "0x1F36C",
        "slogan": "Fresh Breath, Here We Come.",
        "fullName": "Kansas City Breath Mints",
        "location": "Kansas City",
        "nickname": "Breath Mints",
        "mainColor": "#178f55",
        "secondaryColor": "#e6ffec",
        "shorthand": "KCBM",
    },
    "b024e975-1c4a-4575-8936-a3754a08806a": {
        "id": "b024e975-1c4a-4575-8936-a3754a08806a",
        "emoji": "0x1F969",
        "slogan": "Well Done.",
        "fullName": "Dallas Steaks",
        "location": "Dallas",
        "nickname": "Steaks",
        "mainColor": "#8c8d8f",
        "secondaryColor": "#ededed",
        "shorthand": "DAL",
    },
    "b63be8c2-576a-4d6e-8daf-814f8bcea96f": {
        "id": "b63be8c2-576a-4d6e-8daf-814f8bcea96f",
        "emoji": "0x1F6A4",
        "slogan": "¡Dalé!",
        "fullName": "Miami Dalé",
        "location": "Miami",
        "nickname": "Dalé",
        "mainColor": "#9141ba",
        "secondaryColor": "#bfe9ff",
        "shorthand": "MIA",
    },
    "b72f3061-f573-40d7-832a-5ad475bd7909": {
        "id": "b72f3061-f573-40d7-832a-5ad475bd7909",
        "emoji": "0x1F48B",
        "slogan": "Let's Go All The Way!",
        "fullName": "San Francisco Lovers",
        "location": "San Francisco",
        "nickname": "Lovers",
        "mainColor": "#780018",
        "secondaryColor": "#212121",
        "shorthand": "SFL",
    },
    "bfd38797-8404-4b38-8b82-341da28b1f83": {
        "id": "bfd38797-8404-4b38-8b82-341da28b1f83",
        "emoji": "0x1F45F",
        "slogan": "Your Kicks are My Kicks.",
        "fullName": "Charleston Shoe Thieves",
        "location": "Charleston",
        "nickname": "Shoe Thieves",
        "mainColor": "#ffce0a",
        "secondaryColor": "#E2DBAC",
        "shorthand": "CHST",
    },
    "ca3f1c8c-c025-4d8e-8eef-5be6accbeb16": {
        "id": "ca3f1c8c-c025-4d8e-8eef-5be6accbeb16",
        "emoji": "0x1F525",
        "slogan": "We're From Chicago.",
        "fullName": "Chicago Firefighters",
        "location": "Chicago",
        "nickname": "Firefighters",
        "mainColor": "#8c2a3e",
        "secondaryColor": "#d6cbb0",
        "shorthand": "CHIF",
    },
    "eb67ae5e-c4bf-46ca-bbbc-425cd34182ff": {
        "id": "eb67ae5e-c4bf-46ca-bbbc-425cd34182ff",
        "emoji": "0x1F5E3",
        "slogan": "SPRAY IT, DON'T SAY IT",
        "fullName": "Canada Moist Talkers",
        "location": "Canada",
        "nickname": "Moist Talkers",
        "mainColor": "#f5feff",
        "secondaryColor": "#757575",
        "shorthand": "CAN",
    },
    "f02aeae2-5e6a-4098-9842-02d2273f25c7": {
        "id": "f02aeae2-5e6a-4098-9842-02d2273f25c7",
        "emoji": "0x1F31E",
        "slogan": "Stare into the Sun...",
        "fullName": "Moab Sunbeams",
        "location": "Moab",
        "nickname": "Sunbeams",
        "mainColor": "#fffbab",
        "secondaryColor": "#fffaab",
        "shorthand": "SUN",
    },
}
S1_PLAYER_NAMES = [
    ("58c9e294-bd49-457c-883f-fb3162fc668e", "Kichiro Guerra"),
    ("43bf6a6d-cc03-4bcf-938d-620e185433e1", "Miguel Javier"),
    ("2b157c5c-9a6a-45a6-858f-bf4cf4cbc0bd", "Ortiz Lopez"),
    ("11de4da3-8208-43ff-a1ff-0b3480a0fbf1", "Don Mitchell"),
    ("126fb128-7c53-45b5-ac2b-5dbf9943d71b", "Sigmund Castillo"),
    ("cbd19e6f-3d08-4734-b23f-585330028665", "Knight Urlacher"),
    ("ee55248b-318a-4bfb-8894-1cc70e4e0720", "Theo King"),
    ("0eea4a48-c84b-4538-97e7-3303671934d2", "Helga Moreno"),
    ("bd24e18b-800d-4f15-878d-e334fb4803c4", "Helga Burton"),
    ("7c5ae357-e079-4427-a90f-97d164c7262e", "Milo Brown"),
    ("3c331c87-1634-46c4-87ce-e4b9c59e2969", "Yosh Carpenter"),
    ("73265ee3-bb35-40d1-b696-1f241a6f5966", "Parker Meng"),
    ("db33a54c-3934-478f-bad4-fc313ac2580e", "Percival Wheeler"),
    ("80a2f015-9d40-426b-a4f6-b9911ba3add8", "Paul Barnes"),
    ("b390b28c-df96-443e-b81f-f0104bd37860", "Karato Rangel"),
    ("0f62c20c-72d0-4c12-a9d7-312ea3d3bcd1", "Abner Wood"),
    ("23e78d92-ee2d-498a-a99c-f40bc4c5fe99", "Annie Williams"),
    ("f1185b20-7b4a-4ccc-a977-dc1afdfd4cb9", "Frazier Tosser"),
    ("9313e41c-3bf7-436d-8bdc-013d3a1ecdeb", "Sandie Nelson"),
    ("3be2c730-b351-43f7-a832-a5294fe8468f", "Amaya Jackson"),
    ("e749dc27-ca3b-456e-889c-d2ec02ac7f5f", "Aureliano Estes"),
    ("d97835fd-2e92-4698-8900-1f5abea0a3b6", "King Roland"),
    ("26f01324-9d1c-470b-8eaa-1b9bfbcd8b65", "Nerd James"),
    ("9f6d06d6-c616-4599-996b-ec4eefcff8b8", "Silvia Winner"),
    ("0e27df51-ad0c-4546-acf5-96b3cb4d7501", "Chorby Spoon"),
    ("27c68d7f-5e40-4afa-8b6f-9df47b79e7dd", "Basilio Preston"),
    ("63df8701-1871-4987-87d7-b55d4f1df2e9", "Mcdowell Sasquatch"),
    ("1f159bab-923a-4811-b6fa-02bfde50925a", "Wyatt Mason"),
    ("bf6a24d1-4e89-4790-a4ba-eeb2870cbf6f", "Rat Polk"),
    ("ea44bd36-65b4-4f3b-ac71-78d87a540b48", "Wanda Pothos"),
    ("e4034192-4dc6-4901-bb30-07fe3cf77b5e", "Baldwin Breadwinner"),
    ("a1ed3396-114a-40bc-9ff0-54d7e1ad1718", "Patel Beyonce"),
    ("5ca7e854-dc00-4955-9235-d7fcd732ddcf", "Taiga Quitter"),
    ("75f9d874-5e69-438d-900d-a3fcb1d429b3", "Moses Simmons"),
    ("773712f6-d76d-4caa-8a9b-56fe1d1a5a68", "Natha Kath"),
    ("0bb35615-63f2-4492-80ec-b6b322dc5450", "Sexton Wheeler"),
    ("0d5300f6-0966-430f-903f-a4c2338abf00", "Lee Davenport"),
    ("f741dc01-2bae-4459-bfc0-f97536193eea", "Alejandro Leaf"),
    ("e16c3f28-eecd-4571-be1a-606bbac36b2b", "Comfort Glover"),
    ("0ecf6190-f869-421a-b339-29195d30d37c", "McBaseball Clembons"),
    ("d81ce662-07b6-4a73-baa4-acbbb41f9dc5", "Yummy Elliott"),
    ("10ea5d50-ec88-40a0-ab53-c6e11cc1e479", "Nicholas Vincent"),
    ("d8758c1b-afbb-43a5-b00b-6004d419e2c5", "Ortiz Nelson"),
    ("f0594932-8ef7-4d70-9894-df4be64875d8", "Fitzgerald Wanderlust"),
    ("dfe3bc1b-fca8-47eb-965f-6cf947c35447", "Linus Haley"),
    ("3db02423-92af-485f-b30f-78256721dcc6", "Son Jensen"),
    ("6192daab-3318-44b5-953f-14d68cdb2722", "Justin Alstott"),
    ("5149c919-48fe-45c6-b7ee-bb8e5828a095", "Adkins Davis"),
    ("63a31035-2e6d-4922-a3f9-fa6e659b54ad", "Moody Rodriguez"),
    ("937c1a37-4b05-4dc5-a86d-d75226f8490a", "Pippin Carpenter"),
    ("17397256-c28c-4cad-85f2-a21768c66e67", "Cory Ross"),
    ("c83f0fe0-44d1-4342-81e8-944bb38f8e23", "Langley Wheeler"),
    ("c83a13f6-ee66-4b1c-9747-faa67395a6f1", "Zi Delacruz"),
    ("81a0889a-4606-4f49-b419-866b57331383", "Summers Pony"),
    ("14d88771-7a96-48aa-ba59-07bae1733e96", "Sebastian Telephone"),
    ("82d1b7b4-ce00-4536-8631-a025f05150ce", "Sam Scandal"),
    ("05bd08d5-7d9f-450b-abfa-1788b8ee8b91", "Stevenson Monstera"),
    ("083d09d4-7ed3-4100-b021-8fbe30dd43e8", "Jessica Telephone"),
    ("76c4853b-7fbc-4688-8cda-c5b8de1724e4", "Lars Mendoza"),
    ("b7ca8f3f-2fdc-477b-84f4-157f2802e9b5", "Leach Herman"),
    ("6b8d128f-ed51-496d-a965-6614476f8256", "Orville Manco"),
    ("740d5fef-d59f-4dac-9a75-739ec07f91cf", "Conner Haley"),
    ("042962c8-4d8b-44a6-b854-6ccef3d82716", "Ronan Jaylee"),
    ("94baa9ac-ff96-4f56-a987-10358e917d91", "Gabriel Griffith"),
    ("fdfd36c7-e0c1-4fce-98f7-921c3d17eafe", "Reese Harrington"),
    ("dd7e710f-da4e-475b-b870-2c29fe9d8c00", "Itsuki Weeks"),
    ("3f08f8cd-6418-447a-84d3-22a981c68f16", "Pollard Beard"),
    ("721fb947-7548-49ea-8cbe-7721b0ed49e0", "Tamara Lopez"),
    ("c6bd21a8-7880-4c00-8abe-33560fe84ac5", "Wendy Cerna"),
    ("4fe28bc1-f690-4ad6-ad09-1b2e984bf30b", "Cell Longarms"),
    ("ebf2da50-7711-46ba-9e49-341ce3487e00", "Baldwin Jones"),
    ("d796d287-77ef-49f0-89ef-87bcdeb280ee", "Izuki Clark"),
    ("de52d5c0-cba4-4ace-8308-e2ed3f8799d0", "José Mitchell"),
    ("13cfbadf-b048-4c4f-903d-f9b52616b15c", "Bennett Bowen"),
    ("732899a3-2082-4d9f-b1c2-74c8b75e15fb", "Minato Ito"),
    ("88cd6efa-dbf2-4309-aabe-ec1d6f21f98a", "Hewitt Best"),
    ("b39b5aae-8571-4c90-887a-6a00f2a2f6fd", "Dickerson Morse"),
    ("33fbfe23-37bd-4e37-a481-a87eadb8192d", "Whit Steakknife"),
    ("64f4cd75-0c1e-42cf-9ff0-e41c4756f22a", "Grey Alvarado"),
    ("4b6f0a4e-de18-44ad-b497-03b1f470c43c", "Rodriguez Internet"),
    ("cd417f8a-ce01-4ab2-921d-42e2e445bbe2", "Eizabeth Guerra"),
    ("c73d59dd-32a0-49ce-8ab4-b2dbb7dc94ec", "Eduardo Ingram"),
    ("493a83de-6bcf-41a1-97dd-cc5e150548a3", "Boyfriend Monreal"),
    ("53e701c7-e3c8-4e18-ba05-9b41b4b64cda", "Marquez Clark"),
    ("a199a681-decf-4433-b6ab-5454450bbe5e", "Leach Ingram"),
    ("138fccc3-e66f-4b07-8327-d4b6f372f654", "Oscar Vaughan"),
    ("338694b7-6256-4724-86b6-3884299a5d9e", "PolkaDot Patterson"),
    ("3af96a6b-866c-4b03-bc14-090acf6ecee5", "Axel Trololol"),
    ("7663c3ca-40a1-4f13-a430-14637dce797a", "PolkaDot Zavala"),
    ("6e373fca-b8ab-4848-9dcc-50e92cd732b7", "Conrad Bates"),
    ("9fd1f392-d492-4c48-8d46-27fb4283b2db", "Lucas Petty"),
    ("aae38811-122c-43dd-b59c-d0e203154dbe", "Sandie Carver"),
    ("113f47b2-3111-4abb-b25e-18f7889e2d44", "Adkins Swagger"),
    ("fa5b54d2-b488-47cd-a529-592831e4813d", "Kina Larsen"),
    ("a8e757c6-e299-4a2e-a370-4f7c3da98bd1", "Hendricks Lenny"),
    ("6598e40a-d76d-413f-ad06-ac4872875bde", "Daniel Mendoza"),
    ("90c8be89-896d-404c-945e-c135d063a74e", "James Boy"),
    ("a8a5cf36-d1a9-47d1-8d22-4a665933a7cc", "Helga Washington"),
    ("35d5b43f-8322-4666-aab1-d466b4a5a388", "Jordan Boone"),
    ("849e13dc-6eb1-40a8-b55c-d4b4cd160aab", "Justice Valenzuela"),
    ("31f83a89-44e3-47b7-8c9e-0dfdcd8bd30f", "Tyreek Olive"),
    ("bfd9ff52-9bf6-4aaf-a859-d308d8f29616", "Declan Suzanne"),
    ("69196296-f652-42ff-b2ca-0d9b50bd9b7b", "Joshua Butt"),
    ("68f98a04-204f-4675-92a7-8823f2277075", "Isaac Johnson"),
    ("d23a1f7e-0071-444e-8361-6ae01f13036f", "Edric Tosser"),
    ("4bf352d2-6a57-420a-9d45-b23b2b947375", "Rivers Rosa"),
    ("ad8d15f4-e041-4a12-a10e-901e6285fdc5", "Baby Urlacher"),
    ("20e13b56-599b-4a22-b752-8059effc81dc", "Lou Roseheart"),
    ("e4e4c17d-8128-4704-9e04-f244d4573c4d", "Wesley Poole"),
    ("1513aab6-142c-48c6-b43e-fbda65fd64e8", "Caleb Alvarado"),
    ("43d5da5f-c6a1-42f1-ab7f-50ea956b6cd5", "Justice Spoon"),
    ("d46abb00-c546-4952-9218-4f16084e3238", "Atlas Guerra"),
    ("c182f33c-aea5-48a2-97ed-dc74fa29b3c0", "Swamuel Mora"),
    ("16aff709-e855-47c8-8818-b9ba66e90fe8", "Mullen Peterson"),
    ("f071889c-f10f-4d2f-a1dd-c5dda34b3e2b", "Zion Facepunch"),
    ("ce0a156b-ba7b-4313-8fea-75807b4bc77f", "Conrad Twelve"),
    ("3c051b92-4a86-4157-988a-e334bf6dc691", "Tyler Leatherman"),
    ("c8de53a4-d90f-4192-955b-cec1732d920e", "Tyreek Cain"),
    ("54e5f222-fb16-47e0-adf9-21813218dafa", "Grit Watson"),
    ("88ca603e-b2e5-4916-bef5-d6bba03235f5", "Clare Mccall"),
    ("520e6066-b14b-45cf-985c-0a6ee2dc3f7a", "Zi Sliders"),
    ("5f3b5dc2-351a-4dee-a9d6-fa5f44f2a365", "Alston England"),
    ("a7edbf19-caf6-45dd-83d5-46496c99aa88", "Rush Valenzuela"),
    ("7e4f012e-828c-43bb-8b8a-6c33bdfd7e3f", "Patel Olive"),
    ("64aaa3cb-7daf-47e3-89a8-e565a3715b5d", "Travis Nakamura"),
    ("18798b8f-6391-4cb2-8a5f-6fb540d646d5", "Morrow Doyle"),
    ("198fd9c8-cb75-482d-873e-e6b91d42a446", "Ren Hunter"),
    ("4ca52626-58cd-449d-88bb-f6d631588640", "Velasquez Alstott"),
    ("248ccf3d-d5f6-4b69-83d9-40230ca909cd", "Antonio Wallace"),
    ("d47dd08e-833c-4302-a965-a391d345455c", "Stu Trololol"),
    ("b4505c48-fc75-4f9e-8419-42b28dcc5273", "Sebastian Townsend"),
    ("bd4c6837-eeaa-4675-ae48-061efa0fd11a", "Workman Gloom"),
    ("b8ab86c6-9054-4832-9b96-508dbd4eb624", "Esme Ramsey"),
    ("7b0f91aa-4d66-4362-993d-6ff60f7ce0ef", "Blankenship Fischer"),
    ("2ae8cbfc-2155-4647-9996-3f2591091baf", "Forrest Bookbaby"),
    ("f9c0d3cb-d8be-4f53-94c9-fc53bcbce520", "Matteo Prestige"),
    ("36786f44-9066-4028-98d9-4fa84465ab9e", "Beasley Gloom"),
    ("03f920cc-411f-44ef-ae66-98a44e883291", "Cornelius Games"),
    ("5e4dfa16-f1b9-400f-b8ef-a1613c2b026a", "Snyder Briggs"),
    ("5b5bcc6c-d011-490f-b084-6fdc2c52f958", "Simba Davis"),
    ("99e7de75-d2b8-4330-b897-a7334708aff9", "Winnie Loser"),
    ("50154d56-c58a-461f-976d-b06a4ae467f9", "Carter Oconnor"),
    ("5b3f0a43-45e7-44e7-9496-512c24c040f0", "Rhys Rivera"),
    ("93502db3-85fa-4393-acae-2a5ff3980dde", "Rodriguez Sunshine"),
    ("eaaef47e-82cc-4c90-b77d-75c3fb279e83", "Herring Winfield"),
    ("2d22f026-2873-410b-a45f-3b1dac665ffd", "Donia Johnson"),
    ("d002946f-e7ed-4ce4-a405-63bdaf5eabb5", "Jorge Owens"),
    ("d6e9a211-7b33-45d9-8f09-6d1a1a7a3c78", "William Boone"),
    ("3531c282-cb48-43df-b549-c5276296aaa7", "Oliver Hess"),
    ("b056a825-b629-4856-856b-53a15ad34acb", "Bennett Takahashi"),
    ("0fe896e1-108c-4ce9-97be-3470dde73c21", "Bryanayah Chang"),
    ("718dea1a-d9a8-4c2b-933a-f0667b5250e6", "Margarito Nava"),
    ("b86237bb-ade6-4b1d-9199-a3cc354118d9", "Hurley Pacheco"),
    ("defbc540-a36d-460b-afd8-07da2375ee63", "Castillo Turner"),
    ("51c5473a-7545-4a9a-920d-d9b718d0e8d1", "Jacob Haynes"),
    ("7a75d626-d4fd-474f-a862-473138d8c376", "Beck Whitney"),
    ("3064c7d6-91cc-4c2a-a433-1ce1aabc1ad4", "Jorge Ito"),
    ("ab9eb213-0917-4374-a259-458295045021", "Matheo Carpenter"),
    ("2b1cb8a2-9eba-4fce-85cf-5d997ec45714", "Isaac Rubberman"),
    ("ff5a37d9-a6dd-49aa-b6fb-b935fd670820", "Dunn Keyes"),
    ("3e008f60-6842-42e7-b125-b88c7e5c1a95", "Zeboriah Wilson"),
    ("dfd5ccbb-90ed-4bfe-83e0-dae9cc763f10", "Owen Picklestein"),
    ("24f6829e-7bb4-4e1e-8b59-a07514657e72", "King Weatherman"),
    ("a647388d-fc59-4c1b-90d3-8c1826e07775", "Chambers Simmons"),
    ("51985516-5033-4ab8-a185-7bda07829bdb", "Stephanie Schmitt"),
    ("98f26a25-905f-4850-8960-b741b0c583a4", "Stu Mcdaniel"),
    ("4b73367f-b2bb-4df6-b2eb-2a0dd373eead", "Tristin Crankit"),
    ("a938f586-f5c1-4a35-9e7f-8eaab6de67a6", "Jasper Destiny"),
    ("c771abab-f468-46e9-bac5-43db4c5b410f", "Wade Howe"),
    ("a98917bc-e9df-4b0e-bbde-caa6168aa3d7", "Jenkins Ingram"),
    ("2cadc28c-88a5-4e25-a6eb-cdab60dd446d", "Elijah Bookbaby"),
    ("e3e1d190-2b94-40c0-8e88-baa3fd198d0f", "Chambers Kennedy"),
    ("d9a072f5-1cbb-45ce-87fb-b138e4d8f769", "Francisco Object"),
    ("de67b585-9bf4-4e49-b410-101483ca2fbc", "Shaquille Sunshine"),
    ("81b25b16-3370-4eb0-9d1b-6d630194c680", "Zeboriah Whiskey"),
    ("2f3d7bc7-6ffb-40c3-a94f-5e626be413c9", "Elijah Valenzuela"),
    ("4941976e-31fc-49b5-801a-18abe072178b", "Sebastian Sunshine"),
    ("57448b62-f952-40e2-820c-48d8afe0f64d", "Jessi Wise"),
    ("ef32eb48-4866-49d0-ae58-9c4982e01142", "Fitzgerald Massey"),
    ("8a6fc67d-a7fe-443b-a084-744294cec647", "Terrell Bradley"),
    ("3a96d76a-c508-45a0-94a0-8f64cd6beeb4", "Thomas England"),
    ("1e8b09bd-fbdd-444e-bd7e-10326bd57156", "Fletcher Yamamoto"),
    ("7e9a514a-7850-4ed0-93ab-f3a6e2f41c03", "Nolanestophia Patterson"),
    ("9ac2e7c5-5a34-4738-98d8-9f917bc6d119", "Christian Combs"),
    ("7b55d484-6ea9-4670-8145-986cb9e32412", "Stevenson Heat"),
    ("bd549bfe-b395-4dc0-8546-5c04c08e24a5", "Sam Solis"),
    ("167751d5-210c-4a6e-9568-e92d61bab185", "Jacob Winner"),
    ("7158d158-e7bf-4e9b-9259-62e5b25e3de8", "Karato Bean"),
    ("89ec77d8-c186-4027-bd45-f407b4800c2c", "James Mora"),
    ("a2483925-697f-468f-931c-bcd0071394e5", "Timmy Manco"),
    ("527c1f6e-a7e4-4447-a824-703b662bae4e", "Melton Campbell"),
    ("62823073-84b8-46c2-8451-28fd10dff250", "Mckinney Vaughan"),
    ("805ba480-df4d-4f56-a4cf-0b99959111b5", "Leticia Lozano"),
    ("cd6b102e-1881-4079-9a37-455038bbf10e", "Caleb Morin"),
    ("3954bdfa-931f-4787-b9ac-f44b72fe09d7", "Nicholas Nolan"),
    ("ccc99f2f-2feb-4f32-a9b9-c289f619d84c", "Itsuki Winner"),
    ("fbb5291c-2438-400e-ab32-30ce1259c600", "Cory Novak"),
    ("03d06163-6f06-4817-abe5-0d14c3154236", "Garcia Tabby"),
    ("960f041a-f795-4001-bd88-5ddcf58ee520", "Mayra Buckley"),
    ("0bd5a3ec-e14c-45bf-8283-7bc191ae53e4", "Stephanie Donaldson"),
    ("17392be2-7344-48a0-b4db-8a040a7fb532", "Washer Barajas"),
    ("4e6ad1a1-7c71-49de-8bd5-c286712faf9e", "Sutton Picklestein"),
    ("44c92d97-bb39-469d-a13b-f2dd9ae644d1", "Francisco Preston"),
    ("ac69dba3-6225-4afd-ab4b-23fc78f730fb", "Bevan Wise"),
    ("a5adc84c-80b8-49e4-9962-8b4ade99a922", "Richardson Turquoise"),
    ("0c83e3b6-360e-4b7d-85e3-d906633c9ca0", "Penelope Mathews"),
    ("c86b5add-6c9a-40e0-aa43-e4fd7dd4f2c7", "Sosa Elftower"),
    ("aa6c2662-75f8-4506-aa06-9a0993313216", "Eizabeth Elliott"),
    ("63512571-2eca-4bc4-8ad9-a5308a22ae22", "Oscar Dollie"),
    ("9397ed91-608e-4b13-98ea-e94c795f651e", "Yeong-Ho Garcia"),
    ("8adb084b-19fe-4295-bcd2-f92afdb62bd7", "Logan Rodriguez"),
    ("b6aa8ce8-2587-4627-83c1-2a48d44afaee", "Inky Rutledge"),
    ("09f2787a-3352-41a6-8810-d80e97b253b5", "Curry Aliciakeyes"),
    ("bca38809-81de-42ff-94e3-1c0ebfb1e797", "Famous Oconnor"),
    ("9a031b9a-16f8-4165-a468-5d0e28a81151", "Tiana Wheeler"),
    ("450e6483-d116-41d8-933b-1b541d5f0026", "England Voorhees"),
    ("1af239ae-7e12-42be-9120-feff90453c85", "Melton Telephone"),
    ("94f30f21-f889-4a2e-9b94-818475bb1ca0", "Kirkland Sobremesa"),
    ("1ded0384-d290-4ea1-a72b-4f9d220cbe37", "Juan Murphy"),
    ("82733eb4-103d-4be1-843e-6eb6df35ecd7", "Adkins Tosser"),
    ("db53211c-f841-4f33-accf-0c3e167889a0", "Travis Bendie"),
    ("b77dffaa-e0f5-408f-b9f2-1894ed26e744", "Tucker Lenny"),
    ("945974c5-17d9-43e7-92f6-ba49064bbc59", "Bates Silk"),
    ("c6146c45-3d9b-4749-9f03-d4faae61e2c3", "Atlas Diaz"),
    ("ac57cf28-556f-47af-9154-6bcea2ace9fc", "Rey Wooten"),
    ("7310c32f-8f32-40f2-b086-54555a2c0e86", "Dominic Marijuana"),
    ("a311c089-0df4-46bd-9f5d-8c45c7eb5ae2", "Mclaughlin Scorpler"),
    ("5dbf11c0-994a-4482-bd1e-99379148ee45", "Conrad Vaughan"),
    ("4b3e8e9b-6de1-4840-8751-b1fb45dc5605", "Thomas Dracaena"),
    ("4ffd2e50-bb5b-45d0-b7c4-e24d41b2ff5d", "Schneider Bendie"),
    ("f967d064-0eaf-4445-b225-daed700e044b", "Wesley Dudley"),
    ("b1b141fc-e867-40d1-842a-cea30a97ca4f", "Richardson Games"),
    ("413b3ddb-d933-4567-a60e-6d157480239d", "Winnie Mccall"),
    ("a1628d97-16ca-4a75-b8df-569bae02bef9", "Chorby Soul"),
    ("ae4acebd-edb5-4d20-bf69-f2d5151312ff", "Theodore Cervantes"),
    ("81d7d022-19d6-427d-aafc-031fcb79b29e", "Patty Fox"),
    ("378c07b0-5645-44b5-869f-497d144c7b35", "Fynn Doyle"),
    ("9965eed5-086c-4977-9470-fe410f92d353", "Bates Bentley"),
    ("40db1b0b-6d04-4851-adab-dd6320ad2ed9", "Scrap Murphy"),
    ("ab9b2592-a64a-4913-bf6c-3ae5bd5d26a5", "Beau Huerta"),
    ("29bf512a-cd8c-4ceb-b25a-d96300c184bb", "Garcia Soto"),
    ("94d772c7-0254-4f08-814c-f6fc58fcfb9b", "Fletcher Peck"),
    ("1e229fe5-a191-48ef-a7dd-6f6e13d6d73f", "Erickson Fischer"),
    ("9e724d9a-92a0-436e-bde1-da0b2af85d8f", "Hatfield Suzuki"),
    ("5c60f834-a133-4dc6-9c07-392fb37b3e6a", "Ramirez Winters"),
    ("b7cdb93b-6f9d-468a-ae00-54cbc324ee84", "Ruslan Duran"),
    ("c4951cae-0b47-468b-a3ac-390cc8e9fd05", "Timmy Vine"),
    ("1e7b02b7-6981-427a-b249-8e9bd35f3882", "Nora Reddick"),
    ("6a869b40-be99-4520-89e5-d382b07e4a3c", "Jake Swinger"),
    ("8d81b190-d3b8-4cd9-bcec-0e59fdd7f2bc", "Albert Stink"),
    ("1a93a2d2-b5b6-479b-a595-703e4a2f3885", "Pedro Davids"),
    ("c675fcdf-6117-49a6-ac32-99a89a3a88aa", "Valentine Games"),
    ("7dcf6902-632f-48c5-936a-7cf88802b93a", "Parker Parra"),
    ("84a2b5f6-4955-4007-9299-3d35ae7135d3", "Kennedy Loser"),
    ("f8c20693-f439-4a29-a421-05ed92749f10", "Combs Duende"),
    ("4ecee7be-93e4-4f04-b114-6b333e0e6408", "Sutton Dreamy"),
    ("d35ccee1-9559-49a1-aaa4-7809f7b5c46e", "Forrest Best"),
    ("d6c69d2d-9344-4b19-85a4-6cfcbaead5d2", "Joshua Watson"),
    ("a071a713-a6a1-4b4c-bb3f-45d9fba7a08c", "Nora Perez"),
    ("97dfc1f6-ac94-4cdc-b0d5-1cb9f8984aa5", "Brock Forbes"),
    ("f2a27a7e-bf04-4d31-86f5-16bfa3addbe7", "Winnie Hess"),
    ("1ffb1153-909d-44c7-9df1-6ed3a9a45bbd", "Montgomery Bullock"),
    ("d0d7b8fe-bad8-481f-978e-cb659304ed49", "Adalberto Tosser"),
    ("f70dd57b-55c4-4a62-a5ea-7cc4bf9d8ac1", "Tillman Henderson"),
    ("dd8a43a4-a024-44e9-a522-785d998b29c3", "Miguel Peterson"),
    ("d2f827a5-0133-4d96-b403-85a5e50d49e0", "Robbins Schmitt"),
    ("34e1b683-ecd5-477f-b9e3-dd4bca76db45", "Alexandria Hess"),
    ("e1e33aab-df8c-4f53-b30a-ca1cea9f046e", "Joyner Rugrat"),
    ("ce3fb736-d20e-4e2a-88cb-e136783d3a47", "Javier Howe"),
    ("093af82c-84aa-4bd6-ad1a-401fae1fce44", "Elijah Glover"),
    ("7e160e9f-2c79-4e08-8b76-b816de388a98", "Thomas Marsh"),
    ("dd6ba7f1-a97a-4374-a3a7-b3596e286bb3", "Matheo Tanaka"),
    ("7afedcd8-870d-4655-9659-3bdfb2e17730", "Pierre Haley"),
    ("4e63cb5d-4fce-441b-b9e4-dc6a467cf2fd", "Axel Campbell"),
    ("5915b7bb-e532-4036-9009-79f1e80c0e28", "Rosa Holloway"),
    ("1ba715f2-caa3-44c0-9118-b045ea702a34", "Juan Rangel"),
    ("26cfccf2-850e-43eb-b085-ff73ad0749b8", "Beasley Day"),
    ("13a05157-6172-4431-947b-a058217b4aa5", "Spears Taylor"),
    ("80dff591-2393-448a-8d88-122bd424fa4c", "Elvis Figueroa"),
    ("6fc3689f-bb7d-4382-98a2-cf6ddc76909d", "Cedric Gonzalez"),
    ("15ae64cd-f698-4b00-9d61-c9fffd037ae2", "Mickey Woods"),
    ("c17a4397-4dcc-440e-8c53-d897e971cae9", "August Mina"),
    ("06ced607-7f96-41e7-a8cd-b501d11d1a7e", "Morrow Wilson"),
    ("66cebbbf-9933-4329-924a-72bd3718f321", "Kennedy Cena"),
    ("1732e623-ffc2-40f0-87ba-fdcf97131f1f", "Betsy Trombone"),
    ("9786b2c9-1205-4718-b0f7-fc000ce91106", "Kevin Dudley"),
    ("afc90398-b891-4cdf-9dea-af8a3a79d793", "Yazmin Mason"),
    ("60026a9d-fc9a-4f5a-94fd-2225398fa3da", "Bright Zimmerman"),
    ("814bae61-071a-449b-981e-e7afc839d6d6", "Ruslan Greatness"),
    ("0672a4be-7e00-402c-b8d6-0b813f58ba96", "Castillo Logan"),
    ("62111c49-1521-4ca7-8678-cd45dacf0858", "Bambi Perez"),
    ("7f379b72-f4f0-4d8f-b88b-63211cf50ba6", "Jesús Rodriguez"),
    ("906a5728-5454-44a0-adfe-fd8be15b8d9b", "Jefferson Delacruz"),
    ("90cc0211-cd04-4cac-bdac-646c792773fc", "Case Lancaster"),
    ("a7b0bef3-ee3c-42d4-9e6d-683cd9f5ed84", "Haruta Byrd"),
    ("b85161da-7f4c-42a8-b7f6-19789cf6861d", "Javier Lotus"),
    ("d2a1e734-60d9-4989-b7d9-6eacda70486b", "Tiana Takahashi"),
    ("20395b48-279d-44ff-b5bf-7cf2624a2d30", "Adrian Melon"),
    ("d8bc482e-9309-4230-abcb-2c5a6412446d", "August Obrien"),
    ("cd5494b4-05d0-4b2e-8578-357f0923ff4c", "Mcfarland Vargas"),
    ("f2468055-e880-40bf-8ac6-a0763d846eb2", "Alaynabella Hollywood"),
    ("8604e861-d784-43f0-b0f8-0d43ea6f7814", "Randall Marijuana"),
    ("f56657d3-3bdc-4840-a20c-91aca9cc360e", "Malik Romayne"),
    ("472f50c0-ef98-4d05-91d0-d6359eec3946", "Rhys Trombone"),
    ("25376b55-bb6f-48a7-9381-7b8210842fad", "Emmett Internet"),
    ("8e1fd784-99d5-41c1-a6c5-6b947cec6714", "Velasquez Meadows"),
    ("4f69e8c2-b2a1-4e98-996a-ccf35ac844c5", "Igneus Delacruz"),
    ("190a0f31-d686-4ac4-a7f3-cfc87b72c145", "Nerd Pacheco"),
    ("89f74891-2e25-4b5a-bd99-c95ba3f36aa0", "Nagomi Nava"),
    ("5703141c-25d9-46d0-b680-0cf9cfbf4777", "Sandoval Crossing"),
    ("3d3be7b8-1cbf-450d-8503-fce0daf46cbf", "Zack Sanders"),
    ("df4da81a-917b-434f-b309-f00423ee4967", "Eugenia Bickle"),
    ("20fd71e7-4fa0-4132-9f47-06a314ed539a", "Lars Taylor"),
    ("333067fd-c2b4-4045-a9a4-e87a8d0332d0", "Miguel James"),
    ("3dd85c20-a251-4903-8a3b-1b96941c07b7", "Tot Best"),
    ("206bd649-4f5f-4707-ad85-92784be4eb95", "Newton Underbuck"),
    ("f883269f-117e-45ec-bb1e-fa8dbcf40d3e", "Jayden Wright"),
    ("088884af-f38d-4914-9d67-b319287481b4", "Liam Petty"),
    ("6644d767-ab15-4528-a4ce-ae1f8aadb65f", "Paula Reddick"),
    ("14bfad43-2638-41ec-8964-8351f22e9c4f", "Baby Sliders"),
    ("459f7700-521e-40da-9483-4d111119d659", "Comfort Monreal"),
    ("b69aa26f-71f7-4e17-bc36-49c875872cc1", "Francisca Burton"),
    ("4562ac1f-026c-472c-b4e9-ee6ff800d701", "Chris Koch"),
    ("e3c06405-0564-47ce-bbbd-552bee4dd66f", "Scrap Weeks"),
    ("8b0d717f-ae42-4492-b2ed-106912e2b530", "Avila Baker"),
    ("80e474a3-7d2b-431d-8192-2f1e27162607", "Summers Preston"),
    ("cd68d3a6-7fbc-445d-90f1-970c955e32f4", "Miguel Wheeler"),
    ("2b9f9c25-43ec-4f0b-9937-a5aa23be0d9e", "Lawrence Horne"),
    ("b7267aba-6114-4d53-a519-bf6c99f4e3a9", "Sosa Hayes"),
    ("ce0e57a7-89f5-41ea-80f9-6e649dd54089", "Yong Wright"),
    ("4204c2d1-ca48-4af7-b827-e99907f12d61", "Axel Cardenas"),
    ("e4f1f358-ee1f-4466-863e-f329766279d0", "Ronan Combs"),
    ("bd8778e5-02e8-4d1f-9c31-7b63942cc570", "Cell Barajas"),
    ("bd8d58b6-f37f-48e6-9919-8e14ec91f92a", "José Haley"),
    ("316abea7-9890-4fb8-aaea-86b35e24d9be", "Kennedy Rodgers"),
    ("ad1e670a-f346-4bf7-a02f-a91649c41ccb", "Stephanie Winters"),
    ("7007cbd3-7c7b-44fd-9d6b-393e82b1c06e", "Rafael Davids"),
    ("65273615-22d5-4df1-9a73-707b23e828d5", "Burke Gonzales"),
    ("089af518-e27c-4256-adc8-62e3f4b30f43", "Silvia Rugrat"),
    ("aa7ac9cb-e9db-4313-9941-9f3431728dce", "Matteo Cash"),
    ("1750de38-8f5f-426a-9e23-2899a15a2031", "Kline Nightmare"),
    ("e919dfae-91c3-475c-b5d5-8b0c14940c41", "Famous Meng"),
    ("ceac785e-55fd-4a4e-9bc8-17a662a58a38", "Best Cerna"),
    ("ca709205-226d-4d92-8be6-5f7871f48e26", "Rivers Javier"),
    ("6bd4cf6e-fefe-499a-aa7a-890bcc7b53fa", "Igneus Mcdaniel"),
    ("094ad9a1-e2c7-49a0-af18-da0e3eb656ba", "Erickson Sato"),
    ("19af0d67-c73b-4ef2-bc84-e923c1336db5", "Grit Ramos"),
    ("f4ca437c-c31c-4508-afe7-6dae4330d717", "Fran Beans"),
    ("7951836f-581a-49d5-ae2f-049c6bcc575e", "Adkins Gwiffin"),
    ("4542f0b0-3409-4a4a-a9e1-e8e8e5d73fcf", "Brock Watson"),
    ("d89da2d2-674c-4b85-8959-a4bd406f760a", "Fish Summer"),
    ("d74a2473-1f29-40fa-a41e-66fa2281dfca", "Landry Violence"),
    ("c0732e36-3731-4f1a-abdc-daa9563b6506", "Nagomi Mcdaniel"),
    ("80de2b05-e0d4-4d33-9297-9951b2b5c950", "Alyssa Harrell"),
    ("5ff66eae-7111-4e3b-a9b8-a9579165b0a5", "Daniel Duffy"),
    ("70ccff1e-6b53-40e2-8844-0a28621cb33e", "Moody Cookbook"),
    ("32c9bce6-6e52-40fa-9f64-3629b3d026a8", "Ren Morin"),
    ("2e86de11-a2dd-4b28-b5fe-f4d0c38cd20b", "Zion Aliciakeyes"),
    ("7932c7c7-babb-4245-b9f5-cdadb97c99fb", "Randy Castillo"),
    ("9abe02fb-2b5a-432f-b0af-176be6bd62cf", "Nagomi Meng"),
    ("b082ca6e-eb11-4eab-8d6a-30f8be522ec4", "Nicholas Mora"),
    ("2720559e-9173-4042-aaa0-d3852b72ab2e", "Hiroto Wilcox"),
    ("7aeb8e0b-f6fb-4a9e-bba2-335dada5f0a3", "Dunlap Figueroa"),
    ("b3e512df-c411-4100-9544-0ceadddb28cf", "Famous Owens"),
    ("5fc4713c-45e1-4593-a968-7defeb00a0d4", "Percival Bendie"),
    ("77a41c29-8abd-4456-b6e0-a034252700d2", "Elip Dean"),
    ("a73427b3-e96a-4156-a9ab-844edc696fed", "Wesley Vodka"),
    ("04f955fe-9cc9-4482-a4d2-07fe033b59ee", "Zane Vapor"),
    ("6e744b21-c4fa-4fa8-b4ea-e0e97f68ded5", "Daniel Koch"),
    ("37efef78-2df4-4c76-800c-43d4faf07737", "Lenix Ren"),
    ("58fca5fa-e559-4f5e-ac87-dc99dd19e410", "Sullivan Septemberish"),
    ("2727215d-3714-438d-b1ba-2ed15ec481c0", "Dominic Woman"),
    ("7cf83bdc-f95f-49d3-b716-06f2cf60a78d", "Matteo Urlacher"),
    ("695daf02-113d-4e76-b802-0862df16afbd", "Pacheco Weeks"),
    ("db3ff6f0-1045-4223-b3a8-a016ca987af9", "Murphy Thibault"),
    ("5b9727f7-6a20-47d2-93d9-779f0a85c4ee", "Kennedy Alstott"),
    ("d744f534-2352-472b-9e42-cd91fa540f1b", "Tyler Violet"),
    ("d1a7c13f-8e78-4d2e-9cae-ebf3a5fcdb5d", "Elijah Bates"),
    ("70a458ed-25ca-4ff8-97fc-21cbf58f2c2a", "Trevino Merritt"),
    ("1f145436-b25d-49b9-a1e3-2d3c91626211", "Joe Voorhees"),
    ("9be56060-3b01-47aa-a090-d072ef109fbf", "Jesús Koch"),
    ("90768354-957e-4b4c-bb6d-eab6bbda0ba3", "Eugenia Garbage"),
    ("d4a10c2a-0c28-466a-9213-38ba3339b65e", "Richmond Harrison"),
    ("25f3a67c-4ed5-45b6-94b1-ce468d3ead21", "Hobbs Cain"),
    ("542af915-79c5-431c-a271-f7185e37c6ae", "Oliver Notarobot"),
    ("e6502bc7-5b76-4939-9fb8-132057390b30", "Greer Lott"),
    ("a691f2ba-9b69-41f8-892c-1acd42c336e4", "Jenkins Good"),
    ("d8742d68-8fce-4d52-9a49-f4e33bd2a6fc", "Ortiz Morse"),
    ("9ba361a1-16d5-4f30-b590-fc4fc2fb53d2", "Mooney Doctor"),
    ("64f59d5f-8740-4ebf-91bd-d7697b542a9f", "Zeke Wallace"),
    ("8f11ad58-e0b9-465c-9442-f46991274557", "Amos Melon"),
    ("3ebb5361-3895-4a50-801e-e7a0ee61750c", "Augusto Reddick"),
    ("7853aa8c-e86d-4483-927d-c1d14ea3a34d", "Tucker Flores"),
    ("ceb5606d-ea3f-4471-9ca7-3d2e71a50dde", "London Simmons"),
    ("27faa5a7-d3a8-4d2d-8e62-47cfeba74ff0", "Spears Nolan"),
    ("c57222fd-df55-464c-a44e-b15443e61b70", "Natha Spruce"),
    ("c3b1b4e5-4b88-4245-b2b1-ae3ade57349e", "Wall Osborn"),
    ("6524e9e0-828a-46c4-935d-0ee2edeb7e9a", "Carter Turnip"),
    ("51cba429-13e8-487e-9568-847b7b8b9ac5", "Collins Mina"),
    ("24cb35c1-c24c-45ca-ac0b-f99a2e650d89", "Tyreek Peterson"),
    ("503a235f-9fa6-41b5-8514-9475c944273f", "Reese Clark"),
    ("3afb30c1-1b12-466a-968a-5a9a21458c7f", "Dickerson Greatness"),
    ("90c6e6ca-77fc-42b7-94d8-d8afd6d299e5", "Miki Santana"),
    ("fa477c92-39b6-4a52-b065-40af2f29840a", "Howell Franklin"),
    ("285ce77d-e5cd-4daa-9784-801347140d48", "Son Scotch"),
    ("e111a46d-5ada-4311-ac4f-175cca3357da", "Alexandria Rosales"),
    ("ecb8d2f5-4ff5-4890-9693-5654e00055f6", "Yeong-Ho Benitez"),
    ("446a3366-3fe3-41bb-bfdd-d8717f2152a9", "Marco Escobar"),
    ("f38c5d80-093f-46eb-99d6-942aa45cd921", "Andrew Solis"),
    ("32551e28-3a40-47ae-aed1-ff5bc66be879", "Math Velazquez"),
    ("d2d76815-cbdc-4c4b-9c9e-32ebf2297cc7", "Denzel Scott"),
    ("3a8c52d7-4124-4a65-a20d-d51abcbe6540", "Theodore Holloway"),
    ("30218684-7fa1-41a5-a3b3-5d9cd97dd36b", "Jordan Hildebert"),
    ("ceb8f8cd-80b2-47f0-b43e-4d885fa48aa4", "Donia Bailey"),
    ("a8530be5-8923-4f74-9675-bf8a1a8f7878", "Mohammed Picklestein"),
    ("57b4827b-26b0-4384-a431-9f63f715bc5b", "Aureliano Cerna"),
    ("7dca7137-b872-46f5-8e59-8c9c996e9d22", "Emmett Tabby"),
    ("97981e86-4a42-4f85-8783-9f29833c192b", "Daiya Vine"),
    ("b7c4f986-e62a-4a8f-b5f0-8f30ecc35c5d", "Oscar Hollywood"),
    ("b7c1ddda-945c-4b2e-8831-ad9f2ec4a608", "Nolan Violet"),
    ("24ad200d-a45f-4286-bfa5-48909f98a1f7", "Nicholas Summer"),
    ("68462bfa-9006-4637-8830-2e7840d9089a", "Parker Horseman"),
    ("e972984c-2895-451c-b518-f06a0d8bd375", "Becker Solis"),
    ("07ac91e9-0269-4e2c-a62d-a87ef61e3bbe", "Eduardo Perez"),
    ("6bac62ad-7117-4e41-80f9-5a155a434856", "Grit Freeman"),
    ("0eddd056-9d72-4804-bd60-53144b785d5c", "Caleb Novak"),
    ("8ba7e1ff-4c6d-4963-8e0f-7096d14f4b12", "Jenna Maldonado"),
    ("12577256-bc4e-4955-81d6-b422d895fb12", "Jasmine Washington"),
    ("4bda6584-6c21-4185-8895-47d07e8ad0c0", "Aldon Anthony"),
    ("c22e3af5-9001-465f-b450-864d7db2b4a0", "Logan Horseman"),
    ("f0bcf4bb-74b3-412e-a54c-04c12ad28ecb", "Hahn Fox"),
    ("2e6d4fa9-f930-47bd-971a-dd54a3cf7db1", "Raúl Leal"),
    ("64b055d1-b691-4e0c-8583-fc08ba663846", "Theodore Passon"),
    ("bbf9543f-f100-445a-a467-81d7aab12236", "Farrell Seagull"),
    ("af6b3edc-ed52-4edc-b0c9-14e0a5ae0ee3", "Rivers Clembons"),
    ("9820f2c5-f9da-4a07-b610-c2dd7bee2ef6", "Dan Bong"),
    ("8903a74f-f322-41d2-bd75-dbf7563c4abb", "Francisca Sasquatch"),
    ("20be1c34-071d-40c6-8824-dde2af184b4d", "Qais Dogwalker"),
    ("0cc5bd39-e90d-42f9-9dd8-7e703f316436", "Don Elliott"),
    ("b019fb2b-9f4b-4deb-bf78-6bee2f16d98d", "Gloria Bentley"),
    ("c4418663-7aa4-4c9f-ae73-0e81e442e8a2", "Chris Thibault"),
    ("4aa843a4-baa1-4f35-8748-63aa82bd0e03", "Aureliano Dollie"),
    ("97ec5a2f-ac1a-4cde-86b7-897c030a1fa8", "Alston Woods"),
    ("d5192d95-a547-498a-b4ea-6770dde4b9f5", "Summers Slugger"),
    ("b7adbbcc-0679-43f3-a939-07f009a393db", "Jode Crutch"),
    ("7fed72df-87de-407d-8253-2295a2b60d3b", "Stout Schmitt"),
    ("889c9ef9-d521-4436-b41c-9021b81b4dfb", "Liam Snail"),
    ("fcbe1d14-04c4-4331-97ad-46e170610633", "Jode Preston"),
    ("1aec2c01-b766-4018-a271-419e5371bc8f", "Rush Ito"),
    ("0daf04fc-8d0d-4513-8e98-4f610616453b", "Lee Mist"),
    ("1301ee81-406e-43d9-b2bb-55ca6e0f7765", "Malik Destiny"),
    ("f3ddfd87-73a2-4681-96fe-829476c97886", "Theodore Duende"),
    ("8cf78b49-d0ca-4703-88e8-4bcad26c44b1", "Avila Guzman"),
    ("425f3f84-bab0-4cf2-91c1-96e78cf5cd02", "Luis Acevedo"),
    ("495a6bdc-174d-4ad6-8d51-9ee88b1c2e4a", "Shaquille Torres"),
    ("da0bbbe6-d13c-40cc-9594-8c476975d93d", "Lang Richardson"),
    ("8b53ce82-4b1a-48f0-999d-1774b3719202", "Oliver Mueller"),
    ("1068f44b-34a0-42d8-a92e-2be748681a6f", "Allison Abbott"),
    ("03097200-0d48-4236-a3d2-8bdb153aa8f7", "Bennett Browning"),
    ("c6a277c3-d2b5-4363-839b-950896a5ec5e", "Mike Townsend"),
    ("e3c514ae-f813-470e-9c91-d5baf5ffcf16", "Tot Clark"),
    ("6f9de777-e812-4c84-915c-ef283c9f0cde", "Arturo Huerta"),
    ("41949d4d-b151-4f46-8bf7-73119a48fac8", "Ron Monstera"),
    ("04e14d7b-5021-4250-a3cd-932ba8e0a889", "Jaylen Hotdogfingers"),
    ("4ed61b18-c1f6-4d71-aea3-caac01470b5c", "Lenny Marijuana"),
    ("ce58415f-4e62-47e2-a2c9-4d6a85961e1e", "Schneider Blanco"),
    ("efa73de4-af17-4f88-99d6-d0d69ed1d200", "Antonio Mccall"),
    ("f6b38e56-0d98-4e00-a96e-345aaac1e653", "Leticia Snyder"),
    ("a3947fbc-50ec-45a4-bca4-49ffebb77dbe", "Chorby Short"),
    ("f968532a-bf06-478e-89e0-3856b7f4b124", "Daniel Benedicte"),
    ("864b3be8-e836-426e-ae56-20345b41d03d", "Goodwin Morin"),
    ("dd0b48fe-2d49-4344-83ed-9f0770b370a8", "Tillman Wan"),
    ("061b209a-9cda-44e8-88ce-6a4a37251970", "Mcdowell Karim"),
    ("1c73f91e-0562-480d-9543-2aab1d5e5acd", "Sparks Beans"),
    ("b88d313f-e546-407e-8bc6-94040499daa5", "Oliver Loofah"),
    ("0f61d948-4f0c-4550-8410-ae1c7f9f5613", "Tamara Crankit"),
    ("90c2cec7-0ed5-426a-9de8-754f34d59b39", "Tot Fox"),
    ("d8ee256f-e3d0-46cb-8c77-b1f88d8c9df9", "Comfort Septemberish"),
    ("262c49c6-8301-487d-8356-747023fa46a9", "Alexandria Dracaena"),
    ("efafe75e-2f00-4418-914c-9b6675d39264", "Aldon Cashmoney"),
    ("678170e4-0688-436d-a02d-c0467f9af8c0", "Baby Doyle"),
    ("4f328502-d347-4d2c-8fad-6ae59431d781", "Stephens Lightner"),
    ("9c3273a0-2711-4958-b716-bfcf60857013", "Kathy Mathews"),
    ("e6114fd4-a11d-4f6c-b823-65691bb2d288", "Bevan Underbuck"),
    ("b348c037-eefc-4b81-8edd-dfa96188a97e", "Lowe Forbes"),
    ("f3c07eaf-3d6c-4cc3-9e54-cbecc9c08286", "Campos Arias"),
    ("d5b6b11d-3924-4634-bd50-76553f1f162b", "Ogden Mendoza"),
    ("bf122660-df52-4fc4-9e70-ee185423ff93", "Walton Sports"),
    ("f4a5d734-0ade-4410-abb6-c0cd5a7a1c26", "Agan Harrison"),
    ("e376a90b-7ffe-47a2-a934-f36d6806f17d", "Howell Rocha"),
    ("f6342729-a38a-4204-af8d-64b7accb5620", "Marco Winner"),
    ("b9293beb-d199-4b46-add9-c02f9362d802", "Bauer Zimmerman"),
    ("dac2fd55-5686-465f-a1b6-6fbed0b417c5", "Russo Slugger"),
    ("5fbf04bb-f5ec-4589-ab19-1d89cda056bd", "Donia Dollie"),
    ("ecf19925-dc57-4b89-b114-923d5a714dbe", "Margarito Bishop"),
    ("52cfebfb-8008-4b9f-a566-72a30e0b64bf", "Spears Rogers"),
    ("b5c95dba-2624-41b0-aacd-ac3e1e1fe828", "Cote Rodgers"),
    ("16a59f5f-ef0f-4ada-8682-891ad571a0b6", "Boyfriend Berger"),
    ("3de17e21-17db-4a6b-b7ab-0b2f3c154f42", "Brewer Vapor"),
    ("f10ba06e-d509-414b-90cd-4d70d43c75f9", "Hernando Winter"),
]


CHRONICLER_URI = "https://api.sibr.dev/chronicler"

def generate_player_s1(rng: Rng, id: str, name: str):
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
    soul_roll = rng.next()
    player["soul"] = int(soul_roll * 8 + 2)
    return player


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

    def player_attr_change(self, timestamp: str, player_id: str, delta: dict, path_floor=0.01, path_cap=0.99):
        assert all(isinstance(v, float) or isinstance(v, int) for v in delta.values())

        if "patheticism" in delta:
            player = self.players[player_id]
            if player["patheticism"] + delta["patheticism"] < path_floor:
                delta.pop("patheticism")
                self._append({
                    "type": "update_player",
                    "timestamp": timestamp,
                    "player_id": player_id,
                    "delta": {
                        "patheticism": path_floor
                    }
                })
            elif player["patheticism"] + delta["patheticism"] > path_cap:
                delta.pop("patheticism")
                self._append({
                    "type": "update_player",
                    "timestamp": timestamp,
                    "player_id": player_id,
                    "delta": {
                        "patheticism": path_cap
                    }
                })

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
        new_player = generate_player_s1(rng, new_player_id, new_player_name)
        self.create_player(timestamp, new_player)
        self.replace_player(timestamp, team_id, old_player_id, new_player_id)

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
            rd.update_player(S2_ELECTION_TIMESTAMP, player_id, dict(
                cinnamon=cinnamon,
                peanutAllergy=allergy,
                fate=fate,
            ))

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

    S2_ELECTION_POSTFIX_2_TIMESTAMP = "2020-08-02T23:00:00Z"
    # players_resp = get_cached(
    #     f"players_at_{S2_ELECTION_POSTFIX_TIMESTAMP}",
    #     f"{CHRONICLER_URI}/v2/entities?type=player&at={S2_ELECTION_POSTFIX_TIMESTAMP}&count=2000",
    # )
    # chron_players = {t["entityId"]: t["data"] for t in players_resp["items"]}

    # for team_id in ORIGINAL_TEAM_ORDER:
    #     team = rd.teams[team_id]
    #     for player_id in team["lineup"] + team["rotation"] + team["bench"] + team["bullpen"]:
    #         player = rd.players[player_id]
    #         chron_player = chron_players[player_id]

    #         if player["fate"] == 0:
    #             print(f"{player_id}, fate={chron_player['fate']}")
    #         if not player["peanutAllergy"]:
    #             print(f"{player_id}, allergy={chron_player['peanutAllergy']}")

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


def main():
    rd = Redata()

    # Season 1 start setup
    player_name_queue = list(S1_PLAYER_NAMES)
    rng = Rng.parse("0eeb2966d0cf3cfd+1")
    for team_id in ORIGINAL_TEAM_ORDER:
        team_player_ids = []
        for _ in range(25):
            player_id, player_name = player_name_queue.pop(0)
            player = generate_player_s1(rng, player_id, player_name)
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


    pass


if __name__ == "__main__":
    main()
