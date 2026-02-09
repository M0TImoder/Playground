import pygame
import sys
import math
import numpy as np

pygame.init()

WIDTH, HEIGHT = 1280, 720
CELL = 16
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Wavy")
font = pygame.font.SysFont("Consolas", CELL, bold=True)

CHARS = " .:-=+*#%@$"
MAX_LEVEL = len(CHARS) - 1

_glyph_cache = {}

def get_glyph(char_idx, gray):
    key = (char_idx, gray)
    surf = _glyph_cache.get(key)
    if surf is None:
        surf = font.render(CHARS[char_idx], False, (gray, gray, gray))
        _glyph_cache[key] = surf
    return surf

fullscreen = False
clock = pygame.time.Clock()

# 波: (cx, cy, birth_time, strength)
waves = []

WAVE_SPEED = 250.0
WAVE_LIFE = 2.5
WAVE_WIDTH = 35.0
CURSOR_RADIUS = 60.0

# 軌跡から波を生成する設定
prev_mx, prev_my = 0, 0
trail_accum = 0.0
TRAIL_WAVE_INTERVAL = 25.0
TRAIL_WAVE_STRENGTH = 0.4
MAX_WAVES = 200

# グリッド座標キャッシュ
cached_size = (0, 0)
grid_x = None
grid_y = None

while True:
    now = pygame.time.get_ticks() / 1000.0
    sw, sh = screen.get_size()
    mx, my = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()
            elif event.key == pygame.K_F11:
                fullscreen = not fullscreen
                if fullscreen:
                    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                else:
                    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            waves.append((float(mx), float(my), now, 1.0))

    # 軌跡に沿って小さな波を自動生成
    dx = mx - prev_mx
    dy = my - prev_my
    move_dist = math.sqrt(dx * dx + dy * dy)
    if move_dist > 0:
        trail_accum += move_dist
        # 速度に応じて波の強さを変化
        speed_factor = min(move_dist / 30.0, 1.0)
        strength = TRAIL_WAVE_STRENGTH * (0.3 + 0.7 * speed_factor)
        while trail_accum >= TRAIL_WAVE_INTERVAL:
            ratio = 1.0 - (trail_accum - TRAIL_WAVE_INTERVAL) / move_dist
            ratio = max(0.0, min(1.0, ratio))
            wx = prev_mx + dx * ratio
            wy = prev_my + dy * ratio
            waves.append((wx, wy, now, strength))
            trail_accum -= TRAIL_WAVE_INTERVAL
    prev_mx, prev_my = mx, my

    # 古い波を除去 & 上限
    waves = [w for w in waves if now - w[2] < WAVE_LIFE]
    if len(waves) > MAX_WAVES:
        waves = waves[-MAX_WAVES:]

    # グリッド座標（サイズ変更時のみ再計算）
    cols = sw // CELL
    rows = sh // CELL
    if cached_size != (cols, rows):
        cached_size = (cols, rows)
        cx_arr = np.arange(cols, dtype=np.float32) * CELL + CELL // 2
        cy_arr = np.arange(rows, dtype=np.float32) * CELL + CELL // 2
        grid_x, grid_y = np.meshgrid(cx_arr, cy_arr)

    # 明るさ計算
    brightness = np.zeros((rows, cols), dtype=np.float32)

    # カーソル近傍の柔らかい光
    dist_cursor = np.sqrt((grid_x - mx) ** 2 + (grid_y - my) ** 2)
    mask = dist_cursor < CURSOR_RADIUS
    brightness[mask] += (1.0 - dist_cursor[mask] / CURSOR_RADIUS) * 0.4

    # 全波をまとめて処理
    for cx, cy, t0, strength in waves:
        age = now - t0
        radius = age * WAVE_SPEED
        fade = 1.0 - age / WAVE_LIFE
        # バウンディングボックスで計算範囲を絞る
        r_max = radius + WAVE_WIDTH
        r_min = max(0, radius - WAVE_WIDTH)
        col_min = max(0, int((cx - r_max - CELL) / CELL))
        col_max = min(cols, int((cx + r_max + CELL) / CELL) + 1)
        row_min = max(0, int((cy - r_max - CELL) / CELL))
        row_max = min(rows, int((cy + r_max + CELL) / CELL) + 1)
        if col_min >= col_max or row_min >= row_max:
            continue
        gx = grid_x[row_min:row_max, col_min:col_max]
        gy = grid_y[row_min:row_max, col_min:col_max]
        dist = np.sqrt((gx - cx) ** 2 + (gy - cy) ** 2)
        diff = np.abs(dist - radius)
        wmask = diff < WAVE_WIDTH
        if not np.any(wmask):
            continue
        brightness[row_min:row_max, col_min:col_max][wmask] += \
            (1.0 - diff[wmask] / WAVE_WIDTH) * fade * strength

    np.clip(brightness, 0.0, 1.0, out=brightness)

    screen.fill((0, 0, 0))

    lit_rows, lit_cols = np.where(brightness > 0.01)
    for i in range(len(lit_rows)):
        r = lit_rows[i]
        c = lit_cols[i]
        b = brightness[r, c]
        idx = min(int(b * MAX_LEVEL), MAX_LEVEL)
        if idx == 0:
            continue
        gray = min(int(b * 255), 255)
        screen.blit(get_glyph(idx, gray), (c * CELL, r * CELL))

    pygame.display.flip()
    clock.tick(60)
