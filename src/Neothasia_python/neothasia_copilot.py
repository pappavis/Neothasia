# ref https://m365.cloud.microsoft/chat/?fromcode=cmc&redirectid=899014C910A74A7083690D916ADC1350&auth=2&internalredirect=CCM

import mido
import pygame
import os
from tkinter import Tk
from tkinter.filedialog import askopenfilename

# Constants
WHITE_KEYS = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
BLACK_KEYS = ['C#', 'D#', 'F#', 'G#', 'A#']
KEY_WIDTH = 20
KEY_HEIGHT = 100
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Neothasia_pythonV1")
clock = pygame.time.Clock()

# Function to draw the piano keys
def draw_piano():
    for i in range(14):
        key_color = (255, 255, 255) if i % 2 == 0 else (0, 0, 0)
        pygame.draw.rect(screen, key_color, (i * KEY_WIDTH, SCREEN_HEIGHT - KEY_HEIGHT, KEY_WIDTH, KEY_HEIGHT))
        label = WHITE_KEYS[i % len(WHITE_KEYS)] if key_color == (255, 255, 255) else BLACK_KEYS[i % len(BLACK_KEYS)]
        font = pygame.font.Font(None, 24)
        text = font.render(label, True, (0, 0, 0) if key_color == (255, 255, 255) else (255, 255, 255))
        screen.blit(text, (i * KEY_WIDTH + 5, SCREEN_HEIGHT - KEY_HEIGHT + 5))

# Function to load and parse MIDI file
def load_midi(file_path):
    midi = mido.MidiFile(file_path)
    notes = []
    current_time = 0
    for track in midi.tracks:
        for msg in track:
            current_time += msg.time
            if msg.type == 'note_on' and msg.velocity > 0:
                notes.append((msg.note, current_time / midi.ticks_per_beat))
    return notes

# Function to draw falling notes
def draw_notes(notes, time_elapsed):
    for note, start_time in notes:
        if time_elapsed >= start_time:
            y_pos = SCREEN_HEIGHT - (time_elapsed - start_time) * 100
            pygame.draw.rect(screen, (0, 255, 0), (note * KEY_WIDTH % SCREEN_WIDTH, y_pos, KEY_WIDTH, 10))

# Main function
def main():
    # Ask user to select a MIDI file
    Tk().withdraw()
    midi_file = askopenfilename(filetypes=[("MIDI files", "*.mid")])
    if not midi_file:
        print("No file selected. Exiting.")
        return

    notes = load_midi(midi_file)
    start_time = pygame.time.get_ticks()

    running = True
    while running:
        screen.fill((0, 0, 0))
        draw_piano()

        time_elapsed = (pygame.time.get_ticks() - start_time) / 1000
        draw_notes(notes, time_elapsed)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()
