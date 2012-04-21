import utils

gamedata = None

wizard_types = ['purple_wizard',
                'red_wizard',
                'yellow_wizard',
                'green_wizard']

class Wizard(object):
    def __init__(self,pos,type):
        self.pos = pos
        self.type = type
        self.quad = utils.Quad(gamedata.quad_buffer)
        
    def SetPos(self,pos,tile_type,tex_coords):
        utils.setvertices(self.quad.vertex,utils.WorldCoords(self.pos),utils.WorldCoords(self.pos)+gamedata.tile_dimensions,0.5)
        full_type = wizard_types[self.type] + '_' + tile_type
        self.quad.tc[0:4] = tex_coords[full_type]
