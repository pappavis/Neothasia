import pygame
import pygame_gui
import sys
import tkinter as tk
from tkinter import filedialog
from midi_parser import load_midi_notes, get_midi_tracks
# Kies één van de volgende twee regels:
# from synthesizer import MIDISynthesizer  # Als je pyfluidsynth gebruikt
from synthesizer import MIDISynthesizer  # Als je pygame.midi gebruikt
import mido

SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
KEYBOARD_HEIGHT = 100
FPS = 60
DEFAULT_BPM = 120
NOTE_SPEED_BASE = 200  # pixels per seconde

class NoteVisualizer:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Neothesia - Vallende Noten")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('Arial', 16)
        self.manager = pygame_gui.UIManager((SCREEN_WIDTH, SCREEN_HEIGHT))

        self.notes = []
        self.midi_path = None
        self.synth = MIDISynthesizer()

        # UI Variabelen
        self.selected_track_index = 0
        self.paused = False
        self.playing = False
        self.bpm = DEFAULT_BPM
        self.note_speed = NOTE_SPEED_BASE
        self.time_signature = (4, 4)

        # UI Elements
        self.track_dropdown = None
        self.bpm_slider = None
        self.speed_slider = None
        self.pause_button = None
        self.stop_button = None

        self.setup_ui()

    def setup_ui(self):
        y = 10
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((10, y), (150, 30)),
            text="Selecteer Track:",
            manager=self.manager
        )
        y += 30
        self.track_dropdown = pygame_gui.elements.UIDropDownMenu(
            options_list=[],
            starting_option="Geen",
            relative_rect=pygame.Rect((10, y), (200, 30)),
            manager=self.manager
        )

        y += 40
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((10, y), (150, 30)),
            text=f"BPM: {self.bpm}",
            object_id="#bpm_label",
            manager=self.manager
        )
        y += 30
        self.bpm_slider = pygame_gui.elements.UIHorizontalSlider(
            relative_rect=pygame.Rect((10, y), (200, 20)),
            start_value=self.bpm,
            value_range=(40, 200),
            manager=self.manager
        )

        y += 40
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((10, y), (150, 30)),
            text=f"Notensnelheid: {self.note_speed}",
            object_id="#speed_label",
            manager=self.manager
        )
        y += 30
        self.speed_slider = pygame_gui.elements.UIHorizontalSlider(
            relative_rect=pygame.Rect((10, y), (200, 20)),
            start_value=self.note_speed,
            value_range=(50, 500),
            manager=self.manager
        )

        y += 40
        self.pause_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((10, y), (90, 30)),
            text="Pauzeren",
            manager=self.manager
        )
        self.stop_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((110, y), (90, 30)),
            text="Stoppen",
            manager=self.manager
        )

    def update_track_dropdown(self, tracks):
        self.track_dropdown.kill()
        options = [t["name"] for t in tracks]
        self.track_dropdown = pygame_gui.elements.UIDropDownMenu(
            options_list=options,
            starting_option=options[0],
            relative_rect=pygame.Rect((10, 40), (200, 30)),
            manager=self.manager
        )

    def select_midi_file(self):
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(filetypes=[("MIDI Files", "*.mid")])
        if file_path:
            self.midi_path = file_path
            tracks = get_midi_tracks(file_path)
            self.update_track_dropdown(tracks)
            self.load_notes_and_start_playback()

    def load_notes_and_start_playback(self):
        self.notes = load_midi_notes(self.midi_path, self.selected_track_index)
        self.start_time = pygame.time.get_ticks() / 1000
        self.playing = True
        self.synth.play_midi(self.midi_path)

    def draw_piano_roll(self):
        now = pygame.time.get_ticks() / 1000 - self.start_time
        for note in self.notes:
            start_sec = note['start_time']
            end_sec = note['end_time']

            if now < start_sec:
                continue

            y_pos = (start_sec - now) * self.note_speed + 50
            if y_pos > SCREEN_HEIGHT - KEYBOARD_HEIGHT:
                continue

            rect_height = max(20, (end_sec - start_sec) * self.note_speed)
            key_x = self.map_note_to_x(note['note'])

            color = (255, 200, 0)
            pygame.draw.rect(self.screen, color, (key_x, y_pos, 30, rect_height))

    def map_note_to_x(self, note_number):
        base_note = 21  # A0
        white_notes = [n for n in range(base_note, 108) if len(mido.note_number_to_name(n)) == 2]
        try:
            index = white_notes.index(note_number)
            return index * 35
        except ValueError:
            return 0

    def draw_keyboard(self):
        self.screen.fill((20, 20, 20),
                        (0, SCREEN_HEIGHT - KEYBOARD_HEIGHT, SCREEN_WIDTH, KEYBOARD_HEIGHT))

        x = 0
        note_num = 21  # MIDI note number for A0 (lowest key on piano)

        while x < SCREEN_WIDTH:
            try:
                note_name = note_util.note_number_to_name(note_num)
            except ValueError:
                break  # Stop if we're out of valid MIDI range

            if len(note_name) == 2:  # White key
                color = (255, 255, 255)
            else:  # Black key
                color = (0, 0, 0)
                x -= 15  # Shift left to overlay black keys

            pygame.draw.rect(self.screen, color,
                            (x, SCREEN_HEIGHT - KEYBOARD_HEIGHT, 35, KEYBOARD_HEIGHT), 1)

            text = self.font.render(note_name, True, (255, 255, 255))
            self.screen.blit(text, (x + 5, SCREEN_HEIGHT - KEYBOARD_HEIGHT + 5))

            x += 35
            note_num += 1
        
    def run(self):
        self.select_midi_file()

        while True:
            dt = self.clock.tick(FPS) / 1000
            time_now = pygame.time.get_ticks() / 1000

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                elif event.type == pygame.USEREVENT:
                    if event.user_type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
                        if event.ui_element == self.track_dropdown:
                            self.selected_track_index = self.track_dropdown.options_list.index(event.text)
                            self.load_notes_and_start_playback()
                    elif event.user_type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
                        if event.ui_element == self.bpm_slider:
                            self.bpm = int(event.value)
                            self.manager.get_object_ids()[event.ui_element]["label"].set_text(f"BPM: {self.bpm}")
                        elif event.ui_element == self.speed_slider:
                            self.note_speed = int(event.value)
                            self.manager.get_object_ids()[event.ui_element]["label"].set_text(f"Notensnelheid: {int(event.value)}")
                    elif event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                        if event.ui_element == self.pause_button:
                            self.paused = not self.paused
                            self.pause_button.set_text("Hervatten" if self.paused else "Pauzeren")
                            if self.paused:
                                self.synth.stop()
                            else:
                                self.synth.play_midi(self.midi_path)
                        elif event.ui_element == self.stop_button:
                            self.playing = False
                            self.synth.stop()

                self.manager.process_events(event)

            self.manager.update(dt)

            self.screen.fill((20, 20, 20))
            if self.playing and not self.paused:
                self.draw_piano_roll()
            self.draw_keyboard()
            self.manager.draw_ui(self.screen)
            pygame.display.flip()