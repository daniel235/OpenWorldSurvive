##########################
#  Movement Components
##########################
from constants import *
from components.cstore import ComponentStore

class CMove:
    def __init__(self, dest, speed, dist):
        self.dest = dest
        self.speed = speed
        self.dist = dist
        self.status = RUNNING

# specialize for storing this type of component
class ComponentStoreMove(ComponentStore):
    def add(self, eid, dest, speed, dist=0):
        return self.addc(eid, CMove(dest, speed, dist))
    def add_replace(self, eid, dest, speed, dist=0):
        if eid in self.cc: self.remove(eid)
        return self.addc(eid, CMove(dest, speed, dist))

    ##########################
    #  System Update
    ##########################
    def update(self, dt):
        for eid, mov in self.all():
            e = self.world.entities.get(eid)

            path = mov.dest - e.pos
            m = path.magnitude()
            step = mov.speed * dt

            # check for end of move condition
            if m < mov.dist:
                # close enough
                mov.status = SUCCESS
                continue
            elif step >= m:
                e.pos = mov.dest
                # set status
                mov.status = SUCCESS
                continue

            # normal move step
            e.pos = e.pos + path.normalized(m) * step
            mov.status = RUNNING
