# state/behavior/outcome trace
# single line, 1-agent

import copy, re
from constants import *
from components.cbehavior import *

##########################################
# Behavior KB
##########################################

ARG_ENTITY = 0
ARG_TYPEID = 1
ARG_QUANTITY = 2

BEHAVIORS = {'gather' : (CBehaviorMoveAndGather, ((ARG_ENTITY, 'agent'), (ARG_ENTITY, 'target'),)),
             'attack' : (CBehaviorMoveAndAttack, ((ARG_ENTITY, 'agent'), (ARG_ENTITY, 'target'),)),
             'flee' : (CBehaviorFlee, ((ARG_ENTITY, 'agent'), (ARG_ENTITY, 'target'),)),
             'set' : (CBehaviorTrap, ((ARG_ENTITY, 'agent'), (ARG_ENTITY, 'item_type'),)),
             'lure' : (CBehaviorLure, ((ARG_ENTITY, 'agent'), (ARG_ENTITY, 'target'),)),

             'patrol' : (CBehaviorMobPatrol, ((ARG_ENTITY, 'agent'),)),
             'leashing' : (CBehaviorMobPatrol, ((ARG_ENTITY, 'agent'),)),
             'move': (CBehaviorMoveToLocation, ((ARG_ENTITY, 'agent'),)),
             'stunned' : (CBehaviorStun, ((ARG_ENTITY, 'agent'),)),
             'craft' : (CBehaviorCraft, ((ARG_ENTITY, 'agent'), (ARG_TYPEID, 'item_type'),)),
             'eat' : (CBehaviorEat, ((ARG_ENTITY, 'agent'), (ARG_TYPEID, 'item_type'),)),
             'eating' : (CBehaviorEat, ((ARG_ENTITY, 'agent'), (ARG_TYPEID, 'item_type'),)),
             'healing' : (CBehaviorHeal, ((ARG_ENTITY, 'agent'), (ARG_TYPEID, 'item_type'),)),
             'drink' : (CBehaviorDrink, ((ARG_ENTITY, 'agent'), (ARG_TYPEID, 'item_type'),)),
             'killed' : (None, ((ARG_ENTITY, 'agent'), (ARG_ENTITY, 'target'),)),
             'dehydrated' : (None, ((ARG_ENTITY, 'agent'), )),

             'done' : (None, ()),
             'timeout' : (None, ()),
             }

def behavior_class(bname): return BEHAVIORS[bname][0]
def behavior_params(bname): return BEHAVIORS[bname][1]
def explode_behavior_sig(bsig):
    """Return bname, [(acons, aname, aval)...]"""
    m = re.search('\(([a-z]*) (.*)\)', bsig)
    if m is None:
        # as in (done)
        return bsig[1:-1],[]
    else:
        bname = m.group(1)
        argvals = m.group(2).split()
        return bname,[(acons,aname,aval) for (acons,aname),aval in zip(behavior_params(bname),argvals)]

class Trace:
    def __init__(self):
        self.decisions = []
        self.states = []

        # used to mark the trace to take a snapshot at the end of world update
        self.snapshot_state = False

    ##############################################
    # Shared state handling
    ##############################################

    def snapshot(self, world):
        """Store a snapshot of the world if one has been requested."""
        if self.snapshot_state:
            self.states.append(copy.deepcopy(world))
            self.snapshot_state = False

    def state(self, clock):
        for s in self.states:
            if s.clock == clock:
                return s
            elif s.clock > clock:
                # missed it
                return s
        assert False, "Failed to retreive state at {} from {}".format(clock, ','.join([str(s.clock) for s in self.states]))

    ##############################################
    # Decision nodes
    ##############################################

    def add_decision_node(self, clock, behavior_sig, agent_eid=None, instantaneous=None, status=None):
        self.decisions.append(DecisionNode(clock, behavior_sig, agent_eid, instantaneous, status))
        self.snapshot_state = True

    def end_update(self, world, agent_eid, behavior_sig, status):
        # if was running, interrupted
        if status == RUNNING: status = INTERRUPT
        for dn in reversed(self.decisions):
            if dn.agent_eid == agent_eid:
                if dn.is_behavior('killed'):
                    continue
                assert dn.behavior_sig() == behavior_sig, "Failed sig match {} <==> {}".format(dn.behavior_sig(), behavior_sig)
                dn.status = status
                dn.end_clock = world.clock
                self.snapshot_state = True
                return
        assert False, "End update had no prior trace behavior to update for agent {}\n{}".format(agent_eid, "\n".join(str(dn) for dn in self.decisions))

    ##############################################
    # Marking non-behavioral events
    ##############################################

    def add_event(self, world, event, out_of_update=False):
        """Non-behavioral events."""
        self.add_decision_node(world.clock, event, instantaneous=True, status=SUCCESS)
        if out_of_update:
            # event added outside world update, need to snapshot state
            self.snapshot(world)

    def death(self, agent_eid, target_eid, world):
        self.add_decision_node(world.clock, '(killed {} {})'.format(agent_eid, target_eid),
                               agent_eid=agent_eid, instantaneous=True, status=SUCCESS)

    def dehydration(self, agent_eid, world):
        self.add_decision_node(world.clock, '(dehydrated {})'.format(agent_eid),
                               instantaneous=True, status=SUCCESS)

    def looping(self):
        pattern = []
        i=0
        for dn in reversed(self.decisions):
            if len(pattern) < 2:
                pattern.append(dn)
            elif dn.agent_eid == pattern[i].agent_eid and dn.behavior_sig == pattern[i].behavior_sig:
                i += 1
                if i == len(pattern):
                    # matched the whole thing
                    return True
            elif i == 0:
                # no match yet, extend pattern
                pattern.append(dn)
            else:
                # pattern broken, done
                return False
        return False

    ##############################################
    # Clean-up at the end of the run
    ##############################################

    def annotate_endings(self):
        """Update status/time for behaviors interrupted by end of the run or by death."""
        current = {}
        for dn in self.decisions:
            current[dn.agent_eid] = dn
            # deal with killed case, since that ends what target is doing too...
            if (dn.is_behavior('killed') or dn.is_behavior('dehydrated')):
                # clean up what the target was doing
                tgt_eid = dn.behavior_target_id()
                if tgt_eid in current:
                    if current[tgt_eid].status == RUNNING:
                        current[tgt_eid].status = INTERRUPT
                        current[tgt_eid].end_clock = dn.start_clock
                    del current[tgt_eid]
        # mark those interrupted by the end of the game
        for dn in current.values():
            if dn.end_clock is None:
                dn.status = INTERRUPT
                dn.end_clock = self.decisions[-1].start_clock

    ##############################################
    # Reasoning about the trace
    ##############################################

    def agent_eids(self):
        """Return all agent-type eids that act in this trace."""
        return set(agent.eid for agent in (dn.entity('agent', self) for dn in self.decisions) if agent is not None and agent.tid == data.AGENT_TYPE_ID)

    def __str__(self):
        return "\n".join((str(dn) for dn in self.decisions))

class DecisionNode:
    """
    Decision nodes track behavior choices. Instantaneous simply means start and end at
    the same time.

    A DN with no agent is a non-behavioral event, used for book-keeping at this point.
    """

    def __init__(self, clock, behavior_sig, agent_eid=None, instantaneous=False, status=None):
        self.behavior_args = {}

        m = re.search('\(([a-z]*) (.*)\)', behavior_sig)
        if m is None:
            # as in (done)
            self.behavior_name = behavior_sig[1:-1]

        else:
            self.behavior_name = m.group(1)
            argvals = m.group(2).split()

            cls,argcons = BEHAVIORS[self.behavior_name]
            for (acons,aname),val in zip(argcons,argvals):
                if acons == ARG_QUANTITY:
                    self.behavior_args[aname] = (acons, num(val))
                else:
                    # entity and type ids
                    self.behavior_args[aname] = (acons, int(val))

        self.start_clock = clock
        self.status = status or RUNNING

        # optional parameters
        self.agent_eid = agent_eid
        self.end_clock = None
        if instantaneous:
            self.end_clock = self.start_clock
            self.status = status or SUCCESS

    def is_event(self): return self.agent_eid is None

    def instantaneous(self): return self.start_clock == self.end_clock

    def duration(self):
        if self.end_clock is not None: return self.end_clock - self.start_clock
        else: return 0

    def behavior_sig(self):
        return '({} {})'.format(self.behavior_name, ' '.join((str(v) for v in self.arg_values())))

    def behavior_sig_generic(self, mapping=None):
        cls,argcons = BEHAVIORS[self.behavior_name]
        return '({} {})'.format(self.behavior_name, ' '.join((mapping and mapping[self.arg_value(aname)] or aname for acons,aname in argcons)))

    def arg_values(self, include_types=None):
        """Return the argument values in proper order. Only include specified types, or all if None."""
        cls, argcons = BEHAVIORS[self.behavior_name]
        for acons,aname in argcons:
            if include_types is None or acons in include_types:
                yield self.behavior_args[aname][1]

    def arg_value(self, label):
        """Return the specified argument value or None."""
        return label in self.behavior_args and self.behavior_args[label][1]

    def arg_type(self, label):
        """Return the specified argument type or None."""
        return label in self.behavior_args and self.behavior_args[label][0]

    def labeled_entity_ids(self):
        """Return all label : entity ids for this behavior."""
        return {aname : aval for aname,(acons, aval) in self.behavior_args.items() if acons == ARG_ENTITY}

    def labeled_entities(self, trace):
        """Return all label : entities for this behavior."""
        state = trace.state(self.start_clock)
        return {aname : state.entities.get(aval) for aname,(acons, aval) in self.behavior_args.items() if acons == ARG_ENTITY}

    def is_behavior(self, name): return name == self.behavior_name

    def entity(self, label, trace):
        eid = self.arg_value(label)
        if eid is not None:
            state = trace.state(self.start_clock)
            return state.entities.get(eid)
        return None

    #############
    # Compatibility

    def agent(self, trace): return self.entity('agent', trace)
    def behavior_target_id(self): return self.arg_value('target')
    def behavior_target(self, trace): return self.entity('target', trace)
    def behavior_name(self): return self.behavior_name

    def __str__(self):
        if self.end_clock is None:
            return "DN({}) [{:.2f}-] {} :{}".format(self.agent_eid, self.start_clock, self.behavior_sig(), self.status)
        else:
            return "DN({}) [{:.2f}-{:.2f}] {} :{}".format(self.agent_eid, self.start_clock, self.end_clock, self.behavior_sig(), self.status)

def num(s):
    try:
        return int(s)
    except ValueError:
        return float(s)
