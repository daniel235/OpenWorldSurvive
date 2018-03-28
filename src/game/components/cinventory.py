##########################
#  Inventory Components
###########################
import data
import random

from components.cstore import ComponentStore

# REM: unique items, durability, space/weight limits...
class CInventory:
    def __init__(self, owner_eid):
        self.item_counts = {}
        self.item_limit = 15
        self.count = 0
        self.owner_eid = owner_eid

    def all(self):
        for iid,ct in self.item_counts.items():
            yield iid,ct

    def all_weapons(self):
        for iid,ct in self.item_counts.items():
            if iid in data.weapons:
                yield iid,ct

    def max_dps_weapon(self, agent_eid, world):
        maxdps = 0
        maxwid = None
        for wid,ct in self.all_weapons():
            cd,dmg,range = data.weapons[wid]
            dps = (dmg[0] + dmg[1])/2.0/cd
            if dps > maxdps:
                maxdps = dps
                maxwid = wid
        return maxwid


    def add(self, iid, ct, world):
        space = self.item_limit - self.count
        if space >= ct:
            if iid in self.item_counts:
                self.item_counts[iid] += ct
            else:
                self.item_counts[iid] = ct
            self.count += ct
        else:
            if space > 0:
                if iid in self.item_counts:
                    self.item_counts[iid] += space
                else:
                    self.item_counts[iid] = space
                self.count += space
            for _ in range (ct-space):
                world.add_entity({'tid': iid+3000, 'loc': world.entities.get(self.owner_eid).pos})

    def remove(self, iid, ct):
        assert iid in self.item_counts and self.item_counts[iid] >= ct
        self.item_counts[iid] -= ct
        self.count -= ct
        if self.item_counts[iid] == 0:
            del self.item_counts[iid]

    def drop(self, iid, ct, world):
        if iid in self.item_counts and self.item_counts[iid] >= ct:
            space = self.item_limit - self.count
            self.item_counts[iid] -= ct
            self.count -= ct
            for _ in range (ct):
                world.add_entity({'tid': iid+3000, 'loc': world.entities.get(self.owner_eid).pos})

    def item_amount(self, iid):
        if iid in self.item_counts:
            return self.item_counts[iid]
        return 0

    def gain(self, prior_inv):
        G = []
        for iid,ct in self.all():
            prior_ct = prior_inv.item_amount(iid)
            if prior_ct < ct:
                G.append((iid, ct-prior_ct))
        return G

    def loss(self, prior_inv):
        G = []
        for iid,prior_ct in prior_inv.all():
            ct = self.item_amount(iid)
            if prior_ct > ct:
                G.append((iid, prior_ct-ct))
        return G

    def inv_count(self):
        items = 0
        for iid, ct in self.all():
            items += 1
        return items

    def random_item(self):
        if self.inv_count() > 1:
            return list(self.item_counts.keys())[random.randint(0, self.inv_count()-1)]
        elif self.inv_count() is 1:
            return list(self.item_counts.keys())[0]
        else:
            return 0

    def __str__(self):
        return "; ".join(("{}({})".format(data.names[k],v) for k,v in self.item_counts.items()))

# specialize for storing this type of component
class ComponentStoreInv(ComponentStore):
    def add(self, agent):
        return self.addc(agent, CInventory(agent))

