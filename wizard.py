import utils,texture
from utils import Point

gamedata = None

wizard_types = ['purple_wizard',
                'red_wizard',
                'yellow_wizard',
                'green_wizard']

class Action(object):
    pass

class MoveAction(Action):
    def __init__(self,vector,t,duration = 200):
        self.vector = vector
        self.start_time = t
        self.end_time = t + duration

    def Action(self,wizard):
        wizard.MoveRelative(self.vector)

class Wizard(object):
    def __init__(self,pos,type,tiles,isPlayer,name):
        self.pos = pos
        self.type = type
        self.quad = utils.Quad(gamedata.quad_buffer)
        self.uiquad = utils.Quad(gamedata.ui_buffer)
        self.text = texture.TextObject(name+':',gamedata.text_manager)
        self.text.Position(Point(gamedata.screen.x*0.7,gamedata.screen.y*0.9),0.5)
        utils.setcolour(self.uiquad.colour,(0,0,0,1))
        utils.setvertices(self.uiquad.vertex,
                          Point(gamedata.screen.x*0.7,gamedata.screen.y*0.05),
                          Point(gamedata.screen.x*0.95,gamedata.screen.y*0.95),
                          utils.ui_level)
        self.uiquad.Disable()
        self.text.Disable()
        
                          
        self.isPlayer = isPlayer
        self.name = name
        self.action_list = None
        self.tiles = tiles
        
    def SetPos(self,pos):
        self.pos = pos
        tile_data = self.tiles.GetTile(pos)
        tile_type = tile_data.name
        utils.setvertices(self.quad.vertex,utils.WorldCoords(self.pos),utils.WorldCoords(self.pos)+gamedata.tile_dimensions,0.5)
        full_type = wizard_types[self.type] + '_' + tile_type
        self.quad.tc[0:4] = self.tiles.tex_coords[full_type]
        tile_data.SetActor(self)

    def Select(self):
        self.text.Enable()
        self.uiquad.Enable()
    
    def Unselect(self):
        self.text.Disable()
        self.uiquad.Disable()
        

    def IsPlayer(self):
        return self.isPlayer

    def TakeAction(self,t):
        if self.action_list == None:
            #decide what to do!
            #for now just move right 1 square
            self.action_list = [ MoveAction(Point(1,0),t),MoveAction(Point(1,0),t) ]
        else:
            #do the actions according to the times in them
            if len(self.action_list) == 0:
                self.action_list = None
                return True
            else:
                if t >= self.action_list[0].end_time:
                    action = self.action_list.pop(0)
                    action.Action(self)
        return False

    def MoveRelative(self,offset):
        target = self.pos + offset
        if target.x >= self.tiles.width:
            target.x -= self.tiles.width
        if target.x < 0:
            target.x += self.tiles.width
        if target.y >= self.tiles.height:
            target.y = self.tiles.height-1
        if target.y < 0:
            target.y = 0
        target_tile = self.tiles.GetTile(target)
        if self.movement_allowance >= target_tile.movement_cost and target_tile.Empty():
            self.movement_allowance -= target_tile.movement_cost
            self.tiles.GetTile(self.pos).SetActor(None)
            self.SetPos(target)
            

    def StartTurn(self):
        self.movement_allowance = 2
