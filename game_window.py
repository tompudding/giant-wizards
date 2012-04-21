import os,sys
import utils
from utils import Point,GridCoordsY,GridCoordsX,GridCoords,WorldCoords
from pygame.locals import *
from OpenGL.GL import *
import texture,numpy,random

gamedata = None

class TileData(object):
    def __init__(self,pos,name):
        self.pos = pos
        self.name = name

class Tiles(object):
    def __init__(self,atlas,tiles_name,data_filename,map_size):
        self.atlas = atlas
        self.tiles_name = tiles_name
        self.dragging = None
        self.map_size = map_size
        self.width = map_size[0]
        self.height = map_size[1]
        
        #cheat by preallocating enough quads for the tiles. We want them to be rendered first because it matters for 
        #transparency, but we can't actually fill them in yet because we haven't processed the files with information
        #about them yet.
        for i in xrange(map_size[0]*map_size[1]):
            x = utils.Quad(gamedata.quad_buffer)
        
        #Read the tile data from the tiles.data file
        data = {}
        gamedata.tile_dimensions = Point(64,64)
        with open(data_filename) as f:
            for line in f:
                line = line.split('#')[0].strip()
                if ':' in line:
                    name,values = [v.strip() for v in line.split(':')]
                    data[name] = [int(v.strip()) for v in values.split(',')]
               
        self.tex_coords = {}
        for name,(x,y,w,h) in data.iteritems():
            top_left_x = float(x*gamedata.tile_dimensions.x)/self.atlas.Subimage(self.tiles_name).size.x
            top_left_y = float(self.atlas.Subimage(self.tiles_name).size.y - y*gamedata.tile_dimensions.y)/self.atlas.Subimage(self.tiles_name).size.y
            bottom_right_x = top_left_x + float(w*gamedata.tile_dimensions.x)/self.atlas.Subimage(self.tiles_name).size.x
            bottom_right_y = top_left_y - float(h*gamedata.tile_dimensions.y)/self.atlas.Subimage(self.tiles_name).size.y
            tc = numpy.array(((top_left_x,bottom_right_y),(top_left_x,top_left_y),(bottom_right_x,top_left_y),(bottom_right_x,bottom_right_y)),numpy.float32)
            self.atlas.TransformCoords(self.tiles_name,tc)
            self.tex_coords[name] = tc

        #Set up the map
        self.map = []
        for x in xrange(0,map_size[0]):
            col = []
            for y in xrange(0,map_size[1]):
                w,h = gamedata.tile_dimensions
                col.append( TileData(Point(x,y),random.choice(['grass','water'])) )
            self.map.append(col)

        #Fill in the fixed vertices for the tiles
        index = 0
        for col in self.map:
            for tile_data in col:
                world = WorldCoords(tile_data.pos)
                #world.y -= (gamedata.tile_dimensions.y/2)
                #world.y += self.height*gamedata.tile_dimensions.y/2 #make sure it's all above zero
                tex_coords=self.tex_coords[tile_data.name]
                temp_quad = utils.Quad(gamedata.quad_buffer,tc = tex_coords,index = index)
                index += 4
                utils.setvertices(temp_quad.vertex,world,world + gamedata.tile_dimensions,0)


        self.SetViewpos(Point(0,0)) 

    def SetViewpos(self,viewpos):
        #viewpos = list(viewpos)
        top_left= Point(0,gamedata.screen.y)
        top_right = gamedata.screen
        bottom_right = Point(gamedata.screen.x,0)
        #check the bottom left
        viewgrid = GridCoords(viewpos.to_float())
        if viewgrid.y < 0:
            viewgrid.y = 0
            viewpos = WorldCoords(viewgrid).to_int()

        #now the top left
        viewgrid = GridCoords((viewpos+top_left).to_float())
        if viewgrid.x < 0:
            viewgrid.x = 0
            viewpos = (WorldCoords(viewgrid).to_int())-top_left

        viewgrid = GridCoords((viewpos+bottom_right).to_float())
        if viewgrid.x > self.width:
            viewgrid.x = self.width
            viewpos = (WorldCoords(viewgrid).to_int())-bottom_right

        viewgrid = GridCoords((viewpos+top_right).to_float())
        if viewgrid.y > self.height:
            viewgrid.y = self.height
            viewpos = (WorldCoords(viewgrid).to_int())-top_right


        #print viewpos
        
        self.viewpos = viewpos
        #self.miny = int(GridCoordsY(viewpos))
        #self.maxy = int(GridCoordsY(viewpos + gamedata.screen)+1)
        #self.minx = int(GridCoordsX(Point(viewpos.x,viewpos.y+gamedata.screen.y/self.zoom)))
        #self.maxx = int(GridCoordsX(Point(viewpos.x+gamedata.screen.x/self.zoom,viewpos.y))+1)
        #if self.minx < 0:
        #    self.minx = 0
        #if self.miny < 0:
        #    self.miny = 0

    def Draw(self):
        zcoord = 0
        glBindTexture(GL_TEXTURE_2D, self.atlas.texture.texture)
        glLoadIdentity()
        glTranslate(-self.viewpos.x,-self.viewpos.y,0)
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)
        glVertexPointerf(gamedata.quad_buffer.vertex_data)
        glTexCoordPointerf(gamedata.quad_buffer.tc_data)
        glColorPointer(4,GL_FLOAT,0,gamedata.quad_buffer.colour_data)
        glDrawElements(GL_QUADS,gamedata.quad_buffer.current_size,GL_UNSIGNED_INT,gamedata.quad_buffer.indices)
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glDisableClientState(GL_COLOR_ARRAY)

    def MouseButtonDown(self,pos,button):
        if button == 3:
            self.dragging = self.viewpos + pos
            
    def MouseButtonUp(self,pos,button):
        if button == 3:
            self.dragging = None

    def MouseMotion(self,pos,rel):
        if self.dragging:
            new_setpos = self.dragging - pos
            self.SetViewpos(self.dragging - pos)
            difference = self.viewpos - (new_setpos)
            #if difference is non-zero it means that we didn't get what we requested for some reason,
            #so we should update dragging so it still points at the right place
            self.dragging = self.viewpos + pos

class GameWindow(object):
    def __init__(self):
        self.tiles = Tiles(texture.TextureAtlas('tiles_atlas_0.png','tiles_atlas.txt'),
                           'tiles.png'  ,
                           'tiles.data' ,
                           (64,24)     )

    def Update(self):
        self.tiles.Draw()

    def MouseMotion(self,pos,rel):
        hovered_element = self.tiles
        hovered_element.MouseMotion(pos,rel)

    def MouseButtonDown(self,pos,button):
        #check which element we're over at this point?
        hovered_element = self.tiles
        hovered_element.MouseButtonDown(pos,button)

    def MouseButtonUp(self,pos,button):
        #check which element we're over at this point?
        hovered_element = self.tiles
        hovered_element.MouseButtonUp(pos,button)

