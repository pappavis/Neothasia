import pygame.midi
import time
import threading
from mido import MidiFile

class MIDISynthesizer:
    def __init__(self):
        pygame.midi.init()
        self.player = None
        self.stop_flag = True

        self.device_id = self.find_valid_output_device()
        if self.device_id is not None:
            try:
                self.player = pygame.midi.Output(self.device_id)
                print(f"MIDI Output geopend op apparaat ID {self.device_id}")
            except Exception as e:
                print(f"Fout bij openen MIDI output: {e}")
                self.player = None
        else:
            print("Geen geldig MIDI output apparaat gevonden.")

    def find_valid_output_device(self):
        """Zoek naar een geldig MIDI output apparaat."""
        for i in range(pygame.midi.get_count()):
            info = pygame.midi.get_device_info(i)
            if info and info[1]:  # [1] is 'output' boolean
                print(f"Gevonden MIDI output apparaat: ID {i}, Naam: {info[1]}")
                return i
        return None

    def play_midi(self, midi_path):
        if not self.player:
            print("Kan MIDI niet afspelen: Geen geldig output apparaat.")
            return

        def play():
            try:
                mid = MidiFile(midi_path)
                for msg in mid.play():
                    if self.stop_flag:
                        break
                    if msg.type == 'note_on':
                        self.player.note_on(msg.note, msg.velocity)
                    elif msg.type == 'note_off':
                        self.player.note_off(msg.note, msg.velocity)
                    time.sleep(msg.time)
            except Exception as e:
                print(f"Fout bij afspelen MIDI: {e}")

        self.stop_flag = False
        self.thread = threading.Thread(target=play)
        self.thread.start()

    def stop(self):
        self.stop_flag = True
        if self.player:
            self.player.reset()
            self.player.close()
        print("MIDI output gestopt.")
