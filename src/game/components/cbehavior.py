##########################
#  Behaviors and Actions
##########################
import random, math

from constants import *
from vector2 import vector2
import data

from components.cstore import ComponentStore

# module level
DEBUG=True

# component storage and system update class
class ComponentStoreBehavior(ComponentStore):
    # system update, specialized by derived behavior class
    def update(self, dt):
        for eid, b in self.all():
            b.update(eid, self.world, dt)
            if b.status != RUNNING:
                testEntity = self.world.entities.get(eid)
                if testEntity.tid != 1:
                    agent = self.world.mob.get(eid)
                else:
                    agent = self.world.agents.get(eid)
                self.status = SUCCESS
    # alternative remove to include cleanup
    def remove(self, eid, status, world):
        b = self.get(eid)
        b.cleanup(eid, world)
        super().remove(eid, status, True)

##########################
# Base Behavior
##########################

class CBehavior:
    def __init__(self):
        self.reset()

    def update(self, agent, world, dt, trace=None):
        pass

    def reset(self):
        self.status = RUNNING

    def cleanup(self, eid, world):
        pass

class CBehaviorNoOp(CBehavior):
    def __str__(self):
        return "No-op"

    def short(self):
        return "N"

##########################
# Flee Behavior
##########################

class CBehaviorFlee(CBehavior):
    def __init__(self, agent_eid, target_eid):
        super().__init__()
        self.agent_eid = agent_eid
        self.target_eid = target_eid

    def update(self, agent_eid, world, dt, trace=None):
        if self.status == RUNNING:
            action_attack = world.attacking.get(self.target_eid)
            if action_attack is None:
                # not being attacked, if we were
                if world.moving.get(agent_eid) is not None:
                    world.moving.remove(agent_eid)
                self.status = SUCCESS
                return

            # update direction each frame
            agent = world.entities.get(agent_eid)
            target = world.entities.get(self.target_eid)
            flee_vector = (agent.pos - target.pos) * 100

            # DELETE_S1. data.attack_speed was being passed in instead of movement speed. Unsure if intentional. Has
            #            been changed to movement speed.
            world.moving.add_replace(agent_eid, flee_vector, data.attack_speed[agent.tid], 0)

    def cleanup(self, eid, world):
        # make sure actions are gone
        if world.moving.get(eid) is not None:
            world.moving.remove(eid)

    def sig(self): return str(self)

    def __str__(self):
        return "(flee {} {})".format(self.agent_eid, self.target_eid)

    def short(self):
        return "F{}".format(self.target_eid)

    def short_status(self):
        return "F{}-{}".format(self.target_eid, self.status)

    def __eq__(self, other):
        return other.__class__ == self.__class__ and self.target_eid == other.target_eid

##########################
# Move and Gather Behavior
##########################

class CBehaviorMoveAndGather(CBehavior):
    def __init__(self, agent_eid, target_eid,):
        super().__init__()
        self.agent_eid = agent_eid
        self.target_eid = target_eid
        self.drop = []

    # specializing here, but stay stateless!
    def update(self, agent, world, dt, trace=None):
        action_gather = world.gathering.get(agent)
        if action_gather:
            if action_gather.status != RUNNING:
                # gathering done, may or may not have worked
                world.gathering.remove(agent)
                self.status = action_gather.status
                #print("move-and-gather done")
            # else gathering in progress, done here either way
            return

        action_move = world.moving.get(agent)
        if action_move:
            if action_move.status == SUCCESS:
                # move done, at location for gather
                world.moving.remove(agent)
                world.gathering.add(agent, self.target_eid)
                print("[{:.2f}] added gather, status {}".format(world.clock, world.gathering.get(agent).status))
            elif action_move.status == FAILURE:
                # couldn't move there, bail out
                world.moving.remove(agent)
                print("moving failed")
                self.status = FAILURE
            elif not world.gathering.available(self.target_eid):
                # move still running, but lost availability
                world.moving.remove(agent)
                print("node not available")
                self.status = FAILURE
            # else moving in progress, done here either way
            return

        if self.drop != None:
            inv = world.inventories.get(agent)
            for iid in self.drop:
                inv.drop(iid, 1, world)
                print("[{:.2f}] Agent dropped 1x {}".format(world.clock, iid))

        # not moving yet
        a = world.entities.get(agent)
        t = world.entities.get(self.target_eid)
        dist = data.render[a.tid]['size'] + data.render[t.tid]['size']
        world.moving.add(agent, t.pos, data.movement_speed[a.tid], dist)

    def cleanup(self, eid, world):
        # make sure actions are gone
        if world.moving.get(eid) is not None:
            world.moving.remove(eid)
        if world.gathering.get(eid) is not None:
            world.gathering.remove(eid)

    ################# reasoning about this behavior #####################

    @staticmethod
    def target_eids_for_agent(agent_ent, world):
        for eid,ent in world.entities_within_range(agent_ent.eid, data.awareness[agent_ent.tid]):
            if ent.tid in data.gatherable:
                yield ent.eid

    # @staticmethod
    # def node_types_drop_item(iid):
    #     """Return list of node types that drop this item."""
    #     node_typeids = []
    #     for tid,(duration,drops) in data.gatherable.items():
    #         if iid in (dropid for dropid,min,max,prob in drops):
    #             node_typeids.append(tid)
    #     return node_typeids
    #
    # def estimate_cost(self, aid, world):
    #     """Return an estimate of the time this action would take."""
    #     tgt = world.entities.get(self.target_eid)
    #     aent = world.entities.get(aid)
    #     return (aent.pos - tgt.pos).magnitude() / aent.movement_speed()

    ################# debug display #####################

    def sig(self): return str(self)

    def __str__(self):
        return "(gather {} {})".format(self.agent_eid, self.target_eid)

    def short(self):
        return "G{}".format(self.target_eid)

    def short_status(self):
        return "G{}-{}".format(self.target_eid, self.status)

    def __eq__(self, other):
        return other.__class__ == self.__class__ and self.target_eid == other.target_eid


##########################
# Move to Location Behavior
##########################

class CBehaviorMoveToLocation(CBehavior):
    def __init__(self, agent_eid, loc):
        super().__init__()
        self.agent_eid = agent_eid
        self.loc = loc

    # specializing here, but stay stateless!
    def update(self, agent_id, world, dt, trace=None):
        action_move = world.moving.get(agent_id)
        if action_move:
            if action_move.status != RUNNING:
                # move done, may or may not have worked
                agent = world.entities.get(agent_id)
                if agent.flag == 'leash':
                    agent.flag = 'idle'
                world.moving.remove(agent_id)
                self.status = action_move.status
            # else moving in progress, done here either way
            return

        # not moving yet
        a = world.entities.get(agent_id)
        if a.flag == 'leash':
            world.moving.add(agent_id, self.loc, data.movement_speed[a.tid]*3, 0)
        else:
            world.moving.add(agent_id, self.loc, data.movement_speed[a.tid], 0)

    ################# debug display #####################

    def cleanup(self, eid, world):
        if world.moving.get(eid) is not None:
            world.moving.remove(eid)

    def sig(self):
        return str(self)

    def __str__(self):
        return "(move {})".format(self.agent_eid)

    def short(self):
        return "M{}".format(self.loc)

    def short_status(self):
        return "M{}-{}".format(self.loc, self.status)

    def __eq__(self, other):
        return other.__class__ == self.__class__ and self.loc == other.loc

##########################
# Move to Entity Behavior
##########################

class CBehaviorMoveToEntity(CBehavior):
    def __init__(self, agent_eid, target, speed):
        super().__init__()
        self.agent_eid = agent_eid
        self.target = target
        self.speed = speed

    # specializing here, but stay stateless!
    def update(self, agent_id, world, dt, trace=None):
        action_move = world.moving.get(agent_id)
        if action_move:
            if action_move.status != RUNNING:
                # move done, may or may not have worked
                world.moving.remove(agent_id)
                self.status = action_move.status
            # else moving in progress, done here either way
            return

        # not moving yet
        a = world.entities.get(agent_id)
        t = world.entities.get(self.target)
        dist = data.render[a.tid]['size'] + data.render[t.tid]['size']
        world.moving.add(agent_id, t.pos, self.speed, dist)

##########################
# Craft Behavior
##########################

class CBehaviorCraft(CBehavior):
    def __init__(self, agent_eid, item_typeid):
        super().__init__()
        self.agent_eid = agent_eid
        self.item_typeid = item_typeid
        self.apple=0
    def enabled(self, world, agent_id):
        inv = world.inventories.get(agent_id)
        if inv is not None:
            for iclass,ct in data.recipes[self.item_typeid][1]:
                if inv.item_amount(iclass) < ct:
                    return False
        return True

    def remaining(self, world, agent_id):
        inv = world.inventories.get(agent_id)
        if inv is not None:
            for iclass,ct in data.recipes[self.item_typeid][1]:
                amt = inv.item_amount(iclass)
                if amt < ct:
                    # need more of this
                    yield iclass,ct-amt

    # specializing here, but stay stateless!
    def update(self, agent_id, world, dt, trace=None):
        action_craft = world.crafting.get(agent_id)
        if action_craft:
            if action_craft.status != RUNNING:
                # craft done, may or may not have worked
                world.crafting.remove(agent_id)
                self.status = action_craft.status
            # else crafting in progress, done here either way
            return

        # not started yet
        self.apple+=1
        if(self.apple==1):  ##QUICK FIX FOR BEHAVIOR
            world.crafting.add(agent_id, self.item_typeid)

    def __str__(self):
        return "(craft {} {})".format(self.agent_eid, self.item_typeid)

    def sig(self):
        return str(self)

    def short(self):
        return "C{}".format(self.item_typeid)

    def short_status(self):
        return "C{}-{}".format(self.item_typeid, self.status)

    def __eq__(self, other):
        return other.__class__ == self.__class__ and self.item_typeid == other.item_typeid

    def __ne__(self, other): return not self.__eq__(other)

##########################
# Move and Attack Behavior
##########################

class CBehaviorMoveAndAttack(CBehavior):
    def __init__(self, agent_eid, target_eid):
        super().__init__()
        self.agent_eid = agent_eid
        self.target_eid = target_eid

    # specializing here, but stay stateless!
    def update(self, agent_eid, world, dt, trace=None):
        agent = world.entities.get(agent_eid)
        target = world.entities.get(self.target_eid)

        if target == None:
            self.status = INTERRUPT

        elif self.status == RUNNING:
            action_attack = world.attacking.get(agent_eid)
            power = world.finisher.get(agent_eid)
            inv = world.inventories.get(agent_eid)

            ###############conditionals##############
            stun = False
            weak = False
            strongTarget = False
            match = False
            ########stun conditional###########
            if inv.item_amount(3004) > 0:
                stun = True
            if agent.hp < 1.3:
                weak = True
            #################################

            if target.tid == 3 or target.tid == 4 or target.tid == 1:
                strongTarget = True

            if agent.flag == 'iceReady' and target.breed == 'ice':
                match = True
            elif agent.flag == 'fireReady' and target.breed == 'fire':
                match = True
            #setting the stunner
            if weak and stun:
                target.flag = 'stun'

            if agent.flag == 'stun':
                self.status = INTERRUPT

            if agent.flag == 'leash':
                self.status = INTERRUPT

            #######################################
                
            if (agent.flag == 'duoReady' or match) and strongTarget:
                if action_attack is not None:
                    world.attacking.remove(agent_eid)
                if power is None:
                    target = world.entities.get(self.target_eid)
                    if ACTION_LOG and not world.simulation:
                        print("[{:.2f}] {} super attacking {}".format(world.clock, agent, target))
                    power = world.finisher.add(agent_eid, self.target_eid)
                    world.moving.add_replace(agent_eid, target.pos, data.attack_speed[agent.tid], power.melee_dist)

                if power.status != RUNNING:
                    print("done with power attack")
                    world.finisher.remove(agent_eid)
                    world.attacking.add(agent_eid, self.target_eid)
                    return

                elif power.status == SUCCESS:
                    self.status = power.status
                    world.finisher.remove(agent_eid)
                    world.attacking.remove(agent_eid)
                    world.moving.remove(agent_eid)
                    return

            elif action_attack is None:
                # just starting
                if ACTION_LOG and not world.simulation:
                    print ("[{:.2f}] {} attacking {}".format(world.clock, agent, target))
                attack = world.attacking.add(agent_eid, self.target_eid)
                world.moving.add_replace(agent_eid, target.pos, data.attack_speed[agent.tid], attack.melee_dist)
                return

            elif action_attack.status == SUCCESS:
                # dude be dead
                world.attacking.remove(agent_eid)
                world.moving.remove(agent_eid)
                self.status = action_attack.status
                return

            elif action_attack.status == INTERRUPT:
                world.attacking.remove(agent_eid)
                self.status = INTERRUPT
                return
            # still on the attack
            else:
                action_move = world.moving.get(agent_eid)
                action_move.dest = target.pos
                action_move.status = RUNNING



    def cleanup(self, eid, world):
        # make sure actions are gone
        if world.moving.get(eid) is not None:
            world.moving.remove(eid)
        if world.attacking.get(eid) is not None:
            world.attacking.remove(eid)
        if world.finisher.get(eid) is not None:
            world.finisher.remove(eid)

    ################# reasoning about this behavior #####################

    @staticmethod
    def target_eids_for_agent(agent_ent, world):
        for eid, ent in world.entities_within_range(agent_ent.eid, data.awareness[agent_ent.tid]):
            # agent->combatants
            if agent_ent.tid == data.AGENT_TYPE_ID:
                if ent.tid in data.combatants:
                    yield ent.eid
            # mobs->agents
            else:
                if ent.tid == data.AGENT_TYPE_ID:
                    yield ent.eid

    ################# debug display #####################

    def sig(self): return str(self)

    def __str__(self):
        return "(attack {} {})".format(self.agent_eid, self.target_eid)

    def short(self):
        return "A{}".format(self.target_eid)

    def short_status(self):
        return "A{}-{}".format(self.target_eid, self.status)

    def __eq__(self, other):
        return other.__class__ == self.__class__ and self.target_eid == other.target_eid


class CBehaviorStun(CBehavior):
    def __init__(self, agent_eid):
        super().__init__()
        self.agent_eid = agent_eid

    def update(self, agent_eid, world, dt, trace=None):
        agent = world.entities.get(agent_eid)
        stunner = world.stun.get(agent_eid)
        if agent.flag == 'stun':
            if stunner is None:
                print("adding stunner")
                stunner = world.stun.add(agent_eid)
            if stunner.status != RUNNING:
                self.status = INTERRUPT

        if agent.flag == 'unstun':
            world.stun.remove(agent_eid)
            self.status = SUCCESS

    def sig(self): return str(self)

    def __str__(self):
        return "(stunned {})".format(self.agent_eid)

    def short(self):
        return "S{}".format(self.agent_eid)

    def short_status(self):
        return "S-{}".format(self.status)

##########################
# Mob Behavior
##########################

class CBehaviorMobPatrol(CBehavior):
    def __init__(self, agent_eid, anchor, radius):
        super().__init__()
        self.agent_eid = agent_eid
        self.anchor = anchor
        self.radius = radius

        self.patroling = False
        self.pause_duration = self.next_pause()
        self.pause_timer = 0

        self.attack_target = None
        self.leashing = False
        self.leash_point = None

    def next_pause(self):
        v = 0.25 + (random.random() * 2)
        return v

    def next_loc(self):
        radius = random.gauss(0, self.radius/2)
        theta = random.uniform(0, 2*math.pi)
        offset = (radius*math.cos(theta), radius*math.sin(theta))
        return self.anchor + vector2(offset)

    def melee_dist(self, agent, target):
        return data.render[agent.tid]['size'] + data.render[target.tid]['size']

    # specializing here, but stay stateless!
    def update(self, agent_eid, world, dt, trace=None):
        agent = world.entities.get(agent_eid)
        # double checking if not leashing
        if not self.patroling and not self.leashing:
            # attack finished, back to patrolling
            self.patroling = True

        elif agent.flag == 'leash':
            self.status = SUCCESS

        if not self.leashing and self.pause_timer < self.pause_duration:
            # non-combat pause
            self.pause_timer += dt
            if self.pause_timer >= self.pause_duration:
                # done w/ pause, start move
                a = world.entities.get(agent_eid)
                world.moving.add_replace(agent_eid, self.next_loc(), data.movement_speed[a.tid], 0)

        else:
            # non-combat patrol or leash move
            action_move = world.moving.get(agent_eid)
            if action_move is not None and action_move.status != RUNNING:

                world.moving.remove(agent_eid)
                self.pause_timer = 0
                self.pause_duration = self.next_pause()
                self.leashing = False
                self.leash_point = None

    def cleanup(self, eid, world):
        # make sure actions are gone
        if world.moving.get(eid) is not None:
            world.moving.remove(eid)

    ################# debug display #####################

    def sig(self): return str(self)

    def __str__(self):
        return "(patrol {})".format(self.agent_eid)

    def short(self):
        return "P".format()

    def short_status(self):
        return "P-{}".format(self.status)

class CBehaviorEat(CBehavior):
    def __init__(self, agent_eid, edible):
        super().__init__()
        self.agent_eid=agent_eid
        self.edible_iid=edible

    def update(self, agent_eid, world, dt, trace=None):
        inv = world.inventories.get(agent_eid)
        if inv.item_amount(self.edible_iid) >=1:
            a = world.eat.get(agent_eid)  # Agent current Food
            b = data.hunger[world.entities.get(agent_eid).tid]  # Agent Max Food

            item_hunger, item_cd = data.edibles[self.edible_iid]
            if a.food + item_hunger > b[0]:
                a.food = b[0]
            else:
                a.food = a.food + item_hunger
            print("[{:.2f}] agent eats for {} his new food meter is {}".format(world.clock, data.edibles[self.edible_iid][0],
                                                                        a.food))

            #Check if the consumed food has removed the de-buffed state.
            if a.food > 0:
                agent = world.entities.get(agent_eid)
                agent.debuff = None
                a.weak_timer = 0.0
                a.weak_state = 0

            inv.remove(self.edible_iid, 1)
            self.status = SUCCESS
        else:
            self.status = INTERRUPT

    def sig(self): return str(self)

    def __str__(self):
        return "(eating {} {})".format(self.agent_eid, self.edible_iid)

    def short(self):
        return "E{}".format(self.edible_iid)

    def short_status(self):
        return "E{}-{}".format(self.edible_iid,self.status)

#DELETE_HP. Heal behavior is the same as the old eat behavior so this is just a copy of the old eat, with changed naming
#           conventions.
class CBehaviorHeal(CBehavior):
    def __init__(self, agent_eid, heal):
        super().__init__()
        self.agent_eid=agent_eid
        self.heal_iid=heal


    def update(self, agent_eid, world, dt, trace=None):
        action_heal=world.heal.get(agent_eid)

        if action_heal is not None:
            if action_heal.status != RUNNING:
                world.heal.remove(agent_eid)
            return

        # do the initial heal and start the eating cooldown.
        inv = world.inventories.get(agent_eid)

        #DELETE_HP. Though the item is removed upon consumption from the inventory, a unit check was added since it
        #           continued to heal twice. This is the same checked in drink so the root problem may lie elsewhere.
        if inv.item_amount(self.heal_iid) >=1:
            a = world.entities.get(agent_eid)  # Agent current Hp
            b = data.combatants[a.tid]  # Agent Max Hp
            item_heal, item_cd = data.hp_items[self.heal_iid]
            if a.hp + item_heal > b[0]:
                a.hp = b[0]
            else:
                a.hp = a.hp + item_heal
            print("[{:.2f}] agent heals for {} his new hp is {}".format(world.clock, data.hp_items[self.heal_iid][0],
                                                                        world.entities.get(agent_eid).hp))

            inv.remove(self.heal_iid, 1)
            world.heal.add(agent_eid, item_cd)


    def sig(self): return str(self)

    def __str__(self):
        return "(healing {} {})".format(self.agent_eid, self.heal_iid)

    def short(self):
        return "H{}".format(self.heal_iid)

    def short_status(self):
        return "H{}-{}".format(self.heal_iid,self.status)


class CBehaviorDrink(CBehavior): #Based off of CBehaviorMoveAndAttack & CBehaviorEat
    def __init__(self, agent_eid, drink):
        super().__init__()
        self.agent_eid = agent_eid
        self.drink_iid = drink

    def update(self, agent_eid, world, dt, trace=None):
        inv = world.inventories.get(agent_eid)
        ct = inv.item_amount(self.drink_iid)
        a = world.drink.get(agent_eid).thirst
        b = data.thirst[world.entities.get(agent_eid).tid]
        if ct >=1:
            if a + data.drinks[self.drink_iid] > b[0]:
                world.drink.get(agent_eid).thirst = b[0]
            else:
               world.drink.get(agent_eid).thirst = a + data.drinks[self.drink_iid]

            #DELETE_S1. Note, currently gatherable items that drop other items have a 100% drop chance and fixed
            #           drop amount so there is no need for a randomizer.
            if self.drink_iid in data.gatherable:
                g = data.gatherable[self.drink_iid][1]
                for iid, min, max, prob in g:
                    ct = (min+max)//2
                    inv.add(iid, ct, world)
                    print("[{:.2f}] Agent obtained {}x {}".format(world.clock, ct, iid))

            print("[{:.2f}] agent drinks for {} his new thirst to be {}".format(world.clock, data.drinks[self.drink_iid], world.drink.get(agent_eid).thirst))
            inv.remove(self.drink_iid, 1)
            self.status = SUCCESS
        else:
            self.status = INTERRUPT

    def sig(self): return str(self)

    def __str__(self):
        return "(drink {} {})".format(self.agent_eid, self.drink_iid)

    def short(self):
        return "D{}".format(self.drink_iid)

    def short_status(self):
        return "D{}-{}".format(self.drink_iid, self.status)


class CBehaviorTrap(CBehavior):
    def __init__(self, agent_eid, target_eid, trap_typeid):
        super().__init__()
        self.agent_eid = agent_eid
        self.trap_typeid = trap_typeid
        self.target_eid = target_eid

    def update(self, agent_id, world, dt, trace=None):
        if self.status == RUNNING:
            action_trap = world.trap.get(agent_id)
            target = world.entities.get(self.target_eid)
            agent = world.entities.get(self.agent_eid)
            if target and agent:
                dist = (target.pos - agent.pos).magnitude()
                # check if I'm in a probable safe zone around the mob. Hard coded for the moment,
                # based on current equation for leashing
                if not (100 < dist < 300):
                    # if I'm not in a safe zone to set the trap, move to it
                    # NEEDS MORE TESTING
                    new_pos = (target.pos - agent.pos) * 0.5
                    world.moving.add_replace(agent_id, new_pos, data.movement_speed[agent.tid])
            if action_trap is None:
                world.trap.add(agent_id, self.trap_typeid)
            return

    def __str__(self):
        return "(set {} {})".format(self.agent_eid, self.trap_typeid)

    def sig(self):
        return str(self)

    def short(self):
        return "T{}".format(self.trap_typeid)

    def short_status(self):
        return "T{}-{}".format(self.trap_typeid, self.status)

class CBehaviorLure(CBehavior):
    def __init__(self, agent_eid, target_eid, trap_eid):
        super().__init__()
        self.agent_eid = agent_eid
        self.target_eid = target_eid
        self.trap_eid = trap_eid
        self.try_count = 0

    def update(self, agent_eid, world, dt, trace=None):
        if self.status == RUNNING:
            if world.entities.get(self.target_eid).flag == world.trap.get(agent_eid).trap:
                if world.moving.get(agent_eid):
                    world.moving.remove(agent_eid)
                if world.attacking.get(agent_eid) is None:
                    world.attacking.add(agent_eid, self.target_eid)
            elif world.attacking.get(self.target_eid) is None:
                world.attacking.add_replace(agent_eid, self.target_eid)
            # elif self.try_count > 3:
            #     if world.moving.get(agent_eid):
            #         world.moving.remove(agent_eid)
            #     world.gathering.add(agent_eid, self.trap_eid)
            #     self.try_count = 0

            # update direction each frame
            agent = world.entities.get(agent_eid)
            trap = world.entities.get(self.trap_eid)
            target = world.entities.get(self.target_eid)
            if trap and target and world.attacking.get(agent_eid) is None:
                lure_vector = trap.pos - target.pos
                world.moving.add_replace(agent_eid, lure_vector, data.attack_speed[agent.tid], 0)

    def cleanup(self, eid, world):
        # make sure actions are gone
        if world.moving.get(eid) is not None:
            world.moving.remove(eid)

    def sig(self): return str(self)

    def __str__(self):
        return "(lure {} {})".format(self.agent_eid, self.target_eid)

    def short(self):
        return "L{}".format(self.target_eid)

    def short_status(self):
        return "L{}-{}".format(self.target_eid, self.status)

    def __eq__(self, other):
        return other.__class__ == self.__class__ and self.target_eid == other.target_eid