import os, pickle, re
import numpy as np
from exp01.evaluation import Schema, SchemaLib, generate_fv, generate_effects
from exp01.estimation import LinearEstimator, RandomForestEstimator, RandomForestRegressionEstimator, GBClassifierEstimator, ABClassifierEstimator
from exp01.trace_processing import load_traces, convert_traces, interaction_responses
from constants import *

DEBUG = True

DATA_DIR = os.path.join("traces_05_withmobs")
MODEL_DIR = os.path.join("models")
SCHEMA_LIB_FILE = 'schema_lib_3_gather_mobs.pkl'

LIMIT = 1000

def create_schema(htraces):
    # dictionary for schemas-in-progress
    S = {}

    # assign all exemplars to the correct schema
    for interactions,trace in htraces:
        print(trace)
        for intr in interactions:
            print("----- Interaction: {}".format(", ".join([str(dn) for dn in intr])))
            for i,dn in enumerate(intr):
                # ignore non-behavior events
                if dn.behavior_name() in ['done', 'looping', 'killed', 'dehydrated', 'disengaged', 'patrol', 'flee', 'craft', 'leashing']:
                    continue

                # create models if necessary
                if dn.behavior_name() not in S:
                    s = Schema(dn.behavior_name())
                    S[dn.behavior_name()] = s
                else:
                    s = S[dn.behavior_name()]

                # then add exemplar
                # labeled_entities = {}
                # if not dn.is_event(): labeled_entities['agent'] = dn.entity('agent', trace)
                # if dn.behavior_target_id() is not None: labeled_entities['target'] = dn.entity('target', trace)

                # print("adding exempar from {} to {}".format(dn.start_clock, dn.end_clock))
                # icdn = interaction_context(intr, i)
                # icfv = None
                # if icdn is not None:
                #     # ic must have an agent (since that's the dn target), may have a target
                #     ic_entities = {'agent' : labeled_entities['target']}
                #     if icdn.behavior_target_id() is not None: ic_entities['target'] = icdn.entity('target', trace)
                #     # agent of dn is extra binding to predict dn in that context
                #     if not dn.is_event(): ic_entities['third'] = labeled_entities['agent']
                #     icfv = generate_fv(trace.state(icdn.start_clock), ic_entities)
                #     print("ICFV!!! {}".format(icfv))

                s.add_exemplar(dn, trace, interaction_responses(intr, i))

                print("Exemplar added to schema:")
                s.print()

    # for each schema, process the examplars
    SchemaLib.lib = SchemaLib()
    for s in S.values():
        print(s)

        # compute all outcome effect sets
        s.update_exemplar_outcomes()

        # train duration estimator
        print("Training duration estimator")
        V, X, y = s.training_data_for_value('duration')
        rf = RandomForestRegressionEstimator()
        s.erf = rf.validate(V, X, y)
        lr = LinearEstimator()
        s.elr = lr.validate(V, X, y)
        if s.erf < s.elr:
            s.duration_estimator = rf
        else:
            s.duration_estimator = lr
        s.duration_estimator.train(V, X, y)
        print("Variables: {}".format(s.duration_estimator.variables))
        #print("Weights: {}".format(s.duration_estimator.weights))
        #print("Residual: {}".format(s.duration_estimator.residuals))

        s.outcome_validations = []
        for i in range(len(s.outcomes)):
            print("Training outcome {}: {}".format(i, s.outcomes[i]))
            #s.outcome_predictors.append(RandomForestEstimator())
            s.outcome_predictors.append(ABClassifierEstimator())
            V,X,y = s.training_data_for_outcome(i)
            f1 = s.outcome_predictors[i].validate(V, X, y)
            s.outcome_validations.append(f1)
            s.outcome_predictors[i].train(V, X, y)
            print(s.outcome_predictors[i].variables)
            print(s.outcome_predictors[i].clf.feature_importances_)

        for i,r in enumerate(s.response_behaviors):
            m = re.search('\(([a-z]*)', r)
            bname = m.group(1)
            s.response_predictors.append(RandomForestEstimator())
            V, X, y = s.training_data_for_response(bname)
            print("Training Response - {}, {} vars, {} exemplars".format(bname, len(V), len(X)))
            s.response_predictors[i].validate(V, X, y)
            #s.response_predictors[i].train(V, X, y)
            print(s.response_predictors[i].variables)
            if s.response_predictors[i].clf is not None:
                print(s.response_predictors[i].clf.feature_importances_)

            # pos = 0
            # neg = 0
            # for i,o in enumerate(s.outcomes):
            #     for e in o.exemplars:
            #         cls = s.outcome_predictor.estimate([e[0][vname] for vname in vars])
            #         if cls[0][i] == max(cls[0]):
            #             pos += 1
            #         else:
            #             neg += 1
            # print("Testing: pos {}, neg {} ({}%)".format(pos, neg, (pos/(pos+neg))))

        # for r in s.response_behaviors:
        #     m = re.search('\(([a-z]*)', r)
        #     bname = m.group(1)
        #     print("Response - ", bname)
        #     V,X,y = s.training_data_for_response(bname)
        #     print(V)
        #     for fv in X: print(fv)
        #     print(y)

        # # segment outcomes
        # s.segment_outcomes()
        # if DEBUG: s.print()
        #
        # # regress duration
        # s.duration_estimator = LinearEstimator()
        # A = s.extract_all_fvs()
        # durations = s.extract_all_values('duration')
        # s.duration_estimator.train(s.variables, A, durations)
        # print("Variables: {}".format(s.duration_estimator.variables))
        # print("Weights: {}".format(s.duration_estimator.weights))
        # print("Residual: {}".format(s.duration_estimator.residuals))
        #
        # # learn outcome prediction
        # s.outcome_predictor = RandomForestEstimator()
        # A = []
        # outcome_classes = []
        # for i,o in enumerate(s.outcomes):
        #     fvs = o.extract_fvs(s.variables)
        #     A.extend(fvs)
        #     outcome_classes.extend([i]*len(fvs))
        #
        # print("Training outcome predictor")
        # for a in A: print(a)
        # print(outcome_classes)
        #
        # s.outcome_predictor.train(s.variables, A, outcome_classes)
        #
        # # test
        # vars = s.outcome_predictor.variables
        # print(vars)
        # pos = 0
        # neg = 0
        # for i,o in enumerate(s.outcomes):
        #     for e in o.exemplars:
        #         cls = s.outcome_predictor.estimate([e[0][vname] for vname in vars])
        #         if cls[0][i] == max(cls[0]):
        #             pos += 1
        #         else:
        #             neg += 1
        # print("Testing: pos {}, neg {} ({}%)".format(pos, neg, (pos/(pos+neg))))

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
    TR = load_traces(DATA_DIR, limit=LIMIT)
    #for tr in TR: print(tr)

    HTR = convert_traces(TR)

    create_schema(zip(HTR,TR))

    for s in SchemaLib.get().schema:
        print(s, "duration_error RF {}, LR {}".format(s.erf, s.elr))
        print(s, "outcome f1:", ", ".join((str(f1) for f1 in s.outcome_validations)))
