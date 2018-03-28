from constants import *
from components.cstore import ComponentStore
from components.cbehavior import *

DEBUG = True

class CThirst:
    def __init__(self, thirst):
        self.drink_lose, self.cd_drink = thirst[1]
        self.dec_thirst = self.cd_drink
        self.thirst = thirst[0]

class ComponentStoreDrink(ComponentStore):
    def add(self, agent_eid, thirst):
        return self.addc(agent_eid, CThirst(thirst))

    def add_replace(self, agent_eid, thirst):
        if agent_eid in self.cc:
            self.remove(agent_eid)
        return self.addc(agent_eid, CThirst(thirst))

    def update(self, dt):
        for eid, act in self.all():
            a = self.world.drink.get(eid)
            if a.cd_drink <= 0.0:
                if type(self.world.agents.get(eid).active_behavior) is CBehaviorMoveToEntity or type(self.world.agents.get(eid).active_behavior) is CBehaviorMoveToLocation or type(self.world.agents.get(eid).active_behavior) is CBehaviorDrink:
                    a.thirst -= a.drink_lose
                else:
                    a.thirst -= a.drink_lose/2
                a.cd_drink = a.dec_thirst
            else:
                a.cd_drink -= dt

            if a.thirst <= 0:
                print("[{:.2f}] {} died of dehydration!".format(self.world.clock, self.world.entities.get(eid)))
                self.world.entities.remove(eid)
                self.trace.dehydration(eid, self.world)