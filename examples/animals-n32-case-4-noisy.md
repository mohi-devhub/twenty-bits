# paid-v1/animals/32/4/p0.1

Target `juvenile_male_spotted_hyena`. Answer flip probability 0.1. [Frozen cases](../evals/frozen/animals_n32_p0.10.jsonl.gz).

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
ASK: armor
This tests that attribute on the hidden item's row.
ASK: NOT packs
This tests the negation of that attribute.
ASK: (armor AND ringed_tail)
This tests whether both named attributes are true.
These examples show syntax only. Select your own question. Never copy column codes into an expression.

DOMAIN animals
ATTRIBUTES code=name
a=adult,b=adult_male_mane,c=africa,d=america,e=antlers,f=aquatic,g=armor,h=asia,i=australia,j=baleen,k=bird,l=burrows,m=carnivore,n=climbs,o=desert,p=echolocates,q=europe,r=fast,s=feathers,t=female,u=flies,v=flippers,w=fur,x=herbivore,y=hood,z=hooked_beak,aa=hooves,ab=hops,ac=horns,ad=huge,ae=humps,af=insectivore,ag=large,ah=large_ears,ai=lays_eggs,aj=limbless,ak=long_arms,al=long_neck,am=long_snout,an=mammal,ao=mountains,ap=nocturnal,aq=omnivore,ar=packs,as=pink,at=polar,au=pouch,av=reptile,aw=ringed_tail,ax=scales,ay=scavenges,az=silent,ba=sings,bb=slow,bc=spines,bd=spots,be=spray,bf=stripes,bg=swings,bh=throat_pouch,bi=venomous,bj=white
TABLE name|true column codes
adult_male_crocodile|a,f,g,m,ag,ai,av,ax
adult_female_llama|a,d,t,w,x,aa,ag,al,an,ao
juvenile_female_mountain_goat|d,n,t,w,x,aa,ac,an,ao,bj
adult_male_virginia_opossum|a,d,n,w,an,ap,au
juvenile_male_chinchilla|d,w,x,ab,an,ao
adult_female_bactrian_camel|a,h,o,t,w,x,aa,ae,ag,an
juvenile_male_parrot|k,n,s,u,x,z,ai
juvenile_male_ring_tailed_lemur|c,n,w,an,aq,aw
juvenile_female_sperm_whale|f,m,p,t,v,ad,an
juvenile_male_manatee|f,v,x,an,bb
adult_female_gibbon|a,h,n,t,w,x,ak,an,bg
adult_female_humpback_whale|a,f,j,t,v,ad,an,ba
juvenile_male_spotted_hyena|c,m,w,an,ar,ay,bd
juvenile_female_fennec_fox|c,l,m,o,t,w,ah,an,ap
juvenile_female_cheetah|c,m,r,t,w,an,bd
juvenile_female_crested_porcupine|c,t,x,an,ap,bc
adult_male_tasmanian_devil|a,i,m,w,an,ap,au
adult_male_bald_eagle|a,d,k,m,s,u,z,ai
adult_female_pelican|a,f,k,m,s,t,u,ai,bh
juvenile_female_reindeer|e,t,w,x,aa,an,at
adult_male_mountain_goat|a,d,n,w,x,aa,ac,an,ao,bj
adult_male_sperm_whale|a,f,m,p,v,ad,an
juvenile_female_striped_skunk|d,t,w,an,ap,aq,be,bf
adult_male_king_cobra|a,h,m,y,ai,aj,av,ax,bi
juvenile_male_jaguar|d,f,m,w,an,bd
juvenile_male_silky_anteater|d,n,w,af,am,an,ap
adult_female_blue_whale|a,f,j,t,v,ad,an
adult_male_baboon|a,c,w,am,an,aq,ar
juvenile_male_flamingo|f,k,s,u,ai,al,as
juvenile_male_barn_owl|k,m,s,u,ai,ap,az
juvenile_female_rabbit|l,q,t,w,x,ab,ah,an
adult_female_lion|a,b,c,m,t,w,ag,an,ar
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

Win. 8 counted questions. Return 0.76.
[Source archive](../results/main_A11/games.jsonl.gz).

### Action 1

~~~text
ASK: (adult AND (w OR x))
~~~

Environment reply

~~~text
NO
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_male_crocodile","adult_female_llama","juvenile_female_mountain_goat","adult_male_virginia_opossum","juvenile_male_chinchilla","adult_female_bactrian_camel","juvenile_male_parrot","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_manatee","adult_female_gibbon","adult_female_humpback_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","juvenile_female_crested_porcupine","adult_male_tasmanian_devil","adult_male_bald_eagle","adult_female_pelican","juvenile_female_reindeer","adult_male_mountain_goat","adult_male_sperm_whale","juvenile_female_striped_skunk","adult_male_king_cobra","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_female_blue_whale","adult_male_baboon","juvenile_male_flamingo","juvenile_male_barn_owl","juvenile_female_rabbit","adult_female_lion"]
TOP CANDIDATE: adult_male_crocodile
~~~

### Action 2

~~~text
ASK: (t AND (w OR x))
~~~

Environment reply

~~~text
NO
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_male_crocodile","juvenile_female_mountain_goat","adult_male_virginia_opossum","juvenile_male_chinchilla","juvenile_male_parrot","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_manatee","adult_female_humpback_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","juvenile_female_crested_porcupine","adult_male_tasmanian_devil","adult_male_bald_eagle","adult_female_pelican","juvenile_female_reindeer","adult_male_mountain_goat","adult_male_sperm_whale","juvenile_female_striped_skunk","adult_male_king_cobra","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_female_blue_whale","adult_male_baboon","juvenile_male_flamingo","juvenile_male_barn_owl","juvenile_female_rabbit"]
TOP CANDIDATE: adult_male_crocodile
~~~

### Action 3

~~~text
ASK: (m AND (w OR x))
~~~

Environment reply

~~~text
YES
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_male_crocodile","juvenile_female_mountain_goat","adult_male_virginia_opossum","juvenile_male_chinchilla","juvenile_male_parrot","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_manatee","adult_female_humpback_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","juvenile_female_crested_porcupine","adult_male_tasmanian_devil","adult_male_bald_eagle","adult_female_pelican","juvenile_female_reindeer","adult_male_mountain_goat","adult_male_sperm_whale","juvenile_female_striped_skunk","adult_male_king_cobra","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_female_blue_whale","adult_male_baboon","juvenile_male_flamingo","juvenile_male_barn_owl","juvenile_female_rabbit","adult_female_lion"]
TOP CANDIDATE: juvenile_male_spotted_hyena
~~~

### Action 4

~~~text
ASK: (an AND (w OR x))
~~~

Environment reply

~~~text
YES
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_male_crocodile","juvenile_female_mountain_goat","adult_male_virginia_opossum","juvenile_male_chinchilla","juvenile_male_parrot","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_manatee","adult_female_humpback_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","juvenile_female_crested_porcupine","adult_male_tasmanian_devil","adult_male_bald_eagle","adult_female_pelican","juvenile_female_reindeer","adult_male_mountain_goat","adult_male_sperm_whale","juvenile_female_striped_skunk","adult_male_king_cobra","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_female_blue_whale","adult_male_baboon","juvenile_male_flamingo","juvenile_male_barn_owl","juvenile_female_rabbit","adult_female_lion"]
TOP CANDIDATE: juvenile_male_spotted_hyena
~~~

### Action 5

~~~text
ASK: (ar AND (w OR x))
~~~

Environment reply

~~~text
YES
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_male_crocodile","juvenile_female_mountain_goat","adult_male_virginia_opossum","juvenile_male_chinchilla","juvenile_male_parrot","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_manatee","adult_female_humpback_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","juvenile_female_crested_porcupine","adult_male_tasmanian_devil","adult_male_bald_eagle","adult_female_pelican","juvenile_female_reindeer","adult_male_mountain_goat","adult_male_sperm_whale","juvenile_female_striped_skunk","adult_male_king_cobra","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_female_blue_whale","adult_male_baboon","juvenile_male_flamingo","juvenile_male_barn_owl","juvenile_female_rabbit","adult_female_lion"]
TOP CANDIDATE: juvenile_male_spotted_hyena
~~~

### Action 6

~~~text
ASK: (aj AND (w OR x))
~~~

Environment reply

~~~text
YES
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_male_crocodile","juvenile_female_mountain_goat","adult_male_virginia_opossum","juvenile_male_chinchilla","juvenile_male_parrot","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_manatee","adult_female_humpback_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","juvenile_female_crested_porcupine","adult_male_tasmanian_devil","adult_male_bald_eagle","adult_female_pelican","juvenile_female_reindeer","adult_male_mountain_goat","adult_male_sperm_whale","juvenile_female_striped_skunk","adult_male_king_cobra","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_female_blue_whale","adult_male_baboon","juvenile_male_flamingo","juvenile_male_barn_owl","juvenile_female_rabbit","adult_female_lion"]
TOP CANDIDATE: juvenile_male_spotted_hyena
~~~

The recorded answer was flipped. This annotation was private.

### Action 7

~~~text
ASK: (aq AND (w OR x))
~~~

Environment reply

~~~text
NO
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_male_crocodile","juvenile_female_mountain_goat","adult_male_virginia_opossum","juvenile_male_chinchilla","juvenile_male_parrot","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_manatee","adult_female_humpback_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","juvenile_female_crested_porcupine","adult_male_tasmanian_devil","adult_male_bald_eagle","adult_female_pelican","juvenile_female_reindeer","adult_male_mountain_goat","adult_male_sperm_whale","adult_male_king_cobra","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_female_blue_whale","adult_male_baboon","juvenile_male_flamingo","juvenile_male_barn_owl","juvenile_female_rabbit","adult_female_lion"]
TOP CANDIDATE: juvenile_male_spotted_hyena
~~~

### Action 8

~~~text
ASK: (bd AND (w OR x))
~~~

Environment reply

~~~text
YES
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["juvenile_male_chinchilla","juvenile_male_manatee","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","adult_male_tasmanian_devil","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_female_lion"]
TOP CANDIDATE: juvenile_male_spotted_hyena
~~~

### Action 9

~~~text
GUESS: juvenile_male_spotted_hyena
~~~

Environment reply

~~~text
WIN
~~~

## A11 game

Loss. 8 counted questions. Return -0.24.
[Source archive](../results/main_A11/games.jsonl.gz).

[Opening prompt and table](#opening-prompt).

### Action 1

~~~text
ASK: w
~~~

Environment reply

~~~text
YES
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_male_crocodile","adult_female_llama","juvenile_female_mountain_goat","adult_male_virginia_opossum","juvenile_male_chinchilla","adult_female_bactrian_camel","juvenile_male_parrot","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_manatee","adult_female_gibbon","adult_female_humpback_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","juvenile_female_crested_porcupine","adult_male_tasmanian_devil","adult_male_bald_eagle","adult_female_pelican","juvenile_female_reindeer","adult_male_mountain_goat","adult_male_sperm_whale","juvenile_female_striped_skunk","adult_male_king_cobra","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_female_blue_whale","adult_male_baboon","juvenile_male_flamingo","juvenile_male_barn_owl","juvenile_female_rabbit","adult_female_lion"]
TOP CANDIDATE: adult_female_llama
~~~

### Action 2

~~~text
ASK: t
~~~

Environment reply

~~~text
NO
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_male_crocodile","adult_female_llama","juvenile_female_mountain_goat","adult_male_virginia_opossum","juvenile_male_chinchilla","adult_female_bactrian_camel","juvenile_male_parrot","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_manatee","adult_female_gibbon","adult_female_humpback_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","juvenile_female_crested_porcupine","adult_male_tasmanian_devil","adult_male_bald_eagle","adult_female_pelican","juvenile_female_reindeer","adult_male_mountain_goat","adult_male_sperm_whale","juvenile_female_striped_skunk","adult_male_king_cobra","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_female_blue_whale","adult_male_baboon","juvenile_male_flamingo","juvenile_male_barn_owl","juvenile_female_rabbit","adult_female_lion"]
TOP CANDIDATE: adult_male_virginia_opossum
~~~

### Action 3

~~~text
ASK: x
~~~

Environment reply

~~~text
NO
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_male_crocodile","adult_female_llama","juvenile_female_mountain_goat","adult_male_virginia_opossum","juvenile_male_chinchilla","adult_female_bactrian_camel","juvenile_male_parrot","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_manatee","adult_female_gibbon","adult_female_humpback_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","adult_male_tasmanian_devil","adult_male_bald_eagle","adult_female_pelican","juvenile_female_reindeer","adult_male_mountain_goat","adult_male_sperm_whale","juvenile_female_striped_skunk","adult_male_king_cobra","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_female_blue_whale","adult_male_baboon","juvenile_male_flamingo","juvenile_male_barn_owl","juvenile_female_rabbit","adult_female_lion"]
TOP CANDIDATE: adult_male_virginia_opossum
~~~

### Action 4

~~~text
ASK: n
~~~

Environment reply

~~~text
NO
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_male_crocodile","adult_female_llama","adult_male_virginia_opossum","juvenile_male_chinchilla","adult_female_bactrian_camel","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_manatee","adult_female_humpback_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","adult_male_tasmanian_devil","adult_male_bald_eagle","adult_female_pelican","juvenile_female_reindeer","adult_male_mountain_goat","adult_male_sperm_whale","juvenile_female_striped_skunk","adult_male_king_cobra","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_female_blue_whale","adult_male_baboon","juvenile_male_flamingo","juvenile_male_barn_owl","juvenile_female_rabbit","adult_female_lion"]
TOP CANDIDATE: juvenile_male_spotted_hyena
~~~

### Action 5

~~~text
ASK: m
~~~

Environment reply

~~~text
YES
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_male_crocodile","adult_male_virginia_opossum","juvenile_male_chinchilla","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","adult_male_tasmanian_devil","adult_male_bald_eagle","adult_female_pelican","adult_male_sperm_whale","juvenile_female_striped_skunk","adult_male_king_cobra","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_male_baboon","juvenile_male_flamingo","juvenile_male_barn_owl","adult_female_lion"]
TOP CANDIDATE: juvenile_male_spotted_hyena
~~~

### Action 6

~~~text
ASK: an
~~~

Environment reply

~~~text
NO
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_male_crocodile","adult_male_virginia_opossum","juvenile_male_chinchilla","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","adult_male_tasmanian_devil","adult_male_bald_eagle","adult_female_pelican","adult_male_sperm_whale","juvenile_female_striped_skunk","adult_male_king_cobra","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_male_baboon","juvenile_male_flamingo","juvenile_male_barn_owl","adult_female_lion"]
TOP CANDIDATE: adult_male_crocodile
~~~

The recorded answer was flipped. This annotation was private.

### Action 7

~~~text
ASK: ao
~~~

Environment reply

~~~text
NO
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_male_crocodile","adult_male_virginia_opossum","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","adult_male_tasmanian_devil","adult_male_bald_eagle","adult_female_pelican","adult_male_sperm_whale","juvenile_female_striped_skunk","adult_male_king_cobra","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_male_baboon","juvenile_male_flamingo","juvenile_male_barn_owl","adult_female_lion"]
TOP CANDIDATE: adult_male_crocodile
~~~

### Action 8

~~~text
ASK: ac
~~~

Environment reply

~~~text
NO
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_male_crocodile","adult_male_virginia_opossum","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","adult_male_tasmanian_devil","adult_male_bald_eagle","adult_female_pelican","adult_male_sperm_whale","juvenile_female_striped_skunk","adult_male_king_cobra","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_male_baboon","juvenile_male_flamingo","juvenile_male_barn_owl","adult_female_lion"]
TOP CANDIDATE: adult_male_crocodile
~~~

### Action 9

~~~text
GUESS: adult_male_crocodile
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
ASK: an
~~~

Environment reply

~~~text
YES
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_male_crocodile","adult_female_llama","juvenile_female_mountain_goat","adult_male_virginia_opossum","juvenile_male_chinchilla","adult_female_bactrian_camel","juvenile_male_parrot","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_manatee","adult_female_gibbon","adult_female_humpback_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","juvenile_female_crested_porcupine","adult_male_tasmanian_devil","adult_male_bald_eagle","adult_female_pelican","juvenile_female_reindeer","adult_male_mountain_goat","adult_male_sperm_whale","juvenile_female_striped_skunk","adult_male_king_cobra","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_female_blue_whale","adult_male_baboon","juvenile_male_flamingo","juvenile_male_barn_owl","juvenile_female_rabbit","adult_female_lion"]
TOP CANDIDATE: adult_female_llama
~~~

### Action 2

~~~text
ASK: t
~~~

Environment reply

~~~text
NO
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_male_crocodile","adult_female_llama","juvenile_female_mountain_goat","adult_male_virginia_opossum","juvenile_male_chinchilla","adult_female_bactrian_camel","juvenile_male_parrot","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_manatee","adult_female_gibbon","adult_female_humpback_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","juvenile_female_crested_porcupine","adult_male_tasmanian_devil","adult_male_bald_eagle","juvenile_female_reindeer","adult_male_mountain_goat","adult_male_sperm_whale","juvenile_female_striped_skunk","adult_male_king_cobra","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_female_blue_whale","adult_male_baboon","juvenile_male_flamingo","juvenile_male_barn_owl","juvenile_female_rabbit","adult_female_lion"]
TOP CANDIDATE: adult_male_virginia_opossum
~~~

### Action 3

~~~text
ASK: w
~~~

Environment reply

~~~text
YES
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_male_crocodile","adult_female_llama","juvenile_female_mountain_goat","adult_male_virginia_opossum","juvenile_male_chinchilla","adult_female_bactrian_camel","juvenile_male_parrot","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_manatee","adult_female_gibbon","adult_female_humpback_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","juvenile_female_crested_porcupine","adult_male_tasmanian_devil","adult_male_bald_eagle","juvenile_female_reindeer","adult_male_mountain_goat","adult_male_sperm_whale","juvenile_female_striped_skunk","adult_male_king_cobra","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_female_blue_whale","adult_male_baboon","juvenile_male_flamingo","juvenile_male_barn_owl","juvenile_female_rabbit","adult_female_lion"]
TOP CANDIDATE: adult_male_virginia_opossum
~~~

### Action 4

~~~text
ASK: x
~~~

Environment reply

~~~text
NO
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_male_crocodile","adult_female_llama","juvenile_female_mountain_goat","adult_male_virginia_opossum","juvenile_male_chinchilla","adult_female_bactrian_camel","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_manatee","adult_female_gibbon","adult_female_humpback_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","adult_male_tasmanian_devil","adult_male_bald_eagle","juvenile_female_reindeer","adult_male_mountain_goat","adult_male_sperm_whale","juvenile_female_striped_skunk","adult_male_king_cobra","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_female_blue_whale","adult_male_baboon","juvenile_male_flamingo","juvenile_male_barn_owl","juvenile_female_rabbit","adult_female_lion"]
TOP CANDIDATE: adult_male_virginia_opossum
~~~

### Action 5

~~~text
ASK: an
~~~

Environment reply

~~~text
YES
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_female_llama","juvenile_female_mountain_goat","adult_male_virginia_opossum","juvenile_male_chinchilla","adult_female_bactrian_camel","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_manatee","adult_female_gibbon","adult_female_humpback_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","adult_male_tasmanian_devil","juvenile_female_reindeer","adult_male_mountain_goat","adult_male_sperm_whale","juvenile_female_striped_skunk","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_female_blue_whale","adult_male_baboon","juvenile_female_rabbit","adult_female_lion"]
TOP CANDIDATE: adult_male_virginia_opossum
~~~

### Action 6

~~~text
ASK: aa
~~~

Environment reply

~~~text
YES
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_female_llama","juvenile_female_mountain_goat","adult_male_virginia_opossum","juvenile_male_chinchilla","adult_female_bactrian_camel","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_manatee","adult_female_gibbon","adult_female_humpback_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","adult_male_tasmanian_devil","juvenile_female_reindeer","adult_male_mountain_goat","adult_male_sperm_whale","juvenile_female_striped_skunk","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_female_blue_whale","adult_male_baboon","juvenile_female_rabbit","adult_female_lion"]
TOP CANDIDATE: adult_male_virginia_opossum
~~~

The recorded answer was flipped. This annotation was private.

### Action 7

~~~text
ASK: ap
~~~

Environment reply

~~~text
NO
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_female_llama","juvenile_female_mountain_goat","adult_male_virginia_opossum","juvenile_male_chinchilla","adult_female_bactrian_camel","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_manatee","adult_female_gibbon","adult_female_humpback_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","adult_male_tasmanian_devil","juvenile_female_reindeer","adult_male_mountain_goat","adult_male_sperm_whale","juvenile_female_striped_skunk","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_female_blue_whale","adult_male_baboon","juvenile_female_rabbit","adult_female_lion"]
TOP CANDIDATE: juvenile_male_ring_tailed_lemur
~~~

### Action 8

~~~text
ASK: ag
~~~

Environment reply

~~~text
NO
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_female_llama","juvenile_female_mountain_goat","adult_male_virginia_opossum","juvenile_male_chinchilla","adult_female_bactrian_camel","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_manatee","adult_female_gibbon","adult_female_humpback_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","adult_male_tasmanian_devil","juvenile_female_reindeer","adult_male_mountain_goat","adult_male_sperm_whale","juvenile_female_striped_skunk","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_female_blue_whale","adult_male_baboon","juvenile_female_rabbit","adult_female_lion"]
TOP CANDIDATE: juvenile_male_ring_tailed_lemur
~~~

### Action 9

~~~text
ASK: an
~~~

Environment reply

~~~text
YES
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_female_llama","juvenile_female_mountain_goat","adult_male_virginia_opossum","juvenile_male_chinchilla","adult_female_bactrian_camel","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_manatee","adult_female_gibbon","adult_female_humpback_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","adult_male_tasmanian_devil","juvenile_female_reindeer","adult_male_mountain_goat","adult_male_sperm_whale","juvenile_female_striped_skunk","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_female_blue_whale","adult_male_baboon","juvenile_female_rabbit","adult_female_lion"]
TOP CANDIDATE: juvenile_male_ring_tailed_lemur
~~~

### Action 10

~~~text
ASK: n
~~~

Environment reply

~~~text
NO
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_female_llama","juvenile_female_mountain_goat","adult_male_virginia_opossum","juvenile_male_chinchilla","adult_female_bactrian_camel","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_manatee","adult_female_humpback_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","adult_male_tasmanian_devil","juvenile_female_reindeer","adult_male_mountain_goat","adult_male_sperm_whale","juvenile_female_striped_skunk","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_female_blue_whale","adult_male_baboon","juvenile_female_rabbit","adult_female_lion"]
TOP CANDIDATE: juvenile_male_spotted_hyena
~~~

### Action 11

~~~text
ASK: m
~~~

Environment reply

~~~text
LOSS
~~~

## B41 game

Loss. 6 counted questions. Return -0.18.
[Source archive](../results/main_B41/games.jsonl.gz).

[Opening prompt and table](#opening-prompt).

### Action 1

~~~text
ASK: an
~~~

Environment reply

~~~text
YES
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_male_crocodile","adult_female_llama","juvenile_female_mountain_goat","adult_male_virginia_opossum","juvenile_male_chinchilla","adult_female_bactrian_camel","juvenile_male_parrot","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_manatee","adult_female_gibbon","adult_female_humpback_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","juvenile_female_crested_porcupine","adult_male_tasmanian_devil","adult_male_bald_eagle","adult_female_pelican","juvenile_female_reindeer","adult_male_mountain_goat","adult_male_sperm_whale","juvenile_female_striped_skunk","adult_male_king_cobra","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_female_blue_whale","adult_male_baboon","juvenile_male_flamingo","juvenile_male_barn_owl","juvenile_female_rabbit","adult_female_lion"]
TOP CANDIDATE: adult_female_llama
~~~

### Action 2

~~~text
ASK: w
~~~

Environment reply

~~~text
YES
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_female_llama","juvenile_female_mountain_goat","adult_male_virginia_opossum","juvenile_male_chinchilla","adult_female_bactrian_camel","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_manatee","adult_female_gibbon","adult_female_humpback_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","juvenile_female_crested_porcupine","adult_male_tasmanian_devil","juvenile_female_reindeer","adult_male_mountain_goat","adult_male_sperm_whale","juvenile_female_striped_skunk","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_female_blue_whale","adult_male_baboon","juvenile_female_rabbit","adult_female_lion"]
TOP CANDIDATE: adult_female_llama
~~~

### Action 3

~~~text
ASK: t
~~~

Environment reply

~~~text
NO
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_male_crocodile","adult_female_llama","juvenile_female_mountain_goat","adult_male_virginia_opossum","juvenile_male_chinchilla","adult_female_bactrian_camel","juvenile_male_parrot","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_manatee","adult_female_gibbon","adult_female_humpback_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","juvenile_female_crested_porcupine","adult_male_tasmanian_devil","adult_male_bald_eagle","juvenile_female_reindeer","adult_male_mountain_goat","adult_male_sperm_whale","juvenile_female_striped_skunk","adult_male_king_cobra","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_female_blue_whale","adult_male_baboon","juvenile_male_flamingo","juvenile_male_barn_owl","juvenile_female_rabbit","adult_female_lion"]
TOP CANDIDATE: adult_male_virginia_opossum
~~~

### Action 4

~~~text
ASK: x
~~~

Environment reply

~~~text
NO
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_male_crocodile","adult_female_llama","juvenile_female_mountain_goat","adult_male_virginia_opossum","juvenile_male_chinchilla","adult_female_bactrian_camel","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_manatee","adult_female_gibbon","adult_female_humpback_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","adult_male_tasmanian_devil","adult_male_bald_eagle","juvenile_female_reindeer","adult_male_mountain_goat","adult_male_sperm_whale","juvenile_female_striped_skunk","adult_male_king_cobra","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_female_blue_whale","adult_male_baboon","juvenile_male_flamingo","juvenile_male_barn_owl","juvenile_female_rabbit","adult_female_lion"]
TOP CANDIDATE: adult_male_virginia_opossum
~~~

### Action 5

~~~text
ASK: an
~~~

Environment reply

~~~text
YES
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_female_llama","juvenile_female_mountain_goat","adult_male_virginia_opossum","juvenile_male_chinchilla","adult_female_bactrian_camel","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_manatee","adult_female_gibbon","adult_female_humpback_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","adult_male_tasmanian_devil","juvenile_female_reindeer","adult_male_mountain_goat","adult_male_sperm_whale","juvenile_female_striped_skunk","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_female_blue_whale","adult_male_baboon","juvenile_female_rabbit","adult_female_lion"]
TOP CANDIDATE: adult_male_virginia_opossum
~~~

### Action 6

~~~text
ASK: aa
~~~

Environment reply

~~~text
YES
POSTERIOR CANDIDATES (probability > 0.001, plus top): ["adult_female_llama","juvenile_female_mountain_goat","adult_male_virginia_opossum","juvenile_male_chinchilla","adult_female_bactrian_camel","juvenile_male_ring_tailed_lemur","juvenile_female_sperm_whale","juvenile_male_manatee","adult_female_gibbon","adult_female_humpback_whale","juvenile_male_spotted_hyena","juvenile_female_fennec_fox","juvenile_female_cheetah","adult_male_tasmanian_devil","juvenile_female_reindeer","adult_male_mountain_goat","adult_male_sperm_whale","juvenile_female_striped_skunk","juvenile_male_jaguar","juvenile_male_silky_anteater","adult_female_blue_whale","adult_male_baboon","juvenile_female_rabbit","adult_female_lion"]
TOP CANDIDATE: adult_male_virginia_opossum
~~~

The recorded answer was flipped. This annotation was private.

### Action 7

~~~text
GUESS: adult_male_virginia_opossum
~~~

Environment reply

~~~text
LOSS
~~~
