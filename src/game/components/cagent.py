##########################
#  Agent Variables
##########################

import random

from components.cbehavior import *
from components.reasoning.goals import Goal_HasItemType, GoalNode
import data
import constants

# module level
DEBUG = True

# component storage and system update class
class ComponentStoreAgent(ComponentStore):
    def update(self, dt, trace=None):
        """Agent update, apply proposed decisions."""
        for eid, a in self.all():
            # agent updates are specialized by subclasses
            a.update(self.world, dt, trace)

class Cursor:
    def __init__(self):
        self.bindings_used = set()
        self.has_more_bindings = False

    def already_done(self, behavior):
        return behavior.target in self.bindings_used

    def mark(self, behavior):
        self.bindings_used.add(behavior.target)

    def done(self): return not self.has_more_bindings
    def next(self, agent, world): return agent.consider_cursored(world, 0, self)

class Cursor2:
    def __init__(self, options):
        self.options = options

    def done(self): return len(self.options) == 0

    def next(self):
        slice = self.options[0]
        self.options = self.options[1:]
        return slice

##############################################################
# Base agent class, with general-purpose world update method
##############################################################

class CAgent:
    """Base agent class"""
    def __init__(self, eid, goals):
        self.eid = eid
        self.goals = goals
        # for a in self.goals[0].give_needed():
        #     print("ID: {}  CT: {}".format(a.tid,a.ct))

        self.active_behavior = None
        self.proposal = None

    ########### action selection ##############

    def consider(self, world, dt, trace=None, n=1):
        pass

    def consider_cursored(self, world, dt, cursor=None):
        pass

    ########### goals ##############

    def met_goals(self, world):
        return all((g.satisfied(world, self.eid) for g in self.goals))

    def goal_rewards(self, world):
        return sum((g.reward(world, self.eid) for g in self.goals))

    def string_goals(self, world):
        s = ""
        for g in self.goals:
            s += g.to_string(world, self.eid)
        return s

    ########### world update ##############

    def update(self, world, dt, trace=None):
        """Agent update, apply proposed decisions."""
        #agent = world.drink.get(self.eid)
        #if agent is None:
         #   world.drink.add(self.eid)
        #check if alive first
        # agent = world.entities.get(self.eid)
        # if agent.hp < 0
        for a in self.goals:
            a.update(self.eid,world)


        # new proposal!
        if self.proposal is not None:
            # clear old behavior, if active

            if self.active_behavior is not None:
                #print(self.active_behavior.status)
                if DEBUG: print("[{:.2f}] Agent: replacing active {}".format(world.clock, self.active_behavior.short_status()))
                world.behaviors.remove(self.eid, self.active_behavior.status, world)
            # apply new
            if DEBUG and not world.simulation: print("[{:.2f}] Agent: starting {}".format(world.clock, self.proposal))
            self.active_behavior = self.proposal
            self.active_behavior.status = RUNNING
            self.proposal = None
            world.behaviors.addc(self.eid, self.active_behavior, True)
            return

        # got here, no proposal, check for reaping
        if self.active_behavior is not None and self.active_behavior.status != RUNNING:
            if DEBUG: print("{} Agent: reaping active {}".format(world.clock, self.active_behavior.short_status()))
            #if trace: trace.end_update(world, self.eid, self.active_behavior.sig(), self.active_behavior.status)
            world.behaviors.remove(self.eid, self.active_behavior.status, world)
            self.active_behavior = None
            return

        # has no current behavior or still running current behavior
        return

##############################################################
# Behavior Evaluation Agent
##############################################################

class CAgent_BehaviorEval(CAgent):
    """Incrementally generate, evaluate and choose best behavior."""

    def __init__(self, eid, goals):
        super().__init__(eid, goals)

        # goal planning
        self.planner = GoalNode("WIN")
        s = self.planner.add_strategy(None)
        for g in goals:
            s.add_precedent(GoalNode(g))


    ########### behavior generation/evaluation ##############

    def consider(self, world, dt, n=1):
        """Return the top n options at this time. Return all if n is None."""

        # generate all candidate behaviors: gather, fight, flee, craft
        candidates = []
        agent = world.entities.get(self.eid)
        a = world.drink.get(self.eid)
        inv = world.inventories.get(self.eid)

        if (inv.item_amount(2012) is 0 and inv.item_amount(2011) is 0 and inv.item_amount(2018) is 0) and a.thirst < .3:
            a_mem = world.memory.get(self.eid)
            target_eid = a_mem.remember(1005)
            if target_eid is not None:
                candidates.append(CBehaviorMoveAndGather(self.eid, target_eid))

        for eid,ent in world.entities_within_range(self.eid, data.awareness[data.AGENT_TYPE_ID]):
            if ent.tid in data.gatherable:
                if world.tag.get(ent.eid).tag is self.eid or world.tag.get(ent.eid).firmness is not 'Hard':
                    candidates.append(CBehaviorMoveAndGather(self.eid, eid))
            if ent.tid in data.combatants:
                candidates.append(CBehaviorFlee(self.eid, eid))
                candidates.append(CBehaviorMoveAndAttack(self.eid, eid))
                if world.trap.get(self.eid):
                    candidates.append(CBehaviorLure(self.eid, eid, world.trap.get(self.eid).eid))
                candidates.append(CBehaviorTrap)
        for iclass in data.recipes.keys():
            candidates.append(CBehaviorCraft(self.eid, iclass))

        for idf in inv.all():
            if idf[0] in data.edibles:
                candidates.append(CBehaviorEat(self.eid, idf[0]))
            if idf[0] in data.hp_items:
                candidates.append(CBehaviorHeal(self.eid, idf[0]))
            if idf[0] in data.drinks:
                candidates.append(CBehaviorDrink(self.eid, idf[0]))

        # evaluate
        ent = world.entities.get(self.eid)
        evaluated = [(b, self.evaluate(b, world, ent)) for b in candidates]

        # sort
        evaluated.sort(key=lambda e: e[1], reverse=True)
        # print("Sorted: {}".format(", ".join(("{}: {}".format(s,b.short()) for b,s in evaluated))))

        if len(evaluated) > 0 and evaluated[0][1] > 0:
            # set next behavior for self
            if agent.flag == 'stun' and type(self.active_behavior) != CBehaviorStun:
                self.proposal = CBehaviorStun(self.eid)
            elif evaluated[0][0] != self.active_behavior:
                self.proposal = evaluated[0][0]
                if ACTION_LOG and not world.simulation: print(
                    "[{:.2f}] {} selecting {}".format(world.clock, ent, self.proposal.short()))

                # return requested top n candidates (to support cursor)
                if n is None: return [b for b, s in evaluated]
                return [b for b, s in evaluated][:n]

        # no candidates found, try explore
        if self.active_behavior is None or self.active_behavior.status != RUNNING and agent.flag != 'stun':
            # not doing anything, nothing to do
            self.proposal = CBehaviorMoveToLocation(self.eid, world.randloc())

        if type(self.active_behavior) is CBehaviorMoveAndGather:
            if world.entities.get(self.active_behavior.target_eid) is not None and world.entities.get(self.active_behavior.target_eid).tid != 1005:
                owner = world.tag.get(self.active_behavior.target_eid)
                if owner is not None:
                    owner = owner.tag
                if owner is None:
                    world.tag.add_replace(self.active_behavior.target_eid, self.eid)
            else:
                if world.tag.get(self.active_behavior.target_eid) is not None:
                    if not world.tag.get(self.active_behavior.target_eid).contains(self.eid):
                        world.tag.add_replace(self.active_behavior.target_eid, self.eid)

        if type(self.active_behavior) is CBehaviorMoveAndAttack:
            if world.tag.get(self.active_behavior.target_eid) is not None:
                if not world.tag.get(self.active_behavior.target_eid).contains(self.eid):
                    world.tag.add_replace(self.active_behavior.target_eid, self.eid)

        return None

    def evaluate(self, behavior, world, agent, dirty=False):
        if type(behavior) is CBehaviorMoveAndAttack:

            # check goals, check if monster drops item needed, add reward, calculate cost, calculate reward/cost and pump up the value
            reward = 0
            cost = 1
            dtid = data.loot[world.entities.get(behavior.target_eid).tid]
            a=world.agents.get(agent.eid)
            for b in a.goals:
                c_l=b.tree_leaves()
                if(len(c_l)==0):
                    if len(b.needed)==0:
                        if b.tid == dtid:
                            reward =b.value
                            cost = ((world.entities.get(behavior.target_eid).pos - agent.pos).magnitude() / data.movement_speed[data.AGENT_TYPE_ID])
                else:
                    for c in c_l:
                        if len(c.needed)==0:
                            if c.tid==dtid:
                                reward= c.value
                                cost = ((world.entities.get(behavior.target_eid).pos - agent.pos).magnitude() / data.movement_speed[data.AGENT_TYPE_ID])
            if reward != 0:
                return 100 + reward / cost


            action_attack = world.attacking.get(behavior.target_eid)
            if action_attack is not None and action_attack.target_eid == agent.eid:
            # when I'm being attacked...
                # fight or flee, so pump up the value
                pct_hp = (agent.hp / data.combatants[agent.tid][0])
                # if world.entities.get(behavior.target_eid).tid is 1 and not world.relationship.get(agent.eid).current:
                #     print("under attack")
                #     world.relationship.get(agent.eid).decrease(behavior.target_eid)
                #     world.relationship.get(agent.eid).begin_action()
                return 100.0 + ((pct_hp - 0.25) * 10.0)

            # extra check for co-op if the mob is attacking someone else, has loot of some sort, and the fight is not almost over as in mob is not almost dead or other agent is not almost dead

            if action_attack is not None and world.entities.get(behavior.target_eid).tid > 2:
                    # when the mob is attacking someone else
                    pct_hpMob = (world.entities.get(behavior.target_eid).hp / data.combatants[world.entities.get(behavior.target_eid).tid][0])
                    if pct_hpMob < 0.4:
                        return 0
                    if world.tag.get(behavior.target_eid).tag is not None:
                        for others in world.tag.get(behavior.target_eid).tag:
                            if world.entities.get(others) is not None:
                                hp = world.entities.get(others).hp
                                hp = hp / data.combatants[world.entities.get(others).tid][0]
                                reward += world.relationship.get(agent.eid).get(others)
                                if hp < 0.3:
                                    return 0
                    cost = (world.entities.get(behavior.target_eid).pos - agent.pos).magnitude() / data.movement_speed[data.AGENT_TYPE_ID] * 75
                    # reward offset, making it slightly more likely that they'll help each other, just to get loot
                    reward += world.entities.get(behavior.target_eid).tid
                    if world.entities.get(behavior.target_eid).flag == 'stun':
                        reward += 10
                    return reward / cost

            # relationship check
            # if I really don't like this guy, I might attack him if he has something I want and
            # how much hp he has left, how far away he is, how much hp I have left
            if world.relationship.get(agent.eid).get(behavior.target_eid) is -5:
                    # print("considering killing")
                    reward = abs(world.relationship.get(agent.eid).get(behavior.target_eid)) / 5
                    possible_rewards = world.inventories.get(behavior.target_eid)
                    for iid, ct in possible_rewards.all():
                        if iid is gnode.tid:
                            reward += gnode.value
                    cost += (world.entities.get(behavior.target_eid).pos - agent.pos).magnitude() / data.movement_speed[data.AGENT_TYPE_ID] * 75
                    cost += world.entities.get(behavior.target_eid).hp - agent.hp

                    # print("reward: {}, cost: {}".format(reward, cost))

                    if cost < 1:
                        cost = 1
                    return 100 + (reward / cost)



        elif type(behavior) is CBehaviorFlee:
            # when I'm being attacked...
            action_attack = world.attacking.get(behavior.target_eid)
            if action_attack is not None and action_attack.target_eid == agent.eid:
                # fight or flee, so pump up the value
                pct_hp = (agent.hp / data.combatants[agent.tid][0])
                return 100.0 + ((0.25 - pct_hp) * 10.0)

        elif type(behavior) is CBehaviorMoveAndGather:
            if dirty:
                tid = behavior.target_eid
            else:
                tgt = world.entities.get(behavior.target_eid)
                tid = tgt.tid

            inv = world.inventories.get(agent.eid)
            a   = world.agents.get(agent.eid)
            # EST: at what cost?
            cost = data.gatherable[tid][0]  # gather time
            reward = 0
            if tid  >= 5000:
                tid -= 3000



            if tid in (1002, 1005, 1007, 2011, 2012, 2018):
                a= world.drink.get(agent.eid)
                if inv.item_amount(2012)==0 and inv.item_amount(2011)==0 and inv.item_amount(2018)==0:
                    if a.thirst<.6:
                        reward += 5
            # EST: does this progress this goal? how much?
            if tid == 1006 or tid== 2016:
                # if it is a bush
                if inv.item_amount(2016) < 2:
                    # and we do not have at least 2 of either berry type
                    reward += 0.15
                    if agent.hp < 1.0:
                        reward += data.combatants[agent.tid][0] - agent.hp

            if tid in (1004, 1007, 1010, 2009, 2010, 2019, 2020):
                a = world.eat.get(agent.eid)
                if inv.item_amount(2009) < 2 or inv.item_amount(2010) < 2 or inv.item_amount(2019) < 2 or inv.item_amount(2020) < 2:
                    reward += 0.15
                    if a.food < 0:
                        if a.weak_timer >= 3.0:
                            reward += 4.0
                        elif a.weak_timer >= 2.0:
                            reward += 3.0
                        else:
                            reward += 2.0

            a = world.agents.get(agent.eid)
            for a in a.goals:
                for b in a.tree_leaves():
                    if len(b.needed)==0:  # this means that agent is doing winning goal
                        gnode=b
                        for dtid, dmin, dmax, drate in data.gatherable[tid][1]:
                            if gnode.tid == dtid:
                                # tgt drops goal item
                                reward = gnode.value * (((dmin + dmax) / 2) / gnode.ct) * drate
                    else:
                        needed=b.needed
                        for gnode in needed:
                            for dtid, dmin, dmax, drate in data.gatherable[tid][1]:
                                if gnode.tid == dtid:
                                    # tgt drops goal item
                                    reward = gnode.value * (((dmin + dmax) / 2) / gnode.ct) * drate


            # if the behavior is being passed in with a fake entity don't run these evaluations.
            if not dirty:
                cost += ((tgt.pos - agent.pos).magnitude() / data.movement_speed[data.AGENT_TYPE_ID])
                if tid in data.risk:
                    risk = data.risk[tid]
                    cost += ((risk[0]+risk[1])/2) * risk[2] * (data.gatherable[tid][0]/risk[3])

                # relationship check
                # if someone I don't like is going for something and I'm closer than they are
                # add more reward
                tgttag = world.tag.get(tgt.eid)
                if tgttag is not None and tgttag.tag is not self.eid:
                    relationship = world.relationship.get(self.eid).get(tgttag)
                    if relationship < 0:
                        otherDist = (tgt.pos - (world.entities.get(tgttag.tag).pos)).magnitude()
                        selfDist = (tgt.pos - agent.pos).magnitude()
                        if selfDist < otherDist:
                            reward += abs(relationship)

                # if inventory is full then find the lowest reward items in the inventory currently and compare against
                # candidate item.
                if inv.count == inv.item_limit:
                    inv_reward = []
                    for iid, ct in inv.item_counts.items():
                        item_reward = 0
                        item_reward += self.evaluate(CBehaviorMoveAndGather(agent.eid, iid+3000), world, agent, dirty=True)

                        for _ in range(ct):
                            inv_reward.append((iid, item_reward / ct))


                    inv_reward.sort(key=lambda e: e[1], reverse=True)
                    for _ in range(len(data.gatherable[tgt.tid][1])):
                        if reward/cost > inv_reward[-1][1]:
                            behavior.drop.append(inv_reward.pop()[0])
                    if len(behavior.drop) == 0:
                        return 0

            return reward / cost

        elif type(behavior) is CBehaviorCraft:
            # EST: how much progress?
            reward = 0
            # done assessing goals, if there is reward, then calculate cost and return
            b=world.agents.get(agent.eid)
            for a in b.goals:
                for c,prev in a.all_nodes(a.strategy):
                    if c.tid==behavior.item_typeid:
                        if behavior.enabled(world,self.eid):
                            reward=1
                    elif a.tid==behavior.item_typeid:
                        if behavior.enabled(world,self.eid):
                            reward=1
                    if reward>0:
                        cost = data.recipes[behavior.item_typeid][0]  # crafting time
                        return reward / cost

        elif type(behavior) is CBehaviorEat:
            a = world.eat.get(self.eid)
            partRestored = data.edibles[behavior.edible_iid][0]
            reward = 0.0

            if a.food <= 0.0:
                if a.weak_timer >= 3.0:
                    reward += (a.food + partRestored)*4
                elif a.weak_timer >= 2.0:
                    reward += (a.food + partRestored)*3
                else:
                    reward += (a.food + partRestored)*2
            elif a.food < 0.4:
                reward += (a.food + partRestored)*1

            return reward

        #Heal behavior now replaces eat behavior so this evaluation is just a copy of the old eat behavior.
        elif type(behavior) is CBehaviorHeal:
            pct_hp = (agent.hp / data.combatants[agent.tid][0])
            h_hp, h_cd = data.hp_items[behavior.heal_iid]
            pct_ediblehp = (h_hp / data.combatants[agent.tid][0])
            action_heal = world.heal.get(behavior.agent_eid)
            if action_heal == None or action_heal.status == SUCCESS:
                if pct_hp <= .375:
                    return (pct_hp + pct_ediblehp) * 1000
            else:
                return -100.0

        elif type(behavior) is CBehaviorDrink:
            reward = 0.0
            if behavior.drink_iid == 2018:
                reward += self.evaluate(CBehaviorEat(agent.eid, 2020), world, agent)
            partRestored = data.drinks[behavior.drink_iid]
            if world.drink.get(behavior.agent_eid).thirst <= 0.3:
                reward +=(world.drink.get(behavior.agent_eid).thirst + partRestored)*2
            return reward

        elif type(behavior) is CBehaviorTrap:
            inv = world.inventories.get(behavior.agent_eid)
            risk = 0
            possible = 0
            for x in data.traps:
                possible += math.floor(inv.item_amount(x))
            if possible == 0:
                return 0
            risk += (world.entities.get(behavior.target_eid).pos - agent.pos).magnitude()
            if risk > 300 or risk < 100:
                return 0
            return possible / risk

        elif type(behavior) is CBehaviorLure:
            return 1000

        # nothing useful found
        return 0

