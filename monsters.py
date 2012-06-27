import random,action,actor,players,utils
from utils import Point

class Wizard(actor.Actor):
    initial_stats = actor.Stats(attack  = 4,
                                defence = 2,
                                move    = 2,
                                health  = 8,
                                mana    = 2)
    max_mana     = 1000
    def __init__(self,pos,wizardType,tiles,playerType,name,player):
        super(Wizard,self).__init__(pos,'wizard',tiles,playerType,name,player)
        self.controlled       = [self]
        self.controlled_index = 0
        self.player           = player
        if self.IsPlayer():
            self.action_choices   = action.ActionChoiceList(self.options_box,
                                                            self,
                                                            Point(0,0),
                                                            Point(1,0.9),
                                                            ( action.MoveActionCreator    (self,[action.MoveAction]       ),
                                                              action.BlastActionCreator   (self,[action.WeakWizardBlastAction,
                                                                                                 action.WizardBlastAction,
                                                                                                 action.PowerfulWizardBlastAction,
                                                                                                 action.EpicWizardBlastAction]),
                                                              action.SummonActionCreator  (self,[SummonGoblinRuntAction,
                                                                                                 SummonGoblinWarriorAction,
                                                                                                 SummonGoblinShamanAction,
                                                                                                 SummonGoblinLordAction]),
                                                              action.TeleportActionCreator(self,[action.TeleportAction,
                                                                                                 action.RefinedTeleportAction])))
            self.move = self.action_choices[0]
            self.action_choices.Disable()
        else:
            self.blast_action_creator  = action.BlastActionCreator(self,[action.WeakWizardBlastAction,
                                                                         action.WizardBlastAction,
                                                                         action.PowerfulWizardBlastAction,
                                                                         action.EpicWizardBlastAction])
            self.summon_goblin_creator = action.SummonActionCreator(self,[SummonGoblinRuntAction,
                                                                          SummonGoblinWarriorAction,
                                                                          SummonGoblinShamanAction,
                                                                          SummonGoblinLordAction])
            self.teleport_action_creator = action.TeleportActionCreator(self,[action.TeleportAction,
                                                                      action.RefinedTeleportAction])
            self.move_action_creator   = action.MoveActionCreator(self,[action.MoveAction])
            self.ai_actions            = [self.blast_action_creator,self.summon_goblin_creator,self.move_action_creator]
            self.move = self.move_action_creator
        #move is special so make a shortcut for it
        
        #This is just for AI players, I need to split them into different classes really
        

    def TakeAction(self,t):
        if len(self.action_list) == 0 and self.IsPlayer():
            return None

        if not self.IsPlayer() and len(self.action_list) == 0:
            #For a computer player, decide what to do
            #regular players populate this list themselves
            self.InvalidatePathCache()

            #Find the nearest enemy
            
            enemies = []
            danger_score = 0.
            away_vector  = Point(0,0)
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
                    if cost < 6:
                        danger_score += (enemy.stats.attack + enemy.stats.health)/cost
                        away_vector -= (enemy.pos - self.pos)
                    enemies.append((path,cost,enemy))
            enemies.sort(lambda x,y : cmp(x[1],y[1]))
            if len(enemies) == 0:
                #wtf? There are no other wizards? the game should have ended
                return False
            path,cost,enemy = enemies[0]
            danger_score /= float(self.player.personality.confidence)
            print self.name,danger_score,danger_score/self.player.personality.confidence
            if danger_score > 4:
                #we want to leave
                target = self.pos + away_vector
                away_path = None
                for adjust in utils.Spiral(15):
                    final_target = target + adjust
                    away_path = self.tiles.PathTo(self.pos,final_target)
                    if away_path:
                        break
                if away_path:
                    if self.stats.move > 0:
                        #walk that way
                         if self.move_action_creator.Valid(away_path.steps[0]):
                            self.action_list.extend( self.move_action_creator.Create(away_path.steps[0],t,self) )
                    elif self.stats.mana > 0 and danger_score > 6:
                        #try a teleport
                        if self.stats.mana > self.teleport_action_creator.actions[1].cost*2:
                            target_action = 1
                        elif self.stats.mana > self.teleport_action_creator.actions[0].cost:
                            target_action = 0
                        else:
                            #we can't do a teleport
                            target_action = None
                        if target_action != None:
                            self.teleport_action_creator.SetAction(target_action)
                            offset = final_target - self.pos
                            if not self.teleport_action_creator.Valid(offset):
                                #shit, we can't teleport there for some reason, let's try others in the same direction
                                candidates = utils.Brensenham(final_target,self.pos,self.tiles.width)
                                for point in candidates:
                                    if self.teleport_action_creator.Valid(point - self.pos):
                                        final_target = point
                                        offset = final_target - self.pos
                                        break
                                else:
                                    offset = None
                            if offset != None:
                                #Woop can teleport
                                self.action_list.extend( self.teleport_action_creator.Create(offset,t,self) )
            else:
                #Not too dangerous, so attack!
                #Teleports are cool for getting in striking distance quickly If we've got enough mana left over to
                #strike, and we can get in there, lets give it a go
                offset = enemy.pos - self.pos

                if offset.length() < 10:
                    if self.stats.mana > self.teleport_action_creator.actions[1].cost*2:
                        target_action = 1
                    elif self.stats.mana > self.teleport_action_creator.actions[0].cost*2:
                        target_action = 0
                    else:
                        #we we don't want to do a teleport
                        target_action = None
                    if target_action != None:
                        self.teleport_action_creator.SetAction(target_action)
                        #We can't teleport right onto him, try a spiral
                        for adjust in utils.Spiral(16):
                            if self.teleport_action_creator.Valid(offset + adjust):
                                self.action_list.extend( self.teleport_action_creator.Create(offset + adjust,t,self) )
                            break

                if len(self.action_list) == 0:
                    #Not teleporting, maybe we want to move
                    if self.stats.move > 0 and path:
                        if self.move_action_creator.Valid(path.steps[0]):
                            self.action_list.extend( self.move_action_creator.Create(path.steps[0],t,self) )


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
            # if self.player_type == players.PlayerTypes.TENTATIVE:
            #     if self.stats.move > 0:
            #         #Go away from the nearest enemy
            #         opposite_point = enemy.pos + Point(self.tiles.width/2,0)
            #         if enemy.pos.y < self.tiles.height/2:
            #             opposite_point.y = self.tiles.height-1
            #         opposite_point.x %= self.tiles.width
            #         path = self.tiles.PathTo(self.pos,opposite_point)
            #         if path:
            #             if self.move_action_creator.Valid(path.steps[0]):
            #                 self.action_list.extend( self.move_action_creator.Create(path.steps[0],t,self) )
            #     #We've had a chance, at moving, but maybe we decided not to?
            #     if len(self.action_list) == 0:
            #         offset = enemy.pos-self.pos
            #         if self.blast_action_creator.Valid(offset):
            #             self.action_list.extend( self.blast_action_creator.Create(offset,t,self) )
            #         elif self.stats.mana - self.summon_goblin_creator.cost >= 6:
            #             #Want to summon a goblin, find the first spot that works
            #             choices = sorted([p for p in self.summon_goblin_creator.valid_vectors],lambda x,y:cmp(x.length(),y.length()))
            #             for point in choices:
            #                 if self.summon_goblin_creator.Valid(point):
            #                     self.action_list.extend( self.summon_goblin_creator.Create(point,t,self) )
            #                     break
            #             else:
            #                 #coun't find a place to put it. pants
            #                 pass
            # elif self.player_type == players.PlayerTypes.GUNGHO:
            #     if self.stats.move > 0 and path:
            #         if self.move_action_creator.Valid(path.steps[0]):
            #             self.action_list.extend( self.move_action_creator.Create(path.steps[0],t,self) )
            #     #We've had a chance, at moving, but maybe we decided not to?
            #     if len(self.action_list) == 0:
            #         offset = enemy.pos-self.pos
            #         if self.blast_action_creator.Valid(offset):
            #             self.action_list.extend( self.blast_action_creator.Create(offset,t,self) )
            #         elif self.stats.mana - self.summon_goblin_creator.cost >= 2:
            #             #Want to summon a goblin, find the first spot that works
            #             choices = sorted([p for p in self.summon_goblin_creator.valid_vectors],lambda x,y:cmp(x.length(),y.length()))
            #             for point in choices:
            #                 if self.summon_goblin_creator.Valid(point):
            #                     self.action_list.extend( self.summon_goblin_creator.Create(point,t,self) )
            #                     break
            #             else:
            #                 #coun't find a place to put it. pants
            #                 pass
                
        if len(self.action_list) == 0:
            #we failed to think of anything to do, so this guy is done
            return False
        return self.action_list.pop(0)


    def KillFinal(self):
        self.tiles.RemoveWizard(self)

class Goblin(actor.Actor):
    initial_stats = None #this is abstract
  
    actionchoice_list = [(action.MoveActionCreator,[action.MoveAction])]
    def __init__(self,pos,goblin_type,tiles,playerType,name,caster):
        super(Goblin,self).__init__(pos,goblin_type,tiles,playerType,name,caster.player)
        self.caster = caster
        self.ignore_monsters = 0.75 if self.player_type == players.PlayerTypes.TENTATIVE else 0.25
        self.ignore_monsters = True if random.random() < self.ignore_monsters else False
        if self.IsPlayer():
            self.action_choices = action.ActionChoiceList(self.options_box,
                                                          self,
                                                          Point(0,0),
                                                          Point(1,0.9),
                                                          [creator(self,types) for creator,types in self.actionchoice_list])
            self.action_choices.Disable()
            self.move = self.action_choices[0]
            for a in self.action_choices:
                a.Disable()
        else:
            self.move_action_creator = action.MoveActionCreator(self,[action.MoveAction])
            self.ai_actions = [self.move_action_creator]

    def KillFinal(self):
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
            if self.stats.move > 0 and path:
                if self.move_action_creator.Valid(path.steps[0]):
                    self.action_list.extend( self.move_action_creator.Create(path.steps[0],t,self) )
                       
        if len(self.action_list) == 0:
            #we failed to think of anything to do, so this guy is done
            return False
        return self.action_list.pop(0)

class GoblinRunt(Goblin):
    initial_stats = actor.Stats(attack  = 2,
                                defence = 2,
                                move    = 1,
                                health  = 3,
                                mana    = 0)                
    name = 'Goblin Runt'

class GoblinWarrior(Goblin):
    initial_stats = actor.Stats(attack  = 4,
                                defence = 3,
                                move    = 3,
                                health  = 6,
                                mana    = 0)
    name = 'Goblin Warrior'

class GoblinShaman(Goblin):
    initial_stats = actor.Stats(attack  = 2,
                                defence = 1,
                                move    = 2,
                                health  = 4,
                                mana    = 1)
    max_mana          = 6
    name              = 'Goblin Shaman'
    actionchoice_list = [(action.MoveActionCreator,[action.MoveAction]),
                         (action.BlastActionCreator,[action.WeakWizardBlastAction])]

class GoblinLord(Goblin):
    initial_stats = actor.Stats(attack  = 6,
                                defence = 4,
                                move    = 4,
                                health  = 14,
                                mana    = 0)
    name = 'Goblin Lord'

class SummonGoblinAction(action.SummonMonsterAction):
    generic_name = 'Summon Goblin'

class SummonGoblinRuntAction(SummonGoblinAction):
    cost         = 2
    description  = 'A weak and stunted goblin. Perhaps its powerful stench will intimidate opponents.'
    name         = 'Summon Goblin Runt'
    Monster      = GoblinRunt
    monster_type = 'goblin_runt'
    stats        = [(stat_name,getattr(Monster.initial_stats,stat_name)) for stat_name in 'attack','defence','move','health','mana']

class SummonGoblinWarriorAction(SummonGoblinAction):
    cost         = 4
    description  = 'The prime of their tribe\'s arena, this goblin will fight to the death for you, and it will probably take some enemies out with it'
    name         = 'Summon Goblin Warrior'
    Monster      = GoblinWarrior
    monster_type = 'goblin_warrior'
    stats        = [(stat_name,getattr(Monster.initial_stats,stat_name)) for stat_name in 'attack','defence','move','health','mana']

class SummonGoblinShamanAction(SummonGoblinAction):
    description  = 'Goblins are not usually magical by nature, so this one is something of a rarity. Use it well'
    cost         = 5
    name         = 'Summon Goblin Shaman'
    Monster      = GoblinShaman
    monster_type = 'goblin_shaman' 
    stats        = [(stat_name,getattr(Monster.initial_stats,stat_name)) for stat_name in 'attack','defence','move','health','mana']

class SummonGoblinLordAction(SummonGoblinAction):
    description  = 'Whole tribes give feality to this mighty goblin, who used his/her prodigious strength and cunning to become Lord of the goblins.'
    cost         = 8
    name         = 'Summon Goblin Lord'
    Monster      = GoblinLord
    monster_type = 'goblin_lord'
    stats        = [(stat_name,getattr(Monster.initial_stats,stat_name)) for stat_name in 'attack','defence','move','health','mana']
