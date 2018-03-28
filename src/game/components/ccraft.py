##########################
#  Crafting Tools
##########################
import random

from constants import *
import data

from components.cstore import ComponentStore

# module level
DEBUG=True

class CCraft:
    def __init__(self, item_typeid):
        self.item_typeid = item_typeid
        self.duration = data.recipes[item_typeid][0]

        self.originals = None
        self.debuff = False

        # initialize timer state
        self.progress = 0.0
        self.status = RUNNING
        if DEBUG: print("Agent crafting {}...".format(item_typeid))

# specialize for storing this type of component
class ComponentStoreCraft(ComponentStore):
    def add(self, actor_eid, item_typeid):
        # REM: calculate duration
        self.addc(actor_eid, CCraft(item_typeid))

    ##########################
    #  System Update
    ##########################

    def update(self, dt):
        for eid, act in self.all():

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

            # REM: progress bar?
            # REM: status icon (actions upper right)
            if act.progress >= act.duration and act.status !=SUCCESS:

                # check items
                inv = self.world.inventories.get_required(eid)
                recipe = data.recipes[act.item_typeid][1]
                for matid,mct in recipe:
                    if inv.item_amount(matid) < mct:
                        # failed!
                        act.status = FAILURE
                        if DEBUG: print("...crafting failed!")
                        continue

                # got the mats, remove them and add the crafted item
                if act.status is not FAILURE:
                    for matid,mct in recipe:
                        inv.remove(matid, mct)
                    inv.add(act.item_typeid, 1, self.world)
                    if DEBUG: print("...crafting succeeded!")

                # set status to end
                act.status = SUCCESS
                self.remove_ids.add(eid)
                continue

            act.status = RUNNING

    def debuff(self, node, debuff):
        node.originals = node.duration
        node.duration += (node.duration * debuff)
        node.debuff = True

    def reset_buff(self, node):
        node.duration = node.originals
        node.debuff = False