from OpenGL.GL.framebufferobjects import *
from OpenGL.GL import *
from OpenGL.GLU import *
import utils,gamedata
from utils import Point
import texture

#ToDo, update Box,ControlBox,ButtonList to use the new UIElement interface, then
#update all the rest of the code that uses them <sigh>

class UIElementList:
    """
    Very basic implementation of a list of UIElements that can be looked up by position.
    It's using an O(n) algorithm, and I'm sure I can do better once everything's working
    """
    def __init__(self):
        self.items = {}
        
    def Append(self,item):
        self.items[item] = item.level

    def Get(self,pos):
       #not very efficient
        match = [-1,None]
        for ui,height in self.uielements.iteritems():
            if pos in ui and ui.Selectable():
                if height > match[0]:
                    match = [height,ui]
        return match[1]
    
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
        self.SetBounds(pos,tr)
        self.children = []
        if self.parent != None:
            self.parent.AddChild(self)
            self.GetAbsoluteInParent = parent.GetAbsolute
            self.root                = parent.root
            self.level               = parent.level + 1

    def SetBounds(self,pos,tr):
        self.absolute.bottom_left = self.GetAbsoluteInParent(pos)
        self.absolute.top_right   = self.GetAbsoluteInParent(tr)
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

    def Disable(self):
        for child in self.children:
            child.Disable()

    def Enable(self):
        for q in self.children:
            child.Enable()

    def Delete(self):
        for child in self.children:
            child.Delete()

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

class RootElement(UIElement):
    """
    A Root Element has no parent. It represents the top level UI element, and thus its coords are
    screen coords. It handles dispatching mouse movements and events. All of its children and
    grand-children (and so on) can register with it (and only it) for handling mouse actions,
    and those actions get dispatched
    """
    def __init__(self,bl,tr):
        self.SetBounds(pos,tr)
        self.absolute            = AbsoluteBounds()
        self.on                  = True
        self.GetAbsoluteInParent = lambda x:x
        self.root                = self
        self.level               = 0
        self.hovered             = None
        self.children            = []
        self.active_children     = UIElementList()
        
    def RegisterUIElement(self,element):
        self.active_children[element] = element.level

    def RemoveUIElement(self,element):
        try:
            del self.uielements[element]
        except KeyError:
            pass

    def MouseMotion(self,pos,rel):
        hovered = self.active_children.Get(pos)
        if hovered is not self.hovered:
            if self.hovered != None:
                self.hovered.EndHover()
            self.hovered = hovered
            self.hovered.Hover()
        else:
            old_hovered = self.hovered_player
            if self.hovered != None:
                self.hovered.EndHover()
                self.hovered = None
        return hovered

    def MouseButtonUp(self,pos,button):
        if self.hovered:
            self.hovered.OnClick(pos,button)
    

class Box(UIElement):
    def __init__(self,parent,pos,tr,colour):
        super(Box,self).__init__(parent,pos,tr)
        self.quad = utils.Quad(gamedata.ui_buffer)
        self.colour = colour
        self.unselectable_colour = tuple(component*0.6 for component in self.colour)
        self.quad.SetColour(self.colour)
        self.quad.SetVertices(self.absolute.bottom_left,
                              self.absolute.top_right,
                              utils.ui_level)

    def UpdatePosition(self):
        super(Box,self).UpdatePosition()
        self.quad.SetVertices(self.absolute.bottom_left,
                              self.absolute.top_right,
                              utils.ui_level)

    def Delete(self):
        self.quad.Delete()
        
    def Disable(self):
        super(Box,self).Disable()
        self.quad.Disable()

    def Enable(self):
        super(Box,self).Enable()
        self.quad.Enable()

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
    def __init__(self,parent,bl,tr,text,scale,colour = None):
        super(TextBox,self).__init__(parent,bl,tr)
        self.text        = text
        self.scale       = scale
        self.colour      = colour
        self.text_type   = texture.TextTypes.SCREEN_RELATIVE
        self.quads       = [textmanager.Letter(char,self.text_type) for char in self.text]
        self.textmanager = gamedata.textmanager
        #that sets the texture coords for us
        self.Position(self.bottom_left,self.scale,self.colour)

    def Position(self,pos,scale,colour = None):
        """Draw the text at the given location and size. Maybe colour too"""
        #set up the position for the characters
        self.pos = pos
        self.absolute.bottom_left = self.GetAbsoluteInParent(pos)
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
            absolute_bl = self.GetAbsoluteInParent(target_bl)
            absolute_tr = self.GetAbsoluteInParent(target_tr)
            quad.SetVertices(absolute_bl,
                             absolute_tr,
                             TextTypes.LEVELS[self.text_type])
            if colour:
                quad.SetColour(colour)
            cursor.x += letter.x
        height = max([q.height for q in self.quads])
        self.UpdatePosition()

    def UpdatePosition(self):
        """Called by the parent to tell us we need to recalculate our absolute position"""
        super(Box,self).UpdatePosition()
        self.Position(pos,self.scale,self.colour)

    def SetPos(self,pos):
        """Called by the user to update our position directly"""
        self.SetBounds(pos,pos + self.size)
        self.Position(pos,self.scale,self.colour)

    def Delete(self):
        """We're done; pack up and go home!"""
        super(TextBox,self).Delete()
        for quad in self.quads:
            quad.Delete()

    def SetText(self,text,colour = None):
        """Update the text"""
        self.Delete()
        self.text = text
        self.quads = [self.textmanager.Letter(char,self.text_type) for char in self.text]
        self.Position(self.pos,self.scale,colour)

    def Disable(self):
        """Don't draw for a while, maybe we'll need you again"""
        super(TextBox,self).Disable()
        for q in self.quads:
            q.Disable()

    def Enable(self):
        """Alright, you're back on the team!"""
        super(TextBox,self).Enable()
        for q in self.quads:
            q.Enable()

class TextBoxButton(TextBox):
    def __init__(self,parent,text,pos,tr,size=0.5,callback = None,line_width=2):
        self.boxextra    = 0.2
        self.callback    = callback
        self.hover_quads = [utils.Quad(gamedata.ui_buffer) for i in xrange(4)]
        self.line_width  = line_width
        self.hovered     = False
        self.selected    = False
        self.enabled     = False
        super(TextBoxButton,self).__init__(parent,pos,tr,text,size)
        for i in xrange(4):
            self.hover_quads[i].Disable()
        self.registered = False
        
    def Position(self,pos,scale,colour = None):
        super(TextBoxButton,self).Position(pos,scale,colour)
        self.SetVertices()

    def UpdatePosition(self):
        super(TextBoxButton,self).UpdatePosition()
        self.SetVertices()

    def SetVertices(self):
        for i in xrange(4):
            self.hover_quads[i].SetColour((1,0,0,1))
        
        #top bar
        self.hover_quads[0].SetVertices(Point(self.absolute.bottom_left.x,self.absolute.top_right.y-self.line_width),
                                        self.absolute.top_right,
                                        utils.ui_level+1)
        #right bar
        self.hover_quads[1].SetVertices(Point(self.absolute.top_right.x-self.line_width,self.absolute.bottom_left.y),
                                        self.absolute.top_right,
                                        utils.ui_level+1)
        
        #bottom bar
        self.hover_quads[2].SetVertices(self.absolute.bottom_left,
                                        Point(self.absolute.top_right.x,self.absolute.bottom_left.y+self.line_width),
                                        utils.ui_level+1)

        #left bar
        self.hover_quads[3].SetVertices(self.absolute.bottom_left,
                                        Point(self.absolute.bottom_left.x+self.line_width,self.absolute.top_right.y),
                                        utils.ui_level+1)
        if not self.enabled:
            for i in xrange(4):
                self.hover_quads[i].Disable()

                                  
    def SetPos(self,pos):
        super(TextBoxButton,self).SetPos(pos)
        self.SetVertices()

    def Delete(self):
        super(TextButtonBox,self).Delete()
        for quad in self.hover_quads:
            quad.Delete()

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
        super(TextBoxButton,self).Enable()
        if not self.enabled:
            self.enabled = True
            self.root.RegisterUIElement(self)
            if self.hovered:
                self.Hover()
        
    def Disable(self):
        super(TextBoxButton,self).Disable()
        if self.enabled:
            self.enabled = False
            self.root.RemoveUIElement(self,element)
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

class ButtonList(UIElement):
    """
    UI Element for showing a list of buttons. Right now it's very basic, does not actually 
    inherit from UIElement(as it doesn't accept clicks itself), and doesn't really do anything

    Just a placeholder really in case we need scrollbars at some point
    """

    def __init__(self,parent,bl,tr):
        super(ButtonList,self).__init__(parent,bl,tr)
        self.itemheight = 0.04*gamedata.screen.y

    def AddElement(self,element):
        element.SetPos(self.top_left - Point(0,self.itemheight*len(self.buttons)))
        self.children.append(element)

    def __getitem__(self,index):
        return self.children[index]
