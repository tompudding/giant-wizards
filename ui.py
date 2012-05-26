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
        self.SetBounds(pos,tr)
        self.on = True

    def SetBounds(self,pos,tr):
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
        self.textsize = size
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
        
    def SetPos(self,pos):
        self.pos = pos
        self.text.Position(self.pos,self.textsize)
        self.SetBounds(self.pos,self.text.top_right)
        self.SetVertices()

    def SetText(self,newtext):
        self.text.SetText(newtext)
        self.top_right = self.text.top_right
        self.SetVertices()

    def GetText(self):
        return self.text.text

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

class ButtonList(object):
    """
    UI Element for showing a list of buttons. Right now it's very basic, does not actually 
    inherit from UIElement(as it doesn't accept clicks itself), and doesn't really do anything

    Just a placeholder really in case we need scrollbars at some point
    """
    
    def __init__(self,pos,l = []):
        self.buttons  = []
        self.top_left = pos
        self.itemheight = 0.025*gamedata.screen.y
        for item in l:
            self.AddButton(l)

    def AddButton(self,button):
        button.text.SetPos(self.top_left - Point(0,self.itemheight*len(self.buttons)))
        self.buttons.append(button)

    def Enable(self,tiles):
        for button in self.buttons:
            button.Enable()
            tiles.RegisterUIElement(button.text,1)

    def Disable(self,tiles):
        for button in self.buttons:
            button.Disable()
            tiles.RemoveUIElement(button.text)

    def __getitem__(self,index):
        return self.buttons[index]


class ControlBox(UIElement):
    def __init__(self,bl,tr,colour):
        self.bl       = bl
        self.tr       = tr
        self.size     = tr-bl
        self.colour   = colour
        self.ui_box   = BoxUI(bl,
                              tr,
                              colour)
        self.buttons  = {}
        self.elements = [self.ui_box]

    def AddButton(self,text,pos,callback,size = None):
        #FIXME: Sort out the arguments here, there's really no need to duplicate code I'm sure
        if None == size:
            button = TextButtonUI(text,self.bl+(self.size*pos),callback=callback)
        else:
            button = TextButtonUI(text,self.bl+(self.size*pos),size=size,callback=callback)
        button.level = 2
        self.buttons[text] = button
        self.elements.append(button)

    def Register(self,tiles,level):
        for element in self.elements:
            tiles.RegisterUIElement(element,level+0.1 if isinstance(element,TextButtonUI) else level)
        
    def MakeSelectable(self):
        for element in self.elements:
            element.MakeSelectable()

    def MakeUnselectable(self):
        for element in self.elements:
            element.MakeUnselectable()


    
