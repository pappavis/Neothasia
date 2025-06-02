import pygame
import sys
import tkinter as tk
from tkinter import filedialog
from midi_parser import load_midi_notes
import mido


SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
KEYBOARD_HEIGHT = 100
WHITE_KEYS = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
BLACK_KEYS = ['C#', 'D#', 'F#', 'G#', 'A#']
FPS = 60
NOTE_SPEED = 200  # pixels per seconde

class NoteVisualizer:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Neothasia - Vallende Noten")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('Arial', 16)

        self.notes = []
        self.start_time = 0
        self.paused = False
        self.playing = False
        self.offset_y = 0

    def select_midi_file(self):
        root = tk.Tk()
        root.withdraw()  # Verberg hoofdvenster
        file_path = filedialog.askopenfilename(filetypes=[("MIDI Files", "*.mid")])
        if file_path:
            self.notes = load_midi_notes(file_path)
            self.start_time = pygame.time.get_ticks() / 1000
            self.playing = True

    def draw_piano_roll(self):
        self.screen.fill((20, 20, 20))  # Donker achtergrond

        now = pygame.time.get_ticks() / 1000 - self.start_time
        for note in self.notes:
            start_sec = note['start_time']
            end_sec = note['end_time']

            if now < start_sec:
                continue

            y_pos = (start_sec - now) * NOTE_SPEED + 50
            if y_pos > SCREEN_HEIGHT - KEYBOARD_HEIGHT:
                continue

            rect_height = max(20, (end_sec - start_sec) * NOTE_SPEED)
            note_name = mido.note_number_to_name(note['note'])
            key_x = self.map_note_to_x(note['note'])

            color = (255, 200, 0)
            pygame.draw.rect(self.screen, color, (key_x, y_pos, 30, rect_height))

    def map_note_to_x(self, note_number):
        base_note = 21  # A0
        white_keys = [n for n in range(base_note, 108) if mido.note_number_to_name(n)[-1] not in ['#']]
        index = white_keys.index(note_number)
        return index * 35

    def draw_keyboard(self):
        x = 0
        note_num = 21  # A0
        while x < SCREEN_WIDTH:
            note_name = mido.note_number_to_name(note_num)
            if len(note_name) == 2:
                color = (255, 255, 255)
            else:
                color = (0, 0, 0)
                x -= 15
            pygame.draw.rect(self.screen, color, (x, SCREEN_HEIGHT - KEYBOARD_HEIGHT, 35, KEYBOARD_HEIGHT), 1)
            text = self.font.render(note_name, True, (255, 255, 255))
            self.screen.blit(text, (x + 5, SCREEN_HEIGHT - KEYBOARD_HEIGHT + 5))
            x += 35
            note_num += 1

    def run(self):
        self.select_midi_file()

        while True:
            dt = self.clock.tick(FPS) / 1000  # Delta time in seconden

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.paused = not self.paused
                    elif event.key == pygame.K_r:
                        self.select_midi_file()

            if not self.paused and self.playing:
                self.screen.fill((20, 20, 20))
                self.draw_piano_roll()
                self.draw_keyboard()
                pygame.display.flip()
