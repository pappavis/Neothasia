import mido
from mido import MidiFile
import os

def get_midi_tracks(midi_path):
    try:
        mid = MidiFile(midi_path)
    except Exception as e:
        print(f"Fout bij laden MIDI-bestand: {e}")
        return []

    tracks_info = []
    for i, track in enumerate(mid.tracks):
        track_name = ""
        for msg in track:
            if msg.type == 'track_name':
                track_name = msg.name
                break
        tracks_info.append({
            "index": i,
            "name": track_name or f"Track {i}"
        })
    return tracks_info


def load_midi_notes(midi_path, selected_track_index=0):
    try:
        mid = MidiFile(midi_path)
    except Exception as e:
        print(f"Fout bij laden MIDI-bestand: {e}")
        return []

    notes = []
    current_time = 0.0
    active_notes = {}

    selected_track = mid.tracks[selected_track_index]

    for msg in selected_track:
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