"""
Drama Manager

1) Agents have decision policies that gives them sets of reasonable options.
2) Global UCT is used to confirm, to get more details, to explore complex interactions and to find opportunities.
3) Planning is used to get longer term plans.
4) At runtime, scripts, estimated simulation and hierarchical abstraction (zoom!) used to speed up.
5) In training, more extensive UCT run to update policies.

Policies must be used in rollouts to create new nodes (because of the real-time constraint). Random would be really 
silly. Existing nodes can be selected with UCB. Estimated simulation could be a heuristic speed up.
"""

import time, copy, math
from components.cbehavior import CBehaviorNoOp
from components.cagent import Cursor2

# module level
DEBUG=True
DEBUG_ROLLOUT=False

########################### Default Pass-Through #############################

class DramaManager:
    def __init__(self, world):
        self.world = world

    def string_goals(self, target_world=None):
        if target_world is None:
            target_world = self.world

        s = ""
        for pid, a in target_world.agents.all():
            s += a.string_goals(target_world)
        return s

    def goals_met(self, target_world=None):
        """Check if designated key goal(s) are completed."""
        # for now, if any agent has met all their goals, we're done
        if target_world is None:
            target_world = self.world

        return any((a.met_goals(target_world) for pid, a in target_world.agents.all()))

    def goal_rewards(self, target_world=None):
        if target_world is None:
            target_world = self.world

        return {aid : agent.goal_rewards(target_world) / target_world.clock for aid,agent in target_world.agents.all()}

    def diff_rewards(self, start_world, end_world):
        """
        value of reward progress at end - start
        should include rewards added and completed
        """
        for aid, agent in end_world.agents.all():
            sagent = start_world.agents.get(aid)
            yield aid, ((agent.goal_rewards(end_world) - sagent.goal_rewards(start_world)),
                        end_world.clock - start_world.clock)

    def update_consider(self, dt):
        """Default just passes through to agent-level consideration."""
        self.world.consider(dt)

########################### MCTS Drama Manager #############################

class MCStats:
    def __init__(self):
        self.tree_depth = 0
        self.rollout_ct = 0
        self.update_ct = 0
        self.start_time = None
        self.total_effort = 0
        self.applied_behaviors = []
        self.application_time = None

    def effort_per_sec(self):
        if self.application_time == self.start_time: return self.total_effort
        else: return self.total_effort/(self.application_time - self.start_time)

    def __str__(self):
        return "MCTS ({:.2f} - {:.2f}), depth: {}, updates: {}, rollouts: {}, effort/s: {:.4f}, effort/consider: {:.4f}\nBeh: {}".format(
            self.start_time, self.application_time,
            self.tree_depth, self.update_ct, self.rollout_ct,
            self.effort_per_sec(), self.total_effort/self.update_ct,
            ", ".join((str(b) for b in self.applied_behaviors)))

class MCNodeGroup:
    """
    A set of nodes in the search tree with a common timestamp and agent.
    """
    def __init__(self, agent_id, timestamp, first_behavior, cursor, world):
        # common to the group
        self.agent_id = agent_id
        self.timestamp = timestamp
        self.saved_world = copy.deepcopy(world)
        self.reward = 0
        self.cost = 0

        # structure
        self.members = [first_behavior]
        first_behavior.group = self

        # enable incremental expansion
        self.cursor = cursor

        #print("added group {}".format(self))

    def depth(self):
        if len(self.members) == 0: return 0
        return max((child.depth() for child in self.members))

    def add_node(self, node):
        self.members.append(node)
        node.group = self

    def most_rewarding(self):
        """Return member with highest normalized reward."""
        pick = None
        hscore = 0
        for n in self.members:
            score = n.normalized_rewards()
            if pick is None or score > hscore:
                pick = n
                hscore = score
        return pick

    def select_UCB1(self, world):
        """Return child node with highest promise (UCB1 algorithm)."""
        pick,hscore = None,0
        for n in self.members:
            score = n.promise()
            if pick is None or score > hscore:
                pick = n
                hscore = score
        # see if it's time for an alternative behavior (if can generate more)
        if self.cursor is not None and not self.cursor.done() and self.alternative_score() > hscore:
            agent = world.agents.get(self.agent_id)
            agent.proposal = self.cursor.next()
            n = MCNode(agent.proposal)
            self.add_node(n)
            if DEBUG_ROLLOUT: print("...UCB1 select proposing {} alt to {}".format(agent.proposal, pick.behavior))
            return n
        return pick

    def alternative_score(self):
        """Calculate upper bound for unknown alternative behavior. (UCB w/ 0 reward, 1 visit)."""
        return math.sqrt(2 * math.log(self.previous_node.visits + 1))

    def __str__(self):
        return "MCNodeGroup({},{}: {})".format(self.agent_id, self.timestamp, ",".join((str(n) for n in self.members)))

class MCNode:
    """
    A node in the search tree. Specifies a particular agent-behavior-time tuple (incl. no-op).
    Rewards are saved in the node relative to the acting agent's goals.
    """
    next_id = 1000

    @staticmethod
    def gen_next_id():
        MCNode.next_id += 1
        return MCNode.next_id

    def __init__(self, behavior):
        self.id = MCNode.gen_next_id()

        # behavior
        self.behavior = behavior

        # structure
        self.group = None
        self.next_group = None

        # accounting
        self.visits = 0
        self.rewards = {}
        self.applied = False

        #print("added node {}".format(self.behavior))

    def depth(self):
        if self.next_group is None: return 1
        return self.next_group.depth() + 1

    def normalized_rewards(self):
        if self.group is not None and self.group.agent_id in self.rewards: return self.rewards[self.group.agent_id]
        return 0

    def promise(self):
        """How promising is this node to explore? UCB1 algorithm based on reward to the acting agent."""
        return self.normalized_rewards() + self.upperBound()

    def upperBound(self):
        """Helper function for UCB1."""
        return math.sqrt(2 * math.log(self.group.previous_node.visits + 1) / self.visits)

    def update_rewards(self, dm, end_world):
        """Update rewards for all agents in the reward set."""
        self.visits += 1
        if self.group is not None:
            for aid,(r,c) in dm.diff_rewards(self.group.saved_world, end_world):
                self.update_reward(aid, r, c)

    def update_reward(self, agent_id, reward, cost):
        """Update reward for a specific agent by simple average."""
        if agent_id in self.rewards:
            total_reward = (self.rewards[agent_id] * (self.visits-1)) + (reward/cost)
        else:
            total_reward = (reward/cost)
        self.rewards[agent_id] = total_reward / self.visits
        #print("updated node {} to {} (visit {})".format(self.behavior, self.normalized_rewards(), self.visits))

    def update_rewards_recursive(self, dm, end_world):
        """Update rewards up the tree through all parents."""
        self.update_rewards(dm, end_world)
        if self.group is not None:
            self.group.previous_node.update_rewards_recursive(dm, end_world)

    def set_next_group(self, group):
        self.next_group = group
        if group is not None:
            group.previous_node = self

    def insert_group(self, agent_id, timestamp, behavior, cursor, world):
        """Insert the specified group (with one member) between this node and the next group.
        The one member has the same stats as this node.
        """
        # create member node and duplicate stats
        node = MCNode(behavior)
        node.visits = self.visits
        node.rewards = copy.deepcopy(self.rewards)

        # insert into hierarchy
        group = MCNodeGroup(agent_id, timestamp, node, cursor, world)
        node.set_next_group(self.next_group)
        self.set_next_group(group)

        # return group for syntactic nicety
        return group

    def append_group(self, agent_id, timestamp, behavior, cursor, world):
        """Append the specified group (with one member) after this node."""

        # create group w/ one member to append
        group = MCNodeGroup(agent_id, timestamp, MCNode(behavior), cursor, world)
        self.set_next_group(group)

        # return group for syntactic nicety
        return group

    def ts(self):
        if self.group is not None: return self.group.timestamp
        return 0

    def short(self):
        if self.group is None:
            return "(MCNode({}))".format(self.behavior)
        else:
            return "(MCNode({}) {:.4f})".format(self.behavior,self.group.timestamp)

    def __str__(self):
        return "(MCNode({}),{}/{}: {})".format(self.behavior, self.rewards, self.visits, self.next_group)

class DramaManager_MCTS(DramaManager):
    def __init__(self, world, kb, fixed_timestep):
        """
        :param world: the world in the starting state
        :param kb: accumulated policy knowledge
        :param fixed_timestep: the time step for the rollouts to simulate (seconds)
        """
        super().__init__(world)
        self.kb = kb
        self.fixed_timestep = fixed_timestep

        self.active_tree = None
        self.active_stats = None

    def update_consider(self, dt, effort, depth_limit):
        """
        :param dt: last frame delta (seconds)
        :param effort: time to spend searching (seconds)
        :return: 
        """

        #print("Update {}: effort {}".format(self.world.clock, effort))

        # restart the search, as necessary
        if self.active_tree is None:
            if DEBUG: print("================= Starting MCTS at time {} ====================".format(self.world.clock))
            self.active_tree = MCNode(None)
            self.active_stats = MCStats()
            self.active_stats.start_time = self.world.clock

        # only rollout if there is effort and the simulation has gone past the tree
        if self.active_tree.next_group is None or self.world.clock <= self.active_tree.next_group.timestamp:
            # if there is effort, spend it
            if effort > 0:
                self.active_stats.update_ct += 1

            initial_effort = effort
            while effort > 0:
                effort = self.update_mcts(effort, depth_limit)
                #print(str(self.active_tree.next_group))
            self.active_stats.total_effort += (initial_effort - effort)

        #print("...effort left: {}".format(effort))
        #print("...total effort: {}".format(self.active_stats.total_effort))

        # if the time is right for first-level choices, assign those agent behaviors
        group = self.active_tree.next_group
        assigned=False
        while group is not None and group.timestamp <= self.world.clock:
            node = group.most_rewarding()
            node.behavior.reset()
            self.world.agents.get(group.agent_id).proposal = node.behavior
            self.active_stats.applied_behaviors.append(node.behavior)
            if DEBUG: print("============== MCTS applying {} from group {} ===================".format(node.behavior, group))

            # mark node applied (for vizualization)
            node.applied = True

            # keep going to clear all simultaneous selections
            group = node.next_group
            assigned = True

        if assigned:
            # return the tree used for assignment and restart the tree search
            tree = self.active_tree
            self.active_tree = None
            self.active_stats.tree_depth = tree.depth()
            self.active_stats.application_time = self.world.clock
            self.active_stats.rollout_ct = tree.visits
            print("==== MCTS Stats: {}".format(self.active_stats))
            return tree,self.active_stats,effort

        return None,None,effort

    def update_mcts(self, effort, depth_limit):
        """Perform a MCTS update of self.active_tree."""
        start = time.time()
        current = self.active_tree
        rollout = copy.deepcopy(self.world)
        rollout.simulation = True
        depth = 0

        ROLLOUT_LIMIT = 0.01

        if DEBUG_ROLLOUT: print("[{:.2f}] Starting tree update".format(rollout.clock))
        # for debugging
        path = [current]

        finish_rollout = False
        #while (time.time() - start) < effort and not self.goals_met(rollout):
        while not self.goals_met(rollout) and (depth_limit is None or depth < depth_limit):

            if (time.time() - start) > ROLLOUT_LIMIT:
                if DEBUG_ROLLOUT:
                    print("Rollout limit reached at clock {:.2f} after {} rollouts for world:".format(rollout.clock, self.active_stats.rollout_ct))
                    print(rollout.string_entities())
                    print(self.string_goals())
                break

            if not finish_rollout:
                # still traversing the tree

                if current.next_group is not None and rollout.clock >= current.next_group.timestamp:
                    # the simulation has arrived at the next group
                    #print("...arrived at next group")

                    # select the best available behavior and execute it
                    # (repeat for simultaneous next behaviors)
                    while current.next_group is not None and rollout.clock >= current.next_group.timestamp:
                        selected = current.next_group.select_UCB1(rollout)
                        #print("...selected {}".format(selected))
                        # propose for execution (circumventing agent consider)
                        if not isinstance(selected.behavior, CBehaviorNoOp):
                            selected.behavior.reset()
                            rollout.agents.get(current.next_group.agent_id).proposal = selected.behavior
                            #print("{:.4f}...activated {}".format(rollout.clock, selected.behavior))
                        # move current pointer forward and check again
                        if DEBUG_ROLLOUT: print("[{:.2f}]...selected {}".format(rollout.clock, selected))
                        current = selected
                        depth += 1
                        path.append(current)
                else:
                    #print("...stepping to next group (current {})".format(current))

                    # either there is no next group (current is leaf), or we're still before next_group
                    interrupt = current.next_group is not None
                    for aid,agent in rollout.agents.all():
                        options = agent.consider(rollout, self.fixed_timestep)
                        if options is not None:
                            # this agent wants to act, either an interrupt (before the next group) or a new leaf
                            if interrupt:
                                if DEBUG_ROLLOUT: print("[{:.2f}]...interrupt! proposed {} before {}\n...Path: {}".format(
                                    rollout.clock, agent.proposal, current.next_group, "\n".join(n.short() for n in path)))

                                # agent proposed an interruption, insert pre-emptive group w/ no-op behavior above current tree
                                group = current.insert_group(aid, rollout.clock, CBehaviorNoOp(), Cursor2(options[1:]), rollout)
                                # add proposed behavior as second member of the inserted group
                                node = MCNode(agent.proposal)
                                group.add_node(node)
                                # move current pointer down to proposed node
                                current = node
                                depth += 1
                                # and mark as past interrupt (in case of multiple simultaneous agent actions)
                                interrupt = False
                                if DEBUG_ROLLOUT: print("[{:.2f}] post-insert: {}".format(rollout.clock, self.active_tree))
                            else:
                                # there is no next group (this also works for adding more than one action in this frame)
                                #print("{} Pre-Insert: {}".format(rollout.clock, self.active_tree))
                                group = current.append_group(aid, rollout.clock, agent.proposal, Cursor2(options[1:]), rollout)
                                if DEBUG_ROLLOUT: print("[{:.2f}] post-append: {}".format(rollout.clock, self.active_tree))
                                current = group.members[0]
                                depth += 1

                            # mark to finish rollout
                            finish_rollout = True
                            #print("...Finishing rollout")
            else:
                # policy-normal rollout
                rollout.consider(self.fixed_timestep)

            rollout.update(self.fixed_timestep)

        # either satisfied rewards or reached depth limit

        # calculate rewards for end state and update the tree
        current.update_rewards_recursive(self, rollout)

        #print("...Finished tree update")

        # return remaining effort
        return effort - (time.time() - start)

