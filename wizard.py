import utils

gamedata = None

wizard_types = ['purple_wizard',
                'red_wizard',
                'yellow_wizard',
                'green_wizard']

class Wizard(object):
    def __init__(self,pos,type,tc):
        self.pos = pos
        self.type = type
        self.quad = utils.Quad(gamedata.quad_buffer,tc = tc[wizard_types[self.type]])
        utils.setvertices(self.quad.vertex,utils.WorldCoords(self.pos),utils.WorldCoords(self.pos)+gamedata.tile_dimensions,0.5)
