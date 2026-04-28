
import pygame


BUTTON_ROWS = [
    ["C", "CE", "BACK", "/"],
    ["7", "8", "9", "*"],
    ["4", "5", "6", "-"],
    ["1", "2", "3", "+"],
    ["0", ".", "="],
]


def register():
    return {
        "id": "calculator",
        "name": "Calculator",
        "title": "Calculator",
        "window_size": (330, 430),
        "default_position": (90, 90),
        "draw": draw,
        "on_click": on_click,
        "icon": {"shape": "rounded", "primary": (67, 131, 245), "accent": (225, 236, 255)},
        "show_on_desktop": True,
        "show_in_start_menu": True,
    }


def get_button_rects(content_rect):
    display_rect = pygame.Rect(content_rect.x + 16, content_rect.y + 16, content_rect.width - 32, 72)
    rects = []
    start_x = content_rect.x + 16
    start_y = display_rect.bottom + 18
    spacing = 10
    button_w = (content_rect.width - 32 - spacing * 3) // 4
    remaining_height = content_rect.bottom - start_y - 16
    button_h = max(40, (remaining_height - spacing * 4) // 5)
    for row_index, row in enumerate(BUTTON_ROWS):
        col = 0
        for label in row:
            is_wide_zero = label == "0" and row_index == 4
            width = button_w * 2 + spacing if is_wide_zero else button_w
            rect = pygame.Rect(
                start_x + col * (button_w + spacing),
                start_y + row_index * (button_h + spacing),
                width,
                button_h,
            )
            rects.append((rect, label))
            col += 2 if is_wide_zero else 1
    return display_rect, rects


def draw(env, screen, content_rect, font, small_font, window):
    env.draw_panel(content_rect, (242, 244, 247, 232), (255, 255, 255, 120), 18)
    display_rect, button_rects = get_button_rects(content_rect)

    env.draw_panel(display_rect, (255, 255, 255, 235), (225, 232, 245, 160), 16)
    op_text = env.calculator_state["operation"] or ""
    op_surface = small_font.render(op_text, True, (116, 126, 145))
    screen.blit(op_surface, (display_rect.x + 14, display_rect.y + 12))

    display_surface = env.large_font.render(env.calculator_state["display"], True, (34, 42, 56))
    display_pos = display_surface.get_rect(right=display_rect.right - 16, bottom=display_rect.bottom - 14)
    screen.blit(display_surface, display_pos)

    for rect, label in button_rects:
        if label == "=":
            fill = (87, 151, 237)
            outline = (53, 97, 153)
            text_color = (255, 255, 255)
        elif label in {"+", "-", "*", "/"}:
            fill = (227, 234, 246)
            outline = (183, 192, 210)
            text_color = (28, 35, 49)
        elif label in {"C", "CE", "BACK"}:
            fill = (234, 237, 242)
            outline = (191, 198, 210)
            text_color = (28, 35, 49)
        else:
            fill = (255, 255, 255)
            outline = (194, 202, 218)
            text_color = (28, 35, 49)
        text = "<-" if label == "BACK" else label
        env.draw_button(rect, text, font, fill=fill, outline=outline, text_color=text_color, radius=14)


def on_click(env, pos, window, button):
    if button != 1:
        return
    _, button_rects = get_button_rects(window.get_content_rect())
    for rect, label in button_rects:
        if rect.collidepoint(pos):
            env.calculator_button_pressed(label)
            return
