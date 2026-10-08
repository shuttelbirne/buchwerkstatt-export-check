# Buchwerkstatt Export Check

Ein kleines, lokal laufendes Python-Werkzeug für den TXT-Export der
[Rauschwerk-Autorenwerkstatt](https://rauschwerkverlag.de/buchwerkstatt/).
Es zeigt, ob die fünf Abschnitte im erwarteten Format vorhanden sind,
welche noch offen sind und wie viel Text jeder enthält. Eine SHA-256-Prüfsumme
hilft beim Vergleich zweier Dateikopien. Die Datei wird nur gelesen.

## Ohne Konto und ohne Modellaufruf

Python 3.9 oder neuer genügt. Keine Pakete installieren, keine API-Schlüssel
angeben, keinen Text hochladen. Das Programm verwendet keine Netzwerkfunktionen.
Es gibt keine Manuskript-Auszüge und keinen Dateipfad aus. Die Ausgabe enthält
Abschnittsnamen, Umfang und Prüfsumme; auch diese Angaben können privat sein.

```sh
python3 check_export.py /pfad/zu/rauschwerk-buchentwurf.txt
python3 check_export.py /pfad/zu/rauschwerk-buchentwurf.txt --json
```

Zum Ausprobieren mit ausschließlich erfundenem Material:

```sh
python3 check_export.py examples/fiktiver-entwurf.txt
```

## Was wird geprüft?

| Abschnitt | Frage für die eigene Durchsicht |
| --- | --- |
| ARBEITSTITEL | Habe ich einen vorläufigen Titel festgehalten? |
| BUCHIDEE | Ist mein Ausgangsmaterial mitgenommen worden? |
| LESERSCHAFT | Weiß ich noch, für wen ich schreiben möchte? |
| KAPITELPLAN | Kann ich meine Gliederung außerhalb des Browsers lesen? |
| TEXTENTWURF | Sind meine tatsächlichen Formulierungen enthalten? |

Das Werkzeug erkennt die Abschnittsmarken und zählt den Text dazwischen.
Es beantwortet die Fragen nicht inhaltlich. `(noch offen)` oder ein leerer
Abschnitt bleibt ein offener Arbeitsstand, kein Fehler. Wortzahlen zählen
durch Leerraum getrennte Einheiten, keine linguistischen Wörter. Zeichen
sind Python-Unicode-Codepunkte, keine sichtbaren Glyphen.

Ein gültiger Export ergibt Exitcode `0`, auch mit offenen Abschnitten.
Ein unlesbares, zu großes oder abweichendes Format ergibt `2`.
UTF-8 mit oder ohne BOM und LF/CRLF-Zeilenenden sind lesbar. Die Prüfsumme
bezieht sich auf die ursprünglichen Bytes: Schon andere Zeilenenden ändern sie.
Gleiche Prüfsummen bestätigen gleiche Bytes; sie beweisen weder Autorenschaft
noch Vollständigkeit gegenüber einem früheren Entwurf.

## Der wichtige Schritt bleibt dein eigener

1. Den eigenen Entwurf im Schreibplatz als TXT herunterladen.
2. Die Datei im Texteditor öffnen und mit dem sichtbaren Schreibplatz vergleichen.
3. Die Strukturprüfung laufen lassen. Bei fehlenden oder mehrdeutigen Marken
   die unveränderte Originaldatei behalten und den Text manuell ansehen.
4. Eine zweite Kopie an einem selbst gewählten Ort sichern. Das Programm erstellt
   keine Sicherung und stellt keine geschlossenen Browser-Tabs wieder her.

Die Buchwerkstatt verwendet für diesen freien Schreibplatz einen temporären
Speicher im aktuellen Browser-Tab. Ein Download ist deshalb ein eigener
Arbeitsschritt. Dieses separate Prüfwerkzeug ist eine kleine Ergänzung für
Menschen, die ihre Texte als lesbare Dateien behalten möchten; der Schreibplatz
selbst braucht dieses Programm nicht.

Das einfache TXT-Format hat keine Escape-Regel für Abschnittsmarken.
Eine Zeile im eigenen Manuskript, die exakt `BUCHIDEE` oder eine der anderen
Marken lautet, kann mehrdeutig sein. In diesem Fall stoppt die Prüfung, statt
einen vermeintlich korrekten Bericht zu erzeugen. Umformatierte Word-Dateien,
DOCX, PDF und Exportvarianten anderer Werkzeuge werden nicht unterstützt.
Die Datei darf maximal 2 MiB groß sein.

## Für KI-Arbeit gilt dieselbe Grenze

Eine formal lesbare Datei sagt nichts über die Richtigkeit ihrer Aussagen aus.
Das Programm prüft keine Quellen, Rechte, Grammatik oder KI-Veränderungen und
erteilt keine Veröffentlichungsempfehlung. Änderungen des Werkstatt-Exportformats
können eine Anpassung dieses Werkzeugs erfordern. Unterstützt wird das am
8. Oktober 2026 öffentlich bereitgestellte Format.

## Entwicklung und Herkunft

```sh
python3 -m unittest discover -s tests -v
```

Dieses Projekt wurde von einem KI-Assistenten mit ChatGPT/Codex für Rauschwerk
erstellt. Das Beispiel ist vollständig fiktiv. Automatisierte Funktionsprüfungen
ersetzen keine persönliche redaktionelle Prüfung durch Tim Heise.
Der Anbieter ist Rauschwerk Verlag; eine unabhängige Bewertung des Verlags wird
hier nicht behauptet. Code, Beispiel und Dokumentation stehen unter MIT-Lizenz.
