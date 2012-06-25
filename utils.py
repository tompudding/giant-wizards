from OpenGL.GL import *
import math,numpy,gamedata

grid_level = 0
ui_level   = 2
text_level = 10

full_tc       = numpy.array([(0,0),(0,1),(1,1),(1,0)],numpy.float32)

class QuadBuffer(object):
    def __init__(self,size):
        self.vertex_data  = numpy.zeros((size*4,3),numpy.float32)
        self.tc_data      = numpy.zeros((size*4,2),numpy.float32)
        self.colour_data = numpy.ones((size*4,4),numpy.float32) #RGBA default is white opaque
        self.indices      = numpy.zeros(size*4,numpy.uint32)  #de
        self.size = size
        for i in xrange(size*4):
            self.indices[i] = i
        self.current_size = 0
        self.max_size     = size*4
        self.vacant = []

    def next(self):
        if len(self.vacant) > 0:
            #for a vacant one we blatted the indices, so we should reset those...
            out = self.vacant.pop()
            for i in xrange(4):
                self.indices[out+i] = out+i
            return out
            
        out = self.current_size
        self.current_size += 4
        if self.current_size >= self.max_size:
            raise carpets
            # self.max_size *= 2
            # self.vertex_data.resize( (self.max_size,3) )
            # self.tc_data.resize    ( (self.max_size,2) )
        return out

    def truncate(self,n):
        self.current_size = n
        for i in xrange(self.size*4):
            self.indices[i] = i
        self.vacant = []

    def RemoveQuad(self,index):
        self.vacant.append(index)
        for i in xrange(4):
            self.indices[index+i] = 0

class QuadVertex(object):
    def __init__(self,index,buffer):
        self.index = index
        self.buffer = buffer
    
    def __getitem__(self,i):
        if isinstance(i,slice):
            start,stop,stride = i.indices(len(self.buffer)-self.index)
            return self.buffer[self.index+start:self.index+stop:stride]
        return self.buffer[self.index + i]

    def __setitem__(self,i,value):
        if isinstance(i,slice):
            start,stop,stride = i.indices(len(self.buffer)-self.index)
            self.buffer[self.index + start:self.index+stop:stride] = value
        else:
            self.buffer[self.index + i] = value

class Quad(object):
    def __init__(self,source,vertex = None,tc = None,colour_info = None,index = None):
        if index == None:
            self.index = source.next()
        else:
            self.index = index
        self.source = source
        self.vertex = QuadVertex(self.index,source.vertex_data)
        self.tc     = QuadVertex(self.index,source.tc_data)
        self.colour = QuadVertex(self.index,source.colour_data)
        if vertex != None:
            self.vertex[0:4] = vertex
        if tc != None:
            self.tc[0:4] = tc
        self.old_vertices = None
        self.deleted = False

    def Delete(self):
        self.source.RemoveQuad(self.index)
        self.deleted = True

    def Disable(self):
        #It still gets drawn, but just in a single dot in a corner.
        #not very efficient!
        #don't disable again if already disabled
        if self.deleted:
            return
        if self.old_vertices == None:
            self.old_vertices = numpy.copy(self.vertex[0:4])
            for i in xrange(4):
                self.vertex[i] = (0,0,0)

    def Enable(self):
        if self.deleted:
            return
        if self.old_vertices != None:
            for i in xrange(4):
                self.vertex[i] = self.old_vertices[i]
            self.old_vertices = None

    def SetVertices(self,bl,tr,z):
        if self.deleted:
            return
        setvertices(self.vertex,bl,tr,z)
        if self.old_vertices != None:
            self.old_vertices = numpy.copy(self.vertex[0:4])
            for i in xrange(4):
                self.vertex[i] = (0,0,0)
    
    def SetColour(self,colour):
        if self.deleted:
            return
        setcolour(self.colour,colour)

    def SetColours(self,colours):
        if self.deleted:
            return
        for current,target in zip(self.colour,colours):
            for i in xrange(4):
                current[i] = target[i]

    def SetTextureCoordinates(self,tc):
        self.tc[0:4] = tc

def setvertices(vertex,bl,tr,z):
    vertex[0] = (bl.x,bl.y,z)
    vertex[1] = (bl.x,tr.y,z)
    vertex[2] = (tr.x,tr.y,z)
    vertex[3] = (tr.x,bl.y,z)

def setcolour(colour,value):
    for i in xrange(4):
        for j in xrange(4):
            colour[i][j] = value[j]


class Point(object):
    def __init__(self,x = None, y = None):
        self.x = x
        self.y = y
        self.iter_pos = 0
        
    def __add__(self,other_point):
        return Point(self.x + other_point.x, self.y + other_point.y)

    def __sub__(self,other_point):
        return Point(self.x - other_point.x, self.y - other_point.y)

    def __mul__(self,other_point):
        if isinstance(other_point,Point):
            return Point(self.x*other_point.x,self.y*other_point.y)
        else:
            return Point(self.x*other_point,self.y*other_point)

    def __div__(self,factor):
        try:
            return Point(self.x/factor.x,self.y/factor.y)
        except AttributeError:
            return Point(self.x/factor,self.y/factor)

    def __getitem__(self,index):
        return (self.x,self.y)[index]

    def __setitem__(self,index,value):
        setattr(self,('x','y')[index],value)

    def __iter__(self):
        return self

    def __repr__(self):
        return str(self)

    def __str__(self):
        return '(%.2f,%.2f)' % (self.x,self.y)

    def __cmp__(self,other):
        try:
            #a = cmp(abs(self.x*self.y),abs(other.x*other.y))
            #if a != 0:
            #    return a
            a = cmp(self.x,other.x)
            if a != 0:
                return a
            return cmp(self.y,other.y)
        except AttributeError:
            return -1#It's not equal if it's not a point

    def __hash__(self):
        return (int(self.x) << 16 | int(self.y))

    def to_float(self):
        return Point(float(self.x),float(self.y))

    def to_int(self):
        return Point(int(self.x),int(self.y))

    def next(self):
        try:
            out = (self.x,self.y)[self.iter_pos]
            self.iter_pos += 1
        except IndexError:
            self.iter_pos = 0
            raise StopIteration
        return out

    def length(self):
        a = math.sqrt(self.x**2 + self.y**2)
        try:
            b = math.sqrt((gamedata.map_size[0]-self.x)**2+self.y**2)
        except AttributeError:
            #Maybe gamedata isn't set up yet.
            return a
        return min(a,b)

    def DistanceHeuristic(self,other):
        #return (other-self).diaglength()
        diff = other-self
        return (abs(diff.x)+abs(diff.y))
        #return diff.x**2 + diff.y**2

    def diaglength(self):
        return max(abs(self.x),abs(self.y))


class Path(object):
    direction_names = {Point( 1, 0):'right'    ,
                       Point( 1, 1):'up_right' ,
                       Point( 0, 1):'up'       ,
                       Point(-1, 1):'up_left'  ,
                       Point(-1, 0):'left'     ,
                       Point(-1,-1):'down_left',
                       Point( 0,-1):'down'     ,
                       Point( 1,-1):'down_right'}
    def __init__(self,start,tc,width):
        self.path = [start]
        node = start.parent
        while node:
            self.path.insert(0,node)
            node = node.parent

        self.steps = [WrapDistance(self.path[i+1],self.path[i],width) for i in xrange(len(self.path)-1)]
        self.quads = []
        self.tc    = tc
        self.width = width
        self.cost  = start.g

    def Enable(self):
        if self.quads:
            for q in self.quads:
                q.Enable()
        else:
            self.quads = []

            for pos,direction in zip(self.path,self.steps):
                q = Quad(gamedata.quad_buffer,tc = self.tc['path_'+self.direction_names[direction]])
                bl = pos + (direction*0.5)
                tr = bl + Point(1,1)
                q.SetVertices(WorldCoords(bl),
                              WorldCoords(tr),
                              10)
                self.quads.append(q)
    def Disable(self):
        for q in self.quads:
            q.Disable()

    def Delete(self):
        for q in self.quads:
            q.Delete()
        self.quads = []
    def Segments(self):
        steps = [self.path[i+1]-self.path[i] for i in xrange(len(self.path)-1)]
        last = None
        length = 1
        while steps:
            a = steps.pop(0)
            if not last:
                last = a
                continue
            if a == last:
                length += 1
            else:
                yield last,length
                last = a
                length = 1
        if length:
            yield last,length

def GridCoordsX(point):
    return (float(point.x)/gamedata.tile_dimensions.x)

def GridCoordsY(point):
    return (float(point.y)/gamedata.tile_dimensions.y)

def GridCoords(point):
    return Point(GridCoordsX(point),GridCoordsY(point))

def WorldCoords(point):
    return point*gamedata.tile_dimensions

def WrapDistance(a,b,width):
    """
    Distance from b to a, including the possibility of going down from a low number
    and wrapping to a high number. For example:
    A = (31,2)
    B = ( 1,1)
    
    WrapDistance will return (-2,1), for a width of 32
    """

    offset = a - b
    if offset.x < 0:
        other = (offset.x + width )
    else:
        other = (offset.x - width )
    if abs(other) < abs(offset.x):
        offset.x = other
    return offset

def fbisect_left(a, x, lo=0, hi=None):
    """Return the index where to insert item x in list a, assuming a is sorted.

    The return value i is such that all e in a[:i] have e < x, and all e in
    a[i:] have e >= x.  So if x already appears in the list, a.insert(x) will
    insert just before the leftmost x already there.

    Optional args lo (default 0) and hi (default len(a)) bound the
    slice of a to be searched.
    """

    if lo < 0:
        raise ValueError('lo must be non-negative')
    if hi is None:
        hi = len(a)
    while lo < hi:
        mid = (lo+hi)//2
        if a[mid].f < x.f: lo = mid+1
        else: hi = mid
    return lo

def Brensenham(a,b,width):
    """Brensenham line algorithm"""
    x,y = a.to_int()
    x2,y2 = b.to_int()
    steep = 0
    coords = []
    diff = WrapDistance(b,a,width)
    dx = abs(diff.x)
    if (diff.x) > 0: 
        sx = 1
    else: 
        sx = -1
    dy = abs(y2 - y)
    if (y2 - y) > 0: 
        sy = 1
    else: 
        sy = -1
    if dy > dx:
        steep = 1
        x,y = y,x
        dx,dy = dy,dx
        sx,sy = sy,sx
    d = (2 * dy) - dx
    for i in range(0,dx):
        if steep: 
            coords.append(Point(y,x))
        else: 
            coords.append(Point(x,y))
        while d >= 0:
            y = y + sy
            d = d - (2 * dx)
        x = x + sx
        d = d + (2 * dy)
    coords.append(Point(x2,y2))
    return coords

class ExtraArgs(object):
    """
    A noddy decorator for adding arguments to a function call
    """
    def __init__(self,func,*args):
        self.func  = func
        self.extra = args

    def __call__(self, *args):
        return self.func(*(args + self.extra))

def Spiral(length):
    """A tile-based spiral generator, starts with (0,0) and goes up and around"""
    n = 0
    pos = Point(0,0)
    yield pos
    side = 0
    count = 0
    directions = [Point(0,1),Point(1,0),Point(0,-1),Point(-1,0)]
    while count < length:
        direction = directions[side % 4]
        if (side%2) == 0:
            n += 1
        for i in xrange(n):
            pos = pos + direction
            yield pos
            count += 1
            if count >= length:
                return
            
        side += 1
        
