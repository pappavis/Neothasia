# Neothasia
Piano noten als watervalformaat.

Vibe coding experiment.

<img src="./img/neothasia.png"><br>

# Installatie
Je benodig minimaal <a href="https://python.org" target="_blank">python3.11</a> nodig.

```bash
pip install pygame mido python-rtmidi python-fluidsynth
```

## Projectstructuur


```bash
neothasia/
│
├── main.py              ← Hoofdprogramma
├── midi_parser.py       ← Voor laden/parsen MIDI
├── visualizer.py        ← Voor tekenen van noten, toetsenbord, UI
├── synthesizer.py       ← Voor MIDI audio afspelen
└── assets/
    └── fonts/
    └── soundfonts/
```        └── GeneralUser-GS.sf2


Download <a href='https://github.com/mrbumpy409/GeneralUser-GS/blob/main/GeneralUser-GS.sf2'>GeneralUser-GS.sf2</a>

door: Michiel Erasmus
