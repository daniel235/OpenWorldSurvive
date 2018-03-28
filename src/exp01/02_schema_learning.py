import os, pickle
import numpy as np
from exp01.evaluation import Schema, SchemaLib, generate_fv, generate_effects
from exp01.estimation import LinearEstimator
from constants import *

DEBUG = True

DATA_DIR = os.path.join("traces")
MODEL_DIR = os.path.join("models")
SCHEMA_LIB_FILE = 'schema_lib_1_gather_close.pkl'

def load_traces(dir, limit=None):
    """Read in game traces, return as a list."""
    games = []
    for i, fn in enumerate(os.listdir(dir)):
        if limit is not None and i == limit: break

        f = open(os.path.join(dir, fn), 'rb')
        seed, trace = pickle.load(f)
        f.close()

        #if trace.decisions[-1].is_behavior('looping'):
        #    # print("dropping {}".format(trace.decisions[-1]))
        #    continue
        games.append(trace)

    return games

def create_schema(traces):
    # dictionary for schemas-in-progress
    S = {}
    # for each decision node behavior...
    for trace in traces:
        for i,dn in enumerate(trace.decisions):
            # ignore non-behavior events
            if dn.behavior_name() in ['done', 'looping', 'killed']:
                continue

            # create models if necessary
            if dn.behavior_name() not in S:
                s = Schema(dn.behavior_name())
                S[dn.behavior_name()] = s
            else:
                s = S[dn.behavior_name()]

            # then add exemplar
            s.add_exemplar(generate_fv(dn.decision_state, {'agent': dn.entity('agent'), 'target': dn.entity('target')}),
                           dn.end_clock - dn.decision_state.clock,
                           dn.status,
                           generate_effects(dn, trace.decisions[i + 1]),
                           )

    # process the examplars for each models and add to new lib
    SchemaLib.lib = SchemaLib()
    for s in S.values():

        # segment outcomes
        outcome_sets = segment_outcomes(s.exemplars)
        for label,exemplars in outcome_sets:
            print([str(e) for e in label])
            for fv, duration, status, oc in exemplars:
                print(fv, duration, status, [str(e) for e in oc])

        for outcome,exemplars in outcome_sets:
            # regress time
            le = LinearEstimator()

            labels = [key for key in exemplars[0][0]]
            A = [[] for key in labels]

            for fv, duration, status, oc in exemplars:
                for i,key in enumerate(labels):
                    A[i].append(fv[key])

            y = [exemplar[1] for exemplar in exemplars]

            le.train(labels, np.array(A), y)
            print("Labels: {}".format(le.labels))
            print("Weights: {}".format(le.weights))
            print("Residual: {}".format(le.residuals))

            s.add_outcome(outcome, exemplars, le)

        SchemaLib.get(MODEL_DIR, SCHEMA_LIB_FILE).schema.append(s)

    # save model to disk
    SchemaLib.save(MODEL_DIR, SCHEMA_LIB_FILE)

def segment_outcomes(exemplars):
    # build list of unique outcomes
    outcomes = []

    for exemplar in exemplars:
        if exemplar[2] == INTERRUPT: continue
        its = lhs = rhs = None
        done = False
        for i,outcome_group in enumerate(outcomes):
            its,lhs,rhs = outcome_intersection(exemplar[3], outcome_group[0])
            print([str(e) for e in its])
            if len(its) > 0:
                if len(its) == len(exemplar[3]) == len(outcome_group[0]):
                    # same set of outcomes, move to next exemplar
                    outcome_group[1].append(exemplar)
                    its = None
                    done = True
                    break
                else:
                    # different set of outcomes, segment this group
                    break
        if not done:
            if its is not None:
                splits = split_outcomes(outcomes[i], exemplar, its, lhs, rhs)
                outcomes[i] = splits[0]
                outcomes.extend(splits[1:])
            else:
                # got here, no group matched, so new group
                outcomes.append([exemplar[3], [exemplar]])

    return outcomes

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

    return its,lhs_extra,rhs_extra

def split_outcomes(ogroup, exemplar, its, lhs, rhs):
    """
    The outcome group and the exemplar have an overlapping intersection. This splits into three groups: the intersection,
    the extras in the group and the extras in the exemplar.
    """
    its,lhs_extra,rhs_extra = outcome_intersection(ogroup[0], exemplar[5])

    exemplars_copy = list(ogroup[1])

    # existing group reduce outcomes and add new exemplar
    splits = [ogroup]
    ogroup[0] = its
    ogroup[1].append(exemplar)

    # leftovers from the existing group get all the existing exemplars
    if len(lhs_extra) > 0:
        splits.append([lhs_extra, exemplars_copy])

    # leftovers from new exemplar just get that one
    if len(rhs_extra) > 0:
        splits.append([rhs_extra, [exemplar]])

    return splits


if __name__ == '__main__':
    TR = load_traces(DATA_DIR)
    #for tr in TR: print(tr)
    create_schema(TR)
