
# Synthasia game. 1-jun-2025.
prompt

```bash
Ik wil het C#-project 'Neothesia' (https://github.com/PolyMeilex/Neothesia) vertalen naar Python. Mijn doel is om een open-source freeware Python-versie te creëren met vergelijkbare functionaliteit, met name gericht op de visualisatie van vallende noten en de synchronisatie met audio.

Om te beginnen, help me alsjeblieft met het vertalen van de kernfunctionaliteit: het lezen van MIDI-bestanden en het weergeven van vallende noten op een virtueel toetsenbord.

**Specifieke vragen voor de eerste fase:**

1.  **MIDI Parsing:** Hoe kan ik MIDI-bestanden (`.mid`) laden en de noteninformatie (nootnummer, starttijd, duur, snelheid) efficiënt extraheren in Python? Welke Python-bibliotheek is hiervoor het meest geschikt?
2.  **Grafische Weergave (Vallende Noten):** Hoe kan ik een grafische interface in Python opzetten om de "vallende noten" te visualiseren? Dit omvat:
    * Wanneer de app is opgestart, bied de gebruiker de mogelijkheid om een MIDI bestand te selecteer ter afspelen.
    * Een achtergrond die lijkt op een pianorol.
    * Rechthoekige vormen die noten representeren, die van boven naar beneden bewegen.
    * De mogelijkheid om de snelheid van de vallende noten aan te passen.
    * De mogelijkheid om het afspelen te stoppen, pauzeren, hervatten.
    * Wanneer een MIDI midi wordt ingeladen en er zijn meerdere instrumenten, geef de gebruiker een mogelijkheid om een instrument te selecteer die door de pianorol wordt afgespeeld.
    * Waneer een pianorola afspeel, speel die midi noten af.
    * Een statisch pianotoetsenbord onderaan de weergave.
    * De pianotoetsenbord heeft als label de noot naam bijvb A, B, C3, C4 enz.
    * Welke Python GUI-bibliotheek (bijv. PyQt, PyGame, Kivy) zou je aanraden voor deze taak en waarom?
3.  **Synchronisatie (Basis):** Hoe kan ik de weergave van de vallende noten op een *basisniveau* synchroniseren met de tijdsinformatie uit het MIDI-bestand, zodat de noten op het juiste moment de onderkant van het scherm bereiken? Audio afspelen hoeft nog niet in deze fase.

gebruik als voorbeeld input default midi bestand:
    midiFileName = "Alan Walker - Faded (Piano Cover Tutorial - Easy) (midi by Carlo Prato) (www.cprato.com).mid"
    midi_file_to_play = f"../../midi/{midiFileName}" # Pas dit aan naar jouw MIDI-bestand
    if(os.name == "nt"):
        # Windows-specifiek pad
        midi_file_to_play =  f"C:\\Users\\m.erasmus\\OneDrive - Fugro\\Programmacode\\python\\uitprobeersels\\Geluid_en_muziek\\Neothasia\\midi\\{midiFileName}" # os.path.abspath(midi_file_to_play)

Geef codevoorbeelden voor elk van de bovenstaande punten en leg de concepten en gekozen bibliotheken duidelijk uit. Zorg voor een modulair ontwerp zodat we later makkelijk audioafspelen en toetsenbordhighlighting kunnen toevoegen.
```

## prompt 
### direct translate website code
```bash
translate all code in https://github.com/PolyMeilex/Neothesia to Pyhton using appropriate python libraries.

Before your response, show your thinking process, add a unique -char UUID, add a version number scubas "Neothasia_pythonV1", "Neothasia_pythonV2" etc. Append today's date time in Den Haag, then output. Show code neatly formatted for me to copy-paste to VS Code.
```
