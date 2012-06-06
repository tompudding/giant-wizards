import utils
from utils import Point
from pygame.locals import *
from OpenGL.GL import *
import texture,game_window,ui,random,gamedata,players

#This is a terrible hack
names = ['Purple Wizard','Red Wizard','Yellow Wizard','Green Wizard']

class MainMenu(object):
    def __init__(self):
        self.texture = texture.Texture('main.png')
        self.uielements = {}
        self.backdrop = utils.Quad(gamedata.quad_buffer,tc = utils.full_tc)
        self.backdrop.SetVertices(Point(0,0),
                                  gamedata.screen,
                                  0)
        self.static_text = []
        self.buttons = []
        offset = Point(-0.005,-0.045)
        
        #This is stupid but there's only a few hours to go and I still need to get pyinstaller working!
        callbacks = [self.PlayerChange0,
                     self.PlayerChange1,
                     self.PlayerChange2,
                     self.PlayerChange3]
        for i,name in enumerate(names):
            item = ui.TextBox(parent = gamedata.screen_root,
                              bl     = offset + Point(0.05,0.55-i*0.1),
                              tr     = None,
                              text   = name,
                              scale  = 0.7)
            self.static_text.append(item)
            button_bl = offset+Point(0.50,(0.55-i*0.1))
            button = ui.TextBoxButton(gamedata.screen_root     ,
                                      gamedata.player_config[i],
                                      button_bl,
                                      size=0.7,
                                      callback = callbacks[i],
                                      line_width=4)
            self.buttons.append(button)
        self.play_button = ui.TextBoxButton(gamedata.screen_root ,
                                            'Play'               ,
                                            offset+Point(0.22,
                                                         (0.15)),
                                            size=0.7,
                                            callback = self.Play,
                                            line_width=4)
        self.exit_button = ui.TextBoxButton(gamedata.screen_root,
                                            'Exit'              ,
                                            offset+Point(0.35,
                                                         (0.15)),
                                            size=0.7,
                                            callback = self.Quit,
                                            line_width=4)

    def Draw(self):
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.texture.texture)
        glLoadIdentity()
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)
        
        
        glVertexPointerf(gamedata.quad_buffer.vertex_data)
        glTexCoordPointerf(gamedata.quad_buffer.tc_data)
        glColorPointer(4,GL_FLOAT,0,gamedata.quad_buffer.colour_data)
        glDrawElements(GL_QUADS,4,GL_UNSIGNED_INT,gamedata.quad_buffer.indices)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glDisable(GL_TEXTURE_2D)
        
        glVertexPointerf(gamedata.ui_buffer.vertex_data)
        glTexCoordPointerf(gamedata.ui_buffer.tc_data)
        glColorPointer(4,GL_FLOAT,0,gamedata.ui_buffer.colour_data)
        glDrawElements(GL_QUADS,gamedata.ui_buffer.current_size,GL_UNSIGNED_INT,gamedata.ui_buffer.indices)
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_COLOR_ARRAY)
        glEnable(GL_TEXTURE_2D)

    def MouseMotion(self,pos,rel):
        pass

    def CancelMouseMotion(self):
        pass
    
    def MouseButtonDown(self,pos,button):
        pass

    def MouseButtonUp(self,pos,button):
        pass

    def KeyDown(self,key):
        return

    def Update(self,t):
        self.Draw()

    def PlayerChange(self,i):
        if gamedata.player_config[i] == 'Human':
            gamedata.player_config[i] = 'CPU'
        elif gamedata.player_config[i] == 'CPU':
            gamedata.player_config[i] = 'Off'
        else:
            gamedata.player_config[i] = 'Human'
        self.buttons[i].SetText(gamedata.player_config[i])

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
        num_human = 0
        num_cpu   = 0
        for state in gamedata.player_config:
            if state == 'Human':
                states.append(players.PlayerTypes.HUMAN)
                num_human += 1
            elif state == 'CPU':
                states.append(random.choice((players.PlayerTypes.TENTATIVE,players.PlayerTypes.GUNGHO)))
                num_cpu += 1
            else:
                states.append(None)

        #Check that this is a valid configuration before continuing
        if num_human == 0:
            if num_cpu <= 1:
                return
        
        for a in self.static_text:
            a.Delete()
        for b in self.buttons:
            b.Delete()
        self.play_button.Delete()
        self.exit_button.Delete()
        gamedata.ui_buffer.truncate(0)
        gamedata.quad_buffer.truncate(0)
        gamedata.nonstatic_text_buffer.truncate(0)
        gamedata.text_manager.Purge()
        game = game_window.CreateTiles(states)
        gamedata.current_view = game
        
    def Quit(self,pos):
        raise SystemExit
