from constants import *
from components.cstore import ComponentStore
import data
import vector2

DEBUG = False

class CTrap:
    def __init__(self, world, agent_eid, trap):
        if world.inventories.get_required(agent_eid).item_amount(trap) >= 1:
            self.trap = trap
            self.effect = data.traps[trap][1]
            self.setup = data.traps[trap][0]
            self.pos = world.entities.get(agent_eid).pos
            self.status = RUNNING
            self.progress = 0.0
            self.owner = agent_eid

            spec = {'tid': trap,
                    'loc': self.pos, }

            self.world = world
            inv = world.inventories.get_required(agent_eid)
            inv.remove(trap, 1)
            self.eid = world.add_entity(spec)[0]
        else:
            self.status = FAILURE

    def activate(self, target_eid):
        if DEBUG: print("trap activated")
        self.world.entities.remove(self.eid)
        self.world.entities.get(target_eid).flag = self.effect

class ComponentStoreTrap(ComponentStore):
    def add(self, agent_eid, trap):
        self.addc(agent_eid, CTrap(self.world, agent_eid, trap))

    def update(self, dt):
        for eid, act in self.all():
            if act.status is FAILURE:
                self.remove_ids.add(eid)
            elif act.status is not SUCCESS:
                act.progress += dt
                if act.progress >= act.setup:
                    if DEBUG: print("trap set")
                    act.status = SUCCESS
            else:
                for close_eid, ent in self.world.entities_within_range(act.eid, 5):
                    if close_eid is not eid:
                        act.activate(close_eid)
                        self.remove_ids.add(eid)
