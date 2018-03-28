# variable time w/ gui (debugging)

import time, random, copy, queue
from constants import *
import data
from world import World
from dm import DramaManager
from components import cagent
from components.cbehavior import CBehaviorMobPatrol
from trace import Trace

# module level
DEBUG = True

class RunnerPassThrough:
    def __init__(self, dim, viewport, fixed_timestep=None):
        self.dim = dim
        self.viewport = viewport
        self.fixed_timestep = fixed_timestep

        # for reporting simplicity
        self.ups = self.uct = 0

        # list of decision nodes
        self.trace = Trace()

    def setup(self, entities):
        self.world = World(self.dim, self.trace)
        eid = 0
        for spec in entities:
            ct = ('ct' in spec and spec['ct']) or 1
            for i in range(ct):
                eid,ent = self.world.add_entity(spec)
        self.dm = DramaManager(self.world)
        # return last entity id (for camera focus)
        return eid

    def start(self):
        # init timers and counters
        self.last_frame = self.start = time.time()
        self.fps = 0
        self.fct = self.fps_ct = 0
        self.fps_timer = 0

        return None,None

    def done(self):
        return self.dm.goals_met()

    def step(self, pause):
        if pause:
            self.last_frame = time.time()
            return None,None

        # time since last frame
        t = time.time()
        delta = t - self.last_frame
        self.last_frame = t

        # keep track of fps, updates-per-sec
        self.fct += 1
        self.fps_ct += 1
        self.fps_timer += delta
        if self.fps_timer >= 1.0:
            self.fps = self.fps_ct / self.fps_timer
            self.fps_ct = 0
            self.fps_timer -= 1.0

        # first time in, full consider for second move, and set to 0
        self.dm.update_consider((self.fixed_timestep is not None and self.fixed_timestep) or delta)

        # update the world, acting on any moves the dm/agents have chosen
        self.world.update((self.fixed_timestep is not None and self.fixed_timestep) or delta)

        return None,None
