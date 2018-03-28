import random

import data
from vector2 import vector2
from components.cagent import CAgent_BehaviorEval
from components.cagent_bt import CAgent_BT
from components.cagent_dq import dqnPlay
from components.cbehavior import CBehaviorMobPatrol
from components.cmob import CMob_BehaviorEval
from components.reasoning.goals import Goal_HasItemType


#Test environments.
class Worldspec:
    def __init__(self, DIM, seed, weapons, attacks):
        random.seed(seed)

        self.spec = {
                #World includes: crab mobs, coconut trees, herbs, pre-built fire pit, pre-built tent and agent.
                'hp_system'  : [{'tid': 5, 'ct': 5,
                                 'mob_fn': lambda eid, world: CMob_BehaviorEval(eid, world.entities.get(eid).pos, 100),
                                 },
                                {'tid': data.AGENT_TYPE_ID, 'ct': 1,
                                 'loc': vector2([d / 2 for d in DIM]),
                                 'inv': ((2016, 2), (2023, 1), (2024, 1)),
                                 'agent_fn': lambda eid, world: CAgent_BehaviorEval(eid, (Goal_HasItemType(1003, 1, 1.0),)),
                                 },
                               ],

            'bt_test': [{'tid': 1006, 'ct': 6},
                          {'tid': data.AGENT_TYPE_ID, 'ct': 1,
                           'loc': vector2([d / 2 for d in DIM]),
                           'inv': ((2016, 2), (2023, 1), (2024, 1)),
                           'agent_fn': lambda eid, world: CAgent_BT(eid, (Goal_HasItemType(1003, 1, 1.0),)),
                           },
                          ],

            'balance'   : [{'tid': 1007, 'ct': 5},
                               {'tid': 1010, 'ct': 10},
                               {'tid': 1006, 'ct': 6},
                               {'tid': 1002, 'ct': 1, 'decay': (5, 5.0)},
                               {'tid': 5, 'ct': 5,
                                'mob_fn': lambda eid, world: CMob_BehaviorEval(eid, world.entities.get(eid).pos, 100),
                                },
                               {'tid': data.AGENT_TYPE_ID, 'ct': 1,
                               'loc': vector2([d / 2 for d in DIM]),
                               'agent_fn': lambda eid, world: CAgent_BehaviorEval(eid, (Goal_HasItemType(1003, 1, 1.0),)),
                                },
                              ],


                #Last Modified 09/20/2017.
                'defeat_bear': [{'tid': 1000, 'ct': 30},
                                {'tid': 1001, 'ct': 10},
                                {'tid': 1004, 'ct': 15},
                                {'tid': 1005, 'ct': 2},
                                {'tid' : 2, 'ct': 5,
                                 'mob_fn': lambda eid, world: CMob_BehaviorEval(eid, world.entities.get(eid).pos, 100),
                                 },
                                {'tid': 3, 'ct': 2,
                                 'mob_fn': lambda eid, world: CMob_BehaviorEval(eid, world.entities.get(eid).pos, 100),
                                 },
                                {'tid': 4, 'ct': 2,
                                 'mob_fn': lambda eid, world: CMob_BehaviorEval(eid, world.entities.get(eid).pos, 100),
                                 },
                                {'tid': data.AGENT_TYPE_ID, 'ct': 1,
                                 'loc': vector2([d/2 for d in DIM]),
                                 'inv': (random.choice(weapons), random.choice(attacks)),
                                 'agent_fn': lambda eid, world: CAgent_BehaviorEval(eid, (Goal_HasItemType(2013, 1, 1.0),)),
                                 },
                                ],

                'dqnTest': [{'tid':1000, 'ct':2},
                            {'tid': data.AGENT_TYPE_ID, 'ct': 1,
                            'loc': vector2([d/2 for d in DIM]),
                            'agent_fn': lambda eid, world: dqnPlay(eid, (Goal_HasItemType(1000, 1, 1.0),)),
                            },
                            ],

                }