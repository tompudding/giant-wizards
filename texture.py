import pygame
from pygame.locals import *
from OpenGL.GL.framebufferobjects import *
from OpenGL.GL import *
from OpenGL.GLU import *
import utils, gamedata
from utils import Point
import pyinst

cache = {}
global_scale = 0.5


class Texture(object):
    def __init__(self, filename):
        if filename not in cache:
            with open(pyinst.path(filename), "rb") as f:
                self.textureSurface = pygame.image.load(f)
            self.textureData = pygame.image.tostring(self.textureSurface, "RGBA", 1)

            self.width = self.textureSurface.get_width()
            self.height = self.textureSurface.get_height()

            self.texture = glGenTextures(1)
            cache[filename] = (self.texture, self.width, self.height)
            glBindTexture(GL_TEXTURE_2D, self.texture)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexImage2D(
                GL_TEXTURE_2D,
                0,
                GL_RGBA,
                self.width,
                self.height,
                0,
                GL_RGBA,
                GL_UNSIGNED_BYTE,
                self.textureData,
            )
        else:
            self.texture, self.width, self.height = cache[filename]
            glBindTexture(GL_TEXTURE_2D, self.texture)


class RenderTarget(object):
    def __init__(self, x, y, screensize):
        self.fbo = glGenFramebuffers(1)
        self.depthbuffer = glGenRenderbuffers(1)
        self.x = x
        self.y = y
        self.screensize = screensize
        self.texture = glGenTextures(1)
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, self.fbo)
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, self.x, self.y, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
        glBindRenderbufferEXT(GL_RENDERBUFFER_EXT, self.depthbuffer)
        glRenderbufferStorageEXT(GL_RENDERBUFFER_EXT, GL_DEPTH_COMPONENT, self.x, self.y)
        glFramebufferRenderbufferEXT(
            GL_FRAMEBUFFER_EXT, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER_EXT, self.depthbuffer
        )
        glFramebufferTexture2DEXT(
            GL_FRAMEBUFFER_EXT, GL_COLOR_ATTACHMENT0_EXT, GL_TEXTURE_2D, self.texture, 0
        )
        if glCheckFramebufferStatusEXT(GL_FRAMEBUFFER_EXT) != GL_FRAMEBUFFER_COMPLETE_EXT:
            print("crapso")
            raise SystemExit
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, 0)

    def Target(self):
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, self.fbo)
        if glCheckFramebufferStatusEXT(GL_FRAMEBUFFER_EXT) != GL_FRAMEBUFFER_COMPLETE_EXT:
            print("crapso1")
            raise SystemExit
        glPushAttrib(GL_VIEWPORT_BIT)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, self.x, 0, self.y, -10000, 10000)
        glMatrixMode(GL_MODELVIEW)
        glViewport(0, 0, self.x, self.y)

    def Detarget(self):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, self.screensize.x, 0, self.screensize.y, -10000, 10000)
        glMatrixMode(GL_MODELVIEW)
        glPopAttrib()
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, 0)


# texture atlas code taken from
# http://omnisaurusgames.com/2011/06/texture-atlas-generation-using-python/
# I'm assuming it's open source!


class SubImage(object):
    def __init__(self, pos, size):
        self.pos = pos
        self.size = size


class TextureAtlas(object):
    def __init__(self, image_filename, data_filename):
        self.texture = Texture(image_filename)
        self.subimages = {}
        with open(pyinst.path(data_filename), "r") as f:
            for line in f:
                subimage_name, image_name, x, y, w, h = line.strip().split(":")
                # print image_name,image_filename
                # assert(image_name) == image_filename
                w = int(w)
                h = int(h)
                if subimage_name.startswith("font_"):
                    subimage_name = chr(int(subimage_name[5:7], 16))
                    h -= 4
                self.subimages[subimage_name] = SubImage(
                    Point(float(x) / self.texture.width, float(y) / self.texture.height), (Point(w, h))
                )

    def Subimage(self, name):
        return self.subimages[name]

    def TransformCoord(self, subimage, value):
        value[0] = subimage.pos.x + value[0] * (float(subimage.size.x) / self.texture.width)
        value[1] = subimage.pos.y + value[1] * (float(subimage.size.y) / self.texture.height)

    def TransformCoords(self, subimage, tc):
        subimage = self.subimages[subimage]
        for i in range(len(tc)):
            self.TransformCoord(subimage, tc[i])

    def TextureCoords(self, subimage):
        full_tc = [[0, 0], [0, 1], [1, 1], [1, 0]]
        self.TransformCoords(subimage, full_tc)
        return full_tc


class TextTypes:
    SCREEN_RELATIVE = 1
    GRID_RELATIVE = 2
    MOUSE_RELATIVE = 3
    CUSTOM = 4
    LEVELS = {
        SCREEN_RELATIVE: utils.text_level,
        CUSTOM: utils.text_level,
        GRID_RELATIVE: utils.grid_level + 0.1,
        MOUSE_RELATIVE: utils.text_level,
    }


class TextAlignments:
    LEFT = 1
    RIGHT = 2
    CENTRE = 3
    JUSTIFIED = 4


class TextManager(object):
    def __init__(self):
        # self.atlas = TextureAtlas('droidsans.png','droidsans.txt')
        self.atlas = TextureAtlas("pixelmix.png", "pixelmix.txt")
        self.font_height = max(subimage.size.y for subimage in list(self.atlas.subimages.values()))
        self.quads = utils.QuadBuffer(
            131072
        )  # these are reclaimed when out of use so this means 131072 concurrent chars
        TextTypes.BUFFER = {
            TextTypes.SCREEN_RELATIVE: self.quads,
            TextTypes.GRID_RELATIVE: gamedata.nonstatic_text_buffer,
            TextTypes.MOUSE_RELATIVE: gamedata.mouse_relative_buffer,
        }

    def Letter(self, char, textType, userBuffer=None):
        quad = utils.Quad(userBuffer if textType == TextTypes.CUSTOM else TextTypes.BUFFER[textType])
        quad.tc[0:4] = self.atlas.TextureCoords(char)
        # this is a bit dodge, should get its own class if I want to store extra things in it
        quad.width, quad.height = self.atlas.Subimage(char).size
        quad.letter = char
        return quad

    def GetSize(self, text, scale):
        """
        How big would the text be if drawn on a single row in the given size?
        """
        sizes = [self.atlas.Subimage(char).size * scale * global_scale for char in text]
        out = Point(sum(item.x for item in sizes), max(item.y for item in sizes))
        return out

    def Draw(self):
        glBindTexture(GL_TEXTURE_2D, self.atlas.texture.texture)
        glLoadIdentity()
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)
        glVertexPointerf(self.quads.vertex_data)
        glTexCoordPointerf(self.quads.tc_data)
        glColorPointer(4, GL_FLOAT, 0, self.quads.colour_data)
        glDrawElements(GL_QUADS, self.quads.current_size, GL_UNSIGNED_INT, self.quads.indices)
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_COLOR_ARRAY)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)

    def Purge(self):
        self.quads.truncate(0)
