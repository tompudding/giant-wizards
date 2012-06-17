import players,utils,gamedata,ui,texture
from utils import Point

class Actor(object):
    """
    Class to represent all characters than can appear on the game board
    """
    initial_action_points = 0
    initial_move_points   = 0
    initial_health_points = 0
    max_action_points     = 0
    def __init__(self,pos,type,tiles,playerType,name,player):
        self.colour             = player.colour
        self.colour_name        = players.PlayerColours.NAMES[self.colour]
        self.pos                = pos
        self.player             = player
        self.tiles              = tiles
        self.type               = type
        self.full               = None
        self.health             = self.initial_health_points
        self.quad               = utils.Quad(gamedata.quad_buffer)
        self.action_points      = 0
        self.move_points        = 0
        self.options_box        = ui.HoverableBox(gamedata.screen_root,
                                                  Point(0.7,0.5),
                                                  Point(0.95,0.95),
                                                  (0,0,0,0.6))
        self.title              = ui.TextBox(parent  = self.options_box,
                                             bl      = Point(0,0.89)   ,
                                             tr      = None            , #Work it out
                                             text    = name+':'        ,
                                             scale   = 0.5             )

        self.movement_text      = ui.TextBox(parent  = self.options_box,
                                             bl      = Point(0,0.82)   ,
                                             tr      = None            ,
                                             text    = 'Movement : %d' % self.move_points,
                                             scale   = 0.33            )

        self.action_points_text = ui.TextBox(parent  = self.options_box,
                                             bl      = Point(0.6,0.82) ,
                                             tr      = None            ,
                                             text    = 'Mana : %d' % self.action_points,
                                             scale   = 0.33            )

        self.health_text        = ui.TextBox(parent  = self.tiles      ,
                                             bl      = (self.pos + Point(0.6,0.8)) / self.tiles.map_size,
                                             tr      = None            ,
                                             text    = '%d' % self.health,
                                             scale   = 0.3             ,
                                             textType = texture.TextTypes.GRID_RELATIVE)
                                      
        self.ui_elements = [self.title              ,
                            self.action_points_text ,
                            self.movement_text      ,
                            self.options_box        ]
        for t in self.ui_elements:
            t.Disable()
                          
        self.player_type = playerType
        self.name        = name
        self.action_list = []
        self.selected    = False
        self.flash_state = True
        self.SetPos(pos)
        
    def SetPos(self,pos):
        """Set the position of the actor on the game board"""
        #FIXME : sort this shit out so that it doesn't use strings
        self.pos = pos
        tile_data = self.tiles.GetTile(pos)
        tile_type = tile_data.name
        self.SetDrawPos(pos)

        if 'coast' in tile_type:
            tile_type = 'water'
        self.full_type = '_'.join((self.colour_name,self.type,tile_type))
        self.quad.tc[0:4] = self.tiles.tex_coords[self.full_type]
        tile_data.SetActor(self)

        self.health_text.Position((self.pos + Point(0.6,0.8)) / self.tiles.map_size,
                                  0.3)
        if self.tiles.player_action:
            self.tiles.player_action.UpdateQuads()

    def SetDrawPos(self,pos):
        """Set the position of the actor without updating the game board, used for partial moves animations"""
        self.quad.SetVertices(utils.WorldCoords(pos).to_int(),
                              utils.WorldCoords(pos+Point(1,1)).to_int(),
                              0.5)
        self.health_text.Position((pos + Point(0.6,0.8)) / self.tiles.map_size,
                                  0.3)

    def Select(self):
        self.selected = True
        for t in self.ui_elements:
            t.Enable()
        self.HandleAction(Point(0,0),self.move)
    
    def Unselect(self):
        self.selected = False
        for t in self.ui_elements:
            t.Disable()
        self.flash_state = False
        self.quad.Enable()
        self.action_choices.Unselected()
        self.quad.SetColour((1,1,1,1))

    def Update(self,t):
        if not self.selected:
            self.quad.Enable()
            self.quad.SetColour((1,1,1,1))
            self.flash_state = True
            return
        if (t%800) > 400:
            #want to be on
            if not self.flash_state:
                #self.quad.Enable()
                self.quad.SetColour((1,1,1,1))
                self.flash_state = True
        else:
            #want to be off
            if self.flash_state:
                self.quad.SetColour((1,1,1,0.3))
                self.flash_state = False
        

    def IsPlayer(self):
        return self.player_type == players.PlayerTypes.HUMAN

    def NewTurn(self):
        self.action_points += self.initial_action_points
        if self.action_points > self.max_action_points:
            self.action_points = self.max_action_points
        self.move_points    = self.initial_move_points
        self.action_points_text.SetText('Mana : %d' % self.action_points)
        self.movement_text.SetText('Movement : %d' % self.move_points)
        if not self.selected:
            self.action_points_text.Disable()
            self.movement_text.Disable()

    def EndTurn(self,pos):
        self.Unselect()
        self.action_choices.Unselected()

    def MoveRelative(self,offset):
        target = self.pos + offset
        target.x = (target.x+self.tiles.width)%self.tiles.width
        if target.y >= self.tiles.height:
            target.y = self.tiles.height-1
        if target.y < 0:
            target.y = 0
        
        target_tile = self.tiles.GetTile(target)
        if not target_tile.Empty():
            #maybe we're attacking a fella?
            target_actor = target_tile.GetActor()
            if target_actor != None:
                target_actor.Damage(2)
            #need to update the pos anyway to cause various update mechanisms to get triggered
            self.SetPos(self.pos)
        else:
            self.tiles.GetTile(self.pos).SetActor(None)
            self.SetPos(target)
            
    

    def HandleAction(self,pos,action):
        #raise TypeError
        if self.tiles.player_action is action:
            if action is self.move: #always keep move selected if nothing else is
                action.UpdateQuads()
                return
            else:
                self.tiles.player_action = self.move
                action.Unselected()
                self.move.Selected()
        else:
            if self.tiles.player_action:
                self.tiles.player_action.Unselected()
            action.Selected()
            self.tiles.player_action = action
        self.tiles.player_action.UpdateQuads()

    def AdjustActionPoints(self,value):
        self.action_points += value
        self.action_points_text.SetText('Mana : %d' % self.action_points)
        if not self.selected:
            self.action_points_text.Disable()

    def AdjustMovePoints(self,value):
        self.move_points += value
        self.movement_text.SetText('Movement : %d' % self.move_points)
        if not self.selected:
            self.movement_text.Disable()

    def Friendly(self,other):
        return self.player.Controls(other)

    def Damage(self,value):
        self.health -= value
        self.health_text.SetText('%d' % self.health)
        if self.health <= 0:
            self.Kill()

    def Kill(self):
        self.quad.Delete()
        self.health_text.Delete()
        self.tiles.RemoveActor(self)
