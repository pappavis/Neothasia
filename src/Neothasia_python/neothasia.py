# 20250601 ref https://gemini.google.com/gem/coding-partner/7a390be7cebfa0ec
# zie ook https://synthesiagame.com

import pygame
import mido
import os
import time

# --- Constanten voor de weergave ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
NOTE_SPEED = 300 # pixels per seconde (hoe snel noten vallen, hoger is sneller)
KEYBOARD_HEIGHT = 100 # Hoogte van het virtuele toetsenbord onderaan

# Kleuren
BLACK = (0, 0, 0)
NOTE_COLOR = (0, 200, 0) # Groen voor noten
KEY_WHITE_COLOR = (255, 255, 255)
KEY_BLACK_COLOR = (50, 50, 50)
KEY_OUTLINE_COLOR = (100, 100, 100) # Rand van toetsen

# MIDI nootbereik dat we weergeven (bijv. C3 tot C6)
MIN_MIDI_NOTE = 48 # C3
MAX_MIDI_NOTE = 84 # C6 (3 octaven + 1 noot, 37 toetsen)
NUM_DISPLAYED_NOTES = MAX_MIDI_NOTE - MIN_MIDI_NOTE + 1 # Aantal noten die we visualiseren

# --- Klasse: MidiParser ---
class MidiParser:
    """
    Verantwoordelijk voor het laden en parsen van MIDI-bestanden
    en het extraheren van nootinformatie.
    """
    def __init__(self, midi_filepath):
        self.midi_filepath = midi_filepath
        self.parsed_notes = []
        self._load_midi()

    def _load_midi(self):
        """Laadt en parseert het MIDI-bestand."""
        try:
            mid = mido.MidiFile(self.midi_filepath)
        except FileNotFoundError:
            print(f"Fout: Bestand niet gevonden op {self.midi_filepath}")
            return
        except Exception as e:
            print(f"Fout bij het laden van MIDI-bestand: {e}")
            return

        active_note_starts = {}
        current_tempo = mido.bpm2tempo(120) # Standaard 120 BPM

        all_messages = []
        for track in mid.tracks:
            current_time = 0
            for msg in track:
                current_time += msg.time # Delta time in ticks
                all_messages.append({'msg': msg, 'abs_ticks': current_time})

        all_messages.sort(key=lambda x: x['abs_ticks'])

        current_abs_seconds = 0.0
        last_abs_ticks = 0

        for event in all_messages:
            msg = event['msg']
            abs_ticks = event['abs_ticks']

            delta_ticks = abs_ticks - last_abs_ticks
            current_abs_seconds += mido.tick2second(delta_ticks, mid.ticks_per_beat, current_tempo)
            last_abs_ticks = abs_ticks

            if msg.type == 'set_tempo':
                current_tempo = msg.tempo
            elif msg.type == 'note_on' and msg.velocity > 0:
                active_note_starts[msg.note] = current_abs_seconds
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                if msg.note in active_note_starts:
                    start_time = active_note_starts.pop(msg.note)
                    duration = current_abs_seconds - start_time
                    if duration > 0:
                        self.parsed_notes.append({
                            'note': msg.note,
                            'start_time': start_time,
                            'duration': duration,
                            'velocity': msg.velocity
                        })
        self.parsed_notes.sort(key=lambda n: n['start_time'])

    def get_notes(self):
        return self.parsed_notes

# --- Klasse: Note (voor vallende noten) ---
class Note:
    """
    Representeert een enkele vallende noot op het scherm.
    """
    def __init__(self, midi_note_data, note_x_map, note_speed, screen_height, keyboard_height):
        self.note_num = midi_note_data['note']
        self.start_midi_time = midi_note_data['start_time']
        self.duration = midi_note_data['duration']
        
        # Haal de x-positie en breedte van de bijbehorende toets op
        x_pos = note_x_map.get(self.note_num, 0)
        width = note_x_map.get(f"{self.note_num}_width", SCREEN_WIDTH / NUM_DISPLAYED_NOTES)
        
        self.note_speed = note_speed
        self.screen_height = screen_height
        self.keyboard_height = keyboard_height

        self.color = NOTE_COLOR
        
        # De hoogte van de noot is evenredig met zijn duur en snelheid, minimaal 1 pixel
        self.height = max(1, int(self.duration * self.note_speed))
        
        # Initiële y-positie wordt later in update berekend, nu zetten we alleen de x en breedte
        self.rect = pygame.Rect(x_pos, 0, width, self.height)

    def update(self, current_midi_time):
        """
        Werkt de y-positie van de noot bij op basis van de huidige MIDI-tijd.
        """
        # De onderkant van de noot moet de keyboard_y_line raken op self.start_midi_time
        # De y-positie van de bovenkant van de noot:
        self.rect.y = (self.screen_height - self.keyboard_height) - \
                      (self.start_midi_time - current_midi_time) * self.note_speed - \
                      self.rect.height

    def draw(self, screen):
        """Tekent de noot op het scherm."""
        pygame.draw.rect(screen, self.color, self.rect)

    def is_visible(self):
        """Controleert of de noot nog op het scherm zichtbaar is."""
        # De noot is zichtbaar zolang zijn bovenkant niet onder de onderkant van het scherm is
        # en zijn onderkant niet boven de bovenkant van het scherm is.
        # En zolang zijn speeltijd niet voorbij is.
        return self.rect.top < self.screen_height and self.rect.bottom > 0

# --- Klasse: Keyboard ---
class Keyboard:
    """
    Tekent het virtuele pianotoetsenbord onderaan het scherm.
    """
    def __init__(self, min_midi_note, max_midi_note, screen_width, keyboard_height, screen_height):
        self.min_midi_note = min_midi_note
        self.max_midi_note = max_midi_note
        self.screen_width = screen_width
        self.keyboard_height = keyboard_height
        self.screen_height = screen_height
        self.keys = self._generate_keyboard_layout()
        
        # Deze map wordt gebruikt om de x-positie en breedte voor vallende noten op te halen
        self.note_x_map = self._create_note_x_map()

    def _generate_keyboard_layout(self):
        """Genereert posities en breedtes voor de virtuele pianotoetsen."""
        keyboard_keys = []
        white_keys_midi_values = [0, 2, 4, 5, 7, 9, 11]
        
        white_key_count = 0
        for note_num in range(self.min_midi_note, self.max_midi_note + 1):
            if (note_num % 12) in white_keys_midi_values:
                white_key_count += 1
                
        white_key_width = self.screen_width / white_key_count
        
        current_white_x = 0
        white_key_rects = {} # Om later de posities van zwarte toetsen te bepalen
        
        # Eerste pas: teken alle witte toetsen
        for note_num in range(self.min_midi_note, self.max_midi_note + 1):
            if (note_num % 12) in white_keys_midi_values:
                key_rect = pygame.Rect(current_white_x, self.screen_height - self.keyboard_height, 
                                       white_key_width, self.keyboard_height)
                keyboard_keys.append({'note': note_num, 'rect': key_rect, 'color': KEY_WHITE_COLOR, 'is_black': False})
                white_key_rects[note_num] = key_rect
                current_white_x += white_key_width
        
        # Tweede pas: teken alle zwarte toetsen bovenop de witte toetsen
        black_key_width = white_key_width * 0.6
        black_key_height = self.keyboard_height * 0.6
        
        for note_num in range(self.min_midi_note, self.max_midi_note + 1):
            if (note_num % 12) not in white_keys_midi_values: # Het is een zwarte toets
                # De exacte positie van de zwarte toets is afhankelijk van de witte toetsen eromheen
                # Voorbeeld: C# (note % 12 == 1) ligt tussen C (note % 12 == 0) en D (note % 12 == 2)
                
                # De volgende witte toets is vaak de referentie.
                # Bijv. C# (MIDI noot 61) ligt links van D (MIDI noot 62)
                # D# (MIDI noot 63) ligt links van E (MIDI noot 64)
                # F# (MIDI noot 66) ligt links van G (MIDI noot 67)
                # G# (MIDI noot 68) ligt links van A (MIDI noot 69)
                # A# (MIDI noot 70) ligt links van B (MIDI noot 71)

                # Zoek de *volgende* witte toets (als die bestaat binnen het bereik)
                next_white_note = None
                for n_val in range(note_num + 1, self.max_midi_note + 1):
                    if (n_val % 12) in white_keys_midi_values:
                        next_white_note = n_val
                        break
                
                # Als er een volgende witte toets is, positioneer de zwarte toets relatief daaraan
                if next_white_note is not None and next_white_note in white_key_rects:
                    next_white_key_rect = white_key_rects[next_white_note]
                    x_pos = next_white_key_rect.left - (black_key_width / 2)
                    
                    key_rect = pygame.Rect(x_pos, self.screen_height - self.keyboard_height - black_key_height, 
                                           black_key_width, black_key_height)
                    keyboard_keys.append({'note': note_num, 'rect': key_rect, 'color': KEY_BLACK_COLOR, 'is_black': True})

        keyboard_keys.sort(key=lambda k: k['is_black']) # False (wit) komt voor True (zwart)
        return keyboard_keys

    def _create_note_x_map(self):
        """Maakt een map van MIDI-nootnummer naar de x-positie en breedte van de corresponderende toets."""
        note_map = {}
        for key_info in self.keys:
            note_map[key_info['note']] = key_info['rect'].x
            note_map[f"{key_info['note']}_width"] = key_info['rect'].width
        return note_map

    def draw(self, screen):
        """Tekent het virtuele toetsenbord op het scherm."""
        for key_info in self.keys:
            pygame.draw.rect(screen, key_info['color'], key_info['rect'])
            pygame.draw.rect(screen, KEY_OUTLINE_COLOR, key_info['rect'], 1) # Randje

# --- Hoofdklasse: NeothesiaApp ---
class NeothesiaApp:
    """
    De hoofdapplicatieklasse voor de Neothesia visualizer.
    Beheert de Pygame-loop, rendering en game-logica.
    """
    def __init__(self, midi_filepath):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Neothesia Python MVP")
        self.clock = pygame.time.Clock()
        self.running = True

        self.midi_parser = MidiParser(midi_filepath)
        self.all_midi_notes_data = self.midi_parser.get_notes()
        
        if not self.all_midi_notes_data:
            print("Geen noten gevonden in MIDI-bestand, sluiten applicatie.")
            self.running = False
            return

        self.keyboard = Keyboard(MIN_MIDI_NOTE, MAX_MIDI_NOTE, SCREEN_WIDTH, KEYBOARD_HEIGHT, SCREEN_HEIGHT)
        self.active_notes = []
        self.midi_playback_time = 0.0
        self.note_data_index = 0

        # Tijd die het kost voor een noot om van de bovenkant van het scherm naar het toetsenbord te vallen.
        self.screen_travel_time = (SCREEN_HEIGHT - KEYBOARD_HEIGHT) / NOTE_SPEED

    def _handle_input(self):
        """Verwerkt Pygame-events zoals afsluiten."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

    def _update_notes(self, dt):
        """Werkt de status en positie van noten bij."""
        self.midi_playback_time += dt

        # Voeg nieuwe noten toe aan de actieve lijst als hun starttijd nadert
        while self.note_data_index < len(self.all_midi_notes_data) and \
              self.all_midi_notes_data[self.note_data_index]['start_time'] <= self.midi_playback_time + self.screen_travel_time:
            
            note_data = self.all_midi_notes_data[self.note_data_index]
            
            # Voeg alleen noten toe die binnen ons display-bereik vallen
            if MIN_MIDI_NOTE <= note_data['note'] <= MAX_MIDI_NOTE:
                new_note = Note(note_data, self.keyboard.note_x_map, NOTE_SPEED, SCREEN_HEIGHT, KEYBOARD_HEIGHT)
                self.active_notes.append(new_note)
            
            self.note_data_index += 1

        # Update de positie van alle actieve noten
        for note in self.active_notes:
            note.update(self.midi_playback_time)

        # Verwijder noten die niet langer zichtbaar zijn
        # Een noot is niet meer zichtbaar als zijn onderkant onder het toetsenbord is verdwenen EN
        # zijn speeltijd (start_time + duration) voorbij is.
        self.active_notes = [
            note for note in self.active_notes 
            if note.rect.top < SCREEN_HEIGHT and (note.start_midi_time + note.duration) >= self.midi_playback_time
        ]


    def _draw(self):
        """Tekent alle elementen op het scherm."""
        self.screen.fill(BLACK) # Achtergrond wissen

        # Teken vallende noten
        for note in self.active_notes:
            note.draw(self.screen)

        # Teken het toetsenbord
        self.keyboard.draw(self.screen)

        pygame.display.flip() # Scherm updaten

    def run(self):
        """Start de hoofdgame-loop."""
        while self.running:
            dt = self.clock.tick(60) / 1000.0 # Delta tijd in seconden (max 60 FPS)

            self._handle_input()
            self._update_notes(dt)
            self._draw()

        pygame.quit()
        print("Applicatie afgesloten.")

# --- Hoofdprogramma uitvoeren ---
if __name__ == "__main__":
    # VERVANG DIT MET HET PAD NAAR JOUW MIDI-BESTAND
    midi_file_to_play = f"/Users/michiele/Yandex.Disk.localized/michiele/Muziek/Midi bestanden/Faded - Alan Walker (WIP).mid" 
    
    if not os.path.exists(midi_file_to_play):
        print(f"\nLET OP: Het MIDI-bestand '{midi_file_to_play}' is niet gevonden.")
        print("Plaats een MIDI-bestand in dezelfde map als dit script of pas het pad aan.")
        print("Het programma kan niet starten zonder MIDI-bestand.")
    else:
        app = NeothesiaApp(midi_file_to_play)
        app.run()
    