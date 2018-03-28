# Data Collection - random gathering tasks w/ pass-through policy decisions

import os, sys, random, pickle, time

import data
from vector2 import vector2
from runner import RunnerPassThrough
from components.reasoning.goals import Goal_HasItemType
from exp01.cagent import CAgent_OutcomeEval
from components.cbehavior import CBehaviorMobPatrol
from constants import *
#import gui

# control variables
DATA_DIR = os.path.join("traces")
TRIALS = 10
TIME_LIMIT = 120

DIM = (600, 600)
VIEWPORT = (600, 600)
FIXED_TIMESTEP = 0.02

def run_once(i):
    # set seed for repeatable behavior
    seed = random.randint(0, sys.maxsize)
    print("Starting run with seed {}".format(seed), flush=True)
    random.seed(seed)

    spec = [{'tid': 1000, 'ct': 3},
            {'tid': data.AGENT_TYPE_ID, 'ct': 1,
             'loc': vector2([d/2 for d in DIM]),
             'agent_fn': lambda eid, world: CAgent_OutcomeEval(eid,
                                                               (Goal_HasItemType(2000, 6, 1.0),
                                                                ),
                                                               1.0,
                                                               0.01)
             },
    ]

    r = RunnerPassThrough(DIM, VIEWPORT, FIXED_TIMESTEP)
    # eid for last entity is returned (for camera focus)
    focus_eid = r.setup(spec)
    #gui.init(VIEWPORT)

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
            r.trace.add_event(r.world, '(done)')
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

    print("Frames: {}, Updates: {}".format(r.fct, r.uct))

    r.trace.annotate_endings()
    print(r.trace)

    # save trial to disk
    f = open(os.path.join(DATA_DIR, "trace-{:.0f}-{}.pkl".format(time.time(), random.randint(0, 100000))), 'wb')
    pickle.dump((seed, r.trace), f)
    f.close()

if __name__ == '__main__':
    for i in range(TRIALS):
        run_once(i)
