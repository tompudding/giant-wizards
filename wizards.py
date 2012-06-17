import pygame
from pygame.locals import *
import utils,ui
from OpenGL.GL import *
from OpenGL.GLU import *
from utils import Point

#some sort of hack to get py2exe to work
try:
    from OpenGL.platform import win32
except AttributeError:
    pass

import gamedata
#random.seed(7)
pygame.init()

#Initialise the gamedata globals
gamedata.screen                = None
gamedata.quad_buffer           = utils.QuadBuffer(131072)
gamedata.ui_buffer             = utils.QuadBuffer(131072)
gamedata.nonstatic_text_buffer = utils.QuadBuffer(131072)
gamedata.colour_tiles          = utils.QuadBuffer(131072)
gamedata.mouse_relative_buffer = utils.QuadBuffer(1024)
gamedata.text_manager          = None
gamedata.main_menu             = None
gamedata.current_view          = None
gamedata.player_config         = ['Human','CPU','CPU','CPU']
gamedata.time                  = 0 

import texture,main_menu

def Init(gamedata):
    w,h = (1280,720)
    gamedata.screen = Point(w,h)
    gamedata.screen_root = ui.RootElement(Point(0,0),gamedata.screen)
    screen = pygame.display.set_mode((w,h),pygame.OPENGL | pygame.DOUBLEBUF)
    glClearColor(0.0, 0.0, 0.0, 1.0)
    pygame.display.set_caption('Giant Wizards from the Outer Rim!')
    glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(0, w, 0, h, -10000,10000)
    glMatrixMode(GL_MODELVIEW)

    glEnable(GL_TEXTURE_2D)
    glEnable(GL_BLEND)
    glEnable(GL_DEPTH_TEST)
    glAlphaFunc(GL_GREATER, 0.01)
    glEnable(GL_ALPHA_TEST)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glColor4f(1.0,1.0,1.0,1.0)
    glShadeModel(GL_SMOOTH)

def main():
    
    Init(gamedata)
    gamedata.text_manager = texture.TextManager()
    done = False
    last = 0
    clock = pygame.time.Clock()

    gamedata.ui_buffer.truncate(0)
    gamedata.quad_buffer.truncate(0)
    gamedata.text_manager.Purge()
    #gamedata.current_view = game_window.GameWindow([True,True,True,True])
    gamedata.current_view = main_menu.MainMenu()
    gamedata.dragging = None

    while not done:
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        clock.tick(60)
        t = pygame.time.get_ticks()
        if t - last > 1000:
            #print 'FPS:',clock.get_fps()
            last = t
        #gamedata.time = t

        glLoadIdentity()
        gamedata.current_view.Update(t)
        gamedata.text_manager.Draw()
        pygame.display.flip()

        eventlist = pygame.event.get()
        for event in eventlist:
            if event.type == pygame.locals.QUIT:
                done = True
                break
            elif (event.type == KEYDOWN):
                gamedata.current_view.KeyDown(event.key)
            else:
                try:
                    pos = Point(event.pos[0],gamedata.screen[1]-event.pos[1])
                except AttributeError:
                    continue
                if event.type == pygame.MOUSEMOTION:
                    rel = Point(event.rel[0],-event.rel[1])
                    if gamedata.dragging:
                        gamedata.dragging.MouseMotion(pos,rel,False)
                    else:
                        handled = gamedata.screen_root.MouseMotion(pos,rel,False)
                        if handled:
                            gamedata.current_view.CancelMouseMotion()
                        gamedata.current_view.MouseMotion(pos,rel,True if handled else False)
                elif (event.type == MOUSEBUTTONDOWN):
                    for layer in gamedata.screen_root,gamedata.current_view:
                        handled,dragging = layer.MouseButtonDown(pos,event.button)
                        if handled and dragging:
                            gamedata.dragging = dragging
                            break
                        if handled:
                            break
                    
                elif (event.type == MOUSEBUTTONUP):
                    for layer in gamedata.screen_root,gamedata.current_view:
                        handled,dragging = layer.MouseButtonUp(pos,event.button)
                        if handled and not dragging:
                            gamedata.dragging = None
                        if handled:
                            break

import logging

if __name__ == '__main__':
    try:
        #logging.basicConfig(level=logging.DEBUG, filename='errorlog.log')
        logging.basicConfig(level=logging.DEBUG)
    except IOError:
        #pants, can't write to the current directory, try using a tempfile
        pass

    try:
        main()
    except Exception, e:
        print 'Caught exception, writing to error log...'
        logging.exception("Oops:")

