# Data Collector
# interface for storing situation/outcome pairs for training

import os, pickle
import numpy as np

from vector2 import vector2

# Screens
# extract state from world

class VisibleFilter:
    def __init__(self, viewport_dim, filter_dim, types):
        self.viewport_dim = viewport_dim
        self.dim = filter_dim

        self.halfport = self.half_viewport(viewport_dim)
        self.ratio = self.filter_ratio(viewport_dim, filter_dim)

        # observation is array of 1-hot unit counts by type
        self.obs = np.zeros((filter_dim[0], filter_dim[1], len(types)), dtype=np.float32)

        # index table for one-hot types
        self.type_indeces = {tid : i for tid, i in zip(types, range(0,len(types)))}

    def filter(self, world, pid):
        # zero out prior values
        self.obs[:] = 0
        # increment counts for each entity in world according to position
        offset = self.viewport_offset(world, pid)
        #print("offset {}, halfport {}".format(offset, self.halfport))
        for eid, ent in world.entities.all():
            vpos = self.world_to_viewport(ent.pos, offset)
            if self.within_viewport(vpos):
                fpos = self.viewport_to_filter(vpos)
                self.obs[int(fpos.x), int(fpos.y), self.type_indeces[ent.tid]] += 1
            #else:
            #    print("{} => {} out of view".format(ent.pos, vpos))
        return self.obs

    def within_viewport(self, pos):
        return pos.x > 0 and pos.x < self.viewport_dim[0] and pos.y > 0 and pos.y < self.viewport_dim[1]

    def viewport_offset(self, world, pid):
        return world.entities.get(pid).pos

    def half_viewport(self, viewport_dim):
        return vector2([(int(d / 2)) for d in viewport_dim])

    def world_to_viewport(self, pos, offset):
        return pos - offset + self.halfport

    def filter_ratio(self, viewport_dim, filter_dim):
        return (filter_dim[0]/viewport_dim[0], filter_dim[1]/viewport_dim[1])

    def viewport_to_filter(self, pos):
        return vector2((pos.x * self.ratio[0], pos.y * self.ratio[1]))

    def __str__(self):
        s = ""
        for i in range(0, self.dim[0]):
            for j in range(0, self.dim[1]):
                for k in range(0, len(self.type_indeces.keys())):
                    if self.obs[i,j,k] != 0:
                        s += "({},{}) {}: {}\n".format(i,j,k,self.obs[i,j,k])
        return s

def print_obs(obs, d1, d2, depth):
    s = ""
    for i in range(0, d1):
        for j in range(0, d2):
            for k in range(0, depth):
                if obs[i, j, k] != 0:
                    s += "({},{}) {}: {}\n".format(i, j, k, obs[i, j, k])
    return s

def load_from_file(dir, FN, filter_dim, types):
    """Load samples from files into numpy arrays for data, values"""
    D = []
    V = []

    for fn in FN:
        infile = open(os.path.join(dir, fn), 'rb')
        master,all_trees = pickle.load(infile)
        infile.close()

        # state filter
        vf = VisibleFilter(master.viewport, filter_dim, types)

        # all_trees holds a list of (tree,stats) pairs and the total run time
        #  where each tree node group holds the agent making
        #  the decision and the world state at that point, and each tree node holds the per-agent rewards
        for TS,clock in all_trees.values():
            for t,s in TS:
                add_nodes(t, vf, master.player_id, D, V)

    return np.array(D),np.array(V, dtype=np.float32)

def add_nodes(tree, filter, focus_agent_id, data, values):
    # only care if we have a next state (group) to consider
    if tree.next_group is not None:
        if tree.group is not None:
            # the expected reward of a node (behavior) is the quality of the ensuing state
            #  for the agent executing that behavior
            data.append(filter.filter(tree.next_group.saved_world, focus_agent_id))
            values.append(tree.rewards[tree.group.agent_id])

        # and recurse down the tree
        for n in tree.next_group.members:
            add_nodes(n, filter, focus_agent_id, data, values)

def load_choices_from_file(dir, fn, filter_dim, types, depth):
    """
    Load samples from one file, to specified tree depth, as choices
    choices are lists of resulting_state-reward pairs that go together
    """
    choices = []

    infile = open(os.path.join(dir, fn), 'rb')
    master,all_trees = pickle.load(infile)
    infile.close()

    # state filter
    vf = VisibleFilter(master.viewport, filter_dim, types)

    # all_trees holds a list of (tree,stats) pairs and the total run time
    #  where each tree node group holds the agent making
    #  the decision and the world state at that point, and each tree node holds the per-agent rewards
    for TS,clock in all_trees.values():
        for t,s in TS:
            if t.next_group is not None:
                add_choices(t.next_group, vf, master.player_id, choices, depth)

    return choices

def add_choices(group, filter, focus_agent_id, choices, depth):
    if depth == 0: return

    cset = []
    for action in group.members:
        if action.next_group is not None:
            cset.append((filter.filter(action.next_group.saved_world, focus_agent_id),
                         action.rewards[action.group.agent_id]))

            # and recurse down the tree
            add_choices(action.next_group, filter, focus_agent_id, choices, depth-1)

    if len(cset) > 0:
        choices.append(cset)
