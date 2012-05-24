import os,sys
import utils
from utils import Point,GridCoordsY,GridCoordsX,GridCoords,WorldCoords
from pygame.locals import *
from OpenGL.GL import *
import texture,numpy,random,perlin,wizard,pygame,main_menu

gamedata = None

class TileData(object):
    IMPASSABLE = 1000
    def __init__(self,pos,name,movement_cost,tiles):
        self.pos           = pos
        self.name          = name
        self.movement_cost = movement_cost
        self.actor         = None
        self.tiles         = tiles

    def GetActor(self):
        return self.actor

    def SetActor(self,actor):
        self.tiles.InvalidateCache()
        self.actor = actor

    def Empty(self):
        return self.actor == None

    def Impassable(self):
        return self.movement_cost == self.IMPASSABLE

    def MovementCost(self,ignore = None):
        a = 0  
        
        if self.actor:
            if self.actor not in ignore:
                return TileData.IMPASSABLE
        return self.movement_cost


class Viewpos(object):
    def __init__(self,point,tiles):
        self.pos = point
        self.tiles = tiles
        self.NoTarget()

    def NoTarget(self):
        self.target        = None
        self.target_change = None
        self.start_point   = None
        self.target_time   = None
        self.start_time    = None

    def Set(self,point):
        self.pos = point
        self.NoTarget()

    def SetTarget(self,point,t,rate=2):
        self.target = point
        self.target_change = utils.WrapDistance(self.target,self.pos,self.tiles.width*gamedata.tile_dimensions.x)
        self.start_point   = self.pos
        self.start_time    = t
        self.duration      = self.target_change.length()/rate
        if self.duration < 200:
            self.duration = 200
        self.target_time   = self.start_time + self.duration

    def HasTarget(self):
        return self.target != None

    def Get(self):
        return self.pos

    def Update(self,t):
        if self.target:
            if t >= self.target_time:
                self.pos = self.target
                #print 'f',self.start_point,self.target,t,'[%d,%d]' % (self.start_time,self.target_time),self.pos
                self.NoTarget()
            elif t < self.start_time: #I don't think we should get this
                return
            else:
                partial = float(t-self.start_time)/self.duration
                partial = partial*partial*(3 - 2*partial) #smoothstep
                self.pos = (self.start_point + (self.target_change*partial)).to_int()
                #print 'p',self.start_point,self.target,t,'[%d,%d]' % (self.start_time,self.target_time),self.pos
        
class TileHighlights(object):
    def __init__(self,tiles,size):
        self.tiles = tiles
        self.size  = size
        self.quads = [utils.Quad(gamedata.quad_buffer,tc = self.tex_coords['highlight']) for i in xrange(100)]
        for q in self.highlight_quads:
            q.Disable()

class ControlBox(texture.UIElement):
    def __init__(self,bl,tr,colour):
        self.bl       = bl
        self.tr       = tr
        self.size     = tr-bl
        self.colour   = colour
        self.ui_box   = texture.BoxUI(bl,
                                      tr,
                                      colour)
        self.buttons  = {}
        self.elements = [self.ui_box]

    def AddButton(self,text,pos,callback):
        button = texture.TextButtonUI(text,self.bl+(self.size*pos),callback=callback)
        button.level = 2
        self.buttons[text] = button
        self.elements.append(button)

    def Register(self,tiles,level):
        for element in self.elements:
            tiles.RegisterUIElement(element,level+0.1 if isinstance(element,texture.TextButtonUI) else level)
        
    def MakeSelectable(self):
        for element in self.elements:
            element.MakeSelectable()

    def MakeUnselectable(self):
        for element in self.elements:
            element.MakeUnselectable()

class Tiles(object):
    def __init__(self,atlas,tiles_name,data_filename,map_size):
        self.atlas = atlas
        self.tiles_name = tiles_name
        self.dragging = None
        self.map_size = map_size
        self.width = map_size[0]
        self.height = map_size[1]
        self.wizards = []
        self.current_player = None
        self.current_player_index = 0
        self.selected_player = None
        self.uielements = {}
        self.hovered_ui = None
        self.current_action = None
        self.player_action = None
        self.gameover = False
        self.last_time = 0
        self.pathcache = {}

        self.control_box = ControlBox(Point(gamedata.screen.x*0.7,gamedata.screen.y*0.05),
                                      Point(gamedata.screen.x*0.95,gamedata.screen.y*0.27),
                                      (0,0,0,0.6))
        self.control_box.AddButton('End Turn',Point(0.3,0.15),self.EndTurn)
        self.control_box.AddButton('Centre',Point(0.3,0.6),self.CentreSelected)

        self.control_box.Register(self,1)
        self.control_box.MakeSelectable()
        
        gamedata.map_size = self.map_size
        
        #cheat by preallocating enough quads for the tiles. We want them to be rendered first because it matters for 
        #transparency, but we can't actually fill them in yet because we haven't processed the files with information
        #about them yet.
        for i in xrange(map_size[0]*map_size[1]):
            x = utils.Quad(gamedata.quad_buffer)
        
        #Read the tile data from the tiles.data file
        data = {}
        gamedata.tile_dimensions = Point(48,48)
        with open(data_filename) as f:
            for line in f:
                line = line.split('#')[0].strip()
                if ':' in line:
                    name,values = [v.strip() for v in line.split(':')]
                    data[name] = [int(v.strip()) for v in values.split(',')]
               
        self.tex_coords = {}
        for name,(x,y,w,h) in data.iteritems():
            top_left_x = float(x*gamedata.tile_dimensions.x)/self.atlas.Subimage(self.tiles_name).size.x
            top_left_y = float(self.atlas.Subimage(self.tiles_name).size.y - y*gamedata.tile_dimensions.y)/self.atlas.Subimage(self.tiles_name).size.y
            bottom_right_x = top_left_x + float(w*gamedata.tile_dimensions.x)/self.atlas.Subimage(self.tiles_name).size.x
            bottom_right_y = top_left_y - float(h*gamedata.tile_dimensions.y)/self.atlas.Subimage(self.tiles_name).size.y
            tc = numpy.array(((top_left_x,bottom_right_y),(top_left_x,top_left_y),(bottom_right_x,top_left_y),(bottom_right_x,bottom_right_y)),numpy.float32)
            self.atlas.TransformCoords(self.tiles_name,tc)
            self.tex_coords[name] = tc

            
        self.noise = perlin.SimplexNoise(256)

        #Set up the map
        self.map = []
        for x in xrange(0,map_size[0]):
            col = []
            for y in xrange(0,map_size[1]):
                w,h = gamedata.tile_dimensions
                noise_level = self.noise.noise2(x*0.1,y*0.1)
                if noise_level >= 0.8:
                    type = 'mountain'
                    movement_cost = TileData.IMPASSABLE
                elif noise_level >= 0.6:
                    type = 'tree'
                    movement_cost = 1
                elif noise_level >= 0.2:
                    type = 'grass'
                    movement_cost = 1
                else:
                    type = 'water'
                    movement_cost = 2
                col.append( TileData(Point(x,y),type,movement_cost,self))
            self.map.append(col)

        #sort out the coasts
        for x in xrange(len(self.map)):
            for y in xrange(len(self.map[x])):
                tile = self.map[x][y]
                if tile.name == 'water':
                    #look to the left
                    coast_type = []
                    for (a,b),name in (((-1,0),'left'),
                                     ((0,1),'top'),
                                     ((1,0),'right'),
                                     ((0,-1),'bottom')):
                        if y+b >= self.height or y+b < 0:
                            type = 'water'
                        else:
                            type = self.map[(x+a+self.width)%self.width][y+b].name
                        if type in ['grass','mountain','tree']:
                            coast_type.append(name)
                    coast_type.sort()
                    if len(coast_type) > 0:
                        self.map[x][y].name = 'coast_' + '_'.join(coast_type)
                        

        #Fill in the fixed vertices for the tiles
        index = 0
        for col in self.map:
            for tile_data in col:
                world = WorldCoords(tile_data.pos)
                #world.y -= (gamedata.tile_dimensions.y/2)
                #world.y += self.height*gamedata.tile_dimensions.y/2 #make sure it's all above zero
                tex_coords=self.tex_coords[tile_data.name]
                temp_quad = utils.Quad(gamedata.quad_buffer,tc = tex_coords,index = index)
                index += 4
                temp_quad.SetVertices(world,world + gamedata.tile_dimensions,0)
                

        self.text = texture.TextObject('a',gamedata.text_manager)
        self.text.Position(Point(10,10),0.5)
        self.viewpos = Viewpos(Point(0,0),self)
        self.selected      = None
        self.selected_quad = utils.Quad(gamedata.quad_buffer,tc = self.tex_coords['selected'])
        #self.highlights    = TileHighlights(100)
        

    def ValidViewpos(self,viewpos):
        #viewpos = list(viewpos)
        top_left= Point(0,gamedata.screen.y)
        top_right = gamedata.screen
        bottom_right = Point(gamedata.screen.x,0)
        #check the bottom 
        viewgrid = GridCoords(viewpos.to_float())
        if viewgrid.y < 0:
            viewgrid.y = 0
            viewpos = WorldCoords(viewgrid).to_int()

        #now the left
        viewgrid = GridCoords((viewpos+top_left).to_float())
        if viewgrid.x < -(self.width/4):
            viewgrid.x += self.width
            viewpos = (WorldCoords(viewgrid).to_int())-top_left

        #right
        viewgrid = GridCoords((viewpos+bottom_right).to_float())
        if viewgrid.x > (self.width + gamedata.screen.x/gamedata.tile_dimensions.x):
            viewgrid.x -= self.width
            viewpos = (WorldCoords(viewgrid).to_int())-bottom_right

        #top
        viewgrid = GridCoords((viewpos+top_right).to_float())
        if viewgrid.y >= self.height:
            viewgrid.y = self.height
            viewpos = (WorldCoords(viewgrid).to_int())-top_right-Point(0,1)
        
        return viewpos

    def NextPlayer(self):
        if self.current_player == None:
            self.current_player_index = 0
            self.current_player = self.wizards[0]
        else:
            self.current_player_index += 1
            self.current_player_index %= len(self.wizards)
            self.current_player = self.wizards[self.current_player_index]
        self.selected_player = None
        self.text.SetText('It\'s %s\'s turn.' % (self.current_player.name))
        if self.current_player.IsPlayer():
            self.control_box.MakeSelectable()
        else:
            self.control_box.MakeUnselectable()
        self.current_player.StartTurn()
        #as we don't have any monsters or anything, there's no need to allow the player to choose which of his
        #guys to select, as he only has one!
        if self.current_player.IsPlayer():
            self.SelectNextPlayerControlled(0)
        else:
            self.CentreCurrent()

    def SelectNextPlayerControlled(self,adjust):
        if not self.current_action and self.current_player.IsPlayer():
            self.selected_player = self.current_player.NextControlled(adjust)
            self.selected_player.Select()
            self.CentreSelected()
            
    def CentreSelected(self,pos = None):
        target = WorldCoords(self.selected_player.pos)-(gamedata.screen/2)
        self.viewpos.SetTarget(self.ValidViewpos(target),self.last_time)

    def CentreCurrent(self,pos = None):
        target = WorldCoords(self.current_player.pos)-(gamedata.screen/2)
        self.viewpos.SetTarget(self.ValidViewpos(target),self.last_time)
        
    def EndTurn(self,pos):
        if self.current_player.IsPlayer():
            self.current_player.EndTurn(pos)
        
    def Draw(self):
        zcoord = 0
        glBindTexture(GL_TEXTURE_2D, self.atlas.texture.texture)
        glLoadIdentity()
        glTranslate(-self.viewpos.Get().x,-self.viewpos.Get().y,0)

        if self.selected:
            world = WorldCoords(self.selected)
            self.selected_quad.SetVertices(world,world + gamedata.tile_dimensions,zcoord+1)

        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)
        glVertexPointerf(gamedata.quad_buffer.vertex_data)
        glTexCoordPointerf(gamedata.quad_buffer.tc_data)
        glColorPointer(4,GL_FLOAT,0,gamedata.quad_buffer.colour_data)

        glDrawElements(GL_QUADS,gamedata.quad_buffer.current_size,GL_UNSIGNED_INT,gamedata.quad_buffer.indices)

        #draw it again for the wrapping
        glTranslate((self.width*gamedata.tile_dimensions.x),0,0)
        glDrawElements(GL_QUADS,gamedata.quad_buffer.current_size,GL_UNSIGNED_INT,gamedata.quad_buffer.indices)

        #And the other side. It would be nice if this wasn't necessary, but we need some overlap.
        #an obvious efficiency saving would be to only draw part of it, but for now draw it all
        glTranslate((-2*self.width*gamedata.tile_dimensions.x),0,0)
        glDrawElements(GL_QUADS,gamedata.quad_buffer.current_size,GL_UNSIGNED_INT,gamedata.quad_buffer.indices)

        #now draw the non-static text that moves with the board
        glVertexPointerf(gamedata.nonstatic_text_buffer.vertex_data)
        glTexCoordPointerf(gamedata.nonstatic_text_buffer.tc_data)
        glBindTexture(GL_TEXTURE_2D, gamedata.text_manager.atlas.texture.texture)
        glDrawElements(GL_QUADS,gamedata.nonstatic_text_buffer.current_size,GL_UNSIGNED_INT,gamedata.nonstatic_text_buffer.indices)

        glTranslate((self.width*gamedata.tile_dimensions.x),0,0)
        glDrawElements(GL_QUADS,gamedata.nonstatic_text_buffer.current_size,GL_UNSIGNED_INT,gamedata.nonstatic_text_buffer.indices)

        glTranslate((self.width*gamedata.tile_dimensions.x),0,0)
        glDrawElements(GL_QUADS,gamedata.nonstatic_text_buffer.current_size,GL_UNSIGNED_INT,gamedata.nonstatic_text_buffer.indices)

        #now draw the coloured tiles
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glDisable(GL_TEXTURE_2D)
        glVertexPointerf(gamedata.colour_tiles.vertex_data)
        glColorPointer(4,GL_FLOAT,0,gamedata.colour_tiles.colour_data)
        glDrawElements(GL_QUADS,gamedata.colour_tiles.current_size,GL_UNSIGNED_INT,gamedata.colour_tiles.indices)

        glTranslate((-2*self.width*gamedata.tile_dimensions.x),0,0)
        glDrawElements(GL_QUADS,gamedata.colour_tiles.current_size,GL_UNSIGNED_INT,gamedata.colour_tiles.indices)

        glTranslate((self.width*gamedata.tile_dimensions.x),0,0)
        glDrawElements(GL_QUADS,gamedata.colour_tiles.current_size,GL_UNSIGNED_INT,gamedata.colour_tiles.indices)
        #glDisableClientState(GL_VERTEX_ARRAY)
        #glDisableClientState(GL_COLOR_ARRAY)
        self.DrawUI()

    def DrawUI(self):
        glLoadIdentity()

        #glDisable(GL_TEXTURE_2D)
        #glEnableClientState(GL_VERTEX_ARRAY)
        #glEnableClientState(GL_COLOR_ARRAY)
        glVertexPointerf(gamedata.ui_buffer.vertex_data)
        glColorPointer(4,GL_FLOAT,0,gamedata.ui_buffer.colour_data)
        glDrawElements(GL_QUADS,gamedata.ui_buffer.current_size,GL_UNSIGNED_INT,gamedata.ui_buffer.indices)
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_COLOR_ARRAY)
        glEnable(GL_TEXTURE_2D)


            
    def MouseButtonDown(self,pos,button):
        if button == 3:
            self.dragging = self.viewpos.Get() + pos
        elif button == 4: #scroll_up
            self.SelectNextPlayerControlled(1)
        elif button == 5:
            self.SelectNextPlayerControlled(-1)
        
            
    def MouseButtonUp(self,pos,button):
        if button == 3:
            self.dragging = None
        if self.hovered_ui:
            self.hovered_ui.OnClick(pos,button)
        elif not self.gameover:
            if button == 1 and not self.current_action: #don't accept clicks while an actions happening
                #They pressed the left mouse button. If no-one's currently selected and they clicked on their character,
                #select them for movement
                if self.selected_player == None:
                    if self.current_player.Controls(self.hovered_player) and self.current_player.IsPlayer():
                        #select them!
                        self.selected_player = self.current_player
                        self.selected_player.Select(self.hovered_player)
                else:
                    #Are we hovering over a friendly?
                    if self.current_player.Controls(self.hovered_player) and \
                            self.current_player.IsPlayer() and \
                            (self.player_action == None or not self.player_action.FriendlyTargetable()):
                        #select them!
                        self.selected_player = self.current_player
                        self.selected_player.Select(self.hovered_player)
                        
                    elif self.player_action != None:
                        #we've selected and action like move, so tell it where they clicked
                        current_viewpos = self.viewpos.Get() + pos
                        current_viewpos.x = current_viewpos.x % (self.width*gamedata.tile_dimensions.x)
                        self.player_action.OnGridClick(utils.GridCoords(current_viewpos),button)
                     
                    #Remove the ability of the player to deselect his wizard, since we didn't get round to implementing
                    #monsters we don't need it
                    elif self.hovered_player is not self.current_player:
                        print 'unselect!'
                        self.selected_player.Unselect()
                        self.selected_player = None

    def MouseMotion(self,pos,rel):
        if self.dragging:
            new_setpos = self.dragging - pos
            self.viewpos.Set(self.ValidViewpos(self.dragging - pos))
            difference = self.viewpos.Get() - (new_setpos)
            #if difference is non-zero it means that we didn't get what we requested for some reason,
            #so we should update dragging so it still points at the right place
            self.dragging = self.viewpos.Get() + pos
            
        current_viewpos = self.viewpos.Get() + pos
        current_viewpos.x = current_viewpos.x % (self.width*gamedata.tile_dimensions.x)
        hovered_ui = self.HoveredUiElement(pos)
        if hovered_ui:
            #if we're over the ui then obviously nothing is selected
            if hovered_ui is not self.hovered_ui:
                if self.hovered_ui != None:
                    self.hovered_ui.EndHover()
                self.hovered_ui = hovered_ui
                self.hovered_ui.Hover()
            self.selected_quad.Disable()
            self.selected = None
        else:
            
            if self.hovered_ui != None:
                self.hovered_ui.EndHover()
                self.hovered_ui = None
            if not self.gameover:
                self.selected_quad.Enable() 
                selected = GridCoords(current_viewpos).to_int()
                if selected != self.selected:
                    if self.player_action != None:
                        self.player_action.MouseMotion(selected)
                self.selected = selected
                
                self.selected.x = (self.selected.x+self.width) % self.width
                if self.selected.y >= self.height: #There's one pixel row at the top that's off the table
                    self.selected.y = self.height
                tile = self.GetTile(self.selected)
                if tile:
                    self.hovered_player = tile.GetActor()
                    if self.hovered_player in self.current_player.controlled:
                        self.selected_quad.tc[0:4] = self.tex_coords['selected_hover']
                    else:
                        self.selected_quad.tc[0:4] = self.tex_coords['selected']

    def Update(self,t):
        self.last_time = t
        if self.gameover:
            return
        self.viewpos.Update(t)
        for wizard in self.wizards:
            wizard.Update(t)
        if self.current_action:
            finished = self.current_action.Update(t)
            if finished:
                self.current_action = None
                if self.player_action:
                    self.player_action.Selected()
        else:
            #Don't allow the AI to take a move until the screen has finished centering on them
            if not self.viewpos.HasTarget():
                action = self.current_player.TakeAction(t)
                if action == False:
                    self.NextPlayer()
                if action != None:
                    self.current_action = action

    def AddWizard(self,pos,type,isPlayer,name):
        target_tile = self.GetTile(pos)
        self.InvalidateCache()
        new_wizard = wizard.Player(pos,type,self,isPlayer,name)
        new_wizard.pos = pos
        self.wizards.append(new_wizard)

    def KeyDown(self,key):
        if key == pygame.locals.K_RETURN:
            if self.current_player.IsPlayer():
                self.current_player.EndTurn(Point(0,0))
        elif key == pygame.locals.K_ESCAPE:
            self.Quit(0)

    def GetTile(self,pos):
        pos.x = pos.x%self.width
        try:
            out = self.map[pos.x][pos.y]
        except IndexError:
            return None
        return out

    def RegisterUIElement(self,element,height):
        a = {}
        a[element] = True
        self.uielements[element] = height

    def RemoveUIElement(self,element):
        try:
            del self.uielements[element]
        except KeyError:
            pass

    def HoveredUiElement(self,pos):
        #not very efficient, but I only have 2 days, come on.
        match = [-1,None]
        for ui,height in self.uielements.iteritems():
            if pos in ui and ui.Selectable():
                if height > match[0]:
                    match = [height,ui]
        return match[1]

    def RemoveActor(self,actor):
        tile = self.GetTile(actor.pos)
        if tile:
            self.InvalidateCache()
            tile.SetActor(None)

    def RemoveWizard(self,wizard):
        self.RemoveActor(wizard)
        pos = [w.player_character for w in self.wizards].index(wizard)
        del self.wizards[pos]
        if len(self.wizards) == 1:
            winner = self.wizards[0]
            self.GameOver(winner)
            
    def GameOver(self,winner):
        self.gameover = True
        for element in self.uielements:
            element.Delete()
        self.uielements = {}

        self.backdrop = texture.BoxUI(Point(gamedata.screen.x*0.3,gamedata.screen.y*0.3),
                                      Point(gamedata.screen.x*0.7,gamedata.screen.y*0.7),
                                      (0,0,0,0.6))
        self.backdrop.Enable()
        self.RegisterUIElement(self.backdrop,0)
        self.win_message = texture.TextObject('%s wins!' % winner.name,gamedata.text_manager)
        self.win_message.Position(Point(gamedata.screen.x*0.35,gamedata.screen.y*0.6),0.5)
        self.return_button = texture.TextButtonUI('Return',Point(gamedata.screen.x*0.45,gamedata.screen.y*0.35),callback = self.Quit)
        self.RegisterUIElement(self.return_button,0)
        self.InvalidateCache()
        self.selected_quad.Delete()

    def Quit(self,pos):
        for element in self.uielements:
            element.Delete()
        self.uielements = []
        gamedata.ui_buffer.truncate(0)
        gamedata.quad_buffer.truncate(0)
        gamedata.nonstatic_text_buffer.truncate(0)
        gamedata.colour_tiles.truncate(0)
        gamedata.text_manager.Purge()
        glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
        gamedata.current_view = main_menu.MainMenu()
        #raise SystemExit

    def InvalidateCache(self):
        for path in self.pathcache.values():
            path.Delete()
        self.pathcache = {}

    def GetCell(self,pos):
        if pos.y < 0: #you don't get an indexerror for negative values
            return None
        if pos.x < 0:
            pos.x += len(self.map)
        elif pos.x >= len(self.map):
            pos.x -= len(self.map)
        try:
            return self.map[pos.x][pos.y]
        except IndexError:
            return None

    def PathTo(self,start,end):
        #A noddy my-first implementation of A* in python
        #update the map items with current positions of the sprites
        #they're not used normally so we can do what we like with them
        try:
            return self.pathcache[start,end]
        except KeyError:
            #oh well, it was worth a try
            pass
        if start == None or end == None:
            return None
        
        cell = self.GetCell(end)
        if cell == None:
            return None
        if cell.Impassable():
            #if we can't move into the last tile, there's no point
            return None
        if start == end:
            return None

        Closed = set()
        #open is sorted by 'F' value
        Open   = [start]
        Opend  = {start:start}
        start.g = 0
        start.h = start.DistanceHeuristic(end)
        start.f = start.h
        start.parent = None
        #get the object we're going from so we can ignore it in terms of being passable
        start_object = self.map[start.x][start.y].GetActor()
        end_object   = self.map[end.x][end.y].GetActor()
        #print 'PATH:',start,',',end
        while True:
            if len(Open) == 0: #no path, boo
                return None
            current = Open.pop(0)
            del Opend[current]
            if current == end:# or len(Open) > 100:
                #yay, we're finished
                path = utils.Path(current,self.tex_coords,len(self.map))
                self.pathcache[start,end] = path
                return path
            elif current != start:
                p = start,current
                path = utils.Path(current,self.tex_coords,len(self.map))
                if (p in self.pathcache and path.cost < self.pathcache[p]) or p not in self.pathcache:
                    self.pathcache[p] = path
                
                
            Closed.add(current)
            for x in xrange(current.x-1,current.x+2):
                #if x < 0 or x >= len(self.map):
                #    continue
                if x < 0:
                    x += len(self.map)
                elif x >= len(self.map):
                    x -= len(self.map)
                for y in xrange(current.y-1,current.y+2):
                    if y < 0 or y >= len(self.map[x]):
                        continue

                    target = Point(x,y)
                    
                    if target in Closed:
                        continue
                    if target == current:
                        continue

                    cost = 0
                    for tile in (target,):
                        cell = self.map[tile.x][tile.y]
                        this_cost = cell.MovementCost(ignore = (start_object,end_object))
                        if this_cost == TileData.IMPASSABLE:
                            cost = this_cost
                            break
                        cost += this_cost

                    if cost == TileData.IMPASSABLE:
                        if target == end:
                            return None
                        continue

                    #if target != current.x and target.y != current.y:
                        #it's diagonal. It still costs the same, but pretend
                        #otherwise so that h/v movement is preferred as it looks
                        #nicer
                    #    cost *= 1.41

                    newg = current.g + cost
                    try:
                        target_new = Opend[target]
                    except KeyError:
                        target_new = None
                    
                    if target_new == None:
                        target.g    = newg
                        #Open is sorted by g+h, so find the position this goes with a binary search
                        #and put it in the right place

                        target.h = target.DistanceHeuristic(end)
                        target.f = target.g + target.h
                        target.parent = current
                        i = utils.fbisect_left(Open,target)

                        Open.insert(i,target)
                        Opend[target] = target
                    else: #target's already in open
                        target = target_new
                        if newg < target.g:
                            target.g = newg
                            target.f = target.g + target.h
                            target.parent = current

        
names = ['Purple Wizard','Red Wizard','Yellow Wizard','Green Wizard']
        

class GameWindow(object):
    def __init__(self,player_states):
        map_size = (48,24)
        self.tiles = Tiles(texture.TextureAtlas('tiles_atlas_0.png','tiles_atlas.txt'),
                           'tiles.png'  ,
                           'tiles.data' ,
                           map_size     )
        #this will get passed in eventually, but for now configure statically
        #first come up with random positions that aren't too close to each other and aren't on top of a mountain
        positions = []
        total_tried = 0
        players = [(player_states[i],names[i],i) for i in xrange(len(names)) if player_states[i] != None]
        while len(positions) < len(players):
            good_position = False
            tries = 0
            total_tried += 1
            if total_tried > 100:
                #something is wrong here
                print 'Something very wrong has happened to the map. Try again?'
                raise ValueError
            while not good_position:
                tries += 1
                if tries > 10000:
                    #maybe we've tried an unwinnable configuration? start over
                    positions = []
                    break
                pos = Point(*[random.randint(0,v-1) for v in map_size])
                target_tile = self.tiles.GetTile(pos)
                if target_tile and target_tile.name == 'mountain':
                    continue
                try:
                    for other_pos in positions:
                        if (other_pos - pos).length() < 5:
                            raise ValueError
                except ValueError:
                    continue
                positions.append(pos)
                break
                
            
        for i in xrange(len(players)):
            isplayer,name,type = players[i]
            if player_states[type] != None:
                self.tiles.AddWizard(pos  = positions[i],
                                     type = type,
                                     isPlayer = isplayer,
                                     name = name)
        self.tiles.NextPlayer()
        

    def Update(self,t):
        self.tiles.Update(t)
        self.tiles.Draw()

    def KeyDown(self,key):
        hovered_element = self.tiles
        hovered_element.KeyDown(key)

    def MouseMotion(self,pos,rel):
        hovered_element = self.tiles
        hovered_element.MouseMotion(pos,rel)

    def MouseButtonDown(self,pos,button):
        #check which element we're over at this point?
        hovered_element = self.tiles
        hovered_element.MouseButtonDown(pos,button)

    def MouseButtonUp(self,pos,button):
        #check which element we're over at this point?
        hovered_element = self.tiles
        hovered_element.MouseButtonUp(pos,button)

