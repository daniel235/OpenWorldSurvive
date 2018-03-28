# entities

AGENT_TYPE_ID = 1

names = { 1    : 'agent',
          2    : 'angry squirrel',
          3    : 'wolf',
          4    : 'bear',
          5    : 'crab',

          1000 : 'tree',
          1001 : 'rock',
          1002 : 'rain pool',
          1004 : 'bush',
          1005 : 'pond',
          1006 : 'herb bush',
          1007 : 'coconut tree',

          1010 : 'buried root',


          2000 : 'wood',
          2001 : 'stone',
          2002 : 'vine',
          2003 : 'shard',
          2004 : 'axe',
          2005 : 'pick',
          2006 : 'pointy stick',
          2007 : 'spear',
          2008 : 'battleaxe',
          2009 : 'blueberry',
          2010 : 'strawberry',
          2011 : 'dirty water',
          2012 : 'clean water',
          2013 : 'bear claw',
          2014 : 'wolf meat',
          2015 : 'acorn',
          2016 : 'heal herb',
          2017 : 'frond',
          2018 : 'coconut',
          2019 : 'root',
          2020 : 'coconut flesh',
          2021 : 'tent',
          2022 : 'firepit',
          2023: 'twig pile',
          2024: 'frond pile',

          3000 : 'icicle',
          3001 : 'snowball',
          3002 : 'molotov',
          3003 : 'fireball',
          3004 : 'stun',
          3005 : 'widowmaker',

          4000 : 'net trap',  # stunning trap
          }

movement_speed = { 1 : 250.0,
                   2 : 120.0,
                   3 : 100.0,
                   4 : 80.0,
                   5 : 300.0,
                   }
attack_speed = { 1 : 300.0,
                 2 : 400.0,
                 3 : 350.0,
                 4 : 300.0,
                 5 : 350.0,
                 }

awareness = { 1 : 512.0,
              2 : 100.0,
              3 : 100.0,
              4 : 100.0,
              5 : 200.0,
              }

render = { 1000 : { 'shape' : 'circle',
                    'color' : (100,200,150),
                    'size' : 15
                    },
           1001: {'shape': 'circle',
                  'color': (150, 100, 200),
                  'size': 15
                  },
           2021: {'shape': 'circle',
                  'color': (150, 150, 150),
                  'size': 30
                  },
           2022: {'shape': 'circle',
                  'color': (200, 150, 0),
                  'size': 15
                  },
           1004:{'shape': 'circle',
                 'color': (0,21,255),
                 'size': 15
                 },

           1005:{'shape': 'circle',
                 'color': (0, 255, 255),
                 'size': 25
                 },

           1002:{'shape': 'circle',
                 'color': (0, 51, 204),
                 'size': 25
                 },

           1006:{'shape': 'circle',
                 'color': (255, 0, 128),
                 'size': 25
                 },

           1007:{'shape': 'circle',
                 'color': (244, 164, 96),
                 'size': 25
                 },

           2023:{'shape': 'circle',
                 'color': (150, 150, 150),
                 'size': 25
                 },

           2024:{'shape': 'circle',
                 'color': (150, 150, 150),
                 'size': 25
                 },

           1010:{'shape': 'circle',
                 'color': (102, 51, 0),
                 'size': 15
                },

           1 : { 'shape' : 'square',
                 'color' : (0,255,0),
                 'size' : 10
                 },
           2 : { 'shape' : 'rect',
                 'color' : (255,0,200),
                 'size' : 10
                 },
           3 : { 'shape' : 'rect',
                 'color' : (255,178,0),
                 'size' : 15
                 },
           4 : { 'shape' : 'rect',
                 'color' : (255,0,120),
                 'size' : 25
                 },
           5 : { 'shape' : 'square',
                 'color' : (0,128,128),
                 'size' : 10
                 },

           4000 : {'shape' : 'square',
                   'color' : (255, 165, 0),
                   'size' : 10}
           }
for i in range(5000,7000):
    render[i] = {'shape': 'circle',
                 'color': (102, 51, 140),
                 'size': 10
                }
# each entry is (duration, drop_table)
# drop_table is list of (typeid, min, max, drop chance)
gatherable = {1000 : (1.0, ((2000, 2, 2, 1.0), (2002, 1, 1, 0.5))),
              1001 : (2.0, ((2001, 1, 1, 1.0), (2003, 1, 1, 0.7))),
              1004 : (1.0, ((2009, 2, 2, 1.0), (2010, 1, 1, 0.5))),
              1005 : (1.0, ((2011, 1, 4, 1.0), (2012, 1, 2, 0.7))),
              1002 : (1.0, ((2011, 1, 4, 1.0), (2012, 1, 2, 0.7))),
              4000 : (1.0, ((4000, 1, 1, 1.0), (0, 0, 0, 0))),
              1006 : (1.0, ((2016, 1, 1, 1.0),)),
              1007 : (2.0, ((2017, 5, 5, 0.5), (2018, 1, 1, 1.0))),
              1010 : (1.0, ((2019, 1, 1, 1.0),)),
              2018 : (0.01, ((2020, 1, 1, 1.0),)),
              }
for i in range(5000, 5025):
    gatherable[i] = (0.01, ((i-3000, 1, 1, 1.0),))

recipes = {
    2004 : (3.0, ((2000, 2), (2003, 1))),  # axe: 2 wood, 1 shard
    2005 : (3.0, ((2000, 1), (2003, 2))),  # pick: 1 wood, 2 shard
    2007 : (3.0, ((2000, 3), (2002, 1), (2003, 1))), # spear: 3 wood, 1 vine, 1 shard
    2008 : (3.0, ((2007, 1), (2003, 2))),  # Battle Axe: 1 spear, 2 shard
    2022 : (1.0, ((2001, 10), (2000, 10))),  # firepit: 10 stone, 10 wood
    2021 : (1.0, ((2000, 5), (2017, 5))),  # tent: 5 wood, 5 frond
    4000 : (2.0, ((2002, 5), (2001, 4))),  # net trap: 5 vine, 4 stone
    2023 : (1.0, ((2000, 10))),            # Twig pile:  10 wood
    2024 : (1.0, ((2017, 10)))             # Frond pile: 10 Frond
}

gather_effects = {
    2004 : (0.5, (1000,)), # axe: 50% time to gather from trees
    2005 : (0.5, (1001,)), # pick: 50% time to gather from rocks
}

# swing, dmg, range (+melee)

weapons = {
    2006 : (0.5, (0.5, 0.75), 0.0), # pointy stick
    2007 : (0.6, (1.0, 1.5), 0.0),  # spear
    2013 : (0.5, (2.0, 3.5), 0.0), #bearclaw
    2008 : (0.5, (1.0, 2.5), 0.0),  # axe
}

#swing, dmg, range (+melee), ice = 0 hot = 1
attacks = {
    3000 : ((2.0, 3.0), 0.2, 0),  #icicle
    3001 : ((3.2, 3.7), 1.0, 0), #snowball
    3002 : ((3.0, 3.7), 1.0, 1), #molotov
    3003 : ((1.5, 2.5), 0.2, 1), #fireball
    3004 : ((0.0, 0.0), 0.1, 2), #stun
    3005 : ((2.5, 3.6), 0.2, 2), #widowmaker
}

# hp, base swing, base dmg, base range (+melee)
combatants = {
    1 : (4.0,  0.5, (0.25, 0.25), 0.0), # agent
    2 : (1.0,  0.3, (0.1, 0.2), 0.0), # angry squirrel
    3 : (4.0,  0.4, (0.4, 1.0), 0.0), # wolf
    4 : (8.0,  0.5, (1.0, 2.0), 0.0), # bear
    5 : (1.0,  0.3, (0.1, 0.2), 0.0 ) # crab
}

# what item each mob drops
loot = {
    1 : 0,
    2 : 2015,  # acorn
    3 : 2014,  # wolf meat
    4 : 2013,  # bear claw
    5 : 0,
}

# Hunger it restores, followed by cool down time.
# DELETE_HP. Should edibles have a cool down timer? Drinkable items don't and it makes sense since the food meter is
#            always decreasing regardless of the players actions.
edibles = {
    2009 : (0.5, 0.5),  #Blueberry
    2010 : (4.0, 1.5),  #Strawberry
    2014 : (4.0, 1.5),  #Wolf Meat
    2015 : (0.2, 0.5),  #Acorn
    2019 : (0.2, 0.5),  #Root
    2020 : (0.4, 0.5),  #Coconut Flesh
}

# Hp it heals, followed by cool down time.
hp_items = {
    2016 : (0.25, 1.5),  #heal herb
}

# Thirsty Meter Refilled
drinks = {
    2011 : 0.2, #Dirty Water
    2012 : 0.4, #Clean Water
    2018 : 0.4, #Coconut Water
}

# highest possible value (higher the better), rate of depletion
# Rate of depletion is amount lost followed by over what amount of time
thirst = {
    1 : (1.0, (0.2, 2)),  # agent has a 100% meter that losses 20% every 2 seconds
}

# Follows same convention as thirst.
hunger = {
    1 : (1.0, (0.2, 2)),  # agent has a 100% meter that losses 20% every 2 seconds
}

# setup time, activated effect, duration
traps = {
    4000 : (5.0, 'stun', 3.0),
}


#Risk contains items that have a chance at causing damage when a failure state is achieved.
#Values are as follows: TID, ( min_damage, max_damage, fail_chance, interval)
risk = {
    1007 : (0.5, 1.0, 0.134, 1), #DELETE_S1 fail chance used to be 0.25
}