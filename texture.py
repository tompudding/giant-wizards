import pygame,string
from pygame.locals import *
from OpenGL.GL.framebufferobjects import *
from OpenGL.GL import *
from OpenGL.GLU import *
from utils import Point

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

class TextManager(object):
    def __init__(self):
        font = pygame.font.SysFont ("monospace", 64)
        #go with 8 rows of 16 characters
        for i in xrange(8):
            textSurface = font.render(''.join([chr(i) if chr(i) in string.printable else ' ' for i in xrange(i*16,(i+1)*16)]), True, (255,255,255,255), (0,0,0,255))
            print textSurface.get_width(),textSurface.get_height()
        raise SystemExit
        textData = pygame.image.tostring(textSurface, "RGBA", True)
        self.width  = self.textureSurface.get_width()
        self.height = self.textureSurface.get_height()

        self.texture = glGenTextures(1)
