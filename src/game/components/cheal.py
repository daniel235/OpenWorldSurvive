from constants import *
from components.cstore import ComponentStore

DEBUG=True

class CHeal:
    def __init__(self,item_eat,world):
        self.cd_eat=item_eat
        self.status= RUNNING

class ComponentStoreHeal(ComponentStore):
    def add(self,agent_eid,item_eat):
        return self.addc(agent_eid,CHeal( item_eat, self.world))
    def add_replace(self,agent_eid,item_eat):
        if agent_eid in self.cc:self.remove(agent_eid)
        return self.addc(agent_eid, CHeal(item_eat, self.world))

    def update(self, dt):
        for eid, act in self.all():
            if act.status==RUNNING:
                act.cd_eat-=dt
                if(act.cd_eat<=0):
                    act.status=SUCCESS
                    self.remove_ids.add(eid)
