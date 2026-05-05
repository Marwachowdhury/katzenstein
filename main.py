import math

from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import random
import time

start_time = time.time()

# Camera-related variables
camera_pos = (0, 500, 500)

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
bullets_missed = 0  # threshold 10
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


# ──────────────────────────────────────────────────────────────
# NEW ► Bullet class
# ──────────────────────────────────────────────────────────────
class Bullet:
    
    def __init__(self, x, y, dx, dy, damage):
        self.pos    = [x, y, 80]   # mid-body height
        self.dx     = dx
        self.dy     = dy
        self.speed  = 20
        self.damage = damage

bullets = []   # active bullets in the world


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
            forward_offset = 40    # push into screen
            right_offset   = -15   # move to right
            up_offset      = -0    # move downward

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
    Weapon("rifle",  20, (-200, 50, 0)),
]

inventory = Inventory()


# ══════════════════════════════════════════════════════════════
# NEW ► ENEMY SYSTEM
# ══════════════════════════════════════════════════════════════
#
#  Three enemy types, each with a distinct silhouette:
#
#  SCOUT  – thin / fast / low HP  / low damage   (red)
#  SOLDIER– normal / medium stats               (orange, helmet)
#  TANK   – bulky / slow / high HP / high damage (purple, shoulder pads)
#
# ──────────────────────────────────────────────────────────────

ENEMY_CONFIGS = {
    'scout': {
        'health': 30,  'size': 22,
        'color': (1.0, 0.15, 0.15),
        'damage': 5,   'speed': 1.0,
        'score_value': 10,
    },
    'soldier': {
        'health': 80,  'size': 38,
        'color': (0.9, 0.50, 0.0),
        'damage': 15,  'speed': 0.8,
        'score_value': 25,
    },
    'tank': {
        'health': 180, 'size': 60,
        'color': (0.50, 0.0, 0.90),
        'damage': 30,  'speed': 0.6,
        'score_value': 50,
    },
}

enemies          = []
last_spawn_time  = start_time
spawn_interval   = 4.0   # seconds between spawns
max_enemies      = 8


def _spawn_enemy():
   
    margin = GRID_LENGTH - 50
    side   = random.randint(0, 3)

    if   side == 0:  x, y =  random.uniform(-margin, margin),  margin
    elif side == 1:  x, y =  random.uniform(-margin, margin), -margin
    elif side == 2:  x, y =  margin,  random.uniform(-margin, margin)
    else:            x, y = -margin,  random.uniform(-margin, margin)

    etype = random.choice(list(ENEMY_CONFIGS.keys()))
    cfg   = ENEMY_CONFIGS[etype]

    enemies.append(Enemy(
        pos    = [x, y, 0],
        size   = cfg['size'],
        color  = cfg['color'],
        type   = etype,
        damage = cfg['damage'],
        speed  = cfg['speed'],
        health = cfg['health'],
    ))


# ── Drawing helpers ────────────────────────────────────────────

def _draw_scout(s, r, g, b, quad):
    
    legs_h = s * 0.85

    # Torso (narrow)
    glColor3f(r, g, b)
    glPushMatrix()
    glTranslatef(0, 0, s + legs_h)
    glScalef(s * 0.6, s * 0.25, s * 1.6)
    glutSolidCube(1)
    glPopMatrix()

    # Head (small)
    glColor3f(r * 0.75, g * 0.75, b * 0.75)
    glPushMatrix()
    glTranslatef(0, 0, s * 2.1 + legs_h)
    gluSphere(quad, s * 0.30, 12, 12)
    glPopMatrix()

    # Thin arms
    glColor3f(r * 0.65, g * 0.65, b * 0.65)
    for side in (-1, 1):
        glPushMatrix()
        glTranslatef(side * s * 0.45, 0, s * 1.7 + legs_h)
        glRotatef(90, 1, 0, 0)
        gluCylinder(quad, s * 0.07, s * 0.07, s * 1.0, 8, 8)
        glPopMatrix()

    # Thin legs
    glColor3f(0.1, 0.0, 0.4)
    for side in (-1, 1):
        glPushMatrix()
        glTranslatef(side * s * 0.18, 0, 0)
        gluCylinder(quad, s * 0.09, s * 0.09, legs_h, 8, 8)
        glPopMatrix()


def _draw_soldier(s, r, g, b, quad):
    
    legs_h = s * 0.95

    # Body
    glColor3f(r, g, b)
    glPushMatrix()
    glTranslatef(0, 0, s + legs_h)
    glScalef(s, s * 0.50, s * 2.0)
    glutSolidCube(1)
    glPopMatrix()

    # Head (dark skin tone)
    glColor3f(0.70, 0.50, 0.30)
    glPushMatrix()
    glTranslatef(0, 0, s * 2.55 + legs_h)
    gluSphere(quad, s * 0.38, 12, 12)
    glPopMatrix()

    # Helmet (flat cube on head)
    glColor3f(0.15, 0.15, 0.15)
    glPushMatrix()
    glTranslatef(0, 0, s * 2.85 + legs_h)
    glScalef(s * 0.90, s * 0.90, s * 0.28)
    glutSolidCube(1)
    glPopMatrix()

    # Arms
    glColor3f(r * 0.80, g * 0.80, b * 0.80)
    for side in (-1, 1):
        glPushMatrix()
        glTranslatef(side * s * 0.72, 0, s * 2.0 + legs_h)
        glRotatef(90, 1, 0, 0)
        gluCylinder(quad, s * 0.14, s * 0.14, s * 1.2, 10, 10)
        glPopMatrix()

    # Legs
    glColor3f(0.15, 0.10, 0.05)
    for side in (-1, 1):
        glPushMatrix()
        glTranslatef(side * s * 0.27, 0, 0)
        gluCylinder(quad, s * 0.18, s * 0.18, legs_h, 10, 10)
        glPopMatrix()


def _draw_tank(s, r, g, b, quad):
    
    legs_h = s * 0.75

    # Thick torso
    glColor3f(r, g, b)
    glPushMatrix()
    glTranslatef(0, 0, s + legs_h)
    glScalef(s * 1.40, s * 0.70, s * 2.2)
    glutSolidCube(1)
    glPopMatrix()

    # Shoulder pads
    glColor3f(r * 0.55, g * 0.55, b * 0.55)
    for side in (-1, 1):
        glPushMatrix()
        glTranslatef(side * s * 0.95, 0, s * 2.4 + legs_h)
        glScalef(s * 0.50, s * 0.40, s * 0.40)
        glutSolidCube(1)
        glPopMatrix()

    # Big head
    glColor3f(r * 0.70, g * 0.70, b * 0.70)
    glPushMatrix()
    glTranslatef(0, 0, s * 2.85 + legs_h)
    gluSphere(quad, s * 0.52, 16, 16)
    glPopMatrix()

    # Thick arms
    glColor3f(r * 0.80, g * 0.80, b * 0.80)
    for side in (-1, 1):
        glPushMatrix()
        glTranslatef(side * s * 1.0, 0, s * 2.0 + legs_h)
        glRotatef(90, 1, 0, 0)
        gluCylinder(quad, s * 0.24, s * 0.20, s * 1.4, 12, 12)
        glPopMatrix()

    # Thick legs
    glColor3f(0.20, 0.00, 0.40)
    for side in (-1, 1):
        glPushMatrix()
        glTranslatef(side * s * 0.40, 0, 0)
        gluCylinder(quad, s * 0.27, s * 0.27, legs_h, 12, 12)
        glPopMatrix()


def _draw_health_bar_3d(e):
    
    cfg        = ENEMY_CONFIGS[e.type]
    max_hp     = cfg['health']
    ratio      = max(0.0, e.health / max_hp)
    bar_w      = e.size * 1.6
    bar_h      = e.size * 0.28
    bar_d      = bar_h * 0.5
    above      = e.size * 4.8

    glPushMatrix()
    glTranslatef(e.pos[0], e.pos[1], e.pos[2] + above)

    # Dark background strip
    glColor3f(0.25, 0.0, 0.0)
    glPushMatrix()
    glScalef(bar_w, bar_d, bar_h)
    glutSolidCube(1)
    glPopMatrix()

    # Coloured health fill
    if   ratio > 0.6: glColor3f(0.0,  1.0,  0.0)
    elif ratio > 0.3: glColor3f(1.0,  0.75, 0.0)
    else:             glColor3f(1.0,  0.0,  0.0)

    glPushMatrix()
    glTranslatef(-bar_w * (1.0 - ratio) * 0.5, 0, bar_h * 0.35)
    glScalef(bar_w * ratio, bar_d, bar_h)
    glutSolidCube(1)
    glPopMatrix()

    glPopMatrix()


def draw_enemy(e):
    
    quad = gluNewQuadric()

    # Face the player
    dx    = player_pos[0] - e.pos[0]
    dy    = player_pos[1] - e.pos[1]
    angle = math.degrees(math.atan2(dy, dx)) - 90

    r, g, b = e.color

    glPushMatrix()
    glTranslatef(e.pos[0], e.pos[1], e.pos[2])
    glRotatef(angle, 0, 0, 1)

    if   e.type == 'scout':   _draw_scout  (e.size, r, g, b, quad)
    elif e.type == 'soldier': _draw_soldier(e.size, r, g, b, quad)
    elif e.type == 'tank':    _draw_tank   (e.size, r, g, b, quad)

    glPopMatrix()

    _draw_health_bar_3d(e)


# ── Bullet drawing ─────────────────────────────────────────────

def draw_bullet(b):
    quad = gluNewQuadric()
    glPushMatrix()
    glTranslatef(b.pos[0], b.pos[1], b.pos[2])
    glColor3f(1.0, 1.0, 0.0)   # bright yellow
    gluSphere(quad, 5, 8, 8)
    glPopMatrix()


# ── Update loops ───────────────────────────────────────────────

def update_enemies():
    global enemies, lives, score, is_game_over, last_spawn_time

    if is_game_over:
        return

    now = time.time()

    # Timed spawn
    if now - last_spawn_time >= spawn_interval and len(enemies) < max_enemies:
        _spawn_enemy()
        last_spawn_time = now

    alive = []
    for e in enemies:
        dx   = player_pos[0] - e.pos[0]
        dy   = player_pos[1] - e.pos[1]
        dist = math.sqrt(dx * dx + dy * dy)

        contact_dist = e.size + 35   # rough player radius

        if dist < contact_dist:
            # Enemy reaches player → inflict damage and despawn
            lives -= 1
            if lives <= 0:
                lives          = 0
                is_game_over   = True
            # enemy is consumed; do NOT append to alive
        else:
            e.pos[0] += (dx / dist) * e.speed
            e.pos[1] += (dy / dist) * e.speed
            alive.append(e)

    enemies[:] = alive


def update_bullets():
    global bullets, enemies, score

    new_bullets = []
    for b in bullets:
        b.pos[0] += b.dx * b.speed
        b.pos[1] += b.dy * b.speed

        # Cull out-of-bounds
        if abs(b.pos[0]) > GRID_LENGTH + 200 or abs(b.pos[1]) > GRID_LENGTH + 200:
            continue

        # Collision check against every enemy
        hit = False
        for e in enemies:
            ddx  = b.pos[0] - e.pos[0]
            ddy  = b.pos[1] - e.pos[1]
            if math.sqrt(ddx * ddx + ddy * ddy) < e.size:
                e.health -= b.damage
                hit = True
                break          # one bullet hits one enemy

        if not hit:
            new_bullets.append(b)

    bullets[:] = new_bullets

    # Award score and remove dead enemies
    still_alive = []
    for e in enemies:
        if e.health > 0:
            still_alive.append(e)
        else:
            score += ENEMY_CONFIGS[e.type]['score_value']
    enemies[:] = still_alive

# ══════════════════════════════════════════════════════════════
# END NEW ► ENEMY SYSTEM
# ══════════════════════════════════════════════════════════════


def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(1, 1, 1)
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

            if (dx ** 2 + dy ** 2) < 10000:
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

    if key == b'r':
        lives           = 5
        score           = 0
        bullets_missed  = 0
        is_game_over    = False
        player_fall_angle.__class__  # just a no-op; reset below
        globals()['player_fall_angle'] = 0
        enemies.clear()
        bullets.clear()


def specialKeyListener(key, x, y):
    pass


def mouseListener(button, state, x, y):
    global first_person

    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        import math

        rad = math.radians(player_angle)

        dx = math.cos(rad)
        dy = math.sin(rad)

        # Spawn bullet at player position
        bx = player_pos[0]
        by = player_pos[1]

        # ── NEW: determine damage from equipped weapon ──────────────
        if inventory.weapon_idx >= 0:
            dmg = inventory.weapons[inventory.weapon_idx].damage
        else:
            dmg = 5   # bare-hands / no weapon
        bullets.append(Bullet(bx, by, dx, dy, dmg))
        # ─────────────────────────────────────────────────────────────


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
    
    update_enemies()
    update_bullets()
    
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
        glRotatef(player_angle + 90, 0, 0, 1)

    glColor3f(85 / 255, 107 / 255, 47 / 255)
    glPushMatrix()
    glTranslatef(0, 0, scale + legs_height)
    glScalef(scale, scale * 0.5, scale * 2)
    glutSolidCube(1)
    glPopMatrix()

    # matha
    glColor3f(0, 0, 0)
    glPushMatrix()
    glTranslatef(0, 0, scale * 2.5 + legs_height)
    gluSphere(gluNewQuadric(), scale * 0.4, 20, 20)
    glPopMatrix()

    quad = gluNewQuadric()

    # left arm
    glColor3f(1.0, 0.8, 0.6)
    glPushMatrix()
    glTranslatef(-scale * 0.8, 0, scale * 2)
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
    glTranslatef(0 - scale * 0.3, 0, 0)
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
        # ── NEW: enemy counter HUD ─────────────────────────────────────
        draw_text(10, 680, f"Enemies: {len(enemies)}")
        draw_text(10, 650, f"[LMB] Shoot   [F] Pick up weapon   [1/2] Switch   [R] Restart")
        # ──────────────────────────────────────────────────────────────
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

            glVertex3f(x,        y,        0)
            glVertex3f(x + cell, y,        0)
            glVertex3f(x + cell, y + cell, 0)
            glVertex3f(x,        y + cell, 0)

    glEnd()

    for w in weapons:
        w.draw()

    # ── NEW: draw enemies and bullets ─────────────────────────────
    for e in enemies:
        draw_enemy(e)

    for b in bullets:
        draw_bullet(b)
    # ──────────────────────────────────────────────────────────────

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
