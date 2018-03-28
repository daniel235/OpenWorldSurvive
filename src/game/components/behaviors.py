# global shared BT storage

from constants import *
import data


BTS = {}

##########################################################
# Tree Structure
#
# The trees are stateless for update - only one copy of each is needed
##########################################################

class BTNode():
    """
    base class for leaves and selectors
    name is the name of this node in this tree, for debugging and tracing
    """
    def __init__(self, name):
        self.name = name

    def update(self, btcomp, traversal, agent, world, dt):
        return FAILURE,None

    def reset(self, btcomp, world, eid):
        "Reset blackboard state in the bound BTComponent controlled by this node"
        pass

class BTComposite(BTNode):
    """
    base class for nodes with children
    """
    def __init__(self, name):
        super().__init__(name)
        self.children = []

    def addChild(self, child):
        self.children.append(child)

    def reset(self, btcomp, world, eid):
        "Composites reset their children, have no blackboard data"
        for c in self.children:
            c.reset(btcomp, world, eid)

class BTSequence(BTComposite):
    """
    Updates children in order until one returns RUNNING or FAILURE.
    Resumes from last RUNNING child.
    Returns SUCCESS if all children are updated successfully.
    Resets self (and all children) on FAILURE/SUCCESS.

    Loop flag indicates to start at first child again, never SUCCEEDs.
    """

    def __init__(self, name, loop=False):
        super().__init__(name)
        self.loop = loop

    def update(self, btcomp, traversal, agent, world, dt):
        # if there still is an active traversal to follow, get next child index
        current_child = 0
        if len(traversal) > 0:
            current_child = traversal[0]
            traversal = traversal[1:]

        while current_child < len(self.children):
            # update current child
            next = self.children[current_child]
            status,rt = next.update(btcomp, traversal, agent, world, dt)

            if status == RUNNING:
                # continuing with this child and its traversal
                rt.append(current_child)
                return status,rt

            elif status == FAILURE:
                # done, and reset
                self.reset(btcomp, world, agent.eid)
                return FAILURE,None

            # continue to next child on SUCCESS
            current_child += 1
            # old traversal no longer applies
            traversal = []

            if self.loop and current_child == len(self.children):
                current_child = 0

        # got through all children, reset
        self.reset(btcomp, world, agent.eid)
        return SUCCESS,None

class BTSelect(BTComposite):
    """
    Updates children in order until one returns SUCCESS or RUNNING, return that.
    Returns FAILURE if all children return FAILURE.
    Resets self (and all children) on FAILURE/SUCCESS.

    Resume from start flag indicates to start over with the first child every iteration.
    """

    def __init__(self, name, resume_from_start):
        super().__init__(name)
        self.resume_from_start = resume_from_start

    def update(self, btcomp, traversal, agent, world, dt):
        # if there still is an active traversal to follow, get next child index
        current_child = 0
        selected_child = -1
        if len(traversal) > 0:
            selected_child = traversal[0]
            traversal = traversal[1:]

        # start from current child if not resume from start
        if not self.resume_from_start:
            current_child = selected_child

        while current_child < len(self.children):
            next = self.children[current_child]
            #print ("{}".format(next))
            if current_child == selected_child:
                status,rt = next.update(btcomp, traversal, agent, world, dt)
            else:
                status,rt = next.update(btcomp, [], agent, world, dt)

            if status == RUNNING:
                # continuing with this child
                rt.append(current_child)
                return status,rt

            if status == SUCCESS:
                # done, get out
                self.reset(btcomp, world, agent.eid)
                return SUCCESS,None

            # not done, try next
            current_child += 1

        # got through all children, return failure
        self.reset(btcomp, world, agent.eid)
        return FAILURE,None

##########################################################
# Behaviors
##########################################################

###############
# Movement
###############
class BehaviorMove(BTNode):
    """
    """
    def __init__(self, name):
        self.name = name

    def update(self, btcomp, traversal, entity, world, dt):
        '''path = btcomp.destination - entity.pos
        m = path.magnitude()
        step = btcomp.movement_speed * dt

        # check for end of move condition
        if m - step < btcomp.margin:
            # close enough, snap to margin
            step = m - btcomp.margin
            entity.pos = entity.pos + path.normalized(m) * step
            return SUCCESS,[]

        # normal move step
        entity.pos = entity.pos + path.normalized(m) * step
        return RUNNING,[]'''
        action_move = world.moving.get(entity.eid)
        if action_move:
            if action_move.status != RUNNING:
                # move done, may or may not have worked
                world.moving.remove(entity.eid)
                return action_move.status, []
            # else moving in progress, done here either way
            return RUNNING, []

        # not moving yet
        e = world.entities.get(entity.eid)
        if not "Target" in btcomp.bb or btcomp.bb["Target"] is None:
            world.moving.add(entity.eid, world.randloc(), data.movement_speed[e.tid], 0)
        else:
            world.moving.add(entity.eid, btcomp.bb["Target"].pos, data.movement_speed[e.tid], 0)
        return RUNNING, []

    def reset(self, btcomp, world, eid):
        "Reset blackboard state in the bound BTComponent controlled by this node"
        btcomp.bb.setdefault("Target")

        if world.moving.get(eid) is not None:
            world.moving.remove(eid)


###############
# Gather
###############
class BehaviorGather(BTNode):
    def __init__(self,name):
        self.name = name

    def update(self, btcomp, traversal, entity, world, dt):
        action_gather = world.gathering.get(entity.eid)
        if action_gather:
            if action_gather.status != RUNNING:
                # gathering done, may or may not have worked
                world.gathering.remove(entity.eid)
                return action_gather.status, []
                # print("move-and-gather done")
            # else gathering in progress, done here either way
            return RUNNING, []

        world.gathering.add(entity.eid, btcomp.bb["Target"].eid)
        return RUNNING, []

    def reset(self, btcomp, world, eid):
        "Reset blackboard state in the bound BTComponent controlled by this node"
        btcomp.bb.setdefault("Target")

        if world.gathering.get(eid) is not None:
            world.gathering.remove(eid)

###############
#attacking
###############

class BehaviorAttack(BTNode):
    def __init__(self, name):
        self.name = name

    def update(self, btcomp, traversal, entity, world, dt):
        action_attack = world.attacking.get(entity.eid)
        if action_attack:
            if action_attack.status != RUNNING:
                world.gathering.remove(entity.eid)
                return action_attack.status, []
            #else attacking in progress done here either way
            return RUNNING, []

        world.attacking.add(entity.eid, btcomp.bb["Target"].eid)
        return RUNNING, []

    def reset(self, btcomp, world, eid):
        btcomp.bb.setdefault("Target")

        if world.attacking.get(eid) is not None:
            world.attacking.remove(eid)


##########################################################
# Conditions
##########################################################

class VisibleEntities(BTNode):
    def __init__(self,name, negate=False):
        self.name = name
        self.negate = negate

    def update(self, btcomp, traversal, entity, world, dt):
        e = world.entities.get(entity.eid)
        if e.tid in data.awareness:
            btcomp.bb["Visible Entities"] = world.entities_within_range(e.eid, data.awareness[e.tid])
            if btcomp.bb["Visible Entities"] is None and not self.negate:
                return FAILURE, []
            else:
                return SUCCESS, []
        else:
            return FAILURE, []

class IsInRange(BTNode):
    def __init__(self, name, acceptable_range, negate=False):
        self.name = name
        self.range = acceptable_range
        self.negate = negate

    def update(self, btcomp, traversal, entity, world, dt):
        e = world.entities.get(entity.eid)
        if not "Target" in btcomp.bb or btcomp.bb["Target"] is None:
            return FAILURE, []
        else:
            dist = data.render[e.tid]['size'] + data.render[btcomp.bb["Target"].tid]['size'] + self.range
            path = btcomp.bb["Target"].pos - e.pos
            m = path.magnitude()

            if m > dist and not self.negate:
                return FAILURE, []
            else:
                return SUCCESS, []

class IsGatherable(BTNode):
    def __init__(self,name, negate=False):
        self.name = name
        self.negate = negate

    def update(self, btcomp, traversal, entity, world, dt):
        e = world.entities.get(entity.eid)
        gatherables = []
        if btcomp.bb["Visible Entities"] is None:
            return FAILURE, []
        else:
            for eid, ent in btcomp.bb["Visible Entities"]:
                if ent.tid in data.gatherable:
                    path = ent.pos - entity.pos
                    m = path.magnitude()
                    gatherables.append((m, eid, ent))

            if not gatherables:
                return FAILURE, []
            else:
                gatherables.sort(key=lambda e: e[0], reverse=True)
                btcomp.bb["Target"] = gatherables[-1][-1]
                return SUCCESS, []


# build behaviors
'''BTS['test'] = BehaviorMove("Test Move")

movegather = BTSequence("Move and Gather")
movegather.addChild(VisibleEntities("Look Around"))
movegather.addChild(IsGatherable("Is Gatherable?"))
movegather.addChild(BehaviorMove("Move to Gatherable"))
movegather.addChild(IsInRange("Is In Range?", 0))
movegather.addChild(BehaviorGather("Gathering"))

selector = BTSelect("Gather or Explore", True)
selector.addChild(movegather)
selector.addChild(BehaviorMove("Explore"))
BTS['gather']= selector'''