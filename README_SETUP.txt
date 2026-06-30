============================================================
  E-Mail-Assistent – SunProPower
  Einrichtungsanleitung fuer Fredi
============================================================

VORAUSSETZUNGEN:
  Python muss installiert sein (einmalig).
  Download: https://python.org → "Download Python 3.x"
  Bei der Installation: Haken bei "Add Python to PATH" setzen!

------------------------------------------------------------
ERSTEINRICHTUNG (einmalig):
------------------------------------------------------------
1. Doppelklick auf "install.bat"
2. Warten bis "Installation erfolgreich" erscheint
3. Fertig — install.bat nie wieder benoetigt

------------------------------------------------------------
TAEGLICH NUTZEN:
------------------------------------------------------------
1. Doppelklick auf "start.bat"
2. Browser oeffnet sich automatisch
3. Fertig!

Um die App zu beenden: Das Fenster in der Taskleiste schliessen.

------------------------------------------------------------
ERSTE ANMELDUNG (Zugangsdaten eingeben):
------------------------------------------------------------
1. App starten (start.bat)
2. Oben rechts auf das Zahnrad-Symbol klicken (Einstellungen)
3. Postfach 1: Passwort eingeben, "Verbindung testen" klicken
4. Postfach 2: Passwort eingeben
5. Claude API: API-Key eingeben (von console.anthropic.com)
6. "Einstellungen speichern" klicken

WICHTIG bei Postfach 1 (Microsoft/Outlook):
  Falls "Microsoft blockiert die Anmeldung" erscheint:
  → App-Passwort erstellen unter:
    https://account.microsoft.com/security
  → Dann das App-Passwort statt dem normalen Passwort eingeben.

------------------------------------------------------------
STIL-BEISPIELE HINZUFUEGEN:
------------------------------------------------------------
1. Einstellungen oeffnen (Zahnrad-Symbol)
2. Ganz unten: "Stil-Beispiele"
3. Eine fertige E-Mail von Fredi als .txt-Datei speichern
4. Diese Datei hochladen
5. Die KI lernt daraus Fredis Schreibstil

------------------------------------------------------------
DATEISTRUKTUR (was wo liegt):
------------------------------------------------------------
start.bat        ← Fredi klickt das taeglich
install.bat      ← Nur einmalig bei der Einrichtung
launcher.py      ← Wird automatisch von start.bat aufgerufen
app/             ← Programm-Dateien (nicht aendern)
config.json      ← Zugangsdaten (verschluesselt, sicher)
contacts.json    ← Gespeicherte Kundenkontakte
style_examples/  ← Fredis E-Mail-Beispiele fuer die KI

============================================================
