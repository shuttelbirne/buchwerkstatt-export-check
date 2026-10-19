# Buchwerkstatt Export Check

Ein kleines, lokal laufendes Python-Werkzeug für den TXT-Export der
[Rauschwerk-Autorenwerkstatt](https://rauschwerkverlag.de/buchwerkstatt/).
Es zeigt, ob die fünf Werkstattabschnitte im unterstützten Format vorhanden sind,
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

Das Werkzeug prüft die Abschnittsstruktur und zählt den Text darin.
Es beantwortet die Fragen nicht inhaltlich. Ein leerer oder nur aus Leerraum
bestehender Abschnitt bleibt offen. Im alten Format vom 8. Oktober gilt auch
`(noch offen)` als Platzhalter. In TXT 2 und TXT 3 ist diese Zeichenfolge ein
eigener Textinhalt. Wortzahlen zählen
durch Leerraum getrennte Einheiten, keine linguistischen Wörter. Zeichen
sind Python-Unicode-Codepunkte, keine sichtbaren Glyphen.

Ein erkanntes unterstütztes Format ergibt Exitcode `0`, auch mit offenen Abschnitten.
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

Die Buchwerkstatt bietet inzwischen auch getrennte Kapitel, Projektdateien und
einen ausgewählten Manuskriptexport. Dieses Prüfprogramm ist für den
TXT-Entwurf mit den fünf Werkstattabschnitten gedacht. Es erstellt keine
Projektdatei und wertet weder gespeicherte Fassungen noch separate Kapitel aus.
Der Schreibplatz selbst braucht dieses Programm nicht.

## Unterstützte Formatversionen

| Format | Verhalten |
| --- | --- |
| Alter Fünf-Abschnitt-Export vom 8. Oktober 2026 | Abschnittsmarken müssen eindeutig sein; bisherige Zählung bleibt erhalten. |
| Fünf-Abschnitt-Export TXT 2 | Eindeutige Abschnittsmarken; `(noch offen)` wird als eigener Text gezählt. |
| Fünf-Abschnitt-Export TXT 3 | Die gespeicherten Abschnittslängen bestimmen die Grenzen. Gleichlautende Marken im Nutztext sind damit lesbar. |
| TXT-Export mit getrennten Kapiteln | Erkannt, aber nicht ausgewertet; Exitcode 2 mit konkretem Hinweis. |
| Ausgewähltes Manuskript, Projekt-JSON, DOCX, PDF, fremdes oder unbekanntes Format | Nicht unterstützt; Exitcode 2. |

TXT 3 speichert Längen als JavaScript-UTF-16-Einheiten. Der Prüfer liest sie in
dieser Einheit; Zeichen- und Wortzahlen im Bericht bleiben davon getrennt.
Ein Emoji kann beispielsweise zwei UTF-16-Einheiten belegen, obwohl Python
einen Codepunkt zählt. Im TXT-3-Bericht werden führende und abschließende
Leerzeichen des Abschnitts mitgezählt. Bei älteren Formaten werden diese wie
bisher für die Zählung entfernt.

Im alten Format und TXT 2 kann eine eigene Zeile wie `BUCHIDEE` mehrdeutig sein.
Die Prüfung stoppt dann. In TXT 3 stoppt sie bei fehlenden, ungültigen oder nicht
mehr zum Text passenden Längen. Anders als die Werkstatt mit ihrer manuellen
Vorschau versucht dieses Kommandozeilenwerkzeug dann keinen Ersatzimport über
Abschnittsmarken. Die Originaldatei bleibt unverändert; manuelle Änderungen
können deshalb eine eigene Durchsicht erfordern. Die Datei darf maximal 2 MiB
groß sein.

Die JSON-Ausgabe enthält zusätzlich `format_version` und
`coverage: "five-workspace-sections"`. Ein positives Ergebnis bestätigt nur den
hier beschriebenen Strukturumfang. Es beweist keine Vollständigkeit eines
Buchprojekts und keine Übereinstimmung mit einem nicht vorliegenden Original.

## Für KI-Arbeit gilt dieselbe Grenze

Eine formal lesbare Datei sagt nichts über die Richtigkeit ihrer Aussagen aus.
Das Programm prüft keine Quellen, Rechte, Grammatik oder KI-Veränderungen und
erteilt keine Veröffentlichungsempfehlung. Änderungen des Werkstatt-Exportformats
können eine Anpassung dieses Werkzeugs erfordern. Die aktuelle TXT-3-Unterstützung
wurde am 19. Oktober 2026 gegen die öffentlich gelesene Exportfunktion geprüft.
Die Referenzfälle entstanden aus dieser unveränderten Funktion mit fiktiven
Eingaben; daraus wird kein vollständiger Browser- oder Nutzertest abgeleitet.

## Entwicklung und Herkunft

```sh
python3 -m unittest discover -s tests -v
```

Dieses Projekt wurde von einem KI-Assistenten mit ChatGPT/Codex für Rauschwerk
erstellt. Das Beispiel ist vollständig fiktiv. Automatisierte Funktionsprüfungen
ersetzen keine persönliche redaktionelle Prüfung durch Tim Heise.
Der Anbieter ist Rauschwerk Verlag; eine unabhängige Bewertung des Verlags wird
hier nicht behauptet. Code, Beispiel und Dokumentation stehen unter MIT-Lizenz.
