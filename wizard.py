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
        self.action_points = 0
        self.options_box = texture.BoxUI(Point(gamedata.screen.x*0.7,gamedata.screen.y*0.05),
                                         Point(gamedata.screen.x*0.95,gamedata.screen.y*0.95),
                                         (0,0,0,0.6))
        self.title = texture.TextObject(name+':',gamedata.text_manager)
        self.title.Position(Point(gamedata.screen.x*0.7,gamedata.screen.y*0.9),0.5)
        self.action_points_text = texture.TextObject('Action Points : %d' % self.action_points,gamedata.text_manager)
        self.action_points_text.Position(Point(gamedata.screen.x*0.7,gamedata.screen.y*0.87),0.33)
        self.action_header = texture.TextObject('%s%s' % ('Action'.ljust(10),'Cost'.rjust(10)),gamedata.text_manager)
        self.action_header.Position(Point(gamedata.screen.x*0.7,gamedata.screen.y*0.846),0.33)
        
        self.static_text = [self.title,self.action_points_text,self.action_header]
        self.options_box.Disable()
        for t in self.static_text:
            t.Disable()
        self.end_turn = texture.TextButtonUI('End Turn',Point(gamedata.screen.x*0.72,gamedata.screen.y*0.07),callback = self.EndTurn)
        self.end_turn.Disable()
        
                          
        self.isPlayer = isPlayer
        self.name = name
        self.action_list = None
        self.tiles = tiles
        self.selected = False
        
    def SetPos(self,pos):
        self.pos = pos
        tile_data = self.tiles.GetTile(pos)
        tile_type = tile_data.name
        utils.setvertices(self.quad.vertex,utils.WorldCoords(self.pos),utils.WorldCoords(self.pos)+gamedata.tile_dimensions,0.5)
        full_type = wizard_types[self.type] + '_' + tile_type
        self.quad.tc[0:4] = self.tiles.tex_coords[full_type]
        tile_data.SetActor(self)

    def Select(self):
        self.selected = True
        for t in self.static_text:
            t.Enable()
        self.end_turn.Enable()
        self.options_box.Enable()
        self.tiles.RegisterUIElement(self.options_box)
        self.tiles.RegisterUIElement(self.end_turn)
    
    def Unselect(self):
        self.selected = False
        for t in self.static_text:
            t.Disable()
        self.end_turn.Disable()
        self.options_box.Disable()
        self.tiles.RemoveUIElement(self.options_box)
        self.tiles.RemoveUIElement(self.end_turn)
        

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
        if self.action_points >= target_tile.movement_cost and target_tile.Empty():
            self.action_points -= target_tile.movement_cost
            self.tiles.GetTile(self.pos).SetActor(None)
            self.SetPos(target)
            

    def StartTurn(self):
        self.action_points = 4
        self.action_points_text.SetText('Action Points : %d' % self.action_points)
        if not self.selected:
            self.action_points_text.Disable()

    def EndTurn(self,pos):
        self.Unselect()
        self.tiles.NextPlayer()
