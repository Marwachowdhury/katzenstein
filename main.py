import math

from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import random
import time
start_time = time.time()
# Camera-related variables
camera_pos = (0,500,500)

fovY = 120  # Field of view
GRID_LENGTH = 1000

player_pos = [0, 0, 0]
player_angle = 0
move_speed = 10
rot_speed = 5
player_fall_angle = 0
first_person = False
is_cheat_activated = False
scanning = True
target_locked = None
auto_gun_follow = False
view_angle = 0

# game states
lives = 5
bullets_missed = 0 # threshold 10
score = 0
is_game_over = False

class GameState:
    def __str__(self):
        self.score = 0
        self.lives = 3
        self.is_game_over = False
        self.level = 1

class Enemy:
    def __init__(self, pos, size, color, type, damage, speed, health):
        self.pos = pos
        self.size = size
        self.color = color
        self.type = type
        self.damage = damage
        self.speed = speed
        self.health = health

class Player:
    def __init__(self, pos, inventory):
        self.pos = pos
        self.inventory = inventory 
        self.base_speed = 10
        self.health = 100


class Inventory:
    def __init__(self):
        self.weapons = []
        self.power_ups = []
        self.weight = 0.0
        self.weapon_idx = -1
        self.power_up_idx = -1


class Weapon:
    def __init__(self, type, damage, pos):

        self.type = type
        self.damage = damage
        self.rounds = 0
        self.pos = pos
        self.is_equiped = False
        self.in_inventory = False

    def draw(self):
        quad = gluNewQuadric()

        glPushMatrix()

        if not self.in_inventory:
            # Draw on the ground
            glTranslatef(self.pos[0], self.pos[1], self.pos[2] + 50)
            # Lay it flat
            glRotatef(90, 0, 1, 0)

            if self.type == 'pistol':
                glColor3f(0.4, 0.4, 0.4)
                gluCylinder(quad, 5, 5, 50, 10, 10)
            elif self.type == "rifle":
                glColor3f(0.2, 0.57, 0.45)
                gluCylinder(quad, 5, 20, 100, 10, 10)
        
        if self.is_equiped:
            rad = math.radians(player_angle)

            # Forward direction (camera facing)
            fx = math.cos(rad)
            fy = math.sin(rad)
            fz = 0

            # Right direction (perpendicular)
            rx = -math.sin(rad)
            ry = math.cos(rad)
            rz = 0

            # Up direction
            ux, uy, uz = 0, 0, 1

            # ---- OFFSETS (tweak these) ----
            forward_offset = 40   # push into screen
            right_offset   = -15   # move to right
            up_offset      = -0  # move downward

            # Camera position (same as in setupCamera)
            cam_x = player_pos[0] + fx * 20
            cam_y = player_pos[1] + fy * 20
            cam_z = 100

            # Final weapon position
            wx = cam_x + fx * forward_offset + rx * right_offset + ux * up_offset
            wy = cam_y + fy * forward_offset + ry * right_offset + uy * up_offset
            wz = cam_z + fz * forward_offset + rz * right_offset + uz * up_offset

            glTranslatef(wx, wy, wz)

            # Rotate to match camera view
            glRotatef(player_angle, 0, 0, 1)

            # Tilt like FPS gun
            glRotatef(90, 1, 0, 0)
            glRotatef(-45, 0, 1, 0)

            if self.type == 'pistol':
                glColor3f(0.4, 0.4, 0.4)
                gluCylinder(quad, 5, 5, 50, 10, 10)
            elif self.type == "rifle":
                glColor3f(0.2, 0.57, 0.45)
                gluCylinder(quad, 5, 20, 100, 10, 10)
            
        glPopMatrix()

    def draw_weapon_hud(self):
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()

        gluOrtho2D(0, 1000, 0, 800)

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        quad = gluNewQuadric()

        # Position: bottom-right → slightly toward center
        glTranslatef(750, 150, 0)

        # Tilt it nicely (FPS style)
        glRotatef(30, 0, 0, 1)
        glRotatef(70, 1, 0, 0)

        glColor3f(0.4, 0.4, 0.4)

        # Draw cylinder (weapon)
        gluCylinder(quad, 10, 10, 120, 20, 20)

        glPopMatrix()

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

class PowerUp:
    def __init__(self, title, type):
        self.title = title
        self.type = type

class Level:
    pass


weapons = [
    Weapon("pistol", 10, (100, 100, 0)),
    Weapon("rifle", 20, (-200, 50, 0)),
]

inventory = Inventory()

def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(1,1,1)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    
    gluOrtho2D(0, 1000, 0, 800)

    
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def keyboardListener(key, x, y):
    global player_pos, player_angle, lives, is_game_over, bullets_missed, score, is_cheat_activated, auto_gun_follow
    import math
    rad = math.radians(player_angle)

    forward_x = math.cos(rad)
    forward_y = math.sin(rad)

    if key == b'w':
        if abs(player_pos[0] + move_speed * forward_x) < GRID_LENGTH:
            player_pos[0] += move_speed * forward_x
        if abs(player_pos[1] + move_speed * forward_y) < GRID_LENGTH:
            player_pos[1] += move_speed * forward_y

    if key == b's':
        if abs(player_pos[0] - move_speed * forward_x) < GRID_LENGTH:
            player_pos[0] -= move_speed * forward_x
        if abs(player_pos[1] - move_speed * forward_y) < GRID_LENGTH:
            player_pos[1] -= move_speed * forward_y


    if key == b'a':
        player_angle += rot_speed

    if key == b'd':
        player_angle -= rot_speed

    if key == b'f':
        for w in weapons:
            dx = player_pos[0] - w.pos[0]
            dy = player_pos[1] - w.pos[1]

            if (dx**2 + dy**2) < 10000: 
                inventory.weapons.append(w)
                w.in_inventory = True
                if inventory.weapon_idx >= 0:
                    inventory.weapons[inventory.weapon_idx].is_equiped = False
                inventory.weapon_idx += 1
                w.is_equiped = True

    if key == b"1":
        if len(inventory.weapons) > 0:
            inventory.weapon_idx = 0
            for w in inventory.weapons:
                w.is_equiped = False
            inventory.weapons[inventory.weapon_idx].is_equiped = True

    if key == b"2":
        if len(inventory.weapons) > 1:
            inventory.weapon_idx = 1
            for w in inventory.weapons:
                w.is_equiped = False
            inventory.weapons[inventory.weapon_idx].is_equiped = True

    # if key == b'r':
    #     lives = 5
    #     score = 0
    #     bullets_missed = 0
    #     is_game_over = False


def specialKeyListener(key, x, y):
    # global camera_pos
    # x, y, z = camera_pos
    
    # if key == GLUT_KEY_UP:
    #     y += 1

    # if key == GLUT_KEY_DOWN:
    #     y -=1

    # if key == GLUT_KEY_LEFT:
    #     x -= 1

    # if key == GLUT_KEY_RIGHT:
    #     x += 1

    # camera_pos = (x, y, z)
    pass


def mouseListener(button, state, x, y):
    global first_person

    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        import math

        rad = math.radians(player_angle)

        dx = math.cos(rad)
        dy = math.sin(rad)

        # spawn bullet at player position
        bx = player_pos[0]
        by = player_pos[1]

        # bullets.append(Bullet(bx, by, dx, dy))

    # if button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
    #     first_person = not first_person

def setupCamera():
    global first_person, is_cheat_activated, view_angle

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, 1.25, 0.1, 1500)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    import math

    # BASE PLAYER DIRECTION
    cam_x, cam_y, cam_z = camera_pos
    look_x, look_y, look_z = 0, 0, 0

    offset = 20

    cam_x = player_pos[0] + math.cos(math.radians(player_angle)) * offset
    cam_y = player_pos[1] + math.sin(math.radians(player_angle)) * offset

    view_angle = player_angle
    cam_z = 120

    rad = math.radians(view_angle)

    look_x = cam_x + math.cos(rad) * 100
    look_y = cam_y + math.sin(rad) * 100
    look_z = cam_z

    gluLookAt(cam_x, cam_y, cam_z,
              look_x, look_y, look_z,
              0, 0, 1)


def idle():
    glutPostRedisplay()


def draw_player(x, y, z):
    global player_fall_angle, is_game_over

    glPushMatrix()
    scale = 50
    legs_height = 40

    glTranslatef(x, y, z)

    if is_game_over:
        # gradually fall forward
        if player_fall_angle < 90:
            player_fall_angle += 1

        glRotatef(player_fall_angle, 1, 0, 0)
    else:
        glRotatef(player_angle+90, 0, 0, 1)

    glColor3f(85/255, 107/255, 47/255)
    glPushMatrix()
    glTranslatef(0, 0, scale + legs_height)
    glScalef(scale, scale * 0.5, scale * 2)
    glutSolidCube(1)
    glPopMatrix()

    # matha
    glColor3f(0, 0, 0)
    glPushMatrix()
    glTranslatef(0, 0, scale * 2.5 + legs_height)
    glutSolidSphere(scale * 0.4, 20, 20)
    glPopMatrix()

    quad = gluNewQuadric()

    # left arm
    glColor3f(1.0, 0.8, 0.6)
    glPushMatrix()
    glTranslatef(- scale * 0.8, 0, scale * 2)
    glRotatef(90, 1, 0, 0)
    gluCylinder(quad, scale * 0.15, scale * 0.15, scale * 1.2, 10, 10)
    glPopMatrix()

    # right arm
    glPushMatrix()
    glTranslatef(0 + scale * 0.8, 0, scale * 2)
    glRotatef(90, 1, 0, 0)
    gluCylinder(quad, scale * 0.15, scale * 0.15, scale * 1.2, 10, 10)
    glPopMatrix()

    # lleg
    glColor3f(0.0, 0.0, 1.0)
    glPushMatrix()
    glTranslatef(0- scale * 0.3, 0, 0)
    gluCylinder(quad, scale * 0.2, scale * 0.2, scale * 1.5, 10, 10)
    glPopMatrix()

    # rleg
    glPushMatrix()
    glTranslatef(scale * 0.3, 0, 0)
    gluCylinder(quad, scale * 0.2, scale * 0.2, scale * 1.5, 10, 10)
    glPopMatrix()

    

    glPopMatrix() 


def showScreen():

    global is_game_over, lives, bullets_missed, score
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity() 
    glViewport(0, 0, 1000, 800) 

    setupCamera()
    
    if not is_game_over:
        draw_text(10, 770, f"Player Life Remaining: {lives}")
        draw_text(10, 740, f"Game Score: {score}")
        current_weapon = inventory.weapons[inventory.weapon_idx].type if inventory.weapon_idx > -1 else "N/A"
        draw_text(10, 710, f"Current Weapon: {current_weapon}")
    else:
        draw_text(10, 770, f"Game is over. Your score is {score}")
        draw_text(10, 740, f"Press \"R\" to restart the game")

    # draw_player(player_pos[0], player_pos[1], player_pos[2])

    grid = 13
    cell = (2 * GRID_LENGTH) / grid

    glBegin(GL_QUADS)

    for i in range(grid):
        for j in range(grid):
            if (i + j) % 2 == 0:
                glColor3f(1.0, 1.0, 1.0)
            else:
                glColor3f(0.7, 0.5, 0.95)

            x = -GRID_LENGTH + i * cell
            y = -GRID_LENGTH + j * cell

            glVertex3f(x,         y,         0)
            glVertex3f(x + cell,  y,         0)
            glVertex3f(x + cell,  y + cell,  0)
            glVertex3f(x,         y + cell,  0)

    glEnd()

    for w in weapons:
        w.draw()

    glutSwapBuffers()


def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutInitWindowPosition(0, 0)
    wind = glutCreateWindow(b"Katzenstein")

    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)

    glutMainLoop()

if __name__ == "__main__":
    main()