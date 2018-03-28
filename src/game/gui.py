##########################
#  Graphical Interface
##########################
import sys
import pygame
import data
from vector2 import vector2

screen = None
halfport = None
font = None
focus_position = None

MSG_LEFT = 10
MSG_TOP = 15
messages = ["", "", ""]


# singleton init on import
def init(dim):
    global screen, halfport, font
    pygame.init()
    screen = pygame.display.set_mode(dim)
    halfport = vector2([(int(d/2)) for d in dim])
    pygame.display.set_caption( "Survival Simulation" )
    # initialize font; must be called after 'pygame.init()' to avoid 'Font not Initialized' error
    font = pygame.font.SysFont("monospace", 15)



def set_msg(n, text):
    global messages
    messages[n] = text

# system updates
def update_input():
    pygame.event.pump()
    for evt in pygame.event.get():
        if evt.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif evt.type == pygame.KEYDOWN and evt.key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()
        elif evt.type == pygame.KEYDOWN and evt.key == pygame.K_SPACE:
            return True
    return False

def update_screen(world, pid):
    global screen, focus_position
    screen.fill((255,255,0))
    # offset by pid position
    focus = world.entities.get(pid)
    if focus is not None:
        focus_position = focus.pos

    for eid, ent in world.entities.all():
        draw_entity(ent.tid, ent.pos - focus_position + halfport)


    # render text
    top = MSG_TOP
    for m in messages:
        label = font.render(m, False, (255, 0, 0))
        screen.blit(label, (MSG_LEFT, top))
        top += MSG_TOP

    pygame.display.flip()

def draw_entity(tid, loc):
    d = data.render[tid]
    if d['shape'] == 'circle':
        pygame.draw.circle(screen, d['color'], loc.intxy(), d['size'])
    elif d['shape'] == 'ellipse':
        pygame.draw.circle(screen, d['color'], pygame.Rect(loc.intxy(), (d['size'],d['size']*0.65)))
    elif d['shape'] == 'square':
        pygame.draw.rect(screen, d['color'], pygame.Rect(loc.intxy(), (d['size'], d['size'])))
    else:
        pygame.draw.rect(screen, d['color'], pygame.Rect(loc.intxy(), (d['size'],d['size']*0.65)))


def getScreen(c):
    if screen != None:
        pygame.image.save(screen, "images/im" + str(c) + ".jpeg")

