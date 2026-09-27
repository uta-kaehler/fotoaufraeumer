# Werkstattbericht: Wie der Fotoaufräumer entstanden ist

> **English summary.** This tool was built in a single session of about one hour, in a conversation
> with Claude in Claude Code, after Gemini had supported Uta Kähler in setting up GitHub. Uta has no
> programming background and writes no code. She specified the problem by dictation, installed
> Python from the Microsoft Store, ran each version on about 5,000 of her own photos, and directed
> the next iteration from what she observed in real use. She held final responsibility; Claude
> proposed and wrote the code. Three of her test reports (duplicates not shown, a crash on Windows,
> missing WhatsApp images) each led to a concrete adjustment; a fourth remark (“sort by year, month and place”) became a
> new feature. Her requirement sentences below are quoted verbatim from the dictated conversation,
> because they are the actual specification.

## Wer was gemacht hat

- **Uta Kähler (Letztverantwortung):** Ziel, Anforderungen, Auswahl aus den Vorschlägen, Tests mit
  der echten Fotosammlung, Entscheidung über die nächsten Schritte, Abnahme.
- **Gemini (Google):** Unterstützung bei der Einrichtung von GitHub (Konto und Repository).
- **Claude (Anthropic, in Claude Code):** Vorschläge und Umsetzung: Entwurf, gesamter Code,
  Anleitung, Nachjustierung.

Kein Pflichtenheft, keine Vorlage. Die Anforderungen kamen gesprochen, per Diktierfunktion, und
stehen hier so, wie sie ankamen: ungeglättet, mit Auslassungen […] nur dort, wo es privat wurde.

## 1. Das Problem, in ihren Worten

> „Und das Coole wäre natürlich, wenn mal die Fotos aufgeräumt würden, aber ich weiß überhaupt
> nicht, was ich tun muss, um ehrlich zu sein.“

> „Und das Problem ist immer, wenn ich irgendwas löschen will, das ist einfach zu klein, man erkennt
> gar nicht, was man löscht. Deswegen lasse ich es dann immer gefrustet.“

> „Also vielleicht wäre erstmal irgendwie wichtig, alle unscharfen Fotos zu löschen, alle, die
> doppelt sind, zu löschen. Und dann habe ich wirklich keine Ahnung, was ich mit diesen ganzen
> Dokumenten und Screenshots machen soll. Einige sind brauchbar, und müssten bleiben, einige sind
> total sinnlos.“

Der zweite Satz ist der Kern. Das eigentliche Hindernis war nicht fehlende Zeit, sondern fehlende
Sicht. Daraus schlug Claude zwei Grundentscheidungen vor, die sie übernahm:

1. **Groß zeigen.** Die Oberfläche läuft im Browser am Laptop, die Bildgröße ist per Regler frei
   wählbar, jedes Foto lässt sich bildschirmgroß öffnen.
2. **Nie löschen.** Wer aus Angst vor dem Falschen gar nicht löscht, braucht eine Tür zurück.
   Aussortiertes wird nur verschoben und ist mit einem Klick wieder da. Endgültig weg ist es erst,
   wenn sie den Ordner selbst leert.

Dazu kam die dritte Anforderung als eigene Kategorie: Dokumente und Screenshots bekommen eigene
Stapel, und es gibt einen zweiten Zielordner `_Dokumente` für die brauchbaren.

## 2. Erste Version und erster Test

Die erste Version analysierte den Ordner, gruppierte Doppelte, bewertete Schärfe und
Dokument-Ähnlichkeit und zeigte alles im Browser. Uta installierte Python aus dem Microsoft Store
(„aus dem Microsoft Store muss ich was holen, okay, na, ich versuch's mal“), lud das Werkzeug als
ZIP herunter und startete es per Doppelklick.

> „Nein, lief ganz super durch. Er hat auch gesagt, er hat fünftausendeinhundertsiebenundvierzig
> Fotos erkannt.“

> „Er sagt theoretisch gesehen 197 Doppelte, was mich überraschen würde, wenn es so 197 wären.
> Aber die werden zum Beispiel nicht angezeigt, auch die anderen nicht.“

**Beobachtung:** Die Vorschaubilder wurden unter derselben Sperre erzeugt wie alle anderen Anfragen. Große
HEIC-Fotos brauchen dafür je eine Sekunde oder mehr, also blieb beim Reiterwechsel minutenlang alles
leer. **Nachjustierung:** Verkleinern ohne Sperre, alle kleinen Vorschauen gleich nach dem Start im
Hintergrund, Doppelte zuerst. Bei der Gelegenheit: Dokumente und Screenshots gelten nur noch bei
exakt gleicher Datei als doppelt, damit Seite 1 und Seite 2 eines Briefs nicht als Serie gelten.

## 3. Der Absturz unter Windows

Nach dem nächsten Start kam statt der Übersicht eine Fehlermeldung, die Uta als Bildschirmfoto
schickte: ein `TypeError` beim Vergleich von Bytes mit einer Zahl.

**Beobachtung:** Die Dokument-Erkennung lieferte einen NumPy-`float32`, den SQLite unter Windows als rohe
Bytes speicherte. Aufgefallen ist es erst durch die Änderung aus Schritt 2, die diese Werte zum
ersten Mal beim Gruppieren verwendete; auf dem Testrechner unter Linux trat es nicht auf.
**Nachjustierung:** Werte werden als normale Zahlen gespeichert, und bereits gespeicherte Bytes werden beim Öffnen zurückverwandelt,
damit die lange Analyse nicht wiederholt werden muss.

## 4. Was fehlte

> „So, jetzt habe ich 424 aussortiert, was ja prinzipiell ganz cool ist. Aber von 5300 natürlich
> irgendwie ein bisschen wenig. Und das Ganze WhatsApp-Gedödel, das hat es gar nicht angezeigt.“

**Beobachtung:** Kein Programmfehler. Auf einem Samsung-Handy liegen WhatsApp-Bilder und Screenshots
nicht im Kamera-Ordner, sie waren also gar nicht mitkopiert worden. **Nachjustierung:** Die Anleitung
erklärt jetzt, in welchen Handy-Ordnern sie liegen.

> „Und ich glaube, nach Jahren und Monaten sortieren wäre auch sinnvoll. Weil dann kann man nämlich
> gleich irgendwie gucken, wo man hin will. Gäbe es eigentlich eine Möglichkeit, die nach Orten zu
> sortieren? […] so typische Urlaubsorte, alles was Spanien ist, Italien ist, Finnland ist, Sowas.“

**Erweiterung:** Neuer Reiter „Stöbern“ mit Filtern nach Jahr, Monat und Land. Das Land wird ohne
Internet aus den GPS-Daten im Foto bestimmt: nächster Ort aus einem mitgelieferten
GeoNames-Verzeichnis, Ländernamen auf Deutsch. Bereits analysierte Fotos bekommen ihr Land beim
nächsten Start nachgetragen.

## 5. Nachjustieren statt Fehler suchen

Claude hatte den hängenden Start und den Absturz ausdrücklich auf die eigene Kappe genommen („der Fehler war meiner“,
„sorry“). Die Antwort darauf:

> „Und ganz ehrlich, findest du dich nicht ein bisschen streng, wenn man sowas baut, ist doch
> normal, dass da irgendwas nicht funktioniert, oder?“

Das ist mehr als eine Randnotiz. Die Tests waren nur so schnell und so gut, weil Unstimmigkeiten als
Information behandelt wurden und nicht als Versagen, als etwas, das nachjustiert wird: Bildschirmfoto schicken, beschreiben, was man
sieht, weitermachen. Genau diese Rückmeldungen hätte kein automatischer Test geliefert. Das
Windows-Verhalten von SQLite, der Ort der WhatsApp-Bilder auf einem Samsung und die Frage, ob 197
Doppelte plausibel sind, zeigten sich erst an echten Fotos auf einem echten Laptop.

## Was man daraus mitnehmen kann

- **Die Anforderung steckt im Frust, nicht in der Funktionsliste.** „Man erkennt gar nicht, was man
  löscht“ hat die ganze Architektur bestimmt.
- **Sicherheit vor Tempo.** „Nie löschen“ kostet einen Ordner und senkt die Hemmschwelle auf null.
- **Echte Daten schlagen jede Testumgebung.** Alle drei Befunde zeigten sich erst an echten Fotos
  auf einem echten Laptop.
- **Die Rollen waren klar.** Vorschläge und Code kamen von der KI, Auswahl, Urteil und
  Letztverantwortung blieben beim Menschen. Das Werkzeug war fertig, als die Person, die es
  braucht, damit aufgeräumt hat.
