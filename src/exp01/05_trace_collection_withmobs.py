# Data Collection - random gathering tasks w/ pass-through policy decisions

import os, sys, random, pickle, time

import data
from vector2 import vector2
from runner import RunnerPassThrough
from components.reasoning.goals import Goal_HasItemType
from components.cbehavior import CBehaviorMobPatrol
from exp01.cagent import CAgent_OutcomeEval
from constants import *

GUI = False

if GUI: import gui

# control variables
DATA_DIR = os.path.join("traces_05_withmobs")
TRIALS = 500
TIME_LIMIT = 120
EXPLORE_PROB = 1.0 #0.05
EXPLORE_INTERRUPT_PROB = 0.01 #0.01
MODEL_DIR = "models"
LIB_FILE = "" #schema_lib_3_gather_mobs.pkl"

DIM = (600, 600)
VIEWPORT = (600, 600)
if GUI: FIXED_TIMESTEP = None
else: FIXED_TIMESTEP = 0.02

def run_once(i):
    # set seed for repeatable behavior
    seed = random.randint(0, sys.maxsize)
    print("Starting run with seed {}".format(seed), flush=True)
    random.seed(seed)

    # random goals
    goals = []
    iids = [2000, 2001, 2002, 2003]
    random.shuffle(iids)
    for i in range(1 + random.randint(0, 1)):
        goals.append(Goal_HasItemType(iids[0], 1 + random.randint(0, 3), 1.0))
        iids = iids[1:]

    spec = [{'tid': 1000, 'ct': 5},
            {'tid': 1001, 'ct': 5},

            {'tid': 2, 'ct': 1,
             'behavior_fn': lambda eid, world: CBehaviorMobPatrol(eid, world.entities.get(eid).pos, 100),
             },
            {'tid': 3, 'ct': 1,
             'behavior_fn': lambda eid, world: CBehaviorMobPatrol(eid, world.entities.get(eid).pos, 100),
             },
            {'tid': 4, 'ct': 1,
             'behavior_fn': lambda eid, world: CBehaviorMobPatrol(eid, world.entities.get(eid).pos, 100),
             },

            {'tid': data.AGENT_TYPE_ID, 'ct': 1,
             'loc': vector2([d/2 for d in DIM]),
             'thirst' : None,
             'agent_fn': lambda eid, world: CAgent_OutcomeEval(eid,
                                                               goals,
                                                               EXPLORE_PROB, EXPLORE_INTERRUPT_PROB,
                                                               MODEL_DIR, LIB_FILE)
             },
    ]

    r = RunnerPassThrough(DIM, VIEWPORT, FIXED_TIMESTEP)
    # eid for last entity is returned (for camera focus)
    focus_eid = r.setup(spec)
    if GUI: gui.init(VIEWPORT)

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
            r.trace.add_event(r.world, '(looping)', out_of_update=True)
            print(i, "Complete at world time {} => {}".format(r.world.clock, r.trace.decisions[-1].behavior_sig), flush=True)
            break

        # time limit
        if r.world.clock > TIME_LIMIT:
            r.trace.add_event(r.world, '(timeout)', out_of_update=True)
            print(i, "Complete at world time {} => {}".format(r.world.clock, r.trace.decisions[-1].behavior_sig), flush=True)
            break

        # render
        if GUI:
            gui.set_msg(0, "{:.4f} FPS".format(r.fps))
            gui.set_msg(1, "{:.4f} UPS".format(r.ups))
            gui.update_screen(r.world, focus_eid)

    print("Frames: {}, Updates: {}".format(r.fct, r.uct))

    r.trace.annotate_endings()
    print(r.trace)

    # save trial to disk
    f = open(os.path.join(DATA_DIR, "trace-{:.0f}-{}.pkl".format(time.time(), random.randint(0, 100000))), 'wb')
    pickle.dump((seed, r.trace), f)
    f.close()

    # return results
    if r.world.agents.count() > 0:
        # survived!
        return (seed, r.world.clock, True, r.world.agents.get(focus_eid).goal_rewards(r.world))
    return (seed, r.world.clock, False, 0)

if __name__ == '__main__':
    for i in range(TRIALS):
        run_once(i)
