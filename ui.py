from OpenGL.GL.framebufferobjects import *
from OpenGL.GL import *
from OpenGL.GLU import *
import utils,gamedata
from utils import Point
import texture,bisect

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
        """Return the object at a given absolute position, or None if None exist"""
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

    def RemoveChild(self,element):
        for i,child in enumerate(self.children):
            if child is element:
                break
        else:
            return
        del self.children[i]
                

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

    def Depress(self,pos):
        """
        Called when you the mouse cursor is over the element and the button is pushed down. If the cursor
        is moved away while the button is still down, and then the cursor is moved back over this element
        still with the button held down, this is called again. 

        Returns the target of a dragging event if any. For example, if we return self, then we indicate 
        that we have begun a drag and want to receive all mousemotion events until that drag is ended.
        """
        return None

    def Undepress(self):
        """
        Called after Depress has been called, either when the button is released while the cursor is still
        over the element (In which case a OnClick is called too), or when the cursor moves off the element 
        (when OnClick is not called)
        """
        pass

    def OnClick(self,pos,button):
        """
        Called when the mouse button is pressed and released over an element (although the cursor may move
        off and return between those two events). Pos is absolute coords
        """
        pass

    def Scroll(self,amount):
        """
        Called with the value of 1 for a scroll up, and -1 for a scroll down event. Other things could call
        this with larger values for a bigger scoll action
        """
        pass

    def MouseMotion(self,pos,rel,handled):
        """
        Called when the mouse is moved over the element. Pos is absolute coords
        """
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
        self.depressed           = None
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
        #I'm not sure about the logic here. It might be a bit inefficient. Seems to work though
        if hovered:
            hovered.MouseMotion(pos,rel,handled)
        if hovered is not self.hovered:
            if self.hovered != None:
                self.hovered.EndHover()
        if not hovered or not self.depressed or (self.depressed and hovered is self.depressed):
            self.hovered = hovered
            if self.hovered:
                self.hovered.Hover()
            
        return True if hovered else False

    def MouseButtonDown(self,pos,button):
        """
        Handle a mouse click at the given position (screen coords) of the given mouse button.
        Return whether it was handled, and whether it started a drag event
        """
        dragging = None
        if self.hovered:
            if button == 1:
                #If you click and hold on a button, it becomes depressed. If you then move the mouse away, 
                #it becomes undepressed, and you can move the mouse back and depress it again (as long as you
                #keep the mouse button down. You can't move over another button and depress it though, so 
                #we record which button is depressed
                if self.depressed:
                    #Something's got a bit messed up and we must have missed undepressing that last depressed button. Do
                    #that now
                    self.depressed.Undepress()
                self.depressed = self.hovered
                dragging = self.depressed.Depress(pos)
            elif button == 4:
                self.hovered.Scroll(1)
            elif button == 5:
                self.hovered.Scroll(-1)
        return True if self.hovered else False,dragging

    def MouseButtonUp(self,pos,button):
        handled = False
        if button == 1:
            if self.hovered and self.hovered is self.depressed:
                self.hovered.OnClick(pos,button)
                handled = True
            if self.depressed:
                #Whatever happens, the button gets depressed
                self.depressed.Undepress()
                self.depressed = None
        
            return handled,False
        return False,False

    def CancelMouseMotion(self):
        pass

class UIRoot(RootElement):
    def __init__(self,*args,**kwargs):
        super(UIRoot,self).__init__(*args,**kwargs)
        self.drawable_children = {}

    def Draw(self):
        glDisable(GL_TEXTURE_2D)
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glLoadIdentity()
        glVertexPointerf(gamedata.ui_buffer.vertex_data)
        glColorPointer(4,GL_FLOAT,0,gamedata.ui_buffer.colour_data)
        glDrawElements(GL_QUADS,gamedata.ui_buffer.current_size,GL_UNSIGNED_INT,gamedata.ui_buffer.indices)
        glEnable(GL_TEXTURE_2D)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        for item in self.drawable_children:
            item.Draw()

    def RegisterDrawable(self,item):
        self.drawable_children[item] = True

    def RemoveDrawable(self,item):
        try:
            del self.drawable_children[item]
        except KeyError:
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

class HoverableBox(Box,HoverableElement):
    pass

class TextBox(UIElement):
    """ A Screen-relative text box wraps text to a given size """
    def __init__(self,parent,bl,tr,text,scale,colour = None,textType = texture.TextTypes.SCREEN_RELATIVE,alignment = texture.TextAlignments.LEFT):
        if tr == None:
            #If we're given no tr; just set it to one row of text, as wide as it can get without overflowing
            #the parent
            self.shrink_to_fit = True
            text_size          = (gamedata.text_manager.GetSize(text,scale).to_float()/parent.absolute.size)
            margin             = Point(text_size.y*0.06,text_size.y*0.15)
            tr                 = bl + text_size + margin*2 #Add a little breathing room by using 2.1 instead of 2
            #We'd like to store the margin relative to us, rather than our parent
            self.margin = margin/(tr-bl)
        else:
            self.shrink_to_fit = False
        super(TextBox,self).__init__(parent,bl,tr)
        if not self.shrink_to_fit:
            #In this case our margin is a fixed part of the box
            self.margin      = Point(0.05,0.05)
        self.text        = text
        self.scale       = scale
        self.colour      = colour
        self.text_type   = textType
        self.alignment   = alignment
        self.text_manager = gamedata.text_manager
        self.ReallocateResources()
        #self.quads       = [self.text_manager.Letter(char,self.text_type) for char in self.text]
        self.viewpos     = 0
        #that sets the texture coords for us
        self.Position(self.bottom_left,self.scale,self.colour)

    def Position(self,pos,scale,colour = None,ignore_height = False):
        """Draw the text at the given location and size. Maybe colour too"""
        #set up the position for the characters. Note that we do everything here in size relative
        #to our text box (so (0,0) is bottom_left, (1,1) is top_right. 
        self.pos = pos
        self.absolute.bottom_left = self.GetAbsoluteInParent(pos)
        self.scale = scale
        self.lowest_y = 0
        row_height = (float(self.text_manager.font_height*self.scale*texture.global_scale)/self.absolute.size.y)
        #Do this without any kerning or padding for now, and see what it looks like
        cursor = Point(self.margin.x,-self.viewpos + 1 - row_height-self.margin.y)
        letter_sizes = [Point(float(quad.width *self.scale*texture.global_scale)/self.absolute.size.x,
                              float(quad.height*self.scale*texture.global_scale)/self.absolute.size.y) for quad in self.quads]
        #for (i,(quad,letter_size)) in enumerate(zip(self.quads,letter_sizes)):
        i = 0
        while i < len(self.quads):
            quad,letter_size = self.quads[i],letter_sizes[i]
            if cursor.x + letter_size.x > (1-self.margin.x)*1.001:
                #This would take us over a line. If we're in the middle of a word, we need to go back to the start of the 
                #word and start the new line there
                restart = False
                if quad.letter in ' \t':
                    #It's whitespace, so ok to start a new line, but do it after the whitespace
                    while self.quads[i].letter in ' \t':
                        i += 1
                    restart = True
                else:
                    #look for the start of the word
                    while i >= 0 and self.quads[i].letter not in ' \t':
                        i -= 1
                    if i <= 0:
                        #This single word is too big for the line. Shit, er, lets just bail
                        break
                    #skip the space
                    i += 1
                    restart = True
                        
                cursor.x = self.margin.x
                cursor.y -= row_height
                if restart:
                    continue
            
            if cursor.x == self.margin.x and self.alignment == texture.TextAlignments.CENTRE:
                #If we're at the start of a row, and we're trying to centre the text, then check to see how full this row is
                #and if it's not full, offset so that it becomes centred
                width = 0
                for size in letter_sizes[i:]:
                    width += size.x
                    if width > 1-self.margin.x:
                        width -= size.x
                        break
                if width > 0:
                    cursor.x += float(1-(self.margin.x*2)-width)/2

            target_bl = cursor
            target_tr = target_bl + letter_size
            if target_bl.y < self.lowest_y:
                self.lowest_y = target_bl.y
            if target_bl.y < 0 and not ignore_height:
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
            i += 1
        #For the quads that we're not using right now, set them to display nothing
        for quad in self.quads[i:]:
            quad.SetVertices(Point(0,0),Point(0,0),-10)
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
        self.viewpos = 0
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


class ScrollTextBox(TextBox):
    """A TextBox that can be scrolled to see text that doesn't fit in the box"""
    def __init__(self,*args,**kwargs):
        super(ScrollTextBox,self).__init__(*args,**kwargs)
        self.enabled = False
        self.dragging = None

    def Position(self,pos,scale,colour = None):
        super(ScrollTextBox,self).Position(pos,scale,colour,ignore_height = True)

    def Enable(self):
        super(ScrollTextBox,self).Enable()
        if not self.enabled:
            self.enabled = True
            self.root.RegisterUIElement(self)
            self.root.RegisterDrawable(self)

    def Disable(self):
        super(ScrollTextBox,self).Disable()
        if self.enabled:
            self.enabled = False
            self.root.RemoveUIElement(self)
            self.root.RemoveDrawable(self)

    def Depress(self,pos):
        self.dragging = self.viewpos + self.GetRelative(pos).y
        return self

    def ReallocateResources(self):
        self.quad_buffer = utils.QuadBuffer(1024)
        self.text_type = texture.TextTypes.CUSTOM
        self.quads = [self.text_manager.Letter(char,self.text_type,self.quad_buffer) for char in self.text]

    def Draw(self):
        glPushAttrib(GL_VIEWPORT_BIT)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        bl = self.absolute.bottom_left.to_int()
        tr = self.absolute.top_right.to_int()
        glOrtho(bl.x, tr.x, bl.y, tr.y,-10000,10000)
        glMatrixMode(GL_MODELVIEW)
        glViewport(bl.x, bl.y, tr.x-bl.x, tr.y-bl.y)

        glTranslate(0,-self.viewpos*self.absolute.size.y,0)
        glVertexPointerf(self.quad_buffer.vertex_data)
        glTexCoordPointerf(self.quad_buffer.tc_data)
        glColorPointer(4,GL_FLOAT,0,self.quad_buffer.colour_data)
        glDrawElements(GL_QUADS,self.quad_buffer.current_size,GL_UNSIGNED_INT,self.quad_buffer.indices)
        
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, gamedata.screen.x, 0, gamedata.screen.y,-10000,10000)
        glMatrixMode(GL_MODELVIEW)
        glPopAttrib()
        

    def Undepress(self):
        self.dragging = None

    def Scroll(self,amount):
        self.viewpos = self.ValidViewpos(self.viewpos - float(amount)/30)

    def ValidViewpos(self,viewpos):
        low_thresh = 0.05
        high_thresh = 1.05
        if viewpos < self.lowest_y - low_thresh:
            viewpos = self.lowest_y - low_thresh
        if viewpos > low_thresh:
            viewpos = low_thresh
        return viewpos
       
    def MouseMotion(self,pos,rel,handled):
        pos = self.GetRelative(pos)
        low_thresh = 0.05
        high_thresh = 1.05
        if self.dragging != None:
            #print pos,'vp:',self.viewpos,(self.dragging - pos).y
            self.viewpos = self.ValidViewpos(self.dragging - pos.y)

            self.dragging = self.viewpos + pos.y
            if self.dragging > high_thresh:
                self.dragging = high_thresh
            if self.dragging < low_thresh:
                self.dragging = low_thresh
            #print 'stb vp:',self.viewpos
            #self.UpdatePosition()

class TextBoxButton(TextBox):
    def __init__(self,parent,text,pos,tr=None,size=0.5,callback = None,line_width=2):
        self.callback    = callback
        self.line_width  = line_width
        self.hovered     = False
        self.selected    = False
        self.depressed   = False
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

    def Depress(self,pos):
        self.depressed = True
        for i in xrange(4):
            self.hover_quads[i].SetColour((1,1,0,1))
        return None

    def Undepress(self):
        self.depressed = False
        for i in xrange(4):
            self.hover_quads[i].SetColour((1,0,0,1))

    def Enable(self):
        super(TextBoxButton,self).Enable()
        if not self.enabled:
            self.enabled = True
            self.root.RegisterUIElement(self)
            if self.hovered:
                self.Hover()
            elif self.selected:
                self.Selected()
            elif self.depressed:
                self.Depressed()

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
        

class Slider(UIElement):
    def __init__(self,parent,bl,tr,points,callback):
        super(Slider,self).__init__(parent,bl,tr)
        self.points   = sorted(points,lambda x,y:cmp(x[0],y[0]))
        self.callback = callback
        self.lines    = []
        self.uilevel  = utils.ui_level+1
        self.enabled  = False
        self.clickable_area = UIElement(self,Point(0.05,0),Point(0.95,1))
        line          = utils.Quad(gamedata.ui_buffer)
        line_bl       = self.clickable_area.absolute.bottom_left + self.clickable_area.absolute.size*Point(0,0.3)
        line_tr       = line_bl + self.clickable_area.absolute.size*Point(1,0) + Point(0,2)
        line.SetVertices(line_bl,line_tr,self.uilevel)
        line.Disable()
        
        low  = self.points[ 0][0]
        high = self.points[-1][0]
        self.offsets = [float(value - low)/(high-low) if low != high else 0 for value,index in self.points]
        self.lines.append(line)
        self.index    = 0
        self.pointer_quad = utils.Quad(gamedata.ui_buffer)
        self.pointer_colour = (1,0,0,1)
        self.lines.append(self.pointer_quad)
        self.pointer_ui = UIElement(self.clickable_area,Point(0,0),Point(0,0))
        self.SetPointer()
        self.pointer_quad.Disable()
        self.dragging = False
        #now do the blips
        for offset in self.offsets:
            line    = utils.Quad(gamedata.ui_buffer)
            line_bl = self.clickable_area.absolute.bottom_left + Point(offset,0.3)*self.clickable_area.absolute.size
            line_tr = line_bl + self.clickable_area.absolute.size*Point(0,0.2) + Point(2,0)
            line.SetVertices(line_bl,line_tr,self.uilevel)
            line.Disable()
            self.lines.append(line)

    def SetPointer(self):
        offset = self.offsets[self.index]
        
        pointer_bl = Point(offset,0.3) - (Point(2,10)/self.clickable_area.absolute.size)
        pointer_tr = pointer_bl + (Point(7,14)/self.clickable_area.absolute.size)
        self.pointer_ui.SetBounds(pointer_bl,pointer_tr)
        self.pointer_quad.SetVertices(self.pointer_ui.absolute.bottom_left,self.pointer_ui.absolute.top_right,self.uilevel + 0.1)
        self.pointer_quad.SetColour(self.pointer_colour)

    def Enable(self):
        super(Slider,self).Enable()
        for line in self.lines:
            line.Enable()
        if not self.enabled:
            self.enabled = True
            self.root.RegisterUIElement(self)

    def Disable(self):
        super(Slider,self).Disable()
        for line in self.lines:
            line.Disable()
        if self.enabled:
            self.enabled = False
            self.root.RemoveUIElement(self)

    def Depress(self,pos):
        if pos in self.pointer_ui:
            self.dragging = True
            return self
        else:
            return None

    def MouseMotion(self,pos,rel,handled):
        if not self.dragging:
            return #we don't care
        outer_relative_pos = self.GetRelative(pos)
        if outer_relative_pos.x < 0:
            outer_relative_pos.x = 0
        if outer_relative_pos.x > 1:
            outer_relative_pos = 1
        relative_pos = self.GetAbsolute(outer_relative_pos)
        relative_pos = self.clickable_area.GetRelative(relative_pos)
        pointer_bl = Point(relative_pos.x,0.3) - (Point(2,10)/self.clickable_area.absolute.size)
        pointer_tr = pointer_bl + (Point(7,14)/self.clickable_area.absolute.size)
        #This is a bit of a hack to avoid having to do a calculation
        temp_ui = UIElement(self.clickable_area,pointer_bl,pointer_tr)
        self.pointer_quad.SetVertices(temp_ui.absolute.bottom_left,temp_ui.absolute.top_right,self.uilevel + 0.1)
        self.clickable_area.RemoveChild(temp_ui)
        #If there are any eligible choices between the currently selected choice and the mouse cursor, choose 
        #the one closest to the cursor
        #Where is the mouse?
        i = bisect.bisect_right(self.offsets,relative_pos.x)
        if i == len(self.offsets):
            #It's off the right, so choose the last option
            chosen = i - 1
        elif i == 0:
            #It's off the left, so choose the first
            chosen = 0
        else:
            #It's between 2 options, so choose whichevers closest
            if abs(relative_pos.x - self.offsets[i-1]) < abs(relative_pos.x - self.offsets[i]):
                chosen = i-1
            else:
                chosen = i
            
        if chosen != self.index:
            self.index = chosen
            #self.SetPointer()
            self.callback(self.index)

    def Undepress(self):
        self.dragging = False
        self.SetPointer()

    def OnClick(self,pos,button):
        #For now try just changing which is selected
        if pos in self.pointer_ui or self.dragging:
            #It's a click on the pointer, which we ignore
            return
        #If it's a click to the right or left of the pointer, adjust accordingly
        if pos.x > self.pointer_ui.absolute.top_right.x:
            self.index = (self.index + 1) % len(self.points)
        elif pos.x < self.pointer_ui.absolute.bottom_left.x:
            self.index = (self.index + len(self.points) - 1) % len(self.points)
        else:
            return
        self.SetPointer()
        self.callback(self.index)
            
