##########################
#  Decision Agent
##########################
from src import data
from src.constants import *
from src.components import cbehavior

# Each derived agent class represents a specific decision policy

class Agent:
    def __init__(self, eid, world):
        """
        :param int eid: entity Id to bind this agent to
        :param World world: the world the entity lives in
        """
        self.eid = eid
        self.world = world

    def update(self):
        """Called per-frame to execute agent policy decisions
        :return bool: True if policy is still running, False if complete
        """
        pass

class Agent_RandomGather(Agent):
    def update(self):
        b = self.world.behaviors.get(self.eid)

        if not b or b.status != RUNNING:
            if b:
                self.world.behaviors.remove(self.eid)
            # need a new behavior
            for b in self.move_and_gather_targets():
                print("Agent: gathering from {}".format(b.target_eid))
                self.world.behaviors.addc(self.eid, b)
                return True
            # got here? none left
            return False

        # still running current behavior
        return True

    def move_and_gather_targets(self):
        return (cbehavior.CBehaviorMoveAndGather(ent.eid, 250.0) for eid, ent in self.world.entities.all() \
                if ent.tid in data.gatherable)

class Agent_ExecuteBehavior(Agent):

    def __init__(self, eid, world, behavior):
        super().__init__(eid, world)
        self.world.behaviors.addc(eid, behavior)

    def update(self):
        """Called per-frame to check is assigned behavior has finished
        :return bool: True if policy is still running, False if complete
        """
        if self.world.behaviors.get(self.eid).status != RUNNING:
            self.world.behaviors.remove(self.eid)
            return False
        return True

class Agent_MCTS(Agent):

    def update(self):
        # pass one: exhaustive rollouts, avg time as measure of quality
        b = self.world.behaviors.get(self.eid)

        if not b or b.status != RUNNING:
            if b:
                self.world.behaviors.remove(self.eid)
            # need a new behavior (new target)
            for b in self.move_and_gather_targets():
                print("Agent: gathering from {}".format(b.target_eid))
                self.world.behaviors.addc(self.eid, b)
                return True
            # got here? none left
            return False

        # still running current behavior
        return True

    def move_and_gather_targets(self):
        return (cbehavior.CBehaviorMoveAndGather(ent.eid, 250.0) for eid, ent in self.world.entities.all() \
                if ent.tid in data.gatherable)


