from components.cagent import CAgent
from components.cbt import CBehaviorTree
from components.behaviors import *
from components.cbehavior import *
from components.trees import *
from vector2 import vector2
import data
import os
#from plt import image


class CAgent_BT(CAgent):
    def update(self, world, dt, trace=None):
        "Override update to do nothing."
        b = world.behaviors.get(self.eid)
        if b is None:
            cbt = CBehaviorTree('gather', self.eid)
            BTS['gather'] = BehaviorExploreTree('gather', BehaviorGatherTree('gather'))
            cbt.destination = vector2((100,100))
            #cbt.movement_speed = movement_speed[AGENT_TYPE_ID]
            cbt.margin = 0.1
            world.behaviors.addc(self.eid, cbt)



