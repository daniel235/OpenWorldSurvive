import os
import sys
import numpy as np
import tensorflow as tf
from collections import deque
from src.game.worldspec import *
import src.game.gui as g
from src.game.runner import *
import matplotlib.pylab as plt


TIME_LIMIT = 120

DIM = (704, 640)
VIEWPORT = (704, 640)

weapons = ((2004, 1), (2006, 1), (2007, 1), (2008, 1))  # 2004 is no weapon
attacks = ((3000, 1), (3001, 1), (3002, 1), (3003, 1))

class envs():
    def __init__(self):
        self.action_space = 4
        self.world = None
        self.main = None
        self.focus_eid = None
        self.r = None
        self.ct = 0
        self.done = None
        self.stepFlag = 'idle'
        self.agent = None

    def step(self, action):
        self.state = None
        self.reward = 0
        self.done = False
        self.info = None
        if(self.world != None):
            res = None
            for id, a in self.world.agents.all():
                if(a != None):
                    res = a
                    self.state, self.reward, self.done, self.info = res.netInput(self.world, action)

        return self.state, self.reward, self.done, self.info


    #starts game
    def reset(self):
        #this is waiting for start to finish (big problem)
        self.ct = 0
        self.seed = random.randint(0, sys.maxsize)
        self.done = False
        random.seed(self.seed)
        self.worldspec = Worldspec(DIM, self.seed, attacks, weapons)
        self.r = RunnerPassThrough(DIM, VIEWPORT)
        self.focus_eid = self.r.setup(self.worldspec.spec['dqnTest'])
        self.world = self.r.world
        self.eid = self.focus_eid
        self.world.entities.get(self.focus_eid)
        g.init(VIEWPORT)
        self.r.start()
        #im = open("images.im" + str(0) + ".jpeg")
        ims = plt.imread("images.im" + str(0) + ".jpeg")
        ims = np.array(ims)
        return ims


def preprocess_observations(obs):
    img = obs[1:704:8, ::8]#crop and downsize
    img = img.mean(axis=2)
    img = np.array(img)
    img = (img - 128) / 128-1 #normalize from -1 to 1
    return img.reshape(88,80,1)

env = envs()

input_height = 88
input_width = 80
input_channels = 1
conv_n_maps = [32,64,64]
conv_kernel_sizes = [(8,8),(4,4),(3,3)]
conv_strides = [4,2,1]
conv_paddings = ["SAME"] * 3
conv_activation = [tf.nn.relu] * 3
n_hidden_in = 64 * 11 * 10 #conv3 has 64 maps of 11 * 10 each
n_hidden = 512
hidden_activation = tf.nn.relu
n_outputs = 4  #4 discrete actions are available
initializer = tf.contrib.layers.variance_scaling_initializer()

def q_network(X_state, name):
    prev_layer = X_state
    with tf.variable_scope(name) as scope:
        for n_maps, kernel_size, strides, padding, activation in zip(
            conv_n_maps, conv_kernel_sizes, conv_strides,
            conv_paddings, conv_activation):
            prev_layer = tf.layers.conv2d(prev_layer, filters=n_maps, kernel_size=kernel_size, strides=strides, padding=padding, activation=activation, kernel_initializer=initializer)


        last_conv_layer_flat = tf.reshape(prev_layer, shape=[-1, n_hidden_in])
        hidden = tf.layers.dense(last_conv_layer_flat, n_hidden, activation=hidden_activation, kernel_initializer=initializer)
        outputs = tf.layers.dense(hidden, n_outputs, kernel_initializer=initializer)

    trainable_vars = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, scope=scope.name)

    trainable_vars_by_name = {var.name[len(scope.name):]: var
                              for var in trainable_vars}
    return outputs, trainable_vars_by_name

X_state = tf.placeholder(tf.float32, shape=[None, input_height, input_width, input_channels])


online_q_values, online_vars = q_network(X_state, name="q_networks/online")
target_q_values, target_vars = q_network(X_state, name="q_networks/target")

copy_ops = [target_var.assign(online_vars[var_name])
            for var_name, target_var in target_vars.items()]

copy_online_to_target = tf.group(*copy_ops)
X_action = tf.placeholder(tf.int32, shape=[None])
q_value = tf.reduce_sum(target_q_values * tf.one_hot(X_action, n_outputs), axis = 1, keep_dims=True)

y = tf.placeholder(tf.float32, shape=[None, 1])
error = tf.abs(y - q_value)
clipped_error = tf.clip_by_value(error, 0.0, 1.0)
linear_error = 2 * (error - clipped_error)

loss = tf.reduce_mean(tf.square(clipped_error) + linear_error)

learning_rate = 0.001
momentum = 0.95

global_step = tf.Variable(0, trainable=False, name='global_step')
optimizer = tf.train.MomentumOptimizer(learning_rate, momentum, use_nesterov=True)

training_op = optimizer.minimize(loss, global_step=global_step)

init = tf.global_variables_initializer()
saver = tf.train.Saver()

replay_memory_size = 500000
replay_memory = deque([], maxlen=replay_memory_size)

def sample_memories(batch_size):
    indices = np.random.permutation(len(replay_memory))[:batch_size]
    cols = [[],[],[],[],[]]
    for idx in indices:
        memory = replay_memory[idx]
        for col, value in zip(cols, memory):
            col.append(value)

    cols = [np.array(col) for col in cols]
    return (cols[0], cols[1], cols[2].reshape(-1,1), cols[3], cols[4].reshape(-1, 1))


eps_min = 0.1
eps_max = 1.0
eps_decay_steps = 2000000

def epsilon_greedy(q_values, step):
    epsilon = max(eps_min, eps_max - (eps_max-eps_min) * step/eps_decay_steps)
    if np.random.rand() < epsilon:
        return np.random.randint(n_outputs)

    else:
        return np.argmax(q_values) #optimal action

n_steps = 4000000
training_start = 10000
training_interval = 4
save_steps = 1000
copy_steps = 10000
discount_rate = 0.99
skip_start = 90 #skip start of every game
batch_size = 50
iteration = 0 #game iterations
checkpoint_path = "./my_dqn.ckpt"
done = True

with tf.Session() as sess:
    obs = env.reset()
    if os.path.isfile(checkpoint_path + ".index"):
        saver.restore(sess, checkpoint_path)
    else:
        init.run()
        copy_online_to_target.run()

    env.ct += 1
    switch = 1
    while True:
        # exit condition
        # snapshot logic
        ent = env.world.entities.get(env.focus_eid)
        if (env.ct == 0):
            g.getScreen(0)
            env.ct += 1

        if (ent != None):
            if (ent.flag == "snap"):
                #update pictures without truncating image
                if (switch % 2 == 0):
                    env.ct = 1
                else:
                    env.ct = 2

                g.getScreen(env.ct)
                ent.flag = "idle"
                switch += 1

        # focus death
        if env.r.world.entities.get(env.focus_eid) is None:
            print(1, "Complete at world time {} => {}".format(env.r.world.clock, env.r.trace.decisions[-1].behavior_sig),
                  flush=True)
            env.r.trace.add_event(env.r.world, '(done)')
            env.done = True

        # loop
        if env.r.trace.looping():
            env.r.trace.add_event(env.r.world, '(looping)')
            print(1, "Complete at world time {} => {}".format(env.r.world.clock, env.r.trace.decisions[-1].behavior_sig),
                  flush=True)
            env.done = True

        # time limit
        if env.r.world.clock > TIME_LIMIT:
            env.r.trace.add_event(env.r.world, '(timeout)')
            print(1, "Complete at world time {} => {}".format(env.r.world.clock, env.r.trace.decisions[-1].behavior_sig),
                  flush=True)
            env.done = True

        env.r.step(False)

        # render
        g.set_msg(0, "{:.4f} FPS".format(env.r.fps))
        g.set_msg(1, "{:.4f} UPS".format(env.r.ups))
        g.update_screen(env.r.world, env.focus_eid)
        g.update_input()


        step = global_step.eval()
        if step >= n_steps:
            break
        iteration += 1
        if done: #game over start again
            obs = env.reset()
            for skip in range(skip_start):
                pass

            state = preprocess_observations(obs)

        #online dqn evaluates what to do
        q_values = online_q_values.eval(feed_dict={X_state: [state]})
        action = epsilon_greedy(q_values, step)
        #online dqn plays
        obs, reward, done, info = env.step(action)
        if(obs == None):
            done = True
        next_state = preprocess_observations(obs)
        #lets memorize what just happened
        replay_memory.append((state, action, reward, next_state, 1.0 - done))
        state = next_state
        if iteration < training_start or iteration % training_interval != 0:
            continue #only train after warmup period and at regular intervals
        #sample memories and use the target dqn to produce the target q-value
        X_state_val, X_action_val, rewards, X_next_state_val, continues = (sample_memories(batch_size))
        next_q_values = target_q_values.eval(feed_dict={X_state: X_next_state_val})
        max_next_q_values = np.max(next_q_values, axis=1, keepdims=True)
        y_val = rewards + continues * discount_rate * max_next_q_values
        #train the online dqn
        training_op.run(feed_dict={X_state: X_state_val, X_action: X_action_val, y: y_val})
         #regularly copy the online dqn to the target dqn
        if step % copy_steps == 0:
            copy_online_to_target.run()
        #and save regularly
        if step % save_steps == 0:
            saver.save(sess, checkpoint_path)

    env.r.trace.annotate_endings()
    print("Frames: {}, Updates: {}".format(env.r.fct, env.r.uct))
    print(env.r.trace, "\n")


