# note, shouldn't be that many schema if they're behavior-oriented
# retrieve vs. filter options

import copy, math, os, pickle
import data
from components.cbehavior import *
from components.reasoning.goals import Goal_HasItemType
from constants import *

class SchemaLib:
    """Placeholder for now, abstraction of indexed retrieval later."""
    def __init__(self):
        self.schema = []

    ########## singleton ##########
    lib = None

    @staticmethod
    def get(model_dir="", lib_file=""):
        if SchemaLib.lib is None:
            # load model from disk if possible, otherwise create new, empty one
            fn = os.path.join(model_dir, lib_file)
            if os.path.isfile(fn):
                f = open(fn, 'rb')
                SchemaLib.lib = pickle.load(f)
                f.close()
            else:
                SchemaLib.lib = SchemaLib()
        # return existing
        return SchemaLib.lib

    @staticmethod
    def save(model_dir, lib_file):
        if SchemaLib.lib is not None:
            # save model to disk
            f = open(os.path.join(model_dir, lib_file), 'wb')
            pickle.dump(SchemaLib.lib, f)
            f.close()

class BindingFilter_EntityType:
    def __init__(self, typelist):
        self.typelist = typelist

    def filter(self, entity):
        return entity.tid in self.typelist

ENTITY = 0
TYPEID = 1
QUANTITY = 2

BEHAVIORS = {'gather' : (CBehaviorMoveAndGather, ((ENTITY, 'target'),)),
             'attack' : (CBehaviorMoveAndAttack, ((ENTITY, 'target'),)),
             'killed' : (None, ((ENTITY, 'target'),)),
             # 'flee' : CBehaviorFlee,
             # 'patrol' : CBehaviorMobPatrol,
             # 'leashing' : CBehaviorMobPatrol,
             # 'craft' : CBehaviorCraft,
             # 'eat' : CBehaviorEat,
             # 'drink' : CBehaviorDrink
             }

class Schema:
    def __init__(self, behavior_name):
        self.behavior_class = BEHAVIORS[behavior_name][0]
        self.argv = BEHAVIORS[behavior_name][1]

        self.exemplars = []

        # predict duration across all exemplars
        self.duration_estimator = None

        # outcomes are effect sets
        self.outcomes = []
        # binary predictors for each outcome (not mutually exclusive classes)
        self.outcome_predictors = []

        # responses are behaviors observed to target this agent during this behavior
        self.response_behaviors = set()
        # binary predictors for each response (not mutually exclusive classes)
        self.response_predictors = []

    ##################################################
    # Outcome effects
    ##################################################

    def update_outcomes(self, new_effects):
        # check this new one against all the existing outcomes (effect sets)
        if len(new_effects) == 0: return

        matched = False
        while new_effects != None and len(new_effects) > 0:
            for i, outcome in enumerate(self.outcomes):
                matched,split_old,new_effects = outcome.update(new_effects)
                if matched: break

            if not matched:
                # new one! add and all done here
                self.outcomes.append(Outcome(new_effects))
                return

            if split_old is not None and len(split_old) > 0:
                # existing effects from the match split off, just add them and keep going
                self.outcomes.append(Outcome(split_old))

    ##################################################
    # Managing exemplars
    ##################################################

    def add_exemplar(self, dn, trace, responses=[]):
        """Store exemplars at the schema level, update effects set. Post-process to prepare for training."""
        print("adding", dn.behavior_sig)
        e = Exemplar(dn, trace, responses)
        self.exemplars.append(e)
        if dn.status != INTERRUPT:
            self.update_outcomes(e.effects)

        for sig,rdn in e.responses.items():
            self.response_behaviors.add(sig)

    def update_exemplar_outcomes(self):
        """Sweep through all exemplars and assign to current outcome sets."""
        for e in self.exemplars:
            e.outcomes = set()
            for i,outcome in enumerate(self.outcomes):
                if effects_subsume(e.effects, outcome.effects):
                    # e is a positive exemplar for outcome
                    e.outcomes.add(i)

    ##################################################
    # Training data
    ##################################################

    def labeled_entities(self, dn, trace):
        # these are all behavior, so all have an agent
        labeled_entities = {'agent' : dn.entity('agent', trace)}
        for atype,alabel in self.argv:
            if atype == ENTITY:
                labeled_entities[alabel] = dn.entity(alabel, trace)
        return labeled_entities

    def fv_dictionary_to_lists(self, FVdict):
        """Convert from dictionary to list of var names, lists of values. Just for convenience."""
        vars = list(FVdict[0].keys())
        FV = []
        for fv in FVdict:
            FV.append([fv[v] for v in vars])
        return vars,FV

    def training_data_for_outcome(self, ioutcome):
        FV = []
        y = []
        for e in self.exemplars:
            if e.dn.status == INTERRUPT: continue
            le = self.labeled_entities(e.dn, e.trace)
            if le['agent'] is None or le['target'] is None:
                print("Bad dn {}".format(e.dn))
                continue
            FV.append(generate_fv(e.state(), le))
            if ioutcome in e.outcomes:
                # positive exemplar
                y.append(1)
            else:
                y.append(0)
        return (*self.fv_dictionary_to_lists(FV),y)

    def training_data_for_value(self, var):
        FV = []
        y = []
        for e in self.exemplars:
            if e.dn.status == INTERRUPT: continue
            le = self.labeled_entities(e.dn, e.trace)
            if any(v is None for v in le.values()):
                print("Bad dn {}".format(e.dn))
                continue
            FV.append(generate_fv(e.state(), le))
            y.append(e.value(var))
        return (*self.fv_dictionary_to_lists(FV),y)

    def training_data_for_response(self, response_behavior_name):
        FV = []
        y = []
        for e in self.exemplars:
            # add fv from response to fv from behavior
            state = e.state()
            le = self.labeled_entities(e.dn, e.trace)
            if any(v is None for v in le.values()):
                print("Bad dn {}".format(e.dn))
                continue
            # REM: expand to handle n-ary behaviors with different arg constraints
            eids = [ent.eid for ent in le.values()]
            for responder_eid,responder_ent in state.entities.all():
                # filter behavior agent and target
                if responder_eid not in eids:
                    # REM: only things that can do response...
                    if responder_ent.tid in data.combatants:
                        # potential 3rd entity
                        expanded_le = copy.deepcopy(le)
                        expanded_le['responder'] = responder_ent
                        FV.append(generate_fv(state, expanded_le))
                        if e.positive_response_exemplar(response_behavior_name, responder_eid):
                            y.append(1)
                        else:
                            y.append(0)
        return (*self.fv_dictionary_to_lists(FV),y)

    ##################################################
    # Run-time methods
    ##################################################

    def bind(self, agent_eid, world):
        # every behavior has an agent
        self.agent_eid = agent_eid

        # target only for the moment
        target_eids = self.behavior_class.target_eids_for_agent(world.entities.get(agent_eid), world)

        # learned filters applied here, before powerset and candidate generation
        # - would have to specify target outcome

        for target_eid in target_eids:
            yield BoundSchema(self, {'target' : target_eid})

        # # generate candidate list for each slot from world
        # lists = [self.binding_list(cons, filter, world) for name,cons,filter in self.required_bindings]

        # # fill in binding set with powerset, remember to copy for instantiation!
        # for ps in powerset([name for name,cons,filter in self.required_bindings], lists):
        #     s = Schema(ps)
        #     s.agent_eid = agent_eid
        #     yield s

    ##################################################
    # Utility
    ##################################################

    def __str__(self):
        return "Schema({})".format(self.behavior_class)

    def print(self):
        print(self)
        print('...observed outcomes: {}'.format(', '.join([str(o) for o in self.outcomes])))
        print('...observed responses: {}'.format(', '.join([r for r in self.response_behaviors])))

class Exemplar:
    def __init__(self, dn, trace, responses):
        self.dn = dn
        self.trace = trace

        # mapping from eids to labels in this behavior
        params = BEHAVIORS[dn.behavior_name()][1]
        argv = dn.behavior_args()
        self.entity_mapping = {str(self.dn.agent_eid) : 'agent'}
        for (ptype, plabel),val in zip(params, argv):
            if ptype == ENTITY:
                self.entity_mapping[val] = plabel
                print(self.entity_mapping)

        # establish effects with variable mappings (e.g. agent for specific eid)
        self.effects = self.substitute_effects(generate_effects(dn, trace))

        # response has substituted behavior paired with dn (in same trace)
        self.responses = {self.substitute_sig(rdn) : rdn for rdn in responses
                          if rdn.behavior_name() not in ['done', 'looping', 'killed', 'dehydrated', 'disengaged', 'patrol', 'flee', 'craft', 'leashing']}

        # to be filled in later by sweep
        self.outcomes = set()

    def substitute_effects(self, effects):
        for e in effects:
            e.substitute(self.entity_mapping)
        return effects

    def substitute_sig(self, dn):
        name = dn.behavior_name()
        params = BEHAVIORS[name][1]
        argv = dn.behavior_args()

        subbed = []
        for (ptype,plabel),val in zip(params,argv):
            # only sub for entities in the response args
            if ptype == ENTITY and val in self.entity_mapping:
                # sub for label in the base behavior
                subbed.append(self.entity_mapping[val])
            else:
                subbed.append(val)

        return '({} {})'.format(name, ' '.join(v for v in subbed))

    def state(self): return self.trace.state(self.dn.start_clock)
    def end_state(self): return self.trace.state(self.dn.end_clock)

    def value(self, variable):
        """Return value for specified variable for this exemplar."""
        if variable == 'duration': return self.dn.duration()
        elif variable == 'status' : return self.dn.status
        else: return None

    def positive_response_exemplar(self, bname, agent_eid):
        """True if this exemplar is a positive example of the specified response."""
        for rdn in self.responses.values():
            if rdn.behavior_name() == bname and rdn.agent_eid == agent_eid:
                return True
        return False

class Outcome:
    """Class just holds a list, but makes updating/splitting cleaner."""
    def __init__(self, effects):
        self.effects = effects

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

# class Outcome:
#     def __init__(self, effects, exemplars=None):
#         self.effects = effects
#         if exemplars is not None:
#             self.exemplars = exemplars
#         else:
#             self.exemplars = []
#
#     ##################################################
#     # Managing exemplars, effects
#     ##################################################
#
#     def add_exemplar(self, effects, dn, trace, responses=None):
#         """
#         Add new exemplar, which might involve splitting this outcome. Return true if exemplar is added,
#         and list of newly created outcomes.
#         """
#
#         # calculate intersection of effects, left overs on lhs and rhs
#         its, lhs, rhs = outcome_intersection(effects, self.effects)
#         print("its: {}".format([str(e) for e in its]))
#         print("lhs: {}".format([str(e) for e in lhs]))
#         print("rhs: {}".format([str(e) for e in rhs]))
#
#         if len(its) == 0:
#             if len(self.effects) == 0:
#                 # this is the empty case
#                 self.exemplars.append((dn, trace, responses))
#                 return True,None
#             # no intersection, exemplar doesn't fit here
#             return False,None
#
#         if len(rhs) == 0 and len(lhs) == 0:
#             # same set of effects, store in this outcome
#             self.exemplars.append((dn, trace, responses))
#             return True, None
#
#         # split this outcome! updates self and returns new ones to be appended
#         return True,self.split(dn, trace, responses, its, lhs, rhs)
#
#     def split(self, dn, trace, responses, its, lhs, rhs):
#         """
#         The outcome group and the exemplar have an overlapping intersection. This splits into three groups: the intersection,
#         the extras in the group and the extras in the exemplar.
#         """
#         exemplars_copy = list(self.exemplars)
#
#         # existing group: reduce effects and add new exemplar
#         self.effects = its
#         self.exemplars.append((dn, trace, responses))
#
#         # additional groups
#         splits = []
#
#         # leftovers from the existing group get all the existing exemplars
#         if len(lhs) > 0:
#             splits.append(Outcome(lhs, exemplars_copy))
#
#         # leftovers from new exemplar just get that one exemplar
#         if len(rhs) > 0:
#             splits.append(Outcome(rhs, [(dn, trace, responses)]))
#
#         return splits
#
#     ##################################################
#     # Managing exemplars, effects
#     ##################################################
#
#     def extract_fvs(self, variables):
#         """Return value vectors for the specified variables."""
#         return [self.extract_fv(e, variables) for e in self.exemplars]
#
#     def extract_fv(self, exemplar, variables):
#         """Return a value vector for the specified variables from this exemplar."""
#         return [exemplar[0][vname] if vname in exemplar[0] else None for vname in variables]
#
#     def extract_values(self, variable):
#         """Return value vector for specified variable across all exemplars."""
#         return [self.extract_value(e, variable) for e in self.exemplars]
#
#     def extract_value(self, exemplar, variable):
#         """Return value for specified variable for this exemplar."""
#         if variable == 'duration': return exemplar[1]
#         elif variable == 'status' : return exemplar[2]
#         elif variable == 'effects' : return exemplar[3]
#         elif variable in exemplar[0]: return exemplar[0][variable]
#         else: return None
#
#     def __str__(self):
#         return "Outcome: {}".format(",".join([str(e) for e in self.effects]))
#
#     def print_exemplars(self):
#         for fv, duration, status, oc, (icdn,icfv) in self.exemplars:
#             print(fv, duration, status, [str(e) for e in oc])

class BoundSchema:
    def __init__(self, schema, bset):
        self.schema = schema
        self.bset = copy.deepcopy(bset)
        self.reward = 0
        self.cost = 0

    def update_value_ratio(self, world, planner):
        agent = world.entities.get(self.schema.agent_eid)
        target = world.entities.get(self.bset['target'])

        self.reward = 0

        for outcome,predictor in zip(self.schema.outcomes,self.schema.outcome_predictors):
            prob = predictor.estimate_from_scenario({'agent': agent, 'target': target}, world)[0][1]
            print("Odds of outcome {}: {}".format(outcome,prob))
            print("Effects", outcome.effects)
            for effect in outcome.effects:
                for gn in planner.all_goal_nodes():
                    print(effect, gn, effect.outcome_value(gn))
                    self.reward += prob * (effect.outcome_value(gn))

        # material cost?

        # time cost
        #cost = dest.estimate([(target.pos - agent.pos).magnitude()])
        self.cost = self.schema.duration_estimator.estimate_from_scenario({'agent': agent, 'target': target}, world)

        print("{} {}".format(self.schema.behavior_class, self.bset['target']))
        print("expected reward: {}".format(self.reward))
        print("expected cost: {}".format(self.cost))

        return self.reward / self.cost

    def instantiate(self):
        return self.schema.behavior_class(self.bset['target'])

########################################################################
# Attributes and relationships
########################################################################

VALUE_CONTINUOUS = 0
VALUE_CATEGORICAL = 1
RELN_BINARY = 2
RELN_TRINARY = 3

# type is its own special case

ENTITY_ATTRS = {'type'         : (VALUE_CATEGORICAL,    lambda world,ent: ent.tid),
                'hp'           : (VALUE_CONTINUOUS,     lambda world,ent: ent.hp),
                }

BEHAVIORAL_ATTRS = {'move_speed'   : (VALUE_CONTINUOUS,     lambda world,ent: data.movement_speed[ent.tid]),
                    'charge_speed' : (VALUE_CONTINUOUS,     lambda world,ent: data.attack_speed[ent.tid]),
                    'awareness'    : (VALUE_CONTINUOUS,     lambda world,ent: data.awareness[ent.tid])
                    }

COMBAT_ATTRS = {'max_hp'       : (VALUE_CONTINUOUS,     lambda world, ent: data.combatants[ent.tid][0]),
                'hp'           : (VALUE_CONTINUOUS,     lambda world,ent: ent.hp),
                'attack_speed' : (VALUE_CONTINUOUS,     lambda world,ent: attack_stats(world, ent)[0] if ent.tid in data.combatants else None),
                'min_dmg'      : (VALUE_CONTINUOUS,     lambda world,ent: attack_stats(world, ent)[1][0] if ent.tid in data.combatants else None),
                'max_dmg'      : (VALUE_CONTINUOUS,     lambda world,ent: attack_stats(world, ent)[1][1] if ent.tid in data.combatants else None),
                'attack_range' : (VALUE_CONTINUOUS,     lambda world,ent: attack_stats(world, ent)[2] if ent.tid in data.combatants else None)
                }

GATHERABLE_ATTRS = {'gather_time'  : (VALUE_CONTINUOUS,     lambda world, ent: data.gatherable[ent.tid][0]),
                    }

# attrs that are the same across a class
# CLASS_ATTRS = {'max_hp'       : (VALUE_CONTINUOUS,     lambda world,ent: data.combatants[ent.tid][0]),
#                'move_speed'   : (VALUE_CONTINUOUS,     lambda world,ent: data.movement_speed[ent.tid]),
#                'charge_speed' : (VALUE_CONTINUOUS,     lambda world,ent: data.attack_speed[ent.tid]),
#                'awareness'    : (VALUE_CONTINUOUS,     lambda world,ent: data.awareness[ent.tid])
#                }

# attrs that can vary by instance
# INSTANCE_ATTRS = {'hp'           : (VALUE_CONTINUOUS,     lambda world,ent: ent.hp),
#                   'attack_speed' : (VALUE_CONTINUOUS,     lambda world,ent: attack_stats(world, ent)[0] if ent.tid in data.combatants else None),
#                   'min_dmg'      : (VALUE_CONTINUOUS,     lambda world,ent: attack_stats(world, ent)[1][0] if ent.tid in data.combatants else None),
#                   'max_dmg'      : (VALUE_CONTINUOUS,     lambda world,ent: attack_stats(world, ent)[1][1] if ent.tid in data.combatants else None),
#                   'attack_range' : (VALUE_CONTINUOUS,     lambda world,ent: attack_stats(world, ent)[2] if ent.tid in data.combatants else None)
#                   }

RELN_VALUES = {'dist'         : (RELN_BINARY, VALUE_CONTINUOUS,  lambda world,ent1,ent2: distance_between(ent1, ent2)),
               'path_dist'    : (RELN_TRINARY, VALUE_CONTINUOUS, lambda world,ent1,ent2,ent3: distance_to_path(ent1, ent2, ent3)),
               }

def get_attr(label):
    if label in ENTITY_ATTRS: return ENTITY_ATTRS[label]
    if label in BEHAVIORAL_ATTRS: return BEHAVIORAL_ATTRS[label]
    if label in COMBAT_ATTRS: return COMBAT_ATTRS[label]
    if label in GATHERABLE_ATTRS: return GATHERABLE_ATTRS[label]
    assert False, "Attribute {} not valid".format(label)

def all_attrs(tid):
    for key,(vtype,fn) in ENTITY_ATTRS.items(): yield key,(vtype,fn)
    if tid in data.movement_speed:
        for key,(vtype,fn) in BEHAVIORAL_ATTRS.items(): yield key,(vtype,fn)
    if tid in data.combatants:
        for key,(vtype,fn) in COMBAT_ATTRS.items(): yield key,(vtype,fn)
    if tid in data.gatherable:
        for key,(vtype,fn) in GATHERABLE_ATTRS.items(): yield key,(vtype,fn)

def is_continuous(var):
    alabel,attr = var.split('.')
    if not alabel.startswith('reln'):
        vtype,fn = get_attr(attr)
    else:
        arity,vtype,fn = RELN_VALUES[attr]
    return vtype == VALUE_CONTINUOUS

def generate_fv(world, labeled_entities, attrs=None, categorical=True):
    """
    Generate feature vector for all labeled entities (dict) and relns (taken in entity order). If attrs are specified,
    use those rather than all.
    """
    d = {}
    for label,ent in labeled_entities.items():
        for key,(vtype, fn) in all_attrs(ent.tid):
            val = fn(world, ent)
            if val is not None:
                d[label + '.' + key] = val

    # and add relations
    if len(labeled_entities.keys()) == 2:
        d.update({'reln-agent-target.{}'.format(key) : fn(world, labeled_entities['agent'], labeled_entities['target'])
                  for key,(arity, vtype, fn) in
                  RELN_VALUES.items() if arity is RELN_BINARY})
    elif len(labeled_entities.keys()) == 3:
        d.update({'reln-agent-target-entity1.{}'.format(key): fn(world, labeled_entities['agent'], labeled_entities['target'], labeled_entities['entity1'])
                  for key,(arity, vtype, fn) in
                  RELN_VALUES.items() if arity is RELN_TRINARY})
        d.update({'reln-agent-target.' + key: fn(world, labeled_entities['agent'], labeled_entities['target'])
                  for key,(arity, vtype, fn) in
                  RELN_VALUES.items() if arity is RELN_BINARY})
        d.update({'reln-agent-entity1.' + key: fn(world, labeled_entities['agent'], labeled_entities['entity1'])
                  for key,(arity, vtype, fn) in
                  RELN_VALUES.items() if arity is RELN_BINARY})
        d.update({'reln-target-entity1.' + key: fn(world, labeled_entities['target'], labeled_entities['entity1'])
                  for key,(arity, vtype, fn) in
                  RELN_VALUES.items() if arity is RELN_BINARY})
    elif len(labeled_entities.keys()) == 4:
        d.update({'reln-agent-target-entity1.{}'.format(key): fn(world, labeled_entities['agent'], labeled_entities['target'], labeled_entities['entity1'])
                  for key,(arity, vtype, fn) in
                  RELN_VALUES.items() if arity is RELN_TRINARY})
        d.update({'reln-agent-target-entity2.{}'.format(key): fn(world, labeled_entities['agent'], labeled_entities['target'], labeled_entities['entity2'])
                  for key,(arity, vtype, fn) in
                  RELN_VALUES.items() if arity is RELN_TRINARY})
        d.update({'reln-agent-target.' + key: fn(world, labeled_entities['agent'], labeled_entities['target'])
                  for key,(arity, vtype, fn) in
                  RELN_VALUES.items() if arity is RELN_BINARY})
        d.update({'reln-agent-entity1.' + key: fn(world, labeled_entities['agent'], labeled_entities['entity1'])
                  for key,(arity, vtype, fn) in
                  RELN_VALUES.items() if arity is RELN_BINARY})
        d.update({'reln-target-entity1.' + key: fn(world, labeled_entities['target'], labeled_entities['entity1'])
                  for key,(arity, vtype, fn) in
                  RELN_VALUES.items() if arity is RELN_BINARY})
        d.update({'reln-agent-entity2.' + key: fn(world, labeled_entities['agent'], labeled_entities['entity2'])
                  for key,(arity, vtype, fn) in
                  RELN_VALUES.items() if arity is RELN_BINARY})
        d.update({'reln-target-entity2.' + key: fn(world, labeled_entities['target'], labeled_entities['entity2'])
                  for key,(arity, vtype, fn) in
                  RELN_VALUES.items() if arity is RELN_BINARY})
        d.update({'reln-entity1-entity2.' + key: fn(world, labeled_entities['entity1'], labeled_entities['entity2'])
                  for key,(arity, vtype, fn) in
                  RELN_VALUES.items() if arity is RELN_BINARY})
    elif len(labeled_entities.keys()) == 5:
        d.update({'reln-agent-target-entity1.{}'.format(key): fn(world, labeled_entities['agent'], labeled_entities['target'], labeled_entities['entity1'])
                  for key,(arity, vtype, fn) in
                  RELN_VALUES.items() if arity is RELN_TRINARY})
        d.update({'reln-agent-target-entity2.{}'.format(key): fn(world, labeled_entities['agent'], labeled_entities['target'], labeled_entities['entity2'])
                  for key,(arity, vtype, fn) in
                  RELN_VALUES.items() if arity is RELN_TRINARY})
        d.update({'reln-agent-target-entity3.{}'.format(key): fn(world, labeled_entities['agent'], labeled_entities['target'], labeled_entities['entity3'])
                  for key,(arity, vtype, fn) in
                  RELN_VALUES.items() if arity is RELN_TRINARY})
        d.update({'reln-agent-target.' + key: fn(world, labeled_entities['agent'], labeled_entities['target'])
                  for key,(arity, vtype, fn) in
                  RELN_VALUES.items() if arity is RELN_BINARY})
        d.update({'reln-agent-entity1.' + key: fn(world, labeled_entities['agent'], labeled_entities['entity1'])
                  for key,(arity, vtype, fn) in
                  RELN_VALUES.items() if arity is RELN_BINARY})
        d.update({'reln-target-entity1.' + key: fn(world, labeled_entities['target'], labeled_entities['entity1'])
                  for key,(arity, vtype, fn) in
                  RELN_VALUES.items() if arity is RELN_BINARY})
        d.update({'reln-agent-entity2.' + key: fn(world, labeled_entities['agent'], labeled_entities['entity2'])
                  for key,(arity, vtype, fn) in
                  RELN_VALUES.items() if arity is RELN_BINARY})
        d.update({'reln-target-entity2.' + key: fn(world, labeled_entities['target'], labeled_entities['entity2'])
                  for key,(arity, vtype, fn) in
                  RELN_VALUES.items() if arity is RELN_BINARY})
        d.update({'reln-entity1-entity2.' + key: fn(world, labeled_entities['entity1'], labeled_entities['entity2'])
                  for key,(arity, vtype, fn) in
                  RELN_VALUES.items() if arity is RELN_BINARY})
        d.update({'reln-agent-entity3.' + key: fn(world, labeled_entities['agent'], labeled_entities['entity3'])
                  for key,(arity, vtype, fn) in
                  RELN_VALUES.items() if arity is RELN_BINARY})
        d.update({'reln-target-entity3.' + key: fn(world, labeled_entities['target'], labeled_entities['entity3'])
                  for key,(arity, vtype, fn) in
                  RELN_VALUES.items() if arity is RELN_BINARY})
        d.update({'reln-entity1-entity3.' + key: fn(world, labeled_entities['entity1'], labeled_entities['entity3'])
                  for key,(arity, vtype, fn) in
                  RELN_VALUES.items() if arity is RELN_BINARY})
        d.update({'reln-entity2-entity3.' + key: fn(world, labeled_entities['entity2'], labeled_entities['entity3'])
                  for key,(arity, vtype, fn) in
                  RELN_VALUES.items() if arity is RELN_BINARY})

    if attrs is not None:
        d = {k:v for k,v in d.items() if k in attrs}

    return d

#########################################
# Attribute helpers
#########################################

def attack_stats(world, ent):
    """Return the attack stats for ent at the specified point in world."""
    assert ent.tid in data.combatants, "Request for attack stats for non-combatant entity."
    if ent.tid == data.AGENT_TYPE_ID:
        inv = world.inventories.get(ent.eid)
        if inv is not None:
            wid = inv.max_dps_weapon(ent.eid, world)
            if wid is not None:
                return data.weapons[wid]
    return data.combatants[ent.tid][1:]

def distance_to_path(from_ent, to_ent, target_ent):
    l1 = from_ent.pos
    l2 = to_ent.pos
    p = target_ent.pos
    if not within_ray(l1, l2, p):
        # on the outside of l1
        return (p-l1).magnitude()
    if not within_ray(l2, l1, p):
        # on the outside of l2
        return (p - l2).magnitude()
    # within the segment
    return distance_to_line(l1, l2, p)

def distance_between(a, b):
    return (a.pos - b.pos).magnitude()

def distance_to_line(l0, l1, p):
    """Returns distance from p to the line passing through l1,l2."""
    return math.fabs((l1.y-l0.y)*p.x - (l1.x-l0.x)*p.y + l1.x*l0.y - l1.y*l0.x) / (l1-l0).magnitude()

def within_ray(l0, l1, p):
    """True if p's min distance to the ray l0->l1 is within the ray extent."""
    to_end = (l1 - l0).normalized()
    to_point = p - l0
    if to_end.dot(to_point) < 0: return False
    return True

########################################################################
# Behavior outcome models
########################################################################

class StateDelta_Obtain:
    @staticmethod
    def generate(dn, trace):
        """Return Obtain deltas for the diff between dn0 and dn1."""
        inv0 = trace.state(dn.start_clock).inventories.get(dn.agent_eid)
        inv1 = trace.state(dn.end_clock).inventories.get(dn.agent_eid)
        # G is a list of (item id, count)
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
    def generate(dn, trace):
        """Return Died deltas for the diff between dn0 and dn1."""
        #print("diff {}, {}".format(dn0, dn1))
        end_state = trace.state(dn.end_clock)
        for eid,ent in trace.state(dn.start_clock).entities.all():
            #print("entity {}...".format(eid))
            if ent.tid in data.awareness:
                if end_state.entities.get(eid) is None:
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

OUTCOME_MODELS = [StateDelta_Obtain,
                  StateDelta_Died,
                  ]

def generate_effects(dn, trace):
    O = []
    for m in OUTCOME_MODELS:
        for outcome in m.generate(dn, trace):
            O.append(outcome)
    return O

########################################################################
# Utility
########################################################################

def powerset(names, lists):
    if len(lists) == 1:
        # last list
        for e in lists[0]:
            yield {names[0]: e}

    else:
        for e in lists[0]:
            rest_bsets = powerset(names[1:], lists[1:])
            for bset in rest_bsets:
                bset[names[0]] = e
                yield bset

def effects_subsume(e1, e2):
    """Return true if all effects in e2 and also in e1."""
    return all((any((e.like(comp) for comp in e1)) for e in e2))

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

if __name__ == '__main__':
    for ps in powerset(('A', 'B', 'C'),
                       ((0, 1, 2),
                        (3, 4),
                        (5, 6, 7))):
        print(ps)
