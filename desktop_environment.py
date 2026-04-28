
import datetime
import hashlib
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import pygame
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog


ENCRYPTION_MAGIC = b"PYTHOSENC1\n"
WINDOW_RADIUS = 18
BUTTON_RADIUS = 14
TASKBAR_RADIUS = 18


def draw_acrylic_rect(screen, rect, fill_rgba, border_rgba=(255, 255, 255, 60), radius=16, shadow_alpha=40, shadow_offset=(0, 6)):
    shadow_rect = rect.move(*shadow_offset)
    shadow_surface = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
    pygame.draw.rect(shadow_surface, (0, 0, 0, shadow_alpha), shadow_surface.get_rect(), border_radius=radius)
    screen.blit(shadow_surface, shadow_rect.topleft)

    panel_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(panel_surface, fill_rgba, panel_surface.get_rect(), border_radius=radius)
    pygame.draw.rect(panel_surface, border_rgba, panel_surface.get_rect(), 1, border_radius=radius)
    screen.blit(panel_surface, rect.topleft)


def fit_text_to_width(text, font, max_width, ellipsis="..."):
    """Return text shortened to fit inside max_width pixels."""
    text = str(text)
    if max_width <= 0:
        return ""
    if font.size(text)[0] <= max_width:
        return text
    while ellipsis and font.size(ellipsis)[0] > max_width:
        ellipsis = ellipsis[:-1]
    if not ellipsis:
        return ""
    low, high = 0, len(text)
    while low < high:
        mid = (low + high + 1) // 2
        candidate = text[:mid].rstrip() + ellipsis
        if font.size(candidate)[0] <= max_width:
            low = mid
        else:
            high = mid - 1
    return text[:low].rstrip() + ellipsis


def wrap_text_to_width(text, font, max_width, max_lines=None):
    """Wrap text to a list of lines that fit inside max_width pixels."""
    text = str(text)
    if max_width <= 0:
        return [""]
    words = text.split() or [""]
    lines = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if font.size(candidate)[0] <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        if max_lines and len(lines) >= max_lines:
            lines[-1] = fit_text_to_width(lines[-1], font, max_width)
            return lines
        current = word if font.size(word)[0] <= max_width else fit_text_to_width(word, font, max_width)
    if current:
        lines.append(current)
    if max_lines and len(lines) > max_lines:
        trimmed = lines[:max_lines]
        trimmed[-1] = fit_text_to_width(trimmed[-1] + " ...", font, max_width)
        return trimmed
    return lines


def draw_fit_text(screen, text, font, color, pos, max_width):
    fitted = fit_text_to_width(text, font, max_width)
    surface = font.render(fitted, True, color)
    screen.blit(surface, pos)
    return surface


def draw_wrapped_text(screen, text, font, color, rect, line_spacing=2, max_lines=None):
    lines = wrap_text_to_width(text, font, rect.width, max_lines=max_lines)
    y = rect.y
    line_height = font.get_height() + line_spacing
    for line in lines:
        if y + font.get_height() > rect.bottom:
            break
        surface = font.render(line, True, color)
        screen.blit(surface, (rect.x, y))
        y += line_height
    return y


class Window:
    def __init__(self, x, y, width, height, title, app_id):
        self.rect = pygame.Rect(x, y, width, height)
        self.title = title
        self.app_id = app_id
        self.dragging = False
        self.drag_offset = (0, 0)
        self.minimized = False
        self.maximized = False
        self.original_rect = self.rect.copy()
        self.title_bar_height = 42
        self.snap_preview = None

    def get_title_bar_rect(self):
        return pygame.Rect(self.rect.x + 6, self.rect.y + 6, self.rect.width - 12, self.title_bar_height)

    def get_close_button_rect(self):
        return pygame.Rect(self.rect.right - 42, self.rect.y + 12, 24, 24)

    def get_minimize_button_rect(self):
        return pygame.Rect(self.rect.right - 98, self.rect.y + 12, 24, 24)

    def get_maximize_button_rect(self):
        return pygame.Rect(self.rect.right - 70, self.rect.y + 12, 24, 24)

    def get_content_rect(self):
        top = self.rect.y + self.title_bar_height + 12
        return pygame.Rect(self.rect.x + 12, top, self.rect.width - 24, self.rect.height - (top - self.rect.y) - 12)

    def get_work_area(self, screen_width, screen_height, taskbar_height, taskbar_position):
        if taskbar_position == "top":
            return pygame.Rect(0, taskbar_height, screen_width, screen_height - taskbar_height)
        return pygame.Rect(0, 0, screen_width, screen_height - taskbar_height)

    def get_snap_target(self, pos, screen_width, screen_height, taskbar_height, taskbar_position):
        work_area = self.get_work_area(screen_width, screen_height, taskbar_height, taskbar_position)
        edge = 26
        if pos[1] <= work_area.y + edge:
            return work_area.copy()
        if pos[0] <= work_area.x + edge:
            return pygame.Rect(work_area.x, work_area.y, work_area.width // 2, work_area.height)
        if pos[0] >= work_area.right - edge:
            return pygame.Rect(work_area.centerx, work_area.y, work_area.width - (work_area.width // 2), work_area.height)
        return None

    def apply_snap(self, target_rect):
        if not target_rect:
            self.snap_preview = None
            return None
        self.original_rect = self.rect.copy()
        self.rect = target_rect.copy()
        self.maximized = target_rect.width >= self.original_rect.width and target_rect.height >= self.original_rect.height and target_rect.x == 0
        self.dragging = False
        self.snap_preview = None
        return "snap"

    def handle_event(self, event, screen_width, screen_height, taskbar_height, taskbar_position):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.get_close_button_rect().collidepoint(event.pos):
                return "close"
            if self.get_minimize_button_rect().collidepoint(event.pos):
                self.minimized = not self.minimized
                self.dragging = False
                return "minimize"
            if self.get_maximize_button_rect().collidepoint(event.pos):
                work_area = self.get_work_area(screen_width, screen_height, taskbar_height, taskbar_position)
                if self.maximized:
                    self.rect = self.original_rect.copy()
                    self.maximized = False
                else:
                    self.original_rect = self.rect.copy()
                    self.rect = work_area
                    self.maximized = True
                self.dragging = False
                return "maximize"
            if self.get_title_bar_rect().collidepoint(event.pos):
                self.dragging = True
                self.drag_offset = (event.pos[0] - self.rect.x, event.pos[1] - self.rect.y)
                self.snap_preview = None
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging:
                self.dragging = False
                snap_target = self.get_snap_target(event.pos, screen_width, screen_height, taskbar_height, taskbar_position)
                if snap_target:
                    return self.apply_snap(snap_target)
            self.snap_preview = None
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            if self.maximized:
                self.maximized = False
                self.rect = self.original_rect.copy()
                self.drag_offset = (self.rect.width // 2, 14)
            work_area = self.get_work_area(screen_width, screen_height, taskbar_height, taskbar_position)
            self.rect.x = max(work_area.x, min(event.pos[0] - self.drag_offset[0], work_area.right - self.rect.width))
            self.rect.y = max(work_area.y, min(event.pos[1] - self.drag_offset[1], work_area.bottom - self.rect.height))
            self.snap_preview = self.get_snap_target(event.pos, screen_width, screen_height, taskbar_height, taskbar_position)
        return None

    def draw_shell(self, screen, font):
        if self.snap_preview:
            preview_surface = pygame.Surface((self.snap_preview.width, self.snap_preview.height), pygame.SRCALPHA)
            pygame.draw.rect(preview_surface, (138, 188, 255, 55), preview_surface.get_rect(), border_radius=WINDOW_RADIUS)
            pygame.draw.rect(preview_surface, (185, 216, 255, 135), preview_surface.get_rect(), 2, border_radius=WINDOW_RADIUS)
            screen.blit(preview_surface, self.snap_preview.topleft)

        draw_acrylic_rect(screen, self.rect, (248, 250, 255, 228), (255, 255, 255, 130), WINDOW_RADIUS)
        title_bar = self.get_title_bar_rect()
        draw_acrylic_rect(screen, title_bar, (28, 49, 85, 212), (255, 255, 255, 40), WINDOW_RADIUS - 2, shadow_alpha=0, shadow_offset=(0, 0))
        divider_y = title_bar.bottom
        pygame.draw.line(screen, (225, 232, 248), (self.rect.x + 12, divider_y), (self.rect.right - 12, divider_y), 1)

        close_rect = self.get_close_button_rect()
        minimize_rect = self.get_minimize_button_rect()
        maximize_rect = self.get_maximize_button_rect()
        title_max_width = max(40, minimize_rect.x - (title_bar.x + 14) - 10)
        draw_fit_text(screen, self.title, font, (255, 255, 255), (title_bar.x + 14, title_bar.y + 9), title_max_width)

        for rect, fill in [(minimize_rect, (235, 240, 248)), (maximize_rect, (235, 240, 248)), (close_rect, (234, 96, 96))]:
            button_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(button_surface, fill, button_surface.get_rect(), border_radius=12)
            screen.blit(button_surface, rect.topleft)

        pygame.draw.line(screen, (34, 42, 56), (minimize_rect.x + 6, minimize_rect.centery + 3), (minimize_rect.right - 6, minimize_rect.centery + 3), 2)
        pygame.draw.rect(screen, (34, 42, 56), pygame.Rect(maximize_rect.x + 6, maximize_rect.y + 6, 12, 10), 2, border_radius=2)
        pygame.draw.line(screen, (255, 255, 255), (close_rect.x + 7, close_rect.y + 7), (close_rect.right - 7, close_rect.bottom - 7), 2)
        pygame.draw.line(screen, (255, 255, 255), (close_rect.right - 7, close_rect.y + 7), (close_rect.x + 7, close_rect.bottom - 7), 2)


class DesktopIcon:
    def __init__(self, x, y, app_id, label, manifest):
        self.rect = pygame.Rect(x, y, 84, 92)
        self.app_id = app_id
        self.label = label
        self.manifest = manifest
        self.selected = False
        self.click_count = 0
        self.last_click_time = 0

    def draw(self, screen, small_font):
        if self.selected:
            highlight = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            pygame.draw.rect(highlight, (197, 219, 255, 72), highlight.get_rect(), border_radius=18)
            pygame.draw.rect(highlight, (230, 240, 255, 120), highlight.get_rect(), 1, border_radius=18)
            screen.blit(highlight, self.rect.topleft)

        icon_rect = pygame.Rect(self.rect.x + 20, self.rect.y + 8, 44, 44)
        style = self.manifest.get("icon", {})
        primary = tuple(style.get("primary", (87, 143, 255)))
        accent = tuple(style.get("accent", (230, 240, 255)))
        shape = style.get("shape", "rounded")

        icon_surface = pygame.Surface((icon_rect.width, icon_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(icon_surface, (*accent, 240), icon_surface.get_rect(), border_radius=14)
        pygame.draw.rect(icon_surface, (255, 255, 255, 120), icon_surface.get_rect(), 1, border_radius=14)
        screen.blit(icon_surface, icon_rect.topleft)

        if shape == "circle":
            pygame.draw.circle(screen, primary, icon_rect.center, 14)
        elif shape == "folder":
            pygame.draw.rect(screen, primary, pygame.Rect(icon_rect.x + 6, icon_rect.y + 14, 30, 18), border_radius=4)
            pygame.draw.rect(screen, primary, pygame.Rect(icon_rect.x + 10, icon_rect.y + 9, 14, 8), border_radius=4)
        elif shape == "note":
            pygame.draw.circle(screen, primary, (icon_rect.x + 17, icon_rect.y + 31), 6)
            pygame.draw.line(screen, primary, (icon_rect.x + 23, icon_rect.y + 10), (icon_rect.x + 23, icon_rect.y + 30), 4)
            pygame.draw.line(screen, primary, (icon_rect.x + 23, icon_rect.y + 10), (icon_rect.x + 34, icon_rect.y + 14), 4)
        elif shape == "gear":
            pygame.draw.circle(screen, primary, icon_rect.center, 14, 4)
            pygame.draw.circle(screen, primary, icon_rect.center, 5)
            for angle in range(0, 360, 60):
                x = icon_rect.centerx + int(math.cos(math.radians(angle)) * 17)
                y = icon_rect.centery + int(math.sin(math.radians(angle)) * 17)
                pygame.draw.circle(screen, primary, (x, y), 3)
        else:
            pygame.draw.rect(screen, primary, icon_rect.inflate(-8, -8), border_radius=10)
        pygame.draw.rect(screen, (30, 42, 64), icon_rect, 2, border_radius=14)

        for index, line in enumerate(wrap_text_to_width(self.label, small_font, self.rect.width - 8, max_lines=2)):
            text = small_font.render(line, True, (255, 255, 255))
            screen.blit(text, text.get_rect(centerx=self.rect.centerx, y=self.rect.y + 58 + index * 14))

    def handle_click(self, pos):
        if self.rect.collidepoint(pos):
            self.selected = True
            return True
        return False


class DesktopEnvironment:
    def __init__(self):
        pygame.init()
        self.base_dir = Path(__file__).resolve().parent
        self.sys_dir = self.base_dir / "sys"
        self.config_file = self.base_dir / "desktop_config.json"
        self.installed_apps_dir = self.sys_dir / "installed_apps"
        self.cache_dir = self.sys_dir / "cache"
        self.sys_dir.mkdir(exist_ok=True)
        self.installed_apps_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)
        self.ensure_system_layout()

        self.config = self.load_config()
        self.username = self.ensure_user_profile()
        self.user_files_dir = self.base_dir / self.username
        self.user_files_dir.mkdir(exist_ok=True)
        self.migrate_legacy_user_files()

        self.width = int(self.config.get("width", 1280))
        self.height = int(self.config.get("height", 800))
        self.taskbar_position = self.config.get("taskbar_position", "bottom")
        self.wallpaper_pattern = self.config.get("wallpaper_pattern", "gradient")
        self.background_image_path = self.config.get("background_image_path")
        self.background_image = None

        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("PythOS Shell")
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)
        self.large_font = pygame.font.Font(None, 36)
        self.title_font = pygame.font.Font(None, 42)
        self.clock = pygame.time.Clock()

        self.taskbar_height = 54
        self.system_tray_width = 182
        self.taskbar_color = (43, 56, 81)
        self.text_color = (248, 250, 255)
        self.menu_color = (241, 244, 249)
        self.menu_outline = (151, 162, 184)
        self.background_color = (41, 90, 186)
        self.file_manager_root = self.user_files_dir

        self.start_button_rect = None
        self.start_menu_open = False
        self.start_menu_rect = None
        self.start_menu_item_rects = []
        self.start_menu_action_rects = {}
        self.context_menu_open = False
        self.context_menu_rect = None
        self.context_menu_pos = (0, 0)
        self.icon_context_menu_open = False
        self.icon_context_menu_pos = (0, 0)
        self.icon_context_menu_target = None
        self.login_button_rect = None

        self.windows = []
        self.active_window = None
        self.registered_apps = {}
        self.desktop_icons = []
        self.status_message = "Ready"
        self.status_message_until = 0

        self.authenticated = False
        self.session_password = None
        self.session_key = None
        self.system_poll_started = False

        self.system_state = {
            "usb_devices": [],
            "network_name": "Unavailable",
            "battery": "Unknown",
            "last_poll": None,
        }

        self.calculator_state = {"display": "0", "previous_value": 0, "operation": None, "waiting_for_operand": False, "should_reset_display": False}
        self.text_editor_state = {"content": "", "filename": "untitled.txt", "scroll_y": 0, "opened_path": None}
        self.music_player_state = {"current_file": None, "playing": False, "paused": False, "playlist": [], "current_track_index": -1, "volume": 70, "progress": 0, "total_length": 0}
        self.file_manager_state = {
            "files": [],
            "selected_file": None,
            "renaming_file": None,
            "rename_text": "",
            "current_dir": str(self.file_manager_root),
            "last_click_path": None,
            "last_click_time": 0,
        }
        self.settings_state = {"selected_app_id": None, "section": "home"}
        self.terminal_state = {
            "cwd": str(self.user_files_dir),
            "input": "",
            "output": ["Welcome to PythOS Terminal", "Type help, pwd, ls, cd <folder>, clear, or Linux commands."],
            "history": [],
            "history_index": 0,
            "running": False,
            "scroll_offset": 0,
        }

        self.login_state = {
            "phase": "login" if self.config["security"].get("password_hash") else "setup_create",
            "input": "",
            "pending_password": "",
            "message": "Create a system password to finish first boot." if not self.config["security"].get("password_hash") else "Enter your password to unlock PythOS Shell.",
            "error": False,
        }

        try:
            pygame.mixer.init()
        except Exception:
            self.post_status("Audio mixer unavailable")

        self.load_background_image(self.background_image_path)
        self.load_builtin_apps()
        self.load_imported_apps()
        self.rebuild_desktop_icons()
        self.refresh_file_manager()
        self.save_config()

    def load_config(self):
        default = {
            "width": 1280,
            "height": 800,
            "taskbar_position": "bottom",
            "wallpaper_pattern": "gradient",
            "background_image_path": None,
            "username": "",
            "imported_apps": [],
            "app_preferences": {},
            "desktop_icon_positions": {},
            "security": {
                "password_hash": "",
                "password_salt": "",
            },
        }
        if not self.config_file.exists():
            return default
        try:
            with self.config_file.open("r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            for key, value in default.items():
                if key == "security":
                    loaded.setdefault("security", {})
                    for sec_key, sec_value in value.items():
                        loaded["security"].setdefault(sec_key, sec_value)
                else:
                    loaded.setdefault(key, value)
            return loaded
        except Exception:
            return default

    def save_config(self):
        self.config["username"] = self.username
        self.config["width"] = self.width
        self.config["height"] = self.height
        self.config["taskbar_position"] = self.taskbar_position
        self.config["wallpaper_pattern"] = self.wallpaper_pattern
        self.config["background_image_path"] = self.background_image_path
        self.config.setdefault("security", {})
        with self.config_file.open("w", encoding="utf-8") as handle:
            json.dump(self.config, handle, indent=2)

    def post_status(self, message, seconds=3):
        self.status_message = message
        self.status_message_until = pygame.time.get_ticks() + seconds * 1000
        print(message)

    def load_background_image(self, image_path):
        self.background_image = None
        self.background_image_path = None
        if not image_path:
            return
        try:
            image = pygame.image.load(str(image_path))
            self.background_image = pygame.transform.smoothscale(image, (self.width, self.height))
            self.background_image_path = str(image_path)
            self.wallpaper_pattern = "image"
        except Exception as exc:
            self.post_status(f"Failed to load wallpaper: {exc}")

    def ensure_system_layout(self):
        module_names = [
            "calculator_app.py",
            "text_editor_app.py",
            "music_player_app.py",
            "file_manager_app.py",
            "settings_app.py",
            "about_app.py",
            "terminal_app.py",
        ]
        search_roots = [
            self.base_dir / "apps",
            self.base_dir,
        ]
        for module_name in module_names:
            target = self.sys_dir / module_name
            if target.exists():
                continue
            for root in search_roots:
                candidate = root / module_name
                if candidate.exists():
                    shutil.copy2(candidate, target)
                    break

    def validate_username(self, username):
        if not username:
            return "Username is required."
        if len(username) > 12:
            return "Username must be 12 characters or fewer."
        if not re.fullmatch(r"[A-Za-z0-9]+", username):
            return "Use letters and numbers only."
        if username.upper() in {"CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "LPT1", "LPT2", "LPT3"}:
            return "That username is reserved by the operating system."
        return None

    def ensure_user_profile(self):
        configured = str(self.config.get("username", "")).strip()
        if not self.validate_username(configured):
            return configured

        while True:
            root = tk.Tk()
            root.withdraw()
            username = simpledialog.askstring("Initial Boot", "Enter a username (letters and numbers only, max 12):", parent=root)
            if username is None:
                root.destroy()
                pygame.quit()
                raise SystemExit("Initial setup cancelled")
            username = username.strip()
            error = self.validate_username(username)
            if not error:
                root.destroy()
                return username
            messagebox.showerror("Invalid Username", error, parent=root)
            root.destroy()

    def make_password_salt(self):
        return os.urandom(16).hex()

    def hash_password(self, password, salt):
        return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()

    def begin_authenticated_session(self, password):
        security = self.config.setdefault("security", {})
        salt = security.get("password_salt", "")
        self.session_password = password
        self.session_key = hashlib.sha256(f"{salt}:{password}:session".encode("utf-8")).digest()
        self.authenticated = True
        self.login_state["input"] = ""
        self.login_state["error"] = False
        self.start_system_poll_service()
        self.post_status(f"Welcome, {self.username}")

    def verify_password(self, password):
        security = self.config.setdefault("security", {})
        salt = security.get("password_salt", "")
        stored = security.get("password_hash", "")
        if not salt or not stored:
            return False
        return self.hash_password(password, salt) == stored

    def store_new_password(self, password):
        salt = self.make_password_salt()
        security = self.config.setdefault("security", {})
        security["password_salt"] = salt
        security["password_hash"] = self.hash_password(password, salt)
        self.save_config()
        self.begin_authenticated_session(password)

    def migrate_legacy_user_files(self):
        for legacy_dir in [self.base_dir / "user_files", self.base_dir.parent / "root" / "user_files"]:
            if legacy_dir == self.user_files_dir or not legacy_dir.exists() or not legacy_dir.is_dir():
                continue
            for item in legacy_dir.iterdir():
                destination = self.user_files_dir / item.name
                if destination.exists():
                    continue
                shutil.move(str(item), str(destination))

    def start_system_poll_service(self):
        if self.system_poll_started:
            return
        self.system_poll_started = True

        def poll_loop():
            while True:
                try:
                    self.system_state["usb_devices"] = self.poll_usb_devices()
                    self.system_state["network_name"] = self.poll_network_name()
                    self.system_state["battery"] = self.poll_battery_status()
                    self.system_state["last_poll"] = datetime.datetime.now().strftime("%H:%M:%S")
                except Exception:
                    pass
                time.sleep(8)

        threading.Thread(target=poll_loop, daemon=True).start()

    def run_command_capture(self, command):
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=5)
            return (result.stdout or result.stderr or "").strip()
        except Exception:
            return ""

    def poll_usb_devices(self):
        devices = []
        if shutil.which("lsblk"):
            raw = self.run_command_capture(["lsblk", "-o", "NAME,TRAN,TYPE,MOUNTPOINT"])
            for line in raw.splitlines()[1:]:
                if "usb" in line.lower():
                    devices.append(" ".join(line.split()))
        return devices[:4]

    def poll_network_name(self):
        if shutil.which("nmcli"):
            raw = self.run_command_capture(["nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi"])
            for line in raw.splitlines():
                if line.startswith("yes:"):
                    return line.split(":", 1)[1] or "Connected"
        return "Unavailable"

    def poll_battery_status(self):
        power_supply = Path("/sys/class/power_supply")
        if power_supply.exists():
            for item in power_supply.iterdir():
                capacity = item / "capacity"
                status = item / "status"
                if capacity.exists():
                    capacity_text = capacity.read_text(encoding="utf-8", errors="ignore").strip()
                    status_text = status.read_text(encoding="utf-8", errors="ignore").strip() if status.exists() else ""
                    return f"{capacity_text}% {status_text}".strip()
        return "Unknown"

    def load_builtin_apps(self):
        for module_name in [
            "calculator_app.py",
            "text_editor_app.py",
            "music_player_app.py",
            "file_manager_app.py",
            "settings_app.py",
            "about_app.py",
            "terminal_app.py",
        ]:
            module_path = self.sys_dir / module_name
            if not module_path.exists():
                self.post_status(f"Missing system module: {module_name}")
                continue
            self.register_app(self.load_app_manifest_from_file(module_path), source="builtin", module_path=module_path)

    def load_app_manifest_from_file(self, file_path):
        module_name = f"user_app_{file_path.stem}_{abs(hash(str(file_path)))}"
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if not spec or not spec.loader:
            raise ValueError("Could not load module spec")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, "register"):
            manifest = module.register()
        elif hasattr(module, "APP_METADATA"):
            manifest = module.APP_METADATA
        else:
            raise ValueError("Module must expose register() or APP_METADATA")
        if not isinstance(manifest, dict):
            raise ValueError("App manifest must be a dictionary")
        return manifest

    def load_imported_apps(self):
        valid_paths = []
        for raw_path in self.config.get("imported_apps", []):
            path = Path(raw_path)
            if not path.exists():
                continue
            try:
                self.register_app(self.load_app_manifest_from_file(path), source="imported", module_path=path)
                valid_paths.append(str(path))
            except Exception as exc:
                self.post_status(f"Skipped app {path.name}: {exc}")
        self.config["imported_apps"] = valid_paths

    def register_app(self, manifest, source="builtin", module_path=None):
        app_id = manifest.get("id") or manifest.get("name", "").lower().replace(" ", "_")
        if not app_id:
            raise ValueError("App missing name")
        prefs = self.config.setdefault("app_preferences", {}).get(app_id, {})
        normalized = {
            "id": app_id,
            "name": manifest.get("name", app_id.replace("_", " ").title()),
            "title": manifest.get("title", manifest.get("name", app_id)),
            "window_size": tuple(manifest.get("window_size", (520, 380))),
            "default_position": tuple(manifest.get("default_position", (120, 120))),
            "draw": manifest.get("draw"),
            "on_click": manifest.get("on_click"),
            "on_key": manifest.get("on_key"),
            "on_open": manifest.get("on_open"),
            "icon": manifest.get("icon", {}),
            "system_app": bool(manifest.get("system_app", False)),
            "removable": bool(manifest.get("removable", not manifest.get("system_app", False))),
            "show_in_start_menu": prefs.get("show_in_start_menu", manifest.get("show_in_start_menu", True)),
            "show_on_desktop": prefs.get("show_on_desktop", manifest.get("show_on_desktop", False)),
            "source": source,
            "module_path": str(module_path) if module_path else None,
        }
        self.registered_apps[app_id] = normalized
        self.settings_state["selected_app_id"] = self.settings_state["selected_app_id"] or app_id

    def get_app_preferences(self, app_id):
        prefs = self.config.setdefault("app_preferences", {}).setdefault(app_id, {})
        app = self.registered_apps.get(app_id, {})
        prefs.setdefault("show_in_start_menu", app.get("show_in_start_menu", True))
        prefs.setdefault("show_on_desktop", app.get("show_on_desktop", False))
        return prefs

    def set_app_preference(self, app_id, key, value):
        prefs = self.get_app_preferences(app_id)
        prefs[key] = value
        if app_id in self.registered_apps:
            self.registered_apps[app_id][key] = value
        self.save_config()

    def get_next_icon_position(self):
        occupied = {tuple(value) for value in self.config.setdefault("desktop_icon_positions", {}).values()}
        x, y = 44, 42
        while (x, y) in occupied:
            y += 102
            if y > self.height - 180:
                y = 42
                x += 98
        return x, y

    def rebuild_desktop_icons(self):
        self.desktop_icons = []
        positions = self.config.setdefault("desktop_icon_positions", {})
        for app_id, manifest in sorted(self.registered_apps.items(), key=lambda item: item[1]["name"].lower()):
            if not manifest.get("show_on_desktop"):
                continue
            x, y = positions.get(app_id, self.get_next_icon_position())
            positions[app_id] = [x, y]
            self.desktop_icons.append(DesktopIcon(x, y, app_id, manifest["name"], manifest))

    def create_desktop_icon_for_app(self, app_id):
        if app_id not in self.registered_apps:
            return
        self.config.setdefault("desktop_icon_positions", {}).setdefault(app_id, list(self.get_next_icon_position()))
        self.set_app_preference(app_id, "show_on_desktop", True)
        self.rebuild_desktop_icons()
        self.post_status(f"Added {self.registered_apps[app_id]['name']} to desktop")

    def delete_icon(self, icon):
        self.set_app_preference(icon.app_id, "show_on_desktop", False)
        self.config.setdefault("desktop_icon_positions", {}).pop(icon.app_id, None)
        self.rebuild_desktop_icons()
        self.post_status(f"Removed {icon.label} from desktop")

    def draw_button(self, rect, label, font=None, fill=(82, 118, 196), outline=(40, 58, 95), text_color=(255, 255, 255), radius=BUTTON_RADIUS):
        font = font or self.small_font
        button_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(button_surface, (*fill, 242), button_surface.get_rect(), border_radius=radius)
        pygame.draw.rect(button_surface, (*outline, 255), button_surface.get_rect(), 1, border_radius=radius)
        self.screen.blit(button_surface, rect.topleft)
        fitted_label = fit_text_to_width(label, font, rect.width - 12)
        text = font.render(fitted_label, True, text_color)
        self.screen.blit(text, text.get_rect(center=rect.center))

    def draw_panel(self, rect, fill=(248, 250, 255, 220), border=(255, 255, 255, 120), radius=16):
        draw_acrylic_rect(self.screen, rect, fill, border, radius, shadow_alpha=22)

    def fit_text(self, text, font, max_width):
        return fit_text_to_width(text, font, max_width)

    def draw_fit_text(self, text, font, color, pos, max_width):
        return draw_fit_text(self.screen, text, font, color, pos, max_width)

    def draw_wrapped_text(self, text, font, color, rect, line_spacing=2, max_lines=None):
        return draw_wrapped_text(self.screen, text, font, color, rect, line_spacing=line_spacing, max_lines=max_lines)

    def get_taskbar_rect(self):
        if self.taskbar_position == "top":
            return pygame.Rect(10, 10, self.width - 20, self.taskbar_height)
        return pygame.Rect(10, self.height - self.taskbar_height - 10, self.width - 20, self.taskbar_height)

    def get_work_area(self):
        taskbar = self.get_taskbar_rect()
        if self.taskbar_position == "top":
            return pygame.Rect(0, taskbar.bottom + 10, self.width, self.height - taskbar.bottom - 10)
        return pygame.Rect(0, 0, self.width, taskbar.y - 10)

    def get_start_button_rect(self):
        taskbar = self.get_taskbar_rect()
        return pygame.Rect(taskbar.x + 12, taskbar.y + 8, 118, taskbar.height - 16)

    def get_start_menu_rect(self):
        width, height = 470, 500
        taskbar = self.get_taskbar_rect()
        if self.taskbar_position == "bottom":
            return pygame.Rect(taskbar.x, taskbar.y - height - 10, width, height)
        return pygame.Rect(taskbar.x, taskbar.bottom + 10, width, height)

    def get_context_menu_rect(self):
        x, y = self.context_menu_pos
        width, height = 192, 98
        return pygame.Rect(min(x, self.width - width), min(y, self.height - height), width, height)

    def get_start_menu_apps(self):
        apps = [app for app in self.registered_apps.values() if app.get("show_in_start_menu", True)]
        return sorted(apps, key=lambda item: (item["source"] != "builtin", item["name"].lower()))

    def get_managed_apps(self):
        return sorted(self.registered_apps.values(), key=lambda item: (not item["system_app"], item["name"].lower()))

    def is_within_file_manager_root(self, path):
        try:
            Path(path).resolve().relative_to(self.file_manager_root.resolve())
            return True
        except ValueError:
            return False

    def get_file_manager_current_dir(self):
        current_dir = Path(self.file_manager_state.get("current_dir", self.file_manager_root))
        if current_dir.exists() and current_dir.is_dir() and self.is_within_file_manager_root(current_dir):
            return current_dir
        return self.file_manager_root

    def get_file_manager_display_path(self, path=None):
        current_dir = Path(path) if path else self.get_file_manager_current_dir()
        try:
            relative = current_dir.resolve().relative_to(self.file_manager_root.resolve())
        except ValueError:
            return "/"
        if not relative.parts:
            return "/"
        return "/" + "/".join(relative.parts)

    def get_file_manager_places(self):
        return [{"label": "Root", "path": str(self.file_manager_root)}]

    def set_file_manager_directory(self, path):
        target = Path(path)
        if not target.exists() or not target.is_dir() or not self.is_within_file_manager_root(target):
            target = self.file_manager_root
        self.file_manager_state["current_dir"] = str(target.resolve())
        self.file_manager_state["selected_file"] = None
        self.cancel_rename()
        self.refresh_file_manager()

    def navigate_file_manager_up(self):
        current_dir = self.get_file_manager_current_dir()
        if current_dir == self.file_manager_root:
            return
        self.set_file_manager_directory(current_dir.parent)

    def get_file_manager_target_dir(self):
        current_dir = self.get_file_manager_current_dir()
        if self.is_within_file_manager_root(current_dir):
            return current_dir
        return self.user_files_dir

    def make_stream_key(self, length):
        if not self.session_key:
            raise RuntimeError("Session key unavailable")
        stream = bytearray()
        counter = 0
        while len(stream) < length:
            stream.extend(hashlib.sha256(self.session_key + counter.to_bytes(4, "big")).digest())
            counter += 1
        return bytes(stream[:length])

    def encrypt_bytes(self, raw_bytes):
        if not raw_bytes:
            return ENCRYPTION_MAGIC
        stream = self.make_stream_key(len(raw_bytes))
        encrypted = bytes(byte ^ stream[index] for index, byte in enumerate(raw_bytes))
        return ENCRYPTION_MAGIC + encrypted

    def decrypt_bytes(self, stored_bytes):
        if not stored_bytes.startswith(ENCRYPTION_MAGIC):
            return stored_bytes
        payload = stored_bytes[len(ENCRYPTION_MAGIC):]
        if not payload:
            return b""
        stream = self.make_stream_key(len(payload))
        return bytes(byte ^ stream[index] for index, byte in enumerate(payload))

    def read_user_file_bytes(self, path):
        path = Path(path)
        raw = path.read_bytes()
        if self.is_within_file_manager_root(path):
            return self.decrypt_bytes(raw)
        return raw

    def write_user_file_bytes(self, path, raw_bytes):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if self.is_within_file_manager_root(path):
            path.write_bytes(self.encrypt_bytes(raw_bytes))
        else:
            path.write_bytes(raw_bytes)

    def resolve_audio_source(self, raw_path):
        path = Path(raw_path)
        if not path.exists():
            raise FileNotFoundError(path)
        if not self.is_within_file_manager_root(path):
            return str(path)
        raw = path.read_bytes()
        if not raw.startswith(ENCRYPTION_MAGIC):
            return str(path)
        decrypted = self.decrypt_bytes(raw)
        destination = self.cache_dir / f"{path.stem}_decrypted{path.suffix}"
        destination.write_bytes(decrypted)
        return str(destination)

    def draw_wallpaper(self):
        if self.wallpaper_pattern == "image" and self.background_image:
            self.screen.blit(self.background_image, (0, 0))
            return
        if self.wallpaper_pattern == "solid":
            self.screen.fill(self.background_color)
            return
        if self.wallpaper_pattern == "pattern":
            self.screen.fill((26, 58, 125))
            for x in range(0, self.width, 56):
                for y in range(0, self.height, 56):
                    if (x // 56 + y // 56) % 2 == 0:
                        pygame.draw.rect(self.screen, (35, 74, 151), (x, y, 56, 56))
            return
        for y in range(self.height):
            ratio = y / max(1, self.height - 1)
            color = (
                int(26 + 48 * ratio),
                int(84 + 36 * ratio),
                int(152 + 70 * ratio),
            )
            pygame.draw.line(self.screen, color, (0, y), (self.width, y))

    def draw_desktop_icons(self):
        for icon in self.desktop_icons:
            icon.draw(self.screen, self.small_font)

    def draw_windows(self):
        for window in self.windows:
            if window.minimized:
                continue
            window.draw_shell(self.screen, self.font)
            manifest = self.registered_apps.get(window.app_id)
            if not manifest:
                continue
            callback = manifest.get("draw")
            if callable(callback):
                callback(self, self.screen, window.get_content_rect(), self.font, self.small_font, window)

    def draw_taskbar(self):
        taskbar = self.get_taskbar_rect()
        draw_acrylic_rect(self.screen, taskbar, (34, 46, 67, 210), (255, 255, 255, 55), TASKBAR_RADIUS, shadow_alpha=28, shadow_offset=(0, 0))

    def draw_start_button(self, mouse_pos):
        self.start_button_rect = self.get_start_button_rect()
        fill = (61, 136, 233) if self.start_menu_open or self.start_button_rect.collidepoint(mouse_pos) else (79, 91, 115)
        self.draw_button(self.start_button_rect, "Start", self.font, fill=fill, outline=(31, 41, 59), radius=16)

    def draw_window_list(self):
        if not self.windows:
            return
        taskbar = self.get_taskbar_rect()
        start_rect = self.get_start_button_rect()
        available_start = start_rect.right + 10
        available_end = taskbar.right - self.system_tray_width - 12
        available_width = available_end - available_start
        if available_width <= 0:
            return
        button_width = max(124, min(196, (available_width - max(0, len(self.windows) - 1) * 6) // len(self.windows)))
        x = available_start
        for window in self.windows:
            rect = pygame.Rect(x, taskbar.y + 8, button_width, taskbar.height - 16)
            fill = (108, 124, 158) if self.active_window == window and not window.minimized else (72, 83, 106)
            self.draw_button(rect, window.title, self.small_font, fill=fill, outline=(35, 44, 59), radius=14)
            x += button_width + 6

    def draw_system_tray(self):
        taskbar = self.get_taskbar_rect()
        tray_rect = pygame.Rect(taskbar.right - self.system_tray_width, taskbar.y + 8, self.system_tray_width - 10, taskbar.height - 16)
        draw_acrylic_rect(self.screen, tray_rect, (68, 79, 104, 210), (255, 255, 255, 45), 14, shadow_alpha=0, shadow_offset=(0, 0))
        now = datetime.datetime.now()
        time_text = self.font.render(now.strftime("%I:%M %p"), True, self.text_color)
        date_text = self.small_font.render(now.strftime("%b %d, %Y"), True, (201, 211, 232))
        self.screen.blit(time_text, (tray_rect.x + 12, tray_rect.y + 2))
        self.screen.blit(date_text, (tray_rect.x + 12, tray_rect.y + 22))

    def draw_start_menu(self):
        if not self.start_menu_open:
            return
        self.start_menu_rect = self.get_start_menu_rect()
        draw_acrylic_rect(self.screen, self.start_menu_rect, (243, 246, 251, 236), (255, 255, 255, 140), 20)

        header = pygame.Rect(self.start_menu_rect.x + 8, self.start_menu_rect.y + 8, self.start_menu_rect.width - 16, 72)
        draw_acrylic_rect(self.screen, header, (45, 101, 193, 228), (255, 255, 255, 36), 18, shadow_alpha=0, shadow_offset=(0, 0))
        self.screen.blit(self.large_font.render("Start", True, (255, 255, 255)), (header.x + 18, header.y + 14))
        self.draw_fit_text("Open programs, manage apps, and access the system shell.", self.small_font, (220, 231, 252), (header.x + 18, header.y + 44), header.width - 36)

        apps_panel = pygame.Rect(self.start_menu_rect.x + 14, header.bottom + 12, 272, self.start_menu_rect.height - 106)
        quick_panel = pygame.Rect(apps_panel.right + 10, header.bottom + 12, self.start_menu_rect.right - apps_panel.right - 24, self.start_menu_rect.height - 106)
        self.draw_panel(apps_panel, (251, 252, 254, 220), (255, 255, 255, 120), 18)
        self.draw_panel(quick_panel, (233, 238, 246, 220), (255, 255, 255, 110), 18)

        self.screen.blit(self.font.render("Programs", True, (35, 42, 57)), (apps_panel.x + 12, apps_panel.y + 12))
        self.draw_fit_text("Right click any app to pin it to the desktop.", self.small_font, (101, 111, 130), (apps_panel.x + 12, apps_panel.y + 36), apps_panel.width - 24)

        apps = self.get_start_menu_apps()
        list_rect = pygame.Rect(apps_panel.x + 8, apps_panel.y + 62, apps_panel.width - 16, apps_panel.height - 70)
        self.start_menu_item_rects = []
        for index, manifest in enumerate(apps[:10]):
            item_rect = pygame.Rect(list_rect.x, list_rect.y + index * 36, list_rect.width, 32)
            self.start_menu_item_rects.append((item_rect, manifest["id"]))
            self.draw_panel(item_rect, (236, 240, 247, 210), (255, 255, 255, 110), 14)
            app_type = "System" if manifest["system_app"] else "Imported"
            badge = self.small_font.render(app_type, True, (96, 107, 129))
            badge_x = item_rect.right - badge.get_width() - 12
            self.draw_fit_text(manifest["name"], self.font, (26, 33, 45), (item_rect.x + 12, item_rect.y + 5), badge_x - item_rect.x - 22)
            self.screen.blit(badge, (badge_x, item_rect.y + 8))

        self.screen.blit(self.font.render("System", True, (35, 42, 57)), (quick_panel.x + 12, quick_panel.y + 12))
        self.draw_fit_text(f"{len(apps)} programs installed", self.small_font, (102, 113, 135), (quick_panel.x + 12, quick_panel.y + 38), quick_panel.width - 24)
        self.draw_fit_text(f"Network: {self.system_state['network_name']}", self.small_font, (102, 113, 135), (quick_panel.x + 12, quick_panel.y + 58), quick_panel.width - 24)

        file_manager_rect = pygame.Rect(quick_panel.x + 12, quick_panel.y + 92, quick_panel.width - 24, 34)
        settings_rect = pygame.Rect(quick_panel.x + 12, file_manager_rect.bottom + 8, quick_panel.width - 24, 34)
        terminal_rect = pygame.Rect(quick_panel.x + 12, settings_rect.bottom + 8, quick_panel.width - 24, 34)
        about_rect = pygame.Rect(quick_panel.x + 12, terminal_rect.bottom + 8, quick_panel.width - 24, 34)
        exit_rect = pygame.Rect(quick_panel.x + 12, quick_panel.bottom - 46, quick_panel.width - 24, 34)
        self.start_menu_action_rects = {
            "file_manager": file_manager_rect,
            "settings": settings_rect,
            "terminal": terminal_rect,
            "about": about_rect,
            "exit": exit_rect,
        }
        self.draw_button(file_manager_rect, "File Manager", self.small_font, fill=(108, 128, 167), outline=(78, 93, 122))
        self.draw_button(settings_rect, "Settings", self.small_font, fill=(108, 128, 167), outline=(78, 93, 122))
        self.draw_button(terminal_rect, "Terminal", self.small_font, fill=(85, 124, 104), outline=(57, 83, 65))
        self.draw_button(about_rect, "About", self.small_font, fill=(108, 128, 167), outline=(78, 93, 122))
        self.draw_button(exit_rect, "Shut Down", self.small_font, fill=(184, 88, 88), outline=(118, 53, 53))

    def draw_context_menu(self):
        if not self.context_menu_open:
            return
        self.context_menu_rect = self.get_context_menu_rect()
        draw_acrylic_rect(self.screen, self.context_menu_rect, (243, 246, 251, 235), (255, 255, 255, 120), 16)
        items = [f"Taskbar: {self.taskbar_position.title()}", "Move to Top" if self.taskbar_position == "bottom" else "Move to Bottom"]
        for index, item in enumerate(items):
            item_rect = pygame.Rect(self.context_menu_rect.x + 8, self.context_menu_rect.y + 8 + index * 38, self.context_menu_rect.width - 16, 30)
            self.draw_panel(item_rect, (229, 234, 244, 210), (255, 255, 255, 110), 12)
            self.draw_fit_text(item, self.small_font, (30, 37, 54), (item_rect.x + 10, item_rect.y + 7), item_rect.width - 20)

    def draw_icon_context_menu(self):
        if not self.icon_context_menu_open:
            return
        menu_width, menu_height = 140, 110
        x, y = self.icon_context_menu_pos
        rect = pygame.Rect(min(x, self.width - menu_width), min(y, self.height - menu_height), menu_width, menu_height)
        draw_acrylic_rect(self.screen, rect, (243, 246, 251, 235), (255, 255, 255, 120), 16)
        for index, item in enumerate(["Open", "Rename", "Delete"]):
            item_rect = pygame.Rect(rect.x + 8, rect.y + 8 + index * 32, rect.width - 16, 26)
            self.draw_panel(item_rect, (229, 234, 244, 210), (255, 255, 255, 110), 12)
            self.draw_fit_text(item, self.small_font, (30, 37, 54), (item_rect.x + 10, item_rect.y + 5), item_rect.width - 20)

    def draw_status_bar(self):
        if pygame.time.get_ticks() > self.status_message_until:
            return
        rect = pygame.Rect(self.width - 332, 16, 312, 38)
        draw_acrylic_rect(self.screen, rect, (27, 37, 58, 218), (255, 255, 255, 40), 16, shadow_alpha=28)
        self.draw_fit_text(self.status_message, self.small_font, (230, 236, 248), (rect.x + 12, rect.y + 12), rect.width - 24)

    def draw_login_screen(self):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((10, 16, 28, 88))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect((self.width - 500) // 2, (self.height - 360) // 2, 500, 360)
        draw_acrylic_rect(self.screen, panel, (246, 249, 255, 228), (255, 255, 255, 130), 24)
        title = self.title_font.render("PythOS", True, (27, 34, 46))
        subtitle = self.font.render("Gatekeeper", True, (76, 87, 110))
        self.screen.blit(title, (panel.x + 26, panel.y + 24))
        self.screen.blit(subtitle, (panel.x + 28, panel.y + 62))

        self.draw_fit_text(f"User: {self.username}", self.font, (42, 51, 69), (panel.x + 28, panel.y + 106), panel.width - 56)

        prompt_map = {
            "login": "Enter password",
            "setup_create": "Create password",
            "setup_confirm": "Confirm password",
        }
        prompt = self.font.render(prompt_map[self.login_state["phase"]], True, (42, 51, 69))
        self.screen.blit(prompt, (panel.x + 28, panel.y + 142))

        input_rect = pygame.Rect(panel.x + 28, panel.y + 176, panel.width - 56, 54)
        self.draw_panel(input_rect, (255, 255, 255, 230), (215, 224, 241, 160), 18)
        masked = "•" * len(self.login_state["input"])
        display_text = masked if masked else " "
        input_surface = self.large_font.render(display_text, True, (28, 35, 49))
        self.screen.blit(input_surface, (input_rect.x + 18, input_rect.y + 11))

        hint_lines = [
            self.login_state["message"],
            "Press Enter to continue. Passwords are stored as SHA-256 hashes only.",
        ]
        hint_rect = pygame.Rect(panel.x + 28, panel.y + 246, panel.width - 56, 42)
        if self.login_state["error"]:
            self.draw_wrapped_text(self.login_state["message"], self.small_font, (177, 54, 54), hint_rect, line_spacing=3, max_lines=2)
        else:
            self.draw_fit_text(hint_lines[0], self.small_font, (82, 92, 114), (panel.x + 28, panel.y + 246), panel.width - 56)
            self.draw_fit_text(hint_lines[1], self.small_font, (82, 92, 114), (panel.x + 28, panel.y + 266), panel.width - 56)

        self.login_button_rect = pygame.Rect(panel.x + 28, panel.bottom - 70, 140, 38)
        label = "Unlock" if self.login_state["phase"] == "login" else "Continue"
        self.draw_button(self.login_button_rect, label, self.font, fill=(58, 122, 220), outline=(35, 78, 147), radius=16)

        self.draw_fit_text("Desktop rendering remains locked until authentication completes.", self.small_font, (101, 111, 130), (panel.x + 28, panel.bottom - 24), panel.width - 56)

    def handle_login_submit(self):
        value = self.login_state["input"]
        phase = self.login_state["phase"]
        self.login_state["error"] = False

        if phase == "login":
            if self.verify_password(value):
                self.begin_authenticated_session(value)
                return
            self.login_state["message"] = "Incorrect password."
            self.login_state["input"] = ""
            self.login_state["error"] = True
            return

        if phase == "setup_create":
            if len(value) < 4:
                self.login_state["message"] = "Choose a password with at least 4 characters."
                self.login_state["input"] = ""
                self.login_state["error"] = True
                return
            self.login_state["pending_password"] = value
            self.login_state["phase"] = "setup_confirm"
            self.login_state["message"] = "Re-enter the password to confirm it."
            self.login_state["input"] = ""
            return

        if phase == "setup_confirm":
            if value != self.login_state["pending_password"]:
                self.login_state["phase"] = "setup_create"
                self.login_state["pending_password"] = ""
                self.login_state["message"] = "Passwords did not match. Create a new password."
                self.login_state["input"] = ""
                self.login_state["error"] = True
                return
            self.store_new_password(value)

    def handle_login_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.login_button_rect and self.login_button_rect.collidepoint(event.pos):
                self.handle_login_submit()
            return
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_RETURN:
            self.handle_login_submit()
        elif event.key == pygame.K_BACKSPACE:
            self.login_state["input"] = self.login_state["input"][:-1]
        elif event.key == pygame.K_ESCAPE:
            self.login_state["input"] = ""
        elif event.unicode and event.unicode.isprintable():
            self.login_state["input"] += event.unicode

    def open_application(self, app_id):
        if not self.authenticated:
            return
        manifest = self.registered_apps.get(app_id)
        if not manifest:
            self.post_status(f"Application '{app_id}' is not installed")
            return
        width, height = manifest["window_size"]
        x, y = manifest["default_position"]
        work_area = self.get_work_area()
        x = max(work_area.x + 20, min(x, work_area.right - width - 20))
        y = max(work_area.y + 20, min(y, work_area.bottom - height - 20))
        title = self.get_text_editor_window_title() if app_id == "text_editor" else manifest["title"]
        window = Window(x, y, width, height, title, app_id)
        self.windows.append(window)
        self.active_window = window
        callback = manifest.get("on_open")
        if callable(callback):
            callback(self, window)
        self.post_status(f"Opened {manifest['name']}")

    def import_python_app(self):
        try:
            root = tk.Tk()
            root.withdraw()
            file_path = filedialog.askopenfilename(title="Import Python App Module", filetypes=[("Python Files", "*.py")])
            root.destroy()
        except Exception as exc:
            self.post_status(f"App import dialog failed: {exc}")
            return
        if not file_path:
            return
        source = Path(file_path)
        destination = self.installed_apps_dir / source.name
        counter = 1
        while destination.exists():
            destination = self.installed_apps_dir / f"{source.stem}_{counter}{source.suffix}"
            counter += 1
        try:
            shutil.copy2(source, destination)
            manifest = self.load_app_manifest_from_file(destination)
            self.register_app(manifest, source="imported", module_path=destination)
            self.config.setdefault("imported_apps", []).append(str(destination))
            app_id = manifest.get("id") or manifest.get("name", "").lower().replace(" ", "_")
            self.get_app_preferences(app_id)
            self.settings_state["selected_app_id"] = app_id
            self.rebuild_desktop_icons()
            self.refresh_file_manager()
            self.save_config()
            self.post_status(f"Imported app: {self.registered_apps[app_id]['name']}")
        except Exception as exc:
            destination.unlink(missing_ok=True)
            self.post_status(f"Could not import app: {exc}")

    def remove_selected_app(self):
        app_id = self.settings_state.get("selected_app_id")
        manifest = self.registered_apps.get(app_id)
        if not manifest:
            self.post_status("Select an app first")
            return
        if manifest["system_app"] or not manifest["removable"]:
            self.post_status(f"{manifest['name']} is part of the system")
            return
        module_path = manifest.get("module_path")
        if module_path:
            Path(module_path).unlink(missing_ok=True)
        self.config["imported_apps"] = [path for path in self.config.get("imported_apps", []) if path != module_path]
        self.config.get("app_preferences", {}).pop(app_id, None)
        self.config.get("desktop_icon_positions", {}).pop(app_id, None)
        self.windows = [window for window in self.windows if window.app_id != app_id]
        self.registered_apps.pop(app_id, None)
        self.settings_state["selected_app_id"] = next(iter(self.registered_apps.keys()), None)
        self.rebuild_desktop_icons()
        self.refresh_file_manager()
        self.save_config()
        self.post_status(f"Removed app: {manifest['name']}")

    def toggle_selected_app_desktop(self):
        app_id = self.settings_state.get("selected_app_id")
        manifest = self.registered_apps.get(app_id)
        if not manifest:
            return
        new_value = not manifest.get("show_on_desktop")
        self.set_app_preference(app_id, "show_on_desktop", new_value)
        if new_value:
            self.config.setdefault("desktop_icon_positions", {}).setdefault(app_id, list(self.get_next_icon_position()))
        else:
            self.config.setdefault("desktop_icon_positions", {}).pop(app_id, None)
        self.rebuild_desktop_icons()
        self.post_status(("Pinned" if new_value else "Removed") + f" {manifest['name']} on desktop")

    def toggle_selected_app_start(self):
        app_id = self.settings_state.get("selected_app_id")
        manifest = self.registered_apps.get(app_id)
        if not manifest:
            return
        new_value = not manifest.get("show_in_start_menu")
        self.set_app_preference(app_id, "show_in_start_menu", new_value)
        self.post_status(("Pinned" if new_value else "Removed") + f" {manifest['name']} in start menu")

    def open_background_selector(self):
        try:
            root = tk.Tk()
            root.withdraw()
            file_path = filedialog.askopenfilename(title="Select Wallpaper Image", filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp"), ("All Files", "*.*")])
            root.destroy()
        except Exception as exc:
            self.post_status(f"Background picker failed: {exc}")
            return
        if file_path:
            self.load_background_image(file_path)
            self.save_config()

    def set_wallpaper_pattern(self, pattern):
        self.wallpaper_pattern = pattern
        if pattern != "image":
            self.background_image = None
            self.background_image_path = None
        self.save_config()
        self.post_status(f"Wallpaper set to {pattern}")

    def refresh_file_manager(self):
        current_dir = self.get_file_manager_current_dir()
        selected_path = self.file_manager_state["selected_file"]["path"] if self.file_manager_state["selected_file"] else None
        rename_path = self.file_manager_state["renaming_file"]["path"] if self.file_manager_state["renaming_file"] else None
        files = []

        if current_dir != self.file_manager_root:
            files.append({
                "name": "..",
                "type": "folder",
                "path": str(current_dir.parent),
                "is_folder": True,
                "size": 0,
                "modified": "",
                "is_navigation": True,
            })

        for item in sorted(current_dir.iterdir(), key=lambda path: (path.is_file(), path.name.lower())):
            size = item.stat().st_size if item.is_file() else 0
            files.append({
                "name": item.name,
                "type": "folder" if item.is_dir() else self.detect_file_type(item),
                "path": str(item),
                "is_folder": item.is_dir(),
                "size": size,
                "modified": datetime.datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                "is_navigation": False,
            })

        self.file_manager_state["current_dir"] = str(current_dir)
        self.file_manager_state["files"] = files
        self.file_manager_state["selected_file"] = next((item for item in files if item["path"] == selected_path and item["name"] != ".."), None)
        if rename_path:
            self.file_manager_state["renaming_file"] = next((item for item in files if item["path"] == rename_path and item["name"] != ".."), None)
            if not self.file_manager_state["renaming_file"]:
                self.cancel_rename()

    def detect_file_type(self, path):
        suffix = path.suffix.lower()
        if suffix in {".txt", ".md", ".py", ".json", ".csv", ".log"}:
            return "text"
        if suffix in {".png", ".jpg", ".jpeg", ".bmp", ".gif"}:
            return "image"
        if suffix in {".mp3", ".wav", ".ogg"}:
            return "audio"
        return suffix[1:] if suffix else "file"

    def import_file_into_system(self):
        target_dir = self.get_file_manager_target_dir()
        try:
            root = tk.Tk()
            root.withdraw()
            file_paths = filedialog.askopenfilenames(title="Import Files Into System", filetypes=[("All Files", "*.*")])
            root.destroy()
        except Exception as exc:
            self.post_status(f"File import failed: {exc}")
            return
        imported = 0
        for raw_path in file_paths:
            source = Path(raw_path)
            destination = target_dir / source.name
            counter = 1
            while destination.exists():
                destination = target_dir / f"{source.stem}_{counter}{source.suffix}"
                counter += 1
            self.write_user_file_bytes(destination, source.read_bytes())
            imported += 1
        self.refresh_file_manager()
        if imported:
            self.post_status(f"Imported {imported} file(s) into {self.get_file_manager_display_path(target_dir)}")

    def get_unique_child_name(self, base_name, parent_dir=None, folder=False):
        parent_dir = Path(parent_dir) if parent_dir else self.get_file_manager_target_dir()
        destination = parent_dir / base_name
        counter = 1
        stem = destination.stem if destination.suffix else destination.name
        suffix = "" if folder else destination.suffix
        while destination.exists():
            destination = parent_dir / f"{stem} {counter}{suffix}"
            counter += 1
        return destination.name

    def create_new_file(self):
        target_dir = self.get_file_manager_target_dir()
        target = target_dir / self.get_unique_child_name("New File.txt", parent_dir=target_dir)
        self.write_user_file_bytes(target, b"")
        self.refresh_file_manager()
        self.post_status(f"Created {target.name}")

    def create_new_folder(self):
        target_dir = self.get_file_manager_target_dir()
        target = target_dir / self.get_unique_child_name("New Folder", parent_dir=target_dir, folder=True)
        target.mkdir(exist_ok=False)
        self.refresh_file_manager()
        self.post_status(f"Created {target.name}")

    def delete_file(self, file_info):
        if file_info.get("is_navigation"):
            self.post_status("Open the parent folder instead of deleting it")
            return
        path = Path(file_info["path"])
        if path == self.file_manager_root or not self.is_within_file_manager_root(path):
            self.post_status("That item is protected")
            return
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)
        self.refresh_file_manager()
        self.post_status(f"Deleted {file_info['name']}")

    def get_text_editor_window_title(self):
        filename = self.text_editor_state.get("filename") or "untitled.txt"
        return f"Text Editor - {filename}"

    def sync_text_editor_window_title(self):
        title = self.get_text_editor_window_title()
        for window in self.windows:
            if window.app_id == "text_editor":
                window.title = title

    def open_file_in_editor(self, file_info):
        path = Path(file_info["path"])
        if file_info["is_folder"]:
            self.set_file_manager_directory(path)
            self.post_status(f"Opened {self.get_file_manager_display_path(path)}")
            return
        if file_info["type"] == "audio":
            self.music_player_state["playlist"] = [str(path)]
            self.music_player_state["current_track_index"] = 0
            self.music_player_state["current_file"] = str(path)
            if not any(window.app_id == "music_player" for window in self.windows):
                self.open_application("music_player")
            self.music_play_pause()
            return
        if file_info["type"] != "text":
            self.post_status(f"{file_info['name']} is not a text file")
            return
        raw_text = self.read_user_file_bytes(path).decode("utf-8", errors="replace")
        self.text_editor_state["content"] = raw_text
        self.text_editor_state["filename"] = path.name
        self.text_editor_state["opened_path"] = str(path)
        self.text_editor_state["scroll_y"] = 0
        if not any(window.app_id == "text_editor" for window in self.windows):
            self.open_application("text_editor")
        self.sync_text_editor_window_title()
        self.post_status(f"Opened {file_info['name']}")

    def save_text_file(self):
        filename = self.text_editor_state["filename"].strip() or "untitled.txt"
        target_dir = self.get_file_manager_target_dir()
        target = Path(self.text_editor_state["opened_path"]) if self.text_editor_state["opened_path"] else target_dir / filename
        if not self.is_within_file_manager_root(target.parent):
            target = target_dir / filename
        self.write_user_file_bytes(target, self.text_editor_state["content"].encode("utf-8"))
        self.text_editor_state["opened_path"] = str(target)
        self.text_editor_state["filename"] = target.name
        self.refresh_file_manager()
        self.sync_text_editor_window_title()
        self.post_status(f"Saved {target.name}")

    def clear_text_editor(self):
        self.text_editor_state["content"] = ""
        self.text_editor_state["scroll_y"] = 0
        self.text_editor_state["opened_path"] = None
        self.post_status("Editor cleared")

    def new_text_file(self):
        self.text_editor_state["filename"] = self.get_unique_child_name("New File.txt")
        self.text_editor_state["content"] = ""
        self.text_editor_state["scroll_y"] = 0
        self.text_editor_state["opened_path"] = None
        self.sync_text_editor_window_title()
        self.post_status(f"New file: {self.text_editor_state['filename']}")

    def start_rename_file(self, file_info):
        if file_info.get("is_navigation"):
            self.post_status("Select a file or folder to rename")
            return
        self.file_manager_state["renaming_file"] = file_info
        path = Path(file_info["path"])
        self.file_manager_state["rename_text"] = path.stem if path.is_file() and path.suffix else path.name

    def finish_rename(self):
        file_info = self.file_manager_state["renaming_file"]
        if not file_info:
            return
        raw_name = self.file_manager_state["rename_text"].strip()
        if not raw_name:
            self.cancel_rename()
            return
        old_path = Path(file_info["path"])
        if not self.is_within_file_manager_root(old_path):
            self.post_status("That item cannot be renamed")
            return
        raw_name = raw_name.replace("/", "").replace("\\", "").strip()
        if not raw_name or raw_name in {".", ".."}:
            self.post_status("Enter a valid file or folder name")
            return
        if old_path.is_file() and old_path.suffix and not raw_name.lower().endswith(old_path.suffix.lower()):
            raw_name += old_path.suffix
        new_path = old_path.with_name(raw_name)
        if new_path.exists() and new_path.resolve() != old_path.resolve():
            self.post_status(f"{new_path.name} already exists")
            return

        was_open_in_editor = False
        opened_path = self.text_editor_state.get("opened_path")
        if opened_path:
            try:
                was_open_in_editor = Path(opened_path).resolve() == old_path.resolve()
            except OSError:
                was_open_in_editor = str(opened_path) == str(old_path)

        old_path.rename(new_path)

        if was_open_in_editor:
            self.text_editor_state["opened_path"] = str(new_path)
            self.text_editor_state["filename"] = new_path.name
            self.sync_text_editor_window_title()

        self.cancel_rename()
        self.refresh_file_manager()
        self.file_manager_state["selected_file"] = next(
            (item for item in self.file_manager_state["files"] if item["path"] == str(new_path)),
            None,
        )
        self.post_status(f"Renamed to {new_path.name}")

    def cancel_rename(self):
        self.file_manager_state["renaming_file"] = None
        self.file_manager_state["rename_text"] = ""

    def handle_file_manager_input(self, event):
        if event.key == pygame.K_RETURN:
            self.finish_rename()
        elif event.key == pygame.K_ESCAPE:
            self.cancel_rename()
        elif event.key == pygame.K_BACKSPACE:
            self.file_manager_state["rename_text"] = self.file_manager_state["rename_text"][:-1]
        elif event.unicode and event.unicode.isprintable():
            self.file_manager_state["rename_text"] += event.unicode

    def handle_text_editor_input(self, event):
        if event.key == pygame.K_BACKSPACE:
            self.text_editor_state["content"] = self.text_editor_state["content"][:-1]
        elif event.key == pygame.K_RETURN:
            self.text_editor_state["content"] += "\n"
        elif event.key == pygame.K_TAB:
            self.text_editor_state["content"] += "    "
        elif event.unicode and event.unicode.isprintable():
            self.text_editor_state["content"] += event.unicode

    def calculator_button_pressed(self, button):
        state = self.calculator_state
        if button == "C":
            state.update({"display": "0", "previous_value": 0, "operation": None, "waiting_for_operand": False, "should_reset_display": False})
        elif button == "CE":
            state["display"] = "0"
            state["should_reset_display"] = False
        elif button == "BACK":
            state["display"] = state["display"][:-1] if len(state["display"]) > 1 else "0"
        elif button in {"+", "-", "*", "/"}:
            if state["operation"] and not state["waiting_for_operand"]:
                self.calculate_result()
            state["previous_value"] = float(state["display"])
            state["operation"] = button
            state["waiting_for_operand"] = True
            state["should_reset_display"] = True
        elif button == "=":
            if state["operation"] and not state["waiting_for_operand"]:
                self.calculate_result()
                state["operation"] = None
                state["waiting_for_operand"] = False
        elif button == ".":
            if state["should_reset_display"]:
                state["display"] = "0."
                state["should_reset_display"] = False
            elif "." not in state["display"]:
                state["display"] += "."
        else:
            if state["should_reset_display"] or state["display"] == "0":
                state["display"] = button
                state["should_reset_display"] = False
            else:
                state["display"] += button
            state["waiting_for_operand"] = False
        if len(state["display"]) > 14:
            state["display"] = state["display"][:14]

    def calculate_result(self):
        state = self.calculator_state
        current = float(state["display"])
        previous = state["previous_value"]
        operation = state["operation"]
        if operation == "+":
            result = previous + current
        elif operation == "-":
            result = previous - current
        elif operation == "*":
            result = previous * current
        elif operation == "/":
            if current == 0:
                state["display"] = "Error"
                return
            result = previous / current
        else:
            return
        state["display"] = str(int(result)) if result == int(result) else f"{result:.8f}".rstrip("0").rstrip(".")
        if len(state["display"]) > 14:
            state["display"] = f"{result:.3e}"
        state["previous_value"] = result
        state["should_reset_display"] = True

    def open_music_file_dialog(self):
        try:
            root = tk.Tk()
            root.withdraw()
            file_paths = filedialog.askopenfilenames(title="Select Audio Files", filetypes=[("Audio Files", "*.mp3;*.wav;*.ogg"), ("All Files", "*.*")])
            root.destroy()
        except Exception as exc:
            self.post_status(f"Audio import failed: {exc}")
            return
        for file_path in file_paths:
            if file_path not in self.music_player_state["playlist"]:
                self.music_player_state["playlist"].append(file_path)
        if self.music_player_state["playlist"] and self.music_player_state["current_track_index"] == -1:
            self.music_player_state["current_track_index"] = 0
            self.music_player_state["current_file"] = self.music_player_state["playlist"][0]
        if file_paths:
            self.post_status(f"Added {len(file_paths)} track(s)")

    def music_play_pause(self):
        if not self.music_player_state["playlist"]:
            self.post_status("Add audio files first")
            return
        try:
            if self.music_player_state["playing"]:
                pygame.mixer.music.pause()
                self.music_player_state["playing"] = False
                self.music_player_state["paused"] = True
                self.post_status("Playback paused")
                return
            if self.music_player_state["paused"]:
                pygame.mixer.music.unpause()
                self.music_player_state["playing"] = True
                self.music_player_state["paused"] = False
                self.post_status("Playback resumed")
                return
            if self.music_player_state["current_track_index"] < 0:
                self.music_player_state["current_track_index"] = 0
            current_file = self.music_player_state["playlist"][self.music_player_state["current_track_index"]]
            playable_file = self.resolve_audio_source(current_file)
            pygame.mixer.music.load(playable_file)
            pygame.mixer.music.set_volume(self.music_player_state["volume"] / 100)
            pygame.mixer.music.play()
            self.music_player_state["current_file"] = current_file
            self.music_player_state["playing"] = True
            self.music_player_state["paused"] = False
            self.music_player_state["progress"] = 0
            self.music_player_state["total_length"] = 0
            self.start_music_progress_tracking()
            self.post_status(f"Playing {Path(current_file).name}")
        except Exception as exc:
            self.post_status(f"Playback error: {exc}")

    def music_stop(self):
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        self.music_player_state["playing"] = False
        self.music_player_state["paused"] = False
        self.music_player_state["progress"] = 0
        self.post_status("Playback stopped")

    def music_next_track(self):
        if not self.music_player_state["playlist"]:
            return
        self.music_player_state["current_track_index"] = (self.music_player_state["current_track_index"] + 1) % len(self.music_player_state["playlist"])
        self.music_player_state["paused"] = False
        self.music_player_state["playing"] = False
        self.music_player_state["current_file"] = self.music_player_state["playlist"][self.music_player_state["current_track_index"]]
        self.music_play_pause()

    def music_prev_track(self):
        if not self.music_player_state["playlist"]:
            return
        self.music_player_state["current_track_index"] = (self.music_player_state["current_track_index"] - 1) % len(self.music_player_state["playlist"])
        self.music_player_state["paused"] = False
        self.music_player_state["playing"] = False
        self.music_player_state["current_file"] = self.music_player_state["playlist"][self.music_player_state["current_track_index"]]
        self.music_play_pause()

    def set_music_volume(self, volume):
        volume = max(0, min(100, int(volume)))
        self.music_player_state["volume"] = volume
        try:
            pygame.mixer.music.set_volume(volume / 100)
        except Exception:
            pass

    def start_music_progress_tracking(self):
        def track_progress():
            while self.music_player_state["playing"]:
                try:
                    pos_ms = pygame.mixer.music.get_pos()
                    if pos_ms >= 0:
                        self.music_player_state["progress"] = pos_ms // 1000
                    if not pygame.mixer.music.get_busy() and not self.music_player_state["paused"]:
                        self.music_player_state["playing"] = False
                        if self.music_player_state["playlist"]:
                            self.music_next_track()
                        break
                except Exception:
                    break
                time.sleep(0.2)
        threading.Thread(target=track_progress, daemon=True).start()

    def normalize_terminal_path(self, raw_path):
        raw_path = raw_path.strip()
        if not raw_path:
            return Path(self.terminal_state["cwd"])
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = Path(self.terminal_state["cwd"]) / candidate
        try:
            resolved = candidate.resolve()
        except Exception:
            resolved = candidate
        return resolved

    def terminal_append_line(self, line):
        if line is None:
            return
        text = str(line).rstrip("\n")
        self.terminal_state["output"].append(text)
        self.terminal_state["output"] = self.terminal_state["output"][-240:]

    def execute_terminal_command(self, command):
        command = command.strip()
        self.terminal_append_line(f"{self.get_file_manager_display_path(Path(self.terminal_state['cwd']))} $ {command}")
        if not command:
            return
        history = self.terminal_state["history"]
        history.append(command)
        self.terminal_state["history_index"] = len(history)

        if command == "clear":
            self.terminal_state["output"] = []
            return
        if command == "pwd":
            self.terminal_append_line(self.terminal_state["cwd"])
            return
        if command == "help":
            self.terminal_append_line("Built-ins: help, clear, pwd, cd <dir>. Other commands run with subprocess.Popen in a worker thread.")
            return
        if command.startswith("cd"):
            target_raw = command[2:].strip() or str(self.user_files_dir)
            target = self.normalize_terminal_path(target_raw)
            if target.exists() and target.is_dir():
                self.terminal_state["cwd"] = str(target)
                self.terminal_append_line(f"cwd -> {target}")
            else:
                self.terminal_append_line(f"No such directory: {target_raw}")
            return

        self.terminal_state["running"] = True

        def worker():
            try:
                process = subprocess.Popen(
                    command,
                    cwd=self.terminal_state["cwd"],
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                assert process.stdout is not None
                for line in process.stdout:
                    self.terminal_append_line(line)
                process.wait(timeout=60)
                self.terminal_append_line(f"[exit {process.returncode}]")
            except Exception as exc:
                self.terminal_append_line(f"Command failed: {exc}")
            finally:
                self.terminal_state["running"] = False

        threading.Thread(target=worker, daemon=True).start()

    def complete_terminal_path(self):
        current = self.terminal_state["input"]
        if not current:
            return
        parts = current.split(" ")
        token = parts[-1]
        base_dir = Path(self.terminal_state["cwd"])
        search_dir = base_dir
        prefix = token
        if "/" in token or "\\" in token:
            candidate = self.normalize_terminal_path(token)
            search_dir = candidate.parent if candidate.parent.exists() else base_dir
            prefix = candidate.name
        try:
            matches = sorted([item for item in search_dir.iterdir() if item.name.lower().startswith(prefix.lower())], key=lambda p: (p.is_file(), p.name.lower()))
        except Exception:
            matches = []
        if not matches:
            return
        chosen = matches[0]
        replacement = chosen.name + ("/" if chosen.is_dir() else "")
        parts[-1] = replacement
        self.terminal_state["input"] = " ".join(parts)

    def handle_terminal_input(self, event):
        if event.key == pygame.K_RETURN:
            command = self.terminal_state["input"]
            self.terminal_state["input"] = ""
            self.execute_terminal_command(command)
        elif event.key == pygame.K_BACKSPACE:
            self.terminal_state["input"] = self.terminal_state["input"][:-1]
        elif event.key == pygame.K_TAB:
            self.complete_terminal_path()
        elif event.key == pygame.K_UP:
            history = self.terminal_state["history"]
            if history:
                self.terminal_state["history_index"] = max(0, self.terminal_state["history_index"] - 1)
                self.terminal_state["input"] = history[self.terminal_state["history_index"]]
        elif event.key == pygame.K_DOWN:
            history = self.terminal_state["history"]
            if history:
                self.terminal_state["history_index"] = min(len(history), self.terminal_state["history_index"] + 1)
                if self.terminal_state["history_index"] >= len(history):
                    self.terminal_state["input"] = ""
                else:
                    self.terminal_state["input"] = history[self.terminal_state["history_index"]]
        elif event.unicode and event.unicode.isprintable():
            self.terminal_state["input"] += event.unicode

    @staticmethod
    def format_size(size):
        if size < 1024:
            return f"{size} B"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size / (1024 * 1024):.1f} MB"

    @staticmethod
    def format_time(seconds):
        minutes, seconds = divmod(int(seconds), 60)
        return f"{minutes:02d}:{seconds:02d}"

    def handle_start_menu_click(self, pos, button=1):
        for rect, app_id in self.start_menu_item_rects:
            if rect.collidepoint(pos):
                if button == 3:
                    self.create_desktop_icon_for_app(app_id)
                else:
                    self.open_application(app_id)
                    self.start_menu_open = False
                return
        for action, rect in self.start_menu_action_rects.items():
            if rect.collidepoint(pos):
                if action == "exit":
                    pygame.quit()
                    sys.exit()
                self.open_application(action)
                self.start_menu_open = False
                return

    def handle_context_menu_click(self, pos):
        relative_y = pos[1] - self.context_menu_rect.y - 8
        if relative_y // 38 == 1:
            self.taskbar_position = "top" if self.taskbar_position == "bottom" else "bottom"
            self.save_config()
            self.post_status(f"Taskbar moved to {self.taskbar_position}")
        self.context_menu_open = False

    def handle_icon_context_menu_click(self, pos):
        if not self.icon_context_menu_open or not self.icon_context_menu_target:
            return False
        x, y = self.icon_context_menu_pos
        rect = pygame.Rect(min(x, self.width - 140), min(y, self.height - 110), 140, 110)
        if not rect.collidepoint(pos):
            return False
        item_index = (pos[1] - rect.y - 8) // 32
        if item_index == 0:
            self.open_application(self.icon_context_menu_target.app_id)
        elif item_index == 1:
            self.post_status("Icon rename is not implemented yet")
        elif item_index == 2:
            self.delete_icon(self.icon_context_menu_target)
        self.icon_context_menu_open = False
        return True

    def handle_taskbar_window_click(self, pos):
        if not self.windows:
            return False
        taskbar = self.get_taskbar_rect()
        start_rect = self.get_start_button_rect()
        available_start = start_rect.right + 10
        available_end = taskbar.right - self.system_tray_width - 12
        available_width = available_end - available_start
        if available_width <= 0:
            return False
        button_width = max(124, min(196, (available_width - max(0, len(self.windows) - 1) * 6) // len(self.windows)))
        x = available_start
        for window in self.windows:
            rect = pygame.Rect(x, taskbar.y + 8, button_width, taskbar.height - 16)
            if rect.collidepoint(pos):
                if window.minimized:
                    window.minimized = False
                self.active_window = window
                self.windows.remove(window)
                self.windows.append(window)
                return True
            x += button_width + 6
        return False

    def handle_icon_interactions(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN:
            return
        if event.button == 1:
            for icon in self.desktop_icons:
                icon.selected = False
            for icon in self.desktop_icons:
                if icon.handle_click(event.pos):
                    now = pygame.time.get_ticks()
                    icon.click_count = icon.click_count + 1 if now - icon.last_click_time < 500 else 1
                    icon.last_click_time = now
                    if icon.click_count == 2:
                        self.open_application(icon.app_id)
                        icon.click_count = 0
                        icon.selected = False
                    break
        elif event.button == 3:
            for icon in self.desktop_icons:
                if icon.handle_click(event.pos):
                    self.icon_context_menu_open = True
                    self.icon_context_menu_pos = event.pos
                    self.icon_context_menu_target = icon
                    self.start_menu_open = False
                    return

    def handle_window_interactions(self, event):
        for window in reversed(self.windows):
            if window.minimized:
                continue
            result = window.handle_event(event, self.width, self.height, self.taskbar_height + 20, self.taskbar_position)
            if result == "close":
                self.windows.remove(window)
                if self.active_window == window:
                    self.active_window = self.windows[-1] if self.windows else None
                return True
            if result in {"minimize", "maximize", "snap"}:
                return True
            if event.type == pygame.MOUSEBUTTONDOWN and window.rect.collidepoint(event.pos):
                if self.windows[-1] != window:
                    self.windows.remove(window)
                    self.windows.append(window)
                self.active_window = window
                callback = self.registered_apps.get(window.app_id, {}).get("on_click")
                if callable(callback):
                    callback(self, event.pos, window, event.button)
                return True
        return False

    def handle_active_window_key(self, event):
        if not self.active_window or self.active_window.minimized:
            return
        if self.active_window.app_id == "file_manager" and self.file_manager_state["renaming_file"]:
            self.handle_file_manager_input(event)
            return
        if self.active_window.app_id == "text_editor":
            self.handle_text_editor_input(event)
            return
        if self.active_window.app_id == "terminal":
            self.handle_terminal_input(event)
            return
        callback = self.registered_apps.get(self.active_window.app_id, {}).get("on_key")
        if callable(callback):
            callback(self, event, self.active_window)

    def run(self):
        running = True
        while running:
            mouse_pos = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    continue

                if not self.authenticated:
                    self.handle_login_event(event)
                    continue

                window_consumed = self.handle_window_interactions(event)
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if window_consumed and event.button == 1:
                        self.start_menu_open = False
                        self.context_menu_open = False
                        self.icon_context_menu_open = False
                    if not window_consumed:
                        self.handle_icon_interactions(event)
                    if event.button == 1:
                        if self.start_button_rect and self.start_button_rect.collidepoint(event.pos):
                            self.start_menu_open = not self.start_menu_open
                            self.context_menu_open = False
                            self.icon_context_menu_open = False
                        elif self.start_menu_open and self.start_menu_rect and self.start_menu_rect.collidepoint(event.pos):
                            self.handle_start_menu_click(event.pos)
                        elif self.context_menu_open and self.context_menu_rect and self.context_menu_rect.collidepoint(event.pos):
                            self.handle_context_menu_click(event.pos)
                        elif self.icon_context_menu_open and self.handle_icon_context_menu_click(event.pos):
                            pass
                        elif self.handle_taskbar_window_click(event.pos):
                            pass
                        else:
                            self.start_menu_open = False
                            self.context_menu_open = False
                            self.icon_context_menu_open = False
                    elif event.button == 3:
                        if self.start_menu_open and self.start_menu_rect and self.start_menu_rect.collidepoint(event.pos):
                            self.handle_start_menu_click(event.pos, 3)
                        else:
                            taskbar = self.get_taskbar_rect()
                            if taskbar.collidepoint(event.pos):
                                self.context_menu_open = True
                                self.context_menu_pos = event.pos
                                self.start_menu_open = False
                                self.icon_context_menu_open = False
                            else:
                                self.context_menu_open = False
                                self.icon_context_menu_open = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.start_menu_open = False
                        self.context_menu_open = False
                        self.icon_context_menu_open = False
                    elif event.key == pygame.K_F11:
                        patterns = ["gradient", "solid", "pattern"]
                        current = patterns.index(self.wallpaper_pattern) if self.wallpaper_pattern in patterns else 0
                        self.set_wallpaper_pattern(patterns[(current + 1) % len(patterns)])
                    else:
                        self.handle_active_window_key(event)

            self.draw_wallpaper()
            if self.authenticated:
                self.draw_desktop_icons()
                self.draw_windows()
                self.draw_taskbar()
                self.draw_start_button(mouse_pos)
                self.draw_window_list()
                self.draw_system_tray()
                self.draw_start_menu()
                self.draw_context_menu()
                self.draw_icon_context_menu()
                self.draw_status_bar()
            else:
                self.draw_login_screen()
            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    try:
        DesktopEnvironment().run()
    except KeyboardInterrupt:
        pygame.quit()
        sys.exit()
