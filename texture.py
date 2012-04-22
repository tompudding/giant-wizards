import pygame,string
from pygame.locals import *
from OpenGL.GL.framebufferobjects import *
from OpenGL.GL import *
from OpenGL.GLU import *
import utils,numpy
from utils import Point

gamedata = None
cache = {}

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
        for i in xrange(len(tc)):
            self.TransformCoord(subimage,tc[i])

class TextObject(object):
    def __init__(self,text,textmanager,static = True):
        self.text = text
        self.quads = [textmanager.Letter(char,static) for char in self.text]
        self.textmanager = textmanager
        self.static = static
        #that sets the texture coords for us

    def Position(self,pos,scale):
        #set up the position for the characters
        self.pos = pos
        self.scale = scale
        for (i,quad) in enumerate(self.quads):
            utils.setvertices(quad.vertex,
                              pos+Point(self.textmanager.font_width*i*scale,0),
                              pos+Point((self.textmanager.font_width*(i+1)*scale),
                                        self.textmanager.font_height*scale),
                              utils.text_level)
            #utils.setvertices(quad.vertex,
            #                  Point(0,0),
            #                  gamedata.screen,
            #                  utils.text_level)
        self.top_right = pos+Point((self.textmanager.font_width*len(self.quads)*scale),self.textmanager.font_height*scale)
            

    def Delete(self):
        for quad in self.quads:
            quad.Delete()

    def SetText(self,text):
        self.Delete()
        self.text = text
        self.quads = [self.textmanager.Letter(char,self.static) for char in self.text]
        self.Position(self.pos,self.scale)

    def Disable(self):
        for q in self.quads:
            q.Disable()

    def Enable(self):
        for q in self.quads:
            q.Enable()
            

class TextManager(object):
    def __init__(self):
        self.texture = Texture('font.png')
        self.quads = utils.QuadBuffer(131072) #these are reclaimed when out of use so this means 131072 concurrent chars
        self.font_width = 38
        self.font_height = 74

    def Letter(self,char,static):
        quad = utils.Quad(self.quads if static else gamedata.nonstatic_text_buffer)
        x = (ord(char)%16)
        y = 7-(ord(char)/16)
        left   = float(x*self.font_width)/self.texture.width
        top    = float(432+(y+1)*self.font_height)/self.texture.height
        right  = float((x+1)*self.font_width)/self.texture.width
        bottom = float(432+(y)*self.font_height)/self.texture.height
        #top_left_x = 0
        #top_left_y = 1
        #bottom_right_x = 1
        #bottom_right_y = 0
        
        quad.tc[0:4]  = numpy.array(((left,bottom),(left,top),(right,top),(right,bottom)),numpy.float32)
        return quad
    

    def Draw(self):
        glBindTexture(GL_TEXTURE_2D,self.texture.texture)
        glLoadIdentity()
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)
        glVertexPointerf(self.quads.vertex_data)
        glTexCoordPointerf(self.quads.tc_data)
        glColorPointer(4,GL_FLOAT,0,self.quads.colour_data)
        glDrawElements(GL_QUADS,self.quads.current_size,GL_UNSIGNED_INT,self.quads.indices)
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)

    def Purge(self):
        self.quads.truncate(0)


class UIElement(object):
    def __init__(self,pos,tr):
        self.bottom_left = pos
        self.top_right = tr
        self.size = tr - pos

    def __contains__(self,pos):
        if pos.x < self.bottom_left.x or pos.x > self.top_right.x:
            return False
        if pos.y >= self.bottom_left.y and pos.y <= self.top_right.y:
            return True
        return False

    def Hover(self):
        pass
    def EndHover(self):
        pass

    def __hash__(self):
        return hash((self.bottom_left,self.top_right))

class BoxUI(UIElement):
    def __init__(self,pos,tr,colour):
        super(BoxUI,self).__init__(pos,tr)
        self.quad = utils.Quad(gamedata.ui_buffer)
        utils.setcolour(self.quad.colour,colour)
        utils.setvertices(self.quad.vertex,
                          self.bottom_left,
                          self.top_right,
                          utils.ui_level)

    def Delete(self):
        self.quad.Delete()
        
    def Disable(self):
        self.quad.Disable()

    def Enable(self):
        self.quad.Enable()

    def OnClick(self,pos,button):
        pass

class TextButtonUI(UIElement):
    def __init__(self,text,pos,size=0.5,callback = None,line_width=2):
        self.text = TextObject(text,gamedata.text_manager)
        self.text.Position(pos,size)
        self.pos = pos
        self.callback = callback
        super(TextButtonUI,self).__init__(pos,self.text.top_right)
        self.hover_quads = [utils.Quad(gamedata.ui_buffer) for i in xrange(4)]
        self.line_width = line_width
        self.SetVertices()
        self.hovered = False
        self.selected = False
        for i in xrange(4):
            self.hover_quads[i].Disable()

    def SetVertices(self):
        for i in xrange(4):
            utils.setcolour(self.hover_quads[i].colour,(1,0,0,1))
        
        #top bar
        utils.setvertices(self.hover_quads[0].vertex,
                          Point(self.pos.x,self.top_right.y-self.line_width),
                          self.top_right,
                          utils.ui_level+1)
        #right bar
        utils.setvertices(self.hover_quads[1].vertex,
                          Point(self.top_right.x-self.line_width,self.pos.y),
                          self.top_right,
                          utils.ui_level+1)
        
        #bottom bar
        utils.setvertices(self.hover_quads[2].vertex,
                          self.pos,
                          Point(self.top_right.x,self.pos.y+self.line_width),
                          utils.ui_level+1)

        #left bar
        utils.setvertices(self.hover_quads[3].vertex,
                          self.pos,
                          Point(self.pos.x+self.line_width,self.top_right.y),
                          utils.ui_level+1)
                          
    def Delete(self):
        for quad in self.hover_quads:
            quad.Delete()
        self.text.Delete()
        

    def SetText(self,newtext):
        self.text.SetText(newtext)
        self.top_right = self.text.top_right
        self.SetVertices()

    def Hover(self):
        self.hovered = True
        for i in xrange(4):
            self.hover_quads[i].Enable()

    def EndHover(self):
        self.hovered = False
        if not self.hovered and not self.selected:
            for i in xrange(4):
                self.hover_quads[i].Disable()

    def Selected(self):
        self.selected = True
        for i in xrange(4):
            utils.setcolour(self.hover_quads[i].colour,(0,0,1,1))
            self.hover_quads[i].Enable()

    def Unselected(self):
        self.selected = False
        for i in xrange(4):
            utils.setcolour(self.hover_quads[i].colour,(1,0,0,1))
        if not self.hovered and not self.selected:
            for i in xrange(4):
                self.hover_quads[i].Disable()

    def Enable(self):
        if self.hovered:
            Hover()
        self.text.Enable()

    def Disable(self):
        self.text.Disable()
        for i in xrange(4):
            self.hover_quads[i].Disable()

    def OnClick(self,pos,button):
        if self.callback != None and button == 1:
            self.callback(pos)
            
        
        
