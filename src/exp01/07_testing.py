# Data Collection - random gathering tasks w/ pass-through policy decisions

import os, sys, random, pickle, time

import data
from vector2 import vector2
from runner import RunnerPassThrough
from components.reasoning.goals import Goal_HasItemType
from components.cbehavior import CBehaviorMobPatrol
from exp01.cagent import CAgent_OutcomeEval
from constants import *
import numpy as np

GUI = False

if GUI: import gui

# control variables
EXPLORE_PROB = 0.0 #0.05
EXPLORE_INTERRUPT_PROB = 0.0 #0.01
MODEL_DIR = "models"
MODEL_FILE = "igraph-500.pkl"

REPORT_DIR = os.path.join("reports")
REPORT_FILE = "07_testing_next_frame_{}.txt".format(MODEL_FILE)
GUIDE_FILE = "07_testing_.txt"

TRIALS = 100
TIME_LIMIT = 120

DIM = (600, 600)
VIEWPORT = (600, 600)
if GUI: FIXED_TIMESTEP = None
else: FIXED_TIMESTEP = 0.02

def run_once(i, seed=None):

    # set seed for repeatable behavior
    if seed is not None:
        print("Running with existing seed {}".format(seed), flush=True)
    else:
        seed = random.randint(0, sys.maxsize)
        print("Starting run with seed {}".format(seed), flush=True)
    random.seed(seed)

    # random goals
    goals = []
    iids = [2000,2001,2002,2003]
    random.shuffle(iids)
    for i in range(1+random.randint(0,1)):
        goals.append(Goal_HasItemType(iids[0], 1+random.randint(0,3), 1.0))
        iids = iids[1:]

    spec = [{'tid': 1000, 'ct': 5},
            {'tid': 1001, 'ct': 5},

            {'tid': 3, 'ct': 2,
             'behavior_fn': lambda eid, world: CBehaviorMobPatrol(eid, world.entities.get(eid).pos, 100),
             },

            {'tid': data.AGENT_TYPE_ID, 'ct': 1,
             'loc': vector2([d/2 for d in DIM]),
             'thirst' : None,
             'agent_fn': lambda eid, world: CAgent_OutcomeEval(eid,
                                                               goals,
                                                               EXPLORE_PROB,
                                                               EXPLORE_INTERRUPT_PROB,
                                                               MODEL_DIR, MODEL_FILE)
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

    # return results
    if r.world.agents.count() > 0:
        # survived!
        return (seed, r.world.clock, True, r.world.agents.get(focus_eid).goal_rewards(r.world))
    return (seed, r.world.clock, False, 0)

if __name__ == '__main__':

    stats = []
    postimes = []

    if GUIDE_FILE is not None:
        i = 0
        with open(os.path.join(REPORT_DIR, GUIDE_FILE)) as f:
            for line in f.readlines():
                line = line.split('\t')
                if len(line) > 0:
                    stats.append(run_once(i, int(line[0])))
    else:
        for i in range(TRIALS):
            stats.append(run_once(i))

    # store report for all runs
    f = open(os.path.join(REPORT_DIR, REPORT_FILE), 'w')
    for stat in stats:
        print('\t'.join((str(s) for s in stat)), file=f)
        if stat[2]:
            # success!
            postimes.append(stat[1])
    f.close()

    print("{} success rate, {}({}) mean success time".format(len(postimes)/TRIALS, np.mean(postimes), np.std(postimes)))
