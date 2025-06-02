# ref https://chat.qwen.ai/c/822dc4b0-d656-41fd-8b73-3255fc8e39f8
import mido
from mido import MidiFile
import os

def load_midi_notes(midi_path):
    """
    Laadt MIDI-bestand en retourneert een lijst van genormaliseerde nootgebeurtenissen:
    {
        'note': int,
        'start_time': float (in seconden),
        'end_time': float (in seconden),
        'velocity': int
    }
    """
    try:
        mid = MidiFile(midi_path)
    except Exception as e:
        print(f"Fout bij laden MIDI-bestand: {e}")
        return []

    notes = []
    current_time = 0.0
    active_notes = {}

    for track in mid.tracks:
        for msg in track:
            current_time += msg.time
            if msg.type == 'note_on' and msg.velocity > 0:
                active_notes[msg.note] = {'start_time': current_time, 'velocity': msg.velocity}
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                note_data = active_notes.pop(msg.note, None)
                if note_data:
                    note_data['end_time'] = current_time
                    note_data['note'] = msg.note
                    notes.append(note_data)

    return notes
