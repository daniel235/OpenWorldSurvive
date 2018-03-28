from components.cstore import ComponentStore
from components.cbehavior import *

DEBUG = False


class CTag:
    def __init__(self, agent_eid):
        self.tag = agent_eid
        if self.tag is not None:
            self.firmness = 'Soft'
        else:
            self.firmness = None

    def abandoned(self):
        if DEBUG: print("Resource Tag abandoned {}".format(self.tag))
        self.tag = None
        self.firmness = None

    def hard(self):
        if self.firmness is not 'Hard':
            self.firmness = 'Hard'
            if DEBUG : print("Hardened {}".format(self.tag))

    def change(self, agent_eid):
        self.tag = agent_eid
        self.firmness = 'Soft'
        if DEBUG : print("Added Resource Tag {}".format(self.tag))


class CTagMob(CTag):
    def __init__(self, agent_eid):
        super().__init__(agent_eid)
        self.tag = []
        if agent_eid is not None:
            self.tag.append(agent_eid)

    def add(self, agent_eid):
        self.tag.append(agent_eid)
        if DEBUG : print("Added Mob Tag {}".format(self.tag))

    def contains(self, agent_eid):
        for eid in self.tag:
            if eid is agent_eid:
                return True
        return False

    def clear(self):
        self.tag = []
        if DEBUG : print("Mob Tag Cleared")

    def remove(self, agent_eid):
        if DEBUG : print("Removed Mob Tag {}".format(agent_eid))
        if self.contains(agent_eid): self.tag.remove(agent_eid)


class ComponentStoreTag(ComponentStore):
    def add(self, target_eid, agent_eid):
        if self.world.entities.get(target_eid).tid in (1002, 1005) or 0 < self.world.entities.get(target_eid).tid < 6:
            return self.addc(target_eid, CTagMob(agent_eid))
        else:
            return self.addc(target_eid, CTag(agent_eid))

    def add_replace(self, target_eid, agent_eid):
        if target_eid in self.cc:
            if type(self.get(target_eid)) is not CTagMob:
                return self.get(target_eid).change(agent_eid)
            else:
                return self.get(target_eid).add(agent_eid)
        return self.addc(target_eid, CTag(agent_eid))

    def update(self):
        for eid, act in self.all():
            if type(act) is not CTagMob:
                if act.tag is not None:
                    if self.world.living(act.tag):
                        owner = self.world.agents.get(act.tag)
                        if type(owner.active_behavior) is CBehaviorMoveAndGather:
                            if owner.active_behavior.target_eid is eid:
                                continue
                    if type(act) is not CTagMob:
                        act.abandoned()
