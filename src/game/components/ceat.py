from constants import *
from components.cstore import ComponentStore
from components.cbehavior import *

DEBUG=True

class CEat:
    def __init__(self,hunger,world):
        self.food_lost, self.cd_hunger = hunger[1]
        self.dec_hunger = self.cd_hunger
        self.food = hunger[0]
        self.weak_timer = 0.0
        self.weak_state = 0

class ComponentStoreEat(ComponentStore):
    def add(self,agent_eid, hunger):
        return self.addc(agent_eid,CEat( hunger, self.world))

    def add_replace(self,agent_eid,hunger):
        if agent_eid in self.cc:
            self.remove(agent_eid)
        return self.addc(agent_eid, CEat(hunger, self.world))

    def update(self, dt):
        for eid, act in self.all():
            a = self.world.eat.get(eid)
            if a.cd_hunger <= 0.0:
                a.food -= a.food_lost
                a.cd_hunger = a.dec_hunger
            else:
                a.cd_hunger -= dt

            if a.food <= 0:
                a.food = 0
                a.weak_timer +=dt

                #DELETE_Stage1. Hunger state 1 applies no debuff, but states 2 and 3 reduce player efficiency by 25%
                #               and 50 % respectively..
                if a.weak_state == 0 and (a.weak_timer >= 1.0 and a.weak_timer <= 2.0):
                    a.weak_state = 1
                    print("[{:.2f}] agent enters hunger state {}".format(self.world.clock, a.weak_state))
                elif a.weak_state == 1 and (a.weak_timer > 2.0 and a.weak_timer <= 3.0):
                    a.weak_state = 2
                    agent = self.world.entities.get(eid)
                    agent.debuff = 0.25
                    agent.buff_change = True
                    print("[{:.2f}] agent enters hunger state {}".format(self.world.clock, a.weak_state))
                elif a.weak_state == 2 and a.weak_timer > 3.0:
                    a.weak_state = 3
                    agent = self.world.entities.get(eid)
                    agent.debuff = 0.5
                    agent.buff_change = True
                    print("[{:.2f}] agent enters hunger state {}".format(self.world.clock, a.weak_state))