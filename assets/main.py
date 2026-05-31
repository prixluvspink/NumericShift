import os
import sys
import random
import math
from pathlib import Path

import pygame

# ------------------------------------------------
# GAME SETTINGS
# ------------------------------------------------
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
HUD_HEIGHT = 78
GAME_TOP = HUD_HEIGHT
GAME_HEIGHT = SCREEN_HEIGHT - HUD_HEIGHT
GROUND_Y = 606
TILE = 48
GRAVITY = 0.62
BG_SPEED = 0.15

PLAYER_SPEED = 5.4
PLAYER_JUMP = -16.8
PLAYER_START_X = 160
PLAYER_START_Y = GROUND_Y - 132

MAX_HEALTH_HALVES = 6        # 6 halves = 3 full hearts
SKELETON_DAMAGE = 1          # 1 half-heart per hit
INVINCIBLE_TIME = 850        # milliseconds after getting hit

# Experimental polish/unique features. These do not need new assets.
LOW_HEALTH_WARNING_HALVES = 2       # warning at 1 full heart or lower
WRONG_KEY_PENALTY = 25
WRONG_KEY_COOLDOWN = 900
PERFECT_GLITCH_BONUS = 50
DAMAGE_BOOST_DURATION = 12000       # milliseconds
GLITCH_STORM_DURATION = 6500        # milliseconds
MILESTONES = [500, 1000, 2000, 3500, 5000, 7500, 10000, 15000]

TITLE = "Numeric Shift"

# ------------------------------------------------
# PYGAME SETUP
# ------------------------------------------------
pygame.init()
try:
    pygame.mixer.init()
    MIXER_OK = True
except pygame.error:
    MIXER_OK = False

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption(TITLE)
clock = pygame.time.Clock()

FONT = pygame.font.SysFont("consolas", 22, bold=True)
SMALL_FONT = pygame.font.SysFont("consolas", 16, bold=True)
MID_FONT = pygame.font.SysFont("consolas", 34, bold=True)
BIG_FONT = pygame.font.SysFont("consolas", 56, bold=True)

WHITE = (245, 245, 245)
BLACK = (0, 0, 0)
YELLOW = (255, 225, 80)
RED = (230, 70, 60)
GREEN = (80, 220, 120)
BLUE = (90, 170, 255)
PURPLE = (49, 23, 64)
DARK_PURPLE = (31, 15, 44)
LIGHT_GRAY = (210, 210, 220)

# ------------------------------------------------
# ASSET DIRECTORY FINDER
# This makes the code work even if you accidentally put main.py inside assets.
# ------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent


def find_assets_dir():
    candidates = [
        BASE_DIR / "assets",       
        BASE_DIR,                  
        BASE_DIR.parent / "assets"
    ]
    needed = ["background", "blocks", "collectibles", "enemies", "hearthp", "numbers", "player", "soundeffect"]
    for candidate in candidates:
        if candidate.exists() and all((candidate / folder).exists() for folder in needed):
            return candidate
    print("\nERROR: Cannot find the assets folder.")
    print("Put main.py beside the assets folder like this:")
    print("OndajonGame/main.py")
    print("OndajonGame/assets/background/scrollbackground.png")
    input("Press Enter to close...")
    pygame.quit()
    sys.exit()


ASSETS_DIR = find_assets_dir()
PROJECT_DIR = ASSETS_DIR.parent if ASSETS_DIR.name.lower() == "assets" else BASE_DIR
HIGHSCORE_FILE = PROJECT_DIR / "highscore.txt"

print("================================================")
print("NUMERIC SHIFT ASSET CHECK")
print("Using assets folder:", ASSETS_DIR)
print("================================================")

# ------------------------------------------------
# EXACT ASSET LOADER
# ------------------------------------------------

def exact_path(*parts):
    path = ASSETS_DIR.joinpath(*parts)
    if not path.exists():
        print("MISSING:", path)
        return None
    print("LOADED:", path.relative_to(ASSETS_DIR))
    return path


def load_image(parts, size=None, scale=None, smooth=False, critical=True):
    path = exact_path(*parts)
    if path is None:
        if critical:
            print("\nCritical image missing:", "/".join(parts))
            input("Press Enter to close...")
            pygame.quit()
            sys.exit()
        surf = pygame.Surface((32, 32), pygame.SRCALPHA)
        surf.fill((255, 0, 255))
        return surf

    img = pygame.image.load(str(path)).convert_alpha()
    if size is not None:
        if smooth:
            img = pygame.transform.smoothscale(img, size)
        else:
            img = pygame.transform.scale(img, size)
    elif scale is not None:
        w, h = img.get_size()
        new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
        if smooth:
            img = pygame.transform.smoothscale(img, new_size)
        else:
            img = pygame.transform.scale(img, new_size)
    return img


def load_sound(parts, volume=0.55):
    if not MIXER_OK:
        return None
    path = exact_path(*parts)
    if path is None:
        return None
    try:
        sound = pygame.mixer.Sound(str(path))
        sound.set_volume(volume)
        return sound
    except pygame.error as e:
        print("Could not load sound:", path.name, e)
        return None


def play_sound(sound):
    if sound is not None:
        try:
            sound.play()
        except Exception:
            pass


def crop_visible_content(surface, ignore_black=True):
    """Crop images like flatplatform.png so the black empty space is removed.
    This uses only pygame, so it does not require numpy or any extra library.
    """
    w, h = surface.get_size()
    min_x, min_y, max_x, max_y = w, h, 0, 0
    found = False

    for y in range(h):
        for x in range(w):
            r, g, b, a = surface.get_at((x, y))
            if a <= 10:
                continue
            if ignore_black and r < 18 and g < 18 and b < 18:
                continue
            found = True
            if x < min_x: min_x = x
            if y < min_y: min_y = y
            if x > max_x: max_x = x
            if y > max_y: max_y = y

    if not found:
        return surface

    rect = pygame.Rect(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
    return surface.subsurface(rect).copy()


def split_sheet(sheet, frame_w, frame_h, scale=1.0, remove_empty=True):
    frames = []
    sheet_w, sheet_h = sheet.get_size()
    for y in range(0, sheet_h, frame_h):
        for x in range(0, sheet_w, frame_w):
            rect = pygame.Rect(x, y, frame_w, frame_h)
            if rect.right > sheet_w or rect.bottom > sheet_h:
                continue
            frame = sheet.subsurface(rect).copy()
            if remove_empty and frame.get_bounding_rect().width <= 2:
                continue
            if scale != 1.0:
                frame = pygame.transform.scale(frame, (int(frame_w * scale), int(frame_h * scale)))
            frames.append(frame)
    return frames


def split_sheet_by_rows(sheet, frame_w, frame_h, scale=1.0):
    rows = []
    sheet_w, sheet_h = sheet.get_size()
    for y in range(0, sheet_h, frame_h):
        row = []
        for x in range(0, sheet_w, frame_w):
            rect = pygame.Rect(x, y, frame_w, frame_h)
            if rect.right > sheet_w or rect.bottom > sheet_h:
                continue
            frame = sheet.subsurface(rect).copy()
            if frame.get_bounding_rect().width <= 2:
                continue
            if scale != 1.0:
                frame = pygame.transform.scale(frame, (int(frame_w * scale), int(frame_h * scale)))
            row.append(frame)
        if row:
            rows.append(row)
    return rows

# ------------------------------------------------
# LOAD REAL ASSETS WITH EXACT NAMES
# ------------------------------------------------
background_raw = load_image(("background", "scrollbackground.png"), critical=True)

# Preserve background ratio; it scrolls slowly at 0.15 and loops forever.
bg_ratio = background_raw.get_width() / background_raw.get_height()
bg_height = GAME_HEIGHT
bg_width = int(bg_height * bg_ratio)
background_img = pygame.transform.scale(background_raw, (bg_width, bg_height))

# Blocks. These are real images, not placeholder boxes.
grass_tile = load_image(("blocks", "grassblock.png"), size=(TILE, TILE), critical=True)
stone_tile = load_image(("blocks", "stoneblock.png"), size=(TILE, TILE), critical=True)
flatplatform_raw = load_image(("blocks", "flatplatform.png"), critical=True)
flatplatform_cropped = crop_visible_content(flatplatform_raw, ignore_black=True)
# Make the platform thin and usable without stretching it into a giant rectangle.
flatplatform_base = pygame.transform.scale(flatplatform_cropped, (240, 36))

# Collectibles
coin_frames = [
    load_image(("collectibles", "coin_round_gold.png"), size=(28, 28), critical=True),
    load_image(("collectibles", "coin_vertical_gold.png"), size=(28, 28), critical=True),
]
gem_frames = [
    load_image(("collectibles", "pixel_gem_blue.png"), size=(30, 30), critical=True),
    load_image(("collectibles", "pixel_gem_dot.png"), size=(30, 30), critical=True),
]
key_img = load_image(("collectibles", "enemy_drop_code_key.png"), size=(34, 34), critical=True)
chest_img = load_image(("collectibles", "enemy_drop_chest.png"), size=(44, 44), critical=True)

# Hearts
heart_full = load_image(("hearthp", "health_full_heart.png"), size=(32, 32), critical=True)
heart_half = load_image(("hearthp", "health_half_or_broken_heart.png"), size=(32, 32), critical=True)
heart_empty = load_image(("hearthp", "health_empty_heart.png"), size=(32, 32), critical=True)

# Number labels for hidden blocks
number_imgs = {
    7: load_image(("numbers", "keyboard_number_7.png"), size=(34, 34), critical=True),
    8: load_image(("numbers", "keyboard_number_8.png"), size=(34, 34), critical=True),
    9: load_image(("numbers", "keyboard_number_9.png"), size=(34, 34), critical=True),
}

# Player sheet: 288x480 = 6 columns x 10 rows, each frame 48x48.
player_sheet = load_image(("player", "playersprite.png"), critical=True)
player_rows = split_sheet_by_rows(player_sheet, 48, 48, scale=2.65)  # bigger/taller player
# Use safe rows. Even if the exact animation row is different, these are real sprites.
player_idle = player_rows[0] if len(player_rows) > 0 else []
player_walk = player_rows[1] if len(player_rows) > 1 else player_idle
player_attack = player_rows[6] if len(player_rows) > 6 else player_walk
player_hurt = player_rows[8] if len(player_rows) > 8 else player_idle

# Skeleton sheets: each frame is 96x64.
skel_walk = split_sheet(load_image(("enemies", "Skeleton_01_White_Walk.png"), critical=True), 96, 64, scale=1.85)
skel_idle = split_sheet(load_image(("enemies", "Skeleton_01_White_Idle.png"), critical=True), 96, 64, scale=1.85)
skel_hurt = split_sheet(load_image(("enemies", "Skeleton_01_White_Hurt.png"), critical=True), 96, 64, scale=1.85)
skel_die = split_sheet(load_image(("enemies", "Skeleton_01_White_Die.png"), critical=True), 96, 64, scale=1.85)
skel_attack1 = split_sheet(load_image(("enemies", "Skeleton_01_White_Attack1.png"), critical=True), 96, 64, scale=1.85)
skel_attack2 = split_sheet(load_image(("enemies", "Skeleton_01_White_Attack2.png"), critical=True), 96, 64, scale=1.85)

# Sounds
snd_collect = load_sound(("soundeffect", "collectsound.mp3"), 0.55)
snd_enemy_defeat = load_sound(("soundeffect", "enemy_defeat.mp3"), 0.60)
snd_hurt = load_sound(("soundeffect", "hurtsound.mp3"), 0.60)
snd_jump = load_sound(("soundeffect", "jump.mp3"), 0.45)
snd_reveal = load_sound(("soundeffect", "platform_reveal.mp3"), 0.50)

# Background music
if MIXER_OK:
    music_path = exact_path("background", "bgmusic.wav")
    if music_path is not None:
        try:
            pygame.mixer.music.load(str(music_path))
            pygame.mixer.music.set_volume(0.25)
            pygame.mixer.music.play(-1)
        except pygame.error as e:
            print("Could not play bgmusic.wav:", e)

print("================================================")
print("All exact asset names were requested. If the game opens, assets are connected.")
print("================================================\n")

# ------------------------------------------------
# HELPERS
# ------------------------------------------------
def load_highscore():
    try:
        if HIGHSCORE_FILE.exists():
            return int(HIGHSCORE_FILE.read_text().strip() or "0")
    except Exception:
        pass
    return 0


def save_highscore(value):
    try:
        HIGHSCORE_FILE.write_text(str(int(value)))
    except Exception:
        pass


def draw_text(text, x, y, color=WHITE, font=FONT):
    surf = font.render(str(text), True, color)
    screen.blit(surf, (x, y))
    return surf.get_rect(topleft=(x, y))


def world_to_screen_x(world_x, camera_x):
    return int(world_x - camera_x)


def make_platform_image(width):
    """Tile the real flatplatform image horizontally instead of making it look like a plain box."""
    width = int(width)
    h = flatplatform_base.get_height()
    surf = pygame.Surface((width, h), pygame.SRCALPHA)
    x = 0
    while x < width:
        surf.blit(flatplatform_base, (x, 0))
        x += flatplatform_base.get_width()
    return surf


def visible_world_range(camera_x):
    return camera_x - 200, camera_x + SCREEN_WIDTH + 260


def get_active_number(keys):
    # NUMPAD ONLY, based on your requested controls.
    # Only one number is allowed at a time; pressing multiple numpad numbers disables the hidden blocks.
    pressed = set()
    if keys[pygame.K_KP7]:
        pressed.add(7)
    if keys[pygame.K_KP8]:
        pressed.add(8)
    if keys[pygame.K_KP9]:
        pressed.add(9)
    if len(pressed) == 1:
        return next(iter(pressed))
    return None


def key_to_numpad_number(key):
    if key == pygame.K_KP7:
        return 7
    if key == pygame.K_KP8:
        return 8
    if key == pygame.K_KP9:
        return 9
    return None

# ------------------------------------------------
# GAME OBJECTS
# ------------------------------------------------

class GroundSegment:
    """A short piece of land. The game is parkour-style now, so land is NOT endless."""
    def __init__(self, x, width):
        self.x = float(x)
        self.y = GROUND_Y
        self.w = int(width)
        self.h = TILE * 3
        self.rect = pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def draw(self, camera_x):
        sx0 = world_to_screen_x(self.x, camera_x)
        if sx0 > SCREEN_WIDTH + 80 or sx0 + self.w < -80:
            return
        start_x = int(self.x // TILE) * TILE
        end_x = int(self.x + self.w + TILE)
        x = start_x
        while x < end_x:
            sx = world_to_screen_x(x, camera_x)
            # Clip the last tile so the land segment ends cleanly.
            clip_left = max(0, int(self.x - x))
            clip_right = min(TILE, int(self.x + self.w - x))
            if clip_right > clip_left:
                src = pygame.Rect(clip_left, 0, clip_right - clip_left, TILE)
                screen.blit(grass_tile, (sx + clip_left, GROUND_Y), src)
                screen.blit(stone_tile, (sx + clip_left, GROUND_Y + TILE), src)
                screen.blit(stone_tile, (sx + clip_left, GROUND_Y + TILE * 2), src)
            x += TILE

class Platform:
    def __init__(self, x, y, width=240, move_axis=None, amplitude=0, speed=0.0022, phase=0.0):
        self.base_x = float(x)
        self.base_y = float(y)
        self.x = float(x)
        self.y = float(y)
        self.prev_x = float(x)
        self.prev_y = float(y)
        self.dx = 0.0
        self.dy = 0.0
        self.move_axis = move_axis      # None, "x", or "y"
        self.amplitude = float(amplitude)
        self.speed = float(speed)
        self.phase = float(phase)
        self.move_t = random.randint(0, 999)
        self.w = int(width)
        self.h = 36
        self.image = make_platform_image(self.w)
        self.rect = pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    @property
    def moving(self):
        return self.move_axis is not None and self.amplitude > 0

    def update(self, dt):
        self.prev_x = self.x
        self.prev_y = self.y
        self.move_t += dt

        if self.move_axis == "x":
            self.x = self.base_x + math.sin(self.move_t * self.speed + self.phase) * self.amplitude
            self.y = self.base_y
        elif self.move_axis == "y":
            self.x = self.base_x
            self.y = self.base_y + math.sin(self.move_t * self.speed + self.phase) * self.amplitude
        else:
            self.x = self.base_x
            self.y = self.base_y

        self.dx = self.x - self.prev_x
        self.dy = self.y - self.prev_y
        self.rect.topleft = (int(self.x), int(self.y))

    def draw(self, camera_x):
        sx = world_to_screen_x(self.x, camera_x)
        if sx > SCREEN_WIDTH + 120 or sx + self.w < -120:
            return
        screen.blit(self.image, (sx, int(self.y)))
        if self.moving:
            # Small white dots show this is a moving platform without needing new assets.
            pygame.draw.circle(screen, WHITE, (sx + 12, int(self.y) + 10), 3)
            pygame.draw.circle(screen, WHITE, (sx + self.w - 12, int(self.y) + 10), 3)


class HiddenBlock:
    def __init__(self, x, y, number, move_axis=None, amplitude=0, speed=0.0025, phase=0.0, time_limit=0):
        self.base_x = float(x)
        self.base_y = float(y)
        self.x = float(x)
        self.y = float(y)
        self.prev_x = float(x)
        self.prev_y = float(y)
        self.dx = 0.0
        self.dy = 0.0
        self.number = int(number)
        self.move_axis = move_axis      # None, "x", or "y"
        self.amplitude = float(amplitude)
        self.speed = float(speed)
        self.phase = float(phase)
        self.move_t = random.randint(0, 999)
        self.time_limit = int(time_limit)
        self.active_time = 0
        self.cooldown = 0
        self.rect = pygame.Rect(int(x), int(y), TILE, TILE)
        self.was_active = False

    @property
    def moving(self):
        return self.move_axis is not None and self.amplitude > 0

    def update(self, dt):
        self.prev_x = self.x
        self.prev_y = self.y
        self.move_t += dt

        if self.move_axis == "x":
            self.x = self.base_x + math.sin(self.move_t * self.speed + self.phase) * self.amplitude
            self.y = self.base_y
        elif self.move_axis == "y":
            self.x = self.base_x
            self.y = self.base_y + math.sin(self.move_t * self.speed + self.phase) * self.amplitude
        else:
            self.x = self.base_x
            self.y = self.base_y

        self.dx = self.x - self.prev_x
        self.dy = self.y - self.prev_y
        self.rect.topleft = (int(self.x), int(self.y))

    def update_visibility_timer(self, dt, active_number):
        raw_active = active_number == self.number

        if self.cooldown > 0:
            self.cooldown = max(0, self.cooldown - dt)

        if raw_active and self.cooldown <= 0:
            self.active_time += dt
            if self.time_limit > 0 and self.active_time >= self.time_limit:
                # Timed glitch blocks overload when held too long.
                self.cooldown = 850
                self.active_time = 0
        else:
            self.active_time = 0

    def is_active(self, active_number):
        if self.cooldown > 0:
            return False
        if active_number != self.number:
            return False
        if self.time_limit > 0 and self.active_time >= self.time_limit:
            return False
        return True

    def draw(self, camera_x, active_number):
        sx = world_to_screen_x(self.x, camera_x)
        if sx > SCREEN_WIDTH + 120 or sx + TILE < -120:
            return

        active = self.is_active(active_number)
        if active and not self.was_active:
            play_sound(snd_reveal)
        self.was_active = active

        if active:
            screen.blit(stone_tile, (sx, int(self.y)))
            img = number_imgs[self.number]
            screen.blit(img, img.get_rect(center=(sx + TILE // 2, int(self.y) + TILE // 2)))
            pygame.draw.rect(screen, YELLOW, pygame.Rect(sx, int(self.y), TILE, TILE), 2)
            if self.time_limit > 0:
                # Simple timer bar on timed hidden blocks.
                ratio = max(0.0, 1.0 - (self.active_time / self.time_limit))
                pygame.draw.rect(screen, BLACK, (sx + 6, int(self.y) + 5, TILE - 12, 5))
                pygame.draw.rect(screen, GREEN if ratio > 0.35 else RED, (sx + 6, int(self.y) + 5, int((TILE - 12) * ratio), 5))
            if self.moving:
                pygame.draw.circle(screen, WHITE, (sx + TILE // 2, int(self.y) + 8), 3)
        else:
            ghost = stone_tile.copy()
            ghost.set_alpha(65)
            screen.blit(ghost, (sx, int(self.y)))
            img = number_imgs[self.number].copy()
            img.set_alpha(190)
            screen.blit(img, img.get_rect(center=(sx + TILE // 2, int(self.y) + TILE // 2)))
            border_color = RED if self.cooldown > 0 else (255, 255, 255)
            pygame.draw.rect(screen, border_color, pygame.Rect(sx, int(self.y), TILE, TILE), 1)
            if self.cooldown > 0:
                draw_text("WAIT", sx + 3, int(self.y) - 16, RED, SMALL_FONT)
            elif self.time_limit > 0:
                draw_text("FAST", sx + 3, int(self.y) - 16, YELLOW, SMALL_FONT)
            if self.moving:
                pygame.draw.circle(screen, (255, 255, 255), (sx + TILE // 2, int(self.y) + 8), 3)


class Collectible:
    def __init__(self, kind, x, y):
        self.kind = kind
        self.x = float(x)
        self.y = float(y)
        self.spawn_y = float(y)
        self.t = random.randint(0, 999)
        self.collected = False
        self.rect = pygame.Rect(int(x), int(y), 28, 28)

    def update(self, dt):
        self.t += dt
        self.y = self.spawn_y + 5 * pygame.math.Vector2(0, 1).rotate(self.t * 0.18).y
        self.rect.topleft = (int(self.x), int(self.y))

    def draw(self, camera_x):
        if self.collected:
            return
        sx = world_to_screen_x(self.x, camera_x)
        if sx > SCREEN_WIDTH + 80 or sx < -80:
            return
        if self.kind == "coin":
            img = coin_frames[(pygame.time.get_ticks() // 180) % 2]
        else:
            img = gem_frames[(pygame.time.get_ticks() // 220) % 2]
        screen.blit(img, (sx, int(self.y)))


class KeyDrop:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.rect = pygame.Rect(int(x), int(y), 34, 34)
        self.bob = random.randint(0, 999)
        self.dead = False

    def update(self, dt):
        self.bob += dt
        self.rect.topleft = (int(self.x), int(self.y + 4 * pygame.math.Vector2(0, 1).rotate(self.bob * 0.2).y))

    def draw(self, camera_x):
        sx = world_to_screen_x(self.x, camera_x)
        if sx > SCREEN_WIDTH + 80 or sx < -80:
            return
        screen.blit(key_img, (sx, self.rect.y))


class ChestBlock:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.w = 44
        self.h = 44
        self.rect = pygame.Rect(int(x), int(y), self.w, self.h)
        self.dead = False

    def draw(self, camera_x):
        sx = world_to_screen_x(self.x, camera_x)
        if sx > SCREEN_WIDTH + 80 or sx + self.w < -80:
            return
        screen.blit(chest_img, (sx, int(self.y)))
        # Small Q reminder if player is near this chest is drawn in Game.draw.


class FloatingMessage:
    def __init__(self, text, x, y, color=YELLOW):
        self.text = text
        self.x = float(x)
        self.y = float(y)
        self.color = color
        self.life = 900

    def update(self, dt):
        self.life -= dt
        self.y -= 0.035 * dt

    def draw(self, camera_x):
        if self.life <= 0:
            return
        sx = world_to_screen_x(self.x, camera_x)
        surf = SMALL_FONT.render(self.text, True, self.color)
        screen.blit(surf, (sx, int(self.y)))



class Player:
    def __init__(self):
        self.x = PLAYER_START_X
        self.y = PLAYER_START_Y
        self.vx = 0
        self.vy = 0
        self.facing = 1
        self.on_ground = False
        self.health = MAX_HEALTH_HALVES
        self.damage = 1
        self.damage_boost_timer = 0
        self.has_key = False
        self.attack_timer = 0
        self.attack_cooldown = 0
        self.invincible = 0
        self.anim_time = 0
        self.frame_index = 0
        self.state = "idle"
        self.jump_buffer = 0
        self.coyote_timer = 0

        # Bigger/taller player. Collision stays narrower so parkour feels fair.
        sample = player_idle[0] if player_idle else pygame.Surface((128, 128), pygame.SRCALPHA)
        self.draw_w, self.draw_h = sample.get_size()
        self.rect = pygame.Rect(int(self.x), int(self.y), 44, 104)
        self.update_rect()

    def reset(self):
        self.__init__()

    def update_rect(self):
        self.rect.x = int(self.x + (self.draw_w - self.rect.w) / 2)
        self.rect.y = int(self.y + self.draw_h - self.rect.h - 8)

    def attack_rect(self):
        if self.facing == 1:
            return pygame.Rect(self.rect.right, self.rect.y + 16, 72, 50)
        return pygame.Rect(self.rect.left - 72, self.rect.y + 16, 72, 50)

    def request_jump(self):
        # Jump buffer makes Space respond immediately instead of feeling delayed.
        self.jump_buffer = 160

    def take_damage(self, amount):
        if self.invincible > 0:
            return False
        self.health = max(0, self.health - amount)
        self.invincible = INVINCIBLE_TIME
        play_sound(snd_hurt)
        return True

    def heal_full(self):
        self.health = MAX_HEALTH_HALVES

    def start_attack(self):
        if self.attack_cooldown <= 0:
            self.attack_timer = 210
            self.attack_cooldown = 330
            self.state = "attack"

    def update(self, dt, keys, solid_rects):
        self.vx = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.vx = -PLAYER_SPEED
            self.facing = -1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.vx = PLAYER_SPEED
            self.facing = 1

        # Coyote time + jump buffer = real-time, responsive jump.
        if self.on_ground:
            self.coyote_timer = 120
        else:
            self.coyote_timer = max(0, self.coyote_timer - dt)
        if self.jump_buffer > 0:
            self.jump_buffer = max(0, self.jump_buffer - dt)
        if self.jump_buffer > 0 and self.coyote_timer > 0:
            self.vy = PLAYER_JUMP
            self.on_ground = False
            self.jump_buffer = 0
            self.coyote_timer = 0
            play_sound(snd_jump)

        # Horizontal movement
        self.x += self.vx
        self.update_rect()
        for rect in solid_rects:
            if self.rect.colliderect(rect):
                if self.vx > 0:
                    self.rect.right = rect.left
                elif self.vx < 0:
                    self.rect.left = rect.right
                self.x = self.rect.x - (self.draw_w - self.rect.w) / 2

        # Gravity / vertical movement
        self.vy += GRAVITY
        if self.vy > 18:
            self.vy = 18
        self.y += self.vy
        self.update_rect()
        self.on_ground = False
        for rect in solid_rects:
            if self.rect.colliderect(rect):
                if self.vy > 0:
                    self.rect.bottom = rect.top
                    self.y = self.rect.y - self.draw_h + self.rect.h + 8
                    self.vy = 0
                    self.on_ground = True
                elif self.vy < 0:
                    self.rect.top = rect.bottom
                    self.y = self.rect.y - self.draw_h + self.rect.h + 8
                    self.vy = 0

        if self.x < 0:
            self.x = 0

        if self.attack_timer > 0:
            self.attack_timer -= dt
        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt
        if self.invincible > 0:
            self.invincible -= dt
        if self.damage_boost_timer > 0:
            self.damage_boost_timer = max(0, self.damage_boost_timer - dt)
            if self.damage_boost_timer <= 0:
                self.damage = 1

        # Animation state
        if self.attack_timer > 0:
            self.state = "attack"
        elif self.invincible > 0 and pygame.time.get_ticks() % 200 < 100:
            self.state = "hurt"
        elif abs(self.vx) > 0.1:
            self.state = "walk"
        else:
            self.state = "idle"

        self.anim_time += dt
        if self.anim_time >= 95:
            self.anim_time = 0
            self.frame_index += 1

    def draw(self, camera_x):
        if self.invincible > 0 and pygame.time.get_ticks() % 120 < 60:
            return

        frames = player_idle
        if self.state == "walk" and player_walk:
            frames = player_walk
        elif self.state == "attack" and player_attack:
            frames = player_attack
        elif self.state == "hurt" and player_hurt:
            frames = player_hurt

        if not frames:
            return
        img = frames[self.frame_index % len(frames)]
        if self.facing == -1:
            img = pygame.transform.flip(img, True, False)

        sx = world_to_screen_x(self.x, camera_x)
        screen.blit(img, (sx, int(self.y)))

        if self.attack_timer > 0:
            ar = self.attack_rect().copy()
            ar.x = world_to_screen_x(ar.x, camera_x)
            pygame.draw.arc(screen, WHITE, ar, -0.9, 0.9, 3)


class Skeleton:
    def __init__(self, x, surface_y=GROUND_Y):
        self.x = float(x)
        self.y = float(surface_y - 112)
        self.vx = random.choice([-1.25, 1.25])
        self.vy = 0
        self.hp = 2
        self.max_hp = 2
        self.facing = -1 if self.vx < 0 else 1
        self.dead = False
        self.dying = False
        self.death_timer = 560
        self.hurt_timer = 0
        self.attack_timer = 0
        self.attack_cooldown = random.randint(250, 650)
        self.attack_kind = random.choice([1, 2])
        self.attack_damage_done = False
        self.anim_time = 0
        self.frame_index = random.randint(0, 99)
        self.rect = pygame.Rect(int(self.x + 60), int(self.y + 42), 46, 68)
        self.update_rect()

    def update_rect(self):
        self.rect.x = int(self.x + 60)
        self.rect.y = int(self.y + 42)

    def attack_rect(self):
        if self.facing == 1:
            return pygame.Rect(self.rect.right - 4, self.rect.y + 14, 66, 46)
        return pygame.Rect(self.rect.left - 62, self.rect.y + 14, 66, 46)

    def take_damage(self, amount):
        if self.dying:
            return False
        self.hp -= amount
        self.hurt_timer = 220
        if self.hp <= 0:
            self.dying = True
            self.death_timer = 560
            play_sound(snd_enemy_defeat)
            return True
        return False

    def has_floor_ahead(self, solid_rects):
        direction = 1 if self.facing == 1 else -1
        probe = pygame.Rect(self.rect.centerx + direction * 34, self.rect.bottom + 5, 8, 8)
        return any(probe.colliderect(r) for r in solid_rects)

    def update(self, dt, player, solid_rects):
        self.anim_time += dt
        if self.anim_time >= 95:
            self.anim_time = 0
            self.frame_index += 1

        if self.dying:
            self.death_timer -= dt
            if self.death_timer <= 0:
                self.dead = True
            return

        if self.hurt_timer > 0:
            self.hurt_timer -= dt
        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt

        dx = player.rect.centerx - self.rect.centerx
        dy = abs(player.rect.centery - self.rect.centery)
        player_close = abs(dx) < 105 and dy < 80

        if player_close and self.attack_timer <= 0 and self.attack_cooldown <= 0:
            self.attack_timer = 430
            self.attack_kind = random.choice([1, 2])
            self.attack_damage_done = False
            self.facing = 1 if dx > 0 else -1

        if self.attack_timer > 0:
            # Stop walking and actually attack using Attack1/Attack2 sprite sheets.
            self.attack_timer -= dt
            self.vx = 0
            self.facing = 1 if dx > 0 else -1
            if 160 <= self.attack_timer <= 310 and not self.attack_damage_done:
                if self.attack_rect().colliderect(player.rect):
                    player.take_damage(SKELETON_DAMAGE)
                    self.attack_damage_done = True
            if self.attack_timer <= 0:
                self.attack_cooldown = 650
                self.vx = 1.25 * self.facing
        else:
            self.x += self.vx
            self.facing = -1 if self.vx < 0 else 1
            self.update_rect()
            for rect in solid_rects:
                if self.rect.colliderect(rect):
                    if self.vx > 0:
                        self.rect.right = rect.left
                    elif self.vx < 0:
                        self.rect.left = rect.right
                    self.x = self.rect.x - 60
                    self.vx *= -1
                    self.facing *= -1
                    break
            if not self.has_floor_ahead(solid_rects):
                self.vx *= -1
                self.facing *= -1

        # Gravity so skeletons stand correctly on ground/platforms, but don't float.
        self.vy += GRAVITY
        if self.vy > 14:
            self.vy = 14
        self.y += self.vy
        self.update_rect()
        for rect in solid_rects:
            if self.rect.colliderect(rect):
                if self.vy > 0:
                    self.rect.bottom = rect.top
                    self.y = self.rect.y - 42
                    self.vy = 0
                elif self.vy < 0:
                    self.rect.top = rect.bottom
                    self.y = self.rect.y - 42
                    self.vy = 0

        if self.y > SCREEN_HEIGHT + 200:
            self.dead = True

    def draw(self, camera_x):
        sx = world_to_screen_x(self.x, camera_x)
        if sx > SCREEN_WIDTH + 170 or sx < -200:
            return

        if self.dying and skel_die:
            frames = skel_die
        elif self.hurt_timer > 0 and skel_hurt:
            frames = skel_hurt
        elif self.attack_timer > 0:
            frames = skel_attack1 if self.attack_kind == 1 and skel_attack1 else skel_attack2
            if not frames:
                frames = skel_attack2 if skel_attack2 else skel_idle
        elif abs(self.vx) > 0.1 and skel_walk:
            frames = skel_walk
        else:
            frames = skel_idle

        img = frames[self.frame_index % len(frames)]
        if self.facing == -1:
            img = pygame.transform.flip(img, True, False)
        screen.blit(img, (sx, int(self.y)))

        if not self.dying:
            bar_w = 44
            hp_w = int(bar_w * max(0, self.hp) / self.max_hp)
            pygame.draw.rect(screen, BLACK, (sx + 62, int(self.y) + 34, bar_w, 5))
            pygame.draw.rect(screen, RED, (sx + 62, int(self.y) + 34, hp_w, 5))


# ------------------------------------------------
# MAIN GAME CLASS
# ------------------------------------------------
class Game:
    def __init__(self):
        self.highscore = load_highscore()
        self.reset()

    def reset(self):
        self.player = Player()
        self.camera_x = 0.0
        self.bg_scroll = 0.0
        self.score = 0
        self.game_over = False
        self.ground_segments = [GroundSegment(0, 620)]
        self.platforms = []
        self.hidden_blocks = []
        self.collectibles = []
        self.keys = []
        self.chests = []
        self.skeletons = []
        self.messages = []
        self.banner_text = ""
        self.banner_timer = 0
        self.banner_color = YELLOW
        self.screen_shake_timer = 0
        self.screen_shake_intensity = 0
        self.wrong_key_cooldown = 0
        self.low_health_warning_cooldown = 0
        self.glitch_storm_timer = 0
        self.next_glitch_storm_score = 2200
        self.milestone_index = 0
        self.last_perfect_block = None
        self.was_on_ground = False
        self.generated_until = 620
        self.last_hidden_number = random.choice([7, 8, 9])
        self.generate_until(SCREEN_WIDTH * 2)

    def add_message(self, text, x, y, color=YELLOW):
        self.messages.append(FloatingMessage(text, x, y, color))

    def add_banner(self, text, color=YELLOW, duration=1300):
        self.banner_text = str(text)
        self.banner_color = color
        self.banner_timer = duration

    def shake(self, intensity=5, duration=260):
        self.screen_shake_intensity = max(self.screen_shake_intensity, int(intensity))
        self.screen_shake_timer = max(self.screen_shake_timer, int(duration))

    def static_solid_rects(self):
        left, right = visible_world_range(self.camera_x)
        rects = []
        for seg in self.ground_segments:
            if seg.x + seg.w > left and seg.x < right:
                rects.append(seg.rect)
        for p in self.platforms:
            if p.x + p.w > left and p.x < right:
                rects.append(p.rect)
        for chest in self.chests:
            if not chest.dead and chest.x + chest.w > left and chest.x < right:
                rects.append(chest.rect)
        return rects

    def solid_rects(self, active_number):
        rects = self.static_solid_rects()
        left, right = visible_world_range(self.camera_x)
        for hb in self.hidden_blocks:
            if hb.is_active(active_number) and hb.x + TILE > left and hb.x < right:
                rects.append(hb.rect)
        return rects

    def active_solid_objects(self, active_number):
        # Used for carrying Byte when he stands on moving platforms or moving hidden blocks.
        left, right = visible_world_range(self.camera_x)
        objects = []
        for p in self.platforms:
            if p.x + p.w > left and p.x < right:
                objects.append(p)
        for hb in self.hidden_blocks:
            if hb.is_active(active_number) and hb.x + TILE > left and hb.x < right:
                objects.append(hb)
        return objects

    def carry_player_on_moving_blocks(self, active_number):
        if not self.player.on_ground:
            return
        player = self.player
        for obj in self.active_solid_objects(active_number):
            # Check if the player's feet are on top of this object.
            touching_top = abs(player.rect.bottom - obj.rect.top) <= 5
            overlapping = player.rect.right > obj.rect.left + 4 and player.rect.left < obj.rect.right - 4
            if touching_top and overlapping and (abs(getattr(obj, "dx", 0)) > 0.001 or abs(getattr(obj, "dy", 0)) > 0.001):
                player.x += obj.dx
                player.y += obj.dy
                player.update_rect()
                break

    def choose_next_number(self):
        choices = [n for n in [7, 8, 9] if n != self.last_hidden_number]
        n = random.choice(choices)
        self.last_hidden_number = n
        return n

    def add_hidden_pair(self, x, y, number, count=2, moving=False, move_axis="x", amplitude=42, speed=0.0024, timed=False):
        # Same phase keeps side-by-side blocks together instead of separating.
        phase = random.random() * 6.28
        time_limit = random.choice([2000, 2200, 2400]) if timed else 0
        for i in range(count):
            block = HiddenBlock(
                x + i * TILE, y, number,
                move_axis=move_axis if moving else None,
                amplitude=amplitude if moving else 0,
                speed=speed,
                phase=phase,
                time_limit=time_limit
            )
            self.hidden_blocks.append(block)
            # Put collectibles only where the hidden block path is actually useful.
            if random.random() < 0.55:
                kind = "gem" if random.random() < 0.35 else "coin"
                self.collectibles.append(Collectible(kind, x + i * TILE + 10, y - 38))

    def generate_until(self, target_x):
        while self.generated_until < target_x:
            start_edge = self.generated_until
            difficulty = min(1.0, start_edge / 10000)

            # The game is still parkour: short safe land, then a gap route.
            gap_len = random.randint(430, 535) + int(difficulty * 125)
            landing_x = start_edge + gap_len
            landing_w = random.randint(300, 430)

            # Prepared section types. This keeps the "random" feeling, but the placement still makes sense.
            if start_edge < 2300:
                section_kind = "normal_hidden"
            else:
                section_kind = random.choices(
                    ["normal_hidden", "moving_hidden", "moving_platform", "mixed"],
                    weights=[36, 28 + int(difficulty * 18), 20 + int(difficulty * 16), 12 + int(difficulty * 20)],
                    k=1
                )[0]

            # Hidden blocks are the main required route across the gap.
            bx = start_edge + 62
            bridge_y = random.choice([GROUND_Y - 78, GROUND_Y - 86])
            while bx < landing_x - 72:
                num = self.choose_next_number()
                count = 2 if random.random() < 0.82 else 1

                moving_hidden = section_kind in ["moving_hidden", "mixed"] and random.random() < (0.45 + difficulty * 0.30)
                timed_hidden = difficulty > 0.30 and section_kind in ["moving_hidden", "mixed"] and random.random() < (0.18 + difficulty * 0.28)
                if moving_hidden:
                    # Horizontal movement is fair because the height stays predictable.
                    self.add_hidden_pair(
                        bx, bridge_y, num, count,
                        moving=True,
                        move_axis="x",
                        amplitude=random.choice([30, 36, 42, 48]),
                        speed=random.choice([0.0019, 0.0022, 0.0025]),
                        timed=timed_hidden
                    )
                    bx += TILE * count + random.randint(60, 78)
                else:
                    self.add_hidden_pair(bx, bridge_y, num, count, timed=timed_hidden)
                    bx += TILE * count + random.randint(54, 72)

            # A moving platform is only added as a useful bridge in the gap, not as decoration.
            if section_kind in ["moving_platform", "mixed"]:
                mp_width = random.choice([150, 180, 210])
                mp_x = start_edge + int(gap_len * random.choice([0.42, 0.50, 0.58]))
                mp_y = GROUND_Y - random.choice([166, 174])
                axis = "x" if random.random() < 0.78 else "y"
                amp = random.choice([46, 58, 70]) if axis == "x" else random.choice([18, 24, 30])
                self.platforms.append(Platform(mp_x, mp_y, mp_width, move_axis=axis, amplitude=amp, speed=0.0018 + difficulty * 0.0008))
                for i in range(2):
                    self.collectibles.append(Collectible("coin", mp_x + 42 + i * 46, mp_y - 42))

            # A short landing after the hidden/moving path. Not endless land.
            self.ground_segments.append(GroundSegment(landing_x, landing_w))

            # Useful floating platform on/near the landing. High enough to walk under, reachable with one jump.
            if random.random() < 0.78:
                px = landing_x + random.randint(45, max(50, landing_w - 260))
                py = GROUND_Y - random.choice([166, 174, 182])
                pw = random.choice([210, 240, 270])
                moving_landing_platform = difficulty > 0.25 and random.random() < 0.35
                if moving_landing_platform:
                    self.platforms.append(Platform(px, py, pw, move_axis="x", amplitude=random.choice([36, 48, 60]), speed=0.0018 + difficulty * 0.0007))
                else:
                    self.platforms.append(Platform(px, py, pw))
                for i in range(random.choice([2, 3])):
                    self.collectibles.append(Collectible("coin", px + 50 + i * 46, py - 42))
                if landing_x > 1600 and random.random() < (0.35 + difficulty * 0.35):
                    self.skeletons.append(Skeleton(px + pw - 115, py))

            # More skeletons in the long run, but only on safe landing areas/platforms where combat makes sense.
            if landing_x > 900:
                base_chance = 0.78 + difficulty * 0.20
                if random.random() < base_chance:
                    max_count = 1
                    if landing_x > 4500:
                        max_count = 2
                    if landing_x > 8500:
                        max_count = 3
                    skel_count = random.randint(1, max_count)
                    spacing = max(70, landing_w // (skel_count + 1))
                    for i in range(skel_count):
                        sx = landing_x + 55 + i * spacing + random.randint(-18, 22)
                        sx = max(landing_x + 55, min(sx, landing_x + landing_w - 120))
                        self.skeletons.append(Skeleton(sx, GROUND_Y))

            # A few collectibles on safe land, but not spammed everywhere.
            if random.random() < 0.68:
                for i in range(random.choice([2, 3])):
                    kind = "gem" if random.random() < 0.30 else "coin"
                    self.collectibles.append(Collectible(kind, landing_x + 70 + i * 42, GROUND_Y - 46))

            # Next chunk starts exactly where the safe land ends, making another gap.
            self.generated_until = landing_x + landing_w

    def cleanup_old_objects(self):
        cutoff = self.camera_x - 900
        self.ground_segments = [g for g in self.ground_segments if g.x + g.w > cutoff]
        self.platforms = [p for p in self.platforms if max(p.x, p.base_x) + p.w > cutoff]
        self.hidden_blocks = [h for h in self.hidden_blocks if max(h.x, h.base_x) + TILE > cutoff]
        self.collectibles = [c for c in self.collectibles if not c.collected and c.x > cutoff]
        self.keys = [k for k in self.keys if not k.dead and k.x > cutoff]
        self.chests = [c for c in self.chests if not c.dead and c.x > cutoff]
        self.skeletons = [s for s in self.skeletons if not s.dead and s.x > cutoff]
        self.messages = [m for m in self.messages if m.life > 0]

    def spawn_skeleton_wave(self, count=None):
        # Spawn extra skeletons only on real safe land ahead, not randomly in the air.
        if count is None:
            count = 2 if self.score < 7000 else 3
        ahead = [g for g in self.ground_segments if g.x > self.player.x + 260 and g.x < self.camera_x + SCREEN_WIDTH + 950 and g.w >= 260]
        if not ahead:
            return
        seg = min(ahead, key=lambda g: g.x)
        spacing = max(72, seg.w // (count + 1))
        for i in range(count):
            sx = seg.x + 50 + i * spacing
            sx = min(sx, seg.x + seg.w - 120)
            self.skeletons.append(Skeleton(sx, GROUND_Y))
        self.add_banner("SKELETON WAVE!", RED, 1300)
        self.shake(5, 280)

    def start_glitch_storm(self):
        self.glitch_storm_timer = GLITCH_STORM_DURATION
        self.next_glitch_storm_score += random.randint(2300, 3300)
        self.add_banner("GLITCH STORM!", RED, 1600)
        self.shake(7, 420)
        self.spawn_skeleton_wave(2 if self.score < 8000 else 3)

    def check_perfect_glitch(self, active_number):
        if not self.player.on_ground:
            self.was_on_ground = False
            return
        # Award when the player lands on an active hidden block.
        feet = pygame.Rect(self.player.rect.left + 4, self.player.rect.bottom - 4, self.player.rect.w - 8, 8)
        landed_block = None
        for hb in self.hidden_blocks:
            if hb.is_active(active_number) and feet.colliderect(hb.rect):
                landed_block = id(hb)
                break
        if landed_block is not None and (not self.was_on_ground or self.last_perfect_block != landed_block):
            self.score += PERFECT_GLITCH_BONUS
            self.add_message(f"PERFECT +{PERFECT_GLITCH_BONUS}", self.player.x, self.player.y - 20, GREEN)
            self.last_perfect_block = landed_block
        self.was_on_ground = True

    def handle_number_press(self, number):
        if number is None or self.game_over:
            return
        if self.wrong_key_cooldown > 0:
            return
        # Wrong-key penalty only checks nearby useful hidden blocks, so it does not punish random far-away blocks.
        near_blocks = []
        for hb in self.hidden_blocks:
            dx = abs(hb.rect.centerx - self.player.rect.centerx)
            dy = abs(hb.rect.centery - self.player.rect.centery)
            if dx < 210 and dy < 145:
                near_blocks.append(hb)
        if near_blocks and all(hb.number != number for hb in near_blocks):
            self.score = max(0, self.score - WRONG_KEY_PENALTY)
            self.wrong_key_cooldown = WRONG_KEY_COOLDOWN
            self.add_message(f"WRONG CODE -{WRONG_KEY_PENALTY}", self.player.x, self.player.y - 28, RED)
            self.add_banner("WRONG CODE!", RED, 850)
            self.shake(5, 230)

    def drop_from_skeleton(self, skeleton):
        drop_x = skeleton.rect.centerx - 16
        floor_y = skeleton.rect.bottom
        drop_y = floor_y - 38

        if not self.player.has_key and not any(not k.dead for k in self.keys):
            self.keys.append(KeyDrop(drop_x, drop_y))
            self.add_message("KEY DROP", drop_x, drop_y - 28, YELLOW)
        else:
            if self.player.has_key:
                self.chests.append(ChestBlock(drop_x, floor_y - 44))
                self.add_message("CHEST DROP", drop_x, drop_y - 28, YELLOW)
            else:
                self.collectibles.append(Collectible("coin", drop_x, drop_y))

    def open_nearby_chest(self):
        if not self.player.has_key:
            self.add_message("NEED KEY", self.player.x, self.player.y - 18, RED)
            return

        open_area = self.player.rect.inflate(100, 70)
        for chest in self.chests:
            if not chest.dead and open_area.colliderect(chest.rect):
                chest.dead = True
                self.player.has_key = False
                play_sound(snd_collect)
                reward = random.choices(
                    ["full_health", "extra_damage", "bonus_score", "skeleton", "wave", "storm"],
                    weights=[26, 24, 20, 17, 8, 5],
                    k=1
                )[0]

                if reward == "full_health":
                    self.player.heal_full()
                    self.score += 80
                    self.add_message("FULL HEALTH", chest.x, chest.y - 35, GREEN)
                    self.add_banner("CHEST: FULL HEALTH!", GREEN, 1100)
                elif reward == "extra_damage":
                    self.player.damage = 2
                    self.player.damage_boost_timer = DAMAGE_BOOST_DURATION
                    self.score += 120
                    self.add_message("DMG BOOST", chest.x, chest.y - 35, YELLOW)
                    self.add_banner("CHEST: DAMAGE BOOST!", YELLOW, 1100)
                elif reward == "bonus_score":
                    self.score += 300
                    self.add_message("+300 SCORE", chest.x, chest.y - 35, BLUE)
                    self.add_banner("CHEST: +300 SCORE!", BLUE, 1100)
                elif reward == "wave":
                    self.add_message("WAVE!", chest.x, chest.y - 35, RED)
                    self.spawn_skeleton_wave(2)
                elif reward == "storm":
                    self.add_message("STORM!", chest.x, chest.y - 35, RED)
                    self.start_glitch_storm()
                else:
                    self.skeletons.append(Skeleton(chest.x + 70, chest.rect.bottom))
                    self.add_message("MIMIC!", chest.x, chest.y - 35, RED)
                    self.add_banner("MIMIC CHEST!", RED, 1100)
                    self.shake(6, 280)
                return

        self.add_message("GET CLOSER", self.player.x, self.player.y - 18, LIGHT_GRAY)

    def update(self, dt):
        keys = pygame.key.get_pressed()
        active_number = get_active_number(keys)

        if self.game_over:
            return

        if self.banner_timer > 0:
            self.banner_timer = max(0, self.banner_timer - dt)
        if self.screen_shake_timer > 0:
            self.screen_shake_timer = max(0, self.screen_shake_timer - dt)
        if self.wrong_key_cooldown > 0:
            self.wrong_key_cooldown = max(0, self.wrong_key_cooldown - dt)
        if self.low_health_warning_cooldown > 0:
            self.low_health_warning_cooldown = max(0, self.low_health_warning_cooldown - dt)
        if self.glitch_storm_timer > 0:
            self.glitch_storm_timer = max(0, self.glitch_storm_timer - dt)
            # Small survival bonus during storm to make the risk feel rewarding.
            self.score += 0.018 * dt

        self.camera_x = max(0, self.player.x - 310)
        self.generate_until(self.camera_x + SCREEN_WIDTH + 1300)

        # Slowly looping background at exactly 0.15 speed.
        self.bg_scroll += BG_SPEED
        if self.bg_scroll >= background_img.get_width():
            self.bg_scroll = 0.0

        # Update moving platforms and moving hidden blocks before collision is calculated.
        for platform in self.platforms:
            platform.update(dt)
        for block in self.hidden_blocks:
            block.update(dt)
            block.update_visibility_timer(dt, active_number)

        solids = self.solid_rects(active_number)
        self.player.update(dt, keys, solids)
        self.carry_player_on_moving_blocks(active_number)
        self.check_perfect_glitch(active_number)
        self.camera_x = max(0, self.player.x - 310)

        # Score from distance and survival.
        distance_score = int(self.player.x * 0.08)
        self.score = max(self.score, distance_score)

        # Score milestone banners.
        while self.milestone_index < len(MILESTONES) and self.score >= MILESTONES[self.milestone_index]:
            milestone = MILESTONES[self.milestone_index]
            self.add_banner(f"{milestone} SCORE!", YELLOW, 1150)
            self.add_message(f"MILESTONE {milestone}", self.player.x, self.player.y - 35, YELLOW)
            self.score += 25
            self.milestone_index += 1

        # Glitch storm starts later and repeats, not at the very beginning.
        if self.score >= self.next_glitch_storm_score and self.glitch_storm_timer <= 0:
            self.start_glitch_storm()

        # Low health warning, repeated slowly so it does not spam.
        if self.player.health <= LOW_HEALTH_WARNING_HALVES and self.player.health > 0 and self.low_health_warning_cooldown <= 0:
            self.add_banner("LOW HEALTH!", RED, 1000)
            self.add_message("LOW HEALTH", self.player.x, self.player.y - 34, RED)
            self.low_health_warning_cooldown = 1800

        # Collect coins/gems.
        for item in self.collectibles:
            item.update(dt)
            if not item.collected and self.player.rect.colliderect(item.rect):
                item.collected = True
                if item.kind == "coin":
                    self.score += 10
                    self.add_message("+10", item.x, item.y - 20, YELLOW)
                else:
                    self.score += 25
                    self.add_message("+25", item.x, item.y - 20, BLUE)
                play_sound(snd_collect)

        # Pick up key.
        for key in self.keys:
            key.update(dt)
            if not key.dead and self.player.rect.colliderect(key.rect):
                key.dead = True
                self.player.has_key = True
                self.score += 40
                self.add_message("KEY GET", key.x, key.y - 28, YELLOW)
                play_sound(snd_collect)

        # Update skeletons. Static solids only, so skeletons patrol land/platforms and do not depend on hidden keys.
        skeleton_solids = self.static_solid_rects()
        for skel in self.skeletons:
            skel.update(dt, self.player, skeleton_solids)

        # Player attack hits skeletons once per attack swing.
        if self.player.attack_timer > 0:
            attack_rect = self.player.attack_rect()
            for skel in self.skeletons:
                if not skel.dying and not skel.dead and attack_rect.colliderect(skel.rect):
                    killed = skel.take_damage(self.player.damage)
                    self.player.attack_timer = 0
                    if killed:
                        self.score += 100
                        self.drop_from_skeleton(skel)
                    break

        for msg in self.messages:
            msg.update(dt)

        if self.player.health <= 0 or self.player.y > SCREEN_HEIGHT + 220:
            self.game_over = True
            if self.score > self.highscore:
                self.highscore = self.score
                save_highscore(self.highscore)

        self.cleanup_old_objects()

    def draw_background(self):
        x = -self.bg_scroll
        while x < SCREEN_WIDTH:
            screen.blit(background_img, (int(x), GAME_TOP))
            x += background_img.get_width()

    def draw_world(self):
        for p in self.platforms:
            p.draw(self.camera_x)
        keys = pygame.key.get_pressed()
        active_number = get_active_number(keys)
        for h in self.hidden_blocks:
            h.draw(self.camera_x, active_number)
        for seg in self.ground_segments:
            seg.draw(self.camera_x)

    def draw_hud(self, active_number):
        pygame.draw.rect(screen, PURPLE, (0, 0, SCREEN_WIDTH, HUD_HEIGHT))
        pygame.draw.rect(screen, BLACK, (0, HUD_HEIGHT - 4, SCREEN_WIDTH, 4))

        draw_text(f"SCORE: {int(self.score):05d}", 16, 10, WHITE)
        draw_text(f"HIGH: {int(self.highscore):05d}", 210, 10, YELLOW)
        if self.player.damage_boost_timer > 0:
            boost_seconds = max(1, int(self.player.damage_boost_timer / 1000))
            draw_text(f"DMG BOOST: {boost_seconds}s", 390, 10, YELLOW)
        else:
            draw_text(f"DMG: {self.player.damage}", 390, 10, WHITE)
        draw_text(f"KEY: {'YES' if self.player.has_key else 'NO'}", 560, 10, YELLOW if self.player.has_key else WHITE)

        hx = 710
        remaining = self.player.health
        for i in range(3):
            if remaining >= 2:
                img = heart_full
            elif remaining == 1:
                img = heart_half
            else:
                img = heart_empty
            screen.blit(img, (hx + i * 36, 8))
            remaining -= 2

        active_txt = "NONE" if active_number is None else str(active_number)
        draw_text(f"ACTIVE NUMPAD: {active_txt}", 870, 10, WHITE if active_number is None else YELLOW)
        if self.glitch_storm_timer > 0:
            draw_text(f"GLITCH STORM: {int(self.glitch_storm_timer / 1000) + 1}s", 1060, 10, RED)
        if self.player.health <= LOW_HEALTH_WARNING_HALVES and pygame.time.get_ticks() % 600 < 330:
            draw_text("LOW HEALTH!", 1060, 42, RED)
        draw_text("A/D or Arrows: Move | Space: Jump | Enter: Attack | Q: Open Chest | Hold only one NUMPAD: 7 / 8 / 9", 16, 45, LIGHT_GRAY)

    def draw(self):
        keys = pygame.key.get_pressed()
        active_number = get_active_number(keys)

        self.draw_background()
        self.draw_world()

        for chest in self.chests:
            if not chest.dead:
                chest.draw(self.camera_x)
                near = self.player.rect.inflate(100, 70).colliderect(chest.rect)
                if near and self.player.has_key:
                    sx = world_to_screen_x(chest.x, self.camera_x)
                    draw_text("Q", sx + 12, int(chest.y) - 28, YELLOW, SMALL_FONT)

        for item in self.collectibles:
            item.draw(self.camera_x)
        for key in self.keys:
            if not key.dead:
                key.draw(self.camera_x)

        for skel in self.skeletons:
            skel.draw(self.camera_x)

        self.player.draw(self.camera_x)

        for msg in self.messages:
            msg.draw(self.camera_x)

        self.draw_hud(active_number)

        # Center banner for events/rewards/warnings.
        if self.banner_timer > 0 and self.banner_text:
            surf = MID_FONT.render(self.banner_text, True, self.banner_color)
            shadow = MID_FONT.render(self.banner_text, True, BLACK)
            rect = surf.get_rect(center=(SCREEN_WIDTH // 2, 118))
            screen.blit(shadow, (rect.x + 3, rect.y + 3))
            screen.blit(surf, rect)

        # Low health and glitch storm overlays, using simple transparent rectangles only.
        if self.player.health <= LOW_HEALTH_WARNING_HALVES and not self.game_over and pygame.time.get_ticks() % 700 < 180:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((180, 0, 0, 34))
            screen.blit(overlay, (0, 0))
        if self.glitch_storm_timer > 0:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            alpha = 22 if pygame.time.get_ticks() % 240 < 120 else 38
            overlay.fill((115, 20, 150, alpha))
            screen.blit(overlay, (0, 0))

        if self.game_over:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 165))
            screen.blit(overlay, (0, 0))
            title = BIG_FONT.render("GAME OVER", True, RED)
            screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 260)))
            score = MID_FONT.render(f"Score: {int(self.score)}   High Score: {int(self.highscore)}", True, WHITE)
            screen.blit(score, score.get_rect(center=(SCREEN_WIDTH // 2, 330)))
            tip = FONT.render("Press R to Restart or ESC to Quit", True, YELLOW)
            screen.blit(tip, tip.get_rect(center=(SCREEN_WIDTH // 2, 390)))

        # Simple screen shake effect without new assets.
        if self.screen_shake_timer > 0 and self.screen_shake_intensity > 0:
            saved = screen.copy()
            ox = random.randint(-self.screen_shake_intensity, self.screen_shake_intensity)
            oy = random.randint(-self.screen_shake_intensity, self.screen_shake_intensity)
            screen.fill(BLACK)
            screen.blit(saved, (ox, oy))


# ------------------------------------------------
# MAIN LOOP
# ------------------------------------------------
def main():
    game = Game()
    running = True

    while running:
        dt = clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                num = key_to_numpad_number(event.key) 
                if num is not None and not game.game_over:
                    game.handle_number_press(num)

                if event.key == pygame.K_SPACE and not game.game_over:
                    game.player.request_jump()

                if event.key == pygame.K_RETURN and not game.game_over:
                    game.player.start_attack()

                if event.key == pygame.K_q and not game.game_over:
                    game.open_nearby_chest()

                if event.key == pygame.K_r and game.game_over:
                    game.reset()

        game.update(dt)
        game.draw()
        pygame.display.flip()

    if game.score > game.highscore:
        save_highscore(game.score)
    pygame.quit()


if __name__ == "__main__":
    main()
