import pygame,string
from pygame.locals import *
from OpenGL.GL.framebufferobjects import *
from OpenGL.GL import *
from OpenGL.GLU import *
import utils,numpy
from utils import Point

gamedata = None

class Texture(object):
    def __init__(self,filename):
        with open(filename,'rb') as f:
            self.textureSurface = pygame.image.load(f)
        self.textureData = pygame.image.tostring(self.textureSurface, 'RGBA', 1)

        self.width  = self.textureSurface.get_width()
        self.height = self.textureSurface.get_height()

        self.texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.width, self.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, self.textureData)

#texture atlas code taken from 
#http://omnisaurusgames.com/2011/06/texture-atlas-generation-using-python/
#I'm assuming it's open source!

class SubImage(object):
    def __init__(self,pos,size):
        self.pos  = pos
        self.size = size


class TextureAtlas(object):
    def __init__(self,image_filename,data_filename):
        self.texture = Texture(image_filename)
        self.subimages = {}
        with open(data_filename,'rb') as f:
            for line in f:
                subimage_name,\
                image_name   ,\
                x            ,\
                y            ,\
                w            ,\
                h            = line.strip().split(':')
                #print image_name,image_filename
                assert(image_name) == image_filename
                w = int(w)
                h = int(h)
                self.subimages[subimage_name] = SubImage(Point(float(x)/self.texture.width,float(y)/self.texture.height),(Point(w,h)))

    def Subimage(self,name):
        return self.subimages[name]

    def TransformCoord(self,subimage,value):
        value[0] = subimage.pos.x + value[0]*(float(subimage.size.x)/self.texture.width)
        value[1] = subimage.pos.y + value[1]*(float(subimage.size.y)/self.texture.height)
    
    def TransformCoords(self,subimage,tc):
        subimage = self.subimages[subimage]
        #print subimage.pos
        for i in xrange(len(tc)):
            self.TransformCoord(subimage,tc[i])

class TextObject(object):
    def __init__(self,text,textmanager):
        self.text = text
        self.quads = [textmanager.Letter(char) for char in self.text]
        self.textmanager = textmanager
        #that sets the texture coords for us

    def Position(self,pos):
        #set up the position for the characters
        self.pos = pos
        for (i,quad) in enumerate(self.quads):
            utils.setvertices(quad.vertex,
                              pos+Point(self.textmanager.font_width*i,0),
                              pos+Point((self.textmanager.font_width*(i+1)),
                                        self.textmanager.font_height),
                              utils.text_level)
            #utils.setvertices(quad.vertex,
            #                  Point(0,0),
            #                  gamedata.screen,
            #                  utils.text_level)
            

    def Delete(self):
        for quad in self.quads:
            quad.Delete()

    def SetText(self,text):
        self.Delete()
        self.text = text
        print self.text
        self.quads = [self.textmanager.Letter(char) for char in self.text]
        self.Position(self.pos)
            

class TextManager(object):
    def __init__(self):
        font = pygame.font.SysFont ("monospace", 48)
        #go with 8 rows of 16 characters
        widths = {}
        data = []
        print 'ff'
        for i in xrange(8):
            text = ''.join([chr(j) if (chr(j) in string.printable and chr(j) not in '\r\n\t\x0b\x0c') else ' ' for j in xrange(i*16,(i+1)*16)])
            textSurface = font.render(text, True, (255,255,255,255))
            #textSurface = font.render('a', True, (255,255,255,255), (0,0,0,255))
            data.append(pygame.image.tostring(textSurface, 'RGBA', 1))
            import hashlib
            print hashlib.md5(data[-1]).hexdigest()
            
            widths[textSurface.get_width()] = True

        assert(len(widths.keys()) == 1)
        #assert(len(data) == 8)

        self.textData = ''.join(data)
        
        self.font_width  = widths.keys()[0]/16
        self.font_height = 55
        self.width = widths.keys()[0]
        self.height = self.font_height*8

        #self.width  = self.textureSurface.get_width()
        #self.height = self.textureSurface.get_height()
        print self.width,self.height
        #self.textData = pygame.image.tostring(self.textureSurface, 'RGBA', 1)
        self.texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.width, self.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, self.textData)

        self.quads = utils.QuadBuffer(131072) #these are reclaimed when out of use so this means 131072 concurrent chars

    def Letter(self,char):
        quad = utils.Quad(self.quads)
        x = (ord(char)%16)
        y = 1+(ord(char)/16)
        top_left_x = float(x)/16
        top_left_y = float(y)/8
        bottom_right_x = top_left_x + float(1)/16
        bottom_right_y = top_left_y - float(1)/8
        #top_left_x = 0
        #top_left_y = 1
        #bottom_right_x = 1
        #bottom_right_y = 0
        
        quad.tc[0:4] = tc = numpy.array(((top_left_x,bottom_right_y),(top_left_x,top_left_y),(bottom_right_x,top_left_y),(bottom_right_x,bottom_right_y)),numpy.float32)
        return quad
    

    def Draw(self):
        glBindTexture(GL_TEXTURE_2D,self.texture)
        glLoadIdentity()
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        glVertexPointerf(self.quads.vertex_data)
        glTexCoordPointerf(self.quads.tc_data)

        glDrawElements(GL_QUADS,self.quads.current_size,GL_UNSIGNED_INT,self.quads.indices)
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
