##########################
#  Agent Variables
##########################

import random, os

from components.cbehavior import *
from components.reasoning.goals import Goal_HasItemType, GoalNode
from components.cagent import CAgent

from exp01.igraph import StateSignature, IGraph, IGraphNodeBinding

MODEL_DIR = os.path.join("models")
#SCHEMA_LIB_FILE = 'schema_lib_0_empty.pkl'
#SCHEMA_LIB_FILE = 'schema_lib_1_gather_close.pkl'
SCHEMA_LIB_FILE = 'schema_lib_2_gather_trees.pkl'

# module level
DEBUG = True

##############################################################
# Explore/Exploit Agent
##############################################################

class CAgent_ExploreExploit(CAgent):
    """Can produce random or policy behaviors. Subclass to specify policy."""

    def __init__(self, eid, goals, e, ie):
        super().__init__(eid, goals)

        # goal planning
        self.planner = GoalNode("WIN")
        s = self.planner.add_strategy(None)
        for g in goals:
            s.add_precedent(GoalNode(g))

        self.e = e
        self.ie = ie

        self.int_timer = 0

    ########### behavior generation/evaluation ##############

    def consider(self, world, dt, trace=None, n=1):
        """
        Return the top n options at this time, with e% chance of each being a random option. Return all if n is None.
        Each consider has a probability ie every 0.1s of interrupting randomly.
        """

        # check the exploitation view
        candidates = self.consider_exploit(world, dt, trace, n)

        if len(candidates) > 0:
            # conditionally replace with random ones
            self.randoms = self.random_choices(world)
            candidates = [self.explore_replace(c, world) for c in candidates]
            self.randoms = None

        elif self.active_behavior is None or self.active_behavior.status != RUNNING:
            # no candidates, nothing going on, go random
            print("[{:.2f}] no exploit choices, exploring instead".format(world.clock))
            candidates = self.random_choices(world)[:n]

        # no exploit candidates, check for explore interrupt
        else:
            if self.int_timer > 0.1:
                self.int_timer = 0
                if random.random() < self.ie:
                    if ACTION_LOG and not world.simulation: print("[{:.2f}] explore interrupt".format(world.clock))
                    candidates = self.random_choices(world)[:n]
            else:
                self.int_timer += dt

        # candidates set
        if len(candidates) > 0:
            # set next behavior for self
            if candidates[0] != self.active_behavior:
                self.proposal = candidates[0]
                ent = world.entities.get(self.eid)
                if ACTION_LOG and not world.simulation: print("[{:.2f}] {} selecting {}".format(world.clock, ent, self.proposal.short()))
                return candidates

        return None

    def consider_exploit(self, world, dt, trace, n):
        return []

    def random_choices(self, world):
        # generate all candidate behaviors: gather, fight, flee, craft
        candidates = []
        for eid,ent in world.entities_within_range(self.eid, data.awareness[data.AGENT_TYPE_ID]):
            if ent.tid in data.gatherable:
                candidates.append(CBehaviorMoveAndGather(self.eid, eid))
            if ent.tid in data.combatants:
        #        candidates.append(CBehaviorFlee(eid))
                candidates.append(CBehaviorMoveAndAttack(self.eid, eid))
        #for iclass in data.recipes.keys():
        #    candidates.append(CBehaviorCraft(iclass))
        #candidates.append(CBehaviorMoveToLocation(world.randloc()))

        random.shuffle(candidates)
        return candidates

    def explore_replace(self, behavior, world):
        if random.random() > self.e:
            return behavior
        if ACTION_LOG and not world.simulation: print("[{:.2f}] explore replace with random".format(world.clock))
        r = self.randoms[0]
        self.randoms = self.randoms[1:]
        return r

##############################################################
# Outcome Evaluation Agent
##############################################################

class CAgent_OutcomeEval(CAgent_ExploreExploit):
    def __init__(self, eid, goals, e, ie, model_dir="", model_file=""):
        super().__init__(eid, goals, e, ie)

        # retrieve igraph
        self.igraph = IGraph.load(model_dir, model_file)
        #self.current_state = IGraphNodeBinding(self.igraph.get_node('idle'))

        self.key = None
        self.next_frame = False

    def consider_exploit(self, world, dt, trace, n):
        """Override to perform outcome-based kb evaluation."""

        # generate igraph key (agent can handle tracking state diff w/o generic)
        state_sig = StateSignature()
        state_sig.bind(self, world, trace)

        # don't thrash because I just changed something
        if self.next_frame:
            self.next_frame = False
            self.key = state_sig
            return []

        if state_sig.agent_behavior == 'idle':
            print('Key [{}]: {}'.format(world.clock, state_sig))
            self.key = state_sig

            candidates = []

            choices = self.random_choices(world)
            for choice in choices:
                choice_state_sig = state_sig.update_agent_behavior(choice.sig())
                cbound = self.igraph.bind_state(choice_state_sig)
                if cbound is not None:
                    cbound.evaluate(self, world)
                    candidates.append(cbound)

            candidates = bin_sort(candidates)

            # if len(candidates) == 0:
            #     return [CBehaviorMoveToLocation(self.eid, world.randloc())]

            for c in candidates:
                print("{} value: {} concern: {}".format(c.state_sig, c.value_ratio(), c.death_concern()))

            self.next_frame = True
            return [c.instantiate() for c in candidates]

            # if bound is None:
            #     # unobserved state, random it up
            #     print("Unobserved state!")
            #     return [CBehaviorMoveToLocation(self.eid, world.randloc())]
            #
            # # evaluate choices from idle state
            # print("Choices!")
            # bound.evaluate(self, world)
            # for cbound in bound.bind_candidate_choices(world, self.igraph):
            #     print(cbound.node, cbound.state_sig)
            #     cbound.evaluate(self, world)

        elif state_sig != self.key:
            print('Key [{}]: {}'.format(world.clock, state_sig))
            self.key = state_sig

            candidates = []

            bound = self.igraph.bind_state(state_sig)
            if bound is not None:
                bound.evaluate(self, world)
                candidates.append(bound)

            choices = self.random_choices(world)
            for choice in choices:
                choice_state_sig = state_sig.update_agent_behavior(choice.sig())
                cbound = self.igraph.bind_state(choice_state_sig)
                if cbound is not None:
                    cbound.evaluate(self, world)
                    candidates.append(cbound)

            candidates = bin_sort(candidates)

            # if len(candidates) == 0:
            #     return [CBehaviorMoveToLocation(self.eid, world.randloc())]

            # for c in candidates:
            #     print("{} value: {} concern: {}".format(c.state_sig, c.value_ratio(), c.death_concern()))

            self.next_frame = True
            return [c.instantiate() for c in candidates]

            # evaluate current state (that I or other just switched us to)

            # evaluate other choices I could make

            # stay the course or pick the best

        # node = self.igraph.lookup_state(self, world)
        # if node != self.current_state.node or self.current_state.is_idle():
        #     # time to reconsider
        #     if node != self.current_state.node:
        #         # changed state, update evaluation of value
        #         self.current_state = IGraphNodeBinding(node)
        #         self.current_state.evaluate(self, world)
        #
        #     # bind all the choices from this state and evaluate their value
        #     # candidates is a list of (bound behavior, value)
        #     candidates = self.current_state().bind_candidate_choices(self, world)
        #
        #     # add current state (no-op)
        #     candidates.append((CBehaviorNoOp(), self.current_state.value_ratio()))
        #     # add random movement as "better than 0"
        #     candidates.append((CBehaviorMoveToLocation(self.eid, world.randloc()), 0.0001))
        #
        #     # sort and return requested amount
        #     candidates.sort(key=lambda cc: cc[1], reverse=True)
        #     return candidates[:n]

        return []

def bin_sort(candidates):
    """Sort by risk bin, then reward. Discard candidates with no reward."""
    bins = {0:[],1:[],2:[]}
    for c in candidates:
        if c.value_ratio() <= 0:
            continue

        for bini in range(len(bins.keys())):
            if c.death_concern() < (bini+1) * 0.33:
                bins[bini].append(c)
                break

    final = []
    for bini in reversed(range(len(bins.keys())-1)):
        final.extend(sorted(bins[bini], key=lambda c: c.value_ratio(), reverse=True))

    return final
