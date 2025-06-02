# ref https://m365.cloud.microsoft/chat/?fromcode=cmc&redirectid=8AD19A57E1AA4A088F874EAED5B2D5CE&auth=2&internalredirect=CCM

import pygame
import colorsys
from tkinter import Tk, filedialog
from midi_parser import load_midi
from vizualizer import (
    init_visualizer,
    draw_piano,
    draw_notes,
    draw_legend,
    check_legend_click
)
from audio_player import play_midi_with_soundfont
from gui_controls import choose_color, export_colors

def main():
    Tk().withdraw()
    midi_file = filedialog.askopenfilename(filetypes=[("MIDI files", "*.mid")])
    if not midi_file:
        return

    soundfont_file = filedialog.askopenfilename(filetypes=[("SoundFont files", "*.sf2")])
    if not soundfont_file:
        return

    play_midi_with_soundfont(midi_file, soundfont_file)
    notes = load_midi(midi_file)
    screen, clock = init_visualizer()
    start_time = pygame.time.get_ticks()

    num_tracks = max(note[2] for note in notes) + 1
    track_colors = {
        i: pygame.Color(*[int(c * 255) for c in colorsys.hsv_to_rgb(i / num_tracks, 1, 1)])
        for i in range(num_tracks)
    }
    active_tracks = {i: True for i in range(num_tracks)}
    solo_mode = False

    running = True
    while running:
        screen.fill((0, 0, 0))
        time_elapsed = (pygame.time.get_ticks() - start_time) / 1000
        active_notes = draw_notes(screen, notes, time_elapsed, track_colors, active_tracks)
        draw_piano(screen, active_notes)
        draw_legend(screen, track_colors, active_tracks)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                solo_mode, active_tracks = check_legend_click(
                    track_colors, active_tracks, event.pos, solo_mode
                )
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if pygame.mixer.music.get_busy():
                        pygame.mixer.music.pause()
                    else:
                        pygame.mixer.music.unpause()
                elif event.key == pygame.K_c:
                    choose_color(track_colors)
                elif event.key == pygame.K_e:
                    export_colors(track_colors)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
