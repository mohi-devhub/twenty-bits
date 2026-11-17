"""Build explicit, hand-authored animal/tool/food profiles and random tables.

Semantic rows are named profiles: animal age/sex, tool size/grip, and food
cut/drying state. These are declared attributes, never random identity bits.
"""

from pathlib import Path
import json
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
from twenty_bits.worlds import ROOT, World

ANIMALS = """
aardvark|mammal fur nocturnal burrows long_snout insectivore africa
platypus|mammal fur lays_eggs aquatic webbed venomous australia
short_beaked_echidna|mammal lays_eggs spines insectivore long_snout australia
red_kangaroo|mammal fur pouch hops herbivore large australia
koala|mammal fur pouch climbs herbivore australia
tasmanian_devil|mammal fur pouch nocturnal carnivore australia
common_wombat|mammal fur pouch burrows herbivore australia
virginia_opossum|mammal fur pouch nocturnal climbs america
nine_banded_armadillo|mammal armor burrows insectivore america
brown_throated_sloth|mammal fur climbs herbivore slow america
giant_anteater|mammal fur long_snout insectivore large america
silky_anteater|mammal fur long_snout insectivore climbs nocturnal america
pangolin|mammal armor climbs nocturnal insectivore africa
red_fox|mammal fur carnivore nocturnal burrows europe
arctic_fox|mammal fur carnivore burrows white polar
gray_wolf|mammal fur carnivore packs large europe
african_wild_dog|mammal fur carnivore packs spots africa
fennec_fox|mammal fur carnivore nocturnal burrows desert large_ears africa
lion|mammal fur carnivore large adult_male_mane packs africa
tiger|mammal fur carnivore large stripes aquatic asia
leopard|mammal fur carnivore climbs spots africa
snow_leopard|mammal fur carnivore climbs spots mountains asia
cheetah|mammal fur carnivore spots fast africa
jaguar|mammal fur carnivore spots aquatic america
cougar|mammal fur carnivore large climbs america
polar_bear|mammal fur carnivore large aquatic white polar
brown_bear|mammal fur omnivore large hibernates europe
giant_panda|mammal fur herbivore large climbs black_white asia
sun_bear|mammal fur omnivore climbs long_tongue asia
spotted_hyena|mammal fur carnivore packs spots scavenges africa
meerkat|mammal fur insectivore burrows packs africa
honey_badger|mammal fur omnivore burrows africa
striped_skunk|mammal fur omnivore nocturnal stripes spray america
raccoon|mammal fur omnivore nocturnal climbs mask america
red_panda|mammal fur herbivore climbs ringed_tail asia
sea_otter|mammal fur carnivore aquatic floats america
beaver|mammal fur herbivore aquatic webbed flat_tail europe
capybara|mammal fur herbivore aquatic webbed large america
crested_porcupine|mammal spines herbivore nocturnal africa
hedgehog|mammal spines insectivore hibernates europe
naked_mole_rat|mammal burrows herbivore packs hairless africa
squirrel|mammal fur herbivore climbs bushy_tail europe
flying_squirrel|mammal fur herbivore climbs nocturnal glides asia
prairie_dog|mammal fur herbivore burrows packs america
chinchilla|mammal fur herbivore hops mountains america
rabbit|mammal fur herbivore burrows hops large_ears europe
brown_hare|mammal fur herbivore hops fast large_ears europe
pika|mammal fur herbivore burrows mountains asia
ring_tailed_lemur|mammal fur omnivore climbs ringed_tail africa
baboon|mammal fur omnivore packs long_snout africa
gorilla|mammal fur herbivore large climbs knuckle_walks africa
chimpanzee|mammal fur omnivore climbs knuckle_walks africa
orangutan|mammal fur herbivore climbs long_arms asia
gibbon|mammal fur herbivore climbs swings long_arms asia
howler_monkey|mammal fur herbivore climbs loud prehensile_tail america
spider_monkey|mammal fur omnivore climbs prehensile_tail america
bottlenose_dolphin|mammal carnivore aquatic flippers echolocates packs
blue_whale|mammal aquatic flippers baleen huge
humpback_whale|mammal aquatic flippers baleen huge sings
sperm_whale|mammal carnivore aquatic flippers huge echolocates
orca|mammal carnivore aquatic flippers packs black_white
manatee|mammal herbivore aquatic flippers slow
walrus|mammal carnivore aquatic flippers tusks polar
harbor_seal|mammal carnivore aquatic flippers spots
sea_lion|mammal carnivore aquatic flippers external_ears
fruit_bat|mammal fur flies herbivore nocturnal hangs
vampire_bat|mammal fur flies carnivore nocturnal echolocates america
african_elephant|mammal herbivore huge trunk tusks large_ears africa
white_rhinoceros|mammal herbivore huge horn armor africa
hippopotamus|mammal herbivore huge aquatic hairless africa
giraffe|mammal fur herbivore huge long_neck spots africa
zebra|mammal fur herbivore large hooves stripes africa
horse|mammal fur herbivore large hooves adult_male_mane domestic
bactrian_camel|mammal fur herbivore large hooves humps desert asia
llama|mammal fur herbivore large hooves long_neck mountains america
moose|mammal fur herbivore large hooves antlers aquatic europe
reindeer|mammal fur herbivore hooves antlers polar
bison|mammal fur herbivore large hooves horns adult_male_mane america
musk_ox|mammal fur herbivore large hooves horns polar
mountain_goat|mammal fur herbivore hooves horns climbs mountains white america
wild_boar|mammal fur omnivore hooves tusks europe
ostrich|bird feathers lays_eggs flightless huge fast africa
emperor_penguin|bird feathers lays_eggs flightless aquatic black_white polar
flamingo|bird feathers lays_eggs flies aquatic long_neck pink
peacock|bird feathers lays_eggs flies display_tail asia
bald_eagle|bird feathers lays_eggs flies carnivore hooked_beak america
barn_owl|bird feathers lays_eggs flies carnivore nocturnal silent
hummingbird|bird feathers lays_eggs flies herbivore hovers long_beak america
toucan|bird feathers lays_eggs flies herbivore large_beak america
woodpecker|bird feathers lays_eggs flies insectivore climbs drills_wood
pelican|bird feathers lays_eggs flies aquatic carnivore throat_pouch
mallard|bird feathers lays_eggs flies aquatic omnivore webbed
swan|bird feathers lays_eggs flies aquatic herbivore long_neck white
parrot|bird feathers lays_eggs flies herbivore hooked_beak climbs
raven|bird feathers lays_eggs flies omnivore black loud
crocodile|reptile scales lays_eggs aquatic carnivore large armor
komodo_dragon|reptile scales lays_eggs carnivore venomous large asia
green_sea_turtle|reptile scales lays_eggs aquatic herbivore shell flippers
king_cobra|reptile scales lays_eggs carnivore venomous limbless hood asia
chameleon|reptile scales lays_eggs insectivore climbs color_change long_tongue
"""

TOOLS = """
claw_hammer|strikes pulls_nails has_claw metal_head
ball_peen_hammer|strikes shapes_metal round_face metal_head
rubber_mallet|strikes soft_head
sledgehammer|strikes heavy long_handle metal_head
wooden_mallet|strikes soft_head wooden_head
hatchet|cuts chops sharp_edge metal_head
pickaxe|breaks_soil pointed metal_head
hoe|breaks_soil flat_blade long_handle
spade|scoops_soil flat_blade long_handle
round_shovel|scoops_soil pointed long_handle
rake|gathers tines long_handle
pitchfork|lifts tines long_handle
crowbar|pries long_shaft curved
pry_bar|pries flat_blade
nail_puller|pulls_nails jaws
flat_screwdriver|turns_screws flat_tip long_shaft
phillips_screwdriver|turns_screws cross_tip long_shaft
torx_driver|turns_screws star_tip long_shaft
hex_driver|turns_screws hex_tip long_shaft
socket_driver|turns_bolts hollow_tip long_shaft
ratchet_wrench|turns_bolts ratchets
adjustable_wrench|turns_bolts jaws adjustable
open_end_wrench|turns_bolts jaws fixed
box_wrench|turns_bolts ring fixed
pipe_wrench|turns_pipe jaws adjustable toothed
torque_wrench|turns_bolts measures_force
needle_nose_pliers|grips jaws pointed
slip_joint_pliers|grips jaws adjustable
locking_pliers|grips jaws locks
linesman_pliers|grips jaws cuts_wire
bent_nose_pliers|grips jaws curved pointed
round_nose_pliers|grips jaws round_tip
snap_ring_pliers|spreads jaws pointed
wire_cutter|cuts_wire sharp_edge
tin_snips|cuts_sheet sharp_edge scissors
aviation_snips|cuts_sheet sharp_edge scissors compound_leverage
pruning_shears|cuts_branches sharp_edge scissors
loppers|cuts_branches sharp_edge scissors long_handle
hedge_shears|cuts_leaves sharp_edge scissors long_blade
bypass_pruner|cuts_branches sharp_edge scissors curved
hand_saw|saws teeth long_blade
hacksaw|saws teeth metal_frame
coping_saw|saws teeth metal_frame narrow_blade
keyhole_saw|saws teeth pointed
back_saw|saws teeth long_blade reinforced_back
pull_saw|saws teeth flexible_blade
miter_saw|saws teeth angle_guide
utility_knife|cuts sharp_edge retractable
craft_knife|cuts sharp_edge pointed narrow_blade
putty_knife|spreads flat_blade flexible_blade
paint_scraper|scrapes flat_blade sharp_edge
cabinet_scraper|scrapes flat_blade rectangular
wood_chisel|cuts_wood sharp_edge flat_tip
cold_chisel|cuts_metal sharp_edge flat_tip
gouge|cuts_wood sharp_edge curved
center_punch|marks pointed strikes
pin_punch|drives_pins round_tip strikes
nail_set|drives_nails round_tip strikes
bradawl|marks pointed long_shaft
hand_drill|drills rotates geared
brace_drill|drills rotates curved
push_drill|drills rotates spring
countersink|drills bevels rotates
reamer|enlarges_holes rotates teeth
round_file|abrades teeth round_shaft
flat_file|abrades teeth flat_blade
half_round_file|abrades teeth half_round
rasp|abrades coarse_teeth flat_blade
sanding_block|abrades replaceable_sheet rectangular
hand_plane|smooths_wood sharp_edge adjustable
spokeshave|smooths_wood sharp_edge two_handles
drawknife|cuts_wood sharp_edge two_handles
paintbrush|paints bristles
roller|paints rotates soft_head
caulking_gun|dispenses squeezes trigger
soldering_iron|joins_metal heats pointed
hot_glue_gun|joins heats trigger dispenses
staple_gun|fastens trigger spring
rivet_gun|fastens squeezes jaws
pop_rivet_pliers|fastens squeezes jaws long_handle
"""

FOODS = """
apple|fruit sweet grows_tree firm red_skin
pear|fruit sweet grows_tree firm green_skin
banana|fruit sweet grows_plant soft yellow_skin
mango|fruit sweet grows_tree soft orange_flesh
pineapple|fruit sweet grows_plant firm spiny_skin
strawberry|fruit sweet grows_plant soft red_skin seeds_outside
blueberry|fruit sweet grows_bush soft blue_skin
raspberry|fruit sweet grows_bush soft red_skin hollow
blackberry|fruit sweet grows_bush soft black_skin
cherry|fruit sweet grows_tree soft red_skin stone
peach|fruit sweet grows_tree soft fuzzy_skin stone
apricot|fruit sweet grows_tree soft orange_flesh stone
plum|fruit sweet grows_tree soft purple_skin stone
nectarine|fruit sweet grows_tree soft red_skin stone smooth_skin
fig|fruit sweet grows_tree soft many_seeds
kiwi|fruit sweet grows_vine soft fuzzy_skin green_flesh
grape|fruit sweet grows_vine soft purple_skin
green_grape|fruit sweet grows_vine soft green_skin
orange|fruit sweet sour grows_tree citrus orange_flesh
lemon|fruit sour grows_tree citrus yellow_skin
lime|fruit sour grows_tree citrus green_skin
grapefruit|fruit sour bitter grows_tree citrus pink_flesh
coconut|fruit grows_tree firm shell white_flesh
pomegranate|fruit sweet sour grows_tree red_skin many_seeds
watermelon|fruit sweet grows_vine red_flesh large
cantaloupe|fruit sweet grows_vine orange_flesh large
honeydew|fruit sweet grows_vine green_flesh large
papaya|fruit sweet grows_tree orange_flesh many_seeds
guava|fruit sweet grows_tree green_skin pink_flesh
lychee|fruit sweet grows_tree soft red_skin white_flesh
passion_fruit|fruit sour grows_vine purple_skin many_seeds
persimmon|fruit sweet grows_tree orange_flesh soft astringent
avocado|fruit grows_tree green_skin oily stone
tomato|fruit savory grows_plant red_skin soft
cucumber|fruit grows_vine green_skin crisp
zucchini|fruit grows_plant green_skin firm
pumpkin|fruit grows_vine orange_flesh large firm
eggplant|fruit grows_plant purple_skin firm
red_bell_pepper|fruit grows_plant red_skin crisp hollow
green_chili|fruit grows_plant green_skin spicy
carrot|vegetable root orange_flesh crisp
beetroot|vegetable root red_flesh firm
radish|vegetable root white_flesh crisp spicy
turnip|vegetable root white_flesh firm
sweet_potato|vegetable root orange_flesh sweet firm
potato|vegetable tuber starchy white_flesh firm
yam|vegetable tuber starchy white_flesh rough_skin firm
ginger|vegetable rhizome spicy yellow_flesh firm
turmeric|vegetable rhizome bitter orange_flesh firm
onion|vegetable bulb pungent white_flesh layers
garlic|vegetable bulb pungent white_flesh cloves
shallot|vegetable bulb pungent purple_skin layers
leek|vegetable stem pungent green_skin layers
celery|vegetable stem crisp green_skin
asparagus|vegetable stem green_skin pointed
broccoli|vegetable flower green_skin branching
cauliflower|vegetable flower white_flesh branching
artichoke|vegetable flower green_skin layered_leaves
cabbage|vegetable leaves green_skin layered_leaves firm
lettuce|vegetable leaves green_skin layered_leaves soft
spinach|vegetable leaves green_skin soft
kale|vegetable leaves green_skin firm curly
chard|vegetable leaves green_skin red_stem
okra|fruit grows_plant green_skin ridged
pea|legume green_skin round seeds
chickpea|legume beige round seeds
lentil|legume flat seeds
kidney_bean|legume red_skin seeds curved
soybean|legume beige seeds oily
peanut|legume shell seeds oily underground
almond|nut grows_tree seeds oily brown_skin
walnut|nut grows_tree seeds oily shell wrinkled
cashew|nut grows_tree seeds oily curved
pistachio|nut grows_tree seeds oily shell green_flesh
hazelnut|nut grows_tree seeds oily shell round
pecan|nut grows_tree seeds oily shell elongated
chestnut|nut grows_tree seeds starchy shell
macadamia|nut grows_tree seeds oily shell white_flesh
button_mushroom|fungus cap white_flesh
shiitake|fungus cap brown_skin
"""


def profiles(text: str) -> list[tuple[str, set[str]]]:
    return [
        (line.split("|")[0], set(line.split("|")[1].split()))
        for line in text.strip().splitlines()
    ]


def expanded(
    domain: str, text: str, variants: tuple[tuple[str, str, set[str]], ...]
) -> World:
    base = profiles(text)
    seen = {}
    for name, tags in base:
        key = tuple(sorted(tags))
        if key in seen:
            raise ValueError(f"Duplicate {domain} base profiles: {seen[key]}, {name}")
        seen[key] = name
    records = [
        (f"{prefix}_{name}", tags | extra)
        for name, tags in base
        for prefix, _, extra in variants
    ]
    attributes = tuple(sorted(set.union(*(tags for _, tags in records))))
    rows = np.array(
        [[attribute in tags for attribute in attributes] for _, tags in records],
        dtype=np.uint8,
    )
    return World(domain, attributes, tuple(name for name, _ in records), rows)


def main():
    animals = expanded(
        "animals",
        ANIMALS,
        (
            ("adult_female", "", {"adult", "female"}),
            ("adult_male", "", {"adult"}),
            ("juvenile_female", "", {"female"}),
            ("juvenile_male", "", set()),
        ),
    )
    tools = expanded(
        "tools",
        TOOLS,
        (
            ("compact_rubber_grip", "", {"compact", "rubber_grip"}),
            ("full_size_rubber_grip", "", {"rubber_grip"}),
            ("compact_bare_grip", "", {"compact"}),
            ("full_size_bare_grip", "", set()),
        ),
    )
    foods = expanded(
        "foods",
        FOODS,
        (
            ("whole_fresh", "", set()),
            ("chopped_fresh", "", {"chopped"}),
            ("whole_dried", "", {"dried"}),
            ("chopped_dried", "", {"chopped", "dried"}),
        ),
    )
    rng = np.random.default_rng(1731)
    vectors = set()
    while len(vectors) < 512:
        vectors.add(tuple(rng.integers(0, 2, 16).tolist()))
    synthetic = World(
        "synthetic",
        tuple(f"attr_{j}" for j in range(16)),
        tuple(f"row_{j}" for j in range(512)),
        np.array(sorted(vectors), dtype=np.uint8),
    )
    for world in [animals, tools, foods, synthetic]:
        (ROOT / f"data/worlds/{world.domain}.json").write_text(
            json.dumps(world.to_dict(), separators=(",", ":")) + "\n"
        )
        print(world.domain, len(world.names), len(world.attributes))
    shuffled = list(animals.names)
    random.Random(92017).shuffle(shuffled)
    (ROOT / "data/worlds/animal_split.json").write_text(
        json.dumps(
            {
                "seed": 92017,
                "train": sorted(shuffled[:200]),
                "held_out": sorted(shuffled[200:]),
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
