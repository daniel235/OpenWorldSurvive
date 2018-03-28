import os, pickle
import data


DATA_DIR = os.path.join("traces_05_withmobs")
MODEL_DIR = os.path.join("models")
SCHEMA_LIB_FILE = 'schema_lib_3_gather_mobs.pkl'

##############################################################
# Load traces from disk
##############################################################

def load_traces(dir, limit=None):
    """Read in game traces, return as a list."""
    games = []
    for i, fn in enumerate(os.listdir(dir)):
        if limit is not None and i == limit: break

        f = open(os.path.join(dir, fn), 'rb')
        seed, trace = pickle.load(f)
        f.close()
        games.append(trace)

    return games

##############################################################
# Create hierarchical interactions in traces
##############################################################

def convert_traces(traces):
    return [convert_to_interactions(trace) for trace in traces]

def convert_to_interactions(trace):
    used = set()
    return [create_interaction(trace, i, used) for i in range(len(trace.decisions)) if i not in used]

def create_interaction(trace, offset, used):
    start = trace.decisions[offset]

    # construct the complete set of behaviors in this interaction, in order
    interaction = [start]

    agent = start.agent(trace)
    if agent is None:
        # non-behavioral event, done here
        return interaction

    # keep track of what each agent in the interaction is doing
    doing = {agent.eid : start}

    # consider each next (unused) behavior for inclusion
    for i in range(offset+1,len(trace.decisions)):
        if i in used: continue
        dn = trace.decisions[i]

        # time moves on, retire active behaviors that have ended at the start of this behavior
        retire = set()
        for eid,active in doing.items():
            if active.end_clock < dn.start_clock:
                # == or > are still active (to support meets)
                # otherwise, this agent isn't in the interaction anymore (off doing something that didn't replace)
                retire.add(eid)
        for eid in retire: del doing[eid]

        # now consider this one
        next_agent = dn.agent(trace)
        if next_agent is None:
            # non-behavioral event, done here
            continue
        next_target = dn.behavior_target(trace)

        if current_involvement(doing, next_agent.eid):
            # agent already in interaction
            if next_target is not None and current_involvement(doing, next_target.eid):
                # target also in, extend the interaction
                doing[next_agent.eid] = dn
                interaction.append(dn)
                used.add(i)

            # since target is new, agent must continue to be involved to extend
            elif continued_involvement(doing, next_agent.eid, dn.start_clock):
                doing[next_agent.eid] = dn
                interaction.append(dn)
                used.add(i)

            else:
                # agent off to something else, no longer in this interaction
                if next_agent.eid in doing:
                    del doing[next_agent.eid]

        else:
            # agent not in interaction, if target is continuing then extend
            if next_target is not None and continued_involvement(doing, next_target.eid, dn.start_clock):
                doing[next_agent.eid] = dn
                interaction.append(dn)
                used.add(i)

            # otherwise nothing to do

        if len(doing.keys()) == 0:
            #print("Interaction ended at {}".format(dn.decision_state.clock))
            break

    return interaction

def active_target_of(doing, eid):
    """Returns all the dn behaviors in doing where eid is the target."""
    if eid is None: return
    for dn in doing.values():
        tgt_eid = dn.behavior_target_id()
        if tgt_eid == eid:
            yield dn

def current_involvement(doing, eid):
    """True if acting or targeted in current doing set."""
    if eid in doing: return True
    for dn in active_target_of(doing, eid):
        return True
    return False

def continued_involvement(doing, eid, clock, step=0.01):
    """True if acting or targeted beyond the next frame."""
    if eid in doing:
        if doing[eid].end_clock > (clock+step): return True
    for dn in active_target_of(doing, eid):
        if dn.end_clock > (clock+step): return True
    return False

##############################################################
# Working with htrace (should probably convert to class)
##############################################################

def interaction_context(interaction, i):
    """Return the dn representing what the target of decision[i] was doing at the time."""
    if i == 0: return None

    tgt_eid = interaction[i].behavior_target_id()
    if tgt_eid is None: return None

    for j in range(i-1,-1,-1):
        print("interaction: {} {}".format(interaction[j].agent_eid, tgt_eid))
        if interaction[j].agent_eid == tgt_eid:
            return interaction[j]

    return None

def interaction_responses(interaction, i):
    """Return the dns that act on the agent of i during that behavior."""

    agent_eid = interaction[i].agent_eid

    # no agent, no response (REM: that's not right, but is given how we're creating interactions right now)
    if agent_eid is None: return []

    end = interaction[i].end_clock

    for j in range(i+1, len(interaction)):
        next = interaction[j]
        if next.start_clock <= end and next.behavior_target_id() == agent_eid:
            yield (interaction[j])





##############################################################
# Markov event chain
##############################################################

class EntityMapping:
    def __init__(self):
        self.counts = {'A':0,'C':0,'G':0}
        self.lookup = {}

    def token(self, ent):
        """Lookup or add generic token for entity."""
        if ent.eid in self.lookup: return self.lookup[ent.eid]

        if ent.tid == data.AGENT_TYPE_ID: prefix = 'A'
        elif ent.tid in data.combatants: prefix = 'C'
        elif ent.tid in data.gatherable: prefix = 'G'

        ct = self.counts[prefix]
        self.counts[prefix] += 1
        tok = "{}{}".format(prefix, ct)
        self.lookup[ent.eid] = tok
        return tok

class EntityMapping2:
    def __init__(self):
        self.lookup = {}

    def token(self, ent):
        """Lookup or add generic token for entity."""
        if ent.eid in self.lookup: return self.lookup[ent.eid]

        if ent.tid == data.AGENT_TYPE_ID: prefix = 'A'
        elif ent.tid in data.combatants: prefix = 'C'
        elif ent.tid in data.gatherable: prefix = 'G'

        self.lookup[ent.eid] = prefix
        return prefix

class MarkovChain:
    def __init__(self, htraces, mapper=EntityMapping2):
        self.nodes = {'Start' : MCNode()}
        self.reverse_edges = {}

        for htrace in htraces:
            # treat each agent as a separate run
            agents = self.extract_agents(htrace)
            for agent_eid in agents:
                entity_mapping = mapper()
                current_tag = 'Start'
                current_grp = None
                for grp in htrace:
                    # only things relevant to this agent!
                    head_dn = grp[0]
                    tgt = head_dn.behavior_target()
                    if head_dn.agent_eid == agent_eid or (tgt is not None and tgt.eid == agent_eid):
                        current_tag = self.add_transition(current_tag, grp, current_grp, entity_mapping)
                        current_grp = grp
                self.add_transition(current_tag, None, current_grp, entity_mapping)

    def add_transition(self, current_tag, to_grp, from_grp, entity_mapping):
        """Each node is a dict of tag : [transition_ct,case list]."""

        # add destination node if necessary
        if to_grp == None:
            to_tag = 'End'
        else:
            to_tag = self.make_tag(to_grp, entity_mapping)
        if to_tag not in self.nodes:
            self.nodes[to_tag] = MCNode()

        # add transition out of current node
        node = self.nodes[current_tag]
        node.add_transition(to_tag, from_grp, to_grp)

        # add reverse edge index
        if to_tag in self.reverse_edges: self.reverse_edges[to_tag].add(current_tag)
        else: self.reverse_edges[to_tag] = set((current_tag,))

        # move current
        return to_tag

    def make_tag(self, grp, entity_mapping):
        head_dn = grp[0]
        tgt = head_dn.behavior_target()
        # if len(grp) > 1: pre = 'GRP'
        # else: pre = ''
        pre = ''
        if tgt is None:
            return "{}{}{}".format(pre, entity_mapping.token(head_dn.agent()), head_dn.behavior_sig)
        return "{}{}{}".format(pre, entity_mapping.token(head_dn.agent()), head_dn.behavior_sig.replace(str(tgt.eid), entity_mapping.token(tgt)))

    def extract_agents(self, htrace, trace):
        A = set()
        for grp in htrace:
            for dn in grp:
                agent = dn.agent(trace)
                if agent.tid == data.AGENT_TYPE_ID:
                    A.add(agent.eid)
        return A

    def all_case_groups(self, node_tag):
        """All the cases for a given node are in the transitions *to* that node."""
        for tag in self.reverse_edges[node_tag]:
            for from_grp,to_grp in self.nodes[tag].transitions[node_tag]:
                yield to_grp

    def make_sub_chain(self, node_tag, mapper=EntityMapping2):
        if node_tag != 'End':
            self.nodes[node_tag].chain = MarkovChain(([(dn,) for dn in grp] for grp in self.all_case_groups(node_tag)), mapper)

    def __str__(self):
        return "\n".join(("{} {} => {}".format(node.out_ct, tag, str(node)) for tag,node in sorted(self.nodes.items(), key=lambda e: e[0]) if tag != 'End'))

class MCNode:
    """"""
    def __init__(self):
        self.out_ct = 0
        self.transitions = {}

        self.chain = None

    def add_transition(self, to_tag, from_grp, to_grp):
        """Transitions is a dict of tag : [cases]."""
        self.out_ct += 1
        if to_tag in self.transitions:
            self.transitions[to_tag].append((from_grp, to_grp))
        else:
            self.transitions[to_tag] = [(from_grp, to_grp)]

    def __str__(self):
        return ", ".join(("{:.2f}: {}".format(len(cases)/self.out_ct, tag) for tag,cases in self.transitions.items()))

##############################################################

if __name__ == '__main__':
    traces = load_traces(DATA_DIR)

    # convert to hierarchical events
    htraces = convert_traces(traces)

    for t,ht in zip(traces,htraces):
        print("=========================")
        print(t)
        print("=========================")
        for intr in ht:
            print("-----------")
            for dn in intr:
                print(dn)

    # # make hierarchical Markov Chain
    # print("==================== Top level chain ===========================")
    # chain = MarkovChain(htraces)
    # print(chain, flush=True)
    #
    # for tag in chain.nodes.keys():
    #     if tag not in ('Start', 'End'):
    #         print(" ========== Sub chain for {}".format(tag))
    #         chain.make_sub_chain(tag)
    #         print(chain.nodes[tag].chain)
