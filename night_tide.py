# NIGHT TIDE
# JIN2 · @jin_22ee · 2026    Free to use for personal projects, see LICENSE.txt.
#
# run:   pip install -r requirements.txt
#        python night_tide.py
# keys:  Space pause · R restart · S screenshot · Esc quit

import sys
import time
from pathlib import Path

import numpy as np
import pygame

# letters, dark to bright
POOLS = ["1il!;:", "rtfjcvxz=+", "aeoun0{}[]<>", "08B$#&%Q"]
CHARS = " .,:~+*^01|/\\-_#()x" + "".join(POOLS)
AT = {c: i for i, c in enumerate(CHARS)}
FILL = np.array([[AT[p[k % len(p)]] for k in range(12)] for p in POOLS])

LOOP = 20.0
TRAIL = 0.5
CELL = (6, 9, 10)          # cell width, cell height, font px

TAG_COLOR = [[20, 34, 64], [28, 50, 92], [40, 72, 122], [62, 100, 152], [98, 136, 182], [146, 176, 210],
             [196, 206, 218], [236, 238, 240], [222, 230, 240], [86, 84, 98], [170, 180, 205]]
SILVER, GLINT, FOAM, SAND, STAR = 6, 7, 8, 9, 10

HORIZON = -0.28            # screen y of the horizon
EYE = 0.3                  # camera height

# (amplitude, wavelength, direction)
SWELLS = [(0.045, 1.70, -0.05), (0.032, 1.10, 0.30), (0.030, 0.65, 0.10), (0.020, 0.43, -0.45), (0.014, 0.28, 0.60), (0.009, 0.18, -0.20),
          (0.007, 0.115, 1.00), (0.005, 0.075, -0.85), (0.0028, 0.048, 0.45), (0.0018, 0.032, -0.70)]

# breakers
SHORE = 0.47
Z_FAR, Z_BREAK = 2.4, 0.78
T_SWELL, T_BORE, T_SWASH = 4.0, 2.0, 3.0
PERIOD = 2.5
RISE = 0.09

_grid = {}


def smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def grid(cols, rows, aspect):
    if (cols, rows) not in _grid:
        rng = np.random.default_rng(9)
        x = ((np.arange(cols) + 0.5) / cols - 0.5) * aspect
        y = (np.arange(rows) + 0.5) / rows - 0.5
        X, Y = np.meshgrid(x, y)
        _grid[cols, rows] = X, Y, rng.random((rows, cols)), rng.integers(0, 12, (rows, cols)), aspect / cols, 1.0 / rows
    return _grid[cols, rows]


def noise(x, y, s):
    return (np.sin(7.1 * x + 3.3 * np.sin(5.3 * y + s) + s) + np.sin(11.3 * y - 4.7 * x + 2 * s)
            + 0.6 * np.sin(17 * x + 13 * y - s)) / 2.6


def lace(xw, z, seed, age):
    # torn foam, more holes with age
    warp = noise(4 * xw, 15 * z, seed + 7)
    n = noise(9 * xw + 1.5 * warp, 60 * z + 3 * warp, seed) + 0.5 * noise(23 * xw, 140 * z + warp, seed + 1)
    return smooth((n / 1.5 + 0.55 - 0.7 * age) / 0.3)


def front_of(a, xw, seed, zb, ts, tb):
    # wave front distance at age a: swell, bore, swash
    b = np.clip(a - ts, 0, tb)
    u = np.clip((a - ts - tb) / T_SWASH, 0, 1)
    reach = 0.09 + 0.025 * np.sin(2.3 * xw + seed)
    swell = Z_FAR - (Z_FAR - zb) * np.clip(a, 0, None) / ts
    bore = zb - (zb - SHORE) * (1 - (1 - b / tb) ** 2)
    swash = SHORE - reach * 4 * u * (1 - u)
    return np.where(a < ts, swell, np.where(a < ts + tb, bore, swash)), reach


def frame(t, cols, rows, aspect):
    X, Y, rnd, hsh, cw, row = grid(cols, rows, aspect)
    below = Y > HORIZON + 0.5 * row
    z = EYE / np.maximum(Y - HORIZON, 1e-3)
    xw = X * z
    water = below & (z >= SHORE)
    beach = below & (z < SHORE)

    # Gerstner swells, slopes only; sub-cell waves are filtered out
    sx = np.zeros_like(X)
    sz = np.zeros_like(X)
    hgt = np.zeros_like(X)
    for amp, lam, ang in SWELLS:
        k = 2 * np.pi / lam
        w = 2 * np.pi * max(1, round(LOOP * np.sqrt(9.8 * k) / 8 / (2 * np.pi))) / LOOP
        dx, dz = np.sin(ang), -np.cos(ang)
        foot = k * np.hypot(dx * cw * z, dz * row * z * z / EYE)
        keep = np.exp(-(foot / 1.4) ** 2)
        ph = k * (dx * xw + dz * z) - w * t + 3.7 * lam
        steep = amp * k * keep
        sharp = 1 / (1 - 0.5 * steep * np.sin(ph))
        sx += steep * dx * np.cos(ph) * sharp
        sz += steep * dz * np.cos(ph) * sharp
        hgt += amp * np.sin(ph) * keep

    # breakers
    foam = np.zeros_like(X)
    face = np.zeros_like(X)
    lip = np.zeros_like(X)
    spray = np.zeros(X.shape, bool)
    film = np.zeros_like(X)
    wet = np.zeros_like(X)
    for n in range(int(np.floor((t - 12) / PERIOD)), int(np.floor(t / PERIOD)) + 1):
        w_ = np.random.default_rng(100 + n % 8)
        size, angle, bend, late = w_.uniform(0.5, 1.15), w_.uniform(-0.9, 0.9), w_.uniform(-1.2, 1.2), w_.uniform(-0.5, 0.5)
        zb = Z_BREAK + (1.15 - Z_BREAK) * (1.15 - size) / 0.65 + w_.uniform(-0.05, 0.05)
        rise = RISE * size
        ts = T_SWELL * (Z_FAR - zb) / (Z_FAR - Z_BREAK)
        tb = T_BORE * (zb - SHORE) / (Z_BREAK - SHORE) ** 0.6
        seed = (n % 8) * 2.39
        brk = (0.35 + 0.65 * size) * smooth((noise(1.7 * X + seed, seed, n % 8) + 0.45 * size + 0.2) / 0.9)
        brk = np.maximum(brk, 0.35)
        peel = angle * X + bend * X * X + 0.15 * np.sin(2.0 * X + seed) + 0.06 * np.sin(5.3 * X - seed)
        a = t - n * PERIOD - late + peel
        wf = np.zeros_like(X)
        if np.all(a < 0):
            continue
        front, reach = front_of(a, xw, seed, zb, ts, tb)
        yf = HORIZON + EYE / front
        since = a - ts
        g = np.clip(a / ts, 0, 1) ** 2 * (a > 0)

        # swell bump: steep front, long back
        tall = rise * g * (1 - smooth(since / 0.5))
        d = z - front
        wd = np.where(d < 0, 0.05, 0.16)
        bump = tall * np.exp(-(d / wd) ** 2)
        sz += bump * (-2 * d / wd ** 2) * water
        hgt += bump * water

        # wave face and lip
        hs = tall / front
        stand = below & (Y < yf) & (Y > yf - hs) & (since < 0.5)
        face = np.maximum(face, stand * (0.25 + 0.5 * (yf - Y) / np.maximum(hs, 1e-4)))
        lip = np.maximum(lip, below * np.exp(-((Y - (yf - hs)) / (0.8 * row)) ** 2) * g * (since < 0.5))

        # break
        peak = rise / zb
        burst = np.sin(np.pi * np.clip(since / 1.3, 0, 1))
        boil = noise(19 * X + 0.4 * t, 23 * Y - 1.2 * t, n) + 0.5 * noise(41 * X, 47 * Y + 2 * t, n + 2)
        lumps = 0.55 + 0.45 * np.abs(np.sin(31 * X + 2.1 * noise(5 * X, 0.4 * t, n) + 1.5 * t))
        hc = peak * (0.2 + 0.4 * burst) * lumps * zb / front
        crash = below & (Y < yf) & (Y > yf - hc) & (since > 0) & (since < 1.4)
        depth = np.clip((Y - (yf - hc)) / np.maximum(hc, 1e-4), 0, 1)
        wf = np.maximum(wf, crash * (1.0 - 0.35 * depth) * smooth((boil + 1.2 - 0.5 * depth) / 0.4))
        mist = below & (Y < yf - hc) & (Y > yf - peak * 1.8 * burst * zb / front)
        spray |= mist & (brk > 0.5) & (since > 0.1) & (since < 1.3) & (rnd > 0.75 + 0.25 * (yf - Y) / (peak * 1.8 * zb / front + 1e-3))

        # white water roller and trailing foam
        roll = np.clip(since, 0, None)
        hr = 0.5 * peak * (1 - 0.75 * smooth(roll / tb)) * lumps * zb / front
        roller = below & (Y < yf) & (Y > yf - hr) & (since > 0.8) & (since < tb)
        rd = np.clip((Y - (yf - hr)) / np.maximum(hr, 1e-4), 0, 1)
        wf = np.maximum(wf, roller * (0.95 - 0.4 * rd) * smooth((boil + 0.8 - 0.5 * rd) / 0.4))
        behind = z - front
        band = 0.04 + 0.15 * smooth(roll / 1.5)
        fade = (1 - np.clip(behind / band, 0, 1)) ** 1.6
        edge = np.exp(-(behind / 0.012) ** 2)
        on = water & (behind > -0.005) & (behind < band) & (since > 0.3) & (since < tb + 0.3)
        wf = np.maximum(wf, on * ((0.35 + 0.65 * fade) * lace(xw, z, seed, roll / 3.5) + 0.9 * edge))
        old = water & (behind > band) & (z < zb + 0.3) & (since > 0.5)
        clump = smooth((noise(3 * xw + seed, 12 * z, seed + 5) - 0.1) / 0.3)
        wf = np.maximum(wf, old * 0.6 * np.exp(-roll / 2.2) * clump * lace(xw, z, seed + 3, 0.1))

        # foam joins up sideways as it comes in
        join = smooth((np.clip(since, 0, None) - 0.1) / (0.35 * tb))
        foam = np.maximum(foam, wf * np.maximum(brk, join * (0.85 + 0.15 * size)))

        # swash on the sand
        u = np.clip((since - tb) / T_SWASH, 0, 1)
        sw = (since > tb) & (u < 1)
        scallop = 0.008 * np.sin(31 * xw + seed) + 0.004 * np.sin(73 * xw - 2 * seed)
        rim = np.exp(-((z - front - scallop) / 0.008) ** 2) * sw
        left = np.exp(-((z - SHORE + reach - scallop) / 0.007) ** 2) * (u > 0.5) * np.exp(-np.clip(since - tb - 0.5 * T_SWASH, 0, None) / 1.6)
        foam = np.maximum(foam, beach * (rim * (1 - 0.4 * u) + 0.6 * left) * lace(xw, z * 2, seed + 1, 0.5 * u + 0.15))
        film = np.maximum(film, beach * (z > front) * sw)
        wet = np.maximum(wet, beach * (z > SHORE - reach) * (since > tb) * np.exp(-np.clip(since - tb - T_SWASH, 0, None) / 2.5))

    # shading: sky reflection with fresnel
    nrm = np.stack([-sx, np.ones_like(sx), -sz])
    nrm /= np.linalg.norm(nrm, axis=0)
    v = np.stack([xw, -EYE * np.ones_like(xw), z])
    v /= np.linalg.norm(v, axis=0)
    r = v - 2 * (v * nrm).sum(0) * nrm
    facing = np.clip(-(v * nrm).sum(0), 0, 1)
    fresnel = 0.03 + 0.97 * (1 - facing) ** 5
    sky = 0.35 + 0.65 * (1 - np.clip(r[1], 0, 1)) ** 2
    dim = 0.45 + 0.55 * smooth((Y - HORIZON) / 0.2)
    glow = 0.06 + fresnel * sky * 0.75 * dim + 0.08 * smooth(hgt / 0.06 + 0.5)
    far = 1 - smooth((Y - HORIZON) / 0.25)
    glow = glow * (1 - 0.55 * far) + far * 0.42 * smooth((-sz + 0.01) / 0.05)
    shimmer = 0.07 * np.sin(rnd * 977 + t * (2.5 + 4 * rnd))
    lum = np.clip(glow * 1.2 + shimmer, 0, 1.0)
    lum = np.where(face > 0, 0.12 + 0.3 * face, lum)
    lum = lum * (1 - 0.75 * smooth(foam / 0.35))

    # whitecaps far out
    hn = hgt / 0.05
    churn = noise(2.2 * xw + 0.35 * t, 7 * z - 0.9 * t, 4) + 0.5 * np.sin(1.7 * t + 9 * noise(xw, 3 * z, 8))
    cap = water & (z > Z_BREAK + 0.3) & (foam < 0.1) & (rnd < 0.8) & (smooth((hn - 0.5) / 0.3) * smooth((churn - 0.35) / 0.3) > 0.4)

    lum = lum * smooth((lum - 0.06) / 0.22)
    show = (water | (face > 0)) & (lum > 0.03)
    level = np.clip((lum * 3.6).astype(int), 0, 3)
    char = np.where(show, FILL[level, (hsh + (0.6 * t + 3 * hgt / 0.05).astype(int)) % 12], AT[" "])
    char = np.where(show & (lum > 0.8) & (rnd < 0.4), AT["~"], char)
    tag = np.clip((lum * 6).astype(int), 0, 5)
    lum = np.where(show, lum, 0.0)

    # glitter on lit crests
    twinkle = np.sin(rnd * 431 + t * (3 + 7 * rnd) + 40 * hgt)
    crestlit = smooth((lum - 0.2) / 0.25)
    spec = crestlit * smooth((twinkle - 0.68) / 0.15)
    gl = water & (spec > 0.2) & (foam < 0.3)
    char = np.where(gl, np.where(spec > 0.7, np.where(rnd < 0.5, AT["*"], AT["+"]), np.where(rnd < 0.5, AT["^"], AT["."])), char)
    lum = np.where(gl, np.clip(0.5 + 0.7 * spec, 0, 1.15), lum)
    tag = np.where(gl, np.where(spec > 0.55, GLINT, SILVER), tag)

    char = np.where(cap, FILL[1 + (rnd * 2).astype(int), (hsh + int(3 * t)) % 12], char)
    lum = np.where(cap, 0.45 + 0.4 * dim, lum)
    tag = np.where(cap, FOAM, tag)

    crest = (lip > 0.4) & (foam < 0.3)
    char = np.where(crest, AT["~"], char)
    lum = np.where(crest, 0.4 + 0.45 * lip, lum)
    tag = np.where(crest, 4, tag)

    fo = foam > 0.4 + 0.2 * rnd
    flevel = np.clip((3.2 * foam - 0.2).astype(int), 1, 3)
    char = np.where(fo, FILL[flevel, (hsh + int(2 * t)) % 12], char)
    lum = np.where(fo, np.clip(0.6 + 0.55 * foam, 0, 1.15), lum)
    tag = np.where(fo, FOAM, tag)
    sp = spray & ~fo
    char = np.where(sp, np.where(rnd > 0.8, AT["*"], AT["."]), char)
    lum = np.where(sp, 0.8, lum)
    tag = np.where(sp, FOAM, tag)

    # sand
    sheet = beach & ~fo & (film > 0.5) & (rnd < 0.4)
    char = np.where(sheet, AT["-"], char)
    lum = np.where(sheet, 0.32, lum)
    tag = np.where(sheet, 2, tag)
    grain = beach & ~fo & ~sheet & (rnd < 0.08 + 0.15 * wet)
    char = np.where(grain, np.where(rnd < 0.03, AT[":"], AT[","]), char)
    lum = np.where(grain, 0.2 + 0.2 * wet, lum)
    tag = np.where(grain, SAND, tag)

    # stars
    star = ~below & (rnd < 0.003) & (Y < HORIZON - 0.04)
    char = np.where(star, np.where(rnd < 0.0008, AT["+"], AT["."]), char)
    lum = np.where(star, 0.4 + 0.3 * np.sin(0.9 * t + rnd * 7000), lum)
    tag = np.where(star, STAR, tag)

    count = int((char != AT[" "]).sum())
    info = {"swells": len(SWELLS), "foam": float(foam.mean() * 100)}
    return char.astype(int), lum.astype(np.float32), tag.astype(int), info, count


def HUD(info):
    return f"swells {info['swells']}   foam {info['foam']:.2f}"


# window

TITLE = "NIGHT TIDE · JIN2"
SIGN = "@jin_22ee · 2026"
CW, CH, FONT_PX = CELL
W, H = 1080, 960
COLS, ROWS = W // CW, H // CH
ASPECT = (COLS * CW) / (ROWS * CH)
COLOR = np.array(TAG_COLOR, np.float32) / 255
DIM, PINK = (120, 112, 128), (255, 122, 182)


def glyphs():
    font = pygame.font.SysFont("consolas,menlo,dejavusansmono,couriernew,monospace", FONT_PX)
    atlas = []
    for ch in CHARS:
        s = pygame.Surface((CW, CH))
        g = font.render(ch, True, (255, 255, 255))
        s.blit(g, ((CW - g.get_width()) // 2, (CH - g.get_height()) // 2))
        atlas.append(pygame.surfarray.array3d(s)[:, :, 0].T.astype(np.float32) / 255)
    return np.stack(atlas)


class Canvas:
    # glyph mask x colour x brightness, over a fading copy of the previous frame

    def __init__(self, atlas):
        self.atlas = (atlas * 255).astype(np.uint8)
        self.shape = pygame.Surface((COLS * CW, ROWS * CH))
        self.trail = pygame.Surface((W, H))
        self.fade = (int(TRAIL * 255),) * 3

    def reset(self):
        self.trail.fill((0, 0, 0))

    def draw(self, t):
        char, lum, tag, info, count = frame(t, COLS, ROWS, ASPECT)
        mask = self.atlas[char.T].transpose(0, 3, 1, 2).reshape(COLS * CW, ROWS * CH)
        pygame.surfarray.blit_array(self.shape, np.repeat(mask[..., None], 3, 2))
        col = (COLOR[np.clip(tag, 0, len(COLOR) - 1)] * np.clip(lum, 0, 1)[..., None] * 255).astype(np.uint8)
        tint = pygame.transform.scale(pygame.surfarray.make_surface(col.transpose(1, 0, 2)), self.shape.get_size())
        self.shape.blit(tint, (0, 0), special_flags=pygame.BLEND_MULT)
        self.trail.fill(self.fade, special_flags=pygame.BLEND_MULT)
        self.trail.blit(self.shape, (0, 0), special_flags=pygame.BLEND_MAX)
        return self.trail, info, count


def blur(surf, k, radius):
    small = pygame.transform.smoothscale(surf, (W // k, H // k))
    if hasattr(pygame.transform, "gaussian_blur"):
        small = pygame.transform.gaussian_blur(small, max(1, radius // k))
    return pygame.transform.smoothscale(small, (W, H))


def glow_layer(surf, amount):
    layer = surf.copy()
    layer.fill((int(255 * amount),) * 3, special_flags=pygame.BLEND_MULT)
    return layer


def window_size():
    # shrink to fit small or scaled screens
    info = pygame.display.Info()
    k = 1.0
    if info.current_w > 0 and info.current_h > 0:
        k = min(1.0, 0.85 * info.current_h / H, 0.95 * info.current_w / W)
    return int(W * k), int(H * k)


def main():
    pygame.init()
    size = window_size()
    window = pygame.display.set_mode(size)
    pygame.display.set_caption(TITLE)
    screen = pygame.Surface((W, H))
    small = pygame.font.SysFont("consolas,menlo,dejavusansmono,couriernew,monospace", 17)
    canvas, clock = Canvas(glyphs()), pygame.time.Clock()
    t, paused = 0.0, False
    art, info, count = canvas.draw(t)
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                pygame.quit()
                return
            if e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE:
                paused = not paused
            if e.type == pygame.KEYDOWN and e.key == pygame.K_r:
                t = 0.0
                canvas.reset()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_s:
                pygame.image.save(screen, str(Path(__file__).with_name(f"night_tide_{int(time.time())}.png")))
        dt = clock.tick(30) / 1000
        if not paused:
            t += min(dt, 1 / 15)
            if t > LOOP:
                t -= LOOP
            art, info, count = canvas.draw(t)
        screen.fill((0, 0, 0))
        screen.blit(art, (0, 0))
        screen.blit(glow_layer(blur(art, 4, 5), 0.75), (0, 0), special_flags=pygame.BLEND_ADD)
        screen.blit(glow_layer(blur(art, 8, 22), 0.45), (0, 0), special_flags=pygame.BLEND_ADD)
        y = H - 70
        screen.blit(small.render(SIGN, True, (120, 112, 128)), (64, y - 26))
        screen.blit(small.render(HUD(info), True, DIM), (64, y))
        screen.blit(small.render(f"letters {count:05,d}", True, DIM), (64, y + 26))
        tt = small.render(f"{'●' if int(t * 2) % 2 == 0 else ' '} t {t:05.2f}s", True, PINK)
        screen.blit(tt, (W - 64 - tt.get_width(), 30))
        window.blit(screen if size == (W, H) else pygame.transform.smoothscale(screen, size), (0, 0))
        pygame.display.flip()


if __name__ == "__main__":
    sys.exit(main())
