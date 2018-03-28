import random

from constants import *
import data
from components.cstore import ComponentStore

DEBUG = True

class CStun:
    def __init__(self, agent_eid, world):
        self.agent_eid = agent_eid
        self.status = RUNNING
        self.stunTimer = 2



class ComponentStoreStun(ComponentStore):
    def add(self, agent_eid):
        return self.addc(agent_eid, CStun(agent_eid, self.world))
    def add_replace(self, agent_eid):
        if agent_eid in self.cc: self.remove(agent_eid)
        return self.addc(agent_eid, CStun(agent_eid, self.world))

    def update(self, dt, trace=None):
        for eid, act in self.all():
            if act.status == RUNNING:
                agent = self.world.entities.get(eid)
                if agent.flag == 'stun':
                    act.stunTimer -= dt
                    if act.stunTimer <= 0:
                        act.status = SUCCESS
                        agent.flag = 'unstun'

                if agent.hp < 0:
                    act.status = INTERRUPT
