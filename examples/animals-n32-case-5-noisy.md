# paid-v1/animals/32/5/p0.1

Target `adult_male_komodo_dragon`. Answer flip probability 0.1. [Frozen cases](../evals/frozen/animals_n32_p0.10.jsonl.gz).

## Opening prompt

System

~~~text
You are the guesser in a yes/no identification game. One of the table's items is hidden. Identify it using answers to Boolean questions, then make a final guess.

Reply with ONE action on ONE line. No explanation, table, code block, or extra text.
To ask: ASK: <expression>
To finish: GUESS: <exact item name from TABLE>
A guess ends the game. It wins only when it names the hidden item. You must make a guess after the last allowed answer.

Each expression is a Boolean test applied to ONE item. An attribute identifier is already a complete expression. AND, OR, NOT and parentheses combine expressions. Item equality is also legal: item == "<exact item name>". Any legal expression, including a list of item equalities, is allowed. Unknown attributes or item names are invalid. An invalid question consumes a question and returns INVALID.

Read ATTRIBUTES as code=full_name. The short codes in TABLE are a compact storage notation, not expression identifiers. In an ASK, copy the full_name to the RIGHT of =. An item has an attribute when its row lists that attribute's code; every omitted code is false. The table defines truth. Real-world knowledge does not override it.

GRAMMAR EXAMPLES, selected randomly, not moves already played:
ASK: africa
This tests that attribute on the hidden item's row.
ASK: NOT europe
This tests the negation of that attribute.
ASK: (africa AND large_ears)
This tests whether both named attributes are true.
These examples show syntax only. Select your own question. Never copy column codes into an expression.

DOMAIN animals
ATTRIBUTES code=name
a=adult,b=africa,c=america,d=antlers,e=aquatic,f=asia,g=australia,h=baleen,i=bird,j=black_white,k=burrows,l=carnivore,m=climbs,n=echolocates,o=europe,p=fast,q=feathers,r=female,s=flies,t=flippers,u=fur,v=herbivore,w=hibernates,x=hood,y=hooked_beak,z=hooves,aa=hops,ab=horns,ac=huge,ad=insectivore,ae=large,af=large_ears,ag=lays_eggs,ah=limbless,ai=long_arms,aj=long_neck,ak=long_snout,al=mammal,am=mountains,an=nocturnal,ao=omnivore,ap=packs,aq=polar,ar=pouch,as=reptile,at=scales,au=scavenges,av=shell,aw=slow,ax=spines,ay=spots,az=venomous,ba=webbed,bb=white
TABLE name|true column codes
juvenile_male_leopard|b,l,m,u,al,ay
adult_male_komodo_dragon|a,f,l,ae,ag,as,at,az
adult_male_capybara|a,c,e,u,v,ae,al,ba
juvenile_male_manatee|e,t,v,al,aw
adult_female_king_cobra|a,f,l,r,x,ag,ah,as,at,az
juvenile_female_arctic_fox|k,l,r,u,al,aq,bb
juvenile_male_musk_ox|u,v,z,ab,ae,al,aq
juvenile_male_arctic_fox|k,l,u,al,aq,bb
juvenile_male_king_cobra|f,l,x,ag,ah,as,at,az
juvenile_male_polar_bear|e,l,u,ae,al,aq,bb
juvenile_female_baboon|b,r,u,ak,al,ao,ap
adult_male_reindeer|a,d,u,v,z,al,aq
adult_male_sperm_whale|a,e,l,n,t,ac,al
adult_male_bald_eagle|a,c,i,l,q,s,y,ag
juvenile_female_green_sea_turtle|e,r,t,v,ag,as,at,av
adult_male_brown_hare|a,o,p,u,v,aa,af,al
juvenile_female_rabbit|k,o,r,u,v,aa,af,al
adult_female_common_wombat|a,g,k,r,u,v,al,ar
adult_male_leopard|a,b,l,m,u,al,ay
juvenile_female_crested_porcupine|b,r,v,al,an,ax
juvenile_male_brown_bear|o,u,w,ae,al,ao
juvenile_male_african_wild_dog|b,l,u,al,ap,ay
juvenile_male_rabbit|k,o,u,v,aa,af,al
juvenile_male_blue_whale|e,h,t,ac,al
adult_male_snow_leopard|a,f,l,m,u,al,am,ay
adult_female_orangutan|a,f,m,r,u,v,ai,al
juvenile_male_common_wombat|g,k,u,v,al,ar
adult_female_spotted_hyena|a,b,l,r,u,al,ap,au,ay
adult_female_giraffe|a,b,r,u,v,ac,aj,al,ay
juvenile_male_giant_panda|f,j,m,u,v,ae,al
adult_female_short_beaked_echidna|a,g,r,ad,ag,ak,al,ax
adult_female_blue_whale|a,e,h,r,t,ac,al
END TABLE

ENVIRONMENT STATE FEEDBACK
After each answer, including INVALID, the environment supplies candidate names.
With no answer noise, REMAINING CANDIDATES is the exact consistent set.
With answer noise, POSTERIOR CANDIDATES lists items with posterior probability
strictly above 0.001, plus the top candidate. TOP CANDIDATE is the maximum-posterior
item; ties use TABLE order. The noisy list is approximate: excluded items can
reappear after later answers. A list with one item does not prove certainty in
noisy mode. The full original TABLE stays available for every legal question.

~~~

User

~~~text
Answer flip probability: 0.10, independently each question. Maximum questions: 10. After the last answer, make one final guess; another question loses. Begin.
~~~

## Raw Qwen3-8B game

Loss. 10 counted questions. Return -1.3000000000000003.
[Source archive](../results/main_A11/games.jsonl.gz).

### Action 1

~~~text
ASK: (adult AND (mammal AND (not (fast) AND (not (white)))))
~~~

Environment reply

~~~text
INVALID
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["juvenile_male_leopard","adult_male_komodo_dragon","adult_male_capybara","juvenile_male_manatee","adult_female_king_cobra","juvenile_female_arctic_fox","juvenile_male_musk_ox","juvenile_male_arctic_fox","juvenile_male_king_cobra","juvenile_male_polar_bear","juvenile_female_baboon","adult_male_reindeer","adult_male_sperm_whale","adult_male_bald_eagle","juvenile_female_green_sea_turtle","adult_male_brown_hare","juvenile_female_rabbit","adult_female_common_wombat","adult_male_leopard","juvenile_female_crested_porcupine","juvenile_male_brown_bear","juvenile_male_african_wild_dog","juvenile_male_rabbit","juvenile_male_blue_whale","adult_male_snow_leopard","adult_female_orangutan","juvenile_male_common_wombat","adult_female_spotted_hyena","adult_female_giraffe","juvenile_male_giant_panda","adult_female_short_beaked_echidna","adult_female_blue_whale"]
TOP CANDIDATE: juvenile_male_leopard
~~~

### Action 2

~~~text
ASK: (mammal AND (not (fast) AND (not (white))))
~~~

Environment reply

~~~text
INVALID
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["juvenile_male_leopard","adult_male_komodo_dragon","adult_male_capybara","juvenile_male_manatee","adult_female_king_cobra","juvenile_female_arctic_fox","juvenile_male_musk_ox","juvenile_male_arctic_fox","juvenile_male_king_cobra","juvenile_male_polar_bear","juvenile_female_baboon","adult_male_reindeer","adult_male_sperm_whale","adult_male_bald_eagle","juvenile_female_green_sea_turtle","adult_male_brown_hare","juvenile_female_rabbit","adult_female_common_wombat","adult_male_leopard","juvenile_female_crested_porcupine","juvenile_male_brown_bear","juvenile_male_african_wild_dog","juvenile_male_rabbit","juvenile_male_blue_whale","adult_male_snow_leopard","adult_female_orangutan","juvenile_male_common_wombat","adult_female_spotted_hyena","adult_female_giraffe","juvenile_male_giant_panda","adult_female_short_beaked_echidna","adult_female_blue_whale"]
TOP CANDIDATE: juvenile_male_leopard
~~~

### Action 3

~~~text
ASK: (mammal AND (not (fast) AND (not (white)) AND (not (long_neck))))
~~~

Environment reply

~~~text
INVALID
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["juvenile_male_leopard","adult_male_komodo_dragon","adult_male_capybara","juvenile_male_manatee","adult_female_king_cobra","juvenile_female_arctic_fox","juvenile_male_musk_ox","juvenile_male_arctic_fox","juvenile_male_king_cobra","juvenile_male_polar_bear","juvenile_female_baboon","adult_male_reindeer","adult_male_sperm_whale","adult_male_bald_eagle","juvenile_female_green_sea_turtle","adult_male_brown_hare","juvenile_female_rabbit","adult_female_common_wombat","adult_male_leopard","juvenile_female_crested_porcupine","juvenile_male_brown_bear","juvenile_male_african_wild_dog","juvenile_male_rabbit","juvenile_male_blue_whale","adult_male_snow_leopard","adult_female_orangutan","juvenile_male_common_wombat","adult_female_spotted_hyena","adult_female_giraffe","juvenile_male_giant_panda","adult_female_short_beaked_echidna","adult_female_blue_whale"]
TOP CANDIDATE: juvenile_male_leopard
~~~

### Action 4

~~~text
ASK: (mammal AND (not (fast) AND (not (white)) AND (not (long_neck)) AND (not (long_arms))))
~~~

Environment reply

~~~text
INVALID
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["juvenile_male_leopard","adult_male_komodo_dragon","adult_male_capybara","juvenile_male_manatee","adult_female_king_cobra","juvenile_female_arctic_fox","juvenile_male_musk_ox","juvenile_male_arctic_fox","juvenile_male_king_cobra","juvenile_male_polar_bear","juvenile_female_baboon","adult_male_reindeer","adult_male_sperm_whale","adult_male_bald_eagle","juvenile_female_green_sea_turtle","adult_male_brown_hare","juvenile_female_rabbit","adult_female_common_wombat","adult_male_leopard","juvenile_female_crested_porcupine","juvenile_male_brown_bear","juvenile_male_african_wild_dog","juvenile_male_rabbit","juvenile_male_blue_whale","adult_male_snow_leopard","adult_female_orangutan","juvenile_male_common_wombat","adult_female_spotted_hyena","adult_female_giraffe","juvenile_male_giant_panda","adult_female_short_beaked_echidna","adult_female_blue_whale"]
TOP CANDIDATE: juvenile_male_leopard
~~~

### Action 5

~~~text
ASK: (mammal AND (not (fast) AND (not (white)) AND (not (long_neck)) AND (not (long_arms)) AND (not (long_snout))))
~~~

Environment reply

~~~text
INVALID
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["juvenile_male_leopard","adult_male_komodo_dragon","adult_male_capybara","juvenile_male_manatee","adult_female_king_cobra","juvenile_female_arctic_fox","juvenile_male_musk_ox","juvenile_male_arctic_fox","juvenile_male_king_cobra","juvenile_male_polar_bear","juvenile_female_baboon","adult_male_reindeer","adult_male_sperm_whale","adult_male_bald_eagle","juvenile_female_green_sea_turtle","adult_male_brown_hare","juvenile_female_rabbit","adult_female_common_wombat","adult_male_leopard","juvenile_female_crested_porcupine","juvenile_male_brown_bear","juvenile_male_african_wild_dog","juvenile_male_rabbit","juvenile_male_blue_whale","adult_male_snow_leopard","adult_female_orangutan","juvenile_male_common_wombat","adult_female_spotted_hyena","adult_female_giraffe","juvenile_male_giant_panda","adult_female_short_beaked_echidna","adult_female_blue_whale"]
TOP CANDIDATE: juvenile_male_leopard
~~~

### Action 6

~~~text
ASK: (mammal AND (not (fast) AND (not (white)) AND (not (long_neck)) AND (not (long_arms)) AND (not (long_snout)) AND (not (spots))))
~~~

Environment reply

~~~text
INVALID
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["juvenile_male_leopard","adult_male_komodo_dragon","adult_male_capybara","juvenile_male_manatee","adult_female_king_cobra","juvenile_female_arctic_fox","juvenile_male_musk_ox","juvenile_male_arctic_fox","juvenile_male_king_cobra","juvenile_male_polar_bear","juvenile_female_baboon","adult_male_reindeer","adult_male_sperm_whale","adult_male_bald_eagle","juvenile_female_green_sea_turtle","adult_male_brown_hare","juvenile_female_rabbit","adult_female_common_wombat","adult_male_leopard","juvenile_female_crested_porcupine","juvenile_male_brown_bear","juvenile_male_african_wild_dog","juvenile_male_rabbit","juvenile_male_blue_whale","adult_male_snow_leopard","adult_female_orangutan","juvenile_male_common_wombat","adult_female_spotted_hyena","adult_female_giraffe","juvenile_male_giant_panda","adult_female_short_beaked_echidna","adult_female_blue_whale"]
TOP CANDIDATE: juvenile_male_leopard
~~~

### Action 7

~~~text
ASK: (mammal AND (not (fast) AND (not (white)) AND (not (long_neck)) AND (not (long_arms)) AND (not (long_snout)) AND (not (spots)) AND (not (horns))))
~~~

Environment reply

~~~text
INVALID
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["juvenile_male_leopard","adult_male_komodo_dragon","adult_male_capybara","juvenile_male_manatee","adult_female_king_cobra","juvenile_female_arctic_fox","juvenile_male_musk_ox","juvenile_male_arctic_fox","juvenile_male_king_cobra","juvenile_male_polar_bear","juvenile_female_baboon","adult_male_reindeer","adult_male_sperm_whale","adult_male_bald_eagle","juvenile_female_green_sea_turtle","adult_male_brown_hare","juvenile_female_rabbit","adult_female_common_wombat","adult_male_leopard","juvenile_female_crested_porcupine","juvenile_male_brown_bear","juvenile_male_african_wild_dog","juvenile_male_rabbit","juvenile_male_blue_whale","adult_male_snow_leopard","adult_female_orangutan","juvenile_male_common_wombat","adult_female_spotted_hyena","adult_female_giraffe","juvenile_male_giant_panda","adult_female_short_beaked_echidna","adult_female_blue_whale"]
TOP CANDIDATE: juvenile_male_leopard
~~~

### Action 8

~~~text
ASK: (mammal AND (not (fast) AND (not (white)) AND (not (long_neck)) AND (not (long_arms)) AND (not (long_snout)) AND (not (spots)) AND (not (horns)) AND (not (hooves))))
~~~

Environment reply

~~~text
INVALID
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["juvenile_male_leopard","adult_male_komodo_dragon","adult_male_capybara","juvenile_male_manatee","adult_female_king_cobra","juvenile_female_arctic_fox","juvenile_male_musk_ox","juvenile_male_arctic_fox","juvenile_male_king_cobra","juvenile_male_polar_bear","juvenile_female_baboon","adult_male_reindeer","adult_male_sperm_whale","adult_male_bald_eagle","juvenile_female_green_sea_turtle","adult_male_brown_hare","juvenile_female_rabbit","adult_female_common_wombat","adult_male_leopard","juvenile_female_crested_porcupine","juvenile_male_brown_bear","juvenile_male_african_wild_dog","juvenile_male_rabbit","juvenile_male_blue_whale","adult_male_snow_leopard","adult_female_orangutan","juvenile_male_common_wombat","adult_female_spotted_hyena","adult_female_giraffe","juvenile_male_giant_panda","adult_female_short_beaked_echidna","adult_female_blue_whale"]
TOP CANDIDATE: juvenile_male_leopard
~~~

### Action 9

~~~text
ASK: (mammal AND (not (fast) AND (not (white)) AND (not (long_neck)) AND (not (long_arms)) AND (not (long_snout)) AND (not (spots)) AND (not (horns)) AND (not (hooves)) AND (not (spines))))
~~~

Environment reply

~~~text
INVALID
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["juvenile_male_leopard","adult_male_komodo_dragon","adult_male_capybara","juvenile_male_manatee","adult_female_king_cobra","juvenile_female_arctic_fox","juvenile_male_musk_ox","juvenile_male_arctic_fox","juvenile_male_king_cobra","juvenile_male_polar_bear","juvenile_female_baboon","adult_male_reindeer","adult_male_sperm_whale","adult_male_bald_eagle","juvenile_female_green_sea_turtle","adult_male_brown_hare","juvenile_female_rabbit","adult_female_common_wombat","adult_male_leopard","juvenile_female_crested_porcupine","juvenile_male_brown_bear","juvenile_male_african_wild_dog","juvenile_male_rabbit","juvenile_male_blue_whale","adult_male_snow_leopard","adult_female_orangutan","juvenile_male_common_wombat","adult_female_spotted_hyena","adult_female_giraffe","juvenile_male_giant_panda","adult_female_short_beaked_echidna","adult_female_blue_whale"]
TOP CANDIDATE: juvenile_male_leopard
~~~

### Action 10

~~~text
ASK: (mammal AND (not (fast) AND (not (white)) AND (not (long_neck)) AND (not (long_arms)) AND (not (long_snout)) AND (not (spots)) AND (not (horns)) AND (not (hooves)) AND (not (spines)) AND (not (webbed))))
~~~

Environment reply

~~~text
INVALID
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["juvenile_male_leopard","adult_male_komodo_dragon","adult_male_capybara","juvenile_male_manatee","adult_female_king_cobra","juvenile_female_arctic_fox","juvenile_male_musk_ox","juvenile_male_arctic_fox","juvenile_male_king_cobra","juvenile_male_polar_bear","juvenile_female_baboon","adult_male_reindeer","adult_male_sperm_whale","adult_male_bald_eagle","juvenile_female_green_sea_turtle","adult_male_brown_hare","juvenile_female_rabbit","adult_female_common_wombat","adult_male_leopard","juvenile_female_crested_porcupine","juvenile_male_brown_bear","juvenile_male_african_wild_dog","juvenile_male_rabbit","juvenile_male_blue_whale","adult_male_snow_leopard","adult_female_orangutan","juvenile_male_common_wombat","adult_female_spotted_hyena","adult_female_giraffe","juvenile_male_giant_panda","adult_female_short_beaked_echidna","adult_female_blue_whale"]
TOP CANDIDATE: juvenile_male_leopard
~~~

### Action 11

~~~text
ASK: (mammal AND (not (fast) AND (not (white)) AND (not (long_neck)) AND (not (long_arms)) AND (not (long_snout)) AND (not (spots)) AND (not (horns)) AND (not (hooves)) AND (not (spines)) AND (not (webbed)) AND (not (hops))))
~~~

Environment reply

~~~text
LOSS
~~~

## A11 game

Win. 7 counted questions. Return 0.79.
[Source archive](../results/main_A11/games.jsonl.gz).

[Opening prompt and table](#opening-prompt).

### Action 1

~~~text
ASK: al
~~~

Environment reply

~~~text
NO
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["juvenile_male_leopard","adult_male_komodo_dragon","adult_male_capybara","juvenile_male_manatee","adult_female_king_cobra","juvenile_female_arctic_fox","juvenile_male_musk_ox","juvenile_male_arctic_fox","juvenile_male_king_cobra","juvenile_male_polar_bear","juvenile_female_baboon","adult_male_reindeer","adult_male_sperm_whale","adult_male_bald_eagle","juvenile_female_green_sea_turtle","adult_male_brown_hare","juvenile_female_rabbit","adult_female_common_wombat","adult_male_leopard","juvenile_female_crested_porcupine","juvenile_male_brown_bear","juvenile_male_african_wild_dog","juvenile_male_rabbit","juvenile_male_blue_whale","adult_male_snow_leopard","adult_female_orangutan","juvenile_male_common_wombat","adult_female_spotted_hyena","adult_female_giraffe","juvenile_male_giant_panda","adult_female_short_beaked_echidna","adult_female_blue_whale"]
TOP CANDIDATE: adult_male_komodo_dragon
~~~

### Action 2

~~~text
ASK: k
~~~

Environment reply

~~~text
NO
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["juvenile_male_leopard","adult_male_komodo_dragon","adult_male_capybara","juvenile_male_manatee","adult_female_king_cobra","juvenile_female_arctic_fox","juvenile_male_musk_ox","juvenile_male_arctic_fox","juvenile_male_king_cobra","juvenile_male_polar_bear","juvenile_female_baboon","adult_male_reindeer","adult_male_sperm_whale","adult_male_bald_eagle","juvenile_female_green_sea_turtle","adult_male_brown_hare","juvenile_female_rabbit","adult_female_common_wombat","adult_male_leopard","juvenile_female_crested_porcupine","juvenile_male_brown_bear","juvenile_male_african_wild_dog","juvenile_male_rabbit","juvenile_male_blue_whale","adult_male_snow_leopard","adult_female_orangutan","juvenile_male_common_wombat","adult_female_spotted_hyena","adult_female_giraffe","juvenile_male_giant_panda","adult_female_short_beaked_echidna","adult_female_blue_whale"]
TOP CANDIDATE: adult_male_komodo_dragon
~~~

### Action 3

~~~text
ASK: u
~~~

Environment reply

~~~text
NO
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["juvenile_male_leopard","adult_male_komodo_dragon","adult_male_capybara","juvenile_male_manatee","adult_female_king_cobra","juvenile_male_musk_ox","juvenile_male_king_cobra","juvenile_male_polar_bear","juvenile_female_baboon","adult_male_reindeer","adult_male_sperm_whale","adult_male_bald_eagle","juvenile_female_green_sea_turtle","adult_male_brown_hare","adult_male_leopard","juvenile_female_crested_porcupine","juvenile_male_brown_bear","juvenile_male_african_wild_dog","juvenile_male_blue_whale","adult_male_snow_leopard","adult_female_orangutan","adult_female_spotted_hyena","adult_female_giraffe","juvenile_male_giant_panda","adult_female_short_beaked_echidna","adult_female_blue_whale"]
TOP CANDIDATE: adult_male_komodo_dragon
~~~

### Action 4

~~~text
ASK: l
~~~

Environment reply

~~~text
YES
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["juvenile_male_leopard","adult_male_komodo_dragon","juvenile_male_manatee","adult_female_king_cobra","juvenile_male_king_cobra","juvenile_male_polar_bear","adult_male_sperm_whale","adult_male_bald_eagle","juvenile_female_green_sea_turtle","adult_male_leopard","juvenile_female_crested_porcupine","juvenile_male_african_wild_dog","juvenile_male_blue_whale","adult_male_snow_leopard","adult_female_spotted_hyena","adult_female_short_beaked_echidna","adult_female_blue_whale"]
TOP CANDIDATE: adult_male_komodo_dragon
~~~

### Action 5

~~~text
ASK: m
~~~

Environment reply

~~~text
NO
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_male_komodo_dragon","juvenile_male_manatee","adult_female_king_cobra","juvenile_male_king_cobra","juvenile_male_polar_bear","adult_male_sperm_whale","adult_male_bald_eagle","juvenile_female_green_sea_turtle","juvenile_female_crested_porcupine","juvenile_male_african_wild_dog","juvenile_male_blue_whale","adult_female_spotted_hyena","adult_female_short_beaked_echidna","adult_female_blue_whale"]
TOP CANDIDATE: adult_male_komodo_dragon
~~~

### Action 6

~~~text
ASK: t
~~~

Environment reply

~~~text
NO
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_male_komodo_dragon","adult_female_king_cobra","juvenile_male_king_cobra","juvenile_male_polar_bear","adult_male_sperm_whale","adult_male_bald_eagle","juvenile_female_green_sea_turtle","juvenile_female_crested_porcupine","juvenile_male_african_wild_dog","adult_female_spotted_hyena","adult_female_short_beaked_echidna"]
TOP CANDIDATE: adult_male_komodo_dragon
~~~

### Action 7

~~~text
ASK: z
~~~

Environment reply

~~~text
NO
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_male_komodo_dragon","adult_female_king_cobra","juvenile_male_king_cobra","juvenile_male_polar_bear","adult_male_sperm_whale","adult_male_bald_eagle","juvenile_female_green_sea_turtle","juvenile_female_crested_porcupine","juvenile_male_african_wild_dog","adult_female_spotted_hyena","adult_female_short_beaked_echidna"]
TOP CANDIDATE: adult_male_komodo_dragon
~~~

### Action 8

~~~text
GUESS: adult_male_komodo_dragon
~~~

Environment reply

~~~text
WIN
~~~

## A23 game

Win. 8 counted questions. Return 0.76.
[Source archive](../results/main_A23/games.jsonl.gz).

[Opening prompt and table](#opening-prompt).

### Action 1

~~~text
ASK: u
~~~

Environment reply

~~~text
NO
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["juvenile_male_leopard","adult_male_komodo_dragon","adult_male_capybara","juvenile_male_manatee","adult_female_king_cobra","juvenile_female_arctic_fox","juvenile_male_musk_ox","juvenile_male_arctic_fox","juvenile_male_king_cobra","juvenile_male_polar_bear","juvenile_female_baboon","adult_male_reindeer","adult_male_sperm_whale","adult_male_bald_eagle","juvenile_female_green_sea_turtle","adult_male_brown_hare","juvenile_female_rabbit","adult_female_common_wombat","adult_male_leopard","juvenile_female_crested_porcupine","juvenile_male_brown_bear","juvenile_male_african_wild_dog","juvenile_male_rabbit","juvenile_male_blue_whale","adult_male_snow_leopard","adult_female_orangutan","juvenile_male_common_wombat","adult_female_spotted_hyena","adult_female_giraffe","juvenile_male_giant_panda","adult_female_short_beaked_echidna","adult_female_blue_whale"]
TOP CANDIDATE: adult_male_komodo_dragon
~~~

### Action 2

~~~text
ASK: l
~~~

Environment reply

~~~text
YES
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["juvenile_male_leopard","adult_male_komodo_dragon","adult_male_capybara","juvenile_male_manatee","adult_female_king_cobra","juvenile_female_arctic_fox","juvenile_male_musk_ox","juvenile_male_arctic_fox","juvenile_male_king_cobra","juvenile_male_polar_bear","juvenile_female_baboon","adult_male_reindeer","adult_male_sperm_whale","adult_male_bald_eagle","juvenile_female_green_sea_turtle","adult_male_brown_hare","juvenile_female_rabbit","adult_female_common_wombat","adult_male_leopard","juvenile_female_crested_porcupine","juvenile_male_brown_bear","juvenile_male_african_wild_dog","juvenile_male_rabbit","juvenile_male_blue_whale","adult_male_snow_leopard","adult_female_orangutan","juvenile_male_common_wombat","adult_female_spotted_hyena","adult_female_giraffe","juvenile_male_giant_panda","adult_female_short_beaked_echidna","adult_female_blue_whale"]
TOP CANDIDATE: adult_male_komodo_dragon
~~~

### Action 3

~~~text
ASK: al
~~~

Environment reply

~~~text
NO
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["juvenile_male_leopard","adult_male_komodo_dragon","juvenile_male_manatee","adult_female_king_cobra","juvenile_female_arctic_fox","juvenile_male_arctic_fox","juvenile_male_king_cobra","juvenile_male_polar_bear","adult_male_sperm_whale","adult_male_bald_eagle","juvenile_female_green_sea_turtle","adult_male_leopard","juvenile_female_crested_porcupine","juvenile_male_african_wild_dog","juvenile_male_blue_whale","adult_male_snow_leopard","adult_female_spotted_hyena","adult_female_short_beaked_echidna","adult_female_blue_whale"]
TOP CANDIDATE: adult_male_komodo_dragon
~~~

### Action 4

~~~text
ASK: a
~~~

Environment reply

~~~text
YES
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_male_komodo_dragon","adult_female_king_cobra","juvenile_male_king_cobra","adult_male_sperm_whale","adult_male_bald_eagle","juvenile_female_green_sea_turtle","adult_male_leopard","adult_male_snow_leopard","adult_female_spotted_hyena","adult_female_short_beaked_echidna","adult_female_blue_whale"]
TOP CANDIDATE: adult_male_komodo_dragon
~~~

### Action 5

~~~text
ASK: f
~~~

Environment reply

~~~text
YES
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_male_komodo_dragon","adult_female_king_cobra","juvenile_male_king_cobra","adult_male_sperm_whale","adult_male_bald_eagle","adult_male_snow_leopard"]
TOP CANDIDATE: adult_male_komodo_dragon
~~~

### Action 6

~~~text
ASK: ag
~~~

Environment reply

~~~text
YES
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_male_komodo_dragon","adult_female_king_cobra","juvenile_male_king_cobra","adult_male_bald_eagle"]
TOP CANDIDATE: adult_male_komodo_dragon
~~~

### Action 7

~~~text
ASK: as
~~~

Environment reply

~~~text
YES
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_male_komodo_dragon","adult_female_king_cobra","juvenile_male_king_cobra","adult_male_bald_eagle"]
TOP CANDIDATE: adult_male_komodo_dragon
~~~

### Action 8

~~~text
ASK: az
~~~

Environment reply

~~~text
YES
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_male_komodo_dragon","adult_female_king_cobra","juvenile_male_king_cobra"]
TOP CANDIDATE: adult_male_komodo_dragon
~~~

### Action 9

~~~text
GUESS: adult_male_komodo_dragon
~~~

Environment reply

~~~text
WIN
~~~

## B41 game

Win. 6 counted questions. Return 0.8200000000000001.
[Source archive](../results/main_B41/games.jsonl.gz).

[Opening prompt and table](#opening-prompt).

### Action 1

~~~text
ASK: al
~~~

Environment reply

~~~text
NO
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["juvenile_male_leopard","adult_male_komodo_dragon","adult_male_capybara","juvenile_male_manatee","adult_female_king_cobra","juvenile_female_arctic_fox","juvenile_male_musk_ox","juvenile_male_arctic_fox","juvenile_male_king_cobra","juvenile_male_polar_bear","juvenile_female_baboon","adult_male_reindeer","adult_male_sperm_whale","adult_male_bald_eagle","juvenile_female_green_sea_turtle","adult_male_brown_hare","juvenile_female_rabbit","adult_female_common_wombat","adult_male_leopard","juvenile_female_crested_porcupine","juvenile_male_brown_bear","juvenile_male_african_wild_dog","juvenile_male_rabbit","juvenile_male_blue_whale","adult_male_snow_leopard","adult_female_orangutan","juvenile_male_common_wombat","adult_female_spotted_hyena","adult_female_giraffe","juvenile_male_giant_panda","adult_female_short_beaked_echidna","adult_female_blue_whale"]
TOP CANDIDATE: adult_male_komodo_dragon
~~~

### Action 2

~~~text
ASK: ae
~~~

Environment reply

~~~text
YES
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["juvenile_male_leopard","adult_male_komodo_dragon","adult_male_capybara","juvenile_male_manatee","adult_female_king_cobra","juvenile_female_arctic_fox","juvenile_male_musk_ox","juvenile_male_arctic_fox","juvenile_male_king_cobra","juvenile_male_polar_bear","juvenile_female_baboon","adult_male_reindeer","adult_male_sperm_whale","adult_male_bald_eagle","juvenile_female_green_sea_turtle","adult_male_brown_hare","juvenile_female_rabbit","adult_female_common_wombat","adult_male_leopard","juvenile_female_crested_porcupine","juvenile_male_brown_bear","juvenile_male_african_wild_dog","juvenile_male_rabbit","juvenile_male_blue_whale","adult_male_snow_leopard","adult_female_orangutan","juvenile_male_common_wombat","adult_female_spotted_hyena","adult_female_giraffe","juvenile_male_giant_panda","adult_female_short_beaked_echidna","adult_female_blue_whale"]
TOP CANDIDATE: adult_male_komodo_dragon
~~~

### Action 3

~~~text
ASK: al AND ae
~~~

Environment reply

~~~text
NO
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["juvenile_male_leopard","adult_male_komodo_dragon","adult_male_capybara","juvenile_male_manatee","adult_female_king_cobra","juvenile_female_arctic_fox","juvenile_male_musk_ox","juvenile_male_arctic_fox","juvenile_male_king_cobra","juvenile_male_polar_bear","juvenile_female_baboon","adult_male_reindeer","adult_male_sperm_whale","adult_male_bald_eagle","juvenile_female_green_sea_turtle","adult_male_brown_hare","juvenile_female_rabbit","adult_female_common_wombat","adult_male_leopard","juvenile_female_crested_porcupine","juvenile_male_brown_bear","juvenile_male_african_wild_dog","juvenile_male_rabbit","juvenile_male_blue_whale","adult_male_snow_leopard","adult_female_orangutan","juvenile_male_common_wombat","adult_female_spotted_hyena","adult_female_giraffe","juvenile_male_giant_panda","adult_female_short_beaked_echidna","adult_female_blue_whale"]
TOP CANDIDATE: adult_male_komodo_dragon
~~~

### Action 4

~~~text
ASK: al AND af
~~~

Environment reply

~~~text
NO
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["juvenile_male_leopard","adult_male_komodo_dragon","adult_male_capybara","juvenile_male_manatee","adult_female_king_cobra","juvenile_female_arctic_fox","juvenile_male_musk_ox","juvenile_male_arctic_fox","juvenile_male_king_cobra","juvenile_male_polar_bear","juvenile_female_baboon","adult_male_reindeer","adult_male_sperm_whale","adult_male_bald_eagle","juvenile_female_green_sea_turtle","adult_female_common_wombat","adult_male_leopard","juvenile_female_crested_porcupine","juvenile_male_brown_bear","juvenile_male_african_wild_dog","juvenile_male_blue_whale","adult_male_snow_leopard","adult_female_orangutan","juvenile_male_common_wombat","adult_female_spotted_hyena","adult_female_giraffe","juvenile_male_giant_panda","adult_female_short_beaked_echidna","adult_female_blue_whale"]
TOP CANDIDATE: adult_male_komodo_dragon
~~~

### Action 5

~~~text
ASK: al AND af AND ae
~~~

Environment reply

~~~text
NO
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["juvenile_male_leopard","adult_male_komodo_dragon","adult_male_capybara","juvenile_male_manatee","adult_female_king_cobra","juvenile_female_arctic_fox","juvenile_male_musk_ox","juvenile_male_arctic_fox","juvenile_male_king_cobra","juvenile_male_polar_bear","juvenile_female_baboon","adult_male_reindeer","adult_male_sperm_whale","adult_male_bald_eagle","juvenile_female_green_sea_turtle","adult_female_common_wombat","adult_male_leopard","juvenile_female_crested_porcupine","juvenile_male_brown_bear","juvenile_male_african_wild_dog","juvenile_male_blue_whale","adult_male_snow_leopard","adult_female_orangutan","juvenile_male_common_wombat","adult_female_spotted_hyena","adult_female_giraffe","juvenile_male_giant_panda","adult_female_short_beaked_echidna","adult_female_blue_whale"]
TOP CANDIDATE: adult_male_komodo_dragon
~~~

### Action 6

~~~text
ASK: al AND ae AND af
~~~

Environment reply

~~~text
NO
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["juvenile_male_leopard","adult_male_komodo_dragon","adult_male_capybara","juvenile_male_manatee","adult_female_king_cobra","juvenile_female_arctic_fox","juvenile_male_musk_ox","juvenile_male_arctic_fox","juvenile_male_king_cobra","juvenile_male_polar_bear","juvenile_female_baboon","adult_male_reindeer","adult_male_sperm_whale","adult_male_bald_eagle","juvenile_female_green_sea_turtle","adult_female_common_wombat","adult_male_leopard","juvenile_female_crested_porcupine","juvenile_male_brown_bear","juvenile_male_african_wild_dog","juvenile_male_blue_whale","adult_male_snow_leopard","adult_female_orangutan","juvenile_male_common_wombat","adult_female_spotted_hyena","adult_female_giraffe","juvenile_male_giant_panda","adult_female_short_beaked_echidna","adult_female_blue_whale"]
TOP CANDIDATE: adult_male_komodo_dragon
~~~

### Action 7

~~~text
GUESS: adult_male_komodo_dragon
~~~

Environment reply

~~~text
WIN
~~~
