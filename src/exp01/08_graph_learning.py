import os, copy
import data
from exp01.trace_processing import load_traces
from exp01.igraph import *
from exp01.igraph_trainer import *
from exp01.estimation import ABClassifierEstimator, RandomForestRegressionEstimator, LinearEstimator

DATA_DIR = os.path.join("traces_05_withmobs")
MODEL_DIR = os.path.join("models")

LIMIT = 500

MODEL_FILE = 'igraph-{}.pkl'.format(LIMIT)

DEBUG=True

# global control variables

def create_igraph(traces):
    graph = IGraphTrain()

    for trace in traces:
        #if DEBUG: print("IGraph Update -------------------")
        #if DEBUG: print(trace)

        for agent_eid in trace.agent_eids():
            exemplar_seq = create_igraph_exemplars(trace, agent_eid)

            # drop short ones?
            #exemplar_seq = [enode for enode in exemplar_seq if (enode.end_clock - enode.start_clock) >= 0.02]
            exemplar_seq = [enode for enode in exemplar_seq if enode.agent_dn is None or enode.agent_dn.behavior_name != 'killed']

            #if DEBUG: print("-- Exemplars ----------")
            #if DEBUG:
            #    for e in exemplar_seq: print(e)

            graph.add_exemplar(exemplar_seq, trace)

    #if DEBUG: graph.print_graph(print_exemplars=True)

    # training
    graph.update_exemplar_outcomes()

    for node in graph.nodes.values():
        print("Node:", node.key)
        if len(node.success) != 0:
            # this node has success conditions
            print(" {} SUCCESS exemplars, outcomes: {}".format(len(node.success), ', '.join((str(o) for o in node.success_outcomes))))
            print(" {} SUCCESS ratio".format(len(node.success) / node.exemplar_count))
            # train outcome probs, duration across agent behavior entities
            if len(node.success) >= 10:
                V, X, y = node.training_data_for_value('duration')
                node.success_duration_estimator = []
                for est in (RandomForestRegressionEstimator(), LinearEstimator()):
                    est.train(V,X,y)
                    node.success_duration_estimator.append((est, est.validate(V,X,y)))
                for i in range(len(node.success_outcomes)):
                    o = node.success_outcomes[i]
                    est = ABClassifierEstimator()
                    V,X,y = node.training_data_for_outcome(i)
                    if y.count(1) >= 10:
                        est.train(V,X,y)
                        o.probability_predictor = (est, est.validate(V, X, y))

                print("    duration validations:", ', '.join((str(v) for e,v in node.success_duration_estimator)))
                print("    outcome validations:", ', '.join((o.probability_predictor is not None and str(o.probability_predictor[1]) or '-' for o in node.success_outcomes)))

        if len(node.death) != 0:
            print(" {} DEATH ratio".format(len(node.death) / node.exemplar_count))
            # train death prob across all entities
            if len(node.death) >= 10 and len(node.success) >= 10:
                V,X,y = node.training_data_for_death()
                est = ABClassifierEstimator()
                est.train(V,X,y)
                node.death_estimator = (est, est.validate(V, X, y))

        for key,E in node.transitions.items():
            print(" {} TRANS exemplars: {}".format(len(E), key))
            if len(E) >= 10:
                ex,V,X,y = node.training_data_for_transition(key)
                est = ABClassifierEstimator()
                if y.count(1) >= 10 and y.count(0) >= 10:
                    est.train(V, X, y)
                    node.transition_predictors[key] = (est, est.validate(V,X,y), ex)

        for key,(e,v,ex) in node.transition_predictors.items():
            print("    transition validation:", key, v, ex)

    # node = graph.nodes['(gather agent target)']
    # for key,E in node.transitions.items():
    #     print(" {} TRANS exemplars: {}".format(len(E), key))
    #     ex,V,X,y = node.training_data_for_transition(key)
    #     print(V)
    #     for x in X: print(x)
    #     print(y)


    #     print("Training", node.key)
    #
    #     # train duration estimator
    #     print("Training duration estimator")
    #     if len(node.success) > 0:
    #         V, X, y = node.training_data_for_value('duration')
    #         print(V)
    #         for x in X: print(x)
    #         print(y)
    #         rf = RandomForestRegressionEstimator()
    #         node.erf = rf.validate(V, X, y)
    #         lr = LinearEstimator()
    #         node.elr = lr.validate(V, X, y)
    #         if node.erf < node.elr:
    #             node.success_duration_estimator = rf
    #         else:
    #             node.success_duration_estimator = lr
    #         node.success_duration_estimator.train(V, X, y)
    #         print("Variables: {}".format(node.success_duration_estimator.variables))
    #         # print("Weights: {}".format(s.duration_estimator.weights))
    #         # print("Residual: {}".format(s.duration_estimator.residuals))
    #
    #     node.outcome_validations = []
    #     for i in range(len(node.success_outcomes)):
    #         o = node.success_outcomes[i]
    #         print("Training outcome {}: {}".format(i, o))
    #         # s.outcome_predictors.append(RandomForestEstimator())
    #         o.probability_predictor = ABClassifierEstimator()
    #         V, X, y = node.training_data_for_outcome(i)
    #         node.outcome_validations.append(o.probability_predictor.validate(V, X, y))
    #         o.probability_predictor.train(V, X, y)
    #         print(o.probability_predictor.variables)
    #         print(o.probability_predictor.clf.feature_importances_)
    #
    # print("Training Results")
    # for node in graph.nodes.values():
    #     if len(node.success) > 0:
    #         print("Node:", node.key)
    #         print("Duration validation: {} {}".format(node.erf, node.elr))
    #         print("Outcome validation:", ', '.join((str(v) for v in node.outcome_validations)))

    graph.save_igraph(MODEL_DIR, MODEL_FILE)

############################################
# Exemplar Extraction
############################################

def create_igraph_exemplars(trace, agent_eid):
    # first, create sequence of agent behavior nodes
    # REM: insert idles?
    agent_seq = [IGraphExemplarNode(dn=dn) for dn in trace.decisions if dn.arg_value('agent') == agent_eid]

    # use each other behavior to segment
    for dn in trace.decisions:
        if not dn.is_event() and dn.arg_value('agent') != agent_eid:
            agent_seq = update_graph_nodes(agent_seq, dn)

    # append ending state
    agent_seq.append(IGraphExemplarNode(manual_key=trace.decisions[-1].behavior_name, manual_clock=trace.decisions[-1].start_clock))

    return agent_seq

def update_graph_nodes(agent_seq, dn):
    """Split the graph nodes in agent_seq as appropriate to include dn."""
    new_seq = []
    for ign in agent_seq:
        new_seq.extend(split(ign, dn))

    return new_seq

def split(ign, dn):
    """Split this node as appropriate to include dn, which is not the same agent or null agent."""

    if not overlap_entity(ign, dn) or not overlap_temporal(ign, dn):
        # need both, nothing to do here
        return (ign,)

    splits = []

    # some overlap, so deal with before, middle and after possibilities
    if ign.start_clock < dn.start_clock:
        # state before
        before = copy.deepcopy(ign)
        before.end_clock = dn.start_clock
        splits.append(before)

    after = None
    if ign.end_clock > dn.end_clock:
        # state after
        after = copy.deepcopy(ign)
        after.start_clock = dn.end_clock

    # and the overlapping part
    ign.add_overlap(dn)
    splits.append(ign)

    if after is not None: splits.append(after)
    return splits

def overlap_temporal(ign, dn):
    """True if the two dns intervals overlap."""
    return between(dn.start_clock, ign.start_clock, ign.end_clock) or \
           between(ign.start_clock, dn.start_clock, dn.end_clock)

def overlap_entity(ign, dn):
    return any((eid in dn.labeled_entity_ids().values() for eid in ign.agent_dn.labeled_entity_ids().values()))

def between(v, x0, x1):
    return v >= x0 and v < x1




if __name__ == '__main__':
    TR = load_traces(DATA_DIR, limit=LIMIT)
    create_igraph(TR)

