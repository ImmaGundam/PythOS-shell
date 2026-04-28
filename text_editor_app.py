import pygame


def register():
    return {
        "id": "text_editor",
        "name": "Text Editor",
        "title": "Text Editor",
        "window_size": (680, 480),
        "default_position": (140, 120),
        "draw": draw,
        "on_click": on_click,
        "icon": {"shape": "rounded", "primary": (0, 133, 191), "accent": (220, 244, 255)},
        "show_on_desktop": True,
        "show_in_start_menu": True,
    }


def get_layout(content_rect):
    header_rect = pygame.Rect(content_rect.x, content_rect.y, content_rect.width, 34)
    text_rect = pygame.Rect(content_rect.x + 8, header_rect.bottom + 8, content_rect.width - 16, content_rect.height - 102)
    save_rect = pygame.Rect(content_rect.x + 10, content_rect.bottom - 42, 90, 28)
    clear_rect = pygame.Rect(save_rect.right + 10, save_rect.y, 90, 28)
    new_rect = pygame.Rect(clear_rect.right + 10, save_rect.y, 90, 28)
    return header_rect, text_rect, save_rect, clear_rect, new_rect


def draw(env, screen, content_rect, font, small_font, window):
    pygame.draw.rect(screen, (252, 252, 253), content_rect, border_radius=12)
    header_rect, text_rect, save_rect, clear_rect, new_rect = get_layout(content_rect)

    pygame.draw.rect(screen, (236, 240, 248), header_rect, border_radius=10)
    pygame.draw.rect(screen, (192, 200, 220), header_rect, 1, border_radius=10)
    hint_text = "Keyboard input goes here automatically while this window is active."
    hint_width = min(360, max(160, header_rect.width // 2))
    hint_x = header_rect.right - hint_width - 10
    env.draw_fit_text(f"Editing: {env.text_editor_state['filename']}", small_font, (28, 35, 49), (header_rect.x + 10, header_rect.y + 8), hint_x - header_rect.x - 20)
    env.draw_fit_text(hint_text, small_font, (96, 107, 132), (hint_x, header_rect.y + 8), hint_width)

    pygame.draw.rect(screen, (255, 255, 255), text_rect, border_radius=10)
    pygame.draw.rect(screen, (192, 200, 220), text_rect, 1, border_radius=10)

    lines = env.text_editor_state["content"].split("\n")
    start_line = env.text_editor_state["scroll_y"]
    line_height = 18
    max_lines = max(1, (text_rect.height - 12) // line_height)
    for index, line in enumerate(lines[start_line:start_line + max_lines]):
        env.draw_fit_text(line, small_font, (25, 31, 43), (text_rect.x + 10, text_rect.y + 8 + index * line_height), text_rect.width - 20)

    if pygame.time.get_ticks() % 900 < 450:
        cursor_line = max(0, len(lines) - 1 - start_line)
        cursor_x = text_rect.x + 10 + min(len(lines[-1]) * 7, text_rect.width - 24)
        cursor_y = text_rect.y + 8 + cursor_line * line_height
        if cursor_y < text_rect.bottom - 16:
            pygame.draw.line(screen, (30, 37, 54), (cursor_x, cursor_y), (cursor_x, cursor_y + 14), 1)

    env.draw_button(save_rect, "Save", small_font, fill=(92, 173, 110), outline=(57, 115, 68))
    env.draw_button(clear_rect, "Clear", small_font, fill=(219, 164, 97), outline=(151, 105, 48))
    env.draw_button(new_rect, "New", small_font, fill=(101, 145, 221), outline=(58, 88, 146))


def on_click(env, pos, window, button):
    if button != 1:
        return
    _, _, save_rect, clear_rect, new_rect = get_layout(window.get_content_rect())
    if save_rect.collidepoint(pos):
        env.save_text_file()
    elif clear_rect.collidepoint(pos):
        env.clear_text_editor()
    elif new_rect.collidepoint(pos):
        env.new_text_file()
