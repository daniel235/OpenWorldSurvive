import math
from vector2 import vector2


class IBoid(vector2):
    def __init__(self, host):
        #object passed in steering manager
        self.pos = host
        self.x = self.pos.x
        self.y = self.pos.y
        self.velocity = vector2([0, 0])
        self.MaxVelocity = 2
        self.Mass = 2
        self.ahead = None
        self.avoidanceForce = None

    def getVelocity(self, target):
        norm = target - self.pos
        self.velocity = norm.normalized() * self.MaxVelocity
        print("getvelocity", self.velocity)
        return self.velocity

    def getMaxVelocity(self):
        return self.MaxVelocity

    def getPosition(self):
        self.pos = self.pos + self.velocity
        return self.pos

    def getMass(self):
        return self.Mass

    def getAhead(self):
        self.ahead = self.host + self.velocity.normalized() * 2
        return self.ahead

    def getAvoidanceForce(self, enemy):
        self.avoidanceForce = self.ahead - enemy
        #bigger avoidance force the more it pushes away from center of obstacle
        self.avoidanceForce = self.avoidanceForce.normalized() * 2
        print("get avoidance force function", self.avoidanceForce)
        return self.avoidanceForce


class SteeringManager(IBoid):
    def __init__(self, host):
        self.host = IBoid(host)
        super(SteeringManager).__init__()

    def seek(self, target, slowingRadius):
        self.host.incrementBy(self.doSeek(target, slowingRadius))
        return self.host


    def distance(self, a, b):
        return math.sqrt((a.x - b.x) * (a.x - b.x) + (a.y - b.y) * (a.y - b.y))

    def intersectObject(self, ahead, obstacle):
        a = ahead - obstacle
        a = a.magnitude()
        return  a <= 10


    def pursuit(self, target):
        self.steering.incrementBy(self.doPursuit(target))

    def update(self, target, enemy):
        #updating iboid
        print("my position", self.host.pos, " target position ", target.xy)
        self.velocity = self.host.getVelocity(target)
        print("velocity on steering manager update", self.velocity)
        self.position = self.host.getPosition()
        print("position on steering manager update", self.position)
        self.ahead = self.position + self.velocity.normalized() * 2
        print("ahead vector", self.ahead)
        if(self.distance(self.ahead, enemy) < 30):
            print("colliding")

    def reset(self):
        pass



    def doSeek(self, target, slowingRadius):
        force = None
        distance = None

        desired = target - (self.host.getPosition())
        distance = desired.magnitude()
        desired.normalized()

        if(distance <= slowingRadius):
            desired.scale(self.host.getMaxVelocity() * distance / slowingRadius)
        else:
            desired.scale(self.host.getMaxVelocity())

        force = desired - (self.host.getVelocity(target))
        print("do seek function force", force)
        return force

    def doFlee(self, target):
        pass

    def getMaxVelocity(self):
        return 3

    def doWander(self):
        pass

    def collisionAvoidance(self, enemy):
        ahead = self.getAhead()

        mostThreatening = enemy
        avoidance = self.getAvoidanceForce(enemy)

        if mostThreatening != None:
            avoidance.x = ahead.x - mostThreatening.x
            avoidance.y = ahead.y - mostThreatening.y
            print(avoidance)
            avoidance.normalized()
            avoidance.scale(3)
        else:
            avoidance.scale(0)
        print("avoidance force function", avoidance)
        return avoidance



    def doEvade(self, target):
        pass

    def doPursuit(self, target):
        distance = target.getPosition().subtract(self.host.getPosition())

        updatesNeeded = distance.length / self.host.getMaxVelocity()
        tv = target.getVelocity().clone()
        tv.scaleBy(updatesNeeded)

        targetFuturePosition = target.getPosition().clone().add(tv)
        print("do Pursuit function", targetFuturePosition)
        return self.doSeek(targetFuturePosition)