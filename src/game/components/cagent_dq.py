from components.cagent import *
from vector2 import *
import data as data
import numpy as np
from scipy import misc


class dqnPlay(CAgent):
    def __init__(self, eid, goals):
        super().__init__(eid, goals)
        self.ct = 0
        self.agent = None
        self.origPos = None
        self.optimalPos = None

    def setUp(self, world):
        self.agent = world.entities.get(self.eid)
        self.origPos = self.agent.pos
        self.optimalPos = self.closestTree(world)

    def netInput(self, world, action):
        if(self.ct == 0):
            self.setUp(world)
        newPos = vector2([self.agent.pos.x, self.agent.pos.x])
        #setting original position

        #left
        if(action == 0):
            newPos.x -= 40
        #up
        elif(action == 1):
            newPos.y += 40
        #right
        elif(action == 2):
            newPos.x += 40
        #down
        elif(action == 3):
            newPos.y -= 40


        self.agent.pos = newPos
        if(self.optimalPos == None):
            self.optimalPos = vector2([200, 200])

       #print(self.optimalPos)
        #tells the game to snap the current state
        self.agent.flag = "snap"
        reward = 0
        done = False
        currentState = None
        switch = 1
        if(switch % 2 == 0):
            self.ct = 2
        else:
            self.ct = 1

        imr = misc.imread('C:/Users/daniel/Documents/survive/src/game/images/im' + str(self.ct) + '.jpeg')
        #if image ever gets cut off use other image
        if(imr.shape == ()):
            print("in condition")
            if(self.ct == 1):
                self.ct = 2
            else:
                self.ct = 1
            imr = misc.imread('C:/Users/daniel/Documents/survive/src/game/images/im' + str(self.ct) + '.jpeg')
        currentState = imr
        self.ct += 1
        info = 1
        m = self.agent.pos - self.optimalPos
        m = m.magnitude()
        print("mag", m)
        diff = self.agent.pos - self.origPos
        #print(diff.magnitude())
        #if agent pos strayed too far away terminate reward 0
        if (diff.magnitude() > 500 and m > 500):
            done = True
            print("strayed too far")
            return currentState, reward, done, info

        if(m < 200):
            print("finished")
            reward = 1
            done = True

        return currentState, reward, done, info


    def closestTree(self, world):
        agent = world.entities.get(self.eid)
        tree = []
        for eid, ent in world.entities_within_range(self.eid, data.awareness[data.AGENT_TYPE_ID]):
            tree.append(world.entities.get(eid))

        lens = len(tree)
        i = 0
        closest = None
        ind = None
        while(i < lens):
            pos1 = agent.pos - tree[i].pos
            magnit = pos1.magnitude()
            if(closest != None and magnit < closest):
                closest = magnit
                ind = pos1
            elif(closest == None):
                closest = magnit
                ind = pos1

            i += 1

        return ind

    def wanderAround(self):
        pass

