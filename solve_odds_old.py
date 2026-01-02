import requests, json
from data import GameData

sess = requests.Session()

sim_id = "thisidisstaticyo"
with open("./all_s1_players.json") as f:
    s1_players = json.load(f)
    s1_players = {p["id"]: p for p in s1_players}


def tsdelta(timestamp, delta):
    import datetime
    before = datetime.datetime.fromisoformat(timestamp)
    after = before + delta
    x = after.isoformat().replace("+00:00", "Z")
    # print(x)
    return x

s1_teams = {'b72f3061-f573-40d7-832a-5ad475bd7909': {'lineup': ['58c9e294-bd49-457c-883f-fb3162fc668e', '43bf6a6d-cc03-4bcf-938d-620e185433e1', '2b157c5c-9a6a-45a6-858f-bf4cf4cbc0bd', '11de4da3-8208-43ff-a1ff-0b3480a0fbf1', '126fb128-7c53-45b5-ac2b-5dbf9943d71b', 'cbd19e6f-3d08-4734-b23f-585330028665', 'ee55248b-318a-4bfb-8894-1cc70e4e0720', '0eea4a48-c84b-4538-97e7-3303671934d2', 'bd24e18b-800d-4f15-878d-e334fb4803c4'], 'rotation': ['7c5ae357-e079-4427-a90f-97d164c7262e', '3c331c87-1634-46c4-87ce-e4b9c59e2969', '73265ee3-bb35-40d1-b696-1f241a6f5966', 'db33a54c-3934-478f-bad4-fc313ac2580e', '80a2f015-9d40-426b-a4f6-b9911ba3add8']}, '878c1bf6-0d21-4659-bfee-916c8314d69c': {'lineup': ['27c68d7f-5e40-4afa-8b6f-9df47b79e7dd', '63df8701-1871-4987-87d7-b55d4f1df2e9', '1f159bab-923a-4811-b6fa-02bfde50925a', 'bf6a24d1-4e89-4790-a4ba-eeb2870cbf6f', 'ea44bd36-65b4-4f3b-ac71-78d87a540b48', 'e4034192-4dc6-4901-bb30-07fe3cf77b5e', 'a1ed3396-114a-40bc-9ff0-54d7e1ad1718', '5ca7e854-dc00-4955-9235-d7fcd732ddcf', '75f9d874-5e69-438d-900d-a3fcb1d429b3'], 'rotation': ['773712f6-d76d-4caa-8a9b-56fe1d1a5a68', '0bb35615-63f2-4492-80ec-b6b322dc5450', '0d5300f6-0966-430f-903f-a4c2338abf00', 'f741dc01-2bae-4459-bfc0-f97536193eea', 'e16c3f28-eecd-4571-be1a-606bbac36b2b']}, 'b024e975-1c4a-4575-8936-a3754a08806a': {'lineup': ['17397256-c28c-4cad-85f2-a21768c66e67', 'c83f0fe0-44d1-4342-81e8-944bb38f8e23', 'c83a13f6-ee66-4b1c-9747-faa67395a6f1', '81a0889a-4606-4f49-b419-866b57331383', '14d88771-7a96-48aa-ba59-07bae1733e96', '82d1b7b4-ce00-4536-8631-a025f05150ce', '05bd08d5-7d9f-450b-abfa-1788b8ee8b91', '083d09d4-7ed3-4100-b021-8fbe30dd43e8', '76c4853b-7fbc-4688-8cda-c5b8de1724e4'], 'rotation': ['b7ca8f3f-2fdc-477b-84f4-157f2802e9b5', '6b8d128f-ed51-496d-a965-6614476f8256', '740d5fef-d59f-4dac-9a75-739ec07f91cf', '042962c8-4d8b-44a6-b854-6ccef3d82716', '94baa9ac-ff96-4f56-a987-10358e917d91']}, 'adc5b394-8f76-416d-9ce9-813706877b84': {'lineup': ['88cd6efa-dbf2-4309-aabe-ec1d6f21f98a', 'b39b5aae-8571-4c90-887a-6a00f2a2f6fd', '33fbfe23-37bd-4e37-a481-a87eadb8192d', '64f4cd75-0c1e-42cf-9ff0-e41c4756f22a', '4b6f0a4e-de18-44ad-b497-03b1f470c43c', 'cd417f8a-ce01-4ab2-921d-42e2e445bbe2', 'c73d59dd-32a0-49ce-8ab4-b2dbb7dc94ec', '493a83de-6bcf-41a1-97dd-cc5e150548a3', '53e701c7-e3c8-4e18-ba05-9b41b4b64cda'], 'rotation': ['a199a681-decf-4433-b6ab-5454450bbe5e', '138fccc3-e66f-4b07-8327-d4b6f372f654', '338694b7-6256-4724-86b6-3884299a5d9e', '3af96a6b-866c-4b03-bc14-090acf6ecee5', '7663c3ca-40a1-4f13-a430-14637dce797a']}, 'ca3f1c8c-c025-4d8e-8eef-5be6accbeb16': {'lineup': ['31f83a89-44e3-47b7-8c9e-0dfdcd8bd30f', 'bfd9ff52-9bf6-4aaf-a859-d308d8f29616', '69196296-f652-42ff-b2ca-0d9b50bd9b7b', '68f98a04-204f-4675-92a7-8823f2277075', 'd23a1f7e-0071-444e-8361-6ae01f13036f', '4bf352d2-6a57-420a-9d45-b23b2b947375', 'ad8d15f4-e041-4a12-a10e-901e6285fdc5', '20e13b56-599b-4a22-b752-8059effc81dc', 'e4e4c17d-8128-4704-9e04-f244d4573c4d'], 'rotation': ['1513aab6-142c-48c6-b43e-fbda65fd64e8', '43d5da5f-c6a1-42f1-ab7f-50ea956b6cd5', 'd46abb00-c546-4952-9218-4f16084e3238', 'c182f33c-aea5-48a2-97ed-dc74fa29b3c0', '16aff709-e855-47c8-8818-b9ba66e90fe8']}, 'bfd38797-8404-4b38-8b82-341da28b1f83': {'lineup': ['18798b8f-6391-4cb2-8a5f-6fb540d646d5', '198fd9c8-cb75-482d-873e-e6b91d42a446', '4ca52626-58cd-449d-88bb-f6d631588640', '248ccf3d-d5f6-4b69-83d9-40230ca909cd', 'd47dd08e-833c-4302-a965-a391d345455c', 'b4505c48-fc75-4f9e-8419-42b28dcc5273', 'bd4c6837-eeaa-4675-ae48-061efa0fd11a', 'b8ab86c6-9054-4832-9b96-508dbd4eb624', '7b0f91aa-4d66-4362-993d-6ff60f7ce0ef'], 'rotation': ['2ae8cbfc-2155-4647-9996-3f2591091baf', 'f9c0d3cb-d8be-4f53-94c9-fc53bcbce520', '36786f44-9066-4028-98d9-4fa84465ab9e', '03f920cc-411f-44ef-ae66-98a44e883291', '5e4dfa16-f1b9-400f-b8ef-a1613c2b026a']}, '3f8bbb15-61c0-4e3f-8e4a-907a5fb1565e': {'lineup': ['0fe896e1-108c-4ce9-97be-3470dde73c21', '718dea1a-d9a8-4c2b-933a-f0667b5250e6', 'b86237bb-ade6-4b1d-9199-a3cc354118d9', 'defbc540-a36d-460b-afd8-07da2375ee63', '51c5473a-7545-4a9a-920d-d9b718d0e8d1', '7a75d626-d4fd-474f-a862-473138d8c376', '3064c7d6-91cc-4c2a-a433-1ce1aabc1ad4', 'ab9eb213-0917-4374-a259-458295045021', '2b1cb8a2-9eba-4fce-85cf-5d997ec45714'], 'rotation': ['ff5a37d9-a6dd-49aa-b6fb-b935fd670820', '3e008f60-6842-42e7-b125-b88c7e5c1a95', 'dfd5ccbb-90ed-4bfe-83e0-dae9cc763f10', '24f6829e-7bb4-4e1e-8b59-a07514657e72', 'a647388d-fc59-4c1b-90d3-8c1826e07775']}, '979aee4a-6d80-4863-bf1c-ee1a78e06024': {'lineup': ['2f3d7bc7-6ffb-40c3-a94f-5e626be413c9', '4941976e-31fc-49b5-801a-18abe072178b', '57448b62-f952-40e2-820c-48d8afe0f64d', 'ef32eb48-4866-49d0-ae58-9c4982e01142', '8a6fc67d-a7fe-443b-a084-744294cec647', '3a96d76a-c508-45a0-94a0-8f64cd6beeb4', '1e8b09bd-fbdd-444e-bd7e-10326bd57156', '7e9a514a-7850-4ed0-93ab-f3a6e2f41c03', '9ac2e7c5-5a34-4738-98d8-9f917bc6d119'], 'rotation': ['7b55d484-6ea9-4670-8145-986cb9e32412', 'bd549bfe-b395-4dc0-8546-5c04c08e24a5', '167751d5-210c-4a6e-9568-e92d61bab185', '7158d158-e7bf-4e9b-9259-62e5b25e3de8', '89ec77d8-c186-4027-bd45-f407b4800c2c']}, '7966eb04-efcc-499b-8f03-d13916330531': {'lineup': ['17392be2-7344-48a0-b4db-8a040a7fb532', '4e6ad1a1-7c71-49de-8bd5-c286712faf9e', '44c92d97-bb39-469d-a13b-f2dd9ae644d1', 'ac69dba3-6225-4afd-ab4b-23fc78f730fb', 'a5adc84c-80b8-49e4-9962-8b4ade99a922', '0c83e3b6-360e-4b7d-85e3-d906633c9ca0', 'c86b5add-6c9a-40e0-aa43-e4fd7dd4f2c7', 'aa6c2662-75f8-4506-aa06-9a0993313216', '63512571-2eca-4bc4-8ad9-a5308a22ae22'], 'rotation': ['9397ed91-608e-4b13-98ea-e94c795f651e', '8adb084b-19fe-4295-bcd2-f92afdb62bd7', 'b6aa8ce8-2587-4627-83c1-2a48d44afaee', '09f2787a-3352-41a6-8810-d80e97b253b5', 'bca38809-81de-42ff-94e3-1c0ebfb1e797']}, '36569151-a2fb-43c1-9df7-2df512424c82': {'lineup': ['7310c32f-8f32-40f2-b086-54555a2c0e86', 'a311c089-0df4-46bd-9f5d-8c45c7eb5ae2', '5dbf11c0-994a-4482-bd1e-99379148ee45', '4b3e8e9b-6de1-4840-8751-b1fb45dc5605', '4ffd2e50-bb5b-45d0-b7c4-e24d41b2ff5d', 'f967d064-0eaf-4445-b225-daed700e044b', 'b1b141fc-e867-40d1-842a-cea30a97ca4f', '413b3ddb-d933-4567-a60e-6d157480239d', 'a1628d97-16ca-4a75-b8df-569bae02bef9'], 'rotation': ['ae4acebd-edb5-4d20-bf69-f2d5151312ff', '81d7d022-19d6-427d-aafc-031fcb79b29e', '378c07b0-5645-44b5-869f-497d144c7b35', '9965eed5-086c-4977-9470-fe410f92d353', '40db1b0b-6d04-4851-adab-dd6320ad2ed9']}, '8d87c468-699a-47a8-b40d-cfb73a5660ad': {'lineup': ['1a93a2d2-b5b6-479b-a595-703e4a2f3885', 'c675fcdf-6117-49a6-ac32-99a89a3a88aa', '7dcf6902-632f-48c5-936a-7cf88802b93a', '84a2b5f6-4955-4007-9299-3d35ae7135d3', 'f8c20693-f439-4a29-a421-05ed92749f10', '4ecee7be-93e4-4f04-b114-6b333e0e6408', 'd35ccee1-9559-49a1-aaa4-7809f7b5c46e', 'd6c69d2d-9344-4b19-85a4-6cfcbaead5d2', 'a071a713-a6a1-4b4c-bb3f-45d9fba7a08c'], 'rotation': ['97dfc1f6-ac94-4cdc-b0d5-1cb9f8984aa5', 'f2a27a7e-bf04-4d31-86f5-16bfa3addbe7', '1ffb1153-909d-44c7-9df1-6ed3a9a45bbd', 'd0d7b8fe-bad8-481f-978e-cb659304ed49', 'f70dd57b-55c4-4a62-a5ea-7cc4bf9d8ac1']}, '23e4cbc1-e9cd-47fa-a35b-bfa06f726cb7': {'lineup': ['1ba715f2-caa3-44c0-9118-b045ea702a34', '26cfccf2-850e-43eb-b085-ff73ad0749b8', '13a05157-6172-4431-947b-a058217b4aa5', '80dff591-2393-448a-8d88-122bd424fa4c', '6fc3689f-bb7d-4382-98a2-cf6ddc76909d', '15ae64cd-f698-4b00-9d61-c9fffd037ae2', 'c17a4397-4dcc-440e-8c53-d897e971cae9', '06ced607-7f96-41e7-a8cd-b501d11d1a7e', '66cebbbf-9933-4329-924a-72bd3718f321'], 'rotation': ['1732e623-ffc2-40f0-87ba-fdcf97131f1f', '9786b2c9-1205-4718-b0f7-fc000ce91106', 'afc90398-b891-4cdf-9dea-af8a3a79d793', '60026a9d-fc9a-4f5a-94fd-2225398fa3da', '814bae61-071a-449b-981e-e7afc839d6d6']}, 'f02aeae2-5e6a-4098-9842-02d2273f25c7': {'lineup': ['f2468055-e880-40bf-8ac6-a0763d846eb2', '8604e861-d784-43f0-b0f8-0d43ea6f7814', 'f56657d3-3bdc-4840-a20c-91aca9cc360e', '472f50c0-ef98-4d05-91d0-d6359eec3946', '25376b55-bb6f-48a7-9381-7b8210842fad', '8e1fd784-99d5-41c1-a6c5-6b947cec6714', '4f69e8c2-b2a1-4e98-996a-ccf35ac844c5', '190a0f31-d686-4ac4-a7f3-cfc87b72c145', '89f74891-2e25-4b5a-bd99-c95ba3f36aa0'], 'rotation': ['5703141c-25d9-46d0-b680-0cf9cfbf4777', '3d3be7b8-1cbf-450d-8503-fce0daf46cbf', 'df4da81a-917b-434f-b309-f00423ee4967', '20fd71e7-4fa0-4132-9f47-06a314ed539a', '333067fd-c2b4-4045-a9a4-e87a8d0332d0']}, '57ec08cc-0411-4643-b304-0e80dbc15ac7': {'lineup': ['80e474a3-7d2b-431d-8192-2f1e27162607', 'cd68d3a6-7fbc-445d-90f1-970c955e32f4', '2b9f9c25-43ec-4f0b-9937-a5aa23be0d9e', 'b7267aba-6114-4d53-a519-bf6c99f4e3a9', 'ce0e57a7-89f5-41ea-80f9-6e649dd54089', '4204c2d1-ca48-4af7-b827-e99907f12d61', 'e4f1f358-ee1f-4466-863e-f329766279d0', 'bd8778e5-02e8-4d1f-9c31-7b63942cc570', 'bd8d58b6-f37f-48e6-9919-8e14ec91f92a'], 'rotation': ['316abea7-9890-4fb8-aaea-86b35e24d9be', 'ad1e670a-f346-4bf7-a02f-a91649c41ccb', '7007cbd3-7c7b-44fd-9d6b-393e82b1c06e', '65273615-22d5-4df1-9a73-707b23e828d5', '089af518-e27c-4256-adc8-62e3f4b30f43']}, '747b8e4a-7e50-4638-a973-ea7950a3e739': {'lineup': ['d89da2d2-674c-4b85-8959-a4bd406f760a', 'd74a2473-1f29-40fa-a41e-66fa2281dfca', 'c0732e36-3731-4f1a-abdc-daa9563b6506', '80de2b05-e0d4-4d33-9297-9951b2b5c950', '5ff66eae-7111-4e3b-a9b8-a9579165b0a5', '70ccff1e-6b53-40e2-8844-0a28621cb33e', '32c9bce6-6e52-40fa-9f64-3629b3d026a8', '2e86de11-a2dd-4b28-b5fe-f4d0c38cd20b', '7932c7c7-babb-4245-b9f5-cdadb97c99fb'], 'rotation': ['9abe02fb-2b5a-432f-b0af-176be6bd62cf', 'b082ca6e-eb11-4eab-8d6a-30f8be522ec4', '2720559e-9173-4042-aaa0-d3852b72ab2e', '7aeb8e0b-f6fb-4a9e-bba2-335dada5f0a3', 'b3e512df-c411-4100-9544-0ceadddb28cf']}, 'eb67ae5e-c4bf-46ca-bbbc-425cd34182ff': {'lineup': ['5b9727f7-6a20-47d2-93d9-779f0a85c4ee', 'd744f534-2352-472b-9e42-cd91fa540f1b', 'd1a7c13f-8e78-4d2e-9cae-ebf3a5fcdb5d', '70a458ed-25ca-4ff8-97fc-21cbf58f2c2a', '1f145436-b25d-49b9-a1e3-2d3c91626211', '9be56060-3b01-47aa-a090-d072ef109fbf', '90768354-957e-4b4c-bb6d-eab6bbda0ba3', 'd4a10c2a-0c28-466a-9213-38ba3339b65e', '25f3a67c-4ed5-45b6-94b1-ce468d3ead21'], 'rotation': ['542af915-79c5-431c-a271-f7185e37c6ae', 'e6502bc7-5b76-4939-9fb8-132057390b30', 'a691f2ba-9b69-41f8-892c-1acd42c336e4', 'd8742d68-8fce-4d52-9a49-f4e33bd2a6fc', '9ba361a1-16d5-4f30-b590-fc4fc2fb53d2']}, '9debc64f-74b7-4ae1-a4d6-fce0144b6ea5': {'lineup': ['503a235f-9fa6-41b5-8514-9475c944273f', '3afb30c1-1b12-466a-968a-5a9a21458c7f', '90c6e6ca-77fc-42b7-94d8-d8afd6d299e5', 'fa477c92-39b6-4a52-b065-40af2f29840a', '285ce77d-e5cd-4daa-9784-801347140d48', 'e111a46d-5ada-4311-ac4f-175cca3357da', 'ecb8d2f5-4ff5-4890-9693-5654e00055f6', '446a3366-3fe3-41bb-bfdd-d8717f2152a9', 'f38c5d80-093f-46eb-99d6-942aa45cd921'], 'rotation': ['32551e28-3a40-47ae-aed1-ff5bc66be879', 'd2d76815-cbdc-4c4b-9c9e-32ebf2297cc7', '3a8c52d7-4124-4a65-a20d-d51abcbe6540', '30218684-7fa1-41a5-a3b3-5d9cd97dd36b', 'ceb8f8cd-80b2-47f0-b43e-4d885fa48aa4']}, 'b63be8c2-576a-4d6e-8daf-814f8bcea96f': {'lineup': ['0eddd056-9d72-4804-bd60-53144b785d5c', '8ba7e1ff-4c6d-4963-8e0f-7096d14f4b12', '12577256-bc4e-4955-81d6-b422d895fb12', '4bda6584-6c21-4185-8895-47d07e8ad0c0', 'c22e3af5-9001-465f-b450-864d7db2b4a0', 'f0bcf4bb-74b3-412e-a54c-04c12ad28ecb', '2e6d4fa9-f930-47bd-971a-dd54a3cf7db1', '64b055d1-b691-4e0c-8583-fc08ba663846', 'bbf9543f-f100-445a-a467-81d7aab12236'], 'rotation': ['af6b3edc-ed52-4edc-b0c9-14e0a5ae0ee3', '9820f2c5-f9da-4a07-b610-c2dd7bee2ef6', '8903a74f-f322-41d2-bd75-dbf7563c4abb', '20be1c34-071d-40c6-8824-dde2af184b4d', '0cc5bd39-e90d-42f9-9dd8-7e703f316436']}, '105bc3ff-1320-4e37-8ef0-8d595cb95dd0': {'lineup': ['1301ee81-406e-43d9-b2bb-55ca6e0f7765', 'f3ddfd87-73a2-4681-96fe-829476c97886', '8cf78b49-d0ca-4703-88e8-4bcad26c44b1', '425f3f84-bab0-4cf2-91c1-96e78cf5cd02', '495a6bdc-174d-4ad6-8d51-9ee88b1c2e4a', 'da0bbbe6-d13c-40cc-9594-8c476975d93d', '8b53ce82-4b1a-48f0-999d-1774b3719202', '1068f44b-34a0-42d8-a92e-2be748681a6f', '03097200-0d48-4236-a3d2-8bdb153aa8f7'], 'rotation': ['c6a277c3-d2b5-4363-839b-950896a5ec5e', 'e3c514ae-f813-470e-9c91-d5baf5ffcf16', '6f9de777-e812-4c84-915c-ef283c9f0cde', '41949d4d-b151-4f46-8bf7-73119a48fac8', '04e14d7b-5021-4250-a3cd-932ba8e0a889']}, 'a37f9158-7f82-46bc-908c-c9e2dda7c33b': {'lineup': ['0f61d948-4f0c-4550-8410-ae1c7f9f5613', '90c2cec7-0ed5-426a-9de8-754f34d59b39', 'd8ee256f-e3d0-46cb-8c77-b1f88d8c9df9', '262c49c6-8301-487d-8356-747023fa46a9', 'efafe75e-2f00-4418-914c-9b6675d39264', '678170e4-0688-436d-a02d-c0467f9af8c0', '4f328502-d347-4d2c-8fad-6ae59431d781', '9c3273a0-2711-4958-b716-bfcf60857013', 'e6114fd4-a11d-4f6c-b823-65691bb2d288'], 'rotation': ['b348c037-eefc-4b81-8edd-dfa96188a97e', 'f3c07eaf-3d6c-4cc3-9e54-cbecc9c08286', 'd5b6b11d-3924-4634-bd50-76553f1f162b', 'bf122660-df52-4fc4-9e70-ee185423ff93', 'f4a5d734-0ade-4410-abb6-c0cd5a7a1c26']}}

games = sess.get(f"https://api.sibr.dev/chronicler/v1/games?sim={sim_id}").json()['data']
games_by_id = {g['gameId']: g['data'] for g in games}

def calc_standings_at(season, day):
    wins = {}

    season_games = [g for g in games if g['data']['season'] == season]
    for game in sorted(season_games, key=lambda x: x['data']['day']):
        gd = game['data']
        wins[gd['homeTeam']] = wins.get(gd['homeTeam'], 0)
        wins[gd['awayTeam']] = wins.get(gd['awayTeam'], 0)

        if gd['day'] < day-1 and gd['day'] < 99:
            if gd['homeScore'] > gd['awayScore']:
                wins[gd['homeTeam']] = wins.get(gd['homeTeam'], 0) + 1
            else:
                wins[gd['awayTeam']] = wins.get(gd['awayTeam'], 0) + 1

    return wins


from datetime import timedelta
def data_at_odds_gen(season, day):
    if season == 0 and sim_id == "thisidisstaticyo":
        return s1_teams, s1_players, calc_standings_at(season, day)
    if day != 0 and day < 99:
        day -= 1
    start_times = [g['startTime'] for g in games if g['data']['season'] == season and g['data']['day'] == day]
    if not start_times:
        return None
    start_time = min(start_times)
    start_time = tsdelta(start_time, timedelta(minutes=1))
    if start_time < '2020-08-02T00:00:00':
        start_time = '2020-08-02T00:00:00Z'
    # print(start_time)
    team_data = sess.get(f"https://api.sibr.dev/chronicler/v2/entities?type=team&at={start_time}&count=2000").json()['items']
    teams = {t['entityId']: t['data'] for t in team_data}

    player_datas = []
    player_data = sess.get(f"https://api.sibr.dev/chronicler/v2/entities?type=player&at={start_time}&count=2000").json()
    player_datas += player_data["items"]
    while player_data["items"]:
        player_data = sess.get(f"https://api.sibr.dev/chronicler/v2/entities?type=player&at={start_time}&count=2000&page={player_data['nextPage']}").json()
        player_datas += player_data["items"]

    players = {p['entityId']: p['data'] for p in player_datas}

    sim = sess.get(f"https://api.sibr.dev/chronicler/v2/entities?type=sim&at={start_time}&count=2000").json()['items'][0]['data']

    season_items = sess.get(f"https://api.sibr.dev/chronicler/v2/entities?type=season&at={start_time}&id={sim['seasonId']}").json()['items']
    if not season_items:
        return None
    season_obj = season_items[0]['data']
    standings = sess.get(f"https://api.sibr.dev/chronicler/v2/entities?type=standings&at={start_time}&id={season_obj['standings']}").json()['items'][0]['data']
    # print(start_time)
    # stream = sess.get(f"https://api.sibr.dev/chronicler/v2/entities?type=stream&at={start_time}").json()['items'][0]['data']["value"]

    # wins = stream["games"]["standings"]["wins"]
    wins = standings["wins"]
    # print(stream)
    # wins = {tid: standings['gamesPlayed'][tid]-standings['losses'][tid] for tid in wins.keys()}
    return teams, players, wins

for season in [11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]:
    all_rolls = []
    for day in range(0, 150):
        res = data_at_odds_gen(season, day)
        if not res:
            continue
        teams, players, wins = res
        # print(f"data from day {day}")

        # day = 0
        games_on_day = [g['gameId'] for g in games if g['data']['season'] == season and g['data']['day'] == day]
        # wins = fetch_standings_at(data_timestamp, day-1)
        fuzz_rolls = []
        for game_id in games_on_day:
            game = games_by_id[game_id]

            home_team = teams[game['homeTeam']]
            away_team = teams[game['awayTeam']]

            def batting_stars(p):
                if "hittingRating" in p:
                    return p["hittingRating"]
                tragicness = p["tragicness"]
                if (season, day) > (0, 2) and season == 0:
                    tragicness = 0
                # else:
                    # tragicness = 0.1
                return ((1 - tragicness) ** 0.01) * (p['thwackability'] ** 0.35) * (p['moxie'] ** 0.075) * (p['divinity'] ** 0.35) * (p['musclitude'] ** 0.075) * ((1 - p['patheticism']) ** 0.05) * (p['martyrdom'] ** 0.02)

            def pitching_stars(p):
                if "pitchingRating" in p:
                    return p["pitchingRating"]
                return (p["shakespearianism"] ** 0.1) * (p["unthwackability"] ** 0.5) * (p["coldness"] ** 0.025) * (p["overpowerment"] ** 0.15) * (p["ruthlessness"] ** 0.4)


            def batter_star_geom(team):
                prod = 1
                for batter_id in team['lineup']:
                    if batter_id not in players:
                        continue
                    prod *= batting_stars(players[batter_id])
                return prod**(1/len(team['lineup']))

            def batter_star_avg(team):
                sm = 0
                for batter_id in team['lineup']:
                    if batter_id not in players:
                        continue

                    sm += batting_stars(players[batter_id])
                return sm/(len(team['lineup']))

            hp_id = game["homePitcher"]
            ap_id = game["awayPitcher"]
            # pitcher_idx = 1
            # hp_id = teams[game["homeTeam"]]["rotation"][pitcher_idx]
            # ap_id = teams[game["awayTeam"]]["rotation"][pitcher_idx]
            # print(game)

            if hp_id not in players or ap_id not in players:
                continue

            hb = batter_star_geom(home_team)
            ab = batter_star_geom(away_team)
            hp = pitching_stars(players[hp_id])
            ap = pitching_stars(players[ap_id])
            hw = wins[game['homeTeam']]
            aw = wins[game['awayTeam']]


            a = hp/(hp+ab)-0.5
            b = hb/(hb+ap)-0.5

            # hw = 0
            # aw = 0
            if hw > 0 and aw > 0:
                wr = hw/(hw+aw)-0.5
                raw_odds = 0.5 + (a+b+wr)/3
            else:
                raw_odds = 0.5 + (a+b)/2
            fuzzed_odds = game['homeOdds']

            delta = fuzzed_odds-raw_odds

            offset = 0.02
            mul = 0.07
            if raw_odds > 0.5:
                fuzz_roll = (delta+offset)/mul
            else:
                fuzz_roll = -(delta-offset)/mul
            fuzz_rolls.append((game_id, fuzz_roll))
            # print(f"{game_id}, observed {fuzzed_odds}, predicted {raw_odds}, wins {hw}/{aw} estimated roll: {fuzz_roll}")
            # print((game_id, fuzz_roll))
            # print(f"{game_id}, a: {a}, b: {b}, delta: {delta}")
            all_rolls.append(delta)
        # print(max(all_rolls), min(all_rolls), max(all_rolls)-min(all_rolls))

        if any(r[1] < 0 or r[1] > 1 for r in fuzz_rolls):
            print("invalid formulas, skipping")
            continue

        # continue
        STATE_WIDTH = 64
        STATE_MASK = int("1" * STATE_WIDTH, 2)
        import struct, rng_solver
        def to_double(val: int) -> float:
            double_bits = val | 0x3FF0000000000000
            return struct.unpack("d", struct.pack("<Q", double_bits))[0] - 1

        def get_mantissa(val: float) -> int:
            if val == 1.0:
                return STATE_MASK >> 12
            return struct.unpack("<Q", struct.pack("d", val + 1))[0] & 0x000FFFFFFFFFFFFF

        def mask(val, bits):
            raw_bits = get_mantissa(val)
            m = (1<<bits)-1
            lo = raw_bits & ~m
            hi = raw_bits | m
            return to_double(lo), to_double(hi)

        rolls = []
        for game_id, fuzz_roll in fuzz_rolls:
            # print(f"{game_id} ({games_by_id[game_id]['homeTeamNickname']}): {fuzz_roll}")
            rolls.append(mask(fuzz_roll, 8))

        # continue
        import itertools
        perms = list(itertools.permutations(rolls, r=4))
        found = False
        for perm in perms:
            perm2 = []
            for p in perm:
                # perm2.append(None)
                # perm2.append(None)
                perm2.append(p)
            import time
            # bef = time.time()
            sol = rng_solver.solve_in_rng_order(list(perm2[::-1]))
            # exit()
            # aft = time.time()
            # print(aft-bef)
            if sol:
                print(f"season {season+1} day {day+1} {season,day} odds generation:", sol)
                found = True
                # exit()
                break
        if not found:
            print(f"season {season+1} day {day+1} {season,day} not found")