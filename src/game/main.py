# Data Collection - random gathering tasks w/ pass-through policy decisions

import os, sys, random, pickle, time
from runner import RunnerPassThrough
from worldspec import Worldspec
from constants import *
import gui


# control variables
DATA_DIR = os.path.join("..", "..", "results", "exp04", "01_collection_det")
TRIALS = 1
TIME_LIMIT = 120

DIM = (768, 768)
VIEWPORT = (768, 768)

def run_once(i, test=False):
    # set seed for repeatable behavior
    seed = random.randint(0, sys.maxsize)
    print("Starting run with seed {}".format(seed), flush=True)
    random.seed(seed)

    weapons = ((2004, 1), (2006, 1), (2007, 1), (2008, 1)) # 2004 is no weapon
    attacks = ((3000, 1), (3001, 1), (3002, 1), (3003, 1))

    # world environment is defined within the spec variable found in worldspec.py
    worldspec = Worldspec(DIM, seed, attacks, weapons)


    r = RunnerPassThrough(DIM, VIEWPORT)

    # eid for last entity is returned (for camera focus)
    # select what test environment you want to use.
    #focus_eid = r.setup(worldspec.spec['balance'])
    if(test):
        focus_eid = r.setup(worldspec.spec['dqnTest'])
    else:
        focus_eid = r.setup(worldspec.spec['bt_test'])
    gui.init(VIEWPORT)

    #snapshot logic
    ct = 0
    timer = 0
    ent = r.world.entities.get(focus_eid)


    r.start()
    # main loop
    while True:
        # exit condition
        '''if r.done():
            r.trace.add_event(r.world, '(done)')
            print(i, "Complete at world time {} => {}".format(r.world.clock, r.trace.decisions[-1].behavior_sig), flush=True)
            break
        '''
        gui.getScreen(0)
        ct += 1
        if (ent.flag == "snap"):
            gui.getScreen(ct)
            ct += 1

        # focus death
        if r.world.entities.get(focus_eid) is None:
            print(i, "Complete at world time {} => {}".format(r.world.clock, r.trace.decisions[-1].behavior_sig), flush=True)
            r.trace.add_event(r.world, '(done)')
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

        r.step(False)

        # render
        gui.set_msg(0, "{:.4f} FPS".format(r.fps))
        gui.set_msg(1, "{:.4f} UPS".format(r.ups))
        gui.update_screen(r.world, focus_eid)
        gui.update_input()
        '''if(test):
            timer += 1
            if(timer > 150):
                gui.getScreen(ct)
                ct += 1
                timer = 0'''




    r.trace.annotate_endings()
    print("Frames: {}, Updates: {}".format(r.fct, r.uct))

    print(r.trace, "\n")


    # save trial to disk
    #f = open(os.path.join(DATA_DIR, "trace-{:.0f}-{}.pkl".format(time.time(), random.randint(0, 100000))), 'wb')
    #pickle.dump((seed, r.trace), f)
    #f.close()

if __name__ == '__main__':
    for i in range(TRIALS):
        run_once(i)
