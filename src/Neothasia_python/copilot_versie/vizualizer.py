import pygame

WHITE_KEYS = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
BLACK_KEYS = ['C#', 'D#', 'F#', 'G#', 'A#']
KEY_WIDTH = 20
KEY_HEIGHT = 100
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

def init_visualizer():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Neothasia_pythonV1")
    clock = pygame.time.Clock()
    return screen, clock

def draw_piano(screen, active_notes):
    for i in range(14):
        key_color = (255, 255, 255) if i % 2 == 0 else (0, 0, 0)
        if i in active_notes:
            key_color = (255, 255, 0)
        pygame.draw.rect(screen, key_color, (i * KEY_WIDTH, SCREEN_HEIGHT - KEY_HEIGHT, KEY_WIDTH, KEY_HEIGHT))
        label = WHITE_KEYS[i % len(WHITE_KEYS)] if key_color == (255, 255, 255) else BLACK_KEYS[i % len(BLACK_KEYS)]
        font = pygame.font.Font(None, 24)
        text = font.render(label, True, (0, 0, 0) if key_color == (255, 255, 255) else (255, 255, 255))
        screen.blit(text, (i * KEY_WIDTH + 5, SCREEN_HEIGHT - KEY_HEIGHT + 5))

def draw_notes(screen, notes, time_elapsed, track_colors, active_tracks):
    active_notes = set()
    for note, start_time, channel in notes:
        if time_elapsed >= start_time and active_tracks[channel]:
            y_pos = SCREEN_HEIGHT - (time_elapsed - start_time) * 100
            pygame.draw.rect(screen, track_colors[channel], (note * KEY_WIDTH % SCREEN_WIDTH, y_pos, KEY_WIDTH, 10))
            active_notes.add(note % 14)
    return active_notes

def draw_legend(screen, track_colors, active_tracks):
    font = pygame.font.Font(None, 24)
    for i, (channel, color) in enumerate(track_colors.items()):
        pygame.draw.rect(screen, color, (SCREEN_WIDTH - 150, 30 + i * 30, 20, 20))
        text = font.render(f"Track {channel}", True, (255, 255, 255))
        screen.blit(text, (SCREEN_WIDTH - 120, 30 + i * 30))
        if active_tracks[channel]:
            pygame.draw.rect(screen, (0, 255, 0), (SCREEN_WIDTH - 150, 30 + i * 30, 20, 20), 2)

def check_legend_click(track_colors, active_tracks, mouse_pos, solo_mode):
    for i, channel in enumerate(track_colors.keys()):
        if SCREEN_WIDTH - 150 <= mouse_pos[0] <= SCREEN_WIDTH - 130 and 30 + i * 30 <= mouse_pos[1] <= 50 + i * 30:
            if solo_mode and active_tracks[channel]:
                solo_mode = False
                active_tracks = {k: True for k in active_tracks}
            elif solo_mode:
                active_tracks = {k: False for k in active_tracks}
                active_tracks[channel] = True
                solo_mode = True
            else:
                active_tracks[channel] = not active_tracks[channel]
    return solo_mode, active_tracks
