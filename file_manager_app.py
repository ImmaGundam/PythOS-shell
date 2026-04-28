from pathlib import Path

import pygame


TOOLBAR_ITEMS = [
    ("Import", (92, 140, 215)),
    ("Up", (116, 129, 171)),
    ("New File", (98, 173, 111)),
    ("New Folder", (84, 175, 175)),
    ("Open", (129, 143, 214)),
    ("Rename", (221, 176, 101)),
    ("Delete", (202, 101, 101)),
    ("Refresh", (140, 146, 162)),
]


def register():
    return {
        "id": "file_manager",
        "name": "File Manager",
        "title": "File Manager",
        "window_size": (820, 560),
        "default_position": (160, 100),
        "draw": draw,
        "on_click": on_click,
        "icon": {"shape": "folder", "primary": (232, 179, 60), "accent": (255, 242, 203)},
        "show_on_desktop": True,
        "show_in_start_menu": True,
        "system_app": True,
        "removable": False,
    }


def get_layout(content_rect):
    toolbar_rect = pygame.Rect(content_rect.x, content_rect.y, content_rect.width, 44)
    path_rect = pygame.Rect(content_rect.x + 10, toolbar_rect.bottom + 8, content_rect.width - 20, 30)
    sidebar_rect = pygame.Rect(content_rect.x + 10, path_rect.bottom + 10, 168, content_rect.height - 108)
    list_rect = pygame.Rect(sidebar_rect.right + 10, path_rect.bottom + 10, content_rect.right - sidebar_rect.right - 20, content_rect.height - 108)
    buttons = []
    x = toolbar_rect.x + 8
    for label, _ in TOOLBAR_ITEMS:
        rect = pygame.Rect(x, toolbar_rect.y + 8, 90, 28)
        buttons.append((rect, label))
        x += 96
    return toolbar_rect, path_rect, sidebar_rect, list_rect, buttons


def draw(env, screen, content_rect, font, small_font, window):
    pygame.draw.rect(screen, (246, 247, 250), content_rect)
    toolbar_rect, path_rect, sidebar_rect, list_rect, buttons = get_layout(content_rect)

    pygame.draw.rect(screen, (233, 237, 244), toolbar_rect)
    pygame.draw.rect(screen, (194, 202, 222), toolbar_rect, 1)

    selected = env.file_manager_state["selected_file"]
    for (rect, label), (_, fill) in zip(buttons, TOOLBAR_ITEMS):
        disabled = label in {"Open", "Rename", "Delete"} and not selected
        disabled = disabled or (selected and selected.get("is_navigation") and label in {"Rename", "Delete"})
        actual_fill = (177, 182, 191) if disabled else fill
        env.draw_button(rect, label, small_font, fill=actual_fill, outline=(96, 103, 119), text_color=(255, 255, 255))

    pygame.draw.rect(screen, (255, 255, 255), path_rect)
    pygame.draw.rect(screen, (194, 202, 222), path_rect, 1)
    env.draw_fit_text(f"Location: {env.get_file_manager_display_path()}", small_font, (41, 49, 64), (path_rect.x + 10, path_rect.y + 7), path_rect.width - 20)

    pygame.draw.rect(screen, (255, 255, 255), sidebar_rect)
    pygame.draw.rect(screen, (194, 202, 222), sidebar_rect, 1)
    screen.blit(font.render("Places", True, (31, 40, 56)), (sidebar_rect.x + 10, sidebar_rect.y + 10))

    current_dir = env.get_file_manager_current_dir()
    places = env.get_file_manager_places()
    for index, place in enumerate(places):
        row_rect = pygame.Rect(sidebar_rect.x + 8, sidebar_rect.y + 40 + index * 30, sidebar_rect.width - 16, 24)
        is_current = Path(place["path"]).resolve() == current_dir.resolve()
        if is_current:
            pygame.draw.rect(screen, (214, 227, 255), row_rect)
        env.draw_fit_text(place["label"], small_font, (37, 46, 60), (row_rect.x + 8, row_rect.y + 4), row_rect.width - 16)

    pygame.draw.rect(screen, (255, 255, 255), list_rect)
    pygame.draw.rect(screen, (194, 202, 222), list_rect, 1)
    header_rect = pygame.Rect(list_rect.x + 6, list_rect.y + 6, list_rect.width - 12, 24)
    pygame.draw.rect(screen, (235, 239, 246), header_rect)
    screen.blit(small_font.render("Name", True, (43, 52, 69)), (header_rect.x + 10, header_rect.y + 4))
    screen.blit(small_font.render("Type", True, (43, 52, 69)), (header_rect.right - 268, header_rect.y + 4))
    screen.blit(small_font.render("Modified", True, (43, 52, 69)), (header_rect.right - 184, header_rect.y + 4))
    screen.blit(small_font.render("Size", True, (43, 52, 69)), (header_rect.right - 68, header_rect.y + 4))

    files = env.file_manager_state["files"]
    if not files:
        empty = small_font.render("This folder is empty.", True, (124, 132, 151))
        screen.blit(empty, empty.get_rect(center=list_rect.center))
    else:
        visible_rows = max(1, (list_rect.height - 40) // 26)
        for index, file_info in enumerate(files[:visible_rows]):
            row_rect = pygame.Rect(list_rect.x + 6, list_rect.y + 34 + index * 26, list_rect.width - 12, 22)
            if file_info == selected:
                pygame.draw.rect(screen, (220, 232, 255), row_rect)
            prefix = ".." if file_info.get("is_navigation") else ("[DIR]" if file_info["is_folder"] else "[FILE]")
            name = file_info["name"]
            if env.file_manager_state["renaming_file"] == file_info:
                suffix = Path(file_info["path"]).suffix if not file_info["is_folder"] else ""
                edit_text = env.file_manager_state["rename_text"]
                visible_suffix = "" if suffix and edit_text.lower().endswith(suffix.lower()) else suffix
                name = edit_text + visible_suffix + "|"
            type_text = "Folder" if file_info["is_folder"] else file_info["type"].title()
            modified = file_info["modified"] or "--"
            size_text = "" if file_info["is_folder"] else env.format_size(file_info["size"])
            kind_x = row_rect.right - 268
            modified_x = row_rect.right - 184
            size_right = row_rect.right - 12
            env.draw_fit_text(f"{prefix} {name}", small_font, (27, 34, 46), (row_rect.x + 8, row_rect.y + 3), kind_x - row_rect.x - 18)
            env.draw_fit_text(type_text, small_font, (98, 108, 126), (kind_x, row_rect.y + 3), modified_x - kind_x - 8)
            env.draw_fit_text(modified, small_font, (98, 108, 126), (modified_x, row_rect.y + 3), size_right - modified_x - 74)
            size_surface = small_font.render(env.fit_text(size_text, small_font, 58), True, (98, 108, 126))
            screen.blit(size_surface, (size_right - size_surface.get_width(), row_rect.y + 3))

    env.draw_fit_text(
        f"Items: {len(files)}    Root: {env.get_file_manager_display_path(env.file_manager_root)}",
        small_font,
        (98, 107, 126),
        (content_rect.x + 10, content_rect.bottom - 24),
        content_rect.width - 20,
    )


def on_click(env, pos, window, button):
    toolbar_rect, path_rect, sidebar_rect, list_rect, buttons = get_layout(window.get_content_rect())
    if button == 1:
        for rect, label in buttons:
            if rect.collidepoint(pos):
                if label == "Import":
                    env.import_file_into_system()
                elif label == "Up":
                    env.navigate_file_manager_up()
                elif label == "New File":
                    env.create_new_file()
                elif label == "New Folder":
                    env.create_new_folder()
                elif label == "Open" and env.file_manager_state["selected_file"]:
                    env.open_file_in_editor(env.file_manager_state["selected_file"])
                elif label == "Rename" and env.file_manager_state["selected_file"]:
                    env.start_rename_file(env.file_manager_state["selected_file"])
                elif label == "Delete" and env.file_manager_state["selected_file"]:
                    env.delete_file(env.file_manager_state["selected_file"])
                elif label == "Refresh":
                    env.refresh_file_manager()
                    env.post_status("File manager refreshed")
                return

        if sidebar_rect.collidepoint(pos):
            index = (pos[1] - sidebar_rect.y - 40) // 30
            places = env.get_file_manager_places()
            if 0 <= index < len(places):
                env.set_file_manager_directory(places[index]["path"])
            return

    if path_rect.collidepoint(pos):
        return
    if not list_rect.collidepoint(pos):
        return

    index = (pos[1] - list_rect.y - 34) // 26
    if 0 <= index < len(env.file_manager_state["files"]):
        clicked = env.file_manager_state["files"][index]
        previous = env.file_manager_state["selected_file"]
        env.file_manager_state["selected_file"] = clicked
        if button == 1:
            now = pygame.time.get_ticks()
            same_item = previous and previous["path"] == clicked["path"]
            if same_item and now - env.file_manager_state["last_click_time"] < 450:
                env.open_file_in_editor(clicked)
            env.file_manager_state["last_click_path"] = clicked["path"]
            env.file_manager_state["last_click_time"] = now
        elif env.file_manager_state["renaming_file"] and env.file_manager_state["renaming_file"] != clicked:
            env.cancel_rename()
