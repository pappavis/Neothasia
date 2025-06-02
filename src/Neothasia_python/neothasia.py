# ref https://gemini.google.com/gem/coding-partner/7a390be7cebfa0ec
# https://github.com/sfzinstruments/SplendidGrandPiano
# Versie: 8a6e7c1d
import pygame
import os
import sys
import math
import mido # Zorg dat mido geïnstalleerd is: pip install mido
from tkinter import Tk, filedialog # Voor bestandskiezer

# --- Constanten en configuratie ---
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60 # Frames per seconde

# Kleuren
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (50, 50, 50)
LIGHT_GRAY = (100, 100, 100)
DARK_GRAY = (30, 30, 30)
BLUE = (0, 100, 255)
RED = (255, 0, 0)
GREEN = (0, 200, 0)
YELLOW = (255, 255, 0)
NOTE_COLOR = (0, 200, 200) # Cyaan-achtig voor vallende noten

# Piano toetsenbord layout
OCTAVE_START_MIDI = 21 # A0
OCTAVE_END_MIDI = 108 # C8
WHITE_KEY_WIDTH = 20
BLACK_KEY_WIDTH = WHITE_KEY_WIDTH * 0.6
BLACK_KEY_HEIGHT_RATIO = 0.6 # Zwarte toets is 60% van witte toets hoogte
KEYBOARD_HEIGHT = 120
ROLL_HEIGHT = SCREEN_HEIGHT - KEYBOARD_HEIGHT

# Noten namen
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# --- Helper functies ---
def get_note_name(midi_note):
    """Converteert een MIDI-nootnummer naar een naam (e.g., C4, A#3)."""
    octave = (midi_note // 12) - 1 # MIDI C0 is octaaf -1, C4 is octaaf 3
    note_name = NOTE_NAMES[midi_note % 12]
    return f"{note_name}{octave}"

# --- MIDI Parsing (hergebruik van de eerder gemaakte functie) ---
def parse_midi_file(midi_filepath):
    """
    Parset een MIDI-bestand en extraheert noteninformatie.

    Args:
        midi_filepath (str): Het pad naar het MIDI-bestand.

    Returns:
        tuple: Een tuple bestaande uit:
            - list: Een lijst van dicts, waarbij elke dict een noot representeert
                    met 'note', 'start_time', 'duration', 'velocity', 'track_name', 'channel'.
            - list: Een lijst van tracknamen (str).
            - int: De ticks_per_beat van het MIDI-bestand.
            - dict: Een dictionary met tempo-wijzigingen: {absolute_time_in_ticks: tempo_in_microseconds_per_beat}.
    """
    notes_data = []
    track_names = []
    tempo_changes = {} # {absolute_time_in_ticks: tempo_in_microseconds_per_beat}

    try:
        mid = mido.MidiFile(midi_filepath)
    except FileNotFoundError:
        print(f"Fout: Bestand niet gevonden op {midi_filepath}")
        return [], [], 0, {}
    except Exception as e:
        print(f"Fout bij het laden van het MIDI-bestand: {e}")
        return [], [], 0, {}

    ticks_per_beat = mid.ticks_per_beat
    
    # Tijdelijke opslag voor actieve noten
    # {note_number: {'start_time': absolute_time_in_ticks, 'velocity': velocity, 'channel': channel, 'track_name': track_name}}
    active_notes = {}

    # Absolute tijd teller voor elke track (in ticks)
    # We moeten de tijd per track bijhouden omdat messages in een track relatief zijn aan elkaar.
    track_absolute_times = {i: 0 for i in range(len(mid.tracks))}

    for i, track in enumerate(mid.tracks):
        track_name = f"Track {i+1}" # Standaardnaam
        # Probeer de tracknaam te vinden
        for msg in track:
            if msg.type == 'track_name':
                track_name = msg.name
                break
        track_names.append(track_name)
        
        current_track_time = 0 # Tijd in ticks voor de huidige track

        for msg in track:
            current_track_time += msg.time # Voeg relatieve tijd toe aan absolute tijd voor deze track

            if msg.type == 'note_on':
                # Als velocity 0 is, behandelen we het als een note_off
                if msg.velocity > 0:
                    key = (msg.note, msg.channel, track_name) # Unieke sleutel voor de noot
                    active_notes[key] = {
                        'start_time': current_track_time,
                        'velocity': msg.velocity,
                        'channel': msg.channel,
                        'track_name': track_name
                    }
                else: # velocity == 0, dus het is een note_off
                    key = (msg.note, msg.channel, track_name)
                    if key in active_notes:
                        note_info = active_notes.pop(key)
                        duration = current_track_time - note_info['start_time']
                        if duration > 0: # Zorg ervoor dat de duur positief is
                            notes_data.append({
                                'note': note_info['note'],
                                'start_time': note_info['start_time'],
                                'duration': duration,
                                'velocity': note_info['velocity'],
                                'track_name': note_info['track_name'],
                                'channel': note_info['channel']
                            })
            elif msg.type == 'note_off':
                key = (msg.note, msg.channel, track_name)
                if key in active_notes:
                    note_info = active_notes.pop(key)
                    duration = current_track_time - note_info['start_time']
                    if duration > 0:
                        notes_data.append({
                            'note': note_info['note'],
                            'start_time': note_info['start_time'],
                            'duration': duration,
                            'velocity': note_info['velocity'],
                            'track_name': note_info['track_name'],
                            'channel': note_info['channel']
                        })
            elif msg.type == 'set_tempo':
                # Tempo-wijzigingen worden opgeslagen met de absolute tijd in ticks
                tempo_changes[current_track_time] = msg.tempo

    # Sorteer de noten op starttijd voor eenvoudigere verwerking later
    notes_data.sort(key=lambda x: x['start_time'])

    return notes_data, track_names, ticks_per_beat, tempo_changes


# --- UI Elementen (Knoppen, Dropdowns, Sliders) ---
# Een simpele implementatie voor dropdown, knop en slider.
# Voor een robuustere UI zou men een specifieke GUI-bibliotheek of een Pygame UI-uitbreiding gebruiken.

class Button:
    def __init__(self, x, y, width, height, text, font, color, hover_color, action=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.color = color
        self.hover_color = hover_color
        self.action = action
        self.is_hovered = False

    def draw(self, surface):
        current_color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(surface, current_color, self.rect)
        text_surf = self.font.render(self.text, True, BLACK)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.action:
                    self.action()
                return True
        return False

class Dropdown:
    def __init__(self, x, y, width, height, options, font, default_selection_index=0):
        self.rect = pygame.Rect(x, y, width, height)
        self.options = options
        self.font = font
        self.selected_option_index = default_selection_index
        self.is_open = False
        self.option_height = height
        self.max_display_options = 5 # Hoeveel opties zichtbaar zijn in de dropdown

    def draw(self, surface):
        # Draw selected option
        pygame.draw.rect(surface, LIGHT_GRAY, self.rect)
        pygame.draw.rect(surface, BLACK, self.rect, 2)
        text_surf = self.font.render(self.options[self.selected_option_index], True, BLACK)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

        # Draw dropdown arrow
        pygame.draw.polygon(surface, BLACK, [
            (self.rect.right - 20, self.rect.centery - 5),
            (self.rect.right - 10, self.rect.centery - 5),
            (self.rect.right - 15, self.rect.centery + 5)
        ])

        # Draw open options
        if self.is_open:
            for i, option in enumerate(self.options):
                if i >= self.max_display_options: # Beperk aantal zichtbare opties
                    break
                option_rect = pygame.Rect(self.rect.x, self.rect.bottom + i * self.option_height, self.rect.width, self.option_height)
                pygame.draw.rect(surface, WHITE, option_rect)
                pygame.draw.rect(surface, BLACK, option_rect, 1)
                option_text_surf = self.font.render(option, True, BLACK)
                option_text_rect = option_text_surf.get_rect(center=option_rect.center)
                surface.blit(option_text_surf, option_text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.is_open = not self.is_open
                return True
            elif self.is_open:
                for i, option in enumerate(self.options):
                    if i >= self.max_display_options:
                        break
                    option_rect = pygame.Rect(self.rect.x, self.rect.bottom + i * self.option_height, self.rect.width, self.option_height)
                    if option_rect.collidepoint(event.pos):
                        self.selected_option_index = i
                        self.is_open = False
                        return True
        return False

    def get_selected_option(self):
        return self.options[self.selected_option_index]

class Slider:
    def __init__(self, x, y, width, height, min_val, max_val, initial_val, font, label=""):
        self.rect = pygame.Rect(x, y, width, height)
        self.min_val = min_val
        self.max_val = max_val
        self.val = initial_val
        self.font = font
        self.label = label
        self.dragging = False
        self.handle_radius = height / 2

    def draw(self, surface):
        # Slider track
        pygame.draw.line(surface, DARK_GRAY, (self.rect.x + self.handle_radius, self.rect.centery), 
                         (self.rect.right - self.handle_radius, self.rect.centery), 5)
        
        # Slider handle
        handle_x = self.rect.x + self.handle_radius + (self.val - self.min_val) / (self.max_val - self.min_val) * (self.rect.width - 2 * self.handle_radius)
        pygame.draw.circle(surface, BLUE, (int(handle_x), self.rect.centery), int(self.handle_radius))
        pygame.draw.circle(surface, BLACK, (int(handle_x), self.rect.centery), int(self.handle_radius), 2)

        # Label and value
        label_text = f"{self.label}: {self.val:.1f}" if isinstance(self.val, float) else f"{self.label}: {int(self.val)}"
        text_surf = self.font.render(label_text, True, BLACK)
        text_rect = text_surf.get_rect(midleft=(self.rect.right + 10, self.rect.centery))
        surface.blit(text_surf, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            handle_x = self.rect.x + self.handle_radius + (self.val - self.min_val) / (self.max_val - self.min_val) * (self.rect.width - 2 * self.handle_radius)
            handle_rect = pygame.Rect(handle_x - self.handle_radius, self.rect.centery - self.handle_radius, self.handle_radius * 2, self.handle_radius * 2)
            if handle_rect.collidepoint(event.pos):
                self.dragging = True
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
            return True
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            normalized_x = (event.pos[0] - (self.rect.x + self.handle_radius)) / (self.rect.width - 2 * self.handle_radius)
            normalized_x = max(0.0, min(1.0, normalized_x))
            self.val = self.min_val + normalized_x * (self.max_val - self.min_val)
            return True
        return False

    def get_value(self):
        return self.val


# --- Hoofdapplicatieklasse ---
class PianoRollApp:
    # Versie: 8a6e7c1d
    def __init__(self):
        pygame.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Neothesia Python V4")
        self.clock = pygame.time.Clock()

        self.font_small = pygame.font.Font(None, 24)
        self.font_medium = pygame.font.Font(None, 36)
        self.font_large = pygame.font.Font(None, 48)

        self.midi_notes = []
        self.all_tracks = []
        self.ticks_per_beat = 0
        self.tempo_changes = {} # {tick: microseconds_per_beat}

        self.current_notes_on_screen = pygame.sprite.Group() # Voor vallende noten

        self.running = True
        self.playing = False
        self.paused = False
        self.start_time = 0 # Tijd (in ms) waarop afspelen is gestart
        self.pause_offset = 0 # Tijd (in ms) die verstreken is voor de pauze

        # Rollende noten snelheid: Aantal pixels per seconde.
        # Moet afhangen van BPM en schermgrootte
        self.note_fall_speed_factor = 1.0 # Multiplicator voor de valsnelheid
        self.bpm = 120 # Standaard BPM, kan worden overschreven door MIDI-bestand
        self.beats_per_measure_top = 4 # Teller van de maatsoort (bijv. 4 in 4/4)
        self.beats_per_measure_bottom = 4 # Noemer van de maatsoort (bijv. 4 in 4/4)
        
        # Aangepaste instrumenten voor elke track
        # Let op: implementatie van daadwerkelijke instrumentselectie en soundfonts
        # komt in een latere fase. Dit is nu een placeholder UI.
        self.track_instruments = {} # {track_name: "Piano"}

        # UI Elementen
        self.load_midi_button = Button(SCREEN_WIDTH - 200, 20, 180, 40, "Laad MIDI", self.font_medium, LIGHT_GRAY, GRAY, self.load_midi_file)
        self.play_button = Button(20, 20, 100, 40, "Afspelen", self.font_medium, GREEN, (0,255,0), self.play_midi)
        self.pause_button = Button(140, 20, 100, 40, "Pauze", self.font_medium, YELLOW, (255,255,0), self.pause_midi)
        self.stop_button = Button(260, 20, 100, 40, "Stop", self.font_medium, RED, (255,100,100), self.stop_midi)

        self.track_dropdown = None # Wordt geïnitialiseerd na het laden van een MIDI-bestand
        self.instrument_dropdown = None # Wordt geïnitialiseerd na het laden van een MIDI-bestand
        self.current_selected_track = None

        self.bpm_slider = Slider(400, 20, 200, 20, 60, 240, self.bpm, self.font_small, "BPM")
        self.fall_speed_slider = Slider(400, 50, 200, 20, 0.5, 3.0, self.note_fall_speed_factor, self.font_small, "Valsnelheid")
        self.time_signature_top_slider = Slider(650, 20, 100, 20, 1, 16, self.beats_per_measure_top, self.font_small, "Maat (T)")
        self.time_signature_bottom_slider = Slider(650, 50, 100, 20, 1, 16, self.beats_per_measure_bottom, self.font_small, "Maat (B)")

        self.ui_elements = [
            self.load_midi_button, self.play_button, self.pause_button, self.stop_button,
            self.bpm_slider, self.fall_speed_slider, self.time_signature_top_slider, self.time_signature_bottom_slider
        ]
        
        self.loaded_midi_filename = ""
        self.notes_to_spawn = [] # Lijst van noten die nog moeten verschijnen
        self.next_note_index = 0

    def load_midi_file(self):
        Tk().withdraw() # Verberg het hoofdtkinter venster
        # Initialiseer een bestandskiezer voor MIDI-bestanden
        file_path = filedialog.askopenfilename(
            title="Selecteer een MIDI-bestand",
            filetypes=[("MIDI files", "*.mid")]
        )
        if file_path:
            self.loaded_midi_filename = os.path.basename(file_path)
            print(f"Laden van MIDI-bestand: {file_path}")
            notes_data, track_names, ticks_per_beat, tempo_changes = parse_midi_file(file_path)
            
            if notes_data:
                self.midi_notes = notes_data
                self.all_tracks = track_names
                self.ticks_per_beat = ticks_per_beat
                self.tempo_changes = tempo_changes
                print(f"MIDI bestand geladen: {len(self.midi_notes)} noten, {len(self.all_tracks)} tracks.")
                
                # Initialiseer track dropdown
                self.track_dropdown = Dropdown(SCREEN_WIDTH - 200, 70, 180, 40, self.all_tracks, self.font_medium)
                self.ui_elements.append(self.track_dropdown)
                self.current_selected_track = self.track_dropdown.get_selected_option()
                
                # Initialiseer instrument dropdown (placeholder voor nu)
                # Later zou dit dynamisch moeten zijn op basis van beschikbare soundfonts of VSTs
                self.instrument_dropdown = Dropdown(SCREEN_WIDTH - 200, 120, 180, 40, 
                                                    ["Piano", "Gitaar", "Trompet", "Drums"], self.font_medium)
                self.ui_elements.append(self.instrument_dropdown)
                
                # Reset afspeelstatus
                self.stop_midi()
                self.prepare_notes_for_playback()
            else:
                print("Laden van MIDI-bestand mislukt of geen noten gevonden.")
                self.midi_notes = []
                self.all_tracks = []
                self.ticks_per_beat = 0
                self.tempo_changes = {}
                # Verwijder dropdowns als geen bestand is geladen
                if self.track_dropdown in self.ui_elements: self.ui_elements.remove(self.track_dropdown)
                if self.instrument_dropdown in self.ui_elements: self.ui_elements.remove(self.instrument_dropdown)
                self.track_dropdown = None
                self.instrument_dropdown = None


    def prepare_notes_for_playback(self):
        """Filtert noten op basis van de geselecteerde track en reset de afspeelstatus."""
        self.current_notes_on_screen.empty()
        self.notes_to_spawn = []
        self.next_note_index = 0

        if self.current_selected_track:
            self.notes_to_spawn = [
                note for note in self.midi_notes 
                if note['track_name'] == self.current_selected_track
            ]
            print(f"Geselecteerde track: '{self.current_selected_track}'. Aantal noten om af te spelen: {len(self.notes_to_spawn)}")
        else:
            self.notes_to_spawn = list(self.midi_notes) # Speel alle noten af als geen track geselecteerd is
            print(f"Geen specifieke track geselecteerd. Speelt alle {len(self.notes_to_spawn)} noten af.")
        
        # Sorteer de noten opnieuw, voor het geval dat filtering de volgorde heeft verstoord
        self.notes_to_spawn.sort(key=lambda x: x['start_time'])

    def play_midi(self):
        if not self.midi_notes:
            print("Geen MIDI-bestand geladen om af te spelen.")
            return

        if self.paused:
            self.playing = True
            self.paused = False
            # Pas de starttijd aan om de pauzetijd te compenseren
            self.start_time = pygame.time.get_ticks() - self.pause_offset
            print("Afspelen hervat.")
        elif not self.playing:
            self.playing = True
            self.paused = False
            self.start_time = pygame.time.get_ticks() # Registreer de starttijd
            self.pause_offset = 0
            self.current_notes_on_screen.empty() # Leeg alle noten op het scherm
            self.next_note_index = 0 # Reset de noot-index
            self.prepare_notes_for_playback()
            print("Afspelen gestart.")

    def pause_midi(self):
        if self.playing:
            self.playing = False
            self.paused = True
            self.pause_offset = pygame.time.get_ticks() - self.start_time # Sla de verstreken tijd op
            print("Afspelen gepauzeerd.")

    def stop_midi(self):
        self.playing = False
        self.paused = False
        self.start_time = 0
        self.pause_offset = 0
        self.current_notes_on_screen.empty() # Verwijder alle noten van het scherm
        self.next_note_index = 0 # Reset de noot-index
        print("Afspelen gestopt.")

    def get_current_midi_time_in_ticks(self):
        """Berekent de huidige afspeeltijd in MIDI-ticks."""
        if not self.playing and not self.paused:
            return 0
        
        current_playback_time_ms = pygame.time.get_ticks() - self.start_time # Verstreken tijd sinds start/hervat
        
        # Converteer milliseconden naar ticks.
        # Dit is complexer door tempo-wijzigingen. Voor nu een simpele benadering.
        # In een echte implementatie moet je door de tempo_changes loopen om de exacte ticks te bepalen.
        # Voorlopig gaan we uit van een constante BPM voor deze conversie.
        
        # Microseconds per beat = 60,000,000 / BPM
        # Ticks per milliseconde = (ticks_per_beat * BPM) / 60000
        # Ticks = current_playback_time_ms * (ticks_per_beat * BPM / 60000)
        
        # Vereenvoudigde benadering (voor demonstratie):
        # Stel dat 1 beat = 1 seconde voor valsnelheid bepaling, dan 1 tick = 1/ticks_per_beat seconde.
        # current_midi_time_ticks = (current_playback_time_ms / 1000.0) * (self.bpm / 60.0) * self.ticks_per_beat
        
        # Voor nauwkeurigheid met variabele tempo:
        # Dit is een *vereenvoudigde* implementatie van tempo-handling.
        # Een robuuste implementatie zou een lijst van (tick_time, real_time) paren moeten bijhouden
        # en interpoleren, of de tempo_changes dictionary itereren.
        
        # Hier gebruiken we de huidige BPM slider waarde om ms naar ticks te converteren.
        # Dit is niet ideaal voor MIDI-bestanden met ingebouwde tempo-wijzigingen,
        # maar voldoende voor basis synchronisatie met een aanpasbare BPM.
        
        current_bpm = self.bpm_slider.get_value()
        ms_per_beat = (60 / current_bpm) * 1000 # Milliseconden per beat
        ticks_per_ms = self.ticks_per_beat / ms_per_beat
        
        return current_playback_time_ms * ticks_per_ms

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0 # Delta time in seconden

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                
                handled_by_ui = False
                for element in self.ui_elements:
                    if element.handle_event(event):
                        handled_by_ui = True
                        break
                
                if not handled_by_ui:
                    # Specifieke handler voor dropdown selectie verandering
                    if self.track_dropdown and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        if self.track_dropdown.is_open and any(
                            pygame.Rect(self.track_dropdown.rect.x, 
                                        self.track_dropdown.rect.bottom + i * self.track_dropdown.option_height, 
                                        self.track_dropdown.rect.width, 
                                        self.track_dropdown.option_height).collidepoint(event.pos) 
                            for i in range(len(self.track_dropdown.options))
                        ):
                            # Track selectie is gewijzigd, prepareer noten opnieuw
                            if self.current_selected_track != self.track_dropdown.get_selected_option():
                                self.current_selected_track = self.track_dropdown.get_selected_option()
                                self.stop_midi() # Stop en reset afspelen
                                self.prepare_notes_for_playback() # Laad nieuwe noten voor weergave
                                print(f"Track geselecteerd: {self.current_selected_track}")


            # Update logica
            if self.playing:
                current_midi_tick = self.get_current_midi_time_in_ticks()
                
                # Spawn nieuwe noten
                while self.next_note_index < len(self.notes_to_spawn):
                    note_info = self.notes_to_spawn[self.next_note_index]
                    # We willen noten spawnen die op of na de huidige speeltijd zouden moeten 'beginnen'
                    # Maar we laten ze al eerder in beeld verschijnen, zodat ze van boven kunnen vallen.
                    # Bepaal de 'verschijntijd' van de noot bovenaan het scherm.
                    # Dit is (start_time - tijd_om_scherm_over_te_steken).
                    
                    # De hoogte van de pianorol bepaalt de 'reistijd'.
                    # We willen dat de noot precies op `start_time` de 'speellijn' bereikt (onderaan de pianorol).
                    # De snelheid wordt beïnvloed door self.fall_speed_factor en self.bpm_slider.get_value()
                    
                    # Tijd die een noot nodig heeft om het scherm over te steken (in ms)
                    # Stel dat het scherm een "hoogte" heeft in beats. Hoeveel beats passen er in de pianorol?
                    # Een noot beweegt van boven naar beneden. De "speellijn" is de onderkant van de pianorol.
                    # Als de noot op 'start_time' de speellijn moet bereiken, en het duurt X ms om te vallen,
                    # dan moet de noot op (start_time_in_ms - X_ms) al beginnen met vallen.
                    
                    # Deze 'offset_in_ticks' bepaalt hoe ver noten vooruit worden 'voorbereid' en gespawnd.
                    # Dit moet worden afgestemd op de valsnelheid en schermhoogte.
                    # Voor nu een heuristische waarde, dit moet gekoppeld worden aan valsnelheid.
                    
                    # Hoeveel tijd (in ticks) een noot nodig heeft om van boven naar beneden te vallen.
                    # Dit is afhankelijk van de 'visuele' valsnelheid en de lengte van de pianorol.
                    # Laten we aannemen dat de pianorol een vaste 'visuele duur' representeert.
                    # Bijv. 4 beats lang (dit moet aanpasbaar worden).
                    
                    # Stel, de pianorol toont 4 beats aan noten tegelijk.
                    # Dan is de 'valduur' 4 beats.
                    # Valduur in ticks = 4 * self.ticks_per_beat
                    
                    # De snelheid waarmee de noten bewegen is 'pixels per seconde'.
                    # De hoogte van de roll is ROLL_HEIGHT.
                    # Tijd om te vallen (sec) = ROLL_HEIGHT / (basis_valsnelheid * self.fall_speed_factor)
                    # basis_valsnelheid moet hier 'pixels per tick' of 'pixels per beat' zijn
                    
                    # Een simpeler model: de noten reizen van boven naar beneden in een vaste 'echte tijd',
                    # en de BPM bepaalt hoe veel ticks dat is.
                    # Laat de noot bijvoorbeeld 2 seconden duren om te vallen.
                    FALL_TIME_SECONDS = 2.0 / self.fall_speed_slider.get_value() # Pas valsnelheid aan
                    fall_time_ms = FALL_TIME_SECONDS * 1000
                    
                    # Converteer val_tijd_ms naar MIDI ticks
                    current_bpm = self.bpm_slider.get_value()
                    ms_per_beat = (60 / current_bpm) * 1000
                    ticks_per_ms = self.ticks_per_beat / ms_per_beat
                    
                    fall_time_ticks = fall_time_ms * ticks_per_ms

                    # Spawn noot als de starttijd min de valtijd gelijk is aan of voor de huidige tijd
                    if note_info['start_time'] - fall_time_ticks <= current_midi_tick:
                        # Bereken de X-positie op basis van het nootnummer
                        note_x = self.get_note_x_position(note_info['note'])
                        
                        # Bereken de breedte van de noot
                        note_width = WHITE_KEY_WIDTH if note_info['note'] % 12 in [0, 2, 4, 5, 7, 9, 11] else BLACK_KEY_WIDTH

                        # De noot wordt bovenaan de pianorol gespawnd
                        note_y_start = - (note_info['duration'] / self.ticks_per_beat) * (ROLL_HEIGHT / FALL_TIME_SECONDS / (current_bpm / 60)) 
                        # De bovenstaande berekening van note_y_start is complex. Simpeler:
                        # De noot wordt altijd helemaal bovenaan gespawnd, en de lengte representeert de duur.
                        # De y-positie wordt dan dynamisch berekend.
                        
                        # Nootlengte in pixels: afhankelijk van duur en valsnelheid
                        # Duur in ms = (note_info['duration'] / self.ticks_per_beat) * ms_per_beat
                        note_duration_ms = (note_info['duration'] / ticks_per_ms)
                        note_height_pixels = (note_duration_ms / 1000.0) * (ROLL_HEIGHT / FALL_TIME_SECONDS) # pixels per seconde * duur in seconden
                        
                        new_note_sprite = FallingNote(
                            note_info['note'],
                            note_info['start_time'],
                            note_info['duration'],
                            note_x, 
                            note_width, 
                            note_height_pixels,
                            current_bpm,
                            self.ticks_per_beat,
                            self.screen.get_height(), # Totale schermhoogte voor referentie
                            KEYBOARD_HEIGHT,
                            FALL_TIME_SECONDS
                        )
                        self.current_notes_on_screen.add(new_note_sprite)
                        self.next_note_index += 1
                    else:
                        break # Noten zijn gesorteerd, dus we kunnen stoppen met spawnen

                # Update de positie van de vallende noten
                # Pass current_midi_tick zodat noten hun Y-positie kunnen berekenen
                for note_sprite in self.current_notes_on_screen:
                    note_sprite.update(current_midi_tick)

                # Verwijder noten die van het scherm zijn gevallen
                for note_sprite in self.current_notes_on_screen:
                    if note_sprite.rect.top > self.screen.get_height() - KEYBOARD_HEIGHT: # Noten zijn beneden de speellijn
                        # We kunnen hier later een 'trigger' toevoegen voor audio afspelen
                        # Voor nu verwijderen we ze als ze het toetsenbord passeren
                        if note_sprite.rect.top > self.screen.get_height(): # Helemaal buiten beeld
                            self.current_notes_on_screen.remove(note_sprite)
                        
            # Rendering
            self.draw()

        pygame.quit()
        sys.exit()

    def get_note_x_position(self, midi_note):
        """Berekent de x-positie voor een noot op het pianotoetsenbord."""
        # Dit is een vereenvoudigde berekening voor plaatsing op de pianorol.
        # Een echte pianotoetsenbord layout is complexer door zwarte toetsen.
        # Voorlopig plaatsen we ze gewoon naast elkaar.

        # Aantal witte toetsen in een octaaf: C, D, E, F, G, A, B (7)
        # Totaal aantal witte toetsen in ons bereik (A0 tot C8 = 88 toetsen)
        # Midi 21 (A0) tot Midi 108 (C8)
        # Totaal 88 noten.
        
        # We moeten de X-positie op de virtuele pianorol mapen.
        # De breedte van de pianorol is SCREEN_WIDTH.
        # We verdelen dit over 88 noten.
        # Dit is een placeholder en moet nauwkeuriger worden.
        # Voor nu: elke noot krijgt een vaste breedte, beginnend vanaf de linkerkant.
        # MIDI noten: 21 (A0) tot 108 (C8).
        
        # Bereken de start X-positie voor de hele reeks noten
        total_white_keys = 52 # Aantal witte toetsen van A0 (21) tot C8 (108)
        # (108 - 21) + 1 = 88 totale noten.
        # A0=21, A#0=22, B0=23, C1=24 etc.
        
        # Een meer realistische X-positie mapping zou zijn:
        # Bereken de X-posities voor alle *witte* toetsen.
        # De zwarte toetsen liggen daar tussenin en zijn smaller.
        
        # Offset van de start noot (A0 = MIDI 21) naar C0 (MIDI 24)
        midi_note_relative_to_C0 = midi_note - 24 # MIDI 24 is C1
        
        num_white_keys_left_of_note = 0
        current_midi_for_pos = OCTAVE_START_MIDI
        white_key_indices = [0, 2, 4, 5, 7, 9, 11] # C, D, E, F, G, A, B
        
        # Bereken de x-positie op basis van de witte toetsen
        x_offset = 0
        for i in range(OCTAVE_START_MIDI, midi_note):
            if i % 12 in white_key_indices:
                x_offset += WHITE_KEY_WIDTH
            else: # Zwarte toets
                pass # Zwarte toetsen krijgen geen extra offset in deze telling
        
        # De X-coördinaat op de pianorol begint links
        # Dit is een *uitdaging* voor een nauwkeurige weergave.
        # Voor een simpele start: we behandelen elke noot alsof het een vaste kolom heeft.
        # We zullen de noten plaatsen als kolommen in de pianorol.
        # Het totale bereik van noten is 88 (van 21 tot 108).
        # We verdelen de breedte van het scherm over deze noten.
        
        # Breedte per 'nootkolom' in de pianorol
        num_playable_notes = OCTAVE_END_MIDI - OCTAVE_START_MIDI + 1 # 88 noten
        note_column_width = SCREEN_WIDTH / num_playable_notes

        # X-positie van de linkerkant van de nootkolom
        return (midi_note - OCTAVE_START_MIDI) * note_column_width

    def draw_piano_roll_background(self):
        """Tekent de achtergrond van de pianorol (lijnen en balken)."""
        pygame.draw.rect(self.screen, DARK_GRAY, (0, 0, SCREEN_WIDTH, ROLL_HEIGHT))

        num_playable_notes = OCTAVE_END_MIDI - OCTAVE_START_MIDI + 1
        note_column_width = SCREEN_WIDTH / num_playable_notes

        # Teken verticale lijnen voor elke nootkolom
        for i in range(num_playable_notes):
            x = i * note_column_width
            midi_note = OCTAVE_START_MIDI + i
            
            # Witte en zwarte toetsen afscheiding
            if midi_note % 12 in [1, 3, 6, 8, 10]: # Zwarte toetsen
                pygame.draw.line(self.screen, GRAY, (x, 0), (x, ROLL_HEIGHT), 1)
            else: # Witte toetsen
                pygame.draw.line(self.screen, LIGHT_GRAY, (x, 0), (x, ROLL_HEIGHT), 1)

        # Teken horizontale lijnen voor maatstrepen (vereenvoudigd)
        # Dit moet gesynchroniseerd zijn met de BPM en maataanduiding
        # Voor nu tekenen we om de zoveel pixels een lijn
        pixels_per_beat_visual = (ROLL_HEIGHT / (2.0 / self.fall_speed_slider.get_value())) * (60.0 / self.bpm_slider.get_value())
        
        #pixels_per_second = ROLL_HEIGHT / FALL_TIME_SECONDS
        #pixels_per_beat = pixels_per_second * (60 / self.bpm_slider.get_value())
        
        # Aantal pixels per beat (visueel)
        # Hoe langer de 'valsnelheid' is ingesteld, hoe meer pixels per beat
        # Dit is een visuele weergave, niet de echte MIDI-tijd.
        
        # De 'speellijn' onderaan de pianorol
        pygame.draw.line(self.screen, RED, (0, ROLL_HEIGHT), (SCREEN_WIDTH, ROLL_HEIGHT), 3)

        # Horizontale lijnen om de x aantal pixels voor visuele 'beats' of 'maten'
        # Afhankelijk van de 'pixels per beat'
        current_y_line = ROLL_HEIGHT - pixels_per_beat_visual # Start bij de speellijn en ga omhoog
        while current_y_line > 0:
            if (ROLL_HEIGHT - current_y_line) % (pixels_per_beat_visual * self.beats_per_measure_top) < 10: # Maatstreep
                pygame.draw.line(self.screen, YELLOW, (0, current_y_line), (SCREEN_WIDTH, current_y_line), 2)
            else: # Beatstreep
                pygame.draw.line(self.screen, GRAY, (0, current_y_line), (SCREEN_WIDTH, current_y_line), 1)
            current_y_line -= pixels_per_beat_visual


    def draw_piano_keyboard(self):
        """Tekent het statische pianotoetsenbord onderaan."""
        keyboard_y = SCREEN_HEIGHT - KEYBOARD_HEIGHT
        pygame.draw.rect(self.screen, BLACK, (0, keyboard_y, SCREEN_WIDTH, KEYBOARD_HEIGHT))

        # Teken de witte toetsen
        white_keys_drawn = 0
        current_x = 0
        white_key_indices = [0, 2, 4, 5, 7, 9, 11] # C, D, E, F, G, A, B

        # Bereken de start X-positie zodat de toetsen breed genoeg zijn om het hele scherm te vullen
        total_white_keys_in_range = 0
        for i in range(OCTAVE_START_MIDI, OCTAVE_END_MIDI + 1):
            if i % 12 in white_key_indices:
                total_white_keys_in_range += 1
        
        effective_white_key_width = SCREEN_WIDTH / total_white_keys_in_range
        black_key_effective_width = effective_white_key_width * BLACK_KEY_WIDTH / WHITE_KEY_WIDTH # Proportioneel kleiner

        key_rects = [] # Om later toetsen te kunnen highlighten indien nodig
        
        # Trekken witte toetsen
        # Starten vanaf MIDI 21 (A0)
        current_x = 0
        for i in range(OCTAVE_START_MIDI, OCTAVE_END_MIDI + 1):
            if i % 12 in white_key_indices: # Witte toets
                rect = pygame.Rect(current_x, keyboard_y, effective_white_key_width, KEYBOARD_HEIGHT)
                pygame.draw.rect(self.screen, WHITE, rect)
                pygame.draw.rect(self.screen, BLACK, rect, 1) # Rand
                
                # Nootnaam toevoegen
                note_name = get_note_name(i)
                text_surf = self.font_small.render(note_name, True, BLACK)
                text_rect = text_surf.get_rect(center=(rect.centerx, rect.bottom - 15))
                self.screen.blit(text_surf, text_rect)
                
                current_x += effective_white_key_width
                key_rects.append({'note': i, 'rect': rect, 'color': WHITE})
            else:
                # Sla zwarte toetsen voor nu over en teken ze later bovenaan de witte toetsen
                pass
        
        # Trekken zwarte toetsen (bovenop de witte)
        current_x_white_key_start = 0
        for i in range(OCTAVE_START_MIDI, OCTAVE_END_MIDI + 1):
            midi_note_mod_12 = i % 12
            if midi_note_mod_12 in [1, 3, 6, 8, 10]: # Zwarte toetsen: C#, D#, F#, G#, A#
                # De x-positie van de zwarte toets is tussen de twee witte toetsen
                # Bijvoorbeeld: C# ligt tussen C en D.
                # Eenvoudige benadering: plaats het op de helft van de vorige witte toets + helft van de huidige witte toets
                # Dit is complexer om precies te doen met variabele breedtes.
                # Voor nu, we bepalen de x-positie van de *bijbehorende* witte toets en schuiven hem dan op.
                
                # Vind de x-positie van de witte toets links van deze zwarte toets
                # Bijvoorbeeld: voor C# (noot 1) is dat C (noot 0)
                if midi_note_mod_12 == 1: # C#
                    relative_white_note = i - 1
                elif midi_note_mod_12 == 3: # D#
                    relative_white_note = i - 1
                elif midi_note_mod_12 == 6: # F#
                    relative_white_note = i - 1
                elif midi_note_mod_12 == 8: # G#
                    relative_white_note = i - 1
                elif midi_note_mod_12 == 10: # A#
                    relative_white_note = i - 1
                else:
                    continue # Dit zou niet moeten gebeuren

                # Bereken de x-positie van de witte toets links van de zwarte toets
                base_white_x = self.get_note_x_position(relative_white_note) # Dit is de methode van pianorol
                
                # Dit is de correcte manier om de X-positie te berekenen op het toetsenbord.
                # Zoek de x-positie van de *witte toets* die aan de linkerkant van deze zwarte toets grenst.
                # Index van de witte toets in de array van alle witte toetsen.
                num_white_keys_before = 0
                for wk_midi in range(OCTAVE_START_MIDI, i):
                    if wk_midi % 12 in white_key_indices:
                        num_white_keys_before += 1
                
                black_key_x = (num_white_keys_before * effective_white_key_width) + (effective_white_key_width * 0.7) # Positioneren op 70% van de vorige witte toets
                
                rect = pygame.Rect(black_key_x - (black_key_effective_width / 2), keyboard_y, black_key_effective_width, KEYBOARD_HEIGHT * BLACK_KEY_HEIGHT_RATIO)
                pygame.draw.rect(self.screen, BLACK, rect)
                key_rects.append({'note': i, 'rect': rect, 'color': BLACK})


    def draw_ui_elements(self):
        """Tekent alle UI-elementen."""
        # Toon geladen MIDI-bestandsnaam
        if self.loaded_midi_filename:
            text_surf = self.font_small.render(f"Geladen: {self.loaded_midi_filename}", True, BLACK)
            self.screen.blit(text_surf, (SCREEN_WIDTH - text_surf.get_width() - 20, 160))

        for element in self.ui_elements:
            element.draw(self.screen)
        
        # Werk de geselecteerde track bij als de dropdown open is
        if self.track_dropdown:
            if self.track_dropdown.get_selected_option() != self.current_selected_track and not self.track_dropdown.is_open:
                self.current_selected_track = self.track_dropdown.get_selected_option()
                self.stop_midi()
                self.prepare_notes_for_playback()


    def draw(self):
        self.screen.fill(WHITE) # Vul de achtergrond

        self.draw_piano_roll_background()
        
        # Teken de vallende noten
        self.current_notes_on_screen.draw(self.screen)
        
        self.draw_piano_keyboard()
        self.draw_ui_elements()

        pygame.display.flip() # Update het volledige scherm


# --- Sprite voor vallende noten ---
class FallingNote(pygame.sprite.Sprite):
    def __init__(self, midi_note, start_time_ticks, duration_ticks, x_pos, width, height, current_bpm, ticks_per_beat, screen_height, keyboard_height, fall_time_seconds):
        super().__init__()
        self.midi_note = midi_note
        self.start_time_ticks = start_time_ticks # Absolute starttijd in ticks
        self.duration_ticks = duration_ticks # Duur in ticks
        self.x_pos = x_pos # X-positie op de pianorol
        self.width = width # Breedte van de noot
        self.initial_height = height # Initiële hoogte van de noot op het scherm
        
        self.current_bpm = current_bpm
        self.ticks_per_beat = ticks_per_beat
        self.screen_height = screen_height
        self.keyboard_height = keyboard_height
        self.fall_time_seconds = fall_time_seconds # Tijd die de noot nodig heeft om het scherm over te steken
        
        self.image = pygame.Surface([self.width, self.initial_height])
        self.image.fill(NOTE_COLOR)
        self.rect = self.image.get_rect()
        
        # De noot wordt bovenaan het scherm gespawnd.
        # De Y-positie zal worden berekend in update()
        self.rect.x = int(self.x_pos)
        self.rect.y = 0 # Placeholder, zal worden aangepast

    def update(self, current_playback_time_ticks):
        """
        Berekent de Y-positie en hoogte van de noot op basis van de huidige afspeeltijd.
        """
        # Converteer MIDI-ticks naar milliseconden (real-time)
        ms_per_beat = (60 / self.current_bpm) * 1000
        ticks_per_ms = self.ticks_per_beat / ms_per_beat

        start_time_ms = self.start_time_ticks / ticks_per_ms
        duration_ms = self.duration_ticks / ticks_per_ms
        current_playback_time_ms = current_playback_time_ticks / ticks_per_ms

        # Y-positie van de speellijn (onderkant van de roll)
        play_line_y = self.screen_height - self.keyboard_height

        # Tijd die de noot nodig heeft om van boven naar de speellijn te vallen (in ms)
        # Dit is de 'fall_time_seconds' van de app, geconverteerd naar ms
        fall_time_ms = self.fall_time_seconds * 1000

        # Bereken de Y-positie van de top van de noot
        # De noot moet op `start_time_ms` de `play_line_y` bereiken
        # y = play_line_y - ((start_time_ms - current_playback_time_ms) / fall_time_ms) * ROLL_HEIGHT
        
        # De 'top' van de noot beweegt
        # De 'bodem' van de noot moet de play_line_y bereiken op start_time_ms
        # Y_bodem = play_line_y
        
        # De noot beweegt met een constante snelheid in pixels/ms
        # pixels_per_ms = (ROLL_HEIGHT) / fall_time_ms
        
        # Als de noot omhoog beweegt (naar boven in de pianorol), dan is de Y-coördinaat kleiner.
        # Als de noot naar beneden beweegt, dan is de Y-coördinaat groter.
        # De noten 'komen aan' bij play_line_y op hun start_time_ms.
        # Hun *bovenkant* moet de play_line_y bereiken op (start_time_ms + duration_ms)
        
        # y_bottom (waar de noot het toetsenbord raakt) moet play_line_y zijn op start_time_ms
        # y_top (waar de noot begint) moet op play_line_y - ROLL_HEIGHT zijn op (start_time_ms - fall_time_ms)
        
        # Current time difference from target hit time
        time_to_hit_line_ms = start_time_ms - current_playback_time_ms
        
        # Y position of the bottom of the note
        # This is where the note reaches the play line at `start_time_ms`
        # If time_to_hit_line_ms is positive, the note is still above the line.
        # If negative, it has passed the line.
        
        # Y positie van de onderkant van de noot:
        # Dit is play_line_y als time_to_hit_line_ms = 0
        # Dit is play_line_y - (pixels_per_ms * time_to_hit_line_ms)
        
        # pixels_per_ms = ROLL_HEIGHT / fall_time_ms
        y_bottom_of_note = play_line_y - (time_to_hit_line_ms / fall_time_ms) * ROLL_HEIGHT
        
        # De hoogte van de noot verandert niet
        self.rect.height = self.initial_height
        
        # Bereken de Y-positie van de *bovenkant* van de noot
        self.rect.y = int(y_bottom_of_note - self.rect.height)
        
        # Verwijder noot als deze volledig buiten beeld is en voorbij de speellijn
        if self.rect.top > self.screen_height:
            self.kill() # Verwijdert de sprite van alle groepen


# --- Hoofduitvoering ---
if __name__ == "__main__":
    app = PianoRollApp()
    app.run()
