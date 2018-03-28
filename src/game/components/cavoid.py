from components.cstore import ComponentStore
from constants import *
import data
from steering import SteeringManager


DEBUG = True

class CAvoid:
    def __init__(self, dest, speed, dist):
        self.dest = dest
        self.speed = speed
        self.dist = dist
        #initialize timer
        self.status = RUNNING




class ComponentStoreAvoid(ComponentStore):
    def add(self, eid, dest, speed, dist=0):
        return self.addc(eid, CAvoid(dest, speed, dist))
    def add_replace(self, eid, dest, speed, dist=0):
        if eid in self.cc: self.remove(eid)
        return self.addc(eid, CAvoid(dest, speed, dist))


    def update(self, world, dt, trace=None):
        for eid, mov in self.all():
            #agent entitiy
            e = self.world.entities.get(eid)
            path = mov.dest - e.pos
            a = SteeringManager(e.pos)
            a.seek(mov.dest, 100)
            m = path.magnitude()
            step = mov.speed * dt
            possible_enemy = []
            for eid, ent in world.entities_within_range(e.eid, data.awareness[5]):

                max_dist = 0
                if(ent.tid == 2 or ent.tid == 3):
                    print("if loop")
                    possible_enemy.append(world.entities.get(eid))


                    enemy = world.entities.get(eid)
                    enemy = enemy.pos
                    print("updating cavoid update")
                    a.update(mov.dest, enemy)

            for k in possible_enemy:
                print("possible enemy", k)

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