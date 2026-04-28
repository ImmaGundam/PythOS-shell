import pygame


def register():
    return {
        "id": "about",
        "name": "About",
        "title": "About PythOS Shell",
        "window_size": (560, 380),
        "default_position": (250, 150),
        "draw": draw,
        "icon": {"shape": "rounded", "primary": (73, 110, 178), "accent": (225, 234, 252)},
        "show_in_start_menu": False,
        "show_on_desktop": False,
        "system_app": True,
        "removable": False,
    }


def draw(env, screen, content_rect, font, small_font, window):
    env.draw_panel(content_rect, (248, 250, 253, 232), (255, 255, 255, 120), 18)

    env.draw_fit_text(
        "PythOS Shell",
        env.large_font,
        (27, 34, 46),
        (content_rect.x + 18, content_rect.y + 20),
        content_rect.width - 36,
    )

    subtitle_y = content_rect.y + 58
    env.draw_fit_text(
        "A modular pygame desktop shell with Gatekeeper login.",
        font,
        (67, 78, 101),
        (content_rect.x + 18, subtitle_y),
        content_rect.width - 36,
    )
    env.draw_fit_text(
        "Includes a threaded terminal and modular Python app loading.",
        font,
        (67, 78, 101),
        (content_rect.x + 18, subtitle_y + 24),
        content_rect.width - 36,
    )

    lines = [
        "Built-in apps are module-based and loaded through register() manifests.",
        "Gatekeeper blocks the desktop until a SHA-256 password check succeeds.",
        "User text files use lightweight session-based file transformation inside the user root.",
        "The Terminal runs shell commands on worker threads so the UI stays responsive.",
        "Window dragging supports edge snapping similar to standard desktop shells.",
    ]
    y = content_rect.y + 124
    for line in lines:
        y = env.draw_wrapped_text(
            line,
            small_font,
            (48, 56, 74),
            pygame.Rect(content_rect.x + 20, y, content_rect.width - 40, 36),
            line_spacing=2,
            max_lines=2,
        ) + 10
