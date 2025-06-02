import mido

def load_midi(file_path):
    midi = mido.MidiFile(file_path)
    notes = []
    current_time = 0
    for track in midi.tracks:
        for msg in track:
            current_time += msg.time
            if msg.type == 'note_on' and msg.velocity > 0:
                notes.append((msg.note, current_time / midi.ticks_per_beat, msg.channel))
    return notes
