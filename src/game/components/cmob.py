import random
from components.cbehavior import *
from components.reasoning.goals import Goal_HasItemType, GoalNode
import data

# module level
DEBUG = True


class ComponentStoreMob(ComponentStore):
    def update(self, dt):
        """mob update, apply proposed decisions."""
        for eid, a in self.all():
            # agent updates are specialized by subclasses
            a.update(self.world, dt)

class CMob:
    def __init__(self, eid, anchor, radius):
        self.eid = eid
        self.anchor = anchor
        self.radius = radius
        self.leash_point = None
        self.leashing = False
        self.attack_target = None
        self.active_behavior = None
        self.proposal = None


    def update(self, world, dt):
        """Agent update, apply proposed decisions."""

        # new proposal!
        if self.proposal is not None:
            # clear old behavior, if active
            if self.active_behavior is not None:
                print('mob behavior active behavior status', self.active_behavior.status)
                if DEBUG: print("[{:.2f}] Mob: replacing active {}".format(world.clock, self.active_behavior.short_status()))
                world.behaviors.remove(self.eid, self.active_behavior.status, world)
            # apply new
            if DEBUG and not world.simulation: print("[{:.2f}] Mob: starting {}".format(world.clock, self.proposal))
            self.active_behavior = self.proposal
            self.active_behavior.status = RUNNING
            self.proposal = None
            world.behaviors.addc(self.eid, self.active_behavior, True)
            return

        # got here, no proposal, check for reaping
        if self.active_behavior is not None and self.active_behavior.status != RUNNING:
            print('mob behavior active behavior status', self.active_behavior.status)
            if DEBUG: print("[{:.2f}] Mob: reaping active {}".format(world.clock, self.active_behavior.short_status()))
            #if trace: trace.end_update(world, self.eid, self.active_behavior.sig(), self.active_behavior.status)
            world.behaviors.remove(self.eid, self.active_behavior.status, world)
            self.active_behavior = None
            return

        # has no current behavior or still running current behavior
        return

class CMob_BehaviorEval(CMob):
    def __init__(self, eid, anchor, radius):
        super().__init__(eid, anchor, radius)
        self.anchor = anchor
        self.radius = radius
        self.leash_point = None
        self.leashing = False
        self.patroling = False
        self.attack_target = None
        self.check = False
        self.cd_timer = 3.0

    def consider(self, world, dt, trace=None):
        candidates = []
        agent = world.entities.get(self.eid)
        aware = data.awareness[agent.tid]

        #behaviors like patrol, attack, leash
        ################checking for leashing#############
        dist = (self.anchor - agent.pos).magnitude()
        if dist > self.radius + (data.awareness[agent.tid] * 2) or agent.flag == 'leash':
            self.leashing = True
            agent.flag = 'leash'
            self.cd_timer = 3.0

            #if trace: trace.end_update(world, self.eid, '{}'.format(self.active_behavior), INTERRUPT)
            candidates.append(CBehaviorMoveToLocation(self.eid, self.anchor))
        ###################################################

        #######checking for stun####################
        elif agent.flag == 'stun' and self.check == False:
            candidates.append(CBehaviorStun(self.eid))
            self.check = True
            self.cd_timer = 3.0

        #####################################

        ######check if crab mob has finished attacking. if so, run ########
        elif agent.flag == 'pinched':
            target = world.attacking.get(self.attack_target)
            if target is not None and target.target_eid == self.eid:
                candidates.append(CBehaviorFlee(self.eid, self.attack_target))
                self.cd_timer -= dt
            if self.cd_timer <= 0.0:
                self.cd_timer = 3.0
                agent.flag = 'idle'
            else:
                self.cd_timer -= dt

        ############################################################
        else:
            min_dist = 0
            for eid, ent in world.agents_within_range(self.eid, aware):
                dist = (agent.pos - ent.pos).magnitude()
                if min_dist == 0 or dist < min_dist:
                    min_dist = dist
                    self.attack_target = eid
                    self.leash_point = agent.pos
                    if self.attack_target is not None and agent.flag != 'stun':
                        candidates.append(CBehaviorMoveAndAttack(self.eid, self.attack_target))

        if (self.active_behavior is None or self.active_behavior.status != RUNNING) and agent.flag == 'idle':
            candidates.append(CBehaviorMobPatrol(self.eid, self.anchor, self.radius))


        if len(candidates) > 0 and self.active_behavior != candidates[-1]:
            if self.active_behavior != self.proposal:
                self.proposal = candidates.pop()
            else:
                self.proposal = candidates.pop()




