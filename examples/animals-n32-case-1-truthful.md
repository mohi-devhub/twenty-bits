# paid-v1/animals/32/1/p0

Target `juvenile_female_arctic_fox`. Answer flip probability 0. [Frozen cases](../evals/frozen/animals_n32_p0.00.jsonl.gz).

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
ASK: hops
This tests that attribute on the hidden item's row.
ASK: NOT tusks
This tests the negation of that attribute.
ASK: (hops AND antlers)
This tests whether both named attributes are true.
These examples show syntax only. Select your own question. Never copy column codes into an expression.

DOMAIN animals
ATTRIBUTES code=name
a=adult,b=adult_male_mane,c=africa,d=america,e=antlers,f=aquatic,g=armor,h=asia,i=australia,j=bird,k=black,l=black_white,m=burrows,n=carnivore,o=climbs,p=color_change,q=europe,r=fast,s=feathers,t=female,u=flies,v=flippers,w=fur,x=hangs,y=herbivore,z=hood,aa=hooked_beak,ab=hooves,ac=hops,ad=insectivore,ae=large,af=large_ears,ag=lays_eggs,ah=limbless,ai=long_neck,aj=long_snout,ak=long_tongue,al=loud,am=mammal,an=nocturnal,ao=omnivore,ap=packs,aq=pink,ar=polar,as=pouch,at=prehensile_tail,au=reptile,av=scales,aw=silent,ax=spots,ay=stripes,az=tusks,ba=venomous,bb=webbed,bc=white
TABLE name|true column codes
juvenile_male_platypus|f,i,w,ag,am,ba,bb
juvenile_male_polar_bear|f,n,w,ae,am,ar,bc
adult_male_flamingo|a,f,j,s,u,ag,ai,aq
adult_male_barn_owl|a,j,n,s,u,ag,an,aw
adult_female_common_wombat|a,i,m,t,w,y,am,as
adult_male_reindeer|a,e,w,y,ab,am,ar
juvenile_male_giant_panda|h,l,o,w,y,ae,am
adult_female_brown_hare|a,q,r,t,w,y,ac,af,am
juvenile_male_chameleon|o,p,ad,ag,ak,au,av
juvenile_male_walrus|f,n,v,am,ar,az
adult_male_howler_monkey|a,d,o,w,y,al,am,at
juvenile_male_nine_banded_armadillo|d,g,m,ad,am
adult_male_chameleon|a,o,p,ad,ag,ak,au,av
juvenile_female_cheetah|c,n,r,t,w,am,ax
adult_male_pangolin|a,c,g,o,ad,am,an
juvenile_male_howler_monkey|d,o,w,y,al,am,at
juvenile_female_zebra|c,t,w,y,ab,ae,am,ay
adult_female_lion|a,b,c,n,t,w,ae,am,ap
juvenile_female_brown_hare|q,r,t,w,y,ac,af,am
adult_female_aardvark|a,c,m,t,w,ad,aj,am,an
juvenile_female_capybara|d,f,t,w,y,ae,am,bb
adult_female_howler_monkey|a,d,o,t,w,y,al,am,at
juvenile_male_fruit_bat|u,w,x,y,am,an
juvenile_female_arctic_fox|m,n,t,w,am,ar,bc
adult_male_king_cobra|a,h,n,z,ag,ah,au,av,ba
adult_female_cheetah|a,c,n,r,t,w,am,ax
juvenile_female_bald_eagle|d,j,n,s,t,u,aa,ag
adult_male_red_fox|a,m,n,q,w,am,an
juvenile_male_silky_anteater|d,o,w,ad,aj,am,an
juvenile_male_raven|j,k,s,u,ag,al,ao
adult_male_giant_anteater|a,d,w,ad,ae,aj,am
adult_male_walrus|a,f,n,v,am,ar,az
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
Answer flip probability: 0.00, independently each question. Maximum questions: 10. After the last answer, make one final guess; another question loses. Begin.
~~~

## Raw Qwen3-8B game

Win. 7 counted questions. Return 0.79.
[Source archive](../results/main_A11/games.jsonl.gz).

### Action 1

~~~text
ASK: am
~~~

Environment reply

~~~text
YES
REMAINING CANDIDATES: ["juvenile_male_platypus","juvenile_male_polar_bear","adult_female_common_wombat","adult_male_reindeer","juvenile_male_giant_panda","adult_female_brown_hare","juvenile_male_walrus","adult_male_howler_monkey","juvenile_male_nine_banded_armadillo","juvenile_female_cheetah","adult_male_pangolin","juvenile_male_howler_monkey","juvenile_female_zebra","adult_female_lion","juvenile_female_brown_hare","adult_female_aardvark","juvenile_female_capybara","adult_female_howler_monkey","juvenile_male_fruit_bat","juvenile_female_arctic_fox","adult_female_cheetah","adult_male_red_fox","juvenile_male_silky_anteater","adult_male_giant_anteater","adult_male_walrus"]
~~~

### Action 2

~~~text
ASK: am AND NOT w
~~~

Environment reply

~~~text
NO
REMAINING CANDIDATES: ["juvenile_male_platypus","juvenile_male_polar_bear","adult_female_common_wombat","adult_male_reindeer","juvenile_male_giant_panda","adult_female_brown_hare","adult_male_howler_monkey","juvenile_female_cheetah","juvenile_male_howler_monkey","juvenile_female_zebra","adult_female_lion","juvenile_female_brown_hare","adult_female_aardvark","juvenile_female_capybara","adult_female_howler_monkey","juvenile_male_fruit_bat","juvenile_female_arctic_fox","adult_female_cheetah","adult_male_red_fox","juvenile_male_silky_anteater","adult_male_giant_anteater"]
~~~

### Action 3

~~~text
ASK: am AND t
~~~

Environment reply

~~~text
YES
REMAINING CANDIDATES: ["adult_female_common_wombat","adult_female_brown_hare","juvenile_female_cheetah","juvenile_female_zebra","adult_female_lion","juvenile_female_brown_hare","adult_female_aardvark","juvenile_female_capybara","adult_female_howler_monkey","juvenile_female_arctic_fox","adult_female_cheetah"]
~~~

### Action 4

~~~text
ASK: am AND t AND NOT y
~~~

Environment reply

~~~text
YES
REMAINING CANDIDATES: ["juvenile_female_cheetah","adult_female_lion","adult_female_aardvark","juvenile_female_arctic_fox","adult_female_cheetah"]
~~~

### Action 5

~~~text
ASK: am AND t AND NOT y AND NOT ax
~~~

Environment reply

~~~text
YES
REMAINING CANDIDATES: ["adult_female_lion","adult_female_aardvark","juvenile_female_arctic_fox"]
~~~

### Action 6

~~~text
ASK: am AND t AND NOT y AND NOT ax AND NOT ap
~~~

Environment reply

~~~text
YES
REMAINING CANDIDATES: ["adult_female_aardvark","juvenile_female_arctic_fox"]
~~~

### Action 7

~~~text
ASK: am AND t AND NOT y AND NOT ax AND NOT ap AND NOT an
~~~

Environment reply

~~~text
YES
REMAINING CANDIDATES: ["juvenile_female_arctic_fox"]
~~~

### Action 8

~~~text
GUESS: juvenile_female_arctic_fox
~~~

Environment reply

~~~text
WIN
~~~

## A11 game

Loss. 5 counted questions. Return -0.15.
[Source archive](../results/main_A11/games.jsonl.gz).

[Opening prompt and table](#opening-prompt).

### Action 1

~~~text
ASK: w
~~~

Environment reply

~~~text
YES
REMAINING CANDIDATES: ["juvenile_male_platypus","juvenile_male_polar_bear","adult_female_common_wombat","adult_male_reindeer","juvenile_male_giant_panda","adult_female_brown_hare","adult_male_howler_monkey","juvenile_female_cheetah","juvenile_male_howler_monkey","juvenile_female_zebra","adult_female_lion","juvenile_female_brown_hare","adult_female_aardvark","juvenile_female_capybara","adult_female_howler_monkey","juvenile_male_fruit_bat","juvenile_female_arctic_fox","adult_female_cheetah","adult_male_red_fox","juvenile_male_silky_anteater","adult_male_giant_anteater"]
~~~

### Action 2

~~~text
ASK: t
~~~

Environment reply

~~~text
YES
REMAINING CANDIDATES: ["adult_female_common_wombat","adult_female_brown_hare","juvenile_female_cheetah","juvenile_female_zebra","adult_female_lion","juvenile_female_brown_hare","adult_female_aardvark","juvenile_female_capybara","adult_female_howler_monkey","juvenile_female_arctic_fox","adult_female_cheetah"]
~~~

### Action 3

~~~text
ASK: y
~~~

Environment reply

~~~text
NO
REMAINING CANDIDATES: ["juvenile_female_cheetah","adult_female_lion","adult_female_aardvark","juvenile_female_arctic_fox","adult_female_cheetah"]
~~~

### Action 4

~~~text
ASK: r
~~~

Environment reply

~~~text
NO
REMAINING CANDIDATES: ["adult_female_lion","adult_female_aardvark","juvenile_female_arctic_fox"]
~~~

### Action 5

~~~text
ASK: m
~~~

Environment reply

~~~text
YES
REMAINING CANDIDATES: ["adult_female_aardvark","juvenile_female_arctic_fox"]
~~~

### Action 6

~~~text
GUESS: adult_female_aardvark
~~~

Environment reply

~~~text
LOSS
~~~

## A23 game

Loss. 10 counted questions. Return -0.30000000000000004.
[Source archive](../results/main_A23/games.jsonl.gz).

[Opening prompt and table](#opening-prompt).

### Action 1

~~~text
ASK: am
~~~

Environment reply

~~~text
YES
REMAINING CANDIDATES: ["juvenile_male_platypus","juvenile_male_polar_bear","adult_female_common_wombat","adult_male_reindeer","juvenile_male_giant_panda","adult_female_brown_hare","juvenile_male_walrus","adult_male_howler_monkey","juvenile_male_nine_banded_armadillo","juvenile_female_cheetah","adult_male_pangolin","juvenile_male_howler_monkey","juvenile_female_zebra","adult_female_lion","juvenile_female_brown_hare","adult_female_aardvark","juvenile_female_capybara","adult_female_howler_monkey","juvenile_male_fruit_bat","juvenile_female_arctic_fox","adult_female_cheetah","adult_male_red_fox","juvenile_male_silky_anteater","adult_male_giant_anteater","adult_male_walrus"]
~~~

### Action 2

~~~text
ASK: w
~~~

Environment reply

~~~text
YES
REMAINING CANDIDATES: ["juvenile_male_platypus","juvenile_male_polar_bear","adult_female_common_wombat","adult_male_reindeer","juvenile_male_giant_panda","adult_female_brown_hare","adult_male_howler_monkey","juvenile_female_cheetah","juvenile_male_howler_monkey","juvenile_female_zebra","adult_female_lion","juvenile_female_brown_hare","adult_female_aardvark","juvenile_female_capybara","adult_female_howler_monkey","juvenile_male_fruit_bat","juvenile_female_arctic_fox","adult_female_cheetah","adult_male_red_fox","juvenile_male_silky_anteater","adult_male_giant_anteater"]
~~~

### Action 3

~~~text
ASK: t
~~~

Environment reply

~~~text
YES
REMAINING CANDIDATES: ["adult_female_common_wombat","adult_female_brown_hare","juvenile_female_cheetah","juvenile_female_zebra","adult_female_lion","juvenile_female_brown_hare","adult_female_aardvark","juvenile_female_capybara","adult_female_howler_monkey","juvenile_female_arctic_fox","adult_female_cheetah"]
~~~

### Action 4

~~~text
ASK: am
~~~

Environment reply

~~~text
YES
REMAINING CANDIDATES: ["adult_female_common_wombat","adult_female_brown_hare","juvenile_female_cheetah","juvenile_female_zebra","adult_female_lion","juvenile_female_brown_hare","adult_female_aardvark","juvenile_female_capybara","adult_female_howler_monkey","juvenile_female_arctic_fox","adult_female_cheetah"]
~~~

### Action 5

~~~text
ASK: r
~~~

Environment reply

~~~text
NO
REMAINING CANDIDATES: ["adult_female_common_wombat","juvenile_female_zebra","adult_female_lion","adult_female_aardvark","juvenile_female_capybara","adult_female_howler_monkey","juvenile_female_arctic_fox"]
~~~

### Action 6

~~~text
ASK: ae
~~~

Environment reply

~~~text
NO
REMAINING CANDIDATES: ["adult_female_common_wombat","adult_female_aardvark","adult_female_howler_monkey","juvenile_female_arctic_fox"]
~~~

### Action 7

~~~text
ASK: ab
~~~

Environment reply

~~~text
NO
REMAINING CANDIDATES: ["adult_female_common_wombat","adult_female_aardvark","adult_female_howler_monkey","juvenile_female_arctic_fox"]
~~~

### Action 8

~~~text
ASK: ac
~~~

Environment reply

~~~text
NO
REMAINING CANDIDATES: ["adult_female_common_wombat","adult_female_aardvark","adult_female_howler_monkey","juvenile_female_arctic_fox"]
~~~

### Action 9

~~~text
ASK: ag
~~~

Environment reply

~~~text
NO
REMAINING CANDIDATES: ["adult_female_common_wombat","adult_female_aardvark","adult_female_howler_monkey","juvenile_female_arctic_fox"]
~~~

### Action 10

~~~text
ASK: an
~~~

Environment reply

~~~text
NO
REMAINING CANDIDATES: ["adult_female_common_wombat","adult_female_howler_monkey","juvenile_female_arctic_fox"]
~~~

### Action 11

~~~text
ASK: ai
~~~

Environment reply

~~~text
LOSS
~~~

## B41 game

Loss. 7 counted questions. Return -0.21.
[Source archive](../results/main_B41/games.jsonl.gz).

[Opening prompt and table](#opening-prompt).

### Action 1

~~~text
ASK: am
~~~

Environment reply

~~~text
YES
REMAINING CANDIDATES: ["juvenile_male_platypus","juvenile_male_polar_bear","adult_female_common_wombat","adult_male_reindeer","juvenile_male_giant_panda","adult_female_brown_hare","juvenile_male_walrus","adult_male_howler_monkey","juvenile_male_nine_banded_armadillo","juvenile_female_cheetah","adult_male_pangolin","juvenile_male_howler_monkey","juvenile_female_zebra","adult_female_lion","juvenile_female_brown_hare","adult_female_aardvark","juvenile_female_capybara","adult_female_howler_monkey","juvenile_male_fruit_bat","juvenile_female_arctic_fox","adult_female_cheetah","adult_male_red_fox","juvenile_male_silky_anteater","adult_male_giant_anteater","adult_male_walrus"]
~~~

### Action 2

~~~text
ASK: w
~~~

Environment reply

~~~text
YES
REMAINING CANDIDATES: ["juvenile_male_platypus","juvenile_male_polar_bear","adult_female_common_wombat","adult_male_reindeer","juvenile_male_giant_panda","adult_female_brown_hare","adult_male_howler_monkey","juvenile_female_cheetah","juvenile_male_howler_monkey","juvenile_female_zebra","adult_female_lion","juvenile_female_brown_hare","adult_female_aardvark","juvenile_female_capybara","adult_female_howler_monkey","juvenile_male_fruit_bat","juvenile_female_arctic_fox","adult_female_cheetah","adult_male_red_fox","juvenile_male_silky_anteater","adult_male_giant_anteater"]
~~~

### Action 3

~~~text
ASK: t
~~~

Environment reply

~~~text
YES
REMAINING CANDIDATES: ["adult_female_common_wombat","adult_female_brown_hare","juvenile_female_cheetah","juvenile_female_zebra","adult_female_lion","juvenile_female_brown_hare","adult_female_aardvark","juvenile_female_capybara","adult_female_howler_monkey","juvenile_female_arctic_fox","adult_female_cheetah"]
~~~

### Action 4

~~~text
ASK: am
~~~

Environment reply

~~~text
YES
REMAINING CANDIDATES: ["adult_female_common_wombat","adult_female_brown_hare","juvenile_female_cheetah","juvenile_female_zebra","adult_female_lion","juvenile_female_brown_hare","adult_female_aardvark","juvenile_female_capybara","adult_female_howler_monkey","juvenile_female_arctic_fox","adult_female_cheetah"]
~~~

### Action 5

~~~text
ASK: y
~~~

Environment reply

~~~text
NO
REMAINING CANDIDATES: ["juvenile_female_cheetah","adult_female_lion","adult_female_aardvark","juvenile_female_arctic_fox","adult_female_cheetah"]
~~~

### Action 6

~~~text
ASK: r
~~~

Environment reply

~~~text
NO
REMAINING CANDIDATES: ["adult_female_lion","adult_female_aardvark","juvenile_female_arctic_fox"]
~~~

### Action 7

~~~text
ASK: n
~~~

Environment reply

~~~text
YES
REMAINING CANDIDATES: ["adult_female_lion","juvenile_female_arctic_fox"]
~~~

### Action 8

~~~text
GUESS: adult_female_lion
~~~

Environment reply

~~~text
LOSS
~~~
