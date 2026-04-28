from pathlib import Path

import pygame


def register():
    return {
        "id": "music_player",
        "name": "MP3 Player",
        "title": "MP3 Player",
        "window_size": (460, 500),
        "default_position": (210, 130),
        "draw": draw,
        "on_click": on_click,
        "icon": {"shape": "note", "primary": (148, 72, 199), "accent": (239, 228, 255)},
        "show_on_desktop": True,
        "show_in_start_menu": True,
    }


def get_layout(content_rect):
    playlist_rect = pygame.Rect(content_rect.x + 14, content_rect.y + 64, content_rect.width - 28, 200)
    add_rect = pygame.Rect(content_rect.x + 14, playlist_rect.bottom + 14, 110, 30)
    play_rect = pygame.Rect(content_rect.x + 14, add_rect.bottom + 14, 90, 32)
    stop_rect = pygame.Rect(play_rect.right + 8, play_rect.y, 70, 32)
    prev_rect = pygame.Rect(stop_rect.right + 8, play_rect.y, 70, 32)
    next_rect = pygame.Rect(prev_rect.right + 8, play_rect.y, 70, 32)
    volume_rect = pygame.Rect(content_rect.x + 100, play_rect.bottom + 34, 220, 12)
    return playlist_rect, add_rect, play_rect, stop_rect, prev_rect, next_rect, volume_rect


def draw(env, screen, content_rect, font, small_font, window):
    pygame.draw.rect(screen, (31, 34, 46), content_rect, border_radius=14)
    title = font.render("Playlist", True, (255, 255, 255))
    subtitle_name = Path(env.music_player_state["current_file"]).name if env.music_player_state["current_file"] else "No track selected"
    subtitle = small_font.render(subtitle_name[:44], True, (190, 199, 225))
    screen.blit(title, (content_rect.x + 14, content_rect.y + 12))
    screen.blit(subtitle, (content_rect.x + 14, content_rect.y + 38))

    playlist_rect, add_rect, play_rect, stop_rect, prev_rect, next_rect, volume_rect = get_layout(content_rect)
    pygame.draw.rect(screen, (19, 22, 31), playlist_rect, border_radius=12)
    pygame.draw.rect(screen, (84, 92, 116), playlist_rect, 1, border_radius=12)

    if not env.music_player_state["playlist"]:
        empty = small_font.render("No music loaded yet. Use Add Files to build a playlist.", True, (153, 164, 193))
        screen.blit(empty, empty.get_rect(center=playlist_rect.center))
    else:
        for index, track in enumerate(env.music_player_state["playlist"][:8]):
            item_rect = pygame.Rect(playlist_rect.x + 8, playlist_rect.y + 8 + index * 22, playlist_rect.width - 16, 20)
            is_current = index == env.music_player_state["current_track_index"]
            if is_current:
                pygame.draw.rect(screen, (69, 88, 145), item_rect, border_radius=7)
            label = Path(track).name
            text = small_font.render(f"{index + 1}. {label[:38]}", True, (255, 255, 255) if is_current else (210, 216, 232))
            screen.blit(text, (item_rect.x + 6, item_rect.y + 3))

    env.draw_button(add_rect, "Add Files", small_font, fill=(74, 131, 89), outline=(46, 83, 56))
    env.draw_button(play_rect, "Pause" if env.music_player_state["playing"] else "Play", small_font, fill=(96, 115, 207), outline=(62, 76, 133))
    env.draw_button(stop_rect, "Stop", small_font, fill=(187, 92, 92), outline=(112, 51, 51))
    env.draw_button(prev_rect, "Prev", small_font, fill=(130, 103, 68), outline=(93, 70, 42))
    env.draw_button(next_rect, "Next", small_font, fill=(130, 103, 68), outline=(93, 70, 42))

    progress = small_font.render(
        f"Progress: {env.format_time(env.music_player_state['progress'])} / {env.format_time(env.music_player_state['total_length'])}",
        True,
        (190, 199, 225),
    )
    volume = small_font.render(f"Volume: {env.music_player_state['volume']}%", True, (190, 199, 225))
    screen.blit(progress, (content_rect.x + 14, play_rect.bottom + 10))
    screen.blit(volume, (content_rect.x + 14, volume_rect.y - 8))

    pygame.draw.rect(screen, (60, 66, 82), volume_rect, border_radius=6)
    pygame.draw.rect(screen, (87, 96, 122), volume_rect, 1, border_radius=6)
    fill_width = int(volume_rect.width * (env.music_player_state["volume"] / 100))
    pygame.draw.rect(screen, (111, 174, 233), pygame.Rect(volume_rect.x, volume_rect.y, fill_width, volume_rect.height), border_radius=6)


def on_click(env, pos, window, button):
    if button != 1:
        return
    _, add_rect, play_rect, stop_rect, prev_rect, next_rect, volume_rect = get_layout(window.get_content_rect())
    if add_rect.collidepoint(pos):
        env.open_music_file_dialog()
    elif play_rect.collidepoint(pos):
        env.music_play_pause()
    elif stop_rect.collidepoint(pos):
        env.music_stop()
    elif prev_rect.collidepoint(pos):
        env.music_prev_track()
    elif next_rect.collidepoint(pos):
        env.music_next_track()
    elif volume_rect.collidepoint(pos):
        env.set_music_volume(((pos[0] - volume_rect.x) / max(1, volume_rect.width)) * 100)
