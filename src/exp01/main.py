# Data Collection - random gathering tasks w/ pass-through policy decisions

import os, sys, random, pickle, time

import data
from vector2 import vector2
from runner import RunnerPassThrough
from components.reasoning.goals import Goal_HasItemType
from exp01.cagent import CAgent_OutcomeEval
from components.cbehavior import CBehaviorMobPatrol
from constants import *
import gui

# control variables
EXPLORE_PROB = 0.0 #0.05
EXPLORE_INTERRUPT_PROB = 0.00 #0.01
MODEL_DIR = "models"
MODEL_FILE = "igraph.pkl" #schema_lib_3_gather_mobs.pkl"
TRIALS = 1
TIME_LIMIT = 120

DIM = (600, 600)
VIEWPORT = (600, 600)

def run_once(i):
    # set seed for repeatable behavior
    seed = random.randint(0, sys.maxsize)
    print("Starting run with seed {}".format(seed), flush=True)
    random.seed(seed)

    spec = [{'tid': 1000,
             'loc': vector2((100,300))},
            {'tid': 1000,
             'loc': vector2((300, 550))},
            {'tid': 1000,
             'loc': vector2((500, 100))},

            {'tid': 1001, 'ct': 4},

            # {'tid': 2, 'ct': 1,
            #  'behavior_fn': lambda eid, world: CBehaviorMobPatrol(eid, world.entities.get(eid).pos, 100),
            #  },
            {'tid': 3, 'ct': 2,
             'behavior_fn': lambda eid, world: CBehaviorMobPatrol(eid, world.entities.get(eid).pos, 100),
             },
            # {'tid': 4, 'ct': 2,
            #  'behavior_fn': lambda eid, world: CBehaviorMobPatrol(eid, world.entities.get(eid).pos, 100),
            #  },

            {'tid': data.AGENT_TYPE_ID, 'ct': 1,
             'loc': vector2([d/2 for d in DIM]),
             'thirst': None,
             'agent_fn': lambda eid, world: CAgent_OutcomeEval(eid,
                                                               (Goal_HasItemType(2000, 6, 1.0),
                                                                ),
                                                               EXPLORE_PROB,
                                                               EXPLORE_INTERRUPT_PROB,
                                                               MODEL_DIR, MODEL_FILE)

             },
    ]

    r = RunnerPassThrough(DIM, VIEWPORT)
    # eid for last entity is returned (for camera focus)
    focus_eid = r.setup(spec)
    gui.init(VIEWPORT)

    r.start()
    # main loop
    while True:
        # exit condition
        exit = False
        if r.done():
            # still allow step, for behavior cleanup
            r.trace.add_event(r.world, '(done)')
            exit = True

        # focus death (killed or dehydration)
        if r.world.entities.get(focus_eid) is None:
            print(i, "Complete at world time {} => {}".format(r.world.clock, r.trace.decisions[-1].behavior_sig), flush=True)
            exit = True

        r.step(False)

        if exit:
            print(i, "Complete at world time {} => {}".format(r.world.clock, r.trace.decisions[-1].behavior_sig), flush=True)
            break

        # loop
        if r.trace.looping():
            r.trace.add_event(r.world, '(looping)')
            print(i, "Complete at world time {} => {}".format(r.world.clock, r.trace.decisions[-1].behavior_sig), flush=True)
            break

        # time limit
        if r.world.clock > TIME_LIMIT:
            r.trace.add_event(r.world, '(timeout)')
            print(i, "Complete at world time {} => {}".format(r.world.clock, r.trace.decisions[-1].behavior_sig), flush=True)
            break

        # render
        gui.set_msg(0, "{:.4f} FPS".format(r.fps))
        gui.set_msg(1, "{:.4f} UPS".format(r.ups))
        gui.update_screen(r.world, focus_eid)

    print("Frames: {}, Updates: {}".format(r.fct, r.uct))

    r.trace.annotate_endings()
    print(r.trace)

if __name__ == '__main__':
    for i in range(TRIALS):
        run_once(i)
