from constants import *
import data
import vector2
from components.cbehavior import *

from components.cstore import ComponentStore

DEBUG = False

class CRelation:
    def __init__(self, world, agent_eid):
        self.relationships = {}
        self.me = agent_eid
        for eid, ent, in world.agents_within_range(agent_eid, 50):
            self.add(eid)

        # save whether or not the previous action was attacking or gathering so it won't change relationships too many times
        self.current = False

    def get(self, other_agent_eid):
        if self.relationships.get(other_agent_eid) is not None:
            return self.relationships[other_agent_eid]
        return 0

    def add(self, other_agent_eid):
        if self.relationships.get(other_agent_eid) is None:
            self.relationships[other_agent_eid] = 0

    def increase(self, other_agent_eid):
        if DEBUG: print("anger release")
        if self.relationships[other_agent_eid] is None:
            self.add(other_agent_eid)
        if self.relationships[other_agent_eid] < 5:
            self.relationships[other_agent_eid] += 1
            if DEBUG: print("{} + {} : {}".format(self.me, other_agent_eid, self.relationships[other_agent_eid]))

    def decrease(self, other_agent_eid):
        if self.relationships[other_agent_eid] is None:
            self.add(other_agent_eid)
        if self.relationships[other_agent_eid] > -5:
            self.relationships[other_agent_eid] -= 1
            if DEBUG: print("{} - {} : {}".format(self.me, other_agent_eid, self.relationships[other_agent_eid]))

    def begin_action(self):
        self.current = True

    def end_action(self):
        self.current = False


class ComponentStoreRelation(ComponentStore):
    def add(self, world, agent_eid):
        return self.addc(agent_eid, CRelation(world, agent_eid))

    def update(self):
        for agent_eid, c in self.all():
            for eid, ent in self.world.agents_within_range(agent_eid, 50):
                c.add(eid)

            agent = self.world.agents.get(agent_eid)
            if type(agent.active_behavior) is CBehaviorMoveAndGather:
                tag = self.world.tag.get(agent.active_behavior.target_eid)
                if tag is not None:
                    if tag.tag is not agent_eid and tag.firmness is 'Hard' and tag.tag is not None and not c.current:
                        if DEBUG: print("lost race")
                        c.decrease(tag.tag)
                    if self.world.entities.get(agent.active_behavior.target_eid).tid == 1005:
                        if tag.contains(agent_eid) and not c.current:
                            for x in tag.tag:
                                if x is not agent_eid:
                                    if DEBUG: print("peaceful waters")
                                    c.increase(x)
                                    if self.world.relationship.get(x) is not None:
                                        self.world.relationship.get(x).increase(agent_eid)
                            c.begin_action()


            elif type(agent.active_behavior) is CBehaviorMoveAndAttack:
                tag = self.world.tag.get(agent.active_behavior.target_eid)
                if tag is not None:
                    if len(tag.tag) > 1:
                        for eid in tag.tag:
                            if eid is not agent_eid and self.world.living(eid) and not c.current:
                                if DEBUG: print("co-op")
                                c.increase(eid)
                            c.begin_action()

                target = self.world.entities.get(agent.active_behavior.target_eid)
                if target is not None and target.tid is 1 and not c.current:
                    if DEBUG: print("under attack")
                    c.decrease(target.eid)
                    c.begin_action()

            else:
                c.end_action()