from components.behaviors import *
from constants import *

class BehaviorGatherTree(BTSequence):
    def __init__(self, name, tree=None):
        super().__init__(name)
        self.addChild(VisibleEntities("Entities around?"))
        self.addChild(IsGatherable("Can i gather?"))
        self.addChild(BehaviorMove("Move to Gather"))
        self.addChild(IsInRange("Is it close?", 0))
        self.addChild(BehaviorGather("Gathering"))


    def update(self, btcomp, traversal, agent, world, dt):
        return super(BehaviorGatherTree, self).update(btcomp, traversal, agent, world, dt)


class BehaviorExploreTree(BTSelect):
    def __init__(self, name, tree=None):
        super().__init__(name, True)
        self.addChild(tree)
        self.addChild(BehaviorMove("Explore"))


    def update(self, btcomp, traversal, agent, world, dt):
        return super(BehaviorExploreTree, self).update(btcomp, traversal, agent, world, dt)

