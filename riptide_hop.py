#!/usr/bin/env python3
"""Riptide Hop — original ElbowOS neon tide-hopper arcade (Python 3 + pygame)."""
from __future__ import annotations

import math
import os
import random
import subprocess
import sys
from pathlib import Path

W, H = 1080, 1920
FPS = 30
SECONDS = 15
FRAMES = FPS * SECONDS
TITLE = "RIPTIDE HOP"
OUT = Path("/home/workdir/artifacts/RIPTIDE_HOP_ElbowOS.mp4")

if "--play" not in sys.argv:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

LANES = 11
TOP_HUD, BOT_HUD = 160, 110
PLAY_TOP, PLAY_BOT = TOP_HUD + 40, H - BOT_HUD - 40
LANE_H = (PLAY_BOT - PLAY_TOP) // LANES


def col_lerp(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


class Floater:
    __slots__ = ("kind", "x", "w", "speed", "color", "glow")

    def __init__(self, kind, x, w, speed, color, glow):
        self.kind, self.x, self.w, self.speed = kind, float(x), w, speed
        self.color, self.glow = color, glow

    def tick(self):
        self.x += self.speed
        if self.speed > 0 and self.x - self.w > W + 40:
            self.x = -self.w - 20
        elif self.speed < 0 and self.x + self.w < -40:
            self.x = W + 20

    @property
    def left(self):
        return self.x

    @property
    def right(self):
        return self.x + self.w


class Game:
    def __init__(self, seed=7):
        self.rng = random.Random(seed)
        self.score = 0
        self.lives = 3
        self.t = 0
        self.flash = 0
        self.splash = []
        self.reset_lanes()
        self.spawn_player()

    def reset_lanes(self):
        self.lanes = []
        kinds_cycle = ["bank", "boats", "logs", "fish", "logs", "boats",
                       "fish", "logs", "boats", "fish", "bank"]
        for i, kind in enumerate(kinds_cycle):
            items = []
            if kind == "boats":
                spd = self.rng.choice((-7.2, -5.8, 6.1, 7.5))
                gap = self.rng.randint(280, 360)
                w = self.rng.randint(160, 230)
                x = self.rng.randint(0, 400)
                while x < W + 400:
                    items.append(Floater("boat", x, w, spd, (255, 90, 120), (180, 30, 70)))
                    x += w + gap
            elif kind == "logs":
                spd = self.rng.choice((-4.4, -3.6, 3.8, 4.8))
                gap = self.rng.randint(90, 160)
                w = self.rng.randint(170, 260)
                x = self.rng.randint(-80, 200)
                while x < W + 400:
                    items.append(Floater("log", x, w, spd, (40, 220, 170), (10, 120, 90)))
                    x += w + gap
            elif kind == "fish":
                spd = self.rng.choice((-8.5, -6.8, 7.0, 8.8))
                gap = self.rng.randint(220, 300)
                w = self.rng.randint(90, 130)
                x = self.rng.randint(0, 300)
                while x < W + 400:
                    items.append(Floater("fish", x, w, spd, (255, 210, 50), (200, 140, 10)))
                    x += w + gap
            self.lanes.append({"kind": kind, "items": items})

    def spawn_player(self):
        self.lane = 0
        self.px = W * 0.5
        self.hop_cool = 0
        self.alive = True
        self.bob = 0.0

    def lane_y(self, i):
        return PLAY_BOT - (i + 0.5) * LANE_H

    def hop(self, d):
        if self.hop_cool or not self.alive:
            return
        nxt = self.lane + d
        if 0 <= nxt < LANES:
            self.lane = nxt
            self.hop_cool = 7
            self.score += 8 if d > 0 else 1
            if self.lane == LANES - 1:
                self.score += 220
                self.flash = 8
                self.spawn_player()
                self.lane = 0

    def autoplay(self):
        if self.hop_cool or not self.alive:
            return
        ahead = min(self.lane + 1, LANES - 1)
        info = self.lanes[ahead]
        kind = info["kind"]
        if kind == "bank":
            self.hop(1)
            return
        safe = False
        if kind == "logs":
            for it in info["items"]:
                if it.left + 18 < self.px < it.right - 18:
                    future = self.px
                    ok = True
                    for k in range(8):
                        fx = it.x + it.speed * k
                        if not (fx + 10 < future < fx + it.w - 10):
                            ok = False
                    if ok:
                        safe = True
                        break
            if safe:
                self.hop(1)
            elif self.lanes[self.lane]["kind"] == "logs":
                cur = self.lanes[self.lane]
                for it in cur["items"]:
                    if it.left < self.px < it.right:
                        self.px += it.speed * 0.15
        else:
            blocked = False
            for it in info["items"]:
                pred = it.x + it.speed * 6
                if pred - 10 < self.px < pred + it.w + 10:
                    blocked = True
            if not blocked:
                self.hop(1)
            elif random.random() < 0.08:
                self.px += random.choice((-28, 28))

    def tick(self, human=None):
        self.t += 1
        self.bob = math.sin(self.t * 0.18) * 6
        if self.hop_cool:
            self.hop_cool -= 1
        if self.flash:
            self.flash -= 1
        for lane in self.lanes:
            for it in lane["items"]:
                it.tick()
        if human == "up":
            self.hop(1)
        elif human == "down":
            self.hop(-1)
        elif human == "left":
            self.px = max(40, self.px - 28)
        elif human == "right":
            self.px = min(W - 40, self.px + 28)
        else:
            self.autoplay()
        info = self.lanes[self.lane]
        kind = info["kind"]
        if kind == "logs":
            riding = None
            for it in info["items"]:
                if it.left - 6 < self.px < it.right + 6:
                    riding = it
                    break
            if riding:
                self.px += riding.speed
            else:
                self.drown()
        elif kind in ("boats", "fish"):
            for it in info["items"]:
                if it.left + 8 < self.px < it.right - 8:
                    self.drown()
                    break
        self.px = max(30, min(W - 30, self.px))
        splash = []
        for s in self.splash:
            s[0] += s[2]
            s[1] += s[3]
            s[4] -= 1
            if s[4] > 0:
                splash.append(s)
        self.splash = splash
        if self.t % 20 == 0:
            self.score += 1

    def drown(self):
        self.flash = 10
        self.lives = max(0, self.lives - 1)
        self.score = max(0, self.score - 15)
        y = self.lane_y(self.lane)
        for _ in range(18):
            ang = random.random() * 6.28
            spd = random.uniform(1.5, 7)
            self.splash.append([self.px, y, math.cos(ang) * spd, math.sin(ang) * spd, 16])
        self.spawn_player()


def draw(surf, g, fonts):
    font_lg, font_md, font_sm = fonts
    t = g.t
    for y in range(0, H, 8):
        k = y / H
        c = col_lerp((4, 10, 28), (8, 42, 58), k)
        pygame.draw.rect(surf, c, (0, y, W, 8))
    for i in range(10):
        yy = int((t * 4 + i * 210) % H)
        pygame.draw.line(surf, (18, 70, 90), (0, yy), (W, yy), 2)

    for i, lane in enumerate(g.lanes):
        y0 = PLAY_BOT - (i + 1) * LANE_H
        kind = lane["kind"]
        if kind == "bank":
            pygame.draw.rect(surf, (18, 70, 48), (0, y0, W, LANE_H))
            pygame.draw.rect(surf, (40, 160, 90), (0, y0, W, 6))
            for k in range(14):
                px = (k * 90 + (t * 2 if i else 0)) % (W + 40) - 20
                pygame.draw.circle(surf, (70, 210, 120), (int(px), int(y0 + LANE_H * 0.55)), 10)
        else:
            shade = (6, 28 + i * 3, 52) if kind != "logs" else (8, 36, 62)
            pygame.draw.rect(surf, shade, (0, y0, W, LANE_H))
            wave = 10 + int(6 * math.sin(t * 0.12 + i))
            pygame.draw.line(surf, (20, 80 + wave, 110), (0, y0), (W, y0), 2)
        cy = y0 + LANE_H // 2
        for it in lane["items"]:
            r = pygame.Rect(int(it.x), int(cy - LANE_H * 0.32), int(it.w), int(LANE_H * 0.64))
            glow = pygame.Surface((r.w + 24, r.h + 24), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*it.glow, 70), glow.get_rect(), border_radius=18)
            surf.blit(glow, (r.x - 12, r.y - 12))
            pygame.draw.rect(surf, it.color, r, border_radius=16)
            pygame.draw.rect(surf, (255, 255, 230), r, 2, border_radius=16)
            if it.kind == "boat":
                pygame.draw.polygon(surf, (255, 240, 200),
                                    [(r.centerx, r.top + 6), (r.centerx - 10, r.centery),
                                     (r.centerx + 10, r.centery)])
            elif it.kind == "fish":
                pygame.draw.circle(surf, (20, 20, 40), (r.centerx + 16, r.centery - 6), 5)

    py = g.lane_y(g.lane) + g.bob
    px = int(g.px)
    pygame.draw.circle(surf, (80, 255, 230), (px, int(py)), 28)
    pygame.draw.circle(surf, (20, 40, 50), (px, int(py)), 28, 3)
    pygame.draw.circle(surf, (255, 255, 255), (px - 8, int(py) - 6), 6)
    pygame.draw.circle(surf, (255, 255, 255), (px + 8, int(py) - 6), 6)
    pygame.draw.circle(surf, (10, 20, 30), (px - 7, int(py) - 6), 3)
    pygame.draw.circle(surf, (10, 20, 30), (px + 9, int(py) - 6), 3)
    pygame.draw.ellipse(surf, (30, 80, 90), (px - 10, int(py) + 6, 20, 8), 2)

    for s in g.splash:
        pygame.draw.circle(surf, (180, 255, 240), (int(s[0]), int(s[1])), max(2, s[4] // 3))
    if g.flash:
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((80, 255, 210, 36))
        surf.blit(veil, (0, 0))

    bar = pygame.Surface((W, TOP_HUD), pygame.SRCALPHA)
    bar.fill((2, 12, 22, 230))
    surf.blit(bar, (0, 0))
    surf.blit(font_lg.render(TITLE, True, (80, 255, 220)), (36, 18))
    surf.blit(font_sm.render("ElbowOS  ·  Python 3 tide-hopper  ·  autoplay reel", True, (160, 220, 230)), (40, 100))
    sc = font_md.render(f"TIDE  {g.score:05d}", True, (255, 200, 70))
    surf.blit(sc, (W - sc.get_width() - 36, 28))
    lv = font_sm.render("● " * max(1, g.lives), True, (255, 90, 130))
    surf.blit(lv, (W - lv.get_width() - 36, 88))

    foot = pygame.Surface((W, BOT_HUD), pygame.SRCALPHA)
    foot.fill((2, 12, 22, 230))
    surf.blit(foot, (0, H - BOT_HUD))
    tag = font_sm.render("x.com/ElbowOS", True, (80, 255, 220))
    surf.blit(tag, (W - tag.get_width() - 36, H - 68))
    hint = font_sm.render("ARROWS hop   ·   ride the teal logs", True, (130, 180, 190))
    surf.blit(hint, (36, H - 68))


def fonts():
    try:
        return (
            pygame.font.SysFont("dejavusans", 68, bold=True),
            pygame.font.SysFont("dejavusans", 40, bold=True),
            pygame.font.SysFont("dejavusans", 28),
        )
    except Exception:
        return pygame.font.Font(None, 76), pygame.font.Font(None, 46), pygame.font.Font(None, 32)


def record(out: Path = OUT) -> Path:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.font.init()
    surf = pygame.Surface((W, H))
    g = Game()
    fnt = fonts()
    tmp = out.with_suffix(".tmp.mp4")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "20", "-preset", "veryfast", "-movflags", "+faststart", str(tmp),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    assert proc.stdin is not None
    for _ in range(FRAMES):
        g.tick()
        draw(surf, g, fnt)
        proc.stdin.write(pygame.image.tostring(surf, "RGB"))
    proc.stdin.close()
    err = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
    rc = proc.wait()
    pygame.quit()
    if rc != 0 or not tmp.exists():
        raise RuntimeError(f"ffmpeg failed ({rc}): {err[-800:]}")
    tmp.replace(out)
    return out


def play():
    os.environ.pop("SDL_VIDEODRIVER", None)
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((W // 2, H // 2))
    pygame.display.set_caption("Riptide Hop — ElbowOS")
    canvas = pygame.Surface((W, H))
    clock = pygame.time.Clock()
    g = Game()
    fnt = fonts()
    running = True
    while running:
        human = None
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif ev.key == pygame.K_UP:
                    human = "up"
                elif ev.key == pygame.K_DOWN:
                    human = "down"
                elif ev.key == pygame.K_LEFT:
                    human = "left"
                elif ev.key == pygame.K_RIGHT:
                    human = "right"
                elif ev.key == pygame.K_r:
                    g = Game()
        g.tick(human)
        draw(canvas, g, fnt)
        pygame.transform.smoothscale(canvas, screen.get_size(), screen)
        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()


if __name__ == "__main__":
    if "--play" in sys.argv:
        play()
    else:
        path = record()
        print(path)
        print("bytes", path.stat().st_size)
        sys.exit(0)
