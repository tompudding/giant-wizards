from OpenGL.GL import *
import pygame,math,numpy,itertools

gamedata = None

class QuadBuffer(object):
    def __init__(self,size):
        self.vertex_data  = numpy.zeros((size*4,3),numpy.float32)
        self.tc_data      = numpy.zeros((size*4,2),numpy.float32)
        self.colour_data = numpy.ones((size*4,4),numpy.float32) #RGBA default is white opaque
        self.indices      = numpy.zeros(size*4,numpy.uint32)  #de
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
        self.vertex = QuadVertex(self.index,source.vertex_data)
        self.tc     = QuadVertex(self.index,source.tc_data)
        self.colour = QuadVertex(self.index,source.colour_data)
        if vertex != None:
            self.vertex[0:4] = vertex
        if tc != None:
            self.tc[0:4] = tc

def setvertices(vertex,bl,tr,z):
    vertex[0] = (bl.x,bl.y,z)
    vertex[1] = (bl.x,tr.y,z)
    vertex[2] = (tr.x,tr.y,z)
    vertex[3] = (tr.x,bl.y,z)

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
        return '(%2.f,%.2f)' % (self.x,self.y)

    def __cmp__(self,other):
        try:
            a = cmp(self.x,other.x)
            if a == 0:
                return cmp(self.y,other.y)
            else:
                return a

        except AttributeError:
            return -1#It's not equal if it's not a point

    def __hash__(self):
        return (self.x << 16 | self.y)

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
        return math.sqrt(self.x**2 + self.y**2)

def GridCoordsX(point):
    return (float(point.x)/gamedata.tile_dimensions.x)

def GridCoordsY(point):
    return (float(point.y)/gamedata.tile_dimensions.y)

def GridCoords(point):
    return Point(GridCoordsX(point),GridCoordsY(point))

def WorldCoords(point):
    return point*gamedata.tile_dimensions