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
# MIDI noot 21 is A0, 108 is C8. Dit bereik is configureerbaar.
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
        """
        Laadt en parseert het MIDI-bestand.
        Extraheert note_on/note_off berichten met hun absolute tijden en duur.
        """
        try:
            mid = mido.MidiFile(self.midi_filepath)
        except FileNotFoundError:
            print(f"Fout: Bestand niet gevonden op {self.midi_filepath}")
            return
        except Exception as e:
            print(f"Fout bij het laden van MIDI-bestand: {e}")
            return

        active_note_starts = {} # Houdt starttijd bij van noten die nog spelen
        current_tempo = mido.bpm2tempo(120) # Standaard 120 BPM (500000 microsec/beat)

        # Collecteer alle berichten van alle tracks met hun absolute ticks
        all_messages = []
        for track in mid.tracks:
            current_track_ticks = 0
            for msg in track:
                current_track_ticks += msg.time # Delta time in ticks
                all_messages.append({'msg': msg, 'abs_ticks': current_track_ticks})

        # Sorteer alle berichten op hun absolute tick-tijd om een chronologische stroom te krijgen
        all_messages.sort(key=lambda x: x['abs_ticks'])

        current_abs_seconds = 0.0
        last_abs_ticks = 0

        for event in all_messages:
            msg = event['msg']
            abs_ticks = event['abs_ticks']

            # Bereken de verstreken tijd in seconden en update de absolute tijd
            delta_ticks = abs_ticks - last_abs_ticks
            # Update de absolute tijd in seconden, rekening houdend met het huidige tempo
            current_abs_seconds += mido.tick2second(delta_ticks, mid.ticks_per_beat, current_tempo)
            last_abs_ticks = abs_ticks

            if msg.type == 'set_tempo':
                # Als het tempo verandert, update dit voor toekomstige berekeningen
                current_tempo = msg.tempo
            elif msg.type == 'note_on' and msg.velocity > 0:
                # Sla de starttijd van de noot op
                active_note_starts[msg.note] = current_abs_seconds
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                # Als een noot stopt (note_off of note_on met velocity 0)
                if msg.note in active_note_starts:
                    start_time = active_note_starts.pop(msg.note)
                    duration = current_abs_seconds - start_time
                    if duration >= 0.001: # Zorg voor een minimale duur om "klikken" te voorkomen
                        self.parsed_notes.append({
                            'note': msg.note,
                            'start_time': start_time,
                            'duration': duration,
                            'velocity': msg.velocity
                        })
        # Sorteer de noten op starttijd om ze in chronologische volgorde te verwerken
        self.parsed_notes.sort(key=lambda n: n['start_time'])

    def get_notes(self):
        """Geeft de geparseerde lijst van noten terug."""
        return self.parsed_notes

# --- Klasse: Note (voor vallende noten) ---
class Note:
    """
    Representeert een enkele vallende noot op het scherm.
    Beheert zijn visuele eigenschappen en positie.
    """
    def __init__(self, midi_note_data, note_x_map, note_speed, screen_height, keyboard_height):
        self.note_num = midi_note_data['note']
        self.start_midi_time = midi_note_data['start_time']
        self.duration = midi_note_data['duration']
        
        # Haal de x-positie en breedte van de bijbehorende toets op via de map
        x_pos = note_x_map.get(self.note_num, 0)
        width = note_x_map.get(f"{self.note_num}_width", SCREEN_WIDTH / NUM_DISPLAYED_NOTES)
        
        self.note_speed = note_speed
        self.screen_height = screen_height
        self.keyboard_height = keyboard_height

        self.color = NOTE_COLOR
        
        # De hoogte van de noot is evenredig met zijn duur en snelheid. Minimaal 1 pixel.
        self.height = max(1, int(self.duration * self.note_speed))
        
        # Initiële y-positie wordt in update() berekend op basis van afspeeltijd.
        # Nu alleen de x, breedte en hoogte.
        self.rect = pygame.Rect(x_pos, 0, width, self.height)

    def update(self, current_midi_time):
        """
        Werkt de y-positie van de noot bij op basis van de huidige MIDI-tijd.
        Dit simuleert het 'vallen' van de noot.
        """
        # De onderkant van de noot moet de bovenkant van het toetsenbord raken
        # (screen_height - keyboard_height) precies op self.start_midi_time.
        
        # Afstand die de noot nog moet afleggen (in tijdseenheden)
        time_to_reach_bottom = self.start_midi_time - current_midi_time
        
        # De y-positie van de bovenkant van de noot.
        # Dit is de doellijn minus de afstand die hij nog moet afleggen
        # min de hoogte van de noot zelf.
        self.rect.y = (self.screen_height - self.keyboard_height) - \
                      (time_to_reach_bottom * self.note_speed) - \
                      self.rect.height

    def draw(self, screen):
        """Tekent de noot op het Pygame-scherm."""
        pygame.draw.rect(screen, self.color, self.rect)

    def is_active_and_visible(self, current_midi_time):
        """
        Controleert of de noot nog relevant is om te tekenen.
        Dit betekent dat hij ofwel zichtbaar is op het scherm,
        of nog moet beginnen met vallen maar binnenkort in beeld komt.
        """
        # Controleer of de noot nog voorbij zijn speeltijd is OF al volledig uit beeld is
        # De noot is relevant als zijn eindtijd (start + duur) nog niet is gepasseerd
        # EN als hij nog niet (volledig) onderaan het scherm is verdwenen.
        
        # Een noot is 'relevant' als zijn speeltijd nog niet voorbij is EN
        # als zijn onderkant nog niet ver onder het scherm is verdwenen.
        return (self.start_midi_time + self.duration) >= current_midi_time and \
               self.rect.top < self.screen_height + 50 # +50 voor marge onderaan
    
# --- Klasse: Keyboard ---
class Keyboard:
    """
    Tekent het virtuele pianotoetsenbord onderaan het scherm.
    Berekent de lay-out van witte en zwarte toetsen.
    """
    def __init__(self, min_midi_note, max_midi_note, screen_width, keyboard_height, screen_height):
        self.min_midi_note = min_midi_note
        self.max_midi_note = max_midi_note
        self.screen_width = screen_width
        self.keyboard_height = keyboard_height
        self.screen_height = screen_height
        self.keys = [] # Lijst om de toets-objecten op te slaan
        
        self.note_x_map = {} # Map van MIDI-noot naar x-positie en breedte

        self._generate_keyboard_layout()
        self._create_note_x_map()

    def _generate_keyboard_layout(self):
        """Genereert posities en afmetingen voor de virtuele pianotoetsen."""
        white_keys_midi_values = [0, 2, 4, 5, 7, 9, 11] # C, D, E, F, G, A, B (mod 12)
        
        white_key_count = 0
        for note_num in range(self.min_midi_note, self.max_midi_note + 1):
            if (note_num % 12) in white_keys_midi_values:
                white_key_count += 1
                
        white_key_width = self.screen_width / white_key_count
        
        current_white_x = 0
        white_key_rects = {} # Om later de posities van zwarte toetsen te bepalen
        
        # Eerste pas: genereer alle witte toetsen
        for note_num in range(self.min_midi_note, self.max_midi_note + 1):
            if (note_num % 12) in white_keys_midi_values:
                key_rect = pygame.Rect(current_white_x, self.screen_height - self.keyboard_height, 
                                       white_key_width, self.keyboard_height)
                self.keys.append({'note': note_num, 'rect': key_rect, 'color': KEY_WHITE_COLOR, 'is_black': False})
                white_key_rects[note_num] = key_rect
                current_white_x += white_key_width
        
        # Tweede pas: genereer alle zwarte toetsen bovenop de witte toetsen
        black_key_width = white_key_width * 0.6
        black_key_height = self.keyboard_height * 0.6
        
        for note_num in range(self.min_midi_note, self.max_midi_note + 1):
            if (note_num % 12) not in white_keys_midi_values: # Het is een zwarte toets
                # Zoek de *volgende* witte toets om de zwarte toets correct te positioneren.
                # Bijv. C# (MIDI noot 61) ligt links van D (MIDI noot 62).
                next_white_note = None
                for n_val in range(note_num + 1, self.max_midi_note + 1):
                    if (n_val % 12) in white_keys_midi_values:
                        next_white_note = n_val
                        break
                
                if next_white_note is not None and next_white_note in white_key_rects:
                    next_white_key_rect = white_key_rects[next_white_note]
                    # Plaats de zwarte toets gecentreerd tussen het einde van de vorige witte toets
                    # en het begin van de volgende witte toets, of simpelweg over het begin van de volgende.
                    # Voor dit voorbeeld, centreren we hem over de overgang.
                    # Een meer accurate positionering zou kijken naar de absolute afstand tussen witte toetsen.
                    
                    # Vereenvoudigde positionering: plaats de zwarte toets in het midden van de ruimte
                    # tussen de 'vorige' witte toets en de 'huidige' witte toets.
                    # Dit betekent de x-positie van de zwarte toets is de x-positie van de volgende witte toets
                    # minus de helft van de breedte van de zwarte toets.
                    x_pos = next_white_key_rect.left - (black_key_width / 2)
                    
                    key_rect = pygame.Rect(x_pos, self.screen_height - self.keyboard_height - black_key_height, 
                                           black_key_width, black_key_height)
                    self.keys.append({'note': note_num, 'rect': key_rect, 'color': KEY_BLACK_COLOR, 'is_black': True})

        # Sorteer de toetsen zodat witte toetsen eerst worden getekend (laagste z-index),
        # en dan de zwarte toetsen (hoogste z-index) om overlappingen correct weer te geven.
        self.keys.sort(key=lambda k: k['is_black']) # False (wit) komt voor True (zwart)

    def _create_note_x_map(self):
        """
        Maakt een map van MIDI-nootnummer naar de x-positie en breedte van de corresponderende toets.
        Dit is essentieel voor het correct positioneren van vallende noten.
        """
        for key_info in self.keys:
            self.note_x_map[key_info['note']] = key_info['rect'].x
            self.note_x_map[f"{key_info['note']}_width"] = key_info['rect'].width

    def draw(self, screen):
        """Tekent het virtuele toetsenbord op het Pygame-scherm."""
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
            print("Geen noten gevonden in MIDI-bestand. Applicatie wordt afgesloten.")
            self.running = False
            return

        # Initialiseer het toetsenbord en krijg de mapping voor noten
        self.keyboard = Keyboard(MIN_MIDI_NOTE, MAX_MIDI_NOTE, SCREEN_WIDTH, KEYBOARD_HEIGHT, SCREEN_HEIGHT)
        self.active_notes = [] # Lijst van Note-objecten die momenteel vallen/zichtbaar zijn
        
        self.midi_playback_time = 0.0 # Huidige tijd in de MIDI-afspeling (seconde)
        self.note_data_index = 0 # Index om bij te houden welke noten al zijn 'geactiveerd'

        # De tijd die het kost voor een noot om van de bovenkant van het zichtbare scherm
        # naar het toetsenbord te vallen. Dit helpt bij het beslissen wanneer een noot te activeren.
        self.screen_travel_time = (SCREEN_HEIGHT - KEYBOARD_HEIGHT) / NOTE_SPEED

    def _handle_input(self):
        """Verwerkt Pygame-events, zoals het sluiten van het venster."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

    def _update_notes(self, dt):
        """Werkt de status en positie van alle actieve noten bij."""
        self.midi_playback_time += dt # Verhoog de gesimuleerde afspeeltijd

        # Voeg nieuwe noten toe aan de actieve lijst.
        # We activeren een noot wanneer zijn 'landingtijd' (start_time)
        # binnen de huidige afspeeltijd plus de schermreistijd valt.
        while self.note_data_index < len(self.all_midi_notes_data) and \
              self.all_midi_notes_data[self.note_data_index]['start_time'] <= self.midi_playback_time + self.screen_travel_time:
            
            note_data = self.all_midi_notes_data[self.note_data_index]
            
            # Alleen noten toevoegen die binnen ons gedefinieerde MIDI-bereik vallen
            if MIN_MIDI_NOTE <= note_data['note'] <= MAX_MIDI_NOTE:
                new_note = Note(note_data, self.keyboard.note_x_map, NOTE_SPEED, SCREEN_HEIGHT, KEYBOARD_HEIGHT)
                self.active_notes.append(new_note)
            
            self.note_data_index += 1

        # Update de y-positie van alle actieve noten.
        for note in self.active_notes:
            note.update(self.midi_playback_time)

        # Verwijder noten die niet langer relevant zijn (uit beeld of speeltijd voorbij).
        # We filteren op noten die nog steeds actief en/of zichtbaar zijn.
        self.active_notes = [
            note for note in self.active_notes 
            if note.is_active_and_visible(self.midi_playback_time)
        ]

    def _draw(self):
        """Tekent alle elementen op het scherm."""
        self.screen.fill(BLACK) # Maak de achtergrond leeg (pianorol achtergrond)

        # Teken eerst de vallende noten
        for note in self.active_notes:
            note.draw(self.screen)

        # Teken vervolgens het toetsenbord, zodat het over de noten heen ligt
        self.keyboard.draw(self.screen)

        pygame.display.flip() # Update het hele scherm

    def run(self):
        """Start de hoofdgame-loop van de applicatie."""
        while self.running:
            # Bereken de delta tijd (tijd sinds laatste frame)
            # Dit zorgt voor frame-rate onafhankelijke beweging
            dt = self.clock.tick(60) / 1000.0 # Max 60 FPS

            self._handle_input()
            self._update_notes(dt)
            self._draw()

        pygame.quit()
        print("Neothesia Pygame MVP applicatie afgesloten.")

# --- Hoofdprogramma uitvoeren ---
if __name__ == "__main__":
    # VERVANG DIT MET HET PAD NAAR JOUW MIDI-BESTAND
    # Zorg dat je een .mid bestand hebt om te testen!
    # Voorbeeld: midi_file_to_play = "my_awesome_song.mid"
    midiFileName = "Alan Walker - Faded (Piano Cover Tutorial - Easy) (midi by Carlo Prato) (www.cprato.com).mid"
    midi_file_to_play = f"../../midi/{midiFileName}" # Pas dit aan naar jouw MIDI-bestand
    if(os.name == "nt"):
        # Windows-specifiek pad
        midi_file_to_play =  f"C:\\Users\\m.erasmus\\OneDrive - Fugro\\Programmacode\\AI_gerelateerd\\github\\Neothasia\\midi\\{midiFileName}" # os.path.abspath(midi_file_to_play)

    if not os.path.exists(midi_file_to_play):
        print(f"\nFOUT: Het MIDI-bestand '{midi_file_to_play}' is niet gevonden.")
        print("Plaats een MIDI-bestand in dezelfde map als dit script of pas het pad aan.")
        print("Het programma kan niet starten zonder een geldig MIDI-bestand.")
    else:
        # Start de Neothesia applicatie
        app = NeothesiaApp(midi_file_to_play)
        if app.running: # Controleer of de MIDI-parser succesvol was
            app.run()
