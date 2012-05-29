import monsters

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

class Player(object):
    def __init__(self,pos,type,tiles,playerType,name,colour):
        self.colour           = colour
        self.name             = name
        self.player_type      = playerType
        self.tiles            = tiles
        self.player_character = monsters.Wizard(pos,type,tiles,playerType,name,self)
        self.controlled       = [self.player_character]
        self.controlled_index = 0

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
        self.current_controlled.Update(t)
