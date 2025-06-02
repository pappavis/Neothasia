import pygame.midi
import time
import threading
from mido import MidiFile

class MIDISynthesizer:
    def __init__(self):
        pygame.midi.init()
        self.player = pygame.midi.Output(0)
        self.stop_flag = True

    def play_midi(self, midi_path):
        def play():
            mid = MidiFile(midi_path)
            for msg in mid.play():
                if self.stop_flag:
                    break
                if msg.type == 'note_on':
                    self.player.note_on(msg.note, msg.velocity)
                elif msg.type == 'note_off':
                    self.player.note_off(msg.note, msg.velocity)
                time.sleep(msg.time)
        self.stop_flag = False
        self.thread = threading.Thread(target=play)
        self.thread.start()

    def stop(self):
        self.stop_flag = True
        self.player.reset()