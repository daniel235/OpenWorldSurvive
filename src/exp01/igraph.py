import os, pickle, re, copy
import numpy as np

from queue import Queue
from components.cbehavior import *
from components.reasoning.goals import Goal_HasItemType

from trace import behavior_class, behavior_params, explode_behavior_sig
from trace import ARG_ENTITY
from constants import *

class StateSignature:
    def bind(self, cagent, world, trace):
        self.agent_eid = cagent.eid
        self.agent_behavior = ''
        self.behaviors = {}

        # agent behavior first
        if world.entities.get(cagent.eid) is None:
            self.agent_behavior = 'dead'
            return

        agent_dn = None
        for dn in trace.decisions:
            if dn.end_clock is None:
                if dn.arg_value('agent') == cagent.eid:
                    agent_dn = dn
                    break
        if agent_dn is None or agent_dn.status != RUNNING:
            self.agent_behavior = 'idle'
            active_eids = (self.agent_eid,)
        else:
            self.agent_behavior = agent_dn.behavior_sig()
            active_eids = agent_dn.labeled_entity_ids().values()

        # now other behaviors that overlap
        for dn in trace.decisions:
            if dn.end_clock is None:
                if dn.arg_value('agent') != self.agent_eid:
                    # currently active, not the agent
                    if self.overlap_entity(active_eids, dn):
                        self.behaviors[dn.arg_value('agent')] = dn.behavior_sig()

        self.generate_mapping()

    def behavior(self):
        bname,args = explode_behavior_sig(self.agent_behavior)
        return behavior_class(bname)(*(int(aval) for acons,aname,aval in args))

    def key(self):
        # include behaviors in entity order, starting with agent
        key = self.agent_behavior

        for eid in self.ordered_entities():
            if eid in self.behaviors:
                key += '-'
                key += self.behaviors[eid]

        pattern = re.compile(r'\b(' + '|'.join((str(i) for i in self.mapping_to_generic.keys())) + r')\b')
        key = pattern.sub(lambda x: self.mapping_to_generic[int(x.group())], key)

        return key

    def update_agent_behavior(self, new_behavior_sig):
        """Return copy with replaced agent behavior sig."""
        ss = StateSignature()
        ss.agent_eid = self.agent_eid
        ss.agent_behavior = new_behavior_sig
        ss.behaviors = {}
        bname, args = explode_behavior_sig(new_behavior_sig)
        seids = [str(aval) for acons,aname,aval in args]
        for eid,bsig in self.behaviors.items():
            if any((bsig.find(seid) != -1 for seid in seids)):
                ss.behaviors[eid] = bsig
        ss.generate_mapping()
        return ss

    def generate_mapping(self):
        """Return a dictionay mapping from actual entity ids to canonical labels."""
        self.mapping_to_generic = {self.agent_eid : 'agent'}

        if self.agent_behavior != 'idle' and self.agent_behavior != 'dead':
            bname,args = explode_behavior_sig(self.agent_behavior)
            for acons,aname,aval in args:
                self.mapping_to_generic[int(aval)] = aname

        # add other entities in argument order, so that keys are canonical
        next = 1
        for eid in self.ordered_entities():
            if eid not in self.mapping_to_generic :
                # new entity, give generic label
                self.mapping_to_generic[eid] = 'entity{}'.format(next)
                next += 1

        return self.mapping_to_generic

    def ordered_entities(self):
        """Return all entities besides the agent, in argument appearance."""
        done = set()

        # start with the agent behavior, if there is one
        if self.agent_behavior != 'idle' and self.agent_behavior != 'dead':
            q = Queue()
            bname,args = explode_behavior_sig(self.agent_behavior)
            done.add(self.agent_eid)

            # start by adding all the agent behavior entities to the queue
            for acons,aname,aval in args:
                eid = int(aval)
                if acons == ARG_ENTITY and eid not in done:
                    done.add(eid)
                    q.put(eid)

            # clear the queue (all behaviors linked by agent)
            while not q.empty():
                # return the next entity
                next_eid = q.get()
                yield next_eid
                # then add any newcomers from it's behavior, in order, to the end of the queue
                if next_eid in self.behaviors:
                    bname,args = explode_behavior_sig(self.agent_behavior)
                    for acons, aname, aval in args:
                        eid = int(aval)
                        if acons == ARG_ENTITY and eid not in done:
                            done.add(eid)
                            q.put(eid)

        # remining behaviors are linked by target, just return for now
        for next_eid in self.behaviors:
            if next_eid not in done:
                yield next_eid

    def overlap_entity(self, eids, dn):
        return any((eid in eids for eid in dn.labeled_entity_ids().values()))

    def __eq__(self, other):
        return self.agent_behavior == other.agent_behavior and \
            len(self.behaviors) == len(other.behaviors) and \
            all((any(bsig0 == bsig1 for bsig1 in self.behaviors.values()) for bsig0 in other.behaviors.values()))

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return "{}-{}".format(self.agent_behavior, '-'.join((b for b in self.behaviors.values())))

class IGraph:
    @staticmethod
    def load(model_dir, model_file):
        fn = os.path.join(model_dir, model_file)
        if os.path.isfile(fn):
            with open(fn, 'rb') as f:
                return pickle.load(f)
        else:
            # no such graph file
            return IGraph()

    def __init__(self):
        # start with empty nodes
        self.nodes = {'idle' : IGraphNode('idle', self),
                      'dead' : IGraphNode('dead', self),

                      '(gather agent target)' : IGraphNode('(gather agent target)', self),
                      }

    ###################################################
    # API
    ###################################################

    def bind_state(self, state_sig):
        key = state_sig.key()

        # # reverse mapping
        # rmap = {v:k for k,v in mapping.items()}
        # print("RMapping:", rmap)

        if key in self.nodes:
            node = self.nodes[key]
            return IGraphNodeBinding(node, state_sig)

        # unobserved state!
        print("Unobserved:", key, "from", state_sig)
        print(', '.join((str(s) for s in state_sig.ordered_entities())))
        print(state_sig.mapping_to_generic)
        return None

    def state_sig(self, cagent, world, trace, generic=False):
        """For indexing nodes and transitions."""
        mapping = {cagent.eid : 'agent'}

        if world.entities.get(cagent.eid) is None:
            return 'dead',mapping

        agent_dn = None
        behaviors = {}
        # find agent dn, if any, first
        for dn in trace.decisions:
            if dn.end_clock is None:
                if dn.arg_value('agent') == cagent.eid:
                    agent_dn = dn
                    break

        if agent_dn is None or agent_dn.status != RUNNING:
            key = 'idle'
        else:
            # start the mapping with the agent behavior
            for label, eid in agent_dn.labeled_entity_ids().items():
                mapping[eid] = label
            if generic:
                key = agent_dn.behavior_sig_generic(mapping)
            else:
                key = agent_dn.behavior_sig()

        # get the rest of the behaviors by overlap
        for dn in trace.decisions:
            if dn.end_clock is None:
                if dn.arg_value('agent') != cagent.eid:
                    if self.overlap_entity(mapping.keys(), dn):
                        behaviors[dn.arg_value('agent')] = dn

        # add other entities in argument order, so that keys are canonical
        next = 1
        for eid in self.ordered_entities(agent_dn, behaviors):
            if eid not in mapping:
                # new entity, give generic label
                mapping[eid] = 'entity{}'.format(next)
                next += 1

        # include behaviors in entity order
        for eid in self.ordered_entities(agent_dn, behaviors):
            if eid in behaviors:
                key += '-'
                if generic:
                    key += behaviors[eid].behavior_sig_generic(mapping)
                else:
                    key += behaviors[eid].behavior_sig()

        return key,mapping

    def overlap_entity(self, eids, dn):
        return any((eid in eids for eid in dn.labeled_entity_ids().values()))

    def ordered_entities(self, agent_dn, behaviors):
        """Return all entities besides the agent, in argument appearance."""

        done = set()

        # start with the agent behavior, if there is one
        if agent_dn is not None and agent_dn.status == RUNNING:
            q = Queue()
            agent_eid = agent_dn.arg_value('agent')
            done.add(agent_eid)

            # start by adding all the agent behavior entities to the queue
            for eid in agent_dn.arg_values(include_types=(ARG_ENTITY,)):
                if eid not in done:
                    done.add(eid)
                    q.put(eid)

            # clear the queue (all behaviors linked by agent)
            while not q.empty():
                # return the next entity
                next_eid = q.get()
                yield next_eid
                # then add any newcomers from it's behavior, in order, to the end of the queue
                if next_eid in behaviors:
                    for eid in behaviors[next_eid].arg_values(include_types=(ARG_ENTITY,)):
                        if eid not in done:
                            done.add(eid)
                            q.put(eid)

        # remining behaviors are linked by target, just return for now
        for next_eid in behaviors:
            if next_eid not in done:
                yield next_eid

class IGraphNode:
    def __init__(self, key, igraph):
        self.igraph = igraph
        self.key = key

        self.success_pct = 0
        self.death_pct = 0
        self.avg_reward = 0

        # run to completion outcomes
        self.success_outcomes = []
        self.success_duration_estimator = None
        self.death_estimator = None

        # choices are behavior names, label mappings and either a transition number or predictor
        self.choices = [('gather', None)]

        self.transition_predictors = {}

    def is_idle(self):
        return self.key.startswith('idle')

    ##################################################
    # Utility
    ##################################################

    def __str__(self): return 'Node({})'.format(self.key)

class IGraphNodeBinding:
    def __init__(self, inode, state_sig):
        self.node = inode
        self.state_sig = state_sig

        self.reward = 0
        self.cost = 1
        self.death_prob = 0
        self.dread = 0

    def bind_candidate_choices(self, world, igraph):
        agent_eid = self.state_sig.agent_eid
        agent = world.entities.get(agent_eid)

        for bname,mapping in self.node.choices:
            bclass = behavior_class(bname)
            # target only for the moment
            for target_eid in bclass.target_eids_for_agent(agent, world):
                new_behavior_sig = '({} {} {})'.format(bname, agent_eid, target_eid)
                choice_state_sig = self.state_sig.update_agent_behavior(new_behavior_sig)
                next = igraph.bind_state(choice_state_sig)
                if next is not None:
                    yield next

    def evaluate(self, cagent, world):
        self.dread = 0
        self.death_prob = 0
        self.reward = 0
        self.cost = 1

        if self.node.is_idle():
            return 0

        rmap = {v: world.entities.get(k) for k, v in self.state_sig.mapping_to_generic.items()}
        if any((v is None for v in rmap.values())):
            print("Bad RMap {}".format(self.state_sig.mapping_to_generic))
            return

        noint = []
        nodeath = []
        for dest_key,(est,v,extra_entity_labels) in self.node.transition_predictors.items():
            dest_node = self.node.igraph.nodes[dest_key]
            for bs in combo_bindings(extra_entity_labels, world, list((ent.eid for ent in rmap.values()))):
                prob = est.estimate_from_scenario(dadd(rmap, {label:world.entities.get(eid) for label,eid in bs.items()}), world)[0][1]
                #print("  Transition:", dest_key, v, bs, prob, dest_node.success_pct, dest_node.death_pct)
                noint.append(1.0 - prob)
                nodeath.append(1.0 - (prob * dest_node.death_pct * DREAD_FACTOR))

        noint_prob = np.product(noint)
        self.dread = 1.0 - np.product(nodeath)

        # death odds
        if self.node.death_estimator is not None:
            est, v = self.node.death_estimator
            self.death_prob = est.estimate_from_scenario(rmap, world)[0][1]

        for outcome in self.node.success_outcomes:
            # REM: only entities from the actual agent behavior here, right?
            prob = outcome.estimate_from_scenario(rmap, world)
            #print("Odds of outcome {}: {}".format(outcome, prob))
            for effect in outcome.effects:
                for gn in cagent.planner.all_goal_nodes():
                    #print(effect, gn, effect.outcome_value(gn))
                    self.reward += prob * (effect.outcome_value(gn))

        self.reward = self.reward * noint_prob

        # material cost?

        # time cost
        if self.node.success_duration_estimator is not None:
            est = self.node.success_duration_estimator[0][0]
            if self.node.success_duration_estimator[1][1] > self.node.success_duration_estimator[0][1]:
                est = self.node.success_duration_estimator[1][0]
            self.cost = est.estimate_from_scenario(rmap, world)

        #print("  Value: {}, Death%: {}, ".format(self.value_ratio(), self.death_concern()))

            #self.success_duration_estimator = None
        #cost = dest.estimate([(target.pos - agent.pos).magnitude()])
        #self.cost = self.schema.duration_estimator.estimate_from_scenario({'agent': agent, 'target': target}, world)

        # print("{}".format(self.state_sig))
        # print("expected reward: {}".format(self.reward))
        # print("expected cost: {}".format(self.cost))

    def death_concern(self):
        return self.death_prob + self.dread

    def value_ratio(self):
        return self.reward / self.cost

    def instantiate(self):
        """Return ready to go behavior."""
        return self.state_sig.behavior()


########################################################################
# Behavior outcome and effect models
########################################################################

class Outcome:
    """Class just holds a list, but makes updating/splitting cleaner."""
    def __init__(self, effects):
        self.effects = effects
        self.probability_predictor = None

    def estimate_from_scenario(self, labeled_entities, world):
        """Estimate probability of this outcome from my predictor."""
        if self.probability_predictor is not None:
            #print("Using predictor w/ val", self.probability_predictor[1])
            return self.probability_predictor[0].estimate_from_scenario(labeled_entities, world)[0][1]

        # dunno
        return 0.5

    def update(self, new_effects):
        # calculate intersection of effects, left overs on lhs and rhs
        its, lhs, rhs = outcome_intersection(self.effects, new_effects)
        # print("new: {}".format([str(e) for e in new_effects]))
        # print("its: {}".format([str(e) for e in its]))
        # print("lhs: {}".format([str(e) for e in lhs]))
        # print("rhs: {}".format([str(e) for e in rhs]))

        if len(its) == 0:
            # no intersection, exemplar doesn't fit here
            return False,None,new_effects

        if len(rhs) == 0 and len(lhs) == 0:
            # same set of effects, no need to update
            return True,None,None

        # split this outcome! updates self and returns new ones to be added or appended
        self.effects = its
        return True,lhs,rhs

    def __str__(self):
        return ",".join([str(e) for e in self.effects])

##########################
# Effects (state diffs)
##########################

class StateDelta_Obtain:
    @staticmethod
    def generate(s0, s1):
        """Return Obtain deltas for the diff between dn0 and dn1."""
        for eid,inv0 in s0.inventories.all():
            inv1 = s1.inventories.get(eid)
            # G is a list of (item id, count)
            if inv1 is not None:
                for iid, ct in inv1.gain(inv0):
                    yield StateDelta_Obtain(iid, ct)

    def __init__(self, iid, ct):
        self.iid = iid
        self.ct = ct

    def like(self, other):
        return isinstance(other, StateDelta_Obtain) and other.iid == self.iid

    def outcome_value(self, goal_node):
        if isinstance(goal_node.goal, Goal_HasItemType):
            if self.iid == goal_node.goal.tid:
                return goal_node.goal.value * min(1.0, (self.ct / goal_node.goal.ct))
        return 0

    def substitute(self, entity_mapping):
        # iid is a type, doesn't need to be replaced
        pass

    def __str__(self):
        return "(obtain {} {})".format(self.iid, self.ct)

class StateDelta_Died:
    @staticmethod
    def generate(s0, s1):
        """Return Died deltas for the diff between dn0 and dn1."""
        #print("diff {}, {}".format(dn0, dn1))
        for eid,ent in s0.entities.all():
            #print("entity {}...".format(eid))
            if ent.tid in data.awareness:
                if s1.entities.get(eid) is None:
                    #print("...non-existant at time {}".format(dn1.decision_state.clock))
                    yield StateDelta_Died(eid)

    def __init__(self, eid):
        self.eid = eid

    def like(self, other):
        return isinstance(other, StateDelta_Died) and other.eid == self.eid

    def outcome_value(self, goal_node):
        # if isinstance(goal_node.goal, Goal_HasItemType):
        #     if self.iid == goal_node.goal.tid:
        #         return goal_node.goal.value * min(1.0, (self.ct / goal_node.goal.ct))
        return 0

    def substitute(self, entity_mapping):
        """Swap specific entity id for variable label (e.g. agent, target)."""
        self.eid = entity_mapping[str(self.eid)]

    def __str__(self):
        return "(died {})".format(self.eid)

def outcome_intersection(o1, o2):
    """Return the intersection of the two lists of outcome objects, based on "like" object comparison (ignores numerics)."""
    its = []
    lhs_extra = []
    rhs_extra = []

    for o in o1:
        found = False
        for comp in o2:
            if o.like(comp):
                its.append(o)
                found = True
                break
        if not found:
            lhs_extra.append(o)

    for o in o2:
        found = False
        for comp in its:
            if o.like(comp):
                found = True
                break
        if not found:
            rhs_extra.append(o)

    return its, lhs_extra, rhs_extra


def combo_bindings(labels, state, exclude_eids):
    if len(labels) == 0:
        return [{}]

    sets = []
    for eid,ent in state.entities.all():
        if eid not in exclude_eids and ent.tid in data.combatants:
            front = {labels[0] : eid}
            rest = combo_bindings(labels[1:], state, [eid] + exclude_eids)
            for next in rest:
                sets.append(dadd(front, next))
    return sets

def dreverse(d):
    return {v:k for k,v in d.items()}

def dsub(d0, d1):
    return {k:v for k,v in d0.items() if k not in d1}

def dadd(d0, d1):
    d = dict(d0)
    d.update(d1)
    return d
