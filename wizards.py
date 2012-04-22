import os,sys
import pygame
from pygame.locals import *
import utils
from OpenGL.GL import *
from OpenGL.GLU import *
from utils import Point
import game_window,wizard,texture,main_menu
#some sort of hack to get py2exe to work
try:
    from OpenGL.platform import win32
except AttributeError:
    pass

pygame.init()

class GameData(object):
    screen = None
    quad_buffer = utils.QuadBuffer(131072)
    ui_buffer   = utils.QuadBuffer(131072)
    nonstatic_text_buffer = utils.QuadBuffer(131072)
    text_manager = None
    main_menu = None
    current_view = None

def Init(gamedata):
    w,h = (1280,720)
    gamedata.screen = Point(w,h)
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
    glAlphaFunc(GL_GREATER, 0.3)
    glEnable(GL_ALPHA_TEST)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glColor4f(1.0,1.0,1.0,1.0)

if __name__ == '__main__':
    #first make a gamedata struct and set it up in the other modules so they can access it
    #not at all sure that this is best practice.
    gamedata = GameData()
    for module in utils,game_window,wizard,texture,main_menu:
        setattr(module,'gamedata',gamedata)
    
    Init(gamedata)
    gamedata.text_manager = texture.TextManager()
    done = False
    last = 0
    clock = pygame.time.Clock()

    #gamedata.current_view = game_window.GameWindow()
    gamedata.main_menu = main_menu.MainMenu()
    gamedata.current_view = gamedata.main_menu

    while not done:
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        clock.tick(60)
        t = pygame.time.get_ticks()
        if t - last > 1000:
            print 'FPS:',clock.get_fps()
            last = t

        glLoadIdentity()
        gamedata.current_view.Update(t)
        gamedata.text_manager.Draw()
        pygame.display.flip()

        eventlist = pygame.event.get()
        for event in eventlist:
            if event.type == pygame.locals.QUIT:
                done = True
                break
            elif event.type == pygame.MOUSEMOTION:
                gamedata.current_view.MouseMotion(Point(event.pos[0],gamedata.screen[1]-event.pos[1]),Point(event.rel[0],-event.rel[1]))
            elif (event.type == KEYDOWN):
                gamedata.current_view.KeyDown(event.key)
            elif (event.type == MOUSEBUTTONDOWN):
                gamedata.current_view.MouseButtonDown(Point(event.pos[0],gamedata.screen[1]-event.pos[1]),event.button)
            elif (event.type == MOUSEBUTTONUP):
                gamedata.current_view.MouseButtonUp(Point(event.pos[0],gamedata.screen[1]-event.pos[1]),event.button)
