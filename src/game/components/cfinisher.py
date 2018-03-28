import random

from constants import *
import data
import gui
from components.cstore import ComponentStore

# module level
DEBUG=True

#like cinventory
class CFinisher:
    def __init__(self, agent_eid, target_eid, world):
        self.agent_eid = agent_eid
        self.target_eid = target_eid
        self.status = RUNNING
        #stats
        agent = world.entities.get_required(agent_eid)
        target = world.entities.get_required(target_eid)
        self.targetBreed = target.breed
        hp, self.cooldown, self.damage, self.ranger = data.combatants[agent.tid]
        self.melee_dist = data.render[agent.tid]['size'] + data.render[target.tid]['size']
        ###############getting my attack###################
        if agent.flag == 'ready':
            self.damage, self.ranger, self.type = data.attacks[3005]
            self.move = 3005
        else:
            powerful_attack = self.agent_type_attacks(agent_eid, world)
            self.move = powerful_attack

            if powerful_attack is not None:
                self.damage, self.ranger, self.type = data.attacks[powerful_attack]

            # if self.move == None:
            #     self.weapon = self.agent_best_weapon(agent_eid, world)
            #     if self.weapon != None:
            #         self.cooldown, self.damage, self.ranger = data.weapons[self.weapon]

        #####################################################
        self.status = RUNNING

    def agent_type_attacks(self, agent_eid, world):
        inv = world.inventories.get(agent_eid)
        if inv is None: return
        maxdps = 0
        maxw = None


        if self.targetBreed == 'fire':
            for i in range(3000, 3002):
                if inv.item_amount(i) > 0:
                    dmg, ranger, type = data.attacks[i]
                    dps = (dmg[0] + dmg[1])/2.0
                    if dps > maxdps:
                        maxdps = dps
                        maxw = i
        else:
            for i in range(3002, 3004):
                if inv.item_amount(i) > 0:
                    dmg, ranger, type = data.attacks[i]
                    dps = (dmg[0] + dmg[1])/2.0
                    if dps > maxdps:
                        maxdps = dps
                        maxw = i

        return maxw


    def agent_best_weapon(self, agent_eid, world):
        inv = world.inventories.get(agent_eid)
        if inv is None: return
        maxdps = 0
        maxw = None
        for wid,ct in inv.all_weapons():
            cd,dmg,ranger = data.weapons[wid]
            dps = (dmg[0] + dmg[1])/2.0
            if dps > maxdps:
                maxdps = dps
                maxw = wid
        return maxw


class ComponentStoreFinisher(ComponentStore):
    def add(self, agent_eid, target_eid):
        return self.addc(agent_eid, CFinisher(agent_eid, target_eid, self.world))
    def add_replace(self, agent_eid, target_eid):
        if agent_eid in self.cc: self.remove(agent_eid)
        return self.addc(agent_eid, CFinisher(agent_eid, target_eid, self.world))

    def update(self, dt):
        for eid, act in self.all():

            if act.status == RUNNING:
                target = self.world.entities.get(act.target_eid)
                if target is None:
                    act.status = INTERRUPT

                agent = self.world.entities.get(eid)
                inv = self.world.inventories.get(act.agent_eid)

                if agent.flag != 'stun':
                    # apply damage if in range

                    dist = (target.pos - agent.pos).magnitude()
                    if dist <= act.melee_dist + act.ranger:
                        if DET:
                            dmg = (act.damage[0] + act.damage[1]) / 2
                        else:
                            dmg = act.damage[0] + (random.random() * (act.damage[1] - act.damage[0]))
                        target.hp -= dmg
                        if act.move != None:
                            if ACTION_LOG and not self.world.simulation: print("[{:.2f}] {} takes {:.2f} super damage with {} from {}".format(self.world.clock, target, dmg, data.names[act.move], self.world.entities.get(act.agent_eid),))

                        ##########setting everything back to normal state##############
                            inv.remove(act.move, 1)

                        agent.flag = 'idle'
                        act.status = INTERRUPT
                        #############################################################
                        # check for death
                        if target.hp < 0:
                            if ACTION_LOG and not self.world.simulation: print(
                                "[{:.2f}] {} super slain by {}!".format(self.world.clock, target,
                                                                      self.world.entities.get(act.agent_eid)
                                                                      ))

                            self.trace.death(act.agent_eid, act.target_eid, self.world)
                            dead = self.world.entities.get(act.target_eid)
                            deadId = dead.tid

                            deadTag = self.world.tag.get(act.target_eid).tag
                            for attacker in deadTag:
                                if self.world.living(attacker):
                                    invs = self.world.inventories.get(attacker)
                                    invs.add(data.loot[deadId], 1, self.world)
                                    print("[{:.2f}] Agent obtained loot {}x {}".format(self.world.clock, 1,
                                                                                       data.loot[deadId]))

                            self.world.entities.remove(act.target_eid)
                            act.status = SUCCESS

            else:
                act.status = SUCCESS