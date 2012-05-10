import utils,texture,random
from utils import Point

gamedata = None

wizard_types = ['purple_wizard',
                'red_wizard',
                'yellow_wizard',
                'green_wizard']

class Action(object):
    pass

class MoveAction(Action):
    name = 'Move'
    cost = 1
    def __init__(self,vector,t,wizard,speed=4):
        self.vector = vector
        self.initialised = False
        self.speed = speed
        self.wizard = wizard
        
    def Update(self,t):
        if not self.initialised:
            self.start_time = t
            self.end_time = t + (self.vector.length()*1000/self.speed)
            self.duration = self.end_time - self.start_time
            self.initialised = True
        if t > self.end_time:
            self.wizard.MoveRelative(self.vector)
            return True
        return False

    def Valid(self):
        if self.vector.length() < 1.5:
            return True
        return False
        
class WizardBlastAction(Action):
    name = 'Wizard Blast'
    cost = 2
    range = 5
    min_damage = 1
    max_damage = 3
    def __init__(self,vector,t,wizard,speed=4):
        self.vector = vector
        self.wizard = wizard
        self.quad = utils.Quad(gamedata.quad_buffer,tc = self.wizard.tiles.tex_coords['blast'])
        self.quad.Disable()
        self.speed = speed
        self.initialised = False
        self.firing = None
        
    def Update(self,t):
        if not self.initialised:
            self.start_time = t
            self.end_time = self.start_time + (self.vector.length()*1000/self.speed)
            self.duration = self.end_time - self.start_time
            self.start_pos = self.wizard.pos
            self.end_pos  = self.start_pos + self.vector
            self.initialised = True

        if self.firing == None:
            #determine whether we can actually fire
            if self.wizard.action_points >= WizardBlastAction.cost:
                self.wizard.AdjustActionPoints(-WizardBlastAction.cost)
                self.firing = True
            else:
                #we're not going to do it so we're already finished
                return True

        if self.firing:
            if t > self.end_time:
                #check to see if the target needs to take damage
                
                target_tile = self.wizard.tiles.GetTile(self.end_pos)
                target = target_tile.GetActor()
                if target:
                    damage = random.randint(WizardBlastAction.min_damage,WizardBlastAction.max_damage)
                    target.Damage(damage)
                self.quad.Delete()
                self.quad = None
                return True
            elif t > self.start_time:
                part = float(t-self.start_time)/self.duration
                pos = self.start_pos + self.vector*part
                self.quad.SetVertices(utils.WorldCoords(pos).to_int(),
                                      utils.WorldCoords(pos+Point(1,1)).to_int(),
                                      0.5)
                return False

    def Valid(self):
        if self.vector.length() < WizardBlastAction.range:
            return True
        return False

class ActionChoice(object):
    def __init__(self,action,position,wizard,callback = None):
        self.action = action
        self.text = '%s%s' % (action.name.ljust(14),str(action.cost).rjust(6))
        self.text = texture.TextButtonUI(self.text,position,size=0.33,callback = callback)
        self.wizard = wizard
        
    def Enable(self):
        self.text.Enable()
        tiles = self.wizard.tiles
        

    def Disable(self):
        self.text.Disable()
        

    def Selected(self):
        self.text.Selected()

    def Unselected(self):
        self.text.Unselected()

    def OnClick(self,pos,button):
        pos = pos.to_int()
        vector = (pos - self.wizard.pos).to_int()
        if vector.x < 0:
            other = (vector.x + self.wizard.tiles.width )
        else:
            other = (vector.x - self.wizard.tiles.width )
        if abs(other) < abs(vector.x):
            vector.x = other
        if vector.to_int() == Point(0,0):
            #do nothing
            return

        action = self.action(vector,0,self.wizard)
        if action.Valid():
            self.wizard.action_list.append(action)
        

class Wizard(object):
    def __init__(self,pos,type,tiles,isPlayer,name):
        self.pos = pos
        self.type = type
        self.health = 10
        self.quad = utils.Quad(gamedata.quad_buffer)
        self.action_points = 0
        self.options_box = texture.BoxUI(Point(gamedata.screen.x*0.7,gamedata.screen.y*0.3),
                                         Point(gamedata.screen.x*0.95,gamedata.screen.y*0.95),
                                         (0,0,0,0.6))
        self.title = texture.TextObject(name+':',gamedata.text_manager)
        self.title.Position(Point(gamedata.screen.x*0.7,gamedata.screen.y*0.9),0.5)
        self.action_points_text = texture.TextObject('Action Points : %d' % self.action_points,gamedata.text_manager)
        self.action_points_text.Position(Point(gamedata.screen.x*0.7,gamedata.screen.y*0.87),0.33)
        self.action_header = texture.TextObject('%s%s' % ('Action'.ljust(14),'Cost'.rjust(6)),gamedata.text_manager)
        self.action_header.Position(Point(gamedata.screen.x*0.7,gamedata.screen.y*0.846),0.33)

        self.action_choices = [ActionChoice(MoveAction,
                                            Point(gamedata.screen.x*0.7,gamedata.screen.y*0.81),
                                            self,
                                            callback = self.HandleMove),
                               ActionChoice(WizardBlastAction,
                                            Point(gamedata.screen.x*0.7,gamedata.screen.y*0.785),
                                            self,
                                            callback = self.HandleBlast)]
        #move is special so make a shortcut for it
        self.move = self.action_choices[0]
        
        self.static_text = [self.title,self.action_points_text,self.action_header]
        self.health_text = texture.TextObject('%d' % self.health,gamedata.text_manager,static = False)
        self.health_text.Position(utils.WorldCoords(Point(self.pos.x + 0.6,
                                                          self.pos.y + 0.8)),
                                  0.3)
        self.options_box.Disable()
        for t in self.static_text:
            t.Disable()
        for a in self.action_choices:
            a.Disable()
        #self.end_turn = texture.TextButtonUI('End Turn',Point(gamedata.screen.x*0.72,gamedata.screen.y*0.07),callback = self.EndTurn)
        #self.end_turn.Disable()
        
                          
        self.isPlayer = isPlayer
        self.name = name
        self.action_list = [] if self.IsPlayer() else None
        self.tiles = tiles
        self.selected = False
        self.flash_state = True
        
    def SetPos(self,pos):
        self.pos = pos
        tile_data = self.tiles.GetTile(pos)
        tile_type = tile_data.name
        self.quad.SetVertices(utils.WorldCoords(self.pos),utils.WorldCoords(self.pos)+gamedata.tile_dimensions,0.5)
        if 'coast' in tile_type:
            tile_type = 'water'
        full_type = wizard_types[self.type] + '_' + tile_type
        self.quad.tc[0:4] = self.tiles.tex_coords[full_type]
        tile_data.SetActor(self)
        self.health_text.Position(utils.WorldCoords(Point(self.pos.x + 0.6,
                                                          self.pos.y + 0.8)),
                                  0.3)

    def Select(self):
        self.selected = True
        for t in self.static_text:
            t.Enable()
        for a in self.action_choices:
            a.Enable()
            self.tiles.RegisterUIElement(a.text,1)
        #self.end_turn.Enable()
        self.options_box.Enable()
        self.tiles.RegisterUIElement(self.options_box,0)
        #self.tiles.RegisterUIElement(self.end_turn,1)
        self.HandleAction(Point(0,0),self.action_choices[0])
    
    def Unselect(self):
        self.selected = False
        for t in self.static_text:
            t.Disable()
        for a in self.action_choices:
            a.Disable()
            self.tiles.RemoveUIElement(a.text)
        #self.end_turn.Disable()
        self.options_box.Disable()
        self.tiles.RemoveUIElement(self.options_box)
        #self.tiles.RemoveUIElement(self.end_turn)

    def Update(self,t):
        if not self.selected:
            self.quad.Enable()
            self.flash_state = True
            return
        if (t%800) > 400:
            #want to be on
            if not self.flash_state:
                self.quad.Enable()
                self.flash_state = True
        else:
            #want to be off
            if self.flash_state:
                self.quad.Disable()
                self.flash_state = False
        

    def IsPlayer(self):
        return self.isPlayer

    def NextControlled(self,amount):
        return self

    def TakeAction(self,t):
        if self.action_list == None:
            #For a computer player, decide what to do
            #regular players populate this list themselves
            #for now just move right 1 square
            action_points = self.action_points
            self.action_list = []
            #Find the nearest enemy
            match = [None,None,None]
            for wizard in self.tiles.wizards:
                if wizard is self:
                    continue
                offset = utils.WrapDistance(wizard.pos,self.pos,self.tiles.width)

                distance = offset.length()
                if match[0] == None or distance < match[0]:
                    match = [distance,wizard]
            if match[1] == None:
                #wtf? There are no other wizards? the game should have ended
                return False
            distance,wizard = match
            current_pos = self.pos
            while action_points > 0:
                offset = utils.WrapDistance(wizard.pos,current_pos,self.tiles.width)
                if distance < WizardBlastAction.range:
                    self.action_list.append( WizardBlastAction(offset,t,self) )
                    action_points -= WizardBlastAction.cost
                else:
                    vector = Point(0,0)
                    if offset.x != 0:
                        vector.x = 1 if offset.x > 0 else -1
                    if offset.y != 0:
                        vector.y = 1 if offset.y > 0 else -1
                    target = current_pos + vector
                    target.x = ((target.x+self.tiles.width)%self.tiles.width)
                    target_tile = self.tiles.GetTile(target)
                    if target_tile.movement_cost <= action_points:
                        current_pos = current_pos + vector
                        self.action_list.append( MoveAction(vector,t,self) )
                        action_points -= target_tile.movement_cost
                    else:
                        #can't do anything else
                        break
                    
        #do the actions according to the times in them
        
        if len(self.action_list) == 0:
            self.action_list = [] if self.IsPlayer() else None
            #returning none means no action to perform, returning False means
            #that the turn should be ended
            return None if self.IsPlayer() else False
        else:
            #if t >= self.action_list[0].end_time:
            action = self.action_list.pop(0)
            return action
        

    def MoveRelative(self,offset):
        target = self.pos + offset
        target.x = (target.x+self.tiles.width)%self.tiles.width
        if target.y >= self.tiles.height:
            target.y = self.tiles.height-1
        if target.y < 0:
            target.y = 0
        
        target_tile = self.tiles.GetTile(target)
        if self.action_points >= target_tile.movement_cost:
            if not target_tile.Empty():
                #maybe we're attacking a fella?
                target_wizard = target_tile.GetActor()
                if target_wizard != None:
                    target_wizard.Damage(2)
                    self.AdjustActionPoints(-1)
            else:
                self.tiles.GetTile(self.pos).SetActor(None)
                self.AdjustActionPoints(-target_tile.movement_cost)
                self.SetPos(target)
            

    def StartTurn(self):
        self.action_points = 4
        self.action_points_text.SetText('Action Points : %d' % self.action_points)
        if not self.selected:
            self.action_points_text.Disable()

    def EndTurn(self,pos):
        self.Unselect()
        for action_choice in self.action_choices:
            if self.tiles.player_action is action_choice:
                self.tiles.player_action = None
                action_choice.Unselected()
                break
        self.tiles.NextPlayer()
    

    def HandleAction(self,pos,action):
        if self.tiles.player_action is action:
            if action is self.move: #always keep move selected if nothing else is
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

    def HandleMove(self,pos):
        self.HandleAction(pos,self.move)
        
    def HandleBlast(self,pos):
        self.HandleAction(pos,self.action_choices[1])

    def AdjustActionPoints(self,value):
        self.action_points += value
        self.action_points_text.SetText('Action Points : %d' % self.action_points)
        if not self.selected:
            self.action_points_text.Disable()

    def Damage(self,value):
        self.health -= value
        self.health_text.SetText('%d' % self.health)
        if self.health <= 0:
            self.quad.Delete()
            self.health_text.Delete()
            self.tiles.RemoveWizard(self)
                
