import math

class vector2:

    def __init__(self, xy):
        self.x = xy[0]
        self.y = xy[1]

    def __str__(self):
        return "({:.0f},{:.0f})".format(self.x, self.y)

    def xy(self):
        return (self.x,self.y)

    def intxy(self):
        return (int(self.x), int(self.y))

    def __sub__(self, other):
        return vector2(((self.x - other.x), (self.y - other.y)))

    def __add__(self, other):
        if(type(other) == int):
            return vector2(((self.x + other), (self.y + other)))
        return vector2(((self.x + other.x), (self.y + other.y)))

    def __mul__(self, s):
        return vector2(((self.x * s), (self.y * s)))

    def magnitude(self):
        return math.sqrt(self.x*self.x + self.y*self.y)

    def normalized(self, m=None):
        m = m or self.magnitude()
        ans = vector2(self.xy())
        ans.x /= m
        ans.y /= m
        return ans

    def scale(self, s):
        ans = vector2(self.xy())
        ans.x *= s
        ans.y *= s
        return ans

    def dot(self, v):
        return self.x * v.x + self.y * v.y

# statics
zero = vector2((0, 0))
