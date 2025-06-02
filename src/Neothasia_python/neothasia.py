import pygame
import mido
import os
import time
import rtmidi # Voor MIDI output
import fluidsynth # Voor audio synthese met soundfonts
# version a8e6b1d2-c3f4-4e5a-8b9c-0d1e2f3a4b5c

# --- Constanten voor de weergave ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
NOTE_SPEED = 300 # pixels per seconde (hoe snel noten vallen, hoger is sneller)
KEYBOARD_HEIGHT = 100 # Hoogte van het virtuele toetsenbord onderaan

# Kleuren
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
NOTE_COLOR = (0, 200, 0) # Groen voor noten
KEY_WHITE_COLOR = (255, 255, 255)
KEY_BLACK_COLOR = (50, 50, 50)
KEY_OUTLINE_COLOR = (100, 100, 100) # Rand van toetsen
HIGHLIGHT_COLOR = (255, 255, 0) # Geel voor toetsenbord highlight

# MIDI nootbereik dat we weergeven (bijv. C3 tot C6)
MIN_MIDI_NOTE = 48 # C3
MAX_MIDI_NOTE = 84 # C6 (3 octaven + 1 noot, 37 toetsen)
NUM_DISPLAYED_NOTES = MAX_MIDI_NOTE - MIN_MIDI_NOTE + 1

# --- Helper functie voor nootnamen ---
def get_note_name(midi_note_number):
    """Converteert een MIDI-nootnummer naar een nootnaam (bijv. C4, A#3)."""
    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    octave = (midi_note_number // 12) - 1 # MIDI C0 is noot 12, dus C-1 is 0
    note_name = note_names[midi_note_number % 12]
    return f"{note_name}{octave}"

# --- Klasse: MidiParser ---
class MidiParser:
    """
    Verantwoordelijk voor het laden en parsen van MIDI-bestanden
    en het extraheren van nootinformatie per track/instrument.
    """
    def __init__(self, midi_filepath):
        self.midi_filepath = midi_filepath
        self.tracks_data = {} # {track_idx: {'notes': [], 'name': 'Track Name'}}
        self._load_midi()

    def _load_midi(self):
        """
        Laadt en parseert het MIDI-bestand.
        Extraheert note_on/note_off berichten met hun absolute tijden en duur,
        gegroepeerd per MIDI-track.
        """
        try:
            mid = mido.MidiFile(self.midi_filepath)
        except FileNotFoundError:
            print(f"Fout: Bestand niet gevonden op {self.midi_filepath}")
            return
        except Exception as e:
            print(f"Fout bij het laden van MIDI-bestand: {e}")
            return

        # Initialiseer tempo (standaard 120 BPM) en ticks_per_beat
        ticks_per_beat = mid.ticks_per_beat
        default_tempo = mido.bpm2tempo(120)

        for i, track in enumerate(mid.tracks):
            track_name = f"Track {i}"
            # Probeer een tracknaam te vinden
            for msg in track:
                if msg.type == 'track_name':
                    track_name = msg.name
                    break
            
            self.tracks_data[i] = {'name': track_name, 'notes': []}
            
            active_note_starts = {} # {note_number: start_time_in_seconds}
            current_abs_seconds = 0.0
            last_abs_ticks = 0
            current_tempo = default_tempo # Reset tempo per track for simplicity (might be inaccurate for global tempo changes)

            for msg in track:
                delta_ticks = msg.time
                
                # Update absolute tijd
                current_abs_seconds += mido.tick2second(delta_ticks, ticks_per_beat, current_tempo)

                if msg.type == 'set_tempo':
                    current_tempo = msg.tempo
                elif msg.type == 'note_on' and msg.velocity > 0:
                    active_note_starts[msg.note] = current_abs_seconds
                elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                    if msg.note in active_note_starts:
                        start_time = active_note_starts.pop(msg.note)
                        duration = current_abs_seconds - start_time
                        if duration >= 0.001: # Filter zeer korte (0-duur) noten
                            self.tracks_data[i]['notes'].append({
                                'note': msg.note,
                                'start_time': start_time,
                                'duration': duration,
                                'velocity': msg.velocity,
                                'track_idx': i # Voeg track-index toe
                            })
            self.tracks_data[i]['notes'].sort(key=lambda n: n['start_time'])

    def get_track_names(self):
        """Geeft een lijst van (track_idx, track_name) tuples terug."""
        return [(idx, data['name']) for idx, data in self.tracks_data.items()]

    def get_notes_for_track(self, track_idx):
        """Geeft de geparseerde noten voor een specifieke track terug."""
        return self.tracks_data.get(track_idx, {}).get('notes', [])

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
        self.velocity = midi_note_data['velocity']
        
        # Haal de x-positie en breedte van de bijbehorende toets op
        x_pos = note_x_map.get(self.note_num, 0)
        width = note_x_map.get(f"{self.note_num}_width", SCREEN_WIDTH / NUM_DISPLAYED_NOTES)
        
        self.note_speed = note_speed
        self.screen_height = screen_height
        self.keyboard_height = keyboard_height

        self.color = NOTE_COLOR
        
        # De hoogte van de noot is evenredig met zijn duur en snelheid. Minimaal 1 pixel.
        self.height = max(1, int(self.duration * self.note_speed))
        
        # Initiële y-positie wordt in update() berekend op basis van afspeeltijd.
        self.rect = pygame.Rect(x_pos, 0, width, self.height)

    def update(self, current_midi_time):
        """
        Werkt de y-positie van de noot bij op basis van de huidige MIDI-tijd.
        Dit simuleert het 'vallen' van de noot.
        """
        # De onderkant van de noot moet de bovenkant van het toetsenbord raken
        # (screen_height - keyboard_height) precies op self.start_midi_time.
        
        time_to_reach_bottom = self.start_midi_time - current_midi_time
        
        self.rect.y = (self.screen_height - self.keyboard_height) - \
                      (time_to_reach_bottom * self.note_speed) - \
                      self.rect.height

    def draw(self, screen):
        """Tekent de noot op het Pygame-scherm."""
        pygame.draw.rect(screen, self.color, self.rect)

    def is_active_and_visible(self, current_midi_time):
        """
        Controleert of de noot nog relevant is om te tekenen en te verwerken.
        Een noot is relevant als zijn eindtijd (start + duur) nog niet is gepasseerd
        EN hij nog op het scherm (of net daarbuiten) is.
        """
        return (self.start_midi_time + self.duration + 0.1) >= current_midi_time and \
               self.rect.top < self.screen_height # Check if the top is still above screen bottom

# --- Klasse: Keyboard ---
class Keyboard:
    """
    Tekent het virtuele pianotoetsenbord onderaan het scherm.
    Beheert de lay-out van witte en zwarte toetsen en hun highlighting.
    """
    def __init__(self, min_midi_note, max_midi_note, screen_width, keyboard_height, screen_height):
        self.min_midi_note = min_midi_note
        self.max_midi_note = max_midi_note
        self.screen_width = screen_width
        self.keyboard_height = keyboard_height
        self.screen_height = screen_height
        self.keys = [] # Lijst om de toets-objecten op te slaan
        self.active_keys = set() # Set van MIDI-noten die momenteel ingedrukt zijn (voor highlighting)
        
        self.note_x_map = {} # Map van MIDI-noot naar x-positie en breedte (voor vallende noten)

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
        white_key_rects = {} 
        
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
                next_white_note = None
                for n_val in range(note_num + 1, self.max_midi_note + 1):
                    if (n_val % 12) in white_keys_midi_values:
                        next_white_note = n_val
                        break
                
                if next_white_note is not None and next_white_note in white_key_rects:
                    next_white_key_rect = white_key_rects[next_white_note]
                    x_pos = next_white_key_rect.left - (black_key_width / 2)
                    
                    key_rect = pygame.Rect(x_pos, self.screen_height - self.keyboard_height - black_key_height, 
                                           black_key_width, black_key_height)
                    self.keys.append({'note': note_num, 'rect': key_rect, 'color': KEY_BLACK_COLOR, 'is_black': True})

        self.keys.sort(key=lambda k: k['is_black']) # Witte toetsen eerst, dan zwarte toetsen

    def _create_note_x_map(self):
        """
        Maakt een map van MIDI-nootnummer naar de x-positie en breedte van de corresponderende toets.
        """
        for key_info in self.keys:
            self.note_x_map[key_info['note']] = key_info['rect'].x
            self.note_x_map[f"{key_info['note']}_width"] = key_info['rect'].width

    def press_key(self, midi_note_number):
        """Markeert een toets als ingedrukt."""
        if self.min_midi_note <= midi_note_number <= self.max_midi_note:
            self.active_keys.add(midi_note_number)

    def release_key(self, midi_note_number):
        """Markeert een toets als losgelaten."""
        if midi_note_number in self.active_keys:
            self.active_keys.remove(midi_note_number)

    def draw(self, screen):
        """Tekent het virtuele toetsenbord en hun labels op het scherm."""
        font = pygame.font.Font(None, 20) # Klein lettertype voor nootnamen

        for key_info in self.keys:
            # Teken de basiskleur van de toets
            current_color = key_info['color']
            if key_info['note'] in self.active_keys:
                current_color = HIGHLIGHT_COLOR # Highlight als toets ingedrukt is

            pygame.draw.rect(screen, current_color, key_info['rect'])
            pygame.draw.rect(screen, KEY_OUTLINE_COLOR, key_info['rect'], 1) # Randje

            # Teken de nootnaam
            note_name_str = get_note_name(key_info['note'])
            text_surface = font.render(note_name_str, True, BLACK if current_color == KEY_WHITE_COLOR else WHITE)
            
            # Positioneer de tekst op de toets
            text_rect = text_surface.get_rect(centerx=key_info['rect'].centerx)
            if key_info['is_black']:
                # Zwarte toetsen: tekst bovenaan
                text_rect.top = key_info['rect'].top + 5
            else:
                # Witte toetsen: tekst onderaan
                text_rect.bottom = key_info['rect'].bottom - 5
            screen.blit(text_surface, text_rect)

# --- Klasse: MidiPlayer (voor audio afspelen) ---
class MidiPlayer:
    """
    Beheert het afspelen van MIDI-noten via fluidsynth.
    """
    def __init__(self, soundfont_path):
        self.fs = None
        self.soundfont_path = soundfont_path
        self._init_fluidsynth()
        self.midi_out = None # rtmidi output port
        self._init_midi_output()

    def _init_fluidsynth(self):
        """Initialiseert fluidsynth en laadt de soundfont."""
        try:
            # fluidsynth.init() kan problemen geven op sommige systemen.
            # We initialiseren direct de Synth.
            # Instellingen voor lage latentie (kan worden geoptimaliseerd)
            self.fs = fluidsynth.Synth()
            self.fs.start(driver='alsa', device='default') # 'alsa' for Linux, 'coreaudio' for macOS, 'dsound' for Windows. Or 'portaudio' for cross-platform.
            
            if not os.path.exists(self.soundfont_path):
                print(f"Fout: Soundfont-bestand niet gevonden op {self.soundfont_path}")
                print("Download een .sf2 soundfont (bijv. 'GeneralUser GS FluidSynth.sf2') en plaats het op het juiste pad.")
                self.fs = None # Disable fluidsynth if soundfont is missing
                return

            sfid = self.fs.sfload(self.soundfont_path)
            self.fs.program_select(0, sfid, 0, 0) # Kanaal 0, Soundfont ID, Bank 0, Preset 0 (Grand Piano)
            print(f"FluidSynth geladen met soundfont: {self.soundfont_path}")
        except Exception as e:
            print(f"Fout bij initialiseren FluidSynth: {e}")
            print("Zorg ervoor dat FluidSynth zelf is geïnstalleerd op je systeem en de soundfont beschikbaar is.")
            self.fs = None

    def _init_midi_output(self):
        """Initialiseert rtmidi output voor directe MIDI-berichten."""
        try:
            self.midi_out = rtmidi.MidiOut()
            available_ports = self.midi_out.get_ports()
            
            if available_ports:
                print("Beschikbare MIDI-uitvoerpoorten:", available_ports)
                # Probeer een virtuele poort te openen of een bestaande
                try:
                    self.midi_out.open_virtual_port("Neothesia MIDI Out")
                    print("Virtuele MIDI-uitvoerpoort geopend.")
                except rtmidi.midiutil.PortNotOpenError:
                    print("Kon geen virtuele poort openen, probeer de eerste beschikbare.")
                    self.midi_out.open_port(0) # Open de eerste beschikbare poort
                    print(f"Geopende MIDI-uitvoerpoort: {self.midi_out.get_port_name(0)}")
            else:
                print("Geen MIDI-uitvoerpoorten beschikbaar. MIDI-output zal niet werken.")
                self.midi_out = None
        except Exception as e:
            print(f"Fout bij initialiseren rtmidi: {e}")
            self.midi_out = None

    def play_note(self, note_num, velocity=100, channel=0):
        """Speelt een MIDI-noot af (note_on)."""
        if self.fs:
            self.fs.noteon(channel, note_num, velocity)
        if self.midi_out:
            self.midi_out.send_message([mido.Message('note_on', note=note_num, velocity=velocity, channel=channel).bytes()])

    def stop_note(self, note_num, channel=0):
        """Stopt een MIDI-noot (note_off)."""
        if self.fs:
            self.fs.noteoff(channel, note_num)
        if self.midi_out:
            self.midi_out.send_message([mido.Message('note_off', note=note_num, velocity=0, channel=channel).bytes()])

    def stop_all_notes(self):
        """Stopt alle spelende noten."""
        if self.fs:
            self.fs.all_notes_off()
        if self.midi_out:
            # Stuur 'all notes off' control change message
            self.midi_out.send_message([mido.Message('control_change', control=123, value=0).bytes()])
            
    def close(self):
        """Sluit de MIDI-speler en fluidsynth."""
        if self.fs:
            self.fs.delete()
        if self.midi_out:
            self.midi_out.close_port()

# --- Hoofdklasse: NeothesiaApp ---
class NeothesiaApp:
    """
    De hoofdapplicatieklasse voor de Neothesia visualizer.
    Beheert de Pygame-loop, rendering, game-logica, en audio-afspelen.
    """
    def __init__(self, midi_filepath, soundfont_path):
        pygame.init()
        pygame.font.init() # Initialiseer font module
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Neothesia Python MVP")
        self.clock = pygame.time.Clock()
        
        self.midi_player = MidiPlayer(soundfont_path)
        
        self.midi_parser = MidiParser(midi_filepath)
        self.all_midi_tracks_data = self.midi_parser.tracks_data # Alle data, per track

        if not self.all_midi_tracks_data:
            print("Geen noten/tracks gevonden in MIDI-bestand. Applicatie wordt afgesloten.")
            self.running = False
            return

        self.keyboard = Keyboard(MIN_MIDI_NOTE, MAX_MIDI_NOTE, SCREEN_WIDTH, KEYBOARD_HEIGHT, SCREEN_HEIGHT)
        self.active_notes_on_screen = [] # Note-objecten die nu op het scherm zijn
        self.playing_midi_notes = {} # {note_num: time_on_midi_player} voor audio

        self.midi_playback_time = 0.0 # Huidige tijd in de MIDI-afspeling (seconde)
        self.note_data_index = 0 # Index in de GEFILTERDE notenlijst

        self.screen_travel_time = (SCREEN_HEIGHT - KEYBOARD_HEIGHT) / NOTE_SPEED

        self.playback_state = 'stopped' # 'stopped', 'playing', 'paused'
        self.selected_track_idx = None # Track die wordt afgespeeld en gevisualiseerd

        self._initialize_track_selection()
        
        self.running = True

    def _initialize_track_selection(self):
        """
        Toont beschikbare tracks en laat de gebruiker er een selecteren.
        """
        print("\n--- Selecteer een MIDI-track ---")
        track_options = self.midi_parser.get_track_names()
        
        if not track_options:
            print("Geen tracks gevonden in het MIDI-bestand. Kan niet verder.")
            self.running = False
            return
            
        for idx, name in track_options:
            print(f"[{idx}] - {name}")
        
        while self.selected_track_idx is None:
            try:
                choice = input("Voer het nummer van de gewenste track in: ")
                choice_idx = int(choice)
                if choice_idx in self.all_midi_tracks_data:
                    self.selected_track_idx = choice_idx
                    self.filtered_midi_notes_data = sorted(self.all_midi_tracks_data[self.selected_track_idx]['notes'], key=lambda n: n['start_time'])
                    print(f"Track '{self.all_midi_tracks_data[self.selected_track_idx]['name']}' geselecteerd.")
                else:
                    print("Ongeldige invoer. Probeer opnieuw.")
            except ValueError:
                print("Ongeldige invoer. Voer een nummer in.")
        
        if not self.filtered_midi_notes_data:
            print(f"Track '{self.all_midi_tracks_data[self.selected_track_idx]['name']}' bevat geen noten. Applicatie wordt afgesloten.")
            self.running = False


    def _handle_input(self):
        """Verwerkt Pygame-events, zoals het sluiten van het venster en toetsaanslagen."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if self.playback_state == 'playing':
                        self.playback_state = 'paused'
                        self.midi_player.stop_all_notes() # Stop alle audio bij pauze
                        print("Pauze.")
                    elif self.playback_state == 'paused' or self.playback_state == 'stopped':
                        self.playback_state = 'playing'
                        print("Afspelen hervat.")
                elif event.key == pygame.K_s: # 's' voor stop
                    self.playback_state = 'stopped'
                    self.midi_playback_time = 0.0
                    self.note_data_index = 0
                    self.active_notes_on_screen = []
                    self.midi_player.stop_all_notes()
                    self.playing_midi_notes = {} # Reset actieve audio noten
                    self.keyboard.active_keys.clear() # Reset toetsenbord highlight
                    print("Gestopt en gereset.")
                
                # Voor track selectie tijdens runtime (optioneel, kan complexer worden)
                # Als je dit wilt, zou je een apart UI-scherm of overlay nodig hebben.
                # Voor nu, doen we de selectie bij start.

    def _update_playback(self, dt):
        """
        Werkt de afspeeltijd en de status van noten bij als het afspelen actief is.
        """
        if self.playback_state == 'playing':
            self.midi_playback_time += dt

            # Verwerk noten voor visualisatie
            while self.note_data_index < len(self.filtered_midi_notes_data) and \
                  self.filtered_midi_notes_data[self.note_data_index]['start_time'] <= self.midi_playback_time + self.screen_travel_time:
                
                note_data = self.filtered_midi_notes_data[self.note_data_index]
                
                if MIN_MIDI_NOTE <= note_data['note'] <= MAX_MIDI_NOTE:
                    new_note = Note(note_data, self.keyboard.note_x_map, NOTE_SPEED, SCREEN_HEIGHT, KEYBOARD_HEIGHT)
                    self.active_notes_on_screen.append(new_note)
                
                self.note_data_index += 1

            # Verwerk noten voor audio afspelen en toetsenbord highlighting
            # Loop door alle noten in de filtered_midi_notes_data om te zien welke moeten starten of stoppen.
            # Dit is efficiënter dan de 'active_notes_on_screen' lijst, omdat we hier alle noten tracken.

            # Noten die moeten starten
            for i in range(len(self.filtered_midi_notes_data)):
                note_data = self.filtered_midi_notes_data[i]
                note_num = note_data['note']
                
                # Als de noot moet starten EN nog niet speelt
                if self.midi_playback_time >= note_data['start_time'] and \
                   note_num not in self.playing_midi_notes and \
                   MIN_MIDI_NOTE <= note_num <= MAX_MIDI_NOTE: # Check bereik
                    
                    self.midi_player.play_note(note_num, note_data['velocity'])
                    self.keyboard.press_key(note_num)
                    self.playing_midi_notes[note_num] = note_data['start_time'] # Markeer als spelend
                
                # Optimalisatie: Als de noot al ver voorbij de huidige tijd is, stop met zoeken
                # assuming the notes are sorted by start_time
                if note_data['start_time'] > self.midi_playback_time + 0.1: # Kleine marge
                    break
            
            # Noten die moeten stoppen
            notes_to_stop = []
            for note_num in list(self.playing_midi_notes.keys()): # Kopieer lijst om te kunnen verwijderen
                note_start_time = self.playing_midi_notes[note_num]
                # Zoek de volledige nootdata om de duur te vinden
                # Dit is minder efficiënt; idealiter sla je duur op in playing_midi_notes
                # Voor MVP: zoek de eerste die matcht
                found_note = next((n for n in self.filtered_midi_notes_data if n['note'] == note_num and n['start_time'] == note_start_time), None)
                
                if found_note and self.midi_playback_time >= (found_note['start_time'] + found_note['duration']):
                    self.midi_player.stop_note(note_num)
                    self.keyboard.release_key(note_num)
                    notes_to_stop.append(note_num)
            
            for note_num in notes_to_stop:
                del self.playing_midi_notes[note_num]

        # Update de y-positie van alle actieve noten op het scherm
        for note in self.active_notes_on_screen:
            note.update(self.midi_playback_time)

        # Verwijder noten die niet langer relevant zijn (uit beeld of speeltijd voorbij).
        self.active_notes_on_screen = [
            note for note in self.active_notes_on_screen 
            if note.is_active_and_visible(self.midi_playback_time)
        ]
        
        # Als we aan het einde van de MIDI zijn gekomen
        if self.playback_state == 'playing' and self.note_data_index >= len(self.filtered_midi_notes_data) and not self.active_notes_on_screen and not self.playing_midi_notes:
            print("Afspelen voltooid.")
            self.playback_state = 'stopped'
            self.midi_playback_time = 0.0
            self.note_data_index = 0
            self.midi_player.stop_all_notes()
            self.keyboard.active_keys.clear()


    def _draw(self):
        """Tekent alle elementen op het scherm."""
        self.screen.fill(BLACK) # Maak de achtergrond leeg (pianorol achtergrond)

        # Teken eerst de vallende noten
        for note in self.active_notes_on_screen:
            note.draw(self.screen)

        # Teken vervolgens het toetsenbord, zodat het over de noten heen ligt
        self.keyboard.draw(self.screen)

        # Teken afspeelstatus tekst
        font = pygame.font.Font(None, 30)
        status_text = f"Status: {self.playback_state.capitalize()} | Track: {self.all_midi_tracks_data.get(self.selected_track_idx, {}).get('name', 'N/A')}"
        time_text = f"Tijd: {self.midi_playback_time:.2f}s"
        status_surface = font.render(status_text, True, WHITE)
        time_surface = font.render(time_text, True, WHITE)
        
        self.screen.blit(status_surface, (10, 10))
        self.screen.blit(time_surface, (10, 40))

        pygame.display.flip() # Update het hele scherm

    def run(self):
        """Start de hoofdgame-loop van de applicatie."""
        while self.running:
            dt = self.clock.tick(60) / 1000.0 # Max 60 FPS

            self._handle_input()
            self._update_playback(dt)
            self._draw()

        self.midi_player.close() # Sluit audio resources
        pygame.quit()
        print("Neothesia Pygame MVP applicatie afgesloten.")

# --- Hoofdprogramma uitvoeren ---
if __name__ == "__main__":
    # --- MIDI- en Soundfont-paden ---
    midiFileName = "beethoven_opus10_1.mid"
    soundfontFileName = "GeneralUser-GS.sf2"
    # Dit is het relatieve pad vanuit de map waar je script staat
    midi_base_dir = os.path.join(os.path.dirname(__file__), "..", "..", "midi")
    soundfont_base_dir = os.path.join(os.path.dirname(__file__), "..", "..", "soundfonts")
    midi_file_to_play = os.path.abspath(os.path.join(midi_base_dir, midiFileName))

    # Specifiek pad voor Windows indien nodig, anders gebruikt hij de relatieve variant.
    # Pas DIT PAD aan als je op Windows werkt en het bestand niet wordt gevonden!
    if os.name == "nt":
        # Voorbeeld Windows-specifiek pad: C:\Users\m.erasmus\OneDrive - Fugro\Programmacode\python\uitprobeersels\Geluid_en_muziek\Neothasia\midi
        if(not os.path.exists(midi_file_to_play)):
            windows_base_path = r"C:\\Users\\m.erasmus\\OneDrive - Fugro\\Programmacode\\python\\uitprobeersels\\Geluid_en_muziek\\Neothasia"
            midi_file_to_play = os.path.join(windows_base_path, midiFileName)
            # print(f"Windows pad gebruikt: {midi_file_to_play}") # Debugging

    # Soundfont pad
    # VERVANG DIT MET HET PAD NAAR JOUW .sf2 BESTAND!
    # Download een gratis soundfont, bijv. "GeneralUser GS FluidSynth.sf2"
    # en plaats deze in een 'soundfonts' map naast je script, of geef het volledige pad op.
    # soundfont_base_dir = os.path.join(os.path.dirname(__file__), "soundfonts")
    # soundfont_path = os.path.abspath(os.path.join(soundfont_base_dir, "GeneralUser GS FluidSynth.sf2"))
    soundfont_path =os.path.abspath(os.path.join(soundfont_base_dir, soundfontFileName)) # Voorbeeld soundfont pad

    # Controleer of het MIDI-bestand bestaat
    if not os.path.exists(midi_file_to_play):
        print(f"\nFOUT: Het MIDI-bestand '{midi_file_to_play}' is niet gevonden.")
        print("Controleer het pad en zorg ervoor dat het bestand bestaat.")
        print("Het programma kan niet starten zonder een geldig MIDI-bestand.")
    elif not os.path.exists(soundfont_path):
        print(f"\nWAARSCHUWING: Soundfont-bestand '{soundfont_path}' niet gevonden.")
        print("Audio-afspelen zal niet werken. Download een .sf2 bestand en pas 'soundfont_path' aan.")
        print("Visualisatie werkt wel.")
        # Ga door, maar audio is uitgeschakeld
        app = NeothesiaApp(midi_file_to_play, soundfont_path)
        if app.running:
            app.run()
    else:
        # Start de Neothesia applicatie
        app = NeothesiaApp(midi_file_to_play, soundfont_path)
        if app.running: # Controleer of de MIDI-parser succesvol was
            app.run()


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
