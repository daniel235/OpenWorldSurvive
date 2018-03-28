import data

#################################################
# Goal Types
#################################################

class Goal:
    def expand(self):
        pass

class Goal_HasItemType(Goal):
    def __init__(self, tid, ct,value):
        self.tid = tid
        self.ct = ct
        self.value=value
        self.needed=[]
        self.strategy=[]
        if(tid in data.recipes or tid == 2013):
            self.expand()


    def expand(self):
        if (self.tid == 2013):
            self.strategy.append(Goal_HasItemType(2008,1,1))
            self.strategy.append(Goal_HasItemType(4000,1,1))
            self.needed.append(Goal_HasItemType(2010,3,1))
        if (self.tid in data.recipes):
            matlist = data.recipes[self.tid][1]
            val= self.value / len(matlist)
            for matid,matct in matlist:
                if(matid in data.recipes):
                    self.strategy.append(Goal_HasItemType(matid,matct,1))
                else:
                    self.needed.append(Goal_HasItemType(matid,matct,val))
    def current_goal(self):
        a = self.strategy
        if a != None:
            while a.strategy != None:
                a = a.strategy
        return a
    def give_needed(self):
        if len(self.needed)>0:
            return self.needed
        else:
            return None
    def tree_leaves(self): #ONLY RETURNS LEAVES
        items=[]
        p=[]
        for a in self.strategy:
            if len(a.strategy)==0:
                items.append(a)
            else:
                p=a.tree_leaves()
                for d in p:
                    items.append(d)
        return items

    def all_nodes(self,prev):
        for a in prev:
            for b, prevs in  a.all_nodes(a.strategy):
                yield b,prevs
            yield a,prev

    def update(self,eid,world):
        inv=world.inventories.get(eid)

        #INSERT NEW THING
        for b,prev in self.all_nodes(self.strategy):
            if(b.ct<=inv.item_amount(b.tid)):
                del prev[:]


        for a in self.tree_leaves(): #INSERT LEAVE TRAVERSAL
            if len(a.needed)==0:
                for need in self.needed:
                    if need.ct <=inv.item_amount(need.tid):
                        print("Removing something from NEEDED {}".format(need.tid))
                        self.needed.remove(need)
            else:
                for need in a.needed:
                    if need.ct <=inv.item_amount(need.tid):
                        print("Removing something from NEEDED {}".format(need.tid))
                        a.needed.remove(need)


    def satisfied(self, world, agent_id):
        #print("......goal check {} has item {} ({}/{})".format(agent_id, self.tid, world.inventories.get(agent_id).item_amount(self.tid), self.ct))
        return world.inventories.get(agent_id).item_amount(self.tid) >= self.ct

    def reward(self, world, agent_id):
        return min(1.0, (world.inventories.get(agent_id).item_amount(self.tid) / self.ct)) * self.value

    def sig(self):
        """Signature omits numeric values."""
        try:
            return "(~~~~~hasitemtype {})".format(self.tid.sig())
        except AttributeError:
            return "(hasitemtype {})".format(self.tid)

    def __str__(self):
        return "(hasitemtype {} {} (value {}))".format(self.tid, self.ct, self.value)

    def to_string(self, world, agent_id):
        """Advanced to string with world data."""
        return "HasItemType {} ({}/{})".format(self.tid, world.inventories.get(agent_id).item_amount(self.tid), self.ct)

class Strategy:
    """A particular behavior and set of precedent goals to achieve a goal."""
    def __init__(self, goal, behavior):
        self.target_goal = goal
        self.behavior = behavior
        self.precedents = []

    def add_precedent(self, gnode):
        self.precedents.append(gnode)

    def all_goal_nodes(self):
        """Iterate through all goals, pre-order."""
        for gnode in self.precedents:
            yield from gnode.all_goal_nodes()

class GoalNode:
    """A goal and it's expanded strategies."""
    def __init__(self, goal):
        self.goal = goal
        self.strategies = []

    def add_strategy(self, behavior):
        s = Strategy(self.goal, behavior)
        self.strategies.append(s)
        return s

    def has_strategy(self, behavior):
        for s in self.strategies:
            if s.behavior == behavior:
                return True
        return False

    def all_goal_nodes(self):
        if self.goal != "WIN":
            yield self
        for s in self.strategies:
            yield from s.all_goal_nodes()

#################################################
# Goal Tree (children help achieve parent)
#  ignoring and/or structure right now, might be important later
#################################################

# class GoalNode:
#     def __init__(self, goal, parent):
#         """Tree node wrapper. Achieving and child should help achieve the parent."""
#         self.goal = goal
#         self.parent = parent
#
#         # more sophisticated than this...
#         self.expanded = False
#         self.children = []
#
#     def expand(self):
#         # convenience specializer
#         if not self.expanded:
#             exp = self.goal.expand()
#             self.expanded = True
#             if len(exp) > 1:
#                 self.children.append(GoalGroup([GoalNode(n, self) for n in exp]))
#             elif len(exp) == 1:
#                 self.children.append(GoalNode(exp[0], self))
#
#     def expandr(self):
#         self.expand()
#         for c in self.children:
#             c.expand()
#
# class GoalGroup(GoalNode):
#     """Abstraction over set of goals to be achieved as a set."""
#     def __init__(self, GN):
#         self.goal_nodes = GN
#
#     def expand(self):
#         # convenience specializer
#         for gn in self.goal_nodes:
#             gn.expand()

#################################################
# Planning
#################################################

class PlanGraph:
    def __init__(self, goals):
        self.top_level_goals = [GoalNode(g) for g in goals]

    def update(self, world_view):
        pass

