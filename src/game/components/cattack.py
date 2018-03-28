##########################
#  Each attack action
##########################
import random

from constants import *
import data

from components.cstore import ComponentStore
from random import randint

# module level
#from importantGame.src.game.components.cfinisher import CFinisher

DEBUG=True

class CAttack:
    def __init__(self, agent_eid, target_eid, world):
        self.target_eid = target_eid
        self.agent_eid = agent_eid

        # stats
        agent = world.entities.get_required(agent_eid)
        hp,self.cooldown,self.damage,self.range = data.combatants[agent.tid]


        # weapons! (have to update on inv update, but for now...)
        best_weapon = self.agent_best_weapon(agent_eid, world)
        self.attack = self.checkAttack(agent_eid, world)

        if best_weapon is not None:
            self.cooldown,self.damage,self.range = data.weapons[best_weapon]

        agent = world.entities.get(agent_eid)
        target = world.entities.get(target_eid)
        self.melee_dist = data.render[agent.tid]['size'] + data.render[target.tid]['size']

        self.originals = None
        self.debuff = False

        # initialize swing timer state
        self.cd_timer = 0.0
        self.status = RUNNING

    def agent_best_weapon(self, agent_eid, world):
        inv = world.inventories.get(agent_eid)
        if inv is None: return
        maxdps = 0
        maxw = None
        for wid,ct in inv.all_weapons():
            cd,dmg,range = data.weapons[wid]
            dps = (dmg[0] + dmg[1])/2.0/cd
            if dps > maxdps:
                maxdps = dps
                maxw = wid
        return maxw

    def checkAttack(self, agent_eid, world):
        inv = world.inventories.get(agent_eid)
        for i in range(3000, 3004):
            if inv.item_amount(i) > 0:
                return i
        return None


# specialize for storing this type of component
class ComponentStoreAttack(ComponentStore):
    def add(self, agent_eid, target_eid):
        return self.addc(agent_eid, CAttack(agent_eid, target_eid, self.world))
    def add_replace(self, agent_eid, target_eid):
        if agent_eid in self.cc: self.remove(agent_eid)
        return self.addc(agent_eid, CAttack(agent_eid, target_eid, self.world))


    ##########################
    #  System Update
    ##########################

    def update(self, dt, trace=None):
        for eid, act in self.all():

            if act.status == RUNNING:
                target = self.world.entities.get(act.target_eid)
                inv = self.world.inventories.get(act.agent_eid)

                if target is None:
                    act.status = INTERRUPT
               
                elif act.cd_timer <= 0:
                    # apply damage if in range
                    agent = self.world.entities.get(eid)
                    hpprior = target.hp

                    dist = (target.pos - agent.pos).magnitude()
                    if dist <= act.melee_dist + act.range:
                        if DET:
                            dmg = (act.damage[0]+act.damage[1])/2
                        else:
                            dmg = act.damage[0] + (random.random() * (act.damage[1] - act.damage[0]))
                        target.hp -= dmg
                        if ACTION_LOG and not self.world.simulation: print("[{:.2f}] {} takes {:.2f} damage from {}".format(self.world.clock, target, dmg,
                                                                                                                   self.world.entities.get(act.agent_eid),
                                                                                                  ))
                        # and reset cooldown

                        act.cd_timer = act.cooldown

                        # if the attacking mob is a crab then set a flag so that the consider function knows that
                        # the crab has successfully attacked and it should flee next.
                        mob = self.world.entities.get(eid)
                        if mob is not None and mob.tid == 5:
                            mob.flag = 'pinched'

                        # check for death
                        if target.hp < 0:
                            if target.tid is 1 and agent.tid is 1:
                                inv_mugged = self.world.inventories.get(act.target_eid)
                                item = inv_mugged.random_item()
                                if item is not 0:
                                    inv_mugged.remove(item, 1)
                                    inv.add(item, 1, self.world)
                                    print("[{:.2f}] Agent mugged for {}x {}".format(self.world.clock, 1, item))
                                else:
                                    print("[{:.2f}] Agent finished mugging".format(self.world.clock))
                                target.hp = hpprior
                                noConstantAttack = self.world.relationship.get(eid)
                                if noConstantAttack is not None:
                                    noConstantAttack.increase(target.eid)
                                    noConstantAttack.increase(target.eid)
                                self.world.tag.get(target.eid).clear()
                                self.world.entities.get(target.eid).flag = 'stun'

                            else:
                                if ACTION_LOG and not self.world.simulation: print("[{:.2f}] {} slain by {}!".format(self.world.clock, target,
                                                                                                                self.world.entities.get(act.agent_eid)
                                                                                                                ))
                                act.status = SUCCESS


                                self.trace.death(act.agent_eid, act.target_eid, self.world)
                                     # REM: disabling for current experiments

                                dead = self.world.entities.get(act.target_eid)
                                deadId = dead.tid
                                if deadId != 1:
                                    if hpprior > 0:
                                        deadTag = self.world.tag.get(act.target_eid).tag
                                        for attacker in deadTag:
                                            if self.world.living(attacker):
                                                invs = self.world.inventories.get(attacker)
                                                relationship = self.world.relationship.get(attacker)
                                                relationship.current = False
                                                invs.add(data.loot[deadId], 1, self.world)
                                                print("[{:.2f}] Agent obtained loot {}x {}".format(self.world.clock, 1,
                                                                                                       data.loot[deadId]))
                                '''   ##########fire and ice stuff ################
                                    #set flag to type ready
                                selectors = randint(0, 10)
                                if selectors > 5:
                                    if dead.breed == 'fire':
                                        selector = randint(3002, 3004)
                                        agent.flag = 'iceReady'
                                    else:
                                        selector = randint(3000, 3001)
                                        agent.flag = 'fireReady'
                                else:
                                    selector = 3005
                                    inv.add(3004, 1, self.world)
                                    agent.flag = 'ready'

                                inv.add(selector, 1, self.world)
                                #checking inventory to look for two types of attacks(ice or fire)
                                for i in range(3000, 3004):
                                    if inv.item_amount(i) > 0:
                                        if agent.flag == 'fireReady':
                                            if i > 3001:
                                                agent.flag = 'duoReady'
                                        elif agent.flag == 'iceReady':
                                            if i < 3002:
                                                agent.flag = 'duoReady'
                                    ##############################################

                                print("[{:.2f}] Agent obtained ability {}".format(self.world.clock, data.names[selector]))'''

                            self.world.entities.remove(act.target_eid)
                            if self.world.relationship.get(eid) is not None:
                                self.world.relationship.get(eid).end_action()

                            continue
                else:
                    # check if player has been debuffed
                    ent = self.world.entities.get(eid)
                    if ent.debuff is not None:
                        if act.debuff == False:
                            self.debuff(act, ent.debuff)
                        else:
                            if ent.buff_change == True:
                                self.reset_buff(act)
                                self.debuff(act, ent.debuff)
                                ent.buff_change = False
                    elif ent.debuff is None and act.debuff == True:
                        self.reset_buff(act)

                    # tick timer
                    act.cd_timer -= dt

    def debuff(self, node, debuff):
        node.originals = {node.cooldown, node.range, node.damage}
        node.cooldown += (node.cooldown * debuff)
        node.cd_timer += (node.cooldown * debuff)

        node.damage = (node.damage[0] - (node.damage[0] * debuff), node.damage[1] - (node.damage[1] * debuff))
        node.range -= (node.range * debuff)
        node.debuff = True

        if node.damage[0] < 0:
            node.damage[0] = 0
        if node.damage[1] < 0:
            node.damage[1] = 0
        if node.range < 0:
            node.range = 0

    def reset_buff(self, node):
        node.cooldown, node.range,node.damage = node.originals
        node.debuff = False