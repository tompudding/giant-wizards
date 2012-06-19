import utils,math,gamedata,random,ui,texture
from utils import Point

class Action(object):
    def __init__(self,vector,t,actor,speed):
        self.vector      = vector
        self.initialised = False
        self.speed       = speed
        self.actor       = actor

    @staticmethod
    def Unselected():
        pass

    @staticmethod
    def Update(t):
        pass

    def InvalidatePathCache(self):
        pass


#Just wrap the static functions of the class
#This class exists only so we can have a consistent interface
class BasicActionCreator(object):
    def __init__(self,actor,actions):
        self.actions      = actions
        self.action_index = 0
        self.action       = self.actions[self.action_index]
        self.actor        = actor
        #self.detail_text = ui.TextBox()

    @property
    def name(self):
        return self.action.generic_name

    @property
    def cost(self):
        return self.action.cost

    @property
    def valid_vectors(self):
        return self.action.valid_vectors

    def ColourFunction(self,pos):
        return self.action.ColourFunction(pos)

    def Create(self,vector,t,wizard,speed=4):
        yield self.action(vector,t,wizard,speed)

    def Valid(self,vector):
        return self.action.Valid(vector)

    def SetAction(self,index):
        self.action_index = index
        self.action = self.actions[self.action_index]
        self.InvalidatePathCache()

    def MouseMotion(self,pos,vector):
        return

    def Unselected(self):
        return

    def Update(self,t):
        pass

    def InvalidatePathCache(self):
        pass


class MoveAction(Action):
    name = 'Move'
    generic_name = 'Move'
    cost = 1
        
    def Update(self,t):
        if not self.initialised:
            self.start_time  = t
            self.end_time    = t + (self.vector.length()*1000/self.speed)
            self.duration    = self.end_time - self.start_time
            self.start_pos   = self.actor.pos
            self.end_pos     = self.start_pos + self.vector
            self.initialised = True
            self.target_tile = self.actor.tiles.GetTile(self.end_pos)
            self.attacking   = not self.target_tile.Empty() 
            self.will_move   = self.actor.move_points >= self.target_tile.movement_cost
        
        if t > self.end_time:
            self.actor.AdjustMovePoints(-self.target_tile.movement_cost)
            self.actor.MoveRelative(self.vector)
            return True
        elif self.will_move:
            part = float(t-self.start_time)/self.duration
            if not self.attacking:
                pos = self.start_pos + self.vector*part
            else:
                #go halfway then come back
                pos = self.start_pos + self.vector*(part if part < 0.5 else (1-part))
                
            self.actor.SetDrawPos(pos)

        return False


class MoveActionCreator(BasicActionCreator):
    def __init__(self,wizard,actions):
        self.last_ap        = -1
        self._valid_vectors = None
        self.wizard         = wizard
        self.shown_path     = None
        self.action         = actions[0]

    @property
    def valid_vectors(self):
        if 1:#not self._valid_vectors or self.last_ap != self.wizard.action_points:
            ap = self.wizard.move_points
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
            yield self.action(step,t,wizard,speed)

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

class TeleportAction(Action):
    description = 'Tunnel through space to arrive at a new location instantaneously. The further you want to go, the more likely you are to find yourself somewhere unexpected...'
    name = 'Teleport'
    generic_name = 'Teleport'
    cost = 5
    range         = 15
    valid_vectors = set(Point(x,y) for x in xrange(-15,16) \
                            for y in xrange(-15,16) \
                            if Point(x,y).length() != 0 and Point(x,y).length() < 15)
    close_vectors  = set(v for v in valid_vectors if v.length() < 5)
    medium_vectors = set(v for v in valid_vectors if v.length() >=5 and v.length() < 10)
    far_vectors    = set(v for v in valid_vectors if v.length() >= 10)

    def __init__(self,vector,t,actor,speed):
        self.initialised = False
        self.speed       = speed
        self.actor       = actor
        if vector in self.close_vectors:
            disturbance_range = 1
            #weight the choice towards the chosen target
            possible_targets = [vector]*20
        elif vector in self.medium_vectors:
            disturbance_range = 4
            #weight it less
            possible_targets = [vector]*4
        elif vector in self.far_vectors:
            disturbance_range = 20
            #weight it much less
            possible_targets = [vector]
        #make a list of the possible targets within the disturbance range
        for x in xrange(-disturbance_range,disturbance_range+1):
            for y in xrange(-disturbance_range,disturbance_range+1):
                p = vector + Point(x,y)
                if p.y < 0 or p.y > self.actor.tiles.height:
                    continue
                tile = self.actor.tiles.GetTile(self.actor.pos + p)
                if not tile or not tile.Empty() or tile.Impassable():
                    continue
                possible_targets.append(p)
        vector = random.choice(possible_targets)
        self.vector      = vector
        
    def Update(self,t):
        if not self.initialised:
            self.start_time  = t
            self.end_time    = t + (self.vector.length()*1000/self.speed)
            self.duration    = self.end_time - self.start_time
            self.start_pos   = self.actor.pos
            self.end_pos     = self.start_pos + self.vector
            self.initialised = True
            target_tile      = self.actor.tiles.GetTile(self.end_pos)
        
        if t > self.end_time:
            self.actor.AdjustActionPoints(-self.cost)
            self.actor.MoveRelative(self.vector)
            return True
        
        part = float(t-self.start_time)/self.duration
        pos = self.start_pos + self.vector*part

        self.actor.quad.SetVertices(utils.WorldCoords(pos).to_int(),
                                    utils.WorldCoords(pos+Point(1,1)).to_int(),
                                    0.5)
        self.actor.health_text.Position(utils.WorldCoords(Point(pos.x + 0.6,
                                                                pos.y + 0.8)),
                                        0.3)
        return False


class TeleportActionCreator(BasicActionCreator):
    def __init__(self,wizard,actions):
        super(TeleportActionCreator,self).__init__(wizard,actions)
        self.cycle = 0
        
    @property
    def valid_vectors(self):
        vectors = []
        if self.action.cost > self.actor.action_points:
            return vectors
        for p in self.action.valid_vectors:
            target = self.actor.pos + p
            tile = self.actor.tiles.GetTile(target)
            if not tile or tile.Impassable():
                continue
            #check line of sight. Note this isn't very efficient as we're checking
            #some blocks multiple times, but oh well
            path = utils.Brensenham(self.actor.pos,target,self.actor.tiles.width)
            path_tiles = [self.actor.tiles.GetTile(point) for point in path]
            if any( tile == None or tile.name in ('tree','mountain') or tile.actor not in (None,self.actor) for tile in path_tiles[:-1]):
                continue
            vectors.append(p)
        return vectors

    def Create(self,vector,t,wizard,speed=12):
        yield self.action(vector,t,wizard,speed)

    def Valid(self,vector):
        return vector in self.valid_vectors

    def ColourFunctionClose(self,pos):
        part = (pos.length()/5)*math.pi*0.3
        return (0,0,math.cos(part),0.4)

    def ColourFunctionMedium(self,pos):
        part = ((pos.length()-5)/5)*math.pi*0.3
        return (0,math.cos(part),0,0.4)

    def ColourFunctionFar(self,pos):
        part = ((pos.length()-10)/5)*math.pi*0.3
        return (math.cos(part),0,0,0.4)

    def ColourFunction(self,pos):
        distance = pos.length()
        if distance < 5:
            return self.ColourFunctionClose(pos)
        elif distance < 10:
            return self.ColourFunctionMedium(pos)
        else:
            return self.ColourFunctionFar(pos)

    def Update(self,t):
        return
        #cycle = (float(t)/800)
        #if abs(cycle - self.cycle) > 0.2:
        #    self.cycle = cycle

class BlastAction(Action):
    generic_name  = 'Blast'
    cost          = 2
    range         = 5.0
    valid_vectors = set(Point(x,y) for x in xrange(-5,6) \
                                   for y in xrange(-5,6) \
                            if Point(x,y).length() != 0 and Point(x,y).length() < 5)
    def __init__(self,vector,t,actor,speed):
        super(BlastAction,self).__init__(vector,t,actor,speed)        
        self.quad        = utils.Quad(gamedata.quad_buffer,tc = self.actor.tiles.tex_coords['blast'])
        self.quad.Disable()
        self.firing      = None

    def Impact(self):
        raise NotImplemented
        
    def Update(self,t):
        if not self.initialised:
            self.start_time  = t
            self.end_time    = self.start_time + (self.vector.length()*1000/self.speed)
            self.duration    = self.end_time - self.start_time
            self.start_pos   = self.actor.pos
            self.end_pos     = self.start_pos + self.vector
            self.initialised = True

        if self.firing == None:
            #determine whether we can actually fire
            if self.actor.action_points >= self.cost:
                self.actor.AdjustActionPoints(-self.cost)
                self.firing = True
                self.path = utils.Brensenham(self.start_pos,self.end_pos,self.actor.tiles.width)[1:]
                self.visited = {self.start_pos:True}
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
                for d in Point(0,0),Point(0,0.8),Point(0.8,0),Point(0.8,0.8):
                    p = (pos + d).to_int()
                    #if p in self.path and p not in self.visited:
                    if p not in self.visited:
                        self.visited[p] = True
                        self.VisitTile(p)
                    
                self.quad.SetVertices(utils.WorldCoords(pos).to_int(),
                                      utils.WorldCoords(pos+Point(1,1)).to_int(),
                                      0.5)
                return False

    def VisitTile(self,tile):
        pass

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


class BlastActionCreator(BasicActionCreator):
    def __init__(self,wizard,actions):
        super(BlastActionCreator,self).__init__(wizard,actions)
        self.cycle = 0
        self._valid_vectors = None
        
    @property
    def valid_vectors(self):
        vectors = []
        if self.action.cost > self.actor.action_points:
            return vectors

        if self._valid_vectors != None:
            return self._valid_vectors

        for p in self.action.valid_vectors:
            target = self.actor.pos + p
            tile = self.actor.tiles.GetTile(target)
            if not tile:
                continue
            #check line of sight. Note this isn't very efficient as we're checking
            #some blocks multiple times, but oh well
            path = utils.Brensenham(self.actor.pos,target,self.actor.tiles.width)
            path_tiles = [self.actor.tiles.GetTile(point) for point in path]
            if any( tile == None or tile.name in ('tree','mountain') or tile.actor not in (None,self.actor) for tile in path_tiles[:-1]):
                if self.action != EpicWizardBlastAction:
                    #The epic blast can go through obstacles
                    continue
            vectors.append(p)
        self._valid_vectors = vectors
        return vectors

    def Valid(self,vector):
        return vector in self.valid_vectors

    def ColourFunction(self,pos):
        part = (pos.length()/WizardBlastAction.range)*math.pi
        return (math.sin(-part*self.cycle),math.sin(part-math.pi*self.cycle),math.sin(part-math.pi*(self.cycle+0.3)),0.3)

    def Update(self,t):
        return
        #cycle = (float(t)/800)
        #if abs(cycle - self.cycle) > 0.2:
        #    self.cycle = cycle

    def InvalidatePathCache(self):
        self._valid_vectors = None

def RangeTiles(range):
    return set(Point(x,y) for x in xrange(-range,range+1) \
                   for y in xrange(-range,range+1)        \
                   if Point(x,y).length() != 0 and Point(x,y).length() < range)

class WizardBlastAction(BlastAction):
    name         = 'Wizard Blast'
    generic_name = 'Wizard Blast'
    description = 'An entropic whirlwind punched out at the speed of sound. Conservation of momentum won\'t be the only thing getting smashed when your enemies are propelled backwards with the force of this blast.'
    cost        = 2
    min_damage  = 1
    max_damage  = 3

    def Impact(self):
        target_tile = self.actor.tiles.GetTile(self.end_pos)
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

class WeakWizardBlastAction(WizardBlastAction):
    name          = 'Weak Wizard Blast'
    description   = 'A kinetic blast launched from your fingertips with enough speed and ferocity to intimidate even the most couragous butterfly. Roughly equivalent to throwing a shoe "really hard!"'
    cost          = 1
    min_damage    = 1
    max_damage    = 2
    range         = 3
    valid_vectors = RangeTiles(range)

class PowerfulWizardBlastAction(WizardBlastAction):
    name          = 'Powerful Wizard Blast'
    description   = 'Casting this spell causes an instant sonic-boom as a vortex of crackling energy bolts towards your enemies at a terrifying speed. Causing formidable damage and with a chance of disintegration, this spell should not be attempted indoors, or without adult supervision'
    cost          = 4
    min_damage    = 4
    max_damage    = 8
    range         = 6
    valid_vectors = RangeTiles(range)

class EpicWizardBlastAction(WizardBlastAction):
    name          = 'Epic Wizard Blast'
    description   = 'Legend tells that in ages past, when Metrakai the World-Eater cast a shadow of apocalypse over the Earth, that a council of races gathered and channeled the power of the heavens itself into a spell of such destructive power that the gods themselves trembled to behold it. Use at your own risk'
    cost          = 50
    min_damage    = 100
    max_damage    = 1000
    range         = 16
    valid_vectors = RangeTiles(range)

    def __init__(self,*args,**kwargs):
        super(EpicWizardBlastAction,self).__init__(*args,**kwargs)
        self.total_damage = random.randint(self.min_damage,self.max_damage)

    def Impact(self):
        target_tile = self.actor.tiles.GetTile(self.end_pos)
        target = target_tile.GetActor()
        if target:
            damage = random.randint(self.total_damage)
            target.Damage(damage)

    def VisitTile(self,pos):
        """Do damage to each tile we go through as we're epic"""
        target_tile = self.actor.tiles.GetTile(pos)
        if target_tile.name in ('grass','mountain','tree'):
            target_tile.name = 'scorched'
            target_tile.movement_cost = 1
            self.actor.tiles.SetMapVertices()
        target = target_tile.GetActor()
        if target:
            target.Damage(int(self.total_damage*0.1))
            self.total_damage*=0.9


class SummonMonsterAction(BlastAction):
    cost          = 4
    range         = 4
    valid_vectors = set(Point(x,y) for x in xrange(-3,4) \
                            for y in xrange(-3,4)        \
                            if Point(x,y).length() != 0 and Point(x,y).length() < 4)
    Monster       = None #This is abstract, you must subclass and provide a Monster

    def Impact(self):
        target_tile = self.actor.tiles.GetTile(self.end_pos)
        target = target_tile.GetActor()
        if not target:
            monster = self.Monster(self.end_pos,
                                   self.monster_type,
                                   self.actor.tiles,
                                   self.actor.IsPlayer(),
                                   self.actor.name + '\'s ' + self.Monster.name,
                                   self.actor)
            self.actor.player.AddSummoned(monster)

    @staticmethod
    def MouseMotion(pos,vector):
        pass



class SummonActionCreator(BasicActionCreator):
    def __init__(self,wizard,action):
        super(SummonActionCreator,self).__init__(wizard,action)
        
    @property
    def valid_vectors(self):
        vectors = []
        if self.action.cost > self.actor.action_points:
            return vectors
        for p in self.action.valid_vectors:
            target = self.actor.pos + p
            tile = self.actor.tiles.GetTile(target)
            if not tile:
                continue
            if not tile.Empty() or tile.Impassable():
                continue
            vectors.append(p)
        return vectors

    def Valid(self,vector):
        return vector in self.valid_vectors



class ActionChoice(object):
    """
    An action choice represents an action that an actor can perform. It keeps track of an button in the options_box of the 
    actor it belongs to. When that button is clicked it is "Selected", and it displays visual information of where it can
    be applied to on the game board
    """
    def __init__(self,ui_parent,action,position,wizard,callback = None):
        #todo, only active player-controlled characters should get their stuff created and registered
        self.action           = action
        self.text             = '%s' % action.name
        self.text             = ui.TextBoxButton(ui_parent,self.text,position,size=0.33,callback = self.OnButtonClick)
        self.actor_callback   = callback
        self.wizard           = wizard
        self.quads            = [utils.Quad(gamedata.colour_tiles) for p in action.valid_vectors]
        
        self.selected       = False
        self.vectors_cache  = []
        self.UpdateQuads()

    def UpdateQuads(self):
        if len(self.action.valid_vectors) > len(self.quads):
            self.quads.extend([utils.Quad(gamedata.colour_tiles) for p in xrange(len(self.action.valid_vectors)-len(self.quads))])
        elif len(self.quads) > len(self.action.valid_vectors):
            diff = len(self.quads) - len(self.action.valid_vectors)
            for quad in self.quads[:diff]:
                quad.Delete()
            self.quads = self.quads[diff:]
        self.vectors_cache = [v for v in self.action.valid_vectors]
        for quad,p in zip(self.quads,self.vectors_cache):
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

    def Update(self,t):
        self.action.Update(t)
        #for quad,p in zip(self.quads,self.vectors_cache):
        #    quad.SetColour(self.action.ColourFunction(p))

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

    def OnGridClick(self,pos,button):
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

    def OnButtonClick(self,pos):
        return self.actor_callback(pos,self)

    def FriendlyTargetable(self):
        return False   

    def InvalidatePathCache(self):
        self.action.InvalidatePathCache()

class SpellActionChoice(ActionChoice):
    """
    An action choice that also has an extra spell detail box that gives additional information and customisation about
    the spell. The intention is for it to also have a cast button, so that you customise the spell in that button, then
    click cast, followed by clicking on the grid in an appropriate location. The cast button should be greyed out if you
    don't have enough mana
    """
    def __init__(self,ui_parent,action,position,wizard,callback = None):
        super(SpellActionChoice,self).__init__(ui_parent,action,position,wizard,callback)
        self.spell_detail_box = ui.HoverableBox(gamedata.screen_root,
                                                Point(0.7,0.08),
                                                Point(0.95,0.45),
                                                (0,0,0,0.6))
        self.spell_detail_box.name = ui.TextBox(parent = self.spell_detail_box,
                                                bl     = Point(0,0.9),
                                                tr     = Point(1,1),
                                                text   = self.action.action.name,
                                                scale  = 0.3,
                                                alignment = texture.TextAlignments.CENTRE)
        self.spell_detail_box.description = ui.ScrollTextBox(parent = self.spell_detail_box,
                                                             bl     = Point(0,0.15),
                                                             tr     = Point(1,0.7),
                                                             text   = self.action.action.description,
                                                             scale  = 0.25)
        self.spell_detail_box.cost = ui.TextBox(parent = self.spell_detail_box,
                                                bl     = Point(0.10,0.05),
                                                tr     = None,
                                                text   = 'cost : %d' % self.action.action.cost,
                                                scale  = 0.3)

        #Construct the list of points for the slider
        points = [(action.cost,i) for (i,action) in enumerate(self.action.actions)]
        self.spell_detail_box.slider = ui.Slider(parent   = self.spell_detail_box,
                                                 bl       = Point(0.1,0.7),
                                                 tr       = Point(0.9,0.9),
                                                 points   = points,
                                                 callback = self.SetSubAction)

        self.spell_detail_box.Disable()

    def SetSubAction(self,index):
        self.action.SetAction(index)
        self.spell_detail_box.name.SetText(self.action.action.name)
        self.spell_detail_box.description.SetText(self.action.action.description)
        self.spell_detail_box.cost.SetText('cost : %d' % self.action.action.cost)
        self.UpdateQuads()

    def Selected(self):
        super(SpellActionChoice,self).Selected()
        self.spell_detail_box.Enable()

    def Unselected(self):
        super(SpellActionChoice,self).Unselected()
        self.spell_detail_box.Disable()

class ActionChoiceList(ui.UIElement):
    def __init__(self,parent,actor,pos,tr,creators):
        super(ActionChoiceList,self).__init__(parent,pos,tr)
        self.actor = actor
        self.choices = []
        self.itemheight = 0.1
        for creator in creators:
            if isinstance(creator,MoveActionCreator):
                action_class = ActionChoice
            else:
                action_class = SpellActionChoice
            action_choice = action_class(self,creator,Point(0,0),self.actor,self.actor.HandleAction)
            self.choices.append(action_choice)
            action_choice.text.SetPos(self.top_right - Point(self.top_right.x,self.itemheight*len(self.children)))

    def Unselected(self):
        for action_choice in self.choices:
            action_choice.Unselected()

    def Enable(self):
        super(ActionChoiceList,self).Enable()
        for action_choice in self.choices:
            action_choice.Enable()

    def Disable(self):
        super(ActionChoiceList,self).Disable()
        for action_choice in self.choices:
            action_choice.Disable()

    def InvalidatePathCache(self):
        for action_choice in self.choices:
            action_choice.InvalidatePathCache()

    def __getitem__(self,index):
        return self.choices[index]
