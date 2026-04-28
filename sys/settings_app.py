
import pygame


SECTIONS = [
    ("personalization", "Personalization", "Wallpaper and desktop appearance"),
    ("apps", "App Loader", "Import, remove, and pin applications"),
    ("system", "System", "Storage roots and auth status.\nBridge telemetry overview."),
]


def register():
    return {
        "id": "settings",
        "name": "Settings",
        "title": "System Settings",
        "window_size": (760, 520),
        "default_position": (240, 140),
        "draw": draw,
        "on_click": on_click,
        "on_open": on_open,
        "icon": {"shape": "gear", "primary": (88, 98, 110), "accent": (225, 232, 240)},
        "show_on_desktop": True,
        "show_in_start_menu": True,
        "system_app": True,
        "removable": False,
    }


def on_open(env, window):
    env.settings_state["section"] = "home"


def get_home_layout(content_rect):
    header_rect = pygame.Rect(content_rect.x + 16, content_rect.y + 16, content_rect.width - 32, 84)
    cards = []
    card_width = (content_rect.width - 56) // 3
    for index, (section_id, title, subtitle) in enumerate(SECTIONS):
        rect = pygame.Rect(content_rect.x + 16 + index * (card_width + 12), header_rect.bottom + 18, card_width, 190)
        cards.append((rect, section_id, title, subtitle))
    return header_rect, cards


def get_section_header(content_rect, title, subtitle):
    header_rect = pygame.Rect(content_rect.x + 16, content_rect.y + 16, content_rect.width - 32, 62)
    back_rect = pygame.Rect(header_rect.x + 12, header_rect.y + 15, 78, 28)
    title_pos = (back_rect.right + 16, header_rect.y + 9)
    subtitle_pos = (back_rect.right + 16, header_rect.y + 33)
    return header_rect, back_rect, title_pos, subtitle_pos, title, subtitle


def get_personalization_layout(content_rect):
    header = get_section_header(content_rect, "Personalization", "Change wallpaper and desktop appearance")
    panel_rect = pygame.Rect(content_rect.x + 16, content_rect.y + 94, content_rect.width - 32, content_rect.height - 110)
    buttons = {
        "image": pygame.Rect(panel_rect.x + 18, panel_rect.y + 54, 132, 30),
        "gradient": pygame.Rect(panel_rect.x + 18, panel_rect.y + 92, 132, 30),
        "solid": pygame.Rect(panel_rect.x + 18, panel_rect.y + 130, 132, 30),
        "pattern": pygame.Rect(panel_rect.x + 18, panel_rect.y + 168, 132, 30),
    }
    preview_rect = pygame.Rect(panel_rect.right - 240, panel_rect.y + 18, 220, 156)
    return header, panel_rect, buttons, preview_rect


def get_app_loader_layout(content_rect):
    header = get_section_header(content_rect, "App Loader", "Import Python modules and manage where apps appear")
    panel_rect = pygame.Rect(content_rect.x + 16, content_rect.y + 94, content_rect.width - 32, content_rect.height - 110)
    list_rect = pygame.Rect(panel_rect.x + 14, panel_rect.y + 58, panel_rect.width - 28, panel_rect.height - 120)
    buttons = {
        "import_app": pygame.Rect(panel_rect.x + 14, panel_rect.bottom - 42, 104, 28),
        "remove_app": pygame.Rect(panel_rect.x + 126, panel_rect.bottom - 42, 104, 28),
        "toggle_desktop": pygame.Rect(panel_rect.x + 238, panel_rect.bottom - 42, 104, 28),
        "toggle_start": pygame.Rect(panel_rect.x + 350, panel_rect.bottom - 42, 92, 28),
    }
    return header, panel_rect, list_rect, buttons


def get_system_layout(content_rect):
    header = get_section_header(content_rect, "System", "View storage roots, auth state, and Linux bridge polling")
    panel_rect = pygame.Rect(content_rect.x + 16, content_rect.y + 94, content_rect.width - 32, content_rect.height - 110)
    open_files_rect = pygame.Rect(panel_rect.x + 18, panel_rect.bottom - 42, 132, 28)
    terminal_rect = pygame.Rect(open_files_rect.right + 12, open_files_rect.y, 132, 28)
    about_rect = pygame.Rect(terminal_rect.right + 12, open_files_rect.y, 132, 28)
    return header, panel_rect, open_files_rect, terminal_rect, about_rect


def draw(env, screen, content_rect, font, small_font, window):
    env.draw_panel(content_rect, (246, 248, 251, 232), (255, 255, 255, 120), 18)
    section = env.settings_state.get("section", "home")
    if section == "personalization":
        draw_personalization(env, screen, content_rect, font, small_font)
    elif section == "apps":
        draw_app_loader(env, screen, content_rect, font, small_font)
    elif section == "system":
        draw_system(env, screen, content_rect, font, small_font)
    else:
        draw_home(env, screen, content_rect, font, small_font)


def draw_home(env, screen, content_rect, font, small_font):
    header_rect, cards = get_home_layout(content_rect)
    env.draw_panel(header_rect, (231, 238, 248, 220), (255, 255, 255, 120), 18)
    title = env.large_font.render("Settings", True, (27, 34, 46))
    screen.blit(title, (header_rect.x + 16, header_rect.y + 14))
    env.draw_fit_text("Choose a category to open its controls.", small_font, (91, 101, 124), (header_rect.x + 18, header_rect.y + 48), header_rect.width - 36)

    for rect, section_id, title_text, subtitle_text in cards:
        env.draw_panel(rect, (255, 255, 255, 230), (255, 255, 255, 120), 18)
        accent = {
            "personalization": (95, 143, 215),
            "apps": (90, 160, 105),
            "system": (118, 127, 168),
        }[section_id]
        band = pygame.Rect(rect.x + 10, rect.y + 10, rect.width - 20, 42)
        env.draw_button(band, title_text, font, fill=accent, outline=accent, radius=14)
        subtitle_y = rect.y + 66
        for paragraph in str(subtitle_text).split("\n"):
            subtitle_y = env.draw_wrapped_text(
                paragraph,
                small_font,
                (61, 70, 88),
                pygame.Rect(rect.x + 12, subtitle_y, rect.width - 24, 34),
                line_spacing=2,
                max_lines=1,
            ) + 2
        env.draw_fit_text("Click to open", small_font, accent, (rect.x + 12, rect.bottom - 28), rect.width - 24)


def draw_section_header(env, screen, header_parts, font, small_font):
    header_rect, back_rect, title_pos, subtitle_pos, title, subtitle = header_parts
    env.draw_panel(header_rect, (231, 238, 248, 220), (255, 255, 255, 120), 18)
    env.draw_button(back_rect, "Back", small_font, fill=(110, 122, 149), outline=(80, 91, 114))
    max_width = header_rect.right - title_pos[0] - 14
    env.draw_fit_text(title, font, (27, 34, 46), title_pos, max_width)
    env.draw_fit_text(subtitle, small_font, (91, 101, 124), subtitle_pos, max_width)


def draw_personalization(env, screen, content_rect, font, small_font):
    header_parts, panel_rect, buttons, preview_rect = get_personalization_layout(content_rect)
    draw_section_header(env, screen, header_parts, font, small_font)
    env.draw_panel(panel_rect, (255, 255, 255, 230), (255, 255, 255, 120), 18)
    screen.blit(font.render("Wallpaper", True, (27, 34, 46)), (panel_rect.x + 18, panel_rect.y + 18))
    env.draw_button(buttons["image"], "Change Image", small_font, fill=(92, 137, 211), outline=(57, 86, 133))
    env.draw_button(buttons["gradient"], "Gradient", small_font, fill=(84, 123, 191), outline=(52, 77, 121))
    env.draw_button(buttons["solid"], "Solid Color", small_font, fill=(95, 152, 120), outline=(57, 95, 70))
    env.draw_button(buttons["pattern"], "Pattern", small_font, fill=(178, 133, 83), outline=(114, 81, 48))

    env.draw_panel(preview_rect, (235, 240, 247, 220), (255, 255, 255, 120), 18)
    env.draw_fit_text("Current Wallpaper", small_font, (70, 80, 102), (preview_rect.x + 12, preview_rect.y + 12), preview_rect.width - 24)
    env.draw_fit_text(env.wallpaper_pattern.title(), font, (31, 40, 56), (preview_rect.x + 12, preview_rect.y + 40), preview_rect.width - 24)
    env.draw_wrapped_text(
        "Desktop keeps the current shell layout.",
        small_font,
        (94, 104, 126),
        pygame.Rect(preview_rect.x + 12, preview_rect.bottom - 44, preview_rect.width - 24, 34),
        line_spacing=2,
        max_lines=2,
    )


def draw_app_loader(env, screen, content_rect, font, small_font):
    header_parts, panel_rect, list_rect, buttons = get_app_loader_layout(content_rect)
    draw_section_header(env, screen, header_parts, font, small_font)
    env.draw_panel(panel_rect, (255, 255, 255, 230), (255, 255, 255, 120), 18)
    screen.blit(font.render("Installed Applications", True, (27, 34, 46)), (panel_rect.x + 14, panel_rect.y + 18))
    env.draw_fit_text("Import Python modules, remove imported apps, and pin them where you want.", small_font, (91, 101, 124), (panel_rect.x + 14, panel_rect.y + 38), panel_rect.width - 28)

    env.draw_panel(list_rect, (249, 250, 252, 230), (255, 255, 255, 110), 16)

    apps = env.get_managed_apps()
    for index, app in enumerate(apps[:10]):
        item_rect = pygame.Rect(list_rect.x + 8, list_rect.y + 8 + index * 30, list_rect.width - 16, 26)
        selected = app["id"] == env.settings_state.get("selected_app_id")
        if selected:
            env.draw_panel(item_rect, (214, 227, 255, 220), (255, 255, 255, 110), 12)
        meta = "System" if app["system_app"] else "Imported"
        pins = []
        if app["show_on_desktop"]:
            pins.append("Desktop")
        if app["show_in_start_menu"]:
            pins.append("Start")
        pin_text = ", ".join(pins) if pins else "Hidden"
        detail = small_font.render(pin_text, True, (95, 106, 130))
        detail_x = item_rect.right - detail.get_width() - 8
        env.draw_fit_text(f"{app['name']}  [{meta}]", small_font, (27, 34, 46), (item_rect.x + 8, item_rect.y + 5), detail_x - item_rect.x - 16)
        screen.blit(detail, (detail_x, item_rect.y + 5))

    env.draw_button(buttons["import_app"], "Import App", small_font, fill=(86, 137, 218), outline=(54, 87, 139))
    env.draw_button(buttons["remove_app"], "Remove App", small_font, fill=(197, 97, 97), outline=(118, 55, 55))
    env.draw_button(buttons["toggle_desktop"], "Desktop", small_font, fill=(96, 171, 116), outline=(59, 103, 68))
    env.draw_button(buttons["toggle_start"], "Start", small_font, fill=(121, 130, 196), outline=(76, 82, 121))


def draw_system(env, screen, content_rect, font, small_font):
    header_parts, panel_rect, open_files_rect, terminal_rect, about_rect = get_system_layout(content_rect)
    draw_section_header(env, screen, header_parts, font, small_font)
    env.draw_panel(panel_rect, (255, 255, 255, 230), (255, 255, 255, 120), 18)

    managed_apps = env.get_managed_apps()
    imported_count = len([app for app in managed_apps if app["source"] == "imported"])
    usb_summary = ", ".join(env.system_state["usb_devices"][:2]) if env.system_state["usb_devices"] else "None detected"
    lines = [
        f"Authenticated: {'Yes' if env.authenticated else 'No'}",
        f"System apps: {len([app for app in managed_apps if app['system_app']])}",
        f"Imported apps: {imported_count}",
        f"File root: {env.get_file_manager_display_path(env.file_manager_root)}",
        f"User files folder: {env.user_files_dir.name}",
        f"Installed apps folder: {env.installed_apps_dir.name}",
        f"Network: {env.system_state['network_name']}",
        f"Battery: {env.system_state['battery']}",
        f"USB mounts: {usb_summary}",
    ]

    screen.blit(font.render("Shell Information", True, (27, 34, 46)), (panel_rect.x + 18, panel_rect.y + 18))
    for index, line in enumerate(lines):
        env.draw_fit_text(line, small_font, (57, 67, 85), (panel_rect.x + 20, panel_rect.y + 58 + index * 26), panel_rect.width - 40)

    env.draw_button(open_files_rect, "Open Files", small_font, fill=(94, 137, 210), outline=(59, 86, 130))
    env.draw_button(terminal_rect, "Terminal", small_font, fill=(86, 151, 105), outline=(57, 99, 68))
    env.draw_button(about_rect, "About", small_font, fill=(119, 129, 155), outline=(83, 92, 113))


def on_click(env, pos, window, button):
    if button != 1:
        return

    section = env.settings_state.get("section", "home")
    content_rect = window.get_content_rect()
    if section == "home":
        _, cards = get_home_layout(content_rect)
        for rect, section_id, _, _ in cards:
            if rect.collidepoint(pos):
                env.settings_state["section"] = section_id
                return
        return

    if section == "personalization":
        header_parts, _, buttons, _ = get_personalization_layout(content_rect)
        if header_parts[1].collidepoint(pos):
            env.settings_state["section"] = "home"
        elif buttons["image"].collidepoint(pos):
            env.open_background_selector()
        elif buttons["gradient"].collidepoint(pos):
            env.set_wallpaper_pattern("gradient")
        elif buttons["solid"].collidepoint(pos):
            env.set_wallpaper_pattern("solid")
        elif buttons["pattern"].collidepoint(pos):
            env.set_wallpaper_pattern("pattern")
        return

    if section == "apps":
        header_parts, _, list_rect, buttons = get_app_loader_layout(content_rect)
        if header_parts[1].collidepoint(pos):
            env.settings_state["section"] = "home"
        elif buttons["import_app"].collidepoint(pos):
            env.import_python_app()
        elif buttons["remove_app"].collidepoint(pos):
            env.remove_selected_app()
        elif buttons["toggle_desktop"].collidepoint(pos):
            env.toggle_selected_app_desktop()
        elif buttons["toggle_start"].collidepoint(pos):
            env.toggle_selected_app_start()
        elif list_rect.collidepoint(pos):
            index = (pos[1] - list_rect.y - 8) // 30
            apps = env.get_managed_apps()
            if 0 <= index < len(apps):
                env.settings_state["selected_app_id"] = apps[index]["id"]
        return

    if section == "system":
        header_parts, _, open_files_rect, terminal_rect, about_rect = get_system_layout(content_rect)
        if header_parts[1].collidepoint(pos):
            env.settings_state["section"] = "home"
        elif open_files_rect.collidepoint(pos):
            env.open_application("file_manager")
        elif terminal_rect.collidepoint(pos):
            env.open_application("terminal")
        elif about_rect.collidepoint(pos):
            env.open_application("about")
