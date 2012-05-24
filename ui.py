import pygame,string
from pygame.locals import *
from OpenGL.GL.framebufferobjects import *
from OpenGL.GL import *
from OpenGL.GLU import *
import utils,numpy
from utils import Point
import texture

class UIElement(object):
    def __init__(self,pos,tr):
        self.bottom_left = pos
        self.top_right = tr
        self.size = tr - pos
        self.on = True

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

    def Selectable(self):
        return self.on

    def MakeSelectable(self):
        self.on = True

    def MakeUnselectable(self):
        self.on = False

    def __hash__(self):
        return hash((self.bottom_left,self.top_right))

class BoxUI(UIElement):
    def __init__(self,pos,tr,colour):
        super(BoxUI,self).__init__(pos,tr)
        self.quad = utils.Quad(gamedata.ui_buffer)
        self.colour = colour
        self.unselectable_colour = tuple(component*0.6 for component in self.colour)
        self.quad.SetColour(self.colour)
        self.quad.SetVertices(self.bottom_left,
                              self.top_right,
                              utils.ui_level)

    def Delete(self):
        self.quad.Delete()
        
    def Disable(self):
        self.quad.Disable()

    def Enable(self):
        self.quad.Enable()

    def MakeSelectable(self):
        super(BoxUI,self).MakeSelectable()
        self.quad.SetColour(self.colour)

    def MakeUnselectable(self):
        super(BoxUI,self).MakeUnselectable()
        self.quad.SetColour(self.unselectable_colour)

    def OnClick(self,pos,button):
        pass

class TextButtonUI(UIElement):
    def __init__(self,text,pos,size=0.5,callback = None,line_width=2):
        self.text = texture.TextObject(text,gamedata.text_manager)
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
            self.hover_quads[i].SetColour((1,0,0,1))
        
        #top bar
        self.hover_quads[0].SetVertices(Point(self.pos.x,self.top_right.y-self.line_width),
                                        self.top_right,
                                        utils.ui_level+1)
        #right bar
        self.hover_quads[1].SetVertices(Point(self.top_right.x-self.line_width,self.pos.y),
                                        self.top_right,
                                        utils.ui_level+1)
        
        #bottom bar
        self.hover_quads[2].SetVertices(self.pos,
                                        Point(self.top_right.x,self.pos.y+self.line_width),
                                        utils.ui_level+1)

        #left bar
        self.hover_quads[3].SetVertices(self.pos,
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

    def GetText(self):
        return self.text.text

    def Hover(self):
        #print pygame.mouse.get_cursor()
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
            self.hover_quads[i].SetColour((0,0,1,1))
            self.hover_quads[i].Enable()

    def Unselected(self):
        self.selected = False
        for i in xrange(4):
            self.hover_quads[i].SetColour((1,0,0,1))
        if not self.hovered and not self.selected:
            for i in xrange(4):
                self.hover_quads[i].Disable()

    def Enable(self):
        if self.hovered:
            self.Hover()
        self.text.Enable()

    def Disable(self):
        self.text.Disable()
        for i in xrange(4):
            self.hover_quads[i].Disable()

    def OnClick(self,pos,button):
        if self.callback != None and button == 1:
            self.callback(pos)
            
        
class TexturedButton(TextButtonUI):
    def __init__(self,text,pos,size=0.5,callback = None,line_width=2):
        self.text = texture.TextObject(text,gamedata.text_manager)
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

        
