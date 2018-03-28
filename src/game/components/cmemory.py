from constants import *
import data
import vector2

from components.cstore import ComponentStore

# module level
DEBUG=False
class CMemory:
    def __init__(self, dim,agent):
        self.dim=dim
        self.memory = {
                     (0,0): {(0,0):{},
                             (0,1):{},
                             (1,0):{},
                             (1,1):{},
                             },
                     (0,1): {(0,0):{},
                             (0,1):{},
                             (1,0):{},
                             (1,1):{},
                             },
                     (1,0): {(0,0):{},
                             (0,1):{},
                             (1,0):{},
                             (1,1):{},
                             },
                     (1,1): {(0,0):{},
                             (0,1):{},
                             (1,0):{},
                             (1,1):{},
                             },
                     }

        self.last_pos=None
    def distance(self,new_pos,check_pos=None):
        if(check_pos!=None):
            a=check_pos
        else:
            a = self.last_pos
        b=new_pos
        final=a - b
        return final.magnitude()
    def printQuad(self,mem):
        grid=self.memory
        for a_1 in range(0,2):
            for b_1 in range(0,2):
                grid1=grid[(a_1,b_1)]
                for a_2 in range(0,2):
                    for b_2 in range(0,2):
                        grid2=grid1[(a_2,b_2)]
                        print("Outer Quad:{},{} Inner Quad:{},{} and it contains {}".format(a_1,b_1,a_2,b_2, grid2))
    def remember(self, target_tid):
        grid=self.memory
        for a_1 in range(0,2):
            for b_1 in range(0,2):
                grid1=grid[(a_1,b_1)]
                for a_2 in range(0,2):
                    for b_2 in range(0,2):
                        grid2=grid1[(a_2,b_2)]
                        if target_tid in grid2:
                            for ent in grid2[target_tid]:
                                return ent




class ComponentStoreMemory(ComponentStore):
    def add(self, eid, dim,agent):
        return self.addc(eid, CMemory(dim,agent))

    def update(self):
        for eid, mem in self.all():
            agent = self.world.entities.get(eid)
            if mem.last_pos !=None:
                new_pos=mem.distance(agent.pos)
            else:
                new_pos=data.awareness[agent.tid]
            if(new_pos>=200):
                for t_eid,ent in  self.world.entities_within_range(eid,200):
                    grid=mem.memory
                    entity_pos=ent.pos.xy()
                    if (entity_pos[0]) > (mem.dim[0]/2):
                        if entity_pos[1] > (mem.dim[1] / 2):
                            grid=grid[(1,1)]
                        else:
                            grid=grid[(1,0)]
                    else:
                        if entity_pos[1]> (mem.dim[1]/2):
                            grid= grid[(0,1)]
                        else:
                            grid=grid[(0,0)]

  #####################################################################
  #########################   SMALLER GRID   ##########################
  #####################################################################

                    if (entity_pos[0]) > (mem.dim[0] / 4):
                        if entity_pos[1] > (mem.dim[1] / 4):
                            grid= grid[(1,1)]
                        else:
                            grid= grid[(1,0)]
                    else:
                        if entity_pos[1] > (mem.dim[1] / 4):
                            grid= grid[(0,1)]
                        else:
                            grid= grid[(0,0)]

                    if ent.tid in grid:
                        if ent.eid in grid[ent.tid]:
                            x=1
                        else:
                            grid[ent.tid].append(ent.eid)
                    else:
                        grid[ent.tid]=[(ent.eid)]

                    mem.last_pos=agent.pos
