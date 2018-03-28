from constants import *
from components.cstore import ComponentStore

DEBUG=True

class CDecay:
    def __init__(self, stack, time, world):
        self.cd_decay = time
        self.org_time = self.cd_decay
        if stack in (0, 1):
            self.stack = 1
        else:
            self.stack = stack

    def use_stack(self, eid, world):
        a = world.decay.get(eid)
        if a.stack == None:
            return

        a.stack -= 1
        if a.stack <= 0:
            world.decay.remove(eid)
            world.entities.remove(eid)

class ComponentStoreDecay(ComponentStore):
    def add(self,eid, stack=None, time=None):
        return self.addc(eid, CDecay( stack, time, self.world))

    def add_replace(self,eid, time=None, stack=None):
        if eid in self.cc:self.remove(eid)
        return self.addc(eid, CDecay(time, stack , self.world))



    def update(self, dt):
        for eid, act in self.all():
            a = self.world.decay.get(eid)
            if a.cd_decay is None:
                continue

            if a.cd_decay <= 0.0:
                a.cd_decay = a.org_time
                a.stack -= 1
                if a.stack <= 0:
                    self.world.entities.remove(eid)
                    self.remove_ids.add(eid)
            else:
                a.cd_decay -= dt