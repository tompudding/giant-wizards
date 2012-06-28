import monsters,random

class PlayerTypes:
    HUMAN     = 1
    TENTATIVE = 2
    GUNGHO    = 3


#FIXME: Sort this shit out so that we don't need strings anywhere
class PlayerColours:
    PURPLE    = 1
    RED       = 2
    YELLOW    = 3
    GREEN     = 4
    NAMES     = {PURPLE : 'purple',
                 RED    : 'red'   ,
                 YELLOW : 'yellow',
                 GREEN  : 'green' }

class Personality(object):
    def __init__(self,type):
        if type == PlayerTypes.TENTATIVE:
            self.confidence = random.random()*5
            self.emergency_mana = int(abs(random.gauss(5,2)))
            self.necessary_monsters = random.randint(2,6)
            self.desired_monsters = int(abs(random.gauss(6,2)))
        elif type == PlayerTypes.GUNGHO:
            self.confidence = 5 + random.random()*5
            self.emergency_mana = int(abs(random.randint(2,5)))
            self.necessary_monsters = random.randint(0,3)
            self.desired_monsters = int(abs(random.gauss(3,4)))
        else:
            #it's a human so don't care
            self.confidence = 1
        if self.confidence == 0:
            self.confidence = 0.1

class Player(object):
    def __init__(self,pos,type,tiles,playerType,name,colour):
        self.colour           = colour
        self.name             = name
        self.player_type      = playerType
        self.tiles            = tiles
        self.player_character = monsters.Wizard(pos,type,tiles,playerType,name,self)
        self.controlled       = [self.player_character]
        self.controlled_index = 0
        self.personality      = Personality(playerType)

        # if player_type:
        #     self.controlled.append(Goblin(pos+Point(1,1),
        #                                   'goblin',
        #                                   tiles,
        #                                   player_type,
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

    def IsPlayer(self):
        return self.player_type == PlayerTypes.HUMAN

    def StartTurn(self):
        for actor in self.controlled:
            actor.NewTurn()
        self.controlled_index = 0

    def Select(self,monster):
        new_index = self.controlled.index(monster)
        if new_index != self.controlled_index:
            self.current_controlled.Unselect()
            monster.Select()
            self.controlled_index = new_index

    def Unselect(self):
        for monster in self.controlled:
            monster.Unselect()

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
        if self.IsPlayer():
            return self.current_controlled.TakeAction(t)
        else:
            action = self.current_controlled.TakeAction(t)
            while action == False:
                self.controlled_index += 1
                if self.controlled_index == len(self.controlled):
                    #We're done, all controlled units report that no action is possible
                    self.controlled_index = 0
                    return False
                action = self.current_controlled.TakeAction(t)
            #cool, an action!
            return action

    def AddSummoned(self,monster):
        self.controlled.append(monster)

    def RemoveSummoned(self,monster):
        pos = self.controlled.index(monster)
        del self.controlled[pos]
        if self.controlled_index > pos:
            self.controlled_index -= 1
        if len(self.controlled) > 0:
            self.controlled_index %= len(self.controlled)

    def Update(self,t):
        #self.current_controlled.Update(t)
        for monster in self.controlled:
            monster.Update(t)

    def InvalidatePathCache(self):
        for actor in self.controlled:
            actor.InvalidatePathCache()
