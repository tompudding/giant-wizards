from OpenGL.GL.framebufferobjects import *
from OpenGL.GL import *
from OpenGL.GLU import *
import utils,gamedata
from utils import Point
import texture

class AbsoluteBounds(object):
    """
    Store the bottom left, top right and size data for a rectangle in screen coordinates. We could 
    ask the parent and compute this each time, but it will be more efficient if we store it and 
    use it directly, and rely on the parent to update its children when things change
    """
    def __init__(self):
        self.bottom_left = None
        self.top_right   = None
        self.size        = None

class UIElement(object):
    def __init__(self,parent,pos,tr):
        self.parent   = parent
        self.absolute = AbsoluteBounds()
        self.on       = True
        self.SetBounds(parent,pos,tr)
        self.children = UIElementList()
        if self.parent != None:
            self.parent.AddChild(self)

    def SetBounds(self,pos,tr):
        if self.parent == None:
            self.absolute.bottom_left = pos
            self.absolute.top_right   = tr
            self.absolute.size        = tr - pos
        else:
            self.absolute.bottom_left = parent.GetAbsolute(pos)
            self.absolute.top_right   = parent.GetAbsolute(tr)
            self.absolute.size        = self.absolute.top_right - self.absolute.bottom_left
        self.bottom_left          = pos
        self.top_right            = tr
        self.size                 = tr - pos

    def UpdatePosition(self):
        self.SetBounds(self,self.bottom_left,self.top_right)
        for child_element in self.children:
            child_element.UpdatePosition()

    def GetAbsolute(self,p):
        return self.absolute.bottom_left + (self.absolute.size*p)

    def AddChild(self,element):
        self.children.Append(element)

    def __contains__(self,pos):
        if pos.x < self.absolute.bottom_left.x or pos.x > self.absolute.top_right.x:
            return False
        if pos.y >= self.absolute.bottom_left.y and pos.y <= self.absolute.top_right.y:
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
        for child in self.children:
            child.MakeSelectable()

    def MakeUnselectable(self):
        self.on = False
        for child in self.children:
            child.MakeUnselectable()

    def __hash__(self):
        return hash((self.absolute.bottom_left,self.absolute.top_right))
    

class Box(UIElement):
    def __init__(self,parent,pos,tr,colour):
        super(Box,self).__init__(parent,pos,tr)
        self.quad = utils.Quad(gamedata.ui_buffer)
        self.colour = colour
        self.unselectable_colour = tuple(component*0.6 for component in self.colour)
        self.quad.SetColour(self.colour)
        self.quad.SetVertices(self.bottom_left,
                              self.top_right,
                              utils.ui_level)

    def Delete(self):
        self.quad.Delete()
        for child in self.children:
            child.Delete()
        
    def Disable(self):
        self.quad.Disable()
        for child in self.children:
            child.Disable()

    def Enable(self):
        self.quad.Enable()
        for child in self.children:
            child.Enable()

    def MakeSelectable(self):
        super(Box,self).MakeSelectable()
        self.quad.SetColour(self.colour)

    def MakeUnselectable(self):
        super(Box,self).MakeUnselectable()
        self.quad.SetColour(self.unselectable_colour)

    def OnClick(self,pos,button):
        pass


class TextBox(UIElement):
    """ A Screen-relative text box wraps text to a given size """
    def __init__(self,parent,bl,tr,text,textmanager):
        self.parent      = parent
        super(TextBox,self).__init__(parent,bl,tr)
        self.text        = text
        self.text_type   = texture.TextTypes.SCREEN_RELATIVE
        self.quads       = [textmanager.Letter(char,self.text_type) for char in self.text]
        self.textmanager = textmanager
        #that sets the texture coords for us

    def Position(self,pos,scale,colour = None):
        #set up the position for the characters
        self.pos = pos
        self.absolute.bottom_left = parent.GetAbsolute(pos)
        self.scale = scale
        row_height = (float(texture.screen_font_height*self.scale*global_scale)/self.absolute.size.y)
        #Do this without any kerning or padding for now, and see what it looks like
        cursor = Point(0,1 - row_height)
        for (i,quad) in enumerate(self.quads):
            letter_size = Point(quad.width *self.scale*global_scale/self.size.x,
                                quad.height*self.scale*global_scale/self.size.y)
            if self.pos + cursor.x + letter_size.x > 1:
                cursor.x = 0
                cursor.y -= row_height
            target_bl = self.pos+cursor
            target_tr = target_bl + letter_size
                
            if target_bl.y < 0:
                #We've gone too far, now more text to write!
                break
            absolute_bl = parent.GetAbsolute(target_bl)
            absolute_tr = parent.GetAbsolute(target_tr)
            quad.SetVertices(absolute_bl,
                             absolute_tr,
                             TextTypes.LEVELS[self.text_type])
            if colour:
                quad.SetColour(colour)
            cursor.x += letter.x
        height = max([q.height for q in self.quads])
        
    def Delete(self):
        for quad in self.quads:
            quad.Delete()

    def SetText(self,text,colour = None):
        self.Delete()
        self.text = text
        self.quads = [self.textmanager.Letter(char,self.text_type) for char in self.text]
        self.Position(self.pos,self.scale,colour)

    def Disable(self):
        for q in self.quads:
            q.Disable()
        

    def Enable(self):
        for q in self.quads:
            q.Enable()
            


class TextBox(UIElement):
    def __init__(self,bl,tr,text,fontsize):
        super(TextBox,self).__init__(bl,tr)

class TextBoxButton(UIElement):
    def __init__(self,parent,text,pos,tr,size=0.5,callback = None,line_width=2):
        super(TextBoxButton,self).__init__(parent,pos,tr,size)
        self.text.Position(pos,size)
        self.size = self.text.top_right - pos
        self.boxextra = 0.2
        self.pos = pos - (Point(self.size.y,self.size.y)*self.boxextra)
        self.textsize = size
        self.callback = callback
        super(TextButton,self).__init__(parent,pos,self.text.top_right + (Point(self.size.y,self.size.y)*self.boxextra))
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
        self.text.Position(pos,self.textsize)
        self.size = self.text.top_right - pos
        self.pos = pos - (Point(self.size.y,self.size.y)*self.boxextra)
        self.SetBounds(self.pos,self.text.top_right + (Point(self.size.y,self.size.y)*self.boxextra))
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
            
        
class TexturedButton(TextButton):
    def __init__(self,text,pos,size=0.5,callback = None,line_width=2):
        self.text = texture.TextObject(text,gamedata.text_manager)
        self.text.Position(pos,size)
        self.pos = pos
        self.callback = callback
        super(TextButton,self).__init__(pos,self.text.top_right)
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
        self.itemheight = 0.04*gamedata.screen.y
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
        self.ui_box   = Box(bl,
                              tr,
                              colour)
        self.buttons  = {}
        self.elements = [self.ui_box]

    def AddButton(self,text,pos,callback,size = None):
        #FIXME: Sort out the arguments here, there's really no need to duplicate code I'm sure
        if None == size:
            button = TextButton(text,self.bl+(self.size*pos),callback=callback)
        else:
            button = TextButton(text,self.bl+(self.size*pos),size=size,callback=callback)
        button.level = 2
        self.buttons[text] = button
        self.elements.append(button)

    def Register(self,tiles,level):
        for element in self.elements:
            tiles.RegisterUIElement(element,level+0.1 if isinstance(element,TextButton) else level)
        
    def MakeSelectable(self):
        for element in self.elements:
            element.MakeSelectable()

    def MakeUnselectable(self):
        for element in self.elements:
            element.MakeUnselectable()
