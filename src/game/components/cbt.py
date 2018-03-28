##########################################################
# BehaviorTree as a CBehavior
##########################################################

from constants import *
from components.behaviors import BTS
from components.cbehavior import CBehavior

class CBehaviorTree(CBehavior):
    """
    BT component holds:
     reference to the shared tree root
     traversal state
     blackboard variables
     active channel pointers (move, action) for actions that can't be interrupted
     separate interrupt system?
    """
    def __init__(self, bt_id, agent_eid):
        "Set the shared behavior tree to use"
        self.reset()
        # using an id here to avoid deep copy of the shared bts
        self.bt_id = bt_id
        self.agent_eid = agent_eid

        # blackboard
        self.bb = {}

        # traversal state
        self.traversal = []

        # active channel pointers
        self.active_movement = None
        self.active_action = None

    def update(self, agent_eid, world, dt, trace=None):
        "Pass in agent, world so as not to store references in components"
        bt = BTS[self.bt_id]

        status,rtraversal = bt.update(self, self.traversal, world.entities.get(agent_eid), world, dt)
        #self.traversal = reversed(rtraversal)

    def reset(self):
        self.status = RUNNING

    def cleanup(self, eid, world):
        pass
