import random

import data
from components import *
from vector2 import vector2


class World:
    def __init__(self, dim=(1024, 768), trace=None, grid_step=16, mem_step=256, simulation=False):
        self.dim = dim
        self.grid_step = grid_step
        self.next_eid = 2000
        self.mem_step = mem_step

        self.agents = cagent.ComponentStoreAgent(self)
        self.attacking = cattack.ComponentStoreAttack(self, trace)
        self.behaviors = cbehavior.ComponentStoreBehavior(self, trace)
        self.crafting = ccraft.ComponentStoreCraft(self)
        self.decay = cdecay.ComponentStoreDecay(self)
        self.drink = cthirst.ComponentStoreDrink(self, trace)
        self.eat = ceat.ComponentStoreEat(self)
        self.entities = centity.ComponentStoreEntity(self)
        self.finisher = cfinisher.ComponentStoreFinisher(self)
        self.gathering = cgather.ComponentStoreGather(self)
        self.heal = cheal.ComponentStoreHeal(self)
        self.inventories = cinventory.ComponentStoreInv(self)
        self.memory = cmemory.ComponentStoreMemory(self)
        self.mob = cmob.ComponentStoreMob(self)
        self.moving = cmove.ComponentStoreMove(self)
        self.relationship = crelation.ComponentStoreRelation(self)
        self.stun = cstun.ComponentStoreStun(self)
        self.tag = ctag.ComponentStoreTag(self)
        self.trap = ctrap.ComponentStoreTrap(self)

        self.simulation = simulation
        self.clock = 0


        #self.mem_dim = [d/mem_step for d in dim]
        #self.memory = [[set()]*self.mem_dim[1] for i in range(self.mem_dim[0])]

    def eid(self):
        self.next_eid += 1
        return self.next_eid

    def add_entity(self, spec):
        eid = self.eid()

        # default to random location
        loc = (('loc' in spec) and spec['loc']) or self.rand_open()
        # allow variable starting hp (for testing)
        hp = (('hp' in spec) and spec['hp']) or (spec['tid'] in data.combatants and data.combatants[spec['tid']][0]) or None

        # allow variable starting thirst (for testing), or None to disable thirst
        if 'thirst' in spec:
            thirst = spec['thirst']
        else:
            thirst = (spec['tid'] in data.thirst and data.thirst[spec['tid']][0]) or None

        # if this entity has thirst, add the component
        if thirst is not None:
            self.drink.add(eid, data.thirst[1])

        if 'hunger' in spec:
            hunger = spec['hunger']
        else:
            hunger = (spec['tid'] in data.hunger and data.hunger[spec['tid']][0]) or None

        if hunger is not None:
            self.eat.add(eid, data.hunger[1])

        # if the item decays, add the component
        if 'decay' in spec:
            self.decay.add(eid, spec['decay'][0], spec['decay'][1])

        flag = 'idle'

        # add flag
        #adding logic of the typed entities
        if spec['tid'] != 1:
            if eid % 2 == 0:
                breed = 'fire'
            else:
                breed = 'ice'
        else:
            breed = 'human'

        # add base entity component
        ent = self.entities.add(eid, spec['tid'], loc, hp, breed, flag)
        self.tag.add(eid, None)
        # other spec options: inventory
        inv = self.inventories.add(eid)
        if 'inv' in spec:
            for iid,ct in spec['inv']:
                inv.add(iid, ct, self)

        # other spec options: agent
        if 'agent_fn' in spec:
            self.agents.addc(eid, spec['agent_fn'](eid, self))
            self.memory.add(eid,self.dim, self.entities.get(eid))
            self.relationship.add(self, eid)

        # other spec options: behavior
        if 'mob_fn' in spec:
            self.mob.addc(eid, spec['mob_fn'](eid, self))


        return eid,ent

    # world functionality

    def entities_within_range(self, focus_eid, range):
        focus_ent = self.entities.get(focus_eid)
        for eid,ent in self.entities.all():
            if eid != focus_eid:
                if (focus_ent.pos - ent.pos).magnitude() <= range:
                    yield eid,ent

    def agents_within_range(self, focus_eid, range):
        focus_ent = self.entities.get(focus_eid)
        for eid, ent in self.entities.all():
            if eid != focus_eid and self.agents.get(eid) is not None:
                if (focus_ent.pos - ent.pos).magnitude() <= range:
                    yield eid, ent

    # utilities

    def string_entities(self):
        # s = ""
        # for eid,ent in self.entities.all():
        #     s += "{} ({}) at {}\n".format(data.names[ent.tid], eid, ent.pos)
        # return s
        return "\n".join(("{} ({}) at {}".format(data.names[ent.tid], eid, ent.pos) for eid,ent in self.entities.all()))

    # helper method for tagging system. Used to determine if something still exists
    def living(self, target_eid):
        for eid, ent in self.entities.all():
            if eid is target_eid:
                return True
        return False

    def rand_open(self):
        """Returns a random open starting position (grid cell center)"""
        cand = None
        while not cand:
            cand = self.rand_grid()
            for eid,ent in self.entities.all():
                if self.grid_pos(ent.pos) == cand:
                    # no good
                    cand = None
                    break
        # found when loops ends
        return self.grid_center(cand)

    def randloc(self, limits=None):
        return self.grid_center(self.rand_grid(limits=limits))

    def rand_grid(self, limits=None):
        """Returns a random grid position. Limits is [(xmin,ymin), (xmax,ymax)] in world space."""
        if limits is None:
            limits = ((0,0), [int(d/self.grid_step)-1 for d in self.dim])
        else:
            # convert to grid space
            limits = ([int(max(d,0)/self.grid_step) for d in limits[0]],
                      (int(min(limits[1][0],self.dim[0]-1)/self.grid_step), int(min(limits[1][1],self.dim[1]-1)/self.grid_step)))
        return (random.randint(limits[0][0], limits[1][0]), random.randint(limits[0][1], limits[1][1]))

    def center(self):
        return vector2((self.dim[0] / 2, self.dim[1] / 2))

    def grid_pos(self, pos):
        return (int(pos.x // self.grid_step), int(pos.y // self.grid_step))

    def grid_center(self, gp):
        """Returns the world point in the center of the specified grid cell"""
        return vector2(((gp[0]+0.5)*self.grid_step, (gp[1]+0.5)*self.grid_step))

    def entity_at_grid_pos(self, gp):
        for eid, ent in self.entities.all():
            if self.grid_pos(ent.pos) == gp:
                return ent
        return None

    ##################### memory cells #########################



    ##################### Agent and World Update #########################

    def consider(self, dt):
        for id,a in self.agents.all(): a.consider(self, dt, 1)
        for id, a in self.mob.all(): a.consider(self, dt)

    def update(self, dt):
        self.clock += dt

        # agent update, apply proposed decisions
        self.agents.update(dt)
        self.mob.update(dt)
        # simulation updates
        self.behaviors.update(dt)
        self.moving.update(dt)
        self.gathering.update(dt)
        self.crafting.update(dt)
        self.eat.update(dt)
        self.heal.update(dt)
        self.attacking.update(dt)
        self.drink.update(dt)
        self.memory.update()
        self.tag.update()
        self.finisher.update(dt)
        self.stun.update(dt)
        self.relationship.update()
        self.trap.update(dt)
        self.decay.update(dt)


        # clean up
        self.agents.sweep(self.entities.remove_ids)
        self.mob.sweep(self.entities.remove_ids)
        self.behaviors.sweep(self.entities.remove_ids)
        self.moving.sweep(self.entities.remove_ids)
        self.gathering.sweep(self.entities.remove_ids)
        self.crafting.sweep(self.entities.remove_ids)
        self.eat.sweep(self.entities.remove_ids)
        self.attacking.sweep(self.entities.remove_ids)
        self.drink.sweep(self.entities.remove_ids)
        self.memory.sweep(self.entities.remove_ids)
        self.tag.sweep(self.entities.remove_ids)
        self.finisher.sweep(self.entities.remove_ids)
        self.stun.sweep(self.entities.remove_ids)
        self.relationship.sweep(self.entities.remove_ids)
        self.trap.sweep(self.entities.remove_ids)
        self.decay.sweep(self.entities.remove_ids)
        self.heal.sweep(self.entities.remove_ids)


        self.entities.sweep(set())

        # snapshot world, if needed
        #if trace: trace.snapshot(self)
