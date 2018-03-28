import os, pickle
import numpy as np
from exp01.evaluation import Schema, SchemaLib, generate_fv, generate_effects
from exp01.estimation import LinearEstimator, RandomForestEstimator
from constants import *

DEBUG = True

DATA_DIR = os.path.join("traces_03_withrocks")
MODEL_DIR = os.path.join("models")
SCHEMA_LIB_FILE = 'schema_lib_2_gather_trees.pkl'

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

    # assign all exemplars to the correct schema
    for trace in traces:
        #print("-----")
        #print(trace)
        for i,dn in enumerate(trace.decisions):
            # ignore non-behavior events
            if dn.behavior_name() in ['done', 'looping', 'killed', 'dehydrated']:
                continue

            # create models if necessary
            if dn.behavior_name() not in S:
                s = Schema(dn.behavior_name())
                S[dn.behavior_name()] = s
            else:
                s = S[dn.behavior_name()]

            # then add exemplar
            s.add_exemplar(generate_fv(dn.decision_state, {'agent': dn.entity('agent'), 'target': dn.entity('target')}),
                           dn.duration(),
                           dn.status,
                           generate_effects(dn, trace.decisions[i + 1]),
                           )

    # for each schema, process the examplars
    SchemaLib.lib = SchemaLib()
    for s in S.values():

        # segment outcomes
        s.segment_outcomes()
        if DEBUG: s.print()

        # regress duration
        s.duration_estimator = LinearEstimator()
        A = s.extract_all_fvs()
        durations = s.extract_all_values('duration')
        s.duration_estimator.train(s.variables, A, durations)
        print("Variables: {}".format(s.duration_estimator.variables))
        print("Weights: {}".format(s.duration_estimator.weights))
        print("Residual: {}".format(s.duration_estimator.residuals))

        # learn outcome prediction
        s.outcome_predictor = RandomForestEstimator()
        A = []
        outcome_classes = []
        for i,o in enumerate(s.outcomes):
            fvs = o.extract_fvs(s.variables)
            A.extend(fvs)
            outcome_classes.extend([i]*len(fvs))

        s.outcome_predictor.train(s.variables, A, outcome_classes)

        # test
        vars = s.outcome_predictor.variables
        print(vars)
        pos = 0
        neg = 0
        for i,o in enumerate(s.outcomes):
            for e in o.exemplars:
                cls = s.outcome_predictor.estimate([e[0][vname] for vname in vars])
                if cls[0][i] == max(cls[0]):
                    pos += 1
                else:
                    neg += 1
        print("Testing: pos {}, neg {} ({}%)".format(pos, neg, (pos/(pos+neg))))

        # for outcome,exemplars in outcome_sets:
        #
        #     # create matrix of per-attribute value vectors
        #     for fv, duration, status, oc in exemplars:
        #         for i,key in enumerate(labels):
        #             A[i].append(fv[key])
        #
        #     # create training values for duration
        #     y.extend([exemplar[1] for exemplar in exemplars])
        #
        #     # add outcome to schema
        #     s.add_outcome(outcome, exemplars, None)
        #
        #     # create range/threshhold constraints in outcomes
        #     # that is, for this outcome, what is the range/set of X values?
        #
        #     # train outcome numeric estimators
        #     # for numerics in outcomes, train outcome-specific estimators (lr)


        # outcome probabilities
        # 1) global prob of each outcome
        # 2) count prob of each variable value (bin) given each outcome (n.b.)
        # 3) look for constraints (val or range) that 100% predict one outcome, and 0% any other

        #s.outcome_estimator = sklearn



        # look for segmenting constraints across outcomes



        # (just take probability counts per constraint? look for non-overlapping?)

        # n.b. w/ binning for outcome predictions (more complex when drops aren't guaranteed)

        # train duration estimator


        SchemaLib.get(MODEL_DIR, SCHEMA_LIB_FILE).schema.append(s)

    # save model to disk
    SchemaLib.save(MODEL_DIR, SCHEMA_LIB_FILE)




if __name__ == '__main__':
    TR = load_traces(DATA_DIR)
    #for tr in TR: print(tr)
    create_schema(TR)
