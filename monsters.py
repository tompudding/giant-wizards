import random,action,gamedata,actor,players
from utils import Point

class Wizard(actor.Actor):
    initial_action_points = 2
    initial_move_points   = 2
    def __init__(self,pos,type,tiles,playerType,name,player):
        super(Wizard,self).__init__(pos,'wizard',tiles,playerType,name,player)
        self.controlled       = [self]
        self.controlled_index = 0
        self.player           = player
        self.action_choices   = action.ActionChoiceList(self,
                                                        Point(gamedata.screen.x*0.7,gamedata.screen.y*0.79),
                                                        ( action.MoveActionCreator    (self,action.MoveAction       ),
                                                          action.BlastActionCreator   (self,action.WizardBlastAction),
                                                          action.SummonActionCreator  (self,SummonGoblinAction      ),
                                                          action.TeleportActionCreator(self,action.TeleportAction   )))
        #move is special so make a shortcut for it
        self.move = self.action_choices[0]
        self.action_choices.Disable(self.tiles)
        #This is just for AI players, I need to split them into different classes really
        self.blast_action_creator = action.BlastActionCreator(self,action.WizardBlastAction)
        self.summon_goblin_creator = action.SummonActionCreator(self,SummonGoblinAction)
        self.move_action_creator = action.MoveActionCreator(self,action.MoveAction)

    def TakeAction(self,t):
        if len(self.action_list) == 0 and self.IsPlayer():
            return None

        if not self.IsPlayer() and len(self.action_list) == 0:
            #For a computer player, decide what to do
            #regular players populate this list themselves

            #Find the nearest enemy
            enemies = []
            for player in self.tiles.wizards:
                for enemy in player.controlled:
                    if enemy.player is self.player:
                        continue
                    #offset = utils.WrapDistance(enemy.pos,self.pos,self.tiles.width)
                    #distance = offset.length()
                    path = self.tiles.PathTo(self.pos,enemy.pos)
                    if path == None:
                        cost = (enemy.pos-self.pos).length()
                    else:
                        cost = path.cost
                    enemies.append((path,cost,enemy))
            enemies.sort(lambda x,y : cmp(x[1],y[1]))
            if len(enemies) == 0:
                #wtf? There are no other wizards? the game should have ended
                return False
            path,cost,enemy = enemies[0]

            #Stand-in AI logic until the game rules are fixed. There are two types,
            # tentative wizards do:
            #  - Move away from the enemy if possible
            #  - Shoot any enemy in range
            #  - Otherwise try to summon a monster if you can, but stay above 6 mana
            #
            # gungho wizards do:
            #  - Shoot any enemy in range
            #  - Summon a Goblin if they can (but stay above 2 mana for shooting)
            #  - 
            if self.player_type == players.PlayerTypes.TENTATIVE:
                if self.move_points > 0:
                    #Go away from the nearest enemy
                    opposite_point = enemy.pos + Point(self.tiles.width/2,0)
                    if enemy.pos.y < self.tiles.height/2:
                        opposite_point.y = self.tiles.height-1
                    opposite_point.x %= self.tiles.width
                    path = self.tiles.PathTo(self.pos,opposite_point)
                    if path:
                        if self.move_action_creator.Valid(path.steps[0]):
                            self.action_list.extend( self.move_action_creator.Create(path.steps[0],t,self) )
                #We've had a chance, at moving, but maybe we decided not to?
                if len(self.action_list) == 0:
                    offset = enemy.pos-self.pos
                    if self.blast_action_creator.Valid(offset):
                        self.action_list.extend( self.blast_action_creator.Create(offset,t,self) )
                    elif self.action_points - self.summon_goblin_creator.cost >= 6:
                        #Want to summon a goblin, find the first spot that works
                        choices = sorted([p for p in self.summon_goblin_creator.valid_vectors],lambda x,y:cmp(x.length(),y.length()))
                        for point in choices:
                            if self.summon_goblin_creator.Valid(point):
                                self.action_list.extend( self.summon_goblin_creator.Create(point,t,self) )
                                break
                        else:
                            #coun't find a place to put it. pants
                            pass
            elif self.player_type == players.PlayerTypes.GUNGHO:
                if self.move_points > 0 and path:
                    if self.move_action_creator.Valid(path.steps[0]):
                        self.action_list.extend( self.move_action_creator.Create(path.steps[0],t,self) )
                #We've had a chance, at moving, but maybe we decided not to?
                if len(self.action_list) == 0:
                    offset = enemy.pos-self.pos
                    if self.blast_action_creator.Valid(offset):
                        self.action_list.extend( self.blast_action_creator.Create(offset,t,self) )
                    elif self.action_points - self.summon_goblin_creator.cost >= 2:
                        #Want to summon a goblin, find the first spot that works
                        choices = sorted([p for p in self.summon_goblin_creator.valid_vectors],lambda x,y:cmp(x.length(),y.length()))
                        for point in choices:
                            if self.summon_goblin_creator.Valid(point):
                                self.action_list.extend( self.summon_goblin_creator.Create(point,t,self) )
                                break
                        else:
                            #coun't find a place to put it. pants
                            pass
                
        if len(self.action_list) == 0:
            #we failed to think of anything to do, so this guy is done
            return False
        return self.action_list.pop(0)


    def Damage(self,value):
        self.health -= value
        self.health_text.SetText('%d' % self.health)
        if self.health <= 0:
            self.Kill()

    def Kill(self):
        self.quad.Delete()
        self.health_text.Delete()
        self.tiles.RemoveWizard(self)

class Goblin(actor.Actor):
    initial_action_points = 0
    initial_move_points   = 3
    def __init__(self,pos,type,tiles,playerType,name,caster):
        super(Goblin,self).__init__(pos,type,tiles,playerType,name,caster.player)
        self.caster = caster
        self.ignore_monsters = 0.75 if self.player_type == players.PlayerTypes.TENTATIVE else 0.25
        self.ignore_monsters = True if random.random() < self.ignore_monsters else False
        self.action_choices = action.ActionChoiceList(self,
                                                      Point(gamedata.screen.x*0.7,gamedata.screen.y*0.81),
                                                      [action.MoveActionCreator   (self,action.MoveAction)])
        self.move = self.action_choices[0]
        for a in self.action_choices:
            a.Disable()
        self.move_action_creator = action.MoveActionCreator(self,action.MoveAction)

    def Damage(self,value):
        self.health -= value
        self.health_text.SetText('%d' % self.health)
        if self.health <= 0:
            self.quad.Delete()
            self.health_text.Delete()
            self.tiles.RemoveActor(self)
            self.caster.player.RemoveSummoned(self)

    def TakeAction(self,t):
        if len(self.action_list) == 0 and self.IsPlayer():
            return None

        if not self.IsPlayer() and len(self.action_list) == 0:
            #For a computer player, decide what to do
            #regular players populate this list themselves

            #Find the nearest enemy
            enemies = []
            for player in self.tiles.wizards:
                for enemy in player.controlled:
                    if enemy.player is self.player:
                        continue
                    if self.ignore_monsters and not isinstance(enemy,Wizard):
                        continue
                    #offset = utils.WrapDistance(enemy.pos,self.pos,self.tiles.width)
                    #distance = offset.length()
                    path = self.tiles.PathTo(self.pos,enemy.pos)
                    if path == None:
                        cost = (enemy.pos-self.pos).length()
                    else:
                        cost = path.cost
                    enemies.append((path,cost,enemy))
            enemies.sort(lambda x,y : cmp(x[1],y[1]))
            if len(enemies) == 0:
                #wtf? There are no other wizards? the game should have ended
                return False
            path,cost,enemy = enemies[0]
            if self.move_points > 0 and path:
                if self.move_action_creator.Valid(path.steps[0]):
                    self.action_list.extend( self.move_action_creator.Create(path.steps[0],t,self) )
                       
        if len(self.action_list) == 0:
            #we failed to think of anything to do, so this guy is done
            return False
        return self.action_list.pop(0)

class SummonGoblinAction(action.SummonMonsterAction):
    name         = 'Summon Goblin'
    Monster      = Goblin
    monster_type = 'goblin'
