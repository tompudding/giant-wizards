from OpenGL.GL.framebufferobjects import *
from OpenGL.GL import *
from OpenGL.GLU import *
import utils,gamedata
from utils import Point
import texture

#todo, allow the textbox and textbox button to be specified without a top-right, and have 
#the coords generated from the text.

class UIElementList:
    """
    Very basic implementation of a list of UIElements that can be looked up by position.
    It's using an O(n) algorithm, and I'm sure I can do better once everything's working
    """
    def __init__(self):
        self.items = {}

    def __setitem__(self,item,value):
        self.items[item] = value

    def __delitem__(self,item):
        del self.items[item]

    def __contains__(self,item):
        return item in self.items

    def __str__(self):
        return repr(self)

    def __repr__(self):
        out =  ['UIElementList:']
        for item in self.items:
            out.append('%s:%s - %s(%s)' % (item.absolute.bottom_left,item.absolute.top_right,str(item),item.text if hasattr(item,'text') else 'N/A'))
        return '\n'.join(out)
        
    def Get(self,pos):
        #not very efficient
        match = [-1,None]
        for ui,height in self.items.iteritems():
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
        self.children = []
        self.parent.AddChild(self)
        self.GetAbsoluteInParent = parent.GetAbsolute
        self.root                = parent.root
        self.level               = parent.level + 1
        self.SetBounds(pos,tr)

    def SetBounds(self,pos,tr):
        self.absolute.bottom_left = self.GetAbsoluteInParent(pos)
        self.absolute.top_right   = self.GetAbsoluteInParent(tr)
        self.absolute.size        = self.absolute.top_right - self.absolute.bottom_left
        self.bottom_left          = pos
        self.top_right            = tr
        self.size                 = tr - pos

    def UpdatePosition(self):
        self.SetBounds(self.bottom_left,self.top_right)
        for child_element in self.children:
            child_element.UpdatePosition()

    def GetAbsolute(self,p):
        return self.absolute.bottom_left + (self.absolute.size*p)

    def GetRelative(self,p):
        return (p - self.absolute.bottom_left)/self.absolute.size

    def AddChild(self,element):
        self.children.append(element)

    def __contains__(self,pos):
        if pos.x < self.absolute.bottom_left.x or pos.x >= self.absolute.top_right.x:
            return False
        if pos.y >= self.absolute.bottom_left.y and pos.y < self.absolute.top_right.y:
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
        for child in self.children:
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
        return hash((self.absolute.bottom_left,self.absolute.top_right,self.level))

class RootElement(UIElement):
    """
    A Root Element has no parent. It represents the top level UI element, and thus its coords are
    screen coords. It handles dispatching mouse movements and events. All of its children and
    grand-children (and so on) can register with it (and only it) for handling mouse actions,
    and those actions get dispatched
    """
    def __init__(self,bl,tr):
        self.absolute            = AbsoluteBounds()
        self.on                  = True
        self.GetAbsoluteInParent = lambda x:x
        self.root                = self
        self.level               = 0
        self.hovered             = None
        self.children            = []
        self.active_children     = UIElementList()
        self.SetBounds(bl,tr)
        
    def RegisterUIElement(self,element):
        self.active_children[element] = element.level

    def RemoveUIElement(self,element):
        try:
            del self.active_children[element]
        except KeyError:
            pass

    def RemoveAllUIElements(self):
        self.active_children = UIElementList()

    def MouseMotion(self,pos,rel,handled):
        """
        Try to handle mouse motion. If it's over one of our elements, return True to indicate that
        the lower levels should not handle it. Else return false to indicate that they should
        """
        if handled:
            return handled
        hovered = self.active_children.Get(pos)
        if hovered is not self.hovered:
            if self.hovered != None:
                self.hovered.EndHover()
            self.hovered = hovered
            if self.hovered:
                self.hovered.Hover()
        return True if hovered else False

    def MouseButtonDown(self,pos,button):
        return False

    def MouseButtonUp(self,pos,button):
        if self.hovered:
            self.hovered.OnClick(pos,button)
            return True
        return False

    def CancelMouseMotion(self):
        pass
            
class HoverableElement(UIElement):
    """
    This class represents a UI element that accepts a hover; i.e when the cursor is over it the hover event
    does not get passed through to the next layer.
    """
    def __init__(self,parent,pos,tr):
        super(HoverableElement,self).__init__(parent,pos,tr)
        self.root.RegisterUIElement(self)

    def Delete(self):
        self.root.RemoveUIElement(self)
        super(HoverableElement,self).Delete()

    def Disable(self):
        self.root.RemoveUIElement(self)
        super(HoverableElement,self).Disable()

    def Enable(self):
        self.root.RegisterUIElement(self)
        super(HoverableElement,self).Enable()
    

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
        super(Box,self).Delete()
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

class HoverableBox(Box,HoverableElement):
    pass

class TextBox(UIElement):
    """ A Screen-relative text box wraps text to a given size """
    def __init__(self,parent,bl,tr,text,scale,colour = None):
        if tr == None:
            #If we're given no tr; just set it to one row of text, as wide as it can get without overflowing
            #the parent
            self.shrink_to_fit = True
            text_size          = (gamedata.text_manager.GetSize(text,scale).to_float()/parent.absolute.size)
            margin             = Point(text_size.y*0.06,text_size.y*0.15)
            tr                 = bl + text_size + margin*2
            #We'd like to store the margin relative to us, rather than our parent
            self.margin = margin/(tr-bl)
        else:
            self.shrink_to_fit = False
        super(TextBox,self).__init__(parent,bl,tr)
        if not self.shrink_to_fit:
            #In this case our margin is a fixed part of the box
            self.margin      = 0.05
        self.text        = text
        self.scale       = scale
        self.colour      = colour
        self.text_type   = texture.TextTypes.SCREEN_RELATIVE
        self.text_manager = gamedata.text_manager
        self.quads       = [self.text_manager.Letter(char,self.text_type) for char in self.text]
        #that sets the texture coords for us
        self.Position(self.bottom_left,self.scale,self.colour)

    def Position(self,pos,scale,colour = None):
        """Draw the text at the given location and size. Maybe colour too"""
        #set up the position for the characters. Note that we do everything here in size relative
        #to our text box (so (0,0) is bottom_left, (1,1) is top_right. 
        self.pos = pos
        self.absolute.bottom_left = self.GetAbsoluteInParent(pos)
        self.scale = scale
        row_height = (float(self.text_manager.font_height*self.scale*texture.global_scale)/self.absolute.size.y)
        #Do this without any kerning or padding for now, and see what it looks like
        cursor = Point(self.margin.x,1 - row_height-self.margin.y)
        for (i,quad) in enumerate(self.quads):
            letter_size = Point(float(quad.width *self.scale*texture.global_scale)/self.absolute.size.x,
                                float(quad.height*self.scale*texture.global_scale)/self.absolute.size.y)
            if cursor.x + letter_size.x > 1:
                cursor.x = 0
                cursor.y -= row_height
            target_bl = cursor
            target_tr = target_bl + letter_size
            if target_bl.y < 0:
                #We've gone too far, no more room to write!
                break
            absolute_bl = self.GetAbsolute(target_bl)
            absolute_tr = self.GetAbsolute(target_tr)
            quad.SetVertices(absolute_bl,
                             absolute_tr,
                             texture.TextTypes.LEVELS[self.text_type])
            if colour:
                quad.SetColour(colour)
            cursor.x += letter_size.x
        height = max([q.height for q in self.quads])
        super(TextBox,self).UpdatePosition()

    def UpdatePosition(self):
        """Called by the parent to tell us we need to recalculate our absolute position"""
        super(TextBox,self).UpdatePosition()
        self.Position(self.pos,self.scale,self.colour)

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
        if self.shrink_to_fit:
            text_size          = (gamedata.text_manager.GetSize(text,self.scale).to_float()/self.parent.absolute.size)
            margin             = Point(text_size.y*0.06,text_size.y*0.15)
            tr                 = self.pos + text_size + margin*2
            #We'd like to store the margin relative to us, rather than our parent
            self.margin = margin/(tr-self.pos)
            self.SetBounds(self.pos,tr)
        self.ReallocateResources()
        self.Position(self.pos,self.scale,colour)
        self.Enable()
    
    def ReallocateResources(self):
        self.quads = [self.text_manager.Letter(char,self.text_type) for char in self.text]

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
    def __init__(self,parent,text,pos,tr=None,size=0.5,callback = None,line_width=2):
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
        self.Enable()
        
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
        #FIXME: This is shit. I can't be removing and adding every frame
        reregister = self.enabled
        if reregister:
            self.root.RemoveUIElement(self)
        super(TextBoxButton,self).SetPos(pos)
        self.SetVertices()
        if reregister:
            self.root.RegisterUIElement(self)

    def ReallocateResources(self):
        super(TextBoxButton,self).ReallocateResources()
        self.hover_quads = [utils.Quad(gamedata.ui_buffer) for i in xrange(4)]

    def Delete(self):
        super(TextBoxButton,self).Delete()
        for quad in self.hover_quads:
            quad.Delete()
        self.Disable()

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
            if self.enabled:
                self.hover_quads[i].Enable()

    def Unselected(self):
        self.selected = False
        for i in xrange(4):
            self.hover_quads[i].SetColour((1,0,0,1))
        if not self.enabled or (not self.hovered and not self.selected):
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
            self.root.RemoveUIElement(self)
            for i in xrange(4):
                self.hover_quads[i].Disable()

    def OnClick(self,pos,button):
        if 1 or self.callback != None and button == 1:
            self.callback(pos)
        
# class TexturedButton(TextButton):
#     def __init__(self,text,pos,size=0.5,callback = None,line_width=2):
#         self.text = texture.TextObject(text,gamedata.text_manager)
#         self.text.Position(pos,size)
#         self.pos = pos
#         self.callback = callback
#         super(TextButton,self).__init__(pos,self.text.top_right)
#         self.hover_quads = [utils.Quad(gamedata.ui_buffer) for i in xrange(4)]
#         self.line_width = line_width
#         self.SetVertices()
#         self.hovered = False
#         self.selected = False
#         for i in xrange(4):
#             self.hover_quads[i].Disable()
