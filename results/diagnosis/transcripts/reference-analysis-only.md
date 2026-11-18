# Saved Phase 2 transcript: reference analysis truncation

Model: `openai/gpt-oss-120b`. Game: `paid-v1/animals/32/0/p0`.

Target, revealed for diagnosis only: `juvenile_male_aardvark`.

The complete public chat and raw generated responses follow. No action text is shortened. Diagnostics after each response are private analysis and were not fed back to the policy.

## Actual rendered initial prompt

This includes native role markers and any template-provided system header.

````text
<|start|>system<|message|>You are ChatGPT, a large language model trained by OpenAI.
Knowledge cutoff: 2024-06
Current date: 2026-11-18

Reasoning: medium

# Valid channels: analysis, commentary, final. Channel must be included for every message.<|end|><|start|>developer<|message|># Instructions

You play Twenty Questions. Identify one hidden item from the table. After each item name, the listed column codes are true; every omitted code is false. Use full attribute names from the code=name mapping in questions. The table defines truth, even if your world knowledge differs. Output exactly one line: ASK: <Boolean expression> or GUESS: <exact item name>. Expressions use attribute identifiers, AND, OR, NOT, parentheses, and item == <item name>. Quote names containing spaces with JSON double quotes. A wrong guess ends the game. An invalid question costs a question. You may use any legal Boolean expression, including lists of item equalities. Do not explain or show reasoning.
DOMAIN animals
ATTRIBUTES code=name
a=adult,b=africa,c=america,d=aquatic,e=armor,f=asia,g=australia,h=bird,i=burrows,j=carnivore,k=climbs,l=desert,m=echolocates,n=europe,o=feathers,p=female,q=flat_tail,r=flies,s=flippers,t=floats,u=fur,v=herbivore,w=hood,x=hooves,y=hops,z=horn,aa=horns,ab=huge,ac=insectivore,ad=large,ae=large_beak,af=large_ears,ag=lays_eggs,ah=limbless,ai=long_arms,aj=long_snout,ak=loud,al=mammal,am=mountains,an=nocturnal,ao=omnivore,ap=packs,aq=polar,ar=pouch,as=prehensile_tail,at=reptile,au=ringed_tail,av=scales,aw=silent,ax=slow,ay=spines,az=spots,ba=spray,bb=stripes,bc=tusks,bd=venomous,be=webbed,bf=white
TABLE name|true column codes
adult_female_fennec_fox|a,b,i,j,l,p,u,af,al,an
juvenile_female_crested_porcupine|b,p,v,al,an,ay
adult_female_red_fox|a,i,j,n,p,u,al,an
juvenile_male_spider_monkey|c,k,u,al,ao,as
juvenile_female_rabbit|i,n,p,u,v,y,af,al
adult_male_walrus|a,d,j,s,al,aq,bc
adult_female_manatee|a,d,p,s,v,al,ax
adult_male_striped_skunk|a,c,u,al,an,ao,ba,bb
juvenile_female_red_panda|f,k,p,u,v,al,au
juvenile_female_snow_leopard|f,j,k,p,u,al,am,az
juvenile_male_komodo_dragon|f,j,ad,ag,at,av,bd
juvenile_female_white_rhinoceros|b,e,p,v,z,ab,al
juvenile_male_aardvark|b,i,u,ac,aj,al,an
adult_female_zebra|a,b,p,u,v,x,ad,al,bb
juvenile_male_crested_porcupine|b,v,al,an,ay
juvenile_female_ring_tailed_lemur|b,k,p,u,al,ao,au
juvenile_female_beaver|d,n,p,q,u,v,al,be
adult_male_ring_tailed_lemur|a,b,k,u,al,ao,au
juvenile_female_sperm_whale|d,j,m,p,s,ab,al
adult_male_capybara|a,c,d,u,v,ad,al,be
juvenile_male_barn_owl|h,j,o,r,ag,an,aw
adult_male_sea_otter|a,c,d,j,t,u,al
juvenile_male_platypus|d,g,u,ag,al,bd,be
juvenile_female_silky_anteater|c,k,p,u,ac,aj,al,an
juvenile_male_howler_monkey|c,k,u,v,ak,al,as
adult_female_baboon|a,b,p,u,aj,al,ao,ap
juvenile_female_mountain_goat|c,k,p,u,v,x,aa,al,am,bf
adult_female_toucan|a,c,h,o,p,r,v,ae,ag
adult_female_snow_leopard|a,f,j,k,p,u,al,am,az
adult_male_king_cobra|a,f,j,w,ag,ah,at,av,bd
adult_female_orangutan|a,f,k,p,u,v,ai,al
adult_male_virginia_opossum|a,c,k,u,al,an,ar
END TABLE


<|end|><|start|>user<|message|>Answer flip probability: 0.00, independently each question. Maximum questions: 10. After the last answer, make one final guess; another question loses. Begin.<|end|><|start|>assistant
````

## Turn 1: generated response

````text
<|channel|>analysis<|message|>We need to ask a Boolean expression to narrow down. We can directly guess? But we have up to 10 questions. Better to ask about attributes that split.

We need to output ASK: <expr>. The system will respond with true/false? Not given yet, but we need to ask.

We need to consider the table items. Let's list items with their true codes.

I'll enumerate items (name) and codes:

1. adult_female_fennec_fox: a,b,i,j,l,p,u,af,al,an
2. juvenile_female_crested_porcupine: b,p,v,al,an,ay
3. adult_female_red_fox: a,i,j,n,p,u,al,an
4. juvenile_male_spider_monkey: c,k,u,al,ao,as
5. juvenile_female_rabbit: i,n,p,u,v,y,af,al
6. adult_male_walrus: a,d,j,s,al,aq,bc
7. adult_female_manatee: a,d,p,s,v,al,ax
8. adult_male_striped_skunk: a,c,u,al,an,ao,ba,bb
9. juvenile_female_red_panda: f,k,p,u,v,al,au
10. juvenile_female_snow_leopard: f,j,k,p,u,al,am,az
11. juvenile_male_komodo_dragon: f,j,ad,ag,at,av,bd
12. juvenile_female_white_rhinoceros: b,e,p,v,z,ab,al
13. juvenile_male_aardvark: b,i,u,ac,aj,al,an
14. adult_female_zebra: a,b,p,u,v,x,ad,al,bb
15. juvenile_male_crested_porcupine: b,v,al,an,ay
16. juvenile_female_ring_tailed_lemur: b,k,p,u,al,ao,au
17. juvenile_female_beaver: d,n,p,q,u,v,al,be
18. adult_male_ring_tailed_lemur: a,b,k,u,al,ao,au
19. juvenile_female_sperm_whale: d,j,m,p,s,ab,al
20. adult_male_capybara: a,c,d,u,v,ad,al,be

````

Action decoded by the adapter:

````text

````

Answer delivered to the model:

````text
INVALID
````

Private diagnostic: EIG 0.000000000; truncated True; error `Expected one ASK or GUESS line.`.

## Turn 2: generated response

````text
<|channel|>analysis<|message|>We need to ask a Boolean expression question. Use ASK: <expr>. Need to formulate a question that is true for some items. We have up to 10 questions. We need to identify hidden item. We don't know which item is hidden, but we can ask questions to narrow.

We need to output ASK: expression. The system will respond with True/False? Actually we are playing with the system: after each ASK, we get answer? The prompt says after each item name, column codes are true; omitted false. We can ask any Boolean expression using attribute identifiers and item == name. The system will answer presumably with True/False. We need to deduce hidden item within 10 questions then guess.

We need to start with a question.

We need to consider attributes.

Let's list items and their attributes (true codes). We'll need to identify hidden.

List items (name) and attributes:

1 adult_female_fennec_fox: a,b,i,j,l,p,u,af,al,an
2 juvenile_female_crested_porcupine: b,p,v,al,an,ay
3 adult_female_red_fox: a,i,j,n,p,u,al,an
4 juvenile_male_spider_monkey: c,k,u,al,ao,as
5 juvenile_female_rabbit: i,n,p,u,v,y,af,al
6 adult_male_walrus: a,d,j,s,al,aq,bc
7 adult_female_manatee: a,d,p,s,v,al,ax
8 adult_male_striped_skunk: a,c,u,al,an,ao,ba,bb
9 juvenile_female_red_panda: f,k,p,u,v,al,au
10 juvenile_female_snow_leopard: f,j,k,p,u,al,am,az
11 juvenile_male_komodo_dragon: f,j,ad,ag,at,av,bd
12 juvenile_female_white_rhinoceros: b,e,p,v,z,ab,al
13 juvenile_male_aardvark: b,i,u,ac,aj,al,an
14 adult_female_zebra: a,b,p,u,v,x,ad,al,bb
15 juvenile_male_crested_porcupine: b,v,al,an,ay
16 juvenile_female_ring_tailed_lemur: b,k,p,u,al,ao,au
17 juvenile
````

Action decoded by the adapter:

````text

````

Answer delivered to the model:

````text
INVALID
````

Private diagnostic: EIG 0.000000000; truncated True; error `Expected one ASK or GUESS line.`.

## Turn 3: generated response

````text
<|channel|>analysis<|message|>We need to play Twenty Questions. We have a table of items with attributes (codes). We must ask boolean expressions. The system says answer flip probability 0.00, i.e., deterministic answers. Max 10 questions, then final guess.

We need to identify the hidden item. We don't know which one. We can ask questions that narrow down. Use attribute names in full (like adult, africa, etc.) The mapping given: code=name, e.g., a=adult, b=africa, etc.

We need to output ASK: <Boolean expression>. The answer will be true/false from system? Actually we as ChatGPT must output question, then system will respond? The conversation hasn't done that. We need to ask a question now.

We must use attribute identifiers (full names) in expression, not codes. So need to use "adult", "africa", etc. Also can use item == "name". The expression must be valid.

We need to formulate a question that splits possibilities. Let's list items.

I'll list items with attributes:

1 adult_female_fennec_fox: adult, africa, america?, Actually code a,b,i,j,l,p,u,af,al,an. So attributes: adult, africa, america? Wait code i=burrows, j=carnivore, l=desert, p=female, u=fur, af=large_ears, al=mammal, an=nocturnal. Also b=africa. So not america. So include africa, burrows, carnivore, desert, female, fur, large_ears, mammal, nocturnal.

2 juvenile_female_crested_porcupine: b,p,v,al,an,ay. So africa, female, herbivore, mammal, nocturnal, spines.

3 adult_female_red_fox: a,i,j,n,p,u,al,an. adult, burrows, carnivore, no? n=climbs, female, fur, mammal, nocturnal.

4 juvenile_male_spider_monkey: c,k,u,al,ao,as. america, carnivore?, Actually k=climbs, u=fur, al=mammal, ao=omnivore, as=prehensile_tail. Also c=america.

5 juvenile_female_rabbit: i,n,p,u,v,y,af,al. burrows, climbs, female, fur, herbivore, hops, large_ears
````

Action decoded by the adapter:

````text

````

Answer delivered to the model:

````text
INVALID
````

Private diagnostic: EIG 0.000000000; truncated True; error `Expected one ASK or GUESS line.`.

## Turn 4: generated response

````text
<|channel|>analysis<|message|>We need to play Twenty Questions. The user gave "Answer flip probability: 0.00, independently each question. Maximum questions: 10. After the last answer, make one final guess; another question loses. Begin."

We need to ask a question in the required format: "ASK: <Boolean expression>" using attribute identifiers and possibly item equality. We can ask up to 10 questions, but we need to produce a single line per turn. We should ask a question that narrows down items.

We need to follow the rule: After each item name, the listed column codes are true; every omitted code is false. So each row defines the set of true attributes for that item. The attribute codes are given.

We need to output exactly one line: ASK: <Boolean expression> or GUESS: <exact item name>.

We need to ask a valid Boolean expression referencing attribute identifiers (like a, b, etc.) and item == <item name>. The expression must be evaluable true/false based on the hidden item.

We need to decide a good first question.

We have many items. Let's list names and attributes:

1 adult_female_fennec_fox: a,b,i,j,l,p,u,af,al,an

2 juvenile_female_crested_porcupine: b,p,v,al,an,ay

3 adult_female_red_fox: a,i,j,n,p,u,al,an

4 juvenile_male_spider_monkey: c,k,u,al,ao,as

5 juvenile_female_rabbit: i,n,p,u,v,y,af,al

6 adult_male_walrus: a,d,j,s,al,aq,bc

7 adult_female_manatee: a,d,p,s,v,al,ax

8 adult_male_striped_skunk: a,c,u,al,an,ao,ba,bb

9 juvenile_female_red_panda: f,k,p,u,v,al,au

10 juvenile_female_snow_leopard: f,j,k,p,u,al,am,az

11 juvenile_male_komodo_dragon: f,j,ad,ag,at,av,bd

12 juvenile_female_white_rhinoceros: b,e,p,v,z,ab,al

13 juvenile_male_aardvark: b,i,u,ac,aj,al,an

14 adult_female_zebra: a,b,p,u,v,x,ad
````

Action decoded by the adapter:

````text

````

Answer delivered to the model:

````text
INVALID
````

Private diagnostic: EIG 0.000000000; truncated True; error `Expected one ASK or GUESS line.`.

## Turn 5: generated response

````text
<|channel|>analysis<|message|>The user gave "Answer flip probability: 0.00, independently each question. Maximum questions: 10. After the last answer, make one final guess; another question loses. Begin."

We are playing Twenty Questions. We must output ASK: boolean expression or GUESS. We need to ask questions. We have up to 10 questions. The user wants us to begin asking. The rules: each line we output either ASK: <expr> or GUESS: <item>. No explanation.

We need to construct questions to narrow down. Let's see the items list. Items: many. We need to identify hidden item. The hidden item is unknown to us; we can ask about attributes. The table defines truth for each item. Our questions must be boolean expressions referencing attribute identifiers (like a, b, etc) or item== name. We can combine with AND, OR, NOT, parentheses.

We need to ask a question like ASK: a AND b etc. The system will respond? Actually the user is not responding yet. We need to ask a question. So we output an ASK line. Then user will answer? The prompt says after each item name, listed column codes are true; omitted false. We can ask about attributes. So we need to ask a question that the system can answer yes/no? Probably they will answer true/false. So we need to ask a question.

We need to start with a broad question. Let's think: maybe ask about "a" (adult). Many are adult or juvenile. Let's count items: Many have a (adult). So ask ASK: a. That will get yes/no. Let's do that.

So first output: ASK: a.<|end|><|start|>assistant<|channel|>final<|message|>ASK: a<|return|>
````

Action decoded by the adapter:

````text
ASK: a
````

Answer delivered to the model:

````text
INVALID
````

Private diagnostic: EIG 0.000000000; truncated False; error `Unknown attribute: a`.

## Turn 6: generated response

````text
<|channel|>analysis<|message|>The user is playing Twenty Questions. The system gave instructions to output exactly one line: ASK: <Boolean expression> or GUESS: <exact item name>. They gave "Answer flip probability: 0.00, independently each question. Maximum questions: 10. After the last answer, make one final guess; another question loses." So we need to ask a Boolean expression to get answer from system. The user says "INVALID" multiple times. We need to respond with a valid ASK expression. We haven't asked any question yet. So we can ask something like ASK: a AND NOT b etc. Use attribute identifiers. Let's choose something to narrow down. For example ask if it's adult (a). So ASK: a. That is a Boolean expression. Should be fine.<|end|><|start|>assistant<|channel|>final<|message|>ASK: a<|return|>
````

Action decoded by the adapter:

````text
ASK: a
````

Answer delivered to the model:

````text
INVALID
````

Private diagnostic: EIG 0.000000000; truncated False; error `Unknown attribute: a`.

## Turn 7: generated response

````text
<|channel|>analysis<|message|>The user says "Answer flip probability: 0.00, independently each question. Maximum questions: 10. After the last answer, make one final guess; another question loses. Begin."

We need to play Twenty Questions. The assistant should ask a Boolean expression to get truth about attributes, following the format ASK: <Boolean expression>. We have 10 questions max, then final guess.

We must not give explanations. Must output exactly one line per turn: ASK: ... or GUESS: ...

We have to start with a question. Should choose something that narrows down. Let's examine items.

List items with attributes:

1 adult_female_fennec_fox: a,b,i,j,l,p,u,af,al,an
2 juvenile_female_crested_porcupine: b,p,v,al,an,ay
3 adult_female_red_fox: a,i,j,n,p,u,al,an
4 juvenile_male_spider_monkey: c,k,u,al,ao,as
5 juvenile_female_rabbit: i,n,p,u,v,y,af,al
6 adult_male_walrus: a,d,j,s,al,aq,bc
7 adult_female_manatee: a,d,p,s,v,al,ax
8 adult_male_striped_skunk: a,c,u,al,an,ao,ba,bb
9 juvenile_female_red_panda: f,k,p,u,v,al,au
10 juvenile_female_snow_leopard: f,j,k,p,u,al,am,az
11 juvenile_male_komodo_dragon: f,j,ad,ag,at,av,bd
12 juvenile_female_white_rhinoceros: b,e,p,v,z,ab,al
13 juvenile_male_aardvark: b,i,u,ac,aj,al,an
14 adult_female_zebra: a,b,p,u,v,x,ad,al,bb
15 juvenile_male_crested_porcupine: b,v,al,an,ay
16 juvenile_female_ring_tailed_lemur: b,k,p,u,al,ao,au
17 juvenile_female_beaver: d,n,p,q,u,v,al,be
18 adult_male_ring_tailed_lemur: a,b,k,u,al,ao,au
19 juvenile_female_sperm_whale: d,j,m,p,s,ab,al

````

Action decoded by the adapter:

````text

````

Answer delivered to the model:

````text
INVALID
````

Private diagnostic: EIG 0.000000000; truncated True; error `Expected one ASK or GUESS line.`.

## Turn 8: generated response

````text
<|channel|>analysis<|message|>The user is trying to get the game started. The system says we need to output ASK: <Boolean expression> or GUESS: <exact item name>. We have up to 10 questions. The user gave "Answer flip probability: 0.00, independently each question. Maximum questions: 10. After the last answer, make one final guess; another question loses. Begin." So we need to start asking a question. The format: ASK: <Boolean expression>. Use attribute identifiers and maybe item equality. We need to ask something that helps narrow. Could start with something like "a" (adult). But we need correct syntax: ASK: a (that's a Boolean expression, just attribute a). That's acceptable. Could also combine with others. Let's ask something.

We must output exactly one line. So "ASK: a". That's fine.

<|end|><|start|>assistant<|channel|>final<|message|>ASK: a<|return|>
````

Action decoded by the adapter:

````text
ASK: a
````

Answer delivered to the model:

````text
INVALID
````

Private diagnostic: EIG 0.000000000; truncated False; error `Unknown attribute: a`.

## Turn 9: generated response

````text
<|channel|>analysis<|message|>The user says "INVALID" repeatedly. The system expects the assistant to play Twenty Questions. The user gave "Answer flip probability: 0.00, independently each question. Maximum questions: 10. After the last answer, make one final guess; another question loses. Begin."

We need to ask a question (ASK) using Boolean expression. The user then responded "INVALID". That likely means the previous question was invalid? Actually per instructions, if we ask an invalid question, it costs a question. But user says "INVALID". Perhaps they are indicating the previous question was invalid. But we need to continue playing. We have to ask a valid question. Let's think: We need to deduce the hidden item. We can ask about attributes. We have to ask a boolean expression. We have 10 questions max. But user hasn't provided any responses except "INVALID". That seems like they are not playing correctly. But we must continue.

We need to ask a valid question: ASK: <expression>. The expression can be something like "a" meaning adult? Actually attribute identifiers are just codes. The expression must be boolean using identifiers, AND, OR, NOT, parentheses, and possibly item == <item name>. We can ask something like "ASK: a". That asks if attribute a (adult) is true. But user responded "INVALID". Maybe they think it's invalid because they expect a boolean answer? Actually the system expects the assistant to output ASK: expression, then the user will answer "TRUE" or "FALSE". But the user responded with "INVALID". Maybe they think our question was invalid. Why would "ASK: a" be invalid? Possibly because we need to use full attribute names, not codes. The instruction: "Use full attribute names from the code=name mapping in questions." So we must use full names, not codes. So "ASK: a" is invalid. We need to use the full attribute name, e.g., "adult". So we should ask "ASK: adult". That is a boolean attribute.

Thus we need to ask a valid question using full attribute names. Let's ask something like "ASK: adult". Then user should answer TRUE or FALSE. But they might still respond "INVALID" if they don't follow. But we try.

Thus output: ASK: adult.<|end|><|start|>assistant<|channel|>final<|message|>ASK: adult<|return|>
````

Action decoded by the adapter:

````text
ASK: adult
````

Answer delivered to the model:

````text
NO
````

Private diagnostic: EIG 0.997180399; truncated False; error ``.

## Turn 10: generated response

````text
<|channel|>analysis<|message|>The user says "Answer flip probability: 0.00, independently each question. Maximum questions: 10. After the last answer, make one final guess; another question loses. Begin."

So we are playing twenty questions. We need to ask Boolean expressions. The user responded "NO" to "ASK: adult". That means the expression evaluated to false for the hidden item. So the hidden item does NOT have attribute 'adult' (code a). So it's a juvenile. Good.

We have up to 10 questions. We have used 1 question (adult). Need to continue asking. Must output ASK: <Boolean expression>. Use full attribute names from code=name mapping. The table defines truth.

We need to narrow down among items that are juvenile (no a). List all juvenile items:

From table: items where a is not listed.

List:

juvenile_female_crested_porcupine (b,p,v,al,an,ay)
juvenile_male_spider_monkey (c,k,u,al,ao,as)
juvenile_female_rabbit (i,n,p,u,v,y,af,al)
juvenile_female_red_panda (f,k,p,u,v,al,au)
juvenile_female_snow_leopard (f,j,k,p,u,al,am,az)
juvenile_male_komodo_dragon (f,j,ad,ag,at,av,bd)
juvenile_female_white_rhinoceros (b,e,p,v,z,ab,al)
juvenile_male_aardvark (b,i,u,ac,aj,al,an)
juvenile_male_crested_porcupine (b,v,al,an,ay)
juvenile_female_ring_tailed_lemur (b,k,p,u,al,ao,au)
juvenile_female_beaver (d,n,p,q,u,v,al,be)
juvenile_female_sperm_whale (d,j,m,p,s,ab,al)
juvenile_male_barn_owl (h,j,o,r,ag,an,aw)
juvenile_male_platypus (d,g,u,ag,al,bd,be)
juvenile_female_silky_anteater (c,k,p,u,ac,aj,al,an)
juvenile_male_howler_monkey (c,k,u,v,ak,al,as)
juvenile_female_mountain_goat (c,k
````

Action decoded by the adapter:

````text

````

Answer delivered to the model:

````text
INVALID
````

Private diagnostic: EIG 0.000000000; truncated True; error `Expected one ASK or GUESS line.`.

## Turn 11: generated response

````text
<|channel|>analysis<|message|>We have a game: we must ask Boolean expressions to narrow down hidden item. The user says "INVALID" repeatedly. We responded incorrectly. Need to follow protocol: we can ask a question using ASK: <Boolean expression>. The user must answer YES/NO? The game says after each item name, the listed column codes are true; omitted false. We must ask using attribute identifiers, AND, OR, NOT, parentheses, and item == <item name>. The user will respond with YES or NO presumably. The user gave "INVALID" which is not a valid answer. We need to handle this. The instruction: "An invalid question costs a question." But we need to continue. Should we ask a proper question now. We have up to 10 questions. Let's ask a question that splits the list. For example, ask if the hidden item has attribute 'f' (asia). Many items have f? Let's see: items with f: juvenile_female_red_panda (f,k,p...), juvenile_female_snow_leopard (f,j,k...), adult_female_toucan (a,c,h,o,p,r,v,ae,ag) includes f? No, toucan has a,c,... no f. adult_male_king_cobra (a,f,j,w...). adult_female_orangutan (a,f,k...). So f appears in some. That may be decent.

But maybe ask about attribute 'd' (aquatic). Many aquatic: walrus, manatee, beaver, sperm_whale, capybara, sea_otter, platypus. That's many. Could be good.

Better ask about is it a mammal (al). Most are mammals except bird, reptile, etc. Many are mammals. Might not narrow.

We need to identify hidden item. There are many items. We have up to 10 questions.

We could ask about attribute 'h' (bird). Only adult_female_toucan has h (bird). Also barn owl has h? Actually barn owl has h? code list: juvenile_male_barn_owl has h? It has h? In table: "juvenile_male_barn_owl|h,j,o,r,ag,an,aw". Yes includes h (bird). So two birds. So ask if h true. That would narrow to two possibilities.

Let's ask: ASK: h

We'll wait for answer.<|end|><|start|>assistant<|channel|>final<|message|>ASK: h<|return|>
````

Action decoded by the adapter:

````text
ASK: h
````

Answer delivered to the model:

````text
LOSS
````

Private diagnostic: EIG 0.000000000; truncated False; error ``.

End: won=False, questions=10, context_overflow=False, reward=-1.2000.
