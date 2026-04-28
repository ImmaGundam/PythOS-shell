
import pygame


def register():
    return {
        "id": "terminal",
        "name": "Terminal",
        "title": "System Terminal",
        "window_size": (760, 500),
        "default_position": (180, 120),
        "draw": draw,
        "on_key": on_key,
        "icon": {"shape": "rounded", "primary": (46, 196, 110), "accent": (220, 255, 232)},
        "show_on_desktop": True,
        "show_in_start_menu": True,
        "system_app": True,
        "removable": False,
    }


def get_layout(content_rect):
    header_rect = pygame.Rect(content_rect.x, content_rect.y, content_rect.width, 42)
    output_rect = pygame.Rect(content_rect.x + 10, header_rect.bottom + 8, content_rect.width - 20, content_rect.height - 120)
    input_rect = pygame.Rect(content_rect.x + 10, output_rect.bottom + 12, content_rect.width - 20, 36)
    return header_rect, output_rect, input_rect


def draw(env, screen, content_rect, font, small_font, window):
    panel_surface = pygame.Surface((content_rect.width, content_rect.height), pygame.SRCALPHA)
    pygame.draw.rect(panel_surface, (12, 16, 24, 230), panel_surface.get_rect(), border_radius=18)
    pygame.draw.rect(panel_surface, (90, 117, 138, 120), panel_surface.get_rect(), 1, border_radius=18)
    screen.blit(panel_surface, content_rect.topleft)

    header_rect, output_rect, input_rect = get_layout(content_rect)
    env.draw_panel(header_rect, (23, 29, 42, 220), (115, 136, 164, 120), 14)
    title = font.render("Terminal", True, (236, 242, 249))
    env.draw_fit_text(f"cwd: {env.terminal_state['cwd']}", small_font, (164, 180, 196), (header_rect.x + 110, header_rect.y + 11), header_rect.width - 122)
    screen.blit(title, (header_rect.x + 12, header_rect.y + 8))

    env.draw_panel(output_rect, (8, 12, 19, 238), (115, 136, 164, 60), 16)
    old_clip = screen.get_clip()
    screen.set_clip(output_rect.inflate(-10, -10))
    lines = env.terminal_state["output"][-200:]
    line_height = 18
    max_lines = max(1, (output_rect.height - 16) // line_height)
    visible = lines[-max_lines:]
    for index, line in enumerate(visible):
        color = (196, 245, 206) if "$ " in line else (214, 223, 235)
        if line.startswith("[exit"):
            color = (147, 197, 253)
        if line.startswith("Command failed") or line.startswith("No such"):
            color = (248, 161, 161)
        rendered = small_font.render(str(line)[:120], True, color)
        screen.blit(rendered, (output_rect.x + 12, output_rect.y + 10 + index * line_height))
    screen.set_clip(old_clip)

    env.draw_panel(input_rect, (19, 25, 35, 230), (115, 136, 164, 100), 14)
    prompt = small_font.render("> " + env.terminal_state["input"], True, (246, 250, 255))
    screen.blit(prompt, (input_rect.x + 12, input_rect.y + 10))
    if pygame.time.get_ticks() % 900 < 450:
        cursor_x = input_rect.x + 12 + prompt.get_width()
        pygame.draw.line(screen, (255, 255, 255), (cursor_x, input_rect.y + 8), (cursor_x, input_rect.bottom - 8), 1)

    footer = small_font.render("Enter = run · Up/Down = history · Tab = complete", True, (161, 174, 193))
    screen.blit(footer, (content_rect.x + 12, content_rect.bottom - 20))


def on_key(env, event, window):
    env.handle_terminal_input(event)
