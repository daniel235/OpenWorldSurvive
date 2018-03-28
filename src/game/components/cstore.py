##### general component storage

class ComponentStore:
    def __init__(self, world, trace=None):
        self.world = world
        self.reset()
        self.trace = trace

    def reset(self):
        self.cc = {}
        self.remove_ids = set()

    def addc(self, eid, c, d=False):
        if eid in self.cc.keys():
            raise KeyError("Duplicate component add", eid)
        self.cc[eid] = c
        if d:
            testEntity = self.world.entities.get(eid).tid
            if testEntity != 1:
                agent = self.world.mob.get(eid)
            else:
                agent = self.world.agents.get(eid)
            self.trace.add_decision_node(self.world.clock, agent.active_behavior.sig(), eid)
        return c

    def remove(self, eid, status=None, d=False):
        # no components are removing themselves at this time, so default to direct remove?
        # good side: will error if assumption is false, then can fix
        #print("Removing {}: {}".format(self.__class__.__name__, eid))
        if d:
            testEntity = self.world.entities.get(eid).tid
            if testEntity != 1:
                agent = self.world.mob.get(eid)
            else:
                agent = self.world.agents.get(eid)
            self.trace.end_update(self.world, eid, agent.active_behavior.sig(), status)
        del self.cc[eid]
        #self.remove_ids.add(eid)

    def sweep(self, deleted):
        # remove marked components
        for eid in self.remove_ids:
            del self.cc[eid]
        self.remove_ids.clear()
        # remove components for deleted entities
        for eid in deleted:
            if eid in self.cc:
                del self.cc[eid]

    def get(self, eid):
        if eid in self.cc.keys():
            return self.cc[eid]
        return None

    def get_required(self, eid):
        """
        Errors if not there
        """
        return self.cc[eid]

    def all(self):
        return self.cc.items()

    def count(self):
        return len(self.cc.keys())

    def __str__(self):
        s = ""
        for k,v in self.cc.items():
            s = s + "{}: {}\n".format(k,v)
        return s
