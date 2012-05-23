import utils,texture,random,math
from utils import Point

gamedata = None

wizard_types = ['purple_wizard',
                'red_wizard',
                'yellow_wizard',
                'green_wizard']

class Action(object):
    @staticmethod
    def Unselected():
        pass

class MoveAction(Action):
    
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
            self.start_pos = self.wizard.pos
            self.end_pos  = self.start_pos + self.vector
            self.initialised = True
            target_tile = self.wizard.tiles.GetTile(self.end_pos)
            self.attacking   = not target_tile.Empty() 
            self.will_move = self.wizard.action_points >= target_tile.movement_cost
        
        if t > self.end_time:
            self.wizard.MoveRelative(self.vector)
            return True
        elif self.will_move:
            part = float(t-self.start_time)/self.duration
            if not self.attacking:
                pos = self.start_pos + self.vector*part
            else:
                #go halfway then come back
                pos = self.start_pos + self.vector*(part if part < 0.5 else (1-part))
                
            self.wizard.quad.SetVertices(utils.WorldCoords(pos).to_int(),
                                         utils.WorldCoords(pos+Point(1,1)).to_int(),
                                         0.5)
            self.wizard.health_text.Position(utils.WorldCoords(Point(pos.x + 0.6,
                                                                     pos.y + 0.8)),
                                             0.3)
        return False

class MoveActionCreator(object):
    name = 'Move'
    cost = 1
    def __init__(self,wizard):
        self.last_ap = -1
        self._valid_vectors = None
        self.wizard = wizard
        self.shown_path = None

    @property
    def valid_vectors(self):
        if not self._valid_vectors or self.last_ap != self.wizard.action_points:
            ap = self.wizard.action_points
            self._valid_vectors = {}
            for x in xrange(-ap,ap+1):
                for y in xrange(-ap,ap+1):
                    if x == 0 and y == 0:
                        continue
                    p = Point(x,y)
                    target = self.wizard.pos + p
                    tile = self.wizard.tiles.GetTile(target)
                    if not tile:
                        continue
                    actor = tile.GetActor()
                    #Don't move onto friendly chaps
                    if actor and self.wizard.Friendly(actor):
                        continue
                    path = self.wizard.tiles.PathTo(self.wizard.pos,target)
                    if path and path.cost <= ap:
                        self._valid_vectors[p] = path
            self.last_ap = ap
        return self._valid_vectors

    def Create(self,vector,t,wizard,speed=4):
        try:
            path = self.valid_vectors[vector]
        except KeyError:
            return
        
        for step in path.steps:
            yield MoveAction(step,t,wizard,speed)

    def ColourFunction(self,pos):
        #try:
        #    path = self.valid_vectors[pos]
        #except KeyError:
        return (1-pos.length()/6.,1-pos.length()/6.,1-pos.length()/6.,0.6)
        #return (1-path.cost/4.0,1-path.cost/4.0,1-path.cost/4.0,0.6)
        #return (1,1,1,1)

    def Valid(self,vector):
        vectors = self.valid_vectors
        if vectors and vector in vectors:
            return True
        return False

    def MouseMotion(self,pos,vector):
        try:
            newpath = self.valid_vectors[vector]
        except KeyError:
            return
        if newpath != self.shown_path:
            if self.shown_path:
                self.shown_path.Delete()
            newpath.Enable()
            self.shown_path = newpath

    def Unselected(self):
        if self.shown_path != None:
            self.shown_path.Delete()
            self.shown_path = None


class BlastAction(Action):
    name = 'Blast'
    cost = 2
    range = 5.0
    valid_vectors = set(Point(x,y) for x in xrange(-5,6) \
                                   for y in xrange(-5,6) \
                            if Point(x,y).length() != 0 and Point(x,y).length() < 5)
    def __init__(self,vector,t,wizard,speed=4):
        self.vector = vector
        self.wizard = wizard
        self.quad = utils.Quad(gamedata.quad_buffer,tc = self.wizard.tiles.tex_coords['blast'])
        self.quad.Disable()
        self.speed = speed
        self.initialised = False
        self.firing = None

    def Impact(self):
        raise NotImplemented
        
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
                self.quad.Enable()
            else:
                #we're not going to do it so we're already finished
                return True

        if self.firing:
            if t > self.end_time:
                #check to see if the target needs to take damage
                self.Impact()
                
                self.quad.Disable()
                self.quad.Delete()
                self.quad = None
                return True
            elif t >= self.start_time:
                part = float(t-self.start_time)/self.duration
                pos = self.start_pos + self.vector*part
                self.quad.SetVertices(utils.WorldCoords(pos).to_int(),
                                      utils.WorldCoords(pos+Point(1,1)).to_int(),
                                      0.5)
                return False

    @staticmethod
    def Create(vector,t,wizard,speed=4):
        yield BlastAction(vector,t,wizard,speed)

    @staticmethod
    def ColourFunction(pos):
        part = (pos.length()/WizardBlastAction.range)*math.pi
        return (math.sin(part),math.sin(part+math.pi*0.3),math.sin(part+math.pi*0.6),0.3)

    @staticmethod
    def Valid(vector):
        if vector in BlastAction.valid_vectors:
            return True
        return False

class WizardBlastAction(BlastAction):
    name = 'Wizard Blast'
    cost = 2
    min_damage = 1
    max_damage = 3

    def Impact(self):
        target_tile = self.wizard.tiles.GetTile(self.end_pos)
        target = target_tile.GetActor()
        if target:
            damage = random.randint(self.min_damage,self.max_damage)
            target.Damage(damage)

    @staticmethod
    def Create(vector,t,wizard,speed=4):
        yield WizardBlastAction(vector,t,wizard,speed)

    @staticmethod
    def MouseMotion(pos,vector):
        pass
           
class ActionChoice(object):
    def __init__(self,action,position,wizard,callback = None):
        self.action = action
        self.text = '%s%s' % (action.name.ljust(14),str(action.cost).rjust(6))
        self.text = texture.TextButtonUI(self.text,position,size=0.33,callback = callback)
        self.wizard = wizard
        self.quads = [utils.Quad(gamedata.colour_tiles) for p in action.valid_vectors]
        self.selected = False
        self.UpdateQuads()

    def UpdateQuads(self):
        if len(self.action.valid_vectors) > len(self.quads):
            self.quads.extend([utils.Quad(gamedata.colour_tiles) for p in xrange(len(self.action.valid_vectors)-len(self.quads))])
        elif len(self.quads) > len(self.action.valid_vectors):
            diff = len(self.quads) - len(self.action.valid_vectors)
            for quad in self.quads[:diff]:
                quad.Delete()
            self.quads = self.quads[diff:]
        for quad,p in zip(self.quads,self.action.valid_vectors):
            pos = self.wizard.pos + p
            quad.SetVertices(utils.WorldCoords(pos).to_int(),
                             utils.WorldCoords(pos+Point(1,1)).to_int(),
                             0.6)
            #This commented out bit makes the colours smooth. I think pixellated looks better
            #vertices = p,p+Point(0,1),p+Point(1,1),p+Point(1,0)
            #quad.SetColours(self.action.ColourFunction(p) for p in vertices)
            quad.SetColour(self.action.ColourFunction(p))
            if not self.selected:
                quad.Disable()

    def Enable(self):
        self.text.Enable()

    def Disable(self):
        self.text.Disable()

    def Selected(self):
        self.text.Selected()
        self.selected = True
        for q in self.quads:
            q.Enable()

    def Unselected(self):
        self.text.Unselected()
        self.selected = False
        for q in self.quads:
            q.Disable()
        self.action.Unselected()

    def GetVector(self,pos):
        pos = pos.to_int()
        vector = (pos - self.wizard.pos).to_int()
        if vector.x < 0:
            other = (vector.x + self.wizard.tiles.width )
        else:
            other = (vector.x - self.wizard.tiles.width )
        if abs(other) < abs(vector.x):
            vector.x = other
        return vector

    def MouseMotion(self,pos):
        if len(self.wizard.action_list) > 0 or self.wizard.tiles.current_action:
            #don't draw the paths when it's in the process of moving
            self.action.Unselected()
            return
        vector = self.GetVector(pos)
        if not vector:
            self.action.Unselected()
            return None
        if vector.to_int() == Point(0,0):
            #do nothing
            self.action.Unselected()
            return 
        if self.action.Valid(vector):
            self.action.MouseMotion(pos,vector)
        else:
            self.action.Unselected()

    def OnClick(self,pos,button):
        self.action.Unselected()
        vector = self.GetVector(pos)
        if not vector:
            return None
        if vector.to_int() == Point(0,0):
            #do nothing
            return 

        #action = self.action(vector,0,self.wizard)
        if self.action.Valid(vector):
            self.selected = False
            for q in self.quads:
                q.Disable()
            self.action.Unselected()
            for action in self.action.Create(vector,0,self.wizard):
                self.wizard.action_list.append(action)

    def FriendlyTargetable(self):
        return False
        
class Actor(object):
    initial_action_points = 0
    def __init__(self,pos,type,tiles,isPlayer,name,player):
        self.pos = pos
        self.player = player
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
        
        
        
        self.static_text = [self.title,self.action_points_text,self.action_header]
        self.health_text = texture.TextObject('%d' % self.health,gamedata.text_manager,static = False)
        self.health_text.Position(utils.WorldCoords(Point(self.pos.x + 0.6,
                                                          self.pos.y + 0.8)),
                                  0.3)
        self.options_box.Disable()
        for t in self.static_text:
            t.Disable()
                          
        self.isPlayer = isPlayer
        self.name = name
        self.action_list = [] if self.IsPlayer() else None
        self.tiles = tiles
        self.selected = False
        self.flash_state = True
        self.SetPos(pos)
        
    def SetPos(self,pos):
        self.pos = pos
        tile_data = self.tiles.GetTile(pos)
        tile_type = tile_data.name
        self.quad.SetVertices(utils.WorldCoords(self.pos),utils.WorldCoords(self.pos + Point(1,1)),0.5)
        if 'coast' in tile_type:
            tile_type = 'water'
        full_type = self.type + '_' + tile_type
        self.quad.tc[0:4] = self.tiles.tex_coords[full_type]
        tile_data.SetActor(self)
        self.health_text.Position(utils.WorldCoords(Point(self.pos.x + 0.6,
                                                          self.pos.y + 0.8)),
                                  0.3)
        if self.tiles.player_action:
            self.tiles.player_action.UpdateQuads()

    def Select(self):
        self.selected = True
        for t in self.static_text:
            t.Enable()
        for a in self.action_choices:
            a.Enable()
            self.tiles.RegisterUIElement(a.text,1)
        self.options_box.Enable()
        self.tiles.RegisterUIElement(self.options_box,0)
        self.HandleAction(Point(0,0),self.move)
    
    def Unselect(self):
        self.selected = False
        for t in self.static_text:
            t.Disable()
        for a in self.action_choices:
            a.Disable()
            self.tiles.RemoveUIElement(a.text)
        self.options_box.Disable()
        self.tiles.RemoveUIElement(self.options_box)
        self.flash_state = False
        self.quad.Enable()

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

    def NewTurn(self):
        self.action_points = self.initial_action_points
        self.action_points_text.SetText('Action Points : %d' % self.action_points)
        if not self.selected:
            self.action_points_text.Disable()

    def EndTurn(self,pos):
        self.Unselect()
        for action_choice in self.action_choices:
            action_choice.Unselected()

    def TakeAction(self,t):
        if self.action_list == None:
            #For a computer player, decide what to do
            #regular players populate this list themselves
            action_points = self.action_points
            self.action_list = []
            #Find the nearest enemy
            match = [None,None,None]
            for wizard in self.tiles.wizards:
                if wizard.player_character is self:
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
                #need to update the pos anyway to cause various update mechanisms to get triggered
                self.SetPos(self.pos)
            else:
                self.tiles.GetTile(self.pos).SetActor(None)
                self.AdjustActionPoints(-target_tile.movement_cost)
                self.SetPos(target)
            
    

    def HandleAction(self,pos,action):
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

    def HandleMove(self,pos):
        self.HandleAction(pos,self.move)
        
    def HandleBlast(self,pos):
        self.HandleAction(pos,self.action_choices[1])

    def HandleSummon(self,pos):
        self.HandleAction(pos,self.action_choices[2])

    def AdjustActionPoints(self,value):
        self.action_points += value
        self.action_points_text.SetText('Action Points : %d' % self.action_points)
        if not self.selected:
            self.action_points_text.Disable()

    def Friendly(self,other):
        return self.player.Controls(other)

    def Damage(self,value):
        self.health -= value
        self.health_text.SetText('%d' % self.health)
        if self.health <= 0:
            self.quad.Delete()
            self.health_text.Delete()
            self.tiles.RemoveActor(self)

class Player(object):
    def __init__(self,pos,type,tiles,isPlayer,name):
        self.name = name
        self.isPlayer = isPlayer
        self.tiles = tiles
        self.player_character = Wizard(pos,type,tiles,isPlayer,name,self)
        self.controlled = [self.player_character]
        self.controlled_index = 0

        # if isPlayer:
        #     self.controlled.append(Goblin(pos+Point(1,1),
        #                                   'goblin',
        #                                   tiles,
        #                                   isPlayer,
        #                                   self.player_character.name + '\'s Goblin',
        #                                   self))

    @property
    def current_controlled(self):
        return self.controlled[self.controlled_index]

    @property
    def pos(self):
        return self.player_character.pos
    @pos.setter
    def pos(self,value):
        self.player_character.SetPos(value)

    def GetPos(self):
        return self.player_character.pos

    def IsPlayer(self):
        return self.isPlayer

    def StartTurn(self):
        for actor in self.controlled:
            actor.NewTurn()
        self.controlled_index = 0

    def Select(self,monster):
        self.current_controlled.Unselect()
        monster.Select()
        self.controlled_index = self.controlled.index(monster)

    def EndTurn(self,pos):
        for actor in self.controlled:
            actor.EndTurn(pos)
        self.tiles.player_action = None
        self.tiles.NextPlayer()

    def Controls(self,monster):
        #maybe make this efficient at some point
        return monster in self.controlled

    def NextControlled(self,amount):
        self.current_controlled.Unselect()
        self.controlled_index += len(self.controlled) + amount #add the length in case amount is negative
        self.controlled_index %= len(self.controlled)
        #self.controlled[self.controlled_index].Unselect()
        return self.current_controlled

    def TakeAction(self,t):
        return self.current_controlled.TakeAction(t)

    def AddSummoned(self,monster):
        self.controlled.append(monster)

    def RemoveSummoned(self,monster):
        pos = self.controlled.index(monster)
        del self.controlled[pos]
        if self.controlled_index > pos:
            self.controlled_index -= 1
        self.controlled_index %= len(self.controlled)

    def Update(self,t):
        self.current_controlled.Update(t)


class Wizard(Actor):
    initial_action_points = 4
    def __init__(self,pos,type,tiles,isPlayer,name,player):
        full_type = wizard_types[type]
        super(Wizard,self).__init__(pos,full_type,tiles,isPlayer,name,player)
        self.controlled = [self]
        self.controlled_index = 0
        self.player = player
        self.action_choices = [ActionChoice(MoveActionCreator(self),
                                            Point(gamedata.screen.x*0.7,gamedata.screen.y*0.81),
                                            self,
                                            callback = self.HandleMove),
                               ActionChoice(WizardBlastAction,
                                            Point(gamedata.screen.x*0.7,gamedata.screen.y*0.785),
                                            self,
                                            callback = self.HandleBlast),
                               ActionChoice(SummonGoblinAction,
                                            Point(gamedata.screen.x*0.7,gamedata.screen.y*0.76),
                                            self,
                                            callback = self.HandleSummon)]
        #move is special so make a shortcut for it
        self.move = self.action_choices[0]
        for a in self.action_choices:
            a.Disable()

    def Damage(self,value):
        self.health -= value
        self.health_text.SetText('%d' % self.health)
        if self.health <= 0:
            self.quad.Delete()
            self.health_text.Delete()
            self.tiles.RemoveWizard(self)



class Goblin(Actor):
    initial_action_points = 3
    def __init__(self,pos,type,tiles,isPlayer,name,caster):
        super(Goblin,self).__init__(pos,type,tiles,isPlayer,name,caster.player)
        self.caster = caster
        self.action_choices = [ActionChoice(MoveActionCreator(self),
                                            Point(gamedata.screen.x*0.7,gamedata.screen.y*0.81),
                                            self,
                                            callback = self.HandleMove)]
        self.move = self.action_choices[0]
        for a in self.action_choices:
            a.Disable()

    def Damage(self,value):
        self.health -= value
        self.health_text.SetText('%d' % self.health)
        if self.health <= 0:
            self.quad.Delete()
            self.health_text.Delete()
            self.tiles.RemoveActor(self)
            self.caster.RemoveSummoned(self)


class SummonMonsterAction(BlastAction):
    cost  = 4
    range = 4
    valid_vectors = set(Point(x,y) for x in xrange(-3,4) \
                            for y in xrange(-3,4) \
                            if Point(x,y).length() != 0 and Point(x,y).length() < 4)
    
    def Impact(self):
        target_tile = self.wizard.tiles.GetTile(self.end_pos)
        target = target_tile.GetActor()
        if not target:
            monster = self.Monster(self.end_pos,self.monster_type,self.wizard.tiles,self.wizard.IsPlayer(),'A',self.wizard)
            self.wizard.player.AddSummoned(monster)

    @staticmethod
    def MouseMotion(pos,vector):
        pass

class SummonGoblinAction(SummonMonsterAction):
    name  = 'Summon Goblin'
    Monster = Goblin
    monster_type = 'goblin'
 
    @staticmethod
    def Create(vector,t,wizard,speed=4):
        yield SummonGoblinAction(vector,t,wizard,speed)

