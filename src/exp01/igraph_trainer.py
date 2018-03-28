import os, pickle

from queue import Queue
from constants import *
from trace import ARG_ENTITY

from exp01.igraph import *
from exp01.evaluation import generate_fv

######################################################
# Storing exemplar sequences
######################################################

class IGraphExemplarNode:
    def __init__(self, dn=None, manual_key=None, manual_clock=None):
        self.agent_dn = dn
        self.manual_key = manual_key

        if dn is not None:
            self.start_clock = dn.start_clock
            self.end_clock = dn.end_clock
        else:
            self.start_clock = self.end_clock = manual_clock

        self.behaviors = {}

    def add_overlap(self, dn):
        self.behaviors[dn.arg_value('agent')] = dn

        # adjust start/end
        self.start_clock = max(self.start_clock, dn.start_clock)
        self.end_clock = min(self.end_clock, dn.end_clock)

    def key(self):
        """For indexing nodes and edges."""
        if self.agent_dn is None: return self.manual_key,{}

        # start the mapping with the agent behavior
        mapping = {}
        for label, eid in self.agent_dn.labeled_entity_ids().items():
            mapping[eid] = label

        # add other entities in argument order, so that keys are canonical
        next = 1
        for eid in self.ordered_entities():
            if eid not in mapping:
                # new player, give generic label
                mapping[eid] = 'entity{}'.format(next)
                next += 1

        # include behaviors in entity order
        key = self.agent_dn.behavior_sig_generic(mapping)
        for eid in self.ordered_entities():
            if eid in self.behaviors:
                key += '-'
                key += self.behaviors[eid].behavior_sig_generic(mapping)

        return key,mapping

    def ordered_entities(self):
        """Return all entities besides the agent, in argument appearance."""

        # start with the agent behavior
        agent_eid = self.agent_dn.arg_value('agent')
        done = set([agent_eid])
        q = Queue()

        # start by adding all the agent behavior entities to the queue
        for eid in self.agent_dn.arg_values(include_types=(ARG_ENTITY,)):
            if eid not in done:
                done.add(eid)
                q.put(eid)

        # clear the queue (all behaviors linked by agent)
        while not q.empty():
            # return the next entity
            next_eid = q.get()
            yield next_eid
            # then add any newcomers from it's behavior, in order, to the end of the queue
            if next_eid in self.behaviors:
                for eid in self.behaviors[next_eid].arg_values(include_types=(ARG_ENTITY,)):
                    if eid not in done:
                        done.add(eid)
                        q.put(eid)

        # remining behaviors are linked by target, just return for now
        for next_eid in self.behaviors:
            if next_eid not in done:
                yield next_eid

    def __str__(self):
        if self.agent_dn is None:
            return '[{:.2f}-{:.2f}] {}'.format(self.start_clock, self.end_clock, self.manual_key)
        else:
            return '[{:.2f}-{:.2f}] {} :{}'.format(self.start_clock, self.end_clock,
                                                   '-'.join([self.agent_dn.behavior_sig()] + [dn.behavior_sig() for dn in self.behaviors.values()]),
                                                   self.agent_dn.status)

######################################################
# Interactive Graph Training classes
######################################################

class IGraphTrain:
    def __init__(self):
        self.nodes = {'idle' : IGraphTrainNode(self, 'idle'),
                      'dead' : IGraphTrainNode(self, 'dead'),
                      }

    def add_exemplar(self, exemplar, trace):
        # first choice from idle
        idle = self.nodes['idle']
        idle.choices.add((exemplar[0].agent_dn.behavior_name,None))

        # for maximum flexibility, pass the whole sequence and an index
        for i in range(len(exemplar)):
            key,mapping = exemplar[i].key()
            if not self.add_exemplar_node(exemplar, i, trace, key=key):
                # add new graph node
                self.nodes[key] = IGraphTrainNode(self, key)
                self.nodes[key].add_exemplar_node(exemplar, i, trace)

    def add_exemplar_node(self, exemplar, i, trace, key=None):
        # for each exemplar node, add it to the correct graph node or create new
        if key is None:
            key,maping = exemplar[i].key()
        for node in self.nodes.values():
            if node.match_key(key):
                node.add_exemplar_node(exemplar, i, trace)
                return True
        return False

    def update_exemplar_outcomes(self):
        for node in self.nodes.values():
            node.update_exemplar_outcomes()

    def save_igraph(self, model_dir, model_file):
        igraph = IGraph()
        igraph.nodes = {k : n.export(igraph) for k,n in self.nodes.items()}

        with open(os.path.join(model_dir, model_file), 'wb') as f:
            pickle.dump(igraph, f)

    def print_graph(self, print_exemplars=False):
        print("\n===================================== IGraph ============================================\n")
        for k,n in self.nodes.items():
            n.print_node(print_exemplars)


class IGraphTrainNode:
    def __init__(self, igraph, key):
        self.igraph = igraph
        self.key = key
        self.exemplar_count = 0

        self.success_outcomes = []
        self.success_duration_estimator = None
        self.death_estimator = None

        self.transition_predictors = {}

        self.choices = set()

        self.avg_reward = 0

        # not sure about this one yet
        self.choice_transitions = {}

        # exemplars
        self.transitions = {}
        self.success = []
        self.failure = []
        self.death = []

    def match_key(self, key): return self.key == key

    def export(self, graph):
        ign = IGraphNode(self.key, graph)
        ign.success_outcomes = self.success_outcomes
        ign.success_duration_estimator = self.success_duration_estimator
        ign.death_estimator = self.death_estimator

        if self.exemplar_count > 0:
            ign.success_pct = len(self.success) / self.exemplar_count
            ign.avg_reward = self.avg_reward
            ign.death_pct = len(self.death) / self.exemplar_count

        ign.choices = self.choices
        ign.transition_predictors = self.transition_predictors

        return ign

    ##################################################
    # Adding exemplars
    ##################################################

    def add_exemplar_node(self, exemplar, i, trace):
        src_node = exemplar[i]
        if src_node.agent_dn is None:
            # end state
            return

        dest_node = exemplar[i+1]

        self.exemplar_count += 1

        # successful completions
        if src_node.agent_dn.status == SUCCESS and src_node.agent_dn.end_clock == src_node.end_clock:
            self.success.append((exemplar,i,trace))
            exemplar[i].effects = generate_effects(trace.state(exemplar[i].start_clock), trace.state(exemplar[i].end_clock))
            self.update_outcomes(exemplar[i].effects)

            if any(isinstance(e, StateDelta_Obtain) for e in exemplar[i].effects):
                self.avg_reward = 0.33

            # REM: success here means transition to an idle node, then from that idle node
            # REM: not necessarily 'idle', have to do state_sig update, but first...
            if i < len(exemplar) - 1 and exemplar[i+1].agent_dn is not None and not exemplar[i+1].agent_dn.instantaneous():
                # not last
                idle = self.igraph.nodes['idle']
                idle.choices.add((exemplar[i+1].agent_dn.behavior_name, None))

        # failures
        elif src_node.agent_dn.status == FAILURE and src_node.agent_dn.end_clock == src_node.end_clock:
            self.failure.append((exemplar, i))

        # interrupted by being dead
        elif dest_node.manual_key == 'killed':
            self.death.append((exemplar, i, trace))

        else:
            # agent changed what they were doing
            choice = self.find_or_make_choice(exemplar, i)
            if choice.choice_sig != 'NULL':
                choice.add_exemplar(exemplar,i)
                self.choices.add((choice.choice_sig,None))

            # transitions
            else:
                key,mapping = dest_node.key()
                if key not in self.transitions:
                    self.transitions[key] = []
                self.transitions[key].append((exemplar,i,trace,dreverse(mapping)))

    ##################################################
    # Choices
    ##################################################

    def choice_sig(self, exemplar, i):
        # last node in the sequence is no choice
        if i == len(exemplar) - 1: return 'NULL'

        src_node = exemplar[i]
        dest_node = exemplar[i+1]

        if src_node.agent_dn.behavior_sig() == dest_node.agent_dn.behavior_sig():
            # no change, no choice
            return 'NULL'

        # otherwise, it's the destination agent behavior?
        return dest_node.agent_dn.behavior_name

    def find_or_make_choice(self, exemplar, i):
        cs = self.choice_sig(exemplar, i)
        if cs not in self.choice_transitions:
            # add new
            choice = IGraphTrainChoice(cs)
            self.choice_transitions[cs] = choice
        return self.choice_transitions[cs]

    ##################################################
    # Outcome effects
    ##################################################

    def update_outcomes(self, new_effects):
        # check this new one against all the existing outcomes (effect sets)
        if len(new_effects) == 0: return

        matched = False
        split_old = None
        while new_effects != None and len(new_effects) > 0:
            for i, outcome in enumerate(self.success_outcomes):
                matched,split_old,new_effects = outcome.update(new_effects)
                if matched: break

            if not matched:
                # new one! add and all done here
                self.success_outcomes.append(Outcome(new_effects))
                return

            if split_old is not None and len(split_old) > 0:
                # existing effects from the match split off, just add them and keep going
                self.success_outcomes.append(Outcome(split_old))

    def update_exemplar_outcomes(self):
        """Sweep through all exemplars and assign to current outcome sets."""
        for exemplar,i,trace in self.success:
            enode = exemplar[i]
            enode.outcomes = set()
            for i, outcome in enumerate(self.success_outcomes):
                if effects_subsume(enode.effects, outcome.effects):
                    # e is a positive exemplar for outcome
                    enode.outcomes.add(i)

    ##################################################
    # Training data
    ##################################################

    def fv_dictionary_to_lists(self, FVdict):
        """Convert from dictionary to list of var names, lists of values. Just for convenience."""
        vars = list(FVdict[0].keys())
        FV = []
        for fv in FVdict:
            #for v in vars:
                # if v not in fv:
                #     print("{} not in {}".format(v, fv))
            FV.append([fv[v] for v in vars])
        return vars,FV

    def training_data_for_outcome(self, ioutcome):
        FV = []
        y = []
        for exemplar,i,trace in self.success:
            enode = exemplar[i]
            le = enode.agent_dn.labeled_entities(trace)
            if any(v is None for v in le.values()):
                #print("Bad dn {}".format(enode.agent_dn))
                continue
            FV.append(generate_fv(trace.state(exemplar[i].start_clock), le))
            if ioutcome in enode.outcomes:
                # positive exemplar
                y.append(1)
            else:
                y.append(0)
        return (*self.fv_dictionary_to_lists(FV),y)

    def training_data_for_death(self):
        FV = []
        y = []
        for exemplar,i,trace in self.death:
            enode = exemplar[i]
            le = enode.agent_dn.labeled_entities(trace)
            if any(v is None for v in le.values()):
                #print("Bad dn {}".format(enode.agent_dn))
                continue
            FV.append(generate_fv(trace.state(exemplar[i].start_clock), le))
            y.append(1)
        for exemplar,i,trace in self.success:
            enode = exemplar[i]
            le = enode.agent_dn.labeled_entities(trace)
            if any(v is None for v in le.values()):
                #print("Bad dn {}".format(enode.agent_dn))
                continue
            FV.append(generate_fv(trace.state(exemplar[i].start_clock), le))
            y.append(0)
        return (*self.fv_dictionary_to_lists(FV),y)

    def training_data_for_value(self, var):
        FV = []
        y = []
        for exemplar,i,trace in self.success:
            enode = exemplar[i]
            le = enode.agent_dn.labeled_entities(trace)
            if any(v is None for v in le.values()):
                #print("Bad dn {}".format(enode.agent_dn))
                continue
            FV.append(generate_fv(trace.state(exemplar[i].start_clock), le))
            y.append(self.enode_value(enode, var))
        return (*self.fv_dictionary_to_lists(FV),y)

    def enode_value(self, enode, variable):
        """Return value for specified variable for this exemplar."""
        if variable == 'duration': return enode.agent_dn.duration()
        elif variable == 'status' : return enode.agent_dn.status
        else: return None

    def training_data_for_transition(self, dest_key):
        FV = []
        y = []

        # establish extra entities first
        exemplar,i,trace,dest_mapping = self.transitions[dest_key][0]
        key, src_mapping = exemplar[i].key()
        extra_entity_labels = list(dsub(dest_mapping, dreverse(src_mapping)).keys())
        #print("extras:", extra_entity_labels)

        # handle positive transition first
        for exemplar, i, trace, dest_mapping in self.transitions[dest_key]:
            enode = exemplar[i]
            key, src_mapping = enode.key()
            src_mapping = dreverse(src_mapping)
            extra_entities = dsub(dest_mapping, src_mapping)

            # positive example
            m = dadd(src_mapping, extra_entities)
            state = trace.state(enode.start_clock)
            me = {k : state.entities.get(v) for k,v in m.items()}
            #print("Pos:", m)
            FV.append(generate_fv(state, me))
            y.append(1)

            # negative examples
            for bs in combo_bindings(list(extra_entities.keys()), state, list(m.values())):
                me = {k: state.entities.get(v) for k, v in dadd(src_mapping, bs).items()}
                #print("Neg:", dadd(src_mapping, bs))
                if any(v is None for v in me.values()):
                    # print("Bad dn {}".format(enode.agent_dn))
                    continue
                FV.append(generate_fv(state, me))
                y.append(0)

        # handle negative transitions
        #print("From negative trans...")
        for key,E in self.transitions.items():
            if key != dest_key:
                for exemplar, i, trace, dest_mapping in E:
                    enode = exemplar[i]
                    key, src_mapping = enode.key()
                    src_mapping = dreverse(src_mapping)

                    # negative examples
                    for bs in combo_bindings(extra_entity_labels, state, list(src_mapping.values())):
                        me = {k: state.entities.get(v) for k, v in dadd(src_mapping, bs).items()}
                        #print("Neg:", dadd(src_mapping, bs))
                        if any(v is None for v in me.values()):
                            # print("Bad dn {}".format(enode.agent_dn))
                            continue
                        FV.append(generate_fv(state, me))
                        y.append(0)

        return (extra_entity_labels,*self.fv_dictionary_to_lists(FV),y)

    ##################################################
    # Utility
    ##################################################

    def print_node(self, print_exemplars=False):
        print("===== Node {} ======".format(self.key))

        print("Choices:", ', '.join((cs[0] for cs in self.choices)))

        print("Success Outcomes:", '; '.join((str(o) for o in self.success_outcomes)))

        print("--- SUCCESS ---")
        for exemplar,i,trace in self.success:
            print(exemplar[i])

        print("--- FAILURE ---")
        for exemplar,i in self.failure:
            print(exemplar[i])

        print("--- DEATH ---")
        for exemplar,i in self.death:
            print(exemplar[i])

        print("--- Transitions ---")
        for key,EI in self.transitions.items():
            for exemplar,i in EI:
                print(exemplar[i], '=>', key)

        for c in self.choice_transitions.values():
            c.print_choice(print_exemplars)

class IGraphTrainChoice:
    def __init__(self, choice_sig):
        # exemplars are only meaningful within a certain choice
        self.exemplars = []
        # predict transitions given this choice
        self.transition_predictors = []

        self.choice_sig = choice_sig

    def add_exemplar(self, exemplar, i):
        self.exemplars.append((exemplar, i))

    def print_choice(self, print_exemplars=False):
        print("===== Choice {} ======".format(self.choice_sig))
        if print_exemplars:
            for e,i in self.exemplars:
                if i < len(e) - 1:
                    print(e[i], "=>", e[i+1])
                else:
                    print(e[i], '=> end')

class IGraphTrainTransition:
    def __init__(self, dest):
        self.destination_key = dest

        self.vars = []
        # per-choice predictors
        self.choice_predictors = []

        # estimators
        self.duration_estimator = None

OUTCOME_MODELS = [StateDelta_Obtain,
                  StateDelta_Died,
                  ]

def generate_effects(s0, s1):
    O = []
    for m in OUTCOME_MODELS:
        for outcome in m.generate(s0, s1):
            O.append(outcome)
    return O

def effects_subsume(e1, e2):
    """Return true if all effects in e2 and also in e1."""
    return all((any((e.like(comp) for comp in e1)) for e in e2))

# class IGraphNode:
#     def __init__(self, dn=None, manual_key=None):
#         self.agent_dn = dn
#         self.manual_key = manual_key
#         self.mapping = {}
#         self.next_entity_label_ct = 1
#
#         if dn is not None:
#             self.start_clock = dn.start_clock
#             self.end_clock = dn.end_clock
#
#             for label,eid in dn.labeled_entity_ids().items():
#                 self.mapping[eid] = label
#         else:
#             self.start_clock = self.end_clock = 0
#
#         self.behaviors = []
#
#     def add_overlap(self, dn):
#         self.behaviors.append(dn)
#         # expand mapping
#         for eid in dn.entity_ids():
#             if eid not in self.mapping:
#                 # new player, give generic label
#                 self.mapping[eid] = 'entity{}'.format(self.next_entity_label_ct)
#                 self.next_entity_label_ct += 1
#         # adjust start/end
#         self.start_clock = max(self.start_clock, dn.start_clock)
#         self.end_clock = min(self.end_clock, dn.end_clock)
#
#     def key(self):
#         """For indexing nodes and edges."""
#         if self.agent_dn is None: return self.manual_key
#         return '-'.join([self.agent_dn.behavior_sig_generic(self.mapping)] + [dn.behavior_sig_generic(self.mapping) for dn in self.behaviors])
#
#     def merge(self, ign):
#         # just add exemplars?
#         pass
#
#     def __str__(self):
#         return '[{:.2f}-{:.2f}] {}'.format(self.start_clock, self.end_clock,
#                                            self.agent_dn is None and self.manual_key or \
#                                            '-'.join([self.agent_dn.behavior_sig()] + [dn.behavior_sig() for dn in self.behaviors]))
