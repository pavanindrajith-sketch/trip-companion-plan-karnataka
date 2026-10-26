import json
import math
import random
import time
import tkinter as tk
from pathlib import Path


WIDTH = 1180
HEIGHT = 760
FIELD = (42, 118, 914, 710)
FIELD_INNER = (62, 138, 894, 690)

COLORS = {
    "void": "#0c1210",
    "panel": "#151e1a",
    "panel_light": "#202b25",
    "floor": "#1a241f",
    "floor_alt": "#1d2922",
    "grid": "#26332b",
    "line": "#35453a",
    "text": "#edf0df",
    "muted": "#89988a",
    "mint": "#a8df9d",
    "mint_dark": "#426e51",
    "coral": "#ef705d",
    "gold": "#e6c56d",
    "ice": "#83c8c3",
    "enemy": "#d96356",
    "enemy_dark": "#773c37",
    "white": "#ffffff",
}


class Nightshift:
    def __init__(self, root):
        self.root = root
        self.root.title("EMBER PROTOCOL | Blacksite 09")
        self.root.geometry("1180x760")
        self.root.minsize(900, 620)
        self.root.configure(bg=COLORS["void"])

        self.canvas = tk.Canvas(root, bg=COLORS["void"], highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self.on_resize)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Button-1>", self.on_click)
        root.bind("<KeyPress>", self.on_key_down)
        root.bind("<KeyRelease>", self.on_key_up)
        root.bind("<FocusOut>", self.on_focus_out)
        root.bind("<Escape>", self.on_escape)
        root.protocol("WM_DELETE_WINDOW", root.destroy)

        self.scale_x = 1.0
        self.scale_y = 1.0
        self.pointer = (0, 0)
        self.keys = set()
        self.buttons = []
        self.state = "menu"
        self.elapsed = 0.0
        self.last_frame = time.perf_counter()
        self.notice = "SYSTEM READY"
        self.notice_timer = 0.0
        self.save_path = Path(__file__).resolve().parent / "save.json"
        self.high_score = self.read_high_score()
        self.obstacles = [
            (180, 225, 290, 255),
            (357, 350, 390, 448),
            (520, 192, 610, 222),
            (685, 290, 775, 322),
            (200, 515, 292, 545),
            (535, 530, 570, 620),
            (750, 500, 835, 530),
        ]
        self.stars = [
            (random.randint(20, WIDTH - 20), random.randint(20, HEIGHT - 20), random.choice((1, 1, 2)))
            for _ in range(56)
        ]
        self.reset_run(start=False)
        self.root.after(16, self.frame)

    def read_high_score(self):
        try:
            return int(json.loads(self.save_path.read_text(encoding="utf-8")).get("high_score", 0))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return 0

    def save_high_score(self):
        try:
            self.save_path.write_text(json.dumps({"high_score": self.high_score}), encoding="utf-8")
        except OSError:
            pass

    def reset_run(self, start=True):
        self.player = {"x": 490.0, "y": 416.0, "hp": 100, "ammo": 24, "max_ammo": 24, "invulnerable": 0.0}
        self.score = 0
        self.kills = 0
        self.wave = 0
        self.enemies = []
        self.player_bullets = []
        self.enemy_bullets = []
        self.pickups = []
        self.particles = []
        self.popups = []
        self.reload_timer = 0.0
        self.fire_timer = 0.0
        self.wave_timer = 0.0
        self.notice = "SIGNAL ACQUIRED"
        self.notice_timer = 2.0
        self.state = "playing" if start else "menu"
        if start:
            self.start_next_wave()

    def start_next_wave(self):
        self.wave += 1
        count = min(3 + self.wave * 2, 19)
        sentries = 1 if self.wave >= 2 else 0
        for index in range(count):
            kind = "sentry" if sentries and index == count - 1 else "stalker"
            x, y = self.spawn_point()
            hp = 72 + self.wave * 7 if kind == "sentry" else 54 + self.wave * 8
            self.enemies.append({
                "x": x,
                "y": y,
                "hp": hp,
                "max_hp": hp,
                "kind": kind,
                "cooldown": random.uniform(0.35, 1.3),
                "touch_cooldown": 0.0,
                "phase": random.random() * math.tau,
            })
        self.notice = f"WAVE {self.wave:02d} // CONTACT INBOUND"
        self.notice_timer = 2.4

    def spawn_point(self):
        left, top, right, bottom = FIELD_INNER
        for _ in range(90):
            edge = random.randrange(4)
            if edge == 0:
                x, y = random.uniform(left + 24, right - 24), top + 24
            elif edge == 1:
                x, y = random.uniform(left + 24, right - 24), bottom - 24
            elif edge == 2:
                x, y = left + 24, random.uniform(top + 24, bottom - 24)
            else:
                x, y = right - 24, random.uniform(top + 24, bottom - 24)
            if math.hypot(x - self.player["x"], y - self.player["y"]) < 240:
                continue
            if not self.inside_cover(x, y, 22):
                return x, y
        return left + 30, top + 30

    def on_resize(self, event):
        self.scale_x = max(0.1, event.width / WIDTH)
        self.scale_y = max(0.1, event.height / HEIGHT)

    def on_mouse_move(self, event):
        self.pointer = (event.x / self.scale_x, event.y / self.scale_y)

    def on_click(self, event):
        self.pointer = (event.x / self.scale_x, event.y / self.scale_y)
        x, y = self.pointer
        for x1, y1, x2, y2, action in reversed(self.buttons):
            if x1 <= x <= x2 and y1 <= y <= y2:
                action()
                return
        if self.state == "playing":
            self.fire()

    def on_key_down(self, event):
        key = event.keysym.lower()
        self.keys.add(key)
        if key in ("return", "space") and self.state in ("menu", "game_over"):
            self.reset_run()
        elif key in ("return", "space") and self.state == "paused":
            self.state = "playing"
        elif key == "r" and self.state == "playing":
            self.reload()

    def on_key_up(self, event):
        self.keys.discard(event.keysym.lower())

    def on_focus_out(self, _event):
        self.keys.clear()

    def on_escape(self, _event):
        if self.state == "playing":
            self.state = "paused"
            self.keys.clear()
        elif self.state == "paused":
            self.state = "playing"

    def reload(self):
        if self.reload_timer > 0 or self.player["ammo"] >= self.player["max_ammo"]:
            return
        self.reload_timer = 0.9
        self.notice = "RELOADING MAGAZINE"
        self.notice_timer = 1.2

    def fire(self):
        if self.fire_timer > 0 or self.reload_timer > 0:
            return
        if self.player["ammo"] <= 0:
            self.notice = "MAGAZINE EMPTY // PRESS R"
            self.notice_timer = 1.4
            return
        px, py = self.player["x"], self.player["y"]
        dx, dy = self.pointer[0] - px, self.pointer[1] - py
        distance = math.hypot(dx, dy)
        if distance < 1:
            return
        dx, dy = dx / distance, dy / distance
        self.player["ammo"] -= 1
        self.fire_timer = 0.16
        self.player_bullets.append({
            "x": px + dx * 23,
            "y": py + dy * 23,
            "vx": dx * 760,
            "vy": dy * 760,
            "life": 1.15,
            "damage": 58,
        })
        self.burst(px + dx * 28, py + dy * 28, COLORS["gold"], 4, 120)

    def inside_cover(self, x, y, radius=0):
        for x1, y1, x2, y2 in self.obstacles:
            if x1 - radius <= x <= x2 + radius and y1 - radius <= y <= y2 + radius:
                return True
        return False

    def can_stand(self, x, y):
        left, top, right, bottom = FIELD_INNER
        if x < left + 18 or x > right - 18 or y < top + 18 or y > bottom - 18:
            return False
        return not self.inside_cover(x, y, 18)

    def burst(self, x, y, color, count=8, speed=180):
        for _ in range(count):
            angle = random.random() * math.tau
            velocity = random.uniform(speed * 0.25, speed)
            self.particles.append({
                "x": x,
                "y": y,
                "vx": math.cos(angle) * velocity,
                "vy": math.sin(angle) * velocity,
                "life": random.uniform(0.18, 0.46),
                "max_life": 0.46,
                "color": color,
                "size": random.uniform(1.5, 3.5),
            })

    def kill_enemy(self, enemy):
        if enemy not in self.enemies:
            return
        self.enemies.remove(enemy)
        points = 150 if enemy["kind"] == "sentry" else 100
        self.score += points
        self.kills += 1
        self.popups.append({"x": enemy["x"], "y": enemy["y"] - 16, "text": f"+{points}", "life": 0.8})
        self.burst(enemy["x"], enemy["y"], COLORS["coral"], 13, 230)
        roll = random.random()
        if roll < 0.16:
            kind = "med"
        elif roll < 0.47:
            kind = "ammo"
        else:
            kind = None
        if kind:
            self.pickups.append({"x": enemy["x"], "y": enemy["y"], "kind": kind, "phase": random.random() * math.tau})

    def hurt_player(self, amount):
        if self.player["invulnerable"] > 0 or self.state != "playing":
            return
        self.player["hp"] = max(0, self.player["hp"] - amount)
        self.player["invulnerable"] = 0.72
        self.notice = "ARMOR BREACH // MOVE"
        self.notice_timer = 1.1
        self.burst(self.player["x"], self.player["y"], COLORS["coral"], 8, 150)
        if self.player["hp"] <= 0:
            self.state = "game_over"
            self.high_score = max(self.high_score, self.score)
            self.save_high_score()

    def update(self, dt):
        self.elapsed += dt
        if self.notice_timer > 0:
            self.notice_timer = max(0, self.notice_timer - dt)
        self.fire_timer = max(0, self.fire_timer - dt)
        self.player["invulnerable"] = max(0, self.player["invulnerable"] - dt)
        if self.reload_timer > 0:
            self.reload_timer -= dt
            if self.reload_timer <= 0:
                self.player["ammo"] = self.player["max_ammo"]
                self.notice = "MAGAZINE LOCKED // GO"
                self.notice_timer = 1.4

        dx = int("d" in self.keys or "right" in self.keys) - int("a" in self.keys or "left" in self.keys)
        dy = int("s" in self.keys or "down" in self.keys) - int("w" in self.keys or "up" in self.keys)
        length = math.hypot(dx, dy)
        if length:
            speed = 300 if "shift_l" in self.keys or "shift_r" in self.keys else 215
            dx, dy = dx / length * speed * dt, dy / length * speed * dt
            nx, ny = self.player["x"] + dx, self.player["y"] + dy
            if self.can_stand(nx, self.player["y"]):
                self.player["x"] = nx
            if self.can_stand(self.player["x"], ny):
                self.player["y"] = ny

        px, py = self.player["x"], self.player["y"]
        for enemy in list(self.enemies):
            ex, ey = enemy["x"], enemy["y"]
            vx, vy = px - ex, py - ey
            distance = max(1.0, math.hypot(vx, vy))
            nx, ny = vx / distance, vy / distance
            enemy["cooldown"] = max(0, enemy["cooldown"] - dt)
            enemy["touch_cooldown"] = max(0, enemy["touch_cooldown"] - dt)
            if enemy["kind"] == "sentry":
                if distance > 255:
                    self.move_enemy(enemy, nx * 86 * dt, ny * 86 * dt)
                elif distance < 170:
                    self.move_enemy(enemy, -nx * 72 * dt, -ny * 72 * dt)
                if distance < 500 and enemy["cooldown"] <= 0:
                    enemy["cooldown"] = random.uniform(1.0, 1.5)
                    self.enemy_bullets.append({
                        "x": ex,
                        "y": ey,
                        "vx": nx * 320,
                        "vy": ny * 320,
                        "life": 2.0,
                        "damage": 11,
                    })
            else:
                speed = min(142, 82 + self.wave * 4)
                if distance > 24:
                    self.move_enemy(enemy, nx * speed * dt, ny * speed * dt)
                if distance < 31 and enemy["touch_cooldown"] <= 0:
                    enemy["touch_cooldown"] = 0.8
                    self.hurt_player(9)

        self.update_bullets(self.player_bullets, dt, True)
        self.update_bullets(self.enemy_bullets, dt, False)

        for pickup in list(self.pickups):
            pickup["phase"] += dt * 3
            if math.hypot(pickup["x"] - px, pickup["y"] - py) < 28:
                if pickup["kind"] == "med" and self.player["hp"] < 100:
                    self.player["hp"] = min(100, self.player["hp"] + 28)
                    self.notice = "ARMOR PATCH APPLIED"
                elif pickup["kind"] == "ammo" and self.player["ammo"] < self.player["max_ammo"]:
                    self.player["ammo"] = min(self.player["max_ammo"], self.player["ammo"] + 10)
                    self.notice = "MAGAZINE +10"
                else:
                    continue
                self.notice_timer = 1.2
                self.pickups.remove(pickup)
                self.score += 25

        for particle in list(self.particles):
            particle["life"] -= dt
            particle["x"] += particle["vx"] * dt
            particle["y"] += particle["vy"] * dt
            particle["vx"] *= 0.93
            particle["vy"] *= 0.93
            if particle["life"] <= 0:
                self.particles.remove(particle)
        for popup in list(self.popups):
            popup["life"] -= dt
            popup["y"] -= 26 * dt
            if popup["life"] <= 0:
                self.popups.remove(popup)

        if not self.enemies:
            if self.wave_timer <= 0:
                self.wave_timer = 1.35
            else:
                self.wave_timer -= dt
                if self.wave_timer <= 0 and self.state == "playing":
                    self.start_next_wave()

    def move_enemy(self, enemy, dx, dy):
        nx, ny = enemy["x"] + dx, enemy["y"] + dy
        if self.can_stand(nx, enemy["y"]):
            enemy["x"] = nx
        if self.can_stand(enemy["x"], ny):
            enemy["y"] = ny

    def update_bullets(self, bullets, dt, player_fired):
        for bullet in list(bullets):
            bullet["life"] -= dt
            old_x, old_y = bullet["x"], bullet["y"]
            bullet["x"] += bullet["vx"] * dt
            bullet["y"] += bullet["vy"] * dt
            remove = bullet["life"] <= 0 or self.inside_cover(bullet["x"], bullet["y"], 2)
            if not remove and player_fired:
                for enemy in list(self.enemies):
                    if math.hypot(enemy["x"] - bullet["x"], enemy["y"] - bullet["y"]) < 20:
                        enemy["hp"] -= bullet["damage"]
                        self.burst(bullet["x"], bullet["y"], COLORS["gold"], 4, 100)
                        if enemy["hp"] <= 0:
                            self.kill_enemy(enemy)
                        remove = True
                        break
            elif not remove:
                if math.hypot(self.player["x"] - bullet["x"], self.player["y"] - bullet["y"]) < 18:
                    self.hurt_player(bullet["damage"])
                    remove = True
            if remove:
                if bullet in bullets:
                    bullets.remove(bullet)
            else:
                bullet["trail"] = (old_x, old_y)

    def frame(self):
        now = time.perf_counter()
        dt = min(0.045, now - self.last_frame)
        self.last_frame = now
        if self.state == "playing":
            self.update(dt)
        else:
            self.elapsed += dt
        self.draw()
        self.root.after(16, self.frame)

    def px(self, x):
        return x * self.scale_x

    def py(self, y):
        return y * self.scale_y

    def rect(self, x1, y1, x2, y2, fill, outline="", width=1):
        self.canvas.create_rectangle(
            self.px(x1), self.py(y1), self.px(x2), self.py(y2),
            fill=fill, outline=outline, width=max(1, round(width * (self.scale_x + self.scale_y) / 2)),
        )

    def line(self, points, fill, width=1):
        coords = []
        for x, y in points:
            coords.extend((self.px(x), self.py(y)))
        self.canvas.create_line(*coords, fill=fill, width=max(1, round(width * (self.scale_x + self.scale_y) / 2)), capstyle="round")

    def oval(self, x1, y1, x2, y2, fill, outline="", width=1):
        self.canvas.create_oval(
            self.px(x1), self.py(y1), self.px(x2), self.py(y2),
            fill=fill, outline=outline, width=max(1, round(width * (self.scale_x + self.scale_y) / 2)),
        )

    def polygon(self, points, fill, outline="", width=1):
        coords = []
        for x, y in points:
            coords.extend((self.px(x), self.py(y)))
        self.canvas.create_polygon(
            *coords, fill=fill, outline=outline, width=max(1, round(width * (self.scale_x + self.scale_y) / 2)),
        )

    def text(self, x, y, value, size=12, color=None, bold=False, anchor="nw", family="Segoe UI"):
        font_size = max(7, round(size * (self.scale_x + self.scale_y) / 2))
        self.canvas.create_text(
            self.px(x), self.py(y), text=value, fill=color or COLORS["text"], anchor=anchor,
            font=(family, font_size, "bold" if bold else "normal"),
        )

    def button(self, box, label, action, accent=False):
        x1, y1, x2, y2 = box
        hovered = x1 <= self.pointer[0] <= x2 and y1 <= self.pointer[1] <= y2
        fill = COLORS["mint"] if accent else (COLORS["panel_light"] if hovered else COLORS["panel"])
        text_color = COLORS["void"] if accent else COLORS["text"]
        outline = COLORS["mint"] if hovered and not accent else COLORS["line"]
        self.rect(x1, y1, x2, y2, fill, outline, 1)
        self.text((x1 + x2) / 2, (y1 + y2) / 2, label, 13, text_color, True, "center", "Consolas")
        self.buttons.append((*box, action))

    def draw(self):
        self.canvas.delete("all")
        self.buttons = []
        self.rect(0, 0, WIDTH, HEIGHT, COLORS["void"])
        self.draw_backdrop()
        if self.state == "menu":
            self.draw_menu()
        else:
            self.draw_game()
            if self.state == "paused":
                self.draw_overlay("PAUSED", "COMBAT FROZEN", "Resume when ready.", "RESUME RUN", lambda: setattr(self, "state", "playing"))
            elif self.state == "game_over":
                self.draw_overlay("RUN ENDED", "OPERATOR DOWN", f"SCORE  {self.score:06d}    /    BEST  {self.high_score:06d}", "DEPLOY AGAIN", self.reset_run)

    def draw_backdrop(self):
        for x, y, size in self.stars:
            pulse = 0.35 + 0.25 * math.sin(self.elapsed * 1.2 + x * 0.03)
            color = COLORS["line"] if pulse < 0.45 else "#516256"
            self.oval(x, y, x + size, y + size, color)
        self.rect(0, 0, WIDTH, 88, "#101713")
        self.line([(0, 87), (WIDTH, 87)], COLORS["line"])
        self.text(42, 30, "FIELD UNIT   /   09", 12, COLORS["muted"], True, family="Consolas")
        self.text(42, 48, "EMBER PROTOCOL", 18, COLORS["text"], True)
        self.oval(1050, 37, 1058, 45, COLORS["mint"])
        self.text(1070, 30, "LOCAL SYSTEM", 10, COLORS["muted"], True, family="Consolas")
        self.text(1070, 46, "SECURE LINK", 9, COLORS["mint"], True, family="Consolas")

    def draw_menu(self):
        self.text(54, 120, "BLACKSITE 09     //     TACTICAL SURVIVAL", 10, COLORS["mint"], True, family="Consolas")
        self.text(54, 171, "EMBER", 70, COLORS["text"], True, family="Segoe UI")
        self.text(54, 238, "PROTOCOL", 47, COLORS["mint"], True, family="Segoe UI")
        self.rect(57, 310, 360, 314, COLORS["coral"])
        self.text(56, 338, "THE LAST OUTPOST IS DARK.", 13, COLORS["gold"], True, family="Consolas")
        self.text(56, 372, "Hold the breach. Keep moving.", 17, COLORS["text"], True)
        self.text(56, 401, "Clear each wave before the signal fades.", 13, COLORS["muted"])
        self.text(56, 440, f"PERSONAL BEST     {self.high_score:06d}", 11, COLORS["ice"], True, family="Consolas")

        self.draw_preview_arena()
        self.button((56, 610, 334, 662), "BEGIN OPERATION   [ENTER]", self.reset_run, True)
        self.text(56, 685, "WASD MOVE     SHIFT SPRINT     MOUSE AIM + FIRE", 9, COLORS["muted"], True, family="Consolas")
        self.text(56, 704, "R RELOAD     ESC PAUSE", 9, COLORS["muted"], True, family="Consolas")
        self.text(1120, 720, "A SINGLE-PLAYER FIELD TEST", 9, COLORS["muted"], True, "e", "Consolas")

    def draw_preview_arena(self):
        x1, y1, x2, y2 = 625, 132, 1124, 574
        self.rect(x1, y1, x2, y2, COLORS["floor"], COLORS["line"], 2)
        for x in range(x1 + 24, x2, 36):
            self.line([(x, y1 + 1), (x, y2 - 1)], COLORS["grid"])
        for y in range(y1 + 24, y2, 36):
            self.line([(x1 + 1, y), (x2 - 1, y)], COLORS["grid"])
        self.text(647, 149, "LIVE FEED   /   SECTOR 09", 9, COLORS["muted"], True, family="Consolas")
        for ox, oy, ow, oh in ((725, 255, 76, 20), (875, 365, 24, 82), (1010, 244, 66, 20), (827, 478, 78, 18)):
            self.draw_cover(ox, oy, ow, oh)
        self.draw_operator(835, 355, 1000, 260)
        self.draw_enemy(702, 420, 835, 355, "stalker", 0.4)
        self.draw_enemy(1050, 455, 835, 355, "sentry", 0.7)
        self.line([(836, 355), (917, 307)], COLORS["gold"], 2)
        self.oval(911, 301, 923, 313, "", COLORS["gold"], 1)
        self.rect(646, 530, 1102, 552, "#111815", COLORS["line"])
        self.text(660, 536, "THREAT LEVEL   /   ELEVATED", 9, COLORS["coral"], True, family="Consolas")

    def draw_cover(self, x, y, width, height):
        self.rect(x + 5, y + 7, x + width + 5, y + height + 7, "#101713")
        self.rect(x, y, x + width, y + height, "#35443a", "#5a6a59", 1)
        self.line([(x + 5, y + 4), (x + width - 5, y + 4)], "#819078", 2)
        self.rect(x + 8, y + height - 6, x + width - 8, y + height - 4, "#212d25")
        for bx in (x + 8, x + width - 9):
            self.oval(bx - 2, y + height / 2 - 2, bx + 2, y + height / 2 + 2, COLORS["gold"])

    def draw_game(self):
        self.draw_hud()
        self.draw_arena()
        self.draw_sidebar()
        self.draw_footer()
        if self.notice_timer > 0:
            self.rect(365, 96, 610, 116, "#151e1a")
            self.text(487, 106, self.notice, 9, COLORS["gold"], True, "center", "Consolas")

    def draw_hud(self):
        self.text(42, 100, "OPERATION: EMBER PROTOCOL", 10, COLORS["muted"], True, family="Consolas")
        self.text(42, 123, f"WAVE  {self.wave:02d}", 22, COLORS["text"], True)
        self.text(220, 109, "BREACH STATUS", 8, COLORS["muted"], True, family="Consolas")
        for index in range(5):
            color = COLORS["coral"] if index < min(5, len(self.enemies)) else COLORS["line"]
            self.rect(220 + index * 18, 128, 232 + index * 18, 136, color)
        self.text(354, 109, "SCORE", 8, COLORS["muted"], True, family="Consolas")
        self.text(354, 124, f"{self.score:06d}", 19, COLORS["gold"], True, family="Consolas")
        self.text(492, 109, "BEST", 8, COLORS["muted"], True, family="Consolas")
        self.text(492, 124, f"{self.high_score:06d}", 19, COLORS["ice"], True, family="Consolas")
        self.button((835, 101, 907, 139), "ESC  II", lambda: self.on_escape(None))

    def draw_arena(self):
        x1, y1, x2, y2 = FIELD
        self.rect(x1, y1, x2, y2, COLORS["floor"], COLORS["line"], 2)
        left, top, right, bottom = FIELD_INNER
        for row, y in enumerate(range(top, bottom, 42)):
            for col, x in enumerate(range(left, right, 42)):
                if (row + col) % 2 == 0:
                    self.rect(x, y, min(x + 41, right), min(y + 41, bottom), COLORS["floor_alt"])
        for x in range(left, right, 42):
            self.line([(x, top), (x, bottom)], COLORS["grid"])
        for y in range(top, bottom, 42):
            self.line([(left, y), (right, y)], COLORS["grid"])
        self.rect(left, top, right, bottom, "", "#61705f", 1)

        self.text(left + 8, top + 8, "NORTH SERVICE BAY", 8, "#637568", True, family="Consolas")
        self.text(right - 9, top + 8, "09:41:26", 8, "#637568", True, "ne", "Consolas")
        self.draw_door(left + 286, top, left + 356, top + 8)
        self.draw_door(right - 7, top + 250, right, top + 318)
        self.draw_door(left + 495, bottom - 8, left + 565, bottom)
        for obstacle in self.obstacles:
            self.draw_cover(obstacle[0], obstacle[1], obstacle[2] - obstacle[0], obstacle[3] - obstacle[1])

        for pickup in self.pickups:
            bob = math.sin(self.elapsed * 4 + pickup["phase"]) * 3
            color = COLORS["mint"] if pickup["kind"] == "med" else COLORS["gold"]
            x, y = pickup["x"], pickup["y"] + bob
            self.oval(x - 13, y - 13, x + 13, y + 13, "#111815", color, 2)
            if pickup["kind"] == "med":
                self.rect(x - 2, y - 7, x + 2, y + 7, color)
                self.rect(x - 7, y - 2, x + 7, y + 2, color)
            else:
                self.rect(x - 6, y - 6, x + 6, y + 6, color)
                self.line([(x - 3, y - 4), (x - 3, y + 4)], COLORS["void"], 1)
                self.line([(x + 2, y - 4), (x + 2, y + 4)], COLORS["void"], 1)

        for enemy in self.enemies:
            self.draw_enemy(enemy["x"], enemy["y"], self.player["x"], self.player["y"], enemy["kind"], enemy["hp"] / enemy["max_hp"])
        for bullet in self.player_bullets:
            trail = bullet.get("trail", (bullet["x"] - bullet["vx"] * 0.018, bullet["y"] - bullet["vy"] * 0.018))
            self.line([(trail[0], trail[1]), (bullet["x"], bullet["y"])], COLORS["gold"], 3)
            self.oval(bullet["x"] - 3, bullet["y"] - 3, bullet["x"] + 3, bullet["y"] + 3, COLORS["text"])
        for bullet in self.enemy_bullets:
            trail = bullet.get("trail", (bullet["x"] - bullet["vx"] * 0.02, bullet["y"] - bullet["vy"] * 0.02))
            self.line([(trail[0], trail[1]), (bullet["x"], bullet["y"])], COLORS["coral"], 2)
            self.oval(bullet["x"] - 3, bullet["y"] - 3, bullet["x"] + 3, bullet["y"] + 3, COLORS["coral"])
        for particle in self.particles:
            radius = max(1, particle["size"] * max(0.2, particle["life"] / particle["max_life"]))
            self.oval(particle["x"] - radius, particle["y"] - radius, particle["x"] + radius, particle["y"] + radius, particle["color"])
        for popup in self.popups:
            self.text(popup["x"], popup["y"], popup["text"], 10, COLORS["gold"], True, "center", "Consolas")

        if not (self.player["invulnerable"] > 0 and int(self.elapsed * 18) % 2):
            self.draw_operator(self.player["x"], self.player["y"], self.pointer[0], self.pointer[1])
        self.draw_crosshair(self.pointer[0], self.pointer[1])
        if not self.enemies and self.wave_timer > 0:
            self.rect(301, 355, 655, 425, "#101713", COLORS["gold"])
            self.text(478, 374, "SECTOR CLEAR", 14, COLORS["gold"], True, "center", "Consolas")
            self.text(478, 400, "NEXT WAVE INBOUND", 10, COLORS["muted"], True, "center", "Consolas")

    def draw_door(self, x1, y1, x2, y2):
        self.rect(x1, y1, x2, y2, "#111815", COLORS["gold"], 1)
        if x2 - x1 > y2 - y1:
            self.line([((x1 + x2) / 2, y1 + 2), ((x1 + x2) / 2, y2 - 2)], COLORS["line"])
        else:
            self.line([(x1 + 2, (y1 + y2) / 2), (x2 - 2, (y1 + y2) / 2)], COLORS["line"])

    def draw_operator(self, x, y, aim_x, aim_y):
        angle = math.atan2(aim_y - y, aim_x - x)
        self.oval(x - 18, y + 9, x + 19, y + 19, "#111713")
        self.oval(x - 17, y - 17, x + 17, y + 17, "#314c3c", COLORS["mint"], 2)
        self.polygon(self.rotate_points(x, y, [(-11, -11), (6, -13), (13, -4), (10, 11), (-9, 12), (-14, 3)], angle), "#a7d89b", "#e1f0c8", 1)
        self.polygon(self.rotate_points(x, y, [(-6, -7), (8, -8), (10, 6), (-7, 7)], angle), "#4b6850")
        head_x, head_y = x + math.cos(angle) * 8, y + math.sin(angle) * 8
        self.oval(head_x - 6, head_y - 6, head_x + 6, head_y + 6, "#f0d9b2", "#7f7b5e")
        self.line([(x + math.cos(angle) * 8, y + math.sin(angle) * 8), (x + math.cos(angle) * 30, y + math.sin(angle) * 30)], "#dbe6c4", 5)
        self.line([(x + math.cos(angle) * 21, y + math.sin(angle) * 21), (x + math.cos(angle) * 33, y + math.sin(angle) * 33)], COLORS["gold"], 2)
        self.oval(x - 3, y - 3, x + 3, y + 3, COLORS["ice"])

    def rotate_points(self, x, y, points, angle):
        c, s = math.cos(angle), math.sin(angle)
        return [(x + px * c - py * s, y + px * s + py * c) for px, py in points]

    def draw_enemy(self, x, y, target_x, target_y, kind, health_fraction):
        angle = math.atan2(target_y - y, target_x - x)
        self.oval(x - 18, y + 9, x + 19, y + 19, "#101512")
        color = COLORS["enemy"] if kind == "stalker" else COLORS["gold"]
        outline = "#ffb09a" if kind == "stalker" else "#fff0ac"
        self.oval(x - 16, y - 16, x + 16, y + 16, COLORS["enemy_dark"], color, 2)
        self.polygon(self.rotate_points(x, y, [(-10, -10), (7, -12), (13, -2), (10, 11), (-8, 12), (-13, 2)], angle), color, outline, 1)
        self.oval(x - 6, y - 9, x + 7, y + 2, "#312725")
        self.oval(x + math.cos(angle) * 4 - 2, y + math.sin(angle) * 4 - 2, x + math.cos(angle) * 4 + 2, y + math.sin(angle) * 4 + 2, COLORS["text"])
        if kind == "sentry":
            self.line([(x + math.cos(angle) * 8, y + math.sin(angle) * 8), (x + math.cos(angle) * 27, y + math.sin(angle) * 27)], COLORS["gold"], 4)
            self.rect(x - 12, y - 24, x + 12, y - 21, "#101512")
            self.rect(x - 12, y - 24, x - 12 + 24 * max(0, health_fraction), y - 21, COLORS["coral"])

    def draw_crosshair(self, x, y):
        color = COLORS["text"]
        self.oval(x - 10, y - 10, x + 10, y + 10, "", COLORS["gold"], 1)
        self.line([(x - 17, y), (x - 6, y)], color, 1)
        self.line([(x + 6, y), (x + 17, y)], color, 1)
        self.line([(x, y - 17), (x, y - 6)], color, 1)
        self.line([(x, y + 6), (x, y + 17)], color, 1)
        self.oval(x - 1, y - 1, x + 1, y + 1, COLORS["gold"])

    def draw_sidebar(self):
        self.rect(930, 118, 1138, 710, COLORS["panel"], COLORS["line"])
        self.text(950, 138, "OPERATOR", 9, COLORS["muted"], True, family="Consolas")
        self.text(950, 158, "WRAITH-09", 15, COLORS["text"], True)
        self.text(950, 180, "FIELD RANK   //   ROOKIE", 8, COLORS["mint"], True, family="Consolas")
        self.line([(950, 204), (1118, 204)], COLORS["line"])

        self.text(950, 220, "VITALS", 9, COLORS["muted"], True, family="Consolas")
        self.text(1117, 220, f"{self.player['hp']:03d}%", 14, COLORS["text"], True, "ne", "Consolas")
        for index in range(10):
            color = COLORS["coral"] if index * 10 < self.player["hp"] else "#344139"
            self.rect(950 + index * 17, 246, 963 + index * 17, 254, color)
        self.text(950, 272, "MAGAZINE", 9, COLORS["muted"], True, family="Consolas")
        self.text(1117, 269, f"{self.player['ammo']:02d} / 24", 16, COLORS["gold"], True, "ne", "Consolas")
        for index in range(24):
            color = COLORS["gold"] if index < self.player["ammo"] else "#344139"
            self.rect(950 + index * 7, 297, 954 + index * 7, 306, color)
        if self.reload_timer > 0:
            self.text(950, 314, "RELOADING...", 8, COLORS["gold"], True, family="Consolas")

        self.line([(950, 337), (1118, 337)], COLORS["line"])
        self.text(950, 352, "HOSTILE RADAR", 9, COLORS["muted"], True, family="Consolas")
        cx, cy, radius = 1034, 444, 63
        self.oval(cx - radius, cy - radius, cx + radius, cy + radius, "#101713", "#526454")
        self.oval(cx - 39, cy - 39, cx + 39, cy + 39, "", "#35443a")
        self.oval(cx - 15, cy - 15, cx + 15, cy + 15, "", "#35443a")
        self.line([(cx - radius, cy), (cx + radius, cy)], "#35443a")
        self.line([(cx, cy - radius), (cx, cy + radius)], "#35443a")
        for enemy in self.enemies:
            dx = (enemy["x"] - self.player["x"]) / 5.1
            dy = (enemy["y"] - self.player["y"]) / 5.1
            distance = math.hypot(dx, dy)
            if distance > radius - 6:
                dx, dy = dx / distance * (radius - 6), dy / distance * (radius - 6)
            px, py = cx + dx, cy + dy
            self.oval(px - 3, py - 3, px + 3, py + 3, COLORS["gold"] if enemy["kind"] == "sentry" else COLORS["coral"])
        self.oval(cx - 4, cy - 4, cx + 4, cy + 4, COLORS["mint"])

        self.line([(950, 529), (1118, 529)], COLORS["line"])
        self.text(950, 546, "MISSION LOG", 9, COLORS["muted"], True, family="Consolas")
        status = self.notice if self.notice_timer > 0 else ("THREAT CONTAINED" if not self.enemies else "CONTACTS ADVANCING")
        status_color = COLORS["gold"] if "RELOAD" in status or "MAGAZINE" in status else (COLORS["mint"] if "CONTAINED" in status else COLORS["coral"])
        self.text(950, 571, status[:24], 10, status_color, True, family="Consolas")
        self.text(950, 610, "HOSTILES", 8, COLORS["muted"], True, family="Consolas")
        self.text(1118, 607, f"{len(self.enemies):02d}", 15, COLORS["text"], True, "ne", "Consolas")
        self.text(950, 642, "NEUTRALIZED", 8, COLORS["muted"], True, family="Consolas")
        self.text(1118, 639, f"{self.kills:03d}", 15, COLORS["text"], True, "ne", "Consolas")

    def draw_footer(self):
        self.line([(42, 727), (1138, 727)], COLORS["line"])
        self.text(42, 738, "BLACKSITE 09   /   NIGHT OPERATIONS", 8, COLORS["muted"], True, family="Consolas")
        self.text(1138, 738, "ESC  PAUSE", 8, COLORS["muted"], True, "ne", "Consolas")

    def draw_overlay(self, title, eyebrow, detail, button_label, action):
        self.rect(0, 88, WIDTH, HEIGHT, "#07100c")
        self.draw_arena()
        self.draw_sidebar()
        self.rect(296, 266, 686, 508, "#121b16", "#667861", 1)
        self.rect(296, 266, 686, 271, COLORS["mint"] if title == "PAUSED" else COLORS["coral"])
        self.text(491, 298, eyebrow, 9, COLORS["gold"] if title == "RUN ENDED" else COLORS["mint"], True, "center", "Consolas")
        self.text(491, 329, title, 36, COLORS["text"], True, "center")
        self.text(491, 390, detail, 11, COLORS["muted"], False, "center", "Consolas")
        self.button((365, 435, 617, 481), button_label, action, True)
        self.text(491, 493, "PRESS ENTER TO CONTINUE" if title == "PAUSED" else "PRESS ENTER TO REDEPLOY", 8, COLORS["muted"], True, "center", "Consolas")


def main():
    root = tk.Tk()
    Nightshift(root)
    root.mainloop()


if __name__ == "__main__":
    main()