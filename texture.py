import pygame
from pygame.locals import *
from OpenGL.GL.framebufferobjects import *
from OpenGL.GL import *
from OpenGL.GLU import *
import utils,gamedata
from utils import Point

cache = {}
global_scale = 0.5

class Texture(object):
    def __init__(self,filename):
        if filename not in cache:
            with open(filename,'rb') as f:
                self.textureSurface = pygame.image.load(f)
            self.textureData = pygame.image.tostring(self.textureSurface, 'RGBA', 1)

            self.width  = self.textureSurface.get_width()
            self.height = self.textureSurface.get_height()

            self.texture = glGenTextures(1)
            cache[filename] = (self.texture,self.width,self.height)
            glBindTexture(GL_TEXTURE_2D, self.texture)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.width, self.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, self.textureData)
        else:
            self.texture,self.width,self.height = cache[filename]
            glBindTexture(GL_TEXTURE_2D, self.texture)
        

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
                #assert(image_name) == image_filename
                w = int(w)
                h = int(h)
                if subimage_name.startswith('font_'):
                    subimage_name = chr(int(subimage_name[5:7],16))
                    h -= 4
                self.subimages[subimage_name] = SubImage(Point(float(x)/self.texture.width,float(y)/self.texture.height),(Point(w,h)))

    def Subimage(self,name):
        return self.subimages[name]

    def TransformCoord(self,subimage,value):
        value[0] = subimage.pos.x + value[0]*(float(subimage.size.x)/self.texture.width)
        value[1] = subimage.pos.y + value[1]*(float(subimage.size.y)/self.texture.height)
    
    def TransformCoords(self,subimage,tc):
        subimage = self.subimages[subimage]
        for i in xrange(len(tc)):
            self.TransformCoord(subimage,tc[i])

    def TextureCoords(self,subimage):
        full_tc = [[0,0],[0,1],[1,1],[1,0]]
        self.TransformCoords(subimage,full_tc)
        return full_tc

class TextTypes:
    SCREEN_RELATIVE = 1
    GRID_RELATIVE   = 2
    MOUSE_RELATIVE  = 3
    LEVELS          = {SCREEN_RELATIVE : utils.text_level,
                       GRID_RELATIVE   : utils.grid_level + 0.1,
                       MOUSE_RELATIVE  : utils.text_level}                                   

class TextManager(object):
    def __init__(self):
        #self.atlas = TextureAtlas('droidsans.png','droidsans.txt')
        self.atlas = TextureAtlas('pixelmix.png','pixelmix.txt')
        self.font_height = max(subimage.size.y for subimage in self.atlas.subimages.values())
        self.quads = utils.QuadBuffer(131072) #these are reclaimed when out of use so this means 131072 concurrent chars
        TextTypes.BUFFER = {TextTypes.SCREEN_RELATIVE : self.quads,
                            TextTypes.GRID_RELATIVE   : gamedata.nonstatic_text_buffer,
                            TextTypes.MOUSE_RELATIVE  : gamedata.mouse_relative_buffer}


    def Letter(self,char,textType):
        quad = utils.Quad(TextTypes.BUFFER[textType])    
        quad.tc[0:4]  = self.atlas.TextureCoords(char)
        #this is a bit dodge, should get its own class if I want to store extra things in it
        quad.width,quad.height = self.atlas.Subimage(char).size
        return quad

    def GetSize(self,text,scale):
        """
        How big would the text be if drawn on a single row in the given size?
        """
        sizes = [self.atlas.Subimage(char).size*scale*global_scale for char in text]
        out = Point(sum(item.x for item in sizes),max(item.y for item in sizes))
        return out
    

    def Draw(self):
        glBindTexture(GL_TEXTURE_2D,self.atlas.texture.texture)
        glLoadIdentity()
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)
        glVertexPointerf(self.quads.vertex_data)
        glTexCoordPointerf(self.quads.tc_data)
        glColorPointer(4,GL_FLOAT,0,self.quads.colour_data)
        glDrawElements(GL_QUADS,self.quads.current_size,GL_UNSIGNED_INT,self.quads.indices)
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_COLOR_ARRAY)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)

    def Purge(self):
        self.quads.truncate(0)
