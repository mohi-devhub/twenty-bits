# World construction and hand checks

The tables are finite, authored search worlds. They are not biological, nutritional, or engineering reference datasets. scripts/build_worlds.py contains every semantic type and its true attributes in readable text. Missing attributes are false by definition.

| Domain | Rows | Underlying types | Attributes | Profile dimensions |
| --- | ---: | ---: | ---: | --- |
| Animals | 400 | 100 | 90 | Adult/juvenile and female/male |
| Tools | 320 | 80 | 88 | Compact/full size and rubber/bare grip |
| Foods | 320 | 80 | 71 | Whole/chopped and fresh/dried |
| Synthetic | 512 | 512 random vectors | 16 | None |

The larger semantic vocabularies distinguish the authored types without random identity bits. The approximate 16-attribute starting sketch was too coarse for these tables. Descriptive type flags and two explicit profile dimensions give unique vectors. Animal traits refer to the kind, such as an egg-laying kind or a kind whose adult males have manes; the profile's adult and female flags describe that row. This avoids treating a male bird's kind as unable to lay eggs. Size, diet, and habitat tags are coarse descriptions, not universal statements about every individual.

The fixed animals training pool contains 200 rows representing 94 types. The held-out pool has the other 200 rows and also represents 94 types. Eighty-eight types occur in both pools through different profiles. Held-out animal evaluation is therefore profile generalization within the domain, not a claim about 200 unfamiliar species. Paid N=32 and N=128 subsets use only held-out rows. The offline N=256 animals baseline uses the whole world because the held-out pool has 200 rows. No paid animals N=256 cell is proposed.

Tools and foods are entirely held out from training. A tool profile's size and grip describe a plausible manufactured variant; food profile flags describe preparation state. These are 80 types per world, not 320 independent tool designs or ingredients. The compositional construction is a limitation and can make bisection easier.

Synthetic bits come from a seeded RNG with rejection of duplicate vectors. Each game shuffles columns and supplies new opaque names for attributes and items. There is no fixed name-to-bit meaning. The complete table remains visible, so a legal name-list strategy can transfer too. Transfer by itself does not prove attribute reasoning.

## Manual sanity check

The following representative entries were inspected against the authored profiles. The two profile bits were also checked in each named variant.

| Sample | Inspected true traits | Inspected false traits | Result |
| --- | --- | --- | --- |
| Adult female walrus | Mammal, aquatic, flippers, tusks, adult, female | Feathers, flies, herbivore | Plausible coarse kind profile |
| Juvenile male echidna | Mammal, egg-laying kind, spines, insectivore | Adult, female, feathers | Plausible kind profile |
| Adult male emperor penguin | Bird, feathers, aquatic, flightless, adult | Flies, fur, female | Plausible kind profile |
| Juvenile female green sea turtle | Reptile, aquatic, shell, flippers, female | Mammal, adult, flies | Adult diet tag is a kind-level simplification |
| Adult female giant panda | Mammal, fur, herbivore, climbs, female | Flippers, flies, carnivore | Plausible coarse diet |
| Juvenile male king cobra | Reptile, scales, venomous, limbless, hood | Adult, female, fur | Plausible coarse kind profile |
| Compact rubber-grip claw hammer | Strikes, pulls nails, claw, metal head, compact, rubber grip | Turns screws, drills | Plausible tool variant |
| Full-size bare-grip Phillips screwdriver | Turns screws, cross tip, long shaft | Compact, rubber grip, saws | Plausible tool variant |
| Compact bare-grip coping saw | Saws, teeth, metal frame, narrow blade, compact | Rubber grip, heats | Plausible tool variant |
| Full-size rubber-grip paintbrush | Paints, bristles, rubber grip | Compact, cuts wire | Plausible tool variant |
| Chopped dried apple | Fruit, sweet, firm, red skin, chopped, dried | Fungus, fresh profile | Plausible preparation |
| Whole fresh potato | Vegetable, tuber, starchy, firm | Chopped, dried, citrus | Plausible preparation |
| Whole dried shiitake | Fungus, cap, brown skin, dried | Chopped, legume | Plausible preparation |
| Chopped fresh almond | Nut, oily, grows on tree, chopped | Dried, citrus | Plausible preparation |

These checks found no categorical mismatch in the inspected examples. Remaining fine-grained inaccuracies are possible. The table defines the game answers. Every row, every split, and every sampled subset passes machine uniqueness checks. Columns constant within a sampled subset are removed without changing row distinguishability.
