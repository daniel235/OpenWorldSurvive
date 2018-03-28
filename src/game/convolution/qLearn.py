import gym
import numpy as np
import random
import tensorflow as tf
import tensorflow.contrib.slim as slim
import matplotlib.pyplot as plt


try:
    xrange = xrange
except:
    xrange = range

#env = gym.make('CartPole-v0')
class env():
    def __init__(self, environment):
        self.env = np.array(environment).reshape([1,16])
        self.numActions = 4
        self.pos = 8
        self.steps = 0
        self.actions = []

    def step(self, action):
        #get observation
        #get current position(state)
        n = self.env
        b = False
        reward = 0
        cursor = 0
        rs = self.optimal_state()

        if(action == 0):
            cursor = -1
        elif(action == 1):
            cursor = -4
        elif (action == 2):
            cursor = 1
        else:
            cursor = 4

        self.pos += cursor
        self.actions.append(action)
        if(self.pos == rs):
            reward = 1 - (self.steps * .1)
            b = True
            print("got reward steps -> ", self.steps, " " ,action, " ", reward)
            for i in range(len(self.actions)):
                print("steps ", self.actions[i])

        if(self.pos < 0 or self.pos > 16):
            reward = -1
            b = True

        self.steps += 1
        final = [n, reward, b]
        return final

    # this function gives reward similar to pullArm in contextual bandit
    def optimal_state(self):
        #action can be 4 -4 1 or -1
        #need to get state
        rState = []
        for i in range(self.env.shape[1]):
            if(self.env[0,i] == 1):
                rState.append(i)


        #only works for two trees
        one = rState[0] - 8
        two = rState[1] - 8
        one = abs(one)
        two = abs(two)
        if(one < two):
            return rState[0]
        else:
            return rState[1]


    def reset(self):
        #count = len(self.env)/2
        #starting position
        #s = self.env[0][16]
        s = self.env
        self.steps = 0
        self.pos = 8
        self.actions = []
        return s



gamma = 0.95

def discount_rewards(r):
    discounted_r = np.zeros_like(r)
    running_add = 0
    for t in reversed(xrange(0, r.size)):
        running_add = running_add * gamma + r[t]
        discounted_r[t] = running_add
    return discounted_r

class agent():
    def __init__(self, lr, s_size, a_size, h_size):
        #these lines establish the feed forward part of the network
        self.state_in = tf.placeholder(shape=[None,s_size], dtype=tf.float32)
        #state_in_OH = slim.one_hot_encoding(self.state_in, s_size)

        hidden = slim.fully_connected(self.state_in, h_size, biases_initializer=None, activation_fn=tf.nn.relu)

        self.output = slim.fully_connected(hidden, a_size, biases_initializer=None,activation_fn=tf.nn.softmax)
        self.chosen_action = tf.argmax(self.output,1)

        #the next six lines establish training procedure
        self.reward_holder = tf.placeholder(shape=[None], dtype=tf.float32)
        self.action_holder = tf.placeholder(shape=[None],dtype=tf.int32)

        self.indexes = tf.range(0, tf.shape(self.output)[0]) * tf.shape(self.output)[1] + self.action_holder
        self.responsible_outputs = tf.gather(tf.reshape(self.output, [-1]), self.indexes)


        self.loss = -tf.reduce_mean(tf.log(self.responsible_outputs)* self.reward_holder)

        tvars = tf.trainable_variables()
        self.gradient_holders = []
        for idx, var in enumerate(tvars):
            placeholder = tf.placeholder(tf.float32, name=str(idx) + '_holder')
            self.gradient_holders.append(placeholder)

        self.gradients = tf.gradients(self.loss, tvars)

        optimizer = tf.train.AdamOptimizer(learning_rate=lr)
        self.update_batch = optimizer.apply_gradients(zip(self.gradient_holders, tvars))



tf.reset_default_graph()

myAgent = agent(lr=1e-2, s_size=16, a_size=4, h_size=8)
weights = tf.trainable_variables()[0]


e = env([0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,1])
total_episodes = 2000
max_ep = 99
update_frequency = 5
total_reward = np.zeros([8,4])
eChance = 0.25

init = tf.global_variables_initializer()

with tf.Session() as sess:
    sess.run(init)
    i = 0
    total_reward = []
    total_length = []


    gradBuffer = sess.run(tf.trainable_variables())
    for ix, grad in enumerate(gradBuffer):
        gradBuffer[ix] = grad * 0

    while i < total_episodes:
        s = e.reset()  #[0][16]
        running_reward = 0
        ep_history = []

        for j in range(max_ep):
            a_dist = sess.run(myAgent.output, feed_dict={myAgent.state_in:s})
            a = np.random.choice(a_dist[0], p=a_dist[0])
            a = np.argmax(a_dist==a)
            ob = e.step(a)
            sl = ob[0]
            r = ob[1]
            d = ob[2]
            _ = None

            ep_history.append([s,a,r,sl])
            s = sl
            running_reward += r
            if d == True:
                ep_history = np.array(ep_history)
                ep_history[:,2] = discount_rewards(ep_history[:,2])
                feed_dict = {myAgent.reward_holder: ep_history[:, 2],
                             myAgent.action_holder: ep_history[:,1], myAgent.state_in: np.vstack(ep_history[:,0])}
                grads = sess.run(myAgent.gradients, feed_dict)
                for idx, grad in enumerate(grads):
                    gradBuffer[idx] += grad

                if i % update_frequency == 0 and i != 0:
                    feed_dict = dictionary = dict(zip(myAgent.gradient_holders, gradBuffer))
                    _ = sess.run(myAgent.update_batch, feed_dict=feed_dict)
                    for ix, grad in enumerate(gradBuffer):
                        gradBuffer[ix] = grad * 0

                total_reward.append(running_reward)
                total_length.append(j)
                break

        i += 1

    if i % 100 == 0:
        print(np.mean(total_reward[-100:]))
    i += 1

