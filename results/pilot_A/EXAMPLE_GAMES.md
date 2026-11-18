# Paired pilot games

These two development targets were selected before training. The raw-base games are from update 0; the comparison uses the last scheduled development snapshot. Neither case entered gradients. They illustrate strategy and are not representative performance samples.

## train-v1/seed20261122/animals/4/700100/p0

Hidden target: `adult_male_jaguar`. N=4. Final policy update: 16.

Raw base: win, 3 questions, EIG/question 0.333. RL: win, 2 questions, EIG/question 0.500.

| Turn | Raw base action → answer | RL action → answer |
| ---: | --- | --- |
| 1 | <code>ASK: m</code> → **NO**<br>2 remaining; EIG 1.000 | <code>ASK: m</code> → **NO**<br>2 remaining; EIG 1.000 |
| 2 | <code>ASK: j</code> → **YES**<br>2 remaining; EIG 0.000 | <code>ASK: j</code> → **YES**<br>2 remaining; EIG 0.000 |
| 3 | <code>ASK: NOT (m AND j)</code> → **YES**<br>2 remaining; EIG 0.000 | <code>GUESS: adult_male_jaguar</code> → **WIN**<br>2 remaining; EIG 0.000 |
| 4 | <code>GUESS: adult_male_jaguar</code> → **WIN**<br>2 remaining; EIG 0.000 | — |

Candidate table, shared by both players:

```text
DOMAIN animals
ATTRIBUTES code=name
a=adult,b=america,c=aquatic,d=asia,e=bird,f=europe,g=feathers,h=female,i=flies,j=fur,k=hooked_beak,l=large,m=lays_eggs,n=mammal,o=packs,p=reptile,q=scales,r=spots,s=venomous
TABLE name|true column codes
adult_female_bald_eagle|a,b,e,g,h,i,k,m
juvenile_female_gray_wolf|f,h,j,l,n,o
adult_female_komodo_dragon|a,d,h,l,m,p,q,s
adult_male_jaguar|a,b,c,j,n,r
END TABLE

```

## train-v1/seed20261122/animals/8/700100/p0

Hidden target: `adult_male_african_wild_dog`. N=8. Final policy update: 16.

Raw base: loss, 4 questions, EIG/question 0.594. RL: loss, 4 questions, EIG/question 0.594.

| Turn | Raw base action → answer | RL action → answer |
| ---: | --- | --- |
| 1 | <code>ASK: s</code> → **YES**<br>7 remaining; EIG 0.544 | <code>ASK: s</code> → **YES**<br>7 remaining; EIG 0.544 |
| 2 | <code>ASK: l</code> → **YES**<br>5 remaining; EIG 0.863 | <code>ASK: l</code> → **YES**<br>5 remaining; EIG 0.863 |
| 3 | <code>ASK: j</code> → **NO**<br>2 remaining; EIG 0.971 | <code>ASK: j</code> → **NO**<br>2 remaining; EIG 0.971 |
| 4 | <code>ASK: g</code> → **YES**<br>2 remaining; EIG 0.000 | <code>ASK: g</code> → **YES**<br>2 remaining; EIG 0.000 |
| 5 | <code>GUESS: adult_male_tiger</code> → **LOSS**<br>2 remaining; EIG 0.000 | <code>GUESS: adult_male_tiger</code> → **LOSS**<br>2 remaining; EIG 0.000 |

Candidate table, shared by both players:

```text
DOMAIN animals
ATTRIBUTES code=name
a=adult,b=africa,c=america,d=aquatic,e=asia,f=burrows,g=carnivore,h=climbs,i=external_ears,j=female,k=flippers,l=fur,m=hairless,n=herbivore,o=huge,p=knuckle_walks,q=large,r=lays_eggs,s=mammal,t=nocturnal,u=omnivore,v=packs,w=pouch,x=reptile,y=scales,z=shell,aa=spots,ab=stripes
TABLE name|true column codes
adult_male_tiger|a,d,e,g,l,q,s,ab
juvenile_male_green_sea_turtle|d,k,n,r,x,y,z
adult_male_african_wild_dog|a,b,g,l,s,v,aa
adult_male_sea_lion|a,d,g,i,k,s
juvenile_female_gorilla|b,h,j,l,n,p,q,s
adult_female_honey_badger|a,b,f,j,l,s,u
adult_female_virginia_opossum|a,c,h,j,l,s,t,w
adult_female_hippopotamus|a,b,d,j,m,n,o,s
END TABLE

```
