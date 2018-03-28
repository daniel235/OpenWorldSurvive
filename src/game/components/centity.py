##########################
#  Core entity data used for spatial reasoning (viz, collision)
##########################

import data
from components.cstore import ComponentStore

class CEntity:
    def __init__(self, tid, eid, pos, hp, breed, flag):
        self.tid = tid
        self.eid = eid
        self.pos = pos
        self.hp = hp
        self.breed = breed
        self.flag = flag

        #DELETE_Stage1. Currently there is only one debuff applied and it reduces efficiency of all actions except
        #                movement, because of this the debuff has been added to the entity for now. Any value other than
        #                None indicates the percent reduction in efficiency.
        self.debuff = None
        self.buff_change = False

    ########### attributes ##############


    def movement_speed(self):
        """Could account for modifiers"""
        return data.movement_speed[self.tid]

    def __str__(self):
        return "{} ({}) {} {}".format(data.names[self.tid], self.eid, self.hp, self.pos)

# specialize for storing this type of component
class ComponentStoreEntity(ComponentStore):
    def add(self, eid, tid, pos, hp, breed, flag):
        return self.addc(eid, CEntity(tid, eid, pos, hp, breed, flag))

    def remove(self, eid):
        """Removal of entities is delayed to end-of-frame and supports sweeping all components for that entity."""
        self.remove_ids.add(eid)
