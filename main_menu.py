import os,sys
import utils
from utils import Point,GridCoordsY,GridCoordsX,GridCoords,WorldCoords
from pygame.locals import *
from OpenGL.GL import *
import texture,numpy,random,perlin,wizard,pygame,game_window

gamedata = None

class MainMenu(object):
    def __init__(self):
        self.texture = texture.Texture('main.png')
        self.uielements = {}
        self.backdrop = utils.Quad(gamedata.ui_buffer,tc = utils.full_tc)
        utils.setvertices(self.backdrop.vertex,
                          Point(0,0),
                          gamedata.screen,
                          0)
        self.static_text = []
        self.buttons = []
        self.state = ['Human','CPU','CPU','CPU']
        #This is stupid but there's only a few hours to go and I still need to get pyinstaller working!
        callbacks = [self.PlayerChange0,
                     self.PlayerChange1,
                     self.PlayerChange2,
                     self.PlayerChange3]
        for i,name in enumerate(game_window.names):
            item = texture.TextObject(name,gamedata.text_manager)
            item.Position(Point(0.05*gamedata.screen.x,
                                (0.55-i*0.1)*gamedata.screen.y),
                          0.7)
            self.static_text.append(item)
            button = texture.TextButtonUI(self.state[i],Point(0.50*gamedata.screen.x,
                                                         (0.55-i*0.1)*gamedata.screen.y),
                                          size=0.7,
                                          callback = callbacks[i],
                                          line_width=8)
            self.RegisterUIElement(button,1)
            self.buttons.append(button)
        self.play_button = texture.TextButtonUI('Play',Point(0.22*gamedata.screen.x,
                                                             (0.15)*gamedata.screen.y),
                                                size=0.7,
                                                callback = self.Play,
                                                line_width=8)
        self.RegisterUIElement(self.play_button,1)
        self.exit_button = texture.TextButtonUI('Exit',Point(0.35*gamedata.screen.x,
                                                             (0.15)*gamedata.screen.y),
                                                size=0.7,
                                                callback = self.Quit,
                                                line_width=8)
        self.RegisterUIElement(self.exit_button,1)
        self.hovered_ui = None
        
    def Draw(self):
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.texture.texture)
        glLoadIdentity()
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)
        
        glVertexPointerf(gamedata.ui_buffer.vertex_data)
        glTexCoordPointerf(gamedata.ui_buffer.tc_data)
        glColorPointer(4,GL_FLOAT,0,gamedata.ui_buffer.colour_data)
        glDrawElements(GL_QUADS,gamedata.ui_buffer.current_size,GL_UNSIGNED_INT,gamedata.ui_buffer.indices)
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_COLOR_ARRAY)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        

    def MouseButtonDown(self,pos,button):
        pass

    def MouseButtonUp(self,pos,button):
        if self.hovered_ui:
            self.hovered_ui.OnClick(pos,button)
    
    def MouseMotion(self,pos,rel):
        hovered_ui = self.HoveredUiElement(pos)
        if hovered_ui:
            #if we're over the ui then obviously nothing is selected
            if hovered_ui is not self.hovered_ui:
                if self.hovered_ui != None:
                    self.hovered_ui.EndHover()
                self.hovered_ui = hovered_ui
                self.hovered_ui.Hover()
        else:
            if self.hovered_ui != None:
                self.hovered_ui.EndHover()
                self.hovered_ui = None

    def KeyDown(self,key):
        return

    def RegisterUIElement(self,element,height):
        a = {}
        a[element] = True
        self.uielements[element] = height

    def RemoveUIElement(self,element):
        try:
            del self.uielements[element]
        except KeyError:
            pass

    def HoveredUiElement(self,pos):
        #not very efficient, but I only have 2 days, come on.
        match = [-1,None]
        for ui,height in self.uielements.iteritems():
            if pos in ui:
                if height > match[0]:
                    match = [height,ui]
        return match[1]

    def Update(self,t):
        self.Draw()

    def PlayerChange(self,i):
        if self.state[i] == 'Human':
            self.state[i] = 'CPU'
        elif self.state[i] == 'CPU':
            self.state[i] = 'Off'
        else:
            self.state[i] = 'Human'
        self.buttons[i].SetText(self.state[i])

    def PlayerChange0(self,pos):
        return self.PlayerChange(0)
    def PlayerChange1(self,pos):
        return self.PlayerChange(1)
    def PlayerChange2(self,pos):
        return self.PlayerChange(2)
    def PlayerChange3(self,pos):
        return self.PlayerChange(3)

    def Play(self,pos):
        states = []
        for state in self.state:
            if state == 'Human':
                states.append(True)
            elif state == 'CPU':
                states.append(False)
            else:
                states.append(None)
        
        
        #for a in self.static_text:
        #    a.Delete()
        #for b in self.buttons:
        #    b.Delete()
        gamedata.ui_buffer.truncate(0)
        gamedata.quad_buffer.truncate(0)
        gamedata.text_manager.Purge()
        game = game_window.GameWindow(states)
        gamedata.current_view = game
        
    def Quit(self,pos):
        raise SystemExit