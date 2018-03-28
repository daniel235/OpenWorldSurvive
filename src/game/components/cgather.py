##########################
#  Gathering Components
##########################
import random

from constants import *
import data

from components.cstore import ComponentStore

# module level
DEBUG=False

class CGather:
    def __init__(self, target_eid, world):
        self.target_eid = target_eid
        self.target_tid = world.entities.get_required(target_eid).tid

        # get type, duration
        g = data.gatherable[self.target_tid]
        self.duration = g[0]

        # get item risk factor
        self.r = (self.target_tid in data.risk and data.risk[self.target_tid]) or None

        # debuff section
        self.originals = None
        self.debuff = False

        # modify duration based on tools


        # initialize timer state
        self.progress = 0.0
        self.rprogress = 0.0
        self.status = RUNNING

# specialize for storing this type of component
class ComponentStoreGather(ComponentStore):
    def add(self, actor_eid, target_eid):
        # REM: calculate duration
        self.addc(actor_eid, CGather(target_eid, self.world))

    ##########################
    #  System Update
    ##########################

    def update(self, dt):
        for eid, act in self.all():
            if act.status == RUNNING:

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


                # progress
                act.progress += dt

                # update tag to ensure that no one else can gather from it at this point
                if self.world.entities.get(act.target_eid) is not None:
                    if self.world.entities.get(act.target_eid).tid not in (1002, 1005):
                        self.world.tag.get(act.target_eid).hard()

                # REM: progress bar?
                # REM: status icon (actions upper right)
                if act.progress >= act.duration:
                    # add items
                    inv = self.world.inventories.get_required(eid)

                    self.add_items(inv, act.target_eid)


                    # remove node, or start respawn, or mark empty
                    tid = act.target_tid
                    if tid not in (1002, 1005):
                        self.world.entities.remove(act.target_eid)
                    else:
                        self.world.tag.get(act.target_eid).remove(eid)
                        decay = self.world.decay.get(act.target_eid)
                        if decay != None:
                            decay.use_stack(act.target_eid, self.world)

                    # set status to end
                    act.status = SUCCESS
                    continue

                # Calculate fail chance if entity has a risk factor
                elif act.r is not None:
                    act.rprogress += dt
                    if act.rprogress >= act.r[3]:
                        act.rprogress = 0.0
                        roll = random.random()

                        # On failure success, agent takes damage and tags are reset on target entity.
                        if roll < act.r[2]:

                            # agent loses health
                            agent = self.world.entities.get(eid)
                            dmg = random.uniform(act.r[0], act.r[1])
                            agent.hp -= dmg

                            # target entity tags are reset
                            tid = act.target_tid
                            if tid != 1005:
                                self.world.tag.get(act.target_eid).abandoned()
                            else:
                                self.world.tag.get(act.target_eid).remove(eid)

                            # info is printed to the console.
                            if ACTION_LOG and not self.world.simulation: print(
                                "[{:.2f}] {} takes {:.2f} damage from failing gather on ({})".format(self.world.clock,
                                                                                                     agent, dmg, tid))
                            act.status = SUCCESS
                    continue

    def add_items(self, inv, node):
        g = data.gatherable[self.world.entities.get_required(node).tid][1]

        for iid, min, max, prob in g:
            if DET:
                inv.add(iid, (min+max)/2, self.world)
                if ACTION_LOG and not self.world.simulation: print(
                    "[{:.2f}] Agent obtained {}x {}".format(self.world.clock,
                                                            (min+max)/2, iid))
            else:
                roll = random.random()
                if roll < prob:
                    ct = random.randint(min, max) # inclusive
                    inv.add(iid, ct, self.world)
                    if ACTION_LOG and not self.world.simulation: print("[{:.2f}] Agent obtained {}x {}".format(self.world.clock,
                                                                                                  ct, iid))
                else:
                    if ACTION_LOG and not self.world.simulation: print("[{:.2f}] Agent failed gather {}".format(self.world.clock, iid))

    def debuff(self, node, debuff):
        node.originals = node.duration
        node.duration += (node.duration * debuff)
        node.debuff = True

    def reset_buff(self, node):
        node.duration = node.originals
        node.debuff = False

    # helpers
    def available(self, node):
        return True
